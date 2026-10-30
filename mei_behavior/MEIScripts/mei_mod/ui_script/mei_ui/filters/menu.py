# coding=utf-8

# ----------------------------------------------------------------------
#  menu.py is part of MoreEnoughItems.
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
物品栏的筛选与排序菜单（排版 D：标签块 + 步进器，docs/architecture/modes.md §8）。一个界面一份，挂在主节点 main.Filters。

- 搜索框右边的筛选按钮点一下开 / 关（ItemsBrowserScript.ToggleFilters → Toggle）；右上角的小 x、「确定」也关。
- 标签块按下就是选中（几项都要满足）；‹ › 换排序的属性（第一项是「不排序」），右边切升 / 降；「清除」全清。
  改了当场记进 prefs（全局，关界面不复位），物品栏照现在的搜索字重排（ItemsBrowserScript.RefreshItemView）。
- 点击都在按钮绑定的回调里到：只记下，下一帧处理（Update，主节点每帧调）；物品栏藏起来（收成悬浮窗）时菜单跟着关。
- 复位：开界面、关界面都把框写回藏着；筛选按钮的图标按「选没选」两个方向都染（选了是查找按钮开着的那种蓝）
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.constants.texts import FilterText
from MEIScripts.constants.ui import FilterConst, FloatConst, ItemsBrowserPath, UiPathConst
from MEIScripts.mei_mod.state import PrefsManager
from MEIScripts.mei_mod.ui_script.proxy.focus.search import control_rect
from MEIScripts.registry.filters import DESC, ItemFilters
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.lang import localize
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

from . import layout
from .state import active, flip_direction, step_sort, toggle_filter

ViewBinder = clientApi.GetViewBinderCls()

TOGGLE, CHIP, CLOSE, PREV, NEXT, DIR, CLEAR, DONE = "toggle", "chip", "close", "prev", "next", "dir", "clear", "done"

BUTTONS = (
    (CLOSE, FilterConst.CloseName),
    (PREV, FilterConst.PrevName),
    (NEXT, FilterConst.NextName),
    (DIR, FilterConst.DirName),
    (CLEAR, FilterConst.ClearName),
    (DONE, FilterConst.DoneName),
)
""" 除标签块以外的按钮：动作 → 绑定名（JSON 里的 $pressed_button_name）"""


class FilterMenu(object):
    """ 一个界面一份；筛选、排序存在 prefs（PrefsManager.GetItemFilters / GetItemSort）"""

    def __init__(self, main):
        self.MainNode = main
        self.Open = False  # type: bool
        self.Bindings = None  # type: ScreenBinder or None
        self.Filters = []  # type: list  # 这次打开时列出的筛选（ItemFilter），第 i 个标签块就是第 i 项
        self.Sorts = []  # type: list  # 登记的排序（ItemSort），步进器在「不排序 + 这些」里转
        self.ContentPath = None  # type: str or None  # scrolling_panel 里放标签块的那一层（找到就记下）
        self.FrameSize = (layout.WIDTH, 0)  # type: tuple  # 上次排出来的框的大小（Place 按它摆）
        self.__Pending = []  # type: list  # 点击回调里记下的 (动作, 参数)，下一帧处理
        self.__Written = {}  # type: dict  # 写过的值（(路径, 哪一样) -> 值）：一样的不再碰引擎

    # 生命周期
# ======================================================================================================================
    def OnCreate(self):
        """ 开界面：框写回藏着（界面状态跨开关存活，引擎结论 §22），挂按钮的点击，按钮图标照现在选没选染 """
        self.Open = False
        self.__Pending = []
        self.__Written = {}
        self.ShowFrame(False)
        self.Bindings = ScreenBinder(self.MainNode.ScreenNode)
        for index in range(FilterConst.ChipCount):
            self.Bindings.Bind(self.__Click(CHIP, index), ViewBinder.BF_ButtonClickUp, FilterConst.ChipName.format(index))
        for key, name in BUTTONS:
            self.Bindings.Bind(self.__Click(key), ViewBinder.BF_ButtonClickUp, name)
        self.PaintButton()

    def OnDestroy(self):
        self.__Pending = []
        if self.Bindings is not None:
            self.Bindings.UnbindAll()
            self.Bindings = None
        self.Open = False
        self.ShowFrame(False)

    # 入口
