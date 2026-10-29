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

EXTENSIONS = ("vanilla",)
"""
内置扩展的显式清单，装配器按此顺序加载。

刻意不做目录扫描：扫描会让"删一个文件"变成隐式的行为变更。
本门面**不 import 任何扩展**，装配器要用时才导 —— 否则 import 期就把
registry 与 ui_script 全拉起来了（engineering.md 的「包门面急加载」那条债）。
"""
