# coding=utf-8

# ----------------------------------------------------------------------
#  controls.py is part of MoreEnoughItems.
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
控件对象：物品面板与网格。
"""
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel, ItemsGrid
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.controls import GroupItemPanel
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.controls import (
    BroderItemPanel, HistoryItemsGrid,
)
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.controls import MultiItemPanel

__all__ = [
    "BroderItemPanel", "GroupItemPanel", "HistoryItemsGrid", "ItemPanel",
    "ItemsGrid", "MultiItemPanel",
]


class ControlsFacade(object):
    """ ctx.UI.Controls """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
