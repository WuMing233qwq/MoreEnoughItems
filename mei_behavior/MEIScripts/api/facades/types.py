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
数据模型：构造配方与物品。零引擎依赖，扩展的 <type>/types.py 可放心 import。
"""
from MEIScripts.common.classes.types.transfer import (
    TransferContext, TransferEntry, TransferPlan, TransferResult,
)
from MEIScripts.common.classes.base import ItemSource, SlotTarget
from MEIScripts.common.classes.base import RecipeSource
from MEIScripts.common.classes.sources import StaticRecipeSource
from MEIScripts.common.classes.types import (
    Ingredient, Item, ItemAttr, ItemInfo, ItemSpec, ItemStack,
    KIND_BLOCK, KIND_PLAYER, Recipe,
    RecipeCategory, Stack, get_recipe_class, keys, register_recipe_class,
)
from MEIScripts.common.classes.types.ingredient import IngredientLike

__all__ = [
    "Ingredient", "IngredientLike", "Item", "ItemAttr", "ItemInfo", "ItemStack",
    "ItemSource", "ItemSpec", "KIND_BLOCK", "KIND_PLAYER", "Recipe", "RecipeCategory",
    "SlotTarget",
    "RecipeSource", "Stack", "TransferContext", "TransferEntry",
    "TransferPlan", "TransferResult",
    "StaticRecipeSource", "get_recipe_class", "keys", "register_recipe_class",
]


class TypesFacade(object):
    """ ctx.Types """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
