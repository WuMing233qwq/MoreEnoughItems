# coding=utf-8

# ----------------------------------------------------------------------
#  panel.py is part of MoreEnoughItems.
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
from MEIScripts.common.classes.types import Item
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel


class BroderItemPanel(ItemPanel):
    """
    BroderItemPanel 为类似 GroupItemPanel的实现
    但是仅对ItemPanel扩展了边框渲染的功能
    """
    def __init__(self, control):
        ItemPanel.__init__(self, control=control)
        self.BackgroundVisible = False
        self.BorderLeftVisible = False
        self.BorderRightVisible = False
        self.BorderTopVisible = False
        self.BorderBottomVisible = False

    def HideBorders(self):
        """ 隐藏所有边(如果它可见) """
        self.BackgroundVisible = False
        self.BorderLeftVisible = False
        self.BorderRightVisible = False
        self.BorderTopVisible = False
        self.BorderBottomVisible = False

    def SetBorders(self, borders):
        """ 设置分组物品需要显示的边 """
        self.HideBorders()
        self.BackgroundVisible = True
        for edge in borders:
            if edge == 0:
                self.BorderTopVisible = True
            elif edge == 1:
                self.BorderBottomVisible = True
            elif edge == 2:
                self.BorderLeftVisible = True
            elif edge == 3:
                self.BorderRightVisible = True

    def SetBorderedItemData(self, item):  # type: (Item) -> None
        self.SetItemStack(item.stack(count=1))
        if not self.GetChildVisible():
            self.SetChildVisible(True)

    def SetBorder(self):  # type: () -> None
        """ 仅显示边框，不显示 ItemRenderer，用于空槽轮廓 """
        self.SetChildVisible(False)
        self.OverlayControlVisible = False
        self.ItemRendererVisible = False

    @classmethod
    def from_item_with_borders(cls, control, item, edges):
        ins = cls(control)
        ins.SetBorderedItemData(item)
        ins.SetBorders(edges if edges else [])
        return ins

    @classmethod
    def from_borders(cls, control, edges):
        ins = cls(control)
        ins.SetBorder()
        ins.SetBorders(edges if edges else [])
        return ins
