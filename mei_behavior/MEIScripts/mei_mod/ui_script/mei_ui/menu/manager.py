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
触屏的二级菜单（docs/architecture/tooltip.md §6）：点一下格子，出「这一格的信息 + 这一格能做的事」。一个界面一份，
挂在主节点上（UIMainNode.OnCreate 建、OnDestroy 拆，紧跟在 tooltip 管理器后面）。

  · 菜单就是 tooltip 的移动端宿主：内容由 TooltipManager 建（设置开着、格子有 TooltipContent → 配方预览 / 接受物品；
    否则只有标题 —— 设置关着时菜单照出），框里别的东西由这里填；
  · **一个框**（tooltip.md §6.12）：顶栏（这是哪种格子 + 关闭的小 x）、内容、分隔线、分段的按钮区 ——
    动作按段排（查询 / 配方 / 数量 / 排序 / 分组 / 显示 / 删除 / 候选，相邻同段的并成一段），一段一行、左边写段名；
    数量、候选是步进器（[−] 数字 [+]，候选用左右箭头图标）；删除类红字、灰掉的灰字。宽度按字算、按内容收。
    框里每样东西的位置由 menu.layout.box_layout 算，tooltip 管理器摆框时调 Layout；
  · 落位：不贴着点的那一格，摆在格子所在区域的外侧 —— 物品栏的格子摆在物品栏左边、收藏栏的摆在右边、
    配方页的摆在配方页右边，竖直方向跟着那一格；连续浏览时不挡着区域里的格子。放不下照旧贴屏幕边兜底（TooltipManager）；
  · 按钮池（mei_common 的 button_0 … button_15）：按这一格的文字动作填前几个，其余藏起来；带 Icon 的动作用同名的图标按钮
    （icon_prev / icon_next）；「关闭」是顶栏的小 x，不占池子。点击走 button_mappings → 固定名字的 BF_ButtonClickUp 绑定
    （MenuConst.ButtonName / IconName / CloseName，只能单个绑定，引擎结论 §9）；
  · 点格子、点按钮都是在绑定回调里来的：只记下，下一帧（界面代理的 OnTick → Update）再开 / 再执行 —— 绑定回调里不建控件（§27-2）；
  · 手指划进一格：tooltip 管理器认出「移进」后调 Hover，同一帧打开，不检测移出；已经是它的菜单不动。
    菜单是这次触摸划进时开的，松手那一下的点击不当成「再点一下同一格」收起（按住多久都一样）；本来就开着它的，照旧收起；
  · 有的动作点了不收（−1 / +1、上移下移、换候选）：改收藏的那几样一改，收藏栏重排、格子全是新的 —— 先让 tooltip 放掉归属，
    下一帧找到显示同一条收藏的新格子再挂上（跟着这一条走）；删除整组要点两下（第一下按钮变成「确认删除？」）；
  · 多候选格：打开时停下轮播（看着的东西别自己变），收起时接着轮播；点接受物品列表里的一格 = 选中那个候选；
  · 收起：点「关闭」、点了动作、点别的格子（换成那一格）、再点一下同一格；那一格被拆了、换了内容（翻页、切页签、搜索）
    由 TooltipManager 收（它记着显示时的 ContentKey），这里看到它收了就跟着清；点空白处不收；
  · 复位（界面状态跨开关存活，§22）：开界面时框里每个控件的显隐、文字、遮罩都写一遍，每次打开再按这一格两个方向写一遍
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.ui import ItemsBrowserPath, ItemsSidebarPath, MenuConst, MenuKey, RecipeDetailsPath, TooltipPath
from MEIScripts.mei_mod.state.bookmarks import entry_identity
from MEIScripts.mei_mod.ui_script.mei_ui.menu.actions import (
    MenuTarget, actions_for, group_sections, is_stepper, kind_of, mute,
)
from MEIScripts.mei_mod.ui_script.mei_ui.menu.layout import (
    BUTTON_H, CLOSE_OFFSET, CLOSE_SIZE, ICON_SIZE, TEXT_H, box_layout, button_width, number_width, text_width,
)
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
""" 点了顶栏的「关闭」（和按钮池的下标分开记）"""

POOL = "pool"
ICON = "icon"
""" 动作摆在哪：按钮池里的文字按钮，还是图标按钮（MenuAction.Icon 的槽名）"""


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


