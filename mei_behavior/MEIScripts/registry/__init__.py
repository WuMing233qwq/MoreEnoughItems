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

# 配方查询已回退为直查, index.py 随之删除. 现在的 tags.py 是另一样东西: 按 tag 查物品 / 方块(TagLookup,
# 3.10 起问引擎), 和旧的配方索引无关.
# 新模块不该由本门面急加载 —— 那会让只想用 ItemManager 的人白白拉起一整套设施
# (engineering.md 的「包门面急加载」那条债), 消费方直接 `from MEIScripts.registry.<模块> import ...` 即可.
from .items import ItemManager, ItemFactory
from .organizer import ItemOrganizer
from .recipes import RecipeUIManager, RecipeManager
from .sources import SourceRegistry

__all__ = [
    "ItemManager",
    "ItemFactory",
    "ItemOrganizer",
    "RecipeUIManager",
    "RecipeManager",
    "SourceRegistry",
]
