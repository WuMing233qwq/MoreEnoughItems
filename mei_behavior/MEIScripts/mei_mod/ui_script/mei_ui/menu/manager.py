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
触屏的二级菜单（docs/architecture/tooltip.md §6、§6.14）：点一下格子，出「这一格的信息 + 这一格能做的事」。一个界面一份，
挂在主节点上（UIMainNode.OnCreate 建、OnDestroy 拆，紧跟在 tooltip 管理器后面）。

  · 菜单就是 tooltip 的移动端宿主：内容由 TooltipManager 建（设置开着、格子有 TooltipContent → 配方预览 / 接受物品；
    否则只有标题 —— 设置关着时菜单照出），框里别的东西由这里填；
  · **信息卡 + 图标操作条**（扁平风，tooltip.md §6.14）：顶栏（物品图标、种类、关闭的小 x）、内容（和 PC 的 tooltip 一模一样）、
    分隔线、多候选格的翻页行（‹ 2 / 86 ›）、一排等宽的大按钮（图标在上、短字在下）；操作条放不下的、不常用的收进「更多」，
    点一下在下面展开两列文字按钮，再点收起。收藏格的数量写在顶栏的种类后面（「收藏 · 物品  ×2」），−1 / +1 在操作条上。
    框里每样东西的位置由 menu.layout.card_layout 算，tooltip 管理器摆框时调 Layout；「更多」展开 / 收起后让它当场重摆（Relayout）；
  · 落位：不贴着点的那一格，摆在格子所在区域的外侧 —— 物品栏的格子摆在物品栏左边、收藏栏的摆在右边、
    配方页的摆在配方页右边，竖直方向跟着那一格；连续浏览时不挡着区域里的格子。放不下照旧贴屏幕边兜底（TooltipManager）；
  · 按钮：操作条 bar_0 … bar_5、「更多」里的 button_0 … button_15、翻页行的 icon_prev / icon_next，都是 JSON 里静态的按钮，
    按这一格的动作填前几个，其余藏起来；「关闭」是顶栏的小 x，不占位置。点击走 button_mappings → 固定名字的 BF_ButtonClickUp 绑定
    （MenuConst.BarName / ButtonName / IconName / CloseName，只能单个绑定，引擎结论 §9）；
  · 点格子、点按钮都是在绑定回调里来的：只记下，下一帧（界面代理的 OnTick → Update）再开 / 再执行 —— 绑定回调里不建控件（§27-2）；
  · 手指划进一格：tooltip 管理器认出「移进」后调 Hover，同一帧打开，不检测移出；已经是它的菜单不动。
    菜单是这次触摸划进时开的，松手那一下的点击不当成「再点一下同一格」收起（按住多久都一样）；本来就开着它的，照旧收起；
  · 有的动作点了不收（−1 / +1、上移下移、换候选、「更多」）：改收藏的那几样一改，收藏栏重排、格子全是新的 —— 先让 tooltip 放掉归属，
    下一帧找到显示同一条收藏的新格子再挂上（跟着这一条走，「更多」展没展开照旧）；删除整组要点两下（第一下按钮变成「确认删除？」）；
  · 多候选格：打开时停下轮播（看着的东西别自己变），收起时接着轮播；点接受物品列表里的一格 = 选中那个候选；
  · 收起：点「关闭」、点了动作、点别的格子（换成那一格）、再点一下同一格；那一格被拆了、换了内容（翻页、切页签、搜索）
    由 TooltipManager 收（它记着显示时的 ContentKey），这里看到它收了就跟着清；点空白处不收；
  · 复位（界面状态跨开关存活，§22）：开界面时框里每个控件的显隐、文字、遮罩、底图都写一遍，每次打开再按这一格两个方向写一遍
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.texts import MenuKindText
from MEIScripts.constants.ui import (
    ItemsBrowserPath, ItemsSidebarPath, MenuConst, MenuKey, RecipeDetailsPath, TooltipPath, UiPathConst,
)
from MEIScripts.mei_mod.state.bookmarks import entry_identity
from MEIScripts.mei_mod.ui_script.controls.item.panel import render_args
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import full_size, mark_dirty, show_later
from MEIScripts.mei_mod.ui_script.mei_ui.menu.actions import (
    ACTIONS, SECTION_CANDIDATE, SECTION_COUNT, SECTIONS, MenuTarget, actions_for, kind_of, mute, split_bar,
)
from MEIScripts.mei_mod.ui_script.mei_ui.menu.layout import (
    BAR_LIMIT, CARD_CLOSE_OFFSET, CLOSE_SIZE, DIVIDER_H, ICON_SIZE, TEXT_H, bar_width, button_width, card_layout,
    number_width, real_width,
)
from MEIScripts.mei_mod.ui_script.mei_ui.menu.ruler import TextRuler
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import DescribeItem
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.layout import SIDE_LEFT, SIDE_RIGHT
from MEIScripts.utils import utilities
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text, native_str, to_unicode

ViewBinder = clientApi.GetViewBinderCls()

