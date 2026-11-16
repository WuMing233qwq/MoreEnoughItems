# coding=utf-8
# ----------------------------------------------------------------------
#  plan.py is part of MoreEnoughItems.
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
登记哪些页面（docs/architecture/user_recipes.md §22）。纯逻辑，零引擎依赖。

三处的页面：本地开着的分组、订阅的服务器分组、统一的服务器分组。
- 拿下来的（订阅的、统一的）登记时页面 / 配方 Id 前面加服务器上的键（命名空间，state/user_share.qualify）：和本地的、别的分组的都不撞，
  别人抄了谁的 Id 也顶替不了谁；同一个分组订阅着、统一着、取消统一，类型 Id 与配方 Id 都不变（收藏、置顶跟得住）。
- 统一的另外「占住」不带命名空间的同一个 Id：本地同一个页面 / 配方 Id 的不登记（「同 Id 替换」，只给操作员统一生效的那份）。
- 先到先得：统一的 > 本地的 > 订阅的；同一来源里按给的先后。
排序（RecipeCategory.sort_index）：统一的排在所有类型前面（BASES 是负的），本地的、订阅的排在别的类型后面
"""
from MEIScripts.mei_mod.state.user_share import qualify

UNIFIED, LOCAL, SUBSCRIBED = "unified", "local", "sub"
ORDER = (UNIFIED, LOCAL, SUBSCRIBED)
""" 先到先得的顺序 """

BASES = {UNIFIED: -10000, LOCAL: 1000, SUBSCRIBED: 20000}
""" 各来源的排序起点（加上来源自己给的先后）"""


class Entry(object):
    """ 要登记的一个页面：页面、要登记的那几条配方、从哪来、排序、命名空间（服务器上的键，本地的是空串）"""

    __slots__ = ("Page", "Recipes", "Origin", "Sort", "Ns")

    def __init__(self, page, recipes, origin, sort, ns=""):
        self.Page = page  # type: dict
        self.Recipes = recipes  # type: list
        self.Origin = origin  # type: str
        self.Sort = sort  # type: int
        self.Ns = ns  # type: str

    def PageId(self):  # type: () -> str
        """ 登记时的页面 Id（拿下来的带服务器上的键）"""
        return qualify(self.Ns, self.Page["id"])

    def Signature(self):  # type: () -> tuple
        """ 和上次登记的比（same）：页面、配方都是存储里的那几个 dict（改了会换成新的），排序、来源、命名空间也一样就不用重登记 """
        return self.Origin, self.Sort, self.Ns, self.Page, tuple(self.Recipes)


def same(old, new):  # type: (tuple, tuple) -> bool
    """ 两个 Signature 是不是同一份：页面、配方按对象比（is），不按内容比 —— 几千条配方逐条比内容太慢 """
    if old is None or new is None or old[:3] != new[:3] or old[3] is not new[3] or len(old[4]) != len(new[4]):
        return False
    return all(a is b for a, b in zip(old[4], new[4]))


def make_plan(sources):  # type: (dict) -> list
    """
    sources：{来源: [(页面, 它的配方, 先后, 命名空间)]}（来源是 UNIFIED / LOCAL / SUBSCRIBED；先后是这个来源里稳定的序号，决定排序；
    命名空间：本地的给空串，拿下来的给服务器上的键）→ [Entry]，按 ORDER 再按给的先后
    """
    pages_taken, recipes_taken, result = set(), set(), []
    for origin in ORDER:
        for item in sources.get(origin) or ():
            page, recipes, order = item[0], item[1], item[2]
            ns = item[3] if len(item) > 3 else ""
            page_id = qualify(ns, page["id"])
            if page_id in pages_taken:
                continue
            pages_taken.add(page_id)
            if origin == UNIFIED:
                pages_taken.add(page["id"])  # 同 Id 替换：本地同一个页面 Id 的不登记
            kept = []
            for recipe in recipes:
                recipe_id = qualify(ns, recipe["id"])
                if recipe_id in recipes_taken:
                    continue
                recipes_taken.add(recipe_id)
                if origin == UNIFIED:
                    recipes_taken.add(recipe["id"])
                kept.append(recipe)
            result.append(Entry(page, kept, origin, BASES[origin] + order, ns))
    return result


def by_page(recipes):  # type: (list) -> dict
    """ 配方按页面分好（各页面里按原来的先后）"""
    result = {}
    for recipe in recipes:
        result.setdefault(recipe["page"], []).append(recipe)
    return result
