# coding=utf-8

# ----------------------------------------------------------------------
#  parser.py is part of MoreEnoughItems.
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
引擎配方 dict 的解析原语与透传查询，各配方类型共用；具体解析由子类覆写 ParseRecipe。
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.api.facades.types import Ingredient
from MEIScripts.api.facades.types import RecipeSource
from MEIScripts.api.facades.registry import ItemFactory, ItemManager

from .answers import INPUT, OUTPUT, EngineAnswers
from .scanner import RecipeScanner


def _tags_of(stack):  # type: (any) -> set or None
    """ 候选物品的 tag（注册物品时缓存的 Info.Tags）；取不到给 None """
    try:
        return set(stack.Item.Info.Tags or ())
    except Exception:  # noqa  惰性字段取不到
        return None


def _tag_members(tag):  # type: (str) -> set
    """ 物品表里带这个 tag 的物品 (id, aux)；按 tag 放在 ItemManager 的搜索缓存里（物品表一变就清）"""
    def has_tag(item):
        try:
            return tag in (item.Info.Tags or ())
        except Exception:  # noqa
            return False
    return set((item.ItemId, item.AuxValue) for item in ItemManager.SearchByCondition(has_tag, "tag:" + tag))


def common_tag(stacks):  # type: (list) -> str or None
    """
    引擎展开成 list 的原料（它把配方里写的 tag 展开成了物品列表）原本是哪个 tag：候选的 tag 求交集 ——
    正好一个就是它；好几个就挑「物品表里带这个 tag 的正好是这些」的那个；一个都没有（或者有候选取不到 tag）给 None。
    只看缓存的 Info.Tags，不调引擎（GetItemTags 与 GetItemBasicInfo 的 tags 一模一样，CLAUDE.md 引擎结论 §44）
    """
    shared = None
    for stack in stacks:
        tags = _tags_of(stack)
        if not tags:
            return None
        shared = tags if shared is None else shared & tags
        if not shared:
            return None
    if not shared:
        return None
    if len(shared) > 1:
        members = set((stack.Item.ItemId, stack.Item.AuxValue) for stack in stacks)
        shared = [tag for tag in shared if _tag_members(tag) == members]
        if len(shared) != 1:
            return None
    tag = next(iter(shared))
    return tag.encode("utf-8") if isinstance(tag, unicode) else tag  # noqa  进 Recipe.Id 的字一律 str