REGIONS = (
    (RecipeDetailsPath.Screen, RecipeDetailsPath.ContentPanel, SIDE_RIGHT),
    (ItemsBrowserPath.Root, ItemsBrowserPath.Root, SIDE_LEFT),
    (ItemsSidebarPath.Root, ItemsSidebarPath.Root, SIDE_RIGHT),
)
"""
格子长在哪个区域里（第一项）→ 菜单摆在哪个控件（第二项）的哪一边：配方页的格子摆在配方页右边；
物品栏在屏幕右边，摆在它左边；收藏栏在左边，摆在它右边 —— 都朝着屏幕中间。配方页排最前：它盖在物品栏上面
"""

FOLLOW_TICKS = 15
""" 改完收藏后找显示同一条收藏的新格子，最多找这么多帧（约 0.5 秒）；挪到别的页了、找不到就收起 """

CLOSE = "close"
""" 点了顶栏的「关闭」（和按钮的下标分开记）"""

BAR = "bar"
POOL = "pool"
ICON = "icon"
""" 动作摆在哪：操作条（第几个）、「更多」里的文字按钮（第几个）、翻页行的图标按钮（MenuAction.Icon 的槽名）"""


def menu_title(panel):  # type: (any) -> any
    """
    只有标题时写什么：这一格**完整的悬停文字** —— 物品自带的那几行（附魔、属性…）加格子追加的说明（SetLore，比如工具要求、
    「收藏配方」），和 PC 上原版悬停文字一样（只写物品名会丢掉那几行）。失效的收藏格就是「已失效: …」那一行。
    格子还没算过悬停文字才退回物品名
    """
    text = getattr(panel, "ItemHoverText", None)
    if text:
        return text
    item = getattr(panel, "Item", None)
    return to_unicode(DescribeItem(item)) if item is not None else u""


def icon_render(panel):  # type: (any) -> tuple or None
    """
    顶栏物品图标给渲染器的四样（render_args）：格子自己的那一叠（带附魔、userData）对得上它现在的物品就用它，
    不然（多候选格换了候选、原版格子的替身没有 Stack）按物品现造一个；没有物品给 None
    """
    item = getattr(panel, "Item", None)
    if item is None:
        return None
    try:
        stack = getattr(panel, "Stack", None)
        if getattr(stack, "Item", None) is not item or not callable(getattr(stack, "get_render_data", None)):
            make = getattr(item, "stack", None)
            stack = make(1) if callable(make) else None
        data = getattr(stack, "get_render_data", None)
        return render_args(data()) if callable(data) else None
    except Exception as e:  # noqa  取不到就不画图标
        logger.warn("[MEI/menu] 取不到物品图标: {}".format(error_text(e)))
        return None


def button_path(index):  # type: (int) -> str
    return TooltipPath.MenuButton.format(index)


def bar_path(index):  # type: (int) -> str
    return TooltipPath.MenuBar.format(index)


def number_path(index):  # type: (int) -> str
    return TooltipPath.MenuNumber.format(index)


def icon_path(name):  # type: (str) -> str
    return TooltipPath.MenuIcon.format(name)


def plan_slots(actions, limit=min(BAR_LIMIT, MenuConst.BarSize)):  # type: (list, int) -> tuple
    """
    每个动作摆在哪，返回 (动作, 位置) 两张一一对应的表，动作按「操作条、更多、翻页行」排：
      · 带 Icon、而且有这个图标按钮（MenuConst.Icons）的去翻页行（一个槽只给第一个认领的）；
      · 其余按 split_bar 分：常用的上操作条，放不下的、不常用的进「更多」—— 有进「更多」的，操作条最后加一个「更多」按钮；
    位置是 (BAR, 第几个) / (POOL, 第几个) / (ICON, 槽名)
    """
    icons, rest, used = [], [], set()
    for action in actions:
        icon = getattr(action, "Icon", None)
        if icon in MenuConst.Icons and icon not in used:
            used.add(icon)
            icons.append(action)
        else:
            rest.append(action)
    bar, more = split_bar(rest, limit)
    if more:
        bar = bar + [ACTIONS[MenuKey.More]]
    ordered = bar + more + icons
    slots = [(BAR, index) for index in range(len(bar))] + [(POOL, index) for index in range(len(more))] \
        + [(ICON, action.Icon) for action in icons]
    return ordered, slots


def follow_key(cell):  # type: (any) -> tuple
    """ 跟着走认的是哪一条收藏：条目身份 + 角色（同一条配方展开后有产物格、原料格）"""
    return entry_identity(cell.Entry), cell.Role


def menu_region(main, panel):  # type: (any, any) -> tuple
    """ 这一格在哪个区域里：(区域的全局矩形, 首选的一侧)；不在这几个区域里给 (None, None)，菜单就摆在格子旁 """
    control = getattr(panel, "Control", None)
    if control is None:
        return None, None
    try:
        path = control.GetPath()
    except Exception:  # noqa  格子刚被拆
        return None, None
    for member_path, rect_path, side in REGIONS:
        member = main.GetUIControl(member_path)
        if member is None:
            continue
        try:
            if path.startswith(member.GetPath() + "/"):
                region = utilities.GetControlRectSize(main.GetUIControl(rect_path) or member)
                return narrow_region(region, row_span(main, panel), side), side
        except Exception:  # noqa  区域控件不在了：当它不是
            continue
    return None, None


