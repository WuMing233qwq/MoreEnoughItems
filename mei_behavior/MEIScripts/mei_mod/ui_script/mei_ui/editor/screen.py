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
MEI 编辑器的界面（PushScreen 开的，editor.json 的 MeiEditor.editor_screen）：压栈界面的通用部分在 core/screen.py；
主节点是 KIND_EDITOR（只建物品栏），控制器 EditorScript 在主节点建好以后建、每帧推。ESC、背包键先问编辑器（有没存的改动要点两下）
"""
from MEIScripts.constants.ui import EditorConst
from MEIScripts.mei_mod.ui_script.mei_ui.core.screen import MainScreen
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_EDITOR


class EditorScreen(MainScreen):

    KIND = KIND_EDITOR
    CLOSE_NAME = EditorConst.CloseName
    LABEL = "MEI 编辑器"

    def __init__(self, namespace, name, param):
        MainScreen.__init__(self, namespace, name, param)
        self.Request = dict(param or {})  # type: dict  # 打开时带的：{"page", "recipe", "item"}
        self.Script = None  # type: any

    def OnBuilt(self):
        from .script import EditorScript  # 控制器拉起整个编辑器，用到才 import
        self.Script = EditorScript(self, self.Main, self.Request)
        self.Script.Start()

    def OnFrame(self):
        if self.Script is not None:
            self.Script.Tick()

    def OnTearDown(self):
        script, self.Script = self.Script, None
        if script is not None:
            script.Destroy()

    def OnCloseKey(self, _args=None):
        if self.Script is not None:
            self.Script.Close()
        else:
            self.RequestClose()
