# coding=utf-8

# ----------------------------------------------------------------------
#  node.py is part of MoreEnoughItems.
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

from script import RecipeDetailsScript

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()

class RecipeDetailsNode(RecipeDetailsScript):

	def __init__(self, proxy_instance, main_node):
		screen_node = proxy_instance.ScreenNode
		RecipeDetailsScript.__init__(self)
		self.ScreenNode = screen_node
		self.ProxyIns = proxy_instance

		self.MainNode = main_node

	def OnCreate(self):
		self.InitScript()

	def OnDestroy(self):
		self.DestroyScript()