# coding=utf-8

# ----------------------------------------------------------------------
#  focus.py is part of MoreEnoughItems.
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
一个点上是什么（UIScriptMain.FocusAt）：MEI 自己的格子由 PanelAt 直接认，带上那个面板（收藏格有 Cell），
物品取面板上的 Item（Attr 齐全）；别的界面的格子由焦点探针（proxy/focus）认出渲染器（Hit），
按物品名 + 附加值去物品表里找（item_from_hit）。
"""
from MEIScripts.registry import ItemManager


class FocusTarget(object):
    """ 那一点上是什么：Pos 那一点（查找状态的触点、PC 的光标；取不到为 None）、Hit 焦点探针的命中（别的界面的格子才有）、
    Panel MEI 的格子面板、Item 物品 """

    def __init__(self, pos=None, hit=None, panel=None, item=None):
        self.Pos = pos  # type: tuple or None
        self.Hit = hit  # type: any
        self.Panel = panel  # type: any
        self.Item = item  # type: any

    @property
    def Cell(self):  # type: () -> any
        """ 收藏格的那一条（收藏栏面板的 Cell）；不是收藏格为 None """
        return getattr(self.Panel, "Cell", None) if self.Panel is not None else None


def item_from_hit(hit):  # type: (any) -> any
    """
    渲染器显示的物品在物品表里的那一个；不在表里返回 None。
    同名同附加值优先，没有就取同名的第一个 —— 工具的附加值是耐久损耗，按附加值精确找会把用过的剑认丢
    """
    if hit is None:
        return None
    items = ItemManager.GetItemsById(hit.ItemName)
    for item in items:
        if item.AuxValue == hit.AuxValue:
            return item
    return items[0] if items else None
