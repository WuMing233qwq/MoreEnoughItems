# coding=utf-8

# ----------------------------------------------------------------------
#  recipes.py is part of MoreEnoughItems.
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
from collections import OrderedDict

from mod_log import logger

from MEIScripts.common.classes.base import BaseRecipeUIScript, RecipeSource
from MEIScripts.common.classes.types import Item
from MEIScripts.constants.codes import QueryConst
from MEIScripts.utils.lang import localize
from MEIScripts.utils.sequence import dedupe, recipe_id
from MEIScripts.utils.text import error_text

from .sources import SourceRegistry

FALLBACK_ICON = ("minecraft:book", 0)
""" 类型既没声明图标、也没有工作站时 TypeTab 上画的 """


def _builds_full_list(source):  # type: (RecipeSource) -> bool
    """ 这个来源会不会凑出全表：能自报全量的会；覆写了 IsAllComplete 的是边扫边给（引擎来源靠扫描）；两样都不是的给不出 """
    if getattr(source, "CAN_ENUMERATE", False):
        return True
    own = getattr(type(source), "IsAllComplete", None)
    base = RecipeSource.IsAllComplete
    # 比底下的函数对象：py2 的 unbound method 每次取属性都是新的包装，拿 is 比恒为假
    return getattr(own, "__func__", own) is not getattr(base, "__func__", base)


class __RecipeManager(object):  # noqa
    """ 配方查询编排：按类别取来源、合并、去重、缓存 """

    def __init__(self):
        self._query_cache = None  # type: any

    def SetQueryCache(self, cache):
        """ 注入查询缓存(装配层调用), 传 None 即关闭缓存 """
        # 为什么是注入不是 import: 缓存归属 state 层而本模块在 registry 层,
        # registry import state 是反向边(engineering.md §2, probe_layering 守着)
        self._query_cache = cache

    # 类别元信息，转发给 SourceRegistry
# ======================================================================================================================
    @staticmethod
    def GetAllCraftingTypes():  # type: () -> list
        """ 全部类别 id，按 SortIndex 排序 """
        return SourceRegistry.ListCategoryIds()

    @staticmethod
    def GetCategory(crafting_type):  # type: (str) -> any
        return SourceRegistry.GetCategory(crafting_type)

    @staticmethod
    def GetDisplayText(crafting_type):  # type: (str) -> unicode
        """
        类别显示名的**文字**（本地化键查成字，utils/lang.py）。界面上写类型名一律用它 —— 配方页顶上、tooltip 的配方预览、
        配方树的标题与菜单都是这一个函数、这一份缓存，别处不另记名字表（要键就看 GetCategory(...).NameKey）
        """
        category = SourceRegistry.GetCategory(crafting_type)
        return localize(category.NameKey if category else crafting_type)

    @staticmethod
    def GetDisplayItemData(crafting_type):  # type: (str) -> tuple or None
        """
        类别 tab 图标 (ItemId, AuxValue)：类型自己声明的；没声明（RecipeCategory 的 icon 缺省是 None）用第一个工作站，
        再没有用一本书 —— 给 None 的话这个类型进不了 TypeTab：内容是它、亮着的却是别的类型，也点不回它
        """
        category = SourceRegistry.GetCategory(crafting_type)
        if category is None:
            return None
        if category.Icon:
            return category.Icon
        for stack in getattr(category, "Stations", None) or ():
            item = getattr(stack, "Item", None)
            if item is not None:
                return item.ItemId, item.AuxValue
        return FALLBACK_ICON

    @staticmethod
    def GetControlDef(crafting_type):  # type: (str) -> str or None
        """ 配方页控件定义名，JSON UI 的 namespace.control_name """
        category = SourceRegistry.GetCategory(crafting_type)
        return category.ControlDef if category else None

    @staticmethod
    def GetPreviewDef(crafting_type):  # type: (str) -> str or None
        """ tooltip 配方预览用的 grid 定义名；类型没声明（或类型不存在）给 None """
        category = SourceRegistry.GetCategory(crafting_type)
        return (getattr(category, "PreviewDef", "") or None) if category else None

    @staticmethod
    def GetCraftingStations(crafting_type):  # type: (str) -> list
        """ 工作站 ItemStack 列表 """
        # 直通: 解析已经移到类别声明期(RecipeCategory.Stations 直接收 ItemStack).
        # 这里在切配方类型的 UI 路径上, 原先每切一次就重造一遍全部工作站物品
        category = SourceRegistry.GetCategory(crafting_type)
        return category.Stations if category else []

    # 查询
