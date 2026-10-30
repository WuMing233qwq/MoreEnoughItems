# coding=utf-8
# ----------------------------------------------------------------------
#  builtin.py is part of MoreEnoughItems.
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
from .kinds import Action, Slider, Toggle
from .manager import SettingsManager

ROW_ITEMS = "row_items"
""" 物品栏与侧栏每行最多几格 """

DEFAULT_ROW_ITEMS = 6

ADAPTIVE_LAYOUT = "adaptive_layout"
""" 自适应：被原版界面盖住的格子留空、搜索栏与翻页栏缩窄避让；关掉两者都停 """

FIND_BUTTON = "find_button"
""" 搜索框旁的查询按钮（只在触屏出现：点一下进查找状态，再点要查的格子出二级菜单）；开界面时读 """

ITEM_GROUPS = "item_groups"
""" 物品栏的物品分组（可收起 / 展开的组头）；关掉时物品一样一样平铺。建物品栏的分页时读 """

BOOKMARKS_VISIBLE = "bookmarks_visible"
""" 显示左侧栏（收藏与最近浏览）；开界面时读 """

BOOKMARKS_WORLD = "bookmarks_world"
""" 收藏按存档分开保存；关着是全局一份 """

ADVANCED_TOOLTIP = "advanced_tooltip"
""" 高级 Tooltip（配方预览、接受物品这类 MEI 自己的悬浮面板）；关掉时一律不出，格子照常出原版悬停文字。开界面时读 """

TOUCH_OPPOSITE = "touch_opposite"
""" 触屏菜单摆到点的那一格的另一侧屏幕边上（方便两只手操作：右手点、左手按菜单）；关着照常按区域摆。开界面时读 """

SHOW_NAMESPACE = "show_namespace"
""" 物品的悬停文字最底下写命名空间（蓝色斜体，照 Java 版显示模组名的样子）；格子建出来时读 """

SHOW_ITEM_ID = "show_item_id"
""" 物品的悬停文字里写英文 ID（深灰，照 Java 版的高级提示框），在命名空间那一行上面；格子建出来时读 """

FLOAT_MODE = "float_mode"
""" 悬浮窗模式：支持 MEI 的界面也不展开 MEI，只显示悬浮窗（点 MEI 再展开）；开界面时读 """

FLOAT_THRESHOLD = "float_threshold"
""" 自动收起阈值：物品栏或收藏栏任一侧每行排得下的格数小于它就收成悬浮窗、都够了再展开；0 是不自动收。悬浮窗模式开着时不管 """

FLOAT_QUICK_COLLAPSE = "float_quick_collapse"
""" 从悬浮窗点开（带黑底）时点空白处（黑底）就收起，MEI 自己的界面里是关掉它；默认关 —— 太容易误触。开界面时读 """

FLOAT_HUD = "float_hud"
""" 游戏界面（HUD）上也显示悬浮窗；回到 HUD 时读 """

FLOAT_COMPAT = "float_compat"
""" 未支持 MEI 的界面也显示悬浮窗（兼容性不做保证）；打开界面时读 """

TREE_PREVIEW = "tree_preview"
""" 配方树节点菜单里渲染这条配方的预览（各类型的 PREVIEW）；关掉就直接用配方条（工作方块 + 原料 → 产物）。每次开菜单时读 """

RESET_ALL = "reset_all"


def RegisterBuiltinSettings():  # type: () -> None
    """ 登记 MEI 自带的设置项，重复调用无副作用 """
    if SettingsManager.GetSpec(RESET_ALL) is not None:
        return
    for spec in (
        Slider(ROW_ITEMS, "options.mei.general.row_items", 1, 12, step=1, default=DEFAULT_ROW_ITEMS),
        Toggle(ADAPTIVE_LAYOUT, "options.mei.general.adaptive", default=True),
        Toggle(FIND_BUTTON, "options.mei.general.find_button", default=True),
        Toggle(ITEM_GROUPS, "options.mei.general.item_groups", default=True),
        Toggle(BOOKMARKS_VISIBLE, "options.mei.general.bookmarks_visible", default=True),
        Toggle(BOOKMARKS_WORLD, "options.mei.general.bookmarks_world", default=False),
        Toggle(ADVANCED_TOOLTIP, "options.mei.general.advanced_tooltip", default=True),
        Toggle(TOUCH_OPPOSITE, "options.mei.general.touch_opposite", default=False),
        Toggle(SHOW_NAMESPACE, "options.mei.general.show_namespace", default=True),
        Toggle(SHOW_ITEM_ID, "options.mei.general.show_item_id", default=False),
        Toggle(FLOAT_MODE, "options.mei.general.float_mode", default=False),
        Slider(FLOAT_THRESHOLD, "options.mei.general.float_threshold", 0, 11, step=1, default=0),
        Toggle(FLOAT_QUICK_COLLAPSE, "options.mei.general.float_quick_collapse", default=False),
        Toggle(FLOAT_HUD, "options.mei.general.float_hud", default=False),
        Toggle(FLOAT_COMPAT, "options.mei.general.float_compat", default=False),
        Toggle(TREE_PREVIEW, "options.mei.general.tree_preview", default=True),
        Action(RESET_ALL, "options.mei.general.reset_all", SettingsManager.ResetAll),
    ):
        SettingsManager.Register(spec)


