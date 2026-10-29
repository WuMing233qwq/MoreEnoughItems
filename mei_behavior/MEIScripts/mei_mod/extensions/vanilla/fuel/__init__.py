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
燃料（JEI / NEI 的 Fuel 页）：查一样东西的用途时，它能当熔炉燃料就多一页「燃料」，写着烧多久、能烧几个物品。
燃料表和熔炉的燃料格共用一份（furnace/fuels.py）；只有「用途」这个方向 —— 燃料不是做出来的，查来源永远没有。
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import FuelSource
from .ui_script import FuelUIScript

CATEGORY = RecipeCategory(
    category_id="fuel",
    name_key="mei.recipe.category.fuel",
    icon=("minecraft:coal", 0),
    control_def="MeiFuel.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker"]),
    sort_index=20,
)
""" 三种炉子都烧燃料（高炉、烟熏炉烧得快一倍、燃料也烧得快一倍，能烧的个数一样）；排在熔炉后面 """

SOURCE = FuelSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = FuelUIScript
""" 配方页脚本 """
