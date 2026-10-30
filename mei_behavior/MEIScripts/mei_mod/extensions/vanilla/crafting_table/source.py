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
工作台配方来源。
"""
from MEIScripts.api.facades.types import Ingredient

from ..tools.parser import EngineRecipeSource
from .types import ShapedRecipe, ShapelessRecipe

CATEGORY_ID = "crafting_table"


class CraftingTableSource(EngineRecipeSource):
    """ 工作台：引擎透传 """

    # 引擎对床/楼梯这类会返回内容完全相同的多条（第三方模组同样复现，非本仓造成），
    # 去重在 RecipeManager 合并多来源时统一做，本类不重复处理

    def __init__(self):
        EngineRecipeSource.__init__(self, CATEGORY_ID)

    def QueryByOutput(self, item):
        return self.GetRecipesByResult(item)

    def QueryByInput(self, item):
        return self.GetRecipesByInput(item)

    def ParseRecipe(self, raw_list):  # type: (list) -> list
        """ 工作台的一条原始配方要么是有序的要么是无序的，依次试 """
        result = []
        for raw_dict in raw_list or ():
            recipe = self.HandleShaped(raw_dict) or self.HandleShapeless(raw_dict)
            if recipe:
                result.append(recipe)
        return result

    def HandleShaped(self, raw_dict):  # type: (dict) -> ShapedRecipe or None
        try:
            pattern = raw_dict["pattern"]
            key = raw_dict["key"]  # type: dict
            result = raw_dict["result"]

            key_map = {}
            for _key in key:
                items = key[_key]
                if not isinstance(items, dict):
                    return None
                key_map[_key] = self.ParseIngredientFromDict(items)

            height = len(pattern)
            width = max([len(row) for row in pattern]) if pattern else 0

            # 按 pattern 铺平为 width*height 槽, 空格/未定义字符为空 Ingredient
            inputs = []
            for row_index in range(height):
                row = pattern[row_index]
                for col in range(width):
                    char = row[col] if col < len(row) else " "
                    inputs.append(key_map.get(char, Ingredient([])))

            outputs = [o for o in (self._to_output(self.ParseStackFromDict(r)) for r in result) if o]

            return ShapedRecipe(self.CategoryId, inputs, outputs, width, height, list(pattern))
        except (KeyError, TypeError, ValueError):  # 一条认不出只丢这一条（同 ParseShapelessParts）
            return None

    def HandleShapeless(self, raw_dict):  # type: (dict) -> ShapelessRecipe or None
        try:
            ingredients = raw_dict["ingredients"]
            result = raw_dict["result"]

            inputs = [self.ParseIngredientFromDict(i) for i in ingredients]
            outputs = [o for o in (self._to_output(self.ParseStackFromDict(r)) for r in result) if o]

            return ShapelessRecipe(self.CategoryId, inputs, outputs)
        except (KeyError, TypeError, ValueError):  # 一条认不出只丢这一条（同 ParseShapelessParts）
            return None

