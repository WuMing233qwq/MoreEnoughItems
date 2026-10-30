# coding=utf-8
# ----------------------------------------------------------------------
#  script.py is part of MoreEnoughItems.
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

import math
import time

import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.common.classes.base import BaseRecipeUIScript
from MEIScripts.constants.ui import BindingConst, CollectionConst, RecipeDetailsPath
from MEIScripts.constants.codes import NameConst, QueryConst
from MEIScripts.constants.texts import RecipeText, TransferText
from MEIScripts.mei_mod.state import BookmarkManager, CacheManager, PinManager
from MEIScripts.mei_mod.ui_script.controls.item import ItemsGrid
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys.binds import WheelTaken
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details import actions
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.controls.button import (
    RecipeAction, RecipeActionBind,
)
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules import RecipesGridBind
from MEIScripts.mei_mod.network.protocol.client import BuildPlan, SendTransfer
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.craftable import CraftableCache
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.screen_transfers import ScreenTransfers
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import NotifyNoRecipes
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.host import (
    attach_script, build_script, detach_script, is_live)
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.ordering import SortResult
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.typetab import TypeTabNav
from MEIScripts.mei_mod.ui_script.proxy.focus.search import contains, control_rect
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.registry import RecipeUIManager, RecipeManager
from MEIScripts.registry.sources import SourceRegistry
from MEIScripts.utils import utilities
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.events import EventListener
from MEIScripts.utils.page import BuildPage
from MEIScripts.utils.sequence import recipe_id
from MEIScripts.utils.text import error_text, native_str, to_unicode

ViewBinder = clientApi.GetViewBinderCls()

class RecipeDetailsScript(object):
    def __init__(self):
        self.MainNode = None
        self.ScreenNode = None
        self.Events = None  # type: EventListener or None  # 第一次开界面时建，之后复用
        self.Bindings = None  # type: ScreenBinder or None  # 同上：type_tab 与配方行可见性这几条绑定

        self.GameComp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

        self.ContextInited = False
        self.Created = False
        self.RecipeUIReady = False
        self.RecipesGridReady = False
        self.StationItemsGridReady = False
        self.TypeTabsGridReady = False

        self.RecipeUIScriptList = []  # type: list

        self.ItemComp = clientApi.GetEngineCompFactory().CreateItem(clientApi.GetLevelId())

        self.StationItemsGridIns = None
        self.RecipesGridBind = None
        self.RecipeActionBind = None
        self.Craftable = CraftableCache()
        """ 可合成性预检缓存，一次会话算一次；转移成功后失效 """
        self.NoticeText = None  # type: unicode or None
        """ 点了 + 没成时挂在页码后面的一句话（ShowNotice），到 NoticeUntil 那一刻节拍里收掉 """
        self.NoticeUntil = 0.0
        self.RecipesPage = None
        self.RecipeUIScriptCls = None

        self.TypeNav = TypeTabNav()
        """
        配方类型 tab 的导航（选中 + 视图两份状态）。算术全在 modules/typetab.py，
        本类只负责推控件。**替代了原先的 CraftingTypesPage** —— 那个把
        「选中哪个」与「看哪一页」混成了一份状态，所以永远翻不了页。
        """

        self.TypeTabToggleUpdated = False
        """
        「选中态已经同步给引擎了」的闩锁，**在 `UpdateTypeTabsGrid` 里重新武装**。

        tab 是单选组（JSON 的 `$radio_toggle_group`），互斥由引擎保证，
        Python 只需在每次 grid 重建后把选中的那一格推成 True 一次。
        逐格推 True/False 会和单选组打架 —— 见 `SyncTypeTabToggle` 的说明。
        """

        self.SeenTabIndex = set()  # type: set
        """
        哪些 tab 下标的绑定回调已经被引擎调过至少一次。

        **推 toggle 之前必须先见过一次**：grid 子控件首次渲染前不可访问
        （引擎结论 §5），此刻拿到的很可能是**模板控件**，对模板做 screen action
        会触发引擎断言。见过一轮就说明它已经实例化了。
        """

        self.TypeTabIdAux = {}  # type: dict  # crafting_type -> id_aux，**取到才存**
        """
        tab 图标的 id_aux 缓存。引擎对某些方块(尤其第三方的)在开页那一刻答不上来，
        所以**兜底值不进缓存**，下一帧继续问 —— 否则那个 tab 一整次会话都是草方块。
        """

        self.MainContentWidth = 0  # type: int
        self.MainContentHeight = 0  # type: int

        self.StationItemsGridCols = 0  # type: int
        self.StationItemsGridRows = 0  # type: int
        self.StationKeys = None  # type: tuple or None  # 工作站格子现在画的是哪几样（UpdateStationItemsGrid 比对它：没变就不动）

        self.RecipesGridControl = None
        self.MainContentControl = None
        self.CraftingItemsControl = None
        self.TypeTabsGridControl = None
        self.TopOverlayPageUpBtn = None
        self.TopOverlayPageDownBtn = None
        self.TopLine1LabelControl = None
        self.TopLine2LabelControl = None
        self.TopLine1PageUpBtn = None
        self.TopLine1PageDownBtn = None
        self.TopLine2PageUpBtn = None
        self.TopLine2PageDownBtn = None
        self.RightCloseBtn = None
        self.RightBackBtn = None

        # 导航状态**不在这里** —— 它是缓存态, 统一由 CacheManager.GetRecipeNav() 持有,
        # 这样去重(LRUHistory)与容量上限只有一处实现。见 state/cache.py 的 RecipeNav。

        self.MaxRecipesInPage = 0  # type: int
        self.CurrentType = ""  # type: str
        self.CurrentRecipes = []  # type: list
        self.RecipesResult = []  # type: list
        self.RawRecipesResult = []  # type: list   # 查询原序，置顶排序每次都从它出发
        self.PendingFocusId = None  # type: str or None  # 从收藏点开时要翻到的那条配方，建配方分页时用掉
        self.ScanPending = []  # type: list
        """
        正在看的是工作站的用途、它服务的类型全表还在扫（RecipeManager.PendingCategories）：这些类型的页码后面写「扫描中」，
        节拍里等它们扫完、重新查一次刷新（PollScan，只刷新一次）
        """
        self.ScanEntry = None  # type: tuple or None  # 上面那份结果是查哪个 (物品, 方向) 得来的
        self.CraftingStationItems = []  # type: list

        self.ControlDef = ""  # type: str
        self.RecipeHeight = 0 # type: int

        self.GetTypeTabIdAuxWrapper = None

        self.AnimTimer = None   # type: any  # 本页唯一的节拍 timer
        self.PendingSwitchTimer = None  # type: any
        """
        待执行的类型切换。连按逐个切换时用它合并重建 —— 见 StepType。
        """
        self.AnimTicks = 0          # type: int  # 从 1 起, 每 ANIM_TICK_INTERVAL 秒 +1


    # 初始化与销毁相关方法
