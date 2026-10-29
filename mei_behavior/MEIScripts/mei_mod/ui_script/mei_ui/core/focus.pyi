# ----------------------------------------------------------------------
#  focus.pyi is part of MoreEnoughItems.
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
from typing import Any, Optional, Tuple

from MEIScripts.common.classes.types import Item
from MEIScripts.mei_mod.ui_script.proxy.focus.search import FocusHit


class FocusTarget(object):
    Pos: Optional[Tuple[float, float]]
    Hit: Optional[FocusHit]
    Panel: Any
    Item: Optional[Item]

    def __init__(self, pos: Optional[Tuple[float, float]] = ..., hit: Optional[FocusHit] = ...,
                 panel: Any = ..., item: Optional[Item] = ...) -> None: ...

    @property
    def Cell(self) -> Any: ...


def item_from_hit(hit: Optional[FocusHit]) -> Optional[Item]: ...
