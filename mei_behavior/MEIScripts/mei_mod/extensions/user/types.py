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
玩家在 MEI 编辑器里记的配方。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class UserRecipe(Recipe):
    """
    一条自制配方。Id 是 "mei:/user/<存档里的配方 Id>"（build.recipe_key）—— 不按内容算：玩家改了数量、换了原料还是这一条，
    收藏、置顶跟着它走。Inputs / Outputs / Catalysts 按页面里同一角色的格子排（空格是 Ingredient([])），第一个产物是主产物。
    Data：uid（存档里的配方 Id）、page（页面 Id）、f（数值字段）、note（备注）—— 只是展示，不进 Id
    """

    __slots__ = ()
