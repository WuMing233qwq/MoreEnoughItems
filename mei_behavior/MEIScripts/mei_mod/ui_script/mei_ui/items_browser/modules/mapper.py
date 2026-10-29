# coding=utf-8

# ----------------------------------------------------------------------
#  mapper.py is part of MoreEnoughItems.
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

class SlotMapper(object):
    """
    将grid slot索引映射到实际物品数据
    支持遮挡避让: 物品自动跳过被遮挡的slot
    """
    EMPTY = None

    def __init__(self):
        self._slots = {}      # type: dict
        self._dataCount = 0   # type: int

    def Build(self, page_items, capacity, occluded_slots=None):  # type: (list, int, set) -> None
        """
        构建 slot → data 映射, 物品自动避开被遮挡的slot
        被遮挡的slot显示为空占位, 物品顺延到后续可用slot
        """
        self._slots.clear()
        self._dataCount = len(page_items)
        if occluded_slots is None:
            occluded_slots = set()

        data_idx = 0
        for slot_idx in range(capacity):
            if slot_idx in occluded_slots:
                self._slots[slot_idx] = self.EMPTY
            elif data_idx < self._dataCount:
                self._slots[slot_idx] = page_items[data_idx]
                data_idx += 1
            else:
                self._slots[slot_idx] = self.EMPTY

    def ApplyBorders(self, all_edges):  # type: (dict) -> None
        """ 将边框数据应用到对应slot的分组数据（创建新dict, 不修改原始数据） """
        if not all_edges:
            return
        for slot_idx, edges in all_edges.items():
            data = self._slots.get(slot_idx)
            if data is None or not isinstance(data, dict):
                continue
            new_data = {}
            if "GroupHead" in data:
                new_data["GroupHead"] = dict(data["GroupHead"])
                new_data["GroupHead"]["Edges"] = edges
            elif "GroupItem" in data:
                new_data["GroupItem"] = dict(data["GroupItem"])
                new_data["GroupItem"]["Edges"] = edges
            self._slots[slot_idx] = new_data

    def Get(self, slot_index):
        """ 获取指定slot的数据, 不存在返回EMPTY """
        return self._slots.get(slot_index, self.EMPTY)

    def IsEmpty(self, slot_index):  # type: (int) -> bool
        """ 判断指定slot是否为空 """
        return self.Get(slot_index) is self.EMPTY

    def IsGroupHead(self, slot_index):  # type: (int) -> bool
        """ 判断指定slot是否为分组头 """
        data = self.Get(slot_index)
        return isinstance(data, dict) and "GroupHead" in data

    def IsGroupItem(self, slot_index):  # type: (int) -> bool
        """ 判断指定slot是否为分组内物品 """
        data = self.Get(slot_index)
        return isinstance(data, dict) and "GroupItem" in data

    def IsNormalItem(self, slot_index):  # type: (int) -> bool
        """ 判断指定slot是否为普通物品(非分组) """
        data = self.Get(slot_index)
        return data is not self.EMPTY and not isinstance(data, dict)

    @property
    def Slots(self):  # type: () -> dict
        """ 获取slot映射（只读） """
        return self._slots

    @property
    def DataCount(self):  # type: () -> int
        return self._dataCount
