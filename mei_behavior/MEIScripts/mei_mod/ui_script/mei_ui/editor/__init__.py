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
MEI 编辑器（docs/architecture/user_recipes.md §12、§13）：玩家给自己的机器排配方页、记配方。
入口：设置 MEI 分栏的「编辑器」页（settings.py）、物品的触屏菜单「添加配方」、配方树节点菜单的「添加配方」、自定义配方管理器；都走 OpenMeiEditor。
设置「启用自定义配方」关着时（缺省）一个都不开
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst, PathConst
from MEIScripts.constants.ui import EditorConst
from MEIScripts.utils.text import error_text

LABEL = "MEI 编辑器"


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import register
    return register(NameConst.NameSpace, EditorConst.ScreenKey, PathConst.EditorScreenClsPath, EditorConst.ScreenDef, LABEL)


def OpenMeiEditor(page_id=None, recipe_id=None, item=None, group=None):  # type: (str, str, any, str) -> bool
    """
    开编辑器：recipe_id 是改这条配方、item 是给这样物品记一条新配方（产物格先填上它）、page_id 是改这个页面；都不给就是界面模式的第一个页面。
    group：这一回新建的页面放进哪个分组（从管理器开的时候是选中的那个；不给是默认分组）。
    不当场压栈、排到下一拍（入口都在按钮 / 点击的回调里）；排上了给 True。自定义配方关着时不开、给 False
    """
    from .settings import IsUserRecipesEnabled
    if not IsUserRecipesEnabled():
        return False
    request = {"page": page_id, "recipe": recipe_id, "item": item, "group": group}

    def push():
        from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import push as push_screen
        push_screen(NameConst.NameSpace, EditorConst.ScreenKey, request, LABEL)
    try:
        clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId()).AddTimer(0.0, push)
    except Exception as e:  # noqa
        logger.error("[MEI/editor] 打开编辑器失败: {}".format(error_text(e)))
        return False
    return True


def ActiveEditor():  # type: () -> any
    """
    开着的编辑器（EditorScript）；没开给 None。编辑器的界面建了 MEI 主节点（KIND_EDITOR），它在栈里、上面又没有别的带主节点的界面时
    当前主节点就是它的（管理器、配方树不建主节点）
    """
    from MEIScripts.mei_mod.ui_script.mei_ui import context
    return getattr(context.GetMainNode(), "Editor", None)
