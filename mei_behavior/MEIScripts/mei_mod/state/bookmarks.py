# coding=utf-8

# ----------------------------------------------------------------------
#  bookmarks.py is part of MoreEnoughItems.
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
书签（收藏）的存储：多个页签，每个页签一张条目表加一张分组表，全局或按存档保存。
格式见 docs/architecture/bookmarks.md §6。
"""
from MEIScripts.common.classes.types import keys
from MEIScripts.common.classes.types.recipe import ID_NAMESPACE
from MEIScripts.constants.codes import QueryConst, StorageConst
from MEIScripts.utils.log import logger
from MEIScripts.utils.sequence import recipe_id
from MEIScripts.utils.stablehash import stable_digest, stable_text
from MEIScripts.utils.text import error_text, native_str

from .storage import Store

CONFIG_NAME = StorageConst.BookmarksConfigName

VERSION = 4
""" v1 转 v2 翻转顺序，v2 转 v3 并成一张条目表，v3 转 v4 装进页签，见 MIGRATIONS """

KEY_TABS = "tabs"
""" 页签表，list[{"entries": [...], "groups": {...}}]，内存里至少一页 """

KEY_TAB = "tab"
""" 当前页签的下标；等于页签数时表示停在末尾那个还没建出来的「新页签」上 """

KEY_ENTRIES = "entries"
""" 页签里的条目表，list[dict]，就是显示顺序 """

KEY_GROUPS = "groups"
""" 页签里的分组表 {"<分组 id>": {属性}}；"0" 是不分组的那部分，只认视图一项 """

KIND_ITEM = "item"
KIND_RECIPE = "recipe"
KIND_TREE = "tree"
""" 配方树收藏：一整棵存成一条，按根认（SaveTree） """

KINDS = (KIND_ITEM, KIND_RECIPE, KIND_TREE)
""" 当前真正在用的类别 """

FIELD_COUNT = "n"
""" 条目的数量：物品是件数，配方是倍数；缺省 1，只存大于 1 的 """

FIELD_GROUP = "g"
""" 条目所在分组的 id，正整数；缺省表示不分组 """

FIELD_EXPAND = "x"
"""
配方收藏展不展开成「产物 + 原料」：true / false 是玩家按过 C 定下的，缺省跟着所在分组的视图走（竖排清单展开、横排收起）。
只对配方条目有意义；新增的可选字段，旧版本读到原样留着，不升存储版本
"""

UNGROUPED = 0

GROUP_VIEW = "view"
GROUP_FOLD = "fold"
GROUP_CHAIN = "chain"
""" 分组的三个属性：视图（缺省横排）、折叠、合成链（只存不读）"""

VIEW_GRID = "grid"
VIEW_LIST = "list"

MAX_TABS = 8
""" 页签上限；到顶后末尾不再有「新页签」"""

MAX_TAB_ENTRIES = 256
""" 每个页签的条目上限，满了拒绝新增而不淘汰旧的 —— 条目是玩家自己排的；SetConfigData 容量未文档化，取保守值 """

MAX_COUNT = 99999

IDENTITY_ATTRS = (
    ("UserData", "user_data"),
    ("EnchantData", "enchant_data"),
    ("ModEnchantData", "mod_enchant_data"),
    ("ExtraId", "extra_id"),
    ("Durability", "durability"),
)
""" 区分变体的 ItemAttr 字段：(存盘名, ItemAttr 构造参数名)。ShowInHand / CustomTips 只管显示，不收 """

_V2_RECIPES = "recipes"
_V2_ITEMS = "items"
""" v1 / v2 的两张字符串表，只有迁移步还认它们 """


# 条目的构造与身份 —— 纯函数，离线可测
# ======================================================================================================================
def _plain(value):  # type: (any) -> any
    """ 落盘形态：unicode 转 str、tuple 转 list，让会话内与重开后长得一样 """
    if isinstance(value, dict):
        return dict((_plain(k), _plain(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return native_str(value)


def attr_fields(attr):  # type: (any) -> dict
    """ ItemAttr 里区分变体、且不是缺省值的字段 """
    fields = {}
    if attr is None:
        return fields
    for name, _arg in IDENTITY_ATTRS:
        value = getattr(attr, name, None)
        if value:  # None / {} / [] / "" / 0 都是缺省
            fields[name] = _plain(value)
    return fields


def _attr_digest(fields):  # type: (dict) -> str
    """ 变体指纹；算不出来（含不可序列化的值）返回空串，物品退化为只认 id#aux """
    if not fields:
        return ""
    try:
        return stable_digest(stable_text(_plain(fields)))
    except Exception as e:  # noqa  数据可以丢，加载不能卡
        logger.warn("[MEI/bookmarks] 物品属性算不出指纹, 只按 id#aux 收藏: {}".format(error_text(e)))
        return ""


