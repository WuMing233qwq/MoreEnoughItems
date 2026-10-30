# coding=utf-8

# ----------------------------------------------------------------------
#  params.py is part of MoreEnoughItems.
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
# 代理参数（ctx.UI.Screens.Register 登记的，一个界面一份 dict；原版的在 extensions/vanilla/screens.py）的解析。纯计算，不碰引擎

from MEIScripts.utils.text import native_str

ALLOW_CHANGE_VISIBLE = "AllowChangeVisible"
"""
MEI 能不能改原版控件的显隐。不写就是 True —— 现有的界面都不用写。
写布尔：每个目标都照它；写 dict：按目标分开，键用蛇形命名（VISIBLE_TARGETS），没写的目标是 True
"""

ALLOW_CHANGE_VISIBLE_SNAKE = "allow_change_visible"
""" 同一个参数的蛇形写法，两种都认 """

MAIN_CONTENT_CONTROL = "main_content_control"
""" 配方页开着时藏起来、关了再显出来的那一块（VisibleControlPath，不写就是主内容 MainPath）"""

VISIBLE_TARGETS = (MAIN_CONTENT_CONTROL,)
""" MEI 会改显隐的原版控件 """

VISIBLE_CONTROL_PATH = "VisibleControlPath"
"""
配方页开着时藏起来的那一块（相对原版根面板的路径）。不写就兜底成主内容（MainPath，缺省是 ContentPaths 第一项）；
工作台、背包写的是 /content_stack_panel —— 背包栏连同配方栏一起藏（extensions/vanilla/screens.py）
"""

VISIBLE_CONTROL_PATH_SNAKE = "visible_control_path"
""" 同一个参数的蛇形写法，两种都认 """

CONDITIONS = "Conditions"
"""
ContentPaths 里哪几块要另看条件才避让：{路径: condition(get) -> bool}（core/adaptive/rules.py）。
看得见不够的才写 —— 比如原版配方书上面的页签，配方书藏了它挪到别处、却还看得见（extensions/vanilla/screens.py）
"""


def allow_change_visible(params):  # type: (dict or None) -> dict
    """ 代理参数 -> {目标: 能不能改它的显隐} """
    value = True
    if params:
        value = params.get(ALLOW_CHANGE_VISIBLE, params.get(ALLOW_CHANGE_VISIBLE_SNAKE, True))
    if isinstance(value, dict):
        return dict((target, bool(value.get(target, True))) for target in VISIBLE_TARGETS)
    return dict((target, bool(value)) for target in VISIBLE_TARGETS)


def visible_control_path(params, main_path):  # type: (dict or None, str) -> str
    """ 代理参数 -> 配方页开着时藏起来的那一块；没写（或写的不是字符串、是空的）就是主内容 """
    value = None
    if params:
        value = params.get(VISIBLE_CONTROL_PATH, params.get(VISIBLE_CONTROL_PATH_SNAKE))
    if isinstance(value, basestring) and value:
        return native_str(value)
    return main_path or ""


def under(path, root):  # type: (str, str) -> bool
    """ path 是 root 本身或长在它底下（按路径段比，/a/bc 不算在 /a/b 底下）"""
    if not path or not root:
        return False
    root = root.rstrip("/")
    return path == root or path.startswith(root + "/")


def adaptive_conditions(params):  # type: (dict or None) -> dict
    """ 代理参数的 Conditions：{路径: 条件函数}；不是 dict 给空表，不能调的条件丢掉 """
    raw = params.get(CONDITIONS) if params else None
    if not isinstance(raw, dict):
        return {}
    return dict((native_str(path), condition) for path, condition in raw.items()
                if isinstance(path, basestring) and callable(condition))

