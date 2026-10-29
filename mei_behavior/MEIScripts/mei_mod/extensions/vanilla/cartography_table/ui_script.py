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
制图的配方页：照原版制图台界面（cartography_screen.json 的 main_panel）—— 左边一列原料（上）、加号、附加原料（下），
原版的箭头、中间一张地图（cartography_table_map）、再一个箭头、大一号（26 × 26）的产物格。箭头与加号直接用原版的控件；
只有一样原料的（纸 → 空地图），下面那格空着。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder

from ..tools.pages import RecipePageScript


class CartographyUIScript(RecipePageScript):

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputPanel(self, _):
        return self.Render("input", self.Input(0))

    @RecipeBinder.Group(["mei_ui.recipe.additional"])
    def AdditionalPanel(self, _):
        return self.Render("additional", self.Input(1))

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputPanel(self, _):
        return self.Lore(self.Render("output", self.Recipe.GetPrimaryOutput()))
