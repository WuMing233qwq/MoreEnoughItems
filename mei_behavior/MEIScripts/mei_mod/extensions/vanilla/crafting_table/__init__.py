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
工作台合成。一个配方类型一个包，包门面声明该类型的 Category 与 Source。
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import CraftingTableSource
from .transfer import CraftingTransferPolicy
from .ui_script import CraftingTableUIScript

CATEGORY = RecipeCategory(
    category_id="crafting_table",
    name_key="mei.recipe.category.crafting_table",
    icon=("minecraft:crafting_table", 0),
    control_def="MeiCraftingTable.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:crafting_table", "minecraft:crafter"]),
    sort_index=0,
)
""" 类型标识与展示元数据；control_def 是 JSON UI 的 namespace.control_name（tooltip 预览缺省按它推出 <namespace>.PREVIEW）"""

SOURCE = CraftingTableSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

POLICY = CraftingTransferPolicy
""" 转移策略类，同样由扩展实例化后挂到 CATEGORY 上 """

UI_SCRIPT = CraftingTableUIScript
""" 配方页脚本 """
