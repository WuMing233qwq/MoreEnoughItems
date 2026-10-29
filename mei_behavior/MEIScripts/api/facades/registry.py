# coding=utf-8

# ----------------------------------------------------------------------
#  registry.py is part of MoreEnoughItems.
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
注册面：往 MEI 里登记东西。模块级名字即公共 API，ctx.Registry 只是它的对象形态。
"""
from MEIScripts.registry import (
    ItemFactory, ItemManager, ItemOrganizer,
    RecipeManager, RecipeUIManager, SourceRegistry,
)
# 搜索索引刻意不进 registry 门面(包门面急加载那条债), 从模块直取
from MEIScripts.registry.search import ItemSearchIndex
from MEIScripts.registry.transfer import TransferRegistry

__all__ = [
    "ItemFactory", "ItemManager", "ItemOrganizer", "ItemSearchIndex",
    "RecipeManager", "RecipeUIManager", "SourceRegistry", "TransferRegistry",
]


class RegistryFacade(object):
    """ ctx.Registry """

    __slots__ = tuple(__all__)

    def __init__(self):
        self.RecipeManager = RecipeManager
        self.RecipeUIManager = RecipeUIManager
        self.SourceRegistry = SourceRegistry
        self.ItemManager = ItemManager
        self.ItemFactory = ItemFactory
        self.ItemOrganizer = ItemOrganizer
        self.ItemSearchIndex = ItemSearchIndex
        self.TransferRegistry = TransferRegistry