def row_span(main, panel):  # type: (any, any) -> tuple or None
    """ 这一格那一行露出来的那一段（UIScriptMain.RowSpan）；主节点没有这个入口（配方树的壳）给 None """
    finder = getattr(main, "RowSpan", None)
    return finder(panel) if finder is not None else None


def narrow_region(region, span, side):  # type: (tuple, tuple or None, str) -> tuple
    """
    菜单靠着的那条边换成这一行露出来的边（物品栏、收藏栏被原版界面挡住的格子是空着的）：菜单摆在 side 那一侧，
    就把区域那一侧的边挪到这一行能显示东西的那一段的边上 —— 收藏栏这一行只露出两格，菜单就贴着第二格，
    不贴整栏的右边；只看这一行，下面的行露得多、会被菜单盖住几格，不管。纯函数（探针测）
    """
    if span is None:
        return region
    (left, top), (right, bottom) = region
    (span_left, _), (span_right, _) = span
    if side == SIDE_RIGHT:
        return (left, top), (min(right, span_right), bottom)
    return (max(left, span_left), top), (right, bottom)


class TouchMenu(object):

    def __init__(self, main_node, tooltip):
        self.MainNode = main_node
        self.Tooltip = tooltip
        self.Bindings = ScreenBinder(main_node.ScreenNode)  # type: ScreenBinder
        self.Target = None  # type: MenuTarget or None  # 开着的菜单是给哪一格的
        self.Actions = []  # type: list  # 这一格的动作：操作条、「更多」、翻页行（不含「关闭」，它在顶栏）
        self.Slots = []  # type: list  # 每个动作摆在哪：(BAR, 第几个) / (POOL, 第几个) / (ICON, 槽名)，见 plan_slots
        self.More = False  # type: bool  # 「更多」展开着没有：打开别的格子时收起，跟着这一条收藏走时照旧
        self.__Wrappers = []  # type: list  # 挂上的点击绑定，关界面时解绑
        self.__Pending = None  # type: tuple or None  # (哪一格, 点的还是划进的)：Update 里打开；点的再点一下同一格是收起
        self.__Touch = None  # type: tuple or None  # 最近一次划进：(那一格, 划进时菜单是不是已经开着它)，认松手那一下的点击
        self.__Click = None  # type: any  # 点了哪个按钮：(BAR / POOL, 第几个) / (ICON, 槽名) / CLOSE，下一帧执行
        self.__Armed = None  # type: int or None  # 要二次确认的动作点过第一下：它在 Actions 里的位置
        self.__Seek = None  # type: tuple or None  # 改完收藏在找新格子：(跟着的那一条, 找了几帧)
        self.__Written = {}  # type: dict  # 写过的显隐、字、位置、大小、底图、颜色（(路径, 哪一样) -> 值）：一样的不再碰引擎
        self.__Ruler = None  # type: TextRuler or None  # 量字宽（ruler.py）：第一次用到才取覆盖层里那排 label
        self.__Refine = False  # type: bool  # 排的时候有字还没量（照估的宽排了）：量好了重排一次

    def OnCreate(self):
        """ 开界面：复位框里的控件（两个方向都写，§22），挂点击绑定 """
        self.__Pending = None
        self.__Touch = None
        self.__Click = None
        self.__Clear()
        self.__ResetPool()
        self.__Bind()

    def OnDestroy(self):
        self.__Unbind()
        self.__Pending = None
        self.__Touch = None
        self.__Click = None
        self.__Clear()
        self.__Ruler = None
        self.__Refine = False

    def Ruler(self):  # type: () -> TextRuler
        """ 量字宽：这个主节点覆盖层里那排看不见的 label（mei_common.text_ruler），第一次用到才取（那时覆盖层建好了）"""
        if self.__Ruler is None:
            self.__Ruler = TextRuler(self.MainNode.GetUIControl, UiPathConst.Ruler)
        return self.__Ruler

    def MeasureTexts(self):  # type: () -> list
        """ 这一份菜单排版要量的字：顶栏的种类、操作条与「更多」里每个按钮会写的字、翻页行的数字 —— Layout 按字算宽的就是这几样 """
        target = self.Target
        if target is None:
            return []
        texts = [self.KindText(), self.PagerValue()]
        for action, (kind, _) in zip(self.Actions, self.Slots):
            if kind == BAR:
                texts.extend(action.BarWidthLabels(target))
            elif kind == POOL:
                texts.extend(action.WidthLabels(target))
        return [text for text in texts if text]

    def Measured(self):  # type: () -> bool
        """ 要用的字量好了没有：tooltip 管理器显示菜单前问它（量好了再摆，第一眼就是按真宽排的）"""
        return self.Ruler().Ready(self.MeasureTexts())

    def IsOpen(self):  # type: () -> bool
        return self.Target is not None

    # 入口：都是在绑定回调里来的，只记下
