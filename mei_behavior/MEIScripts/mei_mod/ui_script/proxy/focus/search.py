# coding=utf-8

# ----------------------------------------------------------------------
#  search.py is part of MoreEnoughItems.
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
查一个点上的物品渲染器：查询时从扫描根往下递归找（不在后台静默收集）。

逐层 GetChildrenName 往下走 —— **不用 GetAllChildrenPath**：MEI 注入的别人家界面上它会让游戏直接退出（CLAUDE.md 引擎结论 §36），
网易自己的代码也只用逐层列。每个控件：

  1. 不可见（GetVisible 为假）：整棵子树跳过；
  2. 量矩形（GetGlobalPosition + GetSize）：有尺寸、又不含这一点 —— 整棵子树跳过；尺寸为 0 的（锚点之类）照样往下找；
  3. custom、名字像物品渲染器（item_named）、不大于 MAX_RENDERER_SIZE：读它显示的物品，不是空气就是它。
     别的 custom（悬停文字、耐久条、HUD 的心与饥饿条、快捷栏那一整块……）不读；
  4. 往子控件里找，**从后往前**（后画的在上面）。

**子控件可以伸出父控件的矩形**（JSON UI 不裁剪）：原版 common.inventory_panel 只有 88 宽，里面的背包 grid 162 宽、居中，
两边各伸出 37 —— 按第 2 条剪枝，背包最左、最右两列永远查不到，成了「死区」。所以分两遍：
第一遍照上面严格剪枝（快，绝大多数点在这一遍就找到）；没找到再找第二遍，矩形往外放宽 OVERFLOW_MARGIN 再判断要不要往下找
（读物品仍要渲染器自己的矩形含这一点）。点在空白处时两遍都找不到，第二遍只多看点附近的那些控件。

