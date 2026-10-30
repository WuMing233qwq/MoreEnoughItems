# ----------------------------------------------------------------------
#  base.pyi is part of MoreEnoughItems.
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
import abc

from mod.client.ui.controls.baseUIControl import BaseUIControl
from typing import Any, List, Tuple, Optional

from MEIScripts.common.classes.types import Item, Recipe, ItemStack

# 注意: 本存根**刻意不 import** ui_script 侧的类型 (UIMainNode / RecipesGridBind /
# ItemPanel). 运行时的 base.py 与 UI 解耦, 存根须与之一致,
# 否则会误导读者以为契约层仍依赖 UI. 绑定器耦合的实现层存根另见
# ui_script/mei_ui/recipe_details/modules/script_base.py.


class RecipeSource(object):
    __metaclass__ = abc.ABCMeta
    CategoryId: str = str
    CAN_ENUMERATE: bool = bool

    @abc.abstractmethod  # noqa
    def QueryByOutput(self, item: Item) -> List[Recipe]:...

    @abc.abstractmethod  # noqa
    def QueryByInput(self, item: Item) -> List[Recipe]:...

    def GetAll(self) -> List[Recipe]:...

    def IsAllComplete(self) -> bool:...


class BaseRecipeUIScript(object):
    """ 契约层: 纯声明, 零 UI 依赖. 绑定器耦合的实现见 ui_script 侧的 RecipeUIScript """
    __metaclass__ = abc.ABCMeta
    TYPE: str = str
    _Created: bool = False
    GridItemIndex: int = int
    # 运行期由 GetRecipeVisible 注入; 类型是 ui_script 侧的 RecipesGridBind,
    # 但契约层不 import 它(见文件头), 故标 Any
    RecipesGridBind: Any = None
    RecipeControl: Optional[BaseUIControl] = None

    _BindingsInited: bool = False
    _AutoBindingGroupIds: List[str] = []
    _AutoIndexedBindingKeys: List[tuple] = []

    def __init__(self, recipe: Recipe):
        self.Recipe = recipe

    @abc.abstractmethod  # noqa
    def InitBindings(self) -> None:...

    @abc.abstractmethod  # noqa
    def DestroyBindings(self) -> None:...

    @abc.abstractmethod  # noqa
    def OnCreate(self):...

    @abc.abstractmethod  # noqa
    def OnDestroy(self):...

    ANIM_TICK_INTERVAL: float

    def OnAnimTick(self, ticks: int) -> None:...

class SlotTarget(object):
    Slot: int

    def Put(self, stack: Any) -> bool: ...

    def Clear(self) -> bool: ...

    def Peek(self) -> Any: ...

    def Restore(self, previous: Any) -> bool: ...


class ItemSource(object):
    Id: str
    Priority: int

    def Collect(self, ctx: Any) -> List[Any]: ...

    def MoveTo(self, ctx: Any, handle: Any, count: int, target: SlotTarget) -> int: ...
