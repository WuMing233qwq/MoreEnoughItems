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
工作台配方页。槽位渲染契约在框架侧，此处只写布局差异。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder, RecipeUIScript
from MEIScripts.api.facades.ui.slots import render_slot, resolve_input_slot


class CraftingTableUIScript(RecipeUIScript):

    INPUT_PREFIX_LIST = ["mei_ui.recipe.input" + str(i) for i in range(9)]

    GRID_COLUMNS = 3
    """ 工作台是 3x3 —— 这是**本配方类型的界面事实**，不该由框架代为默认 """

    def __init__(self, recipe):
        RecipeUIScript.__init__(self, recipe=recipe)

        self.InputItemPanelControls = {}
        self.OutputItemPanelControl = None

    def InitControls(self):
        for i in range(9):
            self.InputItemPanelControls[i] = self.RecipeControl.GetChildByPath("/wrapper/content/input/{}".format(i))

        self.OutputItemPanelControl = self.RecipeControl.GetChildByPath("/wrapper/content/output/0")

    def OnDestroy(self):
        self.DestroyBindings()
        self.RecipesGridBind.ClearCache()

    def OnCreate(self):
        self.InitControls()

    @RecipeBinder.Group(INPUT_PREFIX_LIST)
    def InputItemPanelCallback(self, index):
        control = self.InputItemPanelControls[index]
        slot = resolve_input_slot(self.Recipe, index, self.GRID_COLUMNS)
        return render_slot(control, slot)

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputItemPanelCallback(self, index):
        _ = index
        return render_slot(self.OutputItemPanelControl, self.Recipe.GetPrimaryOutput())
