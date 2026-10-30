# coding=utf-8

# ----------------------------------------------------------------------
#  drops.py is part of MoreEnoughItems.
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
工具模式的放置目标（docs/architecture/modes.md，对外是 ctx.UI.Drops，docs/modding/05-screens-and-tools.md §2）：别的模组登记「某个界面里的某个控件」，
玩家在工具模式下拿起 MEI 的物品、再点到这个控件上时，MEI 回调 callback(别名或路径, ItemStack) —— 从 MEI 的物品到别的模组界面的跨模组通讯。
**只给 ItemStack**：配方收藏、配方树收藏给的是它们显示的那样物品。

- 登记：界面（screenDef，与 PushScreenEvent 给的一样；None 或 "*" 是哪个界面都算）+ 控件路径（ScreenNode.GetBaseUIControl 用的那种）
  + 回调，可以给个别名（回调拿到别名，没给就拿到路径）。Register 返回一个记号，Unregister(记号) 撤一个；
  owner 填自己扩展的 ID，OnUnload 里 UnregisterOwner(ID) 一次撤干净。
- 命中：点下去那一点在控件的全局矩形里（藏着的、量不出来的不算）；几个都中取面积最小的（套着的取里面那个）。
- 回调抛异常只记一行（同一个目标只记第一次），不影响 MEI。
- 登记时 point=True 的，回调多拿一个参数：点下去那一点的全局坐标 (x, y) —— 一个目标盖住一片格子（比如别人的 3×3 网格）时自己算点中哪一格。
"""
from MEIScripts.mei_mod.ui_script.proxy.focus.search import contains, control_rect
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

ANY_SCREEN = "*"


class DropTarget(object):
    """ 登记的一个放置目标 """

    __slots__ = ("Token", "ScreenDef", "Path", "Alias", "Callback", "Owner", "Warned", "Point")

    def __init__(self, token, screen_def, path, alias, callback, owner, point=False):
        self.Token = token  # type: str
        self.ScreenDef = screen_def  # type: str or None
        self.Path = path  # type: str
        self.Alias = alias  # type: any
        self.Callback = callback  # type: callable
        self.Owner = owner  # type: str
        self.Warned = False  # type: bool
        self.Point = bool(point)  # type: bool  # 回调要不要第三个参数：点下去那一点 (x, y)

    def Name(self):  # type: () -> any
        """ 回调拿到的名字：别名，没给就是控件路径 """
        return self.Alias if self.Alias is not None else self.Path


def _visible(control):  # type: (any) -> bool
    try:
        return control.GetVisible() is not False
    except Exception:  # noqa  问不出来当看得见，矩形量不出来那一步还会筛
        return True


class __DropTargets(object):  # noqa
    """ 放置目标的登记处，构造期不碰引擎 """

    def __init__(self):
        self._targets = []  # type: list  # 按登记的先后
        self._serial = 0  # type: int

    def Register(self, screen_def, path, callback, alias=None, owner="", point=False):
        # type: (str, str, callable, any, str, bool) -> str or None
        """ 登记一个放置目标，返回记号；路径不是字符串、回调不能调的不收（给 None）"""
        if not isinstance(path, basestring) or not path or not callable(callback):
            logger.warn("[MEI/drops] 放置目标登记不上：路径 {!r}、回调 {!r}".format(path, callback))
            return None
        self._serial += 1
        token = "drop:{}".format(self._serial)
        screen = native_str(screen_def) if screen_def else None
        self._targets.append(DropTarget(token, screen, native_str(path), alias, callback, owner or "", point))
        return token

    def Unregister(self, token):  # type: (str) -> bool
        before = len(self._targets)
        self._targets = [target for target in self._targets if target.Token != token]
        return len(self._targets) != before

    def UnregisterOwner(self, owner):  # type: (str) -> int
        """ 撤掉某个扩展登记的全部；空 owner 不撤（免得一下撤光别人的）"""
        if not owner:
            return 0
        before = len(self._targets)
        self._targets = [target for target in self._targets if target.Owner != owner]
        return before - len(self._targets)

    def Targets(self, screen_def):  # type: (str) -> list
        """ 这个界面上的放置目标（登记成哪个界面都算的也在）"""
        return [target for target in self._targets
                if target.ScreenDef in (None, ANY_SCREEN) or target.ScreenDef == screen_def]

    def Find(self, screen_def, control_of, x, y):  # type: (str, callable, float, float) -> DropTarget or None
        """ 这一点上的放置目标：control_of(路径) 给控件（取不到给 None）；几个都中取面积最小的 """
        best, best_area = None, None
        for target in self.Targets(screen_def):
            try:
                control = control_of(target.Path)
            except Exception:  # noqa  别人家界面上取控件出错只当这个目标不在
                control = None
            if control is None or not _visible(control):
                continue
            rect = control_rect(control)
            if rect is None or not contains(rect, x, y):
                continue
            area = (rect[2] - rect[0]) * (rect[3] - rect[1])
            if best is None or area < best_area:
                best, best_area = target, area
        return best

    def Deliver(self, target, stack, pos=None):  # type: (DropTarget, any, tuple) -> bool
        """ 回调它（登记时要了点的位置的多给 pos）；抛了只记一行（同一个目标只记第一次）"""
        try:
            if target.Point:
                target.Callback(target.Name(), stack, pos)
            else:
                target.Callback(target.Name(), stack)
            return True
        except Exception as e:  # noqa  别的模组的回调出错不能带走 MEI
            if not target.Warned:
                target.Warned = True
                logger.error("[MEI/drops] 放置目标 {} 的回调抛异常: {}".format(target.Name(), error_text(e)))
            return False

    def Reset(self):
        self._targets = []


DropTargets = __DropTargets()
