# coding=utf-8

# ----------------------------------------------------------------------
#  rules.py is part of MoreEnoughItems.
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
自适应的生效条件（docs/architecture/settings.md §6.3）：登记的避让目标看得见、还要它的条件说「算」，才拿去避让。

有的控件藏起来以后位置会变、却还看得见（原版配方书藏了，它上面的页签与网易的左右翻页箭头挪到别处），光看 GetVisible 判断不了，
这时由代码说了算：条件是一个函数 condition(get) -> bool，get(路径) 按界面的 RootPath 取同一个界面里的控件（取不到给 None）。
条件在代理参数的 Conditions 里按路径给（ctx.UI.Screens.Register，原版的在 extensions/vanilla/screens.py），
主节点代码登记的避让目标也可以直接带一个（UIScriptMain.RegisterAdaptiveControl）。纯计算，不碰引擎
"""


def holds(condition, get, memo=None):  # type: (callable or None, callable, dict or None) -> bool
    """
    这个条件此刻成不成立：没给条件就是成立；条件抛异常当「不成立」（这一块不避让）。
    memo 是这一轮几何刷新的缓存，按条件函数记 —— 几条路径共用一个条件时一轮只问一次引擎
    """
    if condition is None:
        return True
    key = id(condition)
    if memo is not None and key in memo:
        return memo[key]
    try:
        result = bool(condition(get))
    except Exception:  # noqa  条件是登记方的代码，抛了只当这一块这一轮不避让
        result = False
    if memo is not None:
        memo[key] = result
    return result
