# ----------------------------------------------------------------------
#  block.pyi is part of MoreEnoughItems.
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
from typing import Any, Dict, List, Optional, Tuple

ROLE_IN: str
ROLE_OUT: str
ROLE_CAT: str
ROLES: Tuple[str, str, str]
POS_LIMIT: int


def parse_item(value: Any) -> Optional[Dict[str, Any]]: ...


def item_text(value: Any) -> unicode: ...


class BlockProp(object):
    INT: str
    CHOICE: str
    BOOL: str
    TEXT: str
    FIELD: str
    ITEM: str
    KINDS: Tuple[str, ...]

    Key: str
    Kind: str
    NameKey: str
    Default: Any
    Choices: List[Tuple[Any, str]]
    Min: int
    Max: int
    Step: int
    MaxLength: int
    Ascii: bool

    def __init__(self, key: str, kind: str, name_key: str = "", default: Any = None,
                 choices: Optional[List[Tuple[Any, str]]] = None, minimum: int = 0, maximum: int = 255,
                 step: int = 1, max_length: int = 32, ascii_only: bool = False) -> None: ...

    def Normalize(self, value: Any) -> Any: ...

    def Values(self) -> List[Any]: ...

    def LabelOf(self, value: Any) -> str: ...


class BlockType(object):
    TEMPLATE: Dict[Tuple[str, str], Any]
    Id: str
    NameKey: str
    ControlDef: str
    Size: Tuple[int, int]
    Limit: int
    Holds: bool
    Unit: str
    Props: List[BlockProp]
    Icon: Optional[str]
    SortIndex: int

    def __init__(self, block_id: str, name_key: str = "", control_def: str = "", size: Tuple[int, int] = (18, 18),
                 limit: int = 4, holds: bool = False, props: Optional[List[BlockProp]] = None,
                 icon: Optional[str] = None, sort_index: int = 0, unit: str = "") -> None: ...

    def SizeOf(self, block: Dict[str, Any]) -> Tuple[int, int]: ...

    def IsAnimated(self, block: Dict[str, Any]) -> bool: ...

    def Prop(self, key: str) -> Optional[BlockProp]: ...

    def Defaults(self) -> Dict[str, Any]: ...

    def Normalize(self, block: Dict[str, Any]) -> Dict[str, Any]: ...

    def Paint(self, view: Any) -> None: ...

    def Tick(self, view: Any, ticks: int) -> None: ...

    def ShownItem(self, view: Any) -> Any: ...
