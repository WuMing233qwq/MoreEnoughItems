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
        return True

    def RemoveCategory(self, category):  # type: (str) -> bool
        """ 撤掉一个分类（扩展 OnUnload 用）；没有返回 False """
        if category not in self.categories:
            return False
        del self.categories[category]
        return True

    def AddCategoryItem(self, category, item):
        """ 为分类添加一个物品 """
        if category in self.categories:
            self.categories[category].add(item)
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
            "Expand": False,
        }
        return True

    def RemoveGroup(self, group):  # type: (str) -> bool
        """ 撤掉一个物品组（扩展 OnUnload 用）；没有返回 False """
        if group not in self.item_groups:
            return False
        del self.item_groups[group]
        return True

    def SetGroupName(self, group, name):  # type: (str, str) -> bool
        """ 设置一个分组的名称 """
        if group not in self.item_groups:
            return False
        self.item_groups[group]["Name"] = name
        return True

    def AddGroupItem(self, group, item_id):  # type: (str, str) -> bool
        """ 往组内添加一个新物品，存的是 **id 不是 Item** """
        # 存 id 与 AddTagItem 对齐, 也免得组表持有 Item 实例:
        # 归属关系是旁表, 旁表不该抓着池对象不放(item_model.md §6.3)
        if group not in self.item_groups:
            return False
        self.item_groups[group]["Items"].add(item_id)
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

    def GetGroupName(self, group):  # type: (str) -> str
        """ 获取组的名称 """
        if group not in self.item_groups:
            return ""
        return self.item_groups[group]["Name"]

    def AddGroupItemFromList(self, group, lst):  # type: (str, list) -> None
        for item_id in lst:
            self.AddGroupItem(group, item_id)

class ItemTag(object):
    """
    对物品的标签进行管理的类型
    ItemTags 的结构为 {tag: set(ItemId)}，一个标签可以有多个物品，一个物品也可以有多个标签
    """
    def __init__(self):
        self.item_tags = OrderedDict()  # type: OrderedDict[str, set]

    def GetAllTags(self):
        return self.item_tags

    def AddTag(self, tag):  # type: (str) -> bool
        """ 添加一个物品标签 """
        if tag in self.item_tags:
            return False
        self.item_tags[tag] = set()
        return True

    def RemoveTag(self, tag):  # type: (str) -> bool
        """ 撤掉一个标签（扩展 OnUnload 用）；没有返回 False """
        if tag not in self.item_tags:
            return False
        del self.item_tags[tag]
        return True

    def AddTagItem(self, tag, item):  # type: (str, str) -> bool
        """ 往标签内添加一个新物品 """
        if tag not in self.item_tags:
            return False
        self.item_tags[tag].add(item)
        return True

    def GetTagItems(self, tag):  # type: (str) -> set
        """ 获取标签内的物品列表 """
        if tag not in self.item_tags:
            return set()
        return self.item_tags[tag]

    def AddTagFromList(self, tag, lst):  # type: (str, list) -> None
        for item in lst:
            self.AddTagItem(tag, item)

class __ItemOrganizer(ItemGroup, ItemCategory, ItemTag):
    """ 整合了对物品分组/分类/标签的管理 """
    def __init__(self):
        ItemGroup.__init__(self)
        ItemCategory.__init__(self)
        ItemTag.__init__(self)

ItemOrganizer = __ItemOrganizer()