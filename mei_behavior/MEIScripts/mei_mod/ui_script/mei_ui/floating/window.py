# coding=utf-8

# ----------------------------------------------------------------------
#  window.py is part of MoreEnoughItems.
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
from mod_log import logger

from MEIScripts.constants.ui import FloatConst, UiPathConst
from MEIScripts.mei_mod.state import PrefsManager
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import default_fraction, delta_of, fraction_of, room_of
from MEIScripts.utils.text import error_text

MEI = "mei"
QUERY = "query"
BUTTONS = (
    (MEI, UiPathConst.FloatMei, FloatConst.MeiTexture, FloatConst.MeiPressedTexture),
    (QUERY, UiPathConst.FloatQuery, FloatConst.QueryTexture, FloatConst.QueryPressedTexture),
)
""" 悬浮窗的两个按钮：(名字, 路径, 平时的贴图, 按下的贴图) """


class FloatWindow(object):
    """
    悬浮窗：一条横的，左边握把、右边 MEI 与查询两个按钮（查询只在触屏）。
    拖动是 JSON 原生的（input_panel 的 draggable + contained）：按在按钮上不拖，按在握把、边上拖（引擎结论 §32）。
    脚本只管三件事：按钮的点击；隔一会儿看一眼拖拽偏移，变了才记下（比例，全局一份）；显示时照记下的摆回去（没拖过：上方正中）
    """
    def __init__(self, main, on_click):
        self.MainNode = main
        self.OnClick = on_click  # fn(MEI / QUERY)：在按钮回调里调，调用方只记下
        self.Touch = False  # type: bool
        self.Buttons = {}  # type: dict  # 名字 -> 按钮控件：留着它，回调存在它身上
        self.Visible = False  # type: bool
        self.__PlaceTicks = 0  # type: int  # 刚显示：还要照记下的位置重摆几帧（覆盖层要一两帧才排好尺寸）
        self.__SaveTicks = 0  # type: int  # 还有几帧再看一眼拖拽偏移
        self.__Delta = None  # type: tuple or None  # 上次摆好或记下时的拖拽偏移：和它一样就是没拖过
        self.__Active = {}  # type: dict  # 名字 -> 上次写下去的「按下」样子
        self.__Failed = False  # type: bool  # 拖拽偏移读写失败过：只记一次日志

    def OnCreate(self, touch):  # type: (bool) -> None
        """
        开界面：挂按钮的点击回调，两个按钮写回平时的样子；查询只在触屏 —— 不在触屏时那一格（连同前面的间隔）收成 0 宽、
        悬浮窗跟着窄。两个方向都写（引擎结论 §22）
        """
        self.Touch = touch
        self.Buttons = {}
        self.__Active = {}
        self.__Delta = None
        self.__PlaceTicks = 0
        main = self.MainNode
        for name, path, _normal, _pressed in BUTTONS:
            control = main.GetUIControl(path)
            button = control.asButton() if control is not None else None
            if button is None:
                logger.warn("[MEI/float] 悬浮窗缺按钮 {}".format(path))
                continue
            button.AddTouchEventParams({"isSwallow": True})
            button.SetButtonTouchUpCallback(self.__UpHandler(name))
            self.Buttons[name] = button
            self.SetActive(name, False)
        slot = main.GetUIControl(UiPathConst.FloatQuerySlot)
        if slot is not None:
            slot.SetVisible(touch)
            slot.SetFullSize("x", {"absoluteValue": FloatConst.QuerySlotWidth if touch else 0})
        window = main.GetUIControl(UiPathConst.FloatWindow)
        if window is not None:
            window.SetFullSize("x", {"absoluteValue": self.__Size()[0]})

    def OnDestroy(self):
        """ 不在这里读拖拽偏移：界面正在关（注入的界面已经出栈），平时隔 0.5 秒记一次就够了 """
        self.__PlaceTicks = 0
        self.Visible = False

    def Show(self, on):  # type: (bool) -> None
        """ 显示 / 藏起来。藏之前记一下位置；从藏着到显示才照记下的摆（一直显示着就不动，免得和手指抢）"""
        window = self.MainNode.GetUIControl(UiPathConst.FloatWindow)
        if window is None:
            return
        if self.Visible and not on:
            self.Save()
        was = self.Visible
        window.SetVisible(on)
        self.Visible = on
        if on and not was:
            self.__PlaceTicks = FloatConst.PlaceTicks
            self.__SaveTicks = FloatConst.SaveTicks
            self.Place()

    def Relayout(self):
        """ 屏幕尺寸变了：显示着就照记下的比例重摆几帧 """
        if self.Visible:
            self.__PlaceTicks = FloatConst.PlaceTicks

    def Update(self):
        """ 每帧：刚显示、刚换尺寸的那几帧照记下的位置重摆；之后隔 SaveTicks 帧看一眼拖拽偏移，变了才记 """
        if not self.Visible:
            return
        if self.__PlaceTicks > 0:
            self.__PlaceTicks -= 1
            self.Place()
            return
        self.__SaveTicks -= 1
        if self.__SaveTicks <= 0:
            self.__SaveTicks = FloatConst.SaveTicks
            self.Save()

    def SetActive(self, name, on):  # type: (str, bool) -> None
        """ 按钮常亮成按下的样子（展开着、查找中）：换 default / hover 两张图的贴图 """
        if self.__Active.get(name) == on:
            return
        for button_name, path, normal, pressed in BUTTONS:
            if button_name != name:
                continue
            for sub in FloatConst.FaceSubs:
                face = self.MainNode.GetUIControl(path + sub)
                if face is not None:
                    face.asImage().SetSprite(pressed if on else normal)
        self.__Active[name] = on

    def Place(self):
        """ 照记下的位置摆（没拖过：上方正中）：记的是比例，换分辨率、换界面都还在同一处 """
        panel, parent = self.__Panel(), self.__ParentSize()
        if panel is None or parent is None:
            return
        room = room_of(parent, self.__Size())
        fraction = PrefsManager.GetFloatPosition() or default_fraction(FloatConst.DefaultAnchor, room,
                                                                       FloatConst.DefaultTopGap)
        delta = delta_of(fraction, room)
        try:
            panel.SetOffsetDelta(delta)
        except Exception as e:  # noqa
            self.__Fail("摆不回记下的位置", e)
            return
        self.__Delta = delta

    def Save(self):
        """ 拖过了（拖拽偏移和上次摆好、记下的不一样）才记成比例 """
        panel, parent = self.__Panel(), self.__ParentSize()
        if panel is None or parent is None:
            return
        try:
            delta = tuple(float(v) for v in panel.GetOffsetDelta())
        except Exception as e:  # noqa
            self.__Fail("读不到拖拽偏移", e)
            return
        last = self.__Delta
        if last is not None and abs(delta[0] - last[0]) < 0.5 and abs(delta[1] - last[1]) < 0.5:
            return
        self.__Delta = delta
        PrefsManager.SetFloatPosition(fraction_of(delta, room_of(parent, self.__Size())))

    # 内部
    # ==================================================================================================================
    def __UpHandler(self, name):
        def on_up(_args):
            self.OnClick(name)
        return on_up

    def __Panel(self):
        """ 悬浮窗那个 input_panel（拖拽偏移只在它上面读写）"""
        control = self.MainNode.GetUIControl(UiPathConst.FloatWindow)
        return control.asInputPanel() if control is not None else None

    def __ParentSize(self):  # type: () -> tuple or None
        """ 能拖的范围的外框：MEI 覆盖层（满屏）的尺寸；还没排好（0）给 None """
        root = self.MainNode.GetMEIRootControl()
        if root is None:
            return None
        try:
            width, height = root.GetSize()
        except Exception:  # noqa
            return None
        return (float(width), float(height)) if width > 0 and height > 0 else None

    def __Size(self):  # type: () -> tuple
        """ 悬浮窗自己的尺寸（JSON 里写死的；不在触屏时少查询那一格）"""
        width = FloatConst.Width if self.Touch else FloatConst.Width - FloatConst.QuerySlotWidth
        return float(width), float(FloatConst.Height)

    def __Fail(self, what, error):
        if not self.__Failed:
            self.__Failed = True
            logger.warn("[MEI/float] {}: {}".format(what, error_text(error)))
