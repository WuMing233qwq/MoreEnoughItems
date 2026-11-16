# coding=utf-8
# ----------------------------------------------------------------------
#  blocks.py is part of MoreEnoughItems.
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
"""
积木的登记表（对外 ctx.UI.Blocks）：玩家自制配方页能用哪几种积木。MEI 自带的由内置扩展 mei:user 登记，第三方的走同一个门面。

登记记在扩展名下，扩展卸载时装配器兜底撤掉；同一个 Id 不能登记两次、也不能覆盖别人的（和配方类型一样）。
排版里认不出种类的积木（登记它的模组没装了）由用到的地方跳过、原样留着 —— 这里只管表
"""
from collections import OrderedDict

from MEIScripts.common.classes.types.block import BlockType
from MEIScripts.utils.log import logger


def _ascii_id(value):  # type: (any) -> bool
    if not isinstance(value, basestring) or ":" not in value:
        return False
    try:
        value.encode("ascii") if isinstance(value, unicode) else value.decode("ascii")  # noqa  py2 的 unicode
    except UnicodeError:
        return False
    return True


class __BlockRegistry(object):  # noqa

    def __init__(self):
        self.__Types = OrderedDict()  # type: OrderedDict  # Id -> BlockType，按登记的先后
        self.__Owners = {}  # type: dict  # Id -> 扩展 ID
        self.__Revision = 0

    def Register(self, block_type, owner=""):  # type: (BlockType, str) -> bool
        """ 登记一种积木；不是 BlockType、Id 不带命名空间或不是 ASCII、没写 ControlDef、Id 已被占用都拒掉并记一行 """
        if not isinstance(block_type, BlockType):
            logger.warn("[MEI/blocks] 拒绝 {!r}：不是 BlockType".format(block_type))
            return False
        block_id = block_type.Id
        if not _ascii_id(block_id):
            logger.warn("[MEI/blocks] 拒绝 {!r}：Id 要带命名空间、只用 ASCII，形如 yourmod:gauge".format(block_id))
            return False
        if not block_type.ControlDef or "." not in block_type.ControlDef:
            logger.warn("[MEI/blocks] 拒绝 {}：ControlDef 要写 JSON 的 namespace.name".format(block_id))
            return False
        if block_id in self.__Types:
            logger.warn("[MEI/blocks] 积木 {} 已经登记过：同一个 Id 不能登记两次，也不能覆盖别人的".format(block_id))
            return False
        self.__Types[block_id] = block_type
        self.__Owners[block_id] = owner or ""
        self.__Revision += 1
        return True

    def Unregister(self, block_id, owner=None):  # type: (str, str) -> bool
        """ 撤掉一种；给了 owner 就只撤记在它名下的 """
        if block_id not in self.__Types:
            return False
        if owner is not None and self.__Owners.get(block_id, "") != (owner or ""):
            return False
        del self.__Types[block_id]
        self.__Owners.pop(block_id, None)
        self.__Revision += 1
        return True

    def UnregisterOwner(self, owner):  # type: (str) -> int
        """ 撤掉记在这个扩展名下的全部，返回撤了几种 """
        doomed = [block_id for block_id, who in self.__Owners.items() if who == (owner or "")]
        for block_id in doomed:
            self.Unregister(block_id)
        return len(doomed)

    def Get(self, block_id):  # type: (str) -> BlockType or None
        return self.__Types.get(block_id)

    def List(self):  # type: () -> list
        """ 全部积木，按 SortIndex、同序按登记的先后 """
        return sorted(self.__Types.values(), key=lambda block_type: block_type.SortIndex)

    def Holds(self, block):  # type: (dict) -> bool
        """
        排版里的这一块积木装不装东西（配方的格子按它编号）。种类认得的看 BlockType.Holds；认不得的（登记它的模组没装了）
        看它有没有角色 —— 只有装东西的积木才存角色，这样后面的格子编号不会往前挪、对上别的格子的内容
        """
        if not isinstance(block, dict):
            return False
        block_type = self.__Types.get(block.get("t"))
        if block_type is None:
            return "role" in block
        return block_type.Holds

    def OwnerOf(self, block_id):  # type: (str) -> str or None
        return self.__Owners.get(block_id)

    def Revision(self):  # type: () -> int
        """ 登记、撤销都加一：编辑器的控件池按它重排 """
        return self.__Revision

    def Reset(self):
        self.__Types = OrderedDict()
        self.__Owners = {}
        self.__Revision += 1


BlockRegistry = __BlockRegistry()
