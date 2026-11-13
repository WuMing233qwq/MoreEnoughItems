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
现在是什么模式、收藏一样物品；你画的物品格被点了照 MEI 自己的格子处理（ClickItem / OpenItemMenu）、重建正在看的配方页、
读写物品栏的搜索框、拿 MEI 写的悬停文字。作用在「当前挂着 MEI 的那个界面」上；那会儿没有（没挂 MEI 的界面、还没进世界）就做不了，
给 False / None（ShowRecipes / ShowUses 可以要求开 MEI 自己的界面）。
纯新增，不升 API_VERSION，第三方用 getattr 探测。只在客户端用；**别在绑定回调里调**（会重排格子），挪到下一帧
"""
from MEIScripts.constants.codes import QueryConst

__all__ = [
    "ShowRecipes", "ShowUses", "OpenTree", "ItemAt", "ItemUnderCursor", "Mode", "CheatAllowed",
    "IsBookmarked", "SetBookmarked", "ClickItem", "OpenItemMenu", "RefreshRecipes", "GetSearchText", "SetSearchText",
    "HoverText",
]


def _main():  # type: () -> any
    """ 当前挂着 MEI 的那个界面的主节点（栈顶那份）；没有给 None """
    from MEIScripts.mei_mod.ui_script.mei_ui import context
    return context.GetMainNode()


def _show(item, query_by, category, open_screen):  # type: (any, str, str, bool) -> bool
    if item is None:
        return False
    main = _main()
    if main is not None:
        return bool(main.ShowRecipeDetails(item, query_by, prefer_type=category))
    if not open_screen:
        return False
    from MEIScripts.mei_mod.ui_script.mei_ui.floating.screen import open_screen as push_screen
    return bool(push_screen({"item": item, "query_by": query_by, "prefer_type": category, "focus_id": None}))


def ShowRecipes(item, category=None, open_screen=False):
    # type: (any, str, bool) -> bool
    """
    开这样物品的配方页，看它怎么做（来源）；category 给了就先翻到那个类型。没有配方给 False。
    没挂着 MEI 的界面时：open_screen 为真就开 MEI 自己的界面、在那里开，为假给 False
    """
    return _show(item, QueryConst.Output, category, open_screen)


def ShowUses(item, category=None, open_screen=False):
    # type: (any, str, bool) -> bool
    """ 开这样物品的配方页，看它能用在哪（用途）；工作站会带上它服务的类型的全部配方。open_screen 同 ShowRecipes """
    return _show(item, QueryConst.Input, category, open_screen)


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


def _slot(main, item, path):  # type: (any, any, str) -> any
    """ 别的界面里（或你画的）一格：MEI 给它出菜单、模式接走点击用的那个替身；路径不对、取不到控件给 None """
    if main is None or item is None or not path:
        return None
    from MEIScripts.mei_mod.ui_script.mei_ui.floating.find import SlotTarget
    from MEIScripts.mei_mod.ui_script.proxy.focus.search import FocusHit
    from MEIScripts.utils.text import native_str
    try:
        target = SlotTarget(main, FocusHit(native_str(path), None, item.ItemId, item.AuxValue, False), item)
    except Exception:  # noqa
        return None
    return target if target.Control is not None else None


def ClickItem(item, path=None, secondary=False):
    # type: (any, str, bool) -> bool
    """
    你画的一格物品被点了（点击回调之后、下一帧调），照 MEI 自己的物品格处理：工具 / 作弊模式先接走（拿起、给物品）；
    触屏开 MEI 的二级菜单（来源 / 用途 / 收藏 / 配方树，摆在这一格旁边）；PC 上 secondary 为假查来源、为真查用途。
    path 是这一格物品渲染器的控件路径（从界面最根上算）：模式拿起时从它那儿起、菜单摆在它旁边；不给就只能查配方。
    没挂着 MEI 的界面时开 MEI 自己的界面查。做了什么给 True，什么都没做（没有配方、没有物品）给 False
    """
    if item is None:
        return False
    main = _main()
    target = _slot(main, item, path)
    if target is not None:
        from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager, is_touch
        if ModeManager.Intercept(target, bool(secondary)):
            return True
        if is_touch() and _request_menu(main, target):
            return True
    return _show(item, QueryConst.Input if secondary else QueryConst.Output, None, True)


def OpenItemMenu(item, path):
    # type: (any, str) -> bool
    """ 在这一格旁边开 MEI 的二级菜单（触屏那种：来源 / 用途 / 收藏 / 配方树）；path 同 ClickItem。开不了给 False """
    main = _main()
    return _request_menu(main, _slot(main, item, path))


def _request_menu(main, target):  # type: (any, any) -> bool
    menu = getattr(main, "Menu", None) if main is not None else None
    if target is None or menu is None:
        return False
    menu.Request(target)
    return True


def RefreshRecipes(category=None):
    # type: (str) -> bool
    """
    配方页正开着、正看的是这个类型（不给就是正看的那个）：按它现在的配方页控件重建一遍，停在原来那一页 ——
    改了类型的 RecipeCategory.ControlDef（比如量出来配方行要大一档）之后用。没开着、看的不是它给 False
    """
    main = _main()
    details = getattr(main, "RecipeDetailsIns", None) if main is not None else None
    refresh = getattr(details, "RefreshPage", None)
    return bool(refresh(category)) if callable(refresh) else False


def _search_box():  # type: () -> any
    main = _main()
    browser = getattr(main, "ItemsBrowserIns", None) if main is not None else None
    if browser is None or not getattr(browser, "Inited", False) or getattr(browser, "SearchControl", None) is None:
        return None
    return browser


def GetSearchText():
    # type: () -> any
    """ 物品栏搜索框里现在的字；物品栏没开着给 None """
    browser = _search_box()
    if browser is None:
        return None
    from MEIScripts.utils import utilities
    return utilities.GetEditBoxRawText(browser.SearchControl)


def SetSearchText(text):
    # type: (any) -> bool
    """ 把物品栏搜索框改成这些字并当场搜（空串是清空）；物品栏没开着给 False """
    browser = _search_box()
    if browser is None:
        return False
    from MEIScripts.utils.text import native_str
    browser.SearchControl.SetEditText(native_str(text or ""))
    browser.SearchItem()
    return True


def HoverText(item, lore=None):
    # type: (any, list) -> str
    """
    MEI 给这样物品写的悬停文字：物品自己的几行 + lore（你给的说明行，空一行接在后面）+ 设置「信息显示」里的 ID / 命名空间那两行 ——
    和 MEI 自己的格子一模一样，你的格子用它就和 MEI 的一致。没有物品给空串
    """
    if item is None:
        return ""
    from MEIScripts.mei_mod.ui_script.controls.item.panel import identity_lines
    from MEIScripts.utils.text import native_str
    text = native_str(getattr(item, "HoverText", "") or "")
    if lore:
        text += "\n\n" + "\n".join(native_str(line) for line in lore)
    return "\n".join([part for part in [text] + identity_lines(item) if part])


class ActionsFacade(object):
    """ ctx.UI.Actions """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
