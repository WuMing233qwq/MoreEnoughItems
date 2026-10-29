# coding=utf-8

# ----------------------------------------------------------------------
#  source.py is part of MoreEnoughItems.
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
燃料页的来源：表在自己手上（就是熔炉的燃料表），能给全量；配方当场造（便宜，Id 由内容算、每次一样）。
"""
from MEIScripts.api.facades.types import Ingredient, RecipeSource

from ..furnace.fuels import burn_seconds, fuel_items, is_fuel
from .types import FuelRecipe

CATEGORY_ID = "fuel"


def fuel_recipe(item):  # type: (any) -> FuelRecipe
    """ 一样燃料的那一页 """
    return FuelRecipe(CATEGORY_ID, [Ingredient([item.stack(1)], 1)], [], data={"seconds": burn_seconds(item)})


class FuelSource(RecipeSource):
    """ 只答「用途」：查来源永远是空的 """

    CAN_ENUMERATE = True
    """ 燃料表在自己手上，GetAll 给的就是全部（以后工作站视图查熔炉时直接用）"""

    def __init__(self):
        self.CategoryId = CATEGORY_ID

    def QueryByOutput(self, item):
        return []

    def QueryByInput(self, item):
        return [fuel_recipe(item)] if is_fuel(item) else []

    def GetAll(self):
        return [fuel_recipe(item) for item in fuel_items()]
