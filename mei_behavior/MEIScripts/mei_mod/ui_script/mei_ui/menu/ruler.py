# coding=utf-8

# ----------------------------------------------------------------------
#  ruler.py is part of MoreEnoughItems.
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
量字宽：界面里一排看不见的 label（mei_common.text_ruler：尺寸 default，跟着字长），写上字、等引擎排过一遍，
GetSize 读回真宽，记进 menu/layout 的量过的表 —— real_width 先查它，菜单的框、按钮就按真宽排：
短字照最窄宽、长字不多出一截（引擎结论 §59：字里有汉字时引擎整段换 unicode 字体，比按默认字体估的窄三四成）。

用法：菜单显示之前（透明着建、或者正亮着先不动的那一两帧）把要用的字交给 Request，Ready 了再排；每帧调一次 Tick。
量过的记在 layout 的表里（几个界面共用），同样的字下次不用再量。
- 按画它的那种字体量：label 里有中文时引擎画用 unicode，排版量宽却照 label 写的字体算半角字（§59）——
  量字的 label 写字之前先换成要量的字体（SetTextFont，网易自己的富文本也这么用）；一段字要什么字体由调用方给
  （多行 label 的一行跟着整段，见 layout.font_for），不给就照它自己有没有中文；
- 写上去和读回来至少隔一帧：同一帧里引擎还没排，读到的是上一段字的宽；
- 一格量完写回空字再让给下一段（空字什么都不画）；
- label 藏着引擎不排版（§60），这排 label 一直亮着、只是全透明；
- 量不到（隔了 MAX_TICKS 帧还是 0、控件不全）就不量了，照估的宽排 —— 菜单不能因为量不到就不出来
"""
import math

from mod_log import logger

from MEIScripts.utils.text import error_text, native_str

from . import layout

SLOTS = 24
""" mei_common.text_ruler 里有几个 label（m0 … m23，探针对账）：同时最多量几段字，多的排队 """

MAX_TICKS = 6
""" 一段字写上去以后最多等几帧（Tick）还量不到就不量了，照估的宽排 """


def to_text(text):  # type: (any) -> unicode
    """ 量的、记的都按 unicode（layout.MEASURED 的键）"""
    if not isinstance(text, unicode):  # noqa: F821  py2 的 unicode
        text = native_str(text).decode("utf-8", "replace")
    return text


def to_entry(item):  # type: (any) -> tuple
    """ 要量的一段：字，或者 (字, 字体)（多行 label 里的一行给整段的字体）→ (字体, 字) """
    if isinstance(item, tuple):
        text, font = item
    else:
        text, font = item, None
    text = to_text(text or "")
    return font or layout.font_for(text), text


def match_font(label, text):  # type: (any, any) -> None
    """
    写了字的 label 按字换字体：有中文换 unicode、没有换回 default（引擎结论 §59：不换的话引擎排版照 default 量半角字，
    画却用 unicode，控件比字宽一截）。LabelUIControl.SetTextFont 文档里没写，网易的富文本在用；没有这个接口就不换
    """
    setter = getattr(label, "SetTextFont", None)
    if not callable(setter):
        return
    try:
        setter(layout.font_for(text))
    except Exception as e:  # noqa
        logger.warn("[MEI/ruler] 换不了 label 的字体: {}".format(error_text(e)))


class TextRuler(object):
    """ 一个界面一个：get_control(路径) 取控件（界面节点的 GetBaseUIControl 或主节点的 GetUIControl），path 是 text_ruler 那个控件 """

    ENABLED = True
    """ 关掉就什么都不量、一律照估的宽排（探针的假控件不会量字，测估宽那一套时关）"""

    def __init__(self, get_control, path):  # type: (callable, str) -> None
        self.Labels = []  # type: list  # (控件, label)
        self.Fonts = []  # type: list  # 每一格现在是什么字体（换过才记，一样的不再碰引擎）
        self.Queue = []  # type: list  # 等空位的 (字体, 字)
        self.Busy = {}  # type: dict  # 第几格 → [(字体, 字), 写上去以后 Tick 过几次]
        self.Failed = set()  # type: set  # 量不到的 (字体, 字)：不再量，照估的宽排
        if not self.ENABLED:
            return
        for index in range(SLOTS):
            control = get_control("{}/m{}".format(path, index))
            if control is None:
                break
            try:
                control.SetAlpha(0.0)  # 一直亮着才排版，全透明才看不见（SetAlpha 对 label 管用，引擎结论 §53）
                self.Labels.append((control, control.asLabel()))
            except Exception as e:  # noqa
                logger.warn("[MEI/ruler] 量字的 label 用不了，照估的宽排: {}".format(error_text(e)))
                self.Labels = []
                return
        self.Fonts = [layout.FONT_DEFAULT] * len(self.Labels)  # JSON 里写的 default
        if not self.Labels:
            logger.warn("[MEI/ruler] 找不到量字的 label（{}），照估的宽排".format(path))

    def Known(self, item):  # type: (any) -> bool
        """ 这段字不用再等：量过了、量不到放弃了，或者这里根本量不了（没有 label）"""
        return self.__Known(to_entry(item))

    def __Known(self, entry):  # type: (tuple) -> bool
        font, text = entry
        return not self.Labels or not text or layout.measured_width(text, font) is not None or entry in self.Failed

    def Ready(self, items):  # type: (list) -> bool
        """ 这几段字都不用再等了 """
        return all(self.Known(item) for item in items)

    def Request(self, items):  # type: (list) -> bool
        """
        这几段字要量（字，或者 (字, 字体)；多行的字按行给）：量过的跳过，没量过的排上队、有空位当场写上去；
        返回是不是都不用等了
        """
        ready = True
        for item in items:
            entry = to_entry(item)
            if self.__Known(entry):
                continue
            ready = False
            if entry not in self.Queue and not any(busy[0] == entry for busy in self.Busy.values()):
                self.Queue.append(entry)
        self.__Assign()
        return ready

    def Tick(self):  # type: () -> None
        """ 每帧：写上去已经隔了一帧的读回宽、记下，那一格写回空字让出来；再把排队的写上去 """
        if not self.Busy and not self.Queue:
            return
        for index, busy in list(self.Busy.items()):
            busy[1] += 1
            if busy[1] < 2:
                continue  # 刚写的：引擎还没排过
            (font, text), width = busy[0], self.__Width(index)
            if width > 0:
                layout.remember_width(text, width, font)
            elif busy[1] < MAX_TICKS:
                continue
            else:
                self.Failed.add(busy[0])
            self.__Write(index, "")
            del self.Busy[index]
        self.__Assign()

    def __Assign(self):
        free = [index for index in range(len(self.Labels)) if index not in self.Busy]
        while free and self.Queue:
            entry = self.Queue.pop(0)
            if self.__Known(entry):
                continue
            index = free.pop(0)
            self.__Font(index, entry[0])
            if self.__Write(index, entry[1]):
                self.Busy[index] = [entry, 0]
            else:
                self.Failed.add(entry)

    def __Font(self, index, font):  # type: (int, str) -> None
        """ 那一格换成要量的字体：换过的不再换；没有 SetTextFont（旧版本）就照 JSON 里的 default 量 """
        if self.Fonts[index] == font:
            return
        setter = getattr(self.Labels[index][1], "SetTextFont", None)
        if not callable(setter):
            return
        try:
            setter(font)
            self.Fonts[index] = font
        except Exception as e:  # noqa
            logger.warn("[MEI/ruler] 量字的 label 换不了字体: {}".format(error_text(e)))

    def __Write(self, index, text):  # type: (int, any) -> bool
        try:
            self.Labels[index][1].SetText(native_str(text))
            return True
        except Exception as e:  # noqa
            logger.warn("[MEI/ruler] 写不上量字的 label: {}".format(error_text(e)))
            return False

    def __Width(self, index):  # type: (int) -> int
        try:
            width = float(self.Labels[index][0].GetSize()[0])
        except Exception:  # noqa  还没排好：当没量到
            return 0
        return int(math.ceil(width)) if width > 0 else 0
