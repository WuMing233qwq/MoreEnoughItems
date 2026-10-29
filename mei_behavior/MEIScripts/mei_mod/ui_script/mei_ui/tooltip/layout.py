# coding=utf-8

# ----------------------------------------------------------------------
#  layout.py is part of MoreEnoughItems.
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
tooltip 的纯计算：接受物品排几行几列、贴着屏幕边时往哪边翻。不碰引擎
"""

MAX_COLS = 9
""" 接受物品一行最多几个（原版背包的宽度） """

MAX_ROWS = 6
""" 最多几行；再多就只摆满 MAX_COLS × MAX_ROWS 格，最后一格不画物品、写「+N」（还有几个没显示，tooltip/items.py） """

GAP = 12
"""
tooltip 离光标多远的缺省值。实际用的是 JSON 里 mei_common.tooltip_root/desktop/cursor_gap 的 offset
（管理器每次显示时读，见 cursor_gap），读不到才用这个
"""


def grid_shape(count, max_cols=MAX_COLS, max_rows=MAX_ROWS):  # type: (int, int, int) -> tuple
    """ (列数, 行数, 实际显示几个)；没有东西给 (0, 0, 0) """
    if count <= 0 or max_cols <= 0 or max_rows <= 0:
        return 0, 0, 0
    cols = min(count, max_cols)
    shown = min(count, cols * max_rows)
    rows = (shown + cols - 1) // cols
    return cols, rows, shown


def cursor_gap(x, y):  # type: (float, float) -> tuple
    """
    JSON 里读到的 (横, 竖) 规整成 place 的 gap：取整；两个数不能同时为 0（同时为 0 时竖向当成 1）——
    光标不能落在 tooltip 上：tooltip 里的格子自己也有悬停（配方预览的多候选格还会出 tooltip），落上去就换成悬停它们了。
    只要有一个方向隔开了，光标就在 tooltip 外面（比如 (11, 0)：右边隔 11，顶边与光标齐平）
    """
    x, y = int(round(x)), int(round(y))
    if not x and not y:
        y = 1
    return x, y


def place(cursor, size, bounds, gap=GAP):  # type: (tuple, tuple, tuple, any) -> tuple
    """
    tooltip 相对光标的偏移 (dx, dy)。gap 一个数（两个方向一样）或 (横, 竖)：绝对值是 tooltip 离光标多远，
    正负号是默认在光标哪边 —— 横向正数在右、负数在左，竖向正数在下、负数在上（缺省 GAP 是右下）；
    换句话说，tooltip 离光标最近的那个角落在「光标 + gap」。默认那边放不下翻到另一边（距离不变），
    两边都放不下就贴着屏幕边（宁可压住光标也别出屏）。
    cursor 光标 (x, y)，size tooltip (宽, 高)，bounds 可用区域 ((左, 上), (右, 下))，都是全局坐标
    """
    x, y = cursor
    width, height = size
    (left, top), (right, bottom) = bounds
    gap_x, gap_y = gap if isinstance(gap, (tuple, list)) else (gap, gap)
    return _axis(x, width, left, right, gap_x), _axis(y, height, top, bottom, gap_y)


def _axis(at, length, low, high, gap):  # type: (float, float, float, float, float) -> float
    distance = abs(gap)
    sides = [(at + distance + length <= high, distance),  # 光标后面（右 / 下）
             (at - distance - length >= low, -distance - length)]  # 光标前面（左 / 上）
    if gap < 0:
        sides.reverse()
    for fits, offset in sides:
        if fits:
            return offset
    # 两边都放不下：贴着放得下的那条边，实在太大就顶着起点
    return max(low - at, high - length - at)


def contains(rect, point):  # type: (tuple, tuple) -> bool
    """ 点在不在矩形里（左上闭、右下开）。rect ((左, 上), (右, 下))，point (x, y) """
    (left, top), (right, bottom) = rect
    x, y = point
    return left <= x < right and top <= y < bottom


BESIDE_GAP = 2
""" 移动端 tooltip 离格子多远 """


def place_beside(rect, size, bounds, gap=BESIDE_GAP):  # type: (tuple, tuple, tuple, int) -> tuple
    """
    移动端：tooltip 摆在格子旁边、不跟手指走 —— 右侧顶边对齐，右边放不下放左边，两边都放不下就贴屏幕右边；
    上下夹在屏幕里。返回 tooltip 左上角的全局坐标。rect 格子、bounds 可用区域都是 ((左, 上), (右, 下))
    """
    (left, top), (right, _) = rect
    width, height = size
    (b_left, b_top), (b_right, b_bottom) = bounds
    x = right + gap
    if x + width > b_right:
        x = left - gap - width
        if x < b_left:
            x = max(b_left, b_right - width)
    y = max(b_top, min(top, b_bottom - height))
    return x, y


SIDE_LEFT = "left"
SIDE_RIGHT = "right"

EDGE_MARGIN = 2
""" 摆到屏幕边上时离边多远（设置「触控tooltip是否沿对面侧显示」）"""


def place_opposite(rect, size, bounds, margin=EDGE_MARGIN):  # type: (tuple, tuple, tuple, int) -> tuple
    """
    设置「触控tooltip是否沿对面侧显示」开着时的移动端摆法：摆到点的那一格**另一侧**的屏幕边上 —— 格子在屏幕右半边就贴左边缘，
    在左半边就贴右边缘（方便移动端双手操作）；竖直方向跟着那一格、夹在屏幕里。返回左上角的全局坐标
    """
    (left, top), (right, _) = rect
    width, height = size
    (b_left, b_top), (b_right, b_bottom) = bounds
    if (left + right) / 2.0 >= (b_left + b_right) / 2.0:
        x = b_left + margin
    else:
        x = b_right - margin - width
    x = max(b_left, min(x, b_right - width))
    return x, max(b_top, min(top, b_bottom - height))


def place_outside(rect, size, region, side, bounds, gap=BESIDE_GAP):  # type: (tuple, tuple, tuple, str, tuple, int) -> tuple
    """
    触屏菜单：摆在格子所在区域（物品栏、收藏栏、配方页）的外侧，连续浏览时不挡着区域里的格子。
    side 是首选的一侧：那边放不下换另一侧；两边都放不下退回 place_beside（摆在格子旁、贴屏幕边 —— 原来的出屏检测留着兜底）。
    竖直方向和那一格顶边对齐、夹在屏幕里。rect 格子、region 区域、bounds 可用区域都是 ((左, 上), (右, 下))，返回左上角全局坐标
    """
    (r_left, _), (r_right, _) = region
    (_, top), _ = rect
    width, height = size
    (b_left, b_top), (b_right, b_bottom) = bounds
    left_x, right_x = r_left - gap - width, r_right + gap
    for x in ((right_x, left_x) if side == SIDE_RIGHT else (left_x, right_x)):
        if x >= b_left and x + width <= b_right:
            return x, max(b_top, min(top, b_bottom - height))
    return place_beside(rect, size, bounds, gap)
