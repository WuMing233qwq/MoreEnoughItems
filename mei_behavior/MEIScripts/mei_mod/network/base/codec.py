# coding=utf-8

# ----------------------------------------------------------------------
#  codec.py is part of MoreEnoughItems.
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
载荷规约 —— 跨端载荷的唯一收口。纯函数，零引擎依赖。

引擎事件数据有两条硬限制（CLAUDE.md 引擎结论 §6）：
  · **不支持 tuple**；
  · **不能传 Python 对象**。
两条都没有运行期信号 —— 塞进去不报错，对面收到的是残缺数据。所以出栈前一律过 sanitize。

反方向的坑同样在这里堵：**py2 的 json/事件载荷会给回 unicode，而引擎只吃 str**
（引擎结论 §2 的反向坑）。入栈过 to_native。
"""
from MEIScripts.utils.text import to_native


def sanitize(value):  # type: (any) -> any
    """ 把载荷规约成引擎能收的形状：tuple -> list，其余容器递归 """
    # 不做"顺手转 str": 出栈方向引擎自己会处理编码, 而入栈方向由 to_native 负责,
    # 两个方向各有各的收口, 混在一起会让"到底谁转过了"变得说不清
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return dict((sanitize(k), sanitize(v)) for k, v in value.items())
    return value


def restore(value):  # type: (any) -> any
    """ 入栈规约：把 unicode 还原成 str """
    return to_native(value)


def is_transportable(value):  # type: (any) -> bool
    """
    这个值能不能安全过引擎事件。**只在调试/探针里用**，热路径别调。

    判据就是引擎结论 §6 那两条: 除 dict/list/标量之外一律不行。
    """
    if isinstance(value, tuple):
        return False   # tuple 正是本函数要抓的东西, 别和 list 一起放过
    if isinstance(value, list):
        return all(is_transportable(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(k, (basestring, int, long, float, bool))  # noqa
            and is_transportable(v)
            for k, v in value.items()
        )
    return value is None or isinstance(
        value, (basestring, int, long, float, bool))  # noqa
