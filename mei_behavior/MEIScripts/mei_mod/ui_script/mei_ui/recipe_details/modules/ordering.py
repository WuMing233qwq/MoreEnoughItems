# coding=utf-8

# ----------------------------------------------------------------------
#  ordering.py is part of MoreEnoughItems.
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
查询结果重排。落点必须在查询缓存之外，见 action_buttons.md §5.1。

三级稳定分区，优先级由高到低：

    置顶 -> 现在做得出来 -> 其余

**置顶享有绝对优先，不看做不做得出来** —— 那正是置顶的意义；
玩家会随着进度自己调整置顶，框架不替他判断。

顺序的语义是「**进页那一刻的推荐**」：转移之后不重排，
刚点过的那条不会在玩家眼皮底下掉下去（quick_craft.md 的路线 1）。
"""
from collections import OrderedDict

from MEIScripts.mei_mod.state import PinManager

from .craftable import CraftableIds


def SortRecipes(recipes, craftable_ids=None):  # type: (list, set) -> list
    """ 类型内重排：置顶 -> 可合成 -> 其余，三组各自保持原相对顺序 """
    # 稳定分区而非 sort：同一次查询两次显示的顺序必须一致
    craftable_ids = craftable_ids or ()
    top, ready, rest = [], [], []
    for recipe in recipes:
        if PinManager.HasRecipe(recipe):
            top.append(recipe)
        elif getattr(recipe, "Id", None) in craftable_ids:
            ready.append(recipe)
        else:
            rest.append(recipe)
    if not top and not ready:
        return recipes
    top.sort(key=PinManager.RankOf)
    return top + ready + rest


def SortResult(result):  # type: (dict) -> OrderedDict
    """ 两级重排：含置顶配方的类型整体提前，类型内部再排一次 """
    # 类型也要提前，否则置顶一条熔炉配方而默认选中的仍是工作台，玩家看不出生效
    if not result:
        return result

    # 一次采集算出全部可合成的 Id。**类型顺序不看它** ——
    # 切 tab 本来就是玩家的显式动作, 不该被材料状态左右
    craftable_ids = CraftableIds(result)

    ordered = OrderedDict()
    pinned_types, plain_types = [], []
    for crafting_type, recipes in result.items():
        sorted_recipes = SortRecipes(recipes, craftable_ids)
        ordered[crafting_type] = sorted_recipes
        if sorted_recipes and PinManager.HasRecipe(sorted_recipes[0]):
            pinned_types.append(crafting_type)
        else:
            plain_types.append(crafting_type)

    if not pinned_types:
        return ordered

    pinned_types.sort(key=lambda t: PinManager.RankOf(ordered[t][0]))
    return OrderedDict(
        (crafting_type, ordered[crafting_type])
        for crafting_type in pinned_types + plain_types
    )
