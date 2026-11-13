# coding=utf-8

# ----------------------------------------------------------------------
#  node.py is part of MoreEnoughItems.
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
配方树的配置（照 items_sidebar/node.py：薄薄一层，数值在这儿调，逻辑在 script.py）。
每帧的预算按这里的值，这组值下大树也不卡
"""
from .script import RecipeTreeScript


class RecipeTreeNode(RecipeTreeScript):
    def __init__(self, screen, param=None):
        RecipeTreeScript.__init__(self, screen, param)
        self.SolveBudgetMs = 6.0  # 每帧解算多久（画布上有树、能拖的时候）：一个物品第一次查配方是同步直查（引擎结论 §3），查一次可能就超
        self.SolveIdleBudgetMs = 14.0  # 画布上还没有树的时候（刚打开、以它为根）：没东西可看，算快一点
        self.DrawBudgetMs = 6.0  # 每帧给视口附近分控件、写格子多久；视口里的没写完先藏起画布、写「绘制中」，那时每帧 16 毫秒（canvas.FIRST_BUDGET_MS）

    def OnCreate(self):
        self.InitScript()

    def OnDestroy(self):
        self.DestroyScript()
