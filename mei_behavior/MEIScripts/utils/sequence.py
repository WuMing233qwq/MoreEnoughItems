# coding=utf-8
# ----------------------------------------------------------------------
#  sequence.py is part of MoreEnoughItems.
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
序列工具，纯函数零依赖。放这里而不是 utilities.py：那个模块顶层拉引擎，
纯函数进去就再也不能被 types / storage / 服务端用了。
"""


def dedupe(items, key=None):  # type: (any, callable or None) -> list
    """ 按 key 去重并保留首次出现的顺序；key 返回 None 表示无法判重，该条一律保留 """
    # key 返回 None 一律保留，是因为"判不出重"和"确定重复"必须分开处理：
    # 把它们并到一起会把一批无法判重的条目静默塌成一条
    seen = set()
    result = []
    for item in items:
        marker = key(item) if key else item
        if marker is None:
            result.append(item)
            continue
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def recipe_id(recipe):  # type: (any) -> str or None
    """ 取 Recipe.Id 作为去重键，拿不到就返回 None（交给 dedupe 保留） """
    return getattr(recipe, "Id", None)