# ======================================================================================================================
    def Request(self, panel):
        """ 触屏点了一格（ItemPanel.OpenTouchMenu）：下一帧打开；再点一下同一格是收起 """
        if panel is not None:
            self.__Pending = (panel, True)

    def Hover(self, panel):
        """
        触屏手指划进了这一格（TooltipManager 认的「移进」）：开它的菜单 —— tooltip 管理器排在前面，同一帧就开；
        已经是它的菜单就不动（不像点击那样收起）；没有可做的事（空格子）不开。
        手指按下时先亮 hover、松手才来点击：记下这次触摸开始时菜单是不是已经开着这一格，松手那一下的点击照它算（__ClickCloses）
        """
        ask = getattr(panel, "MenuActions", None)
        if panel is None or not callable(ask) or not ask():
            return
        already = self.Target is not None and self.Target.Panel is panel
        self.__Touch = (panel, already)
        if not already:
            self.__Pending = (panel, False)

    def OnButton(self, key):  # type: (any) -> None
        """ 点了按钮：(BAR / POOL, 第几个) / (ICON, 槽名) / 顶栏的关闭（CLOSE）—— 下一帧执行 """
        self.__Click = key

    # 每帧（界面代理的 OnTick，排在 tooltip 管理器后面）
# ======================================================================================================================
    def Update(self):
        """ 出错只记日志 —— 这里抛出去会带走同一帧别的代理 """
        try:
            if self.__Ruler is not None:
                self.__Ruler.Tick()
            if self.Target is not None and not self.Tooltip.IsVisible():
                # tooltip 管理器那边收起了（那一格被拆了、换了内容）：菜单跟着清
                self.__Clear()
            if self.__Refine and (self.Target is None or self.Measured()):
                # 亮着的时候换了字（翻候选、改数量、原地换一格），有的还没量：量好了照真宽重排一次
                self.__Refine = False
                if self.Target is not None:
                    self.Tooltip.Relayout()
            if self.__Seek is not None:
                self.__Follow()
            click, self.__Click = self.__Click, None
            if click == CLOSE:
                self.Close()
            elif click is not None:
                index = self.__ActionAt(click)
                if index is not None:
                    self.__Run(index)
            pending, self.__Pending = self.__Pending, None
            if pending is not None:
                self.__Open(*pending)
        except Exception as e:  # noqa
            logger.error("[MEI/menu] 每帧处理失败: {}".format(error_text(e)))

    def Close(self):
        if self.Target is not None:
            self.Tooltip.Hide()
        self.__Clear()
        self.__Touch = None

    # 打开、执行
