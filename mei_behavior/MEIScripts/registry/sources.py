# coding=utf-8

# ----------------------------------------------------------------------
#  sources.py is part of MoreEnoughItems.
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
配方类别与来源的注册表：category id 到 Category 与 [Source, ...] 的两张表。
"""
from collections import OrderedDict

from MEIScripts.common.classes.base import RecipeSource
from MEIScripts.common.classes.types import RecipeCategory
from MEIScripts.utils.log import logger


class __SourceRegistry(object):  # noqa
    """ 类别与来源注册表，构造期不碰引擎 """

    def __init__(self):
        # 必须有序：类别顺序即 TypeTab 的排列与默认选中项
        self.categories = OrderedDict()  # type: OrderedDict
        self.sources = {}  # type: dict

    # 类别
# ======================================================================================================================
    def RegisterCategory(self, category):  # type: (RecipeCategory) -> bool
        """
        注册一个配方类别，Id 重复则拒绝并记一行警告 —— **不能覆盖别人的类型**（包括原版的工作台、熔炉；extensions.md §9-3）
        """
        if not isinstance(category, RecipeCategory):
            return False
        if category.Id in self.categories:
            logger.warn("[MEI/registry] 类型 {} 已经注册过：同一个 Id 不能注册两次，也不能覆盖别人的类型".format(category.Id))
            return False
        self.categories[category.Id] = category
        self.sources.setdefault(category.Id, [])
        return True

    def UnRegisterCategory(self, category_id):  # type: (str) -> bool
        """ 反注册类别，连同它名下的全部来源 """
        if category_id not in self.categories:
            return False
        del self.categories[category_id]
        self.sources.pop(category_id, None)
        return True

    def GetCategory(self, category_id):  # type: (str) -> RecipeCategory or None
        return self.categories.get(category_id)

    def ListCategoryIds(self):  # type: () -> list
        """ 按 SortIndex 升序，同序时保持注册序 """
        # sorted 是稳定的，所以只按 SortIndex 排就能拿到「同权重按注册序」
        return [c.Id for c in sorted(self.categories.values(), key=lambda c: c.SortIndex)]

    # 来源
# ======================================================================================================================
    def RegisterSource(self, source):  # type: (RecipeSource) -> bool
        """ 把来源挂到它声明的类别下，同一实例不重复挂 """
        if not isinstance(source, RecipeSource):
            return False
        category_id = getattr(source, "CategoryId", "")
        if not category_id or category_id not in self.categories:
            logger.warn("[MEI/registry] 来源 {} 挂不上：类型 {!r} 还没注册（先 RegisterCategory 再 RegisterSource）".format(
                type(source).__name__, category_id))
            return False
        entries = self.sources.setdefault(category_id, [])
        if source in entries:
            return False
        entries.append(source)
        return True

    def UnRegisterSource(self, source):  # type: (RecipeSource) -> bool
        entries = self.sources.get(getattr(source, "CategoryId", ""), None)
        if not entries or source not in entries:
            return False
        entries.remove(source)
        return True

    def GetSources(self, category_id):  # type: (str) -> list
        """ 按注册序返回，查询结果的合并顺序由它决定 """
        return list(self.sources.get(category_id, ()))

    def Reset(self):
        self.categories = OrderedDict()
        self.sources = {}


SourceRegistry = __SourceRegistry()
