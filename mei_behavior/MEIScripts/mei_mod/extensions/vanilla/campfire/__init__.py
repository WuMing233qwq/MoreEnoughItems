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
营火烘烤：引擎的熔炉配方换 tag（campfire）—— 只有食物，格式与熔炉一模一样；灵魂营火（soul_campfire）查到的
和营火一条不差（CLAUDE.md 引擎结论 §45），所以并成一个类型、两个工作站。不烧燃料、不要合成条：
配方页是「原料、点着的营火模型、熟的」（MeiCampfire；模型由纸娃娃控件渲染，model.py）
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import RecipeCategory

from .source import CampfireSource
from .ui_script import CampfireUIScript

CATEGORY = RecipeCategory(
    category_id="campfire",
    name_key="mei.recipe.category.campfire",
    icon=("minecraft:campfire", 0),
    control_def="MeiCampfire.RECIPES_GRID",
    stations=ItemFactory.GetStacksFromIds(["minecraft:campfire", "minecraft:soul_campfire"]),
    sort_index=13,
)

SOURCE = CampfireSource
""" 配方来源类，由扩展在 OnRegister 里实例化 """

UI_SCRIPT = CampfireUIScript
""" 配方页脚本：原料 → 点着的营火模型 → 熟的 """
