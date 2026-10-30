# coding=utf-8

# ----------------------------------------------------------------------
#  transfers.py is part of MoreEnoughItems.
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
按界面登记的配方转移（docs/modding/05-screens-and-tools.md §3）：你的界面开着时，配方页上这些类型的配方点 + 交给你的转移处理器 ——
MEI 算好清单（每一格要什么、背包里凑得出多少、挑哪一样），处理器说能不能做（+ 亮不亮、悬停写什么）、点了以后自己去做。
老的写法（第二个参数给 callback(Recipe)）照样认。纯新增，不升 API_VERSION，第三方用 getattr 探测
"""
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.screen_transfers import ScreenTransfers, valid_grid


class TransfersFacade(object):
    """ ctx.UI.Transfers：登记都记在这个扩展名下，扩展卸载时 MEI 兜底撤掉（自己在 OnUnload 里撤也行）"""

    __slots__ = ("Owner",)

    def __init__(self, owner=""):
        self.Owner = owner or ""  # type: str

    def Register(self, screen_def, handler, categories=None, accepts=None):
        # type: (str, any, any, callable) -> str or None
        """
        登记：screen_def 是你的界面名（与 PushScreenEvent 的 screenDef 一样；界面要先能挂上 MEI，ctx.UI.Screens）。
        这个界面开着时，配方页上 categories 里这些类型（类型 Id 的列表，不给是全部）的配方 + 交给 handler：

        - handler 是转移处理器（ctx.Types.TransferHandler 的子类，或者有 Transfer 方法的对象）：
          Check(TransferRequest) -> None / TransferError 说 + 亮不亮、悬停写什么；Transfer(TransferRequest) 去做，
          成了返回 True（MEI 关掉配方页回到你的界面），没成返回 False 或 TransferError（原因写在配方页顶上）。
          类属性 GRID = (列, 行) 让 MEI 按格子摊配方，CONSUMES = False 表示只记配方不拿东西，HINT 是能点时的悬停文字。
        - 老的写法：handler 给一个函数 callback(Recipe)，写成了返回 True —— 当作不拿东西、按配方输入顺序的处理器。

        accepts(Recipe) -> bool 可以再筛一道（不收的灰掉）。同一个界面、同一个类型几个都登记了，后登记的优先。
        返回记号（Unregister 用）；界面名、处理器不对给 None
        """
        return ScreenTransfers.Register(screen_def, handler, categories=categories, accepts=accepts, owner=self.Owner)

    def Unregister(self, token):
        # type: (str) -> bool
        return ScreenTransfers.Unregister(token)

    @staticmethod
    def Request(recipe, grid=None):
        # type: (any, tuple) -> any
        """
        按背包现在有的东西给一条配方算清单（TransferRequest，和 + 交给处理器的同一种：每一格要什么、背包里凑得出多少、挑哪一样）——
        不经过 + 的时候用，比如拿着一样物品点到你的「产物格」、要照它的配方写满格子。grid=(列, 行) 按格子摊，不给按配方输入的顺序
        """
        from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.craftable import CraftableCache
        from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.transfer_request import build_request
        return build_request(recipe, CraftableCache().Supply(), grid=valid_grid(grid),
                             category_id=getattr(recipe, "Type", None) or "")

    def UnregisterAll(self):
        # type: () -> int
        """ 撤掉这个扩展登记的全部，返回撤了几个 """
        return ScreenTransfers.UnregisterOwner(self.Owner)
