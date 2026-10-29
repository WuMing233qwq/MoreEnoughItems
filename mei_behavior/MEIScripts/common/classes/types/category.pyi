# ----------------------------------------------------------------------
#  category.pyi is part of MoreEnoughItems.
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
from typing import Any, List, Optional, Tuple

from .item import ItemStack

PREVIEW_AUTO: str
PREVIEW_DEF_NAME: str


def derive_preview_def(control_def: str) -> str: ...


class RecipeCategory(object):
    Id: str
    NameKey: str
    Icon: Optional[Tuple[str, int]]
    ControlDef: str
    PreviewDef: str
    SortIndex: int
    Transfer: Optional[Any]
    _stations: List[Tuple[str, ItemStack]]

    def __init__(self, category_id: str, name_key: str = "",
                 icon: Optional[Tuple[str, int]] = None, control_def: str = "",
                 stations: Optional[List[ItemStack]] = None,
                 sort_index: int = 0, preview_def: Optional[str] = ...) -> None: ...

    @property
    def Stations(self) -> List[ItemStack]: ...

    def AddStation(self, stack: ItemStack, owner: str = "") -> bool: ...

    def AddStations(self, stacks: Optional[List[ItemStack]], owner: str = "") -> int: ...

    def RemoveStation(self, stack: ItemStack) -> bool: ...

    def RemoveStationsByOwner(self, owner: str) -> int: ...

    def SetStations(self, stacks: Optional[List[ItemStack]], owner: str = "") -> int: ...

    def SetTransferPolicy(self, policy: Optional[Any]) -> None: ...

    def CanTransfer(self, ctx: Any) -> bool: ...

    def __Find(self, stack: ItemStack) -> Optional[int]: ...
