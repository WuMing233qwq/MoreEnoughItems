# coding=utf-8

# ----------------------------------------------------------------------
#  find.py is part of MoreEnoughItems.
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
from mod_log import logger

from MEIScripts.constants.texts import MenuKindText
from MEIScripts.constants.ui import MenuKey, UiPathConst
from MEIScripts.utils.text import error_text, native_str


def touch_point(args):  # type: (dict) -> tuple or None
    """ 按钮回调参数里的点（TouchPosX / TouchPosY，与 GetGlobalPosition 同一坐标系）；没有给 None """
    try:
        return float(args["TouchPosX"]), float(args["TouchPosY"])
    except (TypeError, KeyError, ValueError):
        return None


class SlotTarget(object):
    """
    别的界面里的一格（原版背包、快捷栏、别的模组的界面）：没有 MEI 的面板，查找时点到它就替它出二级菜单 ——
    动作与物品格一样（来源 / 用途 / 收藏），菜单摆在它旁边
    """
    def __init__(self, main, hit, item):
        self.MainNode = main
        self.Item = item
        self.Control = main.ScreenNode.GetBaseUIControl(hit.Path)
        self.Destroyed = False
        self.ItemHoverText = ""
        try:
            self.ItemHoverText = native_str(item.HoverText or "")
        except Exception as e:  # noqa  悬停文字取不到：菜单标题退回物品名
            logger.warn("[MEI/float] 取不到 {} 的悬停文字: {}".format(getattr(item, "ItemId", "?"), error_text(e)))

    def MenuActions(self):  # type: () -> tuple
        return MenuKey.Source, MenuKey.Uses, MenuKey.Bookmark, MenuKey.RecipeTree

    def MenuKind(self):  # type: () -> any
        return MenuKindText.Item

    def ContentKey(self):  # type: () -> any
        return self.Item

    def HasMeiTooltip(self):  # type: () -> bool
        return False

    def TooltipContent(self):  # type: () -> any
        return None


def resolve_target(main, focus):  # type: (any, any) -> any
    """
    主节点 FocusAt 认出的这一点该给菜单什么：MEI 自己的格子给它的面板（有动作才算），别的界面的物品格给 SlotTarget；
    认不出物品（不在物品表里）给 None
    """
    if focus is None:
        return None
    panel = getattr(focus, "Panel", None)
    if panel is not None:
        ask = getattr(panel, "MenuActions", None)
        return panel if callable(ask) and ask() else None
    hit, item = getattr(focus, "Hit", None), getattr(focus, "Item", None)
    return SlotTarget(main, hit, item) if hit is not None and item is not None else None


class FindMode(object):
    """
    查找状态：点一下查询按钮进来，下一次点哪就查哪 —— 焦点探针认出那一格，在那儿出它的二级菜单，然后退出；
    没认出来什么都不做（没找到不给反馈）。只在触屏用
    """
    def __init__(self, main, on_change):
        self.MainNode = main
        self.Active = False  # type: bool
        self.OnChange = on_change  # fn(active)：两个查询按钮跟着变样子
        self.Capture = None  # type: any  # 捕获层的按钮控件：留着它，回调存在它身上
        self.__Tap = None  # type: tuple or None  # 捕获层收到的点，下一帧处理（按钮回调里只记下）

    def OnCreate(self):
        """ 开界面：挂捕获层的点击回调；不在查找状态、捕获层藏着（界面状态跨开关存活，引擎结论 §22）"""
        control = self.MainNode.GetUIControl(UiPathConst.FindCapture)
        self.Capture = control.asButton() if control is not None else None
        if self.Capture is not None:
            self.Capture.AddTouchEventParams({"isSwallow": True})
            self.Capture.SetButtonTouchUpCallback(self.OnTap)
        self.Exit()

    def Toggle(self):
        if self.Active:
            self.Exit()
        else:
            self.Enter()

    def Enter(self):
        """ 进查找状态：先收起开着的菜单，显出捕获层（焦点探针查询时才找，不用挂）"""
        menu = getattr(self.MainNode, "Menu", None)
        if menu is not None:
            menu.Close()
        self.Active = True
        self.__Tap = None
        self.__ShowCapture(True)
        self.OnChange(True)

    def Exit(self):
        """ 退出查找状态（查完了、取消了）"""
        self.Active = False
        self.__Tap = None
        self.__ShowCapture(False)
        self.OnChange(False)

    def OnTap(self, args):
        """ 捕获层的点击（引擎的按钮回调）：只记下点在哪 """
        self.__Tap = touch_point(args)

    def Update(self):
        """ 每帧：捕获层收到了点就查那一点（主节点 FocusAt）、退出查找状态；认出来就交给触屏菜单（它下一帧开）"""
        tap, self.__Tap = self.__Tap, None
        if tap is None or not self.Active:
            return
        main = self.MainNode
        target = resolve_target(main, main.FocusAt(tap[0], tap[1]))
        self.Exit()
        menu = getattr(main, "Menu", None)
        if target is not None and menu is not None:
            menu.Request(target)

    def __ShowCapture(self, on):
        control = self.MainNode.GetUIControl(UiPathConst.FindCapture)
        if control is not None:
            control.SetVisible(on)
