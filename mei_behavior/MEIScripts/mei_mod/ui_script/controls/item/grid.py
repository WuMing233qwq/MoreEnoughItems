# coding=utf-8

# ----------------------------------------------------------------------
#  grid.py is part of MoreEnoughItems.
#  Copyright (C) 2026 WuMing233qwq <2691068930@qq.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation, version 3 only.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program.
#  If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------

import time

import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.proxy.focus.search import contains, control_rect
from MEIScripts.utils import utilities, LogPatcher
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.bindname import make_binding_name
from MEIScripts.utils.text import error_text

ViewBinder = clientApi.GetViewBinderCls()


def binding_prefix(collection_name):  # type: (str) -> str
    """
    一个 grid 的绑定名前缀：meiui.<集合名>，JSON 侧在 grid 上写同样的 `$binding_name_prefix`。

    每个 grid 用自己的前缀（原先全部共用 meiui.item_panel，绑定名只差集合名）。SDK 解绑时传的是
    （界面, 集合名, 绑定名）三样，所以共用前缀多半无害，也不是「收藏栏操作后别的 grid 只剩一个物品」的原因
    —— 真正的几个口子见 ItemsGrid 的 SetGridDimension / PauseBindings / CreateBindingCallback
    与 BaseItemsGridScript.GetItemGrids。前缀照样分开：排查时一眼看得出是谁的绑定
    """
    return "meiui." + collection_name


_ROOT_SEGMENT = "/variables_button_mappings_and_controls"
_GRIDS = {}  # type: dict  # 规范化的 grid 路径 -> [绑着的 ItemsGrid, ...]（同一个路径在几个界面里可能各有一份；UnbindAll 摘掉）
_KEEP_PER_PATH = 4  # 同一个路径最多记几份（万一有没解绑就丢掉的，不让它一直涨）


def _grid_key(path):  # type: (any) -> str
    """ 引擎事件给的路径「从 UI 根节点算起」，SDK 控件的路径可能多开头那一层（引擎结论 §24）：两边都去掉它、去掉结尾的「/」再比 """
    text = path if isinstance(path, basestring) else ""
    if text.startswith(_ROOT_SEGMENT):
        text = text[len(_ROOT_SEGMENT):]
    return text.rstrip("/")


def grid_rearranged(path):  # type: (any) -> int
    """
    引擎事件 GridComponentSizeChangedClientEvent（某个 grid 的格子重新排列了；客户端主系统转来）：路径对得上的 MEI grid
    把图标重设一遍（ItemsGrid.OnRearranged）。一边的路径是另一边的结尾就算对上（两边的起点不一定一样）；没给路径就通知全部。
    返回通知了几个；一个出错不影响别的
    """
    target = _grid_key(path)
    notified = 0
    for key, grids in list(_GRIDS.items()):
        if target and not (key.endswith(target) or target.endswith(key)):
            continue
        for grid in list(grids):
            try:
                grid.OnRearranged()
                notified += 1
            except Exception as e:  # noqa  引擎事件的回调里，抛出去只会丢掉这一次通知
                logger.error("[MEI/grid] {}: 格子重新排列后补画失败: {}".format(
                    getattr(grid, "CollectionName", "?"), error_text(e)))
    return notified


