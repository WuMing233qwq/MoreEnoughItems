# coding=utf-8

# ----------------------------------------------------------------------
#  script.py is part of MoreEnoughItems.
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

from mod_log import logger

from MEIScripts.mei_mod.ui_script.mei_ui.core.node import UIMainNode
from MEIScripts.mei_mod.ui_script.proxy.base import ScreenProxy
from MEIScripts.utils.text import error_text

class CustomProxyScript(ScreenProxy):
	"""
	原生UI的代理类
	"""
	def __init__(self, screen_name, screen_node):
		ScreenProxy.__init__(self, screen_name, screen_node)
		self.UINode = None

		self.InitUIMain()

	def InitUIMain(self):
		self.UINode = UIMainNode(self)

	def OnCreate(self):
		self.UINode.OnCreate()

	def OnTick(self):
		"""
		SDK 每个脚本帧（每秒 30 次）对每个代理调一次（NativeScreenManager.OnScriptTickClient）。
		抛出去会带走同一帧排在后面的代理，所以接住；OnDestroy 之后 UINode 已经删了
		"""
		node = getattr(self, "UINode", None)
		if node is None:
			return
		try:
			node.OnTick()
		except Exception as e:  # noqa
			logger.error("[MEI/proxy] OnTick 抛异常: {}".format(error_text(e)))

	def OnDestroy(self):
		self.UINode.OnDestroy()
		del self.UINode


