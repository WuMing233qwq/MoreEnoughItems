# coding=utf-8
# ----------------------------------------------------------------------
#  plus.py is part of MoreEnoughItems.
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
加号：13 × 13，原版铁砧的「+」，摆在几样原料中间
"""
from MEIScripts.api.facades.types import BlockType


class PlusBlock(BlockType):

    TEMPLATE = {("size", ""): (13, 13)}

    def __init__(self):
        BlockType.__init__(self, "mei:plus", name_key="mei.block.plus", control_def="MeiBlocks.plus", size=(13, 13),
                           limit=8, icon="textures/ui/anvil-plus", sort_index=50)
