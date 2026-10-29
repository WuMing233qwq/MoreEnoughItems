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
熔炉的配方数据模型。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class FurnaceRecipe(Recipe):
    """
    烧炼配方: 单输入 (可以是多候选) 单输出.

    **不带燃料** (燃料是驱动机器的、不参与合成, 不进配方本身, 也不用存) ——
    配方页的燃料格问 fuels.py. 原先燃料是字面展开的全部燃料物品、走 Catalysts 计入 Recipe.Id,
    装卸任何带燃料的模组所有熔炉配方都变 Id; 拿掉之后这件事也就没了.
    """

    __slots__ = ()
