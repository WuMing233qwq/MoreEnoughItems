# coding=utf-8

# ----------------------------------------------------------------------
#  actions.py is part of MoreEnoughItems.
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
在 MEI 里做事（docs/modding/api.md「ctx.UI.Actions」）：给一样物品开配方页（来源 / 用途）、开配方树、问屏幕上一点是什么物品、
现在是什么模式、收藏一样物品。作用在「当前挂着 MEI 的那个界面」上；那会儿没有（没挂 MEI 的界面、还没进世界）就做不了，给 False / None。
纯新增，不升 API_VERSION，第三方用 getattr 探测。只在客户端用；**别在绑定回调里调**（会重排格子），挪到下一帧
"""
from MEIScripts.constants.codes import QueryConst

__all__ = [
    "ShowRecipes", "ShowUses", "OpenTree", "ItemAt", "ItemUnderCursor", "Mode", "CheatAllowed",
    "IsBookmarked", "SetBookmarked",
]


def _main():  # type: () -> any
    """ 当前挂着 MEI 的那个界面的主节点（栈顶那份）；没有给 None """
    from MEIScripts.mei_mod.ui_script.mei_ui import context
    return context.GetMainNode()


def ShowRecipes(item, category=None):
    # type: (any, str) -> bool
    """ 开这样物品的配方页，看它怎么做（来源）；category 给了就先翻到那个类型。没挂 MEI、没有配方给 False """
    main = _main()
    if main is None or item is None:
        return False
    return bool(main.ShowRecipeDetails(item, QueryConst.Output, prefer_type=category))


def ShowUses(item, category=None):
    # type: (any, str) -> bool
    """ 开这样物品的配方页，看它能用在哪（用途）；工作站会带上它服务的类型的全部配方 """
    main = _main()
    if main is None or item is None:
        return False
    return bool(main.ShowRecipeDetails(item, QueryConst.Input, prefer_type=category))


def OpenTree(item, count=1):
    # type: (any, int) -> bool
    """ 开这样物品的配方树（要 count 个）。排到下一拍才压栈，排上了给 True """
    if item is None:
        return False
    from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree
    return bool(OpenRecipeTree(item=item, qty=max(1, int(count or 1))))


def ItemAt(x, y):
    # type: (float, float) -> any
    """
    屏幕上这一点（全局坐标，和 GetGlobalPosition 一套）是哪样物品（Item）：MEI 自己的格子、原版和别的模组界面里的物品格都认
    （焦点探针，docs/architecture/focus.md：物品渲染器的控件名要带 item 或者就叫 renderer）；认不出给 None
    """
    main = _main()
    if main is None:
        return None
    return main.FocusAt(x, y).Item


def ItemUnderCursor():
    # type: () -> any
    """ PC 光标下的物品（同 ItemAt）；触屏、认不出给 None """
    main = _main()
    if main is None:
        return None
    return main.FocusAtCursor().Item


def Mode():
    # type: () -> str
    """ 现在是哪种模式：ctx.Const.ModeConst 的 Normal / Tool / Cheat（"normal" / "tool" / "cheat"），全局一份 """
    from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager
    return ModeManager.Current()


def CheatAllowed():
    # type: () -> any
    """ 服务端最近一次答的「有没有作弊模式的权限」（操作员）：True / False；还没问到、问不到给 None """
    from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager
    return ModeManager.CheatAllowed


def IsBookmarked(item):
    # type: (any) -> bool
    """ 这样物品在不在收藏（当前页签）里 """
    from MEIScripts.mei_mod.state import BookmarkManager
    return item is not None and bool(BookmarkManager.HasItem(item))


def SetBookmarked(item, on=True):
    # type: (any, bool) -> bool
    """ 收藏 / 取消收藏这样物品（当前页签）；页签满了收不进去、本来就是这样给 False。收藏栏开着的话当场重排 """
    if item is None:
        return False
    from MEIScripts.mei_mod.state import BookmarkManager
    changed = bool(BookmarkManager.SetItem(item, bool(on)))
    main = _main()
    sidebar = getattr(main, "ItemsSidebarIns", None) if main is not None else None
    if changed and sidebar is not None and getattr(sidebar, "Inited", False):
        sidebar.RefreshBookmarks()
    return changed


class ActionsFacade(object):
    """ ctx.UI.Actions """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