# ======================================================================================================================
    def QueryRecipe(self, item, query_by="output", types=None):
        # type: (Item, str, list or None) -> OrderedDict
        """ 入口统一用 Item 传参，按类别聚合查询；命中缓存直接返回。查工作站的用途带上它服务的类型的全部配方（QueryRecipeFull）"""
        return self.QueryRecipeFull(item, query_by, types)[0]

    def QueryRecipeFull(self, item, query_by="output", types=None):
        # type: (Item, str, list or None) -> tuple
        """
        按类别聚合查询，返回 (结果, 还没凑齐全表的类型集合)。

        **查工作站的用途**（query_by="input"，物品在某些类型的 RecipeCategory.Stations 里）：这些类型排在最前，
        每个类型里先是真用到它的配方，后面接这个类型的全部配方（QueryAll）—— JEI / EMI 查工作台的用途就是整个合成表。
        全表要靠来源自己凑（引擎来源靠分帧扫描），还在凑的类型（IsCategoryBuilding）进第二个返回值：这样的结果**不进查询缓存**，
        凑齐后再查一次就全了。别的查询第二个返回值恒为空。
        """
        if not isinstance(item, Item):
            return OrderedDict(), set()

        cache = self._query_cache
        if cache is not None:
            hit = cache.Get(item, query_by, types)
            if hit is not None:
                return hit, set()

        if query_by not in (QueryConst.Output, QueryConst.Input):
            raise TypeError("Invalid query_by")

        result = OrderedDict()
        pending = set()
        # **不要重绑定 types** —— 它要原样用作缓存键. 展开成全集后再回写,
        # Get(None) 与 Put(全集) 的键就永远对不上了.
        wanted = types if types else self.GetAllCraftingTypes()
        stations = self.StationCategories(item, wanted) if query_by == QueryConst.Input else []

        for category_id in stations + [one for one in wanted if one not in stations]:
            recipes = self._QueryCategory(category_id, item, query_by)
            if category_id in stations:
                everything, _complete = self.QueryAll(category_id)
                if self.IsCategoryBuilding(category_id):
                    pending.add(category_id)
                recipes = dedupe(recipes + everything, key=recipe_id)
            if recipes:
                result[category_id] = recipes

        if cache is not None and not pending:
            cache.Put(item, query_by, result, types)
        return result, pending

    @staticmethod
    def StationCategories(item, wanted=None):  # type: (Item, list or None) -> list
        """ 这个物品是哪些类型的工作站（按 SortIndex）；给了 wanted 就只要其中的 """
        found = SourceRegistry.FindCategoriesByStation(item)
        return [category_id for category_id in found if wanted is None or category_id in wanted]

    def PendingCategories(self, item, query_by):  # type: (Item, str) -> list
        """
        查这个物品时哪些类型的全表还在凑：只有查工作站的用途才会有（它服务的类型还在扫）。
        不碰引擎、不排扫描（IsCategoryBuilding），配方页拿它决定写不写「扫描中」、凑齐了要不要刷新
        """
        if query_by != QueryConst.Input or not isinstance(item, Item):
            return []
        return [category_id for category_id in self.StationCategories(item) if self.IsCategoryBuilding(category_id)]

    @staticmethod
    def IsCategoryBuilding(category_id):  # type: (str) -> bool
        """
        这个类型的全表还在凑没有：有来源会凑出全表（能自报全量的，或覆写了 IsAllComplete、边扫边给的）而它的 IsAllComplete 还是假。
        给不出全表的来源（不能自报全量、也没覆写 IsAllComplete）不算在凑 —— 它永远凑不齐，等它就是一直「扫描中」，
        它的配方只在真用到这个物品时出现。来源炸了也不算在凑（免得一直等下去）。不碰引擎、不排扫描
        """
        for source in SourceRegistry.GetSources(category_id):
            try:
                if _builds_full_list(source) and not source.IsAllComplete():
                    return True
            except Exception as e:  # noqa
                logger.error("[MEI/query] 类别 {} 的来源 {} 报不出全表凑齐没有: {}".format(
                    category_id, type(source).__name__, error_text(e)))
        return False

    @staticmethod
    def QueryAll(category_id):  # type: (str) -> tuple
        """ 一个类别的全部配方，返回 (配方表, 是否完整) """
        # 「怎么凑出全量」是各来源自己的事: 自建表直接给, 引擎源得靠扫描分帧凑,
        # 后者扫完之前 IsAllComplete 为假。本层只负责合并、去重、与算总的完整性。
        merged = []
        complete = True
        for source in SourceRegistry.GetSources(category_id):
            try:
                merged.extend(source.GetAll())
                complete = complete and source.IsAllComplete()
            except Exception as e:  # noqa  一个来源炸了不该让整次查询失败
                complete = False
                logger.error("[MEI/query] 类别 {} 的来源 {} 取全量失败: {}".format(
                    category_id, type(source).__name__, error_text(e)))
        return dedupe(merged, key=recipe_id), complete

    def QueryRecipeEx(self, item, query_by="output", types=None):
        # type: (Item, str, list or None) -> tuple
        """ 同 QueryRecipe, 多返回一个「结果是否完整」标志：查工作站的用途时，它服务的类型还没凑齐全表就是不完整 """
        result, pending = self.QueryRecipeFull(item, query_by, types)
        return result, not pending

    @staticmethod
    def _QueryCategory(category_id, item, query_by):  # type: (str, Item, str) -> list
        """ 一个类别下全部来源的结果合并去重 """
        # 去重放在合并点：同一条配方可能同时来自引擎源与自定义源
        merged = []
        for source in SourceRegistry.GetSources(category_id):
            try:
                if query_by == QueryConst.Output:
                    merged.extend(source.QueryByOutput(item))
                else:
                    merged.extend(source.QueryByInput(item))
            except Exception as e:  # noqa  一个来源炸了不该让整次查询失败
                logger.error("[MEI/query] 类别 {} 的来源 {} 查询失败: {}".format(
                    category_id, type(source).__name__, error_text(e)))
        return dedupe(merged, key=recipe_id)

