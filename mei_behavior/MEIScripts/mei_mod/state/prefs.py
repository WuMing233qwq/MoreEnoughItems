# coding=utf-8
# ----------------------------------------------------------------------
#  prefs.py is part of MoreEnoughItems.
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
用户偏好 —— **跨存档**(isGlobal=True).

本模块也是跨存档持久化的验证载体: OpenCount 每次打开 MEI 界面 +1 并落盘.
退出重进、**换存档**后计数仍连续, 即证明跨存档持久化成立
(docs/migration/tasks_s15.md §7).

> 原先把它拼进物品 hover 文本当调试显示, 那段已随 DebugText 一并删掉
> —— hover 是每帧回读的热路径, 不该长期挂调试串。
> `GetOpenCount()` 因此暂时**没有消费方**, 但**刻意保留**: 它是这条持久化链路
> 唯一的端到端证据, 要验的时候在日志里打一行即可。
"""
from MEIScripts.constants.codes import QueryConst, StorageConst
from MEIScripts.constants.ui import ModeConst

from .storage import Store

CONFIG_NAME = StorageConst.PrefsConfigName
""" 只能含字母/数字/下划线, 带 mei 前缀避免与其他 addon 撞名. 值见 constants/codes.py """

VERSION = 1

MIGRATIONS = {}
""" {旧版本号: fn(payload) -> payload}; 升版时在此登记, 见 storage/store.py """

KEY_OPEN_COUNT = "open_count"
KEY_DEFAULT_QUERY_BY = "default_query_by"
KEY_FLOAT_POSITION = "float_position"
""" 悬浮窗拖到哪：[横, 竖]，各是可用范围里的比例（0~1），换分辨率、换界面都还在同一处 """
KEY_MODE = "mode"
""" 普通 / 工具 / 作弊（ModeConst）：点模式按钮轮换，全局记一份、关界面不复位；作弊没有操作员权限时由界面改回普通 """
KEY_ITEM_FILTERS = "item_filters"
""" 物品栏选了哪几项筛选（registry/filters.py 的 Id 表）；登记表里已经没有的读的时候忽略 """
KEY_ITEM_SORT = "item_sort"
""" 物品栏按什么排：[排序 Id, "asc" / "desc"]；不排是 None """

DEFAULT_QUERY_BY = QueryConst.Output


class __PrefsManager(object):  # noqa
    """ 偏好门面. **构造期不碰引擎** —— Store 惰性创建 """

    def __init__(self):
        self._store = None

    def _get_store(self):  # type: () -> Store
        if self._store is None:
            # 延迟到首次使用才 import backend: 它顶层拉客户端引擎,
            # 在此处 import 可让 mei_mod.state 包本身保持可离线加载
            from .storage.backend import ConfigBackend, EngineScheduler
            self._store = Store(
                ConfigBackend(), CONFIG_NAME, is_global=True,
                version=VERSION, migrations=MIGRATIONS,
                scheduler=EngineScheduler(),
            )
        return self._store

    def SetStore(self, store):
        """ 测试注入点: 替换为带假后端的 Store """
        self._store = store

    # 通用读写
# ======================================================================================================================
    def Get(self, key, default=None):
        return self._get_store().Get(key, default)

    def Set(self, key, value):
        return self._get_store().Set(key, value)

    def Flush(self, force=False):
        return self._get_store().Flush(force)

    def IsDegraded(self):
        return self._get_store().IsDegraded()

    # 具体偏好项
# ======================================================================================================================
    def GetOpenCount(self):  # type: () -> int
        try:
            return int(self.Get(KEY_OPEN_COUNT, 0))
        except (TypeError, ValueError, OverflowError):
            return 0

    def BumpOpenCount(self):  # type: () -> int
        """ 打开 MEI 界面时 +1. 跨存档持久化的验证载体 """
        count = self.GetOpenCount() + 1
        self.Set(KEY_OPEN_COUNT, count)
        return count

    def GetDefaultQueryBy(self):  # type: () -> str
        value = self.Get(KEY_DEFAULT_QUERY_BY, DEFAULT_QUERY_BY)
        return value if value in (QueryConst.Output, QueryConst.Input) else DEFAULT_QUERY_BY

    def SetDefaultQueryBy(self, query_by):  # type: (str) -> bool
        if query_by not in (QueryConst.Output, QueryConst.Input):
            raise ValueError("query_by must be 'output' or 'input'")
        return self.Set(KEY_DEFAULT_QUERY_BY, query_by)

    def GetFloatPosition(self):  # type: () -> tuple or None
        """ 悬浮窗拖到的位置（比例）；没拖过、存的东西看不懂给 None """
        value = self.Get(KEY_FLOAT_POSITION)
        try:
            x, y = float(value[0]), float(value[1])
        except (TypeError, ValueError, IndexError, KeyError):
            return None
        return min(1.0, max(0.0, x)), min(1.0, max(0.0, y))

    def SetFloatPosition(self, position):  # type: (tuple) -> bool
        x, y = position
        return self.Set(KEY_FLOAT_POSITION, [min(1.0, max(0.0, float(x))), min(1.0, max(0.0, float(y)))])

    def GetMode(self):  # type: () -> str
        """ 记下的模式（ModeConst）；没记过、存的看不懂给普通 """
        value = self.Get(KEY_MODE, ModeConst.Normal)
        return value if value in ModeConst.Order else ModeConst.Normal

    def SetMode(self, mode):  # type: (str) -> bool
        if mode not in ModeConst.Order:
            raise ValueError("mode must be one of {}".format(ModeConst.Order))
        return self.Set(KEY_MODE, mode)

    def GetItemFilters(self):  # type: () -> list
        """ 物品栏选了的筛选 Id；存的看不懂给空表 """
        value = self.Get(KEY_ITEM_FILTERS)
        if not isinstance(value, list):
            return []
        return [one for one in value if isinstance(one, basestring)]

    def SetItemFilters(self, filter_ids):  # type: (list) -> bool
        return self.Set(KEY_ITEM_FILTERS, [one for one in filter_ids or () if isinstance(one, basestring)])

    def GetItemSort(self):  # type: () -> tuple or None
        """ 物品栏按什么排：(排序 Id, "asc" / "desc")；不排、存的看不懂给 None """
        value = self.Get(KEY_ITEM_SORT)
        if not isinstance(value, list) or len(value) != 2 or not isinstance(value[0], basestring) \
                or value[1] not in ("asc", "desc"):
            return None
        return value[0], value[1]

    def SetItemSort(self, sort):  # type: (tuple or None) -> bool
        if not sort:
            return self.Set(KEY_ITEM_SORT, None)
        sort_id, direction = sort
        if direction not in ("asc", "desc"):
            raise ValueError("direction must be 'asc' or 'desc'")
        return self.Set(KEY_ITEM_SORT, [sort_id, direction])


PrefsManager = __PrefsManager()
