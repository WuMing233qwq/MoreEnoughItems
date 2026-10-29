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
药水酿造的配方数据模型：两格原料依次是药水、催化剂，一格产物。LORE 是格子上多出来的那一行说明（.lang 的键）。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class BrewingRecipe(Recipe):
    """ 酿造：一样东西 + 催化剂 → 一样东西（第三方加的、两头都不是药水的照字面收成这一类）"""

    __slots__ = ()

    LORE = None


@register_recipe_class
class BrewingMixRecipe(BrewingRecipe):
    """
    混合酿造：药水 + 催化剂 → 另一种药水。药水那两格各是三种瓶子的同一种药水（普通、喷溅、滞留），
    整页轮播同相位 —— 普通对普通、喷溅对喷溅
    """

    __slots__ = ()

    LORE = "mei.recipe.brewing.bottles"


@register_recipe_class
class BrewingContainerRecipe(BrewingRecipe):
    """ 换容酿造：一种药水 + 火药 / 龙息 → 同一种药水换个瓶子（喷溅 / 滞留）；按药水类型一条一条列 """

    __slots__ = ()
