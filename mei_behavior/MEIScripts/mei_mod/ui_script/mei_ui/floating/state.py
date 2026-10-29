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
# 悬浮窗的纯计算：该收着还是展开、摆在哪。不碰引擎（docs/architecture/floating.md §2、§5）

MODE_EXPANDED = "expanded"
""" MEI 照常展开，悬浮窗藏着 """

MODE_COLLAPSED = "collapsed"
""" 收成悬浮窗：物品栏、收藏栏藏着 """

MODE_OVERLAY = "overlay"
""" 从悬浮窗点开：物品栏、收藏栏展开，下面垫 30% 的黑底，悬浮窗还在（再点 MEI 或点黑底收起）"""

KIND_SUPPORTED = "supported"
""" 支持 MEI 的界面（登记过挂 MEI 的，ctx.UI.Screens.Register；原版那 23 个在 extensions/vanilla/screens.py，MEI 的代理建起来的）"""

KIND_HUD = "hud"
""" 游戏界面：设置「在游戏界面展示悬浮窗」开着时注入 """

KIND_COMPAT = "compat"
""" 未支持 MEI 的界面：设置「启用悬浮窗强制兼容」开着时注入（兼容性不做保证）"""

KIND_SCREEN = "screen"
""" MEI 自己的界面（PushScreen 开的）：在 HUD 上点悬浮窗的 MEI 时用它，不在 HUD 里展开"""


def too_narrow(room, threshold):  # type: (list, int) -> bool
    """
    自动收起的条件：阈值大于 0，显示着的几侧（物品栏、收藏栏）里任一侧每行还剩的格数小于它 ——
    被原版界面挡住的格子不算，取最少的那一行（common/base.py 的 RowRoom）
    """
    return threshold > 0 and any(count < threshold for count in room)


def initial_mode(kind, forced, threshold, room):  # type: (str, bool, int, list) -> str
    """
    开界面时：MEI 自己的界面一打开就是点开的样子（就是为了看 MEI 才开的）；注入的界面（HUD、强制兼容）与悬浮窗模式一律收着；
    支持的界面按自动收起阈值
    """
    if kind == KIND_SCREEN:
        return MODE_OVERLAY
    if kind != KIND_SUPPORTED or forced:
        return MODE_COLLAPSED
    return MODE_COLLAPSED if too_narrow(room, threshold) else MODE_EXPANDED


def suppresses_avoidance(kind, forced, mode):  # type: (str, bool, str) -> bool
    """
    这会儿 MEI 该不该避让原版界面（自适应）：悬浮窗管事的时候都不避让（悬浮窗启用时还避让，悬浮窗就没有存在的必要）——
    悬浮窗模式开着、从悬浮窗点开着（带黑底）、不是代理支持的界面（注入的、MEI 自己的界面）
    """
    return kind != KIND_SUPPORTED or forced or mode == MODE_OVERLAY


def auto_mode(mode, kind, forced, threshold, room):  # type: (str, str, bool, int, list) -> str
    """
    每行还剩的格数变了（窗口尺寸变了、原版界面变宽变窄）之后该是什么样：只有支持的界面、没开悬浮窗模式时才自动 ——
    排不下就收起（玩家点开的那种不动），排得下就展开、悬浮窗藏起来
    """
    if kind != KIND_SUPPORTED or forced:
        return mode
    if too_narrow(room, threshold):
        return MODE_COLLAPSED if mode == MODE_EXPANDED else mode
    return MODE_EXPANDED


def toggle_mode(mode):  # type: (str) -> str
    """ 点悬浮窗的 MEI：收着就展开（带黑底），展开着就收起 """
    return MODE_OVERLAY if mode == MODE_COLLAPSED else MODE_COLLAPSED


ACTION_OPEN_SCREEN = "open_screen"
""" 点了之后开 MEI 自己的界面（floating/screen.py）"""

ACTION_CLOSE_SCREEN = "close_screen"
""" 点了之后关掉 MEI 自己的界面 """


def mei_click(kind, mode):  # type: (str, str) -> str
    """
    点悬浮窗的 MEI 之后做什么：HUD 上开 MEI 自己的界面（不在游戏界面里展开），在那个界面里是关掉它，
    别的界面收着就展开（带黑底）、展开着就收起 —— 返回动作或新的样子
    """
    if kind == KIND_HUD:
        return ACTION_OPEN_SCREEN
    if kind == KIND_SCREEN:
        return ACTION_CLOSE_SCREEN
    return toggle_mode(mode)


def backdrop_click(kind, mode, quick=True):  # type: (str, str, bool) -> str or None
    """
    点黑底（空白处）之后做什么：设置「启用快速收起悬浮窗」关着时（默认关着，点黑底收起太容易误触）什么都不做；
    开着时 MEI 自己的界面里是关掉它，别的界面点开着就收起，其余不动（None）
    """
    if not quick:
        return None
    if kind == KIND_SCREEN:
        return ACTION_CLOSE_SCREEN
    return MODE_COLLAPSED if mode == MODE_OVERLAY else None


# 位置：悬浮窗是 JSON 原生可拖的 input_panel（contained），引擎记的是「拖拽偏移」——
# 相对父控件左上角（悬浮窗在那儿出生），范围是 0 到「父控件减自身」（引擎结论 §32）。记下来的是比例，换分辨率也在同一处
# ======================================================================================================================
def room_of(parent_size, window_size):  # type: (tuple, tuple) -> tuple
    """ 能拖的范围：父控件减悬浮窗，不够就是 0 """
    return max(0.0, float(parent_size[0]) - window_size[0]), max(0.0, float(parent_size[1]) - window_size[1])


def delta_of(fraction, room):  # type: (tuple, tuple) -> tuple
    """ 比例（0~1）-> 拖拽偏移（像素，取整）"""
    fx, fy = _clamp01(fraction[0]), _clamp01(fraction[1])
    return int(round(room[0] * fx)), int(round(room[1] * fy))


def fraction_of(delta, room):  # type: (tuple, tuple) -> tuple
    """ 拖拽偏移 -> 比例；能拖的范围是 0 的那一轴给 0.5 """
    x = delta[0] / float(room[0]) if room[0] > 0 else 0.5
    y = delta[1] / float(room[1]) if room[1] > 0 else 0.5
    return _clamp01(x), _clamp01(y)


def default_fraction(anchor, room, top_gap):  # type: (tuple, tuple, int) -> tuple
    """ 没拖过时的比例：横向照 anchor，竖向换成离顶边 top_gap 像素（默认屏幕上方正中）"""
    y = min(1.0, top_gap / float(room[1])) if room[1] > 0 else 0.0
    return _clamp01(anchor[0]), y


def _clamp01(value):  # type: (float) -> float
    return min(1.0, max(0.0, float(value)))
