# coding=utf-8

# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
"""
MEI Tooltip 的管理器：一个界面一份，挂在主节点上（UIMainNode.OnCreate 建、OnDestroy 拆），见 docs/architecture/tooltip.md。

两个宿主：PC 是跟着光标走的 follows_cursor 包装，偏移与贴边翻转改它里面的 frame
（直接改跟随控件的偏移会被 follows_cursor 盖掉）；移动端是摆在点开的格子旁、不动的 panel，里面竖排
「内容 + 动作按钮行」。开界面时按输入方式选一个。

**跟随的宿主一律不碰**：给它 SetPosition 会让 follows_cursor 停掉（挪过一次就再也不跟光标，引擎结论 §29）。
tooltip 的位置全靠 frame 的偏移，按宿主**实际**在哪算：宿主跟上了光标，偏移就是贴边翻转那一段；宿主根本不跟，偏移把差补上。
**PC 上宿主一直亮着，藏 tooltip 只藏 frame**：藏着的宿主不跟光标，显出来那一刻还停在旧位置，偏移补了差，下一帧宿主跳到光标处、
补的差又叠上去，tooltip 就闪到别处（表现是切换配方时屏幕右下角闪一下）。宿主只是光标下 1 像素的空 input_panel，
不吃悬停、层级垫底，原版跟着光标的物品图标（common.inventory_selected_icon_button）也是这样常驻的。
离光标多远、默认在哪边，读 JSON 里 cursor_gap 这个记号的 offset（脚本只读不改），见 layout.place。

内容控件（接受物品 / 某个类型的配方预览）一次只建一个控件，同一时刻只有一个：
  · 收起时不删：拆掉 Python 这边的绑定，藏 frame（移动端藏宿主），控件藏着；
  · 下次还是同一种（接受物品，或同一个类型的配方预览）就直接复用 —— 一个控件都不建；
  · 换了一种才先删旧的、再建新的，卡顿集中在显示新的那一下，连续浏览时离开不卡；
  · 关界面时删掉（界面状态跨开关存活，§22）。
先建好再给看：新建的内容控件生下来全透明（tooltip_background 的 alpha 0 + propagate_alpha，子控件跟着透明），复用的先把透明度写回 0；
照常建，等内容齐了、尺寸稳定了，摆到位、alpha 拉回 1。

驱动：界面代理的 OnTick（每秒 30 次）调 Update，不用定时器 —— SDK 的定时器最短 0.05 秒，AddTimer(0.0) 也要等 50 毫秒。
PC 的悬停：格子 hover 控件上的绑定（always_when_visible）在悬停的那一格上每帧报一次（Probe），Update 里按光标核对、显示；
显示期间光标离开那一格就收起。
触屏上手指划过格子同样会亮 hover（HUD、MEI 自己的界面上都会，引擎结论 §37）：照桌面的做法收探针，但**只认「移进」** ——
上一帧没报、这一帧报上来的那一格当场交给触屏菜单（TouchMenu.Hover，同一帧打开），不检测移出、不随手指离开收起；
触屏上格子一律不出原版悬停文字（HidesVanillaName：菜单标题就是完整的悬停文字），白色高亮照常亮

设置「启用高级Tooltip」（通用 → 信息显示，默认开）开界面时读一次（Enabled）：关着时什么都不出（悬停、调试键 T），
格子照常出原版悬停文字（ReplacesVanillaName 为假），PC 宿主也藏着 —— 这几样每次开界面两个方向都写，
关了再开、开了再关都回得来（界面状态跨开关存活，§22）。设置页和容器界面不会同时开着，所以不用订阅改动。

移动端宿主就是触屏的二级菜单（mei_ui/menu，tooltip.md §6）：内容由这里建，框里别的东西由菜单填。设置关着时菜单照出（触屏上它是唯一的
操作入口），内容只给「只有标题」的那种（ShowTitleFor 不受设置管）。菜单是**一个框**（tooltip.md §6.12）：
框（touch/frame）画 purpleBorder，内容控件在触屏上换成透明图、不画自己的底；框里每样东西摆在哪由菜单按内容尺寸算（SetTouchLayout），
这里只把框摆到屏幕上。框整体透明着建、和内容一起拉回不透明。
显示出来以后那一格换了内容（翻页、重排，panel.ContentKey 变了）或被拆了就收起 —— 翻页这类不用一个个去接
"""
import re

import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import TooltipText
from MEIScripts.constants.ui import ModeConst, TooltipKind, TooltipPath
from MEIScripts.mei_mod.state.settings import IsAdvancedTooltipEnabled, IsTouchOppositeSide
from MEIScripts.mei_mod.ui_script.controls.item.panel import panel_controls
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_HUD
from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import DescribeItem
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.items import TooltipItemsView
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.layout import (
    GAP, contains, cursor_gap, place, place_beside, place_opposite, place_outside,
)
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.recipe import TooltipRecipeView
from MEIScripts.mei_mod.ui_script.proxy.focus.search import HOVER_TEXT, nearby
from MEIScripts.registry import RecipeManager
from MEIScripts.utils import utilities
from MEIScripts.utils.text import error_text, native_str, to_unicode

HOST_DESKTOP = "desktop"
""" PC：跟着光标走 """
HOST_TOUCH = "touch"
""" 移动端：摆在点开的格子旁，不动 """
HOST_SLOTS = {HOST_DESKTOP: TooltipPath.DesktopFrame, HOST_TOUCH: TooltipPath.TouchContent}
""" 内容控件建在哪 """

PHASE_BUILDING = "building"
""" 内容已建（或复用）、还是全透明的，等它建齐 """
PHASE_SHOWN = "shown"
""" 摆到位了 """


