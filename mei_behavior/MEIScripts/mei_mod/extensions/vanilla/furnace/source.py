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
熔炉配方来源。燃料不在配方里（驱动机器的东西不是配方的内容），配方页的燃料格问 fuels.py。
"""
from MEIScripts.api.facades.types import Ingredient
from MEIScripts.api.facades.utils import logger

from ..tools.parser import EngineRecipeSource
from .types import FurnaceRecipe

CATEGORY_ID = "furnace"


class FurnaceSource(EngineRecipeSource):
    """ 熔炉：引擎透传 """

    def __init__(self, category_id=CATEGORY_ID):  # type: (str) -> None
        """ category_id 也是查引擎用的 tag：高炉、烟熏炉、营火是同一种熔炉配方换个 tag（CLAUDE.md 引擎结论 §45）"""
        EngineRecipeSource.__init__(self, category_id)
        self.UnknownOutputs = set()  # type: set  # 认不出的 output 形态（只记一次）

    def QueryByOutput(self, item):
        return self.GetRecipesByResult(item)

    def QueryByInput(self, item):
        return self.GetRecipesByInput(item)

    def ParseRecipe(self, raw_list):  # type: (list) -> list
        result = []
        for raw_dict in raw_list or ():
            recipe = self.HandleFurnace(raw_dict)
            if recipe:
                result.append(recipe)
        return result

    def _furnace_input(self, raw):  # type: (any) -> Ingredient or None
        """
        input：字符串是一种物品（'ns:id[:aux]'）；list 是引擎把 tag 展开成的几种 —— 多候选、按公共 tag 折叠，和工作台一样
        （原先只取第一个候选：别的候选丢了，Id 也只跟着第一个）
        """
        if isinstance(raw, basestring):
            stack = self.ParseStackFromString(raw, 1)
            return Ingredient([stack], 1) if stack else None
        if isinstance(raw, list):
            stacks = [s for s in (self.ParseStackFromString(one, 1) for one in raw) if s]
            return self.MakeListIngredient(stacks, 1) if stacks else None
        return None

    def _furnace_output(self, raw):  # type: (any) -> any
        """
        output：数量 1 是字符串（'ns:id[:aux]'）；**数量大于 1 是 dict**（SDK 文档；不认的话这类配方会被静默丢掉。没见过真实样本，
        键名照工作台产物与 SDK 的写法都试）；list 取第一个能解析的
        """
        if isinstance(raw, basestring):
            return self.ParseStackFromString(raw, 1)
        if isinstance(raw, dict):
            name = raw.get("item") or raw.get("itemName") or raw.get("identifier")
            count = raw.get("count", 1) or 1
            aux = raw.get("data", raw.get("aux", raw.get("auxValue", 0))) or 0
            stack = None
            if isinstance(name, basestring):
                stack = (self.ParseStackFromString(name, count) if name.count(":") == 2
                         else self._safe_stack(name, aux, count))
            if stack is None:
                self.__ReportOutput(raw)
            return stack
        if isinstance(raw, list):
            for one in raw:
                stack = self.ParseStackFromString(one, 1)
                if stack:
                    return stack
        return None

    def __ReportOutput(self, raw):
        """ 认不出的 output：记一行（同一种形态只记一次），在游戏里看到了好补 """
        shape = tuple(sorted(raw.keys())) if isinstance(raw, dict) else type(raw).__name__
        seen = getattr(self, "UnknownOutputs", None)
        if seen is None:
            seen = self.UnknownOutputs = set()
        if shape not in seen:
            seen.add(shape)
            logger.warn("[MEI/furnace] 认不出的熔炉产物: {!r}".format(raw))

    def HandleFurnace(self, raw_dict):  # type: (dict) -> FurnaceRecipe or None
        """ 一条熔炉配方：一样原料（可能是多候选）→ 一样产物；**不带燃料**（燃料格问 fuels.py，Recipe.Id 也就不随燃料变）"""
        try:
            ingredient = self._furnace_input(raw_dict["input"])
            out_stack = self._furnace_output(raw_dict["output"])
            if not ingredient or not out_stack:
                return None
            outputs = [o for o in (self._to_output(out_stack),) if o]
            return FurnaceRecipe(self.CategoryId, [ingredient], outputs)
        except (KeyError, TypeError, ValueError):  # 一条认不出只丢这一条（同 ParseShapelessParts）
            return None