# ======================================================================================================================
    def Toggle(self):
        """ 筛选按钮（触摸回调）：下一帧开 / 关 """
        self.__Pending.append((TOGGLE, None))

    def __Click(self, key, arg=None):
        def on_click(_args):
            self.__Pending.append((key, arg))
        return on_click

    def Update(self):
        """ 每帧（主节点 OnTick）：物品栏藏起来了就关；处理上一帧记下的点击 """
        if self.Open and not self.BrowserShown():
            self.Close()
        pending, self.__Pending = self.__Pending, []
        for key, arg in pending:
            try:
                self.OnButton(key, arg)
            except Exception as e:  # noqa  这里抛出去会带走同一帧别的东西
                logger.error("[MEI/filter] 处理 {} 出错: {}".format(key, error_text(e)))

    def OnButton(self, key, arg=None):
        if key == TOGGLE:
            if self.Open:
                self.Close()
            else:
                self.OpenMenu()
            return
        if not self.Open:
            return
        if key in (CLOSE, DONE):
            self.Close()
            return
        selected, sort = PrefsManager.GetItemFilters(), PrefsManager.GetItemSort()
        if key == CHIP:
            if arg is None or arg >= len(self.Filters):
                return
            selected = toggle_filter(selected, self.Filters[arg].Id)
        elif key in (PREV, NEXT):
            sort = step_sort([spec.Id for spec in self.Sorts], sort, -1 if key == PREV else 1)
        elif key == DIR:
            if not sort:
                return
            sort = flip_direction(sort)
        elif key == CLEAR:
            selected, sort = [], None
        self.Apply(selected, sort)

    # 开、关、生效
# ======================================================================================================================
    def OpenMenu(self):
        if not self.BrowserShown():
            return
        filters = ItemFilters.ListFilters()
        if len(filters) > FilterConst.ChipCount:
            logger.warn("[MEI/filter] 登记的筛选有 {} 项，菜单只放得下 {} 项".format(len(filters), FilterConst.ChipCount))
        self.Filters = filters[:FilterConst.ChipCount]
        self.Sorts = ItemFilters.ListSorts()
        self.Open = True
        self.Render()
        self.Place()
        self.ShowFrame(True)

    def Close(self):
        self.Open = False
        self.ShowFrame(False)

    def Apply(self, selected, sort):
        """ 选的东西变了：存下来、菜单重画、按钮图标重染、物品栏重排 """
        PrefsManager.SetItemFilters(selected)
        PrefsManager.SetItemSort(sort)
        self.Render()
        self.PaintButton()
        browser = self.Browser()
        refresh = getattr(browser, "RefreshItemView", None)
        if callable(refresh):
            refresh()

    # 画
# ======================================================================================================================
    def SortName(self, sort):  # type: (tuple or None) -> any
        for spec in self.Sorts:
            if sort and spec.Id == sort[0]:
                return localize(spec.NameKey)
        return FilterText.NoSort

    def Render(self):
        """ 按现在选的东西把框里每样写一遍（只写变了的）。位置全由 layout.menu_layout 算，绝对定位 """
        selected, sort = PrefsManager.GetItemFilters(), PrefsManager.GetItemSort()
        if sort and sort[0] not in [spec.Id for spec in self.Sorts]:
            sort = None
        names = [localize(spec.NameKey) for spec in self.Filters]
        value = self.SortName(sort)
        direction = FilterText.Descending if sort and sort[1] == DESC else FilterText.Ascending
        plan = layout.menu_layout(names, value, [FilterText.Ascending, FilterText.Descending],
                                  [FilterText.Clear, FilterText.Done])
        self.FrameSize = plan["size"]
        self.__Size(UiPathConst.FilterFrame, plan["size"])
        self.__Text(UiPathConst.FilterTitle, FilterText.Title, plan["title"])
        self.__Move(UiPathConst.FilterClose, plan["close"])
        self.__Text(UiPathConst.FilterSection, FilterText.FilterSection, plan["filter_section"])
        self.__Chips(plan, names, selected)
        self.__Text(UiPathConst.FilterSortSection, FilterText.SortSection, plan["sort_section"])
        self.__Move(UiPathConst.FilterPrev, plan["prev"])
        self.__Text(UiPathConst.FilterValue, value, plan["value"])
        self.__Move(UiPathConst.FilterNext, plan["next"])
        dir_pos, dir_size = plan["dir"]
        self.__Move(UiPathConst.FilterDir, dir_pos, dir_size)
        self.__Label(UiPathConst.FilterDir, direction if sort else FilterText.Mute.format(direction))
        self.__Visible(UiPathConst.FilterDir + "/mask", not sort)
        line_pos, line_size = plan["line"]
        self.__Move(UiPathConst.FilterLine, line_pos, line_size)
        for path, text, (pos, size) in zip((UiPathConst.FilterClear, UiPathConst.FilterDone),
                                           (FilterText.Clear, FilterText.Done), plan["foot"]):
            self.__Move(path, pos, size)
            self.__Label(path, text)

    def __Chips(self, plan, names, selected):
        """ 标签区：scrolling_panel 的大小是看得见的那块，里面那一层是全部标签块的大小（放得下时两个一样高，不滚）"""
        area = plan["chips"]
        self.__Move(UiPathConst.FilterScroll, plan["chips_pos"])
        self.__FullSize(UiPathConst.FilterScroll, area["view"])
        content = self.Content()
        if content is None:
            return
        self.__FullSize(content, area["content"])
        for index in range(FilterConst.ChipCount):
            path = content + FilterConst.ChipSub.format(index)
            shown = index < len(names)
            self.__Visible(path, shown)
            if not shown:
                continue
            on = self.Filters[index].Id in (selected or ())
            self.__Move(path, area["positions"][index], (layout.chip_width(names[index]), layout.BUTTON_H))
            self.__Label(path, FilterText.On.format(names[index]) if on else names[index])
            self.__Sprite(path + FilterConst.FaceSub, FilterConst.FaceOn if on else FilterConst.FaceNormal)

    def Content(self):  # type: () -> str or None
        """ scrolling_panel 里放标签块的那一层（PC / 触屏结构不一样，按 FilterConst.ScrollContents 找第一个在的）"""
        if self.ContentPath is not None:
            return self.ContentPath
        for sub in FilterConst.ScrollContents:
            path = UiPathConst.FilterScroll + sub
            if self.MainNode.GetUIControl(path) is not None:
                self.ContentPath = path
                return path
        logger.warn("[MEI/filter] 找不到滚动区里放标签块的那一层，标签块不显示")
        return None

    def Place(self):
        """ 框摆在筛选按钮旁边（物品栏左边，放不下就压在物品栏上、按钮下面），夹在屏幕里 """
        main = self.MainNode
        screen = control_rect(main.GetUIControl(UiPathConst.FilterLayer))
        if screen is None:
            return
        button = control_rect(main.GetUIControl(ItemsBrowserPath.FilterButton))
        avoid = control_rect(main.GetUIControl(UiPathConst.RightWrapper))
        x, y = layout.place_menu(self.FrameSize, button, avoid, screen)
        self.__Move(UiPathConst.FilterFrame, (x - screen[0], y - screen[1]), force=True)

    def ShowFrame(self, on):  # type: (bool) -> None
        control = self.MainNode.GetUIControl(UiPathConst.FilterFrame)
        if control is not None:
            control.SetVisible(bool(on))
        self.__Written.pop((UiPathConst.FilterFrame, "visible"), None)

    def PaintButton(self):
        """ 筛选按钮的图标：选了（登记着的）筛选或排序是查找按钮开着的那种蓝，没选是平时的灰；两个方向都写 """
        on = active(PrefsManager.GetItemFilters(), PrefsManager.GetItemSort(),
                    [spec.Id for spec in ItemFilters.ListFilters()], [spec.Id for spec in ItemFilters.ListSorts()])
        color = FloatConst.IconActiveColor if on else FloatConst.IconColor
        for sub in FloatConst.IconSubs:
            icon = self.MainNode.GetUIControl(ItemsBrowserPath.FilterButton + sub)
            if icon is None:
                continue
            try:
                icon.asImage().SetSpriteColor(color)
            except Exception:  # noqa  图标还没建（物品栏没开）
                pass

    def Browser(self):  # type: () -> any
        browser = getattr(self.MainNode, "ItemsBrowserIns", None)
        return browser if browser is not None and getattr(browser, "Inited", False) else None

    def BrowserShown(self):  # type: () -> bool
        browser = self.Browser()
        return browser is not None and getattr(browser, "Shown", True)

    # 写控件（只写变了的）
