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

from MEIScripts.constants.ui import RecipeDetailsPath, UiPathConst
from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import BookmarkText
from MEIScripts.mei_mod.state import BookmarkResolver
from MEIScripts.mei_mod.state.settings import IsAdaptiveEnabled
from MEIScripts.mei_mod.ui_script.mei_ui.core.adaptive import AdaptiveControlRegistry, AdaptiveGeometryCache
from MEIScripts.mei_mod.ui_script.mei_ui.core.focus import FocusTarget, item_from_hit
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.feedback import NotifyNoRecipes
from MEIScripts.mei_mod.ui_script.proxy.focus.manager import FocusManager, GetCursorPos
from MEIScripts.utils.text import native_str


class UIScriptMain(object):

    def __init__(self, screen_node):
        self.UiNameSpace = None  # type: ignore
        self.ScreenNode = screen_node

        self.ItemsBrowserIns = None  # type: ignore
        self.ItemsSidebarIns = None  # type: ignore
        self.RecipeDetailsIns = None  # type: ignore
        self.Tooltip = None  # type: ignore  # TooltipManager，一个界面一份，OnCreate 建、OnDestroy 拆
        self.Menu = None  # type: ignore  # TouchMenu（触屏二级菜单），紧跟在 Tooltip 后面建、在它前面拆

        self.MainPath = None  # type: ignore
        self.ContentPaths = None  # type: ignore
        self.MainContent = None  # type: ignore
        self.RootPath = None  # type: ignore
        self.CreateBackGround = None  # type: ignore
        self.Params = None  # type: ignore

        self._AdaptiveRegistry = AdaptiveControlRegistry()  # type: AdaptiveControlRegistry
        self._AdaptiveGeometry = AdaptiveGeometryCache(self._AdaptiveRegistry)  # type: AdaptiveGeometryCache

        self._TypedControlCache = {}  # type: dict

    def _ToAbsPath(self, path, use_root_path=True):
        if not path:
            return self.RootPath if use_root_path else ""
        if use_root_path:
            return self.RootPath + path
        return path

    def InvalidateControlCache(self, path=None, recursive=True, use_root_path=True):
        """ 按路径失效控件缓存；默认递归失效前缀下全部控件 """
        if path is None:
            self._TypedControlCache = {}
            return

        abs_path = self._ToAbsPath(path, use_root_path=use_root_path)
        if recursive:
            for key in list(self._TypedControlCache.keys()):
                if key[0].startswith(abs_path):
                    del self._TypedControlCache[key]
        else:
            for key in list(self._TypedControlCache.keys()):
                if key[0] == abs_path:
                    del self._TypedControlCache[key]

    @staticmethod
    def _CastControl(control, cast):
        if not cast:
            return control

        cast_map = {
            "button": "asButton",
            "grid": "asGrid",
            "label": "asLabel",
            "progress_bar": "asProgressBar",
            "text_edit_box": "asTextEditBox",
            "switch_toggle": "asSwitchToggle",
            "item_renderer": "asItemRenderer",
            "image": "asImage",
            "scroll_view": "asScrollView",
            "netease_paper_doll": "asNeteasePaperDoll",
            "mini_map": "asMiniMap",
            "slider": "asSlider",
            "stack_panel": "asStackPanel",
            "input_panel": "asInputPanel",
            "selection_wheel": "asSelectionWheel",
            "netease_combo_box": "asNeteaseComboBox",
        }

        cast_method = cast_map.get(cast, cast)
        if not hasattr(control, cast_method):
            raise AttributeError("control has no cast method '{}'".format(cast_method))
        return getattr(control, cast_method)()

    def DestroyScripts(self):
        self.ItemsBrowserIns.OnDestroy() if self.ItemsBrowserIns and self.ItemsBrowserIns.Inited else None
        self.ItemsSidebarIns.OnDestroy() if self.ItemsSidebarIns and self.ItemsSidebarIns.Inited else None
        self.RecipeDetailsIns.OnDestroy() if self.RecipeDetailsIns and self.RecipeDetailsIns.Created else None
    
    def ShowRecipeDetails(self, item, query_by=QueryConst.Output, prefer_type=None, focus_id=None):
        """
        打开/切换配方详情界面.

        已经开着的时候**只切换状态**, 不重建控件 —— 点配方里的材料走的就是这条路,
        重建会丢掉导航栈, 也会白白付一次 CreateChildControl 的代价.

        **先查询再建控件**: CreateChildControl 的最后一个参数是 isVisible=True,
        面板一建出来就在屏幕上了。若先建再查, 查空时空壳已经露出来 ——
        表现是从浏览器点无配方的物品会开出一个空页面。
        查询很贵, 所以查到的结果直接带给 ApplyQueryResult, 不查第二遍。
        """
        mei_root = self.GetMEIRootControl()
        if not mei_root:
            return False

        result = self.RecipeDetailsIns.ResolveQuery(item, query_by)
        if result is None:
            # 什么都不发生 = 玩家眼里的"点坏了", 所以要给个说法
            NotifyNoRecipes(item, query_by)
            return False

        if not self.GetRootBaseUIControl(RecipeDetailsPath.Root):
            self.CreateChildControl(
                "MeiRecipeDetails" + ".recipe_details_ui",
                "recipe_details",
                mei_root,
                True
            )
        if not self.RecipeDetailsIns.Created:
            self.RecipeDetailsIns.OnCreate()

        shown = self.RecipeDetailsIns.ApplyQueryResult(
            item, query_by, result, prefer_type=prefer_type, focus_id=focus_id)
        # 配方页开着：物品栏、收藏栏改为避让它，原版主内容按代理参数藏起来（core/node.py）；已经开着时只是切换，不重复做
        self.OnRecipeDetailsShown()
        return shown

    def FocusAtCursor(self):  # type: () -> FocusTarget
        """ 光标下的物品格（PC，调试键用）：FocusAt 光标那一点；取不到光标（非 PC）给空的 FocusTarget """
        pos = GetCursorPos()
        if pos is None:
            return FocusTarget()
        return self.FocusAt(pos[0], pos[1])

    def FocusAt(self, x, y):  # type: (float, float) -> FocusTarget
        """
        这一点上的物品格，任何界面都认（查找状态点一下、调试键）。MEI 自己的格子先认 —— 不走控件树，直接问它的 grid 与配方页
        （PanelAt，物品优先取面板上的，收藏格带 Cell）；不是再到原版 / 别的模组的界面里递归找渲染器
        （焦点探针 FocusManager.Query：从 FocusRoots 往下、跳过 MEI 的覆盖层，查询时才找，docs/architecture/focus.md）
        """
        pos = (float(x), float(y))
        panel = self.PanelAt(pos[0], pos[1])
        if panel is not None:
            return FocusTarget(pos, None, panel, getattr(panel, "Item", None))
        hit = FocusManager.Query(self.ScreenNode, pos[0], pos[1], self.FocusRoots(), self.FocusExclude())
        if hit is None:
            return FocusTarget(pos)
        return FocusTarget(pos, hit, None, item_from_hit(hit))

    def FocusRoots(self):  # type: () -> list
        """ 焦点探针递归找的起点：原版的根面板（RootPath）。主节点（core/node.py）按界面种类覆写（强制兼容的界面另找）"""
        return [self.RootPath] if self.RootPath else [""]

    def FocusExclude(self):  # type: () -> list
        """ 焦点探针跳过的子树：MEI 自己的覆盖层（它的格子由 PanelAt 认，不走控件树）"""
        return [(self.RootPath or "").rstrip("/") + UiPathConst.MeiRoot]

    def PanelAt(self, x, y):  # type: (float, float) -> any
        """
        这一点上 MEI 自己的哪一格（物品栏、收藏栏、最近浏览、配方页的槽位），显示着物品（或是一条收藏）的才算；都不是返回 None。
        藏着的那一栏（悬浮窗收着）不算
        """
        for grid in self.__ItemGrids():
            panel = grid.PanelAt(x, y)
            if panel is not None:
                return panel
        details = self.RecipeDetailsIns
        binder = getattr(details, "RecipesGridBind", None) if getattr(details, "Created", False) else None
        if binder is not None:
            return binder.PanelAt(x, y)
        return None

    def __ItemGrids(self):  # type: () -> list
        """ 显示着的那几栏的 grid（BaseItemsGridScript.Shown：悬浮窗控制器按样子写）"""
        grids = []
        browser, sidebar = self.ItemsBrowserIns, self.ItemsSidebarIns
        if browser and browser.Inited and getattr(browser, "Shown", True):
            grids.append(getattr(browser, "ItemsGridIns", None))
        if sidebar and sidebar.Inited and getattr(sidebar, "Shown", True):
            grids.append(getattr(sidebar, "BookmarksGridIns", None))
            grids.append(getattr(sidebar, "HistoryGridIns", None))
        return [grid for grid in grids if grid is not None]

    def ShowBookmarkedRecipe(self, entry):  # type: (dict) -> bool
        """
        从收藏点开一条配方：找得回就打开它的探针物品并翻到这一条；找不回仍打开显示物品在该类型下的配方（NEI 的退化方式）
        """
        data = entry.get("item")
        item = BookmarkResolver.ResolveItem(data) if isinstance(data, dict) else None
        if item is None:
            logger.info("[MEI/bookmarks] " + BookmarkText.InvalidRecipe.format(native_str(entry.get("id"))))
            return False
        role = entry.get("role")
        if role not in (QueryConst.Output, QueryConst.Input):
            role = QueryConst.Output
        found = BookmarkResolver.ResolveRecipe(entry) is not None
        focus = native_str(entry.get("id")) if found else None
        return self.ShowRecipeDetails(item, role, prefer_type=native_str(entry.get("cat")) or None, focus_id=focus)

    def GetRootControl(self):
        """
        获取根控件。路径不带结尾的「/」：CreateChildControl 拿「父控件路径 + / + 名字」去查重，
        多一个斜杠就成了「…//mei_ui」，永远查不到、会再建一份，返回值也是 None（引擎结论 §33）
        """
        return self.GetRootBaseUIControl("")

    def GetMEIRootControl(self):
        """ 获取MEI根控件 """
        return self.GetRootBaseUIControl(UiPathConst.MeiRoot)

    def GetRootBaseUIControl(self, path):
        """ 从根路径获取BaseUIControl实例 """
        abs_path = self._ToAbsPath(path, use_root_path=True)

        control = self.ScreenNode.GetBaseUIControl(abs_path)
        return control

    def GetUIControl(self, path, cast=None, use_root_path=True):
        """ 获取根路径控件，支持类型转换缓存 """
        abs_path = self._ToAbsPath(path, use_root_path=use_root_path)

        typed_key = (abs_path, cast)
        cached = self._TypedControlCache.get(typed_key)
        if cached:
            return cached

        control = self.ScreenNode.GetBaseUIControl(abs_path)
        if not control:
            return None

        if cast:
            typed = self._CastControl(control, cast)
        else:
            typed = control

        self._TypedControlCache[(abs_path, cast)] = typed
        return typed

    def CreateChildControl(self, control_def, name, parent_control, force_update=True):
        invalidate_path = parent_control.GetPath()
        control = self.ScreenNode.CreateChildControl(control_def, name, parent_control, force_update)
        self.InvalidateControlCache(invalidate_path, recursive=True, use_root_path=False)
        return control

    def RemoveChildControl(self, control):
        if not control:
            raise ValueError("control to remove cannot be None")
        invalidate_path = control.GetPath()
        self.ScreenNode.RemoveChildControl(control)
        self.InvalidateControlCache(invalidate_path, recursive=True, use_root_path=False)

    def GetScreenDef(self):
        """ 获取 ScreenDef 字符串 """
        return self.ScreenNode.GetScreenName()

    def RegisterAdaptiveControl(
            self,
            path=None,
            key=None,
            use_root_path=True,
            condition=None,
            enabled=True,
            control=None,
            always=False
    ):
        """
        登记一块避让目标。condition：生效条件 condition(get) -> bool（core/adaptive/rules.py），看得见还不够、要代码说了算的才给；
        always：悬浮窗管事、不避让原版界面的时候也照样避让它（配方页那几块）
        """
        entry_key = self._AdaptiveRegistry.register_control(
            path=path,
            key=key,
            use_root_path=use_root_path,
            condition=condition,
            enabled=enabled,
            control=control,
            always=always,
        )
        self.InvalidateAdaptiveGeometry()
        return entry_key

    def UnregisterAdaptiveControl(self, key_or_path):
        self._AdaptiveRegistry.UnregisterControl(key_or_path)
        self.InvalidateAdaptiveGeometry()

    def SetAdaptiveControlEnabled(self, key_or_path, enabled):
        self._AdaptiveRegistry.SetEnabled(key_or_path, enabled)
        self.InvalidateAdaptiveGeometry()

    def ClearAdaptiveControls(self):
        self._AdaptiveRegistry.Clear()
        self.InvalidateAdaptiveGeometry()

    def ListAdaptiveControlKeys(self):
        return self._AdaptiveRegistry.ListKeys()

    def InitAdaptiveControlsFromPaths(self, paths, use_root_path=True, clear=True, conditions=None):
        """ 代理参数的 ContentPaths 全部登记成避让目标；conditions 是代理参数的 Conditions（{路径: 条件}）"""
        self._AdaptiveRegistry.InitFromPaths(
            paths, use_root_path=use_root_path, clear=clear, conditions=conditions
        )
        self.InvalidateAdaptiveGeometry()

    def InvalidateAdaptiveGeometry(self):
        self._AdaptiveGeometry.MarkDirty()

    # 设置页「启用自适应」关掉时：不算几何、没有避让目标、没有被遮挡的格子
    def RefreshAdaptiveGeometry(self, force=False):
        if not IsAdaptiveEnabled():
            return False
        return self._AdaptiveGeometry.Refresh(
            screen_node=self.ScreenNode,
            root_getter=self.GetUIControl,
            force=force,
        )

    def GetAdaptiveVisibleRects(self):
        if not IsAdaptiveEnabled():
            return []
        if self.AvoidanceSuppressed():
            return self._AdaptiveGeometry.GetVisibleRects(always_only=True)
        return self._AdaptiveGeometry.GetVisibleRects()

    def GetAdaptiveOcclusionPolygon(self):
        return self._AdaptiveGeometry.GetOcclusionPolygon()

    def DetectAdaptiveOccludedSlots(self, grid_x, grid_y, cols, rows, item_size, applied=True):
        """ applied 为假时不管这会儿避不避让，只看几何（悬浮窗的自动收起阈值用，common/base.py 的 RowRoom）"""
        if not IsAdaptiveEnabled():
            return set()
        if applied and self.AvoidanceSuppressed():
            return self._AdaptiveGeometry.DetectOccludedSlots(grid_x, grid_y, cols, rows, item_size, always_only=True)
        return self._AdaptiveGeometry.DetectOccludedSlots(grid_x, grid_y, cols, rows, item_size)

    def AvoidanceSuppressed(self):  # type: () -> bool
        """
        悬浮窗管事的时候 MEI 不避让原版界面，照满格显示（悬浮窗启用时还避让，悬浮窗就没有存在的必要）——
        悬浮窗模式开着、从悬浮窗点开着（带黑底）、注入的与 MEI 自己的界面（docs/architecture/floating.md §2）。
        登记时 always=True 的（配方页那几块：悬浮窗模式下仍然要支持配方详情的自适应）照样避让，上面两个入口只给它们
        """
        floating = getattr(self, "Float", None)
        return floating is not None and floating.SuppressesAvoidance()

    def OnRecipeDetailsShown(self):
        """ 配方页开了。主节点（core/node.py）覆写：避让目标换成配方页那几块，按代理参数 AllowChangeVisible 藏原版主内容 """

    def OnRecipeDetailsClosed(self):
        """ 配方页关了。主节点（core/node.py）覆写：避让目标与原版主内容的显隐全部还原 """

    def GetAdaptiveGeometryVersion(self):
        return self._AdaptiveGeometry.GetVersion()

    def UpdateAllUI(self):
        """ 全量刷新当前所有可用实例的UI """
        if self.ItemsBrowserIns and self.ItemsBrowserIns.Inited:
            self.ItemsBrowserIns.UpdateUI(update_size=True, update_page=True)
        if self.ItemsSidebarIns and self.ItemsSidebarIns.Inited:
            self.ItemsSidebarIns.UpdateUI(update_size=True, update_page=True)
