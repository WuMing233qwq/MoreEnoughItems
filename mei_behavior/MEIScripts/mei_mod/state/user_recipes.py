# coding=utf-8
# ----------------------------------------------------------------------
#  user_recipes.py is part of MoreEnoughItems.
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
玩家自制配方（MEI 编辑器，docs/architecture/user_recipes.md §12.3）：页面（一个页面 = 一台机器 = 一个配方类型）与配方，全局存、跨存档。

pages   [{"id", "name", "stations": [物品数据]（工作站，0 ~ MAX_STATIONS 个）, "icon": 物品数据或 None（类型的图标；None 是用第一个工作站）,
          "w", "h": 内容区的宽、高, "fields": [字段 Id], "blocks": [积木]}]
recipes [{"id", "page", "in": [格], "out": [格], "cat": [格], "f": {字段 Id: 数}, "note": 备注}]
groups  [{"id", "name", "desc": 介绍, "enabled": 开着没有, "shared": 多人游戏里共享没有, "share": 服务器上的键或 None, "pages": [页面 Id]}]
        默认分组（Id DEFAULT_GROUP）一直在、排最前，它的成员不记：不在别的分组里的页面都归它；一个页面只在一个分组里。
        关着的分组里的页面不登记成配方类型（ActivePages，extensions/user）；分组只管登记与打包（导出、共享），编辑器照样能改里面的页面
格      None（空）或 {"id", "aux"[, "attr"], "n": 数量[, "chance": 概率][, "alts": [物品数据]][, "tag": 标签名]}
物品数据就是收藏的写法（state/bookmarks.item_data），找回走 BookmarkResolver.ResolveItem。

