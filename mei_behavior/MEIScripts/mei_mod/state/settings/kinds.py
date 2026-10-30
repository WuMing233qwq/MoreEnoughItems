# coding=utf-8
# ----------------------------------------------------------------------
#  kinds.py is part of MoreEnoughItems.
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
import re

from MEIScripts.utils.text import to_native

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
""" key 同时进存盘与绑定名，只收小写蛇形 """


class Setting(object):
    """
    设置项声明的基类，Coerce 把任意输入规约成合法值，不合法抛 TypeError / ValueError
    """
    KIND = ""
    HAS_VALUE = True
    RESET_WITH_ALL = True
    """ 跟着「恢复全部默认」一起恢复；按键绑定不跟（它在自己那一页恢复，SettingsManager.ResetAll(kind=...)）"""

    def __init__(self, key, label, default):
        if not isinstance(key, basestring) or not _KEY_PATTERN.match(key):
            raise ValueError("bad setting key: {!r}".format(key))
        self.Key = to_native(key)
        self.Label = to_native(label)
        """ 标题的本地化键 """
        self.Default = default

    def Coerce(self, value):
        raise NotImplementedError

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, self.Key)


class Toggle(Setting):
    """
    开关
    """
    KIND = "toggle"

    def __init__(self, key, label, default=False):
        Setting.__init__(self, key, label, self.Coerce(default))

    def Coerce(self, value):  # type: (any) -> bool
        if isinstance(value, bool):
            return value
        raise TypeError("toggle wants bool, got {}".format(type(value).__name__))


class Slider(Setting):
    """
    数值滑条，取值 Minimum + n * Step，n 在 0~Steps
    """
    KIND = "slider"

    def __init__(self, key, label, minimum, maximum, step=1, default=None, unit=""):
        for number in (minimum, maximum, step):
            if not _is_number(number):
                raise TypeError("slider bounds must be numbers")
        if step <= 0 or maximum <= minimum:
            raise ValueError("slider needs maximum > minimum and step > 0")
        steps = (maximum - minimum) / float(step)
        if abs(steps - round(steps)) > 1e-6:
            raise ValueError("slider range must be a multiple of step")
        self.Minimum = minimum
        self.Maximum = maximum
        self.Step = step
        self.Steps = int(round(steps))
        self.Unit = to_native(unit)
        self.Integral = all(isinstance(n, (int, long)) for n in (minimum, maximum, step))  # noqa
        Setting.__init__(self, key, label, self.Coerce(minimum if default is None else default))

    def Coerce(self, value):  # type: (any) -> int or float
        if not _is_number(value):
            raise TypeError("slider wants a number, got {}".format(type(value).__name__))
        if value != value or value in (_INF, -_INF):
            # 盘上写着 1e999 / Infinity / NaN（json 读成无穷大、非数）：后面 int(round(...)) 会抛 OverflowError
            raise ValueError("slider wants a finite number, got {!r}".format(value))
        return self.FromPosition(self.ToPosition(value))

    def ToPosition(self, value):  # type: (any) -> float
        """ 值 -> 滑条位置（0~Steps） """
        return (value - self.Minimum) / float(self.Step)

    def FromPosition(self, position):  # type: (float) -> int or float
        """ 滑条位置 -> 值，四舍五入到最近一档并夹在范围内 """
        index = min(max(int(round(position)), 0), self.Steps)
        value = self.Minimum + index * self.Step
        return int(value) if self.Integral else round(value, 6)

    def Format(self, value):  # type: (any) -> str
        text = "%d" % value if self.Integral else "%g" % value
        return text + self.Unit


class Choice(Setting):
    """
    N 选 1，Options 为 [(值, 本地化键)]，值是 str
    """
    KIND = "choice"

    def __init__(self, key, label, options, default=None):
        pairs = [(to_native(value), to_native(text)) for value, text in options]
        values = [value for value, _text in pairs]
        if len(pairs) < 2:
            raise ValueError("choice needs at least two options")
        if len(set(values)) != len(values):
            raise ValueError("choice options must be unique")
        if not all(isinstance(value, basestring) for value in values):
            raise TypeError("choice values must be strings")
        self.Options = pairs
        self.Steps = len(pairs) - 1
        Setting.__init__(self, key, label, self.Coerce(values[0] if default is None else default))

    def Coerce(self, value):  # type: (any) -> str
        value = to_native(value)
        for option, _text in self.Options:
            if option == value:
                return option
        raise ValueError("unknown choice {!r}".format(value))

    def ToPosition(self, value):  # type: (any) -> float
        for index, (option, _text) in enumerate(self.Options):
            if option == value:
                return float(index)
        return 0.0

    def FromPosition(self, position):  # type: (float) -> str
        index = min(max(int(round(position)), 0), self.Steps)
        return self.Options[index][0]

    def OptionLabel(self, value):  # type: (any) -> str
        """ 选项的本地化键；值不认识时给第一项的 """
        for option, text in self.Options:
            if option == value:
                return text
        return self.Options[0][1]


class KeyBind(Setting):
    """
    一组按键（设置「按键绑定」页的一行，docs/architecture/bookmarks.md §12）：值是 [修饰位, 主键] 两个整数，[0, 0] 是不绑定。
    值怎么算合法由快捷键那边给（coerce，mei_ui/hotkeys/keys.normalize）—— 设置框架不知道键码的事；
    Wheel 为真是滚轮类（主键是滚轮）。不跟「恢复全部默认」一起恢复
    """
    KIND = "keybind"
    RESET_WITH_ALL = False

    def __init__(self, key, label, default, coerce, wheel=False):
        if not callable(coerce):
            raise TypeError("keybind needs a coerce function")
        self._coerce = coerce
        self.Wheel = bool(wheel)
        Setting.__init__(self, key, label, self.Coerce(default))

    def Coerce(self, value):  # type: (any) -> list
        return self._coerce(value)


class Action(Setting):
    """
    一次性动作（按钮），没有值
    """
    KIND = "action"
    HAS_VALUE = False

    def __init__(self, key, label, run):
        if not callable(run):
            raise TypeError("action needs a callable")
        self.Run = run
        Setting.__init__(self, key, label, None)

    def Coerce(self, value):
        raise TypeError("action has no value")


_INF = float("inf")


def _is_number(value):  # type: (any) -> bool
    # bool 是 int 的子类，不排除的话 True 会被当成 1
    return isinstance(value, (int, long, float)) and not isinstance(value, bool)  # noqa