一次查询（两遍加起来）最多看 MAX_VISITS 个控件。这里不碰引擎模块、不认识 MEI 的业务：界面节点、扫描根、要跳过的子树都由调用方给
（UIScriptMain.FocusAt）
"""
from MEIScripts.utils.text import native_str

MAX_RENDERER_SIZE = 128
""" 渲染器边长上限：比它大的（纸娃娃、飞行物品的动画层）不当物品格 """

MAX_VISITS = 18000
""" 一次查询最多看这么多个控件（防一手：别人家的界面异常地大）。看到上限就停，记一行 """

OVERFLOW_MARGIN = 64.0
"""
第二遍把每个控件的矩形往外放宽多少像素再判断「这一点在不在它（伸出去的子控件）上」。
原版伸得最远的物品格是背包 grid 伸出 inventory_panel 的 37（扫过原版与网易全部界面 JSON 里写死的尺寸）；留到 64，差不多三格半
"""

CUSTOM = 1
""" SDK 的 UIControlType.Custom：GetBaseUIControl 时已经按类型问过一次引擎、记在控件的 ControlType 上，这里不再问 """

AIR_ITEMS = ("", "air", "minecraft:air")

RENDERER_NAMES = ("renderer", "output_slot")
"""
名字里不带 item、但确实是物品渲染器的：MEI 与蔚蓝格子里的 renderer；原版合成器、红石界面输出格的 output_slot
（`output_slot@common.item_renderer`，crafter_screen_pocket.json / redstone_screen.json —— 原版给 common.item_renderer 起的名字里
只有它不带 item；光标上拿着的那个 inventory_selected_icon 本来就不该认）
"""


def item_named(name):  # type: (str) -> bool
    """
    名字像不像物品渲染器：带 item（原版的 item_renderer、filtered_item_renderer，蔚蓝的 item_renderer）、
    但 flying_item_renderer 那种动画不算；或者是 RENDERER_NAMES 里的。HUD 的 heart_renderer、
    hotbar_renderer，格子里的 durability_bar、hover_text 这些 custom 都不像 —— 对它们读物品没验证过，不读
    """
    lowered = name.lower()
    return lowered in RENDERER_NAMES or ("item" in lowered and "flying" not in lowered)


def contains(rect, x, y, margin=0.0):  # type: (tuple, float, float, float) -> bool
    """ 点在矩形里（含左上、不含右下）；margin 是四边各往外放宽多少 """
    return rect[0] - margin <= x < rect[2] + margin and rect[1] - margin <= y < rect[3] + margin


def control_rect(control):  # type: (any) -> tuple or None
    """ 控件的全局矩形 (x0, y0, x1, y1)；没有控件、量不出来（控件正好被拆）、尺寸为 0 都给 None """
    if control is None:
        return None
    try:
        x, y = control.GetGlobalPosition()
        w, h = control.GetSize()
    except Exception:  # noqa
        return None
    if w <= 0 or h <= 0:
        return None
    return float(x), float(y), float(x) + float(w), float(y) + float(h)


HOVER_TEXT = "hover_text"
""" 原版格子的悬停文字控件名（ui_common.json：格子按钮的 hover/highlight/hover_text，custom 的 hover_text_renderer）"""


def nearby(node, path, name, up=3, depth=4, budget=40):  # type: (any, str, str, int, int, int) -> str or None
    """
    path 附近叫 name 的控件：从 path 的父控件起往上最多 up 层，每层在它底下 depth 层以内找（先近后远，看过的子树不重看），
    最多列 budget 次子控件；找到返回路径，没有给 None。只用 GetChildrenName（逐层列，引擎结论 §36）。
    原版格子的悬停文字和物品渲染器是表亲：…/container_item/item_cell/item/<渲染器> 与 …/container_item/<按钮>/hover/highlight/hover_text
    """
    seen = set()
    calls = [0]

    def children(parent):  # type: (str) -> list or None
        if calls[0] >= budget:
            return None
        calls[0] += 1
        try:
            names = node.GetChildrenName(parent)
        except Exception:  # noqa  控件正好被拆
            return []
        return [native_str(child) for child in (names or ()) if isinstance(child, basestring) and child]

    def search(parent, left):  # type: (str, int) -> str or None
        if parent in seen:
            return None
        seen.add(parent)
        kids = children(parent)
        if not kids:
            return None
        if name in kids:
            return parent + "/" + name
        if left <= 1:
            return None
        for kid in kids:
            found = search(parent + "/" + kid, left - 1)
            if found is not None or calls[0] >= budget:
                return found
        return None

    parts = (path or "").rstrip("/").split("/")
    for level in range(1, up + 1):
        if len(parts) - level < 2:
            break
        found = search("/".join(parts[:-level]), depth)
        if found is not None or calls[0] >= budget:
            return found
    return None


class FocusHit(object):
    """ 找到的渲染器：Path 控件路径、Rect 全局矩形 (x0, y0, x1, y1)、它显示的物品 """

    def __init__(self, path, rect, item_name, aux_value, enchanted):
        self.Path = path  # type: str
        self.Rect = rect  # type: tuple
        self.ItemName = item_name  # type: str
        self.AuxValue = aux_value  # type: int
        self.IsEnchanted = enchanted  # type: bool


class FocusSearch(object):
    """
    一次查询。节点只用 GetChildrenName / GetBaseUIControl，控件只用 GetVisible / GetGlobalPosition / GetSize /
    asItemRenderer / GetUiItem
    """

    def __init__(self, node, x, y, exclude=(), budget=MAX_VISITS, margin=OVERFLOW_MARGIN):
        self.Node = node
        self.X = float(x)
        self.Y = float(y)
        self.Exclude = set(path.rstrip("/") for path in exclude if path)  # type: set  # 跳过的子树（MEI 自己的覆盖层）
        self.Budget = budget  # type: int
        self.Visits = 0  # type: int  # 看了几个控件（两遍加起来）
        self.Exhausted = False  # type: bool  # 看到上限停了
        self.Loose = max(0.0, float(margin))  # type: float  # 第二遍放宽多少；0 就只找一遍
        self.Margin = 0.0  # type: float  # 这一遍放宽多少
        self.Retried = False  # type: bool  # 找了第二遍

    def Run(self, roots):  # type: (list) -> FocusHit or None
        """
        依次从每个扫描根往下找，第一个找到的就是；根本身不看（它是装内容的面板）。
        第一遍严格按矩形剪枝；没找到（也没看到上限）再放宽 Loose 找第二遍 —— 伸出父控件的子控件在这一遍找到
        """
        hit = self.__Pass(roots, 0.0)
        if hit is None and not self.Exhausted and self.Loose > 0:
            self.Retried = True
            hit = self.__Pass(roots, self.Loose)
        return hit

    def __Pass(self, roots, margin):  # type: (list, float) -> FocusHit or None
        self.Margin = margin
        for root in roots:
            hit = self.__Under((root or "").rstrip("/"))
            if hit is not None or self.Exhausted:
                return hit
        return None

    def __Under(self, path):  # type: (str) -> FocusHit or None
        for name in reversed(self.__Children(path)):
            child = path + "/" + name
            if child in self.Exclude:
                continue
            if self.Visits >= self.Budget:
                self.Exhausted = True
                return None
            self.Visits += 1
            control = self.__Control(child)
            if control is None or not self.__Visible(control):
                continue
            rect = control_rect(control)  # 尺寸为 0（或量不出来）给 None：这种不拿矩形剪枝，照样往下找
            if rect is not None:
                if not contains(rect, self.X, self.Y, self.Margin):
                    continue
                # 读物品要渲染器自己的矩形含这一点（第二遍放宽的只是「往不往下找」）
                if getattr(control, "ControlType", None) == CUSTOM and item_named(name) \
                        and rect[2] - rect[0] <= MAX_RENDERER_SIZE and rect[3] - rect[1] <= MAX_RENDERER_SIZE \
                        and contains(rect, self.X, self.Y):
                    hit = self.__Read(control, child, rect)
                    if hit is not None:
                        return hit
            hit = self.__Under(child)
            if hit is not None or self.Exhausted:
                return hit
        return None

    # 引擎调用（都接住异常：控件可能正好被拆）
    # ==================================================================================================================
    def __Children(self, path):  # type: (str) -> list
        try:
            names = self.Node.GetChildrenName(path)
        except Exception:  # noqa
            return []
        return [native_str(name) for name in (names or ()) if isinstance(name, basestring) and name]

    def __Control(self, path):
        try:
            return self.Node.GetBaseUIControl(path)
        except Exception:  # noqa
            return None

    @staticmethod
    def __Visible(control):  # type: (any) -> bool
        try:
            return bool(control.GetVisible())
        except Exception:  # noqa
            return False

    @staticmethod
    def __Read(control, path, rect):  # type: (any, str, tuple) -> FocusHit or None
        try:
            renderer = control.asItemRenderer()
            data = renderer.GetUiItem() if renderer is not None else None
        except Exception:  # noqa
            return None
        if not isinstance(data, dict):
            return None
        name = data.get("itemName")
        if not isinstance(name, basestring) or name in AIR_ITEMS:
            return None
        try:
            aux = int(data.get("auxValue") or 0)
        except (TypeError, ValueError):
            aux = 0
        return FocusHit(path, rect, native_str(name), aux, bool(data.get("isEnchanted")))