class ItemsGrid(object):
    """ 用于管理 ItemPanel 的 Grid 控件的逻辑 负责管理绑定属性的处理 """

    PAUSE_AFTER_PASSES = 3
    """
    缓存写满后再等几轮完整拉取才暂停绑定：`always_when_visible` 的绑定（数量、角标、悬停文字）要等控件
    变可见的下一帧才会拉，写满当帧就停，它们就停在上一页的值上 —— 表现是翻页、第一次收藏后
    数量与上标经常丢，要多翻几次才对。轮数按第 0 格的 `.visible` 回调数，它是 always，每帧都拉一次
    """

    STUCK_SECONDS = 1.0
    """ 自检：面板没建全、停了这么久才算卡住（刚翻页、刚改行列数时，引擎要一两帧才把格子建出来、拉一遍） """

    MAX_REPAIRS = 2
    """ 自检：卡住时连着修几次就停手（界面被别的界面盖住时拉取本来就停，别一直修、一直记日志）；建全一次就重新算 """

    REPAINT_PASSES = (2, 3)
    """
    推完行列数之后（或者引擎说格子重新排列了之后），第几轮到第几轮拉到某一格时**核对**它的图标：渲染器上画的不是这一格的物品
    就重设（__CheckIcon）。行列数变了引擎重建格子，重建之前那一轮拉绑定时建好的面板把图标设在了旧控件上（SDK 的控件按路径找，
    SetUiItem 只在建面板时设一次），新控件没有图标 —— 可见、数量这些走绑定的会自己拉到，图标不会（引擎结论 §46）。
    按拉绑定的轮数数、不按时间（换类型那一帧很重，定时器可能赶在重建之前到）。格子重建得晚的，靠引擎的「格子重新排列了」事件
    （grid_rearranged → OnRearranged）当场补；小 grid 还可以把窗口开长（实例的 RepaintPasses：配方页的工作站开到 30 轮 ——
    熔炉 → 高炉这类工作站从 2 格变 1 格时，格子比第 2、3 轮还晚重建，补画落空）
    """

    DIMS_CHECK_DELAY = 0.15
    """
    行列数推下去后过这么久看一眼引擎的 grid 有没有最后一格，没有就当场重推 —— 两栏藏着时推的、界面刚建出来那一帧推的，
    引擎常常没接住；等 STUCK_SECONDS 的自检才补的话，展开后要过好一会儿才复位
    """

    DIMS_FAST_REPUSH = 2
    """ 快速核对连着重推几次就停手（这一栏一直藏着时引擎本来就不建格子），等显出来时 Revive 再推 """

    DIMS_CHECK_PASSES = 2
    """
    推完行列数后，第 0 格的 .visible 至少又被拉了这么多轮（格子真建出来了）才去问最后一格。
    SDK 的 GetGridItem 在格子还没建出来时会 print 一行 `error: cannot find position (x, y) in grid`：
    只等 0.15 秒就问的话，开界面那几帧格子还没建、两栏藏着时引擎根本不建，每次开界面每个 grid 都打三行。
    卡在 1×1（行列数丢了）时第 0 格照样被拉，所以照样查得出来
    """

    def __init__(self, control, child_name, collection_name, binding_name_prefix, item_panel_callback):
        main_node = context.GetMainNode()
        self.Bindings = ScreenBinder(main_node.ScreenNode)  # type: ScreenBinder
        self.ChildName = child_name
        self.Prefix = binding_name_prefix
        self.Control = control
        self.MainNode = main_node
        self.CollectionName = collection_name
        self.ItemPanelCallback = item_panel_callback
        self.ItemPanels = {} # type: dict
        self.BindingWrappers = {}  # type: dict
        self.BindingConfigs = {}  # type: dict
        self.Rows = 0  # type: int or None
        self.Cols = 0  # type: int or None
        self.CacheSaturated = False  # type: bool
        self.AutoCacheLimitEnabled = True  # type: bool
        self.BindingPausedWhenSaturated = True  # type: bool
        self.PendingPause = False  # type: bool
        self.PendingPasses = 0  # type: int  # 写满之后第 0 格又被拉了几轮，够 PAUSE_AFTER_PASSES 才暂停
        self.BindingsPaused = False  # type: bool
        self.BindingTemplates = []  # type: list
        self.Pulls = 0  # type: int  # 第 0 格的 .visible 被拉了几次：自检拿它看绑定还活着没有

        self.__PushedDims = None  # type: tuple or None  # 这个实例推给引擎的行列数（没推过是 None）
        self.__PauseScheduled = False  # type: bool  # 暂停已经排到下一帧了
        self.__Game = None  # 排下一帧用的 GameComp，第一次用到才建
        self.__Faults = {}  # type: dict  # 绑定名 -> 回调抛异常的次数（日志只记第一次）
        self.__StuckSince = None  # type: float or None  # 自检：从什么时候起面板没建全
        self.__StuckPulls = 0  # type: int  # 自检：那时的 Pulls
        self.__Repairs = 0  # type: int  # 自检：卡住以来修了几次
        self.__DimsCheckAt = None  # type: float or None  # 刚推完行列数：到这个时刻看一眼最后一格（DIMS_CHECK_DELAY）
        self.__FastRepushes = 0  # type: int  # 快速核对连着重推了几次
        self.__PullsAtPush = 0  # type: int  # 推行列数那一刻的 Pulls：之后又拉够 DIMS_CHECK_PASSES 轮才核对
        self.Shown = True  # type: bool  # 所在那一栏显示着（脚本按悬浮窗的样子写，SetShown）：藏着时引擎不建格子，自检与快速核对都不做
        self.__RepaintWindow = None  # type: tuple or None  # 核对图标的那几轮（Pulls 的区间，RepaintPasses）
        self.RepaintPasses = self.REPAINT_PASSES  # type: tuple  # 推完行列数 / 格子重新排列后核对哪几轮；小 grid 可以开长
        self.__WakeScheduled = False  # type: bool  # 格子重新排列后「恢复绑定」已经排到下一帧了

    def InitBindings(self):
        self.BindConfigs(self.GetDefaultBindingConfigs())

    def UnbindAll(self):
        """ 全部解绑；顺带清掉暂停状态 —— 排到下一帧的暂停、之后的 ClearItemPanels 都不会再碰引擎 """
        for _, wrapper in list(self.BindingWrappers.items()):
            self.Bindings.Unbind(wrapper)
        self.BindingWrappers = {}
        self.BindingConfigs = {}
        self.BindingsPaused = False
        self.PendingPause = False
        self.PendingPasses = 0
        self.__Untrack()

    def __Key(self):  # type: () -> str
        get_path = getattr(self.Control, "GetPath", None)
        return _grid_key(get_path()) if get_path is not None else ""

    def __Track(self):
        """ 记进 _GRIDS：引擎说这个 grid 的格子重新排列了，就通知到它（grid_rearranged）。绑上、推行列数时都记一下（记过的不重记）"""
        key = self.__Key()
        if not key:
            return
        grids = _GRIDS.setdefault(key, [])
        if not any(grid is self for grid in grids):
            grids.append(self)
            del grids[:-_KEEP_PER_PATH]

    def __Untrack(self):
        key = self.__Key()
        grids = _GRIDS.get(key)
        if not grids:
            return
        grids[:] = [grid for grid in grids if grid is not self]
        if not grids:
            del _GRIDS[key]

    def PauseBindings(self):
        """
        暂停集合绑定，避免缓存饱和后继续高频回调。

        **不能在绑定回调里调**：写满是在第 0 格的 `.visible` 回调里数出来的，当场解绑等于引擎正在挨个拉绑定时
        改它的绑定表（解掉的还包括正在执行的这一条）。所以那边只排到下一帧，见 __SchedulePause
        """
        with LogPatcher():
            if self.BindingsPaused:
                return
            paused = False
            for binding_name, wrapper in list(self.BindingWrappers.items()):
                config = self.BindingConfigs.get(binding_name)
                if not config:
                    continue
                if not config.get("can_pause", True):
                    continue

                self.Bindings.Unbind(wrapper)
                del self.BindingWrappers[binding_name]
                del self.BindingConfigs[binding_name]
                paused = True

            self.BindingsPaused = paused
            self.PendingPause = False

    def ResumeBindings(self):
        """ 恢复集合绑定，用于翻页/清缓存后的重新拉起。调用方都在绑定回调之外（定时器、按钮、事件） """
        with LogPatcher():
            if not self.BindingsPaused:
                return
            if not self.BindingTemplates:
                return

            for config in self.BindingTemplates:
                if not config.get("can_pause", True):
                    continue
                self._BindOneConfig(config)

            self.BindingsPaused = False
            self.PendingPause = False

    def GetControlByIndex(self, index):  # type: (int) -> any
        path = self.Control.GetPath()
        return self.MainNode.GetUIControl(path + "/{}{}".format(self.ChildName, index+1), use_root_path=False)

    def GetDefaultBindingConfigs(self):
        base_configs = utilities.GetItemPanelBindingConfigs()

        base_configs += [
            {
                "suffix": ".visible",
                "flag": ViewBinder.BF_BindBool,
                "resolver": self.__EnsureItemPanelVisible,
                "default": True,
                "can_pause": True,
            },
            {
                "suffix": ".overlay.btn.click_" + self.CollectionName,
                "flag": ViewBinder.BF_ButtonClickUp,
                "resolver": self.PrimaryClickHandler,
                "default": None,
                "can_pause": False,
            },
            {
                "suffix": ".overlay.btn.right_click_" + self.CollectionName,
                "flag": ViewBinder.BF_ButtonClickUp,
                "resolver": self.SecondaryClickHandler,
                "default": None,
                "can_pause": False,
            }
        ]

        return self.BuildConfigs(base_configs)

    def ParsePath(self, btn_path):  # type: (any) -> int or None
        grid_path = self.Control.GetPath()
        if not btn_path:
            return None
        child_path = btn_path[btn_path.find("/")+len(grid_path)+1:]
        child_name = self.ChildName
        if not child_path.startswith(child_name):
            return None
        index = child_path[len(child_name):child_path.find("/")]
        try:
            index = int(index)
        except ValueError:
            return None

        return index

    def PanelAt(self, x, y):  # type: (float, float) -> any
        """
        这一点落在这个 grid 的哪一格（显示着物品、或是一条收藏的面板），不在这个 grid 上返回 None（UIScriptMain.PanelAt）。
        先看整个 grid 的矩形；再按行列估出那一格先量它，不对再逐格量 —— 都是真实矩形，不按 20 像素一格推
        （行距会被均摊成 20.x，引擎结论 §28；旧的 SlotAtPoint 就坏在这）。这一栏藏着时不算
        """
        if not self.Shown or not self.Cols or not self.Rows:
            return None
        box = control_rect(self.Control)
        if box is None or not contains(box, x, y):
            return None
        col = min(self.Cols - 1, int((x - box[0]) * self.Cols / (box[2] - box[0])))
        row = min(self.Rows - 1, int((y - box[1]) * self.Rows / (box[3] - box[1])))
        guess = self.ItemPanels.get(row * self.Cols + col)
        for panel in ([guess] if guess is not None else []) + [p for p in self.ItemPanels.values() if p is not guess]:
            if getattr(panel, "Item", None) is None and getattr(panel, "Cell", None) is None:
                continue
            rect = control_rect(getattr(panel, "Control", None))
            if rect is not None and contains(rect, x, y):
                return panel
        return None

    def PrimaryClickHandler(self, args):
        path = args.get("ButtonPath")
        index = self.ParsePath(path)
        item_panel_ins = self.ItemPanels.get(index-1)
        if not item_panel_ins:
            return
        item_panel_ins.OnPrimaryClick(None)


    def SecondaryClickHandler(self, args):
        path = args.get("ButtonPath")
        index = self.ParsePath(path)
        item_panel_ins = self.ItemPanels.get(index-1)
        if not item_panel_ins:
            return
        item_panel_ins.OnSecondaryClick(None)

    @classmethod
    def from_collection_name(cls, control, collection_name, child_name="item_panel", item_panel_callback=None):
        """ 通过 CollectionName 初始化一个 ItemsGrid 实例 """
        return cls(control, child_name, collection_name, binding_name_prefix=binding_prefix(collection_name),
                   item_panel_callback=item_panel_callback)

    def __GetAutoCacheLimit(self):
        # type: () -> int or None
        if not self.AutoCacheLimitEnabled:
            return None
        if self.Rows <= 0 or self.Cols <= 0:
            return None
        return self.Rows * self.Cols

    def __RefreshCacheSaturatedState(self):
        limit = self.__GetAutoCacheLimit()
        if limit is None:
            self.CacheSaturated = False
            return
        self.CacheSaturated = len(self.ItemPanels) >= limit

    def __CanCreateItemPanel(self):
        self.__RefreshCacheSaturatedState()
        return not self.CacheSaturated

    def BuildConfigs(self, base_configs):
        configs = []
        for base_config in base_configs:
            config = dict(base_config)
            # .replace("$", self.CollectionName)
            config["name"] = make_binding_name(self.Prefix, base_config["suffix"])
            configs.append(config)
        return configs

    def BindConfigs(self, configs):
        self.BindingTemplates = [dict(config) for config in configs]
        self._ApplyBindings(self.BindingTemplates)
        self.BindingsPaused = False
        self.PendingPause = False
        self.PendingPasses = 0
        self.__Track()

    def _ApplyBindings(self, configs):
        self.UnbindAll()

        with LogPatcher():
            for config in configs:
                self._BindOneConfig(config)

    def _BindOneConfig(self, config):
        config_copy = dict(config)
        binding_name = config_copy["name"]
        if binding_name in self.BindingWrappers:
            return

        callback = self.CreateBindingCallback(config_copy)
        # 集合绑定还是普通绑定由 ScreenBinder 按 flag 分：点击类只能普通绑定（引擎结论 §9）
        wrapper = self.Bindings.Bind(callback, config_copy["flag"], binding_name, self.CollectionName)

        self.BindingWrappers[binding_name] = wrapper
        self.BindingConfigs[binding_name] = config_copy

    def _CreateResolverCallback(self, resolver, name, default):
        fault = self.__Fault

        def _callback(args):
            try:
                return resolver(args)
            except Exception as e:  # noqa
                fault(name, args, e)
                return default
        return _callback

    def _CreateAttrCallback(self, attr_name, default, name):
        fault = self.__Fault

        def _callback(args):
            try:
                panel = self.ItemPanels.get(args)
                if not panel:
                    return default
                # getattr 的默认值只兜 AttributeError，属性里抛别的照样往外冒
                return getattr(panel, attr_name, default)
            except Exception as e:  # noqa
                fault(name, args, e)
                return default
        return _callback

    @staticmethod
    def _CreateDefaultCallback(default):
        def _callback(_):
            return default
        return _callback

    def CreateBindingCallback(self, config):
        """
        绑定回调**一律自己接住异常**：回调抛异常 = 引擎当场扔掉这条绑定、不给日志（CLAUDE.md 引擎结论 §15）——
        扔掉的若是 `.visible`，grid 就停在已经建出来的那几格上，而这边还以为绑着，翻页也回不来。
        接住后记一行（同一条绑定只记第一次）、返回默认值，下一帧照常再拉、再试
        """
        resolver = config.get("resolver")
        name = config.get("name")
        default = config.get("default")
        if resolver:
            return self._CreateResolverCallback(resolver, name, default)

        attr_name = config.get("attr")
        if attr_name:
            return self._CreateAttrCallback(attr_name, default, name)

        return self._CreateDefaultCallback(default)

    def __Fault(self, name, args, error):
        """ 绑定回调抛的异常：同一条绑定只记第一次（每帧都会再拉，每次都记会刷屏） """
        count = self.__Faults.get(name, 0) + 1
        self.__Faults[name] = count
        if count == 1:
            where = "第 {} 格".format(args) if isinstance(args, int) else "点击时"
            logger.error("[MEI/grid] {} 的绑定 {} 在{}抛异常，已接住、返回默认值（只记第一次）: {}: {}".format(
                self.CollectionName, name, where, type(error).__name__, error_text(error)))

    # def ResolveBinding(self, args, binding_name):
    #     config = self.BindingConfigs.get(binding_name)
    #     if not config:
    #         return False
    #
    #     resolver = config.get("resolver")
    #     if resolver:
    #         return resolver(args)
    #
    #     panel = self.ItemPanels.get(args)
    #     if not panel:
    #         return config.get("default")
    #
    #     attr_name = config.get("attr")
    #     if not attr_name:
    #         return config.get("default")
    #
    #     return getattr(panel, attr_name, config.get("default"))
    #

    def ClearItemPanels(self):
        """ 清空所有缓存的ItemPanel, 并恢复创建状态 """
        for _, panel in self.ItemPanels.items():
            panel.Destroy()
        self.ItemPanels = {}
        self.CacheSaturated = False
        self.PendingPause = False
        self.PendingPasses = 0
        self.__StuckSince = None
        self.__Repairs = 0
        self.ResumeBindings()

    def SetGridDimension(self, cols, rows, update_control=True):
        """
        设置Grid的行列数。grid 的尺寸不用另设：跟着行列数走的那一轴在 JSON 里写 default（CLAUDE.md 引擎结论 §28）。

        update_control=True 一律推给引擎；False 只在**这个实例没推过这组行列数**时推 —— JSON 里的 grid_dimensions 是 [1, 1]，
        界面跨开关存活而实例每次开界面新建，所以新实例至少推一次，否则引擎停在 1×1、只显示一个物品（引擎结论 §27-1）
        """
        self.Cols = cols
        self.Rows = rows
        if update_control or (cols, rows) != self.__PushedDims:
            self.__PushDims()
        self.__RefreshCacheSaturatedState()
        if not self.CacheSaturated:
            # 格子变多、没写满了：之前数的轮数作废，重新写满后从头数（不然一写满就停，数量、角标来不及拉）
            self.PendingPause = False
            self.PendingPasses = 0
            self.ResumeBindings()
        else:
            self.__ArmPause()

    def __PushDims(self):
        self.Control.SetGridDimension((self.Cols, self.Rows))
        self.__PushedDims = (self.Cols, self.Rows)
        self.__DimsCheckAt = time.time() + self.DIMS_CHECK_DELAY
        self.__PullsAtPush = self.Pulls
        self.__OpenRepaintWindow()
        self.__Track()

    def __OpenRepaintWindow(self):
        first, last = self.RepaintPasses
        self.__RepaintWindow = (self.Pulls + first, self.Pulls + last)

    def __CheckIcon(self, collection_index):
        """
        .visible 回调里、这一格的面板已经在缓存里：在核对窗口里（推完行列数、格子重新排列之后那几轮）看渲染器上画的是不是这一格的物品，
        不是就重设 —— 设到重建出来的新控件上。只碰这一格自己的物品渲染器，不碰绑定表（引擎结论 §27-2 管的是绑定 / 解绑）
        """
        window = self.__RepaintWindow
        if window is None:
            return
        if self.Pulls > window[1]:
            self.__RepaintWindow = None
            return
        if self.Pulls >= window[0]:
            self.__Repaint(collection_index, self.ItemPanels.get(collection_index), verify=True)

    def __Repaint(self, collection_index, panel, verify=False):
        """ 把这一格的图标重设一次（verify：渲染器上已经是它就不设）。设不上（控件这一刻不在）不改面板原来的显隐；出错只少画一次 """
        if panel is None or getattr(panel, "Stack", None) is None or getattr(panel, "Destroyed", False):
            return
        try:
            if verify and self.__ShowsItem(panel):
                return
            shown = getattr(panel, "ItemRendererVisible", True)
            if not panel.SetUiItem():
                panel.ItemRendererVisible = shown
        except Exception as e:  # noqa  不能带走这一格的 .visible（引擎结论 §15），也不能打乱数轮
            self.__Fault("repaint", collection_index, e)

    @staticmethod
    def __ShowsItem(panel):  # type: (any) -> bool
        """ 渲染器上现在画的就是这一格的物品（ItemRenderer 的 GetUiItem，SDK 2.11 起有）；问不到就当不是 —— 照样重设 """
        getter = getattr(getattr(panel, "RendererControl", None), "GetUiItem", None)
        info = getter() if getter is not None else None
        if not isinstance(info, dict):
            return False
        item_id, aux_value = panel.Stack.get_render_data()[:2]
        return info.get("itemName") == item_id and info.get("auxValue") == aux_value

    def OnRearranged(self):
        """
        引擎说这个 grid 的格子重新排列了（GridComponentSizeChangedClientEvent，grid_rearranged 转来）：格子是新建的 ——
        缓存里的面板当场把图标重设一遍（新格子上没有图标，引擎结论 §46；网易自己的宠物背包界面收到这个事件也是把格子里的东西重设一遍），
        再开一个核对窗口（这一刻渲染器可能还没就绪）。绑定暂停着、或者快要暂停的，排到下一帧恢复、从头数轮数 —— 新格子的可见、数量
        这些也要拉到值；这里可能还在引擎更新界面的过程中，不当场改绑定表
        """
        for index, panel in list(self.ItemPanels.items()):
            self.__Repaint(index, panel)
        self.__OpenRepaintWindow()
        if self.BindingsPaused or self.PendingPause:
            self.__ScheduleWake()

    def __ScheduleWake(self):
        if self.__WakeScheduled:
            return
        self.__WakeScheduled = True
        if self.__Game is None:
            self.__Game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        self.__Game.AddTimer(0.0, self.__WakeAfterRearrange)

    def __WakeAfterRearrange(self):
        """ 定时器里：暂停了的绑定恢复（关界面解过绑的不恢复），从头数轮数，写满了再等几轮才停 """
        self.__WakeScheduled = False
        self.ResumeBindings()
        self.PendingPause = False
        self.PendingPasses = 0
        self.__RefreshCacheSaturatedState()
        if self.CacheSaturated:
            self.__ArmPause()

    def Revive(self):
        """
        这个 grid 所在的那一栏刚从藏着变成显示（从悬浮窗点开、从收着展开）：藏着时推下去的行列数、建的格子引擎多半没接住 ——
        当场重推行列数、清掉面板缓存（绑定重新拉一遍，暂停了的恢复），不等自检。调用方在绑定回调之外
        """
        self.__FastRepushes = 0
        if self.Cols and self.Rows:
            self.__PushDims()
        self.ClearItemPanels()

    def Wake(self):
        """
        面板没换、只是某个绑定的值变了（收藏栏的同配方高亮）：暂停了的绑定恢复，拉够 PAUSE_AFTER_PASSES 轮再停 ——
        光 ResumeBindings 不会再停（面板都在缓存里，没有谁再去武装暂停）。不清面板、不重推行列数。调用方在绑定回调之外
        """
        self.ResumeBindings()
        self.__RefreshCacheSaturatedState()
        if self.CacheSaturated:
            self.__ArmPause()

    def __CheckPushedDims(self, now):  # type: (float) -> None
        """
        刚推完行列数（DIMS_CHECK_DELAY 之后）：引擎的 grid 没有最后一格就当场重推，最多 DIMS_FAST_REPUSH 次；不记日志。
        那一栏藏着、格子还没被拉够 DIMS_CHECK_PASSES 轮时先不问（GetGridItem 问不到会 print error），到期了也等着
        """
        due = self.__DimsCheckAt
        if due is None or now < due:
            return
        if not self.Shown or self.Pulls - self.__PullsAtPush < self.DIMS_CHECK_PASSES:
            return
        self.__DimsCheckAt = None
        if not self.Cols or not self.Rows:
            return
        if self.Control.GetGridItem(self.Cols - 1, self.Rows - 1) is not None:
            self.__FastRepushes = 0
            return
        if self.__FastRepushes >= self.DIMS_FAST_REPUSH:
            return
        self.__FastRepushes += 1
        self.__PushDims()

    def __CreateItemPanel(self, collection_index):
        """ 创建指定index的ItemPanel对象 """
        panel = self.ItemPanelCallback(collection_index)
        if panel:
            return panel
        else:
            raise ValueError("ItemPanelCallback must return an ItemPanel instance")

    def __EnsureItemPanelVisible(self, collection_index):
        """ 懒加载ItemPanel；缓存达到上限后不再创建，绑定可见性仍返回True """
        if collection_index == 0:
            self.Pulls += 1
        if collection_index in self.ItemPanels:
            self.__CheckIcon(collection_index)
            self.__CountPassAndMaybePause(collection_index)
            return True

        if not self.__CanCreateItemPanel():
            self.__ArmPause()
            self.__CountPassAndMaybePause(collection_index)
            return True

        panel = self.__CreateItemPanel(collection_index)
        if panel:
            self.ItemPanels[collection_index] = panel
            self.__RefreshCacheSaturatedState()
            # 达到容量上限后仅标记，等几轮完整拉取再暂停，见 PAUSE_AFTER_PASSES
            if self.CacheSaturated:
                self.__ArmPause()
        return True

    def __ArmPause(self):
        """ 进入「待暂停」并从头数轮数；已经在等的不重数 """
        if self.BindingPausedWhenSaturated and not self.PendingPause:
            self.PendingPause = True
            self.PendingPasses = 0

    def __CountPassAndMaybePause(self, collection_index):
        if not self.BindingPausedWhenSaturated or not self.PendingPause or self.BindingsPaused:
            return
        if collection_index == 0:
            self.PendingPasses += 1
        if self.PendingPasses >= self.PAUSE_AFTER_PASSES:
            self.__SchedulePause()

    def __SchedulePause(self):
        """ 这里在绑定回调里（第 0 格的 .visible）：不当场解绑，排到下一帧（见 PauseBindings） """
        if self.__PauseScheduled:
            return
        self.__PauseScheduled = True
        if self.__Game is None:
            self.__Game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        self.__Game.AddTimer(0.0, self.__FlushPause)

    def __FlushPause(self):
        """ 下一帧（定时器里，不在绑定回调里）：期间清过缓存、解过绑的话条件就不成立了，什么都不做 """
        self.__PauseScheduled = False
        if self.PendingPause and self.CacheSaturated and self.PendingPasses >= self.PAUSE_AFTER_PASSES:
            self.PauseBindings()

    def SelfCheck(self, now):  # type: (float) -> str or None
        """
        自检，脚本的定时器调（不在绑定回调里）。面板没建全、又停住超过 STUCK_SECONDS 就修，返回一句话给日志；没事返回 None。

        两种坏法，修法不同：
          · 引擎的 grid 没有最后一格 —— 行列数没推上去或丢了（JSON 里是 [1, 1]，只显示一个物品）⇒ 重推行列数；
          · 格子都在，第 0 格的 .visible 却没被拉 —— 绑定在引擎那边没了，这边还以为绑着 ⇒ 整套重绑。
        暂停了（写满过）或面板已经建全的 grid 不查，一个引擎调用都不花。
        行列数刚推下去的先快速核对一次（__CheckPushedDims），不等卡满 STUCK_SECONDS
        """
        self.__CheckPushedDims(now)
        limit = (self.Rows or 0) * (self.Cols or 0)
        if not self.Shown or self.BindingsPaused or limit <= 0 or len(self.ItemPanels) >= limit:
            # 藏着的栏引擎不建格子，不算卡住（显出来时脚本 SetShown → Revive 当场补推）
            self.__StuckSince = None
            self.__Repairs = 0
            return None
        if not self.BindingWrappers:
            return None
        if self.__StuckSince is None:
            self.__StuckSince, self.__StuckPulls = now, self.Pulls
            return None
        waited = now - self.__StuckSince
        if waited < self.STUCK_SECONDS or self.__Repairs >= self.MAX_REPAIRS:
            return None
        pulls = self.Pulls - self.__StuckPulls
        self.__StuckSince, self.__StuckPulls = now, self.Pulls
        self.__Repairs += 1
        shape = "{}x{}，面板 {}/{}，{:.1f} 秒拉了 {} 轮".format(
            self.Cols, self.Rows, len(self.ItemPanels), limit, waited, pulls)
        if self.Control.GetGridItem(self.Cols - 1, self.Rows - 1) is None:
            self.__PushDims()
            return "引擎的 grid 没有最后一格（{}），行列数没推上去或丢了，重推".format(shape)
        if not pulls:
            self.BindConfigs(self.BindingTemplates)
            return "格子都在、绑定却没被拉（{}），引擎那边的绑定没了，整套重绑".format(shape)
        return "格子都在、也在拉，面板却没建全（{}），看前面有没有这个 grid 的异常".format(shape)
