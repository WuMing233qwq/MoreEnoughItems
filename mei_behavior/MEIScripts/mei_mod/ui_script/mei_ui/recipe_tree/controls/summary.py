# coding=utf-8

# ----------------------------------------------------------------------
#  summary.py is part of MoreEnoughItems.
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
配方树右侧的材料汇总清单：四个页签（原料 / 副产物 / 工具 / 还缺），一行一样东西 —— 格子、名字、一行「需 · 有 · 缺」，
放不下翻页；底下是统计、翻页与「刷新背包」。中间物不单列（玩家要看的只有原料和副产物）；副产物是合成多出来的加上配方的其他产出，
概率产出的格子右上标小方块。

背包对照只在这里：缺不缺看背包放进库存走的那一遍（modules/summary.shortfall）：背包里的中间材料也扣 ——
有 9 个铁锭就不再缺这 9 个铁锭的粗铁。背包开界面时读一次，「刷新背包」再读（脚本做，这里只画）。

汇总栏的宽（展开 / 收起的过渡）由脚本改（SetShown），里面的 body 定宽：变窄时从右边裁掉
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.texts import TreeText
from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.mei_mod.ui_script.mei_ui.menu import layout
from MEIScripts.utils.text import native_str

from .cell import CellSpec, TreeCell
from .menu import control_width, fit_text, fit_width

ViewBinder = clientApi.GetViewBinderCls()

TAB_RAW = "raw"
TAB_BYPRODUCT = "byproduct"
TAB_TOOL = "tool"
TAB_LACK = "lack"
TABS = (TAB_RAW, TAB_BYPRODUCT, TAB_TOOL, TAB_LACK)
TAB_TEXTS = {TAB_RAW: TreeText.TabRaw, TAB_BYPRODUCT: TreeText.TabByproduct, TAB_TOOL: TreeText.TabTool,
             TAB_LACK: TreeText.TabLack}

TAB_GAPS = ("gap_0", "gap_1", "gap_2")
""" 页签之间的间隔（JSON 里写死的宽，脚本读回来算页签一共多宽）"""
PAD = 2
""" 页签、清单离汇总栏左边的空（JSON 里 tabs / rows 的 offset）"""
NAME_X = 23
""" 名字、第二行从这一行的哪儿开始（格子 20 + 间隔 3，JSON 里 name / info 的 offset）"""
LINE_H = 10
PAGER_W = 58
""" 左下翻页那一块（◀ 页码 ▶，JSON 里 prev / page / next 的位置）连同它和「刷新背包」之间的空 """
FOOT_GAP = 19
""" 统计贴着底下那一行往上长（JSON 里 foot 的 offset）"""


def list_rows(tab, summary, have, flags=None, lack=None):  # type: (str, any, dict, dict, dict) -> list
    """
    这一页的清单：[(物品键, 第二行的字, 右上小方块的颜色)]，纯函数（探针测）。
    lack 是还缺的原料（shortfall 的结果，中间物也扣）：「缺少材料」页就是它，「所需原料」页的「缺 / 够了」也看它（「需」照旧不扣背包）；
    不给时退回只在原料那一层比背包
    """
    flags = flags or {}
    rows = []
    if summary is None:
        return rows
    if lack is None:
        lack = dict((key, need - int(have.get(key, 0) or 0)) for key, need in summary.Raw.items()
                    if int(have.get(key, 0) or 0) < need)
    if tab == TAB_LACK:
        for key, count in summary.Sorted(lack):
            if count > 0:
                rows.append((key, TreeText.RowLackOnly.format(int(have.get(key, 0) or 0), count), None))
        return rows
    table = {TAB_RAW: summary.Raw, TAB_BYPRODUCT: summary.Byproducts, TAB_TOOL: summary.Tools}.get(tab, {})
    for key, count in summary.Sorted(table):
        owned = int(have.get(key, 0) or 0)
        if tab == TAB_BYPRODUCT:
            chance = key in summary.Chance
            rows.append((key, TreeText.RowExtra.format(count) + (TreeText.RowChance if chance else u""),
                         TreeConst.ChanceColor if chance else None))
            continue
        short = lack.get(key, 0) if tab == TAB_RAW else count - owned
        info = TreeText.RowNeedHave.format(count, owned) + (TreeText.RowLack.format(short) if short > 0 else
                                                             TreeText.RowEnough)
        rows.append((key, info, TreeConst.BadgeColors.get(flags.get(key)) if tab == TAB_RAW else None))
    return rows


