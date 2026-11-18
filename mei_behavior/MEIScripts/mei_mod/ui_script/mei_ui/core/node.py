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

from MEIScripts.constants.ui import FocusConst, RecipeDetailsPath, UiPathConst
from MEIScripts.constants.codes import NameConst, QueryConst
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.node import ItemsBrowserNode
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.node import ItemsSidebarNode
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import flush
from MEIScripts.mei_mod.ui_script.mei_ui.common import scale as side_scale
from MEIScripts.mei_mod.ui_script.mei_ui.menu.manager import TouchMenu
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys import hover
from MEIScripts.mei_mod.ui_script.mei_ui.floating.manager import FloatController
from MEIScripts.mei_mod.ui_script.mei_ui.floating.screen import open_screen
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_COMPAT, KIND_EDITOR, KIND_HUD, KIND_SCREEN, KIND_SUPPORTED
from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager
from MEIScripts.mei_mod.ui_script.mei_ui.modes.tool import ToolHost
from MEIScripts.mei_mod.ui_script.mei_ui.filters.menu import FilterMenu
from MEIScripts.mei_mod.ui_script.mei_ui.core.params import (
	MAIN_CONTENT_CONTROL, adaptive_conditions, allow_change_visible, under, visible_control_path,
)
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import NotifyNoRecipes
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.node import RecipeDetailsNode
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.manager import TooltipManager
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.mei_mod.ui_script.mei_ui.core.script import UIScriptMain
from MEIScripts.mei_mod.state import BookmarkManager, PinManager, PrefsManager, TreePrefsManager, UserRecipeManager
from MEIScripts.mei_mod.state.settings import IsBookmarksVisible

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()

RECIPE_ADAPTIVE_KEY = "recipe_details:"
""" 配方页那几块在自适应登记表里的键前缀（和原版内容的键 —— 就是路径 —— 分开）"""

_HIDDEN_MAIN = {}
""" screenDef -> 原版主内容的路径：MEI 藏了还没显回来的。界面状态跨开关存活（引擎结论 §22），下次开这个界面时兜底显回来 """

_BUILT_CELL = {}
""" (screenDef, 两栏的路径) -> 建那一栏时用的那一档的格子边长：两栏根上的记号读不出大小时认这个（覆盖层跨开关存活，引擎结论 §22）"""

