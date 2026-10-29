# coding=utf-8
# ----------------------------------------------------------------------
#  keys.py is part of MoreEnoughItems.
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
按键的码、修饰键、一组按键怎么存、怎么显示（纯数据、纯函数，不碰引擎）—— MEI 自己的按键绑定（docs/architecture/bookmarks.md §12）。

- 键码就是裸按键 OnKeyPressInGame 给的那个（Windows 的虚拟键码，和 KeyBoardType 枚举是同一套）：字母 65~90、数字 48~57……
- 修饰键 Shift 16 / Ctrl 17 / Alt 18（引擎不分左右），一组按键里记成修饰位 SHIFT | CTRL | ALT
- 滚轮不是键：滚轮类的动作主键写 WHEEL，向上 / 向下在动作里当 +1 / -1
- 一组按键存成 [修饰位, 主键]（JSON 存得下）；主键 0 是「不绑定」
"""

SHIFT = 1
CTRL = 2
ALT = 4
ALL_MODS = SHIFT | CTRL | ALT

MOD_BITS = {16: SHIFT, 17: CTRL, 18: ALT}
""" 修饰键的键码 -> 修饰位 """

MOD_ORDER = ((CTRL, "Ctrl"), (SHIFT, "Shift"), (ALT, "Alt"))
""" 显示顺序：Ctrl + Shift + Alt + 主键（各家游戏的写法）"""

NONE = 0
""" 主键 0 = 不绑定 """

WHEEL = 1000
""" 滚轮（不是真的键码，比所有键码都大）"""

IME = 229
""" Windows 的 VK_PROCESSKEY：中文输入法吃掉的键，真正是哪个键不知道（引擎结论 §42）—— 不当快捷键、也不录 """

KEY_TAB = 9
KEY_DELETE = 46
""" 录键时单按 Delete（不带修饰键）= 清除绑定 """

WIN_KEYS = (91, 92)
""" Win 键：按下多半是要切走窗口，修饰键的松开可能收不到 —— 全部当已松开 """

MOUSE_CODES = (1, 2, 4, 5, 6)
""" 鼠标键的虚拟键码：万一裸按键也报它们，不当快捷键、不录（点按钮保存那一下就是左键）"""

UNBOUND = (0, 0)

NAMES = {
    8: "Backspace", 9: "Tab", 13: "Enter", 19: "Pause", 20: "CapsLock", 27: "Esc", 32: "Space",
    33: "PageUp", 34: "PageDown", 35: "End", 36: "Home", 37: "Left", 38: "Up", 39: "Right", 40: "Down",
    45: "Insert", 46: "Delete", 106: "Num*", 107: "Num+", 109: "Num-", 110: "Num.", 111: "Num/",
    186: ";", 187: "=", 188: ",", 189: "-", 190: ".", 191: "/", 192: "`", 219: "[", 220: "\\", 221: "]", 222: "'",
    WHEEL: "滚轮",
}
""" 显示用的键名：方向键写英文（Up / Down），不用箭头符号 —— 字体里未必有 """


def key_name(code):  # type: (int) -> str
    """ 一个主键的名字 """
    if code in NAMES:
        return NAMES[code]
    if 65 <= code <= 90 or 48 <= code <= 57:
        return chr(code)
    if 96 <= code <= 105:
        return "Num" + chr(code - 48)
    if 112 <= code <= 135:
        return "F%d" % (code - 111)
    return "Key%d" % code


def mask_names(mask):  # type: (int) -> list
    return [name for bit, name in MOD_ORDER if mask & bit]


def normalize(value):  # type: (any) -> list
    """ 存盘 / 设置里的值 -> [修饰位, 主键]；看不懂抛 TypeError / ValueError（设置框架按默认值走）"""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise TypeError("key binding wants [mask, key], got {!r}".format(value))
    mask, code = value
    for number in (mask, code):
        if not isinstance(number, (int, long)) or isinstance(number, bool):  # noqa
            raise TypeError("key binding wants integers, got {!r}".format(value))
    if mask < 0 or mask > ALL_MODS or code < 0:
        raise ValueError("bad key binding {!r}".format(value))
    if code == NONE:
        return [0, 0]
    return [int(mask), int(code)]


def is_bound(combo):  # type: (any) -> bool
    return bool(combo) and combo[1] != NONE


def format_combo(combo):  # type: (any) -> str
    """ 「Ctrl + Shift + A」「Ctrl + 滚轮」；没绑定给「未绑定」"""
    if not is_bound(combo):
        return "未绑定"
    return " + ".join(mask_names(combo[0]) + [key_name(combo[1])])
