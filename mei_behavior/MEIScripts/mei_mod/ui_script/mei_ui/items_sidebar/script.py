# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
#  script.py is part of MoreEnoughItems.
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

from MEIScripts.constants.texts import BookmarkText
from MEIScripts.constants.ui import CollectionConst, ItemsSidebarPath, PanelProtoConst, UiPathConst
from MEIScripts.common.classes.types import Item
from MEIScripts.mei_mod.state import BookmarkManager, BookmarkResolver, CacheManager
from MEIScripts.mei_mod.ui_script.layout import GroupBorderCalculator
from MEIScripts.mei_mod.ui_script.mei_ui.common.base import BaseItemsGridScript
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.controls import (
    BookmarkItemPanel, BookmarkItemsGrid, BroderItemPanel, HistoryItemsGrid,
)
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.modules import BookmarkPager, build_pages, frame_key, highlight_key
from MEIScripts.utils import utilities
from MEIScripts.utils.text import native_str

ViewBinder = clientApi.GetViewBinderCls()


def _merge_stacks(ingredients):  # type: (any) -> list
    """ 每个格位取第一个候选，同一物品的数量加在一起，按首次出现排 """
    order, items, totals = [], {}, {}
    for ingredient in ingredients or ():
        getter = getattr(ingredient, "get_stacks", None)
        stacks = getter() if callable(getter) else getattr(ingredient, "Stacks", None)
        item = getattr(stacks[0], "Item", None) if stacks else None
        key = BookmarkManager.ItemKey(item) if item is not None else ""
        if not key:
            continue
        getter = getattr(ingredient, "get_amount", None)
        amount = getter() if callable(getter) else 1
        if key not in totals:
            order.append(key)
            items[key] = item
            totals[key] = 0
        totals[key] += max(1, amount or 1)
    return [items[key].stack(count=totals[key]) for key in order]


def _tool_stacks(ingredients):  # type: (any) -> list
    """ 工具（不消耗的物品）：每样取第一个候选、同一物品只留一个，数量一律 1 —— 做几份都只要一把 """
    order, items = [], {}
    for ingredient in ingredients or ():
        getter = getattr(ingredient, "get_stacks", None)
        stacks = getter() if callable(getter) else getattr(ingredient, "Stacks", None)
        item = getattr(stacks[0], "Item", None) if stacks else None
        key = BookmarkManager.ItemKey(item) if item is not None else ""
        if key and key not in items:
            order.append(key)
            items[key] = item
    return [items[key].stack(count=1) for key in order]


def ResolveRecipeRow(entry):  # type: (dict) -> tuple or None
    """
    展开的配方那一行：(产物, 原料, 工具) 三列物品堆；找不回返回 None。现查配方。
    工具是配方给收藏栏看的不消耗物品（GetShownCatalysts，熔炉的燃料不在里面），排在行尾、不乘倍数
    """
    recipe = BookmarkResolver.ResolveRecipe(entry)
    if recipe is None:
        return None
    shown = getattr(recipe, "GetShownCatalysts", None)
    return (_merge_stacks(getattr(recipe, "Outputs", None)), _merge_stacks(getattr(recipe, "Inputs", None)),
            _tool_stacks(shown() if callable(shown) else None))