# ======================================================================================================================
    def InitControls(self):
        self.MainContentControl = self.MainNode.GetRootBaseUIControl(RecipeDetailsPath.Content)
        self.CraftingItemsControl = self.MainNode.GetRootBaseUIControl(RecipeDetailsPath.CraftingItems)

        self.TypeTabsGridControl = self.MainNode.GetUIControl(
            RecipeDetailsPath.TypeTabGrid, "grid")

        self.TopOverlayPageUpBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.StationsPageUpBtn, "button")
        self.TopOverlayPageDownBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.StationsPageDownBtn, "button")

        self.TopLine1LabelControl = self.MainNode.GetUIControl(
            RecipeDetailsPath.DisplayNameLabel, "label")
        self.TopLine2LabelControl = self.MainNode.GetUIControl(
            RecipeDetailsPath.Line2PageIndexLabel, "label")

        self.TopLine1PageUpBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.Line1PageUpBtn, "button")
        self.TopLine1PageDownBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.Line1PageDownBtn, "button")

        self.TopLine2PageUpBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.Line2PageUpBtn, "button")
        self.TopLine2PageDownBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.Line2PageDownBtn, "button")

        self.RightCloseBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.CloseBtn, "button")
        self.RightBackBtn = self.MainNode.GetUIControl(
            RecipeDetailsPath.BackBtn, "button")

        self.TopOverlayPageUpBtn.AddTouchEventParams({"isSwallow": True})
        self.TopOverlayPageDownBtn.AddTouchEventParams({"isSwallow": True})
        self.TopLine1PageUpBtn.AddTouchEventParams({"isSwallow": True})
        self.TopLine1PageDownBtn.AddTouchEventParams({"isSwallow": True})
        self.TopLine2PageUpBtn.AddTouchEventParams({"isSwallow": True})
        self.TopLine2PageDownBtn.AddTouchEventParams({"isSwallow": True})
        self.RightCloseBtn.AddTouchEventParams({"isSwallow": True})
        self.RightBackBtn.AddTouchEventParams({"isSwallow": True})

        # 三组翻页按钮，语义各不相同：
        #   overlay -> tab 条整页翻（不换选中）
        #   line1   -> 逐个切换类型（跨页时 tab 条跟过去，到头循环）
        #   line2   -> 当前类型下的配方翻页
        self.TopOverlayPageUpBtn.SetButtonTouchDownCallback(self.TypeTabPageUp)
        self.TopOverlayPageDownBtn.SetButtonTouchDownCallback(self.TypeTabPageDown)
        self.TopLine1PageUpBtn.SetButtonTouchDownCallback(self.TypeStepNext)
        self.TopLine1PageDownBtn.SetButtonTouchDownCallback(self.TypeStepPrev)
        self.TopLine2PageUpBtn.SetButtonTouchDownCallback(self.RecipesPageUp)
        self.TopLine2PageDownBtn.SetButtonTouchDownCallback(self.RecipesPageDown)

        self.RightCloseBtn.SetButtonTouchUpCallback(self.Close)
        self.RightBackBtn.SetButtonTouchUpCallback(self.GoBack)

        station_items_grid = self.MainNode.GetUIControl(
            RecipeDetailsPath.CraftingItemsGrid, "grid")
        self.StationItemsGridIns = ItemsGrid.from_collection_name(station_items_grid, CollectionConst.CraftingStationItems, item_panel_callback=self.CraftingItemPanelCallback)
        # 工作站这个 grid 只有几格：不暂停绑定（格子重建了，新格子的可见、数量这些要拉得到值），推完行列数后 30 轮（约一秒）里逐轮核对图标 ——
        # 不这样的话，熔炉 → 高炉这类工作站从 2 格变 1 格时，高炉那一格会是空的（引擎结论 §46）
        self.StationItemsGridIns.BindingPausedWhenSaturated = False
        self.StationItemsGridIns.RepaintPasses = (2, 30)
        self.StationKeys = None
        self.RecipesGridBind = RecipesGridBind(self.ScreenNode, CollectionConst.Recipes)

        # 动作按钮(收藏/置顶/转移/配方树). 与 RecipesGridBind 同挂在 recipes_grid 上,
        # 但走的是 toggle 那套绑定 —— 见 controls/button.py 的文档.
        # Interpret 会扫本类上的 @RecipeAction 声明; 没声明的动作补成占位(因而不渲染).
        self.RecipeActionBind = RecipeActionBind(self.ScreenNode, CollectionConst.Recipes)
        self.RecipeActionBind.SetRowResolver(self.GetRecipeAtRow)
        self.RecipeActionBind.SetControlResolver(self.GetRecipeRowControl)
        self.RecipeActionBind.SetPathResolver(actions.ResolvePath)
        self.RecipeActionBind.SetEnabledResolver(self.IsActionEnabled)
        self.RecipeActionBind.Interpret(self, placeholders=actions.BuildPlaceholders())

        self.Bindings.Bind(self.TypeTabToggleCallback, ViewBinder.BF_ToggleChanged, BindingConst.CraftingStationTypeTab)
        self.Bindings.Bind(self.GetRecipeVisible, ViewBinder.BF_BindBool, BindingConst.RecipeVisible, CollectionConst.Recipes)

    def InitEvent(self):
        """ 启动监听一些事件 """
        self.Events.Listen("ScreenSizeChangedClientEvent", self.OnScreenSizeChanged)
        self.Events.Listen("MouseWheelClientEvent", self.OnMouseWheel)

    def InitContentSize(self):
        """ 初始化获取主控件尺寸 """
        self.MainContentWidth, self.MainContentHeight = utilities.GetControlSizeInt(self.MainContentControl)

    def InitScript(self):
        if self.Created:
            return
        if not self.ContextInited:
            self.MainNode = context.GetMainNode()
            self.ScreenNode = self.MainNode.ScreenNode
            self.Events = EventListener(clientApi.GetSystem(NameConst.NameSpace, NameConst.ClientSysName))
            self.Bindings = ScreenBinder(self.ScreenNode)
        self.ContextInited = True

        self.InitControls()
        self.InitContentSize()

        self.InitEvent()
        self.StartAnimTimer()

        self.Created = True

    # 配方页脚本的渲染节拍 —— **整页一个 timer**
