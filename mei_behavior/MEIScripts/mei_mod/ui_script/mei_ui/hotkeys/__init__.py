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
快捷键（docs/architecture/bookmarks.md §12）：MEI 自己的按键绑定（组合键；键位存在 MEI 的设置里，设置「按键绑定」页录键），
不注册给引擎的自定义按键。

- keys.py     键码、修饰位、一组按键怎么存与显示（纯数据）
- table.py    快捷键表（纯数据）：id、按键 / 滚轮、默认键位、设置页里的分组
- binds.py    现在的键位（设置项）与修饰键的按下状态、按组合反查；各界面的滚轮翻页问它的 WheelTaken()
- capture.py  录键的状态机：点一下开始录、按过的键都记下、再点一下保存
- actions.py  每个快捷键做什么（收藏的操作和触屏菜单共用 menu.actions 的 op_*）
- manager.py  收裸按键与滚轮、派发、录键（OnKeyPress / OnWheel / ToggleCapture / KeyText）
- hover.py    按着修饰键悬停（PC）：Ctrl / Shift 高亮同一条配方收藏、Alt 出快捷键帮助；主节点每帧调 Tick

门面不做导入 —— keys / table / capture 是纯数据，探针只想要它们时不该被拖进引擎
"""
