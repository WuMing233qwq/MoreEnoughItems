# coding=utf-8
# ----------------------------------------------------------------------
#  writer.py is part of MoreEnoughItems.
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
直接写一个动态建的控件（不挂绑定，内容由脚本写）：配方树的格子（recipe_tree/controls/cell.py）是同一个做法，这里是不认识具体控件的通用版。

子控件第一次用到才取（sub 是相对这个控件的路径，"" 是它自己）；取不到（刚建出来还没排好）这一次跳过、记下 Missed，调用方下一帧再写一遍。
每样东西记着上次写的值，没变就不碰引擎（一次引擎调用约 0.1 毫秒，引擎结论 §25）。

**改显隐、建控件都不当场刷新界面**：SDK 的 SetVisible、CreateChildControl 缺省每调一次就把整个界面重排一遍（开着 MEI 的工作台两万多个控件），
一行配方几十次、一页就是一秒（引擎结论 §57）。这里一律不刷新、记下这个界面（mark_dirty），这一批写完由调用方 flush 一次（UpdateScreen）。
show_later / full_size 是同一套写法的两个小件，触屏菜单、tooltip、配方树也用（主节点、配方树每帧末尾各 flush 一次）
"""
from mod_log import logger

from MEIScripts.mei_mod.ui_script.controls.item.panel import render_args
from MEIScripts.utils.text import error_text, native_str

_UNSET = object()

ITEM_RETRIES = 10
""" 物品渲染器设不上（刚建出来还没排好）先当没画好、下一帧再设；连着这么多次都不行才当这样东西画不了（minecraft:air 之类），藏起渲染器 """

_PENDING = {}
""" 建了控件、改了显隐，还没刷新的界面（id -> 界面）"""


def mark_dirty(screen):  # type: (any) -> None
    """ 这个界面上建了控件 / 改了显隐（都没刷新）：记下，这一批写完 flush """
    if screen is not None:
        _PENDING[id(screen)] = screen


def forget_screen(screen):  # type: (any) -> None
    """ 界面要关了：记下的不刷了 """
    _PENDING.pop(id(screen), None)


def show_later(control, on, screen):  # type: (any, bool, any) -> None
    """ 改显隐、不当场刷新（forceUpdate 给 False）：记下这个界面，这一批写完由调用方 flush 一次 """
    control.SetVisible(bool(on), False)
    mark_dirty(screen)


def full_size(control, size):  # type: (any, tuple) -> None
    """
    改大小：写尺寸规则（SetFullSize），不用 SetSize —— 后者只改当前的值、不改规则，排版一刷新就回到 JSON 写的大小（引擎结论 §28）。
    JSON 里写 100% 的子控件（按钮的底、遮罩）跟着它变
    """
    control.SetFullSize("x", {"absoluteValue": int(size[0])})
    control.SetFullSize("y", {"absoluteValue": int(size[1])})


def flush():  # type: () -> int
    """ 这一批写完：记下的界面各刷新一次（UpdateScreen，同一帧算好）。给刷新了几个 """
    if not _PENDING:
        return 0
    screens = list(_PENDING.values())
    _PENDING.clear()
    done = 0
    for screen in screens:
        try:
            screen.UpdateScreen(True)
            done += 1
        except Exception as e:  # noqa  界面已经关了
            logger.warn("[MEI/blocks] 刷新界面失败: {}".format(error_text(e)))
    return done

HOVER_KEY = "#hover_text"
""" common.hover_text 读的属性（JSON 里 bindings 写空、property_bag 给它缺省值，脚本 SetPropertyBag 改）"""


class ControlWriter(object):

    __slots__ = ("Screen", "Control", "Path", "Missed", "_Cache", "_Parts")

    def __init__(self, screen, control):
        self.Screen = screen  # type: any  # 能 GetBaseUIControl 的界面节点
        self.Control = control  # type: any
        self.Path = control.GetPath() if control is not None else ""  # type: str
        self.Missed = False  # type: bool  # 有子控件没取到（那一样没写上）
        self._Cache = {}
        self._Parts = {}

    def Prime(self, values):  # type: (dict) -> None
        """ 刚建出来的控件是模板的样子：把这些（名字 -> 值）记成写过，同样的值不再写 """
        self._Cache.update(values)

    def Reset(self):
        """ 忘掉写过的值（控件可能被别人改过、或者换了一个）"""
        self._Cache = {}
        self._Parts = {}

    def Part(self, sub="", cast=None):  # type: (str, str) -> any
        """
        子控件；cast 是 "asLabel" 这类转换名（每转一次引擎要核对一次类型，所以和取到的子控件一起记着）。
        取不到、转不过来（刚建出来还没排好）记 Missed、给 None
        """
        key = (sub, cast)
        part = self._Parts.get(key)
        if part is not None:
            return part
        if sub:
            control = self.Screen.GetBaseUIControl(self.Path + sub) if self.Screen is not None else None
        else:
            control = self.Control
        part = (getattr(control, cast)() if cast else control) if control is not None else None
        if part is None:
            self.Missed = True
            return None
        self._Parts[key] = part
        return part

    def Changed(self, name, value):  # type: (str, any) -> bool
        if self._Cache.get(name, _UNSET) == value:
            return False
        self._Cache[name] = value
        return True

    def Forget(self, name):
        self._Cache.pop(name, None)

    def __Write(self, name, value, sub, cast, write):
        """ 值变了才取控件、写；取不到忘掉这个值（下次再写）"""
        if not self.Changed(name, value):
            return True
        part = self.Part(sub, cast)
        if part is None:
            self.Forget(name)
            return False
        write(part)
        return True

    # 通用的几样
# ======================================================================================================================
    def SetPos(self, pos, sub=""):  # type: (tuple, str) -> None
        """ 位置：相对父控件的左上角（引擎结论 §39：只挪锚在左上的控件）"""
        pos = (int(pos[0]), int(pos[1]))
        self.__Write("pos" + sub, pos, sub, None, lambda c: c.SetPosition(pos))

    def SetSize(self, sub, size):  # type: (str, tuple) -> None
        """ 大小：写尺寸规则（full_size），不是 SetSize —— 后者排版一刷新就回去（引擎结论 §28）"""
        size = (int(size[0]), int(size[1]))
        self.__Write("size" + sub, size, sub, None, lambda c: full_size(c, size))

    def SetVisible(self, sub, on):  # type: (str, bool) -> None
        """ 显隐：不当场刷新（show_later），记下界面等 flush """
        on = bool(on)
        screen = self.Screen
        self.__Write("visible" + sub, on, sub, None, lambda c: show_later(c, on, screen))

    def SetText(self, sub, text, color=None):  # type: (str, any, tuple) -> None
        text = native_str(text if text is not None else "")
        self.__Write("text" + sub, text, sub, "asLabel", lambda c: c.SetText(text))
        if color is not None:
            color = tuple(color)
            self.__Write("tcolor" + sub, color, sub, "asLabel", lambda c: c.SetTextColor(color))

    def SetSprite(self, sub, texture):  # type: (str, str) -> None
        texture = native_str(texture or "")
        self.__Write("sprite" + sub, texture, sub, "asImage", lambda c: c.SetSprite(texture))

    def SetColor(self, sub, color):  # type: (str, tuple) -> None
        """ 贴图的颜色（白图染色）"""
        color = tuple(color)
        self.__Write("color" + sub, color, sub, "asImage", lambda c: c.SetSpriteColor(color))

    def SetAlpha(self, sub, alpha):  # type: (str, float) -> None
        """ 透明度：只对 image 与 label 生效（引擎结论 §53）"""
        alpha = round(float(alpha), 3)
        self.__Write("alpha" + sub, alpha, sub, None, lambda c: c.SetAlpha(alpha))

    def SetClip(self, sub, ratio):  # type: (str, float) -> None
        """
        贴图裁掉多少（0 是整张、1 是全裁掉），方向写在 JSON 的 clip_direction 上；JSON 里**不写 clip_ratio**，
        写了字面值比例就钉死了（引擎结论 §19）
        """
        ratio = round(min(1.0, max(0.0, float(ratio))), 3)
        self.__Write("clip" + sub, ratio, sub, "asImage", lambda c: c.SetSpriteClipRatio(ratio))

    def Replay(self, sub):  # type: (str) -> None
        """
        从头再播一遍 JSON 里的动画（clip 一次 3 秒、不写 next 循环：控件一多 next 循环会成倍加速，配方页的做法同此，
        extensions/vanilla/tools/pages.py）
        """
        part = self.Part(sub, None)
        if part is not None:
            part.StopAnimation()
            part.PlayAnimation()

    def SetHoverText(self, sub, text):  # type: (str, any) -> None
        """ common.hover_text 的字（JSON 里那个控件 bindings 写空、property_bag 给 #hover_text 缺省）"""
        text = native_str(text or "")
        self.__Write("hover" + sub, text, sub, None, lambda c: c.SetPropertyBag({HOVER_KEY: text}))

    def SetItem(self, sub, stack):  # type: (str, any) -> bool
        """
        物品渲染器画这一样（MEI 的 Stack / Item，或者 None 是不画、藏起渲染器）。返回画上了没有。
        设不上的先当没画好（Missed，下一帧再设）—— 刚建的控件还没排好时会这样，记成「画不了」的话要等内容变了才再设；
        连着 ITEM_RETRIES 次都不行才当这样东西画不了（minecraft:air 之类），藏起来
        """
        data = None
        if stack is not None:
            getter = getattr(stack, "get_render_data", None)
            if callable(getter):
                data = render_args(getter())
            elif getattr(stack, "ItemId", None):
                data = render_args((stack.ItemId, getattr(stack, "AuxValue", 0), False, None))
        key = (data[0], data[1], data[2], repr(data[3])) if data else None
        if not self.Changed("item" + sub, key):
            return bool(self._Cache.get("item.shown" + sub, False))
        renderer = self.Part(sub, None)
        if renderer is None:
            self.Forget("item" + sub)
            return False
        shown = False
        if data is not None:
            try:
                shown = bool(renderer.asItemRenderer().SetUiItem(*data))
            except Exception:  # noqa  有的东西渲染不了
                shown = False
            tries = "item.tries" + sub
            if shown:
                self._Cache.pop(tries, None)
            elif self._Cache.get(tries, 0) + 1 < ITEM_RETRIES:
                self._Cache[tries] = self._Cache.get(tries, 0) + 1
                self.Forget("item" + sub)
                self.Missed = True
            else:
                self._Cache.pop(tries, None)
        if self.Changed("item.shown" + sub, shown):
            renderer.SetVisible(shown, False)
            mark_dirty(self.Screen)
        return shown
