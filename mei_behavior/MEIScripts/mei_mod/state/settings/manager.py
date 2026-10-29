# coding=utf-8
# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
设置项注册表与取值，跨存档。界面与生效规则见 docs/architecture/settings.md。
"""
from MEIScripts.constants.codes import StorageConst
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from ..storage import Store
from .kinds import Setting

CONFIG_NAME = StorageConst.SettingsConfigName

VERSION = 1

MIGRATIONS = {}
""" {旧版本号: fn(payload) -> payload}，升版时在此登记，见 storage/store.py """

KEY_VALUES = "values"
""" {设置项 key: 值}，只存玩家改过的；恢复默认即删掉该键，以后跟随默认值 """


class __SettingsManager(object):  # noqa
    """
    设置项门面，构造期不碰引擎
    """

    def __init__(self):
        self._store = None
        self._specs = []  # type: list  # 登记顺序
        self._index = {}  # type: dict
        self._raw = None  # type: dict or None  # 盘上原样的值表，看不懂的键也原样留着
        self._cache = {}  # type: dict  # key -> 规约后的当前值，绑定每帧都读
        self._watchers = {}  # type: dict

    def _get_store(self):  # type: () -> Store
        if self._store is None:
            # 延迟到首次使用才 import backend，它顶层拉客户端引擎
            from ..storage.backend import ConfigBackend, EngineScheduler
            self._store = Store(
                ConfigBackend(), CONFIG_NAME, is_global=True,
                version=VERSION, migrations=MIGRATIONS,
                scheduler=EngineScheduler(),
            )
        return self._store

    def SetStore(self, store):
        """ 测试注入点，替换为带假后端的 Store 并丢弃已读的值 """
        self._store = store
        self._raw = None
        self._cache.clear()

    def _get_raw(self):  # type: () -> dict
        if self._raw is None:
            raw = self._get_store().Get(KEY_VALUES, {})
            if not isinstance(raw, dict):
                # 盘上的东西不成形：设置可以丢，加载不能卡（engineering.md §7-9）
                logger.warn("[MEI/settings] 设置表不是字典({}), 本轮按空处理".format(type(raw).__name__))
                raw = {}
            self._raw = dict(raw)
        return self._raw

    # 注册
# ======================================================================================================================
    def Register(self, spec):  # type: (Setting) -> bool
        """ 登记一个设置项；key 重复则拒绝 """
        if not isinstance(spec, Setting):
            logger.error("[MEI/settings] 不是设置项: {!r}".format(spec))
            return False
        if spec.Key in self._index:
            logger.warn("[MEI/settings] 设置项 {} 重复登记, 忽略后来的".format(spec.Key))
            return False
        self._specs.append(spec)
        self._index[spec.Key] = spec
        return True

    def GetSpec(self, key):  # type: (str) -> Setting or None
        return self._index.get(key)

    def GetSpecs(self):  # type: () -> list
        return list(self._specs)

    # 读写
# ======================================================================================================================
    def Get(self, key):
        """ 当前值；未登记或动作项返回 None """
        if key in self._cache:
            return self._cache[key]
        spec = self._index.get(key)
        if spec is None or not spec.HAS_VALUE:
            return None
        value = spec.Default
        raw = self._get_raw()
        if key in raw:
            try:
                value = spec.Coerce(raw[key])
            except (TypeError, ValueError):
                pass  # 盘上的值看不懂就按默认值走，原值留着不动
        self._cache[key] = value
        return value

    def Set(self, key, value):  # type: (str, any) -> bool
        """ 改值并落盘；值不合法或没变化返回 False """
        spec = self._index.get(key)
        if spec is None or not spec.HAS_VALUE:
            return False
        try:
            value = spec.Coerce(value)
        except (TypeError, ValueError) as e:
            logger.warn("[MEI/settings] {} 的新值不合法: {}".format(key, error_text(e)))
            return False
        if value == self.Get(key):
            return False
        raw = dict(self._get_raw())
        raw[key] = value
        self._commit(raw)
        self._notify(key, value)
        return True

    def Reset(self, key):  # type: (str) -> bool
        """ 恢复默认；返回值是否有变化 """
        spec = self._index.get(key)
        if spec is None or not spec.HAS_VALUE or key not in self._get_raw():
            return False
        before = self.Get(key)
        raw = dict(self._get_raw())
        del raw[key]
        self._commit(raw)
        after = self.Get(key)
        if after == before:
            return False
        self._notify(key, after)
        return True

    def ResetAll(self, kind=None):  # type: (str or None) -> int
        """
        全部恢复默认，返回值有变化的项数；没登记的键不碰。
        不给 kind：恢复跟着「全部」走的项（RESET_WITH_ALL，按键绑定不算 —— 它在自己那一页恢复）；给了只恢复这一类
        """
        return sum(1 for spec in self.GetSpecs() if spec.HAS_VALUE
                   and (spec.KIND == kind if kind else spec.RESET_WITH_ALL) and self.Reset(spec.Key))

    def Run(self, key):  # type: (str) -> bool
        """ 执行动作项 """
        spec = self._index.get(key)
        if spec is None or spec.HAS_VALUE:
            return False
        try:
            spec.Run()
        except Exception as e:  # noqa  一个按钮炸了不该带走设置页
            logger.error("[MEI/settings] 动作 {} 失败: {}".format(key, error_text(e)))
            return False
        return True

    def Watch(self, key, callback):  # type: (str, any) -> None
        """ 订阅某项的变化，回调签名 callback(key, value) """
        watchers = self._watchers.setdefault(key, [])
        if callback not in watchers:
            watchers.append(callback)

    def Unwatch(self, key, callback):  # type: (str, any) -> bool
        watchers = self._watchers.get(key) or []
        if callback not in watchers:
            return False
        watchers.remove(callback)
        return True

    def Flush(self, force=False):  # type: (bool) -> bool
        if self._store is None:
            return False  # 本轮没读写过设置，不必为了写盘去建后端
        return self._store.Flush(force)

    def IsDegraded(self):  # type: () -> bool
        return self._get_store().IsDegraded()

    # 内部
# ======================================================================================================================
    def _commit(self, raw):  # type: (dict) -> None
        self._raw = raw
        self._cache.clear()
        self._get_store().Set(KEY_VALUES, raw)

    def _notify(self, key, value):  # type: (str, any) -> None
        for callback in list(self._watchers.get(key, ())):
            try:
                callback(key, value)
            except Exception as e:  # noqa  订阅方的错不该让改设置失败
                logger.error("[MEI/settings] {} 的订阅回调失败: {}".format(key, error_text(e)))


SettingsManager = __SettingsManager()