# ======================================================================================================================
    def __Changed(self, path, what, value):  # type: (str, str, any) -> bool
        key = (path, what)
        if self.__Written.get(key) == value:
            return False
        self.__Written[key] = value
        return True

    def __Move(self, path, pos, size=None, force=False):
        control = self.MainNode.GetUIControl(path)
        if control is None:
            return
        pos = (int(pos[0]), int(pos[1]))
        if force or self.__Changed(path, "pos", pos):
            control.SetPosition(pos)
        if size is not None:
            self.__Size(path, size, control)

    def __Size(self, path, size, control=None):
        size = (int(size[0]), int(size[1]))
        if not self.__Changed(path, "size", size):
            return
        control = control or self.MainNode.GetUIControl(path)
        if control is not None:
            control.SetSize(size, True)

    def __FullSize(self, path, size):
        """ 里面是相对尺寸的（scrolling_panel 与它的内容）：用 SetFullSize 写绝对值，子控件跟着（引擎结论 §28）"""
        size = (int(size[0]), int(size[1]))
        if not self.__Changed(path, "full", size):
            return
        control = self.MainNode.GetUIControl(path)
        if control is not None:
            control.SetFullSize("x", {"absoluteValue": size[0]})
            control.SetFullSize("y", {"absoluteValue": size[1]})

    def __Visible(self, path, on):
        if not self.__Changed(path, "visible", bool(on)):
            return
        control = self.MainNode.GetUIControl(path)
        if control is not None:
            control.SetVisible(bool(on))

    def __Text(self, path, text, pos):
        self.__Move(path, pos)
        if not self.__Changed(path, "text", text):
            return
        label = self.MainNode.GetUIControl(path, "label")
        if label is not None:
            label.SetText(native_str(text))

    def __Label(self, button_path, text):
        """ 按钮上的字（mei_common.menu_button 的 label）"""
        path = button_path + FilterConst.LabelSub
        if not self.__Changed(path, "text", text):
            return
        label = self.MainNode.GetUIControl(path, "label")
        if label is not None:
            label.SetText(native_str(text))

    def __Sprite(self, path, texture):
        if not self.__Changed(path, "sprite", texture):
            return
        control = self.MainNode.GetUIControl(path)
        if control is not None:
            control.asImage().SetSprite(texture)
