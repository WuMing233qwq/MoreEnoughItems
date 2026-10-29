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
制图的配方来源：引擎透传，tag 是 cartography_table。
"""
from ..tools.parser import EngineRecipeSource
from .types import CartographyRecipe

CATEGORY_ID = "cartography_table"


class CartographySource(EngineRecipeSource):
    """ 一条配方：ingredients 一两格 + result（CLAUDE.md 引擎结论 §45）"""

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
            inputs = [one for one in inputs if one and one.get_stacks()]
            if inputs and outputs:
                result.append(CartographyRecipe(self.CategoryId, inputs[:2], outputs[:1]))
        return result
