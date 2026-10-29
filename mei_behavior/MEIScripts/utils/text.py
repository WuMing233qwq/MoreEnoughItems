# coding=utf-8
# ----------------------------------------------------------------------
#  text.py is part of MoreEnoughItems.
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
py2 文本规约：外部数据进内存的边界上把 unicode 收敛成 str。
理由与事故经过见 CLAUDE.md 引擎结论 §2、engineering.md §7-4b。
"""


def native_str(value):  # type: (any) -> any
    """ unicode 转 utf-8 编码的 str，其余原样返回 """
    # 这里判 unicode 是刻意的，不违反「一律 basestring」——那条防的是漏判，这条要的是拣出
    if isinstance(value, unicode):  # noqa
        return value.encode("utf-8")
    return value


def to_unicode(value):  # type: (any) -> unicode
    """
    拼进 u"" 模板前先解成 unicode：非 ASCII 的字节串直接 .format 进 unicode 模板，py2 按 ASCII 解码就抛。
    （方向与 native_str 相反 —— 那个是递给引擎前收成 str）
    """
    if isinstance(value, unicode):  # noqa  刻意拣出 unicode，同 native_str
        return value
    if isinstance(value, basestring):
        return value.decode("utf-8", "replace")
    return unicode(value)  # noqa


def to_native(value):  # type: (any) -> any
    """ 递归规约容器内的每个 unicode，dict 的键同样转 """
    # 键也要转：键留 unicode 时用 str 照样查得到，但被取出来当值用就又漏出去了（书签正是如此）
    if isinstance(value, unicode):  # noqa
        return value.encode("utf-8")
    if isinstance(value, dict):
        return dict((to_native(k), to_native(v)) for k, v in value.items())
    if isinstance(value, list):
        return [to_native(v) for v in value]
    if isinstance(value, tuple):
        return tuple(to_native(v) for v in value)
    return value


def error_text(error):  # type: (any) -> str
    """ 异常转日志文本，自身绝不抛；except 里拼日志一律用它，见 engineering.md §7-9 """
    # str(e) 遇非 ASCII 的 unicode 消息会抛，而它恰在 except 里被调
    try:
        return str(error)
    except Exception:  # noqa
        try:
            return unicode(error).encode("utf-8")  # noqa
        except Exception:  # noqa
            return repr(error)
