# -*- coding: utf-8 -*-

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

from MEIScripts.mei_mod.state.settings import GetRowItems
from MEIScripts.mei_mod.ui_script.layout.grid_layout import GridLayout
from script import ItemsBrowserScript

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()

class ItemsBrowserNode(ItemsBrowserScript):
	def __init__(self):
		ItemsBrowserScript.__init__(self)

		self.ItemSize = 20  # type: int
		self.RowItems = GetRowItems()  # type: int  # 设置页「每行最大物品显示数量」，每次开界面重读

		self.Layout = GridLayout(self.ItemSize, self.RowItems)

	def OnCreate(self):
		self.InitScript()

	def OnDestroy(self):
		self.DestroyScript()