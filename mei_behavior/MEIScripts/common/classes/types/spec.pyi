# ----------------------------------------------------------------------
#  spec.pyi is part of MoreEnoughItems.
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
from typing import Any, Optional

from .item import ItemAttr, ItemInfo


class ItemSpec(object):
    ItemId: str
    AuxValue: int
    Attr: Optional[ItemAttr]
    ExtraData: Any
    Hidden: bool
    Info: Optional[ItemInfo]
    HoverText: Optional[str]

    def __init__(self, item_id: str, aux_value: int = 0,
                 attr: Optional[ItemAttr] = None, extra_data: Any = None,
                 hidden: bool = False, info: Optional[ItemInfo] = None,
                 hover_text: Optional[str] = None) -> None: ...

    def copy(self) -> ItemSpec: ...
