# coding=utf-8
# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
MEI 自带的积木：一种一个模块，经 ctx.UI.Blocks 登记（和第三方走同一个接口）。加一种 = 加一个模块 + 在 make_blocks 里加一行
"""


def make_blocks():  # type: () -> list
    """ 自带的积木（实例），按控件池里的先后。用到才 import：几个模块拉 UI 层 """
    from .arrow import ArrowBlock
    from .bar import BarBlock
    from .flame import FlameBlock
    from .frame import FrameBlock
    from .image import ImageBlock
    from .item import ItemBlock
    from .plus import PlusBlock
    from .slot import SlotBlock
    from .text import TextBlock
    return [SlotBlock(), ItemBlock(), ArrowBlock(), FlameBlock(), PlusBlock(), BarBlock(), TextBlock(), ImageBlock(),
            FrameBlock()]
