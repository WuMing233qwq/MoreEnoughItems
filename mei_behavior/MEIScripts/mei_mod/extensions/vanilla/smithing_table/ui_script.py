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
锻造的配方页：照原版锻造台界面（smithing_table_2_screen.json 的 recipe_grid）—— 模板、物品、材料三格挨着，
原版的箭头（arrow_large，跨两列居中，锻造没有进度、不会动），产物格。纹饰的产物格和物品那一格同一组候选、同相位轮播。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder

from ..tools.pages import RecipePageScript


class SmithingUIScript(RecipePageScript):

    @RecipeBinder.Group(["mei_ui.recipe.template"])
    def TemplatePanel(self, _):
        return self.Render("template", self.Input(0))

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputPanel(self, _):
        return self.Render("input", self.Input(1))

    @RecipeBinder.Group(["mei_ui.recipe.material"])
    def MaterialPanel(self, _):
        return self.Render("material", self.Input(2))

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputPanel(self, _):
        return self.Lore(self.Render("output", self.Recipe.GetPrimaryOutput()))
