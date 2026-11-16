# coding=utf-8
# ----------------------------------------------------------------------
#  settings.py is part of MoreEnoughItems.
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
设置 MEI 分栏的「编辑器」页（和「通用」「按键绑定」「关于」同级，docs/architecture/settings.md §6）：
「启用自定义配方」（Toggle，缺省开）、一行字写现在有几个页面、几条配方（绑定 names.EDITOR，设置页的代理写，settings/proxy.py 的 EditorInfo）、
「打开 MEI 编辑器」（Action）、「自定义配方管理器」（Action，自定义配方关着也能开，mei_ui/manager/）、
「在物品菜单里显示『添加配方』」（Toggle，缺省关）、「启用强制覆盖」（Toggle，缺省开：多人游戏里操作员统一的配方自动下载、
同 Id 替换本地的，client/share.py 与 extensions/user 看它）。
自定义配方关着时：自制的页面不登记成配方类型（配方页、配方树里都没有，extensions/user 看这个开关）、编辑器打不开、
两个菜单里都没有「添加配方」，设置页上后两行灰着（绑定 names.EDITOR_ENABLED）。
设置项在界面层登记（照 hotkeys/binds.py），client/main_sys 构造期调
"""
from MEIScripts.mei_mod.state.settings import Action, SettingsManager, Toggle

USER_RECIPES = "user_recipes"
OPEN_EDITOR = "open_editor"
OPEN_MANAGER = "open_manager"
MENU_ENTRY = "editor_menu"
FORCE_OVERRIDE = "share_override"


def RegisterSettings():  # type: () -> None
    """ 登记「编辑器」页的几行（不碰引擎；重复调用无副作用）"""
    if SettingsManager.GetSpec(OPEN_EDITOR) is not None:
        return
    SettingsManager.Register(Toggle(USER_RECIPES, "options.mei.editor.enabled", default=True))
    SettingsManager.Register(Action(OPEN_EDITOR, "options.mei.editor.open", OpenFromSettings))
    SettingsManager.Register(Action(OPEN_MANAGER, "options.mei.editor.manager", OpenManagerFromSettings))
    SettingsManager.Register(Toggle(MENU_ENTRY, "options.mei.editor.menu", default=False))
    SettingsManager.Register(Toggle(FORCE_OVERRIDE, "options.mei.editor.override", default=True))


def IsUserRecipesEnabled():  # type: () -> bool
    """ 自定义配方开着没有（缺省开；设置项没登记时也按开）"""
    value = SettingsManager.Get(USER_RECIPES)
    return True if value is None else bool(value)


def IsForceOverride():  # type: () -> bool
    """ 多人游戏里操作员统一的配方：自动下载、同 Id 替换本地的（缺省开；设置项没登记时也按开）"""
    value = SettingsManager.Get(FORCE_OVERRIDE)
    return True if value is None else bool(value)


def IsMenuEntryShown():  # type: () -> bool
    """ 物品的触屏菜单「更多」里出不出「添加配方」：自定义配方开着、这一项也开着（缺省关）"""
    return IsUserRecipesEnabled() and bool(SettingsManager.Get(MENU_ENTRY))


def OpenFromSettings():
    """ 设置页上点了「打开 MEI 编辑器」：编辑器压在设置界面上，关了回到设置（自定义配方关着时按钮灰着，OpenMeiEditor 也不开）"""
    from . import OpenMeiEditor
    OpenMeiEditor()


def OpenManagerFromSettings():
    """ 设置页上点了「自定义配方管理器」：管理器压在设置界面上，关了回到设置（自定义配方关着也开）"""
    from MEIScripts.mei_mod.ui_script.mei_ui.manager import OpenManager
    OpenManager()
