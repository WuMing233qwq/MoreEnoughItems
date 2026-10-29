# coding=utf-8

# ----------------------------------------------------------------------
#  pages.py is part of MoreEnoughItems.
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
原版扩展几个配方页共用的脚本底子：按格子名取控件、格子上的说明行、镜像格、重播 JSON 里的 clip 动画。
只是 Python 这一侧的一点便利 —— 每个类型都有自己的配方页脚本、自己命名空间的 JSON，布局照原版界面
（不做「一进一出」那种几个类型共用的界面）
"""
from MEIScripts.api.facades.ui.binding import RecipeUIScript
from MEIScripts.api.facades.ui.slots import render_slot
from MEIScripts.api.facades.utils import localize

CONTENT = "/wrapper/content/"


class RecipePageScript(RecipeUIScript):
    """
    格子在 JSON 里是 /wrapper/content/<格子路径>/0；格子路径的最后一段就是绑定组前缀 mei_ui.recipe.<名字> 的最后一段
    （镜像格是名字后面带数字，比如酿造台的 bottle0 ~ bottle2 都写 mei_ui.recipe.bottle）。
    ANIMATIONS 列出要重播的 clip 动画：(相对 content 的路径, 隔几拍重播一次)，节拍 0.2 秒 —— 和熔炉一样用接口播，
    不用 JSON 的 next 循环（grid 的子控件数一变，next 循环会成倍加速）
    """

    ANIMATIONS = ()

    def __init__(self, recipe):
        RecipeUIScript.__init__(self, recipe=recipe)
        self.SlotControls = {}  # 格子路径 -> 控件（第一次用到才取）
        self.Animated = []  # type: list  # [(控件, 隔几拍), ...]

    def Find(self, path):  # type: (str) -> any
        """ content 下面的一个控件（相对路径）；行控件还没接上给 None """
        return self.RecipeControl.GetChildByPath(CONTENT + path) if self.RecipeControl is not None else None

    def Slot(self, name):  # type: (str) -> any
        control = self.SlotControls.get(name)
        if control is None:
            control = self.Find(name + "/0")
            if control is not None:
                self.SlotControls[name] = control
        return control

    def Input(self, index):  # type: (int) -> any
        inputs = self.Recipe.GetInputs()
        return inputs[index] if index < len(inputs) else None

    def Lore(self, panel):  # type: (any) -> any
        """ 配方类上写了 LORE（.lang 的键）的，给这一格加一行说明 """
        lore = getattr(self.Recipe, "LORE", None)
        if lore and panel is not None:
            panel.SetLore(localize(lore))
        return panel

    def Render(self, name, slot, mirrors=()):  # type: (str, any, tuple) -> any
        """
        画一格。mirrors 是画同一样东西的别的格子：JSON 里写同一个绑定名前缀 —— 可见、数量、悬停文字、点击走同一组绑定，
        物品图标由格子面板一起设（ItemPanel.AddMirror）
        """
        panel = render_slot(self.Slot(name), slot)
        add = getattr(panel, "AddMirror", None)
        if add is not None:
            for other in mirrors:
                add(self.Slot(other))
        return panel

    def OnCreate(self):
        found = ((self.Find(path), every) for path, every in self.ANIMATIONS)
        self.Animated = [(control, every) for control, every in found if control is not None]

    def OnAnimTick(self, ticks):
        for control, every in self.Animated:
            if ticks % every == 0:
                control.StopAnimation()
                control.PlayAnimation()

    def OnDestroy(self):
        self.DestroyBindings()
