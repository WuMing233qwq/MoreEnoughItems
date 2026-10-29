# coding=utf-8

# ----------------------------------------------------------------------
#  rules.py is part of MoreEnoughItems.
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
from MEIScripts.mei_mod.ui_script.mei_ui import context

def recipe_book_child_visible(_):
    try:
        main_node = context.GetMainNode()
        screen_def = main_node.GetScreenDef()
        if screen_def in ["crafting.inventory_screen", "crafting.crafting_screen"]:
            # 是否需要计算关联到 recipe_book 控件可见性 解决棍母控件影响自适应问题
            recipe_book = main_node.GetUIControl("/content_stack_panel/recipe_book")
            return recipe_book.GetVisible()
        else:
            return False
    except Exception:  # noqa
        return False


RULES = {
    "recipe_book_child_visible": recipe_book_child_visible,
}

STATIC_RULES = {"recipe_book_child_visible"}

RULE_PATH_PREFIXES = (
    "/recipe_book/tab_navigation_panel",
    "/recipe_book/category_tab_left_arrow",
    "/recipe_book/category_tab_right_arrow",
)

def resolve_rule_for_path(path):
    if path and any(prefix in path for prefix in RULE_PATH_PREFIXES):
        return "recipe_book_child_visible"
    return None


def eval_visible_rule(control, visible_rule, rule_cache=None):
    if visible_rule is None:
        return True

    if callable(visible_rule):
        try:
            return bool(visible_rule(control))
        except Exception:  # noqa
            return False

    if isinstance(visible_rule, basestring):
        if rule_cache is not None and visible_rule in STATIC_RULES and visible_rule in rule_cache:
            return rule_cache[visible_rule]

        rule = RULES.get(visible_rule)
        if rule is None:
            return True
        try:
            result = bool(rule(control))
            if rule_cache is not None and visible_rule in STATIC_RULES:
                rule_cache[visible_rule] = result
            return result
        except Exception:  # noqa
            return False

    return True

