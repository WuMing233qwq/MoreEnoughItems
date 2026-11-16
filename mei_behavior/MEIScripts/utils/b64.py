# coding=utf-8
# ----------------------------------------------------------------------
#  b64.py is part of MoreEnoughItems.
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
base64（标准字母表、末尾补 =）的纯 Python 实现，零引擎依赖。

标准库被裁过（CLAUDE.md 引擎结论 §8），base64 模块靠的 binascii 没核实过在不在 —— 用到 base64 的地方（剪贴板的导入导出）一律走这里，
不探测「有就用标准库」：两种写法结果一样，可这样 PC、手机、引擎升级前后一定都能用
"""
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_INDEX = dict((char, index) for index, char in enumerate(ALPHABET))


def encode(data):  # type: (str) -> str
    """ 字节串 → base64 文字 """
    out = []
    append = out.append
    size = len(data)
    for start in range(0, size - size % 3, 3):
        value = (ord(data[start]) << 16) | (ord(data[start + 1]) << 8) | ord(data[start + 2])
        append(ALPHABET[value >> 18] + ALPHABET[(value >> 12) & 63] + ALPHABET[(value >> 6) & 63] + ALPHABET[value & 63])
    rest = size % 3
    if rest == 1:
        value = ord(data[-1]) << 16
        append(ALPHABET[value >> 18] + ALPHABET[(value >> 12) & 63] + "==")
    elif rest == 2:
        value = (ord(data[-2]) << 16) | (ord(data[-1]) << 8)
        append(ALPHABET[value >> 18] + ALPHABET[(value >> 12) & 63] + ALPHABET[(value >> 6) & 63] + "=")
    return "".join(out)


def decode(text):  # type: (str) -> str or None
    """ base64 文字 → 字节串；中间夹着的空白（聊天软件折的行）跳过，有认不出的字、长度不对给 None """
    chars = [char for char in text if char not in " \t\r\n"]
    while chars and chars[-1] == "=":
        chars.pop()
    if len(chars) % 4 == 1:
        return None
    out = []
    append = out.append
    value, bits = 0, 0
    for char in chars:
        index = _INDEX.get(char)
        if index is None:
            return None
        value = ((value << 6) | index) & 0xFFFFFF
        bits += 6
        if bits >= 8:
            bits -= 8
            append(chr((value >> bits) & 0xFF))
    return "".join(out)
