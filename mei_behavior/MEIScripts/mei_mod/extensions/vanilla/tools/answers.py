# coding=utf-8

# ----------------------------------------------------------------------
#  answers.py is part of MoreEnoughItems.
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
引擎配方查询的答案：按（来源, 方向, 物品）记下引擎答了什么，同一个问题不问第二次（EngineRecipeSource.GetRecipesBy*）。

- 记的是「引擎对这个物品答了什么」（解析好的配方，没有配方也记），不拿配方的产物去反推 ——
  引擎给的产物带方块态 data，反推对不上物品表的 aux（state/cache.py）。
- 来源各记各的：同一个物品问工作台、问熔炉是两个问题（tag 不同）。
- 平时查来源、用途问过的记下，全量扫描（tools/scanner.py）再问到同一个就不问引擎了；反过来也一样。
- 只在客户端用，跟扫描结果一起作废（RecipeScanner.Reset：重进世界）。游戏中途有模组用服务端接口动态注册配方（AddRecipe 等），
  客户端没有事件可收（SDK 里没有），记下的要到重进世界才换新
"""

OUTPUT = "output"
INPUT = "input"


def item_key(item):  # type: (any) -> tuple
    """ 引擎按 (id, aux) 回答，记答案也按它 """
    return item.ItemId, item.AuxValue


class __EngineAnswers(object):  # noqa
    """ 引擎配方查询的答案，构造期不碰引擎 """

    def __init__(self):
        self._answers = {}  # type: dict  # (来源, 方向) -> {(id, aux): (配方, ...)}
        self.Asked = 0  # type: int  # 真问了引擎几次（记下一份答案就是问了一次）
        self.Hits = 0  # type: int  # 直接给记下的几次

    def Get(self, source, direction, item):  # type: (any, str, any) -> list or None
        """ 这个来源对这个物品、按这个方向的答案（给副本）；没问过给 None """
        bucket = self._answers.get((source, direction))
        found = bucket.get(item_key(item)) if bucket is not None else None
        if found is None:
            return None
        self.Hits += 1
        return list(found)

    def Put(self, source, direction, item, recipes):  # type: (any, str, any, list) -> None
        """ 刚问完引擎：记下这一份（没有配方也记，下次就不问了）"""
        self.Asked += 1
        self._answers.setdefault((source, direction), {})[item_key(item)] = tuple(recipes or ())

    def Clear(self):
        self._answers = {}
        self.Asked = 0
        self.Hits = 0


EngineAnswers = __EngineAnswers()
