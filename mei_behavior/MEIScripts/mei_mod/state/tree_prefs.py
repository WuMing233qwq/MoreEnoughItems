# coding=utf-8

# ----------------------------------------------------------------------
#  tree_prefs.py is part of MoreEnoughItems.
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
配方树的全局表，跨存档。树里的改动默认只管这一棵、随收藏保存（recipe_tree/modules/choices.py）；
节点菜单的「设为首选」「当原料（全局）」写这里，以后每一棵树都照它；工作方块格显示哪个候选按类型记在这里（只起显示作用）。

- defaults {物品键: 配方 Id}：做这个物品默认用哪条（解算的 prefs.Default）
- raw [物品键]：当原料，树里到它就不往下展开（解算的 prefs.IsRaw）
- stations {类型 Id: 物品键}：这个类型的工作方块格显示哪个工作站

物品键是 "id#aux"（keys.key_to_str）。配方 Id 是 Recipe.Id，和置顶、收藏一样：Id 的定义一改首选就找不回，当没设过。
盘上的东西看不懂就丢掉、不报错（engineering.md §7-9）
"""
from MEIScripts.constants.codes import StorageConst
from MEIScripts.utils.log import logger

from .storage import Store

CONFIG_NAME = StorageConst.TreePrefsConfigName

VERSION = 1

MIGRATIONS = {}
""" {旧版本号: fn(payload) -> payload}，升版时在此登记，见 storage/store.py """

KEY_DEFAULTS = "defaults"
KEY_RAW = "raw"
KEY_STATIONS = "stations"

MAX_DEFAULTS = 1024
MAX_RAW = 1024
""" 上限；到顶拒绝新增（不悄悄挤掉玩家设过的），改已有的照常 """


def _str_map(value, name):  # type: (any, str) -> dict
    if value is None:
        return {}
    if not isinstance(value, dict):
        logger.warn("[MEI/tree] 配方树全局表的 {} 不是字典({}), 本轮按空处理".format(name, type(value).__name__))
        return {}
    return dict((k, v) for k, v in value.items() if isinstance(k, basestring) and isinstance(v, basestring) and k and v)


def _str_set(value, name):  # type: (any, str) -> set
    if value is None:
        return set()
    if not isinstance(value, (list, tuple)):
        logger.warn("[MEI/tree] 配方树全局表的 {} 不是列表({}), 本轮按空处理".format(name, type(value).__name__))
        return set()
    return set(v for v in value if isinstance(v, basestring) and v)


class __TreePrefsManager(object):  # noqa
    """ 配方树全局表的门面，构造期不碰引擎 """

    def __init__(self):
        self._store = None
        self._defaults = None  # type: dict or None
        self._raw = None  # type: set or None
        self._stations = None  # type: dict or None
        self._revision = 0  # type: int

    def _get_store(self):  # type: () -> Store
        if self._store is None:
            # 延迟到首次使用才 import backend，它顶层拉客户端引擎
            from .storage.backend import ConfigBackend, EngineScheduler
            self._store = Store(
                ConfigBackend(), CONFIG_NAME, is_global=True,
                version=VERSION, migrations=MIGRATIONS,
                scheduler=EngineScheduler(),
            )
        return self._store

    def SetStore(self, store):
        """ 测试注入点，替换为带假后端的 Store 并丢弃读过的表 """
        self._store = store
        self._defaults = None
        self._raw = None
        self._stations = None

    def _load(self):
        if self._defaults is not None:
            return
        store = self._get_store()
        self._defaults = _str_map(store.Get(KEY_DEFAULTS), KEY_DEFAULTS)
        self._raw = _str_set(store.Get(KEY_RAW), KEY_RAW)
        self._stations = _str_map(store.Get(KEY_STATIONS), KEY_STATIONS)

    def _touch(self):
        self._revision += 1

    def Revision(self):  # type: () -> int
        """ 改一次加一：开着的树看它变没变决定要不要重算 """
        return self._revision

    # 首选配方
# ======================================================================================================================
    def Default(self, key):  # type: (str) -> str or None
        self._load()
        return self._defaults.get(key)

    def SetDefault(self, key, recipe_id):  # type: (str, str or None) -> bool
        """ 设为首选；recipe_id 给空就是取消。没变、到上限加不进返回 False """
        if not key:
            return False
        self._load()
        if not recipe_id:
            if key not in self._defaults:
                return False
            del self._defaults[key]
        else:
            if self._defaults.get(key) == recipe_id:
                return False
            if key not in self._defaults and len(self._defaults) >= MAX_DEFAULTS:
                return False
            self._defaults[key] = recipe_id
        self._get_store().Set(KEY_DEFAULTS, dict(self._defaults))
        self._touch()
        return True

    # 当原料
# ======================================================================================================================
    def IsRaw(self, key):  # type: (str) -> bool
        self._load()
        return key in self._raw

    def SetRaw(self, key, on):  # type: (str, bool) -> bool
        if not key:
            return False
        self._load()
        if on == (key in self._raw):
            return False
        if on:
            if len(self._raw) >= MAX_RAW:
                return False
            self._raw.add(key)
        else:
            self._raw.discard(key)
        self._get_store().Set(KEY_RAW, sorted(self._raw))
        self._touch()
        return True

    def RawKeys(self):  # type: () -> list
        self._load()
        return sorted(self._raw)

    # 工作方块格显示哪个工作站
# ======================================================================================================================
    def Station(self, type_id):  # type: (str) -> str or None
        self._load()
        return self._stations.get(type_id)

    def SetStation(self, type_id, key):  # type: (str, str or None) -> bool
        """ 只起显示作用，所以不撞 Revision —— 不重算树 """
        if not type_id:
            return False
        self._load()
        if (self._stations.get(type_id) or None) == (key or None):
            return False
        if key:
            self._stations[type_id] = key
        else:
            self._stations.pop(type_id, None)
        self._get_store().Set(KEY_STATIONS, dict(self._stations))
        return True

    def Flush(self, force=False):
        return self._get_store().Flush(force)

    def IsDegraded(self):
        return self._get_store().IsDegraded()


TreePrefsManager = __TreePrefsManager()
