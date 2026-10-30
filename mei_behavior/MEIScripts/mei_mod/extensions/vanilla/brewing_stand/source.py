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
药水酿造的来源。引擎这一类查询很特别（CLAUDE.md 引擎结论 §45）：
- 药水按类型全名查（minecraft:potion_type:<名字>），不认 tag 与 aux；**按催化剂查一条都查不到**（烈焰粉、火药都是 0）；
- 混合配方 {input: 药水类型, reagent: 物品, output: 药水类型}，换容配方 {input: minecraft:potion, reagent: 火药, output: minecraft:splash_potion}。
所以不逐个转发：第一次用到时凑全表 —— 每种药水类型、每种瓶子各按原料查一遍（五十次，一次性），之后按产物、原料、催化剂都查自己建的桶。
- 混合配方：药水那两格各是三种瓶子的同一种药水（整页轮播同相位，普通对普通）；
- 换容配方：按药水类型一条一条列（水瓶、衰变药水也算），火药 / 龙息查用途就是这四十几条。
第三方往酿造台加的配方：原料是药水类型或这三种瓶子的收得进来（两头都不是药水的照字面收）；原料是别的物品的查不到（没有能列全的接口）
"""
import time

from MEIScripts.api.facades.types import Ingredient
from MEIScripts.api.facades.utils import error_text, logger, native_str

from ..tools.parser import EngineRecipeSource
from . import potions
from .types import BrewingContainerRecipe, BrewingMixRecipe, BrewingRecipe

CATEGORY_ID = "brewing_stand"


def _key(item):  # type: (any) -> tuple
    return item.stack(1).get_key()


class BrewingSource(EngineRecipeSource):
    """ 全表自己凑（第一次用到时），按产物 / 原料（含催化剂）各建一个桶 """

    CAN_ENUMERATE = True
    """ 全表是自己凑齐的：GetAll 给的就是全部 """

    def __init__(self):
        EngineRecipeSource.__init__(self, CATEGORY_ID)
        self.Recipes = None  # type: list or None  # 凑齐的全表（第一次用到才凑；重进世界时扩展卸了重装，表跟着重来）
        self.ByOutput = {}  # type: dict  # 物品键 -> [配方]
        self.ByInput = {}  # type: dict  # 物品键 -> [配方]（药水与催化剂）
        self.Unknown = set()  # type: set  # 认不出的药水类型名（只记一次）
        self.Queries = 0  # type: int  # 凑表时向引擎查了几次

    def QueryByOutput(self, item):
        self.Build()
        return list(self.ByOutput.get(_key(item), ()))

    def QueryByInput(self, item):
        self.Build()
        return list(self.ByInput.get(_key(item), ()))

    def GetAll(self):
        self.Build()
        return list(self.Recipes)

    def IsAllComplete(self):
        return True

    # 凑全表
# ======================================================================================================================
    def Build(self):
        if self.Recipes is not None:
            return
        self.Recipes = []  # 先占上：凑表中途出了意外，也不会每次查询都再问引擎五十次
        start = time.time()
        raws, seen = [], set()
        for name in [potions.POTION_TYPE + one for one in potions.TYPES] + list(potions.CONTAINERS):
            for raw in self.__Raw(name):
                triple = (native_str(raw.get("input")), native_str(raw.get("reagent")), native_str(raw.get("output")))
                if triple not in seen:
                    seen.add(triple)
                    raws.append(triple)
        recipes = []
        for triple in raws:
            try:
                recipes.extend(self.__Make(*triple))
            except Exception as e:  # noqa  物品表里没有的东西造物会抛（ItemFactory.CreateItem）：只少这一条
                logger.warn("[MEI/brewing] 这条酿造配方收不进来 {}: {}".format(triple, error_text(e)))
        self.Recipes = recipes
        self.ByOutput, self.ByInput = {}, {}
        for recipe in recipes:
            self.__Index(self.ByOutput, recipe.GetOutputs(), recipe)
            self.__Index(self.ByInput, recipe.GetInputs(), recipe)
        logger.info("[MEI/brewing] 酿造配方 {} 条（引擎给 {} 条，查了 {} 次，{} 毫秒）".format(
            len(recipes), len(raws), self.Queries, int((time.time() - start) * 1000)))

    def __Raw(self, name):  # type: (str) -> list
        """ 按原料查一种药水类型 / 瓶子；只要酿造配方的形状（带 reagent 的）"""
        self.Queries += 1
        try:
            result = self.RecipeComp.GetRecipesByInput(name, self.Tag, 0)
        except Exception as e:  # noqa  一种查炸了只少这一种，不能让整张表凑不起来
            logger.error("[MEI/brewing] 按原料查 {} 失败: {}".format(name, error_text(e)))
            return []
        return [raw for raw in result or () if isinstance(raw, dict) and "reagent" in raw]

    @staticmethod
    def __Index(bucket, ingredients, recipe):
        for ingredient in ingredients:
            for stack in ingredient.get_stacks():
                entries = bucket.setdefault(stack.get_key(), [])
                if recipe not in entries:
                    entries.append(recipe)

    def __Make(self, source, reagent, output):  # type: (str, str, str) -> list
        catalyst = self.__Plain(reagent)
        if catalyst is None:
            if reagent not in self.Unknown:
                self.Unknown.add(reagent)
                logger.warn("[MEI/brewing] 认不出的催化剂 {}（物品表里没有），这条酿造配方不收".format(reagent))
            return []
        if potions.type_name(source) is not None or potions.type_name(output) is not None:
            potion_in, potion_out = self.__Side(source), self.__Side(output)
            if potion_in is None or potion_out is None:
                return []
            return [BrewingMixRecipe(self.CategoryId, [potion_in, catalyst], [potion_out])]
        if source in potions.CONTAINERS and output in potions.CONTAINERS:
            made = []
            for aux in range(len(potions.TYPES)):
                bottle_in, bottle_out = self._safe_stack(source, aux, 1), self._safe_stack(output, aux, 1)
                if bottle_in and bottle_out:
                    made.append(BrewingContainerRecipe(self.CategoryId, [Ingredient([bottle_in], 1), catalyst],
                                                       [Ingredient([bottle_out], 1)]))
            return made
        thing_in, thing_out = self.__Plain(source), self.__Plain(output)
        if thing_in is None or thing_out is None:
            return []
        return [BrewingRecipe(self.CategoryId, [thing_in, catalyst], [thing_out])]

    def __Side(self, value):  # type: (str) -> Ingredient or None
        """ 药水类型 -> 三种瓶子的这种药水（多候选）；不是药水类型的照字面 """
        name = potions.type_name(value)
        if name is None:
            return self.__Plain(value)
        aux = potions.AUX_OF.get(name)
        if aux is None:
            if name not in self.Unknown:
                self.Unknown.add(name)
                logger.warn("[MEI/brewing] 认不出的药水类型 {}（potions.TYPES 里没有），这条酿造配方不收".format(name))
            return None
        stacks = [s for s in (self._safe_stack(bottle, aux, 1) for bottle in potions.CONTAINERS) if s]
        return Ingredient(stacks, 1) if stacks else None

    def __Plain(self, value):  # type: (str) -> Ingredient or None
        stack = self.ParseStackFromString(value, 1) if isinstance(value, basestring) else None
        return Ingredient([stack], 1) if stack else None