def button_path(index):  # type: (int) -> str
    return TooltipPath.MenuButton.format(index)


def section_path(index):  # type: (int) -> str
    return TooltipPath.MenuSection.format(index)


def number_path(index):  # type: (int) -> str
    return TooltipPath.MenuNumber.format(index)


def icon_path(name):  # type: (str) -> str
    return TooltipPath.MenuIcon.format(name)


def assign_slots(actions):  # type: (list) -> list
    """
    每个动作摆在哪个按钮上：带 Icon、而且有这个图标按钮（MenuConst.Icons）的用图标按钮（一个槽只给第一个认领的），
    其余按顺序占按钮池；返回 [(POOL, 池里第几个) 或 (ICON, 槽名), ...]，和 actions 一一对应
    """
    slots, used, pool = [], set(), 0
    for action in actions:
        icon = getattr(action, "Icon", None)
        if icon in MenuConst.Icons and icon not in used:
            used.add(icon)
            slots.append((ICON, icon))
            continue
        slots.append((POOL, pool))
        pool += 1
    return slots


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
                return utilities.GetControlRectSize(main.GetUIControl(rect_path) or member), side
        except Exception:  # noqa  区域控件不在了：当它不是
            continue
    return None, None


def stepper_flags(groups, budget=MenuConst.NumberCount):  # type: (list, int) -> list
    """ 每段排不排成步进器：段有数字、正好两个按钮；数字标签只有 budget 个，多出来的照普通按钮排 """
    flags = []
    for section, actions in groups:
        on = budget > 0 and is_stepper(section, actions)
        if on:
            budget -= 1
        flags.append(on)
    return flags


class TouchMenu(object):

    def __init__(self, main_node, tooltip):
        self.MainNode = main_node
        self.Tooltip = tooltip
        self.Bindings = ScreenBinder(main_node.ScreenNode)  # type: ScreenBinder
        self.Target = None  # type: MenuTarget or None  # 开着的菜单是给哪一格的
        self.Actions = []  # type: list  # 这一格的动作，按显示顺序（不含「关闭」，它在顶栏）
        self.Slots = []  # type: list  # 每个动作摆在哪：(POOL, 池里第几个) 或 (ICON, 槽名)，见 assign_slots
        self.Groups = []  # type: list  # [(段, [动作, ...]), ...]，按显示顺序；动作摊平就是 Actions
        self.Steppers = []  # type: list  # 每段排不排成步进器
        self.Labels = False  # type: bool  # 写不写段名（不止一段、段名标签够用时写）
        self.__Wrappers = []  # type: list  # 挂上的点击绑定，关界面时解绑
        self.__Pending = None  # type: tuple or None  # (哪一格, 点的还是划进的)：Update 里打开；点的再点一下同一格是收起
        self.__Touch = None  # type: tuple or None  # 最近一次划进：(那一格, 划进时菜单是不是已经开着它)，认松手那一下的点击
        self.__Click = None  # type: any  # 点了哪个按钮：(POOL, 第几个) / (ICON, 槽名) / CLOSE，下一帧执行
        self.__Armed = None  # type: int or None  # 要二次确认的动作点过第一下：它在 Actions 里的位置
        self.__Seek = None  # type: tuple or None  # 改完收藏在找新格子：(跟着的那一条, 找了几帧)

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
        """ 点了按钮：(POOL, 池里第几个) / (ICON, 槽名) / 顶栏的关闭（CLOSE）—— 下一帧执行 """
        self.__Click = key

    # 每帧（界面代理的 OnTick，排在 tooltip 管理器后面）
