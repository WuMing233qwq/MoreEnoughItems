# ----------------------------------------------------------------------
#  transfer.pyi is part of MoreEnoughItems.
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

class TransferContext(object):
    PlayerId: str
    Side: str
    Extra: dict

    def __init__(self, player_id: str = "", side: str = "client", extra: Optional[dict] = None) -> None: ...


class TransferEntry(object):
    Slot: int
    ItemId: str
    AuxValue: int
    Count: int
    SourceId: str
    Handle: Any

    def __init__(self, slot: int, item_id: str, aux_value: int = 0, count: int = 1,
                 source_id: str = "", handle: Any = None) -> None: ...

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> TransferEntry: ...


class TransferPlan(object):
    Entries: List[TransferEntry]
    ClearSlots: List[int]

    def __init__(self, entries: Optional[List[TransferEntry]] = None,
                 clear_slots: Optional[List[int]] = None) -> None: ...

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> TransferPlan: ...


class TransferResult(object):
    Filled: int
    Failed: int
    Reason: str

    def __init__(self, filled: int = 0, failed: int = 0, reason: str = "") -> None: ...

    def is_ok(self) -> bool: ...

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> TransferResult: ...


class TransferSlot(object):
    Index: int
    Ingredient: Any
    Need: int
    Have: int
    Stack: Any
    Catalyst: bool

    def __init__(self, index: int, ingredient: Any, need: int, have: int = 0, stack: Any = None,
                 catalyst: bool = False) -> None: ...

    @property
    def Missing(self) -> int: ...


class TransferRequest(object):
    Recipe: Any
    CategoryId: str
    ScreenDef: str
    Slots: List[TransferSlot]
    Catalysts: List[TransferSlot]
    Times: int
    Max: bool
    Fits: bool

    def __init__(self, recipe: Any, category_id: str = "", screen_def: str = "",
                 slots: Optional[List[TransferSlot]] = None, catalysts: Optional[List[TransferSlot]] = None,
                 times: int = 1, wants_max: bool = False, max_times: Any = None, fits: bool = True) -> None: ...

    def MaxTimes(self) -> int: ...

    def Cell(self, index: int) -> Optional[TransferSlot]: ...

    def Missing(self) -> List[TransferSlot]: ...

    def Complete(self) -> bool: ...


class TransferError(object):
    Message: str
    Missing: List[TransferSlot]
    Blocking: bool

    def __init__(self, message: str = "", missing: Optional[List[TransferSlot]] = None,
                 blocking: bool = True) -> None: ...


class TransferHandler(object):
    GRID: Optional[Tuple[int, int]]
    CONSUMES: bool
    HINT: str

    def Check(self, request: TransferRequest) -> Optional[TransferError]: ...

    def Transfer(self, request: TransferRequest) -> Any: ...
