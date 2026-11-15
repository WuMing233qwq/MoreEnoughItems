# coding=utf-8

# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
创造栏里有、物品表里没有的物品。物品表按 id 注册、每个 id 只有 aux 0（RegItemFromIdList），这两类要另外加：
  · 带附加值的（药水、药箭、床、山羊角……）—— table.py，从游戏的创造栏目录生成；
  · 引擎自己往创造栏加的带 userData 的几族（附魔书、烟花火箭、烟火之星、旗帜）—— families.py，手写；
    附魔书全照引擎给的附魔信息出（engine_enchants：原版与模组的附魔都有，不记附魔的表）。
物品栏的分组也在这里（item_groups）：创造栏的物品组（table.GROUPS，生成的）、那几族各一组（families.GROUPS）、
MEI 补的同类组（groups.EXTRA：锭、粗矿……，手写）。
运行时读不到原版包里的文件，所以表是开发期生成、随 MEI 发的；换游戏版本时重跑 debug/scripts/gen_creative_table.py --emit，
它顺带提醒手写的那几族要不要跟着改（docs/architecture/item_model.md §9）
"""
from MEIScripts.api.facades.types import ItemAttr, ItemSpec

from . import families, groups, table

GAME_VERSION = table.GAME_VERSION
""" 表是按哪个游戏版本生成的（开局的汇总日志里写它）"""


class Plan(object):
    """ build 的结果：要加的物品、要从物品栏藏起来的键 """

    __slots__ = ("Specs", "Hide", "HidePlain", "Unknown", "Books", "ModBooks", "SkippedEnchants")

    def __init__(self):
        self.Specs = []  # type: list  # [ItemSpec]，照创造栏的顺序
        self.Hide = []  # type: list  # [(物品 id, aux)]：整个键藏起来（ItemManager.SetHidden）
        self.HidePlain = []  # type: list  # [(物品 id, aux)]：只藏原件，同一个键下带 userData 的照常显示（SetPlainHidden）
        self.Unknown = 0  # type: int  # 引擎不认识、跳过的个数
        self.Books = 0  # type: int  # 附魔书几本
        self.ModBooks = 0  # type: int  # 其中模组附魔的几本
        self.SkippedEnchants = []  # type: list  # 排不出 id 的附魔名（families.split_enchants，这几种附魔书没收）


def build(lookup, load_info, enchants=None):  # type: (callable, callable, list or None) -> Plan
    """
    lookup(物品 id) -> bool：物品表里有没有这个 id；load_info(物品 id, aux) -> ItemInfo 或 None（引擎不认识这个 id / aux）。
    enchants：引擎给的附魔信息（engine_enchants()，开局只问一次），附魔书照它出；没给就没有附魔书（原件照旧留着）。
    引擎不认识的跳过 —— 表比游戏新、或这个版本里没有这个 aux，版本对不上也不出错。
    同一个 (id, aux) 只问一次引擎（附魔书都是 aux 0），问到的信息交给 ItemSpec，注册时就不再问第二次。
    目录里只有带附加值那一样的物品，加上了才藏 aux 0 那份；带 userData 的一族加上了才藏原件 —— 加不上的话原件照旧留着
    """
    plan = Plan()
    plan.SkippedEnchants = families.split_enchants(enchants)[2]
    infos = {}
    handed = set()

    def info_of(item_id, aux):
        key = (item_id, aux)
        if key not in infos:
            info = None
            if lookup(item_id):
                try:
                    info = load_info(item_id, aux)
                except Exception:  # noqa  问不出来就当引擎不认识
                    info = None
            infos[key] = info
        info = infos[key]
        if info is None:
            return None
        if key in handed:
            return info.copy()  # 同一个 (id, aux) 的几样各拿一份
        handed.add(key)
        return info

    added = set()
    for item_id, auxes in table.AUX_VARIANTS:
        for aux in auxes:
            info = info_of(item_id, aux)
            if info is None:
                plan.Unknown += 1
                continue
            plan.Specs.append(ItemSpec(item_id, aux, info=info))
            added.add(item_id)
    plan.Hide = [(item_id, 0) for item_id in table.AUX_ONLY if item_id in added]

    replaced = set()
    for item_id, aux, user_data in families.entries(enchants):
        info = info_of(item_id, aux)
        if info is None:
            plan.Unknown += 1
            continue
        attr = ItemAttr(user_data=user_data) if user_data else None
        plan.Specs.append(ItemSpec(item_id, aux, attr=attr, info=info))
        if user_data:
            replaced.add(item_id)
        if item_id == families.BOOK:
            plan.Books += 1
            if families.mod_enchant_of(user_data):
                plan.ModBooks += 1
    plan.HidePlain = [(item_id, 0) for item_id in families.PLAIN_REPLACED if item_id in replaced]
    return plan


def item_groups(lookup):  # type: (callable) -> list
    """
    物品栏的分组：[(组的键, .lang 的键, [物品 id, ...])]，先创造栏的物品组、再那几族、再 MEI 补的同类组，组里照表里的顺序。
    lookup(物品 id) -> bool：物品表里有没有这个 id；没有的不进组，一样都没有的组不要（表比游戏新、版本对不上也不出错）。
    一个 id 只进第一个组（几张表重了以先出现的为准；生成器换版本时会报出来）
    """
    result = []
    taken = set()
    for key, name_key, ids in tuple(table.GROUPS) + tuple(families.GROUPS) + tuple(groups.EXTRA):
        kept = []
        for item_id in ids:
            if item_id in taken or not lookup(item_id):
                continue
            taken.add(item_id)
            kept.append(item_id)
        if kept:
            result.append((key, name_key, kept))
    return result


def engine_enchants():  # type: () -> list or None
    """
    引擎里已注册的全部附魔（物品组件的 GetAllEnchantsInfo，原版与模组的都有）；拿不到（接口没有、出错、给的不是表）给 None
    """
    try:
        import mod.client.extraClientApi as clientApi
        comp = clientApi.GetEngineCompFactory().CreateItem(clientApi.GetLevelId())
        getter = getattr(comp, "GetAllEnchantsInfo", None)
        result = getter() if callable(getter) else None
    except Exception:  # noqa  老版本没有这个接口
        return None
    return list(result) if isinstance(result, (list, tuple)) else None