def item_data(item, amount=1):  # type: (any, int) -> dict or None
    """ 物品条目的数据部分 {"id", "aux"[, "attr"][, "n"]}；拿不到 ItemId 的返回 None """
    item_id = native_str(getattr(item, "ItemId", None))
    if not item_id or not isinstance(item_id, basestring):
        return None
    try:
        _id, aux = keys.make_key(item_id, getattr(item, "AuxValue", 0))
    except (TypeError, ValueError, OverflowError):
        return None
    data = {"id": item_id, "aux": aux}
    fields = attr_fields(getattr(item, "Attr", None))
    if fields and _attr_digest(fields):
        data["attr"] = fields
    if isinstance(amount, (int, long)) and not isinstance(amount, bool) and amount > 1:
        data["n"] = amount
    return data


def item_key(data):  # type: (any) -> str
    """ 物品的身份键 "id#aux"，带 attr 时再接 "#指纹"；不成形返回空串 """
    if not isinstance(data, dict):
        return ""
    item_id = native_str(data.get("id"))
    if not item_id or not isinstance(item_id, basestring):
        return ""
    try:
        key = keys.key_to_str(keys.make_key(item_id, data.get("aux", 0)))
    except (TypeError, ValueError, OverflowError):  # 盘上 aux 写着 1e999：读成无穷大，int 抛 OverflowError
        return ""
    attr = data.get("attr")
    if isinstance(attr, dict) and attr:
        digest = _attr_digest(attr)
        if digest:
            key += keys.KEY_SEP + digest
    return key


def item_entry(item):  # type: (any) -> dict or None
    """ 物品条目 {"k": "item", "id", "aux"[, "attr"]} """
    data = item_data(item)
    if data is None:
        return None
    entry = {"k": KIND_ITEM}
    entry.update(data)
    return entry


def _stacks_of(ingredient):  # type: (any) -> list
    getter = getattr(ingredient, "get_stacks", None)
    stacks = getter() if callable(getter) else getattr(ingredient, "Stacks", None)
    return list(stacks) if stacks else []


def _amount_of(ingredient):  # type: (any) -> int
    getter = getattr(ingredient, "get_amount", None)
    return getter() if callable(getter) else 1


def _pick_probe(recipe):  # type: (any) -> tuple or None
    """ (方向, 物品数据)：第一个产物，没有产物才取第一个原料，既画在格子上也拿去重查 """
    for role, groups in ((QueryConst.Output, getattr(recipe, "Outputs", None)),
                         (QueryConst.Input, getattr(recipe, "Inputs", None))):
        for ingredient in groups or ():
            amount = _amount_of(ingredient) if role == QueryConst.Output else 1
            for stack in _stacks_of(ingredient):
                data = item_data(getattr(stack, "Item", None), amount)
                if data is not None:
                    return role, data
    return None


def recipe_entry(recipe):  # type: (any) -> dict or None
    """ 配方条目 {"k", "id", "cat"[, "role", "item"]}，拿不到 Id 的返回 None """
    rid = native_str(recipe_id(recipe))
    if not rid or not isinstance(rid, basestring):
        return None
    entry = {"k": KIND_RECIPE, "id": rid}
    category_id = native_str(getattr(recipe, "Type", None))
    if category_id and isinstance(category_id, basestring):
        entry["cat"] = category_id
    try:
        probe = _pick_probe(recipe)
    except Exception as e:  # noqa  探针取不到不影响收藏本身
        logger.warn("[MEI/bookmarks] 配方 {} 取不到显示物品: {}".format(rid, error_text(e)))
        probe = None
    if probe is not None:
        entry["role"], entry["item"] = probe
    return entry


def _identity(kind, key):  # type: (str, str) -> str
    return kind + "|" + native_str(key)


def entry_identity(entry):  # type: (any) -> str or None
    """ 条目的身份键，只在内存里用；看不懂的条目返回 None —— 它们不进索引，但原样留在表里 """
    if not isinstance(entry, dict):
        return None
    kind = entry.get("k")
    if kind == KIND_ITEM:
        key = item_key(entry)
    elif kind == KIND_RECIPE:
        key = native_str(entry.get("id"))
        if not isinstance(key, basestring):
            key = ""
    elif kind == KIND_TREE:
        # 配方树按根认：同一个根只收一条，再存就是更新它
        key = item_key(entry.get("root"))
    else:
        return None
    return _identity(kind, key) if key else None


def _safe_identity(entry):  # type: (any) -> str or None
    try:
        return entry_identity(entry)
    except Exception:  # noqa  一条坏数据不能拖累整张表
        return None


def _positive_int(value, default):  # type: (any, int) -> int
    if isinstance(value, bool) or not isinstance(value, (int, long)) or value < 1:
        return default
    return value


def entry_count(entry):  # type: (any) -> int
    """ 条目的数量，缺省或不成形按 1 """
    value = entry.get(FIELD_COUNT, 1) if isinstance(entry, dict) else 1
    return min(_positive_int(value, 1), MAX_COUNT)


def tree_count(entry):  # type: (any) -> int
    """ 配方树收藏要做几个根（条目里的 count；收藏格的数量 n 不用在树上），缺省或不成形按 1 """
    value = entry.get("count", 1) if isinstance(entry, dict) else 1
    return min(_positive_int(value, 1), MAX_COUNT)


