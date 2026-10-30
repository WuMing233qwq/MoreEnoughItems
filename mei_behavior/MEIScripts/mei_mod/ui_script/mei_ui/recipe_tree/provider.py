# coding=utf-8

# ----------------------------------------------------------------------
#  provider.py is part of MoreEnoughItems.
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
配方树的取数：MEI 的配方 → 解算用的 TreeRecipe（modules/solver.py 只认物品键字符串 "id#aux"，不认 Item / Recipe），
再把物品键换回物品（渲染、名字、查看配方页）。一棵树开着的期间缓存：换配方、换类型重算时不再向引擎查，关掉界面就丢。

- Recipes(key)：做这个物品的配方（RecipeManager.QueryRecipe 按产出查）。同样的原料合并成一格、空格跳过；单次产出取这条配方产出里
  这个物品的数量；工具取 GetShownCatalysts（熔炉的燃料不算，和收藏展开同一个规矩）
- IsItem(key)：流体这类不是物品的条目（Stack.KIND 不是 "item"）当原料、不查配方
- IsPinned(recipe)：置顶的配方先选（PinManager）
- Supply()：背包（和别的物品来源）里有什么，汇总对照用（用现成的接口 TransferRegistry、只在汇总里写）
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.common.classes.types import keys
from MEIScripts.common.classes.types.transfer import TransferContext
from MEIScripts.constants.codes import QueryConst
from MEIScripts.mei_mod.state import PinManager
from MEIScripts.mei_mod.transfer import index_supply
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import DescribeItem
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.registry import ItemFactory, ItemManager, RecipeManager
from MEIScripts.registry.transfer import TransferRegistry
from MEIScripts.utils.text import error_text, native_str

from .modules import TreeRecipe, key_of, split_key


def stack_key(stack):  # type: (any) -> str or None
    """ Stack → 物品键；空的、取不到键的给 None """
    if stack is None:
        return None
    try:
        if stack.is_empty():
            return None
        return keys.key_to_str(stack.get_key())
    except (AttributeError, TypeError, ValueError):
        return None


def _chance_of(ingredient):  # type: (any) -> float
    """ 产出的概率（Ingredient.get_chance，没有就当必得）"""
    try:
        return float(ingredient.get_chance())
    except (AttributeError, TypeError, ValueError):
        return 1.0


class TreeProvider(object):
    """ 一棵树（一个树界面）一份：配方、物品、渲染数据都按物品缓存（同一棵树里同一个物品只向 RecipeManager 查一次）"""

    def __init__(self):
        self.__Recipes = {}  # type: dict  # 物品键 -> [TreeRecipe]
        self.__Items = {}  # type: dict  # 物品键 -> Item 或 None
        self.__Stacks = {}  # type: dict  # 物品键 -> 第一次在配方里见到的 Stack（渲染数据以它为准）
        self.__NonItems = set()  # type: set
        self.__TypeOrder = None  # type: dict or None  # 类型 Id -> 在全部类型里排第几（sort_index）

    def Remember(self, item):  # type: (any) -> str or None
        """ 打开时传进来的物品：记下这个 Item，返回它的物品键 """
        if item is None or not getattr(item, "ItemId", None):
            return None
        key = key_of(item.ItemId, item.AuxValue)
        self.__Items[key] = item
        return key

    def Forget(self):
        """ 背包、配方都可能变了（刷新）：丢掉配方缓存，物品留着 """
        self.__Recipes = {}

    # solver 的取数接口
