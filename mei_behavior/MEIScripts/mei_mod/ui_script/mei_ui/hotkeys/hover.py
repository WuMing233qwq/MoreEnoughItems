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

- **按住 Ctrl 或 Shift**（不带 Alt）悬停在一条配方 / 配方树收藏的某一格上：这一条的全部格子着色（收起的那一格、展开后的产物、原料、工具）。
  只问收藏栏自己的 grid（便宜），光标、修饰键都没变就不问；收藏格上的颜色在 JSON（MeiItemsSidebar.bookmark_highlight）。
- **只按住 Alt**：tooltip 列出光标下这一格现在能用的快捷键（键位跟着玩家改过的走，没绑的、这一格做不了的不列）；松开 Alt 收起。
  借 MEI tooltip 的「只有标题」那一种 —— 设置里关了「启用高级Tooltip」就不出。光标下是什么问焦点探针：在别人家的界面上要逐层找控件，
  所以只在光标挪了、又隔了 HELP_INTERVAL 才重问。
"""
import time

from mod_log import logger

from MEIScripts.constants.texts import HotkeyText
from MEIScripts.utils.lang import localize
from MEIScripts.utils.text import error_text, to_unicode

from . import binds, keys, table
from .actions import applies

HELP_INTERVAL = 0.1
""" 按着 Alt 挪光标时，隔这么久才重问一次光标下是什么（焦点探针不便宜）"""



class _State(object):
    """ 上一帧看到的：修饰键、光标、Alt 帮助上次问的时刻与光标 """
    Mods = 0
    Pos = None
    HelpAt = 0.0
    HelpPos = None


def label(hotkey):  # type: (any) -> unicode
    """ 快捷键的名字：.lang 里 key.mei.<id>（设置页那一行左边写的也是它；查字走 utils/lang.py，同一份缓存）"""
    return localize(hotkey.Label)


def help_lines(main, target):  # type: (any, any) -> list
    """ 光标下这一格现在能用的快捷键：[u"Ctrl + C  复制物品名", ...]，按设置页的顺序；没绑的、做不了的不列 """
    lines = []
    for hotkey in table.HOTKEYS:
        combo = binds.Combo(hotkey.Id)
        if not keys.is_bound(combo) or not applies(hotkey.Id, main, target):
            continue
        lines.append(HotkeyText.HelpLine.format(to_unicode(keys.format_combo(combo)), label(hotkey)))
    return lines


def help_text(main, target):  # type: (any, any) -> unicode or None
    lines = help_lines(main, target)
    if not lines:
        return None
    return u"\n".join([HotkeyText.HelpTitle] + lines)


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
    pos = _cursor() if mods else None
    changed = mods != _State.Mods or pos != _State.Pos
    _State.Mods, _State.Pos = mods, pos
    sidebar = getattr(main, "ItemsSidebarIns", None)
    if sidebar is not None and getattr(sidebar, "Inited", False) and changed:
        key = sidebar.HighlightKeyAt(pos[0], pos[1]) if holding and pos else None
        sidebar.SetHighlight(key)
    if mods != keys.ALT or not pos:
        tooltip.HideHelp()
        _State.HelpPos = None
        return
    now = time.time()
    if _State.HelpPos is not None and (pos == _State.HelpPos or now - _State.HelpAt < HELP_INTERVAL):
        return
    _State.HelpAt, _State.HelpPos = now, pos
    text = help_text(main, main.FocusAt(pos[0], pos[1]))
    if text:
        tooltip.ShowHelp(text)
    else:
        tooltip.HideHelp()