def entry_group(entry):  # type: (any) -> int
    """ 条目所在的分组 id，不分组或不成形返回 0 """
    value = entry.get(FIELD_GROUP, UNGROUPED) if isinstance(entry, dict) else UNGROUPED
    return _positive_int(value, UNGROUPED)


def entry_expanded(entry, listed):  # type: (any, bool) -> bool
    """ 配方收藏此刻展不展开：玩家定过就按定的，没定过跟视图走（listed = 所在分组是竖排清单）"""
    value = entry.get(FIELD_EXPAND) if isinstance(entry, dict) else None
    return value if isinstance(value, bool) else bool(listed)


def replace_fields(entry, changes):  # type: (dict, dict) -> dict
    """ 换掉几个字段得到新条目，不改原条目；数量 1、分组 0 这类缺省值直接去掉 """
    new = dict(entry)
    for name, value in changes.items():
        if (name == FIELD_COUNT and value == 1) or (name == FIELD_GROUP and value == UNGROUPED):
            new.pop(name, None)
        else:
            new[name] = value
    return new


# 页签与分组 —— 纯函数
# ======================================================================================================================
def _empty_tab():  # type: () -> dict
    return {KEY_ENTRIES: [], KEY_GROUPS: {}}


def _normalize_tab(raw):  # type: (any) -> dict
    """ 页签读进内存的样子；不成形的部分降级为空，多出来的键原样留着 """
    if not isinstance(raw, dict):
        logger.warn("[MEI/bookmarks] 页签不是 dict({}), 按空页签处理".format(type(raw).__name__))
        return _empty_tab()
    entries = raw.get(KEY_ENTRIES)
    if not isinstance(entries, list):
        if entries is not None:
            logger.warn("[MEI/bookmarks] 条目表不是列表({}), 按空处理".format(type(entries).__name__))
        entries = []
    groups = raw.get(KEY_GROUPS)
    if not isinstance(groups, dict):
        groups = {}
    tab = dict(raw)
    tab[KEY_ENTRIES] = list(entries)
    tab[KEY_GROUPS] = dict((native_str(k), v) for k, v in groups.items() if isinstance(v, dict))
    return tab


def _parse_gid(key):  # type: (any) -> int or None
    try:
        gid = int(key)
    except (TypeError, ValueError, OverflowError):
        return None
    return gid if gid >= 0 else None


def _clamp_tab(value, count):  # type: (any, int) -> int
    """ 页签下标落进 [0, 页签数]；页签数到上限时没有「新页签」那一格 """
    if isinstance(value, bool) or not isinstance(value, (int, long)):
        return 0
    top = count if count < MAX_TABS else count - 1
    return max(0, min(value, top))


def _new_group_id(tab):  # type: (dict) -> int
    used = [entry_group(e) for e in tab[KEY_ENTRIES]]
    used.extend(_parse_gid(k) or 0 for k in tab[KEY_GROUPS])
    return max(used + [UNGROUPED]) + 1


def _run_bounds(entries, index):  # type: (list, int) -> tuple
    """ index 所在那一段连续同组条目的首尾下标 """
    gid = entry_group(entries[index])
    start = end = index
    while start > 0 and entry_group(entries[start - 1]) == gid:
        start -= 1
    while end + 1 < len(entries) and entry_group(entries[end + 1]) == gid:
        end += 1
    return start, end


def _last_index_of_group(entries, gid):  # type: (list, int) -> int or None
    for index in range(len(entries) - 1, -1, -1):
        if entry_group(entries[index]) == gid:
            return index
    return None


def _prune_groups(tab):
    """ 成员都没了的分组，属性一并删掉；"0"（不分组那部分）一直留着 """
    alive = set(entry_group(e) for e in tab[KEY_ENTRIES])
    groups = tab[KEY_GROUPS]
    for key in list(groups):
        gid = _parse_gid(key)
        if gid is None or (gid != UNGROUPED and gid not in alive):
            del groups[key]


def _set_props(tab, gid, props):
    key = str(gid)
    if props:
        tab[KEY_GROUPS][key] = props
    else:
        tab[KEY_GROUPS].pop(key, None)


# 迁移
# ======================================================================================================================
def _migrate_v1_order(payload):  # type: (dict) -> dict
    """ 逐类翻转列表顺序 """
    for kind in (_V2_RECIPES, _V2_ITEMS):
        entries = payload.get(kind)
        if isinstance(entries, list):
            payload[kind] = list(reversed(entries))
    return payload


def _string_list(value):  # type: (any) -> list
    if not isinstance(value, list):
        return []
    return [native_str(v) for v in value if v and isinstance(v, basestring)]


def _category_of(rid):  # type: (str) -> str
    """ 从 "mei:/<类型>/<指纹>" 里拆出类型；来源自己给的 Id 拆不出，返回空串 """
    prefix = ID_NAMESPACE + ":/"
    if not rid.startswith(prefix):
        return ""
    category_id, sep, _digest = rid[len(prefix):].rpartition("/")
    return category_id if sep else ""


