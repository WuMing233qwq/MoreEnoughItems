# coding=utf-8
# ----------------------------------------------------------------------
#  table.py is part of MoreEnoughItems.
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
快捷键表（纯数据，不碰引擎）：每个快捷键一个 id、一种（按键 / 滚轮）、一组默认按键、设置页里在哪一组。

键位是 MEI 自己存的（自制按键绑定、组合键，单键也一样；不注册给引擎的自定义按键）——
设置「按键绑定」页每个快捷键一行（设置项 key 是 "hotkey_<id>"，名字是 .lang 的 "key.mei.<id>"），玩家在那里录键。
**id 定了别改**：设置里按它记玩家改过的键位。
默认键位照 NEI 的习惯补了组合键（Ctrl+C / X 复制、Ctrl+滚轮改数量、Shift+B 收藏这条配方、Backspace 返回），原来那一套单键不变：
避开原版在容器界面里占用的键（Q 丢弃、E 关闭、1~9 快捷栏、WASD），一组键只做一件事。
"""
from . import keys

PRESS = "press"
""" 按键类：修饰键 + 一个键，按下那一下做 """

WHEEL = "wheel"
""" 滚轮类：修饰键 + 滚轮，向上 +1、向下 -1；**必须带修饰键**（光滚轮会抢了各界面的翻页）"""

GROUP_ITEM = "item"
GROUP_BOOKMARK = "bookmark"
GROUP_RECIPE = "recipe"

GROUPS = (
    (GROUP_ITEM, "options.mei.keys.group.item"),
    (GROUP_BOOKMARK, "options.mei.keys.group.bookmark"),
    (GROUP_RECIPE, "options.mei.keys.group.recipe"),
)
""" 设置页里的分组（顺序）与分组标题的本地化键 """

LABEL_PREFIX = "key.mei."
SETTING_PREFIX = "hotkey_"

KEY_A, KEY_B, KEY_C, KEY_G, KEY_K, KEY_L, KEY_O = 65, 66, 67, 71, 75, 76, 79
KEY_R, KEY_T, KEY_U, KEY_V, KEY_X, KEY_Y = 82, 84, 85, 86, 88, 89
KEY_EQUALS, KEY_MINUS, KEY_BACKSPACE, KEY_UP, KEY_DOWN = 187, 189, 8, 38, 40


class Hotkey(object):
    """
    Id（定了别改）；Kind 按键 / 滚轮；Default 默认的 [修饰位, 主键]（[0, 0] 是默认不绑）；Group 设置页的分组；
    Target 要不要光标下的东西（焦点探针）—— 「返回」这种不看光标的给 False
    """
    __slots__ = ("Id", "Kind", "Default", "Group", "Target")

    def __init__(self, hotkey_id, default, group, kind=PRESS, target=True):  # type: (str, tuple, str, str, bool) -> None
        self.Id = hotkey_id
        self.Kind = kind
        self.Default = keys.normalize(list(default))
        self.Group = group
        self.Target = target

    @property
    def Label(self):  # type: () -> str
        """ 名字的本地化键（设置页那一行的左边）"""
        return LABEL_PREFIX + self.Id

    @property
    def SettingKey(self):  # type: () -> str
        """ 设置项的 key（键位存在设置里，设置项 key 只收小写蛇形）"""
        return SETTING_PREFIX + self.Id


def _key(code, mask=0):
    return mask, code


HOTKEYS = (
    # 物品：光标下的物品（任何界面的物品格）
    Hotkey("source", _key(KEY_R), GROUP_ITEM),  # 查看来源
    Hotkey("uses", _key(KEY_U), GROUP_ITEM),  # 查看用途
    Hotkey("bookmark", _key(KEY_B), GROUP_ITEM),  # 收藏 / 取消收藏；光标在收藏格上时移除那一条
    Hotkey("tree", _key(KEY_Y), GROUP_ITEM),  # 打开配方树
    Hotkey("tooltip", _key(KEY_T), GROUP_ITEM),  # 显示 / 收起高级 Tooltip（钉住看）
    Hotkey("copy_name", _key(KEY_C, keys.CTRL), GROUP_ITEM),  # 复制物品名（NEI 的 Ctrl+C）
    Hotkey("copy_id", _key(KEY_X, keys.CTRL), GROUP_ITEM),  # 复制物品 ID（NEI 的 Ctrl+X）
    Hotkey("candidate_wheel", _key(keys.WHEEL, keys.SHIFT), GROUP_ITEM, kind=WHEEL),  # 多候选格换候选：向上上一个、向下下一个
    Hotkey("candidate_prev", keys.UNBOUND, GROUP_ITEM),  # 上一个候选（默认不绑，滚轮那一条够用）
    Hotkey("candidate_next", keys.UNBOUND, GROUP_ITEM),  # 下一个候选
    # 收藏：光标下的收藏格
    Hotkey("open_bookmark", _key(KEY_O), GROUP_BOOKMARK),  # 打开：配方收藏翻到那一条、配方树收藏打开存的那棵、物品收藏查来源
    Hotkey("remove", _key(KEY_X), GROUP_BOOKMARK),  # 移除这一条
    Hotkey("remove_group", _key(KEY_K), GROUP_BOOKMARK),  # 删除整组（不在分组里的不删）
    Hotkey("count_up", _key(KEY_EQUALS), GROUP_BOOKMARK),  # 数量 +1（配方收藏是倍数）
    Hotkey("count_down", _key(KEY_MINUS), GROUP_BOOKMARK),  # 数量 -1
    Hotkey("count_wheel", _key(keys.WHEEL, keys.CTRL), GROUP_BOOKMARK, kind=WHEEL),  # 数量：向上 +1、向下 -1（NEI 的 Ctrl+滚轮）
    Hotkey("move_up", _key(KEY_UP, keys.CTRL), GROUP_BOOKMARK),  # 上移
    Hotkey("move_down", _key(KEY_DOWN, keys.CTRL), GROUP_BOOKMARK),  # 下移
    Hotkey("move_head", _key(KEY_UP, keys.CTRL | keys.SHIFT), GROUP_BOOKMARK),  # 移到组首
    Hotkey("join", _key(KEY_G), GROUP_BOOKMARK),  # 并入上一组
    Hotkey("leave", _key(KEY_L), GROUP_BOOKMARK),  # 移出分组
    Hotkey("view", _key(KEY_V), GROUP_BOOKMARK),  # 这一组横向 / 纵向排列
    Hotkey("fold", _key(KEY_C), GROUP_BOOKMARK),  # 配方收藏：展开 / 收起这一条；物品收藏：折叠 / 展开所在的组
    # 配方页：光标下的那一行配方
    Hotkey("star_recipe", _key(KEY_B, keys.SHIFT), GROUP_RECIPE),  # 收藏 / 取消收藏这条配方（NEI 的 Shift+A）
    Hotkey("tree_recipe", _key(KEY_Y, keys.SHIFT), GROUP_RECIPE),  # 以这条配方开配方树
    Hotkey("back", _key(KEY_BACKSPACE), GROUP_RECIPE, target=False),  # 返回上一个查询（NEI 的 Backspace）
)
""" 设置页按这个顺序、按 Group 分组列 """

BY_ID = dict((hotkey.Id, hotkey) for hotkey in HOTKEYS)
BY_SETTING = dict((hotkey.SettingKey, hotkey) for hotkey in HOTKEYS)
