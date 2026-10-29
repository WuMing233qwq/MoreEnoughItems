# coding=utf-8

# ----------------------------------------------------------------------
#  menu.py is part of MoreEnoughItems.
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
配方树的节点菜单（PC 和触屏一样）：照触屏菜单的一个框（tooltip.md §6.12）—— 顶栏种类 + 小 x、内容、分隔线、
分段的按钮区，排版直接用触屏菜单的纯函数（menu/layout.box_layout），全部绝对定位。

内容是三样：标题（这一格完整的悬停文字）、一条配方、一行灰字。**配方先用这个类型自己的配方预览**（在配方树页面渲染
配方 ui_script，tooltip 那套 PREVIEW，preview.py）—— 透明着建，建齐了菜单才排版、才显示；类型不支持预览（`preview_def=None`）、
建不出来、等 0.5 秒还没齐，就用配方条兜底（工作方块 + 原料 → 产物，格子用 cell 模板）。

按钮是 JSON 里静态的一池（button.mei.tree.menu.<i>，BF_ButtonClickUp 单个绑定，引擎结论 §9）；步进器两头是图标按钮，
最多两个步进器。动作由脚本给（TreeMenuButton.Action），这里只排版、派发
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.mei_mod.state.settings import IsTreePreviewEnabled
from MEIScripts.mei_mod.ui_script.mei_ui.menu import layout
from MEIScripts.utils.text import error_text, native_str

from .cell import TreeCell
from .preview import MAX_TICKS, TreePreview

ViewBinder = clientApi.GetViewBinderCls()

LINE_H = 10
""" 一行字多高（和触屏菜单的 TEXT_H 一样）"""

CELL = 20
ARROW_W = 14
""" 一条配方里「->」那一格多宽 """

STRIP_PREVIEW = "preview"
""" 点了配方预览里的一格：on_strip((STRIP_PREVIEW, Item, 数量)) —— 预览的格子给的是 Item，不是物品键 """

WHITE = (1.0, 1.0, 1.0)
MUTED = (0.6, 0.6, 0.6)
DANGER = (1.0, 0.4, 0.4)


class TreeMenuButton(object):
    """ 一个按钮：字、点了做什么（无参）、能不能点、红字（删除类）、图标（"prev" / "next"：步进器两头）"""
    __slots__ = ("Text", "Action", "Enabled", "Danger", "Icon")

    def __init__(self, text="", action=None, enabled=True, danger=False, icon=None):
        self.Text = text
        self.Action = action
        self.Enabled = enabled
        self.Danger = danger
        self.Icon = icon


class TreeMenuRow(object):
    """ 一段：段名、按钮；Stepper 为真时只认两个按钮（两头），中间写 Number """
    __slots__ = ("Section", "Buttons", "Stepper", "Number")

    def __init__(self, section, buttons, stepper=False, number=""):
        self.Section = section
        self.Buttons = buttons
        self.Stepper = stepper
        self.Number = number


class TreeMenuModel(object):
    """
    Kind 顶栏种类、Title 标题、Strip 一条配方（[CellSpec]，位置由菜单排）、Arrow 箭头在第几格前（None 不画）、Info 灰字、Rows [TreeMenuRow]；
    Recipe 这条配方（MEI 的 Recipe）：给了就先试配方预览（preview.py），预览不了才用 Strip；PreviewTitle 预览自己的标题 ——
    用预览时菜单自己的标题藏起来、由它顶上（「类型名 · 物品名」一行，照收藏的配方预览）
    """
    __slots__ = ("Kind", "Title", "Strip", "Arrow", "Info", "Rows", "Recipe", "PreviewTitle")

    def __init__(self, kind, title, strip=None, arrow=None, info="", rows=None, recipe=None, preview_title=""):
        self.Kind = kind
        self.Title = title
        self.Strip = strip or []
        self.Arrow = arrow
        self.Info = info
        self.Rows = rows or []
        self.Recipe = recipe
        self.PreviewTitle = preview_title


