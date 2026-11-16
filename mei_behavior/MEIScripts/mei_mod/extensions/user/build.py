# coding=utf-8
# ----------------------------------------------------------------------
#  build.py is part of MoreEnoughItems.
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
存档里的页面、配方（state/user_recipes.py）→ MEI 的类型、配方、来源。

一个页面是一个配方类型（"mei_user:<页面 Id>"），配方页托管给 host.UserPageHost 按排版画；物品按收藏的写法找回（BookmarkResolver），
找不回的格子当空格（模组卸了也不卡）；标签按物品表现查（ItemManager.ResolveTag），查不到就只有记下的那几样。
从服务器拿下来的（订阅的、统一的）页面、配方 Id 前面带服务器上的键（命名空间 ns，plan.py），名字照字面显示（plain_name）
"""
from MEIScripts.api.facades.types import RecipeCategory, StaticRecipeSource
from MEIScripts.common.classes.types.block import ROLES
from MEIScripts.mei_mod.state.user_recipes import holder_index, make_ingredient
from MEIScripts.mei_mod.state.user_share import qualify
from MEIScripts.utils.text import native_str

from .types import UserRecipe

CATEGORY_PREFIX = "mei_user:"
RECIPE_PREFIX = "mei:/user/"
SORT_BASE = 1000
""" 自制页面排在别的类型后面，按建的先后 """

DEFAULT_ICON = "textures/ui/mei/icons/edit"
""" 没设工作站的页面，页签上画铅笔 """


def category_id(page_id):  # type: (str) -> str
    return CATEGORY_PREFIX + page_id


def page_id_of(category):  # type: (any) -> str or None
    """ 类型（RecipeCategory 或 Id）是自制页面的话给页面 Id """
    value = getattr(category, "Id", category)
    if isinstance(value, basestring) and value.startswith(CATEGORY_PREFIX):
        return value[len(CATEGORY_PREFIX):]
    return None


def recipe_key(recipe_id):  # type: (str) -> str
    return RECIPE_PREFIX + recipe_id


def user_recipe_id(recipe):  # type: (any) -> str or None
    """ MEI 的配方是自制的话给存档里的配方 Id """
    data = getattr(recipe, "Data", None)
    return data.get("uid") if isinstance(recipe, UserRecipe) and isinstance(data, dict) else None


def plain_name(text):  # type: (any) -> unicode
    """
    拿下来的页面名照字面显示：去掉 § 格式码与控制字符；长得像本地化键（全是 ASCII、带点、没有空格）的把点换成全角 ——
    类型名要经 localize 查（RecipeManager.GetDisplayText），起名 tile.crafting_table.name 就会显示成「工作台」冒充原版的类型
    """
    text = text if isinstance(text, unicode) else native_str(text or "").decode("utf-8", "replace")
    chars, skip = [], False
    for char in text:
        if skip:
            skip = False
        elif char == u"\u00a7":
            skip = True
        elif ord(char) >= 32 and char != u"\x7f":
            chars.append(char)
    text = u"".join(chars).strip()
    if text and u"." in text and u" " not in text and all(ord(char) < 128 for char in text):
        text = text.replace(u".", u"\uff0e")
    return text


def make_recipe(page, recipe, holds, resolve, tag_items, ns=""):  # type: (dict, dict, callable, callable, callable, str) -> any
    """
    一条配方 → UserRecipe：同一角色按页面里的格子数排齐（排版里没有那么多格的、配方里多出来的不要）。
    一个产物都找不回的给 None（不进配方表）。ns：拿下来的分组在服务器上的键（类型、配方 Id 前面带上；Data 里没有本地配方 Id）
    """
    counts = dict((role, 0) for role in ROLES)
    for _index, role, _number in holder_index(page.get("blocks"), holds):
        counts[role] += 1
    groups = {}
    for role in ROLES:
        cells = list(recipe.get(role) or ())[:counts[role]]
        cells += [None] * (counts[role] - len(cells))
        groups[role] = [make_ingredient(cell, resolve, tag_items) for cell in cells]
    outputs = groups["out"]
    if not any(not ingredient.is_empty() for ingredient in outputs):
        return None
    data = {"uid": None if ns else recipe["id"], "share": ns or None, "page": page["id"], "f": dict(recipe.get("f") or {}),
            "note": recipe.get("note") or u""}
    return UserRecipe(category_id(qualify(ns, page["id"])), groups["in"], outputs, groups["cat"], data=data,
                      recipe_id=recipe_key(qualify(ns, recipe["id"])))


def field_max(page, recipes):  # type: (dict, list) -> dict
    """ 这一页每个字段最大的值（数值条按它画满多少）"""
    result = {}
    for recipe in recipes:
        for field, value in (recipe.get("f") or {}).items():
            if field in page.get("fields", ()) and (field not in result or value > result[field]):
                result[field] = value
    return result


def make_category(page, index, host, resolve, sort_index=None, ns=""):
    # type: (dict, int, any, callable, int, str) -> RecipeCategory
    """
    页面 → 类型：名字就是页面名（不是本地化键，localize 查不到原样给回来；拿下来的照字面显示，plain_name）；工作站一列（找不回的跳过）；
    图标是单独设的那一样，没设（或找不回）用第一个工作站，都没有就是铅笔。
    排序：给了 sort_index 用它（登记计划算的，plan.py），没给是 SORT_BASE + index。ns：拿下来的分组在服务器上的键
    """
    stations = []
    for data in page.get("stations") or ():
        item = resolve(data)
        if item is not None:
            stations.append(item.stack(1))
    chosen = resolve(page["icon"]) if page.get("icon") else None
    icon_item = chosen if chosen is not None else (stations[0].Item if stations else None)
    icon = (icon_item.ItemId, icon_item.AuxValue) if icon_item is not None else DEFAULT_ICON
    name = page.get("name") or page["id"]
    if ns:
        name = plain_name(name) or page["id"]
    return RecipeCategory(category_id(qualify(ns, page["id"])), name_key=native_str(name), icon=icon,
                          stations=stations, sort_index=SORT_BASE + index if sort_index is None else sort_index, page_host=host)


def make_source(page, recipes, holds, resolve, tag_items, ns=""):  # type: (dict, list, callable, callable, callable, str) -> tuple
    """ 一个页面的来源（手登记的配方表）：(StaticRecipeSource, 找不回的配方几条) """
    source = StaticRecipeSource(category_id(qualify(ns, page["id"])))
    dropped = 0
    for recipe in recipes:
        built = make_recipe(page, recipe, holds, resolve, tag_items, ns)
        if built is None:
            dropped += 1
            continue
        source.Add(built)
    return source, dropped
