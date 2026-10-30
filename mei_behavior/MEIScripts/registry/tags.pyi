# ----------------------------------------------------------------------
#  tags.pyi is part of MoreEnoughItems.
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
from typing import Any, Dict, FrozenSet, Optional, Tuple

ITEM: str
BLOCK: str
ENGINE_METHODS: Dict[str, Tuple[Tuple[str, str], ...]]
NAME_KEYS: Tuple[str, ...]


def entry_name(entry: Any) -> Optional[str]: ...


def names_of(result: Any) -> Optional[FrozenSet[str]]: ...


class __TagLookup(object):

    def ItemIds(self, tag: str) -> FrozenSet[str]: ...

    def BlockNames(self, tag: str) -> FrozenSet[str]: ...

    def EngineHas(self, kind: str = ...) -> bool: ...

    def Reset(self) -> None: ...

    def __Lookup(self, kind: str, tag: Any) -> FrozenSet[str]: ...

    def __Sync(self) -> None: ...

    def __Query(self, kind: str, tag: str) -> FrozenSet[str]: ...

    def __Method(self, kind: str) -> Any: ...

    @staticmethod
    def __Find(kind: str) -> Any: ...

    @staticmethod
    def __Fallback(kind: str, tag: str) -> FrozenSet[str]: ...

    def __Say(self, key: str, text: str) -> None: ...


TagLookup: __TagLookup
