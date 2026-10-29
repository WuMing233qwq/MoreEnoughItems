# coding=utf-8

# ----------------------------------------------------------------------
#  pins.py is part of MoreEnoughItems.
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
配方置顶，跨存档，只置配方一类。
作用域、排序落点与上限行为见 docs/architecture/action_buttons.md §5.1。
"""
from MEIScripts.constants.codes import StorageConst
from MEIScripts.utils.history import LRUHistory
from MEIScripts.utils.log import logger
from MEIScripts.utils.sequence import recipe_id

from .storage import Store

CONFIG_NAME = StorageConst.PinsConfigName

VERSION = 1

MIGRATIONS = {}
""" {旧版本号: fn(payload) -> payload}，升版时在此登记，见 storage/store.py """

KEY_RECIPES = "recipes"
""" 置顶配方，list[str] of Recipe.Id，最近置顶在前 """

MAX_ENTRIES = 64
""" 上限；到顶拒绝新增而不是淘汰最旧的，见 Add """


class __PinManager(object):  # noqa
    """
    配方置顶门面，构造期不碰引擎
    """

    def __init__(self):
        self._store = None
        self._history = None  # type: LRUHistory or None
        self._ranks = None  # type: dict or None

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
        """ 测试注入点，替换为带假后端的 Store 并丢弃已建好的历史 """
        self._store = store
        self._history = None
        self._ranks = None

    def _get_history(self):  # type: () -> LRUHistory
        if self._history is None:
            history = LRUHistory(MAX_ENTRIES)
            entries = self._get_store().Get(KEY_RECIPES, [])
            if entries is None:
                entries = []
            if not isinstance(entries, list):
                # 盘上的东西不成形：置顶可以丢，加载不能卡（engineering.md §7-9）
                logger.warn("[MEI/pins] 置顶表不是列表({}), 本轮按空处理".format(
                    type(entries).__name__))
                entries = ()
            # 盘上是最近在前而 add 是头插，倒着灌才能还原顺序
            for key in reversed(list(entries)):
                if key and isinstance(key, basestring):
                    history.add(key)
            self._history = history
        return self._history

    def _persist(self):
        history = self._get_history()
        self._ranks = None
        self._get_store().Set(KEY_RECIPES, history.to_list())

    # 通用：按配方 Id 字符串操作
# ======================================================================================================================
    def Has(self, key):  # type: (str) -> bool
        """ 判存在，O(1)；它在按钮状态绑定的每帧路径上 """
        if not key:
            return False
        return key in self._get_history()

    def Add(self, key):  # type: (str) -> bool
        """ 加入；已存在则原地不动，到上限则拒绝 """
        # 不用 LRUHistory 的淘汰：置顶是玩家显式设的，被悄悄挤掉很怪
        if not key:
            return False
        history = self._get_history()
        if key in history:
            return False
        if len(history) >= MAX_ENTRIES:
            return False
        history.add(key)
        self._persist()
        return True

    def Remove(self, key):  # type: (str) -> bool
        if not key:
            return False
        if not self._get_history().remove(key):
            return False
        self._persist()
        return True

    def Set(self, key, on):  # type: (str, bool) -> bool
        """ 显式设置，toggle 回调直接用它，不必自己判方向 """
        return self.Add(key) if on else self.Remove(key)

    def List(self):  # type: () -> list
        """ 最近置顶在前 """
        return self._get_history().to_list()

    def Count(self):  # type: () -> int
        return len(self._get_history())

    def IsFull(self):  # type: () -> bool
        return len(self._get_history()) >= MAX_ENTRIES

    def Clear(self):
        self._get_history().clear()
        self._persist()

    def Flush(self, force=False):
        return self._get_store().Flush(force)

    def IsDegraded(self):
        return self._get_store().IsDegraded()

    # 配方置顶
# ======================================================================================================================
    @staticmethod
    def RecipeKey(recipe):  # type: (any) -> str
        """ Recipe 转存储键，拿不到 Id 的返回空串 """
        # Recipe.Id 在此被升格为跨存档的持久身份，改 to_canonical 会作废所有人的置顶
        return recipe_id(recipe) or ""

    def HasRecipe(self, recipe):  # type: (any) -> bool
        return self.Has(self.RecipeKey(recipe))

    def SetRecipe(self, recipe, on):  # type: (any, bool) -> bool
        return self.Set(self.RecipeKey(recipe), on)

    def ToggleRecipe(self, recipe):  # type: (any) -> bool
        """ 翻转并返回翻转后的状态；到上限而加不进去时仍返回 False """
        key = self.RecipeKey(recipe)
        if not key:
            return False
        on = not self.Has(key)
        self.Set(key, on)
        return self.Has(key)

    def RankOf(self, recipe):  # type: (any) -> int or None
        """ 置顶序号，越小越靠前；未置顶返回 None """
        # 排序是每次查询都要跑的，而置顶极少变，故把名次缓存下来，写入时置空
        key = self.RecipeKey(recipe)
        if not key:
            return None
        if self._ranks is None:
            self._ranks = dict(
                (entry, index) for index, entry in enumerate(self._get_history())
            )
        return self._ranks.get(key)


PinManager = __PinManager()
