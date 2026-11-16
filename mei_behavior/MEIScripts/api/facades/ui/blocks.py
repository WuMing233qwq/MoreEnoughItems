# coding=utf-8
# ----------------------------------------------------------------------
#  blocks.py is part of MoreEnoughItems.
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
积木（docs/modding/api.md §6.9）：玩家在 MEI 编辑器里给自制配方页排版用的控件。你的模组可以声明自己的积木 ——
继承 ctx.Types.BlockType，写好 JSON 控件定义（ControlDef）与画法（Paint），在这里登记，它就出现在编辑器的控件池里，
玩家排进页面后配方页、编辑器都照你的画法画。纯新增，不升 API_VERSION，第三方用 getattr(ctx.UI, "Blocks", None) 探测
"""
from MEIScripts.registry.blocks import BlockRegistry


class BlocksFacade(object):
    """ ctx.UI.Blocks：登记都记在这个扩展名下，扩展卸载时 MEI 兜底撤掉（自己在 OnUnload 里撤也行）"""

    __slots__ = ("Owner",)

    def __init__(self, owner=""):
        self.Owner = owner or ""  # type: str

    def Register(self, block_type):
        # type: (any) -> bool
        """ 登记一种积木（BlockType 的实例）。Id 要带命名空间、只用 ASCII，已被占用（包括 MEI 自带的）拒掉 """
        return BlockRegistry.Register(block_type, self.Owner)

    def Unregister(self, block_id):
        # type: (str) -> bool
        """ 撤掉自己登记的一种；别人登记的撤不掉 """
        return BlockRegistry.Unregister(block_id, self.Owner)

    def UnregisterAll(self):
        # type: () -> int
        """ 撤掉这个扩展登记的全部，返回撤了几种 """
        return BlockRegistry.UnregisterOwner(self.Owner)

    def Get(self, block_id):
        # type: (str) -> any
        return BlockRegistry.Get(block_id)

    def List(self):
        # type: () -> list
        """ 全部积木（谁登记的都在），按控件池里的先后 """
        return BlockRegistry.List()
