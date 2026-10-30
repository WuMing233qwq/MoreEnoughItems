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
"""
物品栏的筛选与排序菜单（docs/architecture/modes.md §8）。筛选、排序本身在 registry/filters.py（对外 ctx.Registry.ItemFilters）。

- state.py  纯计算（按下标签块、换排序、切升降）
- layout.py 纯计算（标签块换行、要不要滚、每样摆在哪）
- menu.py   菜单本身（一个界面一份，主节点 main.Filters）

门面不导出：menu 要引擎，别让只想用纯计算的人跟着拉进来
"""
