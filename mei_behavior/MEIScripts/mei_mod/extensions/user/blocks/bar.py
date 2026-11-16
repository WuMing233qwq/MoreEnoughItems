# coding=utf-8
# ----------------------------------------------------------------------
#  bar.py is part of MoreEnoughItems.
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
数值条：6 宽、34 / 50 高，按这一页的一个数值字段（能量、时间……）画满多少 —— 这条配方的值占这一页里最大的那个的多少；
悬停写「能量：3200 FE」。没绑字段、这条配方没填的是空条
"""
from MEIScripts.api.facades.types import BlockProp, BlockType

HEIGHTS = (34, 50)


class BarBlock(BlockType):

    TEMPLATE = {("size", ""): (6, 50), ("size", "/fill"): (4, 0), ("hover", "/hover/hover/hover_text"): ""}

    def __init__(self):
        BlockType.__init__(self, "mei:bar", name_key="mei.block.bar", control_def="MeiBlocks.bar", size=(6, 50),
                           limit=4, icon="textures/ui/mei/icons/clock", sort_index=60, props=[
                               BlockProp("h", BlockProp.CHOICE, "mei.block.prop.height", default=50,
                                         choices=[(h, str(h)) for h in HEIGHTS]),
                               BlockProp("field", BlockProp.FIELD, "mei.block.prop.field"),
                           ])

    def SizeOf(self, block):
        height = block.get("h")
        return 6, height if height in HEIGHTS else 50

    def Paint(self, view):
        field = view.Data.get("field") or ""
        height = self.SizeOf(view.Data)[1]
        ratio = view.FieldRatio(field) if field else 0.0
        view.SetSize("/fill", (4, int(round((height - 2) * ratio))))
        text = u""
        if field:
            text = view.FieldText(field) or (view.Painter.FieldInfo(field)[0] if view.Editing else u"")
        view.SetHoverText("/hover/hover/hover_text", text)
