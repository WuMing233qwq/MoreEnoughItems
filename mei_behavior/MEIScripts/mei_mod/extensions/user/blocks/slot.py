# coding=utf-8
# ----------------------------------------------------------------------
#  slot.py is part of MoreEnoughItems.
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
物品格：20 × 20（MEI 自己的格子大小），装一样物品（原料 / 产物 / 催化剂；流体也是 —— 流体在 MEI 里以物品身份登记，数量写 mB 的数）。
右下数量，左上蓝点是催化剂、右上黄点是有概率、左下紫点是几样之一（候选、标签，轮换显示）；编辑器里空格写「原1」这类占位。
点它照 MEI 的格子处理（JSON 的 btn 映射到 button.mei.block.*）
"""
from MEIScripts.api.facades.types import BlockType
from MEIScripts.common.classes.types.block import ROLE_CAT
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree.controls.cell import short_count


def paint_marks(view):
    """ 装东西的积木共用：催化剂 / 概率 / 几样之一三个小点与悬停文字 """
    stack = view.Stack
    view.SetVisible("/cat", view.Role == ROLE_CAT and (stack is not None or view.Editing))
    view.SetVisible("/chance", stack is not None and view.Chance < 1)
    view.SetVisible("/multi", stack is not None and (len(view.Stacks) > 1 or bool(view.Entry.get_tag_id())))
    view.SetHoverText("/btn/hover/hover_text", view.EntryHoverText())


class SlotBlock(BlockType):

    TEMPLATE = {("size", ""): (20, 20), ("item", "/renderer"): None, ("text", "/hint"): "", ("text", "/count"): "",
                ("visible", "/cat"): False, ("visible", "/chance"): False, ("visible", "/multi"): False,
                ("hover", "/btn/hover/hover_text"): ""}

    def __init__(self):
        BlockType.__init__(self, "mei:slot", name_key="mei.block.slot", control_def="MeiBlocks.slot", size=(20, 20),
                           limit=64, holds=True, icon="textures/ui/cell_image", sort_index=10)

    def Paint(self, view):
        stack = view.Stack
        view.SetItem("/renderer", stack)
        view.SetText("/hint", view.Label if (stack is None and view.Editing) else "")
        view.SetText("/count", short_count(view.Amount) if stack is not None else "")
        paint_marks(view)