# ======================================================================================================================
    def __Open(self, panel, toggle=True):
        if self.Target is not None and self.Target.Panel is panel:
            if toggle and self.__ClickCloses(panel):
                self.Close()  # 再点一下同一格：收起
            return
        if self.Tooltip.IsInside(panel):
            self.__PickCandidate(panel)
            return
        if getattr(panel, "Destroyed", False):
            return
        actions, slots = plan_slots([action for action in actions_for(panel)
                                     if action.Key not in (MenuKey.Close, MenuKey.More)])
        pool = [index for index, slot in enumerate(slots) if slot[0] == POOL and slot[1] >= MenuConst.PoolSize]
        if pool:
            logger.warn("[MEI/menu] 这一格有 {} 个动作要收进「更多」，只放得下 {} 个，多的不出".format(
                MenuConst.PoolSize + len(pool), MenuConst.PoolSize))
            actions = [action for index, action in enumerate(actions) if index not in pool]
            slots = [slot for index, slot in enumerate(slots) if index not in pool]
        if self.Target is not None and self.__Seek is None and (
                self.Tooltip.RetitleFor(panel, menu_title(panel)) or self.Tooltip.SwapRecipeFor(panel)):
            # 同一种内容原地换（只有标题 §6.17、同一类型的配方预览 §6.19）：框不收起、不变透明，字、按钮、位置当场换成新格子的
            self.__Clear()
            self.__HoldRotation(panel)
            self.Target = MenuTarget(self.MainNode, panel)
            self.Actions = actions
            self.Slots = slots
            region, side = menu_region(self.MainNode, panel)
            self.Tooltip.SetTouchRegion(region, side)
            self.Tooltip.SetTouchLayout(self.Layout, self.Measured)
            self.__Fill()
            self.Tooltip.Relayout(measure=True)
            return
        self.__Clear()
        self.__HoldRotation(panel)
        if not self.__ShowContent(panel):
            self.__ResumeRotation(panel)
            return
        self.Target = MenuTarget(self.MainNode, panel)
        self.Actions = actions
        self.Slots = slots
        region, side = menu_region(self.MainNode, panel)
        self.Tooltip.SetTouchRegion(region, side)
        self.Tooltip.SetTouchLayout(self.Layout, self.Measured)
        self.__Fill()
        self.Ruler().Request(self.MeasureTexts())  # 内容透明着建的这几帧里先量上，显示前（Measured）多半已经量好

    def __ClickCloses(self, panel):  # type: (any) -> bool
        """
        点了菜单开着的那一格，收不收。最近一次划进的就是这一格：看那次触摸开始时菜单开没开着它 ——
        没开着（菜单是这次触摸划进时开的），这一下是同一次触摸松手来的点击，不收（按住多久都一样）；开着就是再点一下，收。
        没有这一格的划进记录（点开的，或真机上没有 hover）照旧再点一下就收。记录用一次就清
        """
        touch, self.__Touch = self.__Touch, None
        if touch is None or touch[0] is not panel:
            return True
        return touch[1]

    def __ShowContent(self, panel):  # type: (any) -> bool
        """ 设置开着、格子有 TooltipContent → 配方预览 / 接受物品（ShowFor 自己判断）；否则只有标题（普通格子、设置关着）"""
        tooltip = self.Tooltip
        if tooltip.ShowFor(panel):
            return True
        return tooltip.ShowTitleFor(panel, menu_title(panel))

    def __PickCandidate(self, panel):
        """
        点的是菜单内容里的格子（接受物品列表、配方预览）：不开新菜单 —— 开新菜单要先收起现在的内容，会连带把这一格拆掉。
        接受物品列表里的一格 = 在多候选格里选中这个候选（标题、图标、「来源 / 收藏」、翻页行的数字跟着换）；配方预览里的格子不做事
        """
        target = self.Target
        index = self.Tooltip.CandidateIndexOf(panel)
        if target is None or index is None or not callable(getattr(target.Panel, "Select", None)):
            return
        self.__Armed = None
        target.Panel.Select(index)
        self.__Fill()

    def __ActionAt(self, key):  # type: (tuple) -> int or None
        """ 点到的按钮对应 Actions 里第几个动作；没对上（菜单换了、那个按钮没在用）给 None """
        for index, slot in enumerate(self.Slots):
            if slot == key:
                return index
        return None

    def __Run(self, index):
        target, actions = self.Target, self.Actions
        if target is None or self.__Seek is not None or not 0 <= index < len(actions):
            return  # 还在找新格子：这一下按旧格子算会点错条目，不做
        action = actions[index]
        if action.Key == MenuKey.More:
            self.__Armed = None  # 收起「更多」时二次确认一起作废
            self.More = not self.More
            self.__Fill()
            self.Tooltip.Relayout()  # 框变高了 / 变矮了：当场重排、重摆（贴边按新尺寸算）
            return
        if not action.IsEnabled(target):
            return
        if action.Confirm and self.__Armed != index:
            self.__Armed = index  # 要点两下：第一下按钮变成「确认删除？」
            self.__Fill()
            return
        self.__Armed = None
        if not action.Keep:
            self.Close()
        elif action.Follow and target.Cell is not None:
            self.__Seek = (follow_key(target.Cell), 0)
            self.Tooltip.Release()
        try:
            action.Run(target)
        except Exception as e:  # noqa
            logger.error("[MEI/menu] 动作 {} 失败: {}".format(action.Key, error_text(e)))
        if action.Keep and self.__Seek is None and self.Target is target:
            self.__Fill()  # 点了不收、格子也没换（换候选）：字、遮罩、图标、翻页行的数字可能变了

    def __Follow(self):
        """ 改完收藏后，找显示同一条收藏的新格子挂上去；找了 FOLLOW_TICKS 帧还没有（挪到别的页、没了）就收起 """
        key, ticks = self.__Seek
        panel = self.__FindBookmarkPanel(key)
        if panel is None:
            if ticks + 1 >= FOLLOW_TICKS:
                self.__Seek = None
                self.Close()
            else:
                self.__Seek = (key, ticks + 1)
            return
        self.__Seek = None
        self.Target = MenuTarget(self.MainNode, panel)
        if not self.Tooltip.Adopt(panel):
            self.Close()
            return
        self.__Fill()

    def __FindBookmarkPanel(self, key):  # type: (tuple) -> any
        sidebar = getattr(self.MainNode, "ItemsSidebarIns", None)
        grid = getattr(sidebar, "BookmarksGridIns", None) if getattr(sidebar, "Inited", False) else None
        for panel in (getattr(grid, "ItemPanels", None) or {}).values():
            cell = getattr(panel, "Cell", None)
            if cell is not None and not getattr(panel, "Destroyed", False) and follow_key(cell) == key:
                return panel
        return None

    # 多候选格的轮播：看着的东西别自己变
# ======================================================================================================================
    @staticmethod
    def __HoldRotation(panel):
        if callable(getattr(panel, "ResumeRotate", None)) and len(getattr(panel, "Candidates", None) or ()) > 1:
            panel.Select(panel.CurrentIndex)

    @staticmethod
    def __ResumeRotation(panel):
        if panel is not None and not getattr(panel, "Destroyed", False) and callable(getattr(panel, "ResumeRotate", None)):
            panel.ResumeRotate()

    # 框：排版（摆在哪）由 tooltip 管理器摆框时调 Layout；字、图标、遮罩、显隐由 __Fill 写