# ======================================================================================================================
    def StartAnimTimer(self):
        """
        起本页唯一的节拍 timer。间隔取 `BaseRecipeUIScript.ANIM_TICK_INTERVAL`

        **整页共享一个**，不是一个配方行一个：后者正是 §2.7-5 记的那类问题
        （`MultiItemPanel` 每个多候选槽起一个 timer，数量随行数线性增长且相位不同步）。
        """
        if self.AnimTimer is not None:
            return
        self.AnimTicks = 0
        self.AnimTimer = self.GameComp.AddRepeatedTimer(
            BaseRecipeUIScript.ANIM_TICK_INTERVAL, self.OnAnimTimer)

    def CancelPendingSwitch(self):
        """ 取消还没跑的类型切换 —— 关页时必须调, 否则回调会摸到已销毁的控件 """
        if self.PendingSwitchTimer is not None:
            self.GameComp.CancelTimer(self.PendingSwitchTimer)
            self.PendingSwitchTimer = None

    def StopAnimTimer(self):
        if self.AnimTimer is None:
            return
        self.GameComp.CancelTimer(self.AnimTimer)
        self.AnimTimer = None

    @staticmethod
    def OverridesAnimTick(script_cls):  # type: (type) -> bool
        """
        这个配方页脚本类有没有覆写 `OnAnimTick`

        ⚠ **不能写成 `cls.OnAnimTick is BaseRecipeUIScript.OnAnimTick`** —— py2 的 unbound method
        是每次取属性时**新建**的包装对象，`is` 恒为 False，那个判据永远认为"覆写了"，
        于是静态配方页也会被逐个调用（回归位 probe_extensions X-13）。
        要比的是底下的**函数对象** `__func__`。
        """
        own = getattr(script_cls, "OnAnimTick", None)
        base = BaseRecipeUIScript.OnAnimTick
        return getattr(own, "__func__", own) is not getattr(base, "__func__", base)

    def PrimeAnimTick(self, script_ins):
        """
        配方行刚建好就**立刻先画第 0 帧**，不等下一拍。

        不这么做会有一段最长 **0.4 秒**的空窗，且是两段叠加：
          ① 创建完到下一拍，最多等 `ANIM_TICK_INTERVAL`（0.2s）；
          ② 那一拍旧实现里只对表就 `continue` 了，再等 0.2s。
        期间控件停在 layout 里的初值上，看着像“卡一下才开始动”。

        对表与首帧合并在这里做：`_AnimBase` 钉在当前拍，紧接着派发
        `OnAnimTick(0)` —— 于是第 0 帧由创建时画，之后 timer 从 1 接上。
        """
        if not self.OverridesAnimTick(type(script_ins)):
            return
        script_ins._AnimBase = self.AnimTicks  # noqa
        self.DispatchAnimTick(script_ins, 0)

    @staticmethod
    def DispatchAnimTick(script_ins, ticks):
        """ 派一拍。**一个配方页炸了不能停掉整页的 timer** """
        try:
            script_ins.OnAnimTick(ticks)
        except Exception as e:  # noqa
            logger.error("[MEI/ui] {} 的 OnAnimTick 抛异常: {}".format(
                type(script_ins).__name__, error_text(e)))

    def OnAnimTimer(self):
        """ 把节拍派发给本页所有已创建的配方脚本 """
        self.AnimTicks += 1
        for script_ins in self.RecipeUIScriptList:
            # 半成品实例不能碰: 控件要等 Tick 接上；接的时候出了错的(_Broken)也不碰
            if not is_live(script_ins):
                continue
            # **没覆写就不调** —— 绝大多数配方页是静态的, 不该为它们付遍历以外的代价
            if not self.OverridesAnimTick(type(script_ins)):
                continue
            # ticks 要相对**它自己出生的时刻**, 否则中途创建的配方行会撞上
            # 任意相位, 表现为动画跳帧。对表正常在 PrimeAnimTick 里做,
            # 这里只是兵到山前(理论上走不到)
            if script_ins._AnimBase is None:  # noqa
                self.PrimeAnimTick(script_ins)
                continue
            self.DispatchAnimTick(
                script_ins, self.AnimTicks - script_ins._AnimBase)  # noqa

        # 面板侧的节拍(多候选轮播)。转发由绑定器做 —— 面板归它持有
        if self.RecipesGridBind:
            self.RecipesGridBind.TickPanels(self.AnimTicks)

        try:
            self.PollScan()
        except Exception as e:  # noqa  刷新失败只少一次刷新，不能停掉整页的节拍
            self.ScanPending = []
            logger.error("[MEI/ui] 扫描完成后刷新工作站的用途失败: {}".format(error_text(e)))
        try:
            self.ExpireNotice()
        except Exception as e:  # noqa
            self.NoticeText = None
            logger.error("[MEI/ui] 配方页提示收不掉: {}".format(error_text(e)))


    def DestroyScript(self):
        self.StopAnimTimer()
        self.CancelPendingSwitch()
        self.Bindings.UnbindAll()
        self.ClearUICache()

        self.StationItemsGridIns.UnbindAll()
        self.RecipesGridBind.Destroy()
        self.RecipesGridBind = None
        self.RecipeActionBind.Destroy()
        self.RecipeActionBind = None

        self.ControlDef = ""
        self.RecipesPage = None
        self.TypeNav = TypeTabNav()
        self.TypeTabToggleUpdated = False
        self.SeenTabIndex = set()
        self.TypeTabIdAux = {}
        self.CurrentRecipes = []
        self.CurrentType = ""
        # 注意这里**不动** CacheManager 的 RecipeNav: 导航状态是缓存态, 跨关闭存活,
        # 关掉再开还能继续往回退. 栈里存的是 Item 实例, GoBack 直接拿它重查即可.
        # 重开时的重渲染由 ApplyQueryResult 保证 —— 判据正是这里被清空的 RecipesResult.
        self.RecipesResult = []
        self.RawRecipesResult = []
        self.PendingFocusId = None
        self.NoticeText = None
        self.ScanPending = []
        self.ScanEntry = None
        self.RecipesGridControl = None
        self.TypeTabsGridReady = False

        self.Events.UnlistenAll()

        self.Created = False


    def ResolveQuery(self, item, query_by=QueryConst.Output):
        # type: (any, str) -> dict or None
        """
        **纯查询**: 不碰任何控件, 不改任何状态, 无结果返回 None.

        单独拆出来是为了让调用方能"先问后建" —— 配方面板一旦 CreateChildControl
        出来就是可见的, 若等到查完才发现没结果, 空壳已经露在屏幕上了
        (表现是从浏览器点无配方的物品会开出一个空页面)。
        查询本身很贵(CLAUDE.md 引擎结论 §3), 所以结果要带着走, 不能查两遍。
        """
        result, _complete = RecipeManager.QueryRecipeEx(item=item, query_by=query_by)
        if not result:
            return None  # 纯查询不提示：用户发起的那几处自己调 NotifyNoRecipes
        return result

    def ApplyQueryResult(self, item, query_by, result, push_history=True, prefer_type=None, focus_id=None):
        # type: (any, str, dict, bool, str, str) -> bool
        """ 把已经查好的结果铺到页面上, 并推进导航状态；prefer_type / focus_id 是从收藏点开时要停的类型与配方 """
        nav = CacheManager.GetRecipeNav()
        entry = (item, query_by)

        if push_history:
            moved = nav.Go(entry)
            # 同页短路: 点配方的产出格查的正是当前物品, 不该入栈也不该重渲染.
            # 但**页面上什么都没有**时必须照渲染不误 —— 导航状态是跨关闭存活的,
            # 关掉再开时 nav 仍记得 Current, 光靠短路会让新面板空着.
            if not moved and self.RecipesResult:
                if prefer_type or focus_id:
                    return self.FocusRecipe(prefer_type, focus_id)
                return True
        else:
            nav.SetCurrent(entry)

        CacheManager.AddHistory(item)
        self.ScanEntry = entry
        self.ScanPending = RecipeManager.PendingCategories(item, query_by)
        self.SetRecipesResult(result, prefer_type, focus_id)
        self.UpdateBackButton()
        return True

    def PollScan(self):
        """
        正在看的工作站用途，它服务的类型扫完了：重新查一次，停在原来的类型和那一页（按这一页的第一条配方定位），只刷新这一次。
        节拍里调（每 0.2 秒）：只问各来源还在不在凑全表（RecipeManager.IsCategoryBuilding），不碰引擎
        """
        if not self.ScanPending:
            return False
        if any(RecipeManager.IsCategoryBuilding(category_id) for category_id in self.ScanPending):
            return False
        entry, self.ScanPending = self.ScanEntry, []
        if entry is None or not self.RecipesResult or CacheManager.GetRecipeNav().Current != entry:
            return False
        result = self.ResolveQuery(*entry)
        if result is None:
            return False
        shown = self.RecipesPage.current_items if self.RecipesPage else []
        focus = native_str(recipe_id(shown[0])) if shown and recipe_id(shown[0]) else None
        self.SetRecipesResult(result, prefer_type=self.CurrentType, focus_id=focus)
        return True

    def FocusRecipe(self, crafting_type, focus_id):  # type: (str, str) -> bool
        """ 结果已经在页面上：切到某个类型、翻到某条配方，从收藏点开正在看的物品时走这里 """
        if crafting_type not in self.RecipesResult:
            crafting_type = self.CurrentType
        self.PendingFocusId = focus_id
        if crafting_type != self.CurrentType:
            self.TypeNav.SelectByKey(crafting_type)
            self.ShowRecipeDetails(crafting_type)
        else:
            self.UpdateRecipeUI(update_page=True)
        return True

    def ShowRecipesFor(self, item, query_by=QueryConst.Output, push_history=True):
        # type: (any, str, bool) -> bool
        """
        把整套配方页切换到另一个物品 —— 点击配方里的材料走的就是这里.

        无结果时**什么都不做**: 不入栈、不改变当前显示.
        (面板尚未打开时, 由 UIScriptMain.ShowRecipeDetails 负责先 ResolveQuery
         再决定建不建控件, 所以也不会开出空页面。)
        """
        result = self.ResolveQuery(item, query_by)
        if result is None:
            NotifyNoRecipes(item, query_by)
            return False
        return self.ApplyQueryResult(item, query_by, result, push_history)

    # 动作按钮的声明. Interpret 扫这些装饰器, 一行绑定机制都不用写.
