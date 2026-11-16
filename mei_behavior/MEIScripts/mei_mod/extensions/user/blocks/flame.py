# coding=utf-8
# ----------------------------------------------------------------------
#  flame.py is part of MoreEnoughItems.
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
火焰：13 × 13，熔炉的燃烧火焰；带动画时一次 3 秒烧完、每 3 秒重播，不带动画就是一团满的火
"""
from MEIScripts.api.facades.types import BlockProp, BlockType

REPLAY_TICKS = 15


class FlameBlock(BlockType):

    TEMPLATE = {("size", ""): (13, 13), ("visible", "/full"): False, ("visible", "/fill"): False}

    def __init__(self):
        BlockType.__init__(self, "mei:flame", name_key="mei.block.flame", control_def="MeiBlocks.flame", size=(13, 13),
                           limit=4, icon="textures/ui/flame_full_image", sort_index=40, props=[
                               BlockProp("anim", BlockProp.BOOL, "mei.block.prop.anim", default=True),
                           ])

    def IsAnimated(self, block):
        return bool(block.get("anim"))

    def Paint(self, view):
        animated = self.IsAnimated(view.Data)
        view.SetVisible("/full", not animated)
        view.SetVisible("/fill", animated)

    def Tick(self, view, ticks):
        if ticks % REPLAY_TICKS == 0:
            view.Replay("/fill")