# ======================================================================================================================
    def KindText(self):  # type: () -> any
        """ 顶栏写的种类：面板的 MenuKind()；有数量的收藏格后面跟着「×2」（−1 / +1 在操作条上，数字看这里）"""
        target = self.Target
        if target is None:
            return u""
        kind = kind_of(target.Panel)
        if any(action.Section == SECTION_COUNT for action in self.Actions):
            value = SECTIONS[SECTION_COUNT].ValueFor(target)
            if value:
                return MenuKindText.Counted.format(to_unicode(kind), to_unicode(value))
        return kind

    def PagerValue(self):  # type: () -> any
        """ 翻页行中间写的：第几个候选「2 / 86」；没有翻页行给 None """
        if self.Target is None or not any(slot[0] == ICON for slot in self.Slots):
            return None
        return SECTIONS[SECTION_CANDIDATE].ValueFor(self.Target)

    def Layout(self, content_size):  # type: (tuple) -> tuple
        """
        tooltip 管理器摆菜单时调（显示那一刻、内容尺寸变了、挂到新格子上、「更多」展开 / 收起）：按内容尺寸排好框里的每样东西，
        返回框的尺寸。位置、尺寸都由这里写（绝对定位）；按钮改宽写尺寸规则（full_size：底、遮罩是 100% 跟着变，图标、字跟着锚点走）。
        字宽按量的算（ruler.py）；有字还没量（亮着的时候换了字）先照估的宽排，量好了 Update 里重排一次
        """
        if not self.Ruler().Request(self.MeasureTexts()):
            self.__Refine = True
        target = self.Target
        bar, more = [], []
        for action, (kind, _) in zip(self.Actions, self.Slots):
            if kind == BAR:
                bar.append(bar_width(action.BarWidthLabels(target), real_width))
            elif kind == POOL:
                more.append(button_width(action.WidthLabels(target), real_width))
        value = self.PagerValue()
        pager = None
        if value is not None:
            icon_w, icon_h = self.__IconSize()
            pager = (icon_w, icon_h, number_width(value, real_width))
        close_size, close_offset = self.__CloseGeometry()
        has_icon = target is not None and icon_render(target.Panel) is not None
        geo = card_layout(content_size, bar, more, self.More, pager, has_icon, real_width(self.KindText()),
                          close_size, close_offset)
        if geo["icon"] is not None:
            self.__Move(TooltipPath.TouchIcon, geo["icon"])
        self.__Move(TooltipPath.TouchKind, geo["kind"])
        x, y, width, height = geo["close"]
        self.__Move(TooltipPath.TouchCloseSlot, (x, y), (width, height))
        self.__Move(TooltipPath.TouchContent, geo["content"])
        divider = geo["divider"]
        if divider is not None:
            x, y, width = divider
            self.__Move(TooltipPath.TouchDivider, (x, y), (width, DIVIDER_H))
        x, y, width, height = geo["actions"]
        self.__Move(TooltipPath.TouchActions, (x, y), (width, height))
        if geo["pager"] is not None:
            self.__Move(icon_path(MenuConst.Icons[0]), geo["pager"]["prev"])  # 图标按钮的尺寸写在 JSON 里
            self.__Move(icon_path(MenuConst.Icons[1]), geo["pager"]["next"])
            x, y, width = geo["pager"]["number"]
            self.__Move(number_path(0), (x, y), (width, TEXT_H))
        bars = [slot[1] for slot in self.Slots if slot[0] == BAR]
        for slot, (x, y, width, height) in zip(bars, geo["bar"]):
            if slot < MenuConst.BarSize:
                self.__Move(bar_path(slot), (x, y), (width, height))
        if geo["more_line"] is not None:
            x, y, width = geo["more_line"]
            self.__Move(TooltipPath.MenuMoreLine, (x, y), (width, DIVIDER_H))
        pool = [slot[1] for slot in self.Slots if slot[0] == POOL]
        for slot, (x, y, width, height) in zip(pool, geo["more"]):
            if slot < MenuConst.PoolSize:
                self.__Move(button_path(slot), (x, y), (width, height))
        return geo["size"]

    def __IconSize(self):  # type: () -> tuple
        """
        翻页行的箭头（图标按钮）多大：**读 JSON 里 icon_prev 排出来的大小**（$flat_icon_size，缺省在 mei_common.json 的 flat_icon_button）；
        调箭头大小只改 JSON。读不到（还没排好）用 layout 的缺省
        """
        button = self.__Control(icon_path(MenuConst.Icons[0]))
        if button is not None:
            try:
                width, height = button.GetSize()
                if width > 0 and height > 0:
                    return int(round(width)), int(round(height))
            except Exception:  # noqa  还没排好：用缺省
                pass
        return ICON_SIZE

    def __CloseGeometry(self):  # type: () -> tuple
        """
        顶栏小 x 的尺寸与偏移：**读 JSON 里 close 的 $flat_icon_size 与 offset**（脚本只摆它的插槽、从不挪它，所以 GetPosition 读到的就是
        JSON 里的 offset —— 和 cursor_gap 同一个路子）。调大小、调偏移只改 JSON；读不到用 layout 的缺省
        """
        button = self.__Control(TooltipPath.TouchClose)
        size, offset = CLOSE_SIZE, CARD_CLOSE_OFFSET
        if button is None:
            return size, offset
        try:
            width, height = button.GetSize()
            if width > 0 and height > 0:
                size = (int(round(width)), int(round(height)))
            x, y = button.GetPosition()
            offset = (int(round(x)), int(round(y)))
        except Exception as e:  # noqa
            logger.warn("[MEI/menu] 读不到小 x 的尺寸 / 偏移，用缺省 {} / {}: {}".format(CLOSE_SIZE, CARD_CLOSE_OFFSET,
                                                                                    error_text(e)))
        return size, offset

    def __Fill(self):
        """
        按这一格写框里的东西（两个方向都写）：物品图标、种类、关闭、分隔线、操作条（字、图标、颜色、选中的底、遮罩）、
        「更多」（展开着才显出来）、翻页行
        """
        target, actions = self.Target, self.Actions
        if target is None:
            return
        self.__FillIcon(target.Panel)
        self.__SetText(TooltipPath.TouchKind, self.KindText())
        self.__Show(TooltipPath.TouchKind, True)
        self.__Show(TooltipPath.TouchClose, True)
        self.__Show(TooltipPath.TouchDivider, bool(actions))
        bars, pool, icons = {}, {}, {}
        for index, (kind, key) in enumerate(self.Slots):
            {BAR: bars, POOL: pool, ICON: icons}[kind][key] = index
        for slot in range(MenuConst.BarSize):
            index = bars.get(slot)
            if index is None:
                self.__Show(bar_path(slot), False)
                continue
            self.__FillBar(slot, actions[index], index == self.__Armed)
        for slot in range(MenuConst.PoolSize):
            index = pool.get(slot)
            if index is None or not self.More:
                self.__Show(button_path(slot), False)
                continue
            action = actions[index]
            enabled = action.IsEnabled(target)
            text = action.LabelFor(target, armed=index == self.__Armed)
            self.__SetText(button_path(slot) + TooltipPath.MenuButtonLabelSub, text if enabled else mute(text))
            self.__Show(button_path(slot) + TooltipPath.MenuButtonMaskSub, not enabled)
            self.__Show(button_path(slot), True)
        self.__Show(TooltipPath.MenuMoreLine, self.More and bool(pool))
        for name in MenuConst.Icons:
            self.__Show(icon_path(name), name in icons)
        value = self.PagerValue()
        self.__SetText(number_path(0), value if value is not None else u"")
        self.__Show(number_path(0), value is not None)

    def __FillBar(self, slot, action, armed):
        """ 操作条上的一个按钮：字（删除类红、用不了灰）、图标与颜色、选中的底（绿色下划线）、遮罩 """
        target = self.Target
        path = bar_path(slot)
        enabled = action.IsEnabled(target)
        on = self.More if action.Key == MenuKey.More else action.IsOn(target)
        text = action.BarLabelFor(target, armed)
        self.__SetText(path + TooltipPath.MenuButtonLabelSub, text if enabled else mute(text))
        glyph = action.GlyphFor(target)
        icon = path + TooltipPath.MenuBarIconSub
        self.__Show(icon, bool(glyph))
        if glyph:
            self.__Sprite(icon, MenuConst.GlyphPath.format(glyph))
        if not enabled:
            color = MenuConst.GlyphMutedColor
        elif action.Danger:
            color = MenuConst.GlyphDangerColor
        elif on:
            color = MenuConst.GlyphOnColor
        else:
            color = MenuConst.GlyphColor
        self.__Color(icon, color)
        self.__Sprite(path + TooltipPath.MenuButtonFaceSub, MenuConst.FaceOn if on and enabled else MenuConst.FaceNormal)
        self.__Show(path + TooltipPath.MenuButtonMaskSub, not enabled)
        self.__Show(path, True)

    def __FillIcon(self, panel):
        """ 顶栏的物品图标：这一格有物品就画上（多候选格是当前的候选），没有（失效的收藏）就藏起来 """
        render = icon_render(panel)
        if render is not None:
            try:
                renderer = self.MainNode.GetUIControl(TooltipPath.TouchIconItem, "item_renderer")
                if renderer is None or not renderer.SetUiItem(*render):
                    render = None
            except Exception as e:  # noqa  画不出来就不画
                logger.warn("[MEI/menu] 画不出物品图标: {}".format(error_text(e)))
                render = None
        self.__Show(TooltipPath.TouchIcon, render is not None)

    def __ResetPool(self):
        """ 开界面：框里的东西全藏、字清空、底换回平时的（界面状态跨开关存活，§22）"""
        self.__Written = {}
        self.__Show(TooltipPath.TouchIcon, False)
        self.__SetText(TooltipPath.TouchKind, u"")
        self.__Show(TooltipPath.TouchKind, False)
        self.__Show(TooltipPath.TouchClose, False)
        self.__Show(TooltipPath.TouchDivider, False)
        self.__Show(TooltipPath.MenuMoreLine, False)
        self.__Move(TooltipPath.TouchActions, (0, 0), (0, 0))
        for index in range(MenuConst.BarSize):
            self.__Show(bar_path(index), False)
            self.__SetText(bar_path(index) + TooltipPath.MenuButtonLabelSub, u"")
            self.__Show(bar_path(index) + TooltipPath.MenuButtonMaskSub, False)
            self.__Sprite(bar_path(index) + TooltipPath.MenuButtonFaceSub, MenuConst.FaceNormal)
        for index in range(MenuConst.PoolSize):
            self.__Show(button_path(index), False)
            self.__SetText(button_path(index) + TooltipPath.MenuButtonLabelSub, u"")
            self.__Show(button_path(index) + TooltipPath.MenuButtonMaskSub, False)
        for name in MenuConst.Icons:
            self.__Show(icon_path(name), False)
        for index in range(MenuConst.NumberCount):
            self.__SetText(number_path(index), u"")
            self.__Show(number_path(index), False)

    def __Control(self, path):
        return self.MainNode.GetUIControl(path)

    def __Move(self, path, pos, size=None):
        """
        位置、大小：和上次写的一样不碰引擎。大小写尺寸规则（full_size）—— 旧的 SetSize 只改当前的值，排版一刷新就回到 JSON 的大小（引擎结论 §28），
        显隐改成一批写完才刷新以后，那次刷新就会把按钮、分隔线拉回去。按钮里的底、遮罩是 100%，跟着变
        """
        pos = (int(pos[0]), int(pos[1]))
        size = (int(size[0]), int(size[1])) if size is not None else None
        moved = self.__Changed(path, "pos", pos)
        resized = size is not None and self.__Changed(path, "size", size)
        if not moved and not resized:
            return
        control = self.__Control(path)
        if control is None:
            self.__Written.pop((path, "pos"), None)
            self.__Written.pop((path, "size"), None)
            return
        if moved:
            control.SetPosition(pos)
        if resized:
            full_size(control, size)
            mark_dirty(self.MainNode.ScreenNode)  # 尺寸规则也等这一帧末尾那次刷新一起排

    def __Show(self, path, on):
        """
        显隐：和上次写的一样不碰引擎；写也不当场刷新（show_later），这一帧写完由主节点 flush 一次 ——
        SDK 缺省每改一次显隐就重排整个界面（引擎结论 §57），填一次菜单要写三十来个，原来就是三十来次整屏重排（tooltip.md §6.15 第 2 条）
        """
        on = bool(on)
        if not self.__Changed(path, "visible", on):
            return
        control = self.__Control(path)
        if control is None:
            self.__Written.pop((path, "visible"), None)
            return
        show_later(control, on, self.MainNode.ScreenNode)

    def __SetText(self, path, text):
        text = native_str(text)
        if not self.__Changed(path, "text", text):
            return
        label = self.MainNode.GetUIControl(path, "label")
        if label is None:
            self.__Written.pop((path, "text"), None)
            return
        label.SetText(text)

    def __Changed(self, path, what, value):  # type: (str, str, any) -> bool
        key = (path, what)
        if self.__Written.get(key) == value:
            return False
        self.__Written[key] = value
        return True

    def __Sprite(self, path, texture):
        """ 换图（按钮的底、操作条的图标）：和上次写的一样就不碰引擎 """
        if not self.__Changed(path, "sprite", texture):
            return
        image = self.MainNode.GetUIControl(path, "image")
        if image is not None:
            image.SetSprite(texture)

    def __Color(self, path, color):
        if not self.__Changed(path, "color", tuple(color)):
            return
        image = self.MainNode.GetUIControl(path, "image")
        if image is not None:
            image.SetSpriteColor(tuple(color))

    def __Clear(self):
        target = self.Target
        self.Target = None
        self.Actions = []
        self.Slots = []
        self.More = False
        self.__Armed = None
        self.__Seek = None
        if target is not None:
            self.__ResumeRotation(target.Panel)

    # 点击绑定