def items_title(total, shown):  # type: (int, int) -> str
    if shown < total:
        return TooltipText.AcceptsCut.format(total, shown)
    return TooltipText.Accepts.format(total)


def with_lore(text, line):  # type: (any, any) -> str
    """ 照格子悬停文字的写法再加一行说明：已经有说明（空一行之后那一段）就接在后面，没有就空一行再写 """
    text, line = native_str(text or ""), native_str(line)
    if not text:
        return line
    return text + ("\n" if "\n\n" in text else "\n\n") + line


def candidate_title(panel):  # type: (any) -> any
    """
    多候选格：标题是它当前轮播到的那个候选，写这一格**完整的悬停文字** —— 物品自带的那几行（附魔、属性…）
    加格子追加的说明（SetLore，比如工具要求）。PC 上这一格的原版悬停文字让位给了这个 tooltip，只写名字就把这些丢了
    （触屏上同样不能只出物品名）。格子还没算过悬停文字才退回物品名。轮播换候选时面板先重算悬停文字、再通知，所以跟得上。
    下面再加一行灰色的「接受以下物品: 」，引出下面那张列表
    """
    text = getattr(panel, "ItemHoverText", None)
    if not text:
        current = panel.Current
        item = getattr(current, "Item", None) if current is not None else None
        text = to_unicode(DescribeItem(item)) if item is not None else u""
    return with_lore(text, TooltipText.AcceptsLore)


def content_name(control_def):  # type: (str) -> str
    """ 内容控件的名字带上定义名：换一种时新旧不同名，删旧的、建新的在同一帧也撞不上（SDK 遇到同名会直接返回旧的那个） """
    return TooltipPath.ContentName + "_" + re.sub(r"\W", "_", control_def)


def content_key(panel):  # type: (any) -> any
    """ 这一格现在显示的是什么（panel.ContentKey，没有就是它的物品）：显示出来以后变了就收起 """
    key_of = getattr(panel, "ContentKey", None)
    return key_of() if callable(key_of) else getattr(panel, "Item", None)


def mouse_pos():  # type: () -> tuple or None
    """ 光标位置（与 GetGlobalPosition 同一套坐标）；触屏上引擎给 None，取不到一律 None """
    try:
        return utilities.GetMousePosInt()
    except Exception:  # noqa
        return None


def is_touch():  # type: () -> bool
    try:
        return utilities.GetInputMode() == 1
    except Exception:  # noqa
        return False


def previewable_recipe(item, query_by=QueryConst.Output):  # type: (any, str) -> any
    """ 这个物品第一条能预览的配方（类型有预览、注册了配方页脚本）；没有返回 None """
    try:
        result = RecipeManager.QueryRecipe(item, query_by)
    except Exception as e:  # noqa
        logger.error("[MEI/tooltip] 查 {} 的配方失败: {}".format(native_str(getattr(item, "ItemId", "")), error_text(e)))
        return None
    for recipes in result.values():
        for recipe in recipes or ():
            if TooltipRecipeView.CanPreview(recipe):
                return recipe
    return None


