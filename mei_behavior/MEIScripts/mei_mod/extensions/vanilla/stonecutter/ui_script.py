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
切制的配方页：照原版切石机界面右半边（stonecutter_screen.json 的 top_half_stack_panel）—— 原料格、原版的箭头（arrow_large，
切石机本来就没有进度，箭头不动）、大一号（26 × 26）的产物格。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder

from ..tools.pages import RecipePageScript


class StonecutterUIScript(RecipePageScript):

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputPanel(self, _):
        return self.Render("input", self.Input(0))

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputPanel(self, _):
        return self.Lore(self.Render("output", self.Recipe.GetPrimaryOutput()))
