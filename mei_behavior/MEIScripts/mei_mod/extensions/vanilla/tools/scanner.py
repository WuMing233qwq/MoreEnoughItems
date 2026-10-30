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
全量配方的分帧扫描器：**有人要某个类型的全表时才扫**（EngineRecipeSource.GetAll，查工作站的用途就是要全表）。

它存在的唯一理由是**引擎不给枚举接口**（GetRecipesBy* 必须带 tag、只能逐个物品问，CLAUDE.md 引擎结论 §43），
所以它属于本扩展而不是框架：自建表的来源（CAN_ENUMERATE）知道自己有哪些配方，根本用不上它。

- **一个类型一趟**：按物品表逐个问这个类型的引擎来源（多数按产物问；锻造台按原料问 —— 纹饰配方没有产物，见 SCAN_BY），
  问到的配方按 Id 去重收进这个类型的全表。问的时候走来源自己的查询，引擎的答案由来源记下（tools/answers.py）：
  平时查过的物品这里不再问引擎，扫过的物品以后再查也不问。
- **不在进存档时扫**：游戏有动态注册配方的接口，开局扫了，以后为了兼容只能每加一条配方就整个作废重扫，反而更费；有人要才扫，作废了也只是下次要时再扫。
- 要全表的类型插到最前、那几帧多给时间（Request(urgent=True)）。
- 每帧按时间预算推进；一格问出错只少这一格（同一个来源只记第一次，扫完的汇总里有次数）。
- 排着的都扫完记一行汇总：每个类型多少条、问了几次（其中真问引擎几次）、一共多少毫秒、从开始到扫完多久。

