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
锻造：锻造台的配方，两种 —— 锻造转换（模板 + 物品 + 材料 → 新物品，原版就是九样下界合金升级）、
锻造纹饰（模板 + 盔甲 + 材料 → 同一件盔甲加上纹饰）。引擎给的都是无序配方的形状：ingredients 三格（模板、物品、材料）+ result；
纹饰的 result 是空表、三格是引擎展开的物品列表，按产物查不到（CLAUDE.md 引擎结论 §45）
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import SmithingSource
from .ui_script import SmithingUIScript

CATEGORY = RecipeCategory(
    category_id="smithing_table",
    name_key="mei.recipe.category.smithing_table",
    icon=("minecraft:smithing_table", 0),
    control_def="MeiSmithing.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:smithing_table"]),
    sort_index=16,
)

SOURCE = SmithingSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = SmithingUIScript
""" 配方页脚本：照原版锻造台 —— 模板、物品、材料挨着 → 箭头 → 产物 """
