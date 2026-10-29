# coding=utf-8

# ----------------------------------------------------------------------
#  grid_layout.py is part of MoreEnoughItems.
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

def row_room(blocked, cols, rows):  # type: (set, int, int) -> int
    """
    被挡住的格子（下标 = 行 * 列数 + 列）去掉后，每行还剩几格，取最少的那一行。
    避让不改列数（被挡的格子只是不放东西），悬浮窗的自动收起阈值看的是这个数；没有行时就是列数
    """
    if cols <= 0:
        return 0
    worst = 0
    for row in range(max(0, rows)):
        base = row * cols
        worst = max(worst, sum(1 for index in range(base, base + cols) if index in blocked))
    return cols - worst


class GridLayout(object):
    """
    网格布局计算器
    将所有像素→网格维度的转换封装到一处
    消除散落在各处的魔法数字
    """
    PADDING = 10        # 网格区域的左右总内边距
    HEADER_HEIGHT = 54  # 顶部控件占的高度（翻页栏等）

    def __init__(self, item_size, max_cols):  # type: (int, int) -> None
        self.ItemSize = item_size  # type: int
        self.MaxCols = max_cols    # type: int
        self._cols = max_cols      # type: int
        self._rows = 0            # type: int

    def Recalculate(self, available_height):  # type: (int) -> None
        """ 根据可用区域高度重新计算行数 """
        self._rows = max(1, int((available_height - self.HEADER_HEIGHT) // self.ItemSize))

    def ApplyCols(self, cols):  # type: (int) -> None
        """ 应用指定的列数 """
        self._cols = max(1, min(cols, self.MaxCols))

    def ResetCols(self):
        """ 重置为最大列数 """
        self._cols = self.MaxCols

    def CalcAvoidanceCols(self, available_width):  # type: (int) -> int
        """ 根据可用宽度计算避让后的列数 """
        return max(1, int((available_width - self.PADDING) // self.ItemSize))

    def NeedsAvoidance(self, absolute_root_width, content_right_x):  # type: (int, int) -> bool
        """ 判断默认布局是否与内容区域重叠 """
        default_left_edge = absolute_root_width - self.DefaultWrapperWidth
        return default_left_edge <= content_right_x

    @property
    def Cols(self):  # type: () -> int
        return self._cols

    @property
    def Rows(self):  # type: () -> int
        return self._rows

    @property
    def Capacity(self):  # type: () -> int
        return self._cols * self._rows

    @property
    def GridWidth(self):  # type: () -> int
        """ 网格控件宽度（不含外部padding） """
        return self._cols * self.ItemSize

    @property
    def GridHeight(self):  # type: () -> int
        """ 网格控件高度 """
        return self._rows * self.ItemSize

    @property
    def WrapperWidth(self):  # type: () -> int
        """ 包含padding的包装器宽度 """
        return self._cols * self.ItemSize + self.PADDING

    @property
    def DefaultWrapperWidth(self):  # type: () -> int
        """ 使用最大列数时的包装器宽度 """
        return self.MaxCols * self.ItemSize + self.PADDING
