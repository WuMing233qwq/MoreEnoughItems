# ----------------------------------------------------------------------
#  script.pyi is part of MoreEnoughItems.
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
from MEIScripts.mei_mod.ui_script.mei_ui.core.adaptive import AdaptiveControlRegistry, AdaptiveGeometryCache
from mod.client.ui.controls.baseUIControl import (
    MiniMapUIControl,
    InputPanelUIControl,
    ItemRendererUIControl,
    NeteaseComboBoxUIControl,
    ProgressBarUIControl,
    ButtonUIControl,
    SwitchToggleUIControl,
    StackPanelUIControl,
    SelectionWheelUIControl,
    TextEditBoxUIControl,
    GridUIControl,
    NeteasePaperDollUIControl,
    BaseUIControl,
    ScrollViewUIControl,
    SliderUIControl,
)
from mod.client.ui.screenNode import ScreenNode
from typing import List, Dict, Optional, Callable, overload, Literal, Any, Union
from MEIScripts.utils.polygon import RectPolygon

from MEIScripts.common.classes.types import Item
from MEIScripts.mei_mod.ui_script.mei_ui.core.focus import FocusTarget
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.node import ItemsBrowserNode
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.node import ItemsSidebarNode
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.node import RecipeDetailsNode
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.manager import TooltipManager
from MEIScripts.mei_mod.ui_script.mei_ui.menu.manager import TouchMenu


class UIScriptMain(object):

    def __init__(self, screen_node):
        self.UiNameSpace: str = str
        self.ScreenNode: ScreenNode = ScreenNode

        self.ItemsBrowserIns: ItemsBrowserNode = ItemsBrowserNode
        self.RecipeDetailsIns: RecipeDetailsNode = RecipeDetailsNode
        self.ItemsSidebarIns: ItemsSidebarNode = ItemsSidebarNode
        self.Tooltip: Optional[TooltipManager] = TooltipManager
        self.Menu: Optional[TouchMenu] = TouchMenu

        self.MainPath: str = str
        self.ContentPaths: List[str] = List
        self.MainContent: str = str
        self.RootPath: str = str
        self.Params: Dict[str, Any] = Dict
        self._AdaptiveRegistry: AdaptiveControlRegistry = AdaptiveControlRegistry
        self._AdaptiveGeometry: AdaptiveGeometryCache = AdaptiveGeometryCache
        self._ControlCache: Dict[str, BaseUIControl] = Dict
        self._TypedControlCache: Dict[tuple, Any] = Dict

    def _ToAbsPath(self, path: Optional[str], use_root_path: bool = True) -> str:...

    def InvalidateControlCache(self, path: Optional[str] = None, recursive: bool = True, use_root_path: bool = True) -> None:...

    @staticmethod
    def _CastControl(control: BaseUIControl, cast: Optional[str]) -> Any:...

    def DestroyScripts(self):...


    def ShowRecipeDetails(self, item: Item, query_by: str = ..., prefer_type: Optional[str] = ...,
                          focus_id: Optional[str] = ...) -> bool:...

    def FocusAtCursor(self) -> FocusTarget:...

    def FocusAt(self, x: float, y: float) -> FocusTarget:...

    def FocusRoots(self) -> list:...

    def FocusExclude(self) -> list:...

    def PanelAt(self, x: float, y: float) -> Any:...

    def __ItemGrids(self) -> list:...

    def ShowBookmarkedRecipe(self, entry: dict) -> bool:...

    def GetRootControl(self) -> Optional[BaseUIControl]:...

    def GetMEIRootControl(self) -> Optional[BaseUIControl]:...

    def GetScreenDef(self) -> str:...

    def GetRootBaseUIControl(self, path: str) -> Optional[BaseUIControl]:...

    # @overload
    # def GetUIControl(self, path: str, cast: Optional[str] = None, use_root_path: bool=True) -> Optional[any]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["button"] = None, use_root_path: bool=True) -> Optional[ButtonUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["grid"] = None, use_root_path: bool=True) -> Optional[GridUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["progress_bar"] = None, use_root_path: bool=True) -> Optional[ProgressBarUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["text_edit_box"] = None, use_root_path: bool=True) -> Optional[TextEditBoxUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["switch_toggle"] = None, use_root_path: bool=True) -> Optional[SwitchToggleUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["item_renderer"] = None, use_root_path: bool=True) -> Optional[ItemRendererUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["scroll_view"] = None, use_root_path: bool=True) -> Optional[ScrollViewUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["netease_paper_doll"] = None, use_root_path: bool=True) -> Optional[NeteasePaperDollUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["mini_map"] = None, use_root_path: bool=True) -> Optional[MiniMapUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["slider"] = None, use_root_path: bool=True) -> Optional[SliderUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["stack_panel"] = None, use_root_path: bool=True) -> Optional[StackPanelUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["input_panel"] = None, use_root_path: bool=True) -> Optional[InputPanelUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["selection_wheel"] = None, use_root_path: bool=True) -> Optional[SelectionWheelUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["netease_combo_box"] = None, use_root_path: bool=True) -> Optional[NeteaseComboBoxUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["grid"] = None, use_root_path: bool=True) -> Optional[GridUIControl]:...
    @overload
    def GetUIControl(self, path: str, cast: Literal["grid"] = None, use_root_path: bool=True) -> Optional[GridUIControl]:...

    def CreateChildControl(self, control_def: str, name: str, parent_control: BaseUIControl,
                           force_update: bool = True) -> Optional[BaseUIControl]:...

    def RemoveChildControl(self, control: Optional[BaseUIControl]) -> None:...


    def RegisterAdaptiveControl(self, path: Optional[str] = None, key: Optional[str] = None,
                                use_root_path: bool = True, visible_rule: Optional[Union[str, Callable[[BaseUIControl], bool]]] = None,
                                enabled: bool = True, control: Optional[BaseUIControl] = None,
                                always: bool = False) -> str:...

    def UnregisterAdaptiveControl(self, key_or_path: str):...

    def SetAdaptiveControlEnabled(self, key_or_path: str, enabled: bool):...

    def ClearAdaptiveControls(self):...

    def ListAdaptiveControlKeys(self) -> List[str]:...

    def InitAdaptiveControlsFromPaths(self, paths: Optional[List[str]], use_root_path: bool = True, clear: bool = True):...

    def InvalidateAdaptiveGeometry(self) -> None:...

    def RefreshAdaptiveGeometry(self, force: bool = False) -> bool:...

    def GetAdaptiveVisibleRects(self) -> List[tuple]:...

    def GetAdaptiveOcclusionPolygon(self) -> RectPolygon:...

    def DetectAdaptiveOccludedSlots(self, grid_x: int, grid_y: int, cols: int, rows: int, item_size: int,
                                    applied: bool = True) -> set:...

    def AvoidanceSuppressed(self) -> bool:...

    def OnRecipeDetailsShown(self) -> None:...

    def OnRecipeDetailsClosed(self) -> None:...

    def GetAdaptiveGeometryVersion(self) -> int:...

    def UpdateAllUI(self):...