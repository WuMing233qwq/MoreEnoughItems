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

KIND_PLAYER: str
KIND_BLOCK: str


class TransferContext(object):
    PlayerId: str
    Side: str
    Dimension: int
    Position: Optional[Tuple[int, int, int]]
    Extra: dict

    def __init__(self, player_id: str = "", side: str = "client", dimension: int = 0,
                 position: Optional[Tuple[int, int, int]] = None,
                 extra: Optional[dict] = None) -> None: ...


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
    Kind: str
    Entries: List[TransferEntry]
    Position: Optional[Tuple[int, int, int]]
    Dimension: int
    ClearSlots: List[int]

    def __init__(self, kind: str = KIND_PLAYER, entries: Optional[List[TransferEntry]] = None,
                 position: Optional[Tuple[int, int, int]] = None, dimension: int = 0,
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
