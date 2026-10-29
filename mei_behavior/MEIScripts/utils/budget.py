# coding=utf-8
# ----------------------------------------------------------------------
#  budget.py is part of MoreEnoughItems.
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
时间预算分帧队列 —— **纯逻辑, 零引擎依赖**, 时钟由构造注入.

为什么按时间而不按条数 (engineering.md §6):
  单次引擎调用的耗时不受控 —— 查一条工作台配方和查一条熔炉配方差一个量级,
  固定条数在低端机上必掉帧. 按预算切片才是稳的.

时钟注入的意义: 离线可用假时钟精确验证「预算耗尽即让出」, 不必真的睡。
"""
from .log import logger

import time
from MEIScripts.utils.text import error_text

DEFAULT_BUDGET_MS = 3.0
""" 每帧预算. engineering.md §6 建议 3~4ms 即让出 """


def _default_clock():  # type: () -> float
    """ 毫秒时钟 """
    return time.time() * 1000.0


class BudgetQueue(object):
    """
    每次 PumpOnce 处理到预算耗尽即让出, 剩余任务留在队列等下一帧.

    job 是无参可调用. **单个 job 抛异常不会中断整条队列** ——
    否则一条坏配方就能让整个索引构建停摆(引擎会吞异常, 现象是"索引永远建不完").
    """

    def __init__(self, budget_ms=DEFAULT_BUDGET_MS, clock=None, name="budget"):
        self.BudgetMs = float(budget_ms)
        self.Name = name
        self._clock = clock or _default_clock
        self._jobs = []
        self._cursor = 0
        self._errors = 0
        self._done = 0

    # 状态
# ======================================================================================================================
    def __len__(self):
        return len(self._jobs) - self._cursor

    def IsEmpty(self):  # type: () -> bool
        return len(self) <= 0

    def GetStats(self):  # type: () -> dict
        return {"pending": len(self), "done": self._done, "errors": self._errors}

    # 入队与执行
# ======================================================================================================================
    def Push(self, job):
        if not callable(job):
            raise TypeError("job must be callable")
        self._jobs.append(job)

    def Extend(self, jobs):
        for job in jobs:
            self.Push(job)

    def Clear(self):
        self._jobs = []
        self._cursor = 0

    def PumpOnce(self):  # type: () -> int
        """ 跑一帧的量, 返回本次处理的 job 数 """
        if self.IsEmpty():
            return 0

        started = self._clock()
        processed = 0
        while self._cursor < len(self._jobs):
            job = self._jobs[self._cursor]
            self._cursor += 1
            try:
                job()
                self._done += 1
            except Exception as e:  # noqa  一个 job 炸不能拖垮整条队列
                self._errors += 1
                logger.error("[MEI/{}] job 执行失败(已跳过): {}".format(self.Name, error_text(e)))
            processed += 1

            if self._clock() - started >= self.BudgetMs:
                break

        # 队列跑空后回收, 避免 _jobs 无限增长
        if self._cursor >= len(self._jobs):
            self._jobs = []
            self._cursor = 0

        return processed

    def PumpAll(self, max_frames=10000):  # type: (int) -> int
        """ 反复 Pump 直到跑空 (离线/测试用; **不要**在游戏帧内调) """
        total = 0
        for _ in range(max_frames):
            if self.IsEmpty():
                break
            total += self.PumpOnce()
        return total
