# coding=utf-8
# ----------------------------------------------------------------------
#  workspace.py is part of MoreEnoughItems.
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
编辑器的工作区：配方页上一行的真样子（配方页的灰底、右边那一列按钮），积木由 blocks/painter.py 画 —— 和配方页同一套画法。

点哪一块由脚本算（BlockPainter.PickAt：画在最上面的那块，配方模式装东西的积木优先）：内容区上面只盖一个透明的拾取层（JSON 里的 blank，
层级在积木上面），不给每块积木各盖一个按钮 —— 那样同层的按钮按建的先后叠，后放的底框会挡住它上面的格子。PC 上光标下那块亮一层白（hover）。
界面模式：点积木选中，选中的那块画黄框（sel），上面再盖一个透明的、可拖的把手（原生拖动的 input_panel，
拖拽偏移就是它在内容区里的位置，引擎结论 §32）。把手**不 contained**：夹在内容区里的话拖到边上光标就离开了把手，
在把手外面松手引擎收不到、把手一直跟着光标（引擎结论 §58）—— 夹回内容区由这里做（clamp），只挪积木与黄框。
拖着时每帧挪这一块；连续几帧不动就写回排版（on_moved），这时不碰把手（玩家可能还按着）；之后点了别的、改了位置才把把手摆回积木上。
选中的积木上面还压着别的积木（底框、图片上摆着格子）时，把手不盖住整块（那样压在上面的格子就点不着了），缩成它左上角外侧的一个小拖动柄（GRIP）。
配方模式：点装东西的积木选中那一格（黄框，不能拖），点物品栏的物品填进去
"""
from mod_log import logger

from MEIScripts.constants.ui import EditorConst, EditorPath
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.painter import BlockPainter
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.row import row_layout
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import ControlWriter
from MEIScripts.mei_mod.ui_script.proxy.focus.manager import GetCursorPos
from MEIScripts.utils.text import error_text

from .modules import draft

CLICK_SLOP = 6
""" 按下到抬起挪了超过这么多不算点（是在划）"""

HOVER_FRAMES = 2
""" 隔几帧看一眼光标下是哪一块（PC）"""

GRIP = 9
""" 小拖动柄的边长：摆在积木左上角外侧（把手的位置 = 积木的位置 - GRIP）"""



class Workspace(object):
    """
    on_block(第几块) 点了一块积木；on_blank() 点了空白处；on_moved(第几块, x, y) 拖完了；
    clamp(第几块, x, y) -> (x, y) 把一块积木的位置夹回内容区
    """

    def __init__(self, screen, on_block, on_blank, on_moved, clamp):
        self.Screen = screen
        self.OnBlock = on_block
        self.OnBlank = on_blank
        self.OnMoved = on_moved
        self.Clamp = clamp
        self.Work = self.__Writer(EditorPath.Work)
        self.Row = self.__Writer(EditorPath.Row)
        self.Stage = self.__Writer(EditorPath.Stage)
        self.Sel = self.__Writer(EditorPath.Select)
        self.Drag = self.__Writer(EditorPath.Drag)
        self.Buttons = self.__Writer(EditorPath.RowButtons)
        self.Status = self.__Writer(EditorPath.Status)
        self.Hint = self.__Writer(EditorPath.Hint)
        self.Hover = self.__Writer(EditorPath.Hover)
        self.Painter = BlockPainter(screen, self.__Create, self.__Remove, editing=True)
        if self.Stage is not None:
            self.Painter.Attach(self.Stage.Control, prefix="eb")
        self.__BindPicker()
        self.HoldersFirst = False  # type: bool  # 点的时候装东西的积木优先（配方模式）
        self.Pressed = None  # type: tuple or None  # 拾取层按下的那一点（全局坐标）
        self.Hovered = None  # type: int or None  # 光标下亮着的那一块
        self.Page = None  # type: dict or None
        self.DragIndex = None  # type: int or None  # 把手盖在哪一块上
        self.DragLast = None  # type: tuple or None  # 上一帧读到的拖拽偏移（把手的位置，没夹过）
        self.Committed = None  # type: tuple or None  # 写回排版的位置（夹过的）
        self.Still = 0  # type: int  # 拖拽偏移连续几帧没变
        self.MovedAt = -1000  # type: int  # 最后一次读到拖拽偏移变了是第几帧
        self.GripOffset = (0, 0)  # type: tuple  # 积木的位置 = 拖拽偏移 + 它（缩成小拖动柄时是 (GRIP, GRIP)）
        self.Committing = False  # type: bool  # 正在把拖完的位置写回排版（这一轮刷新不摆把手）
        self.Frame = 0
        self.Ticks = 0

    def __Writer(self, path):  # type: (str) -> ControlWriter or None
        control = self.Screen.GetBaseUIControl(path)
        if control is None:
            logger.warn("[MEI/editor] 工作区的控件 {} 取不到".format(path))
            return None
        return ControlWriter(self.Screen, control)

    def __Create(self, control_def, name, parent):
        # 不当场刷新（painter 记下界面，编辑器这一批写完 flush 一次）
        return self.Screen.CreateChildControl(control_def, name, parent, False)

    def __Remove(self, control):
        self.Screen.RemoveChildControl(control)

    def __BindPicker(self):
        picker = self.Screen.GetBaseUIControl(EditorPath.Blank)
        if picker is None:
            return
        try:
            button = picker.asButton()
            button.AddTouchEventParams({"isSwallow": True})
            button.SetButtonTouchDownCallback(self.__OnPickDown)
            button.SetButtonTouchUpCallback(self.__OnPickUp)
        except Exception as e:  # noqa
            logger.error("[MEI/editor] 工作区的拾取层挂不上触摸回调: {}".format(error_text(e)))

    def __OnPickDown(self, args):
        self.Pressed = (args.get("TouchPosX"), args.get("TouchPosY"))

    def __OnPickUp(self, args):
        down, self.Pressed = self.Pressed, None
        up = (args.get("TouchPosX"), args.get("TouchPosY"))
        if down is None or None in down or None in up:
            down = up
        if None in down:
            return
        if abs(up[0] - down[0]) > CLICK_SLOP or abs(up[1] - down[1]) > CLICK_SLOP:
            return
        index = self.PickAt(down[0], down[1])
        if index is None:
            self.OnBlank()
        else:
            self.OnBlock(index)

    def PickAt(self, x, y):  # type: (float, float) -> int or None
        """ 屏幕上这一点（全局坐标）点中的是第几块 """
        origin = self.__Origin()
        if origin is None:
            return None
        return self.Painter.PickAt(x - origin[0], y - origin[1], self.HoldersFirst)

    def __Origin(self):  # type: () -> tuple or None
        """ 内容区左上角的全局坐标 """
        if self.Stage is None:
            return None
        try:
            pos = self.Stage.Control.GetGlobalPosition()
        except Exception:  # noqa
            return None
        return (float(pos[0]), float(pos[1])) if pos else None

    # 摆
# ======================================================================================================================
    def Place(self, pos, size):  # type: (tuple, tuple) -> None
        """ 工作区在窗口里的位置与大小（左栏、物品栏开合时改）"""
        if self.Work is not None:
            self.Work.SetPos(pos)
            self.Work.SetSize("", size)

    def Show(self, page, editing):  # type: (dict, bool) -> None
        """ 照这一页的排版建 / 挪积木；editing 为假是预览（不画占位）"""
        self.Page = page
        self.Hovered = -1  # 排版可能变了：光标下那块下一次重新摆
        width, height = draft.area(page)
        layout = row_layout(width, height)  # 和配方页上的一行一样（mei_ui/blocks/row.py）：按钮一排横在内容区下面、右边对齐
        if self.Row is not None:
            self.Row.SetSize("", layout["size"])
        if self.Stage is not None:
            self.Stage.SetSize("", (width, height))
        if self.Buttons is not None:
            self.Buttons.SetPos(layout["buttons"])
        if self.Painter.Editing != bool(editing):
            self.Painter.Editing = bool(editing)
            self.Painter.Invalidate()
        self.Painter.Layout(page.get("blocks") or [], page.get("fields") or [])

    def SetContent(self, entries, fields, field_max):  # type: (dict, dict, dict) -> None
        self.Painter.SetContent(entries, fields, field_max)

    def SetStatus(self, text, hint=u""):
        if self.Status is not None:
            self.Status.SetText("", text)
        if self.Hint is not None:
            self.Hint.SetText("", hint)

    # 选中
# ======================================================================================================================
    def Select(self, index, drag):  # type: (int or None, bool) -> None
        """ 选中第 index 块：画黄框；drag 为真再盖上可拖的把手（界面模式），不然只有黄框（配方模式）；None 是不选 """
        view = self.Painter.ViewAt(index)
        if view is None:
            self.__HideSelect()
            return
        pos = (int(view.Data.get("x", 0)), int(view.Data.get("y", 0)))
        size = view.Size
        self.__Frame(pos, size)
        if not drag or self.Drag is None:
            self.DragIndex = None
            if self.Drag is not None:
                self.Drag.SetVisible("", False)
            return
        grip = self.Painter.Covered(index)
        if not self.Committing:
            self.GripOffset = (GRIP, GRIP) if grip else (0, 0)
        self.Drag.SetSize("", (GRIP, GRIP) if self.GripOffset != (0, 0) else size)
        self.Drag.SetVisible("/grip", self.GripOffset != (0, 0))
        self.Drag.SetVisible("", True)
        want = (pos[0] - self.GripOffset[0], pos[1] - self.GripOffset[1])
        if self.DragIndex != index:
            self.__SetDelta(want)
        elif not self.Committing and self.DragLast != want and not self.__Moving():
            self.__SetDelta(want)  # 位置被左栏改了、换了把手的样子、或者上次拖到了内容区外面：把手摆回积木上
        self.DragIndex, self.Committed = index, pos
        if not self.Committing:
            self.Still = 0

    def __Frame(self, pos, size):
        if self.Sel is not None:
            self.Sel.SetPos((pos[0] - 1, pos[1] - 1))
            self.Sel.SetSize("", (size[0] + 2, size[1] + 2))
            self.Sel.SetVisible("", True)

    def __Moving(self):  # type: () -> bool
        """ 刚拖过（玩家可能还按着把手）：这时把把手挪走，松手的地方就不在把手上了 """
        return self.Frame - self.MovedAt <= EditorConst.DragSettle * 4

    def __HideSelect(self):
        self.DragIndex = None
        for writer in (self.Drag, self.Sel):
            if writer is not None:
                writer.SetVisible("", False)

    def __UpdateHover(self):
        """ PC：光标下那块亮一层白（触屏、光标不在内容区里、正在拖的都不亮）"""
        index = None
        cursor = GetCursorPos() if self.DragIndex is None or self.Frame - self.MovedAt > EditorConst.DragSettle else None
        if cursor is not None:
            index = self.PickAt(cursor[0], cursor[1])
        view = self.Painter.ViewAt(index)
        if view is None:
            index = None
        if index == self.Hovered or self.Hover is None:
            return
        self.Hovered = index
        if view is None:
            self.Hover.SetVisible("", False)
            return
        self.Hover.SetPos((int(view.Data.get("x", 0)), int(view.Data.get("y", 0))))
        self.Hover.SetSize("", view.Size)
        self.Hover.SetVisible("", True)

    def __SetDelta(self, pos):
        try:
            self.Drag.Control.asInputPanel().SetOffsetDelta((float(pos[0]), float(pos[1])))
        except Exception as e:  # noqa
            logger.warn("[MEI/editor] 摆不了拖动的把手: {}".format(error_text(e)))
            return
        self.DragLast = (int(pos[0]), int(pos[1]))

    def __ReadDelta(self):  # type: () -> tuple or None
        try:
            delta = self.Drag.Control.asInputPanel().GetOffsetDelta()
        except Exception:  # noqa
            return None
        return int(round(delta[0])), int(round(delta[1]))

    # 每帧
# ======================================================================================================================
    def Update(self):  # type: () -> tuple or None
        """ 每帧：补画没画好的积木、节拍（每 6 帧一拍）、读拖拽偏移；正在拖的话给 (第几块, x, y) 好写状态栏 """
        self.Frame += 1
        if self.Frame % EditorConst.TickFrames == 0:
            self.Ticks += 1
            self.Painter.Tick(self.Ticks)
        elif self.Painter.Pending():
            self.Painter.Paint()
        if self.Frame % HOVER_FRAMES == 0:
            self.__UpdateHover()
        if self.DragIndex is None or self.Drag is None:
            return None
        delta = self.__ReadDelta()
        if delta is None:
            return None
        index = self.DragIndex
        pos = tuple(self.Clamp(index, delta[0] + self.GripOffset[0], delta[1] + self.GripOffset[1]))
        if delta != self.DragLast:
            self.DragLast, self.Still, self.MovedAt = delta, 0, self.Frame
            self.Painter.Move(index, pos)
            view = self.Painter.ViewAt(index)
            if view is not None:
                self.__Frame(pos, view.Size)
            return index, pos[0], pos[1]
        if pos != self.Committed:
            self.Still += 1
            if self.Still >= EditorConst.DragSettle:
                self.Committed = pos
                self.Committing = True
                try:
                    self.OnMoved(index, pos[0], pos[1])
                finally:
                    self.Committing = False
            return index, pos[0], pos[1]
        return None

    def Clear(self):
        self.__HideSelect()
        if self.Hover is not None:
            self.Hover.SetVisible("", False)
        self.Painter.Clear()
