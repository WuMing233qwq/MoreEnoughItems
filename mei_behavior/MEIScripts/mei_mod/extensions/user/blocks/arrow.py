# coding=utf-8
# ----------------------------------------------------------------------
#  arrow.py is part of MoreEnoughItems.
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
箭头：四种样式照原版界面（工作台的大箭头、熔炉、向下、酿造台），可以带进度动画 —— JSON 里一次 3 秒的 clip 动画，节拍里每 3 秒重播一遍
（和配方页一样不写 next 循环）。向下的箭头没有进度图，不动
"""
from collections import OrderedDict

from MEIScripts.api.facades.types import BlockProp, BlockType

REPLAY_TICKS = 15
""" 节拍 0.2 秒一拍：3 秒重播一次 """

STYLES = OrderedDict([
    # 样式: (大小, 底图, 进度图的控件, 进度图)
    ("large", ((24, 17), "textures/ui/arrow_large", "/fill_h", "textures/ui/arrow_active")),
    ("furnace", ((22, 15), "textures/ui/arrow_inactive", "/fill_h", "textures/ui/arrow_active")),
    ("down", ((15, 22), "textures/ui/arrow_down_large", None, None)),
    ("brew", ((9, 28), "textures/ui/brewing_arrow_empty", "/fill_v", "textures/ui/brewing_arrow_full")),
])

FILLS = ("/fill_h", "/fill_v")


class ArrowBlock(BlockType):

    TEMPLATE = {("size", ""): (24, 17), ("sprite", "/base"): "textures/ui/arrow_large", ("visible", "/fill_h"): False,
                ("visible", "/fill_v"): False, ("sprite", "/fill_h"): "textures/ui/arrow_active",
                ("sprite", "/fill_v"): "textures/ui/brewing_arrow_full"}

    def __init__(self):
        BlockType.__init__(self, "mei:arrow", name_key="mei.block.arrow", control_def="MeiBlocks.arrow", size=(24, 17),
                           limit=8, icon="textures/ui/arrow_large", sort_index=30, props=[
                               BlockProp("s", BlockProp.CHOICE, "mei.block.prop.style", default="large",
                                         choices=[(name, "mei.block.arrow." + name) for name in STYLES]),
                               BlockProp("anim", BlockProp.BOOL, "mei.block.prop.anim", default=True),
                           ])

    @staticmethod
    def Style(block):  # type: (dict) -> tuple
        return STYLES.get(block.get("s")) or STYLES["large"]

    def SizeOf(self, block):
        return self.Style(block)[0]

    def IsAnimated(self, block):
        return bool(block.get("anim")) and self.Style(block)[2] is not None

    def Paint(self, view):
        _size, base, fill, texture = self.Style(view.Data)
        animated = self.IsAnimated(view.Data)
        view.SetSprite("/base", base)
        for path in FILLS:
            view.SetVisible(path, animated and path == fill)
        if animated:
            view.SetSprite(fill, texture)

    def Tick(self, view, ticks):
        if ticks % REPLAY_TICKS == 0:
            view.Replay(self.Style(view.Data)[2])
