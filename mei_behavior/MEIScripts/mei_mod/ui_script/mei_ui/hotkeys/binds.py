# coding=utf-8
# ----------------------------------------------------------------------
#  binds.py is part of MoreEnoughItems.
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
现在的键位与修饰键的按下状态（不碰引擎：引擎事件在 manager.py 里接，这里只记账、查表）。

- 键位：每个快捷键登记成一个设置项（KeyBind，key 是 "hotkey_<id>"），玩家改过的存在 MEI 的设置里，没改过的跟默认（table.py）。
  不做缓存：一次按键查一遍二十几项，设置那边本来就有缓存。
- 修饰键：引擎没有「这个键现在按着没有」的接口，只能按裸按键的按下 / 松开自己记；修饰键按住不连发（引擎结论 §42），
  所以**不能拿「多久没收到按下」判断松开** —— 界面压栈 / 出栈时清掉（manager.ResetInput），按着 Alt 收到 Tab 当 Alt 已松开。
- 各界面的滚轮翻页先问 WheelTaken()：按着修饰键、又正好有滚轮类的绑定用这组修饰键，这一下归快捷键，不翻页。
"""
from MEIScripts.mei_mod.state.settings import Action, KeyBind, SettingsManager

from . import keys, table

RESET_KEY = "reset_hotkeys"
""" 按键页最下面的「恢复全部默认按键」"""

_MODS = [0]  # 此刻按着的修饰位


# 设置项
# ======================================================================================================================
def RegisterSettings():  # type: () -> None
    """ 把每个快捷键登记成设置项（client/main_sys 构造期调，不碰引擎；重复调用无副作用）"""
    if SettingsManager.GetSpec(RESET_KEY) is not None:
        return
    for hotkey in table.HOTKEYS:
        SettingsManager.Register(KeyBind(hotkey.SettingKey, hotkey.Label, hotkey.Default, keys.normalize,
                                         wheel=hotkey.Kind == table.WHEEL))
    SettingsManager.Register(Action(RESET_KEY, "options.mei.keys.reset_all", ResetAll))


def ResetAll():  # type: () -> int
    """ 全部快捷键恢复默认（「恢复全部默认」那个按钮不动它们）"""
    return SettingsManager.ResetAll(kind=KeyBind.KIND)


def Combo(hotkey_id):  # type: (str) -> list
    """ 这个快捷键现在的 [修饰位, 主键]；设置项没登记（探针、还没初始化）时给默认 """
    hotkey = table.BY_ID.get(hotkey_id)
    if hotkey is None:
        return list(keys.UNBOUND)
    value = SettingsManager.Get(hotkey.SettingKey)
    return value if value is not None else list(hotkey.Default)


def Save(hotkey_id, combo):  # type: (str, any) -> bool
    """ 录好了：存下这组按键（[0, 0] 是清除绑定）；返回有没有变化 """
    hotkey = table.BY_ID.get(hotkey_id)
    return hotkey is not None and SettingsManager.Set(hotkey.SettingKey, keys.normalize(combo))


def Lookup(mask, code):  # type: (int, int) -> list
    """ 按键类：修饰位与主键正好对上的快捷键（精确匹配：Shift+B 不会也触发 B）"""
    return [hotkey.Id for hotkey in table.HOTKEYS
            if hotkey.Kind == table.PRESS and Combo(hotkey.Id) == [mask, code]]


def WheelIds(mask):  # type: (int) -> list
    """ 滚轮类：修饰位正好对上的快捷键；不按修饰键的一律不算（光滚轮是各界面的翻页）"""
    if not mask:
        return []
    return [hotkey.Id for hotkey in table.HOTKEYS
            if hotkey.Kind == table.WHEEL and Combo(hotkey.Id) == [mask, keys.WHEEL]]


def Conflicts(hotkey_id):  # type: (str) -> list
    """ 和它绑在同一组按键上的别的快捷键（设置页标红用；照样都做 —— NEI 的做法，靠光标下是什么分开）"""
    combo = Combo(hotkey_id)
    if not keys.is_bound(combo):
        return []
    return [hotkey.Id for hotkey in table.HOTKEYS if hotkey.Id != hotkey_id and Combo(hotkey.Id) == combo]


# 修饰键
# ======================================================================================================================
def Mods():  # type: () -> int
    return _MODS[0]


def SetMod(code, down):  # type: (int, bool) -> None
    """ 修饰键（16 / 17 / 18）按下记上、松开清掉 """
    bit = keys.MOD_BITS.get(code)
    if bit:
        _MODS[0] = (_MODS[0] | bit) if down else (_MODS[0] & ~bit)


def ClearMod(bit):  # type: (int) -> None
    _MODS[0] &= ~bit


def ResetMods():  # type: () -> None
    _MODS[0] = 0


def WheelTaken():  # type: () -> bool
    """ 这一下滚轮归快捷键（按着的修饰键正好有滚轮类的绑定）：各界面的滚轮翻页先问它，是就不翻 """
    return bool(WheelIds(_MODS[0]))
