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
燃料页：燃料格 + 火焰动画 + 两行字（烧多久、能烧几个物品）。
字在 OnCreate 里写一次（翻页、换类型都会重建脚本）；字的格式在 zh_CN.lang（mei.recipe.fuel.*），不写死在代码里。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder, RecipeUIScript
from MEIScripts.api.facades.ui.slots import render_slot
from MEIScripts.api.facades.utils import localize as _text

from ..furnace.fuels import SMELT_SECONDS

TEXT_BURN = "mei.recipe.fuel.burn"
TEXT_SMELTS = "mei.recipe.fuel.smelts"
TEXT_UNKNOWN = "mei.recipe.fuel.unknown"


def number(value):  # type: (float) -> str
    """ 80.0 -> 80、7.5 -> 7.5、0.75 -> 0.75 """
    return "{:g}".format(round(float(value), 2))


def lines_of(seconds):  # type: (float or None) -> tuple
    """ (第一行, 第二行)，unicode：烧多久、能烧几个物品（熔炉一个物品 10 秒）；认不出时长只写一行 """
    if not seconds:
        return _text(TEXT_UNKNOWN), u""
    return _text(TEXT_BURN).format(number(seconds)), _text(TEXT_SMELTS).format(number(seconds / SMELT_SECONDS))


class FuelUIScript(RecipeUIScript):

    ANIM_TICKS = 15
    """ 火焰 3 秒播一遍（节拍 0.2 秒），和熔炉页一样 """

    def __init__(self, recipe):
        RecipeUIScript.__init__(self, recipe=recipe)

        self.FlameActiveControl = None
        self.InputItemPanelControl = None
        self.BurnLabel = None
        self.SmeltsLabel = None

    def InitControls(self):
        get = self.RecipeControl.GetChildByPath
        self.FlameActiveControl = get("/wrapper/content/flame/full")
        self.InputItemPanelControl = get("/wrapper/content/input/0")
        self.BurnLabel = get("/wrapper/content/burn")
        self.SmeltsLabel = get("/wrapper/content/smelts")

    def OnAnimTick(self, ticks):
        if ticks % self.ANIM_TICKS or self.FlameActiveControl is None:
            return
        self.FlameActiveControl.StopAnimation()
        self.FlameActiveControl.PlayAnimation()

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputItemPanelCallback(self, _):
        inputs = self.Recipe.GetInputs()
        return render_slot(self.InputItemPanelControl, inputs[0] if inputs else None)

    def OnCreate(self):
        self.InitControls()
        getter = getattr(self.Recipe, "GetSeconds", None)
        burn, smelts = lines_of(getter() if callable(getter) else None)
        for control, text in ((self.BurnLabel, burn), (self.SmeltsLabel, smelts)):
            if control is not None:
                control.asLabel().SetText(text.encode("utf-8"))

    def OnDestroy(self):
        self.DestroyBindings()
