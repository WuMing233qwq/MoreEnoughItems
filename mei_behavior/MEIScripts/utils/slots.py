# coding=utf-8

# ----------------------------------------------------------------------
#  slots.py is part of MoreEnoughItems.
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
按 __slots__ 复制对象（纯函数，零引擎依赖）。structure.md §5.2 待办 B：原先 Item / ItemInfo / ItemAttr / ItemSpec 各手写一份逐字段的 copy()，
每加一个字段都要手工同步，漏了就静默丢字段；Item 的还写死了构造 Item，子类一 copy 就降级成基类。

copy_slots 不走构造：新对象和原对象**同一个类**，每个槽位默认**原样共享**（不可变的值、要共享的加载器）——
deep 里的 copy.deepcopy、shallow 里的 copy.copy、copied 里的调它自己的 copy()（None 照旧 None）。
新加的槽位自动带上、默认共享：要深拷、浅拷的新字段记得写进调用方的名单。
"""
import copy


def slot_names(cls):  # type: (type) -> list
    """ 这个类连同父类声明的全部槽位（基类的在前）；__dict__ / __weakref__ 不算，双下划线的按名字改编后的写 """
    names = []
    for klass in reversed(cls.__mro__):
        slots = klass.__dict__.get("__slots__", ())
        if isinstance(slots, basestring):
            slots = (slots,)
        for name in slots:
            if name in ("__dict__", "__weakref__"):
                continue
            if name.startswith("__") and not name.endswith("__"):
                name = "_{}{}".format(klass.__name__.lstrip("_"), name)
            if name not in names:
                names.append(name)
    return names


def copy_slots(obj, deep=(), shallow=(), copied=()):  # type: (any, tuple, tuple, tuple) -> any
    """ 复制一份：同一个类、每个槽位按名单处理（见模块说明）；没赋过值的槽位照样空着；子类要是有 __dict__ 也浅拷过去 """
    cls = type(obj)
    made = cls.__new__(cls)
    for name in slot_names(cls):
        try:
            value = getattr(obj, name)
        except AttributeError:
            continue
        if name in deep:
            value = copy.deepcopy(value)
        elif name in shallow:
            value = copy.copy(value)
        elif name in copied and value is not None:
            value = value.copy()
        setattr(made, name, value)
    extra = getattr(obj, "__dict__", None)
    if extra:
        made.__dict__.update(extra)
    return made