class TooltipManager(object):

    BUILD_MAX_TICKS = 15
    """ 构建最多等这么多帧（约 0.5 秒）：还没建齐也照常显示，不能一直不出 """

    def __init__(self, main_node):
        self.MainNode = main_node
        self.GameComp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        self.Items = TooltipItemsView(main_node)
        self.Recipe = TooltipRecipeView(main_node)
        self.Host = HOST_DESKTOP  # type: str  # 开界面时按输入方式定
        self.Enabled = True  # type: bool  # 设置「启用高级Tooltip」：开界面时读，关着时什么都不出
        self.ReplacesVanillaName = True  # type: bool  # 会出 MEI tooltip 的格子不出原版物品名（只在 PC 上、设置开着时）
        self.OppositeSide = False  # type: bool  # 设置「触控tooltip是否沿对面侧显示」：触屏菜单摆到点的那一格另一侧的屏幕边上。开界面时读
        self.Current = None  # type: str or None  # 亮着（或正在建）的是哪一种：TooltipKind.Items / Recipe；藏着时 None
        self.Phase = None  # type: str or None  # PHASE_BUILDING / PHASE_SHOWN
        self.Content = None  # type: str or None  # 内容控件的路径（显示中或藏着）
        self.ContentDef = None  # type: str or None  # 它的定义名：下次同一种就复用
        self.Owner = None  # type: any  # 悬停出的 tooltip 归哪一格；调试键 T 出的是 None，不随光标收起
        self.OwnerRect = None  # type: tuple or None
        self.OwnerKey = None  # type: any  # 显示时那一格的 content_key：变了（翻页、重排）就收起
        self.AnchorRect = None  # type: tuple or None  # 移动端摆在哪一格旁边
        self.TouchRegion = None  # type: tuple or None  # 触屏菜单：(格子所在区域的矩形, 首选的一侧)，摆在区域外侧；没有就摆在格子旁
        self.TouchLayout = None  # type: callable or None  # 触屏菜单：fn(内容尺寸) -> 框的尺寸，顺带把框里的东西摆好（TouchMenu.Layout）
        self.Placed = None  # type: tuple or None  # 触屏菜单上次按多大的内容摆的，变了就重摆
        self.Candidates = None  # type: any  # 正在显示的多候选面板（监听它换候选）
        self.Help = None  # type: any  # 正在显示的快捷键帮助的字（按住 Alt）；别的内容顶掉它、收起时清掉
        self.BuildTicks = 0  # type: int
        self.LastTipSize = None  # type: tuple or None  # 构建中上一帧量到的内容尺寸：两帧一样才算排好
        self.Offset = None  # type: tuple or None  # frame 相对宿主的偏移（上次推下去的）
        self.Bounds = None  # type: tuple or None  # tooltip 根（整块 MEI 覆盖层）的全局矩形，每次显示量一次
        self.Gap = (GAP, GAP)  # type: tuple  # 离光标多远、默认在哪边：JSON 里 cursor_gap 的 offset，每次显示读一次
        self.__Hovered = {}  # type: dict  # id(面板) -> 面板：这一帧悬停探针报上来的
        self.__TouchHovered = {}  # type: dict  # 触屏：上一帧报上来的（认「移进」用：这一帧有、上一帧没有的那一格）
        self.__Rejected = None  # type: any  # 上次没建成的那一格：光标离开前不再试
        self.__HelpWoke = False  # type: bool  # 快捷键帮助亮着时唤醒过 MEI 的 grid（悬停文字的绑定要再拉一遍才让位）
        self.__HelpQuiet = None  # type: str or None  # 帮助亮着时要藏的原版悬停文字控件：光标下是原版 / 别的模组的格子时才有
        self.__Quieted = None  # type: str or None  # 现在藏着的那一个（显回时用）
        self.__HoverTextOf = {}  # type: dict  # 物品渲染器的路径 -> 它那一格的悬停文字控件（找不到是 None）；开关界面时清

    def OnCreate(self):
        """
        开界面：读设置、按输入方式选宿主；MEI 根控件跨开关存活（引擎结论 §22），宿主显隐两个方向都显式写（开着设置时 PC 宿主
        从这一刻起一直亮着、跟着光标；关着时根与宿主都藏），上次关界面时亮着的 tooltip 藏掉。
        原版名让不让位也每次重算：设置关着时会出 MEI tooltip 的格子照常出原版名（格子的悬停文字绑定在这之后才拉）
        """
        self.Enabled = IsAdvancedTooltipEnabled()
        self.OppositeSide = IsTouchOppositeSide()
        # HUD 上一律用触屏宿主：游戏界面没有光标，PC 那个 follows_cursor 的宿主只在 PushScreen 建的界面里管用（官方文档），
        # 一直亮着的 input_panel 也不该挂在游戏界面上（floating.md §6）
        on_hud = getattr(self.MainNode, "Kind", None) == KIND_HUD
        self.Host = HOST_TOUCH if is_touch() or on_hud else HOST_DESKTOP
        self.ReplacesVanillaName = self.Enabled and self.Host == HOST_DESKTOP
        self.__TouchHovered = {}
        self.__HoverTextOf = {}
        self.__HelpWoke = False
        self.__HelpQuiet = None
        self.Hide(force=True)

    def OnDestroy(self):
        self.__Hovered = {}
        self.__TouchHovered = {}
        self.__Rejected = None
        self.Hide(force=True)
        # 藏过的原版悬停文字关界面前显回：界面状态跨开关存活（引擎结论 §22）。grid 正在解绑，不唤醒
        self.__HelpWoke = False
        self.__HelpQuiet = None
        self.__SyncHelp()
        self.__HoverTextOf = {}

    def HidesVanillaName(self, panel):  # type: (any) -> bool
        """
        这一格悬停时不出原版悬停文字（ItemPanel.MeiTooltipHidesName 问这里，悬停文字的绑定每帧都问 —— 只做便宜的判断）：
        触屏上一律不出（划过就开菜单，菜单标题就是完整的悬停文字）；PC 上设置开着、会出 MEI tooltip 的格子不出；
        按住 Alt 的快捷键帮助亮着时一律不出（不然两段字叠在光标右边）
        """
        if self.Host == HOST_TOUCH or self.Help is not None:
            return True
        return self.ReplacesVanillaName and panel.HasMeiTooltip()

    def IsVisible(self):  # type: () -> bool
        """ 亮着或正在建（藏着的内容控件不算） """
        return self.Current is not None

    def IsInside(self, panel):  # type: (any) -> bool
        """
        这一格是不是长在亮着的内容控件里（接受物品列表、配方预览的格子）。触屏菜单据此不给它们开新菜单 ——
        开新菜单会先收起现在的内容，连带把被点的这一格拆掉，新菜单下一帧就跟着收了
        """
        control = getattr(panel, "Control", None)
        if self.Current is None or self.Content is None or control is None:
            return False
        tip = self.MainNode.GetUIControl(self.Content)
        try:
            return bool(tip) and control.GetPath().startswith(tip.GetPath() + "/")
        except Exception:  # noqa  格子刚被拆、控件已经不在
            return False

    # 显示
