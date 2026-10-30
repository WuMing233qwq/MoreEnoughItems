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

from MEIScripts.constants.ui import CollectionConst, ItemsBrowserPath, PanelProtoConst, UiPathConst
from MEIScripts.mei_mod.state import CacheManager, PrefsManager
from MEIScripts.mei_mod.state.settings import IsFindButtonEnabled
from MEIScripts.mei_mod.ui_script.mei_ui.common.base import BaseItemsGridScript
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.controls.grid import GroupItemsGrid
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.controls.panel import GroupItemPanel
from MEIScripts.mei_mod.ui_script.mei_ui.items_browser.modules.page import BuildPage, PageWithGroup
from MEIScripts.registry import ItemManager
from MEIScripts.utils.text import native_str
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.manager import is_touch
from MEIScripts.registry.filters import ItemFilters
from MEIScripts.registry.search import ItemSearchIndex
from MEIScripts.utils import utilities

ViewBinder = clientApi.GetViewBinderCls()

class ItemsBrowserScript(BaseItemsGridScript):
    def __init__(self):
        BaseItemsGridScript.__init__(self)
        self.FindBtnControl = None  # 顶栏最右边的查询按钮（只在触屏、设置开着时有）
        self.FilterBtnControl = None  # 搜索框右边的筛选按钮：开 / 关筛选与排序菜单（main.Filters）
        self.PageIndexLabelControl = None
        self.PageIndexProgressBarControl = None
        self.PageDownBtnControl = None
        self.PageUpBtnControl = None
        self.SearchControl = None
        self.ClearEditBtnControl = None

        self.InputText = ""  # type: str
        self.ItemPanels = {}  # type: dict

    def InitControls(self):
        """ 初始化获取所有控件对象 """
        self.RootControl = self.MainNode.GetMEIRootControl()
        self.ContentControl = None

        self.WrapperControl = self.MainNode.GetUIControl(UiPathConst.RightWrapper)
        self.PageUpBtnControl = self.MainNode.GetUIControl(ItemsBrowserPath.PageUpBtn, "button")
        self.PageDownBtnControl = self.MainNode.GetUIControl(ItemsBrowserPath.PageDownBtn, "button")
        self.SearchControl = self.MainNode.GetUIControl(ItemsBrowserPath.SearchEditBox, "text_edit_box")
        self.ClearEditBtnControl = self.MainNode.GetUIControl(ItemsBrowserPath.SearchClearBtn, "button")
        self.PageIndexLabelControl = self.MainNode.GetUIControl(ItemsBrowserPath.PageIndexLabel, "label")
        self.PageIndexProgressBarControl = self.MainNode.GetUIControl(ItemsBrowserPath.PageIndexBar, "progress_bar")
        self.TopControl = self.MainNode.GetUIControl(ItemsBrowserPath.Top)
        self.BottomControl = self.MainNode.GetUIControl(ItemsBrowserPath.Bottom)

        items_grid_control = self.MainNode.GetUIControl(ItemsBrowserPath.ItemsGrid, "grid")
        self.ItemsGridIns = GroupItemsGrid.from_collection_name(items_grid_control, CollectionConst.ItemsBrowser, PanelProtoConst.Group, self.ItemPanelCallback)
        self.ItemsGridIns.InitBindings()

        self.PageUpBtnControl.AddTouchEventParams({"isSwallow": True})
        self.PageDownBtnControl.AddTouchEventParams({"isSwallow": True})
        self.ClearEditBtnControl.AddTouchEventParams({"isSwallow": True})

        self.PageUpBtnControl.SetButtonTouchDownCallback(self.PageUp)
        self.PageDownBtnControl.SetButtonTouchDownCallback(self.PageDown)
        self.ClearEditBtnControl.SetButtonTouchDownCallback(self.ClearEditBox)
        self.InitFindButton()
        self.InitFilterButton()

    def InitFilterButton(self):
        """ 搜索框右边的筛选按钮：点一下开 / 关筛选与排序菜单（mei_ui/filters/）；图标按选没选染色（菜单那边写）"""
        self.FilterBtnControl = self.MainNode.GetUIControl(ItemsBrowserPath.FilterButton, "button")
        if self.FilterBtnControl is not None:
            self.FilterBtnControl.AddTouchEventParams({"isSwallow": True})
            self.FilterBtnControl.SetButtonTouchUpCallback(self.ToggleFilters)
        filters = getattr(self.MainNode, "Filters", None)
        if filters is not None:
            filters.PaintButton()

    def ToggleFilters(self, _args=None):
        """ 点了筛选按钮：交给这个界面的筛选菜单，下一帧开 / 关 """
        filters = getattr(self.MainNode, "Filters", None)
        if filters is not None:
            filters.Toggle()

    def InitFindButton(self):
        """
        顶栏最右边的查询按钮：只在触屏、设置「在搜索框旁启用查询按钮」开着时显示，两个方向都写（引擎结论 §22）。
        藏的时候宽度也写成 0：stack_panel 收不收拢藏起来的子控件还没实证（引擎结论 §21），宽度 0 就不会空出一格
        """
        shown = IsFindButtonEnabled() and is_touch()
        panel = self.MainNode.GetUIControl(ItemsBrowserPath.FindPanel)
        if panel is not None:
            panel.SetVisible(shown)
            if shown:
                panel.SetFullSize("x", {"followType": "y", "relativeValue": 1.0})
            else:
                panel.SetFullSize("x", {"absoluteValue": 0})
        self.FindBtnControl = self.MainNode.GetUIControl(ItemsBrowserPath.FindButton, "button") if shown else None
        if self.FindBtnControl is not None:
            self.FindBtnControl.AddTouchEventParams({"isSwallow": True})
            self.FindBtnControl.SetButtonTouchUpCallback(self.ToggleFind)

    def ToggleFind(self, _args=None):
        """ 点了查询按钮：交给悬浮窗控制器（悬浮窗上的查询按钮也归它），下一帧进 / 出查找状态 """
        floating = getattr(self.MainNode, "Float", None)
        if floating is not None:
            floating.ToggleFind()

    def UpdateControlsSize(self):
        """ 更新ItemsGrid的尺寸 """
        if self.ItemsGridIns.ItemPanels:
            self.ItemsGridIns.ClearItemPanels()

        layout = self.Layout
        root_pos_x, _ = utilities.GetControlPosInt(self.RootControl)
        root_width, root_height = utilities.GetControlSizeInt(self.RootControl)

        self.AbsoluteRootWidth = root_pos_x + root_width

        layout.Recalculate(root_height)

        current_wrapper_size = utilities.GetControlSizeInt(self.WrapperControl)
        wrapper_size = (layout.WrapperWidth, root_height)
        if current_wrapper_size != wrapper_size:
            self.WrapperControl.SetSize(wrapper_size, True)

        # grid 的高在 JSON 里写的 default（行列数 × 格子），推了行列数尺寸就跟着变（引擎结论 §28）
        self.ItemsGridIns.SetGridDimension(layout.Cols, layout.Rows, False)


    def UpdateIndexPanel(self):
        """ 更新当前页面文本 """
        current = self.ItemsPage.current_page_number
        total = self.ItemsPage.total_page
        progress = float(current)/float(total)
        self.PageIndexProgressBarControl.SetValue(progress)
        self.PageIndexLabelControl.SetText("{}/{}".format(current, total))

        if total <= 1:
            utilities.SetButtonEnable(self.PageUpBtnControl, False)
            utilities.SetButtonEnable(self.PageDownBtnControl, False)
        else:
            utilities.SetButtonEnable(self.PageUpBtnControl, True)
            utilities.SetButtonEnable(self.PageDownBtnControl, True)

    def InitItemsList(self):
        """ 初始化物品标识表 (不含slot映射, 由调用方通过 _refreshSlots 处理) """
        layout = self.Layout
        filtered = self.HasItemView()
        cached = CacheManager.GetItemsPage() if not filtered else None
        if not cached:
            items = self.ApplyItemView(self.ItemSource())
            self.ItemsPage = BuildPage(items, layout.Cols, layout.Rows)  # type: PageWithGroup
            if not filtered:
                CacheManager.CacheItemsPage(self.ItemsPage)
        else:
            self.ItemsPage = cached

    @staticmethod
    def HasItemView():  # type: () -> bool
        """ 选了筛选或排序没有（prefs）；没选时整条路照旧（缓存的分页也照旧用）"""
        return bool(PrefsManager.GetItemFilters() or PrefsManager.GetItemSort())

    @staticmethod
    def ItemSource(text=None):  # type: (any) -> list
        """
        物品栏的候选：有搜索字按搜索、没有就是整张表。选了加法的筛选（「隐藏物品」）时连藏着的一起拿，
        留哪些由 ApplyItemView 按那几项定
        """
        hidden = ItemFilters.HasAdditions(PrefsManager.GetItemFilters())
        if text:
            return ItemSearchIndex.Search(text, include_hidden=hidden)
        return ItemManager.GetBrowsableItems(include_hidden=hidden)

    @staticmethod
    def ApplyItemView(items):  # type: (list) -> list
        """ 物品栏的筛选与排序（registry/filters.py；先搜、再加、再筛、再排）；什么都没选原样返回 """
        filters, sort = PrefsManager.GetItemFilters(), PrefsManager.GetItemSort()
        if not filters and not sort:
            return items
        return ItemFilters.Apply(items, filters, sort, shown=lambda item: not ItemManager.IsHidden(item))

    def RefreshItemView(self):
        """ 筛选 / 排序变了（筛选菜单）：照现在的搜索字重排物品栏、回到第一页；搜索的缓存作废（它是按旧的筛选排的）"""
        if not self.Inited:
            return
        CacheManager.ClearSearchData()
        layout = self.Layout
        if self.InputText:
            self.ItemsPage = BuildPage(self.ApplyItemView(self.ItemSource(self.InputText)), layout.Cols, layout.Rows)
            CacheManager.CacheSearchData(self.InputText, self.ItemsPage)
        else:
            self.InitItemsList()
        self.RefreshSlots()

    def OnMouseWheel(self, args):
        x, _ = utilities.GetMousePosInt()
        layout = self.Layout

        if x > (self.AbsoluteRootWidth - layout.WrapperWidth - 50):
            # 只在屏幕特定区域触发翻页
            if args["direction"] == 1:
                self.PageDown()
            else:
                self.PageUp()

    def OnSearchTick(self):
        self.SearchItem()

    def PageUp(self, _=None):
        """ 向前翻页 """
        self.ItemsPage.PageUp()
        self.UpdateUI(update_size=False)

    def PageDown(self, _=None):
        """ 向后翻页 """
        self.ItemsPage.PageDown()
        self.UpdateUI(update_size=False)

    def ClearEditBox(self, _=None):
        """ 清空编辑框的内容 """
        self.SearchControl.SetEditText("")

    def ItemPanelCallback(self, index):
        """ 提供给Grid的回调 """
        item_panel_control = self.ItemsGridIns.GetControlByIndex(index)

        slot_data = self.SlotMapper.Get(index)

        if self.SlotMapper.IsEmpty(index):
            item_panel_ins = GroupItemPanel.from_empty(item_panel_control)

        else:
            if self.SlotMapper.IsGroupItem(index):
                item_panel_ins = GroupItemPanel.from_group_item_data(item_panel_control, slot_data)
            elif self.SlotMapper.IsGroupHead(index):
                item_panel_ins = GroupItemPanel.from_group_head_data(item_panel_control, slot_data)
            else:
                item_panel_ins = GroupItemPanel.from_normal_item(item_panel_control, slot_data)

        return item_panel_ins

    def DestroyControls(self):
        BaseItemsGridScript.DestroyControls(self)
        self.SearchControl.SetEditText("")

    def SearchItem(self):
        """ 检测搜索物品的回调，当文本出现变化，自动触发搜索并刷新当前的物品 """
        input_text = utilities.GetEditBoxRawText(self.SearchControl)
        layout = self.Layout

        if not input_text and self.InputText:
            self.InputText = ""
            self.InitItemsList()
            self.UpdateUI()
            CacheManager.ClearSearchData()
            return

        elif not input_text:
            cached = CacheManager.GetSearchData()
            if cached:
                self.InputText, self.ItemsPage = cached
                self.SearchControl.SetEditText(native_str(self.InputText))
                self.RefreshSlots()
                self.UpdateIndexPanel()
                return

        else:
            if input_text == self.InputText:
                return
            self.InputText = input_text

            items = self.ApplyItemView(self.ItemSource(self.InputText))

            self.ItemsPage = BuildPage(items, layout.Cols, layout.Rows)
            self.RefreshSlots()
            self.UpdateIndexPanel()

            CacheManager.CacheSearchData(self.InputText, self.ItemsPage)

