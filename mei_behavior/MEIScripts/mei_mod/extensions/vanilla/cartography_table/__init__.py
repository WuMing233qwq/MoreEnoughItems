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
制图：制图台的配方。引擎给的是无序配方的形状（ingredients 一两格 + result），tag 是 cartography_table；
原版只有两条：纸 → 空地图、纸 + 指南针 → 空定位地图（empty_map 的 aux 2，由原版扩展的创造栏表加进物品表，creative/）。
复制、扩大、锁定地图是写死在引擎里的，查不到（CLAUDE.md 引擎结论 §45）
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import CartographySource
from .ui_script import CartographyUIScript

CATEGORY = RecipeCategory(
    category_id="cartography_table",
    name_key="mei.recipe.category.cartography_table",
    icon=("minecraft:cartography_table", 0),
    control_def="MeiCartography.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:cartography_table"]),
    sort_index=15,
)

SOURCE = CartographySource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = CartographyUIScript
""" 配方页脚本：照原版制图台 —— 原料、加号、附加原料一列 → 箭头 → 地图 → 箭头 → 产物 """