# ======================================================================================================================
    def ShowItems(self, stacks, title=None):  # type: (list, any) -> bool
        """ 接受物品：一格一个候选。没有可显示的、设置里关了高级 Tooltip 都返回 False """
        if not self.Enabled:
            return False
        stacks = [stack for stack in (stacks or ()) if stack is not None and not stack.is_empty()]
        if not stacks:
            return False
        self.Hide()
        path = self.__Mount(TooltipKind.Defs[TooltipKind.Items])
        if path is None:
            return False
        total, shown = self.Items.Show(stacks, path + TooltipPath.ItemsGridSub)
        if not shown:
            self.Hide()
            return False
        self.__SetTitle(title or items_title(total, shown))
        self.__Build(TooltipKind.Items)
        return True

    def ShowCandidates(self, panel):  # type: (any) -> bool
        """ 多候选格的接受物品：标题是它当前的候选，轮播换了标题跟着换 """
        if not self.ShowItems(panel.Candidates, title=candidate_title(panel)):
            return False
        self.Candidates = panel
        panel.AddListener(self.OnCandidateChanged)
        return True

    def OnCandidateChanged(self, panel):
        if panel is self.Candidates and self.Content is not None:
            self.__SetTitle(candidate_title(panel))

    def ShowRecipe(self, recipe, title=None):  # type: (any, any) -> bool
        """ 配方预览：建（或复用）该类型的 PREVIEW —— 整个 tooltip 只这一个控件。类型没有预览、设置里关了高级 Tooltip 都返回 False """
        if recipe is None or not self.Enabled:
            return False
        self.Hide()
        if not TooltipRecipeView.CanPreview(recipe):
            return False
        control_def = RecipeManager.GetPreviewDef(recipe.Type)
        path = self.__Mount(control_def)
        if path is None:
            TooltipRecipeView.BROKEN.add(control_def)
            logger.warn("[MEI/tooltip] 类型 {} 的预览 {} 建不出来：JSON 里没照规范写 PREVIEW 那一行？"
                        "不想要预览就在 RecipeCategory 上写 preview_def=None（这一局不再试）".format(
                            native_str(recipe.Type), native_str(control_def)))
            return False
        if not self.Recipe.Show(recipe, path):
            self.Hide()
            return False
        self.__SetTitle(title or self.RecipeTitle(recipe))
        self.__Build(TooltipKind.Recipe)
        return True

    def ShowFor(self, panel, rect=None, own=True):  # type: (any, tuple or None, bool) -> bool
        """
        按格子给的内容显示（panel.TooltipContent）。own 为真时记下归属：光标离开这一格就收起（悬停出的）；
        调试键 T 出的不记，等再按一下 T
        """
        if not self.Enabled:
            return False
        content = panel.TooltipContent() if panel is not None else None
        if content is None:
            return False
        kind, data = content
        cell_rect = rect if rect is not None else self.__RectOf(panel)
        if kind == TooltipKind.Items:
            shown = self.ShowCandidates(data)
        elif kind == TooltipKind.Recipe:
            shown = self.ShowRecipe(data() if callable(data) else data)
        else:
            shown = False
        if not shown:
            return False
        self.__Own(panel, cell_rect, own)
        return True

    def ShowTitle(self, text):  # type: (any) -> bool
        """
        只有标题一行：触屏菜单给普通格子（没有 TooltipContent）、设置里关了高级 Tooltip 时用。不受设置管 ——
        菜单是触屏上唯一的操作入口（设置关着时菜单照出，只是不出预览）
        """
        self.Hide()
        path = self.__Mount(TooltipKind.Defs[TooltipKind.Title])
        if path is None:
            return False
        self.__SetTitle(text)
        self.__Build(TooltipKind.Title)
        return True

    def ShowTitleFor(self, panel, text, rect=None):  # type: (any, any, tuple or None) -> bool
        """ 按格子显示只有标题的那种，并记下归属（那一格被拆了、换了内容就收起）—— 触屏菜单用 """
        cell_rect = rect if rect is not None else self.__RectOf(panel)
        if not self.ShowTitle(text):
            return False
        self.__Own(panel, cell_rect, True)
        return True

    def ShowHelp(self, text, target=None):  # type: (any, any) -> bool
        """
        快捷键帮助（按住 Alt，hotkeys/hover.py）：只有标题那一种，不归哪一格（光标挪开不收，松开 Alt 才收）；同样的字不重建。
        只在 PC 上、设置开着时出（关着时 PC 宿主是藏着的）。
        亮着时光标下那一格的原版悬停文字让位（__SyncHelp）：target 是光标下的 FocusTarget，原版 / 别的模组的格子按它找悬停文字控件
        """
        if not self.Enabled or self.Host != HOST_DESKTOP:
            return False
        self.__HelpQuiet = self.__VanillaHoverText(target)
        if self.Help == text and self.Current is not None:
            return True
        if not self.ShowTitle(text):
            return False
        self.Help = text
        return True

    def HideHelp(self):
        """ 松开 Alt：帮助还亮着就收起（别的内容顶掉它的时候 Help 已经清了）"""
        if self.Help is not None:
            self.Hide()

    def SetTouchRegion(self, region, side):  # type: (tuple or None, str) -> None
        """ 触屏菜单：摆在这个区域（物品栏、收藏栏、配方页）外侧，首选 side 那一边；region 为 None 就摆在格子旁 """
        self.TouchRegion = (region, side) if region is not None else None

    def SetTouchLayout(self, layout):  # type: (callable or None) -> None
        """
        触屏菜单：fn(内容尺寸) -> 框的尺寸，顺带把框里的东西（顶栏、内容、分隔线、按钮区）摆好。摆框时调（显示那一刻、内容尺寸变了、挂到新格子上）。
        框多大用菜单算好的、不去量 —— 脚本改过尺寸的控件，外面的 stack_panel 不一定跟着重排（表现是贴边时按钮区没算进去）
        """
        self.TouchLayout = layout

    def Release(self):
        """
        放掉归属，内容照样亮着、不随旧格子收起：触屏菜单要改收藏（−1 / +1、上移下移）时先放，收藏栏一重排格子全是新的，
        改完用 Adopt 挂到显示同一条收藏的新格子上
        """
        self.Owner = None
        self.OwnerRect = None
        self.OwnerKey = None

    def Adopt(self, panel):  # type: (any) -> bool
        """ 挂到新格子上：记下归属；已经摆出来的按新格子重新摆（触屏）。格子量不到、没在显示返回 False """
        rect = self.__RectOf(panel)
        if rect is None or self.Current is None:
            return False
        self.__Own(panel, rect, True)
        if self.Phase == PHASE_SHOWN and self.Host == HOST_TOUCH:
            tip = self.MainNode.GetUIControl(self.Content) if self.Content is not None else None
            if tip is not None:
                self.__PlaceTouch(tip.GetSize())
        return True

    def CandidateIndexOf(self, panel):  # type: (any) -> int or None
        """ 接受物品列表里的这一格是第几个候选（「+N」那格、别的格子给 None）—— 触屏菜单里点它就选中这个候选 """
        if self.Current != TooltipKind.Items or self.Candidates is None:
            return None
        return self.Items.IndexOf(panel)

    def __Own(self, panel, rect, own):
        """ 显示前的 Hide 清掉了这些；摆出来要等建好（Update），那时用得到 """
        self.AnchorRect = rect
        if own:
            self.Owner = panel
            self.OwnerRect = rect
            self.OwnerKey = content_key(panel)

    def Hide(self, force=False):
        """
        收起：拆掉 Python 这边的绑定，藏 frame（PC）或移动端宿主（界面状态跨开关存活，§22）；内容控件**不删**，藏着等下次复用或替换。
        force（开关界面时）才连控件一起删
        """
        candidates, self.Candidates = self.Candidates, None
        if candidates is not None:
            candidates.RemoveListener(self.OnCandidateChanged)
        self.Items.Hide()
        self.Recipe.Hide()
        if force:
            self.__Discard()
        if force or self.Current is not None:
            self.__ApplyHosts(False)
        self.Current = None
        self.Phase = None
        self.Help = None
        self.Owner = None
        self.OwnerRect = None
        self.OwnerKey = None
        self.AnchorRect = None
        self.TouchRegion = None
        self.TouchLayout = None
        self.Placed = None
        self.BuildTicks = 0
        self.LastTipSize = None
        self.Offset = None
        self.Bounds = None

    # 每帧（界面代理的 OnTick）
