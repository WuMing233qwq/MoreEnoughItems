# coding=utf-8

# ----------------------------------------------------------------------
#  state.py is part of MoreEnoughItems.
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
筛选与排序菜单的纯计算：点了哪个按钮之后选的是什么。不碰引擎。

选了的筛选是 Id 表（几项都要满足），排序是 (排序 Id, ASC / DESC) 或 None（不排序），和 prefs 里存的一个样子（PrefsManager）
"""
from MEIScripts.registry.filters import ASC, DESC


def toggle_filter(selected, filter_id):  # type: (list, str) -> list
    """ 按一下标签块：没选的选上（排在最后），选了的去掉 """
    selected = list(selected or ())
    if filter_id in selected:
        return [one for one in selected if one != filter_id]
    return selected + [filter_id]


def step_sort(sort_ids, current, delta):  # type: (list, tuple or None, int) -> tuple or None
    """
    步进器的 ‹ ›：在「不排序 + 登记的排序」里往前 / 往后走一格，转圈。方向沿用现在的，不排序时从升序开始。
    sort_ids 是登记的排序 Id（按菜单的先后）；现在的排序不在里面（扩展撤了）当成不排序
    """
    order = [None] + list(sort_ids or ())
    now = current[0] if current else None
    index = order.index(now) if now in order else 0
    chosen = order[(index + delta) % len(order)]
    if chosen is None:
        return None
    direction = current[1] if current and current[1] in (ASC, DESC) else ASC
    return chosen, direction


def flip_direction(current):  # type: (tuple or None) -> tuple or None
    """ 升 / 降切换；不排序时什么都不变 """
    if not current:
        return None
    return current[0], DESC if current[1] == ASC else ASC


def active(selected, sort, filter_ids, sort_ids):  # type: (list, tuple or None, list, list) -> bool
    """ 筛选按钮要不要显示成「开着」：选了登记着的筛选，或者按登记着的排序在排（撤掉的那些不算）"""
    known = set(filter_ids or ())
    return any(one in known for one in selected or ()) or bool(sort and sort[0] in set(sort_ids or ()))