class __RecipeUIManager(object):  # noqa
    """ 配方页脚本表，键是类别 id """

    def __init__(self):
        self.scripts = {}  # type: dict

    def RegisterScript(self, category_id, script, params=None):
        """ 注册一个 RecipeUIScript """
        # 键从前是 script.TYPE、第一个参数却叫 control_def，看着像键其实不是；
        # Category 化之后类别 id 显式传入，控件定义名退回 RecipeCategory.ControlDef
        if not isinstance(script, type):
            return False
        if not issubclass(script, BaseRecipeUIScript):
            return False
        if not category_id:
            return False
        if category_id in self.scripts:
            logger.warn("[MEI/registry] 类型 {} 的配方页脚本已经注册过：不能覆盖别人的配方页".format(category_id))
            return False

        self.scripts[category_id] = (script, params if params else {})
        return True

    def UnRegisterScript(self, category_id):  # type: (str) -> bool
        """ 反注册一个 RecipeUIScript """
        if category_id in self.scripts:
            del self.scripts[category_id]
            return True
        return False

    def GetScriptData(self, category_id):  # type: (str) -> tuple or None
        """ (脚本类, 参数)；控件定义名走 RecipeManager.GetControlDef """
        return self.scripts.get(category_id)

RecipeManager = __RecipeManager()

RecipeUIManager = __RecipeUIManager()
