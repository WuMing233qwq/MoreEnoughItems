# coding=utf-8
# ----------------------------------------------------------------------
#  panel.py is part of MoreEnoughItems.
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

from MEIScripts.common.classes.types import Item
from MEIScripts.constants.texts import MenuKindText
from MEIScripts.constants.ui import MenuKey, TooltipKind
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel
from MEIScripts.utils.text import error_text


class MultiItemPanel(ItemPanel):
	"""
	多候选格：一格轮流显示几个候选（配方这一格接受一个 tag 下的多个物品、熔炉的燃料……）。

	显示哪一个由 CurrentIndex 定。两种推进方式：
	  · 自动轮播：配方页的节拍每 RotateTicks 拍调一次 Rotate，往下翻一个；
	  · 手动选择：Select / Next / Prev。选过之后自动轮播停下（AutoRotate = False），ResumeRotate 恢复。
	    入口（前后切换的按键、滚轮、触屏点选）以后接，这里只把接口留好。
	当前候选一变就通知监听者（AddListener）—— 接受物品 tooltip 的标题靠它跟着当前候选走（docs/architecture/tooltip.md §5）。

	第三方经 ctx.UI.Controls.MultiItemPanel 拿到它：工厂方法与 ItemStackList / CurrentIndex / RotateTicks 的旧写法照常可用
	"""

	def __init__(self, control):
		ItemPanel.__init__(self, control)
		self.RotateTicks = self.TicksOf(1.0)
		""" 每多少拍换一个候选。**不自己起 timer** —— 节拍由配方详情页统一驱动，整页一个，所有轮播因此**相位同步** """

		self.AnimBase = None  # type: int or None
		""" 节拍对表基准，由 `RecipesGridBind.TickPanels` 在第一拍写入。没有它，中途建出来的槽位第一次轮播会提前 """

		self.ItemListProvider = None  # type: callable or None
		""" 候选会变的话给一个取候选的函数，每次轮播前问一遍 """
		self.ItemStackList = []  # type: list
		""" 全部候选（ItemStack）。旧名保留：第三方、调试键都在读 """
		self.CurrentIndex = 0  # type: int
		self.AutoRotate = True  # type: bool
		""" 手动选过就停（False）：玩家正在挑某一个时，别再自己翻走 """
		self._Listeners = []  # type: list

	@staticmethod
	def TicksOf(interval):  # type: (float) -> int
		""" 秒 -> 拍。至少 1 拍, 否则会变成每拍都换 """
		from MEIScripts.common.classes.base import BaseRecipeUIScript
		step = BaseRecipeUIScript.ANIM_TICK_INTERVAL or 0.2
		return max(1, int(round(float(interval or step) / step)))

	# 工厂
# ======================================================================================================================
	@classmethod
	def from_item_stack_list(cls, control, item_stack_list, rotate_interval=1.0):
		ins = cls(control)
		ins.RotateTicks = cls.TicksOf(rotate_interval)
		ins.SetItemStackList(item_stack_list)
		return ins

	@classmethod
	def from_item_list(cls, control, item_list, rotate_interval=1.0):
		ins = cls(control)
		ins.RotateTicks = cls.TicksOf(rotate_interval)
		ins.SetItemStackList([item.stack(count=1) for item in item_list])
		return ins

	@classmethod
	def from_provider(cls, control, provider):
		ins = cls(control)
		ins.ItemListProvider = provider
		ins.StartRotate()
		return ins

	# 候选
# ======================================================================================================================
	@property
	def Candidates(self):  # type: () -> list
		""" 全部候选的副本 """
		return list(self.ItemStackList)

	@property
	def Current(self):  # type: () -> any
		""" 当前显示的那个候选（ItemStack）；没有候选为 None """
		if not self.ItemStackList:
			return None
		return self.ItemStackList[self.CurrentIndex]

	def SetItemList(self, item_list):
		normalized = []
		for item in item_list or []:
			if isinstance(item, Item):
				normalized.append(item.stack(count=1))
		self.SetItemStackList(normalized)

	def SetItemStackList(self, item_stack_list):
		""" 换一批候选：下标越界就回到第一个；画上当前这个，并通知监听者（候选变了，标题也得变）"""
		self.ItemStackList = list(item_stack_list or [])
		if self.CurrentIndex >= len(self.ItemStackList):
			self.CurrentIndex = 0
		self.StartRotate()
		self.__Notify()

	def StartRotate(self):
		""" 只渲染当前这个; 推进交给 Rotate() / Select() """
		self.__RenderCurrentItem()

	# 选择（手动入口以后接：前后切换的按键、滚轮、触屏点选）
