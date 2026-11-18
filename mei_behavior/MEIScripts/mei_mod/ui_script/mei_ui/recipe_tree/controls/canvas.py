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
配方树的画布：视口、三层拖动、四个控件池、**只给视口附近的东西分控件**（视口虚拟化）。

**拖动照网易成就界面**（JSON 原生拖拽，引擎结论 §32）：cut（视口，clips_children）→ dragpanel（居中在视口里）→
canvas（可拖的 input_panel，contained）。画布 C 比视口 V 大时 canvas 的大小 I = C、dragpanel 的大小 D = 2I − V，
拖拽偏移 d 夹在 [0, I − V]：d = I − V 时看到画布的左上，d = 0 时看到右下；画布比视口小时整块挪到中间（content 的偏移）。
画布里一点 p 在视口里的位置 s = p + 居中偏移 + d + V − I —— 反过来，视口看到的是画布上 [I − V − d − 居中偏移, 再加 V] 那一块。

**视口的宽跟着右侧汇总栏**（SetSide）：汇总栏占掉的宽从视口里扣掉（cut 的宽 = 窗口 − 8 − 汇总栏），树不会被它挡住；
展开 / 收起时视口中心那一点留在视口中心（按上面的式子反算 d），过渡里每帧调一次，树跟着汇总栏平移。

**只画看得见的**（上万格的树：每格一个控件既建不完，一个父控件下挂太多子控件引擎还会断言，引擎结论 §54）：
- 一版画面（Scene）只是数据：每一格、框、线的位置。画之前按 TILE 见方的格子建空间索引（分帧建，建好之前旧的那一版照常显示）；
- 每帧按拖拽偏移算视口在画布上的那一块：视口里的、外面一圈（PREFETCH 倍视口）的分到控件，离视口超过 KEEP 倍的收回、给新进来的用
  （拖动时一边出一边进，收回的先给进来的用，没用上的才藏起来）。视口里的先画、外面一圈后画，每帧限时，没画完下一帧接着画；
- 控件池只增不减，挂在分桶里（每桶最多 BUCKET_SIZE 个，桶也是动态建的空 panel），池子最多 BUCKET_SIZE × MAX_BUCKETS 个；
- 换一版画面：原来分出去的控件全收回，按新的一版重新分 —— 视口里的那些写完之前整块藏着，不会看到新旧混在一起；
  建索引、写视口里的那些期间一直写着「绘制中… x/y」（建索引时旧的那一版还亮着，字压在上面）。
解算的那几帧（还没有新的画面要画）顺手先建一批控件藏着（Warm），画的时候只剩写。

