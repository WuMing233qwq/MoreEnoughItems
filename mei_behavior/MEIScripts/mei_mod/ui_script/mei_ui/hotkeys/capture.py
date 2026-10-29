# coding=utf-8
# ----------------------------------------------------------------------
#  capture.py is part of MoreEnoughItems.
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
录键（纯状态机，不碰引擎）—— 照各大游戏的做法，点一下开始录、按下的键都记下、再点一下保存。

- 录的是**按过的全部键**，不是此刻按着的：修饰键记成修饰位（按过就算，松开不删），别的键记成主键（再按别的就换成它 —— 一组只有一个主键）；
- 229（输入法吃掉的键）不录，记一笔好提示切英文；鼠标键不录（点按钮保存那一下就是左键）；
- 单按 Delete（不带修饰键）= 清除绑定；
- 滚轮类只认「修饰键 + 滚轮」：键盘上的主键不录，光滚轮不让存（会抢了各界面的翻页）。
按钮上的字（Text）：没录到东西「> … <」、只有修饰键「> Ctrl + … <」、录好了「> Ctrl + A <」，黄字（§e）表示正在录。
"""
from . import keys, table

RECORDING = "§e"
""" 正在录的按钮字是黄的 """


class Capture(object):
    def __init__(self):
        self.Id = None  # type: str or None  # 正在录哪个快捷键
        self.Kind = table.PRESS
        self.Mask = 0
        self.Key = keys.NONE
        self.Ime = False
        self.Clear = False

    def Reset(self):  # type: () -> None
        self.__init__()

    def Active(self):  # type: () -> bool
        return self.Id is not None

    def Start(self, hotkey):  # type: (table.Hotkey) -> None
        self.Reset()
        self.Id = hotkey.Id
        self.Kind = hotkey.Kind

    def FeedKey(self, code):  # type: (int) -> None
        """ 录键时按下了一个键（按住连发的那几下 manager 已经滤掉）"""
        if code in keys.MOD_BITS:
            self.Mask |= keys.MOD_BITS[code]
        elif code == keys.IME:
            self.Ime = True
        elif code in keys.MOUSE_CODES:
            pass
        elif code == keys.KEY_DELETE and not self.Mask:
            self.Clear, self.Key = True, keys.NONE
        elif self.Kind == table.PRESS:
            self.Clear, self.Key, self.Ime = False, code, False

    def FeedWheel(self):  # type: () -> None
        if self.Kind == table.WHEEL:
            self.Clear, self.Key = False, keys.WHEEL

    def Result(self):  # type: () -> list or None
        """ 再点一下时存什么：[修饰位, 主键]；[0, 0] 是清除绑定；None 是没录成（不存，原来的键位不动）"""
        if self.Clear:
            return list(keys.UNBOUND)
        if self.Key == keys.NONE:
            return None
        if self.Kind == table.WHEEL and not self.Mask:
            return None
        return [self.Mask, self.Key]

    def Text(self):  # type: () -> str
        """ 正在录时按钮上的字 """
        if self.Clear:
            return RECORDING + "> 清除绑定 <"
        if self.Ime and self.Key == keys.NONE:
            return RECORDING + "> 请切到英文 <"
        names = keys.mask_names(self.Mask)
        if self.Key == keys.NONE:
            return RECORDING + "> " + " + ".join(names + ["…"]) + " <"
        if self.Kind == table.WHEEL and not self.Mask:
            return RECORDING + "> 要加修饰键 <"
        return RECORDING + "> " + keys.format_combo([self.Mask, self.Key]) + " <"
