# coding=utf-8
# ----------------------------------------------------------------------
#  form.py is part of MoreEnoughItems.
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
编辑器左栏的表单：一池固定的控件（editor.json 左栏的 l / v / b / i / e / r 几组），按要显示的几行（FormRow）摆位置、写字、切显隐 ——
照配方树节点菜单那一池静态按钮的做法，换内容不建控件（只写变了的，blocks/writer.py）。
按钮的点击走触摸回调（参数是池里的下标），输入框隔几帧读一次原文、变了交给 on_action(行的键, "text", 字)；
行多了一页放不下就分页（最后一行是翻页）。几种行：
    TITLE 标题  TEXT 一行说明  STEP 步进（4 个按钮）  CHOICE 左右切换  EDIT 输入框  BUTTONS 一排按钮  TILE 控件池的一格  ITEM 一样物品 + 按钮
带标签的行左边是一列标签（宽度取这一页最长的标签，夹在 LABEL_MIN ~ LABEL_MAX），控件从标签列右边排到右边界；不带标签的从左边界排起。
写控件都经 ControlWriter（显隐不当场刷新界面）：调用方这一批写完 flush 一次。
一个界面可以有几张表单（自定义配方管理器左右各一张，mei_ui/manager/）：每张给自己那一池控件所在的面板（root）、池子大小（counts）、行宽（width）；
池子里控件的名字（l / v / b / i / e / r 加下标）与模板（MeiEditor.form_*）大家一样
"""
from mod_log import logger

from MEIScripts.constants.ui import EditorConst, EditorPath
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import ControlWriter
from MEIScripts.mei_mod.ui_script.mei_ui.menu.layout import text_width
from MEIScripts.utils import utilities
from MEIScripts.utils.text import error_text, native_str

TITLE, TEXT, STEP, CHOICE, EDIT, BUTTONS, TILE, ITEM = "title", "text", "step", "choice", "edit", "buttons", "tile", "item"
LABELED = (STEP, CHOICE, EDIT, ITEM)
""" 有标签列的几种行 """

HEIGHTS = {TITLE: 13, TEXT: 11}
ROW_H = EditorConst.RowHeight
LEFT = 3
WIDTH = EditorConst.LeftWidth - EditorConst.Pad - 3
""" 一行的左右边界（左栏宽 LeftWidth - Pad，两边各留 3）"""

LABEL_MIN, LABEL_MAX = 12, 28
""" 标签列的宽：这一页最长的标签（汉字按 9 算），夹在这中间 —— 28 放得下三个字（工作站）"""

STEP_BIG, STEP_SMALL = 20, 12
""" 步进的大步、小步按钮宽（大步写「-10」「+1k」，三个半角字）"""

ICON_W = 14
""" ITEM 行右边的小按钮（选 / 清）：一个字的按钮这么宽，字多的按字算 """

WHITE = (0.95, 0.95, 0.95)
MUTE = (0.6, 0.62, 0.66)
VALUE = (0.86, 0.87, 0.9)
DANGER = (1.0, 0.45, 0.45)

ON, OFF, RED = "on", "off", "red"
""" 按钮的样子：开着（亮底）、灰掉（点了没反应）、红字（删除类）"""

PAGER = "__pager"


def fit(text, width):  # type: (any, int) -> unicode
    """ 放不下就截短、末尾写「…」"""
    text = text if isinstance(text, unicode) else native_str(text or "").decode("utf-8", "replace")
    if text_width(text) <= width:
        return text
    while text and text_width(text + u"…") > width:
        text = text[:-1]
    return text + u"…"


class FormRow(object):
    """
    左栏的一行。Buttons：[(op, 字, 样子)]，样子是 ON / OFF / RED 或 None；
    STEP 是 4 个（大减、减、加、大加），CHOICE 是 2 个（前、后），BUTTONS 是 1 ~ 4 个，TILE 是 1 个，ITEM 是 1 ~ 2 个
    """

    __slots__ = ("Kind", "Key", "Label", "Value", "Buttons", "Text", "Item", "Icon", "Color")

    def __init__(self, kind, key="", label=u"", value=u"", buttons=(), text=None, item=None, icon=None, color=None):
        self.Kind = kind
        self.Key = key
        self.Label = label
        self.Value = value
        self.Buttons = list(buttons)
        self.Text = text
        self.Item = item
        self.Icon = icon
        self.Color = color


def step_row(key, label, value, small, big):  # type: (str, any, any, int, int) -> FormRow
    """ 步进的一行：大减、减、加、大加（op 是带符号的数，「-10」「+1」）"""
    return FormRow(STEP, key, label=label, value=str(value), buttons=[
        ("-{}".format(big), u"-{}".format(big), None), ("-{}".format(small), u"-", None),
        ("+{}".format(small), u"+", None), ("+{}".format(big), u"+{}".format(big), None)])


EDITOR_COUNTS = {"l": EditorConst.Labels, "v": EditorConst.Values, "b": EditorConst.Buttons, "i": EditorConst.Icons,
                 "e": EditorConst.Edits, "r": EditorConst.Items}
""" 编辑器左栏那一池的大小（editor.json）"""


def button_width(text):  # type: (any) -> int
    """ ITEM 行右边一个按钮的宽：一个字 ICON_W，字多的按字算 """
    width = text_width(text) + 6
    return ICON_W if width <= ICON_W + 1 else width


class Form(object):

    def __init__(self, screen, on_action, root=None, counts=None, width=None):
        self.Screen = screen
        self.OnAction = on_action  # type: callable  # on_action(行的键, op, 值)
        self.Root = root or EditorPath.Left  # type: str  # 池子所在的面板
        self.Width = int(width or WIDTH)  # type: int  # 行的右边界（面板宽减 3）；面板宽跟着屏幕变的，调用方改它再 Show
        counts = counts or EDITOR_COUNTS
        self.Labels = [self.__Writer("{}/l{}".format(self.Root, i)) for i in range(counts.get("l", 0))]
        self.Values = [self.__Writer("{}/v{}".format(self.Root, i)) for i in range(counts.get("v", 0))]
        self.Buttons = [self.__Writer("{}/b{}".format(self.Root, i)) for i in range(counts.get("b", 0))]
        self.Icons = [self.__Writer("{}/i{}".format(self.Root, i)) for i in range(counts.get("i", 0))]
        self.Edits = [self.__Writer("{}/e{}".format(self.Root, i)) for i in range(counts.get("e", 0))]
        self.Items = [self.__Writer("{}/r{}".format(self.Root, i)) for i in range(counts.get("r", 0))]
        self.ButtonOps = {}  # type: dict  # 按钮池的下标 -> (行的键, op)
        self.EditKeys = {}  # type: dict  # 输入框池的下标 -> 行的键
        self.EditSeen = {}  # type: dict  # 输入框池的下标 -> 上次读到 / 写下的字
        self.Height = 200  # type: int  # 左栏能用的高
        self.LabelWidth = LABEL_MIN  # type: int  # 这一页标签列的宽
        self.Page = 0
        self.Pages = 1
        self.Frame = 0
        for index, writer in enumerate(self.Buttons):
            self.__BindButton(writer, index)

    def __Writer(self, path):  # type: (str) -> ControlWriter or None
        control = self.Screen.GetBaseUIControl(path)
        if control is None:
            logger.warn("[MEI/editor] 表单的控件 {} 取不到".format(path))
            return None
        return ControlWriter(self.Screen, control)

    def __BindButton(self, writer, index):
        if writer is None:
            return
        try:
            button = writer.Control.asButton()
            button.AddTouchEventParams({"isSwallow": True, "form": index})
            button.SetButtonTouchUpCallback(self.__OnUp)
        except Exception as e:  # noqa
            logger.error("[MEI/editor] 左栏的按钮挂不上触摸回调: {}".format(error_text(e)))

    def __OnUp(self, args):
        index = (args.get("AddTouchEventParams") or {}).get("form")
        target = self.ButtonOps.get(index)
        if target is None:
            return
        key, op = target
        if key == PAGER:
            self.Page = max(0, min(self.Pages - 1, self.Page + (1 if op == "next" else -1)))
            self.OnAction(PAGER, op, None)
            return
        self.OnAction(key, op, None)

    # 摆
# ======================================================================================================================
    def Show(self, rows):  # type: (list) -> None
        """ 照这几行摆一遍（只写变了的）；一页放不下就分页，停在原来那一页（超了就最后一页）"""
        pages = self.__Paginate(rows)
        self.Pages = len(pages)
        self.Page = max(0, min(self.Page, self.Pages - 1))
        shown = list(pages[self.Page])
        if self.Pages > 1:
            shown.append(FormRow(CHOICE, PAGER, value=u"{}/{}".format(self.Page + 1, self.Pages),
                                 buttons=[("prev", u"<", OFF if self.Page == 0 else None),
                                          ("next", u">", OFF if self.Page == self.Pages - 1 else None)]))
        self.ButtonOps, edit_keys = {}, {}
        used = {"l": 0, "v": 0, "b": 0, "i": 0, "e": 0, "r": 0}
        widths = [text_width(row.Label) for row in shown if row.Label and row.Kind in LABELED]
        self.LabelWidth = max(LABEL_MIN, min(LABEL_MAX, max(widths) if widths else LABEL_MIN))
        y = 3
        for row in shown:
            try:
                self.__Place(row, y, used, edit_keys)
            except Exception as e:  # noqa  一行摆坏了不拖垮整个左栏
                logger.error("[MEI/editor] 左栏摆不下一行 {}: {}".format(row.Key, error_text(e)))
            y += HEIGHTS.get(row.Kind, ROW_H)
        self.__HideRest(used)
        for index in list(self.EditSeen):
            if edit_keys.get(index) != self.EditKeys.get(index):
                self.EditSeen.pop(index, None)
        self.EditKeys = edit_keys

    def __Paginate(self, rows):  # type: (list) -> list
        room = max(ROW_H * 2, self.Height - 4)
        pages, page, used = [], [], 0
        for row in rows:
            height = HEIGHTS.get(row.Kind, ROW_H)
            if page and used + height > room - ROW_H:
                pages.append(page)
                page, used = [], 0
            page.append(row)
            used += height
        pages.append(page)
        if len(pages) == 2 and sum(HEIGHTS.get(r.Kind, ROW_H) for r in rows) <= room:
            return [rows]  # 留给翻页的那一行其实用不着
        return pages

    def __Take(self, used, kind, pool):  # type: (dict, str, list) -> ControlWriter or None
        index = used[kind]
        if index >= len(pool):
            return None
        used[kind] = index + 1
        return pool[index]

    def __Label(self, used, text, pos, color):
        writer = self.__Take(used, "l", self.Labels)
        if writer is not None:
            writer.SetText("", text, color)
            writer.SetPos(pos)
            writer.SetVisible("", True)

    def __Value(self, used, text, pos, color=VALUE, center_width=None):
        writer = self.__Take(used, "v", self.Values)
        if writer is None:
            return
        if center_width is not None:
            text = fit(text, center_width)
            pos = (pos[0] + max(0, (center_width - text_width(text)) // 2), pos[1])
        writer.SetText("", text, color)
        writer.SetPos(pos)
        writer.SetVisible("", True)

    def __Button(self, used, key, op, text, style, pos, width):
        index = used["b"]
        writer = self.__Take(used, "b", self.Buttons)
        if writer is None:
            return
        writer.SetPos(pos)
        writer.SetSize("", (width, 14))
        writer.SetText(EditorPath.ButtonLabel, fit(text, width - 2), DANGER if style == RED else VALUE)
        writer.SetVisible("/on", style == ON)
        writer.SetVisible(EditorPath.ButtonMask, style == OFF)
        writer.SetVisible("", True)
        if style != OFF:
            self.ButtonOps[index] = (key, op)

    def __Place(self, row, y, used, edit_keys):
        kind = row.Kind
        if kind == TITLE:
            value_w = text_width(row.Value) + 4 if row.Value else 0
            self.__Label(used, fit(row.Label, self.Width - LEFT - value_w), (LEFT, y + 1), row.Color or WHITE)
            if row.Value:
                self.__Value(used, row.Value, (self.Width - text_width(row.Value), y + 1), MUTE)
            return
        if kind == TEXT:
            self.__Label(used, fit(row.Label, self.Width - LEFT), (LEFT, y), row.Color or MUTE)
            return
        x0 = LEFT
        if row.Label and kind in LABELED:
            self.__Label(used, fit(row.Label, self.LabelWidth), (LEFT, y + 2), MUTE)
            x0 = LEFT + self.LabelWidth + 3
        buttons = row.Buttons
        if kind == STEP:
            slots = ((x0, STEP_BIG), (x0 + STEP_BIG + 1, STEP_SMALL),
                     (self.Width - STEP_BIG - 1 - STEP_SMALL, STEP_SMALL), (self.Width - STEP_BIG, STEP_BIG))
            for (op, text, style), (x, width) in zip(buttons, slots):
                self.__Button(used, row.Key, op, text, style, (x, y), width)
            left = x0 + STEP_BIG + STEP_SMALL + 2
            self.__Value(used, row.Value, (left, y + 2), row.Color or VALUE,
                         center_width=self.Width - STEP_BIG - STEP_SMALL - 2 - left)
        elif kind == CHOICE:
            for (op, text, style), (x, width) in zip(buttons, ((x0, 13), (self.Width - 13, 13))):
                self.__Button(used, row.Key, op, text, style, (x, y), width)
            self.__Value(used, row.Value, (x0 + 14, y + 2), row.Color or VALUE, center_width=self.Width - 14 - (x0 + 14))
        elif kind == EDIT:
            self.__Edit(used, row, (x0, y), edit_keys)
        elif kind == BUTTONS:
            count = max(1, len(buttons))
            width = (self.Width - LEFT - (count - 1)) // count
            for index, (op, text, style) in enumerate(buttons):
                self.__Button(used, row.Key, op, text, style, (LEFT + index * (width + 1), y), width)
        elif kind == TILE:
            op, text, style = buttons[0] if buttons else ("add", row.Label, None)
            self.__Button(used, row.Key, op, u"", style, (LEFT, y), self.Width - LEFT)
            icon = self.__Take(used, "i", self.Icons)
            if icon is not None:
                icon.SetSprite("", row.Icon or "textures/ui/mei/blank")
                icon.SetPos((LEFT + 2, y + 1))
                icon.SetVisible("", bool(row.Icon))
            value_w = text_width(row.Value) + 4 if row.Value else 0
            self.__Label(used, fit(row.Label, self.Width - 3 - (LEFT + 18) - value_w), (LEFT + 18, y + 2),
                         row.Color or (VALUE if style != OFF else MUTE))
            if row.Value:
                self.__Value(used, row.Value, (self.Width - 3 - text_width(row.Value), y + 2), MUTE)
        elif kind == ITEM:
            right = self.Width
            for op, text, style in reversed(buttons):
                width = button_width(text)
                right -= width
                self.__Button(used, row.Key, op, text, style, (right, y), width)
                right -= 1
            renderer = self.__Take(used, "r", self.Items)
            if renderer is not None:
                shown = renderer.SetItem("", row.Item)
                renderer.SetPos((x0, y - 1))
                renderer.SetVisible("", shown)
            if row.Text:  # 灰字的后缀（管理器的页面一行写「几条」）：贴着按钮，名字放不下先截名字
                suffix_w = text_width(row.Text)
                self.__Value(used, row.Text, (right - 2 - suffix_w, y + 2), MUTE)
                right -= suffix_w + 4
            self.__Value(used, fit(row.Value, right - 2 - (x0 + 18)), (x0 + 18, y + 2), row.Color or VALUE)

    def __Edit(self, used, row, pos, edit_keys):
        index = used["e"]
        writer = self.__Take(used, "e", self.Edits)
        if writer is None:
            return
        writer.SetPos(pos)
        writer.SetSize("", (self.Width - pos[0], 14))
        writer.SetVisible("", True)
        edit_keys[index] = row.Key
        text = native_str(row.Text or u"")
        if self.EditKeys.get(index) != row.Key or self.EditSeen.get(index) != text:
            # 换了一行、或者内容被别处改了（换了积木、撤了改动）才写进去 —— 玩家正在打的字不覆盖
            try:
                writer.Control.asTextEditBox().SetEditText(text)
            except Exception as e:  # noqa
                logger.warn("[MEI/editor] 输入框写不进字: {}".format(error_text(e)))
            self.EditSeen[index] = text

    def __HideRest(self, used):
        for kind, pool in (("l", self.Labels), ("v", self.Values), ("b", self.Buttons), ("i", self.Icons),
                           ("e", self.Edits), ("r", self.Items)):
            for writer in pool[used[kind]:]:
                if writer is not None:
                    writer.SetVisible("", False)

    # 输入框
# ======================================================================================================================
    def Poll(self):
        """ 每帧调：隔几帧读一次显示着的输入框，变了交给 on_action(键, "text", 字) """
        self.Frame += 1
        if self.Frame % EditorConst.TextPoll:
            return
        for index, key in list(self.EditKeys.items()):
            writer = self.Edits[index]
            if writer is None:
                continue
            try:
                text = native_str(utilities.GetEditBoxRawText(writer.Control) or "")
            except Exception:  # noqa  输入框刚显出来还没排好
                continue
            if text != self.EditSeen.get(index):
                self.EditSeen[index] = text
                self.OnAction(key, "text", text)

    def TextSnapshot(self):  # type: () -> tuple
        """ 显示着的输入框此刻的字（快捷键判断「这一下是不是打字」用）"""
        result = []
        for index in sorted(self.EditKeys):
            writer = self.Edits[index]
            try:
                result.append(utilities.GetEditBoxRawText(writer.Control) if writer is not None else None)
            except Exception:  # noqa
                result.append(None)
        return tuple(result)