def _migrate_v2_entries(payload):  # type: (dict) -> dict
    """ 两张字符串表并成一张条目表，配方排前，看不懂的旧值跳过，见 bookmarks.md §6 """
    entries = []
    for rid in _string_list(payload.get(_V2_RECIPES)):
        entry = {"k": KIND_RECIPE, "id": rid}
        category_id = _category_of(rid)
        if category_id:
            entry["cat"] = category_id
        entries.append(entry)
    for text in _string_list(payload.get(_V2_ITEMS)):
        try:
            item_id, aux = keys.key_from_str(text)
        except ValueError:
            continue
        entries.append({"k": KIND_ITEM, "id": item_id, "aux": aux})

    migrated = dict((k, v) for k, v in payload.items() if k not in (_V2_RECIPES, _V2_ITEMS))
    migrated[KEY_ENTRIES] = entries
    return migrated


def _migrate_v3_tabs(payload):  # type: (dict) -> dict
    """ 原来那一张条目表成为第一个页签，不分组，顺序不动，见 bookmarks.md §6 """
    entries = payload.get(KEY_ENTRIES)
    migrated = dict((k, v) for k, v in payload.items() if k != KEY_ENTRIES)
    migrated[KEY_TABS] = [{KEY_ENTRIES: entries if isinstance(entries, list) else [], KEY_GROUPS: {}}]
    migrated[KEY_TAB] = 0
    return migrated


MIGRATIONS = {1: _migrate_v1_order, 2: _migrate_v2_entries, 3: _migrate_v3_tabs}
""" {旧版本号: fn(payload) -> payload}，升版时在此登记，见 storage/store.py """


class __BookmarkManager(object):  # noqa
    """
    书签门面，构造期不碰引擎；条目当不可变数据用，改动只换表里的元素
    """
    def __init__(self):
        self._stores = {}  # type: dict
        """ is_global -> Store，用到哪个建哪个 """
        self._factory = None
        self._world = False
        self._tabs = None  # type: list or None
        self._tab = 0
        self._index = {}  # type: dict
        """ 当前页签：身份键 -> 条数，按钮状态每帧都问 """
        self._revision = 0
        self._pages = {}  # type: dict
        """ 页签下标 -> 收藏栏停在第几页，只在内存里 """

    # 存储的选择
# ======================================================================================================================
    def _make_store(self, is_global):  # type: (bool) -> Store
        if self._factory is not None:
            return self._factory(is_global)
        # 延迟到首次使用才 import backend，它顶层拉客户端引擎
        from .storage.backend import ConfigBackend, EngineScheduler
        return Store(
            ConfigBackend(), CONFIG_NAME, is_global=is_global,
            version=VERSION, migrations=MIGRATIONS,
            scheduler=EngineScheduler(),
        )

    def _store_of(self, is_global):  # type: (bool) -> Store
        store = self._stores.get(is_global)
        if store is None:
            store = self._make_store(is_global)
            self._stores[is_global] = store
        return store

    def _get_store(self):  # type: () -> Store
        return self._store_of(not self._world)

    def SetStoreFactory(self, factory):
        """ 测试注入点：factory(is_global) -> Store；换了就丢掉已建好的内存表 """
        self._factory = factory
        self._stores = {}
        self._world = False
        self._drop()

    def SetStore(self, store):
        """ 测试注入点：只给一个全局 Store，并回到全局模式 """
        self._factory = None
        self._stores = {True: store}
        self._world = False
        self._drop()

    def SetWorldSpecific(self, on):  # type: (bool) -> bool
        """ 切换全局 / 按存档保存：先把手上的写下去再换；返回是否真的换了 """
        on = bool(on)
        if on == self._world:
            return False
        if self._tabs is not None:
            self.Flush()
        self._world = on
        self._drop()
        return True

    def IsWorldSpecific(self):  # type: () -> bool
        return self._world

    def ResetWorldStore(self):
        """ 进了另一个存档：按存档的那份要从头读（门面跨存档存活），全局那份留着 """
        self._stores.pop(False, None)
        if self._world:
            self._drop()

    def _drop(self):
        self._tabs = None
        self._tab = 0
        self._index = {}
        self._pages = {}
        self._revision += 1

    # 读写
