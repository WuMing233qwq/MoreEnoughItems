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
配方树：PushScreen 一个新界面，自上而下画出一条合成路径（多格节点：工作方块 + 原料组），
能拖动平移、底部汇总（合并计算、对照背包）、节点菜单（PC 和触屏一样），保存成一条能展开的收藏。
设计与交互预览：docs/design/recipe_tree.html；说明：docs/architecture/recipe_tree.md。

- screen.py   RecipeTreeScreen：PushScreen 的界面类（照 floating/screen.py）
- node.py / script.py   控制器：解算、画、菜单、汇总、收藏串在一起
- provider.py MEI 的配方 → 解算用的配方；背包里有什么
- controls/   画布（三层拖动）、格子与连线的池、节点菜单、汇总、顶栏
- modules/    纯逻辑（solver / summary / layout / choices），探针离线测

门面不在 import 时拉界面：入口用到才 import
"""


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次界面 """
    from .screen import register_screen as register
    return register()


def OpenRecipeTree(item=None, recipe=None, saved=None, qty=1):  # type: (any, any, dict or None, int) -> bool
    """
    打开配方树。item：根物品；recipe：根用这条配方（从配方行打开时）；saved：收藏里的树条目（按它恢复）；qty：要几个。
    不当场压栈、排到下一拍（入口多在按钮 / 点击绑定的回调里）；排上了返回 True，压不上（没注册上、已经开着）到时候记一行
    """
    from .screen import open_later
    return open_later({"item": item, "recipe": recipe, "saved": saved, "qty": qty})
