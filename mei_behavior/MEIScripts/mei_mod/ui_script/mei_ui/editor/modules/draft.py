# coding=utf-8
# ----------------------------------------------------------------------
#  draft.py is part of MoreEnoughItems.
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
编辑器的草稿（纯逻辑，不碰引擎、不碰登记表）：页面与配方都是 state/user_recipes.py 的 dict，编辑器拿一份拷贝改，存的时候交回去。
积木的大小、装不装东西由调用方给（size_of(积木) / holds(积木)，就是 BlockType.SizeOf 与 BlockRegistry.Holds）
"""
import copy
from collections import OrderedDict

from MEIScripts.mei_mod.state.user_recipes import (
    DEFAULT_HEIGHT, DEFAULT_WIDTH, HEIGHT_RANGE, ROLES, WIDTH_RANGE, clamp_size, holder_index,
)

FIT_PAD = 2
""" 「贴合积木」在积木外面留几像素 """

SLOT, ARROW, FLAME = "mei:slot", "mei:arrow", "mei:flame"


def _slot(role, x, y):
    return {"t": SLOT, "role": role, "x": x, "y": y}


def _arrow(x, y, style="large"):
    return {"t": ARROW, "s": style, "anim": True, "x": x, "y": y}


PRESETS = OrderedDict([
    # 名字: (内容区的宽, 高, 积木)。都是贴合积木的（外面留 FIT_PAD）：格子 20 × 20、大箭头 24 × 17、熔炉箭头 22 × 15、火焰 13 × 13
    ("craft", (124, 64, [_slot("in", 2 + (i % 3) * 20, 2 + (i // 3) * 20) for i in range(9)]
               + [_arrow(68, 23), _slot("out", 102, 22)])),
    ("furnace", (84, 40, [_slot("in", 2, 2), {"t": FLAME, "anim": True, "x": 5, "y": 25}, _arrow(30, 17, "furnace"),
                          _slot("out", 62, 15)])),
    ("one", (84, 24, [_slot("in", 2, 2), _arrow(30, 3), _slot("out", 62, 2)])),
    ("two", (104, 24, [_slot("in", 2, 2), _slot("in", 22, 2), _arrow(50, 3), _slot("out", 82, 2)])),
    ("crush", (106, 44, [_slot("in", 2, 12), _arrow(30, 13), _slot("out", 64, 2), _slot("out", 84, 2),
                         _slot("out", 64, 22), _slot("out", 84, 22)])),
    ("alloy", (108, 44, [_slot("in", 2, 2), _slot("in", 22, 2), _slot("in", 2, 22), _slot("in", 22, 22),
                         _arrow(52, 13), _slot("out", 86, 12)])),
])
""" 预设的排版：新页面是工作台那一页，左栏「页面」里能换 """

DEFAULT_PRESET = "craft"


def preset(name):  # type: (str) -> tuple
    """ (内容区的宽, 高, 积木的拷贝)；不认识的名字给工作台 """
    width, height, blocks = PRESETS.get(name) or PRESETS[DEFAULT_PRESET]
    return width, height, copy.deepcopy(blocks)


def new_page(name=DEFAULT_PRESET):  # type: (str) -> dict
    width, height, blocks = preset(name)
    return {"id": None, "name": u"", "stations": [], "icon": None, "w": width, "h": height, "fields": [], "blocks": blocks}


def new_recipe(page_id):  # type: (str) -> dict
    return {"id": None, "page": page_id, "in": [], "out": [], "cat": [], "f": {}, "note": u""}


def area(page):  # type: (dict) -> tuple
    """ 内容区的大小（积木摆在它里面）"""
    page = page or {}
    return (clamp_size(page.get("w"), WIDTH_RANGE, DEFAULT_WIDTH),
            clamp_size(page.get("h"), HEIGHT_RANGE, DEFAULT_HEIGHT))


def resize(page, key, delta):  # type: (dict, str, int) -> int
    """ 内容区的宽（key "w"）或高（"h"）加减 delta，夹在范围里；返回新的值 """
    bounds, default = (WIDTH_RANGE, DEFAULT_WIDTH) if key == "w" else (HEIGHT_RANGE, DEFAULT_HEIGHT)
    page[key] = clamp_size(clamp_size(page.get(key), bounds, default) + int(delta), bounds, default)
    return page[key]


def fit(page, size_of, pad=FIT_PAD):  # type: (dict, callable, int) -> bool
    """
    「贴合积木」：积木整体挪到左上角留 pad 的地方，内容区收到积木外框再留 pad（夹在范围里）；没有积木不动。变了给 True
    """
    blocks = page.get("blocks") or []
    if not blocks:
        return False
    boxes = []
    for block in blocks:
        width, height = size_of(block)
        x, y = int(block.get("x") or 0), int(block.get("y") or 0)
        boxes.append((x, y, x + int(width), y + int(height)))
    left, top = min(b[0] for b in boxes), min(b[1] for b in boxes)
    right, bottom = max(b[2] for b in boxes), max(b[3] for b in boxes)
    dx, dy = pad - left, pad - top
    size = (clamp_size(right - left + pad * 2, WIDTH_RANGE, DEFAULT_WIDTH),
            clamp_size(bottom - top + pad * 2, HEIGHT_RANGE, DEFAULT_HEIGHT))
    changed = bool(dx or dy) or size != area(page)
    for block in blocks:
        block["x"] = int(block.get("x") or 0) + dx
        block["y"] = int(block.get("y") or 0) + dy
    page["w"], page["h"] = size
    clamp_all(page, size_of)
    return changed


# 积木
# ======================================================================================================================
def counts(blocks):  # type: (list) -> dict
    result = {}
    for block in blocks or ():
        result[block.get("t")] = result.get(block.get("t"), 0) + 1
    return result


def clamp(block, size, room):  # type: (dict, tuple, tuple) -> dict
    """ 夹回内容区里（大过内容区的贴左上）"""
    block["x"] = int(max(0, min(room[0] - size[0], int(block.get("x") or 0))))
    block["y"] = int(max(0, min(room[1] - size[1], int(block.get("y") or 0))))
    return block


def overlaps(a, size_a, b, size_b):  # type: (dict, tuple, dict, tuple) -> bool
    return (a["x"] < b["x"] + size_b[0] and b["x"] < a["x"] + size_a[0]
            and a["y"] < b["y"] + size_b[1] and b["y"] < a["y"] + size_a[1])


def free_spot(blocks, size, room, size_of, step=4):  # type: (list, tuple, tuple, callable, int) -> tuple
    """ 新放一块的位置：从左上往右下找第一个不和别的积木重叠的地方，找不到放左上 """
    for y in range(0, max(1, room[1] - size[1] + 1), step):
        for x in range(0, max(1, room[0] - size[0] + 1), step):
            probe = {"x": x, "y": y}
            if not any(overlaps(probe, size, other, size_of(other)) for other in blocks):
                return x, y
    return 0, 0


def add_block(page, block, size_of):  # type: (dict, dict, callable) -> int
    """ 放一块（已规整过的积木 dict），摆到空地方；返回它的下标 """
    blocks = page.setdefault("blocks", [])
    size = size_of(block)
    block["x"], block["y"] = free_spot(blocks, size, area(page), size_of)
    blocks.append(block)
    return len(blocks) - 1


def copy_block(page, index, size_of):  # type: (dict, int, callable) -> int or None
    """ 复制一块，放在它右下 4 像素（放不下夹回来）；返回新的下标 """
    blocks = page.get("blocks") or []
    if not 0 <= index < len(blocks):
        return None
    twin = copy.deepcopy(blocks[index])
    twin["x"] = int(twin.get("x") or 0) + 4
    twin["y"] = int(twin.get("y") or 0) + 4
    clamp(twin, size_of(twin), area(page))
    blocks.append(twin)
    return len(blocks) - 1


def remove_block(page, index):  # type: (dict, int) -> bool
    blocks = page.get("blocks") or []
    if not 0 <= index < len(blocks):
        return False
    del blocks[index]
    return True


def clamp_all(page, size_of):  # type: (dict, callable) -> int
    """ 内容区的宽高改了：把跑出内容区的积木夹回来；返回挪了几块 """
    room, moved = area(page), 0
    for block in page.get("blocks") or ():
        before = (block.get("x"), block.get("y"))
        clamp(block, size_of(block), room)
        if (block.get("x"), block.get("y")) != before:
            moved += 1
    return moved


# 配方的格子
# ======================================================================================================================
def holder_of(blocks, index, holds):  # type: (list, int, callable) -> tuple or None
    """ 第 index 块积木是第几个什么格子：(角色, 编号)；不装东西给 None """
    for block_index, role, number in holder_index(blocks, holds):
        if block_index == index:
            return role, number
    return None


def cell(recipe, role, number):  # type: (dict, str, int) -> dict or None
    cells = (recipe or {}).get(role) or []
    return cells[number] if 0 <= number < len(cells) else None


def set_cell(recipe, role, number, entry):  # type: (dict, str, int, dict or None) -> None
    cells = recipe.setdefault(role, [])
    while len(cells) <= number:
        cells.append(None)
    cells[number] = entry
    while cells and cells[-1] is None:
        cells.pop()


def next_empty(blocks, recipe, index, holds):  # type: (list, dict, int, callable) -> int or None
    """ 填好一格之后跳到哪：同一角色里它后面第一个空格（到头了从前面找）；都满了给 None """
    order = holder_index(blocks, holds)
    here = [entry for entry in order if entry[0] == index]
    if not here:
        return None
    role = here[0][1]
    same = [entry for entry in order if entry[1] == role]
    position = same.index(here[0])
    for block_index, _role, number in same[position + 1:] + same[:position]:
        if cell(recipe, role, number) is None:
            return block_index
    return None


def entries_of(recipe, make):  # type: (dict, callable) -> dict
    """ 画工作区用：{角色: [make(格) 或 None]} """
    return dict((role, [make(entry) if entry else None for entry in (recipe or {}).get(role) or ()]) for role in ROLES)


# 检查
# ======================================================================================================================
def page_problems(page, holds, known):  # type: (dict, callable, callable) -> list
    """ 存页面之前要说的：(问题的键, 数)；键在 EditorText.Problems。没起名、没有产物格存不了，别的只提示 """
    problems = []
    blocks = page.get("blocks") or []
    if not (page.get("name") or u"").strip():
        problems.append(("name", 0))
    if not any(role == "out" for _index, role, _number in holder_index(blocks, holds)):
        problems.append(("output", 0))
    unknown = len([block for block in blocks if not known(block)])
    if unknown:
        problems.append(("unknown", unknown))
    return problems


BLOCKING = ("name", "output")
""" 有这几样问题的页面存不了 """