# ======================================================================================================================
    @staticmethod
    def _read(store):  # type: (Store) -> tuple
        """ (页签表, 当前下标)；读不到时页签表为 None """
        try:
            return store.Get(KEY_TABS, None), store.Get(KEY_TAB, 0)
        except Exception as e:  # noqa  Store 自己兜过一层，这里防注入的后端与将来的改动
            logger.error("[MEI/bookmarks] 读取失败, 本轮按空处理: {}".format(error_text(e)))
            return None, 0

    def _load(self):  # type: () -> list
        """ 首次访问时从 Store 灌一次；盘上不成形的东西只降级不外抛（engineering.md §7-9）"""
        if self._tabs is not None:
            return self._tabs
        raw_tabs, raw_tab = self._read(self._get_store())
        if raw_tabs is None and self._world:
            # 按存档的还没写过：照 NEI 拿全局的一份当起点；只在内存里，第一次改动时才写进存档
            raw_tabs, raw_tab = self._read(self._store_of(True))
        if raw_tabs is not None and not isinstance(raw_tabs, list):
            logger.warn("[MEI/bookmarks] 页签表不是列表({}), 本轮按空处理".format(type(raw_tabs).__name__))
            raw_tabs = None
        tabs = [_normalize_tab(raw) for raw in raw_tabs or ()]
        if not tabs:
            tabs = [_empty_tab()]
        self._tabs = tabs
        self._tab = _clamp_tab(raw_tab, len(tabs))
        self._reindex()
        return tabs

    def _current_tab(self):  # type: () -> dict or None
        """ 当前页签；停在「新页签」上时为 None """
        tabs = self._load()
        return tabs[self._tab] if self._tab < len(tabs) else None

    def _current_entries(self):  # type: () -> list
        tab = self._current_tab()
        return tab[KEY_ENTRIES] if tab is not None else []

    def _writable_tab(self):  # type: () -> dict or None
        """ 当前页签；停在「新页签」上时先把它建出来，页签数到上限返回 None """
        tabs = self._load()
        if self._tab < len(tabs):
            return tabs[self._tab]
        if len(tabs) >= MAX_TABS:
            return None
        tab = _empty_tab()
        tabs.append(tab)
        self._tab = len(tabs) - 1
        return tab

    def _reindex(self):
        index = {}
        for entry in self._current_entries():
            identity = _safe_identity(entry)
            if identity is not None:
                index[identity] = index.get(identity, 0) + 1
        self._index = index

    def _persist(self):
        """ 整张页签表写回；条目是不可变数据，浅拷贝就足够让 Store 看出变了没有 """
        self._revision += 1
        self._reindex()
        tabs = []
        for tab in self._tabs:
            copied = dict(tab)
            copied[KEY_ENTRIES] = list(tab[KEY_ENTRIES])
            copied[KEY_GROUPS] = dict(tab[KEY_GROUPS])
            tabs.append(copied)
        try:
            store = self._get_store()
            store.Set(KEY_TABS, tabs)
            store.Set(KEY_TAB, self._tab)
        except Exception as e:  # noqa
            logger.error("[MEI/bookmarks] 写入失败: {}".format(error_text(e)))

    def Flush(self, force=False):  # type: (bool) -> bool
        """ 写盘；一次都没读写过时不建后端 """
        if not self._stores:
            return True
        try:
            return self._get_store().Flush(force)
        except Exception as e:  # noqa
            logger.error("[MEI/bookmarks] 写盘失败: {}".format(error_text(e)))
            return False

    def IsDegraded(self):  # type: () -> bool
        return self._get_store().IsDegraded()

    def Revision(self):  # type: () -> int
        """ 改动计数：增删改、切页签、换存储位置都会变，收藏栏按它判断要不要重排 """
        self._load()
        return self._revision

    # 页签
# ======================================================================================================================
    def TabCount(self):  # type: () -> int
        """ 已有的页签数，不含末尾那个「新页签」"""
        return len(self._load())

    def TabIndex(self):  # type: () -> int
        self._load()
        return self._tab

    def IsNewTab(self):  # type: () -> bool
        """ 是否停在末尾那个还没建出来的「新页签」上 """
        return self.TabIndex() >= self.TabCount()

    def StepTab(self, delta):  # type: (int) -> int
        """ 循环切换页签；页签数没到上限时末尾多一格「新页签」"""
        tabs = self._load()
        slots = len(tabs) + (1 if len(tabs) < MAX_TABS else 0)
        return self.SwitchTab((self._tab + delta) % slots)

    def SwitchTab(self, index):  # type: (int) -> int
        """ 切到第 index 个页签；离开的页签若已经空了就删掉（只剩一页时留着）"""
        tabs = self._load()
        index = _clamp_tab(index, len(tabs))
        if index == self._tab:
            return index
        old = self._tab
        if old < len(tabs) and not tabs[old][KEY_ENTRIES] and len(tabs) > 1:
            del tabs[old]
            self._pages = dict(((i - 1 if i > old else i), page) for i, page in self._pages.items() if i != old)
            if index > old:
                index -= 1
        self._tab = index
        self._persist()
        return index

    def PageOfTab(self):  # type: () -> int
        """ 收藏栏在当前页签停在第几页（从 0 起）"""
        self._load()
        return self._pages.get(self._tab, 0)

    def SetPageOfTab(self, page):  # type: (int) -> None
        self._load()
        self._pages[self._tab] = max(0, int(page))

    # 条目与分组：下标都是当前页签条目表里的位置
