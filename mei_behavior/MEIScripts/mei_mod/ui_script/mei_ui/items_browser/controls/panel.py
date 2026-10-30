# coding=utf-8

# ----------------------------------------------------------------------
#  panel.py is part of MoreEnoughItems.
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

from MEIScripts.common.classes.types import Item
from MEIScripts.constants.texts import ItemText
from MEIScripts.utils.text import native_str
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel
from MEIScripts.mei_mod.ui_script.controls.item.panel import render_args
from MEIScripts.registry import ItemOrganizer


class GroupItemPanel(ItemPanel):
    """
    继承了ItemPanel的对象，用于扩展ItemPanel
    实现了分组物品的渲染 (可变边框)
    """
    def __init__(self, control):
        ItemPanel.__init__(self, control)

        self.IsGroupItem = False
        self.IsGroupHead = False
        self.Group = None

        self.BorderLeftVisible = False
        self.BorderRightVisible = False
        self.BorderTopVisible = False
        self.BorderBottomVisible = False
        self.GroupRendererVisible = False

        self.Renderer1Control = None
        self.Renderer2Control = None

    def SetGroupItemData(self, data_dict):
        """ 初始化ItemPanel 用于维护分组内的物品 """
        self.HideGroupControls()

        self.BackgroundVisible = True
        self.IsGroupItem = True

        self.Group, item, edges = data_dict["GroupItem"]["Group"], data_dict["GroupItem"]["Item"], data_dict["GroupItem"]["Edges"]
        self.SetBorders(edges)

        self.SetItemStack(item.stack(count=1))

    @classmethod
    def from_group_item_data(cls, control, group_data):
        ins = cls(control)
        ins.SetGroupItemData(group_data)
        return ins

    def SetGroupHeadData(self, data_dict):
        """ 初始化ItemPanel 用于维护分组头部的物品 """
        path = self.Control.GetPath()

        self.Renderer1Control = self.MainNode.GetUIControl(path + "/item/group/1", "item_renderer", False)
        self.Renderer2Control = self.MainNode.GetUIControl(path + "/item/group/2", "item_renderer", False)

        self.HideGroupControls()

        self.LabelVisible = True
        self.BackgroundVisible = True
        self.GroupRendererVisible = True
        self.ItemRendererVisible = False
        self.IsGroupHead = True

        self.Group, name, items, length, edges = data_dict["GroupHead"]["Group"], data_dict["GroupHead"]["Name"], data_dict["GroupHead"]["Items"], data_dict["GroupHead"]["Length"], data_dict["GroupHead"]["Edges"]
        item_1 = items[0]
        item_2 = items[1] if len(items) > 1 else item_1

        self.SetBorders(edges)
        self.Renderer1Control.SetUiItem(*render_args(item_1.stack().get_render_data()))
        self.Renderer2Control.SetUiItem(*render_args(item_2.stack().get_render_data()))

        self.SetItemStack(item_1.stack(count=1))
        # 经 native_str 收敛: 模板是 unicode(见 constants/texts.py), name 来自
        # 引擎也可能是 unicode —— 拼出来的 unicode 直接进 hover 绑定的话,
        # 引擎不抛不报只是取不到东西(引擎结论 §2), 表现为分组悬浮文本空白
        self.ItemHoverText = native_str(ItemText.GroupHover.format(name, length))

    def OnPrimaryClick(self, _):
        """
        分组头: 展开/收起; 普通物品: 走基类(查来源).

        注意方法名 —— 派发方(ItemsGrid.PrimaryClickHandler)只调 OnPrimaryClick,
        覆写成别的名字(如 OnClick)就**永远不会被调用**: 点分组头会打开该组
        首个物品的配方, 分组展开/收起成了死功能. 基类也没有 OnClick, 调到会 AttributeError.
        """
        if not self.IsGroupHead:
            return ItemPanel.OnPrimaryClick(self, _)

        self.OnGroupHeadPress(_)
        return None

    @classmethod
    def from_group_head_data(cls, control, group_data):
        ins = cls(control)
        ins.SetGroupHeadData(group_data)
        return ins

    def SetNormalItemData(self, item):  # type: (Item) -> None
        """ 初始化ItemPanel 用于维护正常的物品(初始化前隐藏所有Group物品相关的控件) """
        self.HideGroupControls()
        self.SetItemStack(item.stack(count=1))

    @classmethod
    def from_normal_item(cls, control, item):
        ins = cls(control)
        ins.SetNormalItemData(item)
        return ins

    def SetBorders(self, borders):
        """ 设置分组物品需要显示的边 """
        self.HideBorders()
        for edge in borders:
            if edge == 0:
                self.BorderTopVisible = True
            elif edge == 1:
                self.BorderBottomVisible = True
            elif edge == 2:
                self.BorderLeftVisible = True
            elif edge == 3:
                self.BorderRightVisible = True

    def HideBorders(self):
        """ 隐藏所有边(如果它可见) """
        self.BorderLeftVisible = False
        self.BorderRightVisible = False
        self.BorderTopVisible = False
        self.BorderBottomVisible = False

    def HideGroupControls(self):
        """ 隐藏所有GroupItem相关的控件 """
        self.HideBorders()
        self.LabelVisible = False
        self.GroupRendererVisible = False
        self.BackgroundVisible = False
        self.ItemRendererVisible = True
        # self.LabelControl.SetText("")

    def OnGroupHeadPress(self, args):
        """ 当分组头部物品被按下时的回调 """
        ItemOrganizer.ToggleGroupExpand(self.Group)
        self.MainNode.UpdateAllUI()
        # 对分组进行折叠/展开
        return True
