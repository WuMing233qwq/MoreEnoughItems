# coding=utf-8

# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
焦点探针的入口：一个点上是哪个物品渲染器、它显示的什么物品。**查询时才递归找**（search.FocusSearch），
不在后台扫描、不建索引、没有挂 / 摘 —— 分帧扫描、索引、抽查、点名、动态根这套做法性能反而更差，
还有恶性 bug（别人家界面上 GetAllChildrenPath 会让游戏退出，引擎结论 §36）。

它不认识 MEI 的业务：从哪儿找（扫描根）、跳过哪棵子树（MEI 自己的覆盖层）由调用方给，
是不是 MEI 自己的格子、拿它做什么是 UIScriptMain.FocusAt 与调用方的事
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.mei_mod.ui_script.proxy.focus.search import FocusSearch
from MEIScripts.utils.text import error_text


def GetCursorPos():  # type: () -> tuple or None
    """ 光标坐标，按与控件 GetGlobalPosition 同一坐标系用；非 PC 返回 None（官方：仅 PC、仅 PushScreen 时正常）"""
    try:
        comp = clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())
        pos = comp.GetMousePosition()
    except Exception:  # noqa
        return None
    if not pos or len(pos) < 2 or pos[0] is None or pos[1] is None:
        return None
    return float(pos[0]), float(pos[1])


class __FocusManager(object):
    """ 无状态：每次查询现找 """

    @staticmethod
    def Query(screen_node, x, y, roots, exclude=()):  # type: (any, float, float, list, any) -> any
        """
        这一点上最上面那个显示着物品的渲染器（search.FocusHit），没有给 None。给离散事件用（点一下、按一个键），别每帧调
        """
        if screen_node is None or not roots:
            return None
        search = FocusSearch(screen_node, x, y, exclude)
        try:
            hit = search.Run(roots)
        except Exception as e:  # noqa  查询出错不能带走调用方（按键、查找状态的那一帧）
            logger.error("[MEI/focus] 查询失败: " + error_text(e))
            return None
        if search.Exhausted:
            logger.warn("[MEI/focus] 查 ({}, {}) 看了 {} 个控件还没找完，停了".format(x, y, search.Visits))
        return hit

    def QueryCursor(self, screen_node, roots, exclude=()):  # type: (any, list, any) -> tuple
        """ 光标处：(光标坐标或 None, FocusHit 或 None) """
        pos = GetCursorPos()
        if pos is None:
            return None, None
        return pos, self.Query(screen_node, pos[0], pos[1], roots, exclude)


FocusManager = __FocusManager()