# ======================================================================================================================
    def Entries(self, kind=None):  # type: (str or None) -> list
        """ 当前页签条目表的副本（显示顺序）；kind 为空时连看不懂的条目也给出，调用方自己跳过 """
        entries = list(self._current_entries())
        if kind is None:
            return entries
        return [e for e in entries if isinstance(e, dict) and e.get("k") == kind]

    def EntryAt(self, index):  # type: (int) -> dict or None
        entries = self._current_entries()
        return entries[index] if 0 <= index < len(entries) else None

    def Count(self, kind=None):  # type: (str or None) -> int
        return len(self.Entries(kind))

    def IsTabFull(self):  # type: () -> bool
        return len(self._current_entries()) >= MAX_TAB_ENTRIES

    def Groups(self):  # type: () -> dict
        """ 当前页签分组表的副本 {分组 id: 属性} """
        tab = self._current_tab()
        if tab is None:
            return {}
        result = {}
        for key, props in tab[KEY_GROUPS].items():
            gid = _parse_gid(key)
            if gid is not None:
                result[gid] = dict(props)
        return result

    def GroupProps(self, gid):  # type: (int) -> dict
        return self.Groups().get(gid, {})

    def HasKey(self, identity):  # type: (str) -> bool
        """ 当前页签里有没有这个身份的条目，O(1)；它在按钮状态绑定的每帧路径上 """
        if not identity:
            return False
        self._load()
        return identity in self._index

    def AddEntry(self, entry, group=UNGROUPED):  # type: (dict, int) -> bool
        """ 加到末尾；给了分组就加到该组最后一条后面。条目不成形、页签满了返回 False """
        if _safe_identity(entry) is None:
            return False
        tab = self._writable_tab()
        if tab is None:
            logger.info("[MEI/bookmarks] 页签数已到上限 {}, 拒绝新建".format(MAX_TABS))
            return False
        entries = tab[KEY_ENTRIES]
        if len(entries) >= MAX_TAB_ENTRIES:
            logger.info("[MEI/bookmarks] 当前页签已满 {} 条, 拒绝新增".format(MAX_TAB_ENTRIES))
            return False
        entry = replace_fields(entry, {FIELD_GROUP: group})
        last = _last_index_of_group(entries, group) if group else None
        if last is None:
            entries.append(entry)
        else:
            entries.insert(last + 1, entry)
        self._persist()
        return True

    def RemoveAt(self, index):  # type: (int) -> bool
        tab = self._current_tab()
        if tab is None or not 0 <= index < len(tab[KEY_ENTRIES]):
            return False
        del tab[KEY_ENTRIES][index]
        _prune_groups(tab)
        self._persist()
        return True

    def RemoveKey(self, identity):  # type: (str) -> bool
        """ 删掉当前页签里这个身份的全部条目 """
        tab = self._current_tab()
        if tab is None or not identity:
            return False
        entries = tab[KEY_ENTRIES]
        kept = [e for e in entries if _safe_identity(e) != identity]
        if len(kept) == len(entries):
            return False
        tab[KEY_ENTRIES] = kept
        _prune_groups(tab)
        self._persist()
        return True

    def RemoveGroup(self, gid):  # type: (int) -> bool
        """ 删掉整组；gid 为 0 时删的是全部不分组的条目，看不懂的条目照样留着 """
        tab = self._current_tab()
        if tab is None:
            return False
        entries = tab[KEY_ENTRIES]
        kept = [e for e in entries if entry_group(e) != gid or _safe_identity(e) is None]
        if len(kept) == len(entries):
            return False
        tab[KEY_ENTRIES] = kept
        _prune_groups(tab)
        self._persist()
        return True

    def Clear(self, kind=None):
        """ 清掉当前页签的一类；kind 为空时清空整个页签（含看不懂的条目）"""
        tab = self._current_tab()
        if tab is None:
            return
        entries = tab[KEY_ENTRIES]
        if kind is None:
            kept = []
        else:
            kept = [e for e in entries if not (isinstance(e, dict) and e.get("k") == kind)]
        if len(kept) == len(entries):
            return
        tab[KEY_ENTRIES] = kept
        _prune_groups(tab)
        self._persist()

    def SetCountAt(self, index, count):  # type: (int, int) -> bool
        """ 改数量，夹在 [1, MAX_COUNT]；没变返回 False """
        entry = self.EntryAt(index)
        if entry is None or _safe_identity(entry) is None:
            return False
        try:
            count = max(1, min(int(count), MAX_COUNT))
        except (TypeError, ValueError, OverflowError):
            return False
        if count == entry_count(entry):
            return False
        self._current_entries()[index] = replace_fields(entry, {FIELD_COUNT: count})
        self._persist()
        return True

    def AdjustCountAt(self, index, delta):  # type: (int, int) -> bool
        entry = self.EntryAt(index)
        return entry is not None and self.SetCountAt(index, entry_count(entry) + delta)

    def SetExpandedAt(self, index, expanded):  # type: (int, bool) -> bool
        """ 配方 / 配方树收藏展开 / 收起（记成玩家定的，换视图也不变；树展开就是原料汇总）；不是这两种或没变返回 False """
        entry = self.EntryAt(index)
        if entry is None or entry.get("k") not in (KIND_RECIPE, KIND_TREE) or _safe_identity(entry) is None:
            return False
        expanded = bool(expanded)
        if entry.get(FIELD_EXPAND) is expanded:
            return False
        self._current_entries()[index] = replace_fields(entry, {FIELD_EXPAND: expanded})
        self._persist()
        return True

    def JoinPrevGroupAt(self, index):  # type: (int) -> int
        """ 并入上一条所在的组；上一条不分组就以这一条新建一组。返回所在分组 id，没动返回 0 """
        tab = self._current_tab()
        if tab is None or not 0 <= index < len(tab[KEY_ENTRIES]):
            return UNGROUPED
        entries = tab[KEY_ENTRIES]
        entry = entries[index]
        if _safe_identity(entry) is None:
            return UNGROUPED
        current = entry_group(entry)
        previous = entry_group(entries[index - 1]) if index > 0 else UNGROUPED
        if previous and previous != current:
            target = previous
        elif current == UNGROUPED:
            target = _new_group_id(tab)
        else:
            return UNGROUPED
        entries[index] = replace_fields(entry, {FIELD_GROUP: target})
        _prune_groups(tab)
        self._persist()
        return target

    def LeaveGroupAt(self, index):  # type: (int) -> bool
        """ 移出分组；在组中间时把组一分为二，后半截换新 id 并带走原属性 """
        tab = self._current_tab()
        if tab is None or not 0 <= index < len(tab[KEY_ENTRIES]):
            return False
        entries = tab[KEY_ENTRIES]
        current = entry_group(entries[index])
        if current == UNGROUPED:
            return False
        start, end = _run_bounds(entries, index)
        entries[index] = replace_fields(entries[index], {FIELD_GROUP: UNGROUPED})
        if start < index < end:
            split = _new_group_id(tab)
            props = tab[KEY_GROUPS].get(str(current))
            if props:
                tab[KEY_GROUPS][str(split)] = dict(props)
            for i in range(index + 1, end + 1):
                entries[i] = replace_fields(entries[i], {FIELD_GROUP: split})
        _prune_groups(tab)
        self._persist()
        return True

    def ToggleGroupView(self, gid):  # type: (int) -> str
        """ 横排 / 竖排清单互换，返回换完的视图；gid 为 0 时换的是不分组那部分 """
        tab = self._current_tab()
        if tab is None:
            return VIEW_GRID
        props = dict(tab[KEY_GROUPS].get(str(gid), {}))
        if props.get(GROUP_VIEW) == VIEW_LIST:
            props.pop(GROUP_VIEW, None)
        else:
            props[GROUP_VIEW] = VIEW_LIST
        _set_props(tab, gid, props)
        self._persist()
        return props.get(GROUP_VIEW, VIEW_GRID)

    def ToggleGroupFold(self, gid):  # type: (int) -> bool
        """ 折叠 / 展开一组，返回换完是否折叠；不分组的那部分不能折叠 """
        tab = self._current_tab()
        if tab is None or gid == UNGROUPED:
            return False
        props = dict(tab[KEY_GROUPS].get(str(gid), {}))
        if props.get(GROUP_FOLD):
            props.pop(GROUP_FOLD, None)
        else:
            props[GROUP_FOLD] = True
        _set_props(tab, gid, props)
        self._persist()
        return bool(props.get(GROUP_FOLD))

    def CanJoinPrevGroupAt(self, index):  # type: (int) -> bool
        """ 「并入上一组」会不会动（和 JoinPrevGroupAt 的判断同一套）：触屏菜单拿它决定灰不灰 """
        entries = self._current_entries()
        if not 0 <= index < len(entries) or _safe_identity(entries[index]) is None:
            return False
        current = entry_group(entries[index])
        previous = entry_group(entries[index - 1]) if index > 0 else UNGROUPED
        return bool(previous and previous != current) or current == UNGROUPED

    # 排序（上移 / 下移 / 移到组首；组在条目表里是连在一起的一串，挪动不能把它拆开）