def stepper(section, number, prev_action, next_action, prev_enabled=True, next_enabled=True):
    # type: (any, any, any, any, bool, bool) -> TreeMenuRow
    return TreeMenuRow(section, [TreeMenuButton(action=prev_action, enabled=prev_enabled, icon="prev"),
                                 TreeMenuButton(action=next_action, enabled=next_enabled, icon="next")],
                       stepper=True, number=number)


def fit_width(texts, minimum=14):  # type: (list, int) -> int
    """
    放得下这几种字的按钮要多宽：最宽的那种字 + 两边各 BUTTON_PAD（字宽照 menu/layout 的估法）。
    顶栏、汇总的按钮都按它改宽 —— 字会改，宽不能写死在 JSON 里
    """
    return max([minimum] + [layout.text_width(text) + 2 * layout.BUTTON_PAD for text in texts if text])


def fit_text(text, width):  # type: (any, int) -> unicode
    """ 一段字放不下 width 就从后面截短、末尾写「…」（字宽照 menu/layout 的估法）"""
    text = native_str(text or "").decode("utf-8", "replace")
    if layout.text_width(text) <= width:
        return text
    ellipsis = u"\u2026"
    while text and layout.text_width(text + ellipsis) > width:
        text = text[:-1]
    return text + ellipsis


def control_width(control, fallback=0):  # type: (any, int) -> int
    """ 控件现在多宽（JSON 里写死的间隔、小 x）；读不到给 fallback """
    if control is None:
        return fallback
    try:
        return int(round(control.GetSize()[0]))
    except Exception:  # noqa
        return fallback


def icon_size(control):  # type: (any) -> tuple
    """
    左右箭头（图标按钮）多大：读它在 JSON 里排出来的大小 —— 缺省在 mei_common.json 的 menu_icon_button（$menu_icon_size|default，
    只在那里调），触屏菜单、这里的菜单、汇总的翻页都跟它；读不到（还没排好）用 menu/layout 的缺省
    """
    if control is not None:
        try:
            width, height = control.GetSize()
            if width > 0 and height > 0:
                return int(round(width)), int(round(height))
        except Exception:  # noqa
            pass
    return layout.ICON_SIZE


def content_size(model, preview=None):  # type: (TreeMenuModel, tuple) -> tuple
    """
    内容的尺寸（含四周 4 像素）与里面几样的位置：((宽, 高), 标题 (x, y) 或 None, 配方条 (x, y) 或 None, 灰字 (x, y) 或 None, 预览 (x, y) 或 None)。
    preview 是建齐了的配方预览的尺寸（PREVIEW 自己四周各有 4 的边、自己带标题）：给了就排它、不排配方条，**菜单自己的标题不排**（给 None）——
    根摆在 (pad − 4, pad − 4)，它的标题正好落在菜单标题的位置 (pad, pad)
    """
    pad = layout.PAD
    strip = None
    shown = None
    if preview is not None:
        title = None
        shown = (pad - 4, pad - 4)
        width = int(preview[0]) - pad - 4  # 根的右边（pad − 4 + 宽）不出内容的右边（宽 + 2 × pad）
        y = pad - 4 + int(preview[1]) - 4  # 预览里内容的底边：灰字照旧隔 2 接在下面，没有灰字时根的下边正好是内容的下边
    else:
        lines = native_str(model.Title or "").split("\n")
        width = max([layout.text_width(line) for line in lines] + [0])
        title = (pad, pad)
        y = pad + len(lines) * LINE_H
        if model.Strip:
            y += 2
            strip = (pad, y)
            width = max(width, len(model.Strip) * CELL + (ARROW_W if model.Arrow is not None else 0))
            y += CELL
    info = None
    if model.Info:
        y += 2
        info = (pad, y)
        info_lines = native_str(model.Info).split("\n")
        width = max([width] + [layout.text_width(line) for line in info_lines])
        y += len(info_lines) * LINE_H
    return (width + 2 * pad, y + pad), title, strip, info, shown


