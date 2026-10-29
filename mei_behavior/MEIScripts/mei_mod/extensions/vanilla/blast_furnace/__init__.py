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
高炉烧炼：引擎的熔炉配方换 tag（blast_furnace，矿石、铁 / 金的工具与盔甲回炉）—— 格式与熔炉一模一样（CLAUDE.md 引擎结论 §45）。
配方页、燃料格、tooltip 预览都用熔炉那一套（MeiFurnace）：它也烧燃料，燃料表就是熔炉扩展那一份（furnace/fuels.py）
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from ..furnace.ui_script import FurnaceUIScript
from .source import BlastFurnaceSource

CATEGORY = RecipeCategory(
    category_id="blast_furnace",
    name_key="mei.recipe.category.blast_furnace",
    icon=("minecraft:blast_furnace", 0),
    control_def="MeiFurnace.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:blast_furnace"]),
    sort_index=11,
)

SOURCE = BlastFurnaceSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = FurnaceUIScript
""" 配方页脚本：熔炉那一份（燃料格、火焰、箭头）"""
