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
模式本身（docs/architecture/modes.md）：全局一份，跨界面、跨存档（存在 prefs 里，关界面不复位）。

- 收藏栏顶栏最左边的模式按钮点一下轮换：普通 → 工具 → 作弊（作弊要服务端说是操作员才轮得到）。
- 每次开界面问一次服务端有没有作弊的权限；说没有而存着的是作弊 → 退回普通并记成普通。回答到之前照存着的来（真给的时候服务端还会再查）。
- 点 MEI 的一格（物品栏、收藏栏、最近浏览、配方页、工作站、配方树）先问 Intercept：作弊给物品、工具拿起来，接走了平时的点击就不做。
  组头（物品分组那一格）、空格、不是物品的条目不接，照平时。
- 按钮的颜色每个界面自己跟着 Revision 重染（ToolHost.Update），被盖住的界面露出来、栏后建出来都对得上
"""
from MEIScripts.common.classes.types import ItemStack
from MEIScripts.constants.ui import ItemsSidebarPath, ModeConst
from MEIScripts.mei_mod.network.protocol.client import AskCheatAccess, SendCheatGive
from MEIScripts.mei_mod.state import PrefsManager
from MEIScripts.utils import utilities
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from .state import checked_mode, next_mode, whole_stack


def is_touch():  # type: () -> bool
    try:
        return utilities.GetInputMode() == 1
    except Exception:  # noqa
        return False


def stack_of(panel):  # type: (any) -> ItemStack or None
    """
    这一格拿起 / 给的是什么：显示着的那一样物品，数量 1。配方收藏、配方树收藏给它显示的那一样（BookmarkItemPanel.Item），
    轮播格给当前轮到的。组头、空格、不是物品的条目（流体之类）给 None
    """
    if panel is None or getattr(panel, "IsGroupHead", False):
        return None
    stack = getattr(panel, "Stack", None)
    if stack is not None and getattr(stack, "KIND", "item") != "item":
        return None
    item = getattr(panel, "Item", None)
    if item is None:
        return None
    return ItemStack(item, 1)


class __ModeManager(object):  # noqa

    def __init__(self):
        self.Mode = None  # type: str or None  # 第一次用到才从 prefs 读
        self.CheatAllowed = None  # type: any  # 服务端最近一次答的：True / False；还没答到、超时、出错是 None
        self.Revision = 0  # type: int  # 模式每变一次加一：各界面的按钮按它重染
        self.__Asking = 0  # type: int  # 问权限的序号：只认最后一次问的回答

    def Current(self):  # type: () -> str
        if self.Mode is None:
            self.Mode = PrefsManager.GetMode()
        return self.Mode

    def SetMode(self, mode):  # type: (str) -> bool
        """ 换成这一种并存下来；没变返回 False """
        if mode not in ModeConst.Order or mode == self.Current():
            return False
        self.Mode = mode
        try:
            PrefsManager.SetMode(mode)
        except Exception as e:  # noqa
            logger.error("[MEI/mode] 存模式失败: {}".format(error_text(e)))
        self.Revision += 1
        return True

    def Cycle(self, _args=None):  # type: (any) -> bool
        """ 点了模式按钮：轮到下一种（触摸回调，不在绑定回调里）"""
        return self.SetMode(next_mode(self.Current(), self.CheatAllowed))

    def OnScreenOpen(self):
        """ 开界面：问一次服务端有没有作弊的权限（答回来之前照存着的来）"""
        self.__Asking += 1
        asking = self.__Asking

        def __on_result(allowed):
            if asking == self.__Asking:
                self.SetAccess(allowed)

        try:
            AskCheatAccess(__on_result)
        except Exception as e:  # noqa
            logger.error("[MEI/mode] 问作弊权限失败: {}".format(error_text(e)))

    def SetAccess(self, allowed):  # type: (any) -> None
        """ 服务端答了：说没有而现在是作弊 → 退回普通并存下来；None（不知道）不动 """
        if allowed is None:
            return
        self.CheatAllowed = bool(allowed)
        mode = checked_mode(self.Current(), self.CheatAllowed)
        if mode != self.Current():
            logger.info("[MEI/mode] 没有操作员权限，切回普通模式")
            self.SetMode(mode)

    # 点格子
# ======================================================================================================================
    def Intercept(self, panel, secondary=False):  # type: (any, bool) -> bool
        """
        点了 MEI 的一格（点击绑定的回调里）：作弊、工具模式接走返回 True，调用方不再走平时的点击。
        工具模式要这个界面有拿起的宿主（main.Tool）—— 配方树没有，照平时
        """
        mode = self.Current()
        if mode == ModeConst.Normal:
            return False
        stack = stack_of(panel)
        if stack is None:
            return False
        if mode == ModeConst.Cheat:
            return self.Give(stack.Item, whole_stack(secondary, is_touch()))
        host = getattr(getattr(panel, "MainNode", None), "Tool", None)
        if host is None:
            return False
        return host.RequestLift(stack, panel)

    def Give(self, item, whole=True):  # type: (any, bool) -> bool
        """ 作弊模式：让服务端给一组（whole）或一个。服务端说不行就退回普通 """
        if item is None:
            return False

        def __on_result(body):
            if isinstance(body, dict) and body.get("allowed") is False:
                self.SetAccess(False)

        try:
            return SendCheatGive(item, whole, __on_result)
        except Exception as e:  # noqa
            logger.error("[MEI/mode] 作弊给物品失败: {}".format(error_text(e)))
            return False

    # 按钮
# ======================================================================================================================
    def Paint(self, main):  # type: (any) -> bool
        """
        这个界面的模式按钮染成现在这一种的颜色（ore_style_button 平时、悬停两张脸的图标；按下那张 JSON 里有自己的颜色）。
        收藏栏没建（「显示左侧栏」关着、注入的界面还没展开）就什么都不做，返回 False
        """
        sidebar = getattr(main, "ItemsSidebarIns", None)
        if sidebar is None or not getattr(sidebar, "Inited", False):
            return False
        color = ModeConst.Colors.get(self.Current(), ModeConst.Colors[ModeConst.Normal])
        painted = False
        for sub in ModeConst.IconSubs:
            icon = main.GetUIControl(ItemsSidebarPath.ModeButton + sub)
            if icon is None:
                continue
            try:
                icon.asImage().SetSpriteColor(color)
                painted = True
            except Exception:  # noqa  图标还没建
                pass
        return painted


ModeManager = __ModeManager()
