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
切制：切石机的配方。引擎给的是无序配方的形状 —— ingredients 一格 + result（带数量），tag 是 stonecutter（CLAUDE.md 引擎结论 §45）。
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import StonecutterSource
from .ui_script import StonecutterUIScript

CATEGORY = RecipeCategory(
    category_id="stonecutter",
    name_key="mei.recipe.category.stonecutter",
    icon=("minecraft:stonecutter_block", 0),
    control_def="MeiStonecutter.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:stonecutter_block"]),
    sort_index=14,
)

SOURCE = StonecutterSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = StonecutterUIScript
""" 配方页脚本：照原版切石机 —— 原料 → 箭头 → 产物（JSON recipes/stonecutter.json，命名空间 MeiStonecutter）"""