class ItemsSidebarScript(BaseItemsGridScript):

    def __init__(self):
        BaseItemsGridScript.__init__(self)
        self.MainNode = None  # type: any  # 主节点（mei_ui/core/node.py 的 UIMainNode）

        self.BookmarksGridIns = None
        self.HistoryGridIns = None

        self.PageUpBtnControl = None
        self.PageDownBtnControl = None
        self.PageIndexLabelControl = None
        self.PageIndexProgressBarControl = None
        self.TabPrevBtnControl = None
        self.TabNextBtnControl = None
        self.TabLabelControl = None
        self.TabIndexBarControl = None

        self.__BookmarkCells = {}  # type: dict  # 当前页：格子下标 -> Cell
        self.__BookmarkEdges = {}  # type: dict  # 当前页：格子下标 -> 分组外轮廓的边
        self.__BookmarkRevision = None  # 上次排版时收藏的改动计数，变了就重排
        self.__HighlightKey = None  # type: str or None  # 修饰键高亮：高亮的是哪一条收藏（layout.highlight_key）

        self.BookmarksRows = 1
        self.ItemSize = 20
        self.HistoryRows = 3
        self.HistoryHeight = self.HistoryRows * self.ItemSize  # JSON 里最近浏览的高写的 default（行数 × 格子），跟着行数走

        self.HistoryItems = []
        self.__LastHistorySignature = None
        self.__LastHistoryItemsSignature = None
        self.__LastHistoryAdaptiveVersion = -1
        self.__LastHistoryGridShape = None
        self.__HistoryOccludedSlots = set()
        self.__HistoryVisibleSlotMap = {}
        self.__HistoryBorderEdges = {}

    def GetAvoidAnchorMode(self):
        return "left"

    def GetAvoidGapPx(self):
        return 5

    def InitControls(self):
        self.RootControl = self.MainNode.GetMEIRootControl()
        self.ContentControl = None

        self.WrapperControl = self.MainNode.GetUIControl(UiPathConst.LeftWrapper)
        self.TopControl = self.MainNode.GetUIControl(ItemsSidebarPath.Top)
        self.BottomControl = self.MainNode.GetUIControl(ItemsSidebarPath.Bottom)

        self.PageUpBtnControl = self.MainNode.GetUIControl(ItemsSidebarPath.PageUpBtn, "button")
        self.PageDownBtnControl = self.MainNode.GetUIControl(ItemsSidebarPath.PageDownBtn, "button")
        self.PageIndexLabelControl = self.MainNode.GetUIControl(ItemsSidebarPath.PageIndexLabel, "label")
        self.PageIndexProgressBarControl = self.MainNode.GetUIControl(ItemsSidebarPath.PageIndexBar, "progress_bar")
        self.TabPrevBtnControl = self.MainNode.GetUIControl(ItemsSidebarPath.TabPrevBtn, "button")
        self.TabNextBtnControl = self.MainNode.GetUIControl(ItemsSidebarPath.TabNextBtn, "button")
        self.TabLabelControl = self.MainNode.GetUIControl(ItemsSidebarPath.TabLabel, "label")
        self.TabIndexBarControl = self.MainNode.GetUIControl(ItemsSidebarPath.TabIndexBar, "progress_bar")

        bookmarks_grid_control = self.MainNode.GetUIControl(ItemsSidebarPath.BookmarksGrid, "grid")
        history_grid_control = self.MainNode.GetUIControl(ItemsSidebarPath.HistoryGrid, "grid")

        self.BookmarksGridIns = BookmarkItemsGrid.from_collection_name(bookmarks_grid_control, CollectionConst.SidebarBookmarks, PanelProtoConst.Bookmark, self.BookmarkItemPanelCallback)
        self.HistoryGridIns = HistoryItemsGrid.from_collection_name(history_grid_control, CollectionConst.SidebarHistory, PanelProtoConst.Bordered, self.HistoryItemPanelCallback)

        self.BookmarksGridIns.InitBindings()
        self.HistoryGridIns.InitBindings()

        self.ItemsGridIns = self.BookmarksGridIns

        self.PageUpBtnControl.AddTouchEventParams({"isSwallow": True})
        self.PageDownBtnControl.AddTouchEventParams({"isSwallow": True})
        self.PageUpBtnControl.SetButtonTouchDownCallback(self.PageUp)
        self.PageDownBtnControl.SetButtonTouchDownCallback(self.PageDown)
        for button, callback in ((self.TabPrevBtnControl, self.TabPrev), (self.TabNextBtnControl, self.TabNext)):
            if button:
                button.AddTouchEventParams({"isSwallow": True})
                button.SetButtonTouchDownCallback(callback)

    def InitItemsList(self):
        self.ItemsPage = BookmarkPager()
        self.RefreshHistoryGrid(force=True)

    def GetItemGrids(self):
        """ 两个 grid：ItemsGridIns 只是收藏栏，最近浏览也要关界面时解绑、定时自检 """
        return [grid for grid in (self.BookmarksGridIns, self.HistoryGridIns) if grid is not None]

    def GetGridRows(self):
        return self.BookmarksRows

    def BuildSlots(self, occluded):
        """
        收藏按行排版（分组另起一行、竖排清单、折叠、展开的配方），见 modules/layout.py；
        外轮廓按当前页算：每个分组一个框，不在分组里的展开配方各自一个框（frame_key）
        """
        cols = self.Layout.Cols
        pages = build_pages(BookmarkManager.Entries(), BookmarkManager.Groups(), cols, self.BookmarksRows,
                            occluded, resolve=ResolveRecipeRow)
        self.ItemsPage.SetPages(pages, BookmarkManager.PageOfTab())
        BookmarkManager.SetPageOfTab(self.ItemsPage.Index)
        cells = self.ItemsPage.Current()
        members = {}
        for slot, cell in cells.items():
            key = frame_key(cell)
            if key is not None:
                members.setdefault(key, set()).add(slot)
        edges = {}
        for slots in members.values():
            edges.update(GroupBorderCalculator.CalculateFromIndices(slots, cols))
        self.__BookmarkCells = cells
        self.__BookmarkEdges = edges
        self.__BookmarkRevision = BookmarkManager.Revision()

    def RefreshBookmarks(self, force=False):  # type: (bool) -> bool
        """ 收藏有改动（增删改、切页签、换存储位置）才重排，没改动不碰控件 """
        if not force and BookmarkManager.Revision() == self.__BookmarkRevision:
            return False
        self.RefreshSlots(recompute_occlusion=False)
        return True

    def TabPrev(self, _=None):
        BookmarkManager.StepTab(-1)
        self.RefreshBookmarks()

    def TabNext(self, _=None):
        BookmarkManager.StepTab(1)
        self.RefreshBookmarks()

    def UpdateTabLabel(self):
        """ 顶栏的页签号与进度条，样子照底栏的页码；停在「新页签」上时进度条走满 """
        count = BookmarkManager.TabCount()
        if BookmarkManager.IsNewTab():
            text, progress = BookmarkText.TabNew, 1.0
        else:
            current = BookmarkManager.TabIndex() + 1
            text, progress = BookmarkText.TabLabel.format(current, count), float(current) / float(max(1, count))
        if self.TabLabelControl:
            self.TabLabelControl.SetText(native_str(text))
        if self.TabIndexBarControl:
            self.TabIndexBarControl.SetValue(progress)

    def UpdateControlsSize(self):
        if self.BookmarksGridIns and self.BookmarksGridIns.ItemPanels:
            self.BookmarksGridIns.ClearItemPanels()
        if self.HistoryGridIns and self.HistoryGridIns.ItemPanels:
            self.HistoryGridIns.ClearItemPanels()

        layout = self.Layout
        root_pos_x, _ = utilities.GetControlPosInt(self.RootControl)
        root_width, root_height = utilities.GetControlSizeInt(self.RootControl)
        self.AbsoluteRootWidth = root_pos_x + root_width

        layout.Recalculate(root_height)

        bookmarks_height = max(self.ItemSize, layout.GridHeight - self.HistoryHeight)
        self.BookmarksRows = max(1, bookmarks_height // self.ItemSize)

        current_wrapper_size = utilities.GetControlSizeInt(self.WrapperControl)
        wrapper_size = (layout.WrapperWidth, root_height)
        if current_wrapper_size != wrapper_size:
            self.WrapperControl.SetSize(wrapper_size, True)

        # 两个 grid 的高在 JSON 里写的 default（行列数 × 格子），推了行列数尺寸就跟着变（引擎结论 §28）
        self.BookmarksGridIns.SetGridDimension(layout.Cols, self.BookmarksRows, False)
        self.HistoryGridIns.SetGridDimension(layout.Cols, self.HistoryRows, False)

        if self.ItemsPage:
            self.ItemsPage.Rows = self.BookmarksRows
            self.ItemsPage.Cols = layout.Cols
            self.ItemsPage.UpdatePage()

        self.RefreshHistoryGrid(force=True)

    def OnTimerCall(self):
        BaseItemsGridScript.OnTimerCall(self)
        self.RefreshHistoryGrid(force=False)
        self.RefreshBookmarks()

    def UpdateIndexPanel(self):
        if not self.ItemsPage:
            return

        current = self.ItemsPage.current_page_number
        total = self.ItemsPage.total_page
        progress = float(current) / float(total)
        self.PageIndexProgressBarControl.SetValue(progress)
        self.PageIndexLabelControl.SetText("{}/{}".format(current, total))

        enable = total > 1
        utilities.SetButtonEnable(self.PageUpBtnControl, enable)
        utilities.SetButtonEnable(self.PageDownBtnControl, enable)
        self.UpdateTabLabel()

    def BookmarkItemPanelCallback(self, index):
        item_panel_control = self.BookmarksGridIns.GetControlByIndex(index)
        cell = self.__BookmarkCells.get(index)
        if cell is None:
            return BookmarkItemPanel.from_empty(item_panel_control)
        panel = BookmarkItemPanel.from_cell(item_panel_control, cell, self.__BookmarkEdges.get(index, ()))
        panel.HighlightVisible = self.__HighlightKey is not None and highlight_key(cell) == self.__HighlightKey
        return panel

    # 修饰键高亮同一配方（PC；hotkeys/hover.py 每帧问）
# ======================================================================================================================
    def HighlightKeyAt(self, x, y):  # type: (float, float) -> str or None
        """ 这一点上的收藏格属于哪一条配方 / 配方树收藏（只问收藏栏自己的 grid，不走焦点探针）；不是给 None """
        grid = self.BookmarksGridIns
        panel = grid.PanelAt(x, y) if grid is not None else None
        cell = getattr(panel, "Cell", None) if panel is not None else None
        return highlight_key(cell) if cell is not None else None

    def SetHighlight(self, key):  # type: (str or None) -> bool
        """ 高亮这一条收藏的全部格子（None 是都不高亮）；变了才写、才唤醒 grid 的绑定。返回变没变 """
        if key == self.__HighlightKey:
            return False
        self.__HighlightKey = key
        grid = self.BookmarksGridIns
        if grid is None:
            return True
        for panel in grid.ItemPanels.values():
            cell = getattr(panel, "Cell", None)
            panel.HighlightVisible = key is not None and cell is not None and highlight_key(cell) == key
        grid.Wake()
        return True

    def HistoryItemPanelCallback(self, index):
        item_panel_control = self.HistoryGridIns.GetControlByIndex(index)

        if index in self.__HistoryOccludedSlots:
            return BroderItemPanel.from_empty(item_panel_control)

        visible_index = self.__HistoryVisibleSlotMap.get(index)
        if visible_index is None:
            return BroderItemPanel.from_empty(item_panel_control)

        edges = self.__HistoryBorderEdges.get(index, [])

        if isinstance(visible_index, int) and visible_index < len(self.HistoryItems):
            item = self.HistoryItems[visible_index]
            if isinstance(item, Item):
                return BroderItemPanel.from_item_with_borders(item_panel_control, item, edges)
        return BroderItemPanel.from_borders(item_panel_control, edges)

    def OnMouseWheel(self, args):
        x, _ = utilities.GetMousePosInt()
        layout = self.Layout
        root_left = utilities.GetControlPosInt(self.RootControl)[0]

        if x < (root_left + layout.WrapperWidth + 50):
            if args.get("direction") == 1:
                self.PageDown()
            else:
                self.PageUp()

    def PageUp(self, _=None):
        if self.ItemsPage:
            self.ItemsPage.PageUp()
            BookmarkManager.SetPageOfTab(self.ItemsPage.Index)
            self.UpdateUI(update_size=False)

    def PageDown(self, _=None):
        if self.ItemsPage:
            self.ItemsPage.PageDown()
            BookmarkManager.SetPageOfTab(self.ItemsPage.Index)
            self.UpdateUI(update_size=False)

    @staticmethod
    def __BuildHistorySignature(items):
        result = []
        for item in items:
            item_id = getattr(item, "ItemId", None)
            aux_value = getattr(item, "AuxValue", None)
            if item_id is not None:
                result.append((item_id, aux_value))
            else:
                result.append(id(item))
        return tuple(result)

    @staticmethod
    def __BuildVisibleSlotMap(cols, rows, occluded_slots):
        mapping = {}
        visible_index = 0
        total = max(0, cols * rows)
        for slot_index in range(total):
            if slot_index in occluded_slots:
                continue
            mapping[slot_index] = visible_index
            visible_index += 1
        return mapping

    def __GetHistoryOccludedSlots(self):
        if not self.Layout or not self.HistoryGridIns:
            return set()

        return self._ComputeOccludedSlotsForGrid(
            self.HistoryGridIns.Control,
            self.Layout.Cols,
            self.HistoryRows,
            self.ItemSize,
        )

    @staticmethod
    def __BuildHistoryBorderEdges(cols, rows, occluded_slots):
        total = max(0, cols * rows)
        visible_slots = set()
        for slot_index in range(total):
            if slot_index in occluded_slots:
                continue
            visible_slots.add(slot_index)

        return GroupBorderCalculator.CalculateFromIndices(visible_slots, cols)

    def CalcHistoryVisibleCapacity(self):
        if not self.Layout or not self.HistoryGridIns:
            return 0

        base_capacity = max(0, self.Layout.Cols * self.HistoryRows)
        if base_capacity <= 0:
            return 0

        occluded_slots = self.__GetHistoryOccludedSlots()
        visible_capacity = max(0, base_capacity - len(occluded_slots))
        return visible_capacity

    def RefreshHistoryGrid(self, force=False):
        if not self.Layout or not self.HistoryGridIns:
            return False

        history_items = list(CacheManager.GetHistory())
        item_signature = self.__BuildHistorySignature(history_items)
        adaptive_version = self.MainNode.GetAdaptiveGeometryVersion() if self.MainNode else -1
        grid_shape = (self.Layout.Cols, self.HistoryRows)

        if (
            not force
            and self.__LastHistoryItemsSignature == item_signature
            and self.__LastHistoryAdaptiveVersion == adaptive_version
            and self.__LastHistoryGridShape == grid_shape
        ):
            return False

        occluded_slots = self.__GetHistoryOccludedSlots()
        signature = (
            grid_shape,
            tuple(sorted(occluded_slots)),
            item_signature,
        )

        if not force and signature == self.__LastHistorySignature:
            self.__LastHistoryAdaptiveVersion = adaptive_version
            return False

        self.__LastHistorySignature = signature
        self.__LastHistoryItemsSignature = item_signature
        self.__LastHistoryAdaptiveVersion = adaptive_version
        self.__LastHistoryGridShape = grid_shape
        self.__HistoryOccludedSlots = set(occluded_slots)
        self.__HistoryVisibleSlotMap = self.__BuildVisibleSlotMap(self.Layout.Cols, self.HistoryRows,
                                                                  self.__HistoryOccludedSlots)
        self.__HistoryBorderEdges = self.__BuildHistoryBorderEdges(self.Layout.Cols, self.HistoryRows,
                                                                   self.__HistoryOccludedSlots)
        self.HistoryItems = history_items

        if self.HistoryGridIns:
            self.HistoryGridIns.ClearItemPanels()

        return True
