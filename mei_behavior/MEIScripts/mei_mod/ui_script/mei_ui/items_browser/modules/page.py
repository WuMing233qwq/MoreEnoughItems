# coding=utf-8

# ----------------------------------------------------------------------
#  page.py is part of MoreEnoughItems.
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

from MEIScripts.registry import ItemManager, ItemOrganizer
from MEIScripts.utils.page import Page


class PageWithGroup(Page):
    """
    基于滑动窗口的分组物品分页器
    使用偏移量(offset) + 可见容量(capacity)的模型
    窗口缩放时容量变化但偏移量不变, 用户看到的起始物品不会跳动
    """
    def __init__(self, items_input, group_index, cols, rows):  # type: (list, dict, int, int) -> None
        self.Cols = cols          # type: int
        self.Rows = rows          # type: int
        self._offset = 0          # type: int
        self._items_input = items_input   # type: list
        self._group_index = group_index  # type: dict
        self._expanded_list = []   # type: list
        self._view_capacity = max(1, self._capacity)  # type: int
        super(PageWithGroup, self).__init__(self._expanded_list, self._view_capacity)
        self.update_page()

    @property
    def items(self):  # type: () -> list
        return self._expanded_list

    @items.setter
    def items(self, value):  # type: (list) -> None
        self._expanded_list = value

    @property
    def index(self):  # type: () -> int
        return self._offset

    @index.setter
    def index(self, value):  # type: (int) -> None
        self._offset = value

    @property
    def page_size(self):  # type: () -> int
        return self._view_capacity

    @page_size.setter
    def page_size(self, value):  # type: (int) -> None
        self._view_capacity = max(1, int(value))

    @property
    def _capacity(self):  # type: () -> int
        return self.Cols * self.Rows

    @property
    def length(self):  # type: () -> int
        return len(self._expanded_list)

    def update_page(self):
        """ 重建分组展开后的物品列表 """
        curr_offset = self._offset
        self._expanded_list = self.__BuildExpandedList()
        # 保持当前偏移, 确保不越界
        if self.length > 0:
            self._offset = max(0, min(curr_offset, self.length - 1))
        else:
            self._offset = 0

    def UpdatePage(self):
        self.update_page()

    def set_page_size(self, capacity):  # type: (int) -> None
        """ 设置当前可见页容量(扣除遮挡后的可用slot数) """
        self._view_capacity = max(1, int(capacity))
        if self.length > 0:
            self._offset = max(0, min(self._offset, self.length - 1))
        else:
            self._offset = 0

    def SetViewCapacity(self, capacity):  # type: (int) -> None
        self.set_page_size(capacity)

    def __BuildExpandedList(self):
        """ 根据分组展开状态构建完整物品列表 """
        lt, group_index = self._items_input, self._group_index
        tmp = list(lt)
        tmp_offset = 0

        for index, group in group_index.items():
            is_expanded = ItemOrganizer.GetGroupIsExpanded(group)
            items = lt[index][group]
            length = len(items)
            expanded_index = tmp_offset + index

            if is_expanded:
                for item in reversed(items):
                    tmp.insert(expanded_index + 1, {
                        "GroupItem": {
                            "Item": item,
                            "Group": group,
                        },
                    })
                tmp_offset += length

            tmp.pop(expanded_index)
            tmp.insert(expanded_index, {
                "GroupHead": {
                    "Group": group,
                    "Name": ItemOrganizer.GetGroupName(group),
                    "Items": items,
                    "Length": length,
                },
            })

        return tmp

    @property
    def current_items(self):  # type: () -> list
        """ 获取当前页的原始数据（不含边框, 边框由调用方在slot映射后计算） """
        end_index = min(self._offset + self._view_capacity, self.length)
        return self._expanded_list[self._offset:end_index]

    @property
    def value(self):  # type: () -> list
        return self.current_items

    @property
    def current_page_number(self):  # type: () -> int
        if self._view_capacity <= 0:
            return 1
        return (self._offset // self._view_capacity) + 1

    @property
    def currPageNum(self):  # type: () -> int
        return self.current_page_number

    @property
    def total_page(self):  # type: () -> int
        if self._view_capacity <= 0:
            return 1
        return max(1, (self.length + self._view_capacity - 1) // self._view_capacity)

    @property
    def pageNum(self):  # type: () -> int
        return self.total_page

    def scroll(self, delta):  # type: (int) -> None
        """
        滚动偏移量
        delta > 0 向后, delta < 0 向前
        支持按行滚动(delta=cols)或按页滚动(delta=capacity)
        """
        self._offset += delta
        self._clamp_index(strict=False)

    def _clamp_index(self, strict=False):
        """ 确保偏移量在有效范围内, 超出边界时循环 """
        if self._capacity <= 0 or self.length <= 0:
            self._offset = 0
            return
        if strict:
            self._offset = max(0, min(self._offset, self.length - 1))
            return
        if self._offset >= self.length:
            self._offset = 0
        elif self._offset < 0:
            step = max(1, self._view_capacity)
            last_page_offset = max(0, ((self.length - 1) // step) * step)
            self._offset = last_page_offset

    def __ClampOffset(self):
        self._clamp_index(strict=False)


def group_items(items):  # type: (list) -> (list, dict)
    """
    对列表进行分组，用于展示折叠
    """
    item_to_category = {}
    for group_name, group_data in ItemOrganizer.GetAllGroups().items():
        for item in group_data["Items"]:
            item_to_category[item.ItemId] = group_name

    category_info = {}
    unclassified = []

    for i, item in enumerate(items):
        item_id = item.ItemId
        cat_name = item_to_category.get(item_id)
        if cat_name is not None:
            info = category_info.get(cat_name)
            if info is None:
                info = (i, [], set())
                category_info[cat_name] = info
            info[1].append(item)
            info[2].add(item_id)
        else:
            unclassified.append((i, item))

    sorted_categories = sorted(category_info.items(), key=lambda x: x[1][0])

    result = []
    index_map = OrderedDict()

    cat_iter = iter(sorted_categories)
    unc_iter = iter(unclassified)

    cat_entry = next(cat_iter, None)
    unc_entry = next(unc_iter, None)

    while cat_entry is not None or unc_entry is not None:
        cat_pos = cat_entry[1][0] if cat_entry else float('inf')
        unc_pos = unc_entry[0] if unc_entry else float('inf')

        if unc_pos < cat_pos:
            result.append(unc_entry[1])
            unc_entry = next(unc_iter, None)
        else:
            cat_name, (_, matched_items, matched_ids) = cat_entry
            # 组表存的是 id(旁表不持有池对象), 这里反查回实例
            group_all = []
            for group_item_id in ItemOrganizer.GetGroupItems(cat_name):
                group_all.extend(ItemManager.GetItemsById(group_item_id))
            other_items = [
                item for item in group_all
                if item.ItemId not in matched_ids
            ]
            result.append({cat_name: matched_items + other_items})
            index_map[len(result) - 1] = cat_name
            cat_entry = next(cat_iter, None)

    return result, index_map

def BuildPage(items, cols, rows):  # type: (list, int, int) -> PageWithGroup
    items_input, group_index = group_items(items)
    return PageWithGroup(items_input, group_index, cols, rows)