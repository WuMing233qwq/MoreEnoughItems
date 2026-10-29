# coding=utf-8
# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
快捷键的派发与录键（docs/architecture/bookmarks.md §12）。

用的是 MEI 自己的按键绑定（组合键的体验远好于单键，单键也走这一套）：不注册给引擎的自定义按键，
键位存在 MEI 的设置里（设置「按键绑定」页，binds.py）；只收裸按键 OnKeyPressInGame 与滚轮 MouseWheelClientEvent（client/main_sys 转来）。

- 修饰键自己记（binds.py）；界面压栈 / 出栈时清掉（ResetInput）；按着 Alt 收到 Tab、按下 Win 键：当修饰键已松开（窗口多半要切走了）。
- 主键第一下按下时，此刻按着的修饰键正好等于某一组的修饰位才算（精确匹配）；按住连发的不算（REPEAT_WINDOW）；229、鼠标键不算。
  一组按键绑了几个快捷键就都做（各自看光标下是什么，不在能做的格子上的什么都不做 —— NEI 的做法）。
- 滚轮：按着修饰键滚、修饰键正好对上某个滚轮类的绑定就做（向上 +1、向下 -1）；各界面的滚轮翻页先问 binds.WheelTaken()。
- 录键时（设置页点了某一行的按钮）按下的键、滚轮都交给 capture.py，不当快捷键。
光标下是什么问焦点探针；在搜索框里打字不算（按下后等 DEFER_SECONDS 看搜索框的字变没变）。日志只记出错。每个键做什么在 actions.py。
"""
import time

from mod_log import logger

from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.utils import utilities
from MEIScripts.utils.text import error_text

from . import binds, keys, table
from .actions import ACTIONS
from .capture import Capture

DEFER_SECONDS = 0.05
""" 按下后等这么久再做：这一下要是打进了搜索框，字会变，那就不是快捷键 """

REPEAT_WINDOW = 1.0
"""
按住不放时引擎会连发主键的「按下」（先隔约 0.37 秒、之后约 0.15 秒一次）：同一个键没松开、离上一次按下不到这么久，就是连发，不算。
开关类的键被连发会来回翻；松开事件万一丢了，静默这么久也会恢复
"""

_HELD = {}  # type: dict  # 主键码 -> 最近一次「按下」的时间，松开时清掉
CAPTURE = Capture()


def ResetInput():  # type: () -> None
    """ 界面压栈 / 出栈（client/main_sys）：修饰键与按住的键全部当已松开 —— 按住时切界面、切出窗口，松开多半收不到 """
    binds.ResetMods()
    _HELD.clear()


def OnKeyPress(args):  # type: (dict) -> bool
    """ OnKeyPressInGame 的回调；做了（排上了）至少一个快捷键返回 True """
    try:
        code = int(args.get("key"))
    except (TypeError, ValueError):
        return False
    down = str(args.get("isDown")) == "1"
    if code in keys.MOD_BITS:
        binds.SetMod(code, down)
        if down and CAPTURE.Active():
            CAPTURE.FeedKey(code)
        return False
    if not down:
        _HELD.pop(code, None)
        return False
    if code in keys.WIN_KEYS:
        binds.ResetMods()
        return False
    if code == keys.KEY_TAB and binds.Mods() & keys.ALT:
        binds.ClearMod(keys.ALT)  # Alt+Tab 切走了，Alt 的松开多半收不到
    now = time.time()
    last = _HELD.get(code)
    _HELD[code] = now
    if last is not None and now - last < REPEAT_WINDOW:
        return False  # 按住不放的连发
    if CAPTURE.Active():
        CAPTURE.FeedKey(code)
        return False
    if code == keys.IME or code in keys.MOUSE_CODES:
        return False
    result = False
    for hotkey_id in binds.Lookup(binds.Mods(), code):
        result = _start(hotkey_id, 0) or result
    return result


def OnWheel(args):  # type: (dict) -> bool
    """ MouseWheelClientEvent 的回调（direction 1 向上、0 向下）；这一下归了快捷键返回 True """
    step = 1 if args.get("direction") == 1 else -1
    if CAPTURE.Active():
        CAPTURE.FeedWheel()
        return True
    ids = binds.WheelIds(binds.Mods())
    for hotkey_id in ids:
        _start(hotkey_id, step)
    return bool(ids)


# 录键（设置「按键绑定」页，ui_script/settings/proxy.py）
# ======================================================================================================================
def ToggleCapture(setting_key):  # type: (str) -> bool
    """
    点了某一行的按钮：没在录它就开始录（别的行正在录的放弃）；正在录它就保存（没录成什么都不改）。返回是不是开始录了
    """
    hotkey = table.BY_SETTING.get(setting_key)
    if hotkey is None:
        return False
    if CAPTURE.Id == hotkey.Id:
        combo = CAPTURE.Result()
        CAPTURE.Reset()
        if combo is not None:
            binds.Save(hotkey.Id, combo)
        return False
    CAPTURE.Start(hotkey)
    _HELD.clear()  # 点按钮之前按着的键，松开前再报的「按下」别当成连发吞掉
    return True


def CancelCapture():  # type: () -> None
    """ 放弃录键：关设置页、切界面、点了这一行的恢复默认 """
    CAPTURE.Reset()


def KeyText(setting_key):  # type: (str) -> str
    """ 设置页那一行按钮上的字：正在录给录到的（黄字），否则现在的键位；和别的快捷键撞了是红字（§c）"""
    hotkey = table.BY_SETTING.get(setting_key)
    if hotkey is None:
        return ""
    if CAPTURE.Id == hotkey.Id:
        return CAPTURE.Text()
    text = keys.format_combo(binds.Combo(hotkey.Id))
    return "§c" + text if binds.Conflicts(hotkey.Id) else text


# 派发
# ======================================================================================================================
def _start(hotkey_id, step):  # type: (str, int) -> bool
    try:
        return _handle(hotkey_id, step)
    except Exception as e:  # noqa  快捷键出错只记日志，不能把按键事件带崩
        logger.error("[MEI/hotkeys] 快捷键 {} 处理失败: {}".format(hotkey_id, error_text(e)))
        return False


def _browser(main):
    browser = getattr(main, "ItemsBrowserIns", None)
    return browser if getattr(browser, "Inited", False) else None


def _search_text(browser):  # type: (any) -> any
    """ 物品栏搜索框此刻的字；取不到返回 None """
    control = getattr(browser, "SearchControl", None) if browser else None
    if control is None:
        return None
    try:
        return utilities.GetEditBoxRawText(control)
    except Exception:  # noqa
        return None


def _refresh(main):
    sidebar = getattr(main, "ItemsSidebarIns", None)
    if getattr(sidebar, "Inited", False):
        sidebar.RefreshBookmarks()


def _run(main, hotkey_id, target, step):  # type: (any, str, any, int) -> bool
    try:
        changed = ACTIONS[hotkey_id](main, target, step)
    except Exception as e:  # noqa
        logger.error("[MEI/hotkeys] 快捷键 {} 处理失败: {}".format(hotkey_id, error_text(e)))
        return False
    if changed:
        _refresh(main)
    return bool(changed)


def _handle(hotkey_id, step):  # type: (str, int) -> bool
    main = context.GetMainNode()
    hotkey = table.BY_ID.get(hotkey_id)
    if main is None or hotkey is None or hotkey_id not in ACTIONS:
        return False
    target = None
    if hotkey.Target:
        target = main.FocusAtCursor()
        if target.Pos is None:
            return False
    if hotkey.Kind == table.WHEEL:
        # 滚轮打不进搜索框，不用等
        _run(main, hotkey_id, target, step)
        return True

    browser = _browser(main)
    before = _search_text(browser)
    game = getattr(browser, "GameComp", None)
    if game is None:
        return _run(main, hotkey_id, target, step)

    def deferred():
        # 字变了就是这一下打进了搜索框，不当快捷键
        if _search_text(browser) == before:
            _run(main, hotkey_id, target, step)

    game.AddTimer(DEFER_SECONDS, deferred)
    return True
