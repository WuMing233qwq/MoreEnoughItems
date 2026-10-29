# coding=utf-8
# ----------------------------------------------------------------------
#  keys.py is part of MoreEnoughItems.
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
全库统一的物品键与等价关系.

键是索引/书签/配方树/去重的共同地基 —— 没有它, 四条链路都无从建起.

**tuple 红线**: make_key() 返回 tuple, **仅限进程内内存**.
它不得进入 CreateEventData、本地存储载荷、JSON 或 UI 绑定
(engineering.md §7-3: 引擎事件数据不支持 tuple).
一切序列化边界强制过 key_to_str() / key_from_str().

**身份只属于 Stack**: 一组候选(Ingredient)无法作为索引键有意义地存在,
故本模块服务的是 Stack.get_key(), 不上提到 IngredientLike 契约.
"""

AUX_ANY = -1
""" 引擎中表示"任意特殊值"的通配 aux """

KEY_SEP = "#"
""" 键的字符串形式分隔符: "item_id#aux" """

LIST = "list"
""" 列表上下文: 精确. 收藏/黑名单需要区分附魔、耐久等变体 """

RECIPE = "recipe"
""" 配方上下文: 宽松. 对未注册 Comparison 的物品忽略附魔/耐久噪声 """


def make_key(item_id, aux=0):  # type: (str, int) -> tuple
    """
    构造全库统一的哈希键.

    aux 为 AUX_ANY(-1) 时视为通配, 规约为 0 入索引 —— 否则同一物品的
    "任意特殊值"与"特殊值 0"会占据两个桶, 查询必漏.
    """
    if not item_id:
        raise ValueError("item_id cannot be empty")
    if aux is None or aux == AUX_ANY:
        aux = 0
    return item_id, int(aux)


def key_to_str(key):  # type: (tuple) -> str
    """ 键 -> "item_id#aux" (序列化边界唯一出口) """
    if not isinstance(key, tuple) or len(key) != 2:
        raise ValueError("key must be a 2-tuple from make_key()")
    return "{}{}{}".format(key[0], KEY_SEP, key[1])


def key_from_str(text):  # type: (str) -> tuple
    """ "item_id#aux" -> 键. 无分隔符时 aux 取 0 """
    if not isinstance(text, basestring):
        raise ValueError("key text must be string")
    if KEY_SEP not in text:
        return make_key(text, 0)
    item_id, _, aux_text = text.rpartition(KEY_SEP)
    try:
        aux = int(aux_text)
    except ValueError:
        raise ValueError("bad key text: {}".format(text))
    return make_key(item_id, aux)


class Comparison(object):
    """
    可插拔的等价关系.

    谓词与哈希**必须成对给出**: 索引是 dict, 谓词说"相等"而哈希说"不等",
    条目就永远查不到. 这不是洁癖, 是索引能不能用的前提.

    默认策略(EMI 的宽松默认): 只比键, 同物品的不同附魔/耐久视为同种.
    药水、附魔书这类需要按 UserData 细分的物品, 由上层按 item_id 注册收紧.

    注: **本模块只提供类本身, 不提供 item_id -> Comparison 的注册表** ——
    注册表是状态, 归属 registry 层; 而 common 不得 import registry
    (engineering.md §2). Comparison 的**应用**发生在索引层.
    """

    __slots__ = ("Predicate", "HashFn")

    def __init__(self, predicate, hash_fn):
        if not callable(predicate) or not callable(hash_fn):
            raise TypeError("predicate and hash_fn must both be callable")
        self.Predicate = predicate
        self.HashFn = hash_fn

    def equals(self, a, b):  # type: (any, any) -> bool
        return bool(self.Predicate(a, b))

    def hash_of(self, stack):  # type: (any) -> any
        return self.HashFn(stack)


DEFAULT = Comparison(lambda a, b: True, lambda s: 0)
""" 默认等价关系: 只比键, 不看 UserData (同 item_id+aux 即同种) """
