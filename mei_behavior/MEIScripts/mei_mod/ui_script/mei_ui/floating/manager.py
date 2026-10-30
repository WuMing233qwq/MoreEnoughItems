# coding=utf-8

# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst
from MEIScripts.constants.ui import FloatConst, ItemsBrowserPath, UiPathConst
from MEIScripts.mei_mod.state.settings import (
    GetFloatThreshold, IsBookmarksVisible, IsFloatModeForced, IsFloatQuickCollapse,
)
from MEIScripts.mei_mod.ui_script.mei_ui.floating.find import FindMode
from MEIScripts.mei_mod.ui_script.mei_ui.floating.screen import open_screen, request_close
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import (
    ACTION_CLOSE_SCREEN, ACTION_OPEN_SCREEN, MODE_COLLAPSED, MODE_EXPANDED, MODE_OVERLAY, auto_mode, backdrop_click,
    initial_mode, mei_click, suppresses_avoidance,
)
from MEIScripts.mei_mod.ui_script.mei_ui.floating.window import MEI, QUERY, FloatWindow
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.manager import is_touch
from MEIScripts.utils.events import EventListener
from MEIScripts.utils.text import error_text

BACKDROP = "backdrop"


def layer_of(control):  # type: (any) -> int or None
    """ 控件的 GetLayer；没有控件、读不出、给的不是数（布尔也不算）给 None """
    try:
        layer = control.GetLayer() if control is not None else None
    except Exception:  # noqa
        return None
    if isinstance(layer, bool) or not isinstance(layer, (int, long, float)):
        return None
    return int(layer)


def side_layers(main):  # type: (any) -> tuple
    """
    两栏平时 / 悬浮窗管事时的层级（悬浮窗模式下调高）。值写在根控件
    （mei_proxy_ui / mei_float_ui）的变量 $mei_side_layer / $mei_float_side_layer 上，经两个记号控件带出来，
    再和同在 MEI 根下、层级为 0 的第三个记号做差 —— GetLayer 给的是相对父控件的值还是一路累加的值，差都一样。
    读不到（记号没了、给的不是数）就给 (None, None)：不动层级
    """
    values = [layer_of(main.GetUIControl(path))
              for path in (UiPathConst.SideLayerZero, UiPathConst.SideLayerNormal, UiPathConst.SideLayerFloat)]
    if None in values:
        return None, None
    return values[1] - values[0], values[2] - values[0]


class FloatController(object):
    """
    一个界面一份：收着（悬浮窗）/ 展开 / 从悬浮窗点开（带黑底）三种样子，悬浮窗与查找状态都归它。
    开界面时按设置定样子（每次都重新定，引擎结论 §22）；之后布局变了按自动收起阈值收放（docs/architecture/floating.md）
    """
    def __init__(self, main, kind):
        self.MainNode = main
        self.Kind = kind  # type: str  # state.KIND_*：支持的界面 / HUD / 强制兼容
        self.Mode = MODE_EXPANDED  # type: str
        self.Forced = False  # type: bool  # 设置「启用悬浮窗模式」：开界面时读
        self.Threshold = 0  # type: int  # 设置「自动收起阈值」：开界面时读
        self.QuickCollapse = False  # type: bool  # 设置「启用快速收起悬浮窗」：开界面时读，开着才点黑底收起
        self.Sidebar = True  # type: bool  # 设置「显示左侧栏」：开界面时读
        self.Touch = False  # type: bool
        self.Room = None  # type: list or None  # 上次看到的每侧每行还剩几格（显示着的几侧，被原版界面挡住的不算）
        self.Window = FloatWindow(main, self.OnClick)
        self.Find = FindMode(main, self.OnFindChanged)
        self.Backdrop = None  # type: any  # 黑底的按钮控件：留着它，回调存在它身上
        self.Events = None  # type: EventListener or None  # 屏幕尺寸变了要重摆悬浮窗
        self.SideLayers = (None, None)  # type: tuple  # 两栏平时 / 悬浮窗管事时的层级，开界面时从根控件的记号读（side_layers）
        self.__Clicks = []  # type: list  # 按钮回调里记下的点击：MEI / QUERY / BACKDROP，下一帧处理

    def OnCreate(self):
        """ 开界面：读设置、挂回调，按设置定样子并两个方向都写（MEI 根控件跨开关存活，上次的样子还在）"""
        self.Forced = IsFloatModeForced()
        self.Threshold = GetFloatThreshold()
        self.QuickCollapse = IsFloatQuickCollapse()
        self.Sidebar = IsBookmarksVisible()
        self.Touch = is_touch()
        self.__Clicks = []
        control = self.MainNode.GetUIControl(UiPathConst.Backdrop)
        self.Backdrop = control.asButton() if control is not None else None
        if self.Backdrop is not None:
            self.Backdrop.AddTouchEventParams({"isSwallow": True})
            self.Backdrop.SetButtonTouchUpCallback(self.OnBackdrop)
        # 悬浮窗上的查询那一格：只在触屏出
        self.Window.OnCreate(self.Touch)
        self.Find.OnCreate()
        self.Events = EventListener(clientApi.GetSystem(NameConst.NameSpace, NameConst.ClientSysName))
        self.Events.Listen("ScreenSizeChangedClientEvent", self.OnScreenSizeChanged)
        self.SideLayers = side_layers(self.MainNode)
        self.Room = self.RoomNow()
        self.Mode = initial_mode(self.Kind, self.Forced, self.Threshold, self.Room)
        self.Apply(quiet=True)
        if self.SuppressesAvoidance():
            # 两栏的脚本建在控制器之前，第一次算遮挡时还不知道该不该避让：这里重算一次
            self.RefreshAvoidance()

    def OnDestroy(self):
        if self.Events is not None:
            self.Events.UnlistenAll()
            self.Events = None
        self.Find.Exit()
        self.Window.OnDestroy()
        self.__Clicks = []

    def OnScreenSizeChanged(self, _args=None):
        self.Window.Relayout()

    # 入口：按钮回调里来的，只记下
