# coding=utf-8

# ----------------------------------------------------------------------
#  base.py is part of MoreEnoughItems.
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
import mod.client.extraClientApi as clientApi

from MEIScripts.utils.binder import ScreenBinder

UIScreenProxy = clientApi.GetUIScreenProxyCls()


class ScreenProxy(UIScreenProxy):
    """
    MEI 挂在原版界面上的代理的基类：记着界面节点，带一个往这个界面上挂绑定的 ScreenBinder
    """
    def __init__(self, screen_name, screen_node):
        UIScreenProxy.__init__(self, screen_name, screen_node)
        self.ScreenNode = screen_node
        self.Bindings = ScreenBinder(screen_node)  # type: ScreenBinder
