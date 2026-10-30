# coding=utf-8

# ----------------------------------------------------------------------
#  tags.py is part of MoreEnoughItems.
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
按 tag 查物品、方块。MEI 自己不记 tag：3.10 起问引擎的 LookupItemsByItemTag / LookupBlocksByBlockTag ——
netease_tags 里注册的 tag（# 引用的自动展开，几个模组注册了同一个 tag 自动合并去重），没注册的原版 tag 也能直接查。

引擎没有这个接口（3.10 之前）时，物品退回到物品表里按缓存的物品信息找（Info.Tags，就是 GetItemTags 给的，CLAUDE.md 引擎结论 §44）；
方块给空。结果按 tag 缓存，物品表换了版本（进世界、扩展重装）就清。构造期不碰引擎
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

ITEM, BLOCK = "item", "block"

ENGINE_METHODS = {
    ITEM: (("CreateItem", "LookupItemsByItemTag"),),
    BLOCK: (("CreateBlockInfo", "LookupBlocksByBlockTag"), ("CreateBlock", "LookupBlocksByBlockTag")),
}
"""
引擎的接口挂在哪个组件上（依次找，找到第一个能调的为准）：物品在物品组件上（和 GetItemTags 一处），方块在方块信息组件上。
挂在别处的话这里加一行；找不到就当这个版本没有
"""

NAME_KEYS = ("itemName", "name", "identifier", "blockName", "newItemName")
""" 结果里的一项是字典时，名字在哪个键上 """


def entry_name(entry):  # type: (any) -> str or None
    """
    结果里的一项 -> 物品 / 方块的 identifier（str）：名字本身，或带名字的字典；"命名空间:名字:附加值" 去掉附加值（tag 认的是 id）。
    看不懂给 None
    """
    if isinstance(entry, dict):
        entry = next((entry.get(key) for key in NAME_KEYS if entry.get(key)), None)
    if not isinstance(entry, basestring) or not entry:
        return None
    name = native_str(entry)
    parts = name.split(":")
    if len(parts) >= 3 and parts[-1].isdigit():
        name = ":".join(parts[:-1])
    return name


def names_of(result):  # type: (any) -> frozenset or None
    """
    引擎给的结果 -> 名字的集合：列表 / 元组 / 集合逐项认（entry_name）；字典认它的键（{名字: 别的}）；None 是空的。
    别的写法认不出给 None（调用方退回物品信息里的 tags）
    """
    if result is None:
        return frozenset()
    if isinstance(result, dict):
        result = list(result.keys())
    if not isinstance(result, (list, tuple, set, frozenset)):
        return None
    return frozenset(name for name in (entry_name(entry) for entry in result) if name)


class __TagLookup(object):  # noqa
    """ 按 tag 查物品、方块；每个 tag 第一次问才问引擎，构造期不碰引擎 """

    def __init__(self):
        self._version = None  # type: any  # 缓存是按物品表的哪个版本攒的
        self._cache = {}  # type: dict  # (ITEM 或 BLOCK, tag) -> frozenset
        self._methods = {}  # type: dict  # ITEM 或 BLOCK -> 引擎的方法；False 是这个版本没有
        self._said = set()  # type: set  # 记过的日志（每种只记一行）

    def ItemIds(self, tag):  # type: (str) -> frozenset
        """ 带这个物品 tag 的物品 id（str）；tag 不认识、没有成员给空集合 """
        return self.__Lookup(ITEM, tag)

    def BlockNames(self, tag):  # type: (str) -> frozenset
        """ 带这个方块 tag 的方块名（str）；引擎没有这个接口（3.10 之前）给空集合 """
        return self.__Lookup(BLOCK, tag)

    def EngineHas(self, kind=ITEM):  # type: (str) -> bool
        """ 引擎有没有按 tag 查的接口（3.10 起有）；kind 是 ITEM / BLOCK """
        self.__Sync()
        return self.__Method(kind) is not None

    def Reset(self):
        """ 丢掉缓存（测试、热重载用；进世界时按物品表的版本自己会清）"""
        self._version = None
        self._cache = {}
        self._methods = {}

    def __Lookup(self, kind, tag):  # type: (str, any) -> frozenset
        tag = native_str(tag)
        if not tag or not isinstance(tag, basestring):
            return frozenset()
        self.__Sync()
        key = (kind, tag)
        if key not in self._cache:
            self._cache[key] = self.__Query(kind, tag)
        return self._cache[key]

    def __Sync(self):
        """ 物品表换了版本（进世界、扩展重装）：缓存、找到的引擎方法都作废（方法绑在组件上，组件绑在世界上）"""
        from .items import ItemManager  # 惰性：items 要 import 本模块
        version = ItemManager.Version()
        if version != self._version:
            self._version = version
            self._cache = {}
            self._methods = {}

    def __Query(self, kind, tag):  # type: (str, str) -> frozenset
        method = self.__Method(kind)
        if method is not None:
            try:
                names = names_of(method(tag))
                if names is not None:
                    return names
                self.__Say("error:shape:" + kind, "[MEI/tags] 按 tag 查{}，引擎给的结果认不出（{}），{}".format(
                    "物品" if kind == ITEM else "方块", tag, "退回物品信息里的 tags" if kind == ITEM else "给空"))
            except Exception as e:  # noqa  引擎这一下出错：物品退回物品信息里的 tags，这个 tag 不至于什么都查不到
                self.__Say("error:" + kind, "[MEI/tags] 按 tag 查{}出错（{}），{}: {}".format(
                    "物品" if kind == ITEM else "方块", tag, "退回物品信息里的 tags" if kind == ITEM else "给空", error_text(e)))
        elif kind == ITEM:
            self.__Say("fallback", "[MEI/tags] 引擎没有 LookupItemsByItemTag（3.10 起才有），按 tag 查物品退回物品信息里的 tags")
        return self.__Fallback(kind, tag)

    def __Method(self, kind):  # type: (str) -> any
        if kind not in self._methods:
            self._methods[kind] = self.__Find(kind) or False
        return self._methods[kind] or None

    @staticmethod
    def __Find(kind):  # type: (str) -> any
        """ 在 ENGINE_METHODS 列的组件上找接口（能力探测，CLAUDE.md 引擎结论 §12）；拿不到给 None """
        try:
            import mod.client.extraClientApi as clientApi
            factory = clientApi.GetEngineCompFactory()
            level_id = clientApi.GetLevelId()
        except Exception:  # noqa  引擎还没就绪
            return None
        for comp_name, method_name in ENGINE_METHODS.get(kind, ()):
            create = getattr(factory, comp_name, None)
            if not callable(create):
                continue
            try:
                comp = create(level_id)
            except Exception:  # noqa
                continue
            method = getattr(comp, method_name, None)
            if callable(method):
                return method
        return None

    @staticmethod
    def __Fallback(kind, tag):  # type: (str, str) -> frozenset
        """ 引擎查不了：物品按物品表里缓存的物品信息找（Info.Tags 与 GetItemTags 一模一样，引擎结论 §44）；方块给空 """
        if kind != ITEM:
            return frozenset()
        from .items import ItemManager
        found = set()
        for item in ItemManager.GetItems():
            try:
                if tag in (item.Info.Tags or ()):
                    found.add(item.ItemId)
            except Exception:  # noqa  惰性字段取不到：当它不带
                continue
        return frozenset(found)

    def __Say(self, key, text):  # type: (str, str) -> None
        if key in self._said:
            return
        self._said.add(key)
        (logger.warn if key.startswith("error") else logger.info)(text)


TagLookup = __TagLookup()
