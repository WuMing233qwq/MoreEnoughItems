# coding=utf-8

# ----------------------------------------------------------------------
#  providers.py is part of MoreEnoughItems.
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
焦点提供器（对外 ctx.UI.Focus，docs/modding/api.md §6.8）：别的模组告诉 MEI「这一点上的物品格到哪儿去找」。

焦点探针（manager.FocusManager）找物品格时跳过 MEI 自己的覆盖层（那里的格子由 MEI 的面板认）—— 可第三方画在 MEI 覆盖层里的东西
（比如塞进配方页的自己的控件）就谁都认不到了：快捷键、查找状态、Actions.ItemAt 都对它们没反应。提供器补这一块：
主节点的 FocusAt 先问 MEI 自己的格子，再按登记的先后问提供器，都没有才去原版 / 别的模组的界面里找。

提供器 provider(x, y)（全局坐标）返回：
- None：这一点不归它管；
- 一个控件路径或几个（从界面最根上算）：MEI 在它下面按自己的规则找物品渲染器（看得见、矩形含这一点、名字像渲染器的）；
- (物品, 渲染器路径)：自己认出来了。物品是 MEI 的 Item，或 (id, aux)。
提供器抛异常当没有，同一个只记一次日志。登记记在扩展名下，扩展卸载时装配器兜底撤
"""
from mod_log import logger

from MEIScripts.utils.text import error_text, native_str

from .manager import FocusManager
from .search import FocusHit


def _is_text(value):  # type: (any) -> bool
    return isinstance(value, basestring)


class __FocusProviders(object):  # noqa

    def __init__(self):
        self.__Entries = []  # type: list  # [(记号, 提供器, 扩展 ID)]
        self.__Serial = 0
        self.__Warned = set()

    def Register(self, provider, owner=""):  # type: (callable, str) -> str or None
        if not callable(provider):
            return None
        self.__Serial += 1
        token = "focus{}".format(self.__Serial)
        self.__Entries.append((token, provider, owner or ""))
        return token

    def Unregister(self, token):  # type: (str) -> bool
        before = len(self.__Entries)
        self.__Entries = [entry for entry in self.__Entries if entry[0] != token]
        return len(self.__Entries) != before

    def UnregisterOwner(self, owner):  # type: (str) -> int
        before = len(self.__Entries)
        self.__Entries = [entry for entry in self.__Entries if entry[2] != (owner or "")]
        return before - len(self.__Entries)

    def Count(self):  # type: () -> int
        return len(self.__Entries)

    def Ask(self, screen_node, x, y):  # type: (any, float, float) -> any
        """ 按登记的先后问，第一个认出来的给 search.FocusHit；都没有给 None """
        for token, provider, owner in list(self.__Entries):
            try:
                answer = provider(x, y)
            except Exception as e:  # noqa  别人的提供器坏了不能带走按键、查找状态
                if token not in self.__Warned:
                    self.__Warned.add(token)
                    logger.error("[MEI/focus] {} 的焦点提供器出错（之后不再记）: {}".format(owner or token, error_text(e)))
                continue
            hit = self.__Resolve(screen_node, x, y, answer)
            if hit is not None:
                return hit
        return None

    @staticmethod
    def __Resolve(screen_node, x, y, answer):  # type: (any, float, float, any) -> any
        if answer is None:
            return None
        if _is_text(answer):
            return FocusManager.Query(screen_node, x, y, [native_str(answer)])
        if isinstance(answer, (list, tuple)) and answer and all(_is_text(part) for part in answer):
            return FocusManager.Query(screen_node, x, y, [native_str(part) for part in answer])
        if isinstance(answer, (list, tuple)) and len(answer) == 2 and _is_text(answer[1]):
            item, path = answer
            if isinstance(item, (list, tuple)) and len(item) >= 2 and _is_text(item[0]):
                item_id, aux = native_str(item[0]), int(item[1] or 0)
            else:
                item_id, aux = getattr(item, "ItemId", None), getattr(item, "AuxValue", 0)
            if not item_id:
                return None
            return FocusHit(native_str(path), (x, y, x, y), native_str(item_id), int(aux or 0), False)
        return None


FocusProviders = __FocusProviders()
