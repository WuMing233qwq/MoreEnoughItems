# coding=utf-8

# ----------------------------------------------------------------------
#  canvas.py is part of MoreEnoughItems.
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
配方树的画布：视口、三层拖动、四个控件池、分帧画。

**拖动照网易成就界面**（JSON 原生拖拽，引擎结论 §32）：cut（视口，clips_children）→ dragpanel（居中在视口里）→
canvas（可拖的 input_panel，contained）。画布 C 比视口 V 大时 canvas 的大小 I = C、dragpanel 的大小 D = 2I − V，
拖拽偏移 d 夹在 [0, I − V]：d = I − V 时看到画布的左上，d = 0 时看到右下；画布比视口小时整块挪到中间（content 的偏移）。
画布里一点 p 在视口里的位置 s = p + 居中偏移 + d + V − I —— 重排之后按它把同一格摆回原处，视野不跳。

**控件池**：格子、工作方块的框、原料组的框、连线各一个池，重排只挪位置、改内容，不删不建；不够才建（CreateChildControl，
一批不刷新、这一帧建完 UpdateScreen 一次），多出来的藏起来。**分帧画**：建控件、写内容排成一串小活，每帧限时做一段；
一帧做不完就先藏起整块画布、写「绘制中」，做完一起显示 —— 不会看到画了一半的树。

