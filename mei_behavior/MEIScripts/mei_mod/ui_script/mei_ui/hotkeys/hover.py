# coding=utf-8

# ----------------------------------------------------------------------
#  hover.py is part of MoreEnoughItems.
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
按着修饰键悬停（照 NEI；只在 PC 上 —— 触屏没有键盘）。主节点每帧调 Tick（界面代理的 OnTick）：
按住 Ctrl 或 Shift（不带 Alt）悬停在一条配方 / 配方树收藏的某一格上，这一条的全部格子着色（收起的那一格、展开后的产物、原料、工具）。
只问收藏栏自己的 grid（便宜），光标、修饰键都没变就不问；收藏格上的颜色在 JSON（MeiItemsSidebar.bookmark_highlight）。
"""
from mod_log import logger

from MEIScripts.utils.text import error_text

from . import binds, keys


class _State(object):
    """ 上一帧看到的：修饰键、光标 """
    Mods = 0
    Pos = None


def _cursor():  # type: () -> tuple or None
    try:
        from MEIScripts.mei_mod.ui_script.proxy.focus.manager import GetCursorPos
        return GetCursorPos()
    except Exception:  # noqa  取不到光标（非 PC）
        return None


def Tick(main):  # type: (any) -> None
    """ 主节点每帧调；出错只记日志 """
    try:
        _tick(main)
    except Exception as e:  # noqa
        logger.error("[MEI/hotkeys] 修饰键悬停处理失败: {}".format(error_text(e)))


def _tick(main):
    tooltip = getattr(main, "Tooltip", None)
    if tooltip is None or getattr(tooltip, "Host", None) != "desktop":
        return
    mods = binds.Mods()
    holding = mods & (keys.CTRL | keys.SHIFT) and not mods & keys.ALT
    pos = _cursor() if holding else None
    changed = mods != _State.Mods or pos != _State.Pos
    _State.Mods, _State.Pos = mods, pos
    sidebar = getattr(main, "ItemsSidebarIns", None)
    if sidebar is not None and getattr(sidebar, "Inited", False) and changed:
        key = sidebar.HighlightKeyAt(pos[0], pos[1]) if pos else None
        sidebar.SetHighlight(key)
