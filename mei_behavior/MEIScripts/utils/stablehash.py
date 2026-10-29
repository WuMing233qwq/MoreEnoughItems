# coding=utf-8
# ----------------------------------------------------------------------
#  stablehash.py is part of MoreEnoughItems.
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
跨平台稳定的内容指纹 —— **纯 Python, 零依赖**.

## 为什么不用 hashlib

网易 py2.7 运行时里 `hashlib` **能 import, 但没有 md5 属性**
(`'module' object has no attribute 'md5'`), 显然是被裁剪过. 其余摘要函数是否可用未验证.

## 为什么不做能力探测

「有 md5 用 md5, 没有就退化」看似稳妥, 实则是最坏的选择:
可用集合取决于**引擎版本与平台构建**, 于是同一条配方在 PC 和手机上、
或引擎升级前后, 会算出**不同的 Id** —— 书签、跳转、索引主键全部错位.
⇒ 只允许**一个到处都一样的实现**. 慢一点也认。

## 为什么不用内置 hash()

py2 的 str hash 在 32 位(Android/iOS)与 64 位(Windows)上结果不同, 同样出局.

## 算法

FNV-1a 的 64 位变体, 但**以 4 字节小端字为单位**而非逐字节 ——
纯 Python 下逐字节循环太慢(一条配方的 canonical 约 1000 字节, 每次构造 Recipe 都要算).
字长化后循环次数降到约 1/4. 长度一并混入, 避免尾部补零造成的平凡碰撞.
"""
import json

_OFFSET = 0xCBF29CE484222325
_PRIME = 0x100000001B3
_MASK = 0xFFFFFFFFFFFFFFFF

HEX_LEN = 16
""" 输出十六进制位数. 16 位 = 64 bit —— 10^5 条配方的碰撞概率约 3e-10 """

try:
    import struct

    def _to_words(data):
        return struct.unpack("<%dI" % (len(data) // 4), data)
except ImportError:  # 极端裁剪环境的兜底; **必须与 struct 版本给出完全相同的结果**
    def _to_words(data):
        return [
            ord(data[i]) | (ord(data[i + 1]) << 8)
            | (ord(data[i + 2]) << 16) | (ord(data[i + 3]) << 24)
            for i in range(0, len(data), 4)
        ]


def stable_hash64(text):  # type: (any) -> int
    """ 返回 64 位无符号整数指纹. 输入为 str/unicode, unicode 按 utf-8 编码 """
    if isinstance(text, unicode):  # noqa
        data = text.encode("utf-8")
    else:
        data = text

    length = len(data)
    pad = (-length) % 4
    if pad:
        data += "\0" * pad

    value = _OFFSET
    for word in _to_words(data):
        value = ((value ^ word) * _PRIME) & _MASK
    # 混入原始长度: 否则 "ab" 与 "ab\0\0" 补齐后同形
    value = ((value ^ length) * _PRIME) & _MASK
    return value


def stable_digest(text, hex_len=HEX_LEN):  # type: (any, int) -> str
    """ 返回定长十六进制指纹字符串 """
    return ("%016x" % stable_hash64(text))[:hex_len]


def stable_text(obj):  # type: (any) -> str
    """ 贫血结构的稳定字符串形式，用于排序、落盘与指纹 """
    # ⚠ 这四个参数是**跨存档的身份契约**: Recipe.Id 由它派生, 改任何一个都会让
    # 全部配方换 Id, 从而静默作废所有玩家的置顶与配方书签, 且不会有任何报错。
    # 金标准值钉在 probe_identity.py 的 GOLDEN_IDS, 动这里必然让那条探针变红。
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