# ======================================================================================================================
    def Update(self):
        """
        每帧一次：核对悬停、推进构建、跟着光标摆位置。出错只记日志 —— 这里抛出去会带走同一帧别的代理。
        设置关着时 PC 上什么都不做；触屏上照常（菜单的「只有标题」那种还要建、要摆）
        """
        hovered, self.__Hovered = self.__Hovered, {}
        self.__SyncHelp()
        if not self.Enabled and self.Host == HOST_DESKTOP:
            return
        try:
            if self.Phase is not None:
                self.__Tick()
            if self.Host == HOST_TOUCH:
                self.__CheckTouchHover(hovered)
            elif hovered or self.__Rejected is not None:
                self.__CheckHovered(list(hovered.values()))
        except Exception as e:  # noqa
            logger.error("[MEI/tooltip] 每帧处理失败: {}".format(error_text(e)))

    def __SyncHelp(self):
        """
        快捷键帮助亮没亮，原版悬停文字跟着让位 / 显回（每帧对一次，帮助换了内容、被别的内容顶掉、松开 Alt 都在这里收拾）：
        · MEI 的格子：悬停文字的绑定问 HidesVanillaName，帮助亮着时给空 —— 写满后暂停了的 grid 要唤醒才会再拉，亮 / 灭时各唤醒一次；
        · 原版 / 别的模组的格子：它的悬停文字由引擎的绑定给字，只能把那一格的 hover_text 控件藏起来，帮助收起、光标换了格子时显回
        """
        try:
            on = self.Help is not None
            if on != self.__HelpWoke:
                self.__HelpWoke = on
                self.__WakeGrids()
            want = self.__HelpQuiet if on else None
            if want != self.__Quieted:
                self.__ShowHoverText(self.__Quieted, True)
                self.__Quieted = want if self.__ShowHoverText(want, False) else None
        except Exception as e:  # noqa
            logger.error("[MEI/tooltip] 快捷键帮助让位失败: {}".format(error_text(e)))

    def __WakeGrids(self):
        """ 物品栏、收藏栏、最近浏览的 grid 唤醒一下：暂停了的悬停文字绑定再拉几轮（ItemsGrid.Wake）"""
        main = self.MainNode
        for name in ("ItemsBrowserIns", "ItemsSidebarIns"):
            script = getattr(main, name, None)
            grids = getattr(script, "GetItemGrids", None) if script is not None else None
            if not callable(grids):
                continue
            for grid in grids() or ():
                grid.Wake()

    def __VanillaHoverText(self, target):  # type: (any) -> str or None
        """ 光标下是原版 / 别的模组的格子：它的悬停文字控件（焦点探针的 nearby 找，按渲染器的路径记下）；MEI 自己的格子、找不到给 None """
        if target is None or getattr(target, "Panel", None) is not None:
            return None
        path = getattr(getattr(target, "Hit", None), "Path", None)
        if not path:
            return None
        if path not in self.__HoverTextOf:
            self.__HoverTextOf[path] = nearby(self.MainNode.ScreenNode, path, HOVER_TEXT)
        return self.__HoverTextOf[path]

    def __ShowHoverText(self, path, visible):  # type: (str or None, bool) -> bool
        """ 按路径显 / 藏一个原版悬停文字控件；没有路径、控件不在了返回 False """
        if not path:
            return False
        control = self.MainNode.ScreenNode.GetBaseUIControl(path)
        if control is None:
            return False
        control.SetVisible(visible)
        return True

    def Probe(self, panel):
        """
        悬停探针（格子 hover 控件上的绑定，always_when_visible）报上来的格子：悬停期间每帧报一次。
        是在绑定回调里调的 —— 只记下，Update 里再核对、显示（绑定回调里不建控件、不绑定，引擎结论 §27-2）。
        PC 上设置关着时不收；触屏上照收（划过格子开菜单，菜单不受设置管）
        """
        if panel is None or (self.Host == HOST_DESKTOP and not self.Enabled):
            return
        self.__Hovered[id(panel)] = panel

    def __CheckTouchHover(self, hovered):  # type: (dict) -> None
        """
        触屏：手指划进哪一格就给它开菜单，不等点（学桌面的悬停，但只检测移入 —— 不像鼠标悬停要自动关）。
        「移进」= 这一帧报上来、上一帧没报的那一格；一帧冒出好几格新的（hover 状态在很多格子上亮着）不认。
        菜单内容里的格子（接受物品列表、配方预览）不开新菜单 —— 那会先收起现在的内容，连带把这一格拆掉
        """
        previous, self.__TouchHovered = self.__TouchHovered, hovered
        entered = [panel for key, panel in hovered.items() if key not in previous]
        if len(entered) != 1:
            return
        panel = entered[0]
        if getattr(panel, "Destroyed", False) or self.IsInside(panel):
            return
        # 工具 / 作弊模式下点一格是拿起、给物品（ModeManager.Intercept），划进去不开菜单
        if ModeManager.Current() != ModeConst.Normal:
            return
        menu = getattr(self.MainNode, "Menu", None)
        if menu is not None:
            menu.Hover(panel)

    def __CheckHovered(self, panels):
        """
        光标真停在哪一格上。悬停期间每帧都报，错过一帧下一帧还会再来（只在可见性变化时报一次的话，
        没赶上就要动一下鼠标才出）。只信光标落在矩形里、又出 MEI tooltip 的那一格；
        调试键 T 钉住的不被悬停换掉；上次没建成的那一格等光标离开再试，免得每帧建一次
        """
        if self.__Rejected is not None and not any(panel is self.__Rejected for panel in panels):
            self.__Rejected = None
        if not panels or (self.Current is not None and self.Owner is None):
            return
        if any(panel is self.Owner for panel in panels):
            return
        mouse = mouse_pos()
        if not mouse:
            return
        for panel in panels:
            if panel is self.__Rejected or getattr(panel, "Destroyed", False) or not panel.HasMeiTooltip():
                continue
            rect = self.__RectOf(panel)
            if rect is None or not contains(rect, mouse):
                continue
            if not self.ShowFor(panel, rect):
                self.__Rejected = panel
                if not panel.HasMeiTooltip():
                    # 格子改了主意（配方收藏找不回配方、这个类型的预览建不出来）：悬停文字的绑定这下要给原版名了，
                    # 可写满后暂停了的 grid 不再拉 —— 唤醒一次，不然 PC 上悬停什么都不出
                    self.__WakeGrids()
            return

    def __Tick(self):
        """
        格子拆没拆、换没换内容（翻页、重排）、光标离没离开那一格（PC）；构建中的问建好没有，显示中的跟着光标、贴边翻转
        """
        mouse = mouse_pos()
        owner = self.Owner
        if owner is not None:
            if getattr(owner, "Destroyed", False) or content_key(owner) != self.OwnerKey:
                self.Hide()
                return
            if self.Host == HOST_DESKTOP and (not mouse or self.OwnerRect is None
                                              or not contains(self.OwnerRect, mouse)):
                self.Hide()
                return
        if self.Phase == PHASE_BUILDING:
            self.__PollBuild(mouse)
        elif self.Host == HOST_DESKTOP:
            self.__Follow(mouse)
        else:
            self.__Settle()

    # 内容控件
