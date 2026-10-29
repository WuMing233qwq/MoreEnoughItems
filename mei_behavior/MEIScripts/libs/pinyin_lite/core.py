# coding=utf-8

# ----------------------------------------------------------------------
#  core.py is part of MoreEnoughItems.
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

HANZI_FIRST = u"一"
HANZI_LAST = u"鿿"

_TABLE = {}  # 字 → 它的全部读音（主读音在前）；第一次用到才从 table.py 建，免得 import 就付这笔


def _table():  # type: () -> dict
    if not _TABLE:
        from .table import READINGS
        for rank in READINGS:
            for syllable, chars in rank.items():
                reading = unicode(syllable)  # noqa: F821  py2 的 unicode
                for char in chars:
                    _TABLE[char] = _TABLE.get(char, ()) + (reading,)
    return _TABLE


def to_unicode(text):  # type: (any) -> unicode
    """ 库里一律用 unicode：字节串按 utf-8 解（解不了的字换成替代符），别的类型转成字 """
    if isinstance(text, unicode):  # noqa: F821
        return text
    if isinstance(text, basestring):  # noqa: F821
        return text.decode("utf-8", "replace")
    return unicode(text)  # noqa: F821


def is_hanzi(char):  # type: (unicode) -> bool
    """ 是不是基本区的汉字（U+4E00–U+9FFF，字表只收这一段）"""
    return HANZI_FIRST <= char <= HANZI_LAST


def readings(char):  # type: (unicode) -> tuple
    """ 一个字的全部读音（去声调，ü 写 v，主读音在前）；字表里没有的是空元组 """
    return _table().get(to_unicode(char), ())


def segments(text):  # type: (any) -> list
    """
    把一段字切开：有读音的字一个一段，读音是它的全部读音；其余连续的字合成一段，读音是空元组。
    例：u"TNT炸药" → [(u"TNT", ()), (u"炸", (u"zha", ...)), (u"药", (u"yao",))]
    """
    table = _table()
    result, run = [], []
    for char in to_unicode(text):
        found = table.get(char)
        if not found:
            run.append(char)
            continue
        if run:
            result.append((u"".join(run), ()))
            run = []
        result.append((char, found))
    if run:
        result.append((u"".join(run), ()))
    return result


def lazy_pinyin(text):  # type: (any) -> list
    """ 每个字取主读音，其余连续的字原样一段（与 pypinyin 的 lazy_pinyin 缺省一样，只是不按词组定读音）"""
    return [found[0] if found else seg for seg, found in segments(text)]


def first_letters(text):  # type: (any) -> unicode
    """ 每个字取主读音的首字母，其余连续的字原样保留，拼成一串 """
    return u"".join(found[0][0] if found else seg for seg, found in segments(text))
