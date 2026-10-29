# coding=utf-8
# ----------------------------------------------------------------------
#  tag.py is part of MoreEnoughItems.
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

_TYPE_KEY = "__type__"
_VALUE_KEY = "__value__"


class TagParser(object):

    __slots__ = ("_raw",)

    def __init__(self, raw):
        # type: (list or dict) -> None
        self._raw = {} if raw is None else raw

    @classmethod
    def new_leaf(cls, tag_type, value):
        # type: (int, object) -> TagParser
        return cls({_TYPE_KEY: tag_type, _VALUE_KEY: value})

    @classmethod
    def new_compound(cls):
        # type: () -> TagParser
        return cls({})

    @classmethod
    def new_list(cls):
        # type: () -> TagParser
        return cls([])

    @property
    def is_leaf(self):
        # type: () -> bool
        return isinstance(self._raw, dict) and _TYPE_KEY in self._raw

    @property
    def is_compound(self):
        # type: () -> bool
        return isinstance(self._raw, dict) and _TYPE_KEY not in self._raw

    @property
    def is_list(self):
        # type: () -> bool
        return isinstance(self._raw, list)

    @property
    def raw(self):
        # type: () -> object
        return self._raw

    @property
    def type(self):
        # type: () -> int or None
        if self.is_leaf:
            return self._raw[_TYPE_KEY]
        return None

    @property
    def value(self):
        # type: () -> object
        """ 叶子节点的标量值 非叶子返回 None """
        if self.is_leaf:
            return self._raw[_VALUE_KEY]
        return None

    @value.setter
    def value(self, v):
        # type: (object) -> None
        if not self.is_leaf:
            raise TypeError("cannot set .value on a non-leaf node")
        self._raw[_VALUE_KEY] = v

    def set_type(self, tag_type):
        # type: (int) -> TagParser
        """ 修改叶子节点的 Tag 类型 可链式调用 """
        if not self.is_leaf:
            raise TypeError("cannot set type on a non-leaf node")
        self._raw[_TYPE_KEY] = tag_type
        return self

    # -- 导航 ---------------------------------------------------------

    def __getitem__(self, key):
        # type: (object) -> TagParser
        # 复合节点 -> str 键;列表节点 -> int 下标
        return TagParser(self._raw[key])

    def get(self, key, default=None):
        # type: (object, object) -> TagParser or object
        """按键/下标取子节点 不存在时返回 default """
        if self.is_compound:
            if key in self._raw:
                return TagParser(self._raw[key])
            return default
        if self.is_list:
            if isinstance(key, int) and -len(self._raw) <= key < len(self._raw):
                return TagParser(self._raw[key])
            return default
        return default

    def path(self, dotted, default=None):
        # type: (str, object) -> TagParser or object
        """
        按 a/b/0/c 路径深度导航
        会在下钻途中自动创建缺失的复合节点
        (列表下标永不自动创建) 返回目标叶子/分支节点
        """
        if default is None:
            default = {}
        node = self
        parts = [p for p in dotted.replace(".", "/").split("/") if p != ""]
        for part in parts:
            key = int(part) if (node.is_list and _is_int(part)) else part
            child = node.get(key)
            if child is None:
                if node.is_compound:
                    node._raw[key] = default
                    child = TagParser(node._raw[key])
            node = child
        return node

    # -- 复合 / 列表 通用 ---------------------------------------------

    def keys(self):
        # type: () -> list
        """ 复合节点的键列表 """
        if not self.is_compound:
            raise TypeError("keys() is only valid on a compound node")
        return list(self._raw.keys())

    def items(self):
        # type: () -> list
        """ 遍历复合节点 返回 (键, 子节点) 列表。"""
        if not self.is_compound:
            raise TypeError("items() is only valid on a compound node")
        return [(k, TagParser(v)) for k, v in self._raw.items()]

    def __contains__(self, key):
        # type: (object) -> bool
        if self.is_compound:
            return key in self._raw
        if self.is_list:
            return isinstance(key, int) and -len(self._raw) <= key < len(self._raw)
        return False

    def __len__(self):
        # type: () -> int
        if self.is_list or self.is_compound:
            return len(self._raw)
        raise TypeError("len() is only valid on a list or compound node")

    def __iter__(self):
        if self.is_compound:
            return iter(self._raw.keys())
        if self.is_list:
            return iter(TagParser(e) for e in self._raw)
        raise TypeError("cannot iterate a leaf node")

    # -- 修改:复合节点 -----------------------------------------------

    def set(self, key, node):
        # type: (object, object) -> TagParser
        """ 在 key 下挂入一个子节点 (TagParser 或原始对象) """
        if not self.is_compound:
            raise TypeError("set() is only valid on a compound node")
        self._raw[key] = node.raw if isinstance(node, TagParser) else node
        return TagParser(self._raw[key])

    def set_leaf(self, key, tag_type, value):
        # type: (object, int, object) -> TagParser
        """ 创建/替换一个叶子子节点 返回新建的叶子节点 """
        return self.set(key, {_TYPE_KEY: tag_type, _VALUE_KEY: value})

    def setdefault(self, key, node):
        # type: (object, object) -> TagParser
        """ 类似 dict.setdefault 返回已存在或新设置的子节点 """
        if not self.is_compound:
            raise TypeError("setdefault() is only valid on a compound node")
        if key not in self._raw:
            self.set(key, node)
        return TagParser(self._raw[key])

    def __setitem__(self, key, node):
        # type: (object, object) -> None
        raw = node.raw if isinstance(node, TagParser) else node
        self._raw[key] = raw

    def __delitem__(self, key):
        # type: (object) -> None
        del self._raw[key]

    def remove(self, key):
        # type: (object) -> bool
        """ 按键/下标删除子节点(若存在) 删除成功返回 True """
        if key in self:
            del self._raw[key]
            return True
        return False

    def append(self, node):
        # type: (object) -> TagParser
        """ 向列表节点追加一个子节点 返回被追加的节点 """
        if not self.is_list:
            raise TypeError("append() is only valid on a list node")
        raw = node.raw if isinstance(node, TagParser) else node
        self._raw.append(raw)
        return TagParser(raw)

    def append_leaf(self, tag_type, value):
        # type: (int, object) -> TagParser
        return self.append({_TYPE_KEY: tag_type, _VALUE_KEY: value})

    def to_value(self):
        # type: () -> object
        """ 递归脱壳为纯 python 对象(去掉 __type__ 包装) """
        return _unwrap(self._raw)

    def copy(self):
        # type: () -> TagParser
        """ 深拷贝 与原始 userData 脱钩 """
        return TagParser(_deepcopy(self._raw))

    def dumps(self, pretty=False):
        # type: (bool) -> str
        """
        返回保留 __type__/__value__ 包装的字符串 用于调试打印
        pretty=True 多行缩进 (pprint) pretty=False 单行 (repr)
        字节串(如 \\xc2\\xa7 颜色码)以转义形式呈现 不会触发解码错误
        """
        if pretty:
            import pprint
            return pprint.pformat(self._raw)
        return repr(self._raw)

    def __repr__(self):
        if self.is_leaf:
            return "TagParser(leaf type=%r value=%r)" % (self.type, self.value)
        if self.is_list:
            return "TagParser(list len=%d)" % len(self._raw)
        return "TagParser(compound keys=%r)" % (list(self._raw.keys()),)

def _is_int(s):
    # type: (object) -> bool
    try:
        int(s)  # type: ignore
        return True
    except (TypeError, ValueError):
        return False


def _unwrap(raw):
    # type: (object) -> object
    if isinstance(raw, dict):
        if _TYPE_KEY in raw:
            return raw.get(_VALUE_KEY)
        return dict((k, _unwrap(v)) for k, v in raw.items())
    if isinstance(raw, list):
        return [_unwrap(e) for e in raw]
    return raw


def _deepcopy(raw):
    # type: (object) -> object
    if isinstance(raw, dict):
        return dict((k, _deepcopy(v)) for k, v in raw.items())
    if isinstance(raw, list):
        return [_deepcopy(e) for e in raw]
    return raw