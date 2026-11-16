# coding=utf-8
# ----------------------------------------------------------------------
#  text.py is part of MoreEnoughItems.
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
文字：一行字（最多 32 个字符），里面写 {字段} 换成这条配方的值（{energy} FE 显示成 3200 FE）。三种颜色照原版界面：
灰字（容器标题那种，不带阴影）、白字、黄字（带阴影）—— 阴影是 JSON 定的，所以是两个标签，用哪个写哪个
"""
from collections import OrderedDict

from MEIScripts.api.facades.types import BlockProp, BlockType
from MEIScripts.mei_mod.ui_script.mei_ui.menu.layout import text_width

COLORS = OrderedDict([
    # 颜色: (RGB, 带不带阴影)
    ("gray", ((0.251, 0.251, 0.251), False)),
    ("white", ((1.0, 1.0, 1.0), True)),
    ("yellow", ((1.0, 0.847, 0.29), True)),
])

HEIGHT = 10


class TextBlock(BlockType):

    TEMPLATE = {("size", ""): (24, HEIGHT), ("text", "/plain"): "", ("text", "/shadow"): "",
                ("tcolor", "/plain"): COLORS["gray"][0], ("tcolor", "/shadow"): (1.0, 1.0, 1.0)}

    def __init__(self):
        BlockType.__init__(self, "mei:text", name_key="mei.block.text", control_def="MeiBlocks.text", size=(24, HEIGHT),
                           limit=32, icon="textures/ui/mei/icons/caret", sort_index=70, props=[
                               BlockProp("v", BlockProp.TEXT, "mei.block.prop.text", default=u"文字", max_length=128),
                               BlockProp("c", BlockProp.CHOICE, "mei.block.prop.color", default="gray",
                                         choices=[(name, "mei.block.color." + name) for name in COLORS]),
                           ])

    def SizeOf(self, block):
        return max(12, text_width(block.get("v") or u"")), HEIGHT

    def Paint(self, view):
        color, shadow = COLORS.get(view.Data.get("c")) or COLORS["gray"]
        text = view.Format(view.Data.get("v") or u"")
        view.SetText("/plain", u"" if shadow else text, color)
        view.SetText("/shadow", text if shadow else u"", color)
