# coding=utf-8

# ----------------------------------------------------------------------
#  sources.py is part of MoreEnoughItems.
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
框架自带的配方来源实现。引擎不认识自定义配方，这里替开发者把索引与匹配写一遍。
"""
from .base import RecipeSource
from .types import keys


class StaticRecipeSource(RecipeSource):
    """ 手工登记的配方表，自建两个桶，供自定义配方使用 """

    CAN_ENUMERATE = True
    """ 表在自己手上，GetAll 给的就是全部 """

    def __init__(self, category_id=""):  # type: (str) -> None
        self.CategoryId = category_id
        self._all = []  # type: list
        self._by_output = {}  # type: dict
        self._by_input = {}  # type: dict

    # 维护
# ======================================================================================================================
    def Add(self, recipe):  # type: (any) -> bool
        """ 登记一条配方，Id 重复则不动 """
        recipe_id = getattr(recipe, "Id", None)
        if recipe_id is None or self._Find(recipe_id) is not None:
            return False
        self._all.append(recipe)
        self._Index(recipe)
        return True

    def AddAll(self, recipes):  # type: (any) -> int
        return len([r for r in recipes if self.Add(r)])

    def Remove(self, recipe_id):  # type: (str) -> bool
        recipe = self._Find(recipe_id)
        if recipe is None:
            return False
        self._all.remove(recipe)
        self._Reindex()
        return True

    def Clear(self):
        self._all = []
        self._by_output = {}
        self._by_input = {}

    def Count(self):  # type: () -> int
        return len(self._all)

    # 查询
# ======================================================================================================================
    def QueryByOutput(self, item):  # type: (any) -> list
        return list(self._by_output.get(self._ItemKey(item), ()))

    def QueryByInput(self, item):  # type: (any) -> list
        return list(self._by_input.get(self._ItemKey(item), ()))

    def GetAll(self):  # type: () -> list
        return list(self._all)

    # 内部
# ======================================================================================================================
    def _Find(self, recipe_id):  # type: (str) -> any
        for recipe in self._all:
            if recipe.Id == recipe_id:
                return recipe
        return None

    @staticmethod
    def _ItemKey(item):  # type: (any) -> tuple or None
        item_id = getattr(item, "ItemId", None)
        if not item_id:
            return None
        return keys.make_key(item_id, getattr(item, "AuxValue", 0))

    def _Index(self, recipe):
        # Ingredient 是规格没有身份, 不能直接做键, 展开成 Stack 后逐个入桶
        # (见 types/recipe.py 的 to_canonical 注释)
        self._Fill(self._by_output, recipe.GetOutputs(), recipe)
        self._Fill(self._by_input, recipe.GetInputs(), recipe)
        # **催化剂也算「用途」**: 玩家点一把扳手想知道"它能干什么",
        # 答案就包括"这些配方要用它"—— 哪怕它不被消耗。
        # 不索引的话 GetCatalysts() 里的东西对查询完全不可达
        # (比如蔚蓝机件加工台的工具)。
        # _Fill 自带同配方去重, 所以既是输入又是催化剂也只会入一次
        self._Fill(self._by_input, recipe.GetCatalysts(), recipe)

    def _Fill(self, bucket, ingredients, recipe):
        for ingredient in ingredients:
            if not ingredient:
                continue
            for stack in ingredient.get_stacks():
                if not stack or stack.is_empty():
                    continue
                key = stack.get_key()
                entries = bucket.setdefault(key, [])
                # 同一条配方可能多个槽位吃同一种材料, 只入一次
                if recipe not in entries:
                    entries.append(recipe)

    def _Reindex(self):
        self._by_output = {}
        self._by_input = {}
        for recipe in self._all:
            self._Index(recipe)
