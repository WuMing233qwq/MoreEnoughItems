# coding=utf-8

# ----------------------------------------------------------------------
#  choices.py is part of MoreEnoughItems.
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
这一棵树的选择（纯逻辑）。树里的改动默认只管这一棵，随收藏保存；「设为首选」「当原料（全局）」另写全局表（state/tree_prefs.py）。

- Root / Qty / RootRecipe：根的物品键、要几个、根用哪条配方（从配方行打开时才有）
- Choices {物品键: 配方 Id}：本树「用这条」的；Types {物品键: 类型 Id}：本树点工作方块换的类型
- Picks {候选签名: 物品键}：多候选的原料（标签）选了哪个（solver.choice_sig）
- Stop：本树「不再展开」的物品键；Fold：折叠的格子（路径签名，视图状态）

和收藏条目互转（k = "tree"，bookmarks.md §4）：root 是 {"id", "aux"}，count 是数量，别的用物品键字符串；raw 是保存那一刻的原料汇总快照，
收藏栏展开时直接显示、不查配方。看不懂的字段丢掉、不报错（数据可以丢，加载不能卡 —— engineering.md §7-9）
"""
from MEIScripts.common.classes.types import keys

KIND_TREE = "tree"
""" 收藏条目的 k（与 state/bookmarks.py 的 KIND_TREE 相同，探针对账）"""

MAX_QTY = 99999
""" 数量上限（与收藏的 MAX_COUNT 相同）"""


def key_of(item_id, aux=0):  # type: (str, int) -> str
    """ 物品键 "id#aux"（keys.key_to_str）"""
    return keys.key_to_str(keys.make_key(item_id, aux))


def split_key(key):  # type: (str) -> tuple
    """ 物品键 → (id, aux) """
    return keys.key_from_str(key)


def item_ref(key, count=None):  # type: (str, int or None) -> dict
    item_id, aux = split_key(key)
    ref = {"id": item_id, "aux": aux}
    if count is not None:
        ref["n"] = int(count)
    return ref


class TreeState(object):
    __slots__ = ("Root", "Qty", "RootRecipe", "Choices", "Types", "Picks", "Stop", "Fold")

    def __init__(self, root, qty=1, root_recipe=None):
        self.Root = root  # type: str
        self.Qty = clamp_qty(qty)  # type: int
        self.RootRecipe = root_recipe  # type: str or None
        self.Choices = {}  # type: dict
        self.Types = {}  # type: dict
        self.Picks = {}  # type: dict
        self.Stop = set()  # type: set
        self.Fold = set()  # type: set

    def Copy(self):  # type: () -> TreeState
        other = TreeState(self.Root, self.Qty, self.RootRecipe)
        other.Choices = dict(self.Choices)
        other.Types = dict(self.Types)
        other.Picks = dict(self.Picks)
        other.Stop = set(self.Stop)
        other.Fold = set(self.Fold)
        return other

    def SetType(self, key, type_id):  # type: (str, str) -> None
        """ 点工作方块换类型：这一格本树选过的配方不是这个类型的就作废（原料格只在当前类型里翻）"""
        self.Types[key] = type_id

    def ToEntry(self, raw=None):  # type: (dict or None) -> dict
        """ 收藏条目；raw 是 {物品键: 数量}（汇总的原料），存成快照 """
        entry = {"k": KIND_TREE, "root": item_ref(self.Root)}
        if self.Qty != 1:
            entry["count"] = self.Qty
        if self.RootRecipe:
            entry["rid"] = self.RootRecipe
        if self.Choices:
            entry["choices"] = dict(self.Choices)
        if self.Types:
            entry["types"] = dict(self.Types)
        if self.Picks:
            entry["picks"] = dict(self.Picks)
        if self.Stop:
            entry["stop"] = sorted(self.Stop)
        if self.Fold:
            entry["fold"] = sorted(self.Fold)
        if raw:
            entry["raw"] = [item_ref(key, count) for key, count in sorted(raw.items(), key=lambda pair: (-pair[1], pair[0]))]
        return entry

    @classmethod
    def FromEntry(cls, entry):  # type: (dict) -> TreeState or None
        """ 收藏条目 → 选择；根都认不出给 None，别的字段不成形的丢掉 """
        if not isinstance(entry, dict) or entry.get("k") != KIND_TREE:
            return None
        root = entry.get("root")
        if not isinstance(root, dict) or not isinstance(root.get("id"), basestring) or not root.get("id"):
            return None
        try:
            root_key = key_of(root.get("id"), root.get("aux", 0))
        except (TypeError, ValueError):
            return None
        rid = entry.get("rid")
        state = cls(root_key, entry.get("count", 1), rid if isinstance(rid, basestring) and rid else None)
        state.Choices = _str_map(entry.get("choices"))
        state.Types = _str_map(entry.get("types"))
        state.Picks = _str_map(entry.get("picks"))
        state.Stop = _str_set(entry.get("stop"))
        state.Fold = _str_set(entry.get("fold"))
        return state


def clamp_qty(qty):  # type: (any) -> int
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return 1
    return max(1, min(MAX_QTY, qty))


def raw_snapshot(entry):  # type: (dict) -> list
    """ 收藏条目里的原料快照：[(物品键, 数量)]，不成形的条目跳过 """
    result = []
    for ref in (entry.get("raw") if isinstance(entry, dict) else None) or ():
        if not isinstance(ref, dict) or not isinstance(ref.get("id"), basestring) or not ref.get("id"):
            continue
        try:
            result.append((key_of(ref.get("id"), ref.get("aux", 0)), max(1, int(ref.get("n", 1)))))
        except (TypeError, ValueError):
            continue
    return result


def _str_map(value):  # type: (any) -> dict
    if not isinstance(value, dict):
        return {}
    return dict((k, v) for k, v in value.items() if isinstance(k, basestring) and isinstance(v, basestring) and k and v)


def _str_set(value):  # type: (any) -> set
    if not isinstance(value, (list, tuple)):
        return set()
    return set(v for v in value if isinstance(v, basestring) and v)