# ======================================================================================================================
	def Select(self, index, manual=True):  # type: (int, bool) -> bool
		"""
		显示第 index 个候选（越界按候选数取模，负数从尾部数），返回当前候选变没变。
		manual 为真（玩家选的）时停下自动轮播；轮播自己推进时传 False
		"""
		count = len(self.ItemStackList)
		if not count:
			self.SetChildVisible(False)
			return False
		index %= count
		changed = index != self.CurrentIndex
		self.CurrentIndex = index
		if manual:
			self.AutoRotate = False
		self.__RenderCurrentItem()
		if changed:
			self.__Notify()
		return changed

	def Next(self, manual=True):  # type: (bool) -> bool
		return self.Select(self.CurrentIndex + 1, manual)

	def Prev(self, manual=True):  # type: (bool) -> bool
		return self.Select(self.CurrentIndex - 1, manual)

	def ResumeRotate(self):
		""" 恢复自动轮播（比如光标离开这一格时） """
		self.AutoRotate = True

	# 监听：当前候选变了
# ======================================================================================================================
	def AddListener(self, listener):  # type: (callable) -> None
		""" listener(panel)：当前候选或候选表变了时调 """
		if listener not in self._Listeners:
			self._Listeners.append(listener)

	def RemoveListener(self, listener):  # type: (callable) -> None
		if listener in self._Listeners:
			self._Listeners.remove(listener)

	def __Notify(self):
		for listener in list(self._Listeners):
			try:
				listener(self)
			except Exception as e:  # noqa  监听者炸了不能拖垮轮播（轮播跑在配方页的节拍里）
				logger.error("[MEI/ui] 多候选格的监听者抛异常: {}".format(error_text(e)))

	# 节拍
# ======================================================================================================================
	def __PullItemList(self):
		provider = self.ItemListProvider
		if not callable(provider):
			return
		latest = provider()  # noqa
		if latest is None:
			return
		self.SetItemStackList(latest)

	def __RenderCurrentItem(self):
		if not self.ItemStackList:
			self.SetChildVisible(False)
			return
		self.SetChildVisible(True)
		self.SetItemStack(self.ItemStackList[self.CurrentIndex])

	def Rotate(self, ticks):
		"""
		每 RotateTicks 拍换一个候选。由 `RecipesGridBind` 驱动，`ticks` **相对本面板出生的时刻**（驱动方已对表）。
		手动选过（AutoRotate 为假）就不翻，但候选表照样按 provider 刷新。

		**刻意不叫 `OnAnimTick`** —— 那是 `BaseRecipeUIScript` 的契约，面向写扩展的人；
		轮播是配方页的内部实现，不该在控件层再铸一个同名契约。
		"""
		if ticks % self.RotateTicks:
			return
		self.__PullItemList()
		if not self.ItemStackList:
			self.SetChildVisible(False)
			return
		if self.AutoRotate:
			self.Select(self.CurrentIndex + 1, manual=False)

	# MEI tooltip：悬停时出「接受物品」，标题是当前候选
# ======================================================================================================================
	def HasMeiTooltip(self):  # type: () -> bool
		return len(self.ItemStackList) > 1

	def TooltipContent(self):  # type: () -> tuple or None
		if not self.HasMeiTooltip():
			return None
		return TooltipKind.Items, self

	def MenuActions(self):  # type: () -> tuple
		""" 触屏菜单：候选多于一个时多「上一个 / 下一个」（换了候选，来源 / 收藏就对着新的那个，标题跟着换）"""
		base = ItemPanel.MenuActions(self)
		if base and len(self.ItemStackList) > 1:
			return base + (MenuKey.PrevCandidate, MenuKey.NextCandidate)
		return base

	def MenuKind(self):  # type: () -> any
		""" 触屏菜单顶栏：候选多于一个时写「可选物品」 """
		return MenuKindText.Candidates if len(self.ItemStackList) > 1 else ItemPanel.MenuKind(self)

	def ContentKey(self):  # type: () -> any
		"""
		轮播换的是当前候选，格子本身没换内容：认候选那一组（重新渲染这一格、换了一批候选才变）。
		不覆写的话按物品认，tooltip / 触屏菜单每轮播一次就收起一次
		"""
		return tuple(id(stack) for stack in self.ItemStackList)

	def Destroy(self):
		# 没有 timer 要撤 —— 节拍归配方详情页管, 面板被丢弃就自然不再被 tick；监听者一并放掉
		self._Listeners = []
		ItemPanel.Destroy(self)
