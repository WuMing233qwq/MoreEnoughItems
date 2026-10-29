# coding=utf-8

# ----------------------------------------------------------------------
#  bindname.py is part of MoreEnoughItems.
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
集合绑定名（纯函数）。structure.md §5.2 待办 C：原先 ItemsGrid、配方页的绑定器、配方行的动作按钮各拼各的。
"""


def make_binding_name(prefix, suffix):  # type: (str, str) -> str
    """
    '#' + 前缀 + 后缀（后缀以「.」开头，如 .item.visible）。**必须与 JSON 侧逐字一致**：JSON 写的是
    ('#' + $binding_name_prefix + '.item.visible')；拼歪了就是「注册成功、零报错、引擎永不投递」（CLAUDE.md 引擎结论 §9）
    """
    return "#" + prefix + suffix
