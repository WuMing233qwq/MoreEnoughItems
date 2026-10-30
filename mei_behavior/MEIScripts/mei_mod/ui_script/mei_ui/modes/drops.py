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
- 命中：点下去那一点在控件的全局矩形里（藏着的、量不出来的不算 —— 外面哪一层藏着也算藏着：MEI 开着配方页时藏的是原版内容外面那一层）；
  几个都中取面积最小的（套着的取里面那个）。
- 回调抛异常只记一行（同一个目标只记第一次），不影响 MEI。
- 登记时 point=True 的，回调多拿一个参数：点下去那一点的全局坐标 (x, y) —— 一个目标盖住一片格子（比如别人的 3×3 网格）时自己算点中哪一格。
- 登记时给了 accepts(ItemStack) -> bool 的，不收的东西点上去当这个目标不在（套在外面的目标照样能接）。
- 回调的返回值：None / 真是收下了（工具模式放下手里的东西）；False 是不收、一句话是不收并说为什么 —— 手里的东西不放下，
  玩家可以换个地方再点（那句话交给工具模式提示出来）。抛异常同样当不收。
"""
from MEIScripts.mei_mod.ui_script.proxy.focus.search import contains, control_rect
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

ANY_SCREEN = "*"


class DropTarget(object):
    """ 登记的一个放置目标 """

    __slots__ = ("Token", "ScreenDef", "Path", "Alias", "Callback", "Owner", "Warned", "Point", "Accept")

    def __init__(self, token, screen_def, path, alias, callback, owner, point=False, accept=None):
        self.Token = token  # type: str
        self.ScreenDef = screen_def  # type: str or None
        self.Path = path  # type: str
        self.Alias = alias  # type: any
        self.Callback = callback  # type: callable
        self.Owner = owner  # type: str
        self.Warned = False  # type: bool
        self.Point = bool(point)  # type: bool  # 回调要不要第三个参数：点下去那一点 (x, y)
        self.Accept = accept  # type: callable or None  # accepts(ItemStack) -> bool；不给是什么都收

    def Name(self):  # type: () -> any
        """ 回调拿到的名字：别名，没给就是控件路径 """
        return self.Alias if self.Alias is not None else self.Path


def _visible(control):  # type: (any) -> bool
    try:
        return control.GetVisible() is not False
    except Exception:  # noqa  问不出来当看得见，矩形量不出来那一步还会筛
        return True


def _shown(control_of, path):  # type: (callable, str) -> bool
    """
    控件连同外面每一层都显示着。引擎的 GetVisible 只管控件自己：MEI 开配方页、别的模组切页时藏的都是外面那一层，
    只看目标自己的话，点下去会落到底下被藏起来的目标上。从外往里逐层问（只在点下去命中矩形之后问，不是每帧）
    """
    parts = path.strip("/").split("/")
    for depth in range(1, len(parts)):
        try:
            control = control_of("/" + "/".join(parts[:depth]))
        except Exception:  # noqa  取不到的那一层当看得见
            control = None
        if control is not None and not _visible(control):
            return False
    return True


class __DropTargets(object):  # noqa
    """ 放置目标的登记处，构造期不碰引擎 """

    def __init__(self):
        self._targets = []  # type: list  # 按登记的先后
        self._serial = 0  # type: int

    def Register(self, screen_def, path, callback, alias=None, owner="", point=False, accepts=None):
        # type: (str, str, callable, any, str, bool, callable) -> str or None
        """ 登记一个放置目标，返回记号；路径不是字符串、回调不能调、accepts 给了却不能调的不收（给 None）"""
        if not isinstance(path, basestring) or not path or not callable(callback) \
                or (accepts is not None and not callable(accepts)):
            logger.warn("[MEI/drops] 放置目标登记不上：路径 {!r}、回调 {!r}、accepts {!r}".format(path, callback, accepts))
            return None
        self._serial += 1
        token = "drop:{}".format(self._serial)
        screen = native_str(screen_def) if screen_def else None
        self._targets.append(DropTarget(token, screen, native_str(path), alias, callback, owner or "", point, accepts))
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

    def Accepts(self, target, stack):  # type: (DropTarget, any) -> bool
        """ 这个目标收不收这样东西：没给 accepts 是都收；抛了当不收（只记一行）"""
        if target.Accept is None or stack is None:
            return True
        try:
            return bool(target.Accept(stack))
        except Exception as e:  # noqa  别的模组的判断出错不能带走 MEI
            self.__Warn(target, "accepts", e)
            return False

    def Find(self, screen_def, control_of, x, y, stack=None):
        # type: (str, callable, float, float, any) -> DropTarget or None
        """ 这一点上的放置目标：control_of(路径) 给控件（取不到给 None）；给了 stack 的跳过不收它的；几个都中取面积最小的 """
        best, best_area = None, None
        for target in self.Targets(screen_def):
            if not self.Accepts(target, stack):
                continue
            try:
                control = control_of(target.Path)
            except Exception:  # noqa  别人家界面上取控件出错只当这个目标不在
                control = None
            if control is None or not _visible(control):
                continue
            rect = control_rect(control)
            if rect is None or not contains(rect, x, y) or not _shown(control_of, target.Path):
                continue
            area = (rect[2] - rect[0]) * (rect[3] - rect[1])
            if best is None or area < best_area:
                best, best_area = target, area
        return best

    def Deliver(self, target, stack, pos=None):  # type: (DropTarget, any, tuple) -> tuple
        """
        回调它（登记时要了点的位置的多给 pos），返回 (收下了没有, 不收的原因)：回调给 None / 真是收下了；
        False 是不收；一句话是不收、原因就是它。抛了当不收，只记一行（同一个目标只记第一次）
        """
        try:
            if target.Point:
                result = target.Callback(target.Name(), stack, pos)
            else:
                result = target.Callback(target.Name(), stack)
        except Exception as e:  # noqa  别的模组的回调出错不能带走 MEI
            self.__Warn(target, "回调", e)
            return False, ""
        if result is False:
            return False, ""
        if isinstance(result, basestring) and result:
            return False, result
        return True, ""

    @staticmethod
    def __Warn(target, what, error):
        if target.Warned:
            return
        target.Warned = True
        logger.error("[MEI/drops] 放置目标 {} 的{}抛异常: {}".format(target.Name(), what, error_text(error)))

    def Reset(self):
        self._targets = []


DropTargets = __DropTargets()
