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
每个快捷键做什么：ACTIONS 按快捷键 id（table.py）给 fn(主节点, FocusTarget, step) -> 是否改动了收藏（改了由 manager 让收藏栏重排）。
step 是滚轮类的方向（向上 +1、向下 -1），按键类恒为 0；目标是光标下的东西（table 里 Target 为假的「返回」给 None）。
光标下是什么由 manager 问焦点探针，这里只按它给的目标做事；不在能做的格子上就什么都不做、返回 False。
收藏的操作本身调 menu.actions 的 op_*：和触屏菜单共用一份（docs/architecture/tooltip.md §6）。
"""
import re

import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import BookmarkText
from MEIScripts.mei_mod.state import BookmarkManager, BookmarkResolver
from MEIScripts.mei_mod.state.bookmarks import KIND_RECIPE, KIND_TREE, MAX_TAB_ENTRIES, UNGROUPED
from MEIScripts.mei_mod.ui_script.mei_ui.menu.actions import (
    op_count, op_expand, op_fold, op_join, op_leave, op_move, op_move_head, op_remove, op_remove_group, op_toggle_item,
    op_unfold, op_view,
)
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.manager import previewable_recipe
from MEIScripts.utils.text import error_text, native_str

_FORMAT = re.compile(r"\xa7.")
""" 名字里的颜色码（§ 加一个字符）：复制出去的名字不要它 """


def _toggle_item(item):  # type: (any) -> bool
    had, now = op_toggle_item(item)
    if not had and not now and BookmarkManager.IsTabFull():
        # 页签满了收藏不进去：界面上看就是按了没反应，记一行好查
        logger.info("[MEI/hotkeys] " + native_str(BookmarkText.TabFull.format(MAX_TAB_ENTRIES)))
        return False
    return True


def _toggle(main, target, step=0):
    """ 收藏 / 取消收藏光标下的物品；光标在收藏格上时移除那一条 """
    cell = target.Cell
    if cell is not None:
        return op_remove(cell)
    if target.Item is None:
        return False
    return _toggle_item(target.Item)


def _on_cell(action):
    """ 只认光标下的收藏格的操作；不在收藏格上不动 """
    def run(main, target, step=0):
        cell = target.Cell
        if cell is None:
            return False
        return action(cell)
    return run


def _on_cell_step(action):
    """ 滚轮类、只认光标下的收藏格：action(格子, step) """
    def run(main, target, step=0):
        cell = target.Cell
        if cell is None or not step:
            return False
        return action(cell, step)
    return run


def _remove_group(cell):
    """ 只删真正的分组：不分组的那部分整个清掉太容易误按 """
    if cell.Group == UNGROUPED:
        return False
    return op_remove_group(cell)


def _count(delta):
    def run(cell):
        return op_count(cell, delta)
    return run


def _join(cell):
    return bool(op_join(cell))


def _view(cell):
    op_view(cell)
    return True


def _fold(cell):
    """
    配方收藏 = 展开 / 收起这一条（横排、竖排都行）；物品收藏 = 折叠 / 展开所在的组。
    组折叠着时先把组展开 —— 折叠的组里配方都收成一格，单独展开一条也看不出来
    """
    if op_unfold(cell):
        return True
    if cell.Entry.get("k") in (KIND_RECIPE, KIND_TREE):
        return op_expand(cell) is not None
    return op_fold(cell) is not None


def _show(query_by):
    """ 查光标下物品的来源 / 用途，任何界面的物品格都行；不改收藏 """
    def run(main, target, step=0):
        item = target.Item
        if item is not None:
            main.ShowRecipeDetails(item, query_by)
        return False
    return run


def _tree(main, target, step=0):
    """ 光标下的物品开配方树（任何界面的物品格都行）；不改收藏 """
    item = target.Item
    if item is None:
        return False
    from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree  # 配方树用到才 import
    OpenRecipeTree(item=item)
    return False


def _tooltip(main, target, step=0):
    """
    显示 / 收起高级 Tooltip（docs/architecture/tooltip.md §7）。比悬停多两样：出的不随光标收起（钉住看），普通物品也能看配方预览。
    已显示 → 收起；格子自带 tooltip（多候选格、声明了预览的配方收藏）→ 显示它，不随光标收起；
    别的配方收藏 → 那条配方的预览；别的物品 → 它第一条能预览的配方。设置里关了「启用高级Tooltip」就什么都不出
    """
    tooltip = getattr(main, "Tooltip", None)
    if tooltip is None or not getattr(tooltip, "Enabled", True):
        return False
    if tooltip.IsVisible():
        tooltip.Hide()
        return False
    panel = target.Panel
    content_of = getattr(panel, "TooltipContent", None) if panel is not None else None
    if callable(content_of) and content_of() is not None:
        # 格子自带的（多候选格、声明了预览的配方收藏）：和悬停出的一样，只是不随光标收起
        tooltip.ShowFor(panel, own=False)
        return False
    cell = target.Cell
    if cell is not None and cell.Entry.get("k") == KIND_RECIPE:
        recipe = BookmarkResolver.ResolveRecipe(cell.Entry)
    elif target.Item is not None:
        recipe = previewable_recipe(target.Item)
    else:
        return False
    if recipe is not None:
        tooltip.ShowRecipe(recipe)
    return False


def _copy(get_text):
    """ 把光标下物品的名字 / ID 放进剪贴板（NEI 的 Ctrl+C / Ctrl+X）；不改收藏 """
    def run(main, target, step=0):
        item = target.Item
        if item is None:
            return False
        text = get_text(item)
        if text:
            try:
                game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
                game.SetClipboardContent(native_str(text))  # 递给引擎的字一律 str（引擎结论 §2）
            except Exception as e:  # noqa
                logger.error("[MEI/hotkeys] 写剪贴板失败: {}".format(error_text(e)))
        return False
    return run


def _plain_name(item):  # type: (any) -> str
    """ 物品名：悬停文字的第一行、去掉颜色码；取不到用 ID """
    try:
        text = native_str(item.HoverText or "")
    except Exception:  # noqa  惰性字段取不到
        text = ""
    name = _FORMAT.sub("", text.decode("utf-8", "replace").split(u"\n")[0]).strip()
    return native_str(name) if name else native_str(getattr(item, "ItemId", "") or "")


def _item_id(item):  # type: (any) -> str
    return native_str(getattr(item, "ItemId", "") or "")


def _candidate(fixed=0):
    """ 多候选格换候选：按键类给 fixed（-1 上一个、+1 下一个），滚轮类按方向（向上上一个、向下下一个）；不改收藏 """
    def run(main, target, step=0):
        panel = target.Panel
        direction = fixed or -step
        if panel is None or not direction or len(getattr(panel, "Candidates", None) or ()) < 2:
            return False
        (panel.Prev if direction < 0 else panel.Next)()
        return False
    return run


def _open_bookmark(main, target, step=0):
    """ 打开光标下的收藏：配方收藏翻到那一条、配方树收藏打开存的那棵、物品收藏查来源；不改收藏 """
    cell = target.Cell
    if cell is None:
        return False
    kind = cell.Entry.get("k")
    if kind == KIND_RECIPE:
        main.ShowBookmarkedRecipe(cell.Entry)
    elif kind == KIND_TREE:
        from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree  # 配方树用到才 import
        OpenRecipeTree(saved=cell.Entry)
    elif target.Item is not None:
        main.ShowRecipeDetails(target.Item, QueryConst.Output)
    return False


def _details(main):
    """ 开着的配方页；没开给 None """
    details = getattr(main, "RecipeDetailsIns", None)
    return details if getattr(details, "Created", False) else None


def _row_recipe(main, target):
    """ 光标下那一行配方（配方页开着才有）"""
    details = _details(main)
    finder = getattr(details, "RecipeAt", None) if details is not None else None
    if finder is None or target is None or target.Pos is None:
        return None
    return finder(target.Pos[0], target.Pos[1])


def _star_recipe(main, target, step=0):
    """ 收藏 / 取消收藏光标下这一行配方（NEI 的 Shift+A）；配方页上的星号跟着变（每帧回读收藏）"""
    recipe = _row_recipe(main, target)
    if recipe is None or not BookmarkManager.RecipeKey(recipe):
        return False
    starred = BookmarkManager.HasRecipe(recipe)
    if not starred and BookmarkManager.IsTabFull():
        logger.info("[MEI/hotkeys] " + native_str(BookmarkText.TabFull.format(MAX_TAB_ENTRIES)))
        return False
    BookmarkManager.SetRecipe(recipe, not starred)
    return True


def _tree_recipe(main, target, step=0):
    """ 以光标下这一行配方开配方树（和配方行上的树按钮一样）；不改收藏 """
    recipe = _row_recipe(main, target)
    if recipe is None:
        return False
    from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree
    OpenRecipeTree(recipe=recipe)
    return False


def _back(main, target=None, step=0):
    """ 配方页返回上一个查询（NEI 的 Backspace）；配方页没开什么都不做 """
    details = _details(main)
    if details is not None:
        details.GoBack()
    return False


# 光标下的东西能不能做（Alt 快捷键帮助只列这些；和上面各个动作自己的判断对上）
# ======================================================================================================================
def _has_item(main, target):
    return target is not None and target.Item is not None


def _has_cell(main, target):
    return target is not None and target.Cell is not None


def _has_group(main, target):
    return _has_cell(main, target) and target.Cell.Group != UNGROUPED


def _has_candidates(main, target):
    panel = target.Panel if target is not None else None
    return len(getattr(panel, "Candidates", None) or ()) >= 2


def _has_row(main, target):
    return _row_recipe(main, target) is not None


def _has_details(main, target=None):
    return _details(main) is not None


APPLIES = {
    "source": _has_item,
    "uses": _has_item,
    "bookmark": lambda main, target: _has_item(main, target) or _has_cell(main, target),
    "tree": _has_item,
    "tooltip": _has_item,
    "copy_name": _has_item,
    "copy_id": _has_item,
    "candidate_wheel": _has_candidates,
    "candidate_prev": _has_candidates,
    "candidate_next": _has_candidates,
    "open_bookmark": _has_cell,
    "remove": _has_cell,
    "remove_group": _has_group,
    "count_up": _has_cell,
    "count_down": _has_cell,
    "count_wheel": _has_cell,
    "move_up": _has_cell,
    "move_down": _has_cell,
    "move_head": _has_cell,
    "join": _has_cell,
    "leave": _has_cell,
    "view": _has_cell,
    "fold": _has_cell,
    "star_recipe": _has_row,
    "tree_recipe": _has_row,
    "back": _has_details,
}
""" 快捷键 id -> fn(主节点, FocusTarget 或 None) -> 光标下的东西能不能做它 """


def applies(hotkey_id, main, target):  # type: (str, any, any) -> bool
    check = APPLIES.get(hotkey_id)
    try:
        return check is not None and bool(check(main, target))
    except Exception as e:  # noqa  判断出错就当做不了，帮助少列一行而已
        logger.warn("[MEI/hotkeys] 判断 {} 能不能做失败: {}".format(hotkey_id, error_text(e)))
        return False


ACTIONS = {
    "source": _show(QueryConst.Output),
    "uses": _show(QueryConst.Input),
    "bookmark": _toggle,
    "tree": _tree,
    "tooltip": _tooltip,
    "copy_name": _copy(_plain_name),
    "copy_id": _copy(_item_id),
    "candidate_wheel": _candidate(),
    "candidate_prev": _candidate(-1),
    "candidate_next": _candidate(1),
    "open_bookmark": _open_bookmark,
    "remove": _on_cell(op_remove),
    "remove_group": _on_cell(_remove_group),
    "count_up": _on_cell(_count(1)),
    "count_down": _on_cell(_count(-1)),
    "count_wheel": _on_cell_step(op_count),
    "move_up": _on_cell(lambda cell: op_move(cell, -1) is not None),
    "move_down": _on_cell(lambda cell: op_move(cell, 1) is not None),
    "move_head": _on_cell(lambda cell: op_move_head(cell) is not None),
    "join": _on_cell(_join),
    "leave": _on_cell(op_leave),
    "view": _on_cell(_view),
    "fold": _on_cell(_fold),
    "star_recipe": _star_recipe,
    "tree_recipe": _tree_recipe,
    "back": _back,
}
""" 快捷键 id -> fn(主节点, FocusTarget 或 None, step) -> 是否改动了收藏 """