# ======================================================================================================================
    def __Mount(self, control_def):  # type: (str) -> str or None
        """
        准备好这一种内容控件，返回路径；建不出来 None。
        还藏着同一种的就复用（透明度先写回 0，建齐了再拉回来），一个控件都不建；换了一种先删旧的、再建新的（生下来就全透明）
        """
        if self.Content is not None and self.ContentDef == control_def:
            tip = self.MainNode.GetUIControl(self.Content)
            if tip is not None:
                tip.SetAlpha(0.0)
                return self.Content
        self.__Discard()
        slot_path = HOST_SLOTS[self.Host]
        slot = self.MainNode.GetUIControl(slot_path)
        if slot is None:
            logger.error("[MEI/tooltip] 界面里没有 tooltip 的宿主（{}）".format(slot_path))
            return None
        name = content_name(control_def)
        self.MainNode.CreateChildControl(control_def, name, slot, True)
        path = slot_path + "/" + name
        tip = self.MainNode.GetUIControl(path)
        if tip is None:
            logger.error("[MEI/tooltip] {} 建不出来".format(native_str(control_def)))
            return None
        # JSON 里本来就是 0；同名的残留（上次关界面没走到 OnDestroy）SDK 会直接还给我们，那个不一定是透明的
        tip.SetAlpha(0.0)
        if self.Host == HOST_TOUCH:
            self.__Bare(path)
        self.Content = path
        self.ContentDef = control_def
        return path

    def __Bare(self, path):
        """
        触屏：内容控件不画自己的 purpleBorder，换成 1×1 的透明图 —— 菜单的框已经画了一个（tooltip.md §6.12）。
        只换底图：尺寸照旧跟着内容（「100%c+8px」），透明着建、拉回不透明也照旧靠它。PC 上不换
        """
        image = self.MainNode.GetUIControl(path, "image")
        if image is None:
            return
        try:
            image.SetSprite(TooltipPath.BlankSprite)
        except Exception as e:  # noqa
            logger.warn("[MEI/tooltip] 换不了内容的底图（触屏上会多画一层框）: {}".format(error_text(e)))

    def __Discard(self):
        """ 删掉藏着（或亮着）的内容控件：换一种之前、开关界面时 """
        path, self.Content, self.ContentDef = self.Content, None, None
        if path is None:
            return
        control = self.MainNode.GetUIControl(path)
        if control is not None:
            self.MainNode.RemoveChildControl(control)

    def __SetTitle(self, text):
        if self.Content is None:
            return
        label = self.MainNode.GetUIControl(self.Content + TooltipPath.TitleSub, "label")
        if label is not None:
            label.SetText(native_str(text))

    def RecipeTitle(self, recipe):  # type: (any) -> unicode
        """ 「类型名 · 主产物名」；没有产物的（燃料页）写第一样原料 """
        output = None
        primary = recipe.GetPrimaryOutput() if hasattr(recipe, "GetPrimaryOutput") else None
        if primary is None:
            inputs = recipe.GetInputs() if hasattr(recipe, "GetInputs") else ()
            primary = inputs[0] if inputs else None
        stacks = primary.get_stacks() if primary is not None else ()
        if stacks:
            output = DescribeItem(stacks[0].Item)
        return TooltipText.Recipe.format(self.CategoryName(recipe.Type), to_unicode(output or ""))

    @staticmethod
    def CategoryName(category_id):  # type: (str) -> unicode
        """ 类型名：和配方页、配方树同一个来源（RecipeManager.GetDisplayText；不另记一张名字表） """
        return RecipeManager.GetDisplayText(category_id)

    # 建好再给看
