# coding=utf-8
# ----------------------------------------------------------------------
#  names.py is part of MoreEnoughItems.
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
设置页的绑定名，由设置项 key 推出；JSON 里每一行都得照这里写（探针 probe_settings 对账）。
"""

SCREEN_DEF = "settings.screen_world_controls_and_settings"
""" 暂停菜单进的那个游戏内设置页 """

PROXY_PATH = "MEIScripts.mei_mod.ui_script.settings.proxy.SettingsProxy"

PREFIX = "mei.settings"

ENABLED = "#mei.settings.enabled"
""" 所有行共用的启用位 """

DEGRADED = "#mei.settings.degraded"
""" 存储降级时为真，控制那行提示的可见性 """

ABOUT = "#mei.settings.about"


def toggle_changed(key):  # type: (str) -> str
    return "toggle.{}.{}".format(PREFIX, key)


def toggle_state(key):  # type: (str) -> str
    return "#{}.{}.state".format(PREFIX, key)


def slider_changed(key):  # type: (str) -> str
    return "#{}.{}.slider".format(PREFIX, key)


def slider_value(key):  # type: (str) -> str
    return "#{}.{}.value".format(PREFIX, key)


def slider_steps(key):  # type: (str) -> str
    return "#{}.{}.steps".format(PREFIX, key)


def slider_label(key):  # type: (str) -> str
    return "#{}.{}.label".format(PREFIX, key)


def button_pressed(key):  # type: (str) -> str
    return "button.{}.{}".format(PREFIX, key)


def key_reset(key):  # type: (str) -> str
    """ 按键绑定那一行右边的「恢复默认」"""
    return "button.{}.{}.reset".format(PREFIX, key)


def key_text(key):  # type: (str) -> str
    """ 按键绑定那一行按钮上的字（现在的键位 / 正在录的）"""
    return "#{}.{}.text".format(PREFIX, key)


ROLES = {
    "toggle": (("changed", toggle_changed), ("state", toggle_state)),
    "slider": (("changed", slider_changed), ("value", slider_value),
               ("steps", slider_steps), ("label", slider_label)),
    "choice": (("changed", slider_changed), ("value", slider_value),
               ("steps", slider_steps), ("label", slider_label)),
    "action": (("pressed", button_pressed),),
    "keybind": (("pressed", button_pressed), ("reset", key_reset), ("text", key_text)),
}
""" 设置项类型 -> 它在界面上要的绑定；选项复用滑条那一套；按键绑定是「点了录键 / 保存」「恢复默认」「按钮上的字」"""


def names_of(kind, key):  # type: (str, str) -> dict
    """ {角色: 绑定名}；不认识的类型给空表 """
    return dict((role, make(key)) for role, make in ROLES.get(kind, ()))
