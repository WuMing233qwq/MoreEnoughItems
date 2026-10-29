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
熔炉配方页，含火焰与箭头的循环动画。
"""
from MEIScripts.api.facades.ui.binding import RecipeBinder, RecipeUIScript
from MEIScripts.api.facades.ui.slots import render_slot

from .fuels import fuel_ingredient


class FurnaceUIScript(RecipeUIScript):

    ANIM_TICKS = 15
    """
    重播动画的节拍数。节拍是 0.2 秒一次 ⇒ 15 拍 = 3 秒，与 clip 动画的 duration 对齐。

    原先是自己起一个 3 秒的重复 timer；改走框架的 `OnAnimTick` 之后
    **整页只有一个 timer**，不再是每个配方行一个。
    """

    def __init__(self, recipe):
        RecipeUIScript.__init__(self, recipe=recipe)

        self.FlameActiveControl = None
        self.ArrowActiveControl = None
        self.InputItemPanelControl = None
        self.OutputItemPanelControl = None
        self.FuelItemPanelControl = None

    def InitControls(self):
        self.ArrowActiveControl = self.RecipeControl.GetChildByPath("/wrapper/content/arrow/active")
        self.FlameActiveControl = self.RecipeControl.GetChildByPath("/wrapper/content/flame/full")
        self.InputItemPanelControl = self.RecipeControl.GetChildByPath("/wrapper/content/input/0")
        self.OutputItemPanelControl = self.RecipeControl.GetChildByPath("/wrapper/content/output/0")
        self.FuelItemPanelControl = self.RecipeControl.GetChildByPath("/wrapper/content/fuel/0")

    def OnAnimTick(self, ticks):
        """ 每 ANIM_TICKS 拍重播一次火焰与箭头 """
        if ticks % self.ANIM_TICKS:
            return
        # 解释一下这里为什么不使用JSON UI的next属性循环播放动画 因为我发现在Grid的子控件数量改变时 会导致动画的速度成倍加快
        # 但是很神奇的是 使用接口播放动画没有这个问题
        self.FlameActiveControl.StopAnimation()
        self.FlameActiveControl.PlayAnimation()
        self.ArrowActiveControl.StopAnimation()
        self.ArrowActiveControl.PlayAnimation()

    @RecipeBinder.Group(["mei_ui.recipe.fuel"])
    def FuelItemPanelCallback(self, _):
        # 燃料不在配方里（驱动机器的东西不是配方的内容），问熔炉扩展的燃料表 —— 只给显示
        return render_slot(self.FuelItemPanelControl, fuel_ingredient())

    @RecipeBinder.Group(["mei_ui.recipe.input"])
    def InputItemPanelCallback(self, _):
        inputs = self.Recipe.GetInputs()
        slot = inputs[0] if inputs else None
        return render_slot(self.InputItemPanelControl, slot)

    @RecipeBinder.Group(["mei_ui.recipe.output"])
    def OutputItemPanelCallback(self, _):
        return render_slot(self.OutputItemPanelControl, self.Recipe.GetPrimaryOutput())

    def OnCreate(self):
        self.InitControls()

    def OnDestroy(self):
        # 不再需要撤 timer: 节拍归配方详情页统一管，页面关掉它自己就停了
        self.DestroyBindings()
