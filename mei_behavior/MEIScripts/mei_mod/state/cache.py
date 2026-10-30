# coding=utf-8
# ----------------------------------------------------------------------
#  cache.py is part of MoreEnoughItems.
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
from MEIScripts.utils import LRUCache, LRUHistory
# 注意: 这里原先 import 了 ui_script 侧的 PageWithGroup, 但它**只出现在 # type: 注释里**
# (类型注释是字符串, 不求值), 却让 state 层的 import 链拉起整个 UI 栈
# —— engineering.md §2 记的 state → ui 违例, 已删除.
# 若将来真需要类型标注, 走 .pyi 存根, 不要在运行时 import 上层.


class RecipeQueryCache(object):
    """
    配方查询结果缓存 —— 记住「引擎对**这个物品**答了什么」。

    **和反向索引在设计上是两回事**, 这点决定了 aux 会不会咬人:

      反向索引: 把配方**产物**拆成键装桶, 由我们**自己重新推导**哪条配方匹配哪个物品。
                于是 aux 成了匹配依据 —— 而引擎给的产物带的是方块态 data
                (箱子 data=2、活塞 data=1), 与物品表里的 aux(0) 对不上, 必然查空。
      本缓存:   只记结果, **不做任何匹配** —— 匹配引擎已经做完了。
                aux 在这里只用来**区分缓存条目**, 不参与判断"是不是同一个东西"。

    键为 (Item, query_by, types签名):
      · Item 的 __eq__/__hash__ 是**值语义**(ItemId + AuxValue + IsEnchanted +
        Attr + ExtraData), 所以附魔变体、不同 aux、带 UserData 的物品各占一条,
        不会互相串味 —— 这正是"严格校验 Item 是否相同"想要的效果。
      · types 会改变结果集合, 必须进键; None 与显式全集视为不同键(不做等价化,
        因为"全部类型"的集合会随注册变化)。

    两条硬规矩:
      ① **空结果不缓存**。一次因引擎未就绪/时序而返回的空, 若被记住就是永久的假阴性
         —— 比如记忆化把 done 记成"已扫", 之后再点都不查。
         重查一次空结果的代价远小于永久查不到。
      ② **返回副本**。调用方(UI)会对结果列表排序/裁剪, 直接给内部对象会被改脏。
    """

    __slots__ = ("_lru", "Hits", "Misses", "Skipped")

    def __init__(self, maxsize=256):
        self._lru = LRUCache(maxsize=maxsize)
        self.Hits = 0
        self.Misses = 0
        self.Skipped = 0   # 因结果为空而**未**写入的次数

    @staticmethod
    def MakeKey(item, query_by, types=None):
        """ types 归一化为可哈希且与顺序无关的签名 """
        sig = tuple(sorted(types)) if types else None
        return item, query_by, sig

    def Get(self, item, query_by, types=None):
        """ 命中返回结果的**副本**; 未命中返回 None """
        cached = self._lru.get(self.MakeKey(item, query_by, types))
        if cached is None:
            self.Misses += 1
            return None
        self.Hits += 1
        return self._copy(cached)

    def Put(self, item, query_by, result, types=None):
        """ 写入. **空结果不写** —— 见类文档的硬规矩 ① """
        if not result:
            self.Skipped += 1
            return False
        self._lru.put(self.MakeKey(item, query_by, types), self._copy(result))
        return True

    @staticmethod
    def _copy(result):
        """ 外层 dict 与内层 list 都复制一层; Recipe 对象本身共享(不可变地用) """
        # 用 result.__class__ 而非 dict()，否则 OrderedDict 进来会被拍平成无序，
        # 而类型顺序就是 TypeTab 的排列顺序
        return result.__class__(
            (type_id, list(recipes)) for type_id, recipes in result.items()
        )

    def Clear(self):
        """ 重进世界必须调 —— 物品对象会重建, 配方也可能变 """
        self._lru.clear()
        self.Hits = 0
        self.Misses = 0
        self.Skipped = 0

    def GetStats(self):  # type: () -> dict
        return {
            "size": len(self._lru),
            "hits": self.Hits,
            "misses": self.Misses,
            "skipped_empty": self.Skipped,
        }


class RecipeNav(object):
    """
    配方页的返回栈。

    **和 HISTORY_KEY 不是一回事**: 那个是侧边栏的"最近浏览过什么"
    (消费者 items_sidebar/script.py), 这个是"返回键该去哪"。

    去重靠 LRUHistory: 同一个 (item, query_by) 再次入栈时是**移动**而不是**追加**。
    没有它, 来回点两个物品 A→B→A→B… 会把栈无限撑大;
    有了它栈稳定在 2。再加上 Go() 的同页短路, 就不会出现
    "按返回键停在同一页"这种空按。
    """
    __slots__ = ("_stack", "Current")

    def __init__(self, maxsize):
        self._stack = LRUHistory(maxsize=maxsize)
        self.Current = None  # type: tuple or None   # (item, query_by)

    def Go(self, entry):  # type: (tuple) -> bool
        """
        前进到 entry, 把当前页压栈。

        返回 False 表示**本来就在这一页**, 调用方应当整个跳过(别入栈也别重渲染) ——
        点配方的产出格就会撞上这条, 它查的正是你正在看的那个物品。
        """
        if entry == self.Current:
            return False
        if self.Current is not None:
            self._stack.add(self.Current)
        self.Current = entry
        return True

    def Pop(self):  # type: () -> tuple or None
        """ 弹出上一页(不改 Current —— 渲染成功后由调用方 SetCurrent 确认) """
        return self._stack.pop()

    def SetCurrent(self, entry):
        self.Current = entry

    def Reset(self):
        self._stack = LRUHistory(maxsize=self._stack.maxsize)
        self.Current = None

    def Depth(self):  # type: () -> int
        return len(self._stack)


