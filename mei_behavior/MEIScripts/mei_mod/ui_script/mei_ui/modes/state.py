# coding=utf-8

# ----------------------------------------------------------------------
#  state.py is part of MoreEnoughItems.
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
三种模式的纯计算（docs/architecture/modes.md）：点模式按钮轮到哪一种、问到权限以后该是哪一种、作弊给一组还是一个。不碰引擎。

权限有三种值：True（服务端说是操作员）、False（说不是）、None（还没问到、超时、出错）——「不知道」不当成「没有」
"""
from MEIScripts.constants.ui import ModeConst


def cycle(cheat_allowed):  # type: (any) -> list
    """ 按钮轮换的顺序：作弊只在权限是 True 时在里面 """
    return [one for one in ModeConst.Order if one != ModeConst.Cheat or cheat_allowed is True]


def next_mode(mode, cheat_allowed):  # type: (str, any) -> str
    """ 点一下模式按钮之后：轮到下一种（没有权限跳过作弊）；现在的不在轮换里（作弊却没了权限）从头来 """
    order = cycle(cheat_allowed)
    if mode not in order:
        return order[0]
    return order[(order.index(mode) + 1) % len(order)]


def checked_mode(mode, cheat_allowed):  # type: (str, any) -> str
    """ 问到权限以后：作弊而没有权限（False）退回普通；还不知道（None）先不动；看不懂的当普通 """
    if mode not in ModeConst.Order:
        return ModeConst.Normal
    if mode == ModeConst.Cheat and cheat_allowed is False:
        return ModeConst.Normal
    return mode


def whole_stack(secondary, touch):  # type: (bool, bool) -> bool
    """ 作弊模式给一组还是一个：触屏点一下给一组；PC 左键一组、右键一个 """
    return touch or not secondary
