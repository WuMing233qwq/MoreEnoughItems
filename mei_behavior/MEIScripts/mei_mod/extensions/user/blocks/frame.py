# coding=utf-8
# ----------------------------------------------------------------------
#  frame.py is part of MoreEnoughItems.
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
底框：配方页那种浅色圆角框（textures/ui/mei/recipe/recipe_bg），宽高自己定，垫在别的积木底下（JSON 里层级最低）
"""
from MEIScripts.api.facades.types import BlockProp, BlockType
from MEIScripts.mei_mod.state.user_recipes import HEIGHT_RANGE, WIDTH_RANGE


class FrameBlock(BlockType):

    TEMPLATE = {("size", ""): (60, 40)}

    def __init__(self):
        BlockType.__init__(self, "mei:frame", name_key="mei.block.frame", control_def="MeiBlocks.frame", size=(60, 40),
                           limit=8, icon="textures/ui/mei/recipe/recipe_bg", sort_index=80, props=[
                               BlockProp("w", BlockProp.INT, "mei.block.prop.width", default=60, minimum=8, maximum=WIDTH_RANGE[1], step=2),
                               BlockProp("h", BlockProp.INT, "mei.block.prop.height", default=40, minimum=8, maximum=HEIGHT_RANGE[1], step=2),
                           ])

    def SizeOf(self, block):
        return int(block.get("w") or 60), int(block.get("h") or 40)
