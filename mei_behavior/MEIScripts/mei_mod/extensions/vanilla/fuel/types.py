# coding=utf-8

# ----------------------------------------------------------------------
#  types.py is part of MoreEnoughItems.
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
燃料页的「配方」：一样原料（燃料本身）、没有产物；烧多久放 Data（展示用，不进 Recipe.Id）。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class FuelRecipe(Recipe):
    """
    Data["seconds"] 是一个能烧多少秒（float，认不出是 None）。
    收藏它时没有产物，收藏栏画的、找回时重查的是那样燃料（bookmarks.recipe_entry 没有产物就取第一个原料）
    """

    __slots__ = ()

    def GetSeconds(self):  # type: () -> float or None
        return self.Data.get("seconds")
