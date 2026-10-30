# coding=utf-8

# ----------------------------------------------------------------------
#  transfer_request.py is part of MoreEnoughItems.
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
转移处理器（ctx.UI.Transfers）拿到的清单 TransferRequest：配方的每一格要什么、背包里凑得出多少、挑哪一样。

和 MEI 自己的快捷合成用同一个匹配器（mei_mod/transfer/matcher.py：多候选、全局配额、稳定选取），
所以 + 亮不亮、悬停写的缺什么，和别处的判断是一回事。原版合成格的悬停文字也用这里的 match_slots 数缺的东西。
纯计算：供给表由调用方给（CraftableCache 开页时采集一次），不碰引擎
"""
from MEIScripts.common.classes.types import keys
from MEIScripts.common.classes.types.transfer import TransferRequest, TransferSlot
from MEIScripts.constants.texts import TransferText
from MEIScripts.mei_mod.transfer.matcher import candidate_keys, copy_supply, max_multiplier, plan_entries
from MEIScripts.utils.text import to_unicode
from .slots import flatten_inputs, resolve_input_slot

MISSING_SHOWN = 4
""" 悬停里最多列几样缺的东西，多的写「等 N 样」"""


def _listed(recipe, getter):  # type: (any, str) -> list
    """ recipe.GetInputs() / GetCatalysts()；别人的配方类取不出来当没有 """
    try:
        return list(getattr(recipe, getter)() or ())
    except Exception:  # noqa
        return []


def layout(recipe, grid=None):  # type: (any, tuple) -> list
    """
    [(下标, Ingredient)]：给了 grid (列, 行) 按格子摊（resolve_input_slot，和配方页、原版工作台同一个摊法），
    没给按配方输入的顺序；空格（没有候选）不在里面
    """
    pairs = []
    if grid:
        columns, rows = grid
        for index in range(columns * rows):
            ingredient = resolve_input_slot(recipe, index, columns)
            if candidate_keys(ingredient):
                pairs.append((index, ingredient))
        return pairs
    for index, ingredient in enumerate(_listed(recipe, "GetInputs")):
        if candidate_keys(ingredient):
            pairs.append((index, ingredient))
    return pairs


def catalysts_of(recipe):  # type: (any) -> list
    """ [(下标, Ingredient)]：配方的催化剂（工具），空的不在里面 """
    return [(index, ingredient) for index, ingredient in enumerate(_listed(recipe, "GetCatalysts"))
            if candidate_keys(ingredient)]


def _pick(ingredient, key, need):  # type: (any, tuple, int) -> any
    """ 这一格挑的那样（ItemStack，数量是 need）：键对得上的候选，没有就是第一个候选；没有候选给 None """
    chosen = None
    for stack in ingredient.get_stacks() or ():
        item = getattr(stack, "Item", None) if stack else None
        if item is None or stack.is_empty():
            continue
        if chosen is None:
            chosen = stack
        if key is not None and keys.make_key(item.ItemId, item.AuxValue) == key:
            chosen = stack
            break
    if chosen is None:
        return None
    picked = chosen.copy()
    picked.Count = need
    return picked


def _leftover(ingredient, supply):  # type: (any, dict) -> tuple
    """ 凑不齐的一格：它的候选里剩得最多的那一种还有多少、是哪一种（一格只用一种候选，几种加起来不算，同 matcher）"""
    best_key, best = None, 0
    for key in candidate_keys(ingredient):
        count = sum(int(entry[0] or 0) for entry in supply.get(key, ()))
        if count > best:
            best_key, best = key, count
    return best, best_key


def fits(recipe, grid):  # type: (any, tuple) -> bool
    """ 配方摊得进 grid (列, 行) 吗：有序配方看宽高，无序配方看摊平后几格；没给 grid 一律算摊得进 """
    if not grid:
        return True
    columns, rows = grid
    try:
        shape = recipe.GetShape()
    except Exception:  # noqa  别人的配方类没有形状当无序
        shape = None
    if shape:
        return int(shape[0]) <= columns and int(shape[1]) <= rows
    return len(flatten_inputs(_listed(recipe, "GetInputs"))) <= columns * rows


def match_slots(pairs, supply, catalyst=False):  # type: (list, dict, bool) -> list
    """
    [(下标, Ingredient)] 按供给表配出 TransferSlot 表（供给表**就地扣减**，几次调用接着扣 = 全局配额）：
    凑齐的格子 Have = Need、挑背包里的那一样；凑不齐的格子什么都不扣，Have 是它的候选在剩下的供给里还有多少（不超过 Need），挑剩得最多的那个候选
    """
    entries, missing = plan_entries(pairs, supply, 1)
    taken = {}
    for entry in entries:
        taken.setdefault(entry.Slot, []).append(entry)
    short = set(missing)
    rows = []
    for index, ingredient in pairs:
        if not candidate_keys(ingredient):
            continue  # 空格（中空配方的那一格）不是「要一个什么都不是」，和匹配器一样跳过
        need = max(1, int(ingredient.get_amount() or 1))
        picks = taken.get(index)
        if picks and index not in short:
            have = sum(int(entry.Count) for entry in picks)
            key = keys.make_key(picks[0].ItemId, picks[0].AuxValue)
        else:
            have, key = None, None
        rows.append([index, ingredient, need, have, key])
    slots = []
    for index, ingredient, need, have, key in rows:
        if have is None:
            # 等这一批都扣完再数剩下的：凑不齐的格子只拿别的格子挑剩的
            have, key = _leftover(ingredient, supply)
        slots.append(TransferSlot(index, ingredient, need, min(need, have), _pick(ingredient, key, need), catalyst))
    return slots


def build_request(recipe, supply, grid=None, category_id="", screen_def="", wants_max=False):
    # type: (any, dict, tuple, str, str, bool) -> TransferRequest
    """
    一条配方的清单：输入格（grid 给了按格子摊，没给按配方输入的顺序）先配、催化剂接着配（同一份供给，工具不会被算两次）；
    MaxTimes() 第一次问时才二分试算（只看输入格）。supply 不会被改
    """
    supply = supply or {}
    inputs = layout(recipe, grid)
    work = copy_supply(supply)
    slots = match_slots(inputs, work)
    catalysts = match_slots(catalysts_of(recipe), work, catalyst=True)
    return TransferRequest(
        recipe, category_id=category_id or "", screen_def=screen_def or "", slots=slots, catalysts=catalysts,
        times=1, wants_max=wants_max, max_times=lambda: max_multiplier(inputs, supply), fits=fits(recipe, grid))


def stack_name(stack):  # type: (any) -> unicode
    """ 一样东西给玩家看的名字（物品表里缓存的名字，取不到用 id）"""
    item = getattr(stack, "Item", None)
    if item is None:
        return u"?"
    try:
        name = item.Info.ItemName
    except Exception:  # noqa  Info 是惰性字段，取不到不该带走悬停文字
        name = None
    return to_unicode(name or item.ItemId or u"?")


def describe_missing(slots, limit=MISSING_SHOWN):  # type: (list, int) -> unicode
    """ 「铁锭 ×2、木棍 ×1 等 3 样」：缺的格子按挑中的那样写，同一样东西合并 """
    merged = []
    counts = {}
    for slot in slots:
        if slot.Missing <= 0:
            continue
        name = stack_name(slot.Stack)
        if name not in counts:
            merged.append(name)
            counts[name] = 0
        counts[name] += slot.Missing
    parts = [TransferText.MissingItem.format(name, counts[name]) for name in merged[:limit]]
    text = TransferText.Separator.join(parts)
    if len(merged) > limit:
        text += TransferText.More.format(len(merged) - limit)
    return text
