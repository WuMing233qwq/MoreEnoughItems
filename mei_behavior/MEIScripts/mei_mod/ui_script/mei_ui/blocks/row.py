# coding=utf-8
# ----------------------------------------------------------------------
#  row.py is part of MoreEnoughItems.
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
自制配方页的一行怎么排（纯计算；托管配方页 extensions/user/host.py 与编辑器的工作区 editor/workspace.py 共用）：
内容区（页面的宽 × 高，积木摆在里面）在左上；按钮一排横在内容区下面、隔 3，右边和内容区对齐 ——
照 mei_recipe_common.buttons_panel_horizontal：按钮 13 × 13、每格 14（按钮之间隔 1 像素）。内容区比这一排按钮窄时按钮从左边起。
JSON 里 MeiBlocks.row 的缺省尺寸就是 row_layout(172, 70) 算出来的那一套（托管者把它记成写过，一样的不写）
"""

PAD_LEFT = 6
PAD_RIGHT = 10
""" 右边多留 4：配方页右侧的竖页签盖住内容区右边 4 像素（docs/architecture/recipe_page.md）"""
PAD_TOP = 2
PAD_BOTTOM = 2
BUTTONS_GAP = 3
""" 内容区和按钮那一排之间 """
BUTTON = 13
BUTTON_PITCH = 14
""" 一个按钮占的宽：13 的按钮 + 1 像素的缝 """
BUTTONS = 4
""" 一行几个按钮（配方树、置顶、收藏、+ 配方转移）"""


def buttons_width(count=BUTTONS):  # type: (int) -> int
    return BUTTON_PITCH * count


def row_layout(width, height, count=BUTTONS):  # type: (int, int, int) -> dict
    """ 内容区 width × height 的一行：{"size": 行的大小, "content": 内容区的位置, "buttons": 按钮那一排的位置}（都相对行的左上角）"""
    width, height = int(width), int(height)
    row_buttons = buttons_width(count)
    inner = max(width, row_buttons)
    top = PAD_TOP + height + BUTTONS_GAP
    return {"size": (PAD_LEFT + inner + PAD_RIGHT, top + BUTTON + PAD_BOTTOM),
            "content": (PAD_LEFT, PAD_TOP),
            "buttons": (PAD_LEFT + inner - row_buttons, top)}
