# coding=utf-8

# ----------------------------------------------------------------------
#  spec.py is part of MoreEnoughItems.
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
造物请求。描述「要造一个什么样的物品」，不是造好的物品。
"""
from MEIScripts.utils.slots import copy_slots


class ItemSpec(object):
    """
    追加物品用的构造参数，`ItemManager.AddItems()` 的入参

    ItemId    str       物品 id；引擎不认识也可以，见 Info
    AuxValue  int       特殊值；aux 变体就是同 id 不同 aux 的多个 spec
    Attr      ItemAttr  附魔/耐久/UserData 等
    ExtraData any       挂给消费方的自由数据，MEI 自己不解释
    Hidden    bool      是否隐藏；**落到旁表**，不写进造出来的 Item
    Info      ItemInfo  自带物品信息；给了就不问引擎
    HoverText str       自带悬浮文本；给了就不问引擎

    `Info` / `HoverText` 存在的理由: 自定义物品引擎根本不认识，
    `GetItemBasicInfo` 只会给空壳，名字都没有。不自带就等于造一个查不到也搜不到的东西。
    """

    __slots__ = ("ItemId", "AuxValue", "Attr", "ExtraData", "Hidden", "Info", "HoverText")

    def __init__(
            self,
            item_id,
            aux_value=0,
            attr=None,
            extra_data=None,
            hidden=False,
            info=None,
            hover_text=None
    ):  # type: (str, int, any, any, bool, any, str) -> None
        if not item_id:
            raise ValueError("item_id cannot be empty")
        self.ItemId = item_id  # type: str
        self.AuxValue = int(aux_value or 0)  # type: int
        self.Attr = attr  # type: any
        self.ExtraData = extra_data  # type: any
        self.Hidden = bool(hidden)  # type: bool
        self.Info = info  # type: any
        self.HoverText = hover_text  # type: str or None

    def copy(self):  # type: () -> ItemSpec
        """ 按槽位复制（utils/slots.py）：字段全部照搬（造物请求本来就是共享着用的），新加的字段自动带上 """
        return copy_slots(self)

    def __repr__(self):
        return "<ItemSpec {}:{}>".format(self.ItemId, self.AuxValue)
