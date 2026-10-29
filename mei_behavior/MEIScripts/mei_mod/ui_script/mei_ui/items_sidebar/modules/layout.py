# coding=utf-8

# ----------------------------------------------------------------------
#  layout.py is part of MoreEnoughItems.
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
收藏栏的排版：把一个页签的条目排进若干页格子。纯函数，不碰引擎，规则见 docs/architecture/bookmarks.md §11。
"""
from MEIScripts.mei_mod.state.bookmarks import (
    GROUP_FOLD, GROUP_VIEW, KIND_ITEM, KIND_RECIPE, KIND_TREE, UNGROUPED, VIEW_LIST,
    entry_count, entry_expanded, entry_group, entry_identity, tree_count,
)

ROLE_ITEM = "item"
""" 物品收藏 """
ROLE_RECIPE = "recipe"
""" 配方收藏收起时（横排、折叠）的那一格，画显示物品 """
ROLE_OUTPUT = "out"
ROLE_INPUT = "in"
""" 配方收藏展开成的产物格与原料格（竖排清单里默认展开，横排时按 C 展开）"""
ROLE_TOOL = "tool"
""" 展开时排在行尾的工具格：配方的不消耗物品，数量固定 1、不乘倍数 """
ROLE_TREE = "tree"
""" 配方树收藏收起时的那一格：画根，数量是这棵树做几个 """
ROLE_TREE_ROOT = "tree_root"
ROLE_TREE_RAW = "tree_raw"
""" 配方树收藏展开成的一行：根，后面是保存那一刻的原料汇总（快照，不查配方）"""

EXPANDED_ROLES = (ROLE_OUTPUT, ROLE_INPUT, ROLE_TOOL, ROLE_TREE_ROOT, ROLE_TREE_RAW)
EXPANDABLE_KINDS = (KIND_RECIPE, KIND_TREE)
""" 能展开的收藏：配方（产物 + 原料 + 工具）、配方树（根 + 原料汇总）"""
TREE_MARKER = "T"
""" 配方树收藏左上角的标记 """


class Cell(object):
    """
    一格要画什么：Data 是存下来的物品数据（交给 BookmarkResolver 找回），Stack 是现查配方得到的物品堆，二者有其一
    """
    __slots__ = ("Index", "Entry", "Role", "Data", "Stack", "Amount", "Marker", "Group")

    def __init__(self, index, entry, role, data=None, stack=None, amount=1, marker=""):
        self.Index = index
        self.Entry = entry
        self.Role = role
        self.Data = data
        self.Stack = stack
        self.Amount = amount
        self.Marker = marker
        self.Group = entry_group(entry)

    def __repr__(self):
        return "<Cell #{} {} x{}{}>".format(self.Index, self.Role, self.Amount,
                                            " " + self.Marker if self.Marker else "")


def recipe_marker(entry):  # type: (dict) -> str
    """ 配方收藏左上角的标记：倍数大于 1 写 xN，否则写 R """
    count = entry_count(entry)
    return "x{}".format(count) if count > 1 else "R"


def _display_cell(index, entry):  # type: (int, dict) -> Cell
    """ 横排与折叠时一条收藏画一格；配方画它存下的显示物品，产量乘上倍数；配方树画根；没存显示物品的画成失效格 """
    if entry.get("k") == KIND_ITEM:
        return Cell(index, entry, ROLE_ITEM, data=entry, amount=entry_count(entry))
    if entry.get("k") == KIND_TREE:
        root = entry.get("root")
        return Cell(index, entry, ROLE_TREE, data=root if isinstance(root, dict) else None, amount=tree_count(entry),
                    marker=TREE_MARKER)
    data = entry.get("item")
    if not isinstance(data, dict):
        return Cell(index, entry, ROLE_RECIPE, marker=recipe_marker(entry))
    per_craft = data.get("n", 1)
    if isinstance(per_craft, bool) or not isinstance(per_craft, (int, long)) or per_craft < 1:
        per_craft = 1
    return Cell(index, entry, ROLE_RECIPE, data=data, amount=per_craft * entry_count(entry),
                marker=recipe_marker(entry))


def _recipe_row(index, entry, resolve):  # type: (int, dict, any) -> list
    """
    一条配方收藏展开成的一行：先产物后原料，数量乘上倍数；工具排在最后，数量固定 1（做几份都只要一把）；
    查不回来就只画显示物品
    """
    resolved = None
    if resolve is not None:
        try:
            resolved = resolve(entry)
        except Exception:  # noqa  查询失败只是退回显示物品，排版不能断
            resolved = None
    if not resolved:
        return [_display_cell(index, entry)]
    outputs, inputs = resolved[0], resolved[1]
    tools = resolved[2] if len(resolved) > 2 else ()
    multiplier = entry_count(entry)
    cells = []
    for role, stacks in ((ROLE_OUTPUT, outputs), (ROLE_INPUT, inputs)):
        for stack in stacks or ():
            marker = recipe_marker(entry) if not cells else ""
            amount = max(1, int(getattr(stack, "Count", 1) or 1)) * multiplier
            cells.append(Cell(index, entry, role, stack=stack, amount=amount, marker=marker))
    for stack in tools or ():
        cells.append(Cell(index, entry, ROLE_TOOL, stack=stack, marker=recipe_marker(entry) if not cells else ""))
    return cells or [_display_cell(index, entry)]


def _tree_row(index, entry):  # type: (int, dict) -> list
    """ 一条配方树收藏展开成的一行：根，后面是保存那一刻的原料汇总（条目里的 raw 快照）；不成形的跳过 """
    root = entry.get("root")
    cells = [Cell(index, entry, ROLE_TREE_ROOT, data=root if isinstance(root, dict) else None,
                  amount=tree_count(entry), marker=TREE_MARKER)]
    for ref in entry.get("raw") or ():
        if not isinstance(ref, dict) or not ref.get("id"):
            continue
        amount = ref.get("n", 1)
        if isinstance(amount, bool) or not isinstance(amount, (int, long)) or amount < 1:
            amount = 1
        cells.append(Cell(index, entry, ROLE_TREE_RAW, data={"id": ref.get("id"), "aux": ref.get("aux", 0)},
                          amount=amount))
    return cells


class _Cursor(object):
    """
    往格子里一格格落的光标：跳过被遮挡的格子，写满一页换下一页
    """
    def __init__(self, cols, rows, occluded):
        self.Cols = cols
        self.Capacity = cols * rows
        self.Occluded = frozenset(occluded)
        self.Pages = [{}]
        self.Slot = 0

    def _skip(self):
        while True:
            if self.Slot >= self.Capacity:
                self.Pages.append({})
                self.Slot = 0
            if self.Slot in self.Occluded:
                self.Slot += 1
                continue
            return

    def Place(self, cell, indent=False):
        """ 落一格；indent 为真时若刚好折到行首就空出第一格（竖排清单的续行缩进）"""
        self._skip()
        if indent and self.Cols > 1 and self.Slot % self.Cols == 0:
            self.Slot += 1
            self._skip()
        self.Pages[-1][self.Slot] = cell
        self.Slot += 1

    def Row(self):  # type: () -> tuple
        """ 下一格会落在哪一行：(页, 行) """
        self._skip()
        return len(self.Pages) - 1, self.Slot // self.Cols

    def NewRow(self):
        if self.Slot % self.Cols:
            self.Slot += self.Cols - self.Slot % self.Cols

    def Result(self):  # type: () -> list
        pages = self.Pages
        while len(pages) > 1 and not pages[-1]:
            pages = pages[:-1]
        return pages


def _blocks(entries):  # type: (list) -> list
    """ 按「连续同组」切段：[(分组 id, [(下标, 条目)])]，看不懂的条目不画 """
    blocks = []
    for index, entry in enumerate(entries):
        try:
            readable = entry_identity(entry) is not None
        except Exception:  # noqa
            readable = False
        if not readable or entry.get("k") not in (KIND_ITEM, KIND_RECIPE, KIND_TREE):
            continue
        gid = entry_group(entry)
        if blocks and blocks[-1][0] == gid:
            blocks[-1][1].append((index, entry))
        else:
            blocks.append((gid, [(index, entry)]))
    return blocks


def build_pages(entries, groups, cols, rows, occluded=(), resolve=None):
    # type: (list, dict, int, int, any, any) -> list
    """
    排版，返回 [ {格子下标: Cell} ]，至少一页；resolve(entry) -> (产物, 原料[, 工具]) 几列物品堆，只有展开的配方会问。
    配方展不展开见 entry_expanded：竖排清单默认展开、横排默认收起，按过 C 的按 C；横排里展开的配方自己占整行
    """
    if cols < 1 or rows < 1:
        return [{}]
    occluded = set(i for i in occluded if 0 <= i < cols * rows)
    if len(occluded) >= cols * rows:
        return [{}]
    cursor = _Cursor(cols, rows, occluded)
    groups = groups or {}
    for number, (gid, members) in enumerate(_blocks(entries)):
        if number:
            cursor.NewRow()
        props = groups.get(gid) or {}
        if gid != UNGROUPED and props.get(GROUP_FOLD):
            row = cursor.Row()
            for index, entry in members:
                if cursor.Row() != row:
                    break
                cursor.Place(_display_cell(index, entry))
            continue
        listed = props.get(GROUP_VIEW) == VIEW_LIST
        for position, (index, entry) in enumerate(members):
            expanded = entry.get("k") in EXPANDABLE_KINDS and entry_expanded(entry, listed)
            if (listed and position) or (expanded and not listed):
                cursor.NewRow()
            if expanded and entry.get("k") == KIND_TREE:
                cells = _tree_row(index, entry)
            elif expanded:
                cells = _recipe_row(index, entry, resolve)
            else:
                cells = [_display_cell(index, entry)]
            for order, cell in enumerate(cells):
                cursor.Place(cell, indent=order > 0)
            if expanded and not listed:
                # 横排里展开的配方自己占整行：后面的条目另起一行
                cursor.NewRow()
    return cursor.Result()


def highlight_key(cell):  # type: (Cell) -> str or None
    """
    按住 Ctrl / Shift 悬停时「同一条」怎么认（照 NEI）：配方、配方树收藏的格子 —— 收起的那一格、展开后的产物、原料、工具、
    根与原料汇总 —— 给条目的身份；物品收藏、空格不高亮（同一条就是它自己一格）
    """
    entry = getattr(cell, "Entry", None)
    if not isinstance(entry, dict) or entry.get("k") not in EXPANDABLE_KINDS:
        return None
    return entry_identity(entry)


def frame_key(cell):  # type: (Cell) -> tuple or None
    """
    这一格画在哪个框里：分组的格子按分组；不在分组里的展开配方自己一个框（产物 + 原料）；别的不画框。
    在分组里的展开配方不另画框，靠组框
    """
    if cell.Group:
        return "group", cell.Group
    if cell.Role in EXPANDED_ROLES:
        return "recipe", cell.Index
    return None