class __CacheManager(object):
    HISTORY_KEY = "history"
    ITEMS_PAGE_KEY = "items_page"
    SEARCH_DATA_KEY = "search_data"
    RECIPE_NAV_KEY = "recipe_nav"
    RECIPE_QUERY_KEY = "recipe_query"
    MaxHistorySize = 100
    MaxNavSize = 32
    MaxRecipeQuerySize = 256
    """ 缓存的查询条数上限. 一条 = 一个 (物品, 方向, 类型集) 组合的结果 """

    def __init__(self):
        self.cache = {}
        self.InitCache()

    def InitCache(self):
        self.cache[self.HISTORY_KEY] = LRUHistory(maxsize=self.MaxHistorySize)
        self.cache[self.ITEMS_PAGE_KEY] = None
        self.cache[self.SEARCH_DATA_KEY] = None
        self.cache[self.RECIPE_NAV_KEY] = RecipeNav(maxsize=self.MaxNavSize)
        self.cache[self.RECIPE_QUERY_KEY] = RecipeQueryCache(maxsize=self.MaxRecipeQuerySize)

    def clear(self):
        self.cache = {}
        self.InitCache()

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value

    def AddHistory(self, item):
        history_list = self.get(self.HISTORY_KEY)  # type: LRUHistory
        history_list.add(item)
        return True

    def GetHistory(self):
        history_list = self.get(self.HISTORY_KEY)  # type: LRUHistory
        return history_list.to_list()

    def CacheItemsPage(self, page):  # type: (PageWithGroup) -> None
        """ 缓存物品分页，连同当时的物品表版本一起存 """
        from MEIScripts.registry import ItemManager
        return self.set(self.ITEMS_PAGE_KEY, (ItemManager.Version(), page))

    def GetItemsPage(self):  # type: () -> PageWithGroup or None
        """ 取物品分页；物品表变过就当没有，让调用方重建 """
        # 分页是按 Item 实例建的, 物品表一变(加变体/改隐藏)它就是旧世界的东西.
        # registry 不能反过来通知 state, 所以由这边拿版本号比对 —— 拉模型
        from MEIScripts.registry import ItemManager
        cached = self.get(self.ITEMS_PAGE_KEY)
        if not cached or cached[0] != ItemManager.Version():
            return None
        return cached[1]

    def CacheSearchData(self, keyword, result_page):  # type: (str, PageWithGroup) -> None
        """ 缓存搜索的结果页，连同当时的物品表版本一起存（同 CacheItemsPage）"""
        from MEIScripts.registry import ItemManager
        return self.set(self.SEARCH_DATA_KEY, (ItemManager.Version(), keyword, result_page))

    def GetSearchData(self):  # type: () -> (str, PageWithGroup) or None
        """ (搜索字, 结果页)；物品表变过（加了变体、换了世界）就当没有 —— 结果页里是旧的 Item 实例 """
        from MEIScripts.registry import ItemManager
        cached = self.get(self.SEARCH_DATA_KEY)
        if not cached or cached[0] != ItemManager.Version():
            return None
        return cached[1], cached[2]

    def ClearSearchData(self):
        return self.set(self.SEARCH_DATA_KEY, None)

    def ResetWorld(self):
        """
        进世界（SyncLoadedItems）时调：上一个世界的 Item / Recipe 实例全作废 —— 最近浏览、物品栏的分页、搜索结果页、
        配方页的返回栈、配方查询缓存一起清（物品表、扩展、配方都可能换了；值语义的旧 Item 还能「匹配上」新世界的物品，
        最近浏览里会留着新世界没有的东西、配方页的「返回」会回到上一个世界的配方）。返回栈与查询缓存原地清，持有它们的不用换
        """
        self.set(self.HISTORY_KEY, LRUHistory(maxsize=self.MaxHistorySize))
        self.set(self.ITEMS_PAGE_KEY, None)
        self.set(self.SEARCH_DATA_KEY, None)
        self.GetRecipeNav().Reset()
        self.GetRecipeQueryCache().Clear()

    def GetRecipeNav(self):  # type: () -> RecipeNav
        return self.get(self.RECIPE_NAV_KEY)

    def GetRecipeQueryCache(self):  # type: () -> RecipeQueryCache
        return self.get(self.RECIPE_QUERY_KEY)

CacheManager = __CacheManager()

