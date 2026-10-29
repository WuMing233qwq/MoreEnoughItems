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
配方树底部的材料汇总：四个页签（原料 / 副产物 / 工具 / 还缺），一行格子，左右翻页。
中间物不单列（玩家要看的只有原料和副产物）；副产物是合成多出来的加上配方的其他产出，概率产出的格子右上标小方块。

背包对照只在这里：原料、工具、还缺三页的格子左上写背包里有几个，右下的数字绿色是够、红色是缺；
「还缺」页右下写还缺几个。缺不缺看背包放进库存走的那一遍（modules/summary.shortfall）：背包里的中间材料也扣 ——
有 9 个铁锭就不再缺这 9 个铁锭的粗铁。背包开界面时读一次，「刷新背包」再读（脚本做，这里只画）
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.texts import TreeText
from MEIScripts.constants.ui import TreeConst, TreePath
from MEIScripts.mei_mod.ui_script.mei_ui.menu import layout
from MEIScripts.utils.text import native_str

from .cell import CellSpec, TreeCell, short_count
from .menu import control_width, fit_text, fit_width, icon_size

ViewBinder = clientApi.GetViewBinderCls()

TAB_RAW = "raw"
TAB_BYPRODUCT = "byproduct"
TAB_TOOL = "tool"
TAB_LACK = "lack"
TABS = (TAB_RAW, TAB_BYPRODUCT, TAB_TOOL, TAB_LACK)
TAB_TEXTS = {TAB_RAW: TreeText.TabRaw, TAB_BYPRODUCT: TreeText.TabByproduct, TAB_TOOL: TreeText.TabTool,
             TAB_LACK: TreeText.TabLack}

CELL = 20
SLOTS_Y = 17
""" 格子那一行在汇总里的 y（JSON 里 slots 的 offset）"""
TAB_GAPS = ("gap_0", "gap_1", "gap_2", "gap_3")
""" 页签之间的间隔（JSON 里写死的宽，脚本读回来算页签一共多宽）"""


def page_label_width():  # type: () -> int
    """ 页码那一格多宽：按两位数的页码算（「99/99」照 TreeText.Page 的写法）"""
    return fit_width([TreeText.Page.format(99, 99)], 20)


def pager_width(arrow):  # type: (tuple) -> int
    """ 右边翻页那一块多宽：两个箭头 + 页码 + 两边各空 2 """
    return 2 * int(arrow[0]) + page_label_width() + 4