# ======================================================================================================================
    def __ApplyHosts(self, showing):  # type: (bool) -> bool
        """
        宿主显隐，每次都把四个控件两个方向显式写一遍（界面状态跨开关存活，§22）。设置开着时根一直亮着；PC 宿主在 PC 上一直亮着、
        一直跟着光标，显示时它已经在光标处 —— 藏 tooltip 只藏 frame；移动端藏的是它自己的宿主（触屏菜单）。
        设置关着时 PC 上根和 PC 宿主也藏（什么都不出，也就不用跟光标）；触屏上根照样亮着 —— 菜单照出。界面里没有 tooltip 返回 False
        """
        root = self.MainNode.GetUIControl(TooltipPath.Root)
        if root is None:
            return False
        desktop = self.Host == HOST_DESKTOP
        root.SetVisible(self.Enabled or not desktop)
        for path, visible in ((TooltipPath.Desktop, self.Enabled and desktop),
                              (TooltipPath.DesktopFrame, desktop and showing),
                              (TooltipPath.Touch, showing and not desktop)):
            control = self.MainNode.GetUIControl(path)
            if control is not None:
                control.SetVisible(visible)
        return True

    def __Build(self, kind):
        """
        内容控件准备好了：亮 frame（PC）或移动端宿主，内容还是全透明的；建齐之后 __Reveal 摆到位、拉回不透明。
        移动端菜单的框也先写回透明，和内容一起拉回来（不然顶栏、按钮先冒出来、内容后到）
        """
        if not self.__ApplyHosts(True):
            logger.error("[MEI/tooltip] 界面里没有 tooltip 控件（{}）".format(TooltipPath.Root))
            return
        self.__SetTouchAlpha(0.0)
        self.Current = kind
        self.Phase = PHASE_BUILDING
        self.BuildTicks = 0
        self.LastTipSize = None
        self.Offset = None
        self.Bounds = None
        self.Placed = None

    def __PollBuild(self, mouse):
        """ 构建中：视图说建齐了、内容尺寸两帧一样，就显示；等太久也照常显示，不能一直不出 """
        tip = self.MainNode.GetUIControl(self.Content) if self.Content is not None else None
        if tip is None:
            self.Hide()
            return
        self.BuildTicks += 1
        view_ready = self.__ViewReady()
        width, height = tip.GetSize()
        size = (int(round(width)), int(round(height)))
        stable = size == self.LastTipSize and size[0] > 0 and size[1] > 0
        self.LastTipSize = size
        if not (view_ready and stable) and self.BuildTicks < self.BUILD_MAX_TICKS:
            return
        self.__Reveal(mouse, size)

    def __ViewReady(self):  # type: () -> bool
        if self.Current == TooltipKind.Items:
            return self.Items.IsReady()
        if self.Current == TooltipKind.Recipe:
            return self.Recipe.Poll()
        return True

    def __SetTouchAlpha(self, alpha):
        """ 移动端菜单的框（顶栏、分隔线、按钮区都在它下面）跟着内容透明 / 不透明；PC 上没有它 """
        if self.Host != HOST_TOUCH:
            return
        frame = self.MainNode.GetUIControl(TooltipPath.TouchFrame)
        if frame is not None:
            frame.SetAlpha(alpha)

    def __Reveal(self, mouse, size):
        """ 建好了：摆到位，再把内容的 alpha 拉回 1（同一帧里做，玩家看到的第一眼就是摆好的） """
        self.Phase = PHASE_SHOWN
        root = self.MainNode.GetUIControl(TooltipPath.Root)
        if root is not None:
            self.Bounds = utilities.GetControlRectSize(root)
            if self.Host == HOST_TOUCH:
                self.__PlaceTouch(size)
            else:
                self.Offset = None
                self.Gap = self.__ReadGap()
                self.__PlaceDesktop(mouse, size)
        tip = self.MainNode.GetUIControl(self.Content) if self.Content is not None else None
        if tip is not None:
            tip.SetAlpha(1.0)
        self.__SetTouchAlpha(1.0)

    # 摆位置
