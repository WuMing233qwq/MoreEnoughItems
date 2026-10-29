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
# 轻量拼音库：纯 Python、零引擎依赖、不 import MEIScripts 的其他包。字表取自 pypinyin（MIT，见 LICENSE.txt）
from .core import first_letters, is_hanzi, lazy_pinyin, readings, segments, to_unicode
from .search import PinyinIndex

__all__ = [
    "PinyinIndex",
    "first_letters",
    "is_hanzi",
    "lazy_pinyin",
    "readings",
    "segments",
    "to_unicode",
]
