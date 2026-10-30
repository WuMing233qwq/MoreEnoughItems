# coding=utf-8

# ----------------------------------------------------------------------
#  tool.py is part of MoreEnoughItems.
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
工具模式：拿起 MEI 的一样物品，再点一下放到别的模组登记过的控件上（drops.py，docs/architecture/modes.md）。一个界面一份，挂在主节点 main.Tool。

- 点格子（ModeManager.Intercept）只记下，下一帧才拿起（点击回调里不动控件）。PC 上拿起的物品跟着光标（follows_cursor 的宿主一直亮着），
  触屏上摆在点的那一格上、往上抬一点。都比格子里的图标大一圈（JSON 里写 24）。
- 拿着的时候整屏一层透明的捕获层（layer 96，悬浮窗在它上面）收下一下点击：点中登记过的放置目标 → 回调它，收下了就放下、
  不收就接着拿着（它说了原因就用引擎的 tip 消息提示）；点中 MEI 别的物品格 → 换成拿那一样；别的地方 → 放下，什么都不触发。
- **显隐全走绑定**（"#mei.tool.*"，每帧回读「拿着没有」）；绑定挂上之前、拆掉之后脚本把这几个控件写回藏着
  （界面状态跨开关存活，引擎结论 §22：关界面时拿着的，下次开不能留一层透明的捕获层挡住点击）。脚本只设图标、摆触屏那一格的位置。
- 模式按钮的颜色也在这里每帧对一下 ModeManager.Revision（变了才染），被盖住的界面露出来、收藏栏后建出来都对得上
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.common.classes.types import ItemStack
from MEIScripts.constants.texts import ModeText
from MEIScripts.constants.ui import ModeConst, UiPathConst
from MEIScripts.mei_mod.ui_script.controls.item.panel import render_args
from MEIScripts.mei_mod.ui_script.proxy.focus.search import control_rect
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

from .drops import DropTargets
from .manager import ModeManager, is_touch, stack_of

ViewBinder = clientApi.GetViewBinderCls()

MODE_HOVER = {
    ModeConst.Normal: native_str(ModeText.Normal),
    ModeConst.Tool: native_str(ModeText.Tool),
    ModeConst.Cheat: native_str(ModeText.Cheat),
}
""" 模式按钮的悬停文字（str，递给引擎的不能是 unicode，引擎结论 §2）"""

LIFT_PX = 6
""" 触屏上拿起的物品比原来那一格往上抬几像素（「拿起来」的样子）"""


def held_stack(stack):  # type: (any) -> ItemStack or None
    """ 拿起的那一份：只认物品（流体这类别的条目不算），一律是数量 1 的 ItemStack、还是物品表里的同一个 Item """
    if stack is None or getattr(stack, "KIND", "item") != "item":
        return None
    item = getattr(stack, "Item", None)
    return ItemStack(item, 1) if item is not None else None


class ToolHost(object):
    """ 一个界面一份；ModeManager 管模式，本类管拿起、放下与显示 """

    def __init__(self, main):
        self.MainNode = main
        self.Held = None  # type: any  # 拿着的 ItemStack；没拿着是 None
        self.Touch = False  # type: bool  # 开界面时定：触屏摆在格子上，PC 跟着光标
        self.Bindings = None  # type: ScreenBinder or None
        self.Capture = None  # type: any
        self.Painted = -1  # type: int  # 模式按钮染到了 ModeManager 的哪一版；-1：这次开界面还没染
        self.__Pending = None  # type: tuple or None  # 点击回调里记下的：("lift", stack, panel) / ("tap", x, y)，下一帧处理

    def OnCreate(self):
        """ 开界面：清掉上次的（拿着的东西不跨开关留着），挂显隐绑定、接捕获层的点击 """
        self.Held = None
        self.__Pending = None
        self.Painted = -1
        self.Touch = is_touch()
        self.HideAll()
        self.Bindings = ScreenBinder(self.MainNode.ScreenNode)
        for callback, name in ((self.IsHolding, "#mei.tool.capture"), (self.Follows, "#mei.tool.follow"),
                               (self.ShowsDesktop, "#mei.tool.desktop"), (self.ShowsTouch, "#mei.tool.touch")):
            self.Bindings.Bind(callback, ViewBinder.BF_BindBool, name)
        self.Bindings.Bind(self.ModeHoverText, ViewBinder.BF_BindString, ModeConst.HoverBinding)
        control = self.MainNode.GetUIControl(UiPathConst.ToolCapture)
        self.Capture = control.asButton() if control is not None else None
        if self.Capture is not None:
            self.Capture.AddTouchEventParams({"isSwallow": True})
            self.Capture.SetButtonTouchUpCallback(self.OnTap)

    def OnDestroy(self):
        self.Release()
        self.__Pending = None
        if self.Bindings is not None:
            self.Bindings.UnbindAll()
            self.Bindings = None
        self.HideAll()
        self.Capture = None

    def HideAll(self):
        """ 捕获层与两个拿起的物品写回藏着（绑定没挂着的时候；挂着时由绑定每帧写）"""
        for path in (UiPathConst.ToolCapture, UiPathConst.ToolDesktopItem, UiPathConst.ToolTouchItem):
            control = self.MainNode.GetUIControl(path)
            if control is not None:
                control.SetVisible(False)

    # 绑定（每帧回读）
