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
from MEIScripts.mei_mod.ui_script.mei_ui.common.scale import NORMAL
from script import ItemsBrowserScript

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()

class ItemsBrowserNode(ItemsBrowserScript):
	def __init__(self):
		ItemsBrowserScript.__init__(self)

		self.RowItems = GetRowItems()  # type: int  # 设置页「每行最大物品显示数量」，每次开界面重读
		# 格子与栏的大小按两侧UI缩放的那一档：主节点建好控件后按建的那一档再给一次（UIMainNode.EnsureScripts）
		self.ApplyScale(NORMAL)

	def OnCreate(self):
		self.InitScript()

	def OnDestroy(self):
		self.DestroyScript()