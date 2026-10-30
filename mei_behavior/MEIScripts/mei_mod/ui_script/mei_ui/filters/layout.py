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
筛选与排序菜单（排版 D：标签块 + 步进器，docs/architecture/modes.md §8）的纯计算：框里每样东西摆在哪、多大。不碰引擎。

  筛选与排序 ………………………………… x
  筛选（按下的都要满足）
  [防具] [武器] [食物] [燃料] [有耐久] …    ← 标签块，一行放不下就换行；超过 SCROLL_ROWS 行就在固定高的框里上下滚
  排序
  ‹  名称  ›  [升序]                          ← 步进器：‹ › 换排序的属性（含「不排序」），右边切升 / 降
  ─────────────────
                          [清除] [确定]

全部绝对定位（同触屏菜单，menu/layout.py）；按钮宽按字算，字宽估算也用触屏菜单那一份
"""
from MEIScripts.mei_mod.ui_script.mei_ui.menu.layout import BUTTON_PAD, MIN_BUTTON_W, text_width

WIDTH = 150
""" 框宽 """

PAD = 4
""" 框的内边距 """

GAP = 2
""" 标签块之间、步进器各部分之间的空隙 """

ROW_GAP = 3
""" 一段与下一段之间的空隙 """

BUTTON_H = 14
""" 标签块、按钮的高（同触屏菜单）"""

ICON = 14
""" 步进器的左右箭头、右上角的关闭 """

SECTION_H = 10
""" 段名（灰字）一行的高 """

TEXT_DY = 3
""" 按钮高里摆一行字时，字往下挪多少才居中 """

VALUE_W = 52
""" 步进器中间写排序名字的那一格宽 """

SCROLL_ROWS = 8
""" 标签块超过这么多行才滚动（阈值可以大一些）：框里只给这么高，多的上下滚 """

SCROLLBAR_W = 6
""" 要滚动时，右边给滚动条留的宽（标签块按扣掉它的宽重排）"""

INNER_W = WIDTH - 2 * PAD
""" 框里能摆东西的宽 """


def chip_width(text):  # type: (any) -> int
    """ 一个标签块多宽：字宽 + 两边留白，至少 MIN_BUTTON_W（颜色码不占宽，按下 / 弹起不变宽）"""
    return max(MIN_BUTTON_W, text_width(text) + 2 * BUTTON_PAD)


def rows_height(rows):  # type: (int) -> int
    """ 几行标签块总共多高 """
    return rows * BUTTON_H + max(0, rows - 1) * GAP if rows > 0 else 0


def pack_chips(widths, avail):  # type: (list, int) -> tuple
    """
    标签块从左往右摆，一行放不下就换行（单个比整行还宽的独占一行）。
    返回 ([(x, y) 相对标签区左上角], 行数)
    """
    positions, x, row = [], 0, 0
    for width in widths:
        if x > 0 and x + width > avail:
            x, row = 0, row + 1
        positions.append((x, row * (BUTTON_H + GAP)))
        x += width + GAP
    return positions, (row + 1 if widths else 0)


def chips_area(widths, avail=INNER_W, max_rows=SCROLL_ROWS):  # type: (list, int, int) -> dict
    """
    标签区：放得下就照内容高，放不下就固定 max_rows 行高、上下滚（标签块按扣掉滚动条的宽重排）。
    返回 {"positions", "rows", "content": (宽, 高), "view": (宽, 高), "scroll": 要不要滚}
    """
    positions, rows = pack_chips(widths, avail)
    scroll = rows > max_rows
    if scroll:
        positions, rows = pack_chips(widths, avail - SCROLLBAR_W)
    content_h = rows_height(rows)
    view_h = rows_height(max_rows) if scroll else content_h
    return {
        "positions": positions,
        "rows": rows,
        "content": (avail - SCROLLBAR_W if scroll else avail, content_h),
        "view": (avail, view_h),
        "scroll": scroll,
    }


def menu_layout(chip_texts, value_text, dir_texts, foot_texts, max_rows=SCROLL_ROWS):
    # type: (list, any, list, list, int) -> dict
    """
    整个框的排版。chip_texts 是标签块上的字（决定宽），value_text 是步进器中间现在写的排序名，
    dir_texts 是升 / 降按钮可能写的几种字（宽取最宽的，切换时不跳），foot_texts 是底下两个按钮 [清除, 确定] 的字。
    返回各部分的 (x, y) 与尺寸，坐标相对框的左上角
    """
    out = {}
    y = PAD
    out["title"] = (PAD, y + TEXT_DY)
    out["close"] = (WIDTH - PAD - ICON, y)
    y += ICON + ROW_GAP

    out["filter_section"] = (PAD, y)
    y += SECTION_H + GAP
    area = chips_area([chip_width(text) for text in chip_texts], INNER_W, max_rows)
    out["chips"] = area
    out["chips_pos"] = (PAD, y)
    y += area["view"][1] + ROW_GAP

    out["sort_section"] = (PAD, y)
    y += SECTION_H + GAP
    x = PAD
    out["prev"] = (x, y)
    x += ICON + GAP
    value_w = text_width(value_text)
    out["value"] = (x + max(0, (VALUE_W - value_w) // 2), y + TEXT_DY)
    x += VALUE_W + GAP
    out["next"] = (x, y)
    x += ICON + 2 * GAP
    dir_w = max(chip_width(text) for text in dir_texts) if dir_texts else MIN_BUTTON_W
    out["dir"] = ((x, y), (min(dir_w, WIDTH - PAD - x), BUTTON_H))
    y += BUTTON_H + ROW_GAP

    out["line"] = ((PAD, y), (INNER_W, 1))
    y += 1 + ROW_GAP

    right = WIDTH - PAD
    feet = []
    for text in reversed(foot_texts):
        width = chip_width(text)
        right -= width
        feet.append(((right, y), (width, BUTTON_H)))
        right -= GAP
    out["foot"] = list(reversed(feet))
    y += BUTTON_H + PAD
    out["size"] = (WIDTH, y)
    return out


def place_menu(size, button_rect, avoid_rect, screen_rect, gap=2):  # type: (tuple, tuple, tuple, tuple, int) -> tuple
    """
    框摆在屏幕上哪（全局坐标的左上角）：贴在 avoid_rect（物品栏）的左边、上沿对齐筛选按钮；左边放不下就压在物品栏上、
    右沿对齐按钮、摆在按钮下面。最后夹在屏幕里。矩形都是 (x0, y0, x1, y1)；button_rect 量不出来给 None 时按屏幕右上角摆
    """
    width, height = size
    sx0, sy0, sx1, sy1 = screen_rect
    if button_rect is None:
        x, y = sx1 - width - gap, sy0 + gap
    else:
        left = (avoid_rect or button_rect)[0]
        x, y = left - gap - width, button_rect[1]
        if x < sx0:
            x, y = button_rect[2] - width, button_rect[3] + gap
    x = min(max(x, sx0), sx1 - width)
    y = min(max(y, sy0), sy1 - height)
    return x, y