# ======================================================================================================================
    @RecipeAction.State(actions.STAR)
    def IsRecipeStarred(self, _row, recipe):  # type: (int, any) -> bool
        """ 星号亮不亮 = 这条配方是否已收藏，每帧回读，走内存索引 O(1) """
        return BookmarkManager.HasRecipe(recipe)

    @RecipeAction.Toggle(actions.STAR)
    def OnRecipeStarToggled(self, ctx):
        """ 玩家切换星号. 新状态在 ctx.State, 直接交给书签服务 """
        if ctx.Recipe is None:
            logger.info("[MEI/star] 行 {} 拿不到配方, 忽略".format(ctx.Row))
            return
        BookmarkManager.SetRecipe(ctx.Recipe, ctx.State)

    @RecipeAction.Visible(actions.STAR)
    def CanStarRecipe(self, _row, recipe):  # type: (int, any) -> bool
        """ 拿不到 Recipe.Id 的行没法收藏(键就是 Id), 那一行不渲染星号 """
        return bool(BookmarkManager.RecipeKey(recipe))

    @RecipeAction.Hover(actions.STAR)
    def StarHoverText(self, _row, recipe):  # type: (int, any) -> unicode
        return RecipeText.UnstarHover if BookmarkManager.HasRecipe(recipe) else RecipeText.StarHover

    @RecipeAction.State(actions.TOP)
    def IsRecipePinned(self, _row, recipe):  # type: (int, any) -> bool
        """ 置顶号亮不亮 = 这条配方是否已置顶，每帧回读，走内存索引 O(1) """
        return PinManager.HasRecipe(recipe)

    @RecipeAction.Toggle(actions.TOP)
    def OnRecipeTopToggled(self, ctx):
        """ 玩家切换置顶，下一帧重排当前结果 """
        if ctx.Recipe is None:
            logger.info("[MEI/top] 行 {} 拿不到配方, 忽略".format(ctx.Row))
            return
        PinManager.SetRecipe(ctx.Recipe, ctx.State)
        if ctx.State and not PinManager.HasRecipe(ctx.Recipe):
            # 到上限被拒；按钮已被玩家按亮，靠重排把状态推回去
            logger.info("[MEI/top] 置顶已满 {} 条, 拒绝新增".format(PinManager.Count()))

        # 重排要拆掉正在派发这次回调的那一行的控件，不能在引擎回调里同步做
        def __reorder():
            self.RefreshPinnedOrder()
        self.GameComp.AddTimer(0.0, __reorder)

    @RecipeAction.Visible(actions.TOP)
    def CanPinRecipe(self, _row, recipe):  # type: (int, any) -> bool
        """ 拿不到 Recipe.Id 的行没法置顶(键就是 Id), 那一行不渲染置顶号 """
        return bool(PinManager.RecipeKey(recipe))

    @RecipeAction.Hover(actions.TOP)
    def PinHoverText(self, _row, recipe):  # type: (int, any) -> unicode
        return RecipeText.UnpinHover if PinManager.HasRecipe(recipe) else RecipeText.PinHover

    @RecipeAction.Hover(actions.TREE)
    def TreeHoverText(self, _row, _recipe):  # type: (int, any) -> unicode
        return RecipeText.TreeHover

    # 配方树 —— docs/architecture/recipe_tree.md
# ======================================================================================================================
    @RecipeAction.Visible(actions.TREE)
    def CanOpenTree(self, _row, recipe):  # type: (int, any) -> bool
        """ 有主产物的配方都能开：以主产物为根，根就用这一条 """
        primary = recipe.GetPrimaryOutput() if recipe is not None else None
        return primary is not None and bool(primary.get_stacks())

    @RecipeAction.Button(actions.TREE)
    def OnOpenTree(self, ctx):
        """ PushScreen 一个新界面（OpenRecipeTree 自己排到下一拍压栈，不在按钮回调里当场做）"""
        if ctx.Recipe is None:
            return
        from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree  # 配方树用到才 import
        OpenRecipeTree(recipe=ctx.Recipe)

    # 快捷合成 —— 方案见 docs/architecture/quick_craft.md
# ======================================================================================================================
    @RecipeAction.Visible(actions.PLUS)
    def CanTransferRecipe(self, _row, recipe):  # type: (int, any) -> bool
        """
        这一类配方根本转移不了（类型没有转移策略、也没有哪个界面登记收它）才不渲染。
        能转移、只是当前界面不收或者材料不够，一律**灰掉**（Enabled，悬停写原因）——
        开着哪个界面是运行时的条件，藏起来玩家就不知道有这个功能（engineering.md §5.1f）
        """
        if recipe is None:
            return False
        return self.Craftable.Transferable(self.__CurrentCategory(), recipe, self.CurrentType)

    @RecipeAction.Enabled(actions.PLUS)
    def IsRecipeCraftable(self, _row, recipe):  # type: (int, any) -> bool
        """
        材料够不够。**每帧被回读，所以必须走缓存** —— 真正的采集在开页时算一次

        (不缓存就是每帧扫一遍背包, 正是 binding_cost.md 记的那类事故)
        交给界面登记的转移目标的不看材料，问它收不收这一条（同样走缓存）
        """
        target = self.Craftable.TransferTarget(recipe, self.CurrentType)
        if target is not None:
            return self.Craftable.Allows(target, recipe, self.CurrentType)
        return self.Craftable.CanCraft(self.__CurrentCategory(), recipe)

    @RecipeAction.Hover(actions.PLUS)
    def PlusHoverText(self, _row, recipe):  # type: (int, any) -> unicode
        """ + 的悬停文字：能点写点了会怎样，灰着写为什么、缺什么（转移处理器的检查、原版合成格的材料）。同样走缓存 """
        if recipe is None:
            return u""
        target = self.Craftable.TransferTarget(recipe, self.CurrentType)
        return self.Craftable.PlusHover(target, self.__CurrentCategory(), recipe, self.CurrentType)

    @RecipeAction.Button(actions.PLUS)
    def OnTransferRecipe(self, ctx):
        """
        玩家点了快捷合成：算清单 -> 发给服务端 -> 回执后关页

        **当前一律最大化转移**（材料与格子容量允许的最大倍数）。
        "普通转移 / 最大化"的手势区分还没有，
        与物品书签入口手势是同一件悬着的事。
        """
        if ctx.Recipe is None:
            return
        target = self.Craftable.TransferTarget(ctx.Recipe, self.CurrentType)
        if target is not None:
            # 交给当前界面登记的转移处理器：MEI 算好清单，处理器自己做。写成了关掉配方页回到那个界面；
            # 不在按钮回调里同步关（引擎结论 §10）。没成就把原因挂在页码后面。
            # 清单按点下去这一刻的背包算（开页时采的供给可能已经过时），顺带让 + 的结论重问
            self.Craftable.Invalidate()
            request = self.Craftable.Request(target, ctx.Recipe, self.CurrentType, wants_max=True)
            done, error = ScreenTransfers.Deliver(target, request)
            if done:
                self.Craftable.Invalidate()
                self.GameComp.AddTimer(0.0, self.Close)
            else:
                self.ShowNotice((error.Message if error is not None else u"") or TransferText.Failed)
            return
        category = self.__CurrentCategory()
        if category is None or category.Transfer is None:
            return

        plan = BuildPlan(category, ctx.Recipe, self.Craftable.MakeContext())
        if plan is None:
            NotifyNoRecipes(None, "transfer")
            return
        SendTransfer(plan, self.__OnTransferDone)

    def __OnTransferDone(self, result):  # type: (any) -> None
        """ 服务端回执。成功就关掉配方页 —— 玩家的下一步是回工作台按合成；一格都没放进去就在页码后面说一声 """
        if result.Filled <= 0:
            self.ShowNotice(TransferText.NothingMoved)
            return
        self.Craftable.Invalidate()
        if result.Failed > 0:
            # 放进去了几格、中途有一格没放成（服务端逐格提交，停在那一格）：不关页，说一声
            self.ShowNotice(TransferText.Partial)
            return
        # 不在回执回调里同步关: 这条回调来自引擎事件, 而 Close 会拆掉整棵控件树.
        # 与置顶重建行控件是同一条教训(回调里不同步拆建控件, 引擎结论 §10)
        self.GameComp.AddTimer(0.0, self.Close)

    def __CurrentCategory(self):  # type: () -> any
        return SourceRegistry.GetCategory(self.CurrentType) if self.CurrentType else None

    # 「配方怎么摊到容器槽位上」整个归转移策略的 MapRecipe 管 ——
    # 有序配方的形状换算(2x2 落在 0/1/3/4 而不是 0/1/2/3)、无序配方按 Amount 摊平,
    # 都在那一层, 且与配方页渲染走的是同一个 resolve_input_slot.
    # 不能用 enumerate(GetInputs()) 当格位下标: 那是**扁平输入序**不是网格位置,
    # 2x2 的配方会被放进 0/1/2/3

    def GetRecipeRowControl(self, row):  # type: (int) -> any
        """
        第 row 行的**配方行控件**. 动作按钮由绑定器再按相对路径取下去.

        直接复用 RecipeUIScript.RecipeControl —— 它在行渲染时由本屏幕填好
        (见 GetRecipeVisible), 不必再拼一次绝对路径.
        行控件还没建出来时返回 None 是常态(grid 懒建), 调用方安静跳过.
        """
        if 0 <= row < len(self.RecipeUIScriptList):
            return self.RecipeUIScriptList[row].RecipeControl
        return None

    def IsActionEnabled(self, prefix):  # type: (str) -> bool
        """ 当前配方类型启不启用某个内置动作, 由脚本类的 ACTIONS 声明 """
        # 每帧被问, 但只是一次 getattr + 一次 in, 比 Interpret 时问要对得多:
        # Interpret 只在屏幕初始化跑一次, 那时的 RecipeUIScriptCls 切一次类型就过期了
        return actions.IsEnabled(prefix, getattr(self.RecipeUIScriptCls, "ACTIONS", None))

    def GetRecipeAtRow(self, row):  # type: (int) -> any
        """
        第几行 -> 该行的 Recipe. 动作按钮的 ctx.Recipe 就来自这里.

        与 PrepareRecipeUIScript 用的是同一个 current_items, 所以行号语义一致;
        翻页/切类型后 RecipesPage 会重建, 这里自然跟着变, 不需要额外失效.
        """
        page = self.RecipesPage
        if not page:
            return None
        items = page.current_items
        if row is None or row < 0 or row >= len(items):
            return None
        return items[row]

    def RecipeAt(self, x, y):  # type: (float, float) -> any
        """
        这一点落在哪一行配方上（快捷键「收藏这条配方」「这条配方开配方树」用），没有返回 None。
        按行控件（接上脚本的才有）的真实矩形量，行里的空白处也算
        """
        for index, script_ins in enumerate(self.RecipeUIScriptList):
            rect = control_rect(getattr(script_ins, "RecipeControl", None))
            if rect is not None and contains(rect, x, y):
                return self.GetRecipeAtRow(index)
        return None

    def GoBack(self, _=None):  # type: (any) -> bool
        """
        回退一层. 栈空时什么都不做.

        若上一格已经查不出结果(索引变了/物品没了), 就**丢掉这一格继续往下找**,
        免得返回键卡在一个永远渲染不出来的条目上。
        """
        nav = CacheManager.GetRecipeNav()
        while True:
            entry = nav.Pop()
            if entry is None:
                self.UpdateBackButton()
                return False

            item, query_by = entry
            result = self.ResolveQuery(item, query_by)
            if result is not None:
                return self.ApplyQueryResult(item, query_by, result, push_history=False)

    def UpdateBackButton(self):
        utilities.SetButtonEnable(
            self.RightBackBtn, bool(CacheManager.GetRecipeNav().Depth()))

