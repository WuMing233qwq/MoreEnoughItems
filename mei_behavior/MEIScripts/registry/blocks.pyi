# ----------------------------------------------------------------------
#  blocks.pyi is part of MoreEnoughItems.
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
from typing import List, Optional

from MEIScripts.common.classes.types.block import BlockType


class __BlockRegistry(object):
    def Register(self, block_type: BlockType, owner: str = "") -> bool: ...

    def Unregister(self, block_id: str, owner: Optional[str] = None) -> bool: ...

    def UnregisterOwner(self, owner: str) -> int: ...

    def Get(self, block_id: str) -> Optional[BlockType]: ...

    def List(self) -> List[BlockType]: ...

    def Holds(self, block: dict) -> bool: ...

    def OwnerOf(self, block_id: str) -> Optional[str]: ...

    def Revision(self) -> int: ...

    def Reset(self) -> None: ...


BlockRegistry: __BlockRegistry
