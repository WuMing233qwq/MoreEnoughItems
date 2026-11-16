# coding=utf-8

# ----------------------------------------------------------------------
#  screen.py is part of MoreEnoughItems.
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
# MEI 自己的界面：HUD 上点悬浮窗的 MEI、在 HUD 上查到配方时不在游戏界面里展开，PushScreen 开这个空界面，
# MEI 照支持的界面那样建在它的根面板下（docs/architecture/floating.md §6.1）。压栈界面的通用部分在 core/screen.py
from MEIScripts.constants.codes import NameConst, PathConst, QueryConst
from MEIScripts.constants.ui import FloatConst
from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import MainScreen, push, register
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_SCREEN

RECIPE_DELAY = 3
""" 带着配方开的：MEI 建好后再等这么多帧才开配方页，让刚建的两栏先排好 """

LABEL = "MEI 界面"


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    return register(NameConst.NameSpace, FloatConst.ScreenKey, PathConst.MeiScreenClsPath, FloatConst.ScreenDef, LABEL)


def open_screen(recipe=None):  # type: (dict or None) -> bool
    """
    开 MEI 自己的界面。recipe 是开好后要打开的配方页：{"item", "query_by", "prefer_type", "focus_id"}。
    栈里已经有它就开不出来（SDK 不让同一个界面压两次），返回 False
    """
    return push(NameConst.NameSpace, FloatConst.ScreenKey, {"recipe": recipe} if recipe else None, LABEL)


def request_close(node):  # type: (any) -> bool
    """ 关掉 MEI 压栈开的界面（MEI 自己的界面、编辑器）：只记下，它下一帧在自己的 Update 里出栈 """
    if not isinstance(node, MainScreen):
        return False
    node.RequestClose()
    return True


class MeiScreen(MainScreen):
    """
    PushScreen 开的空界面，MEI 建在它的根面板下（主节点 KIND_SCREEN）：一打开就是从悬浮窗点开的样子（带黑底），
    点悬浮窗的 MEI、点黑底、按 ESC 或背包键都是关掉它
    """

    KIND = KIND_SCREEN
    CLOSE_NAME = FloatConst.ScreenClose
    LABEL = LABEL

    def __init__(self, namespace, name, param):
        MainScreen.__init__(self, namespace, name, param)
        param = param or {}
        self.Recipe = param.get("recipe")  # type: dict or None  # 开好后要打开的配方页，开过就清掉
        self.RecipeDelay = RECIPE_DELAY  # type: int

    def OnFrame(self):
        if self.Recipe is None or self.Main is None:
            return
        self.RecipeDelay -= 1
        if self.RecipeDelay <= 0:
            recipe, self.Recipe = self.Recipe, None
            self.Main.ShowRecipeDetails(recipe.get("item"), recipe.get("query_by") or QueryConst.Output,
                                        prefer_type=recipe.get("prefer_type"), focus_id=recipe.get("focus_id"))

    def OnTearDown(self):
        self.Recipe = None
