# coding=utf-8

# ----------------------------------------------------------------------
#  organizer.py is part of MoreEnoughItems.
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

from MEIScripts.common.classes.types import Item


def _touch():
    """
    归属变了（组、分类的增删、成员、组名）：撞物品表的版本 —— 物品栏的分页按它自愈。
    展开 / 收起不算（界面自己当场重排，撞版本会让搜索索引白重建一次）。惰性 import：免得和 items 互相 import
    """
    from .items import ItemManager
    ItemManager.Touch()


class ItemCategory(object):
    """
    对物品的分类进行管理的类型
    """
    def __init__(self):
        self.categories = OrderedDict()  # type: OrderedDict

    def GetAllCategories(self):
        return self.categories

    def AddCategory(self, category):  # type: (str) -> bool
        """ 添加一个分类 """
        if category in self.categories:
            return False
        self.categories[category] = set()
        _touch()
        return True

    def RemoveCategory(self, category):  # type: (str) -> bool
        """ 撤掉一个分类（扩展 OnUnload 用）；没有返回 False """
        if category not in self.categories:
            return False
        del self.categories[category]
        _touch()
        return True

    def AddCategoryItem(self, category, item):
        """ 为分类添加一个物品 """
        if category in self.categories:
            self.categories[category].add(item)
            _touch()
            return True
        return False

class ItemGroup(object):
    """
    对物品的分组进行管理的类型
    """
    def __init__(self):
        self.item_groups = OrderedDict()  # type: OrderedDict

    def GetAllGroups(self):
        return self.item_groups

    def AddGroup(self, group, name=""):  # type: (str, str) -> bool
        """ 添加一个物品组 """
        if group in self.item_groups:
            return False
        self.item_groups[group] = {
            "Name": name if name else group,
            "Items": set(),
            "Order": [],  # 物品 id，按加进来的顺序（GetGroupOrder）
            "Expand": False,
        }
        _touch()
        return True

    def RemoveGroup(self, group):  # type: (str) -> bool
        """ 撤掉一个物品组（扩展 OnUnload 用）；没有返回 False """
        if group not in self.item_groups:
            return False
        del self.item_groups[group]
        _touch()
        return True

    def SetGroupName(self, group, name):  # type: (str, str) -> bool
        """ 设置一个分组的名称 """
        if group not in self.item_groups:
            return False
        self.item_groups[group]["Name"] = name
        _touch()
        return True

    def AddGroupItem(self, group, item_id):  # type: (str, str) -> bool
        """ 往组内添加一个新物品，存的是 **id 不是 Item** """
        # 存 id, 免得组表持有 Item 实例:
        # 归属关系是旁表, 旁表不该抓着池对象不放(item_model.md §6.3)
        if group not in self.item_groups:
            return False
        entry = self.item_groups[group]
        if item_id not in entry["Items"]:
            entry["Items"].add(item_id)
            entry["Order"].append(item_id)
            _touch()
        return True

    def RemoveGroupItem(self, group, item_id):  # type: (str, str) -> bool
        """
        从组里撤掉一样（往别人的组里加过东西的扩展 OnUnload 用：原版的锭、粗矿这类组不是它的，撤不掉整个）；
        组不在、本来就没有给 False
        """
        if group not in self.item_groups:
            return False
        entry = self.item_groups[group]
        if item_id not in entry["Items"]:
            return False
        entry["Items"].discard(item_id)
        if item_id in entry["Order"]:
            entry["Order"].remove(item_id)
        _touch()
        return True

    def SetGroupExpand(self, group, expand):  # type: (str, bool) -> bool
        """ 设置组是否展开 """
        if group not in self.item_groups:
            return False
        self.item_groups[group]["Expand"] = expand
        return True

    def ToggleGroupExpand(self, group):  # type: (str) -> bool
        """ 切换组展开状态 """
        if group not in self.item_groups:
            return False
        self.item_groups[group]["Expand"] = not self.item_groups[group]["Expand"]
        return self.item_groups[group]["Expand"]

    def GetGroupIsExpanded(self, group):  # type: (str) -> bool
        """ 获取组是否展开 """
        if group not in self.item_groups:
            return False
        return self.item_groups[group]["Expand"]

    def GetGroupItems(self, group):  # type: (str) -> set
        """ 获取组内的物品 """
        if group not in self.item_groups:
            return set()
        return self.item_groups[group]["Items"]

    def GetGroupOrder(self, group):  # type: (str) -> list
        """ 组里的物品 id，按加进来的顺序（物品栏没选排序时组里照它排：创造栏的组是木 → 石 → 铜 → 铁 → 金 → 钻石 → 下界合金）"""
        if group not in self.item_groups:
            return []
        return list(self.item_groups[group]["Order"])

    def GetGroupName(self, group):  # type: (str) -> str
        """ 获取组的名称 """
        if group not in self.item_groups:
            return ""
        return self.item_groups[group]["Name"]

    def AddGroupItemFromList(self, group, lst):  # type: (str, list) -> None
        for item_id in lst:
            self.AddGroupItem(group, item_id)

class __ItemOrganizer(ItemGroup, ItemCategory):
    """
    整合了对物品分组 / 分类的管理。标签不在这里记：tag 由引擎记（模组在 netease_tags 里注册），
    按 tag 查物品走 registry/tags.py 的 TagLookup（3.10 起问引擎的 LookupItemsByItemTag）
    """
    def __init__(self):
        ItemGroup.__init__(self)
        ItemCategory.__init__(self)

ItemOrganizer = __ItemOrganizer()