# ======================================================================================================================
    def MoveTargetAt(self, index, delta):  # type: (int, int) -> int or None
        """
        上移（delta = -1）/ 下移（+1）会落到哪个下标，只算不改（菜单拿它决定灰不灰）。
        在组里的只在本组里动，到了组的头尾给 None；不在组里的碰到一个组，整个跳过它落到另一头 —— 不会混进组里。
        看不懂的条目、越界给 None
        """
        entries = self._current_entries()
        if delta not in (-1, 1) or not 0 <= index < len(entries) or _safe_identity(entries[index]) is None:
            return None
        neighbor = index + delta
        if not 0 <= neighbor < len(entries):
            return None
        gid = entry_group(entries[index])
        if gid != UNGROUPED:
            return neighbor if entry_group(entries[neighbor]) == gid else None
        if entry_group(entries[neighbor]) == UNGROUPED:
            return neighbor
        start, end = _run_bounds(entries, neighbor)
        return start if delta < 0 else end

    def MoveAt(self, index, delta):  # type: (int, int) -> int or None
        """ 上移 / 下移一步（规则见 MoveTargetAt），返回挪到的下标；挪不动返回 None """
        target = self.MoveTargetAt(index, delta)
        if target is None:
            return None
        entries = self._current_entries()
        entries.insert(target, entries.pop(index))
        self._persist()
        return target

    def GroupHeadAt(self, index):  # type: (int) -> int or None
        """ 「移到组首」会落到哪：在组里的是本组第一条的位置；不在组里（灰掉）、已经是组首、看不懂的给 None """
        entries = self._current_entries()
        if not 0 <= index < len(entries) or _safe_identity(entries[index]) is None:
            return None
        if entry_group(entries[index]) == UNGROUPED:
            return None
        start, _end = _run_bounds(entries, index)
        return start if start < index else None

    def MoveToGroupHeadAt(self, index):  # type: (int) -> int or None
        """ 移到本组第一条，返回挪到的下标；挪不动返回 None """
        target = self.GroupHeadAt(index)
        if target is None:
            return None
        entries = self._current_entries()
        entries.insert(target, entries.pop(index))
        self._persist()
        return target

    # 配方书签：配方页的星号走这一组