def GetRowItems():  # type: () -> int
    """ 每行最多几格；设置项没登记时给默认值 """
    return SettingsManager.Get(ROW_ITEMS) or DEFAULT_ROW_ITEMS


def IsAdaptiveEnabled():  # type: () -> bool
    """ 自适应开关；设置项没登记时按开 """
    return SettingsManager.Get(ADAPTIVE_LAYOUT) is not False


def IsBookmarksVisible():  # type: () -> bool
    """ 左侧栏显不显示；设置项没登记时按显示 """
    return SettingsManager.Get(BOOKMARKS_VISIBLE) is not False


def IsBookmarksWorldSpecific():  # type: () -> bool
    """ 收藏是否按存档分开保存；设置项没登记时按全局 """
    return SettingsManager.Get(BOOKMARKS_WORLD) is True


def IsAdvancedTooltipEnabled():  # type: () -> bool
    """ 高级 Tooltip 开不开；设置项没登记时按开 """
    return SettingsManager.Get(ADVANCED_TOOLTIP) is not False


def IsTouchOppositeSide():  # type: () -> bool
    """ 触屏菜单摆不摆到另一侧屏幕边上；设置项没登记时按不摆 """
    return SettingsManager.Get(TOUCH_OPPOSITE) is True


def IsNamespaceShown():  # type: () -> bool
    """ 悬停文字最底下写不写命名空间；设置项没登记时按写 """
    return SettingsManager.Get(SHOW_NAMESPACE) is not False


def IsItemIdShown():  # type: () -> bool
    """ 悬停文字里写不写英文 ID；设置项没登记时按不写 """
    return SettingsManager.Get(SHOW_ITEM_ID) is True


def IsFindButtonEnabled():  # type: () -> bool
    """ 搜索框旁的查询按钮；设置项没登记时按开 """
    return SettingsManager.Get(FIND_BUTTON) is not False


def IsItemGroupsEnabled():  # type: () -> bool
    """ 物品栏分不分组；设置项没登记时按分 """
    return SettingsManager.Get(ITEM_GROUPS) is not False


def IsFloatModeForced():  # type: () -> bool
    """ 悬浮窗模式；设置项没登记时按关 """
    return SettingsManager.Get(FLOAT_MODE) is True


def GetFloatThreshold():  # type: () -> int
    """ 自动收起阈值；设置项没登记时是 0（不自动收）"""
    value = SettingsManager.Get(FLOAT_THRESHOLD)
    return int(value) if value else 0


def IsFloatQuickCollapse():  # type: () -> bool
    """ 点空白处（黑底）快速收起悬浮窗；设置项没登记时按关 """
    return SettingsManager.Get(FLOAT_QUICK_COLLAPSE) is True


def IsFloatOnHud():  # type: () -> bool
    """ HUD 上显不显示悬浮窗；设置项没登记时按不显示 """
    return SettingsManager.Get(FLOAT_HUD) is True


def IsFloatCompat():  # type: () -> bool
    """ 未支持 MEI 的界面也显示悬浮窗；设置项没登记时按关 """
    return SettingsManager.Get(FLOAT_COMPAT) is True


def IsTreePreviewEnabled():  # type: () -> bool
    """ 配方树节点菜单里出不出配方预览；设置项没登记时按开 """
    return SettingsManager.Get(TREE_PREVIEW) is not False
