# coding=utf-8

# ----------------------------------------------------------------------
#  scale.py is part of MoreEnoughItems.
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
两侧UI缩放：物品栏、收藏栏有两档大小 —— 格子 20、上下栏 22（缺省），与格子 18、上下栏 20。

尺寸写在 JSON 的五个变量上（$mei_slot_size / $mei_slot_item_size / $mei_side_bar_size / $mei_side_area_size /
$mei_side_progress_offset），缺省值是 20 那一档；mei_main 里 18 那一档的派生定义只给这五个变量换值。
建好的控件改不了尺寸（变量在建控件时求值），换一档就把那一栏拆了按另一档的定义重建（UIMainNode.EnsureScripts）。
这里的格子与栏高要和 JSON 里的变量一致（探针 probe_ui_slots 对账），脚本按它们排行数（GridLayout）
"""
from MEIScripts.constants.ui import UiPathConst
from MEIScripts.mei_mod.state.settings import GetSideUiScale


class SideScale(object):
    """ 一档：格子边长、上下栏的高，与两栏在两种层级下用的定义（平时那一档 / 悬浮窗那一档）"""
    __slots__ = ("Cell", "Bar", "Defs")

    def __init__(self, cell, bar, right, left, float_right, float_left):
        self.Cell = cell  # type: int
        self.Bar = bar  # type: int
        self.Defs = {
            (UiPathConst.RightWrapper, False): right,
            (UiPathConst.LeftWrapper, False): left,
            (UiPathConst.RightWrapper, True): float_right,
            (UiPathConst.LeftWrapper, True): float_left,
        }

    def WrapperDef(self, path, floating):  # type: (str, bool) -> str
        """ 建这一栏用的定义：path 是 UiPathConst.RightWrapper / LeftWrapper；floating 为真时用悬浮窗那一档层级的 """
        return self.Defs[(path, bool(floating))]


NORMAL = SideScale(20, 22, UiPathConst.SideRightWrapperDef, UiPathConst.SideLeftWrapperDef,
                   UiPathConst.FloatRightWrapperDef, UiPathConst.FloatLeftWrapperDef)
""" 现在的大小：设置「两侧UI缩放」是 1 """

SMALL = SideScale(18, 20, UiPathConst.SideRightWrapperSmallDef, UiPathConst.SideLeftWrapperSmallDef,
                  UiPathConst.FloatRightWrapperSmallDef, UiPathConst.FloatLeftWrapperSmallDef)
""" 小一档：设置是 0 """

SCALES = (NORMAL, SMALL)


def current():  # type: () -> SideScale
    """ 设置里选的那一档 """
    return NORMAL if GetSideUiScale() >= 1 else SMALL


def by_cell(cell):  # type: (any) -> SideScale or None
    """ 按格子边长认是哪一档（读两栏根上的记号 cell_mark 用）；认不出给 None """
    for scale in SCALES:
        if scale.Cell == cell:
            return scale
    return None
