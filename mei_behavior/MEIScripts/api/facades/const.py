# coding=utf-8

# ----------------------------------------------------------------------
#  const.py is part of MoreEnoughItems.
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
常量：命名空间、查询方向、UI 路径与集合名。
"""
from MEIScripts.constants.codes import NameConst, QueryConst, TagConst
from MEIScripts.constants.ui import (
    BindingConst, CollectionConst, ItemsSidebarPath, PanelProtoConst,
    RecipeDetailsPath, UiPathConst,
)

__all__ = [
    "BindingConst", "CollectionConst", "ItemsSidebarPath", "NameConst",
    "PanelProtoConst", "QueryConst", "RecipeDetailsPath", "TagConst", "UiPathConst",
]


class ConstFacade(object):
    """ ctx.Const """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
