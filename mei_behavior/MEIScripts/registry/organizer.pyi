# ----------------------------------------------------------------------
#  organizer.pyi is part of MoreEnoughItems.
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

from typing import Set, Dict, List

from MEIScripts.common.classes.types import Item


class ItemCategory(object):
    def __init__(self):
        self.categories: OrderedDict[str: Set[str]] = OrderedDict()

    def GetAllCategories(self) -> OrderedDict[str: Set[str]]:...

    def AddCategory(self, category: str) -> bool:...

    def RemoveCategory(self, category: str) -> bool:...

    def AddCategoryItem(self, category: str, item: str) -> None:...

class ItemGroup(object):
    def __init__(self):
        self.item_groups: OrderedDict[str: Dict[str: bool or Set[Item] or str]] = OrderedDict()

    def GetAllGroups(self) -> OrderedDict[str: Dict[str: bool or Set[Item] or str]]:...

    def AddGroup(self, group: str, name: str="") -> bool:...

    def RemoveGroup(self, group: str) -> bool:...

    def SetGroupName(self, group: str, name: str) -> bool:...

    def AddGroupItem(self, group: str, item_id: str) -> bool:...

    def SetGroupExpand(self, group: str, expand: bool) -> bool:...

    def ToggleGroupExpand(self, group: str) -> bool:...

    def GetGroupIsExpanded(self, group: str) -> bool:...

    def GetGroupItems(self, group: str) -> Set[str]:...

    def GetGroupName(self, group: str) -> str:...

    def AddGroupItemFromList(self, group: str, lst: List[Item]):...

class ItemTag(object):

    def __init__(self):
        self.item_tags: OrderedDict[str: Set[str]] = OrderedDict()

    def GetAllTags(self) -> OrderedDict[str: Set[str]]:...

    def AddTag(self, tag: str) -> bool:...

    def RemoveTag(self, tag: str) -> bool:...

    def AddTagItem(self, tag: str, item: str) -> bool:...

    def AddTagFromList(self, tag: str, lst: List[str]):...

    def GetTagItems(self, tag: str) -> Set[str]:...

class __ItemOrganizer(ItemGroup, ItemCategory, ItemTag):
    """ 整合了对物品分组/分类/标签的管理 """
    def __init__(self):
        ItemGroup.__init__(self)
        ItemCategory.__init__(self)
        ItemTag.__init__(self)

ItemOrganizer: __ItemOrganizer