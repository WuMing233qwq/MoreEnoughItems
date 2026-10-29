# ----------------------------------------------------------------------
#  cache.pyi is part of MoreEnoughItems.
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
# 这个存根**存在的理由**就是 PageWithGroup:
# cache.py 运行期不能 import ui_script(state -> ui 是反向边),
# 但类型上它确实持有 PageWithGroup. 存根不被执行, 在这里 import 零运行期代价 ——
# 这正是 engineering.md 里「类型需要上层, 运行期不需要」该走存根的那条规则.
from typing import Any, Dict, List, Optional, Tuple

from MEIScripts.common.classes.types import Item, Recipe
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.modules.page import PageWithGroup
from MEIScripts.utils.history import LRUCache, LRUHistory

# 导航栈的一格: (物品, 查询方向)
NavEntry = Tuple[Item, str]

# 查询缓存的键: (物品, 查询方向, 类型过滤签名)
QueryKey = Tuple[Item, str, Optional[Tuple[str, ...]]]

# 查询结果: {crafting_type: [Recipe, ...]}
QueryResult = Dict[str, List[Recipe]]


class RecipeQueryCache(object):
    """ 配方查询结果记忆化. 键含 Item 本身(值相等语义), 故 aux/附魔变体互不串味 """

    _cache: LRUCache
    Hits: int
    Misses: int

    def __init__(self, maxsize: int = 256): ...

    @staticmethod
    def MakeKey(item: Item, query_by: str, types: Optional[List[str]] = None) -> QueryKey: ...

    def Get(self, item: Item, query_by: str,
            types: Optional[List[str]] = None) -> Optional[QueryResult]: ...

    def Put(self, item: Item, query_by: str, result: QueryResult,
            types: Optional[List[str]] = None) -> bool: ...

    def Clear(self) -> None: ...

    def GetStats(self) -> Dict[str, Any]: ...


class RecipeNav(object):
    """ 配方页的返回栈. 与侧边栏的"最近浏览"(HISTORY_KEY)不是一回事 """

    _stack: LRUHistory
    Current: Optional[NavEntry]

    def __init__(self, maxsize: int): ...

    def Go(self, entry: NavEntry) -> bool: ...

    def Pop(self) -> Optional[NavEntry]: ...

    def SetCurrent(self, entry: Optional[NavEntry]) -> None: ...

    def Reset(self) -> None: ...

    def Depth(self) -> int: ...


class __CacheManager(object):
    HISTORY_KEY: str
    ITEMS_PAGE_KEY: str
    SEARCH_DATA_KEY: str
    RECIPE_NAV_KEY: str
    RECIPE_QUERY_KEY: str
    MaxHistorySize: int
    MaxNavSize: int

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    def InitCache(self) -> None: ...

    def clear(self) -> None: ...

    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...

    def AddHistory(self, item: Item) -> bool: ...

    def GetHistory(self) -> List[Item]: ...

    def CacheItemsPage(self, page: PageWithGroup) -> None: ...

    def GetItemsPage(self) -> Optional[PageWithGroup]: ...

    def CacheSearchData(self, keyword: str, result_page: PageWithGroup) -> None: ...

    def GetSearchData(self) -> Optional[Tuple[str, PageWithGroup]]: ...

    def ClearSearchData(self) -> None: ...

    def GetRecipeNav(self) -> RecipeNav: ...

    def GetRecipeQueryCache(self) -> RecipeQueryCache: ...


CacheManager: __CacheManager
