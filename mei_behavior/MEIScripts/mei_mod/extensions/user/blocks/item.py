# coding=utf-8
# ----------------------------------------------------------------------
#  item.py is part of MoreEnoughItems.
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
物品：画一样固定的物品（装饰：机器的图标、要用的工具……，不是配方的格子），大小自己定。物品在编辑器里打「命名空间:名字[:附加值]」，
或者点「选」再点 MEI 物品栏里的一样（带附魔这类也照原样）。悬停、点击照 MEI 的格子处理（查来源 / 用途）。
物品表里找不到的（模组卸了）不画，编辑器里画一个问号
"""
from MEIScripts.api.facades.types import BlockProp, BlockType


class ItemBlock(BlockType):

    TEMPLATE = {("size", ""): (16, 16), ("item", "/renderer"): None, ("visible", "/missing"): False,
                ("hover", "/btn/hover/hover_text"): ""}

    def __init__(self):
        BlockType.__init__(self, "mei:item", name_key="mei.block.item", control_def="MeiBlocks.item", size=(16, 16),
                           limit=32, icon="textures/items/item_frame", sort_index=15, props=[
                               BlockProp("item", BlockProp.ITEM, "mei.block.prop.item"),
                               BlockProp("s", BlockProp.INT, "mei.block.prop.size", default=16, minimum=8, maximum=64, step=2),
                           ])

    def SizeOf(self, block):
        size = int(block.get("s") or 16)
        return size, size

    def ShownItem(self, view):
        return view.PropItem("item")

    def Paint(self, view):
        item = self.ShownItem(view)
        view.SetItem("/renderer", item)
        view.SetVisible("/missing", view.Editing and item is None)
        view.SetHoverText("/btn/hover/hover_text", view.HoverOf(item) if item is not None else "")