class TreeMenu(object):
    """ on_close()：点了小 x；on_strip(target)：点了配方条里的一格 """

    def __init__(self, screen, binder, on_close, on_strip):
        self.Screen = screen
        self.OnClose = on_close
        self.OnStrip = on_strip
        get = screen.GetBaseUIControl
        self.Host = get(TreePath.Menu)
        self.Frame = get(TreePath.MenuFrame)
        self.Kind = get(TreePath.MenuKind)
        self.CloseSlot = get(TreePath.MenuCloseSlot)
        self.Content = get(TreePath.MenuContent)
        self.Title = get(TreePath.MenuTitle)
        self.Strip = get(TreePath.MenuStrip)
        self.Arrow = get(TreePath.MenuArrow)
        self.Info = get(TreePath.MenuInfo)
        self.Divider = get(TreePath.MenuDivider)
        self.Actions = get(TreePath.MenuActions)
        self.Buttons = [get(TreePath.MenuButton.format(i)) for i in range(TreeConst.MenuPool)]
        self.Icons = [(get(TreePath.MenuIcon.format(prev)), get(TreePath.MenuIcon.format(nxt)))
                      for prev, nxt in TreeConst.MenuIcons]
        self.Sections = [get(TreePath.MenuSection.format(i)) for i in range(TreeConst.MenuSections)]
        self.Numbers = [get(TreePath.MenuNumber.format(i)) for i in range(TreeConst.MenuNumbers)]
        self.Cells = []
        for index in range(TreeConst.StripCells):
            control = get(TreePath.MenuStripCell.format(index))
            if control is not None:
                cell = TreeCell(screen, control, index)
                self.Cells.append(cell)
                button = cell.Button()
                if button is not None:
                    button.AddTouchEventParams({"isSwallow": True, "strip": index})
                    button.SetButtonTouchUpCallback(self.OnStripUp)
        self.ButtonActions = [None] * len(self.Buttons)
        self.IconActions = {}
        self.Open = False
        # 配方预览（preview.py）：建齐之前菜单先不排（Pending 记着要排的那一份），每帧 Tick 开始建、问它好了没有
        self.Preview = TreePreview(screen, TreePath.MenuPreview, self.OnPreviewSlot)
        self.Pending = None  # type: tuple or None  # (model, anchor, 开始建了没有)
        for index in range(len(self.Buttons)):
            binder.Bind(self.__Handler(index), ViewBinder.BF_ButtonClickUp, TreeConst.MenuButtonName.format(index))
        for prev, nxt in TreeConst.MenuIcons:
            for slot in (prev, nxt):
                binder.Bind(self.__IconHandler(slot), ViewBinder.BF_ButtonClickUp, TreeConst.MenuIconName.format(slot))
        binder.Bind(self.OnCloseClick, ViewBinder.BF_ButtonClickUp, TreeConst.MenuCloseName)
        if self.Host is None or self.Frame is None:
            logger.error("[MEI/tree] 配方树的菜单控件不全")

    # 派发
# ======================================================================================================================
    def __Handler(self, index):
        def handler(_args=None):
            self.__Run(self.ButtonActions[index] if index < len(self.ButtonActions) else None)
        return handler

    def __IconHandler(self, slot):
        def handler(_args=None):
            self.__Run(self.IconActions.get(slot))
        return handler

    @staticmethod
    def __Run(action):
        if action is None:
            return
        try:
            action()
        except Exception as e:  # noqa  按钮回调里抛出去引擎不给日志（引擎结论 §15）
            logger.error("[MEI/tree] 菜单动作出错: {}".format(error_text(e)))

    def OnCloseClick(self, _args=None):
        self.OnClose()

    def OnStripUp(self, args):
        params = args.get("AddTouchEventParams") or {}
        index = params.get("strip")
        if index is not None and 0 <= index < len(self.Cells) and self.Cells[index].Target is not None:
            self.OnStrip(self.Cells[index].Target)

    def OnPreviewSlot(self, panel):
        """ 点了配方预览里的一格（TreeRecipesGridBind 转来，在绑定回调里）：和点配方条一样，交给脚本写灰字 """
        item = getattr(panel, "Item", None)
        if item is None:
            return
        count = getattr(getattr(panel, "Stack", None), "Count", 1) or 1
        try:
            self.OnStrip((STRIP_PREVIEW, item, count))
        except Exception as e:  # noqa  绑定回调里抛出去引擎不给日志（引擎结论 §15）
            logger.error("[MEI/tree] 点配方预览出错: {}".format(error_text(e)))

    # 显示