不用 BudgetQueue：它是先进先出的，排好的任务插不了队；这里的「任务」是每个类型一个游标，插队就是挪一下队列里的类型。
物品表在第一次推进时才取；来源在这个类型开扫时才取（别的扩展可能在 OnReady 里才挂来源）。
重进世界必须 Reset：扫出来的配方与记下的答案引用的是旧世界的 Item 实例。
"""
import time

from MEIScripts.api.facades.registry import ItemManager, SourceRegistry
from MEIScripts.api.facades.utils import error_text, logger, recipe_id

from .answers import INPUT, OUTPUT, EngineAnswers

BUDGET_MS = 3.0
""" 每帧预算（毫秒），与 engineering.md §6 的建议一致 """

URGENT_BUDGET_MS = 10.0
""" 有人在等某个类型的全表时每帧的预算：这时多半是配方页开着、玩家正看着「扫描中」，早扫完一秒是一秒 """


def _clock():  # type: () -> float
    """ 毫秒时钟 """
    return time.time() * 1000.0


def scan_direction(source):  # type: (any) -> str
    """ 扫描时按哪个方向问这个来源：看它的 SCAN_BY，缺省按产物 """
    return INPUT if getattr(source, "SCAN_BY", OUTPUT) == INPUT else OUTPUT


class _Pass(object):
    """ 一个类型的一趟扫描：游标之前的物品都问过了 """

    __slots__ = ("CategoryId", "Sources", "Cursor", "Recipes", "Seen", "Queries", "Spent")

    def __init__(self, category_id):  # type: (str) -> None
        self.CategoryId = category_id
        self.Sources = None  # type: list or None  # 开扫时这个类型里不能自报全量的来源；还没开扫是 None
        self.Cursor = 0  # type: int  # 物品表里下一个要问的下标
        self.Recipes = []  # type: list  # 扫到的配方，按扫到的先后，已按 Id 去重
        self.Seen = set()  # type: set  # 收过的配方 Id
        self.Queries = 0  # type: int  # 问了几次（一个物品问几个来源算几次；记下过的不问引擎，也算在里面）
        self.Spent = 0.0  # type: float  # 问（含解析）一共多少毫秒


class __RecipeScanner(object):  # noqa
    """ 按类型扫描全量配方，构造期不碰引擎也不扫任何东西 """

    def __init__(self, clock=None):
        self._clock = clock or _clock
        self._items = None  # type: list or None  # 扫的物品表（第一次推进时取）
        self._passes = {}  # type: dict  # category_id -> _Pass（排过的都在，扫完的也在）
        self._queue = []  # type: list  # 还没扫完的类型，最前面的正在扫
        self._done = set()  # type: set
        self._urgent = set()  # type: set  # 有人在等的类型：它们没扫完之前每帧用 URGENT_BUDGET_MS
        self._warned = set()  # type: set  # 记过错误日志的来源类名
        self._errors = 0  # type: int
        self._began = None  # type: float or None  # 这一批从哪一刻开始推进（汇总里的「从开始到扫完」）
        self._asked = 0  # type: int  # 这一批开始时引擎已经被问过几次（汇总里算这一批真问了几次）
        self._finished = []  # type: list  # 这一批里扫完的，等汇总

    # 查询
# ======================================================================================================================
    def IsDone(self, category_id):  # type: (str) -> bool
        """ 该类别是否已扫完；没要过全表（没开始）也算未完成 """
        return category_id in self._done

    def IsScanning(self, category_id):  # type: (str) -> bool
        return category_id in self._passes and category_id not in self._done

    def GetRecipes(self, category_id):  # type: (str) -> list
        """ 已扫到的配方；扫描中返回的是**部分结果**，配合 IsDone 用 """
        scan = self._passes.get(category_id)
        return list(scan.Recipes) if scan is not None else []

    def GetStats(self):  # type: () -> dict
        total = len(self._items or ())
        return {
            "pending": sum(total - self._passes[category_id].Cursor for category_id in self._queue),
            "done": len(self._done),
            "errors": self._errors,
            "categories": len(self._passes),
            "completed": len(self._done),
            "queries": sum(scan.Queries for scan in self._passes.values()),
        }

    # 驱动
# ======================================================================================================================
    def Request(self, category_id, urgent=False):  # type: (str, bool) -> bool
        """
        请求扫一个类型：没排过就排到队尾（urgent 插到最前）；已经排着的，urgent 也会把它提到最前。
        扫完的、没注册的不排。**不同步扫** —— 只排队，Pump 才问。返回这一次是不是新排进去的
        """
        if not category_id or category_id in self._done:
            return False
        if category_id in self._passes:
            if urgent:
                self._Promote(category_id)
            return False
        if SourceRegistry.GetCategory(category_id) is None:
            logger.warn("[MEI/scan] 类别 {} 未注册, 不扫".format(category_id))
            return False
        self._passes[category_id] = _Pass(category_id)
        self._queue.append(category_id)
        if urgent:
            self._Promote(category_id)
        return True

    def Pump(self):  # type: () -> int
        """ 推进一帧，由扩展的 OnTick 调；返回这一帧问了几个物品，队列空时立即返回 0 """
        if not self._queue:
            return 0
        if self._items is None:
            self._items = list(ItemManager.GetItems() or ())
            if not self._items:
                # 物品表还没建好就开扫：排着的全判完成（全表是空的），留给下一次 Reset 之后重来
                logger.warn("[MEI/scan] 物品表为空, 排着的 {} 个类型判为扫完".format(len(self._queue)))
        started = self._clock()
        if self._began is None:
            self._began, self._asked = started, EngineAnswers.Asked
        budget = URGENT_BUDGET_MS if self._urgent else BUDGET_MS
        processed = 0
        while self._queue:
            scan = self._passes[self._queue[0]]
            if scan.Sources is None:
                scan.Sources = [source for source in SourceRegistry.GetSources(scan.CategoryId)
                                if not getattr(source, "CAN_ENUMERATE", False)]
            if not scan.Sources or scan.Cursor >= len(self._items):
                self._Finish(scan)
                continue
            self._Step(scan, self._items[scan.Cursor])
            scan.Cursor += 1
            processed += 1
            if self._clock() - started >= budget:
                break
        if not self._queue:
            self._Report()
        return processed

    def Reset(self):
        """
        扫描结果与记下的引擎答案一起作废（tools/answers.py）。重进世界必须调：Item 实例会全部重建，扫出来的配方引用的是旧世界的对象；
        以后要兼容游戏中途动态注册的配方，也是调这一个（有人再要全表时重扫）
        """
        self._items = None
        self._passes = {}
        self._queue = []
        self._done = set()
        self._urgent = set()
        self._warned = set()
        self._errors = 0
        self._began = None
        self._asked = 0
        self._finished = []
        EngineAnswers.Clear()

    # 内部
# ======================================================================================================================
    def _Promote(self, category_id):
        """ 插到最前；扫到一半的接着它的游标扫 """
        if category_id in self._queue:
            self._queue.remove(category_id)
            self._queue.insert(0, category_id)
            self._urgent.add(category_id)

    def _Step(self, scan, item):  # type: (_Pass, any) -> None
        """ 问一个物品：这个类型的每个来源各问一次（来源记下过的不问引擎），配方收进全表 """
        for source in scan.Sources:
            direction = scan_direction(source)
            began = self._clock()
            failed = None
            try:
                found = source.QueryByInput(item) if direction == INPUT else source.QueryByOutput(item)
            except Exception as e:  # noqa  一个物品问炸了只少这一格，不能让整趟扫描停下
                found, failed = None, e
            scan.Queries += 1
            scan.Spent += self._clock() - began
            if failed is not None:
                self._Fail(source, item, failed)
                continue
            for recipe in found or ():
                marker = recipe_id(recipe)
                if marker is not None:
                    # 同一条配方会被问到好几次（多个产物、按原料扫时每样原料各一次）
                    if marker in scan.Seen:
                        continue
                    scan.Seen.add(marker)
                scan.Recipes.append(recipe)

    def _Fail(self, source, item, error):
        self._errors += 1
        name = type(source).__name__
        if name not in self._warned:
            self._warned.add(name)
            logger.error("[MEI/scan] {} 问 {} 时出错（这个来源之后的错只计数）: {}".format(
                name, getattr(item, "ItemId", "?"), error_text(error)))

    def _Finish(self, scan):  # type: (_Pass) -> None
        if scan.CategoryId in self._queue:
            self._queue.remove(scan.CategoryId)
        self._urgent.discard(scan.CategoryId)
        self._done.add(scan.CategoryId)
        self._finished.append(scan)

    def _Report(self):
        """ 这一批扫完：一行汇总；没有要扫的来源的类型（酿造、燃料自己有全表）不写 """
        finished, self._finished = [scan for scan in self._finished if scan.Sources], []
        began, self._began = self._began, None
        if not finished:
            return
        queries = sum(scan.Queries for scan in finished)
        spent = sum(scan.Spent for scan in finished)
        elapsed = (self._clock() - began) / 1000.0 if began is not None else 0.0
        counts = ", ".join("{} {}".format(scan.CategoryId, len(scan.Recipes)) for scan in finished)
        logger.info("[MEI/scan] 全量配方扫描完成: {}；{} 个物品，问了 {} 次（其中问引擎 {} 次，别的之前查过；出错 {} 次），共 {} 毫秒，"
                    "从开始到扫完 {:.1f} 秒".format(counts, len(self._items or ()), queries, EngineAnswers.Asked - self._asked,
                                                self._errors, int(spent), elapsed))


RecipeScanner = __RecipeScanner()
