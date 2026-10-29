# coding=utf-8
# ----------------------------------------------------------------------
#  hashable.py is part of MoreEnoughItems.
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
import collections

class HashableMaker(object):
    """ 将可变容器递归转换为可哈希形式 用于实现__hash__ """

    @classmethod
    def to_hashable(cls, obj):
        """递归转换入口"""
        def _sort_key(item):
            # 使用类型名 + repr 作为兜底排序键，避免键不可比较时报错
            key = item[0]
            return type(key).__name__, repr(key)

        def _convert(value, stack):
            # 基础不可变类型直接返回
            if isinstance(value, (type(None), bool, int, long, float, str, unicode)):
                return value

            # 防止容器循环引用导致无限递归
            if isinstance(value, (list, tuple, set, dict, collections.deque, collections.OrderedDict)):
                obj_id = id(value)
                if obj_id in stack:
                    raise ValueError('Circular reference detected while converting to hashable')
                stack.add(obj_id)
                try:
                    if isinstance(value, list):
                        return tuple(_convert(item, stack) for item in value)

                    if isinstance(value, tuple):
                        return tuple(_convert(item, stack) for item in value)

                    if isinstance(value, set):
                        return frozenset(_convert(item, stack) for item in value)

                    # OrderedDict 需要在 dict 之前处理，保留插入顺序
                    if isinstance(value, collections.OrderedDict):
                        converted = [(_convert(key, stack), _convert(val, stack)) for key, val in value.items()]
                        return tuple(converted)

                    # 处理字典及其子类（如 defaultdict）
                    if isinstance(value, dict):
                        converted = [(_convert(key, stack), _convert(val, stack)) for key, val in value.items()]
                        converted.sort(key=_sort_key)
                        return tuple(converted)

                    if isinstance(value, collections.deque):
                        return tuple(_convert(item, stack) for item in value)
                finally:
                    stack.remove(obj_id)

            # 其他情况假设对象自身已可哈希
            return value

        return _convert(obj, set())