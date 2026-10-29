# coding=utf-8

# ----------------------------------------------------------------------
#  ui_script.py is part of MoreEnoughItems.
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
药水酿造的配方页：照原版酿造台界面（brewing_stand_screen.json 的 brewing_stand_pictogram，坐标照抄）——
左上燃料格（烈焰粉，只是画出来：驱动机器的东西不进配方本身）、燃料管道、气泡、燃料条，上面一格催化剂、它右边向下的进度箭头、
下面三瓶药水（上 1 下 3，下三是同一个物品 —— JSON 里三格写同一个绑定名前缀 mei_ui.recipe.bottle，物品图标由镜像格一起设），
产物照 JEI 放在右上。不带绑定的原版控件（管道、空箭头、空气泡、空燃料条）直接引用；进度箭头、气泡、满燃料条原版绑着酿造台的进度，
在 MeiBrewing 里照原版写一份、换成自己的 clip 动画。混合酿造的药水格、产物格各是三种瓶子（同相位轮播），格子上写一行说明。
"""
from MEIScripts.api.facades.registry import ItemFactory
from MEIScripts.api.facades.types import Ingredient
from MEIScripts.api.facades.ui.binding import RecipeBinder

from ..tools.pages import RecipePageScript

PICTO = "pictogram/"
FUEL = "minecraft:blaze_powder"


class BrewingUIScript(RecipePageScript):

    ANIMATIONS = ((PICTO + "arrow_full", 15), (PICTO + "bubbles_full", 5))
    """ 进度箭头 3 秒一遍、气泡 1 秒一遍（节拍 0.2 秒）"""

    @RecipeBinder.Group(["mei_ui.recipe.fuel"])
    def FuelPanel(self, _):
        return self.Render(PICTO + "fuel", Ingredient(ItemFactory.GetStacksFromIds([FUEL]), 1))

    @RecipeBinder.Group(["mei_ui.recipe.reagent"])
    def ReagentPanel(self, _):
        return self.Render(PICTO + "reagent", self.Input(1))

    @RecipeBinder.Group(["mei_ui.recipe.bottle"])
    def BottlePanel(self, _):
        return self.Lore(self.Render(PICTO + "bottle0", self.Input(0), (PICTO + "bottle1", PICTO + "bottle2")))

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputPanel(self, _):
        return self.Lore(self.Render(PICTO + "output", self.Recipe.GetPrimaryOutput()))
