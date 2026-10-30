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
药水酿造：酿造台的配方，两种 —— 混合酿造（药水 + 催化剂 → 另一种药水）、换容酿造（药水 + 火药 / 龙息 → 喷溅 / 滞留型）。
引擎的酿造查询很特别（CLAUDE.md 引擎结论 §45）：药水按类型全名查、不认 tag 与 aux，按催化剂查不到 —— 来源自己凑全表、自己建桶（source.py）；
药水的 aux ↔ 类型名直接映射（potions.py）。三种瓶子 aux 1 ~ 46 的药水物品表里本来没有，由原版扩展的创造栏表加（creative/）
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import BrewingSource
from .ui_script import BrewingUIScript

CATEGORY = RecipeCategory(
    category_id="brewing_stand",
    name_key="mei.recipe.category.brewing_stand",
    icon=("minecraft:brewing_stand", 0),
    control_def="MeiBrewing.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:brewing_stand"]),
    sort_index=17,
)

SOURCE = BrewingSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = BrewingUIScript
""" 配方页脚本：照原版酿造台 —— 上面催化剂、下面三瓶药水（同一个绑定名），右上产物 """
