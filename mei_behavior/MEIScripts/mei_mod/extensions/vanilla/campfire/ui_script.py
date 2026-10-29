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
营火烘烤的配方页：原料、点着的营火、熟的（不要合成条）。营火是纸娃娃渲染的方块模型（model.py），画不出来退回物品图标。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder

from ..tools.pages import RecipePageScript
from . import model

DOLL = "model/doll"
ICON = "model/icon"


class CampfireUIScript(RecipePageScript):

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputPanel(self, _):
        return self.Render("input", self.Input(0))

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputPanel(self, _):
        return self.Lore(self.Render("output", self.Recipe.GetPrimaryOutput()))

    def OnCreate(self):
        RecipePageScript.OnCreate(self)
        doll, icon = self.Find(DOLL), self.Find(ICON)
        shown = model.render(doll)
        # 两个方向都写（行控件会被复用，引擎结论 §22）
        if doll is not None:
            doll.SetVisible(shown)
        if icon is not None:
            icon.SetVisible(not shown)
            if not shown:
                model.render_icon(icon)
