# coding=utf-8

# ----------------------------------------------------------------------
#  cell.py is part of MoreEnoughItems.
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
配方树的一格（recipe_tree.json 的 cell 模板）。画布里的格子是动态建的、不挂绑定（MEI 的 ItemPanel 认的是主节点那块界面，
这里不是），内容全由脚本直接写：物品、右下数量、黄字合成次数、左上背包有几个、右上状态小方块、左下折叠了几格、紫点、暗一点、选中框。

同一个控件在池里反复用（换配方、折叠后重排只改内容和位置），每样东西记着上次写的值、没变就不碰引擎
（一次引擎调用约 0.1 毫秒，引擎结论 §25）。子控件第一次用到才取；取不到（刚建出来还没排好）这次跳过、下次再取
"""
from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.utils.text import native_str

_UNSET = object()


def short_count(count):  # type: (int) -> str
    """ 格子右下的数字：1 不写；四位以上缩写（1.5k、12k、3m），20 像素宽放得下 """
    count = int(count or 0)
    if count <= 1:
        return ""
    if count < 1000:
        return str(count)
    if count < 1000000:
        value, unit = count / 1000.0, "k"
    else:
        value, unit = count / 1000000.0, "m"
    text = ("%.1f" % value) if value < 10 else str(int(value))
    if text.endswith(".0"):
        text = text[:-2]
    return text + unit


class CellSpec(object):
    """
    一格要画成什么样（脚本按解算结果和布局算好，交给画布 / 菜单 / 汇总去写）：
    Target 点它时认谁（(种类, 签名或物品键)），Pos 位置，Render 物品渲染数据 (id, aux, 附魔, userData) 或 None，
    Count 右下数量（字）、CountColor 它的颜色（None 是白）、Crafts 黄字合成次数、Have 左上背包有几个、Fold 左下折叠了几格，
    Badge 右上小方块的颜色（None 不画）、Multi 左上紫色小方块、Dim 暗一点、Selected 选中框（各自的意思见 TreeConst.BadgeColors / MultiColor）
    """
    __slots__ = ("Target", "Pos", "Render", "Count", "CountColor", "Crafts", "Have", "Fold", "Badge", "Multi", "Dim",
                 "Selected")

    def __init__(self, target, pos=(0, 0), render=None, count="", count_color=None, crafts="", have="", fold="",
                 badge=None, multi=False, dim=False, selected=False):
        self.Target = target
        self.Pos = pos
        self.Render = render
        self.Count = count
        self.CountColor = count_color
        self.Crafts = crafts
        self.Have = have
        self.Fold = fold
        self.Badge = badge
        self.Multi = multi
        self.Dim = dim
        self.Selected = selected


class TreeCell(object):
    """ 一个格子控件。Target 是现在显示的是谁（点它时认它）；Index 是它在池里排第几（触摸回调的参数）"""

    WHITE = (1.0, 1.0, 1.0)

    def __init__(self, screen, control, index=0):
        self.Screen = screen
        self.Control = control
        self.Path = control.GetPath()
        self.Index = index
        self.Target = None
        self.__Cache = {}
        self.__Parts = {}

    def __Part(self, sub, cast):
        part = self.__Parts.get(sub)
        if part is None:
            control = self.Screen.GetBaseUIControl(self.Path + sub)
            if control is None:
                return None
            part = getattr(control, cast)() if cast else control
            self.__Parts[sub] = part
        return part

    def __Changed(self, name, value):
        if self.__Cache.get(name, _UNSET) == value:
            return False
        self.__Cache[name] = value
        return True

    def __Forget(self, name):
        self.__Cache.pop(name, None)

    def Button(self):  # type: () -> any
        return self.__Part(TreePath.CellButton, "asButton")

    # 整格
# ======================================================================================================================
    def SetVisible(self, on):  # type: (bool) -> None
        if self.__Changed("visible", bool(on)):
            self.Control.SetVisible(bool(on))

    def SetPos(self, pos):  # type: (tuple) -> None
        pos = (int(pos[0]), int(pos[1]))
        if self.__Changed("pos", pos):
            self.Control.SetPosition(pos)

    def Apply(self, spec):  # type: (CellSpec) -> None
        """ 照 spec 写一遍（只写变了的），并显示出来 """
        self.Target = spec.Target
        self.SetPos(spec.Pos)
        self.SetItem(spec.Render)
        self.__Label("count", TreePath.CellCount, spec.Count, spec.CountColor or self.WHITE)
        self.__Label("crafts", TreePath.CellCrafts, spec.Crafts)
        self.__Label("have", TreePath.CellHave, spec.Have)
        self.__Label("fold", TreePath.CellFold, spec.Fold)
        self.__Dot("badge", TreePath.CellBadge, spec.Badge)
        self.__Dot("multi", TreePath.CellMulti, TreeConst.MultiColor if spec.Multi else None)
        self.__Toggle("dim", TreePath.CellDim, spec.Dim)
        self.SetSelected(spec.Selected)
        self.SetVisible(True)

    def Hide(self):
        self.Target = None
        self.SetSelected(False)
        self.SetVisible(False)

    # 各个部件
# ======================================================================================================================
    def SetItem(self, render):  # type: (tuple or None) -> None
        """ render 是 (id, aux, 附魔, userData)；None 是空格子（藏起渲染器）"""
        key = (native_str(render[0]), int(render[1] or 0), bool(render[2])) if render else None
        if not self.__Changed("item", key):
            return
        renderer = self.__Part(TreePath.CellRenderer, None)
        if renderer is None:
            self.__Forget("item")
            return
        shown = False
        if key is not None:
            try:
                shown = bool(renderer.asItemRenderer().SetUiItem(key[0], key[1], key[2], render[3]))
            except Exception:  # noqa  有的东西渲染不了（minecraft:air 之类）：藏起渲染器
                shown = False
        renderer.SetVisible(shown)

    def SetSelected(self, on):  # type: (bool) -> None
        self.__Toggle("sel", TreePath.CellSel, on)

    def __Label(self, name, sub, text, color=None):
        text = native_str(text or "")
        if self.__Changed(name, text):
            label = self.__Part(sub, None)
            if label is None:
                self.__Forget(name)
                return
            if text:
                label.asLabel().SetText(text)
            label.SetVisible(bool(text))
        if color is not None and text and self.__Changed(name + ".color", tuple(color)):
            label = self.__Part(sub, None)
            if label is not None:
                label.asLabel().SetTextColor(tuple(color))
            else:
                self.__Forget(name + ".color")

    def __Toggle(self, name, sub, on):
        if self.__Changed(name, bool(on)):
            part = self.__Part(sub, None)
            if part is None:
                self.__Forget(name)
                return
            part.SetVisible(bool(on))

    def __Dot(self, name, sub, color):
        """ 上标（2×2 的白色小方块）：给了颜色就染上显示，None 就藏起来 """
        if not self.__Changed(name, tuple(color) if color else None):
            return
        part = self.__Part(sub, None)
        if part is None:
            self.__Forget(name)
            return
        if color:
            part.asImage().SetSpriteColor(tuple(color))
        part.SetVisible(bool(color))