# ======================================================================================================================
    def __Follow(self, mouse):
        """ 显示中（PC）：跟着光标、贴边翻转 """
        tip = self.MainNode.GetUIControl(self.Content) if self.Content is not None else None
        if tip is None or self.Bounds is None:
            return
        width, height = tip.GetSize()
        self.__PlaceDesktop(mouse, (width, height))

    def __ReadGap(self):  # type: () -> tuple
        """
        离光标多远、默认在哪边：JSON 里 cursor_gap 这个记号的 offset（mei_common.tooltip_root/desktop/cursor_gap），
        脚本只读不改，所以 GetPosition 读到的就是 JSON 里写的数。每次显示读一次（开界面那一刻它可能还没排过版）；读不到用 GAP
        """
        marker = self.MainNode.GetUIControl(TooltipPath.DesktopGap)
        if marker is None:
            return GAP, GAP
        try:
            x, y = marker.GetPosition()
        except Exception as e:  # noqa
            logger.warn("[MEI/tooltip] 读不到 cursor_gap 的位置，用缺省 {}: {}".format(GAP, error_text(e)))
            return GAP, GAP
        return cursor_gap(x, y)

    def __PlaceDesktop(self, mouse, size):
        """
        tooltip 的左上角 = 光标 + 离光标那段距离与贴边翻转（layout.place，距离与默认方向是 self.Gap）；
        frame 的偏移相对宿主，所以按宿主**实际**在哪算差。宿主跟上了光标（常亮的宿主一直跟着）：偏移就是 place 那一段，
        平时不变、不碰控件；宿主根本不跟：偏移把差补上。宿主本身一律不碰
        """
        host = self.MainNode.GetUIControl(TooltipPath.Desktop)
        frame = self.MainNode.GetUIControl(TooltipPath.DesktopFrame)
        if host is None or frame is None or self.Bounds is None:
            return
        host_x, host_y = host.GetGlobalPosition()
        anchor = tuple(mouse) if mouse else (host_x, host_y)
        dx, dy = place(anchor, size, self.Bounds, self.Gap)
        offset = (int(round(anchor[0] + dx - host_x)), int(round(anchor[1] + dy - host_y)))
        if offset != self.Offset:
            frame.SetPosition(offset)
            self.Offset = offset

    def __Settle(self):
        """
        显示中（触屏菜单）：内容尺寸变了就按新尺寸重新摆 —— 菜单里换了候选，标题（那个候选的悬停文字）行数会变；
        框、宿主的尺寸（吞点击的底板）和贴边都得跟着。只量一个控件，菜单开着时每帧一次
        """
        tip = self.MainNode.GetUIControl(self.Content) if self.Content is not None else None
        if tip is None:
            return
        width, height = tip.GetSize()
        size = (int(round(width)), int(round(height)))
        if size != self.Placed:
            self.__PlaceTouch(size)

    def __PlaceTouch(self, size):
        """
        移动端（触屏菜单）：不跟手指走；这个宿主不是 follows_cursor，可以挪。
        框多大、框里的东西摆在哪由菜单按内容尺寸算（SetTouchLayout）；没给就是只有内容那么大、内容摆在左上角。
        宿主与框都写成这个尺寸（吞点击的底板盖得住整个菜单，purpleBorder 画满）。
        设置「触控tooltip是否沿对面侧显示」开着时摆到点的那一格另一侧的屏幕边上（place_opposite，方便双手操作）；
        否则菜单给了区域就摆在区域外侧（place_outside：物品栏的格子摆在物品栏左边、收藏栏的摆在右边、配方页的摆在配方页右边，
        竖直方向跟着那一格），没给就摆在格子旁（place_beside）；都会贴屏幕边兜底
        """
        host = self.MainNode.GetUIControl(TooltipPath.Touch)
        if host is None or self.Bounds is None:
            return
        size = (int(round(size[0])), int(round(size[1])))
        self.Placed = size
        total = None
        if self.TouchLayout is not None:
            try:
                total = self.TouchLayout(size)
            except Exception as e:  # noqa
                logger.error("[MEI/tooltip] 菜单排版失败: {}".format(error_text(e)))
        if not total:
            total = size
            slot = self.MainNode.GetUIControl(TooltipPath.TouchContent)
            if slot is not None:
                slot.SetPosition((0, 0))
        total = (int(round(total[0])), int(round(total[1])))
        host.SetSize(total)
        frame = self.MainNode.GetUIControl(TooltipPath.TouchFrame)
        if frame is not None:
            frame.SetSize(total)
        (root_x, root_y), _ = self.Bounds
        rect = self.AnchorRect or ((0, 0), (0, 0))
        if self.OppositeSide:
            x, y = place_opposite(rect, total, self.Bounds)
        elif self.TouchRegion is not None:
            region, side = self.TouchRegion
            x, y = place_outside(rect, total, region, side, self.Bounds)
        else:
            x, y = place_beside(rect, total, self.Bounds)
        host.SetPosition((int(round(x - root_x)), int(round(y - root_y))))

    def __RectOf(self, panel):  # type: (any) -> tuple or None
        """ 这一格的矩形；有镜像格的（酿造台下面三瓶）取光标所在的那一个，光标不在哪个上面就取它自己的 """
        rects = []
        for control in panel_controls(panel):
            try:
                rects.append(utilities.GetControlRectSize(control))
            except Exception:  # noqa  格子刚被拆、控件已经不在
                continue
        rects = [rect for rect in rects if rect is not None]
        if len(rects) > 1:
            mouse = mouse_pos()
            for rect in rects:
                if mouse and contains(rect, mouse):
                    return rect
        return rects[0] if rects else None