# ======================================================================================================================
    def __Bind(self):
        self.__Unbind()
        for index in range(MenuConst.PoolSize):
            wrapper = self.Bindings.Bind(self.__ClickHandler((POOL, index)), ViewBinder.BF_ButtonClickUp,
                                         MenuConst.ButtonName.format(index))
            self.__Wrappers.append(wrapper)
        for name in MenuConst.Icons:
            wrapper = self.Bindings.Bind(self.__ClickHandler((ICON, name)), ViewBinder.BF_ButtonClickUp,
                                         MenuConst.IconName.format(name))
            self.__Wrappers.append(wrapper)
        for index in range(MenuConst.BarSize):
            wrapper = self.Bindings.Bind(self.__ClickHandler((BAR, index)), ViewBinder.BF_ButtonClickUp,
                                         MenuConst.BarName.format(index))
            self.__Wrappers.append(wrapper)
        wrapper = self.Bindings.Bind(self.__ClickHandler(CLOSE), ViewBinder.BF_ButtonClickUp, MenuConst.CloseName)
        self.__Wrappers.append(wrapper)

    def __ClickHandler(self, key):
        def on_click(_args):
            self.OnButton(key)
        return on_click

    def __Unbind(self):
        wrappers, self.__Wrappers = self.__Wrappers, []
        for wrapper in wrappers:
            try:
                self.Bindings.Unbind(wrapper)
            except Exception as e:  # noqa
                logger.warn("[MEI/menu] 解绑失败: {}".format(error_text(e)))
