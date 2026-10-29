# coding=utf-8

# ----------------------------------------------------------------------
#  slots.py is part of MoreEnoughItems.
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
槽位渲染契约：所有配方页共用，写新配方类型的界面必用。
"""
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.slots import (
    render_slot, resolve_input_slot, SlotPanelRegistry, DEFAULT_KIND,
)

__all__ = ["render_slot", "resolve_input_slot", "Register", "Unregister", "DEFAULT_KIND"]


def Register(kind, panel_cls, multi_cls=None):
    # type: (str, type, type) -> None
    """
    注册一种条目的槽位面板，之后 `render_slot` 遇到 `Stack.KIND == kind`
    (或显式传 `kind=`) 就走这个面板。

    `multi_cls=None` 表示**该种类不参与多候选轮播**，多候选时退回单候选面板。
    流体就是这样：一格流体永远是一种流体。

    面板类要实现三个 classmethod（与内置的 `ItemPanel` 同名同义）：
    `from_empty(control)` / `from_item_stack(control, stack)` /
    `from_item_stack_list(control, stacks)`（只在注册了 multi_cls 时才会被调）。

    **贴图、配色、单位这些是扩展自己的数据，不进 MEI** ——
    MEI 核心不认识任何具体的流体 id。
    """
    SlotPanelRegistry.Register(kind, panel_cls, multi_cls)


def Unregister(kind):
    # type: (str) -> bool
    """
    撤掉一种条目的槽位面板（OnUnload 里调，和 Register 成对 —— 热重载、重进世界时不撤会留着旧的面板类）。
    物品（DEFAULT_KIND）撤不掉；没注册过返回 False。纯新增，老版本 MEI 用 getattr 探测
    """
    return SlotPanelRegistry.Unregister(kind)


class SlotsFacade(object):
    """ ctx.UI.Slots """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
