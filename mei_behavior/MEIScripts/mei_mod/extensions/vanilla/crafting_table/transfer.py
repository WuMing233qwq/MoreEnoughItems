# coding=utf-8

# ----------------------------------------------------------------------
#  transfer.py is part of MoreEnoughItems.
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
工作台的转移策略：MEI 自己往玩家侧的合成格里放（第三方的机器用 ctx.UI.Transfers 的转移处理器，docs/modding/05-screens-and-tools.md §3）。

槽位表是在游戏里打表得来的（`debug/ingame/ui_slot_scan.py`）：

    背包 2x2 合成栏   28 ~ 31
    工作台 3x3        32 ~ 40，**行优先**（左上角 = 32，Corner() 实测）

两段连续且共用一个编号空间，所以**同一个 ui_index 在两种容器下落到不同槽位** ——
这就是 SlotOf 必须知道"当前开着哪个容器"的原因。
"""
from MEIScripts.api.facades.ui.slots import resolve_input_slot

CRAFT_BASE = 32
""" 工作台 3x3 的首格 """

CRAFT_COLUMNS = 3
""" 工作台容器是 3 列 —— **本配方类型的界面事实**，不该由框架代为默认 """

DISPLAY_COLUMNS = 3
""" 配方页把输入排成 3 列，与 CraftingTableUIScript.GRID_COLUMNS 一致 """

DISPLAY_CELLS = 9
""" 配方页最多显示几个输入格 """

GRID_BASE = 28
""" 背包 2x2 合成栏的首格 """

GRID_COLUMNS = 2

SCREEN_CRAFTING = "crafting.crafting_screen"
""" 工作台屏幕。判据用 screen_def """

SCREEN_INVENTORY = "crafting.inventory_screen"
""" 背包界面，它自带 2x2 合成栏 """

_LAYOUT = {
    SCREEN_CRAFTING: (CRAFT_BASE, CRAFT_COLUMNS, 3),
    SCREEN_INVENTORY: (GRID_BASE, GRID_COLUMNS, 2),
}
""" screen_def -> (首格, 列数, 行数)。**只有本模块认识这张表**，框架不认识 """


class CraftingTransferPolicy(object):
    """
    工作台/背包合成栏的转移策略

    框架只调 CanTransfer / MapRecipe / AllSlots / Capacity（配方页另外读可选的 HINT / SCREEN_HINT），别的都是本类自己的事。
    """

    HINT = u"§7转移材料"
    """ + 能点时的悬停文字（配方页读，可选）"""

    SCREEN_HINT = u"§7不可用的合成站"
    """ 当前界面不是工作台 / 背包时 + 的悬停文字（可选）"""
    """ 槽位归玩家（关掉界面材料退回背包），故走 SetPlayerUIItem 那条路 """

    def CanTransfer(self, ctx):  # type: (any) -> bool
        """ 当前开着的界面能不能转移 """
        return self.__Layout(ctx) is not None

    def SlotOf(self, ctx, ui_index):  # type: (any, int) -> int or None
        """ 把配方界面的格位下标映射到容器槽位；放不下返回 None """
        layout = self.__Layout(ctx)
        if layout is None:
            return None
        base, columns, rows = layout
        row, col = divmod(int(ui_index), CRAFT_COLUMNS)
        # 配方界面永远按 3 列排布, 而 2x2 合成栏只有 2 列 ——
        # 超出的格位不是"放到下一行", 是**这个容器装不下这条配方**
        if row >= rows or col >= columns:
            return None
        return base + row * columns + col

    def MapRecipe(self, ctx, recipe):  # type: (any, any) -> list or None
        """
        把一条配方摊到当前容器的槽位上，返回 [(槽位, Ingredient), ...]；装不下返回 None

        **形状换算走 resolve_input_slot** —— 与配方页渲染用的是同一个函数，
        所以"界面上摆在哪"与"材料放进哪一格"天然一致：
        2x2 的有序配方在 3 列网格里落在 0/1/3/4，不是 0/1/2/3；
        无序配方按 Amount 摊平，一格一个。
        """
        mapped = []
        for ui_index in range(DISPLAY_CELLS):
            ingredient = resolve_input_slot(recipe, ui_index, DISPLAY_COLUMNS)
            if ingredient is None:
                continue
            slot = self.SlotOf(ctx, ui_index)
            if slot is None:
                # 这个容器装不下(比如 3x3 的配方开着背包 2x2 合成栏)
                return None
            mapped.append((slot, ingredient))
        return mapped or None

    def AllSlots(self, ctx):  # type: (any) -> list
        """
        当前容器的**全部输入槽位**，供转移前整片清空

        只清要放的那几格不够: 上一条配方留下的材料会和新的混在一起，
        玩家看到的是一个既不是旧配方也不是新配方的网格。
        """
        layout = self.__Layout(ctx)
        if layout is None:
            return []
        base, columns, rows = layout
        return [base + i for i in range(columns * rows)]

    def Capacity(self, ctx):  # type: (any) -> int
        """ 当前容器有几个输入格。预检拿它先筛掉"根本放不下"的配方 """
        layout = self.__Layout(ctx)
        if layout is None:
            return 0
        _base, columns, rows = layout
        return columns * rows

    @staticmethod
    def __Layout(ctx):  # type: (any) -> tuple or None
        screen = (ctx.Extra or {}).get("screen_def", "")
        # 不记日志: 玩家开个箱子就会走到这里, 而"不支持"是常态不是异常.
        # 界面支不支持, 看 plus 按钮灰不灰就知道了
        return _LAYOUT.get(screen)


POLICY = CraftingTransferPolicy
""" 包门面按这个名字取，与 CATEGORY / SOURCE / UI_SCRIPT 同一个约定 """
