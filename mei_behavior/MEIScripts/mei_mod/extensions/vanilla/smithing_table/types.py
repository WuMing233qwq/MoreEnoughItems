# coding=utf-8

# ----------------------------------------------------------------------
#  types.py is part of MoreEnoughItems.
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
锻造的配方数据模型：三格原料依次是模板、物品、材料。LORE 是产物格多出来的那一行说明（.lang 的键）。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class SmithingTransformRecipe(Recipe):
    """ 锻造转换：模板 + 物品 + 材料 → 新物品（保留原物品的附魔与耐久）"""

    __slots__ = ()

    LORE = "mei.recipe.smithing.transform"


@register_recipe_class
class SmithingTrimRecipe(Recipe):
    """
    锻造纹饰：模板 + 盔甲 + 材料 → 同一件盔甲加上纹饰。引擎给的 result 是空的，产物这一格画成和「盔甲」那一格同一组候选 ——
    配方页的轮播整页同相位，两格一一对上（画不出纹饰本身，说明写在 LORE 里）
    """

    __slots__ = ()

    LORE = "mei.recipe.smithing.trim"
