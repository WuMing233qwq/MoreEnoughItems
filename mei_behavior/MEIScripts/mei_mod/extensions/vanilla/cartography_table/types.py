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
制图的配方数据模型。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class CartographyRecipe(Recipe):
    """ 制图：一两样原料（上面一格、下面一格）→ 一样产物 """

    __slots__ = ()

    INPUTS_ORDERED = False
    """ 引擎给的是无序配方的形状：原料的先后不进 Id（显示照引擎给的顺序，上面一格是第一样）"""