# ======================================================================================================================
    def Recipes(self, key):  # type: (str) -> list
        cached = self.__Recipes.get(key)
        if cached is not None:
            return cached
        result = []
        item = self.ItemOf(key) if key not in self.__NonItems else None
        if item is not None:
            try:
                found = RecipeManager.QueryRecipe(item, QueryConst.Output)
            except Exception as e:  # noqa  一个物品查炸了只当它没配方，不能让整棵树停住
                logger.error("[MEI/tree] 查 {} 的配方失败: {}".format(native_str(key), error_text(e)))
                found = {}
            order = self.__Order()
            for type_id, recipes in found.items():
                rank = order.get(type_id, len(order))
                for index, recipe in enumerate(recipes or ()):
                    converted = self.__Convert(recipe, key, type_id, (rank, index))
                    if converted is not None:
                        result.append(converted)
        self.__Recipes[key] = result
        return result

    def IsItem(self, key):  # type: (str) -> bool
        return key not in self.__NonItems

    @staticmethod
    def IsPinned(recipe):  # type: (TreeRecipe) -> bool
        return PinManager.Has(recipe.Id)

    # MEI 配方 → TreeRecipe
# ======================================================================================================================
    def __Convert(self, recipe, key, type_id, order):  # type: (any, str, str, tuple) -> TreeRecipe or None
        try:
            inputs, merged = [], {}
            for ingredient in recipe.GetInputs() or ():
                choices = self.__Choices(ingredient)
                if not choices:
                    continue
                amount = max(1, int(ingredient.get_amount() or 1))
                index = merged.get(choices)
                if index is None:
                    merged[choices] = len(inputs)
                    inputs.append([choices, amount])
                else:
                    inputs[index][1] += amount
            tools = []
            for ingredient in recipe.GetShownCatalysts() or ():
                choices = self.__Choices(ingredient)
                if choices and choices[0] not in tools:
                    tools.append(choices[0])
            output, byproducts = self.__Outputs(recipe, key)
            return TreeRecipe(recipe.Id, type_id, inputs, output, tools, source=recipe, order=order, byproducts=byproducts)
        except Exception as e:  # noqa  第三方的配方长得怪：跳过这一条
            logger.error("[MEI/tree] 配方 {} 转不成配方树用的样子: {}".format(
                native_str(getattr(recipe, "Id", "?")), error_text(e)))
            return None

    def __Choices(self, ingredient):  # type: (any) -> tuple
        """ 一格原料的候选物品键（按配方给的顺序、去重）；顺手记下见过的 Stack 和不是物品的条目 """
        if ingredient is None:
            return ()
        try:
            if ingredient.is_empty():
                return ()
            stacks = ingredient.get_stacks() or ()
        except Exception:  # noqa
            return ()
        found = []
        for stack in stacks:
            key = stack_key(stack)
            if key is None or key in found:
                continue
            found.append(key)
            if key not in self.__Stacks:
                self.__Stacks[key] = stack
            if getattr(stack, "KIND", "item") != "item":
                self.__NonItems.add(key)
        return tuple(found)

    def __Outputs(self, recipe, key):  # type: (any, str) -> tuple
        """
        (这条配方做一次出几个这个物品, 其他产出 [(物品键, 单次几个, 概率)])。
        这一格是哪个产出：正是它的 → 同一个 id 的（aux 写成通配的）→ 主产物；剩下的产出格都是副产物（每格认第一个候选）——
        主产物也可能是副产物：从副产物查到这条配方时（比如查某台机器的附带产出），这一格是它、主产物就多出来了
        """
        outputs = list(recipe.GetOutputs() or ())
        item_id = key.rsplit("#", 1)[0]
        exact = loose = None
        for index, ingredient in enumerate(outputs):
            for stack in ingredient.get_stacks() or ():
                found = stack_key(stack)
                if found == key:
                    exact = index if exact is None else exact
                elif loose is None and found is not None and found.rsplit("#", 1)[0] == item_id:
                    loose = index
        chosen = exact if exact is not None else loose if loose is not None else 0
        amount, extras = 1, []
        for index, ingredient in enumerate(outputs):
            count = max(1, int(ingredient.get_amount() or 1))
            if index == chosen:
                amount = count
                continue
            choices = self.__Choices(ingredient)
            if choices:
                extras.append((choices[0], count, _chance_of(ingredient)))
        return amount, extras

    def __Order(self):  # type: () -> dict
        if self.__TypeOrder is None:
            self.__TypeOrder = dict((type_id, index) for index, type_id in enumerate(RecipeManager.GetAllCraftingTypes()))
        return self.__TypeOrder

    # 物品键 → 物品
