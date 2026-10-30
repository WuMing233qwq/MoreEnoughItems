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
三种模式：普通 / 工具 / 作弊（docs/architecture/modes.md）。

- state.py   纯计算（轮到哪一种、权限、一组还是一个）
- drops.py   工具模式的放置目标（别的模组登记的控件，对外 ctx.UI.Drops）
- manager.py 模式本身（全局一份 ModeManager：存着的模式、权限、点格子时接走）
- tool.py    工具模式拿起 / 放下（一个界面一份，主节点 main.Tool）

门面不导出：manager / tool 要引擎，别让只想用 state 的人跟着拉进来
"""