# ======================================================================================================================
    def OnClick(self, name):
        self.__Clicks.append(name)

    def OnBackdrop(self, _args):
        self.__Clicks.append(BACKDROP)

    def ToggleFind(self):
        """ 顶栏的查询按钮 """
        self.__Clicks.append(QUERY)

    # 每帧（界面代理的 OnTick，排在触屏菜单后面）
# ======================================================================================================================
    def Update(self):
        """ 出错只记日志 —— 这里抛出去会带走同一帧别的代理 """
        try:
            clicks, self.__Clicks = self.__Clicks, []
            for click in clicks:
                self.Handle(click)
            self.Find.Update()
            self.Auto()
            self.Window.Update()
        except Exception as e:  # noqa
            logger.error("[MEI/float] 每帧处理失败: {}".format(error_text(e)))

    def Handle(self, click):
        if click == MEI:
            self.Act(mei_click(self.Kind, self.Mode))
        elif click == BACKDROP:
            self.Act(backdrop_click(self.Kind, self.Mode, self.QuickCollapse))
        elif click == QUERY and self.Touch:
            self.Find.Toggle()

    def Act(self, action):  # type: (str or None) -> None
        """
        点了之后：HUD 上开 MEI 自己的界面（不在游戏界面里展开；HUD 这份随即被盖住、收好，floating/hosts.py），
        在那个界面里关掉它（下一帧它自己出栈），别的就是换样子
        """
        if action == ACTION_OPEN_SCREEN:
            open_screen()
        elif action == ACTION_CLOSE_SCREEN:
            request_close(self.MainNode.ScreenNode)
        elif action is not None:
            self.SetMode(action)

    def Auto(self):
        """ 每侧每行还剩的格数变了（窗口尺寸变了、原版界面变宽变窄）就按阈值重新判断：排不下收起、排得下展开 """
        room = self.RoomNow()
        if room == self.Room:
            return
        self.Room = room
        self.SetMode(auto_mode(self.Mode, self.Kind, self.Forced, self.Threshold, room))

    def SetMode(self, mode):  # type: (str) -> None
        if mode == self.Mode:
            return
        suppressed = self.SuppressesAvoidance()
        self.Mode = mode
        self.Apply()
        if suppressed != self.SuppressesAvoidance():
            self.RefreshAvoidance()

    def Suspend(self):
        """ 界面被别的界面盖住（注入的界面，floating/hosts.py）：收成悬浮窗，顺带关菜单、退出查找状态，没处理的点击作废 """
        self.__Clicks = []
        if self.Mode != MODE_COLLAPSED:
            self.SetMode(MODE_COLLAPSED)
        else:
            menu = getattr(self.MainNode, "Menu", None)
            if menu is not None:
                menu.Close()
            self.Find.Exit()

    def Resume(self):
        """ 盖着的界面关了：照收着的样子两个方向重写一遍（覆盖层藏过，状态跨开关存活，引擎结论 §22）"""
        self.__Clicks = []
        self.Apply(quiet=True)

    def IsCollapsed(self):  # type: () -> bool
        return self.Mode == MODE_COLLAPSED

    def IsOverlay(self):  # type: () -> bool
        """ 从悬浮窗点开着（带黑底）"""
        return self.Mode == MODE_OVERLAY

    def SuppressesAvoidance(self):  # type: () -> bool
        """ 悬浮窗管事的时候 MEI 不避让原版界面（UIScriptMain.AvoidanceSuppressed）：悬浮窗模式、点开着、注入的与 MEI 自己的界面 """
        return suppresses_avoidance(self.Kind, self.Forced, self.Mode)

    def RoomNow(self):  # type: () -> list
        """
        显示着的几侧每行还剩几格（被原版界面挡住的不算，取最少的那一行，物品栏脚本 0.2 秒算一次遮挡时顺带算）：
        物品栏一直算，收藏栏开着才算；还没建起来、还没算过的不算
        """
        main, room = self.MainNode, []
        sides = [main.ItemsBrowserIns]
        if self.Sidebar:
            sides.append(main.ItemsSidebarIns)
        for script in sides:
            count = getattr(script, "RowRoom", None) if getattr(script, "Inited", False) else None
            if count is not None:
                room.append(count)
        return room

    def RefreshAvoidance(self):
        """ 点开 / 收起时避不避让变了：两侧马上重算（点开时不避让，原版界面压在黑底下面）"""
        self.MainNode.RefreshAvoidance()

    def Apply(self, quiet=False):
        """
        按 Mode 写显隐，两个方向都写：物品栏、收藏栏（还要看「显示左侧栏」）、黑底、悬浮窗与 MEI 按钮的按下样子；
        露着的两栏层级照样子对一下（悬浮窗管事时用根控件变量 $mei_float_side_layer，平时用 $mei_side_layer；EnsureLayer：
        一样就不写 —— SetLayer 要重算整个界面的层级，很贵）。收着时两栏藏着，层级不管。
        两栏显没显示也告诉脚本（主节点 ShowSides）：藏着时 grid 不自检，从藏着变成显示时当场补推（不等 1 秒的自检）。
        quiet 是开界面那一次；之后换样子时收起菜单、退出查找状态（它们指着的格子可能刚藏起来）
        """
        main = self.MainNode
        expanded = self.Mode != MODE_COLLAPSED
        if expanded:
            main.EnsureScripts()
        layer = self.SideLayers[1] if self.Mode == MODE_OVERLAY else self.SideLayers[0]
        for path, on, side in ((UiPathConst.RightWrapper, expanded, True),
                               (UiPathConst.LeftWrapper, expanded and self.Sidebar, True),
                               (UiPathConst.Backdrop, self.Mode == MODE_OVERLAY, False)):
            control = main.GetUIControl(path)
            if control is None:
                continue
            control.SetVisible(on)
            if side and on and layer is not None:
                self.EnsureLayer(control, layer)
        self.Window.Show(self.Mode != MODE_EXPANDED)
        self.Window.SetActive(MEI, self.Mode == MODE_OVERLAY)
        sides = getattr(main, "ShowSides", None)
        if callable(sides):
            sides(expanded, expanded and self.Sidebar)
        if quiet:
            return
        menu = getattr(main, "Menu", None)
        if menu is not None:
            menu.Close()
        self.Find.Exit()

    def EnsureLayer(self, control, layer):  # type: (any, int) -> bool
        """
        一栏的层级对成 layer：现在就是它就不写（GetLayer 和零点记号做差，同 side_layers），读不出才照写。返回写没写。
        SetLayer 要重算整个界面的层级（开着 MEI 的工作台两万多个控件），能不调就不调：两栏生下来的层级就是它们最常用的那一档
        （支持的界面是平时那一档、别的界面是悬浮窗那一档），只有支持的界面在「照常展开」与「从悬浮窗点开」之间换的那一下才真写
        """
        zero = layer_of(self.MainNode.GetUIControl(UiPathConst.SideLayerZero))
        now = layer_of(control)
        if zero is not None and now is not None and now - zero == layer:
            return False
        control.SetLayer(layer)
        return True

    def OnFindChanged(self, active):  # type: (bool) -> None
        """ 查找状态变了：两个查询按钮跟着变样子（悬浮窗的换贴图，顶栏的图标换颜色）"""
        self.Window.SetActive(QUERY, active)
        color = FloatConst.IconActiveColor if active else FloatConst.IconColor
        for sub in FloatConst.IconSubs:
            icon = self.MainNode.GetUIControl(ItemsBrowserPath.FindButton + sub)
            if icon is not None:
                try:
                    icon.asImage().SetSpriteColor(color)
                except Exception:  # noqa  图标还没建（物品栏没开）
                    pass