# ======================================================================================================================
    def ItemOf(self, key):  # type: (str) -> any
        """ 物品表里的那个 Item（同一个 aux）→ 配方里见过的 → 现造一个；id 都不认识给 None """
        if key in self.__Items:
            return self.__Items[key]
        item = None
        try:
            item_id, aux = split_key(key)
        except (TypeError, ValueError):
            item_id, aux = None, 0
        if item_id:
            for candidate in ItemManager.GetItemsById(item_id):
                if candidate.AuxValue == aux:
                    item = candidate
                    break
            if item is None:
                item = getattr(self.__Stacks.get(key), "Item", None)
            if item is None and ItemManager.LookUpItem(item_id):
                try:
                    item = ItemFactory.GetItem(ItemId=item_id, AuxValue=aux)
                except Exception:  # noqa
                    item = None
        self.__Items[key] = item
        return item

    def RenderData(self, key):  # type: (str) -> tuple
        """ (id, aux, 附魔, userData)，给物品渲染器的 SetUiItem """
        stack = self.__Stacks.get(key)
        if stack is not None:
            try:
                return stack.get_render_data()
            except Exception:  # noqa
                pass
        item = self.ItemOf(key)
        if item is not None:
            return item.ItemId, item.AuxValue, item.IsEnchanted, item.Attr.UserData
        item_id, aux = split_key(key)
        return item_id, aux, False, None

    def NameOf(self, key):  # type: (str) -> str
        """ 名字（悬停文字的第一行）"""
        item = self.ItemOf(key)
        return native_str(DescribeItem(item)) if item is not None else native_str(key)

    def HoverOf(self, key):  # type: (str) -> str
        """ 完整的悬停文字（菜单标题）"""
        item = self.ItemOf(key)
        if item is None:
            return native_str(key)
        try:
            return native_str(item.HoverText or "") or native_str(key)
        except Exception:  # noqa  惰性字段取不到
            return self.NameOf(key)

    # 类型
# ======================================================================================================================
    @staticmethod
    def TypeName(type_id):  # type: (str) -> str
        """ 类型名：和配方页、tooltip 同一个来源（RecipeManager.GetDisplayText；不另记一张名字表） """
        return native_str(RecipeManager.GetDisplayText(type_id))

    def Stations(self, type_id):  # type: (str) -> list
        """ 这个类型的工作站（物品键，按登记顺序）；没登记工作站的用类型图标 """
        category = RecipeManager.GetCategory(type_id)
        found = []
        for stack in (category.Stations if category is not None else ()) or ():
            key = stack_key(stack)
            if key is not None and key not in found:
                found.append(key)
                self.__Stacks.setdefault(key, stack)
        if not found and category is not None and category.Icon:
            try:
                found.append(key_of(category.Icon[0], category.Icon[1] if len(category.Icon) > 1 else 0))
            except (TypeError, ValueError, IndexError):
                pass
        return found

    # 背包
# ======================================================================================================================
    @staticmethod
    def Supply():  # type: () -> dict
        """ {物品键: 有几个}：问遍物品来源（背包是内置的那个，quick_craft.md）；读不到给空表 """
        try:
            ctx = TransferContext(player_id=clientApi.GetLocalPlayerId(), side="client",
                                  extra={"screen_def": ProxyManager.GetCurrentScreen()})
            supply = index_supply(TransferRegistry.Collect(ctx))
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 读背包失败: {}".format(error_text(e)))
            return {}
        have = {}
        for key, entries in supply.items():
            try:
                text = keys.key_to_str(key)
            except ValueError:
                continue
            have[text] = have.get(text, 0) + sum(count for count, _, _ in entries)
        return have
