# coding=utf-8

# ----------------------------------------------------------------------
#  scanner.py is part of MoreEnoughItems.
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
全量配方的分帧扫描器。

它存在的唯一理由是**引擎不给枚举接口**，只能逐个物品反查凑，所以它属于本扩展而不是框架：
自建表的来源(StaticRecipeSource)知道自己有哪些配方，根本用不上它。
"""
from MEIScripts.api.facades.registry import ItemManager, SourceRegistry
from MEIScripts.api.facades.utils import BudgetQueue, dedupe, logger, recipe_id

BUDGET_MS = 3.0
""" 每帧预算，与 engineering.md §6 的建议一致 """


class __RecipeScanner(object):  # noqa
    """ 按类别扫描全量配方，构造期不碰引擎也不扫任何东西 """

    def __init__(self):
        self._queue = BudgetQueue(BUDGET_MS, name="scan")
        self._results = {}  # type: dict  # category_id -> list
        self._done = set()  # type: set
        self._started = set()  # type: set

    # 查询
# ======================================================================================================================
    def IsDone(self, category_id):  # type: (str) -> bool
        """ 该类别是否已扫完；未开始也算未完成 """
        return category_id in self._done

    def IsScanning(self, category_id):  # type: (str) -> bool
        return category_id in self._started and category_id not in self._done

    def GetRecipes(self, category_id):  # type: (str) -> list
        """ 已扫到的配方；扫描中返回的是**部分结果**，配合 IsDone 用 """
        return list(self._results.get(category_id, ()))

    def GetStats(self):  # type: () -> dict
        stats = self._queue.GetStats()
        stats["categories"] = len(self._started)
        stats["completed"] = len(self._done)
        return stats

    # 驱动
# ======================================================================================================================
    def Request(self, category_id):  # type: (str) -> bool
        """ 请求扫描一个类别；已扫过或正在扫则不重复排队 """
        if not category_id or category_id in self._started:
            return False
        if SourceRegistry.GetCategory(category_id) is None:
            logger.warn("[MEI/scan] 类别 {} 未注册, 不扫".format(category_id))
            return False

        self._started.add(category_id)
        self._results[category_id] = []

        items = ItemManager.GetItems()
        if not items:
            # 物品表还没建好就请求，直接判完成，留给下一次 Reset 之后重来
            logger.warn("[MEI/scan] 物品表为空, {} 的扫描判为完成".format(category_id))
            self._done.add(category_id)
            return False

        for item in items:
            self._queue.Push(self._MakeJob(category_id, item))
        # 收尾 job 排在最后，队列跑到它就说明这一类扫完了
        self._queue.Push(self._MakeFinishJob(category_id, len(items)))
        logger.info("[MEI/scan] {} 开始扫描, 共 {} 个物品".format(category_id, len(items)))
        return True

    def Pump(self):  # type: () -> int
        """ 推进一帧，由客户端主系统的 Update 调 """
        return self._queue.PumpOnce()

    def Reset(self):
        """ 重进世界必须调：Item 实例会全部重建，扫出来的配方引用的是旧世界的对象 """
        self._queue.Clear()
        self._results = {}
        self._done = set()
        self._started = set()

    # 内部
# ======================================================================================================================
    def _MakeJob(self, category_id, item):  # type: (str, any) -> callable
        def _job():
            found = []
            for source in SourceRegistry.GetSources(category_id):
                if source.CAN_ENUMERATE:
                    # 能自报全量的来源不必逐个物品问，收尾时一次性并进来
                    continue
                found.extend(source.QueryByOutput(item))
            if found:
                self._results[category_id].extend(found)
        return _job

    def _MakeFinishJob(self, category_id, total):  # type: (str, int) -> callable
        def _finish():
            merged = list(self._results.get(category_id, ()))
            for source in SourceRegistry.GetSources(category_id):
                if source.CAN_ENUMERATE:
                    merged.extend(source.GetAll())
            # 一条配方有多个产物时会被扫到多次，按 Id 去重
            self._results[category_id] = dedupe(merged, key=recipe_id)
            self._done.add(category_id)
            logger.info("[MEI/scan] {} 扫描完成: {} 个物品 -> {} 条配方".format(
                category_id, total, len(self._results[category_id])))
        return _finish


RecipeScanner = __RecipeScanner()
