# coding=utf-8

# ----------------------------------------------------------------------
#  filters.py is part of MoreEnoughItems.
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
物品栏的筛选与排序：登记处与计算，零引擎依赖（界面的几种排版候选在 docs/design/item_filter.html）。

- **筛选**：每一项是「这样物品算不算」的判断，只看物品注册时已经缓存的基本信息（Item.Info，不再问引擎）。
  选了几项就要都满足；和搜索叠加 —— 先搜、再筛。扩展可以登记自己的：原版扩展登记「能燃烧」，用它的燃料表
  （引擎给方块类燃料的燃烧时长是 0，只看 Info 会漏掉木头这些，CLAUDE.md 引擎结论 §11）。
- **加法的筛选**（`Additive`，内置的「隐藏物品」）：选了不是把表筛小，而是把平时不显示的物品里它认的那些加进来；
  别的筛选照样再筛一遍。候选要连藏着的物品一起给（`Apply` 的 shown 说哪些是平时显示的）。
- **排序**：一种属性，升序或降序；不选就照原来的顺序（物品表按 ID、搜索按相关度）。拿不到值的排在最后，同值保持原顺序。
- 判断或取值抛异常的那一样当「不算」/「拿不到值」，不能让整张表出不来。
"""
from collections import OrderedDict

from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, to_unicode

ASC = "asc"
DESC = "desc"

HIDDEN = "hidden"
""" 内置的加法筛选「隐藏物品」的 Id """


class ItemFilter(object):
    """
    一项筛选：Test(item) 为真就留下。Additive 的一项是加法：选了不是把表筛小，而是把平时不显示的物品里 Test 为真的加进来
    """

    __slots__ = ("Id", "NameKey", "Test", "Order", "Additive")

    def __init__(self, filter_id, name_key, test, order=0, additive=False):
        # type: (str, str, callable, int, bool) -> None
        self.Id = filter_id  # type: str
        self.NameKey = name_key  # type: str  # 显示名的本地化键
        self.Test = test  # type: callable
        self.Order = order  # type: int  # 菜单里的先后，小的在前
        self.Additive = bool(additive)  # type: bool


class ItemSort(object):
    """ 一种排序：Key(item) 给可比的值，拿不到给 None（排最后）"""

    __slots__ = ("Id", "NameKey", "Key", "Order")

    def __init__(self, sort_id, name_key, key, order=0):  # type: (str, str, callable, int) -> None
        self.Id = sort_id  # type: str
        self.NameKey = name_key  # type: str
        self.Key = key  # type: callable
        self.Order = order  # type: int


def info_of(item, field):  # type: (any, str) -> any
    """ 物品基本信息里的一项；Info 取不到给 None """
    try:
        return getattr(item.Info, field, None)
    except Exception:  # noqa  惰性字段取不到
        return None


def positive(field):  # type: (str) -> callable
    """ 筛选：这一项大于 0 """
    def test(item):
        value = info_of(item, field)
        return isinstance(value, (int, long, float)) and not isinstance(value, bool) and value > 0
    return test


def number(field):  # type: (str) -> callable
    """ 排序：这一项的数（不是数给 None）"""
    def key(item):
        value = info_of(item, field)
        return value if isinstance(value, (int, long, float)) and not isinstance(value, bool) else None
    return key


def _enchanted(item):  # type: (any) -> bool
    """ 带附魔（EnchantData / ModEnchantData），或 userData 里存着附魔 —— 附魔书的附魔写在 userData 的 ench 里，IsEnchanted 看不到 """
    if getattr(item, "IsEnchanted", False):
        return True
    user_data = getattr(getattr(item, "Attr", None), "UserData", None)
    return isinstance(user_data, dict) and bool(user_data.get("ench"))


def _name(item):  # type: (any) -> unicode or None
    """ 排序用的名字，一律 unicode：引擎给的是 unicode、扩展自带的 ItemInfo 常是 utf-8 的 str —— py2 里两种非 ASCII 的比大小会抛 """
    name = info_of(item, "ItemName")
    return to_unicode(name) if name else None


def _hidden(item):  # type: (any) -> bool
    """ 藏起来的物品（引擎的隐藏表、扩展 SetHidden / SetPlainHidden 藏的）"""
    from .items import ItemManager  # 用到才 import：本模块零引擎依赖，registry/items.py 顶层拉引擎
    return ItemManager.IsHidden(item)


def _modded(item):  # type: (any) -> bool
    item_id = getattr(item, "ItemId", "") or ""
    return ":" in item_id and not item_id.startswith("minecraft:")


BUILTIN_FILTERS = (
    ItemFilter("armor", "mei.filter.armor", positive("ArmorDefense"), 10),
    ItemFilter("weapon", "mei.filter.weapon", positive("WeaponDamage"), 20),
    ItemFilter("food", "mei.filter.food", positive("FoodNutrition"), 30),
    ItemFilter("durable", "mei.filter.durable", positive("MaxDurability"), 40),
    ItemFilter("enchantable", "mei.filter.enchantable", positive("EnchantSlotType"), 50),
    ItemFilter("enchanted", "mei.filter.enchanted", _enchanted, 60),
    ItemFilter("unstackable", "mei.filter.unstackable", lambda item: info_of(item, "MaxStackSize") == 1, 70),
    ItemFilter("modded", "mei.filter.modded", _modded, 80),
    ItemFilter(HIDDEN, "mei.filter.hidden", _hidden, 1000, additive=True),
)
"""
内置的筛选（看 Item.Info）。弓、弩的攻击力，马铠的护甲值，蛋糕的营养值引擎都给 0，这几样筛不出来（引擎结论 §11）。
「隐藏物品」是加法、排在最后（扩展登记的缺省 90，也在它前面）
"""

BUILTIN_SORTS = (
    ItemSort("name", "mei.sort.name", _name, 10),
    ItemSort("id", "mei.sort.id", lambda item: getattr(item, "ItemId", None), 20),
    ItemSort("damage", "mei.sort.damage", number("WeaponDamage"), 30),
    ItemSort("armor", "mei.sort.armor", number("ArmorDefense"), 40),
    ItemSort("durability", "mei.sort.durability", number("MaxDurability"), 50),
    ItemSort("food", "mei.sort.food", number("FoodNutrition"), 60),
    ItemSort("stack", "mei.sort.stack", number("MaxStackSize"), 70),
    ItemSort("tier", "mei.sort.tier", number("ItemTierLevel"), 80),
)


class __ItemFilters(object):  # noqa
    """ 筛选与排序的登记处 + 计算 """

    def __init__(self):
        self._filters = OrderedDict()  # type: OrderedDict
        self._sorts = OrderedDict()  # type: OrderedDict
        self._warned = set()  # type: set
        self.Reset()

    def Reset(self):
        """ 回到只有内置的那几项（重进世界时扩展重新登记）"""
        self._filters = OrderedDict((spec.Id, spec) for spec in BUILTIN_FILTERS)
        self._sorts = OrderedDict((spec.Id, spec) for spec in BUILTIN_SORTS)

    # 登记
# ======================================================================================================================
    def RegisterFilter(self, spec):  # type: (ItemFilter) -> bool
        """ 登记一项筛选；Id 重复的不收（不能覆盖别人的）"""
        if not isinstance(spec, ItemFilter) or not spec.Id or spec.Id in self._filters or not callable(spec.Test):
            return False
        self._filters[spec.Id] = spec
        return True

    def UnregisterFilter(self, filter_id):  # type: (str) -> bool
        return self._filters.pop(filter_id, None) is not None

    def AddFilter(self, filter_id, name, test, order=90, additive=False):
        # type: (str, str, callable, int, bool) -> bool
        """
        加一项筛选（RegisterFilter 的简便写法）：name 是名字的本地化键，也可以直接写字（键查不到就照写），
        test(item) -> bool 说这样物品算不算；order 是菜单里的先后（内置的是 10 ~ 80，「隐藏物品」1000）。
        additive 为真是加法：选了把平时不显示的物品里 test 为真的加进来。Id 重复不收
        """
        return self.RegisterFilter(ItemFilter(filter_id, name, test, order, additive))

    def RegisterSort(self, spec):  # type: (ItemSort) -> bool
        if not isinstance(spec, ItemSort) or not spec.Id or spec.Id in self._sorts or not callable(spec.Key):
            return False
        self._sorts[spec.Id] = spec
        return True

    def UnregisterSort(self, sort_id):  # type: (str) -> bool
        return self._sorts.pop(sort_id, None) is not None

    def AddSort(self, sort_id, name, key, order=90):  # type: (str, str, callable, int) -> bool
        """ 加一种排序（RegisterSort 的简便写法）：key(item) 给可比较的值，没有这一项给 None（排在最后）"""
        return self.RegisterSort(ItemSort(sort_id, name, key, order))

    def ListFilters(self):  # type: () -> list
        """ 菜单里的先后：按 Order，同序按登记的先后 """
        return sorted(self._filters.values(), key=lambda spec: spec.Order)

    def ListSorts(self):  # type: () -> list
        return sorted(self._sorts.values(), key=lambda spec: spec.Order)

    # 计算
# ======================================================================================================================
    def HasAdditions(self, filter_ids):  # type: (any) -> bool
        """ 选了的里有没有加法的 —— 有的话候选要连平时不显示的物品一起给 """
        return any(self._filters[filter_id].Additive for filter_id in filter_ids or () if filter_id in self._filters)

    def Apply(self, items, filter_ids=(), sort=None, shown=None):  # type: (list, any, any, callable or None) -> list
        """
        先加、再筛、再排；什么都没选给原表的副本。
        - 加：选了加法的筛选时，候选连平时不显示的一起给（HasAdditions），shown(item) 说哪样是平时就显示的；
          平时不显示的只留下有一项加法认的。没选加法的筛选时候选里本来就没有它们，不逐个问 shown（每次重排都是整张表）；
        - 筛：别的选了的都要满足（登记表里没有的忽略）；
        - 排：sort 是 (排序 Id, ASC / DESC)，None 不排
        """
        selected = [self._filters[filter_id] for filter_id in filter_ids or () if filter_id in self._filters]
        adds = [spec.Test for spec in selected if spec.Additive]
        tests = [spec.Test for spec in selected if not spec.Additive]
        result = list(items)
        if adds and shown is not None:
            result = [item for item in result
                      if self.__Pass(shown, item) or any(self.__Pass(add, item) for add in adds)]
        if tests:
            result = [item for item in result if all(self.__Pass(test, item) for test in tests)]
        spec = self._sorts.get(sort[0]) if sort else None
        if spec is None:
            return result
        descending = sort[1] == DESC
        keyed = [(self.__Key(spec, item), index, item) for index, item in enumerate(result)]
        present = [entry for entry in keyed if entry[0] is not None]
        missing = [entry for entry in keyed if entry[0] is None]
        # 同值保持原顺序：降序时按 (值, -下标) 倒过来排
        try:
            present.sort(key=lambda entry: (entry[0], -entry[1] if descending else entry[1]), reverse=descending)
        except Exception as e:  # noqa  值的类型对不上（扩展的排序一边给数一边给字）：照原来的顺序，不能让物品栏出不来
            self.__Warn(spec, e)
            return result
        return [entry[2] for entry in present + missing]

    def __Pass(self, test, item):  # type: (callable, any) -> bool
        try:
            return bool(test(item))
        except Exception as e:  # noqa  一样物品判不了只当它不算
            self.__Warn(test, e)
            return False

    def __Key(self, spec, item):  # type: (ItemSort, any) -> any
        try:
            return spec.Key(item)
        except Exception as e:  # noqa
            self.__Warn(spec, e)
            return None

    def __Warn(self, what, error):
        marker = id(what)
        if marker not in self._warned:
            self._warned.add(marker)
            logger.error("[MEI/filter] 筛选 / 排序 {} 出错（只记第一次）: {}".format(
                getattr(what, "Id", getattr(what, "__name__", what)), error_text(error)))


ItemFilters = __ItemFilters()
