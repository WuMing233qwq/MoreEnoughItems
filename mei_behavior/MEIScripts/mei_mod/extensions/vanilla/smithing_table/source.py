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
锻造的配方来源：引擎透传，tag 是 smithing_table。纹饰配方按产物查不到（它的 result 是空的），只在查模板、盔甲、材料的用途时出现。
"""
from MEIScripts.api.facades.types import Ingredient

from ..tools.parser import EngineRecipeSource
from .types import SmithingTransformRecipe, SmithingTrimRecipe

CATEGORY_ID = "smithing_table"


class SmithingSource(EngineRecipeSource):
    """ 一条配方：ingredients 三格（模板、物品、材料）+ result（纹饰是空表）"""

    SCAN_BY = "input"
    """ 全量扫描按原料问：纹饰配方按产物查不到，按原料扫才凑得全（转换配方按原料也都查得到，同一条按 Id 去重）"""

    def __init__(self):
        EngineRecipeSource.__init__(self, CATEGORY_ID)

    def QueryByOutput(self, item):
        return self.GetRecipesByResult(item)

    def QueryByInput(self, item):
        return self.GetRecipesByInput(item)

    def ParseRecipe(self, raw_list):  # type: (list) -> list
        result = []
        for raw_dict in raw_list or ():
            parts = self.ParseShapelessParts(raw_dict)
            if parts is None:
                continue
            inputs, outputs = parts
            if len(inputs) != 3 or not inputs[1].get_stacks():
                continue
            if raw_dict.get("result"):
                # 锻造转换：产物认不出（物品表里没有）就不收，不能当成纹饰
                if outputs:
                    result.append(SmithingTransformRecipe(self.CategoryId, inputs, outputs[:1]))
                continue
            base = inputs[1]
            result.append(SmithingTrimRecipe(self.CategoryId, inputs,
                                             [Ingredient(list(base.get_stacks()), 1, tag_id=base.TagId)]))
        return result
