# coding=utf-8

# ----------------------------------------------------------------------
#  summary.py is part of MoreEnoughItems.
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
配方树的材料汇总（纯逻辑）。

**按树深度优先走一遍，带一个库存**（照 EMI 的 BoM：副产物要拿去抵树里别处的需求，recipe_tree.md §0.5.1）。
库存是已经做出来、还没用掉的东西：
1. 走到一格先从库存里拿（先拿这一格的物品，不够再拿同一组候选里别的 —— 标签原料哪个都行）；拿够了这一格这一次就不用做，子树整棵不走。
2. 原料格（叶子、不再展开、当原料、绕回、截断、不是物品）：剩下要几个记进原料。
3. 合成格：做 ⌈剩下 ÷ 单次产出⌉ 次，按配方原料的顺序走子格；**子树走完之后**，多出来的与配方必出的其他产出才放进库存 ——
   所以一格的余量喂不到自己子树里的需求，只喂之后才走到的兄弟、表亲（照「深度优先、先走完的先做」的顺序合成，正好先有后用）。
   概率产出不进库存、不拿来抵，另记最多 / 平均（Chance）。
4. 走完以后库存里剩下的，加上概率产出，就是副产物；工具只算真的做了的格子的配方（整棵被抵掉的子树不算），每样 1 个、不乘倍数。

同一个中间物在几个分支里都要时，前一个做出来的余量后一个直接拿 —— 和「按物品 + 配方合并再取整」一样省；
同一个物品在不同分支用了不同配方也照样抵（不用退回逐个相加、写「上界」）。
结果和走的顺序有关（贪心）：后走到的分支做出来的余量帮不了先走到的，这里按配方原料的顺序走。
树上每一格写的还是「这一支要几个」（不扣库存），只有汇总是抵过的总数。

**背包扣减**是同一套（shortfall）：背包里有的先放进库存再走一遍，剩下的原料就是还缺的 —— 背包里有 9 个铁锭，就不再算这 9 个铁锭的粗铁；
根自己不扣（打开配方树就是要再做这么多个）。背包对照只在汇总里
"""
import math

from .solver import STATE_OK


class Summary(object):
    """
    Raw 原料（叶子）、Byproducts 副产物（库存里剩下的 + 概率产出按每次都出算）、Tools 工具：都是 {物品键: 数量}；
    Chance 是副产物里概率产出的那部分 {物品键: [最多几个, 平均几个]}；
    Flags 是原料为什么是原料（叶子 / 不再展开 / 当原料 / 绕回 / 截断，solver 的 STATE_*）
    """
    __slots__ = ("Raw", "Byproducts", "Chance", "Tools", "Flags")

    def __init__(self):
        self.Raw = {}  # type: dict
        self.Byproducts = {}  # type: dict
        self.Chance = {}  # type: dict
        self.Tools = {}  # type: dict
        self.Flags = {}  # type: dict

    def Sorted(self, table):  # type: (dict) -> list
        """ [(物品键, 数量)]，多的在前，一样多的按键排（确定的顺序）"""
        return sorted(table.items(), key=lambda pair: (-pair[1], pair[0]))


def _add(table, key, count):  # type: (dict, str, int) -> None
    table[key] = table.get(key, 0) + count


def _take(stock, node, need):  # type: (dict, any, int) -> int
    """ 从库存里拿，返回还要几个：先拿这一格的物品，不够再拿同一组候选里别的（标签原料哪个都行）"""
    keys = [node.Key] + [key for key in getattr(node, "Choices", None) or () if key != node.Key]
    for key in keys:
        have = stock.get(key, 0)
        if have <= 0:
            continue
        used = min(have, need)
        stock[key] = have - used
        need -= used
        if need <= 0:
            break
    return need


def _made(summary, stock, node, crafts, need):  # type: (Summary, dict, any, int, int) -> None
    """ 一格的子树走完了：多出来的、必出的其他产出放进库存；概率产出不进库存，记进副产物与 Chance """
    recipe = node.Recipe
    surplus = crafts * recipe.Output - need
    if surplus > 0:
        _add(stock, node.Key, surplus)
    for key, count, chance in recipe.Byproducts:
        made = crafts * count
        if chance >= 1.0:
            _add(stock, key, made)
            continue
        _add(summary.Byproducts, key, made)
        entry = summary.Chance.setdefault(key, [0, 0.0])
        entry[0] += made
        entry[1] += made * chance


def _walk(nodes, qty, stock):  # type: (list, int, dict) -> Summary
    """ 从根深度优先走一遍（不递归：树最深 256 层）；stock 是库存，走的时候会改它 """
    summary = Summary()
    # (节点 Id, 要几个, None) 是走到这一格；(节点 Id, 要几个, 做几次) 是它的子树走完了
    stack = [(0, qty, None)]
    while stack:
        node_id, need, crafts = stack.pop()
        node = nodes[node_id]
        if crafts is not None:
            _made(summary, stock, node, crafts, need)
            continue
        need = _take(stock, node, need)
        if need <= 0:
            continue
        if node.State != STATE_OK:
            _add(summary.Raw, node.Key, need)
            summary.Flags[node.Key] = node.State
            continue
        recipe = node.Recipe
        crafts = int(math.ceil(need / float(recipe.Output)))
        for tool in recipe.Tools:
            summary.Tools[tool] = 1
        stack.append((node_id, need, crafts))
        # 子格和配方原料同一个顺序；倒着压栈，第一样原料先走
        for (_, count), child in reversed(list(zip(recipe.Inputs, node.Children))):
            stack.append((child, crafts * count, None))
    return summary


def summarize(nodes, qty):  # type: (list, int) -> Summary
    """ nodes 是 solver 的 Nodes（[0] 是根），qty 是要几个根 """
    if not nodes:
        return Summary()
    stock = {}
    summary = _walk(nodes, qty, stock)
    for key, count in stock.items():
        if count > 0:
            _add(summary.Byproducts, key, count)
    return summary


def shortfall(nodes, qty, have):  # type: (list, int, dict) -> dict
    """
    还缺什么（「缺少材料」页）：背包里有的先放进库存再走一遍，剩下的原料 {物品键: 还缺几个}。
    中间物也扣（背包里有 9 个铁锭，就不再算这 9 个铁锭的粗铁）；根自己不扣（打开配方树就是要再做这么多个）。
    have 是 {物品键: 背包里有几个}（provider 读的；读不到就是空表，全都算缺）
    """
    if not nodes:
        return {}
    root = nodes[0].Key
    stock = {}
    for key, count in (have or {}).items():
        count = int(count or 0)
        if key != root and count > 0:
            stock[key] = count
    return _walk(nodes, qty, stock).Raw