页面里装东西的积木按角色编号（排版里的先后）：配方的 in / out / cat 第 k 个对上同一角色的第 k 块；排版改了配方不用动，多出来的不显示。
积木的种类与属性这里不认（积木由扩展登记，可能还没登记、也可能登记它的模组没装了）：这里只规整结构，属性由用到的地方规整（BlockType.Normalize），
看不懂的键原样留着；整条不成形的丢掉（engineering.md §7-9：数据可以丢，加载不能卡）。
这些数据也会从剪贴板、服务器上别人的分组来（user_pack.py、user_share.py）：页面、配方 Id 只收字母数字与 _-、看不懂的键与积木
嵌套太深 / 太大的丢掉（_bounded）、物品的附加数据（attr）有大小上限、积木的坐标夹在页面里
"""
import copy
import time

from MEIScripts.common.classes.types.recipe import Ingredient
from MEIScripts.constants.codes import StorageConst
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from .bookmarks import item_key
from .storage import Store

CONFIG_NAME = StorageConst.UserRecipesConfigName

VERSION = 4

KEY_PAGES = "pages"
KEY_RECIPES = "recipes"
KEY_GROUPS = "groups"

DEFAULT_GROUP = "default"
""" 默认分组的 Id：一直在，成员不记（不在别的分组里的页面都归它），不能改名、删除 """
MAX_GROUPS = 256
DESC_LENGTH = 256

WIDTH_RANGE = (20, 256)
HEIGHT_RANGE = (20, 160)
""" 页面内容区（积木摆在里面）的宽、高能取多少；一行比内容区宽 16、高 20（左右留边、下面一排按钮，mei_ui/blocks/row.py）"""

DEFAULT_WIDTH = 172
DEFAULT_HEIGHT = 70

MAX_STATIONS = 16
""" 一个页面最多几个工作站 """

ROLES = ("in", "out", "cat")

FIELDS = ("energy", "time", "heat")
""" 页面能用的数值字段（配方里填数，文字积木写 {字段}、条按它画满多少）；名字与单位在 constants/texts.py 的 UserText.Fields """

MAX_PAGES = 2048
MAX_RECIPES = 32768
MAX_BLOCKS = 192
""" 一页最多几块积木（每种积木另有自己的上限，BlockType.Limit；MEI 自带的九种加起来正好 192）。
一个父控件下挂不了太多子控件（引擎结论 §54：超过 250 断言），配方页的一行、编辑器的内容区都在这个数以内 """
MAX_SLOTS = 64
""" 一条配方的 in / out / cat 各最多几格（物品格一页最多 64 个，第三方装东西的积木另算）"""
MAX_ALTS = 64
MAX_FIELDS = 8
NAME_LENGTH = 48
NOTE_LENGTH = 256
TAG_LENGTH = 64
MAX_AMOUNT = 1000000000
MAX_FIELD_VALUE = 1e15

MAX_TAG_ITEMS = 256
""" 一格写的是标签时最多展开几样（轮播用）"""

ID_LENGTH = 40
""" 页面、配方 Id 最长几个字（只收字母数字与 _-）"""
MAX_DEPTH = 16
MAX_NODES = 4096
MAX_STRING = 8192
""" 看不懂的键、积木、物品附加数据：最深几层、最多几个值、字最长多少 —— 超了整个丢掉（别人的分组、剪贴板里来的不能拿来撑爆内存、递归）"""
ATTR_NODES = 1024

LISTENER_ALL = "*"
""" 改动通知里「整张表都可能变了」（换了存储、重读）的记号 """

ERR_BAD, ERR_NAME, ERR_OUTPUT, ERR_PAGES, ERR_RECIPES = "bad", "name", "output", "pages", "recipes"
""" 存不进去的原因（SavePage / SaveRecipe 的第二个返回值）：数据不成形、页面没起名、配方没有产物、页面满了、配方满了 """
ERR_GROUPS, ERR_EMPTY = "groups", "empty"
""" 分组满了；导进来的一包里一个页面都没有 """


def _text(value, limit):  # type: (any, int) -> unicode
    """ 一律 unicode（存盘读回来的是字节串）；不是字符串、解不开给空 """
    if not isinstance(value, basestring):
        return u""
    if not isinstance(value, unicode):
        try:
            value = value.decode("utf-8")
        except UnicodeError:
            return u""
    return value.strip()[:limit]


def _ident(value):  # type: (any) -> str or None
    """ 页面、配方、字段的 Id：非空的 ASCII 字符串 """
    if not isinstance(value, basestring) or not value:
        return None
    try:
        return value.encode("ascii") if isinstance(value, unicode) else value.decode("ascii").encode("ascii")
    except UnicodeError:
        return None


def _safe_id(value):  # type: (any) -> str or None
    """ 页面、配方 Id：只收字母数字与 _-，不超过 ID_LENGTH（登记成类型 Id、配方 Id 的一部分）"""
    value = _ident(value)
    if not value or len(value) > ID_LENGTH or not all(char.isalnum() or char in "_-" for char in value):
        return None
    return value


def _bounded(value, depth=0, budget=None):  # type: (any, int, list) -> bool
    """ JSON 一样的值：没超过 MAX_DEPTH 层、MAX_NODES 个值、字没超过 MAX_STRING，也只有 dict / list / 字符串 / 数 / 布尔 / None """
    budget = budget if budget is not None else [MAX_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_DEPTH:
        return False
    if isinstance(value, dict):
        return all(isinstance(key, basestring) and len(key) <= MAX_STRING and _bounded(item, depth + 1, budget)
                   for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_bounded(item, depth + 1, budget) for item in value)
    if isinstance(value, basestring):
        return len(value) <= MAX_STRING
    return value is None or isinstance(value, (bool, int, long, float))


def _number(value):  # type: (any) -> any
    """ 有限的数（int / float），别的给 None """
    if isinstance(value, bool) or not isinstance(value, (int, long, float)):
        return None
    if value != value or abs(value) > MAX_FIELD_VALUE:
        return None
    return value


def _item(data):  # type: (any) -> dict or None
    """ 物品数据 {"id", "aux"[, "attr"]}；认不出给 None """
    if not isinstance(data, dict) or not item_key(data):
        return None
    result = {"id": data.get("id"), "aux": data.get("aux", 0)}
    attr = data.get("attr")
    if isinstance(attr, dict) and attr and _bounded(attr, budget=[ATTR_NODES]):
        result["attr"] = attr  # 附魔书、药水这类带附加数据的；太大、太深的不要（引擎拿到畸形的附加数据会怎样没验过）
    return result


def normalize_entry(entry):  # type: (any) -> dict or None
    """ 一格：认不出物品的当空格 """
    item = _item(entry)
    if item is None:
        return None
    amount = entry.get("n", 1)
    if isinstance(amount, bool) or not isinstance(amount, (int, long, float)) or amount != amount:
        amount = 1
    item["n"] = int(min(MAX_AMOUNT, max(1, amount)))
    chance = _number(entry.get("chance"))
    if chance is not None and 0 < chance < 1:
        item["chance"] = round(float(chance), 4)
    alts = [alt for alt in (_item(alt) for alt in (entry.get("alts") or ()) if isinstance(entry.get("alts"), list)) if alt]
    if alts:
        item["alts"] = alts[:MAX_ALTS]
    tag = _ident(entry.get("tag"))
    if tag:
        item["tag"] = tag[:TAG_LENGTH]
    return item


def normalize_recipe(recipe):  # type: (any) -> dict or None
    """ 一条配方：没有 Id、没有页面的给 None；别的规整过，看不懂的键原样留着 """
    if not isinstance(recipe, dict):
        return None
    recipe_id, page_id = _safe_id(recipe.get("id")), _safe_id(recipe.get("page"))
    if not recipe_id or not page_id:
        return None
    result = dict((key, value) for key, value in recipe.items() if key in RECIPE_KEYS or _bounded(value))
    result["id"], result["page"] = recipe_id, page_id
    for role in ROLES:
        slots = recipe.get(role)
        slots = slots if isinstance(slots, list) else []
        cells = [normalize_entry(cell) for cell in slots[:MAX_SLOTS]]
        while cells and cells[-1] is None:
            cells.pop()
        result[role] = cells
    fields = recipe.get("f")
    result["f"] = dict((key, value) for key, value in ((_ident(k), _number(v)) for k, v in fields.items())
                       if key and value is not None) if isinstance(fields, dict) else {}
    result["note"] = _text(recipe.get("note"), NOTE_LENGTH)
    return result


RECIPE_KEYS = ("id", "page", "in", "out", "cat", "f", "note")
PAGE_KEYS = ("id", "name", "stations", "station", "icon", "w", "h", "fields", "blocks")
""" 自己认得、会逐项规整的键；别的键原样留着，但太深、太大的丢掉 """

RENAMED_BLOCKS = {"mei:tank": "mei:slot"}
""" MEI 自带、后来删掉的积木 → 换成哪一种（读回来时换；装东西的换成装东西的，角色、位置、编号都不变，配方照样对得上）"""


def clamp_size(value, bounds, default):  # type: (any, tuple, int) -> int
    """ 内容区的宽或高：取整、夹在范围里；不是数给缺省 """
    number = _number(value)
    if number is None:
        return default
    return int(max(bounds[0], min(bounds[1], int(round(number)))))


def _migrate_v1_size(payload):  # type: (dict) -> dict
    """ v1 → v2：页面原来存行高（四档 48 / 74 / 100 / 126，内容区比它矮 4、宽一律 172），改成存内容区自己的宽、高 """
    for page in payload.get(KEY_PAGES) or ():
        if not isinstance(page, dict):
            continue
        height = _number(page.get("h"))
        page["h"] = int(height) - 4 if height is not None else DEFAULT_HEIGHT
        page.setdefault("w", DEFAULT_WIDTH)
    return payload


def _migrate_v2_stations(payload):  # type: (dict) -> dict
    """ v2 → v3：一个工作站（station）换成一列（stations），图标单独存（icon，缺省 None：用第一个工作站）"""
    for page in payload.get(KEY_PAGES) or ():
        if not isinstance(page, dict):
            continue
        station = page.pop("station", None)
        page.setdefault("stations", [station] if station else [])
        page.setdefault("icon", None)
    return payload


def _migrate_v3_groups(payload):  # type: (dict) -> dict
    """ v3 → v4：加分组表（原来的页面都在默认分组里，默认分组的成员不记，表里先空着）"""
    if not isinstance(payload.get(KEY_GROUPS), list):
        payload[KEY_GROUPS] = []
    return payload


MIGRATIONS = {1: _migrate_v1_size, 2: _migrate_v2_stations, 3: _migrate_v3_groups}
""" {旧版本号: fn(payload) -> payload}，升版时在此登记，见 storage/store.py """


def normalize_page(page):  # type: (any) -> dict or None
    """ 一个页面：没有 Id 的给 None；积木只认结构（dict 且有种类），属性留给积木自己规整 """
    if not isinstance(page, dict):
        return None
    page_id = _safe_id(page.get("id"))
    if not page_id:
        return None
    result = dict((key, value) for key, value in page.items() if key in PAGE_KEYS or _bounded(value))
    result["id"] = page_id
    result["name"] = _text(page.get("name"), NAME_LENGTH)
    stations, seen = [], set()
    raw_stations = page.get("stations") if isinstance(page.get("stations"), list) else [page.get("station")]
    for data in raw_stations:
        data = _item(data)
        if data is not None and item_key(data) not in seen and len(stations) < MAX_STATIONS:
            seen.add(item_key(data))
            stations.append(data)
    result.pop("station", None)
    result["stations"] = stations
    result["icon"] = _item(page.get("icon"))
    result["w"] = clamp_size(page.get("w"), WIDTH_RANGE, DEFAULT_WIDTH)
    result["h"] = clamp_size(page.get("h"), HEIGHT_RANGE, DEFAULT_HEIGHT)
    fields = []
    for field in (page.get("fields") if isinstance(page.get("fields"), list) else ()):
        field = _ident(field)
        if field and field not in fields:
            fields.append(field)
    result["fields"] = fields[:MAX_FIELDS]
    blocks = page.get("blocks") if isinstance(page.get("blocks"), list) else []
    result["blocks"] = []
    for block in blocks[:MAX_BLOCKS]:
        if isinstance(block, dict) and _ident(block.get("t")) and _bounded(block):
            block = dict(block)
            block["t"] = RENAMED_BLOCKS.get(block["t"], block["t"])
            for axis, limit in (("x", result["w"]), ("y", result["h"])):
                if _number(block.get(axis)) is not None:
                    block[axis] = min(max(block[axis], 0), limit)  # 夹在页面里：别人的分组摆到页面外面会盖住配方页别的地方
            result["blocks"].append(block)
    return result


def normalize_group(group):  # type: (any) -> dict or None
    """ 一个分组：没有 Id 的给 None；成员去重（是不是真有这个页面由 UserRecipeManager 读进来时核对）；看不懂的键原样留着 """
    if not isinstance(group, dict):
        return None
    group_id = _ident(group.get("id"))
    if not group_id:
        return None
    result = dict(group)
    result["id"] = group_id
    result["name"] = _text(group.get("name"), NAME_LENGTH) if group_id != DEFAULT_GROUP else u""
    result["desc"] = _text(group.get("desc"), DESC_LENGTH)
    result["enabled"] = group.get("enabled") is not False
    result["shared"] = group.get("shared") is True
    result["share"] = _ident(group.get("share"))
    pages = []
    if group_id != DEFAULT_GROUP and isinstance(group.get("pages"), list):
        for page_id in group.get("pages"):
            page_id = _ident(page_id)
            if page_id and page_id not in pages:
                pages.append(page_id)
    result["pages"] = pages
    return result


def default_group():  # type: () -> dict
    return normalize_group({"id": DEFAULT_GROUP})


def page_icon(page):  # type: (dict) -> dict or None
    """ 页面（类型）的图标：单独设过的，没设用第一个工作站，都没有给 None（类型那边用铅笔）"""
    stations = page.get("stations") or ()
    return page.get("icon") or (stations[0] if stations else None)


def holder_index(blocks, holds):  # type: (list, callable) -> list
    """
    装东西的积木的编号：[(积木在排版里的下标, 角色, 这一角色的第几个)]，按排版里的先后。
    holds(积木 dict) 说这一块装不装东西（看它的种类，BlockType.Holds）
    """
    counters, result = {}, []
    for index, block in enumerate(blocks or ()):
        if not holds(block):
            continue
        role = block.get("role") if block.get("role") in ROLES else ROLES[0]
        number = counters.get(role, 0)
        counters[role] = number + 1
        result.append((index, role, number))
    return result


def make_ingredient(entry, resolve, tag_items):  # type: (any, callable, callable) -> Ingredient
    """
    一格 → MEI 的 Ingredient：主物品 + 候选 + 标签展开（去重），数量、概率、标签名照记的；一样都找不回的是空格（Ingredient([])）。
    resolve(物品数据) 找回物品（BookmarkResolver.ResolveItem），tag_items(标签名) 给带这个标签的物品（ItemManager.ResolveTag）
    """
    if not isinstance(entry, dict):
        return Ingredient([])
    stacks, seen = [], set()

    def add(item):
        if item is None:
            return
        stack = item.stack(1)
        key = stack.get_key()
        if key not in seen:
            seen.add(key)
            stacks.append(stack)
    add(resolve(entry))
    for alt in entry.get("alts") or ():
        add(resolve(alt))
    tag = entry.get("tag") or None
    if tag:
        for item in (tag_items(tag) or ())[:MAX_TAG_ITEMS]:
            add(item)
    if not stacks:
        return Ingredient([])
    return Ingredient(stacks, int(entry.get("n", 1) or 1), tag_id=tag, chance=float(entry.get("chance", 1.0) or 1.0))


def id_maker(prefix, taken):  # type: (str, set) -> callable
    """
    一次要起很多个新 Id 时用（导入一包）：接着上一个往后数，不像 new_id 那样每次从此刻的毫秒数重新试 —— 同一毫秒里起几千个会越试越慢。
    起出来的记进 taken
    """
    state = [int(time.time() * 1000)]

    def make():  # type: () -> str
        while True:
            candidate = "{}{:x}".format(prefix, state[0])
            state[0] += 1
            if candidate not in taken:
                taken.add(candidate)
                return candidate
    return make


def new_id(prefix, taken):  # type: (str, any) -> str
    """ 新的 Id：前缀 + 毫秒时间的十六进制（同一毫秒里再往后挪），不和 taken 里的撞 """
    stamp = int(time.time() * 1000)
    while True:
        candidate = "{}{:x}".format(prefix, stamp)
        if candidate not in taken:
            return candidate
        stamp += 1


class __UserRecipeManager(object):  # noqa
    """ 玩家自制配方的门面，构造期不碰引擎 """

    def __init__(self):
        self._store = None
        self._pages = None  # type: list or None
        self._recipes = None  # type: list or None
        self._groups = None  # type: list or None
        self._revision = 0  # type: int
        self._listeners = []  # type: list

    def _get_store(self):  # type: () -> Store
        if self._store is None:
            # 延迟到首次使用才 import backend，它顶层拉客户端引擎
            from .storage.backend import ConfigBackend, EngineScheduler
            self._store = Store(
                ConfigBackend(), CONFIG_NAME, is_global=True,
                version=VERSION, migrations=MIGRATIONS,
                scheduler=EngineScheduler(), compact=True,
            )
        return self._store

    def SetStore(self, store):
        """ 测试注入点，替换为带假后端的 Store 并丢弃读过的表 """
        self._store = store
        self._pages = None
        self._recipes = None
        self._groups = None
        self._revision += 1
        self._notify(set([LISTENER_ALL]))

    def _load(self):
        if self._pages is not None:
            return
        store = self._get_store()
        self._pages = self._read(store.Get(KEY_PAGES), normalize_page, KEY_PAGES)
        self._recipes = self._read(store.Get(KEY_RECIPES), normalize_recipe, KEY_RECIPES)
        self._groups = self._read_groups(store.Get(KEY_GROUPS))

    def _read_groups(self, value):  # type: (any) -> list
        """ 分组表：默认分组一直在、排最前；成员只认真有的页面，一个页面只算在第一个认它的分组里 """
        groups = self._read(value, normalize_group, KEY_GROUPS) if value is not None else []
        default = [group for group in groups if group["id"] == DEFAULT_GROUP]
        result = [default[0] if default else default_group()]
        alive = set(page["id"] for page in self._pages)
        claimed = set()
        for group in groups:
            if group["id"] == DEFAULT_GROUP:
                continue
            if len(result) >= MAX_GROUPS:
                logger.warn("[MEI/user] 分组超过 {} 个，多出来的丢掉（页面回到默认分组）".format(MAX_GROUPS))
                break
            group["pages"] = [page_id for page_id in group["pages"] if page_id in alive and page_id not in claimed]
            claimed.update(group["pages"])
            result.append(group)
        return result

    @staticmethod
    def _read(value, normalize, name):  # type: (any, callable, str) -> list
        if value is None:
            return []
        if not isinstance(value, list):
            logger.warn("[MEI/user] 自制配方的 {} 不是列表({}), 本轮按空处理".format(name, type(value).__name__))
            return []
        result, seen, dropped = [], set(), 0
        for raw in value:
            entry = normalize(raw)
            if entry is None or entry["id"] in seen:
                dropped += 1
                continue
            seen.add(entry["id"])
            result.append(entry)
        if dropped:
            logger.warn("[MEI/user] 自制配方的 {} 里有 {} 条不成形、丢掉".format(name, dropped))
        return result

    def _persist(self, pages=None, keys=(KEY_PAGES, KEY_RECIPES, KEY_GROUPS)):  # type: (set, tuple) -> None
        """
        写回存储、版本加一、通知听众（pages：这些页面的登记可能变了；None 是整张表都可能变了；空集合是只有分组的名字、介绍这类变了）。
        keys：动了哪几张表。表是自己持有的那一份，直接 Put（不复制、不比较 —— 几万条配方每改一条都深拷贝一遍、再整个比一遍太慢），
        落盘时不排序（Store compact）
        """
        store = self._get_store()
        tables = {KEY_PAGES: self._pages, KEY_RECIPES: self._recipes, KEY_GROUPS: self._groups}
        for key in keys:
            store.Put(key, tables[key])
        self._revision += 1
        self._notify(set([LISTENER_ALL]) if pages is None else pages)

    def _notify(self, pages):  # type: (set) -> None
        for listener in list(self._listeners):
            try:
                listener(set(pages))
            except Exception as e:  # noqa  一个听众坏了不拖垮保存
                logger.error("[MEI/user] 自制配方的改动通知出错: {}".format(error_text(e)))

    # 读
# ======================================================================================================================
    def Revision(self):  # type: () -> int
        """ 每改一次加一 """
        return self._revision

    def Pages(self):  # type: () -> list
        """ 全部页面（按建的先后）。**只读**：要改拿 PageCopy 改完 SavePage """
        self._load()
        return self._pages

    def Page(self, page_id):  # type: (str) -> dict or None
        """ 只读 """
        for page in self.Pages():
            if page["id"] == page_id:
                return page
        return None

    def PageCopy(self, page_id):  # type: (str) -> dict or None
        page = self.Page(page_id)
        return copy.deepcopy(page) if page is not None else None

    def Recipes(self, page_id=None):  # type: (str) -> list
        """ 全部配方，或者一个页面的（按建的先后）。**只读** """
        self._load()
        if page_id is None:
            return self._recipes
        return [recipe for recipe in self._recipes if recipe["page"] == page_id]

    def Recipe(self, recipe_id):  # type: (str) -> dict or None
        """ 只读 """
        self._load()
        for recipe in self._recipes:
            if recipe["id"] == recipe_id:
                return recipe
        return None

    def RecipeCopy(self, recipe_id):  # type: (str) -> dict or None
        recipe = self.Recipe(recipe_id)
        return copy.deepcopy(recipe) if recipe is not None else None

    def Counts(self):  # type: () -> tuple
        """ (页面数, 配方数) """
        self._load()
        return len(self._pages), len(self._recipes)

    # 写
# ======================================================================================================================
    def NewPageId(self):  # type: () -> str
        return new_id("p", set(page["id"] for page in self.Pages()))

    def NewRecipeId(self):  # type: () -> str
        self._load()
        return new_id("r", set(recipe["id"] for recipe in self._recipes))

    def SavePage(self, page, group_id=None):  # type: (dict, str) -> tuple
        """
        存一个页面（没有 Id、Id 不在表里的是新的）：返回 (页面 Id, 错误)，错误是 ERR_*、成了是 None。
        group_id：新页面放进哪个分组（不给、或者分组不在了是默认分组）；改旧的页面不动它在哪个分组
        """
        self._load()
        if not isinstance(page, dict):
            return None, ERR_BAD
        page = dict(page)
        if not _ident(page.get("id")):
            page["id"] = self.NewPageId()
        entry = normalize_page(page)
        if entry is None:
            return None, ERR_BAD
        if not entry["name"]:
            return None, ERR_NAME
        index = self._index(self._pages, entry["id"])
        if index is None:
            if len(self._pages) >= MAX_PAGES:
                return None, ERR_PAGES
            self._pages.append(entry)
            group = self.Group(group_id) if group_id and group_id != DEFAULT_GROUP else None
            if group is not None:
                group["pages"] = group["pages"] + [entry["id"]]
        else:
            self._pages[index] = entry
        self._persist(set([entry["id"]]))
        return entry["id"], None

    def DeletePage(self, page_id):  # type: (str) -> int
        """ 删一个页面连同它的配方；返回删了几条配方，页面不在给 -1 """
        self._load()
        index = self._index(self._pages, page_id)
        if index is None:
            return -1
        del self._pages[index]
        before = len(self._recipes)
        self._recipes = [recipe for recipe in self._recipes if recipe["page"] != page_id]
        for group in self._groups:
            if page_id in group["pages"]:
                group["pages"] = [entry for entry in group["pages"] if entry != page_id]
        self._persist(set([page_id]))
        return before - len(self._recipes)

    def SaveRecipe(self, recipe):  # type: (dict) -> tuple
        """ 存一条配方（没有 Id 的是新的）：返回 (配方 Id, 错误) """
        self._load()
        if not isinstance(recipe, dict):
            return None, ERR_BAD
        recipe = dict(recipe)
        if not _ident(recipe.get("id")):
            recipe["id"] = self.NewRecipeId()
        entry = normalize_recipe(recipe)
        if entry is None or self.Page(entry["page"]) is None:
            return None, ERR_BAD
        if not any(cell is not None for cell in entry["out"]):
            return None, ERR_OUTPUT
        index = self._index(self._recipes, entry["id"])
        touched = set([entry["page"]])
        if index is None:
            if len(self._recipes) >= MAX_RECIPES:
                return None, ERR_RECIPES
            self._recipes.append(entry)
        else:
            touched.add(self._recipes[index]["page"])
            self._recipes[index] = entry
        self._persist(touched)
        return entry["id"], None

    def DeleteRecipe(self, recipe_id):  # type: (str) -> bool
        self._load()
        index = self._index(self._recipes, recipe_id)
        if index is None:
            return False
        page_id = self._recipes[index]["page"]
        del self._recipes[index]
        self._persist(set([page_id]))
        return True

    @staticmethod
    def _index(entries, entry_id):  # type: (list, str) -> int or None
        for index, entry in enumerate(entries):
            if entry["id"] == entry_id:
                return index
        return None

    # 分组（docs/architecture/user_recipes.md §22）
# ======================================================================================================================
    def Groups(self):  # type: () -> list
        """ 全部分组（默认分组在最前，别的按建的先后）。**只读**：改走下面几个 """
        self._load()
        return self._groups

    def Group(self, group_id):  # type: (str) -> dict or None
        """ 只读 """
        for group in self.Groups():
            if group["id"] == group_id:
                return group
        return None

    def GroupOf(self, page_id):  # type: (str) -> str
        """ 页面在哪个分组（不在别的分组里的都在默认分组）"""
        for group in self.Groups():
            if page_id in group["pages"]:
                return group["id"]
        return DEFAULT_GROUP

    def _claimed(self):  # type: () -> set
        claimed = set()
        for group in self._groups:
            claimed.update(group["pages"])
        return claimed

    def GroupPages(self, group_id):  # type: (str) -> list
        """ 一个分组里的页面（只读）：默认分组按建的先后，别的按移进来的先后 """
        self._load()
        if group_id == DEFAULT_GROUP:
            claimed = self._claimed()
            return [page for page in self._pages if page["id"] not in claimed]
        group = self.Group(group_id)
        if group is None:
            return []
        by_id = dict((page["id"], page) for page in self._pages)
        return [by_id[page_id] for page_id in group["pages"] if page_id in by_id]

    def GroupCounts(self, group_id):  # type: (str) -> tuple
        """ (页面数, 配方数) """
        ids = set(page["id"] for page in self.GroupPages(group_id))
        return len(ids), len([recipe for recipe in self._recipes if recipe["page"] in ids])

    def ActivePages(self):  # type: () -> list
        """ 开着的分组里的页面（按建的先后）—— 只有它们登记成配方类型 """
        self._load()
        off, default_on = set(), True
        for group in self._groups:
            if group["id"] == DEFAULT_GROUP:
                default_on = group["enabled"]
            elif not group["enabled"]:
                off.update(group["pages"])
        claimed = self._claimed() if not default_on else set()
        return [page for page in self._pages if page["id"] not in off and (default_on or page["id"] in claimed)]

    def IsPageActive(self, page_id):  # type: (str) -> bool
        group = self.Group(self.GroupOf(page_id))
        return group is None or group["enabled"]

    def NewGroupId(self):  # type: () -> str
        return new_id("g", set(group["id"] for group in self.Groups()))

    def CreateGroup(self, name, desc=u""):  # type: (any, any) -> tuple
        """ 建一个空分组（开着、不共享）：返回 (分组 Id, 错误) """
        self._load()
        if len(self._groups) >= MAX_GROUPS:
            return None, ERR_GROUPS
        group = normalize_group({"id": self.NewGroupId(), "name": name, "desc": desc, "pages": []})
        self._groups.append(group)
        self._persist(set(), keys=(KEY_GROUPS,))
        return group["id"], None

    def UpdateGroup(self, group_id, **fields):  # type: (str, ...) -> bool
        """
        改分组的 name / desc / enabled / shared / share（默认分组不能改名）；返回改没改。
        开关变了这个分组的页面要重新登记（通知里带上它们），别的只是版本加一
        """
        group = self.Group(group_id)
        if group is None:
            return False
        updated = dict(group)
        for key in ("name", "desc", "enabled", "shared", "share"):
            if key in fields:
                updated[key] = fields[key]
        updated = normalize_group(updated)
        if updated == group:
            return False
        self._groups[self._index(self._groups, group_id)] = updated
        pages = set(page["id"] for page in self.GroupPages(group_id)) if updated["enabled"] != group["enabled"] else set()
        self._persist(pages, keys=(KEY_GROUPS,))
        return True

    def MovePage(self, page_id, group_id):  # type: (str, str) -> bool
        """ 把一个页面移到另一个分组（移到默认分组 = 从原来的分组里拿掉）；返回动没动 """
        self._load()
        if self.Page(page_id) is None or self.Group(group_id) is None or self.GroupOf(page_id) == group_id:
            return False
        for group in self._groups:
            if page_id in group["pages"]:
                group["pages"] = [entry for entry in group["pages"] if entry != page_id]
        if group_id != DEFAULT_GROUP:
            target = self.Group(group_id)
            target["pages"] = target["pages"] + [page_id]
        self._persist(set([page_id]), keys=(KEY_GROUPS,))
        return True

    def DisbandGroup(self, group_id):  # type: (str) -> int
        """ 解散一个分组：页面回到默认分组；返回回去了几个页面，默认分组、不在的分组给 -1 """
        self._load()
        index = self._index(self._groups, group_id)
        if group_id == DEFAULT_GROUP or index is None:
            return -1
        pages = list(self._groups[index]["pages"])
        del self._groups[index]
        self._persist(set(pages), keys=(KEY_GROUPS,))
        return len(pages)

    def DeleteGroup(self, group_id):  # type: (str) -> tuple or None
        """ 删一个分组连同它的页面与配方：返回 (删了几个页面, 几条配方)；默认分组、不在的分组给 None """
        self._load()
        index = self._index(self._groups, group_id)
        if group_id == DEFAULT_GROUP or index is None:
            return None
        pages = set(self._groups[index]["pages"])
        del self._groups[index]
        self._pages = [page for page in self._pages if page["id"] not in pages]
        before = len(self._recipes)
        self._recipes = [recipe for recipe in self._recipes if recipe["page"] not in pages]
        self._persist(pages)
        return len(pages), before - len(self._recipes)

    def ExportGroup(self, group_id):  # type: (str) -> dict or None
        """ 一个分组打成一包（拷贝）：{"name", "desc", "pages", "recipes"}；分组不在给 None。默认分组的名字是空的，调用方写显示的名字 """
        group = self.Group(group_id)
        if group is None:
            return None
        pages = self.GroupPages(group_id)
        ids = set(page["id"] for page in pages)
        return {"name": group["name"], "desc": group["desc"], "pages": copy.deepcopy(pages),
                "recipes": copy.deepcopy([recipe for recipe in self._recipes if recipe["page"] in ids])}

    def ImportGroup(self, pack, name=None):  # type: (dict, any) -> tuple
        """
        一包（ExportGroup 的样子，剪贴板导进来的）→ 一个新分组：页面、配方都换新 Id（和已有的同一份也导成新的，原来的不动）。
        整包放不下（分组、页面、配方满了）一样都不导。返回 (分组 Id, 错误)
        """
        self._load()
        pack = pack if isinstance(pack, dict) else {}
        raw_pages = pack.get("pages") if isinstance(pack.get("pages"), list) else []
        raw_recipes = pack.get("recipes") if isinstance(pack.get("recipes"), list) else []
        next_page = id_maker("p", set(page["id"] for page in self._pages))
        next_recipe = id_maker("r", set(recipe["id"] for recipe in self._recipes))
        remap, fresh_pages = {}, []
        for page in (normalize_page(raw) for raw in raw_pages[:MAX_PAGES]):
            if page is None or page["id"] in remap:
                continue
            fresh = dict(page)
            fresh["id"] = remap[page["id"]] = next_page()
            fresh_pages.append(fresh)
        fresh_recipes = []
        for recipe in (normalize_recipe(raw) for raw in raw_recipes[:MAX_RECIPES]):
            if recipe is None or recipe["page"] not in remap:
                continue
            fresh = dict(recipe)
            fresh["id"] = next_recipe()
            fresh["page"] = remap[recipe["page"]]
            fresh_recipes.append(fresh)
        if not fresh_pages:
            return None, ERR_EMPTY
        if len(self._groups) >= MAX_GROUPS:
            return None, ERR_GROUPS
        if len(self._pages) + len(fresh_pages) > MAX_PAGES:
            return None, ERR_PAGES
        if len(self._recipes) + len(fresh_recipes) > MAX_RECIPES:
            return None, ERR_RECIPES
        group = normalize_group({"id": self.NewGroupId(), "name": name if name is not None else pack.get("name"),
                                 "desc": pack.get("desc"), "pages": [page["id"] for page in fresh_pages]})
        self._pages.extend(fresh_pages)
        self._recipes.extend(fresh_recipes)
        self._groups.append(group)
        self._persist(set(page["id"] for page in fresh_pages))
        return group["id"], None

    # 改动通知
# ======================================================================================================================
    def AddListener(self, listener):  # type: (callable) -> None
        """ listener(页面 Id 的集合)：这些页面（或它们的配方）变了；集合里有 LISTENER_ALL 是整张表都可能变了 """
        if callable(listener) and listener not in self._listeners:
            self._listeners.append(listener)

    def RemoveListener(self, listener):  # type: (callable) -> None
        if listener in self._listeners:
            self._listeners.remove(listener)

    # 存储
# ======================================================================================================================
    def Flush(self, force=False):
        return self._get_store().Flush(force)

    def IsDegraded(self):
        return self._get_store().IsDegraded()


UserRecipeManager = __UserRecipeManager()