# 其他逻辑
# ======================================================================================================================
    def SetRecipesResult(self, result, prefer_type=None, focus_id=None):
        """ 设置当前的配方查询结果；给了 prefer_type 且结果里有就停在它上面，focus_id 是要翻到的那条配方 """
        if not result:
            return

        # 置顶重排在这里做而不是在 QueryRecipe 里：查询缓存存的是引擎事实，
        # 置顶是展示决策，混进缓存键会让每次 toggle 都把整个缓存作废
        self.RawRecipesResult = result
        result = SortResult(result)

        self.RecipesResult = result
        # 先定显示哪个类型（给了 prefer_type 且结果里有就是它，不然第一个），类型导航跟着它选中 ——
        # 导航要是按旧的 CurrentType 选（新结果里也有这个类型就停在它上面）、内容却显示第一个，两边就对不上：
        # 比如看下界合金装备（锻造台）时点下界合金锭，TypeTab 停在锻造台、内容是工作台合成
        crafting_type = prefer_type if prefer_type in result else next(iter(result))
        self.CurrentType = crafting_type
        self.BuildTypeNav(result.keys())
        self.PendingFocusId = focus_id
        self.ShowRecipeDetails(crafting_type)

    def RefreshPinnedOrder(self):  # type: () -> bool
        """ 置顶变化后重排当前结果，停在原来的类型上 """
        # 必须从查询原序 RawRecipesResult 出发重排，不能在上一次排好的结果上再排：
        # 未置顶组保留的是输入顺序，取消置顶时那条配方已经在输入的最前面，排完还在最前面
        if not self.RawRecipesResult:
            return False

        self.RecipesResult = SortResult(self.RawRecipesResult)
        self.BuildTypeNav(self.RecipesResult.keys())

        crafting_type = self.CurrentType
        if crafting_type not in self.RecipesResult:
            for crafting_type in self.RecipesResult:
                break
        self.ShowRecipeDetails(crafting_type)
        return True

    def ShowRecipeDetails(self, crafting_type):
        script_data = RecipeUIManager.GetScriptData(crafting_type)
        if not script_data:
            return

        script_cls, params = script_data
        control_def = RecipeManager.GetControlDef(crafting_type)

        self.ClearUICache()

        recipes = self.RecipesResult[crafting_type]
        self.CurrentType = crafting_type
        self.CreateRecipesGrid(control_def)
        self.RecipeUIScriptCls = script_cls
        self.CurrentRecipes = recipes

        self.StationItemsGridIns.InitBindings()

        self.RecipeUIReady = True

    TYPE_TABS_PER_PAGE = 8
    """ tab 条一页放几个。改它要同时改 UpdateTypeTabsGrid 的 SetGridDimension """

    def BuildTypeNav(self, types):
        """ 构建合成方式数据的页面 """
        # 这里**只存 (类型, 物品 id, aux)**，不在这一刻去问 id_aux。
        # 要是在此处 GetItemBasicInfo 并把取不到时的兜底值 131072 **固化**进表里，
        # 「开页那一刻引擎还答不上来」就等于这个 tab 一整次会话都是草方块，
        # 关掉重开才好(第三方机器方块首开必中)。
        # ⇒ 惰性解析，取到才缓存，取不到下一帧继续问，见 ResolveTypeTabIdAux。
        data = []
        for crafting_type in types:
            display_item_data = RecipeManager.GetDisplayItemData(crafting_type)
            if not display_item_data:
                continue
            item_id, aux_value = display_item_data
            data.append((crafting_type, item_id, aux_value))
        self.TypeTabIdAux = {}

        # 带上当前类型: 重排/刷新之后视图要停在原处, 而不是跳回第一页
        self.TypeNav.SetTypes(
            data, self.TYPE_TABS_PER_PAGE,
            key_of=lambda entry: entry[0],
            current_key=self.CurrentType or None)

    def UpdateTopLine1Label(self, crafting_type=None):
        """
        更新顶部第一行的 label 控件

        `crafting_type` 显式传入是给**逐个切换**用的：那时页面还没重建，
        `CurrentType` 仍是旧值，而类型名要立刻跟着按键走（见 StepType）。
        """
        # 和 tooltip、配方树同一个来源：不交键给标签自己本地化（别处在 Python 里查，一个名字就成了两条路）
        display_name = RecipeManager.GetDisplayText(crafting_type or self.CurrentType)
        self.TopLine1LabelControl.SetText(native_str(display_name))

    def UpdateTopLine2Label(self):
        """ 更新顶部第二行的 label 控件；这个类型的全表还在扫（查工作站的用途时），页码后面写「扫描中」"""
        page_index = "{}/{}".format(self.RecipesPage.current_page_number, self.RecipesPage.total_page)
        if self.CurrentType in self.ScanPending:
            page_index = RecipeText.Scanning.format(page_index)
        notice = getattr(self, "NoticeText", None)
        if notice:
            page_index = RecipeText.Notice.format(page_index, notice)
        self.TopLine2LabelControl.SetText(native_str(page_index))

    NOTICE_SECONDS = 3.0
    """ 点了 + 没成时，原因在页码后面挂几秒 """

    def ShowNotice(self, text):  # type: (unicode) -> None
        """ 页码后面挂一句话（点了 + 没成的原因），NOTICE_SECONDS 秒后节拍里收掉 """
        if not text:
            return
        # 第三方给的原因多半是 utf-8 字节串：先解开，不然挂着的这 3 秒里每次刷新页码都抛（在 #visible 回调里就带走了绑定）
        self.NoticeText = to_unicode(text)
        self.NoticeUntil = time.time() + self.NOTICE_SECONDS
        try:
            self.UpdateTopLine2Label()
        except Exception as e:  # noqa  页面还没建好时只是这次不显示
            logger.error("[MEI/ui] 配方页提示写不上: {}".format(error_text(e)))

    def ExpireNotice(self):  # type: () -> bool
        """ 节拍里调：提示到期了收掉、把页码写回去 """
        if self.NoticeText is None or time.time() < self.NoticeUntil:
            return False
        self.NoticeText = None
        self.UpdateTopLine2Label()
        return True

    def UpdateTypeTabsGrid(self):
        """ 更新合成方法选择网格 """
        types_data = self.TypeNav.PageItems
        max_type_tab = min(self.TYPE_TABS_PER_PAGE, len(types_data))
        self.TypeTabsGridControl.SetGridDimension((max_type_tab, 1))
        # grid 重建 -> 新控件停在默认态、且都还没被渲染过。两样都要重置：
        #   闩锁不重新武装 -> 新 grid 上没有一格会亮
        #   SeenTabIndex 不清 -> 会把新控件当成"已渲染过"而立刻去碰模板控件
        self.TypeTabToggleUpdated = False
        self.SeenTabIndex = set()
        self.TypeTabsGridReady = True
        # 这里不绑 type_tab.item_id_aux: 唯一调用方 UpdateRecipeUI 紧接着会绑一次并留下句柄,
        # 这里再绑一次、wrapper 又丢弃的话**解不掉**, 纯属泄漏 (recipe_ui_api.md §2.7-3).

    def UpdateStationItemsGrid(self):
        """
        更新工作站物品表的 ItemsGrid 控件。**工作站没变就什么都不动**（同一个类型翻页、换到工作站一样的类型）：
        不清面板、不推行列数 —— 翻页不重建控件、中间不清。变了才清面板；行列数只在变了时推（推过同一组就不推）。
        每次都清、每次都推的话：引擎收到行列数就重建格子，重建之前建好的面板把图标设在了旧控件上（SetUiItem 只设一次），
        新控件没有图标 —— 表现是「工作站有时候少一两个，普遍是第一个」。推了行列数的，ItemsGrid 之后逐轮核对图标、
        引擎说格子重新排列了就当场重设（这个 grid 的设置在 InitControls：不暂停绑定、核对 30 轮）
        """
        self.CraftingStationItems = RecipeManager.GetCraftingStations(self.CurrentType)
        keys = tuple(stack.get_key() for stack in self.CraftingStationItems or ())

        if not self.CraftingStationItems:
            rows, cols = 1, 0
        else:
            item_length = len(self.CraftingStationItems)
            rows = min(self.MainContentHeight // 20, item_length)
            cols = int(math.ceil(item_length / float(rows)))

        grid = self.StationItemsGridIns
        if grid is not None and keys == self.StationKeys and (cols, rows) == (self.StationItemsGridCols, self.StationItemsGridRows) \
                and grid.ItemPanels:
            self.StationItemsGridReady = True
            return

        self.StationItemsGridRows, self.StationItemsGridCols = rows, cols
        self.StationKeys = keys
        if grid is not None:
            grid.ClearItemPanels()
            grid.SetGridDimension(cols, rows, False)
        self.StationItemsGridReady = True

    def ClearRecipeUIScripts(self):
        """ 销毁配方 UI Script 实例 """
        for script_ins in self.RecipeUIScriptList:
            # 销毁已加载的UI Script实例（出错只记一行，不能拦住翻页、换类型）
            detach_script(script_ins)

    def UpdateRecipeUI(
            self,
            clear_ui_cache=True,
            update_page=False,
            set_ui_ready=True,
    ):
        """ 从页面数据更新配方 UI Script 实例"""
        if clear_ui_cache:
            self.ClearUICache()
        if update_page:
            self.RecipesPage = None
        self.UpdateRecipesGrid()
        if update_page:
            if self.BuildRecipesPage():
                # 翻到了要定位的那一页（最后一页可能不满）：行数按这一页的条数重推，不然多出几行空壳
                self.UpdateRecipesGrid()
            self.UpdateTopLine1Label()
            self.UpdateTypeTabsGrid()
        self.UpdateTopLine2Label()
        self.PrepareRecipeUIScript()
        self.UpdateStationItemsGrid()
        self.UpdateButtons()

        self.RecipeUIReady = set_ui_ready
        self.RebindTypeTabIdAux()

    TYPE_TAB_ID_AUX_BINDING = BindingConst.TypeTabItemIdAux
    TYPE_TAB_COLLECTION = "crafting_station_tab_grid"

    def RebindTypeTabIdAux(self):
        """
        重建 type_tab 的 item_id_aux 绑定, **幂等**.

        必须先解再绑: UpdateRecipeUI 每次都会走到这里, 而 ClearUICache 只在
        clear_ui_cache=True 时才解. 不先解的话, clear_ui_cache=False 那条路
        会让旧 wrapper 被字段覆盖后**再也解不掉** —— 又一条泄漏.
        """
        self.UnbindTypeTabIdAux()
        self.GetTypeTabIdAuxWrapper = self.Bindings.Bind(
            self.GetTypeTabIdAux, ViewBinder.BF_BindInt, self.TYPE_TAB_ID_AUX_BINDING, self.TYPE_TAB_COLLECTION)

    def UnbindTypeTabIdAux(self):
        """ 解绑并**清空句柄** —— 不清空的话重复调用会拿着废句柄反复解 """
        if self.GetTypeTabIdAuxWrapper:
            self.Bindings.Unbind(self.GetTypeTabIdAuxWrapper)
            self.GetTypeTabIdAuxWrapper = None

    def ClearUICache(self):
        """ 清理UI的一些缓存 准备 Update """
        self.RecipeUIReady = False
        self.RecipesGridReady = False
        self.StationItemsGridReady = False
        self.ClearRecipeUIScripts()

        self.RecipesGridBind.ClearCache()
        self.RecipeUIScriptList = []

        # 行控件会被重建, 动作按钮"上次推过的状态"缓存必须一并失效 ——
        # 不清的话新控件上是默认态, 而缓存以为"没变"就不会再推.
        if self.RecipeActionBind:
            self.RecipeActionBind.InvalidatePushCache()

        self.UnbindTypeTabIdAux()


    def BuildRecipesPage(self):
        """ 更新配方分页显示；有待定位的配方就翻到它所在的那一页。翻了页给 True """
        self.RecipesPage = BuildPage(self.CurrentRecipes, self.MaxRecipesInPage)
        focus, self.PendingFocusId = self.PendingFocusId, None
        if not focus:
            return False
        for index, recipe in enumerate(self.CurrentRecipes):
            if native_str(recipe_id(recipe)) == focus:
                size = self.RecipesPage.page_size
                start = (index // size) * size
                moved = start != self.RecipesPage.index
                self.RecipesPage.index = start
                return moved
        return False

    def PrepareRecipeUIScript(self):
        """ 准备配方 UI Script 实例 """
        # **每次重建配方页脚本都重新采一次物品状态** —— 这个点同时覆盖了
        # 开界面、切配方类型、翻页三种情况. 只在转移成功后失效的话, 表现是
        # "关掉整个界面再开才刷新".
        # 代价可控: 一次页面重建算一次, 而不是每帧 —— 每帧那条路仍然走缓存
        self.Craftable.Invalidate()
        self.RecipeUIScriptList = []
        recipes = self.RecipesPage.current_items
        cls = self.RecipeUIScriptCls
        if not cls:
            raise ValueError("RecipeUIScriptCls cannot be None")
        for recipe in recipes:
            # 构造也兜住：这里在 #visible 的绑定回调里跑，抛出去整条绑定被扔掉、整页都空（引擎结论 §15）
            self.RecipeUIScriptList.append(build_script(cls, recipe))

    def CreateRecipesGrid(self, control_def):
        """ 创建 RecipesGrid 控件 """
        if control_def != self.ControlDef:
            if self.RecipesGridControl:
                self.MainNode.RemoveChildControl(self.RecipesGridControl)
            self.MainNode.CreateChildControl(control_def, "recipes", self.MainContentControl, True)
            self.ControlDef = control_def

        self.TypeTabsGridReady = False

    def UpdateRecipesGrid(self):
        """ 更新 RecipesGrid 控件的属性 """
        self.UpdateRecipeHeight()
        self.RecipesGridControl = self.MainNode.GetUIControl(
            RecipeDetailsPath.Recipes, "grid")
        max_height = utilities.GetControlSizeInt(self.MainContentControl)[1] - 34 - 5
        recipe_height = self.RecipeHeight

        self.MaxRecipesInPage = max_height // recipe_height

        current_recipes = len(self.CurrentRecipes)
        current_page_recipe = len(self.RecipesPage.current_items) if self.RecipesPage else current_recipes
        max_items = self.MaxRecipesInPage

        recipes_in_page = min(current_page_recipe, current_recipes, max_items)

        self.RecipesGridControl.SetGridDimension((1, recipes_in_page))
        self.RecipesGridReady = True

    def UpdateRecipeHeight(self):
        """ 获取 recipe 控件的高度 用于后续计算显示数量 """
        recipe_control = self.MainNode.GetRootBaseUIControl(RecipeDetailsPath.FirstRecipe)
        if not recipe_control:
            return
        self.RecipeHeight = utilities.GetControlSizeInt(recipe_control)[1]

    def UpdateButtons(self):
        """ 更新按钮状态 """
        # 判据一律取**全局**数量: 逐个切换能跨页, 页内只剩一个不代表切不动。
        # 原先用 len(current_items) <= 1, 类型少时两者恰好相等所以没暴露 ——
        # 9 个类型时第 2 页只有 1 个, 那时按钮会被错误地禁用(recipe_ui_api.md §4.8)
        top_line1_enable = self.TypeNav.CanStep()
        top_overlay_enable = self.TypeNav.CanTurnPage()
        # 原先这里先设标志再无条件解引用, RecipesPage 为 None 时直接 AttributeError
        top_line2_enable = bool(self.RecipesPage) and self.RecipesPage.total_page > 1

        utilities.SetButtonEnable(self.TopOverlayPageUpBtn, top_overlay_enable)
        utilities.SetButtonEnable(self.TopOverlayPageDownBtn, top_overlay_enable)
        self.TopOverlayPageUpBtn.SetVisible(top_overlay_enable, False)
        self.TopOverlayPageDownBtn.SetVisible(top_overlay_enable, False)
        utilities.SetButtonEnable(self.TopLine1PageUpBtn, top_line1_enable)
        utilities.SetButtonEnable(self.TopLine1PageDownBtn, top_line1_enable)
        utilities.SetButtonEnable(self.TopLine2PageUpBtn, top_line2_enable)
        utilities.SetButtonEnable(self.TopLine2PageDownBtn, top_line2_enable)


# 事件的回调
# ======================================================================================================================
    def OnScreenSizeChanged(self, _):
        def __update():
            self.UpdateRecipeUI(clear_ui_cache=True, update_page=True)
        self.GameComp.AddTimer(0.1, __update)

    def OnMouseWheel(self, args):
        if WheelTaken():
            return  # 按着修饰键、正好有滚轮类的快捷键：这一下归快捷键（hotkeys/binds.py），不翻页
        if not self.RecipesPage or self.RecipesPage.total_page <= 1:
            return  # 只有一页：翻过去还是这一页，不必整页重建
        if self.__Covered():
            return  # 配方页被盖住了（从配方行开了配方树）：滚轮是上面那个界面的
        mouse_x, _ = utilities.GetMousePosInt()
        content_x, _ = utilities.GetControlPosInt(self.MainContentControl)

        if content_x < mouse_x < content_x + self.MainContentWidth:
            if args["direction"] == 1:
                self.RecipesPageDown()
            else:
                self.RecipesPageUp()

    def __Covered(self):  # type: () -> bool
        """ 配方页所在的界面不是当前界面（被 PushScreen 的界面盖住）；问不出来当没盖住 """
        current = ProxyManager.GetCurrentScreen()
        try:
            own = self.MainNode.GetScreenDef()
        except Exception:  # noqa
            return False
        return bool(current) and bool(own) and current != own

    def Close(self, _=None):
        """ 关闭配方界面；已经关过（+ 成交后排的下一拍关、紧接着又按了 ESC）就什么都不做 """
        if not getattr(self, "Created", False):
            return
        self.DestroyScript()
        # 物品栏、收藏栏改回避让原版内容，藏了的原版主内容显回来（core/node.py，代理参数 AllowChangeVisible）
        self.MainNode.OnRecipeDetailsClosed()
        self.MainNode.RemoveChildControl(self.MainNode.GetRootBaseUIControl(RecipeDetailsPath.Root))

    def RecipesPageUp(self, _=None):
        """ 对当前浏览的配方向上翻页 """
        self.RecipesPage.PageUp()
        self.UpdateRecipeUI()

    def RecipesPageDown(self, _=None):
        """ 对当前浏览的配方向下翻页 """
        self.RecipesPage.PageDown()
        self.UpdateRecipeUI()

    def CraftingItemPanelCallback(self, index):
        """ 工作站 ItemPanel 回调 """
        control = self.StationItemsGridIns.GetControlByIndex(index)
        if self.StationItemsGridReady:
            item_stack = utilities.GetVerticalRightLeftItem(
                index, self.StationItemsGridRows, self.StationItemsGridCols, self.CraftingStationItems
            )

            if item_stack:
                return ItemPanel.from_item_stack(control, item_stack)

        return ItemPanel.from_empty(control)

    def TypeTabToggleCallback(self, args):
        if not self.TypeTabsGridReady:
            return
        index = args["index"]
        if not args["state"]:
            # 取消选中不代表要切类型: 那是把上一个亮着的 tab 熄掉时的必然产物
            return

        # **回灌防护**: SyncTypeTabToggle 推下去的 SetToggleState 会被引擎当成
        # 一次状态变化, 下一帧把 ToggleChanged 送回来(引擎结论 §10)。
        #
        # 判据取「它是不是已经是当前选中项」, **不要**换成"比对上次推下去的值":
        # 那种判据依赖一张会被 UpdateTypeTabsGrid 清空的表, 而推送与回灌之间隔了一帧
        # —— 中间被清掉的回灌就伪装成玩家点击, 走进 ShowRecipeDetails,
        # update_page=True 把 RecipesPage 重建, **配方页码弹回第 1 页**,
        # 表现是"配方翻页翻不动"。
        #
        # 本判据不依赖任何缓存, 且顺带把"重复点击已选中的 tab"变成无事发生
        # —— 那本来也不该重建整个配方页。
        if index == self.TypeNav.PageIndexOfSelected():
            return

        type_data = self.TypeNav.SelectByPageIndex(index)
        if not type_data:
            return
        self.ShowRecipeDetails(type_data[0])

    TYPE_TAB_FALLBACK_ID_AUX = 131072
    """ 问不到 id_aux 时的兜底。**只用于这一帧的返回值，不写进缓存** """

    def GetTypeTabIdAux(self, index):
        """
        获取合成方式标签显示的 IdAux。**每帧路径**

        ⚠ 本方法是**图标绑定的回调**：它一旦抛异常，引擎就拿不到值、
        回落到 property_bag 里的 `#item_id_aux: 131072`（那个草方块）。
        所以推 toggle 的失败**绝不能冒泡到这里**（引擎结论 §15）。
        """
        if not self.TypeTabsGridReady:
            return 0
        types_data = self.TypeNav.PageItems
        if index < 0 or index >= len(types_data):
            return 0

        id_aux = self.ResolveTypeTabIdAux(types_data[index])
        # 顺带把选中态推下去。**放在算完 id_aux 之后**，且自身不抛
        self.SyncTypeTabToggle(index)
        return id_aux

    def ResolveTypeTabIdAux(self, type_data):  # type: (tuple) -> int
        """
        解析 tab 图标的 id_aux，**取到才缓存**

        引擎对某些方块(尤其第三方的)在开页那一刻答不上来，过一会儿就好了。
        兜底值不进缓存，所以下一帧会继续问，不必关掉界面重开。
        """
        crafting_type = type_data[0]
        cached = self.TypeTabIdAux.get(crafting_type)
        if cached:
            return cached
        try:
            basic_info = self.ItemComp.GetItemBasicInfo(type_data[1], type_data[2])
            id_aux = basic_info.get("id_aux") if basic_info else None
        except Exception:  # noqa  这是每帧路径, 问不到就下一帧再问, 不刷日志
            id_aux = None
        if not id_aux:
            return self.TYPE_TAB_FALLBACK_ID_AUX
        self.TypeTabIdAux[crafting_type] = id_aux
        return id_aux

    def SyncTypeTabToggle(self, index):
        """
        让选中的那一格亮起来。**每次 tab 网格重建后只推一次，且只推 True**

        为什么**只推 True、不去熄灭别的**：这些 tab 是一个单选组
        （`recipe_details.json` 的 `tab_toggle` 带 `$radio_toggle_group: true`），
        「同时只有一个亮」由**引擎按 `$toggle_name` 自己保证**。
        往单选成员推 `False` 是在和它抢方向盘 —— 后果是
        **五个 tab 全亮**，而全亮之后点击不产生状态跃迁、引擎根本不投递
        `ToggleChanged`，于是"点一下都不会变"。

        为什么还需要 Python 推这一次：`$toggle_state_binding_name` 指向
        `#netease_editor_template_namespace.toggle_state`（没人提供的占位名），
        状态绑定是惰性的，外观只认 `SetToggleState()`（引擎结论 §10）。

        闩锁在 `UpdateTypeTabsGrid` 里重新武装 —— 那个粒度恰好对：
        grid 一重建（开页 / 切类型 / 翻页）就该重新同步一次。

        **本方法永不抛。** 它挂在图标绑定的回调里，抛出去就把图标一起弄没了。
        """
        if self.TypeTabToggleUpdated:
            return
        # 选中项不在当前页时一个都不推 —— grid 重建后本来就都是灭的, 那正是对的
        if index != self.TypeNav.PageIndexOfSelected():
            return

        # 先让这一格至少被引擎渲染过一轮再碰它。grid 子控件首次渲染前不可访问
        # (引擎结论 §5)，而此刻拿到的很可能是**模板控件** —— 对模板做 screen action
        # 正是那条 "Template controls shouldn't be doing anything with screen actions" 断言。
        if index not in self.SeenTabIndex:
            self.SeenTabIndex.add(index)
            return

        try:
            item = self.TypeTabsGridControl.GetGridItem(index, 0)
            if not item:
                return
            toggle = item.asSwitchToggle().GetChildByPath("/toggle")
            if not toggle:
                return
            toggle.asSwitchToggle().SetToggleState(True)
        except Exception:  # noqa  控件还没就绪, 下一帧再来 —— 但不能带走图标
            return
        self.TypeTabToggleUpdated = True

    # 类型导航 —— 算术全在 modules/typetab.py, 这里只负责推控件
# ======================================================================================================================
    def TypeTabPageUp(self, _=None):
        """ tab 条翻到下一页。**不换选中的类型** —— 玩家只是想看看有什么 """
        if self.TypeNav.PageUp():
            self.RefreshTypeTabs()

    def TypeTabPageDown(self, _=None):
        if self.TypeNav.PageDown():
            self.RefreshTypeTabs()

    def TypeStepNext(self, _=None):
        """ 逐个切到下一个类型；到末尾循环回开头，跨页时 tab 条自动跟过去 """
        self.StepType(1)

    def TypeStepPrev(self, _=None):
        self.StepType(-1)

    def StepType(self, delta):  # type: (int) -> None
        """
        逐个切类型。**选中态立刻改，重建页面推迟到下一帧并合并**

        为什么要合并（不合并的话连按时 tab 与配方明显不同步）：
        两边走的是**两棵不同的控件树**，帧数天然不等 ——

          · tab 条的 grid 不会被销毁，绑定下一帧就重算 ⇒ 约 1 帧；
          · 配方列表的 grid **每次换类型都被销毁重建**（每个类型的 control_def 都不同），
            新控件要先渲染一轮、绑定才触发，再跑 UpdateRecipeUI、再渲染 ⇒ 若干帧。

        连按时每一下都排一次完整的销毁+重建，堆积起来就是"tab 已经跑远了、
        配方还在追"。合并之后连按 N 次只重建一次，中间那些类型根本不需要建出来。

        **不是把 tab 拖慢去迁就配方** —— 那只会让整个交互都变钝。
        """
        type_data, _page_changed = self.TypeNav.Step(delta)
        if not type_data:
            return
        # 先把便宜的即时反馈给出去: 类型名跟着按键走, 手感不打折
        self.UpdateTopLine1Label(type_data[0])
        self.ScheduleShowRecipeDetails(type_data[0])

    def ScheduleShowRecipeDetails(self, crafting_type):  # type: (str) -> None
        """ 把重建推迟到下一帧，并**取消上一个还没跑的** —— 连按只重建最后那次 """
        self.CancelPendingSwitch()

        def __switch():
            self.PendingSwitchTimer = None
            # 期间玩家可能又按了几下, 以 TypeNav 的最终选中项为准而不是排队时那个
            current = self.TypeNav.Current
            self.ShowRecipeDetails(current[0] if current else crafting_type)

        self.PendingSwitchTimer = self.GameComp.AddTimer(0.0, __switch)

    def RefreshTypeTabs(self):
        """ 只重画 tab 条本身（翻页用），不动配方列表 """
        self.UpdateTypeTabsGrid()
        self.UpdateButtons()
        self.RebindTypeTabIdAux()

    def GetRecipeVisible(self, index):
        """
        配方行的可见性（每帧拉）。这一行的格子被拉到了、脚本还没接：**当场接上** ——
        翻页、换类型时新脚本在同一轮拉绑定里接上，这一行的格子绑定紧跟着就拿到新值：物品格直接覆盖，中间没有一帧空白、不闪。
        推到下一帧的 Tick 再接的话，中间那一帧格子的绑定找不到这一行、只能回缺省值（藏起来），翻页就闪。
        接的时候出错只丢这一行（modules/host.attach_script 接住异常、记一行），所以这条 #visible 不会被引擎扔掉（引擎结论 §15）；
        绑定器只在第一次见到某个绑定前缀时才向引擎注册绑定（RecipesGridBind.AddGroup），翻页、换类型只改 Python 这边的表
        """
        if not self.RecipeUIReady:
            return True

        if not self.RecipesGridReady:
            self.UpdateRecipeUI(clear_ui_cache=False, update_page=True)

        if index < len(self.RecipeUIScriptList):
            script_ins = self.RecipeUIScriptList[index]
            if script_ins._Created:  # noqa
                return True
            grid = self.RecipesGridControl
            recipe_control = grid.GetChildByPath("/recipe{}".format(index + 1)) if grid is not None else None
            if recipe_control is None:
                # 格子还没渲染出来（grid 子控件首次渲染前取不到，引擎结论 §5）：这条绑定是 always，下一帧还会来。
                # 不守这一下就是把 None 交给 OnCreate（第三方的配方页，比如蔚蓝的电力槽，会撞上这条时序）
                return True
            if attach_script(script_ins, index, self.RecipesGridBind, recipe_control):
                # **立刻画第 0 帧** —— 不然这一行会有最长 0.4 秒停在布局初值上
                self.PrimeAnimTick(script_ins)
        return True
