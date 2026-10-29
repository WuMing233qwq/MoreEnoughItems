# coding=utf-8

# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
配方树的纯逻辑：不 import 引擎，探针离线测（debug/scripts/probe_recipe_tree.py）。
- solver   解算：分帧 BFS、路径排除、还原识别、选路、数量、护栏
- summary  汇总：深度优先 + 库存（副产物抵扣、背包扣减）
- layout   多格节点的布局：逐层轮廓打包、连线
- choices  这一棵树的选择，与收藏条目互转
"""
from .choices import KIND_TREE, TreeState, clamp_qty, item_ref, key_of, raw_snapshot, split_key
from .layout import DEFAULT, Metrics, Placement, anchor_of, group_width, place
from .solver import (MAX_DEPTH, MAX_NODES, STATE_CYCLIC, STATE_LEAF, STATE_NONITEM, STATE_OK, STATE_PENDING,
                     STATE_RAW, STATE_STOP, STATE_TRUNC, Candidate, Solver, TreeNode, TreeRecipe, choice_sig)
from .summary import Summary, shortfall, summarize

__all__ = [
    "Candidate", "DEFAULT", "KIND_TREE", "MAX_DEPTH", "MAX_NODES", "Metrics", "Placement", "STATE_CYCLIC", "STATE_LEAF",
    "STATE_NONITEM", "STATE_OK", "STATE_PENDING", "STATE_RAW", "STATE_STOP", "STATE_TRUNC", "Solver", "Summary",
    "TreeNode", "TreeRecipe", "TreeState", "anchor_of", "choice_sig", "clamp_qty", "group_width",
    "item_ref", "key_of", "place", "raw_snapshot", "shortfall", "split_key", "summarize",
]
