# coding=utf-8

# ----------------------------------------------------------------------
#  border_calc.py is part of MoreEnoughItems.
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

from MEIScripts.utils import utilities


class GroupBorderCalculator(object):
    """
    独立的分组边框计算器
    根据当前页的物品列表和列数, 计算每个分组物品需要显示的边框
    """

    @staticmethod
    def Calculate(page_items, cols):  # type: (list, int) -> dict
        """ 输入当前页物品列表 + 列数, 输出 {index: [edges]} """
        group_ranges = GroupBorderCalculator._CollectGroupRanges(page_items)
        if not group_ranges:
            return {}
        return GroupBorderCalculator._ComputeEdges(group_ranges, cols)

    @staticmethod
    def CalculateFromIndices(slot_indices, cols):  # type: (set, int) -> dict
        """ 基于一组有效槽位计算外轮廓边框 """
        if not slot_indices:
            return {}

        result = {}
        for idx in slot_indices:
            col = idx % cols
            edges = []
            if (idx - cols) not in slot_indices:
                edges.append(0)
            if (idx + cols) not in slot_indices:
                edges.append(1)

            left = idx - 1 if col > 0 else -1
            if left not in slot_indices:
                edges.append(2)

            right = idx + 1 if col < cols - 1 else -1
            if right not in slot_indices:
                edges.append(3)

            result[idx] = edges

        return result

    @staticmethod
    def CalculateFromSlots(slots, cols):  # type: (dict, int) -> dict
        """
        基于slot映射中的实际grid位置计算分组边框
        支持非连续的slot分布（遮挡避让后的情况）
        """
        group_slots = {}  # type: dict  # group_name -> set(slot_indices)
        for slot_idx in sorted(slots.keys()):
            data = slots[slot_idx]
            if data is None or not isinstance(data, dict):
                continue
            group = None
            if "GroupHead" in data:
                group = data["GroupHead"]["Group"]
            elif "GroupItem" in data:
                group = data["GroupItem"]["Group"]
            if group is not None:
                if group not in group_slots:
                    group_slots[group] = set()
                group_slots[group].add(slot_idx)

        if not group_slots:
            return {}

        all_edges = {}
        for group, indices in group_slots.items():
            all_edges.update(GroupBorderCalculator.CalculateFromIndices(indices, cols))
        return all_edges

    @staticmethod
    def _CollectGroupRanges(page_items):  # type: (list) -> dict
        """ 收集每个分组在当前页中的索引范围 """
        group_ranges = {}
        for i, item in enumerate(page_items):
            if not isinstance(item, dict):
                continue
            group = None
            if "GroupHead" in item:
                group = item["GroupHead"]["Group"]
            elif "GroupItem" in item:
                group = item["GroupItem"]["Group"]
            if group is not None:
                if group not in group_ranges:
                    group_ranges[group] = [i, i]
                else:
                    group_ranges[group][1] = i
        return group_ranges

    @staticmethod
    def _ComputeEdges(group_ranges, cols):  # type: (dict, int) -> dict
        """ 基于网格位置计算边框 """
        all_edges = {}
        for group, (start, end) in group_ranges.items():
            edges = utilities.CalEdge(cols, start, end)
            all_edges.update(edges)
        return all_edges

    @staticmethod
    def ApplyEdges(page_items, all_edges):  # type: (list, dict) -> list
        """ 构建带边框数据的结果列表（不修改原始数据） """
        if not all_edges:
            return page_items
        result = []
        for i, item in enumerate(page_items):
            if isinstance(item, dict) and i in all_edges:
                new_item = {}
                if "GroupHead" in item:
                    new_item["GroupHead"] = dict(item["GroupHead"])
                    new_item["GroupHead"]["Edges"] = all_edges[i]
                elif "GroupItem" in item:
                    new_item["GroupItem"] = dict(item["GroupItem"])
                    new_item["GroupItem"]["Edges"] = all_edges[i]
                result.append(new_item)
            else:
                result.append(item)
        return result