def foot_lines(text, width):  # type: (any, int) -> int
    """ 统计在这么宽里排几行（label 自己换行；字宽照 menu/layout 的估法，宁多不少）"""
    lines = 0
    for part in native_str(text or "").decode("utf-8", "replace").split(u"\n"):
        lines += max(1, -(-layout.text_width(part) // max(1, width)))
    return lines


def capacity(height, foot_h):  # type: (int, int) -> int
    """ 汇总栏这么高、统计占 foot_h 时一页放几行 """
    room = height - TreeConst.SummaryTop - FOOT_GAP - foot_h - 2
    return max(1, min(TreeConst.SummaryRows, (room + 2) // TreeConst.SummaryRowH))


class SummaryRow(object):
    """ 清单的一行：行控件、它里面的格子（TreeCell）和两行字 """
    __slots__ = ("Control", "Cell", "Name", "Info", "Shown", "Texts")

    def __init__(self, control, cell, name, info):
        self.Control = control
        self.Cell = cell
        self.Name = name
        self.Info = info
        self.Shown = None  # type: bool or None
        self.Texts = (None, None)

    def SetVisible(self, on):  # type: (bool) -> None
        if self.Shown != on:
            self.Shown = on
            self.Control.SetVisible(on)
        if not on:
            self.Cell.Hide()

    def SetTexts(self, name, info):  # type: (unicode, unicode) -> None
        if self.Texts == (name, info):
            return
        self.Texts = (name, info)
        for label, text in ((self.Name, name), (self.Info, info)):
            if label is not None:
                label.asLabel().SetText(native_str(text))


class TreeSummary(object):
    """ on_tab(tab)、on_refresh()、on_cell(key, cell)：脚本接 """

    def __init__(self, screen, binder, on_tab, on_refresh, on_cell):
        self.Screen = screen
        self.OnTab = on_tab
        self.OnRefresh = on_refresh
        self.OnCell = on_cell
        get = screen.GetBaseUIControl
        self.Panel = get(TreePath.Summary)
        self.Body = get(TreePath.SummaryBody)
        self.Foot = get(TreePath.Foot)
        self.Empty = get(TreePath.Empty)
        self.Prev = get(TreePath.PagePrev)
        self.Next = get(TreePath.PageNext)
        self.PageLabel = get(TreePath.Page)
        self.RefreshButton = get(TreePath.Refresh)
        self.TabControls = dict((tab, get(TreePath.Tabs + "/tab_" + tab)) for tab in TABS)
        self.Lines = []  # type: list  # SummaryRow
        self.Cells = []  # type: list  # 每一行的格子（TreeCell）：脚本按它找菜单跟着的那一格
        for index in range(TreeConst.SummaryRows):
            row = get(TreePath.SummaryRow.format(index))
            control = get(TreePath.SummaryCell.format(index))
            if row is None or control is None:
                continue
            cell = TreeCell(screen, control, index)
            self.Cells.append(cell)
            self.Lines.append(SummaryRow(row, cell, row.GetChildByPath(TreePath.RowName),
                                         row.GetChildByPath(TreePath.RowInfo)))
            button = cell.Button()
            if button is not None:
                button.AddTouchEventParams({"isSwallow": True, "sum": len(self.Cells) - 1})
                button.SetButtonTouchUpCallback(self.OnCellUp)
        self.Tab = TAB_RAW
        self.Page = 0
        self.Rows = []
        self.Selected = None
        self.FootText = u""
        # 页签按字改宽（SetFullSize：它们在 stack_panel 里，stack_panel 照尺寸规则排，SetSize 管不到 —— 引擎结论 §28）；
        # 汇总栏的宽跟着页签走，最窄 SideMinWidth
        tabs_width = sum(self.__Fit(self.TabControls.get(tab), TAB_TEXTS[tab]) for tab in TABS)
        tabs_width += sum(control_width(get(TreePath.Tabs + "/" + gap)) for gap in TAB_GAPS)
        self.Width = max(TreeConst.SideMinWidth, tabs_width + 2 * PAD)
        if self.Body is not None:
            self.Body.SetFullSize("x", {"absoluteValue": self.Width})
        self.__SetLabel(self.RefreshButton, TreeText.Refresh)
        set_tip(self.Prev, TreeText.TipPrev)
        set_tip(self.Next, TreeText.TipNext)
        for tab in TABS:
            binder.Bind(self.__TabHandler(tab), ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("tab_" + tab))
        binder.Bind(self.OnRefreshClick, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("refresh"))
        binder.Bind(self.OnPrev, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("page_prev"))
        binder.Bind(self.OnNext, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("page_next"))
        if self.Panel is None or self.Body is None:
            logger.error("[MEI/tree] 配方树的汇总控件不全")

    @staticmethod
    def __SetLabel(control, text):
        label = control.GetChildByPath(TreePath.ButtonLabel) if control is not None else None
        if label is not None:
            label.asLabel().SetText(native_str(text))

    def __Fit(self, control, text):  # type: (any, any) -> int
        """ 写上字、按字改宽，返回宽 """
        width = fit_width([text])
        self.__SetLabel(control, text)
        if control is not None:
            control.SetFullSize("x", {"absoluteValue": width})
        return width

    def __TabHandler(self, tab):
        def handler(_args=None):
            self.OnTab(tab)
        return handler

    def OnRefreshClick(self, _args=None):
        self.OnRefresh()

    def OnPrev(self, _args=None):
        if self.Page > 0:
            self.Page -= 1
            self.Render()

    def OnNext(self, _args=None):
        if self.Page + 1 < self.Pages():
            self.Page += 1
            self.Render()

    def OnCellUp(self, args):
        params = args.get("AddTouchEventParams") or {}
        index = params.get("sum")
        if index is not None and 0 <= index < len(self.Cells) and self.Cells[index].Target is not None:
            self.OnCell(self.Cells[index].Target, self.Cells[index])

    # 汇总栏的宽
# ======================================================================================================================
    def SetShown(self, width):  # type: (int) -> None
        """ 汇总栏露出来多宽（0 是收起）：过渡里每帧调 """
        if self.Panel is None:
            return
        width = max(0, int(round(width)))
        self.Panel.SetFullSize("x", {"absoluteValue": width})
        self.Panel.SetVisible(width > 0)

    # 画
# ======================================================================================================================
    def Capacity(self):  # type: () -> int
        """ 一页放几行：汇总栏的高减去页签、统计、底下那一行 """
        try:
            height = int(self.Panel.GetSize()[1])
        except Exception:  # noqa
            height = 0
        if height <= 0:
            return len(self.Lines)
        lines = foot_lines(self.FootText, self.Width - 6) if self.FootText else 0
        return min(len(self.Lines), capacity(height, lines * LINE_H))

    def Pages(self):  # type: () -> int
        per = self.Capacity()
        return max(1, (len(self.Rows) + per - 1) // per)

    def SetRows(self, tab, rows, foot, render_of, name_of):
        # type: (str, list, any, any, any) -> None
        """ 换一页的内容（list_rows 算的），render_of(key) 给物品渲染数据、name_of(key) 给名字；换了页签回到第一页 """
        if tab != self.Tab:
            self.Page = 0
        self.Tab = tab
        self.Rows = [(key, info, badge, render_of(key), name_of(key)) for key, info, badge in rows]
        for name, control in self.TabControls.items():
            if control is None:
                continue
            on = name == tab
            label = control.GetChildByPath(TreePath.ButtonLabel)
            if label is not None:
                label.asLabel().SetTextColor(TreeConst.TabOnColor if on else TreeConst.TabOffColor)
            mark = control.GetChildByPath("/on")
            if mark is not None:
                mark.SetVisible(on)
        self.FootText = native_str(foot or "").decode("utf-8", "replace")
        if self.Foot is not None:
            self.Foot.asLabel().SetText(native_str(self.FootText))
        self.Page = min(self.Page, self.Pages() - 1)
        self.Render()

    def Select(self, key):  # type: (any) -> None
        self.Selected = key
        for cell in self.Cells:
            if cell.Target is not None:
                cell.SetSelected(cell.Target == key)

    def Render(self):
        per = self.Capacity()
        start = self.Page * per
        shown = self.Rows[start:start + per]
        text_w = self.Width - 2 * PAD - NAME_X - 2
        for index, line in enumerate(self.Lines):
            if index >= len(shown):
                line.SetVisible(False)
                continue
            key, info, badge, render, name = shown[index]
            line.Cell.Apply(CellSpec(key, (0, 0), render, badge=badge, selected=key == self.Selected))
            line.SetTexts(fit_text(name, text_w), fit_text(info, text_w))
            line.SetVisible(True)
        if self.Empty is not None:
            if not self.Rows:
                text = TreeText.EmptyLack if self.Tab == TAB_LACK else TreeText.Empty
                self.Empty.asLabel().SetText(native_str(text))
            self.Empty.SetVisible(not self.Rows)
        # 翻页都锚在 JSON 里（左下），这里只切显隐、改字；只有一页时「刷新背包」占满底下那一行
        pages = self.Pages()
        paged = pages > 1
        for control, on in ((self.Prev, self.Page > 0), (self.Next, self.Page + 1 < pages)):
            if control is not None:
                control.SetVisible(paged)
                mask = control.GetChildByPath(TreePath.ButtonMask)  # SetAlpha 只对图片、文字生效：到头了盖上遮罩
                if mask is not None:
                    mask.SetVisible(not on)
        if self.PageLabel is not None:
            self.PageLabel.asLabel().SetText(native_str(TreeText.Page.format(self.Page + 1, pages)))
            self.PageLabel.SetVisible(paged)
        if self.RefreshButton is not None:
            width = self.Width - 2 * PAD - (PAGER_W if paged else 0)
            self.RefreshButton.SetFullSize("x", {"absoluteValue": width})


def set_tip(control, text):  # type: (any, any) -> None
    """ 图标按钮（recipe_tree.json 的 flat_icon_button）的悬停字：悬停、按下两个状态里各一份 """
    if control is None:
        return
    for sub in ("/hover/tip/label", "/pressed/tip/label"):
        label = control.GetChildByPath(sub)
        if label is not None:
            label.asLabel().SetText(native_str(text))
