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
焦点探针：一个点上是哪个物品渲染器、它显示的是什么物品 —— 对任何界面都成立（原版容器、HUD、别的模组的界面）。
查询时才从扫描根往下递归找（不在后台扫描、不建索引）。

- search.py   递归找（纯逻辑，不碰引擎模块；节点由调用方给）
- manager.py  入口 FocusManager.Query / QueryCursor、光标坐标 GetCursorPos

门面这里**不导出任何东西**：search 是纯逻辑，想单独用它的人不该被 manager 顺手拖进引擎。
用的时候直接 import 子模块，见 docs/architecture/focus.md。
"""
