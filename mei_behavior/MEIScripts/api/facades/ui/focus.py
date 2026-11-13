# coding=utf-8

# ----------------------------------------------------------------------
#  focus.py is part of MoreEnoughItems.
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
焦点提供器（docs/modding/05-screens-and-tools.md §5，接口参考 docs/modding/api.md §6.8）：你画在 MEI 覆盖层里的物品格
（比如塞进配方页的自己的控件），MEI 的焦点探针是跳过的 —— 登记一个提供器告诉 MEI 到哪儿找，快捷键（来源 / 用途 / 收藏 / 配方树）、
查找状态、Actions.ItemAt / ItemUnderCursor 就都认它们。纯新增，不升 API_VERSION，第三方用 getattr 探测
"""
from MEIScripts.mei_mod.ui_script.proxy.focus.providers import FocusProviders


class FocusFacade(object):
    """ ctx.UI.Focus：登记都记在这个扩展名下，扩展卸载时 MEI 兜底撤掉（自己在 OnUnload 里撤也行）"""

    __slots__ = ("Owner",)

    def __init__(self, owner=""):
        self.Owner = owner or ""  # type: str

    def Register(self, provider):
        # type: (callable) -> str or None
        """
        provider(x, y)：屏幕上这一点（全局坐标）的物品格到哪儿找 —— 给 None 是不归你管；给一个控件路径或几个（从界面最根上算），
        MEI 在它下面按自己的规则找物品渲染器（看得见、矩形含这一点）；给 (物品, 渲染器路径) 是你自己认出来了（物品是 MEI 的 Item 或 (id, aux)）。
        MEI 自己的格子先认，再按登记的先后问提供器，都没有才去别的界面里找。返回记号（Unregister 用）；provider 不能调用给 None
        """
        return FocusProviders.Register(provider, self.Owner)

    def Unregister(self, token):
        # type: (str) -> bool
        return FocusProviders.Unregister(token)

    def UnregisterAll(self):
        # type: () -> int
        """ 撤掉这个扩展登记的全部，返回撤了几个 """
        return FocusProviders.UnregisterOwner(self.Owner)