class EngineRecipeSource(RecipeSource):
    """
    透传引擎的配方来源：GetRecipesBy* 查询 + dict 解析。问过引擎的（这个来源、这个方向、这个物品）记下答案、不问第二次（tools/answers.py）；
    全表要的时候才分帧扫描凑（tools/scanner.py）
    """

    SCAN_BY = OUTPUT
    """
    全量扫描逐个物品问这个来源时按哪个方向问：缺省按产物（"output"）。
    有的配方按产物查不到就改成按原料（"input"）—— 锻造纹饰的产物是空的，只在查模板、盔甲、材料的用途时出来
    """

    def __init__(self, category_id):  # type: (str) -> None
        self.CategoryId = category_id
        self.RecipeComp = clientApi.GetEngineCompFactory().CreateRecipe(clientApi.GetLevelId())
        self.Tag = category_id

    @staticmethod
    def _safe_stack(item_id, aux_value=0, count=1):  # type: (str, int, int) -> any
        """
        安全构造 ItemStack：物品不在物品表里（ItemFactory 抛 ValueError）、数量不对时返回 None ——
        一条配方里有一格认不出，不该让这个物品整个类型的配方都出不来
        """
        try:
            item = ItemFactory.GetItem(ItemId=item_id, AuxValue=aux_value)
            if not item:
                return None
            return item.stack(count=count)
        except (TypeError, ValueError):
            return None

    def ParseIngredientFromDict(self, _dict):  # type: (dict) -> Ingredient
        """
        将原始输入字典解析为 Ingredient (空槽/非法 -> Ingredient([])).

        数量约定: 候选 Stack 的 Count 一律归一化为 1, 数量只由 Ingredient.Amount 承载.
        (原实现两个分支约定不一致: str 分支把 count 同时写进 Count 与 Amount,
         list 分支只写 Amount —— 同一个信息存两份且互相矛盾.)
        """
        if not isinstance(_dict, dict):
            return Ingredient([])
        item = _dict["item"]
        count = _dict.get("count", 1)
        if isinstance(item, basestring):
            stack = self._safe_stack(item, _dict.get("data", 0), 1)
            return Ingredient([stack], count) if stack else Ingredient([])
        if isinstance(item, list):
            stacks = [s for s in (self._safe_stack(i, 0, 1) for i in item) if s]
            return self.MakeListIngredient(stacks, count)
        return Ingredient([])

    @staticmethod
    def MakeListIngredient(stacks, count):  # type: (list, int) -> Ingredient
        """
        引擎给的 list 原料：候选照旧全在，再带上它们原本的 tag（common_tag）——
        Recipe.Id 的规范形遇到 tag 只写 tag 名，模组往这个 tag 里加物品，Id 不变；显示、存盘不变（Ingredient.to_canonical）。
        认不出 tag 的照字面算（engineering.md §7-9：配方数据可以因模组切换丢失，但不能卡）
        """
        return Ingredient(stacks, count, tag_id=common_tag(stacks) if stacks else None)

    def ParseShapelessParts(self, raw_dict):  # type: (dict) -> tuple or None
        """
        无序配方形状的 dict（ingredients + result）拆成 (原料表, 产物表)：切石机、制图台、锻造台给的都是这个形状
        （CLAUDE.md 引擎结论 §45；锻造纹饰的 result 是空表）。result 是一个 dict 也收；不是这个形状给 None
        """
        if not isinstance(raw_dict, dict):
            return None
        ingredients, result = raw_dict.get("ingredients"), raw_dict.get("result")
        if not isinstance(ingredients, list) or result is None:
            return None
        if isinstance(result, dict):
            result = [result]
        try:
            inputs = [self.ParseIngredientFromDict(one) for one in ingredients]
            outputs = [o for o in (self._to_output(self.ParseStackFromDict(one)) for one in result or ()) if o]
        except (KeyError, TypeError, ValueError):  # 缺 item、aux 不是数字：这一条不收
            return None
        return inputs, outputs

    @staticmethod
    def _to_output(stack):  # type: (any) -> Ingredient or None
        """
        输出侧统一包成 Ingredient (Outputs 与 Inputs/Catalysts 同为 list[Ingredient]).

        为什么输出也是 Ingredient: ① 消费端(render_slot/索引/配方树)只认一种类型;
        ② 概率产出与多候选产出(mod 机器)装不进裸 Stack —— Chance 在 Ingredient 上.
        数量约定同输入: Stack.Count 归一化为 1, 数量进 Amount.
        """
        if not stack:
            return None
        count = stack.Count
        stack.Count = 1
        return Ingredient([stack], count)

    def ParseStackFromDict(self, _dict):  # type: (dict) -> any
        """ 将原始输出字典解析为单个具体 Stack (取首个有效候选) """
        if not isinstance(_dict, dict):
            return None
        item = _dict["item"]
        count = _dict.get("count", 1)
        if isinstance(item, basestring):
            return self._safe_stack(item, _dict.get("data", 0), count)
        if isinstance(item, list):
            for i in item:
                stack = self._safe_stack(i, 0, count)
                if stack:
                    return stack
        return None

    def ParseStackFromString(self, _string, count=1):  # type: (str, int) -> any
        """ 解析 'ns:id[:aux]' 字符串为单个 Stack """
        if not isinstance(_string, basestring):
            return None
        data = _string.split(":")
        if len(data) == 3:
            item_id = data[0] + ":" + data[1]
            try:
                aux_value = int(data[2])
            except ValueError:  # 附加值不是数：认不出这一格
                return None
        elif len(data) == 2:
            item_id = data[0] + ":" + data[1]
            aux_value = 0
        else:
            return None
        return self._safe_stack(item_id, aux_value, count)

    def GetAll(self):  # type: () -> list
        """
        本类型已扫到的全部配方；引擎不给枚举接口，只能靠扫描凑 —— **第一次要全表时才开扫**。
        要全表就是有人在等（查工作站的用途）：还没扫完的插到扫描队列最前（Request(urgent=True)）
        """
        RecipeScanner.Request(self.CategoryId, urgent=True)
        return RecipeScanner.GetRecipes(self.CategoryId)

    def IsAllComplete(self):  # type: () -> bool
        """ 扫完才是真（还没要过全表的也是假）"""
        return RecipeScanner.IsDone(self.CategoryId)

    def ParseRecipe(self, raw_list):  # type: (list) -> list
        """ 把引擎给的原始 dict 表转成 Recipe 实例表，由各配方类型覆写 """
        # 从前这里是 if self.Tag == "crafting_table" / elif "furnace" 的字符串分支,
        # 加一个类型就要回来改一次；改成钩子之后各类型只管自己那一份
        _ = raw_list
        return []

    def GetRecipesByResult(self, item):
        """ 按产物问引擎；问过的（不管是平时查来源还是全量扫描）直接给记下的答案 """
        known = EngineAnswers.Get(self, OUTPUT, item)
        if known is not None:
            return known
        recipes = self.ParseRecipe(self.RecipeComp.GetRecipesByResult(item.ItemId, self.Tag, item.AuxValue))
        EngineAnswers.Put(self, OUTPUT, item, recipes)
        return recipes

    def GetRecipesByInput(self, item):
        """ 按原料问引擎（官方说这个方向昂贵）；问过的直接给记下的答案 """
        known = EngineAnswers.Get(self, INPUT, item)
        if known is not None:
            return known
        recipes = self.ParseRecipe(self.RecipeComp.GetRecipesByInput(item.ItemId, self.Tag, item.AuxValue))
        EngineAnswers.Put(self, INPUT, item, recipes)
        return recipes
