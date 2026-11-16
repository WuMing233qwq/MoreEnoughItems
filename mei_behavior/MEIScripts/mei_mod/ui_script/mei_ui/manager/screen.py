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
"""
自定义配方管理器的界面（PushScreen 开的，manager.json 的 MeiManager.manager_screen）：压栈界面的通用部分在 core/screen.py（PlainScreen，
不建 MEI 主节点 —— 管理器没有物品格）。控制器 ManagerScript 第一次 Update 时建、每帧推。
MEI_NO_HOTKEYS：开着时 MEI 的快捷键不认（hotkeys/manager.py）—— 没有物品格可指，往输入框里打字时字母也别被当成快捷键
"""
from MEIScripts.constants.ui import ManagerConst
from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import PlainScreen

from . import set_active


class ManagerScreen(PlainScreen):

    CLOSE_NAME = ManagerConst.CloseName
    LABEL = "自定义配方管理器"
    MEI_NO_HOTKEYS = True

    def __init__(self, namespace, name, param):
        PlainScreen.__init__(self, namespace, name, param)
        self.Request = dict(param or {})  # type: dict  # 打开时带的：{"group"}
        self.Script = None  # type: any

    def OnBuilt(self):
        from .script import ManagerScript  # 控制器用到才 import
        self.Script = ManagerScript(self, self.Request)
        set_active(self.Script)
        self.Script.Start()

    def OnFrame(self):
        if self.Script is not None:
            self.Script.Tick()

    def OnTearDown(self):
        script, self.Script = self.Script, None
        set_active(None)
        if script is not None:
            script.Destroy()
