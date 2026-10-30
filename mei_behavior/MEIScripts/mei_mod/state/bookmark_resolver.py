# coding=utf-8

# ----------------------------------------------------------------------
#  bookmark_resolver.py is part of MoreEnoughItems.
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
书签条目找回成活的 Item / Recipe：惰性、带缓存、出错只返回 None。
悬停、点击、转移、配方树共用这一个入口，见 docs/architecture/bookmarks.md §3.3。
"""
from MEIScripts.common.classes.types import keys
from MEIScripts.common.classes.types.item import ItemAttr
from MEIScripts.constants.codes import QueryConst
from MEIScripts.utils.log import logger
from MEIScripts.utils.sequence import recipe_id
from MEIScripts.utils.text import error_text, native_str

from .bookmarks import IDENTITY_ATTRS, KIND_RECIPE, item_data, item_key


class _Miss(object):
    """
    缓存里「找过、找不到」的标记，区别于「还没找过」
    """
    def __repr__(self):
        return "<miss>"


_MISS = _Miss()


class RegistryBackend(object):
    """
    默认后端：现查 registry；全部惰性 import，registry 包门面顶层就拉引擎
    """
    @staticmethod
    def version():  # type: () -> tuple
        """ 物品表的版本 + 类型 / 来源表的版本：任何一个变了，记下的物品与配方（包括「找不回」）都作废 """
        from MEIScripts.registry import ItemManager
        from MEIScripts.registry.sources import SourceRegistry
        return ItemManager.Version(), SourceRegistry.Revision()

    @staticmethod
    def items_by_id(item_id):  # type: (str) -> list
        from MEIScripts.registry import ItemManager
        return ItemManager.GetItemsById(item_id)

    @staticmethod
    def has_item_id(item_id):  # type: (str) -> bool
        from MEIScripts.registry import ItemManager
        return ItemManager.LookUpItem(item_id)

    @staticmethod
    def make_item(item_id, aux, attr):  # type: (str, int, any) -> any
        from MEIScripts.registry import ItemFactory
        return ItemFactory.GetItem(ItemId=item_id, AuxValue=aux, Attr=attr)

    @staticmethod
    def has_category(category_id):  # type: (str) -> bool
        from MEIScripts.registry import SourceRegistry
        return SourceRegistry.GetCategory(category_id) is not None

    @staticmethod
    def query(item, role, category_id):  # type: (any, str, str) -> list
        from MEIScripts.registry import RecipeManager
        return RecipeManager.QueryRecipe(item, role, [category_id]).get(category_id, [])


def _attr_from(fields):  # type: (any) -> ItemAttr or None
    """ 存下的变体字段还原成 ItemAttr，用来现造显示用的物品 """
    if not isinstance(fields, dict) or not fields:
        return None
    kwargs = {}
    for name, arg in IDENTITY_ATTRS:
        if name in fields:
            kwargs[arg] = fields[name]
    return ItemAttr(**kwargs)


class __BookmarkResolver(object):  # noqa
    """
    条目 → 活对象，带缓存；构造期不碰引擎
    """
    def __init__(self):
        self._backend = None
        self._version = None
        self._items = {}  # type: dict
        """ 物品身份键 -> Item 或 _MISS """
        self._recipes = {}  # type: dict
        """ 配方 Id -> Recipe 或 _MISS """

    def SetBackend(self, backend):
        """ 测试注入点；传 None 恢复默认后端。换后端即清缓存 """
        self._backend = backend
        self.Reset()

    def Reset(self):
        self._version = None
        self._items = {}
        self._recipes = {}

    def _get_backend(self):
        if self._backend is None:
            self._backend = RegistryBackend()
        return self._backend

    def _sync(self, backend):
        """
        物品表换了版本（重新同步、扩展重装）、类型 / 来源变了（第三方晚到的注册）就清缓存 ——
        不然先前记下的「找不回」一直找不回：收藏栏的格子停在失效的样子
        """
        try:
            version = backend.version()
        except Exception:  # noqa  取不到版本就当没变，宁可旧一点也不能卡
            return
        if version != self._version:
            self._items = {}
            self._recipes = {}
            self._version = version

    # 物品
# ======================================================================================================================
    def ResolveItem(self, data):  # type: (any) -> any
        """ 物品数据找回成 Item：先认物品表里的变体，id 还在就现造一个显示用的，id 都没了返回 None """
        key = item_key(data)
        if not key:
            return None
        backend = self._get_backend()
        self._sync(backend)
        hit = self._items.get(key)
        if hit is None:
            hit = self._find_item(backend, data, key)
            self._items[key] = _MISS if hit is None else hit
        return None if hit is _MISS else hit

    @staticmethod
    def _find_item(backend, data, key):  # type: (any, dict, str) -> any
        item_id = native_str(data.get("id"))
        try:
            for item in backend.items_by_id(item_id) or ():
                if item_key(item_data(item)) == key:
                    return item
            if not backend.has_item_id(item_id):
                return None
            _id, aux = keys.make_key(item_id, data.get("aux", 0))
            return backend.make_item(item_id, aux, _attr_from(data.get("attr")))
        except Exception as e:  # noqa
            logger.warn("[MEI/bookmarks] 物品 {} 找不回: {}".format(key, error_text(e)))
            return None

    # 配方
# ======================================================================================================================
    def ResolveRecipe(self, entry):  # type: (any) -> any
        """ 配方条目找回成 Recipe：拿 item 按 role 在 cat 里重查一次再按 Id 认，找不回返回 None """
        if not isinstance(entry, dict) or entry.get("k") != KIND_RECIPE:
            return None
        rid = native_str(entry.get("id"))
        if not rid or not isinstance(rid, basestring):
            return None
        backend = self._get_backend()
        self._sync(backend)
        hit = self._recipes.get(rid)
        if hit is None:
            hit = self._find_recipe(backend, entry, rid)
            self._recipes[rid] = _MISS if hit is None else hit
        return None if hit is _MISS else hit

    def _find_recipe(self, backend, entry, rid):  # type: (any, dict, str) -> any
        category_id = native_str(entry.get("cat"))
        data = entry.get("item")
        if not category_id or not isinstance(category_id, basestring) or not isinstance(data, dict):
            return None
        role = entry.get("role")
        if role not in (QueryConst.Output, QueryConst.Input):
            role = QueryConst.Output
        try:
            if not backend.has_category(category_id):
                return None
            probe = self.ResolveItem(data)
            if probe is None:
                return None
            for recipe in backend.query(probe, role, category_id) or ():
                if native_str(recipe_id(recipe)) == rid:
                    return recipe
        except Exception as e:  # noqa
            logger.warn("[MEI/bookmarks] 配方 {} 找不回: {}".format(rid, error_text(e)))
        return None


BookmarkResolver = __BookmarkResolver()