# ======================================================================================================================
    def Hide(self):
        self.Open = False
        self.Pending = None
        self.Preview.Stop()
        self.ButtonActions = [None] * len(self.Buttons)
        self.IconActions = {}
        if self.Host is not None:
            self.Host.SetVisible(False)

    def Destroy(self):
        """ 关配方树：预览的脚本、绑定、控件一起拆 """
        self.Pending = None
        self.Preview.Destroy()

    def Tick(self):
        """
        每帧（脚本的 OnTick）：Show 记下的配方预览在这里开始建（建控件、挂绑定不在按钮回调里做）；
        建齐了就排菜单、拉回不透明；等太久（0.5 秒）、脚本接坏了或建不出来就用配方条
        """
        if self.Pending is None:
            return
        model, anchor, started = self.Pending
        if not started:
            if not self.Preview.Begin(model.Recipe, model.PreviewTitle):
                self.Pending = None
                self.__Present(model, anchor, None)
                return
            self.Pending = (model, anchor, True)
            return
        if not self.Preview.Poll() and not self.Preview.TimedOut():
            return
        self.Pending = None
        if self.Preview.Ready:
            self.__Present(model, anchor, self.Preview.Size)
            return
        if self.Preview.Ticks >= MAX_TICKS:
            logger.warn("[MEI/tree] 配方预览等了 {} 帧还没建齐（{}），用配方条".format(self.Preview.Ticks, self.Preview.Stage()))
        else:
            logger.warn("[MEI/tree] 配方预览建不成（{}），用配方条".format(self.Preview.Stage()))
        self.Preview.Stop()
        self.__Present(model, anchor, None)

    def SetInfo(self, text):  # type: (any) -> None
        """ 只改灰字（点了配方条里的一格写它的名字）"""
        if self.Info is not None and text:
            self.Info.asLabel().SetText(native_str(text))
            self.Info.SetVisible(True)

    def Show(self, model, anchor):  # type: (TreeMenuModel, tuple) -> None
        """
        anchor 是点开它的那一格在界面根面板里的 (x, y, 宽, 高)：菜单摆在它旁边。
        给了配方的先试配方预览：同一条已经建好、正亮着的当场排；要建的先记着，下一帧的 Tick 里开始建、建齐了再排 ——
        Show 常在按钮回调里被调（菜单动作改完东西重开），建控件、挂绑定不在那里做（引擎结论 §27-2）
        """
        if self.Host is None or self.Frame is None:
            return
        pending, self.Pending = self.Pending, None
        # 设置「启用节点配方预览Tooltip」关着：直接用配方条（切换时的闪动晃眼，给个开关）
        if model.Recipe is not None and IsTreePreviewEnabled() and self.Preview.Supports(model.Recipe):
            if self.Preview.Showing(model.Recipe):
                self.__Present(model, anchor, self.Preview.Size)
                return
            # 同一条正建着（菜单动作当场重排一次、重画完又排一次）：接着建，只换成新的这一份模型与位置
            started = pending is not None and pending[2] and self.Preview.Building(model.Recipe)
            self.Pending = (model, anchor, started)
            self.__Conceal()
            return
        self.__Present(model, anchor, None)

    def __Conceal(self):
        """
        配方预览建着的这几帧：整个框透明（frame 的 alpha 0 + propagate_alpha，子控件跟着），宿主却得亮着 ——
        藏着的话引擎不建预览 grid 的格子（每一类都会等到超时、全用配方条，引擎结论 §38）。旧菜单的按钮先不响应；
        算开着（ESC 先关菜单）
        """
        self.ButtonActions = [None] * len(self.Buttons)
        self.IconActions = {}
        self.Frame.SetAlpha(0.0)
        self.Host.SetVisible(True)
        self.Open = True

    def __Present(self, model, anchor, preview):  # type: (TreeMenuModel, tuple, tuple) -> None
        """ 排版、显示；preview 是建齐了的配方预览尺寸（None 就用配方条）"""
        # 框先拉回不透明：建预览时写过 0。放在最前 —— 下面给个别控件写的透明度（灰掉的箭头）在它之后，不会被它带着改掉
        self.Frame.SetAlpha(1.0)
        size, title_pos, strip_pos, info_pos, preview_pos = content_size(model, preview)
        rows, specs = self.__Rows(model.Rows)
        # 段名那一列按最长的段名给宽（缺省两个字宽）：段名改长了也不压到按钮
        label_w = max([layout.LABEL_W] + [layout.text_width(row.Section) for row in model.Rows])
        box = layout.box_layout(size, rows, labels=True, kind_width=layout.text_width(model.Kind),
                                close_size=layout.CLOSE_SIZE, close_offset=layout.CLOSE_OFFSET, label_w=label_w)
        self.Frame.SetSize(box["size"], False)
        self.Kind.SetPosition(box["kind"])
        self.Kind.asLabel().SetText(native_str(model.Kind))
        self.CloseSlot.SetPosition(box["close"][:2])
        self.Content.SetPosition(box["content"])
        # 用配方预览时标题由它顶上（它自己带标题），菜单自己的藏起来；两个方向都写（界面状态跨开关存活，引擎结论 §22）
        if title_pos is not None:
            self.Title.SetPosition(title_pos)
            self.Title.asLabel().SetText(native_str(model.Title or ""))
        self.Title.SetVisible(title_pos is not None)
        self.__ShowStrip(model, strip_pos)
        if preview_pos is not None:
            self.Preview.Reveal(preview_pos)
        else:
            self.Preview.Stop()
        if info_pos is not None:
            self.Info.SetPosition(info_pos)
            self.Info.asLabel().SetText(native_str(model.Info))
        self.Info.SetVisible(info_pos is not None)
        if box["divider"] is not None:
            x, y, width = box["divider"]
            self.Divider.SetPosition((x, y))
            self.Divider.SetSize((width, 1), False)
        self.Divider.SetVisible(box["divider"] is not None)
        self.Actions.SetPosition(box["actions"][:2])
        self.__ShowButtons(model.Rows, specs, box)
        self.__Place(box["size"], anchor)
        self.Host.SetVisible(True)
        self.Open = True

    def __Rows(self, rows):
        """ 交给 box_layout 的 (items, 是不是步进器, 数字至少多宽)，和每个按钮对应的 TreeMenuButton（同样的顺序）"""
        result, specs = [], []
        icon_w, icon_h = icon_size(self.Icons[0][0] if self.Icons else None)
        for row in rows:
            items = []
            for button in row.Buttons:
                if button.Icon:
                    items.append((icon_w, icon_h, True))
                else:
                    items.append((layout.button_width([button.Text]), layout.BUTTON_H, False))
                specs.append(button)
            result.append((items, row.Stepper, layout.number_width(row.Number) if row.Stepper else 0))
        return result, specs

    def __ShowStrip(self, model, pos):
        if pos is not None:
            self.Strip.SetPosition(pos)
        x = 0
        for index, cell in enumerate(self.Cells):
            if pos is None or index >= len(model.Strip):
                cell.Hide()
                continue
            if model.Arrow is not None and index == model.Arrow:
                self.Arrow.SetPosition((x + 2, 6))
                x += ARROW_W
            spec = model.Strip[index]
            spec.Pos = (x, 0)
            cell.Apply(spec)
            x += CELL
        self.Strip.SetVisible(pos is not None)
        self.Arrow.SetVisible(pos is not None and model.Arrow is not None and model.Arrow < len(model.Strip))

    def __ShowButtons(self, rows, specs, box):
        self.ButtonActions = [None] * len(self.Buttons)
        self.IconActions = {}
        used_buttons = 0
        used_icons = set()
        steppers = 0
        order = 0
        for row_index, row in enumerate(rows):
            stepper_slot = None
            if row.Stepper:
                stepper_slot = steppers
                steppers += 1
            for button in row.Buttons:
                spec = specs[order]
                x, y, width, height = box["buttons"][order]
                order += 1
                if button.Icon:
                    if stepper_slot is None or stepper_slot >= len(self.Icons):
                        continue
                    side = 0 if button.Icon == "prev" else 1
                    control = self.Icons[stepper_slot][side]
                    slot = TreeConst.MenuIcons[stepper_slot][side]
                    used_icons.add(slot)
                    if control is None:
                        continue
                    control.SetPosition((x, y))
                    control.SetVisible(True)
                    control.SetAlpha(1.0 if spec.Enabled else 0.35)
                    self.IconActions[slot] = spec.Action if spec.Enabled else None
                    continue
                if used_buttons >= len(self.Buttons):
                    logger.warn("[MEI/tree] 菜单按钮不够用（{} 个）".format(len(self.Buttons)))
                    continue
                control = self.Buttons[used_buttons]
                self.ButtonActions[used_buttons] = spec.Action if spec.Enabled else None
                used_buttons += 1
                if control is None:
                    continue
                control.SetPosition((x, y))
                control.SetSize((width, height), True)
                label = control.GetChildByPath(TreePath.ButtonLabel)
                if label is not None:
                    label.asLabel().SetText(native_str(spec.Text))
                    label.asLabel().SetTextColor(DANGER if spec.Danger else (WHITE if spec.Enabled else MUTED))
                mask = control.GetChildByPath(TreePath.ButtonMask)
                if mask is not None:
                    mask.SetVisible(not spec.Enabled)
                control.SetVisible(True)
            if row_index < len(self.Sections) and self.Sections[row_index] is not None:
                section = self.Sections[row_index]
                if box["names"][row_index] is not None:
                    section.SetPosition(box["names"][row_index])
                section.asLabel().SetText(native_str(row.Section))
                section.SetVisible(True)
            if stepper_slot is not None and stepper_slot < len(self.Numbers) and self.Numbers[stepper_slot] is not None:
                number = box["numbers"][row_index]
                control = self.Numbers[stepper_slot]
                if number is not None:
                    control.SetPosition((number[0], number[1]))
                    control.SetSize((number[2], LINE_H), False)
                control.asLabel().SetText(native_str(row.Number))
                control.SetVisible(True)
        for index in range(used_buttons, len(self.Buttons)):
            if self.Buttons[index] is not None:
                self.Buttons[index].SetVisible(False)
        for slots, controls in zip(TreeConst.MenuIcons, self.Icons):
            for slot, control in zip(slots, controls):
                if slot not in used_icons and control is not None:
                    control.SetVisible(False)
        for index in range(len(rows), len(self.Sections)):
            if self.Sections[index] is not None:
                self.Sections[index].SetVisible(False)
        for index in range(steppers, len(self.Numbers)):
            if self.Numbers[index] is not None:
                self.Numbers[index].SetVisible(False)

    def __Place(self, size, anchor):
        root = self.Screen.GetBaseUIControl(TreePath.Root)
        try:
            root_w, root_h = root.GetSize()
        except Exception:  # noqa
            root_w, root_h = 427, 240
        x0, y0, w0, _h0 = anchor
        x = x0 + w0 + 4
        if x + size[0] > root_w - 4:
            x = x0 - 4 - size[0]
        x = max(4, min(int(root_w) - 4 - size[0], x))
        y = max(4, min(int(root_h) - 4 - size[1], y0 - 8))
        self.Host.SetPosition((int(x), int(y)))