**点格子**：格子盖着一层按钮（触摸回调，不吞事件：按在格子上也能拖）。按下记位置与拖拽偏移，松手比一下，动过就是在拖、不算点
"""
import collections
import time

from mod_log import logger

from MEIScripts.constants.texts import TreeText
from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.utils.text import error_text, native_str

from .cell import TreeCell

KIND_CELL = "cell"
KIND_WS = "ws"
KIND_ING = "ing"
KIND_LINE = "line"
DEFS = {KIND_CELL: TreeConst.CellDef, KIND_WS: TreeConst.WsFrameDef, KIND_ING: TreeConst.IngFrameDef,
        KIND_LINE: TreeConst.LineDef}
PREFIX = {KIND_CELL: "n", KIND_WS: "w", KIND_ING: "g", KIND_LINE: "l"}

CLICK_SLOP = 4
""" 按下到松手动了几像素以上就算拖，不算点 """

VIEW_FRAMES = 3
""" 改完画布大小后这么多帧里，拖拽偏移被引擎按旧大小夹过就再写一遍；最后一帧还对不上（大小没生效、偏移被夹了）记一行警告 """


def set_size(control, size):  # type: (any, tuple) -> None
    """
    改控件的大小：**用 SetFullSize 写绝对值**，不用 SetSize —— SetSize 是旧接口，只改当前的值、不改尺寸规则，
    JSON 里写相对尺寸（100%）的控件下一次排版就被拉回去（引擎结论 §28 grid 那次同一类；大树「偏下、拉不到剩下的」多半就是它）。
    悬浮窗、成就界面改尺寸也都用 SetFullSize
    """
    control.SetFullSize("x", {"absoluteValue": int(size[0])})
    control.SetFullSize("y", {"absoluteValue": int(size[1])})


class Scene(object):
    """ 一版画面：Cells [CellSpec]、WsFrames [(x, y)]、IngFrames [((x, y), (w, h))]、Lines [(x, y, w, h)]、Size 画布大小 """
    __slots__ = ("Cells", "WsFrames", "IngFrames", "Lines", "Size")

    def __init__(self, size=(0, 0)):
        self.Cells = []  # type: list
        self.WsFrames = []  # type: list
        self.IngFrames = []  # type: list
        self.Lines = []  # type: list
        self.Size = (int(size[0]), int(size[1]))

    def Positions(self):  # type: () -> dict
        return dict((spec.Target, spec.Pos) for spec in self.Cells)


class TreeCanvas(object):
    """ on_click(target, cell)：点了画布上的一格 """

    def __init__(self, screen, on_click):
        self.Screen = screen
        self.OnClick = on_click
        get = screen.GetBaseUIControl
        self.Cut = get(TreePath.Cut)
        self.Drag = get(TreePath.DragPanel)
        self.CanvasControl = get(TreePath.Canvas)
        self.Input = self.CanvasControl.asInputPanel() if self.CanvasControl is not None else None
        self.Content = get(TreePath.Content)
        self.Busy = get(TreePath.Busy)
        self.Parents = {KIND_CELL: get(TreePath.Cells), KIND_WS: get(TreePath.Frames), KIND_ING: get(TreePath.Frames),
                        KIND_LINE: get(TreePath.Lines)}
        self.Pools = dict((kind, []) for kind in DEFS)
        self.Scene = None  # type: Scene or None  # 正在显示的那一版
        self.Pending = None  # type: Scene or None  # 正在画的那一版
        self.Anchor = None  # type: tuple or None  # (锚点 target, 它在视口里的位置, 根在视口里的位置)：画完按它摆视野
        self.Jobs = collections.deque()
        self.JobsTotal = 0  # type: int
        self.Hidden = False  # type: bool
        self.Inner = (0, 0)  # type: tuple  # canvas 的大小 I
        self.Outer = (0, 0)  # type: tuple  # dragpanel 的大小 D = 2I − V
        self.Shift = (0, 0)  # type: tuple  # 画布比视口小时 content 的居中偏移
        self.View = (0, 0)  # type: tuple  # 视口大小 V
        self.Wanted = None  # type: tuple or None  # 要写的拖拽偏移（改完大小后再写几帧）
        self.WantedFrames = 0  # type: int
        self.Selected = None  # type: tuple or None
        self.Touch = None  # type: tuple or None  # 按下时 (池序号, x, y, 拖拽偏移)
        self.__Ready = None not in (self.Cut, self.Drag, self.Input, self.Content) and None not in self.Parents.values()
        if not self.__Ready:
            logger.error("[MEI/tree] 配方树的画布控件不全，画不了")

    # 画
# ======================================================================================================================
    def Draw(self, scene, anchor=None):  # type: (Scene, any) -> None
        """
        排一版画面，分帧画完再显示。anchor 是要摆回原处的那一格的 target（找不到退回根）；
        还没画过时根摆在视口上方正中
        """
        if not self.__Ready:
            return
        self.Anchor = self.__Capture(anchor)
        self.Pending = scene
        self.Jobs.clear()
        need = {KIND_CELL: len(scene.Cells), KIND_WS: len(scene.WsFrames), KIND_ING: len(scene.IngFrames),
                KIND_LINE: len(scene.Lines)}
        for kind, count in need.items():
            for index in range(len(self.Pools[kind]), count):
                self.Jobs.append((self.__Create, (kind, index)))
        for index, spec in enumerate(scene.Cells):
            self.Jobs.append((self.__ApplyCell, (index, spec)))
        for index, pos in enumerate(scene.WsFrames):
            self.Jobs.append((self.__ApplyFrame, (KIND_WS, index, pos, None)))
        for index, (pos, size) in enumerate(scene.IngFrames):
            self.Jobs.append((self.__ApplyFrame, (KIND_ING, index, pos, size)))
        for index, rect in enumerate(scene.Lines):
            self.Jobs.append((self.__ApplyFrame, (KIND_LINE, index, rect[:2], rect[2:])))
        for kind, count in need.items():
            self.Jobs.append((self.__HideRest, (kind, count)))
        self.Jobs.append((self.__Finish, (scene,)))
        self.JobsTotal = len(self.Jobs)

    def IsDrawing(self):  # type: () -> bool
        return bool(self.Jobs)

    def Tick(self, budget_ms):  # type: (float) -> bool
        """ 每帧：做一段活（限时），补写拖拽偏移。这一版画完了返回 True（只在画完的那一帧）"""
        self.__KeepView()
        if not self.Jobs:
            return False
        deadline = time.time() + budget_ms / 1000.0
        created = False
        while self.Jobs:
            func, args = self.Jobs.popleft()
            try:
                created = func(*args) is True or created
            except Exception as e:  # noqa  一格写坏了不能让整版停住
                logger.error("[MEI/tree] 画配方树出错: {}".format(error_text(e)))
            if time.time() >= deadline:
                break
        if created:
            self.Screen.UpdateScreen(True)
        if self.Jobs:
            self.__SetHidden(True)
            if self.Busy is not None:
                done = self.JobsTotal - len(self.Jobs)
                self.Busy.asLabel().SetText(native_str(TreeText.Drawing.format(done, self.JobsTotal)))
            return False
        return True

    def __Create(self, kind, index):
        parent = self.Parents[kind]
        name = "{}{}".format(PREFIX[kind], index)
        control = self.Screen.CreateChildControl(DEFS[kind], name, parent, False)
        if control is None:
            raise RuntimeError("建不出 {}（{}）".format(name, DEFS[kind]))
        if kind == KIND_CELL:
            cell = TreeCell(self.Screen, control, index)
            self.__Bind(cell)
            self.Pools[kind].append(cell)
        else:
            self.Pools[kind].append(control)
        return True

    def __ApplyCell(self, index, spec):
        pool = self.Pools[KIND_CELL]
        if index < len(pool):
            spec.Selected = spec.Target == self.Selected
            pool[index].Apply(spec)

    def __ApplyFrame(self, kind, index, pos, size):
        pool = self.Pools[kind]
        if index >= len(pool):
            return
        control = pool[index]
        control.SetPosition((int(pos[0]), int(pos[1])))
        if size is not None:
            set_size(control, size)
        control.SetVisible(True)

    def __HideRest(self, kind, count):
        for item in self.Pools[kind][count:]:
            if kind == KIND_CELL:
                item.Hide()
            else:
                item.SetVisible(False)

    def __Finish(self, scene):
        self.Scene = scene
        self.Pending = None
        self.__Fit(scene)
        self.__SetHidden(False)

    def __SetHidden(self, hidden):
        if self.Hidden == hidden:
            return
        self.Hidden = hidden
        self.Content.SetVisible(not hidden)
        if self.Busy is not None:
            self.Busy.SetVisible(hidden)

    # 视野
# ======================================================================================================================
    def __ViewSize(self):  # type: () -> tuple
        try:
            size = self.Cut.GetSize()
            return int(size[0]), int(size[1])
        except Exception:  # noqa
            return self.View

    def __Delta(self):  # type: () -> tuple
        try:
            delta = self.Input.GetOffsetDelta()
            return float(delta[0]), float(delta[1])
        except Exception:  # noqa
            return 0.0, 0.0

    def ScreenPos(self, target):  # type: (any) -> tuple or None
        """ 这一格现在在视口里的哪儿（左上角）；不在当前画面里给 None """
        if self.Scene is None:
            return None
        pos = self.Scene.Positions().get(target)
        if pos is None:
            return None
        delta = self.__Delta()
        return tuple(pos[axis] + self.Shift[axis] + delta[axis] + self.View[axis] - self.Inner[axis] for axis in (0, 1))

    def __Capture(self, anchor):  # type: (any) -> tuple or None
        """ 重画之前记下锚点那一格、根（画面里第一格总是根）现在在视口里的位置 """
        if self.Scene is None or not self.Scene.Cells:
            return None
        root = self.Scene.Cells[0].Target
        return anchor, (self.ScreenPos(anchor) if anchor is not None else None), self.ScreenPos(root)

    def __Fit(self, scene):
        """ 按画布大小设 dragpanel / canvas 的大小、content 的居中偏移，再按锚点算拖拽偏移 """
        view = self.__ViewSize()
        self.View = view
        width, height = scene.Size
        inner = (max(view[0], width), max(view[1], height))
        self.Inner = inner
        self.Shift = ((inner[0] - width) // 2 if width < view[0] else 0, (inner[1] - height) // 2 if height < view[1] else 0)
        self.Outer = (2 * inner[0] - view[0], 2 * inner[1] - view[1])
        set_size(self.Drag, self.Outer)
        set_size(self.CanvasControl, inner)
        self.Content.SetPosition(self.Shift)
        root = scene.Cells[0] if scene.Cells else None
        if root is None:
            self.SetDelta((0, 0))
            return
        target, screen, root_screen = self.Anchor or (None, None, None)
        pos = scene.Positions().get(target) if target is not None and screen is not None else None
        if pos is None:
            # 锚点那一格这一版里没有了（折叠掉了、换配方后没了）：根摆回它原来的位置；还没画过的摆在视口上方正中
            pos = root.Pos
            screen = root_screen or (view[0] // 2 - 10, 18)
        self.SetDelta(tuple(screen[axis] - pos[axis] - self.Shift[axis] - view[axis] + inner[axis] for axis in (0, 1)))

    def SetDelta(self, delta):  # type: (tuple) -> None
        """ 写拖拽偏移（夹在 [0, I − V]）；刚改过大小时引擎可能按旧大小夹，之后几帧不对就再写 """
        clamped = tuple(max(0, min(self.Inner[axis] - self.View[axis], int(round(delta[axis])))) for axis in (0, 1))
        self.Wanted = clamped
        self.WantedFrames = VIEW_FRAMES
        self.Input.SetOffsetDelta(clamped)

    def __KeepView(self):
        if self.Wanted is None:
            return
        self.WantedFrames -= 1
        current = self.__Delta()
        off = abs(current[0] - self.Wanted[0]) > 0.5 or abs(current[1] - self.Wanted[1]) > 0.5
        if self.WantedFrames <= 0:
            if off:
                self.__Report(current)
            self.Wanted = None
        elif off:
            self.Input.SetOffsetDelta(self.Wanted)

    def __Report(self, current):
        """ 自检：几帧过去拖拽偏移还是对不上（多半是大小没生效、引擎按别的范围夹了），记一行，看日志就知道是哪样 """
        try:
            drag, canvas = tuple(self.Drag.GetSize()), tuple(self.CanvasControl.GetSize())
        except Exception:  # noqa
            drag, canvas = None, None
        logger.warn("[MEI/tree] 拖拽偏移没摆到位：要 {}、读回 {}；视口 {}，dragpanel 设 {} 读回 {}，canvas 设 {} 读回 {}".format(
            self.Wanted, current, self.View, self.Outer, drag, self.Inner, canvas))

    def CenterRoot(self):
        """ 根摆回视口上方正中 """
        if self.Scene is None or not self.Scene.Cells:
            return
        root = self.Scene.Cells[0].Pos
        self.SetDelta(tuple(target - root[axis] - self.Shift[axis] - self.View[axis] + self.Inner[axis]
                            for axis, target in ((0, self.View[0] // 2 - 10), (1, 18))))

    def Scroll(self, dy):  # type: (int) -> None
        """ 滚轮：上下挪 dy 像素（正数往上看）"""
        if self.Scene is None or self.Input is None:
            return
        delta = self.__Delta()
        self.SetDelta((delta[0], delta[1] + dy))

    def ResetDrag(self):
        """ 松手时（成就界面也这么做：PointerPressReleaseClientEvent → ResetDrag）"""
        if self.Input is not None:
            try:
                self.Input.ResetDrag()
            except Exception:  # noqa
                pass

    # 选中、点击
# ======================================================================================================================
    def Select(self, target):  # type: (any) -> None
        """ 菜单开着的那一格画选中框（换一格只碰新旧两格）"""
        if target == self.Selected:
            return
        self.Selected = target
        for cell in self.Pools[KIND_CELL]:
            if cell.Target is not None:
                cell.SetSelected(cell.Target == target)

    def CellOf(self, target):  # type: (any) -> TreeCell or None
        for cell in self.Pools[KIND_CELL]:
            if cell.Target == target:
                return cell
        return None

    def __Bind(self, cell):
        button = cell.Button()
        if button is None:
            return
        button.AddTouchEventParams({"isSwallow": False, "pool": cell.Index})
        button.SetButtonTouchDownCallback(self.OnCellDown)
        button.SetButtonTouchUpCallback(self.OnCellUp)

    def OnCellDown(self, args):
        params = args.get("AddTouchEventParams") or {}
        self.Touch = (params.get("pool"), args.get("TouchPosX"), args.get("TouchPosY"), self.__Delta())

    def OnCellUp(self, args):
        params = args.get("AddTouchEventParams") or {}
        down, self.Touch = self.Touch, None
        index = params.get("pool")
        if down is None or down[0] != index or self.Jobs:
            return
        x, y = args.get("TouchPosX"), args.get("TouchPosY")
        if None not in (x, y, down[1], down[2]) and (abs(x - down[1]) > CLICK_SLOP or abs(y - down[2]) > CLICK_SLOP):
            return
        delta = self.__Delta()
        if abs(delta[0] - down[3][0]) > CLICK_SLOP or abs(delta[1] - down[3][1]) > CLICK_SLOP:
            return
        pool = self.Pools[KIND_CELL]
        if index is None or not 0 <= index < len(pool) or pool[index].Target is None:
            return
        self.OnClick(pool[index].Target, pool[index])