class UIMainNode(UIScriptMain):
	def __init__(self, proxy_instance, kind=KIND_SUPPORTED, params=None):
		screen_node = proxy_instance.ScreenNode
		UIScriptMain.__init__(self, screen_node)
		self.ScreenNode = screen_node
		self.Kind = kind  # type: str  # 支持的界面（代理建的）/ HUD / 强制兼容（注入的，floating/hosts.py）/ MEI 自己的界面（floating/screen.py）
		self.Float = None  # type: FloatController or None  # 悬浮窗、查找状态，OnCreate 建、OnDestroy 拆
		self.Tool = None  # type: ToolHost or None  # 工具模式拿起的物品（docs/architecture/modes.md），OnCreate 建、OnDestroy 拆
		self.Filters = None  # type: FilterMenu or None  # 物品栏的筛选与排序菜单（mei_ui/filters/），OnCreate 建、OnDestroy 拆
		self.Covered = False  # type: bool  # 注入的界面被别的界面盖着（Cover / Uncover）：不推每帧
		self.Editor = None  # type: any  # MEI 编辑器（KIND_EDITOR 的界面才有，editor/script.py）：点物品栏的物品先交给它
		# 覆盖层用哪个定义：两种都不带两栏，两栏由 EnsureScripts 按「两侧UI缩放」的那一档建（支持的界面开界面就建，平时那一档的层级；
		# 注入的界面第一次展开才建、MEI 自己的界面一打开就建，都是悬浮窗那一档的层级 —— HUD 上平时只多一个悬浮窗，
		# 不把两栏几百个控件塞进游戏界面的每次重排；生下来就是要的层级，不用每次开都 SetLayer（很贵：要重算整个界面的层级））
		self.RootDef = UiPathConst.ProxyRootDef if kind == KIND_SUPPORTED else UiPathConst.FloatRootDef  # type: str
		self.AllowChangeVisible = {}  # type: dict  # 代理参数 AllowChangeVisible 解析成 {目标: 布尔}（core/params.py）
		self.RecipeAdaptive = False  # type: bool  # 配方页开着：它的几块登记成了避让目标
		self.SuspendedContent = []  # type: list  # 配方页开着时停了避让的原版内容（主内容和长在它底下的）
		self.MainContentHidden = False  # type: bool  # 那一块（VisiblePath）是 MEI 藏的（配方页开着、参数允许）
		self.VisiblePath = ""  # type: str  # 配方页开着时藏起来的那一块：代理参数 VisibleControlPath，不写就是主内容（core/params.py）

		self.Params = {}  # type: dict
		self.CreateBackGround = False  # type: bool
		self.RootPath = ""  # type: str
		self.MainPath = ""  # type: str
		self.ContentPaths = []  # type: list

		self.UiNameSpace = NameConst.MainUiNameSpace

		# params
		# ===================================================
		self.GetParams(params)


		self.ItemsBrowserIns = ItemsBrowserNode()
		self.ItemsSidebarIns = ItemsSidebarNode()
		self.RecipeDetailsIns = RecipeDetailsNode(proxy_instance, self)

	def GetParams(self, params=None):
		""" 界面参数：支持的界面查登记表（ProxyManager.GetCustomUIParams，ctx.UI.Screens.Register 登记的），注入的界面由注入方给 """
		self.Params = params if params is not None else ProxyManager.GetCustomUIParams(self.ScreenNode.GetScreenName())
		self.CreateBackGround = self.Params.get("CreateBackground", False)
		self.RootPath = self.Params.get("RootPath", UiPathConst.ScreenRoot)

		self.ContentPaths = self.Params.get("ContentPaths", ["/"])
		self.MainPath = self.Params.get("MainPath", self.ContentPaths[0] if self.ContentPaths else "")
		self.AllowChangeVisible = allow_change_visible(self.Params)
		self.VisiblePath = visible_control_path(self.Params, self.MainPath)

		self.InitAdaptiveControlsFromPaths(self.ContentPaths, use_root_path=True, clear=True,
		                                   conditions=adaptive_conditions(self.Params))

	def OnCreate(self):
		context.SetMainNode(self)
		root_control = self.GetRootControl()
		if not root_control:
			raise RuntimeError("cannot to find root control.")
		mei_root = self.GetMEIRootControl()
		if not mei_root:
			# 已经有了就不再建（覆盖层跨开关存活，引擎结论 §22）；父控件取的路径不带结尾的「/」，SDK 才查得出重名（引擎结论 §33）
			self.CreateChildControl(self.UiNameSpace + "." + self.RootDef, UiPathConst.MeiRoot.lstrip("/"), root_control, True)
		else:
			# 被盖住时藏过整个覆盖层（注入的界面，floating/hosts.py），两个方向都写（引擎结论 §22）
			mei_root.SetVisible(True)

		# 上次开着配方页时界面没正常关：原版主内容可能还藏着，显回来（只还原 MEI 自己藏的）
		self.ShowMainContent(True)

		# 物品栏、收藏栏的显隐归悬浮窗控制器（FloatController.Apply，两个方向都写）；注入的界面以悬浮窗起步，第一次展开才建
		if self.Kind in (KIND_SUPPORTED, KIND_SCREEN):
			self.EnsureScripts()
			PrefsManager.BumpOpenCount()
		elif self.Kind == KIND_EDITOR:
			self.EnsureScripts()

		# tooltip：全局各一个（接受物品、配方预览），控件随 MEI 根控件跨开关存活，开界面时显式藏掉，见 docs/architecture/tooltip.md
		self.Tooltip = TooltipManager(self)
		self.Tooltip.OnCreate()
		# 触屏的二级菜单：就是 tooltip 的移动端宿主，内容归 tooltip 建、按钮区归它填，见 docs/architecture/tooltip.md §6
		self.Menu = TouchMenu(self, self.Tooltip)
		self.Menu.OnCreate()
		flush()  # tooltip、菜单复位时写的显隐都没当场刷新（show_later）：这里一次刷新
		# 悬浮窗与查找状态（docs/architecture/floating.md）：按设置定这次是展开还是收成悬浮窗
		# 编辑器不要悬浮窗、黑底：物品栏的显隐归编辑器（ShowEditorBrowser）
		if self.Kind != KIND_EDITOR:
			self.Float = FloatController(self, self.Kind)
			self.Float.OnCreate()
		# 三种模式（docs/architecture/modes.md）：工具模式拿起的物品、捕获层一个界面一份；每次开界面问一次服务端有没有作弊的权限
		self.Tool = ToolHost(self)
		self.Tool.OnCreate()

		self.Filters = FilterMenu(self)
		self.Filters.OnCreate()
		ModeManager.OnScreenOpen()

	def EnsureScripts(self):
		"""
		物品栏、收藏栏（「显示左侧栏」开着才建）的控件与脚本建起来，建过的不再建。
		两栏一律建在覆盖层下面（名字取路径最后一段），定义按设置「两侧UI缩放」的那一档选（common/scale.py）：
		支持的界面用平时那一档层级的，注入的界面、MEI 自己的界面用悬浮窗那一档的（这几种界面两栏一露面就是悬浮窗管事，不用再 SetLayer）。
		已经建着、却是另一档建的（改了设置）就先拆脚本、拆控件，再按现在的那一档重建 —— 建好的控件改不了尺寸（变量在建控件时求值）。
		所以改了设置，下次打开容器（HUD 上是下次展开）才生效
		"""
		scale = side_scale.current()
		floating = self.Kind != KIND_SUPPORTED
		self.__EnsureSide(self.ItemsBrowserIns, UiPathConst.RightWrapper, scale, floating)
		if IsBookmarksVisible() and self.Kind != KIND_EDITOR:
			self.__EnsureSide(self.ItemsSidebarIns, UiPathConst.LeftWrapper, scale, floating)

	def __EnsureSide(self, script, path, scale, floating):  # type: (any, str, any, bool) -> None
		""" 一栏：控件不在、或是另一档建的就（拆了）按这一档建；脚本没建就按这一档建 """
		control = self.GetUIControl(path)
		if control is not None and self.BuiltCell(path) != scale.Cell:
			if script.Inited:
				script.OnDestroy()
			self.RemoveChildControl(control)
			control = None
		if control is None:
			mei_root = self.GetMEIRootControl()
			if mei_root is None:
				return
			self.CreateChildControl(scale.WrapperDef(path, floating), path.rsplit("/", 1)[-1], mei_root, True)
			if self.GetUIControl(path) is None:
				return
			_BUILT_CELL[(self.GetScreenDef(), path)] = scale.Cell
		if not script.Inited:
			script.ApplyScale(scale)
			script.OnCreate()

	def BuiltCell(self, path):  # type: (str) -> int or None
		"""
		这一栏是按哪一档建的（格子边长）：读它根上的记号 cell_mark（大小就是 $mei_slot_size），读不出来认建的时候记下的；
		都没有给 None（EnsureScripts 当成对不上、重建一次）
		"""
		mark = self.GetUIControl(path + UiPathConst.CellMark)
		if mark is not None:
			try:
				size = mark.GetSize()
			except Exception:  # noqa
				size = None
			if size and len(size) > 0:
				found = side_scale.by_cell(int(round(size[0])))
				if found is not None:
					return found.Cell
		return _BUILT_CELL.get((self.GetScreenDef(), path))

	def FocusRoots(self):  # type: () -> list
		"""
		焦点探针递归找的起点：支持的界面、MEI 自己的界面、HUD 用原版根面板 RootPath（MEI 的覆盖层由 FocusExclude 跳过）；
		强制兼容的界面先试常见的内容面板（FocusConst.CompatRoots），一个都没有就退到界面最根上
		"""
		if self.Kind != KIND_COMPAT:
			return UIScriptMain.FocusRoots(self)
		for path in FocusConst.CompatRoots:
			if self.ScreenNode.GetBaseUIControl(path) is not None:
				return [path]
		return [""]

	def ShowRecipeDetails(self, item, query_by=QueryConst.Output, prefer_type=None, focus_id=None):
		"""
		游戏界面（HUD）上不开配方页：先查有没有配方（没有就照常提示），有就开 MEI 自己的界面、在那里开。
		别的界面照常（UIScriptMain.ShowRecipeDetails）
		"""
		if self.Kind == KIND_EDITOR:
			return False  # 编辑器里不开配方页（会盖在编辑器上）
		if self.Kind != KIND_HUD:
			return UIScriptMain.ShowRecipeDetails(self, item, query_by, prefer_type=prefer_type, focus_id=focus_id)
		if self.RecipeDetailsIns.ResolveQuery(item, query_by) is None:
			NotifyNoRecipes(item, query_by)
			return False
		return open_screen({"item": item, "query_by": query_by, "prefer_type": prefer_type, "focus_id": focus_id})

	def Cover(self):
		"""
		注入的界面被别的界面盖住（floating/hosts.py）：收成悬浮窗（顺带关菜单、退出查找状态），整个覆盖层藏起来。
		界面还活着，控件照常能碰；露出来时 Uncover
		"""
		if self.Float is not None:
			self.Float.Suspend()
		if self.Tool is not None:
			self.Tool.Release()
		self.ShowRoot(False)
		self.Covered = True

	def Uncover(self):
		""" 盖着它的界面关了：覆盖层显出来（收着的样子），重新成为当前的主节点 """
		self.Covered = False
		context.SetMainNode(self)
		self.ShowRoot(True)
		if self.Float is not None:
			self.Float.Resume()

	def ShowRoot(self, on):  # type: (bool) -> None
		""" 整个覆盖层的显隐：被盖住时藏、露出来时显（两个方向都走这里，引擎结论 §22）"""
		mei_root = self.GetMEIRootControl()
		if mei_root is not None:
			mei_root.SetVisible(on)

	# 配方页开着时的避让（docs/architecture/settings.md §6.2）
	# ==================================================================================================================
	def OnRecipeDetailsShown(self):
		"""
		配方页开了：物品栏、收藏栏改为避让配方页自己的那几块（RecipeDetailsPath.AdaptivePaths，第一块就是这时的主内容）；
		要藏的那一块（VisibleControlPath，不写就是主内容 MainPath，连同登记在它底下的避让目标）不再避让 —— 不管能不能藏它；
		代理参数 AllowChangeVisible 允许的话把它藏起来。配方页开着时再打开别的物品（只是切换）不重复做；关的时候 OnRecipeDetailsClosed 全部还原
		"""
		if self.RecipeAdaptive:
			return
		self.RecipeAdaptive = True
		target = self.VisiblePath or ""
		self.SuspendedContent = [key for key in self.ListAdaptiveControlKeys() if under(key, target)]
		for key in self.SuspendedContent:
			self.SetAdaptiveControlEnabled(key, False)
		for path in RecipeDetailsPath.AdaptivePaths:
			# always：悬浮窗管事、不避让原版界面时也照样避让配方页
			self.RegisterAdaptiveControl(path=path, key=RECIPE_ADAPTIVE_KEY + path, always=True)
		if target and self.AllowChangeVisible.get(MAIN_CONTENT_CONTROL, True):
			self.ShowMainContent(False)
		self.RefreshAvoidance()

	def OnRecipeDetailsClosed(self):
		""" 配方页关了（关按钮、退回到头、关界面）：配方页那几块不再是避让目标，原版内容的避让恢复，藏了的主内容显回来 """
		if not self.RecipeAdaptive:
			return
		self.RecipeAdaptive = False
		for path in RecipeDetailsPath.AdaptivePaths:
			self.UnregisterAdaptiveControl(RECIPE_ADAPTIVE_KEY + path)
		for key in self.SuspendedContent:
			self.SetAdaptiveControlEnabled(key, True)
		self.SuspendedContent = []
		self.ShowMainContent(True)
		self.RefreshAvoidance()

	def ShowMainContent(self, on):  # type: (bool) -> None
		"""
		配方页开着时藏的那一块（VisiblePath：代理参数 VisibleControlPath，不写就是主内容）的显隐，两个方向都走这里。
		藏了就记进模块级的表（_HIDDEN_MAIN，按 screenDef）；显的时候**只显表里记着的那一块** —— MEI 没藏过的（原版自己藏起来的）
		不去动。关的时候已经取不到控件、界面没正常关的，记录留着，下次开这个界面时兜底显回来。
		MEI 的覆盖层长在它底下的（比如主内容写的是 "/"）不藏 —— 会把 MEI 一起藏掉
		"""
		screen_def = self.GetScreenDef()
		path = _HIDDEN_MAIN.get(screen_def, "") if on else (self.VisiblePath or "")
		if not path or under(UiPathConst.MeiRoot, path):
			return
		control = self.GetUIControl(path)
		if control is None:
			return
		control.SetVisible(on)
		self.MainContentHidden = not on
		if on:
			_HIDDEN_MAIN.pop(screen_def, None)
		else:
			_HIDDEN_MAIN[screen_def] = path

	def RefreshAvoidance(self):
		""" 避让目标变了：物品栏、收藏栏马上重算遮挡与上下栏，不等它们 0.2 秒一次的定时器 """
		for script in (self.ItemsBrowserIns, self.ItemsSidebarIns):
			if script is not None and getattr(script, "Inited", False):
				script.RefreshAvoidance()

	def ShowEditorBrowser(self, on):  # type: (bool) -> None
		""" 编辑器的右栏（物品栏）开 / 收：外层的显隐两个方向都写（引擎结论 §22），再照 ShowSides 补推行列数 """
		wrapper = self.GetUIControl(UiPathConst.RightWrapper)
		if wrapper is not None:
			wrapper.SetVisible(bool(on))
		self.ShowSides(bool(on), False)

	def ShowSides(self, browser, sidebar):  # type: (bool, bool) -> None
		"""
		两栏显没显示（悬浮窗控制器每次换样子、开界面都写，两个方向都写，FloatController.Apply）：藏着时 grid 不自检、不快速核对
		（引擎不建格子，问最后一格会 print error）；从藏着变成显示时当场补推行列数、重建格子再重算避让（BaseItemsGridScript.SetShown）——
		藏着时推下去的引擎多半没接住，不当场补就要等 grid 自检卡满 1 秒才补（展开后过好一会儿才复位）
		"""
		for script, on in ((self.ItemsBrowserIns, browser), (self.ItemsSidebarIns, sidebar)):
			if script is not None and getattr(script, "Inited", False):
				script.SetShown(on)

	def OnTick(self):
		""" 界面代理每帧调（每秒 30 次）：tooltip 的悬停核对、构建、摆位置，触屏菜单的打开与执行都挂在这里 —— SDK 的定时器最短 0.05 秒 """
		tooltip = self.Tooltip
		if tooltip is not None:
			tooltip.Update()
		menu = self.Menu
		if menu is not None:
			menu.Update()
		tool = self.Tool
		if tool is not None:
			tool.Update()
		filters = self.Filters
		if filters is not None:
			filters.Update()
		floating = self.Float
		if floating is not None:
			floating.Update()
		# 托管配方页（类型的 PageHost）：容器建好后的那一帧分页、画第一页
		details = getattr(self, "RecipeDetailsIns", None)
		if details is not None and getattr(details, "Created", False):
			details.PollHostedPage()
		# 按着修饰键悬停（PC）：Ctrl / Shift 高亮同一条配方收藏
		hover.Tick(self)
		# 这一帧 tooltip、触屏菜单写的显隐都没当场刷新（show_later：SDK 缺省每改一次显隐就重排整个界面，引擎结论 §57）：一帧刷新一次
		flush()

	def OnDestroy(self):
		context.ClearMainNode(self)
		if self.Filters is not None:
			self.Filters.OnDestroy()
			self.Filters = None
		if self.Tool is not None:
			self.Tool.OnDestroy()
			self.Tool = None
		if self.Float is not None:
			self.Float.OnDestroy()
			self.Float = None
		if self.Menu is not None:
			self.Menu.OnDestroy()
			self.Menu = None
		if self.Tooltip is not None:
			self.Tooltip.OnDestroy()
			self.Tooltip = None
		flush()  # 收起菜单、tooltip 写的显隐（没当场刷新）：刷新一次
		# 开着配方页关的界面：先把避让目标与原版主内容的显隐还原（界面状态跨开关存活，引擎结论 §22）
		self.OnRecipeDetailsClosed()
		recipe_details_control = self.GetRootBaseUIControl(RecipeDetailsPath.Root)
		if recipe_details_control:
			self.RemoveChildControl(recipe_details_control)

		self.DestroyScripts()

		# 强制刷盘点: 客户端没有可靠的「退出游戏前」回调, 关界面是最接近
		# 「用户用完了」的时机. 平时的写由 Store 的节流合并负责.
		# 两个 Store 各自独立, 得各刷各的 —— 漏掉书签会丢掉关界面前 2s 内的收藏.
		# 注入的界面（HUD、强制兼容）每次被别的界面盖住都要拆一次：有改动才写，不强刷
		force = self.Kind in (KIND_SUPPORTED, KIND_SCREEN, KIND_EDITOR)
		PrefsManager.Flush(force=force)
		BookmarkManager.Flush(force=force)
		PinManager.Flush(force=force)
		TreePrefsManager.Flush()  # 配方树的首选、当原料：有改动才写
		UserRecipeManager.Flush()  # 编辑器里做的页面与配方：有改动才写