# ======================================================================================================================
    def Update(self):
        """ 出错只记日志 —— 这里抛出去会带走同一帧别的代理 """
        try:
            if self.Target is not None and not self.Tooltip.IsVisible():
                # tooltip 管理器那边收起了（那一格被拆了、换了内容）：菜单跟着清
                self.__Clear()
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
        actions = [action for action in actions_for(panel) if action.Key != MenuKey.Close]
        if len(actions) > MenuConst.PoolSize:
            logger.warn("[MEI/menu] 这一格有 {} 个动作，按钮池只有 {} 个，多的不出".format(len(actions), MenuConst.PoolSize))
            actions = actions[:MenuConst.PoolSize]
        self.__Clear()
        self.__HoldRotation(panel)
        if not self.__ShowContent(panel):
            self.__ResumeRotation(panel)
            return
        self.Target = MenuTarget(self.MainNode, panel)
        self.Actions = actions
        self.Slots = assign_slots(actions)
        self.Groups = group_sections(actions)
        self.Steppers = stepper_flags(self.Groups)
        self.Labels = 1 < len(self.Groups) <= MenuConst.SectionCount
        region, side = menu_region(self.MainNode, panel)
        self.Tooltip.SetTouchRegion(region, side)
        self.Tooltip.SetTouchLayout(self.Layout)
        self.__Fill()

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
        接受物品列表里的一格 = 在多候选格里选中这个候选（标题、「来源 / 收藏」、候选的数字跟着换）；配方预览里的格子不做事
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
            self.__Fill()  # 点了不收、格子也没换（换候选）：字、遮罩、步进器的数字可能变了

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

    # 框：排版（摆在哪）由 tooltip 管理器摆框时调 Layout；字、遮罩、显隐由 __Fill 写
