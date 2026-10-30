# coding=utf-8

# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
配方页 UI 门面。ui 是长路径重灾区，故再分七组：控件 / 槽位 / 绑定 / 挂 MEI 的界面 / 工具模式的放置目标 / 按界面登记的配方转移 /
在 MEI 里做事。
"""


class UiFacade(object):
    """ ctx.UI —— 七组各自成子门面, 用起来是 ctx.UI.Controls.ItemPanel """

    __slots__ = ("Controls", "Slots", "Binding", "Screens", "Drops", "Transfers", "Actions")

    def __init__(self, owner=""):
        # 七个子模块顶层都拉 ui_script, 放构造里而不是模块顶层
        from .actions import ActionsFacade
        from .binding import BindingFacade
        from .controls import ControlsFacade
        from .drops import DropsFacade
        from .screens import ScreensFacade
        from .slots import SlotsFacade
        from .transfers import TransfersFacade
        self.Controls = ControlsFacade()
        self.Slots = SlotsFacade()
        self.Binding = BindingFacade()
        self.Screens = ScreensFacade()
        self.Drops = DropsFacade(owner)  # owner：扩展的 ID，放置目标记在它名下
        self.Transfers = TransfersFacade(owner)  # 同上，转移目标也记在它名下
        self.Actions = ActionsFacade()
