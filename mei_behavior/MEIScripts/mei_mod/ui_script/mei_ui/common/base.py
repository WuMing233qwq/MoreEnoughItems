# coding=utf-8

# ----------------------------------------------------------------------
#  base.py is part of MoreEnoughItems.
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

import time

import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst
from MEIScripts.mei_mod.ui_script.layout import GroupBorderCalculator, row_room
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.modules import SlotMapper
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys.binds import WheelTaken
from MEIScripts.utils import utilities
from MEIScripts.utils.events import EventListener
from MEIScripts.utils.text import error_text


class BaseItemsGridScript(object):
    """ 可复用的单分页 Grid UI 脚本骨架 """

    def __init__(self):
        self.ScreenNode = None
        self.MainNode = None
        self.Events = None  # type: EventListener or None  # 挂在客户端主系统上的事件，开界面时建
        self.GameComp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

        self.Layout = None
        self.AbsoluteRootWidth = 0

        self.__LastOccludedSlots = set()
        self.RowRoom = None  # type: int or None  # 被原版界面挡住后每行还剩几格（最少的那一行），悬浮窗的自动收起阈值看它
        self.__LastAvoidanceState = False
        self.__AdaptiveGeometryVersion = -1  # type: int
        self.__AdaptiveVisibleRects = []  # type: list

        self.__AvoidMinDeltaPx = 1
        self.__ShrunkBars = set()  # type: set  # 正在避让、宽度被写成绝对值的栏（"top" / "bottom"）

        self.Inited = False
        self.Shown = True  # 这一栏显示着（悬浮窗控制器按样子写，SetShown）：藏着时 grid 不自检

        self.RootControl = None
        self.ContentControl = None
        self.ContentControls = []
        self.WrapperControl = None
        self.TopControl = None
        self.BottomControl = None

        self.ItemsGridIns = None
        self.ItemsPage = None
        self.SlotMapper = SlotMapper()
        self.Timer = None

    def InitScript(self):
        if not self.Inited:
            self.MainNode = context.GetMainNode()
            self.ScreenNode = self.MainNode.ScreenNode
            self.Events = EventListener(clientApi.GetSystem(NameConst.NameSpace, NameConst.ClientSysName))
        self.Inited = True

        self.InitControls()
        self._InvalidateAdaptiveGeometrySnapshot()
        self.InitItemsList()
        self.UpdateUI(update_size=True, update_page=True)
        self.AddTimer()
        self.InitEvent()

    def DestroyScript(self):
        self.CancelTimer()
        # 先解绑再清缓存：反过来的话，清缓存会把暂停中的绑定先恢复一遍，紧接着又解掉
        for grid in self.GetItemGrids():
            grid.UnbindAll()
            grid.ClearItemPanels()
        self.DestroyEvent()

        self.DestroyControls()
        self.Inited = False

    def GetItemGrids(self):  # type: () -> list
        """
        这个脚本持有的全部 ItemsGrid：关界面时逐个解绑、定时自检都按它来。**多一个 grid 就要写进来** ——
        漏掉的那个关界面时不解绑，绑定留在跨开关存活的界面上，下次开界面同名再绑一遍
        （比如收藏栏下面的最近浏览：只收拾 ItemsGridIns 就会漏掉它）
        """
        return [self.ItemsGridIns] if self.ItemsGridIns is not None else []

    def CheckGrids(self):
        """ grid 自检（ItemsGrid.SelfCheck）：面板没建全又停住了就修，并记一行；自检本身出错也不能带走定时器 """
        now = time.time()
        for grid in self.GetItemGrids():
            grid.Shown = self.Shown  # 后来新建的 grid 也跟上这一栏现在显不显示
            try:
                message = grid.SelfCheck(now)
            except Exception as e:  # noqa
                message = "自检失败: {}".format(error_text(e))
            if message:
                logger.warn("[MEI/grid] {}: {}".format(grid.CollectionName, message))

    def DestroyControls(self):
        # 复位到 JSON 设计尺寸：同一批控件再 InitScript 时从干净的状态开始
        for role, control in self._Bars():
            self._RestoreBar(role, control, force=True)

    def InitEvent(self):
        self.Events.Listen("ScreenSizeChangedClientEvent", self.OnScreenSizeChanged)
        self.Events.Listen("MouseWheelClientEvent", self._OnWheel)

    def _OnWheel(self, args):
        # 按着修饰键、正好有滚轮类的快捷键（Ctrl+滚轮改收藏数量这类，hotkeys/binds.py）：这一下归快捷键，不翻页
        if WheelTaken():
            return
        self.OnMouseWheel(args)

    def DestroyEvent(self):
        if self.Events is not None:  # 没走过 InitScript（建界面时抛了）也能关
            self.Events.UnlistenAll()

    def OnScreenSizeChanged(self, _):
        self._InvalidateAdaptiveGeometrySnapshot()

        def _update():
            self._RefreshAdaptiveGeometrySnapshot(force=True)
            self.UpdateUI(update_size=True, update_page=True)
        self.GameComp.AddTimer(0.1, _update)

    def CheckUpdate(self, _=None):
        self._RefreshAdaptiveGeometrySnapshot()
        self.CheckOcclusion()
        self.CheckAvoidance()

    def RefreshAvoidance(self):
        """ 避不避让变了（从悬浮窗点开 / 收起）：几何快照作废，马上重算遮挡与上下栏，不等 0.2 秒一次的定时器 """
        if not self.Inited:
            return
        self._InvalidateAdaptiveGeometrySnapshot()
        self.CheckUpdate()

    def SetShown(self, on):  # type: (bool) -> None
        """
        这一栏显没显示（悬浮窗控制器每次换样子、开界面都写，两个方向都写，主节点 ShowSides 转过来）：
        藏着时 grid 不自检、不快速核对（引擎不建格子，问最后一格会 print error）；从藏着变成显示时当场 Revive
        """
        was, self.Shown = self.Shown, bool(on)
        for grid in self.GetItemGrids():
            grid.Shown = self.Shown
        if self.Shown and not was:
            self.Revive()

    def Revive(self):
        """
        这一栏刚从藏着变成显示（悬浮窗点开、从收着展开，SetShown）：每个 grid 当场补推行列数、重建格子（ItemsGrid.Revive），
        再按现在该不该避让重算一遍 —— 不等 grid 的自检（等它的话展开后要过好一会儿才复位）
        """
        if not self.Inited:
            return
        for grid in self.GetItemGrids():
            grid.Revive()
        self.RefreshAvoidance()

    def _InvalidateAdaptiveGeometrySnapshot(self):
        self.__AdaptiveGeometryVersion = -1
        self.__AdaptiveVisibleRects = []
        if self.MainNode:
            self.MainNode.InvalidateAdaptiveGeometry()

    def _RefreshAdaptiveGeometrySnapshot(self, force=False):
        if not self.MainNode:
            return False

        refreshed = self.MainNode.RefreshAdaptiveGeometry(force=force)
        version = self.MainNode.GetAdaptiveGeometryVersion()
        if refreshed or version != self.__AdaptiveGeometryVersion:
            self.__AdaptiveGeometryVersion = version
            self.__AdaptiveVisibleRects = self.MainNode.GetAdaptiveVisibleRects()
            return True
        return False

    def OnTimerCall(self):
        self.OnSearchTick()
        self.CheckUpdate()
        self.CheckGrids()

    def OnSearchTick(self):
        pass

    def AddTimer(self):
        self.OnTimerCall()
        # 立即执行一次 因为启动Timer需要先进行一次延迟
        self.Timer = self.GameComp.AddRepeatedTimer(0.2, self.OnTimerCall)

    def CancelTimer(self):
        if self.Timer:
            self.GameComp.CancelTimer(self.Timer)

    def CheckOcclusion(self):
        new_occluded = self.__ComputeOcclusion()
        if new_occluded != self.__LastOccludedSlots:
            self.__LastOccludedSlots = new_occluded
            self.RefreshSlots(recompute_occlusion=False)

    def RefreshSlots(self, recompute_occlusion=True):
        if not self.Layout or not self.ItemsPage or not self.ItemsGridIns:
            return

        if recompute_occlusion:
            self.__LastOccludedSlots = self.__ComputeOcclusion()

        self.BuildSlots(self.__LastOccludedSlots)
        self.UpdateIndexPanel()
        self.ItemsGridIns.ClearItemPanels()

    def BuildSlots(self, occluded):  # type: (set) -> None
        """ 把当前页的数据排进格子；收藏栏按行排版，覆写它 """
        capacity = self.Layout.Cols * self.GetGridRows()
        visible_capacity = max(1, capacity - len(occluded))
        self.ItemsPage.SetViewCapacity(visible_capacity)

        self.SlotMapper.Build(self.ItemsPage.current_items, capacity, occluded)
        all_edges = GroupBorderCalculator.CalculateFromSlots(self.SlotMapper.Slots, self.Layout.Cols)
        self.SlotMapper.ApplyBorders(all_edges)

    def GetGridRows(self):  # type: () -> int
        """ 物品 grid 的行数；收藏栏下面还有最近浏览，行数比整体布局少，覆写它 """
        return self.Layout.Rows

    def __ComputeOcclusion(self):
        """
        这会儿要藏的格子（被原版界面挡住的）。顺带记下每行还剩几格（RowRoom）—— 按几何算、不管这会儿避不避让：
        从悬浮窗点开时不避让，自动收起阈值还得看「要是避让会剩几格」，不然一点开就满足条件被收回去。
        悬浮窗管事时只避让「照样要避让」的那几块（配方页），由主节点的入口按 applied 挑
        """
        if not self.Layout or not self.ItemsGridIns:
            return set()

        cols, rows = self.Layout.Cols, self.GetGridRows()
        blocked = self._ComputeOccludedSlotsForGrid(
            self.ItemsGridIns.Control,
            cols,
            rows,
            self.Layout.ItemSize,
            applied=False,
        )
        self.RowRoom = row_room(blocked, cols, rows)
        if not self.MainNode.AvoidanceSuppressed():
            return blocked
        return self._ComputeOccludedSlotsForGrid(self.ItemsGridIns.Control, cols, rows, self.Layout.ItemSize, applied=True)

    def _ComputeOccludedSlotsForGrid(self, grid_control, cols, rows, item_size, applied=True):
        """ 按任意 Grid 配置计算被遮挡的槽位索引；applied 为假时不管这会儿避不避让，只看几何 """
        if not grid_control or not self.MainNode:
            return set()

        grid_pos_x, grid_pos_y = utilities.GetControlPosInt(grid_control)

        return self.MainNode.DetectAdaptiveOccludedSlots(
            grid_pos_x,
            grid_pos_y,
            cols,
            rows,
            item_size,
            applied=applied,
        )


    def _CollectVisibleContentRects(self):
        rects = []
        wrapper_rect = utilities.GetControlRectSize(self.WrapperControl) if self.WrapperControl else None

        if not self.__AdaptiveVisibleRects:
            self._RefreshAdaptiveGeometrySnapshot()

        for content_rect in self.__AdaptiveVisibleRects:
            if not content_rect:
                continue

            width = content_rect[1][0] - content_rect[0][0]
            height = content_rect[1][1] - content_rect[0][1]
            if width <= 0 and height <= 0:
                continue

            if wrapper_rect and utilities.RectContains(content_rect, wrapper_rect):
                continue

            rects.append(content_rect)

        return rects

    @staticmethod
    def _BuildRectByWidth(rect, width, anchor_mode="right"):
        if anchor_mode == "left":
            left = rect[0][0]
            return (left, rect[0][1]), (left + width, rect[1][1])

        right = rect[1][0]
        left = right - width
        return (left, rect[0][1]), (right, rect[1][1])

    def _CollectAvoidTargetsForControl(self, control, test_width):
        if not control:
            return []

        control_rect = utilities.GetControlRectSize(control)
        test_rect = self._BuildRectByWidth(control_rect, test_width, self.GetAvoidAnchorMode())

        targets = []
        for content_rect in self._CollectVisibleContentRects():
            if utilities.RectOverlap(test_rect, content_rect):
                targets.append(content_rect)
        return targets

    def _CalcAvoidedWidthForControl(self, control, base_width, gap_px=0):
        if not control or base_width is None:
            return base_width

        control_rect = utilities.GetControlRectSize(control)
        left_x = control_rect[0][0]
        right_x = control_rect[1][0]

        targets = self._CollectAvoidTargetsForControl(control, base_width)
        if not targets:
            return int(max(1, base_width))

        width_limits = []
        anchor_mode = self.GetAvoidAnchorMode()
        for rect in targets:
            if anchor_mode == "left":
                width_limits.append((rect[0][0] - gap_px) - left_x)
            else:
                width_limits.append(right_x - (rect[1][0] + gap_px))

        if not width_limits:
            return int(max(1, base_width))

        width = max(1, min(width_limits))
        return int(min(base_width, width))

    def GetBarNaturalWidth(self):  # type: () -> int or None
        """ 上下栏不避让时的宽度：栏是面板的 100%，面板是包装器减内边距，正好等于网格宽 """
        return self.Layout.GridWidth if self.Layout else None

    def _Bars(self):  # type: () -> list
        return [(role, control) for role, control in (("top", self.TopControl), ("bottom", self.BottomControl))
                if control]

    def CheckAvoidance(self):
        # 不避让时的宽度每次从当前布局算，不记历史观察值，见 docs/architecture/settings.md §6.1
        natural = self.GetBarNaturalWidth()
        if natural is None:
            return
        gap = self.GetAvoidGapPx()
        for role, control in self._Bars():
            width = self._CalcAvoidedWidthForControl(control, natural, gap)
            if width >= natural:
                self._RestoreBar(role, control)
                continue
            current = utilities.GetControlSizeInt(control)[0]
            if role not in self.__ShrunkBars or abs(width - current) >= self.__AvoidMinDeltaPx:
                self.SetControlWidth(control, int(width))
                self.__ShrunkBars.add(role)

    def _RestoreBar(self, role, control, force=False):
        """ 栏回到 JSON 里的设计尺寸（父控件宽的 100%），之后跟着布局自己变 """
        if not force and role not in self.__ShrunkBars:
            return
        self.__ShrunkBars.discard(role)
        set_full_size = getattr(control, "SetFullSize", None)
        if set_full_size:
            set_full_size("x", {"followType": "parent", "relativeValue": 1.0})
            return
        # 没有相对尺寸接口时退回按当前布局算出的绝对宽度
        natural = self.GetBarNaturalWidth()
        if natural is not None:
            self.SetControlWidth(control, natural)

    def UpdateUI(self, update_size=True, update_page=False):
        if not self.Layout or not self.ItemsPage:
            return

        if update_size:
            self._InvalidateAdaptiveGeometrySnapshot()
            self.UpdateControlsSize()
            self._RefreshAdaptiveGeometrySnapshot(force=True)
            self.CheckAvoidance()

        self.ItemsPage.Cols = self.Layout.Cols
        if update_page:
            self.ItemsPage.Rows = self.GetGridRows()
            self.ItemsPage.UpdatePage()

        self.RefreshSlots()
        self.UpdateIndexPanel()

    @staticmethod
    def SetControlWidth(control, width):
        return control.SetSize((width, utilities.GetControlSizeInt(control)[1]), True)

    def GetAvoidAnchorMode(self):
        return "right"

    def GetAvoidGapPx(self):
        return 0

    def InitControls(self):
        raise NotImplementedError

    def InitItemsList(self):
        raise NotImplementedError

    def UpdateControlsSize(self):
        raise NotImplementedError

    def UpdateIndexPanel(self):
        raise NotImplementedError

    def OnMouseWheel(self, args):
        raise NotImplementedError

