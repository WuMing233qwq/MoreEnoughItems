# coding=utf-8

# ----------------------------------------------------------------------
#  grid.py is part of MoreEnoughItems.
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

from MEIScripts.mei_mod.ui_script.controls.item import ItemsGrid

ViewBinder = clientApi.GetViewBinderCls()

class GroupItemsGrid(ItemsGrid):
    def __init__(self,  control, child_name, collection_name, binding_name_prefix, item_panel_callback):
        ItemsGrid.__init__(self,  control, child_name, collection_name, binding_name_prefix, item_panel_callback)

    def InitBindings(self):
        configs = self.GetDefaultBindingConfigs()
        configs.extend([
            {
                "suffix": ".item.background.border.left.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "BorderLeftVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".item.background.border.right.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "BorderRightVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".item.background.border.top.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "BorderTopVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".item.background.border.bottom.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "BorderBottomVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".item.group.renderer.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "GroupRendererVisible",
                "default": False,
                "can_pause": True,
            }
        ])
        self.BindConfigs(self.BuildConfigs(configs))