# ======================================================================================================================
    def IsHolding(self):  # type: () -> bool
        return self.Held is not None

    def Follows(self):  # type: () -> bool
        """ PC 上跟光标的宿主一直亮着（藏着的 follows_cursor 控件跟不住光标）"""
        return not self.Touch

    def ShowsDesktop(self):  # type: () -> bool
        return self.Held is not None and not self.Touch

    def ShowsTouch(self):  # type: () -> bool
        return self.Held is not None and self.Touch

    @staticmethod
    def ModeHoverText():  # type: () -> str
        """ 模式按钮悬停时的字（mei_common.mode_hover_tip）：这一种模式是什么、点格子会怎样 """
        return MODE_HOVER.get(ModeManager.Current(), MODE_HOVER[ModeConst.Normal])

    # 入口
# ======================================================================================================================
    def RequestLift(self, stack, panel):  # type: (any, any) -> bool
        """ 点了一格（点击回调里）：只记下，下一帧拿起；不是物品的不拿 """
        held = held_stack(stack)
        if held is None:
            return False
        self.__Pending = ("lift", held, panel)
        return True

    def OnTap(self, args):
        """ 拿着的时候点了一下（捕获层）：只记下点在哪，下一帧处理 """
        try:
            self.__Pending = ("tap", float(args["TouchPosX"]), float(args["TouchPosY"]))
        except (KeyError, TypeError, ValueError):
            self.__Pending = ("tap", None, None)

    def Update(self):
        """ 每帧（主节点 OnTick）：模式按钮的颜色；不是工具模式了就放下；处理上一帧记下的拿起 / 点击 """
        if self.Painted != ModeManager.Revision and ModeManager.Paint(self.MainNode):
            self.Painted = ModeManager.Revision
        if ModeManager.Current() != ModeConst.Tool:
            self.Held = None
            self.__Pending = None
            return
        pending, self.__Pending = self.__Pending, None
        if pending is None:
            return
        try:
            if pending[0] == "lift":
                self.Lift(pending[1], pending[2])
            else:
                self.Drop(pending[1], pending[2])
        except Exception as e:  # noqa  这里抛出去会带走同一帧别的东西
            self.Release()
            logger.error("[MEI/tool] 拿起 / 放下出错: {}".format(error_text(e)))

    # 拿起、放下
# ======================================================================================================================
    def Lift(self, stack, panel=None):  # type: (any, any) -> bool
        held = held_stack(stack)
        if held is None:
            return False
        self.Held = held
        render = render_args(held.get_render_data())
        for path in (UiPathConst.ToolDesktopItem, UiPathConst.ToolTouchItem):
            renderer = self.MainNode.GetUIControl(path, "item_renderer")
            if renderer is not None:
                renderer.SetUiItem(*render)
        if self.Touch:
            self.__PlaceTouch(panel)
        return True

    def Drop(self, x, y):  # type: (float, float) -> str
        """
        点在 (x, y)：放置目标 → 回调，收下了放下（给 "drop"），不收接着拿着（"rejected"，说了原因就提示）；
        MEI 别的物品格 → 换成拿它（"swap"）；别的 → 放下（"release"）
        """
        held = self.Held
        if held is None:
            return ""
        if x is None or y is None:
            self.Release()
            return "release"
        main = self.MainNode
        target = DropTargets.Find(main.GetScreenDef(), main.ScreenNode.GetBaseUIControl, x, y, held)
        if target is not None:
            accepted, reason = DropTargets.Deliver(target, held, (x, y))
            if accepted:
                self.Release()
                return "drop"
            if reason:
                self.Tip(reason)
            return "rejected"
        panel = main.PanelAt(x, y)
        if self.Lift(stack_of(panel), panel):  # 和点格子时同一个认法：组头、不是物品的不拿；配方收藏拿它显示的那一样
            return "swap"
        self.Release()
        return "release"

    def Release(self):
        """ 放下（显隐由绑定跟着变）"""
        self.Held = None

    @staticmethod
    def Tip(message):  # type: (unicode) -> None
        """ 放置目标不收时说的原因：引擎的 tip 消息（物品栏上方）。开着容器界面时看不看得见没有验证过，看不见也只是少一句话 """
        logger.info("[MEI/tool] 放置目标不收: {}".format(native_str(message)))
        try:
            comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
            comp.SetTipMessage(native_str(message))
        except Exception as e:  # noqa
            logger.warn("[MEI/tool] 提示不出来: {}".format(error_text(e)))

    def __PlaceTouch(self, panel):
        """ 触屏：摆在点的那一格上、往上抬一点；量不出那一格就摆在屏幕正中 """
        item = self.MainNode.GetUIControl(UiPathConst.ToolTouchItem)
        layer = control_rect(self.MainNode.GetUIControl(UiPathConst.ToolLayer))
        if item is None or layer is None:
            return
        size = item.GetSize()
        rect = control_rect(getattr(panel, "Control", None))
        if rect is None:
            cx, cy = (layer[0] + layer[2]) / 2.0, (layer[1] + layer[3]) / 2.0
        else:
            cx, cy = (rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0 - LIFT_PX
        x = min(max(cx - size[0] / 2.0, layer[0]), layer[2] - size[0]) - layer[0]
        y = min(max(cy - size[1] / 2.0, layer[1]), layer[3] - size[1]) - layer[1]
        item.SetPosition((x, y))
