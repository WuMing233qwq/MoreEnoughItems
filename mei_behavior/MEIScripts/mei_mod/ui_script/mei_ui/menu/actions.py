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
触屏菜单的动作表（docs/architecture/tooltip.md §6.6）。格子说「我出哪些动作」（panel.MenuActions() 返回 MenuKey），
这里按名字找到动作：按钮上的字、能不能点、点了做什么。写法照配方页的 RecipeAction —— 字、可用、执行分开声明。

收藏的那些操作（数量、分组、折叠、展开、排序、删除）写成下面一组 op_* 函数：**快捷键与菜单共用这一份**
（mei_ui/hotkeys，键只是另一个入口）。op_* 只改收藏、返回改没改，不碰界面；菜单的动作改完再让收藏栏重排，快捷键改完由它自己让收藏栏重排。

每个动作还说自己在哪一段（Section：查询 / 配方 / 数量 / 排序 / 分组 / 显示 / 删除 / 候选）、是不是删除类（Danger，按钮红字）——
菜单按段排（tooltip.md §6.12）：面板给的顺序里相邻同段的并成一段，一段一行、左边写段名；
数量、候选这两段是步进器（两头按钮、中间写数字，SECTIONS 里有 Value 的）
"""
from mod_log import logger

from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import MenuKindText, MenuSectionText, MenuText
from MEIScripts.constants.ui import MenuKey
from MEIScripts.mei_mod.state import BookmarkManager
from MEIScripts.mei_mod.state.bookmarks import (
    GROUP_FOLD, GROUP_VIEW, KIND_RECIPE, KIND_TREE, MAX_COUNT, UNGROUPED, VIEW_LIST, entry_count, entry_expanded,
)
from MEIScripts.registry import RecipeManager
from MEIScripts.utils.text import error_text


class MenuTarget(object):
    """
    菜单是给哪一格开的：主节点、面板、收藏格（只有收藏栏的格子有）。物品跟着面板走 —— 多候选格选了别的候选，
    「来源 / 收藏」就对着新的那个。调试键没有面板时直接给物品。Cache 是这一次打开里查过的东西（比如有没有配方）
    """
    __slots__ = ("Main", "Panel", "Cell", "Cache", "_Item")

    def __init__(self, main, panel=None, item=None, cell=None):
        self.Main = main
        self.Panel = panel
        self.Cell = cell if cell is not None else getattr(panel, "Cell", None)
        self.Cache = {}
        self._Item = item

    @property
    def Item(self):  # type: () -> any
        if self.Panel is not None:
            return getattr(self.Panel, "Item", None)
        return self._Item


class MenuAction(object):
    """
    菜单里的一个动作。Label 是按钮上的字，或 fn(target) -> 字（「收藏 / 取消收藏」跟着状态变）；
    Enabled 是 fn(target) -> 能不能点（缺省都能，不能的灰掉、点了不执行）；Run 是 fn(target)。
    Keep：点了不收起菜单（−1 / +1、上移下移、换候选要连点）；Follow：改完收藏栏会重排、格子换了新的，菜单跟着这一条收藏走；
    Confirm：要二次确认时第一下按钮变成的字（删除整组：没有撤销）；
    Section：在哪一段（SECTIONS 的键，None 就自成一段、不写段名）；Danger：删除类，按钮上的字用红色；
    Icon：用哪个图标按钮显示（MenuConst.Icons 的槽名，比如候选的左右箭头），None 就是文字按钮
    """
    __slots__ = ("Key", "Label", "Run", "Enabled", "Keep", "Follow", "Confirm", "Section", "Danger", "Icon")

    def __init__(self, key, label, run, enabled=None, keep=False, follow=False, confirm=None, section=None, danger=False,
                 icon=None):
        self.Key = key
        self.Label = label
        self.Run = run
        self.Enabled = enabled
        self.Keep = keep or follow
        self.Follow = follow
        self.Confirm = confirm
        self.Section = section
        self.Danger = danger
        self.Icon = icon

    def LabelFor(self, target, armed=False):  # type: (MenuTarget, bool) -> any
        if armed and self.Confirm:
            return self.Confirm
        text = self.Label(target) if callable(self.Label) else self.Label
        return DANGER_COLOR + text if self.Danger and text else text

    def WidthLabels(self, target):  # type: (MenuTarget) -> list
        """
        排版按哪几种字算这个按钮的宽：现在的字，加上开着菜单时会变成的字（二次确认）。
        别的会变的字（收藏 / 取消收藏、折叠 / 展开…）点了就收起菜单，下次打开重新排，不用预留
        """
        labels = [self.LabelFor(target)]
        if self.Confirm:
            labels.append(self.Confirm)
        return labels

    def IsEnabled(self, target):  # type: (MenuTarget) -> bool
        if self.Enabled is None:
            return True
        try:
            return bool(self.Enabled(target))
        except Exception as e:  # noqa  判断出错就别灰掉，点了照常去做
            logger.warn("[MEI/menu] 动作 {} 判断能不能点失败: {}".format(self.Key, error_text(e)))
            return True


DANGER_COLOR = u"\u00a7c"
""" 删除类按钮的字色（§c，红）；二次确认的「确认删除？」自带这个颜色 """

MUTED_COLOR = u"\u00a77"
""" 灰掉的按钮的字色（§7，灰）：遮罩盖住了按钮底，字也跟着灰，一眼看得出点不了 """


def mute(text):  # type: (any) -> any
    """ 灰掉的按钮的字：去掉开头的颜色码（删除类的红），换成灰色 """
    if not text:
        return text
    if not isinstance(text, unicode):  # noqa: F821  py2 的 unicode
        text = text.decode("utf-8", "replace")
    while len(text) >= 2 and text[0] == u"\u00a7":
        text = text[2:]
    return MUTED_COLOR + text


# 收藏的操作：调试键与菜单共用，只改收藏、返回改没改（或改完的样子）
# ======================================================================================================================
def op_toggle_item(item):  # type: (any) -> tuple
    """ 收藏 / 取消收藏这个物品，返回 (原来收着没有, 现在收着没有) —— 两个都是假就是页签满了没收进去 """
    had = BookmarkManager.HasItem(item)
    return had, bool(BookmarkManager.ToggleItem(item))


def op_remove(cell):  # type: (any) -> bool
    return bool(BookmarkManager.RemoveAt(cell.Index))


def op_remove_group(cell):  # type: (any) -> bool
    """ 只删真正的分组：不分组的那部分整个清掉太容易误按 """
    return cell.Group != UNGROUPED and bool(BookmarkManager.RemoveGroup(cell.Group))


def op_count(cell, delta):  # type: (any, int) -> bool
    return bool(BookmarkManager.AdjustCountAt(cell.Index, delta))


def op_join(cell):  # type: (any) -> int
    """ 并入上一组，返回所在分组 id；没动返回 0 """
    return BookmarkManager.JoinPrevGroupAt(cell.Index)


def op_leave(cell):  # type: (any) -> bool
    return bool(BookmarkManager.LeaveGroupAt(cell.Index))


def op_view(cell):  # type: (any) -> str
    """ 所在的组（或不分组的那部分）横排 / 竖排互换，返回换完的视图 """
    return BookmarkManager.ToggleGroupView(cell.Group)


def op_unfold(cell):  # type: (any) -> bool
    """ 所在的组折叠着就展开它（折叠的组里配方都收成一格，单独展开一条也看不出来），返回动没动 """
    if cell.Group == UNGROUPED or not BookmarkManager.GroupProps(cell.Group).get(GROUP_FOLD):
        return False
    BookmarkManager.ToggleGroupFold(cell.Group)
    return True


def op_fold(cell):  # type: (any) -> any
    """ 折叠 / 展开所在的组，返回换完是否折叠；不在组里返回 None（不分组的那部分不能折叠）"""
    if cell.Group == UNGROUPED:
        return None
    return BookmarkManager.ToggleGroupFold(cell.Group)


def is_expanded(cell):  # type: (any) -> bool
    """ 配方收藏现在是不是展开的：玩家定过就按定的，没定过跟视图走（竖排展开、横排收起）"""
    return entry_expanded(cell.Entry, BookmarkManager.GroupProps(cell.Group).get(GROUP_VIEW) == VIEW_LIST)


def op_expand(cell):  # type: (any) -> any
    """ 配方 / 配方树收藏展开 / 收起这一条，返回改之前是不是展开的；不是这两种、没改动返回 None """
    if cell.Entry.get("k") not in (KIND_RECIPE, KIND_TREE):
        return None
    expanded = is_expanded(cell)
    if not BookmarkManager.SetExpandedAt(cell.Index, not expanded):
        return None
    return expanded


def op_move(cell, delta):  # type: (any, int) -> any
    """ 上移（-1）/ 下移（+1），返回挪到的下标；挪不动返回 None（规则见 BookmarkManager.MoveTargetAt）"""
    return BookmarkManager.MoveAt(cell.Index, delta)


def op_move_head(cell):  # type: (any) -> any
    """ 移到组首，返回挪到的下标；不在组里、已经是组首返回 None """
    return BookmarkManager.MoveToGroupHeadAt(cell.Index)


# 动作（菜单用）
# ======================================================================================================================
def _refresh_bookmarks(target):
    """ 收藏变了：收藏栏立刻重排，不等它 0.2 秒一次的轮询 """
    sidebar = getattr(target.Main, "ItemsSidebarIns", None)
    if getattr(sidebar, "Inited", False):
        sidebar.RefreshBookmarks()


def _changes_bookmarks(op):
    """
    收藏格的动作：改收藏（只在收藏格上），改了就让收藏栏重排。改没改看收藏的改动计数 —— op 的返回值各有各的意思
    （折叠成「否」、挪到第 0 位都是改了），不拿它判断
    """
    def run(target):
        if target.Cell is None:
            return
        before = BookmarkManager.Revision()
        op(target.Cell)
        if BookmarkManager.Revision() != before:
            _refresh_bookmarks(target)
    return run


def _has_recipes(query_by):
    """ 来源 / 用途灰不灰：这个物品有没有配方。每次打开菜单查一次（走查询缓存），查出错就当有 —— 点了照常去查 """
    def enabled(target):
        item = target.Item
        if item is None:
            return False
        key = (query_by, getattr(item, "ItemId", None), getattr(item, "AuxValue", None))
        if key not in target.Cache:
            try:
                result = RecipeManager.QueryRecipe(item, query_by)
                target.Cache[key] = bool(result) and any(result.values())
            except Exception as e:  # noqa
                logger.warn("[MEI/menu] 查配方失败（按有配方算）: {}".format(error_text(e)))
                target.Cache[key] = True
        return target.Cache[key]
    return enabled


def _source(target):
    target.Main.ShowRecipeDetails(target.Item, QueryConst.Output)


def _uses(target):
    target.Main.ShowRecipeDetails(target.Item, QueryConst.Input)


def _recipe_tree(target):
    """ 以这个物品为根开配方树（PushScreen 一个新界面，docs/architecture/recipe_tree.md）"""
    from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree  # 配方树用到才 import
    if target.Item is not None:
        OpenRecipeTree(item=target.Item)


def _open_tree(target):
    """ 配方树收藏：按存下的选择、折叠、数量打开那棵树 """
    from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree
    if target.Cell is not None:
        OpenRecipeTree(saved=target.Cell.Entry)


def _bookmark_label(target):
    return MenuText.Unbookmark if BookmarkManager.HasItem(target.Item) else MenuText.Bookmark


def _bookmark_enabled(target):
    """ 页签满了只能取消、不能再收 """
    return target.Item is not None and (BookmarkManager.HasItem(target.Item) or not BookmarkManager.IsTabFull())


def _bookmark(target):
    if target.Item is not None:
        op_toggle_item(target.Item)
        _refresh_bookmarks(target)


def _open_recipe(target):
    if target.Cell is not None:
        target.Main.ShowBookmarkedRecipe(target.Cell.Entry)


def _grouped(target):
    return target.Cell is not None and target.Cell.Group != UNGROUPED


def _count_enabled(delta):
    def enabled(target):
        if target.Cell is None:
            return False
        count = entry_count(target.Cell.Entry)
        return count > 1 if delta < 0 else count < MAX_COUNT
    return enabled


def _fold_label(target):
    folded = _grouped(target) and BookmarkManager.GroupProps(target.Cell.Group).get(GROUP_FOLD)
    return MenuText.Unfold if folded else MenuText.Fold


def _expand_label(target):
    cell = target.Cell
    if cell is None:
        return MenuText.ExpandRecipe
    if cell.Group != UNGROUPED and BookmarkManager.GroupProps(cell.Group).get(GROUP_FOLD):
        return MenuText.UnfoldGroup
    return MenuText.CollapseRecipe if is_expanded(cell) else MenuText.ExpandRecipe


def _expand(cell):
    """ C 的配方那一半：组折叠着先展开组，否则展开 / 收起这一条 """
    if op_unfold(cell):
        return True
    return op_expand(cell)


def _view_label(target):
    listed = target.Cell is not None and BookmarkManager.GroupProps(target.Cell.Group).get(GROUP_VIEW) == VIEW_LIST
    return MenuText.ToGrid if listed else MenuText.ToList


def _move_enabled(delta):
    def enabled(target):
        return target.Cell is not None and BookmarkManager.MoveTargetAt(target.Cell.Index, delta) is not None
    return enabled


def _join_enabled(target):
    return target.Cell is not None and BookmarkManager.CanJoinPrevGroupAt(target.Cell.Index)


def _head_enabled(target):
    return target.Cell is not None and BookmarkManager.GroupHeadAt(target.Cell.Index) is not None


def _candidates(target):
    return len(getattr(target.Panel, "Candidates", None) or ()) > 1


def _step_candidate(step):
    def run(target):
        panel = target.Panel
        if panel is not None and _candidates(target):
            (panel.Prev if step < 0 else panel.Next)()
    return run


def _close(_target):
    """ 收起由菜单自己做 """


# 段
# ======================================================================================================================
SECTION_QUERY = "query"
SECTION_RECIPE = "recipe"
SECTION_COUNT = "count"
SECTION_SORT = "sort"
SECTION_GROUP = "group"
SECTION_VIEW = "view"
SECTION_DELETE = "delete"
SECTION_CANDIDATE = "candidate"


class MenuSection(object):
    """
    菜单里的一段：Label 是段名，或 fn(target) -> 段名（数量一段在配方收藏上写「倍数」）；
    Value 是 fn(target) -> 步进器中间的数字（有它的段，两个按钮时排成步进器：[−] 数字 [+]）
    """
    __slots__ = ("Key", "Label", "Value")

    def __init__(self, key, label, value=None):
        self.Key = key
        self.Label = label
        self.Value = value

    def LabelFor(self, target):  # type: (MenuTarget) -> any
        return self.Label(target) if callable(self.Label) else self.Label

    def ValueFor(self, target):  # type: (MenuTarget) -> any
        """ 步进器中间的数字；出错只记一行、给空串 —— 这是填按钮时调的，抛出去整个菜单就填不完 """
        if self.Value is None:
            return None
        try:
            return self.Value(target)
        except Exception as e:  # noqa
            logger.warn("[MEI/menu] 段 {} 的数字取不到: {}".format(self.Key, error_text(e)))
            return u""


def _count_section_label(target):
    cell = target.Cell
    if cell is not None and cell.Entry.get("k") == KIND_RECIPE:
        return MenuSectionText.Multiple
    return MenuSectionText.Count


def _count_value(target):
    cell = target.Cell
    return MenuSectionText.CountValue.format(entry_count(cell.Entry)) if cell is not None else u""


def _candidate_value(target):
    panel = target.Panel
    candidates = getattr(panel, "Candidates", None) or ()
    if not candidates:
        return u""
    return MenuSectionText.CandidateValue.format(getattr(panel, "CurrentIndex", 0) + 1, len(candidates))


SECTIONS = {
    SECTION_QUERY: MenuSection(SECTION_QUERY, MenuSectionText.Query),
    SECTION_RECIPE: MenuSection(SECTION_RECIPE, MenuSectionText.Recipe),
    SECTION_COUNT: MenuSection(SECTION_COUNT, _count_section_label, _count_value),
    SECTION_SORT: MenuSection(SECTION_SORT, MenuSectionText.Sort),
    SECTION_GROUP: MenuSection(SECTION_GROUP, MenuSectionText.Group),
    SECTION_VIEW: MenuSection(SECTION_VIEW, MenuSectionText.View),
    SECTION_DELETE: MenuSection(SECTION_DELETE, MenuSectionText.Delete),
    SECTION_CANDIDATE: MenuSection(SECTION_CANDIDATE, MenuSectionText.Candidate, _candidate_value),
}
""" 段名 -> 段 """


def group_sections(actions):  # type: (list) -> list
    """
    动作按段分组：照给的顺序，相邻同段的并成一段，返回 [(段, [动作, ...]), ...]。
    没写段（Section 为 None）、或段表里没有的，各自成一段（段名空着）
    """
    groups = []
    for action in actions:
        key = action.Section
        if groups and key is not None and groups[-1][0].Key == key:
            groups[-1][1].append(action)
            continue
        section = SECTIONS.get(key) if key is not None else None
        groups.append((section or MenuSection(key, u""), [action]))
    return groups


def is_stepper(section, actions):  # type: (MenuSection, list) -> bool
    """ 排成步进器：段有数字、正好两个按钮（[−] 数字 [+]）"""
    return section.Value is not None and len(actions) == 2


ACTIONS = {
    MenuKey.Source: MenuAction(MenuKey.Source, MenuText.Source, _source, enabled=_has_recipes(QueryConst.Output),
                               section=SECTION_QUERY),
    MenuKey.Uses: MenuAction(MenuKey.Uses, MenuText.Uses, _uses, enabled=_has_recipes(QueryConst.Input),
                             section=SECTION_QUERY),
    MenuKey.Bookmark: MenuAction(MenuKey.Bookmark, _bookmark_label, _bookmark, enabled=_bookmark_enabled,
                                 section=SECTION_QUERY),
    MenuKey.Remove: MenuAction(MenuKey.Remove, MenuText.Remove, _changes_bookmarks(op_remove), section=SECTION_DELETE,
                               danger=True),
    MenuKey.OpenRecipe: MenuAction(MenuKey.OpenRecipe, MenuText.OpenRecipe, _open_recipe, section=SECTION_RECIPE),
    MenuKey.RecipeTree: MenuAction(MenuKey.RecipeTree, MenuText.RecipeTree, _recipe_tree,
                                   enabled=_has_recipes(QueryConst.Output), section=SECTION_QUERY),
    MenuKey.OpenTree: MenuAction(MenuKey.OpenTree, MenuText.OpenTree, _open_tree, section=SECTION_RECIPE),
    MenuKey.CountDown: MenuAction(MenuKey.CountDown, MenuText.CountDown, _changes_bookmarks(lambda c: op_count(c, -1)),
                                  enabled=_count_enabled(-1), follow=True, section=SECTION_COUNT),
    MenuKey.CountUp: MenuAction(MenuKey.CountUp, MenuText.CountUp, _changes_bookmarks(lambda c: op_count(c, 1)),
                                enabled=_count_enabled(1), follow=True, section=SECTION_COUNT),
    MenuKey.JoinGroup: MenuAction(MenuKey.JoinGroup, MenuText.JoinGroup, _changes_bookmarks(op_join),
                                  enabled=_join_enabled, section=SECTION_GROUP),
    MenuKey.LeaveGroup: MenuAction(MenuKey.LeaveGroup, MenuText.LeaveGroup, _changes_bookmarks(op_leave),
                                   enabled=_grouped, section=SECTION_GROUP),
    MenuKey.FoldGroup: MenuAction(MenuKey.FoldGroup, _fold_label, _changes_bookmarks(op_fold), enabled=_grouped,
                                  section=SECTION_VIEW),
    MenuKey.Expand: MenuAction(MenuKey.Expand, _expand_label, _changes_bookmarks(_expand), section=SECTION_RECIPE),
    MenuKey.View: MenuAction(MenuKey.View, _view_label, _changes_bookmarks(op_view), section=SECTION_VIEW),
    MenuKey.RemoveGroup: MenuAction(MenuKey.RemoveGroup, MenuText.RemoveGroup, _changes_bookmarks(op_remove_group),
                                    enabled=_grouped, confirm=MenuText.ConfirmRemoveGroup, section=SECTION_DELETE,
                                    danger=True),
    MenuKey.MoveUp: MenuAction(MenuKey.MoveUp, MenuText.MoveUp, _changes_bookmarks(lambda c: op_move(c, -1)),
                               enabled=_move_enabled(-1), follow=True, section=SECTION_SORT),
    MenuKey.MoveDown: MenuAction(MenuKey.MoveDown, MenuText.MoveDown, _changes_bookmarks(lambda c: op_move(c, 1)),
                                 enabled=_move_enabled(1), follow=True, section=SECTION_SORT),
    MenuKey.MoveHead: MenuAction(MenuKey.MoveHead, MenuText.MoveHead, _changes_bookmarks(op_move_head),
                                 enabled=_head_enabled, follow=True, section=SECTION_SORT),
    MenuKey.PrevCandidate: MenuAction(MenuKey.PrevCandidate, MenuText.PrevCandidate, _step_candidate(-1),
                                      enabled=_candidates, keep=True, section=SECTION_CANDIDATE, icon="prev"),
    MenuKey.NextCandidate: MenuAction(MenuKey.NextCandidate, MenuText.NextCandidate, _step_candidate(1),
                                      enabled=_candidates, keep=True, section=SECTION_CANDIDATE, icon="next"),
    MenuKey.Close: MenuAction(MenuKey.Close, MenuText.Close, _close),
}
""" 名字 -> 动作 """


def kind_of(panel):  # type: (any) -> any
    """ 顶栏左边写的「这是哪种格子」：面板的 MenuKind()，没有就写物品 """
    ask = getattr(panel, "MenuKind", None)
    try:
        kind = ask() if callable(ask) else None
    except Exception as e:  # noqa
        logger.warn("[MEI/menu] 取格子种类失败: {}".format(error_text(e)))
        kind = None
    return kind if kind else MenuKindText.Item


def actions_for(panel):  # type: (any) -> list
    """
    这一格出哪些动作（照面板给的顺序），最后一定是「关闭」（菜单把它画在顶栏，不占按钮池）。面板没写 MenuActions 就只有「关闭」；
    不认识的名字跳过、记一行（第三方面板继承 ItemPanel，不覆写就是来源、用途、收藏）
    """
    ask = getattr(panel, "MenuActions", None)
    keys = list(ask() or ()) if callable(ask) else []
    actions = []
    for key in keys:
        action = ACTIONS.get(key)
        if action is None:
            logger.warn("[MEI/menu] 不认识的菜单动作 {!r}，跳过".format(key))
            continue
        if action.Key != MenuKey.Close and action not in actions:
            actions.append(action)
    actions.append(ACTIONS[MenuKey.Close])
    return actions