def tab_rows(tab, summary, have, flags=None, lack=None):  # type: (str, any, dict, dict, dict) -> list
    """
    这一页的格子：[(物品键, 右下的字, 右下的颜色, 左上的字, 右上小方块的颜色)]，纯函数（探针测）。
    lack 是还缺的原料（shortfall 的结果，中间物也扣）：「缺少材料」页就是它，「所需原料」页的红绿也看它（数字照旧不扣背包）；
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
            if count <= 0:
                continue
            owned = int(have.get(key, 0) or 0)
            rows.append((key, short_count(count) or "1", TreeConst.LackColor, short_count(owned) or
                         ("1" if owned == 1 else ""), None))
        return rows
    table = {TAB_RAW: summary.Raw, TAB_BYPRODUCT: summary.Byproducts, TAB_TOOL: summary.Tools}.get(tab, {})
    compare = tab in (TAB_RAW, TAB_TOOL)
    for key, count in summary.Sorted(table):
        if compare:
            owned = int(have.get(key, 0) or 0)
            short = lack.get(key, 0) > 0 if tab == TAB_RAW else owned < count
            color = TreeConst.LackColor if short else TreeConst.HaveColor
            have_text = short_count(owned) or ("1" if owned == 1 else "")
            count_text = short_count(count) or ("1" if tab == TAB_RAW else "")
        else:
            color, have_text, count_text = None, "", short_count(count)
        if tab == TAB_RAW:
            badge = TreeConst.BadgeColors.get(flags.get(key))
        else:
            badge = TreeConst.ChanceColor if tab == TAB_BYPRODUCT and key in summary.Chance else None
        rows.append((key, count_text, color, have_text, badge))
    return rows


class TreeSummary(object):
    """ on_tab(tab)、on_refresh()、on_cell(key, cell)：脚本接 """

    def __init__(self, screen, binder, on_tab, on_refresh, on_cell):
        self.Screen = screen
        self.OnTab = on_tab
        self.OnRefresh = on_refresh
        self.OnCell = on_cell
        get = screen.GetBaseUIControl
        self.Panel = get(TreePath.Summary)
        self.Note = get(TreePath.Note)
        self.NoteLow = get(TreePath.NoteLow)
        self.Foot = get(TreePath.Foot)
        self.Empty = get(TreePath.Empty)
        self.Prev = get(TreePath.PagePrev)
        self.Next = get(TreePath.PageNext)
        self.PageLabel = get(TreePath.Page)
        self.TabControls = dict((tab, get(TreePath.Tabs + "/tab_" + tab)) for tab in TABS)
        self.Cells = []
        for index in range(TreeConst.SummaryCells):
            control = get(TreePath.SummaryCell.format(index))
            if control is None:
                continue
            cell = TreeCell(screen, control, index)
            self.Cells.append(cell)
            button = cell.Button()
            if button is not None:
                button.AddTouchEventParams({"isSwallow": True, "sum": index})
                button.SetButtonTouchUpCallback(self.OnCellUp)
        self.Tab = TAB_RAW
        self.Page = 0
        self.Rows = []
        self.Selected = None
        # 页签、刷新按钮按字改宽（SetFullSize：它们在 stack_panel 里，stack_panel 照尺寸规则排，SetSize 管不到 —— 引擎结论 §28）
        self.TabsWidth = 0
        for tab in TABS:
            control = self.TabControls.get(tab)
            self.TabsWidth += self.__Fit(control, TAB_TEXTS[tab])
            binder.Bind(self.__TabHandler(tab), ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("tab_" + tab))
        self.TabsWidth += self.__Fit(get(TreePath.Tabs + "/refresh"), TreeText.Refresh)
        self.TabsWidth += sum(control_width(get(TreePath.Tabs + "/" + gap)) for gap in TAB_GAPS)
        binder.Bind(self.OnRefreshClick, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("refresh"))
        binder.Bind(self.OnPrev, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("page_prev"))
        binder.Bind(self.OnNext, ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format("page_next"))
        if self.Panel is None:
            logger.error("[MEI/tree] 配方树的汇总控件不全")

    @staticmethod
    def __Fit(control, text):  # type: (any, any) -> int
        """ 写上字、按字改宽，返回宽 """
        width = fit_width([text])
        if control is not None:
            label = control.GetChildByPath(TreePath.ButtonLabel)
            if label is not None:
                label.asLabel().SetText(native_str(text))
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

    # 画
# ======================================================================================================================
    def Capacity(self):  # type: () -> int
        """ 一页摆得下几格：汇总的宽减去右边翻页那一块 """
        try:
            width = int(self.Panel.GetSize()[0])
        except Exception:  # noqa
            width = 0
        pager = pager_width(icon_size(self.Prev))
        return max(1, min(len(self.Cells), (width - pager) // CELL)) if width > 0 else len(self.Cells)

    def Pages(self):  # type: () -> int
        capacity = self.Capacity()
        return max(1, (len(self.Rows) + capacity - 1) // capacity)

    def SetRows(self, tab, rows, note, foot, render_of):
        # type: (str, list, any, any, any) -> None
        """ 换一页的内容（tab_rows 算的），render_of(key) 给物品渲染数据；换了页签回到第一页 """
        if tab != self.Tab:
            self.Page = 0
        self.Tab = tab
        self.Rows = [(key, count, color, have, badge, render_of(key)) for key, count, color, have, badge in rows]
        self.Page = min(self.Page, self.Pages() - 1)
        for name, control in self.TabControls.items():
            label = control.GetChildByPath(TreePath.ButtonLabel) if control is not None else None
            if label is not None:
                label.asLabel().SetTextColor(TreeConst.TabOnColor if name == tab else TreeConst.TabOffColor)
        if self.Foot is not None:
            self.Foot.asLabel().SetText(native_str(foot or ""))
        self.__PlaceNote(note or u"", foot or u"")
        self.Render()

    def __PlaceNote(self, note, foot):
        """
        右边那句说明（上界 / 部分结果；合并计算成了是空的，两个都藏）：页签右边放得下就写在 note（锚右上），放不下写在 note_low
        （底下一行，锚右下，左边是统计），还放不下就截短。两个都锚在 JSON 里，这里只换字、换显隐、两个方向都写 ——
        不用 SetPosition 挪：它是相对父控件左上的坐标，会把锚在右边的控件拽到左边、被页签挡住（引擎结论 §39）
        """
        width = control_width(self.Panel)
        text = native_str(note).decode("utf-8", "replace")
        low = bool(width) and self.TabsWidth + 8 + layout.text_width(text) > width
        if low:
            text = fit_text(text, width - layout.text_width(foot) - 8)
        for control, on in ((self.Note, bool(text) and not low), (self.NoteLow, bool(text) and low)):
            if control is None:
                continue
            control.asLabel().SetText(native_str(text) if on else "")
            control.SetVisible(on)

    def Select(self, key):  # type: (any) -> None
        self.Selected = key
        for cell in self.Cells:
            if cell.Target is not None:
                cell.SetSelected(cell.Target == key)

    def Render(self):
        capacity = self.Capacity()
        start = self.Page * capacity
        shown = self.Rows[start:start + capacity]
        for index, cell in enumerate(self.Cells):
            if index >= len(shown):
                cell.Hide()
                continue
            key, count, color, have, badge, render = shown[index]
            cell.Apply(CellSpec(key, (index * CELL, 0), render, count=count, count_color=color, have=have, badge=badge,
                                selected=key == self.Selected))
        if self.Empty is not None:
            if not self.Rows:
                text = TreeText.EmptyLack if self.Tab == TAB_LACK else TreeText.Empty
                self.Empty.asLabel().SetText(native_str(text))
            self.Empty.SetVisible(not self.Rows)
        pages = self.Pages()
        paged = pages > 1
        arrow_w, arrow_h = icon_size(self.Prev)
        x = capacity * CELL + 2
        arrow_y = SLOTS_Y + (CELL - arrow_h) // 2
        if self.Prev is not None:
            self.Prev.SetPosition((x, arrow_y))
            self.Prev.SetVisible(paged)
            self.Prev.SetAlpha(1.0 if self.Page > 0 else 0.35)
        label_w = page_label_width()
        if self.PageLabel is not None:
            self.PageLabel.SetPosition((x + arrow_w, SLOTS_Y + (CELL - 10) // 2))
            self.PageLabel.SetSize((label_w, 10), False)
            self.PageLabel.asLabel().SetText(native_str(TreeText.Page.format(self.Page + 1, pages)))
            self.PageLabel.SetVisible(paged)
        if self.Next is not None:
            self.Next.SetPosition((x + arrow_w + label_w, arrow_y))
            self.Next.SetVisible(paged)
            self.Next.SetAlpha(1.0 if self.Page + 1 < pages else 0.35)
