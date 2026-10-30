# ----------------------------------------------------------------------
#  search.pyi is part of MoreEnoughItems.
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
from typing import Dict, List, Optional, Tuple

from MEIScripts.common.classes.types import Item
from MEIScripts.libs.pinyin_lite import PinyinIndex

KIND_NAME: str
KIND_NAMESPACE: str
KIND_TEXT: str
KIND_EXACT: str
KIND_ID: str
PREFIXES: Dict[unicode, str]
NEGATE: unicode
ALTERNATIVE: unicode
COSTS: Dict[str, int]
DEFAULT_NAMESPACE: unicode


class Term(object):
    Kind: str
    Text: unicode
    Negate: bool

    def __init__(self, kind: str, text: unicode, negate: bool = False): ...

    def Key(self) -> Tuple[str, unicode]: ...


def parse_term(piece: unicode) -> Optional[Term]: ...


def parse_query(query: str) -> List[List[Term]]: ...


class __ItemSearchIndex(object):
    def __init__(self):
        self._engine: PinyinIndex = PinyinIndex()
        self._count: int = 0
        self._version: int = -1
        self._texts: Dict[Tuple[str, int], Tuple[unicode, unicode]] = {}

    def Rebuild(self, items: Optional[List[Item]] = None) -> int: ...

    def Search(self, query: str, include_hidden: bool = False) -> List[Item]: ...

    def Count(self) -> int: ...

    def Clear(self): ...

    def __ByName(self, query: unicode) -> List[Item]: ...

    def __Passes(self, segment: List[Term], item: Item, universe: List[Item], cache: Dict[Tuple[str, unicode], object]) -> bool: ...

    def __Matches(self, term: Term, item: Item, universe: List[Item], cache: Dict[Tuple[str, unicode], object]) -> bool: ...

    def __Hits(self, term: Term, universe: List[Item]) -> object: ...

    def __TextMatches(self, needle: unicode, item: Item) -> bool: ...

    def __RankByNames(self, items: List[Item], filters: List[List[Term]], cache: Dict[Tuple[str, unicode], object]) -> List[Item]: ...


ItemSearchIndex: __ItemSearchIndex
