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
自定义配方管理器（docs/architecture/user_recipes.md §22）：按分组整理玩家自制的页面 —— 启用 / 停用、移到别的分组、介绍、
剪贴板导出导入。入口：设置「编辑器」页的「自定义配方管理器」、编辑器顶栏的分组按钮；都走 OpenManager。
「启用自定义配方」关着也能开（整理分组、导入导出照样能做，只是不登记成配方类型）
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst, PathConst
from MEIScripts.constants.ui import ManagerConst
from MEIScripts.utils.text import error_text

LABEL = "自定义配方管理器"

_ACTIVE = [None]
""" 开着的管理器（ManagerScript）：界面建好时记、拆的时候清 """


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import register
    return register(NameConst.NameSpace, ManagerConst.ScreenKey, PathConst.ManagerScreenClsPath, ManagerConst.ScreenDef, LABEL)


def set_active(script):  # type: (any) -> None
    _ACTIVE[0] = script


def ActiveManager():  # type: () -> any
    """ 开着的管理器（ManagerScript）；没开给 None """
    return _ACTIVE[0]


def OpenManager(group=None):  # type: (str) -> bool
    """
    开管理器：group 是先选中哪个分组（不给是默认分组）。不当场压栈、排到下一拍（入口都在按钮的回调里）；排上了给 True。
    已经开着就开不出来（SDK 不让同一个界面压两次）
    """
    request = {"group": group}

    def push():
        from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import push as push_screen
        push_screen(NameConst.NameSpace, ManagerConst.ScreenKey, request, LABEL)
    try:
        clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId()).AddTimer(0.0, push)
    except Exception as e:  # noqa
        logger.error("[MEI/manager] 打开管理器失败: {}".format(error_text(e)))
        return False
    return True
