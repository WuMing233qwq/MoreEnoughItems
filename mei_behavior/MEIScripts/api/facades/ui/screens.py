# coding=utf-8

# ----------------------------------------------------------------------
#  screens.py is part of MoreEnoughItems.
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
挂 MEI 的界面：哪些界面开着时旁边出物品栏、收藏栏，各自的代理参数是什么（docs/extension_api.md §5.59）。
原版那 23 个由原版扩展登记（extensions/vanilla/screens.py）。纯新增，不升 API_VERSION，第三方用 getattr 探测
"""
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager

__all__ = ["Register", "Unregister", "IsRegistered"]


def Register(screen_def, params=None):
    # type: (str, dict) -> bool
    """
    让这个界面开着时挂上 MEI（与原版容器界面一样：旁边出物品栏、收藏栏，避让 params 里登记的几块）。
    params 的键见 docs/extension_api.md §5.59（ContentPaths / VisibleControlPath / AllowChangeVisible …），不给就是空的。
    SDK 拒绝（这一局已经挂过同一个代理）时返回 False。登记要在每次进存档装配时做 —— SDK 退出存档时把代理表清了
    """
    return ProxyManager.RegisterCustomUIScreen(screen_def, dict(params or {}))


def Unregister(screen_def):
    # type: (str) -> bool
    """ 撤掉 Register；没登记过返回 False。扩展的 OnUnload 里调 """
    return ProxyManager.UnregisterCustomUIScreen(screen_def)


def IsRegistered(screen_def):
    # type: (str) -> bool
    return ProxyManager.IsCustomUIScreen(screen_def)


class ScreensFacade(object):
    """ ctx.UI.Screens """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
