# ----------------------------------------------------------------------
#  keys.pyi is part of MoreEnoughItems.
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
from typing import Any, Callable, Tuple

AUX_ANY: int
KEY_SEP: str
LIST: str
RECIPE: str


def make_key(item_id: str, aux: int = 0) -> Tuple[str, int]: ...
def key_to_str(key: Tuple[str, int]) -> str: ...
def key_from_str(text: str) -> Tuple[str, int]: ...


class Comparison(object):
    __slots__ = ("Predicate", "HashFn")

    Predicate: Callable[[Any, Any], bool]
    HashFn: Callable[[Any], Any]

    def __init__(self, predicate: Callable[[Any, Any], bool],
                 hash_fn: Callable[[Any], Any]): ...

    def equals(self, a: Any, b: Any) -> bool: ...
    def hash_of(self, stack: Any) -> Any: ...


DEFAULT: Comparison
