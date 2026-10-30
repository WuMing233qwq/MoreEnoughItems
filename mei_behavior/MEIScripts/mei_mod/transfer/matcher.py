# coding=utf-8

# ----------------------------------------------------------------------
#  matcher.py is part of MoreEnoughItems.
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
把「一条配方的输入」与「玩家实际有的东西」配起来，产出搬运清单。

匹配用 **keys.make_key(id, aux)** —— 项目里现成的等价关系，不另造轮子。
它正是 keys.RECIPE 档的语义(忽略附魔/耐久噪声)，也就是玩家的直觉：
不会指望"必须用那把附了魔的镐"去合成。

三件事必须一起解决，缺一件就会算错：
  1. **多候选**：Ingredient 可以有多个候选(任意木板)，要挑玩家真有的那个；
  2. **全局配额**：九个格子可能要同一种物品，逐格判断会得出"每格都够、合起来不够"；
  3. **稳定选取**：同一次点击算两次必须给同样的结果，否则玩家看到材料乱跳。
"""
from MEIScripts.common.classes.types import keys
from MEIScripts.common.classes.types.transfer import TransferEntry

DEFAULT_MAX_STACK = 64
"""
问不到最大堆叠时的兜底值。

`GetItemBasicInfo` 对部分物品拿不到个别字段且**返回 0 而不是 None**
（CLAUDE.md 引擎结论 §11），所以"取到 0"必须当成"没问到"而不是"堆叠上限是 0"。
"""


def index_supply(collected):  # type: (list) -> dict
    """
    把 TransferRegistry.Collect 的结果按物品键分桶

    返回 {key: [(count, source_id, handle), ...]}，桶内保持 Collect 给的顺序 ——
    那个顺序已经按来源优先级排好，直接继承就是"稳定选取"。
    """
    supply = {}
    for stack, source_id, handle in collected or ():
        item = getattr(stack, "Item", None)
        if item is None:
            continue
        key = keys.make_key(item.ItemId, item.AuxValue)
        supply.setdefault(key, []).append(
            (int(getattr(stack, "Count", 0) or 0), source_id, handle))
    return supply


def _candidates(ingredient):  # type: (any) -> list
    """ 一个输入格的候选键表，按 Ingredient 给的顺序 """
    # 走 get_stacks() 展开, **不能拿 to_canonical 去比** ——
    # 那个对 tag 是折叠的, 是身份用的不是匹配用的(tasks_s2b.md §2)
    found = []
    for stack in ingredient.get_stacks() or ():
        if not stack or stack.is_empty():
            continue
        item = getattr(stack, "Item", None)
        if item is None:
            continue
        key = keys.make_key(item.ItemId, item.AuxValue)
        if key not in found:
            found.append(key)
    return found


def candidate_keys(ingredient):  # type: (any) -> list
    """ 一格的候选物品键（keys.make_key），按 Ingredient 给的顺序、去重；空格（没有候选）给空表 """
    if ingredient is None:
        return []
    return _candidates(ingredient)


def max_stack_of(ingredient):  # type: (any) -> int
    """
    这个格位放得下多少个 —— 取全部候选里**最小**的堆叠上限

    取最小而不是取第一个：到底会挑中哪个候选取决于玩家有什么，
    按最小算保证任何一种候选都塞得下，宁可少放也不溢出。
    """
    smallest = 0
    for stack in ingredient.get_stacks() or ():
        if not stack or stack.is_empty():
            continue
        try:
            size = int(stack.Item.Info.MaxStackSize or 0)
        except Exception:  # noqa  Info 是惰性字段, 取不到不该把整次规划带走
            size = 0
        if size <= 0:
            continue
        smallest = size if smallest <= 0 else min(smallest, size)
    return smallest or DEFAULT_MAX_STACK


def max_multiplier(slots, supply, limit=DEFAULT_MAX_STACK):  # type: (list, dict, int) -> int
    """
    这批格位最多能重复几次 —— 「最大化转移」的核心

    两个上限一起卡：
      · **格子放得下几倍**：某格要 2 个，堆叠上限 64 ⇒ 最多 32 倍；
      · **材料够几倍**：靠二分 + 复用 plan_entries 试算。

    二分而不是闭式求解是刻意的：多候选（"任意木板"）与全局配额纠缠在一起，
    闭式很容易算错；而 plan_entries 已经把这两件事做对了，直接问它"这么多做得成吗"
    最多试 log2(64) ≈ 6 次，而且这是点击路径不是每帧路径。
    """
    if not slots:
        return 0

    # 先卡格子容量: 每格最终是 amount*N 个, 不能超过该格的堆叠上限
    cap = limit
    for _slot, ingredient in slots:
        if ingredient is None or not _candidates(ingredient):
            continue   # 空格不占容量
        amount = max(1, int(ingredient.get_amount() or 1))
        cap = min(cap, max(0, max_stack_of(ingredient) // amount))
    if cap <= 0:
        return 0

    if not can_fulfill(slots, copy_supply(supply), 1):
        return 0

    low, high = 1, cap
    while low < high:
        mid = (low + high + 1) // 2
        if can_fulfill(slots, copy_supply(supply), mid):
            low = mid
        else:
            high = mid - 1
    return low


def plan_entries(slots, supply, multiplier=1):  # type: (list, dict, int) -> tuple
    """
    按 [(slot, ingredient), ...] 与供给表算出搬运清单

    返回 (entries, missing)：missing 是没凑齐的格位下标表，空表示全部凑齐。
    **供给表会被就地扣减**（配额），所以同一份 supply 不要复用于两次规划。

    multiplier 是"这条配方做几次"：每格的需求量乘以它。
    """
    multiplier = max(1, int(multiplier or 1))
    entries = []
    missing = []
    for slot, ingredient in slots:
        if ingredient is None:
            continue
        candidates = _candidates(ingredient)
        if not candidates:
            # **零候选 = 这格空着**，不是"需要 1 个什么都不是"。
            # 中空配方(箱子: 8 木板围一圈, 中间留空)的空格就是这种 ——
            # 解析层把它铺成 Ingredient([]) 而 Amount 默认为 1,
            # 当成需求去凑就永远凑不齐, 于是整条配方判为做不了.
            # render_slot 早就是这么判的(没有候选就渲染空面板), 这里对齐它
            continue
        need = max(1, int(ingredient.get_amount() or 1)) * multiplier
        taken = _take_from_supply(supply, candidates, need, slot)
        if taken is None:
            missing.append(slot)
            continue
        entries.extend(taken)
    return entries, missing


def _take_from_supply(supply, candidates, need, slot):  # type: (dict, list, int, int) -> list
    """
    从供给里为一个格位凑 need 个，凑不齐返回 None 且**不扣**任何东西

    凑不齐就整格放弃是刻意的：半格没有意义，而"先扣了再发现不够"要回滚。
    """
    picked = []
    remain = need
    # 先在不改 supply 的前提下试算, 确认凑得齐再真扣 —— 避免失败时的回滚
    trial = []
    for key in candidates:
        for index, (count, source_id, handle) in enumerate(supply.get(key, ())):
            if remain <= 0:
                break
            use = min(count, remain)
            if use <= 0:
                continue
            trial.append((key, index, use, source_id, handle))
            remain -= use
        if remain <= 0:
            break
    if remain > 0:
        return None

    for key, index, use, source_id, handle in trial:
        count, src, hdl = supply[key][index]
        supply[key][index] = (count - use, src, hdl)
        picked.append(TransferEntry(
            slot=slot, item_id=key[0], aux_value=key[1],
            count=use, source_id=source_id, handle=handle))
    return picked


def can_fulfill(slots, supply, multiplier=1):  # type: (list, dict, int) -> bool
    """
    只问"凑不凑得齐"，不产出清单 —— 供配方页开页时的预检用

    走同一条规划路径(而不是另写一套判断)，保证"预检说能做"与"真做得成"一致。
    supply 会被消耗，调用方自己给副本。
    """
    _entries, missing = plan_entries(slots, supply, multiplier)
    return not missing


def reachable(slots, supply):  # type: (list, dict) -> bool
    """
    每个要东西的格位，供给里至少有它的一种候选 —— can_fulfill 的**必要条件**：这里说不行的，can_fulfill 一定也说不行。
    便宜（不复制供给表、不试算配额），一次判一大批配方时先拿它筛掉明显做不出来的（查工作台的用途时是整个合成表）。
    不读 supply 里的数量：说行的照样要 can_fulfill 定夺
    """
    for _slot, ingredient in slots:
        if ingredient is None:
            continue
        candidates = _candidates(ingredient)
        if candidates and not any(key in supply for key in candidates):
            return False
    return True


def copy_supply(supply):  # type: (dict) -> dict
    """ 供给表的浅副本，桶内元组不可变故只需复制列表 """
    return dict((key, list(bucket)) for key, bucket in supply.items())
