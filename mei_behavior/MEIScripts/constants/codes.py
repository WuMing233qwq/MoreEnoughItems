# coding=utf-8

# ----------------------------------------------------------------------
#  codes.py is part of MoreEnoughItems.
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

class NameConst(object):
    NameSpace = "MoreEnoughItems"

    ItemsBrowserUiNameSpace = "ItemsBrowser"
    RecipeDetailsUiNameSpace = "RecipeDetails"
    CommonUiNameSpace = "mei_common"
    MainUiNameSpace = "mei_main"

    ClientSysName = "clientMain"
    ServerSysName = "serverMain"

class PathConst(object):
    ClientMainSysPath = "MEIScripts.mei_mod.client.main_sys.MainSys"
    ServerMainSysPath = "MEIScripts.mei_mod.server.main_sys.MainSys"
    MeiScreenClsPath = "MEIScripts.mei_mod.ui_script.mei_ui.floating.screen.MeiScreen"  # MEI 自己的界面（HUD 上点 MEI 时开）
    RecipeTreeScreenClsPath = "MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree.screen.RecipeTreeScreen"  # 配方树（PushScreen）

class QueryConst(object):
    # 配方查询方向, 即 RecipeManager.QueryRecipe(query_by=...) 的取值.
    # 放这里而不是 UI 层: registry 与 ui_script 都要用, 按依赖方向只能落在 constants.
    Output = "output"
    Input = "input"

class TagConst(object):
    # 内建 tag 的 id. 值进了 Recipe.Id 的 canonical, 改动即改变所有相关配方的身份.
    # Fuels: MEI 自己不用 (燃料不进配方本身) —— 留着是因为 ctx.Const.TagConst 是对外门面, 删掉算不兼容改动
    Fuels = "mei:fuels"

class StorageConst(object):
    # 落盘用的 configName. 引擎侧只认字母/数字/下划线, 且改名等于丢弃已存数据.
    PrefsConfigName = "mei_prefs"
    BookmarksConfigName = "mei_bookmarks"
    PinsConfigName = "mei_pins"
    SettingsConfigName = "mei_settings"
    TreePrefsConfigName = "mei_tree_prefs"  # 配方树的全局表：首选配方、当原料、工作方块显示哪个