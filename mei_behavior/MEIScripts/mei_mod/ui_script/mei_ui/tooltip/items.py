# coding=utf-8

# ----------------------------------------------------------------------
#  items.py is part of MoreEnoughItems.
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
「接受物品」tooltip 里那张物品 grid：一格一个候选（配方接受 tag 下的多个物品时，把它们都摆出来）。
放不下（超过 MAX_COLS × MAX_ROWS 个）时最后一格不画物品、写「+N」—— 没显示出来的还有几个。

格子用自己的模板 mei_common.tooltip_item_panel（和 item_panel 一样由槽位基件组装，多一个居中的「+N」），
那两条绑定只挂在这张 grid 上（TooltipItemsGrid）—— 不往全局的格子模板上加：每个槽位多一条绑定，就是每格每帧多拉一次
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.constants.ui import CollectionConst, PanelProtoConst
from MEIScripts.mei_mod.ui_script.controls.item.grid import ItemsGrid, binding_prefix
from MEIScripts.mei_mod.ui_script.controls.item.panel import ItemPanel
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.layout import grid_shape

ViewBinder = clientApi.GetViewBinderCls()


def more_text(count):  # type: (int) -> str
    """ 最后一格的字：还有几个没显示 """
    return "+{}".format(count)


class TooltipItemPanel(ItemPanel):
    """ 接受物品列表的一格：多两样「+N」用的属性（只有这张 grid 的绑定会来拉）"""

    def __init__(self, control):
        ItemPanel.__init__(self, control)
        self.MoreVisible = False  # type: bool
        self.MoreText = ""  # type: str

    @classmethod
    def from_more(cls, control, count):  # type: (any, int) -> TooltipItemPanel
        """ 最后一格：不画物品（也就没有物品、没有悬停文字），只写「+N」"""
        ins = cls(control)
        ins.SetChildVisible(False)
        ins.MoreVisible = True
        ins.MoreText = more_text(count)
        return ins


class TooltipItemsGrid(ItemsGrid):
    """ 接受物品列表的 grid：通用槽位绑定之外再挂「+N」那两条，绑定名与 tooltip_item_panel 的 JSON 一一对应 """

    def InitBindings(self):
        configs = self.GetDefaultBindingConfigs()
        configs.extend([
            {
                "suffix": ".more.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "MoreVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".more.text",
                "flag": ViewBinder.BF_BindString,
                "attr": "MoreText",
                "default": "",
                "can_pause": True,
            },
        ])
        self.BindConfigs(self.BuildConfigs(configs))


class TooltipItemsView(object):
    """
    显示时才绑定、收起就解绑 —— 槽位的绑定大多是 always 档（binding_cost.md），收起后还绑着就是每帧白拉一遍
    """

    def __init__(self, main_node):
        self.MainNode = main_node
        self.Grid = None  # type: ItemsGrid or None
        self.Stacks = []  # type: list
        self.Shown = 0  # type: int  # 用了几格（放不下时含最后那格「+N」）
        self.More = 0  # type: int  # 最后一格写的 N：没显示出来的个数；放得下是 0

    def Show(self, stacks, grid_path):  # type: (list, str) -> tuple
        """
        在 grid_path（宿主里的内容控件里那张 grid）上摆这些物品，返回 (总数, 实际画出来几个物品 —— 「+N」那格不算)；
        grid 不在返回 (0, 0)。内容控件会复用，ItemsGrid 每次显示都新建（收起时解绑了）
        """
        self.Hide()
        self.Stacks = list(stacks)
        cols, rows, self.Shown = grid_shape(len(self.Stacks))
        self.More = len(self.Stacks) - self.Shown + 1 if len(self.Stacks) > self.Shown else 0
        control = self.MainNode.GetUIControl(grid_path, "grid")
        if control is None:
            return 0, 0
        self.Grid = TooltipItemsGrid(control, PanelProtoConst.Tooltip, CollectionConst.TooltipItems,
                                     binding_prefix(CollectionConst.TooltipItems), self.PanelCallback)
        self.Grid.InitBindings()
        self.Grid.SetGridDimension(cols, rows, False)
        return len(self.Stacks), self.Shown - (1 if self.More else 0)

    def IsReady(self):  # type: () -> bool
        """ 每一格的面板都建出来了（ItemsGrid 写满）：管理器等到这一刻才把 tooltip 摆出来，免得格子一个个冒出来 """
        return self.Grid is not None and self.Grid.CacheSaturated

    def PanelCallback(self, index):  # type: (int) -> ItemPanel
        control = self.Grid.GetControlByIndex(index)
        if self.More and index == self.Shown - 1:
            return TooltipItemPanel.from_more(control, self.More)
        if index < self.Shown:
            return TooltipItemPanel.from_item_stack(control, self.Stacks[index])
        return TooltipItemPanel.from_empty(control)

    def IndexOf(self, panel):  # type: (any) -> int or None
        """ 这一格是第几个候选：只认真的候选格（「+N」那格、空格给 None）—— 触屏菜单里点它就选中这个候选 """
        grid = self.Grid
        if grid is None:
            return None
        last = self.Shown - (1 if self.More else 0)
        for index, candidate in grid.ItemPanels.items():
            if candidate is panel:
                return index if 0 <= index < last else None
        return None

    def Hide(self):
        grid, self.Grid = self.Grid, None
        if grid is not None:
            # 先解绑再清缓存：反过来清缓存会把暂停中的绑定先恢复一遍（BaseItemsGridScript.DestroyScript 同一条）
            grid.UnbindAll()
            grid.ClearItemPanels()
        self.Stacks = []
        self.Shown = 0
        self.More = 0
