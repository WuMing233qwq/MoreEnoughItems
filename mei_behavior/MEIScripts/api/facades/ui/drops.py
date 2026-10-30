# coding=utf-8

# ----------------------------------------------------------------------
#  drops.py is part of MoreEnoughItems.
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
工具模式的放置目标（docs/modding/05-screens-and-tools.md §2，docs/architecture/modes.md）：玩家在工具模式下拿起 MEI 的一样物品、
再点到你登记的控件上，MEI 回调 callback(名字, ItemStack) —— 名字是登记时给的别名，没给就是控件路径；ItemStack 数量是 1。
纯新增，不升 API_VERSION，第三方用 getattr 探测
"""
from MEIScripts.mei_mod.ui_script.mei_ui.modes.drops import ANY_SCREEN, DropTargets


class DropsFacade(object):
    """ ctx.UI.Drops：登记都记在这个扩展名下，扩展卸载时 MEI 兜底撤掉（自己在 OnUnload 里撤也行）"""

    __slots__ = ("Owner", "ANY_SCREEN")

    def __init__(self, owner=""):
        self.Owner = owner or ""  # type: str
        self.ANY_SCREEN = ANY_SCREEN

    def Register(self, screen_def, path, callback, alias=None, point=False):
        # type: (str, str, callable, any, bool) -> str or None
        """
        登记一个放置目标：screen_def 是界面名（与 PushScreenEvent 的 screenDef 一样；ANY_SCREEN 或 None 是哪个界面都算），
        path 是那个界面里的控件路径（ScreenNode.GetBaseUIControl 用的那种），alias 是回调拿到的名字（不给就拿到路径）。
        point=True 时回调是 callback(名字, ItemStack, (x, y))：多给点下去那一点的全局坐标（一个目标盖住几格时自己算哪一格）。
        返回记号（Unregister 用）；路径、回调不对给 None。点中时那个控件要看得见；几个都中取面积最小的（套着的取里面那个）
        """
        return DropTargets.Register(screen_def, path, callback, alias=alias, owner=self.Owner, point=point)

    def Unregister(self, token):
        # type: (str) -> bool
        return DropTargets.Unregister(token)

    def UnregisterAll(self):
        # type: () -> int
        """ 撤掉这个扩展登记的全部，返回撤了几个 """
        return DropTargets.UnregisterOwner(self.Owner)

    @staticmethod
    def Held():
        # type: () -> any
        """ 当前界面工具模式拿着的 ItemStack；没拿着给 None。想在拿着时把自己的放置区亮起来，就在自己界面的每帧里问它 """
        from MEIScripts.mei_mod.ui_script.mei_ui import context
        main = context.GetMainNode()
        tool = getattr(main, "Tool", None) if main is not None else None
        return getattr(tool, "Held", None)