# ======================================================================================================================
    @staticmethod
    def RecipeKey(recipe):  # type: (any) -> str
        """ 配方的 Id，拿不到的返回空串 —— 这样的配方收不进来 """
        rid = native_str(recipe_id(recipe))
        return rid if rid and isinstance(rid, basestring) else ""

    def HasRecipe(self, recipe):  # type: (any) -> bool
        rid = self.RecipeKey(recipe)
        return self.HasKey(_identity(KIND_RECIPE, rid)) if rid else False

    def SetRecipe(self, recipe, on):  # type: (any, bool) -> bool
        """ 显式设置，toggle 回调直接用它；打开时已有就不再加，关掉时删掉当前页签里的全部同一条 """
        rid = self.RecipeKey(recipe)
        if not rid:
            return False
        identity = _identity(KIND_RECIPE, rid)
        if not on:
            return self.RemoveKey(identity)
        if self.HasKey(identity):
            return False
        entry = recipe_entry(recipe)
        return self.AddEntry(entry) if entry else False

    def ListRecipes(self):  # type: () -> list
        """ 当前页签收藏的配方 Id，按显示顺序 """
        return [native_str(e.get("id")) for e in self.Entries(KIND_RECIPE)
                if _safe_identity(e) is not None]

    # 配方树（docs/architecture/recipe_tree.md）：一整棵存成一条，能展开，展开就是原料汇总的快照
# ======================================================================================================================
    def TreeIndex(self, root_key):  # type: (str) -> int or None
        """ 当前页签里根是这个物品（物品键 "id#aux"）的配方树收藏在第几条；没有给 None """
        if not root_key:
            return None
        identity = _identity(KIND_TREE, root_key)
        if not self.HasKey(identity):
            return None
        for index, entry in enumerate(self._current_entries()):
            if _safe_identity(entry) == identity:
                return index
        return None

    def SaveTree(self, entry):  # type: (dict) -> str or None
        """
        存一棵配方树（recipe_tree 的 TreeState.ToEntry）：同一个根已经收过就原地更新那一条（分组、展开、数量照旧），
        否则加到末尾。返回 "updated" / "added"，条目不成形或页签满了给 None
        """
        identity = _safe_identity(entry)
        if identity is None or entry.get("k") != KIND_TREE:
            return None
        index = None
        if self.HasKey(identity):
            for at, old in enumerate(self._current_entries()):
                if _safe_identity(old) == identity:
                    index = at
                    break
        if index is None:
            return "added" if self.AddEntry(entry) else None
        old = self._current_entries()[index]
        kept = dict((name, old[name]) for name in (FIELD_GROUP, FIELD_EXPAND, FIELD_COUNT) if name in old)
        new = dict(entry)
        new.update(kept)
        self._current_entries()[index] = new
        self._persist()
        return "updated"

    # 物品书签
# ======================================================================================================================
    @staticmethod
    def ItemKey(item):  # type: (any) -> str
        """ 物品的身份键 "id#aux"，带区分变体的 Attr 时再接 "#指纹"；拿不到 ItemId 的返回空串 """
        return item_key(item_data(item))

    def HasItem(self, item):  # type: (any) -> bool
        key = self.ItemKey(item)
        return self.HasKey(_identity(KIND_ITEM, key)) if key else False

    def SetItem(self, item, on, group=UNGROUPED):  # type: (any, bool, int) -> bool
        key = self.ItemKey(item)
        if not key:
            return False
        identity = _identity(KIND_ITEM, key)
        if not on:
            return self.RemoveKey(identity)
        if self.HasKey(identity):
            return False
        entry = item_entry(item)
        return self.AddEntry(entry, group) if entry else False

    def ToggleItem(self, item):  # type: (any) -> bool
        """ 翻转并返回翻转后的状态，拿不到身份键的物品返回 False """
        key = self.ItemKey(item)
        if not key:
            return False
        identity = _identity(KIND_ITEM, key)
        self.SetItem(item, not self.HasKey(identity))
        return self.HasKey(identity)

    def ListItems(self):  # type: () -> list
        """ 当前页签收藏物品的身份键，按显示顺序 """
        return [item_key(e) for e in self.Entries(KIND_ITEM) if item_key(e)]


BookmarkManager = __BookmarkManager()