# ======================================================================================================================
    def Layout(self, content_size):  # type: (tuple) -> tuple
        """
        tooltip 管理器摆菜单时调（显示那一刻、内容尺寸变了、挂到新格子上）：按内容尺寸排好框里的每样东西，返回框的尺寸。
        位置、尺寸都由这里写（绝对定位）；池里的按钮按所在的列改宽（SetSize 带上子控件：底图、遮罩跟着变，字居中）
        """
        target = self.Target
        rows, index = [], 0
        icon_w, icon_h = self.__IconSize()
        for (section, actions), stepper in zip(self.Groups, self.Steppers):
            items = []
            for action in actions:
                if self.Slots[index][0] == ICON:
                    items.append((icon_w, icon_h, True))
                else:
                    items.append((button_width(action.WidthLabels(target)), BUTTON_H, False))
                index += 1
            rows.append((items, stepper, number_width(section.ValueFor(target)) if stepper else 0))
        kind = text_width(kind_of(target.Panel)) if target is not None else 0
        close_size, close_offset = self.__CloseGeometry()
        geo = box_layout(content_size, rows, self.Labels, kind, close_size, close_offset)
        self.__Move(TooltipPath.TouchKind, geo["kind"])
        x, y, width, height = geo["close"]
        self.__Move(TooltipPath.TouchCloseSlot, (x, y), (width, height))
        self.__Move(TooltipPath.TouchContent, geo["content"])
        divider = geo["divider"]
        if divider is not None:
            x, y, width = divider
            self.__Move(TooltipPath.TouchDivider, (x, y), (width, 1))
        x, y, width, height = geo["actions"]
        self.__Move(TooltipPath.TouchActions, (x, y), (width, height))
        for slot, (x, y, width, height) in zip(self.Slots, geo["buttons"]):
            kind_of_slot, key = slot
            if kind_of_slot == ICON:
                self.__Move(icon_path(key), (x, y))  # 图标按钮的尺寸写在 JSON 里
            elif key < MenuConst.PoolSize:
                self.__Move(button_path(key), (x, y), (width, height), True)
        for index, pos in enumerate(geo["names"][:MenuConst.SectionCount]):
            if pos is not None:
                self.__Move(section_path(index), pos)
        numbers = [number for number in geo["numbers"] if number is not None]
        for index, (x, y, width) in enumerate(numbers[:MenuConst.NumberCount]):
            self.__Move(number_path(index), (x, y), (width, TEXT_H))
        return geo["size"]

    def __IconSize(self):  # type: () -> tuple
        """
        图标按钮（候选的左右箭头）的尺寸：**读 JSON 里 icon_prev 排出来的大小**（$menu_icon_size，缺省在 mei_common.json 的 menu_icon_button）；
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
        顶栏小 x 的尺寸与偏移：**读 JSON 里 close 的 $menu_icon_size 与 offset**（脚本只摆它的插槽、从不挪它，所以 GetPosition 读到的就是
        JSON 里的 offset —— 和 cursor_gap 同一个路子）。调大小、调偏移只改 JSON；读不到用 layout 的缺省
        """
        button = self.__Control(TooltipPath.TouchClose)
        size, offset = CLOSE_SIZE, CLOSE_OFFSET
        if button is None:
            return size, offset
        try:
            width, height = button.GetSize()
            if width > 0 and height > 0:
                size = (int(round(width)), int(round(height)))
            x, y = button.GetPosition()
            offset = (int(round(x)), int(round(y)))
        except Exception as e:  # noqa
            logger.warn("[MEI/menu] 读不到小 x 的尺寸 / 偏移，用缺省 {} / {}: {}".format(CLOSE_SIZE, CLOSE_OFFSET, error_text(e)))
        return size, offset

    def __Fill(self):
        """ 按这一格写框里的字、遮罩、显隐（两个方向都写）：种类、关闭、分隔线、按钮池、段名、步进器的数字 """
        target, actions = self.Target, self.Actions
        if target is None:
            return
        self.__SetText(TooltipPath.TouchKind, kind_of(target.Panel))
        self.__Show(TooltipPath.TouchKind, True)
        self.__Show(TooltipPath.TouchClose, True)
        self.__Show(TooltipPath.TouchDivider, bool(actions))
        pool, icons = {}, {}
        for index, (kind, key) in enumerate(self.Slots):
            (icons if kind == ICON else pool)[key] = index
        for slot in range(MenuConst.PoolSize):
            index = pool.get(slot)
            if index is None:
                self.__Show(button_path(slot), False)
                continue
            action = actions[index]
            enabled = action.IsEnabled(target)
            text = action.LabelFor(target, armed=index == self.__Armed)
            self.__SetText(button_path(slot) + TooltipPath.MenuButtonLabelSub, text if enabled else mute(text))
            self.__Show(button_path(slot) + TooltipPath.MenuButtonMaskSub, not enabled)
            self.__Show(button_path(slot), True)
        for name in MenuConst.Icons:
            self.__Show(icon_path(name), name in icons)
        for index in range(MenuConst.SectionCount):
            shown = self.Labels and index < len(self.Groups)
            self.__SetText(section_path(index), self.Groups[index][0].LabelFor(target) if shown else u"")
            self.__Show(section_path(index), shown)
        steppers = [section for (section, _), on in zip(self.Groups, self.Steppers) if on]
        for index in range(MenuConst.NumberCount):
            shown = index < len(steppers)
            self.__SetText(number_path(index), steppers[index].ValueFor(target) if shown else u"")
            self.__Show(number_path(index), shown)

    def __ResetPool(self):
        """ 开界面：框里的东西全藏、字清空（界面状态跨开关存活，§22）；关闭按钮的字写上 """
        self.__SetText(TooltipPath.TouchKind, u"")
        self.__Show(TooltipPath.TouchKind, False)
        self.__Show(TooltipPath.TouchClose, False)
        self.__Show(TooltipPath.TouchDivider, False)
        area = self.__Control(TooltipPath.TouchActions)
        if area is not None:
            area.SetSize((0, 0))
        for index in range(MenuConst.PoolSize):
            self.__Show(button_path(index), False)
            self.__SetText(button_path(index) + TooltipPath.MenuButtonLabelSub, u"")
            self.__Show(button_path(index) + TooltipPath.MenuButtonMaskSub, False)
        for name in MenuConst.Icons:
            self.__Show(icon_path(name), False)
        for index in range(MenuConst.SectionCount):
            self.__SetText(section_path(index), u"")
            self.__Show(section_path(index), False)
        for index in range(MenuConst.NumberCount):
            self.__SetText(number_path(index), u"")
            self.__Show(number_path(index), False)

    def __Control(self, path):
        return self.MainNode.GetUIControl(path)

    def __Move(self, path, pos, size=None, resize_children=False):
        control = self.__Control(path)
        if control is None:
            return
        control.SetPosition((int(pos[0]), int(pos[1])))
        if size is not None:
            control.SetSize((int(size[0]), int(size[1])), resize_children)

    def __Show(self, path, on):
        control = self.__Control(path)
        if control is not None:
            control.SetVisible(bool(on))

    def __SetText(self, path, text):
        label = self.MainNode.GetUIControl(path, "label")
        if label is not None:
            label.SetText(native_str(text))

    def __Clear(self):
        target = self.Target
        self.Target = None
        self.Actions = []
        self.Slots = []
        self.Groups = []
        self.Steppers = []
        self.Labels = False
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