**点格子**：格子盖着一层按钮（触摸回调，不吞事件：按在格子上也能拖）。按下记位置与拖拽偏移，松手比一下，动过就是在拖、不算点；
控件现在分给了哪一格（TreeCell.Target）就是点了哪一格
"""
import time

from mod_log import logger

from MEIScripts.constants.texts import TreeText
from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import flush, full_size, mark_dirty, show_later
from MEIScripts.utils.text import error_text, native_str

from .cell import TreeCell

KIND_CELL = "cell"
KIND_WS = "ws"
KIND_ING = "ing"
KIND_LINE = "line"
KINDS = (KIND_CELL, KIND_WS, KIND_ING, KIND_LINE)
""" 分控件的先后：格子最要紧，框、线其次 """
DEFS = {KIND_CELL: TreeConst.CellDef, KIND_WS: TreeConst.WsFrameDef, KIND_ING: TreeConst.IngFrameDef,
        KIND_LINE: TreeConst.LineDef}
PREFIX = {KIND_CELL: "n", KIND_WS: "w", KIND_ING: "g", KIND_LINE: "l"}

CLICK_SLOP = 4
""" 按下到松手动了几像素以上就算拖，不算点 """

VIEW_FRAMES = 3
""" 改完画布大小后这么多帧里，拖拽偏移被引擎按旧大小夹过就再写一遍；最后一帧还对不上（大小没生效、偏移被夹了）记一行警告 """

CUT_MARGIN = 8
""" 视口比窗口窄多少（JSON 里 cut 的 "100% - 8px"，左右各 4）"""

TILE = 128
""" 空间索引一格多大（GUI 像素）：视口几百像素，一次查十几格 """

PREFETCH = 0.5
""" 视口外面先画出多宽一圈（视口宽 / 高的倍数）：拖得不太快就看不到空白 """

KEEP = 1.0
""" 离视口多远（视口宽 / 高的倍数）才把控件收回：比 PREFETCH 大，来回拖时不反复换 """

BUCKET_SIZE = 64
""" 一个桶里最多挂几个控件：桶数 + 一桶的子控件 + 上面几层没走完的兄弟，远低于引擎的 250（引擎结论 §54） """

MAX_BUCKETS = 48
""" 每一种控件最多几个桶 —— 池子最多 BUCKET_SIZE × MAX_BUCKETS 个；视口附近的东西比这还多就有一部分不画（记一行警告）"""

FIRST_BUDGET_MS = 16.0
""" 整块藏着（建索引、写视口里的那些）的时候每帧做多久：没东西在动，掉几帧看不出 """

WARM_BUDGET_MS = 3.0
""" 解算期间每帧顺手建控件的时间 """

SYNC_STEP = 12
""" 拖拽偏移变了不到这么多像素就不重新分控件（外面那一圈够用；拖动时每帧省一次查索引）"""

RETRY_LIMIT = 5
""" 一格的子控件取不到，最多再写这么多帧 """


set_size = full_size
""" 改控件的大小：写尺寸规则（blocks.writer.full_size）—— SetSize 只改当前的值，大树「偏下、拉不到剩下的」多半就是它（引擎结论 §28）"""


def _hits(rect, area):  # type: (tuple, tuple) -> bool
    """ rect (x, y, 宽, 高) 和 area (左, 上, 右, 下) 有没有交 """
    return rect[0] < area[2] and rect[0] + rect[2] > area[0] and rect[1] < area[3] and rect[1] + rect[3] > area[1]


def _grow(area, view, ratio):  # type: (tuple, tuple, float) -> tuple
    dx, dy = view[0] * ratio, view[1] * ratio
    return area[0] - dx, area[1] - dy, area[2] + dx, area[3] + dy


class Scene(object):
    """
    一版画面：Cells [CellSpec 或 LazyCell]（第一格总是根）、WsFrames [(x, y)]、IngFrames [((x, y), (w, h))]、Lines [(x, y, w, h)]、
    Size 画布大小、CellSize 一格多大、WsSize 工作方块的框多大
    """
    __slots__ = ("Cells", "WsFrames", "IngFrames", "Lines", "Size", "CellSize", "WsSize", "PosMap")

    def __init__(self, size=(0, 0), cell=20, ws=24):
        self.Cells = []  # type: list
        self.WsFrames = []  # type: list
        self.IngFrames = []  # type: list
        self.Lines = []  # type: list
        self.Size = (int(size[0]), int(size[1]))
        self.CellSize = int(cell)
        self.WsSize = int(ws)
        self.PosMap = None  # type: dict or None

    def Positions(self):  # type: () -> dict
        """ {target: 位置}（第一次要时建好，之后不变：画面建好就不再改）"""
        if self.PosMap is None:
            self.PosMap = dict((spec.Target, spec.Pos) for spec in self.Cells)
        return self.PosMap

    def Count(self, kind):  # type: (str) -> int
        if kind == KIND_CELL:
            return len(self.Cells)
        if kind == KIND_WS:
            return len(self.WsFrames)
        if kind == KIND_ING:
            return len(self.IngFrames)
        return len(self.Lines)

    def Rect(self, kind, index):  # type: (str, int) -> tuple
        """ 第 index 个东西的矩形 (x, y, 宽, 高) """
        if kind == KIND_CELL:
            pos = self.Cells[index].Pos
            return pos[0], pos[1], self.CellSize, self.CellSize
        if kind == KIND_WS:
            pos = self.WsFrames[index]
            return pos[0], pos[1], self.WsSize, self.WsSize
        if kind == KIND_ING:
            pos, size = self.IngFrames[index]
            return pos[0], pos[1], size[0], size[1]
        return self.Lines[index]


class TreeShape(object):
    """ 框、连线：位置、大小、显隐各记着上次写的，没变不碰引擎；显隐不当场刷新（画布这一批分完控件 flush 一次）"""
    __slots__ = ("Control", "Screen", "Pos", "Size", "Shown", "Fresh")

    def __init__(self, control, screen=None):
        self.Control = control
        self.Screen = screen
        self.Pos = None  # type: tuple or None
        self.Size = None  # type: tuple or None
        self.Shown = True  # 刚建出来是亮着的（模板没写 visible）
        self.Fresh = False  # 建出来就藏着、还没亮过（第一次亮的那一帧要 UpdateScreen）

    def Apply(self, pos, size=None):
        pos = (int(pos[0]), int(pos[1]))
        if pos != self.Pos:
            self.Control.SetPosition(pos)
            self.Pos = pos
        if size is not None:
            size = (int(size[0]), int(size[1]))
            if size != self.Size:
                set_size(self.Control, size)
                self.Size = size
        self.Show(True)

    def Show(self, on):
        on = bool(on)
        if on != self.Shown:
            show_later(self.Control, on, self.Screen)
            self.Shown = on


class TreeCanvas(object):
    """ on_click(target, cell)：点了画布上的一格 """

    def __init__(self, screen, on_click):
        self.Screen = screen
        self.OnClick = on_click
        get = screen.GetBaseUIControl
        self.Window = get(TreePath.Window)
        self.Cut = get(TreePath.Cut)
        self.Drag = get(TreePath.DragPanel)
        self.CanvasControl = get(TreePath.Canvas)
        self.Input = self.CanvasControl.asInputPanel() if self.CanvasControl is not None else None
        self.Content = get(TreePath.Content)
        self.Busy = get(TreePath.Busy)
        self.Parents = {KIND_CELL: get(TreePath.Cells), KIND_WS: get(TreePath.Frames), KIND_ING: get(TreePath.Frames),
                        KIND_LINE: get(TreePath.Lines)}
        self.Pools = dict((kind, []) for kind in KINDS)  # 建过的全部（TreeCell / TreeShape），只增不减
        self.Buckets = dict((kind, []) for kind in KINDS)
        self.Live = dict((kind, {}) for kind in KINDS)  # 画面里第几个 -> 池里第几个
        self.Owner = dict((kind, {}) for kind in KINDS)  # 池里第几个 -> 画面里第几个（None 是空着）
        self.Free = dict((kind, []) for kind in KINDS)  # 池里空着的（下标）
        self.Released = []  # type: list  # 收回了、还亮着的 (种类, 池里第几个)：分控件那一步结束时没再用上的藏起来
        self.Scene = None  # type: Scene or None  # 正在显示的那一版
        self.Pending = None  # type: Scene or None  # 正在建索引的那一版
        self.Index = None  # type: dict or None  # 正在显示的那一版的空间索引：(格 x, 格 y) -> [(种类, 第几个)]
        self.Building = None  # type: list or None  # [索引, 第几种, 第几个]：Pending 的索引建到哪了
        self.Anchor = None  # type: tuple or None  # (锚点 target, 它在视口里的位置, 根在视口里的位置)：画完按它摆视野
        self.First = False  # type: bool  # 刚换了一版，视口里的还没写完
        self.FirstLeft = 0  # type: int
        self.FirstTotal = 0  # type: int
        self.Synced = None  # type: tuple or None  # 上次分完控件时的（拖拽偏移, (视口, 画布, 居中偏移)）
        self.Retry = {}  # type: dict  # (种类, 画面里第几个) -> 写过几次：子控件没取到、下一帧再写一遍
        self.Warned = set()  # type: set
        self.Warmed = False  # type: bool  # 解算期间预先建的已经够数了（之后不再量视口）
        self.Hidden = False  # type: bool
        self.BusyShown = False  # type: bool  # 「绘制中」亮着没有
        self.Inner = (0, 0)  # type: tuple  # canvas 的大小 I
        self.Outer = (0, 0)  # type: tuple  # dragpanel 的大小 D = 2I − V
        self.Shift = (0, 0)  # type: tuple  # 画布比视口小时 content 的居中偏移
        self.View = (0, 0)  # type: tuple  # 视口大小 V
        self.Side = 0  # type: int  # 右侧汇总栏占掉的宽（连同它和视口之间的空）
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
        排一版画面：先分帧建索引（旧的那一版照常显示），建好换上、把视口里的写完再显示。anchor 是要摆回原处的那一格的
        target（找不到退回根）；还没画过时根摆在视口上方正中
        """
        if not self.__Ready:
            return
        self.Anchor = self.__Capture(anchor)
        self.Pending = scene
        self.Building = [{}, 0, 0]

    def IsDrawing(self):  # type: () -> bool
        """ 正在换新的一版（建索引、写视口里的那些）：这时点格子不算（池里的控件可能还是旧的那一版）"""
        return self.Building is not None or self.First

    def Tick(self, budget_ms):  # type: (float) -> bool
        """ 每帧：建索引 / 给视口附近分控件（限时），补写拖拽偏移。新的一版画完了返回 True（只在画完的那一帧）"""
        self.__KeepView()
        if not self.__Ready:
            return False
        hidden = self.Building is not None or self.First
        deadline = time.time() + max(budget_ms, FIRST_BUDGET_MS if hidden else 0) / 1000.0
        if self.Building is not None:
            if not self.__BuildIndex(deadline):
                self.__Progress()
                return False
            self.__Switch()
        if self.Scene is None:
            return False
        self.__Sync(deadline)
        if not self.First:
            return False
        if self.FirstLeft > 0:
            self.__SetHidden(True)
            self.__Progress()
            return False
        self.First = False
        self.__SetHidden(False)
        self.__SetBusy(False)
        return True

    def __BuildIndex(self, deadline):  # type: (float) -> bool
        """ 往 Pending 的索引里加一段（限时），建完返回 True """
        scene, state = self.Pending, self.Building
        tiles = state[0]
        while state[1] < len(KINDS):
            kind = KINDS[state[1]]
            count, index = scene.Count(kind), state[2]
            while index < count:
                x, y, w, h = scene.Rect(kind, index)
                entry = (kind, index)
                for tx in range(int(x) // TILE, int(x + max(w, 1) - 1) // TILE + 1):
                    for ty in range(int(y) // TILE, int(y + max(h, 1) - 1) // TILE + 1):
                        bucket = tiles.get((tx, ty))
                        if bucket is None:
                            tiles[(tx, ty)] = [entry]
                        else:
                            bucket.append(entry)
                index += 1
                if index & 63 == 0 and time.time() >= deadline:
                    state[2] = index
                    return False
            state[1] += 1
            state[2] = 0
        return True

    def __Switch(self):
        """ 索引建好了：换上新的一版、按锚点摆视野，原来分出去的控件全收回（下一步按新的一版重新分）"""
        scene = self.Pending
        self.Scene, self.Index = scene, self.Building[0]
        self.Pending, self.Building = None, None
        self.Retry = {}
        self.__Fit(scene)
        for kind in KINDS:
            owner = self.Owner[kind]
            for slot in self.Live[kind].values():
                owner[slot] = None
                self.Free[kind].append(slot)
                self.Released.append((kind, slot))
            self.Live[kind] = {}
        self.First = True
        self.FirstTotal = self.FirstLeft = 0
        self.Synced = None

    def __Progress(self):
        if self.Busy is None:
            return
        self.__SetBusy(True)
        if self.Building is not None:
            done = sum(self.Pending.Count(kind) for kind in KINDS[:self.Building[1]]) + self.Building[2]
            total = sum(self.Pending.Count(kind) for kind in KINDS)
        else:
            done, total = self.FirstTotal - self.FirstLeft, self.FirstTotal
        self.Busy.asLabel().SetText(native_str(TreeText.Drawing.format(done, total)))

    # 只给视口附近的东西分控件
# ======================================================================================================================
    def __Area(self, delta):  # type: (tuple) -> tuple
        """ 视口现在看到的是画布上的哪一块 (左, 上, 右, 下) """
        left = self.Inner[0] - self.View[0] - delta[0] - self.Shift[0]
        top = self.Inner[1] - self.View[1] - delta[1] - self.Shift[1]
        return left, top, left + self.View[0], top + self.View[1]

    def __Query(self, area):  # type: (tuple) -> set
        found = set()
        tiles = self.Index
        for tx in range(int(area[0]) // TILE, int(area[2]) // TILE + 1):
            for ty in range(int(area[1]) // TILE, int(area[3]) // TILE + 1):
                bucket = tiles.get((tx, ty))
                if bucket:
                    found.update(bucket)
        return found

    def __Sync(self, deadline):  # type: (float) -> None
        scene = self.Scene
        delta = self.Wanted if self.Wanted is not None else self.__Delta()
        frame = (self.View, self.Inner, self.Shift)
        if self.Synced is not None and not self.Retry and self.Synced[1] == frame \
                and abs(delta[0] - self.Synced[0][0]) < SYNC_STEP and abs(delta[1] - self.Synced[0][1]) < SYNC_STEP:
            return  # 没怎么动：外面那一圈够用
        view = self.__Area(delta)
        want, keep = _grow(view, self.View, PREFETCH), _grow(view, self.View, KEEP)
        # 离得太远的收回（拖动时先给新进来的用，没用上的最后才藏）
        released = self.Released
        for kind in KINDS:
            live, owner, free = self.Live[kind], self.Owner[kind], self.Free[kind]
            for item, slot in list(live.items()):
                if not _hits(scene.Rect(kind, item), keep):
                    del live[item]
                    owner[slot] = None
                    free.append(slot)
                    released.append((kind, slot))
                    self.Retry.pop((kind, item), None)
        # 要画的：视口里的在前、外面一圈在后；同一圈里格子在前。子控件上次没取到的（Retry）再写一遍
        near, around = [], []
        found = self.__Query(want)
        for key in [key for key in self.Retry if key not in found]:
            del self.Retry[key]  # 已经不在附近了：等它再进来时整格重写
        for kind, item in found:
            if item in self.Live[kind] and (kind, item) not in self.Retry:
                continue
            rect = scene.Rect(kind, item)
            if _hits(rect, view):
                near.append((KINDS.index(kind), item, kind))
            elif _hits(rect, want):
                around.append((KINDS.index(kind), item, kind))
        near.sort()
        around.sort()
        if self.First and not self.FirstTotal:
            self.FirstTotal = len(near)
        refresh, stopped, left, placed = False, False, 0, 0
        for group in (near, around):
            for position, (_, item, kind) in enumerate(group):
                if placed and time.time() >= deadline:  # 每帧至少写一个：预算再紧也画得完
                    stopped = True
                    if group is near:
                        left = len(near) - position
                    break
                try:
                    created = self.__Place(kind, item)
                except Exception as e:  # noqa  一格写坏了不能让整版停住
                    logger.error("[MEI/tree] 画配方树出错: {}".format(error_text(e)))
                    continue
                placed += 1
                refresh = refresh or bool(created)
            if stopped:
                break
        if self.First:
            self.FirstLeft = left
        # 收回了、这一帧没再用上的藏起来：拖动时收回的在视口外面，可下一版画面里同一个位置可能不是它；
        # 换一版时收回的是上一版的，没用上的不藏就一直画在那儿
        for kind, slot in released:
            if self.Owner[kind].get(slot) is None:
                self.__Hide(kind, slot)
        self.Released = []
        if refresh:
            mark_dirty(self.Screen)
        flush()  # 这一批分控件里建的、改了显隐的一起刷新一次（显隐都没当场刷新：拖动时一批进出视口就是一批整屏重排）
        self.Synced = None if stopped else (delta, frame)

    def __Place(self, kind, item):  # type: (str, int) -> bool or None
        """ 给画面里第 item 个分一个控件并写上；建了新控件（或第一次亮出建好藏着的）给 True，分不到给 None """
        live = self.Live[kind]
        slot = live.get(item)
        created = False
        if slot is None:
            free = self.Free[kind]
            if free:
                slot = free.pop()
            else:
                slot = self.__Create(kind)
                if slot is None:
                    return None
                created = True
            live[item] = slot
            self.Owner[kind][slot] = item
        target = self.Pools[kind][slot]
        if getattr(target, "Fresh", False):
            target.Fresh = False
            created = True
        scene = self.Scene
        if kind == KIND_CELL:
            spec = scene.Cells[item].Spec()
            spec.Selected = spec.Target == self.Selected
            target.Apply(spec)
            if target.Missed:
                tries = self.Retry.get((kind, item), 0) + 1
                if tries < RETRY_LIMIT:
                    self.Retry[(kind, item)] = tries
                else:
                    self.Retry.pop((kind, item), None)
            else:
                self.Retry.pop((kind, item), None)
        elif kind == KIND_WS:
            target.Apply(scene.WsFrames[item])
        elif kind == KIND_ING:
            pos, size = scene.IngFrames[item]
            target.Apply(pos, size)
        else:
            rect = scene.Lines[item]
            target.Apply(rect[:2], rect[2:])
        return created

    def __Hide(self, kind, slot):
        target = self.Pools[kind][slot]
        if kind == KIND_CELL:
            target.Hide()
        else:
            target.Show(False)

    def __Create(self, kind):  # type: (str) -> int or None
        """ 建一个控件放进池里（挂在当前的桶里，桶满了先建下一个桶）；池满了、建不出给 None """
        pool = self.Pools[kind]
        index = len(pool)
        number = index // BUCKET_SIZE
        if number >= MAX_BUCKETS:
            if kind not in self.Warned:
                self.Warned.add(kind)
                logger.warn("[MEI/tree] 视口附近的{}超过 {} 个，多出来的不画".format(kind, BUCKET_SIZE * MAX_BUCKETS))
            return None
        buckets = self.Buckets[kind]
        while len(buckets) <= number:
            name = "{}b{}".format(PREFIX[kind], len(buckets))
            bucket = self.Screen.CreateChildControl(TreeConst.BucketDef, name, self.Parents[kind], False)
            if bucket is None:
                raise RuntimeError("建不出 {}（{}）".format(name, TreeConst.BucketDef))
            buckets.append(bucket)
        name = "{}{}".format(PREFIX[kind], index)
        control = self.Screen.CreateChildControl(DEFS[kind], name, buckets[number], False)
        if control is None:
            raise RuntimeError("建不出 {}（{}）".format(name, DEFS[kind]))
        if kind == KIND_CELL:
            item = TreeCell(self.Screen, control, index)
            item.Prime()
            self.__Bind(item)
        else:
            item = TreeShape(control, self.Screen)
        pool.append(item)
        self.Owner[kind][index] = None
        return index

    def Warm(self, budget_ms=WARM_BUDGET_MS):  # type: (float) -> None
        """
        解算的那几帧顺手建一批控件藏着（视口大概放得下多少就建多少），画的时候只剩写。正在换一版画面时不建（那时自己会建）
        """
        if not self.__Ready or self.Warmed or self.Building is not None or self.First:
            return
        view = self.__ViewSize()
        cells = (view[0] // 20 + 1) * (view[1] // 44 + 1)
        targets = {KIND_CELL: cells, KIND_LINE: cells, KIND_WS: cells // 3 + 1, KIND_ING: cells // 3 + 1}
        if all(len(self.Pools[kind]) >= targets[kind] for kind in KINDS):
            self.Warmed = True
            return
        deadline = time.time() + budget_ms / 1000.0
        created = False
        for kind in KINDS:
            while len(self.Pools[kind]) < targets[kind] and time.time() < deadline:
                try:
                    slot = self.__Create(kind)
                except Exception as e:  # noqa
                    logger.error("[MEI/tree] 预先建配方树的控件出错: {}".format(error_text(e)))
                    return
                if slot is None:
                    break
                self.__Hide(kind, slot)
                self.Pools[kind][slot].Fresh = True
                self.Free[kind].append(slot)
                created = True
        if created:
            mark_dirty(self.Screen)
            flush()

    def __SetHidden(self, hidden):
        """ 整块画布藏不藏（视口里的还没写完时藏）；「绘制中」另由 __SetBusy 管 """
        if self.Hidden == hidden:
            return
        self.Hidden = hidden
        show_later(self.Content, not hidden, self.Screen)

    def __SetBusy(self, shown):
        if self.BusyShown == shown or self.Busy is None:
            return
        self.BusyShown = shown
        show_later(self.Busy, shown, self.Screen)

    # 视野
# ======================================================================================================================
    def __ViewSize(self):  # type: () -> tuple
        """ 视口多大：高读 cut，宽按窗口减去边距与汇总栏算（刚改过 cut 的宽，这一帧读回来的可能还是旧的）"""
        try:
            size = self.Cut.GetSize()
            width, height = int(size[0]), int(size[1])
        except Exception:  # noqa
            return self.View
        if self.Window is not None:
            try:
                width = int(self.Window.GetSize()[0]) - CUT_MARGIN - self.Side
            except Exception:  # noqa
                pass
        return max(1, width), height

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

    def HasTarget(self, target):  # type: (any) -> bool
        """ 这一格在正在显示的那一版里吗（不管它现在有没有分到控件）"""
        return self.Scene is not None and target in self.Scene.Positions()

    def GlobalPos(self, target):  # type: (any) -> tuple or None
        """ 这一格的全局位置（左上角）：分到了控件读控件的，没分到（在视口外）按视口的位置算；不在画面里给 None """
        cell = self.CellOf(target)
        if cell is not None:
            try:
                return tuple(cell.Control.GetGlobalPosition())
            except Exception:  # noqa
                pass
        pos = self.ScreenPos(target)
        if pos is None:
            return None
        try:
            x, y = self.Cut.GetGlobalPosition()
        except Exception:  # noqa
            return None
        return x + pos[0], y + pos[1]

    def __Capture(self, anchor):  # type: (any) -> tuple or None
        """ 重画之前记下锚点那一格、根（画面里第一格总是根）现在在视口里的位置 """
        if self.Scene is None or not self.Scene.Cells:
            return None
        root = self.Scene.Cells[0].Target
        return anchor, (self.ScreenPos(anchor) if anchor is not None else None), self.ScreenPos(root)

    def __Resize(self, scene, view):  # type: (Scene, tuple) -> None
        """ 按画布大小与视口设 dragpanel / canvas 的大小、content 的居中偏移 """
        self.View = view
        width, height = scene.Size
        inner = (max(view[0], width), max(view[1], height))
        self.Inner = inner
        self.Shift = ((inner[0] - width) // 2 if width < view[0] else 0, (inner[1] - height) // 2 if height < view[1] else 0)
        self.Outer = (2 * inner[0] - view[0], 2 * inner[1] - view[1])
        set_size(self.Drag, self.Outer)
        set_size(self.CanvasControl, inner)
        self.Content.SetPosition(self.Shift)

    def __Fit(self, scene):
        """ 设大小（__Resize），再按锚点算拖拽偏移 """
        view = self.__ViewSize()
        self.__Resize(scene, view)
        inner = self.Inner
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

    def SetSide(self, side):  # type: (int) -> None
        """
        右侧汇总栏占掉多宽（展开 / 收起的过渡里每帧调）：视口跟着变窄 / 变宽，视口中心那一点留在新视口的中心 ——
        中心 p = I − V/2 − 居中偏移 − d（s = V/2 反算），新的 d = I' − V'/2 − p − 居中偏移'。
        cut 的宽写成「父控件 100% − 边距 − 汇总栏」（SetFullSize 跟随父控件）：屏幕尺寸变了照样对
        """
        side = max(0, int(round(side)))
        if not self.__Ready or side == self.Side:
            return
        center = None
        if self.Scene is not None and self.View[0] > 0:
            delta = self.__Delta()
            center = tuple(self.Inner[axis] - self.View[axis] / 2.0 - self.Shift[axis] - delta[axis] for axis in (0, 1))
        self.Side = side
        self.Cut.SetFullSize("x", {"followType": "parent", "relativeValue": 1.0, "absoluteValue": -(CUT_MARGIN + side)})
        if self.Scene is None:
            return  # 还没有画好的画面：画完 __Fit 按新的视口摆
        self.__Resize(self.Scene, self.__ViewSize())
        if center is not None:
            self.SetDelta(tuple(self.Inner[axis] - self.View[axis] / 2.0 - center[axis] - self.Shift[axis]
                                for axis in (0, 1)))

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
        """ 菜单开着的那一格画选中框（换一格只碰新旧两格；没分到控件的等它进视口时按 Selected 画）"""
        if target == self.Selected:
            return
        self.Selected = target
        pool = self.Pools[KIND_CELL]
        for slot in self.Live[KIND_CELL].values():
            cell = pool[slot]
            if cell.Target is not None:
                cell.SetSelected(cell.Target == target)

    def CellOf(self, target):  # type: (any) -> TreeCell or None
        """ 这一格现在分到的格子控件；在视口外、没分到给 None """
        pool = self.Pools[KIND_CELL]
        for slot in self.Live[KIND_CELL].values():
            if pool[slot].Target == target:
                return pool[slot]
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
        if down is None or down[0] != index or self.IsDrawing():
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
