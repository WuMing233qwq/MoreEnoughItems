# coding=utf-8

# ----------------------------------------------------------------------
#  fuels.py is part of MoreEnoughItems.
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
熔炉的燃料表 —— 给熔炉配方页的燃料格、燃料页（fuel 类型）用。

燃料是驱动机器的、不参与合成，**不进配方本身，也不用存**（FurnaceRecipe 不带燃料，Recipe.Id 也就不随燃料变）。

燃料 = 物品表里燃料时长大于 0 的（物品类燃料：煤、木炭、木棍、木制工具、岩浆桶、烈焰棒……）
     + 按 tag 补的方块类燃料（方块类燃料的燃料时长给 0，CLAUDE.md 引擎结论 §11 / §44）：
       minecraft:logs_that_burn 正好是能烧的原木；minecraft:planks / minecraft:wooden_slabs 去掉下界木（绯红 / 诡异也带这两个 tag，只能按名字排除）。
楼梯、栅栏、工作台、箱子这些没有 tag 的 3.8 上补不了，先缺着；3.10 起有原生的 tag 查找，那时换这一处。
tag 就在注册物品时缓存的 Info.Tags 里：不调引擎、不另建索引；结果放在 ItemManager 的搜索缓存里（物品表一变就清）。
"""
from MEIScripts.api.facades.types import Ingredient
from MEIScripts.api.facades.registry import ItemManager

BURNING_TAGS = ("minecraft:logs_that_burn",)
""" 带它就是燃料 """

WOODEN_TAGS = ("minecraft:planks", "minecraft:wooden_slabs")
""" 带它、又不是下界木的是燃料 """

NETHER_WOODS = ("crimson", "warped")
""" 下界木的名字（绯红、诡异）：它们的木板、台阶带的 tag 和能烧的一样，只能按名字排除 """

CACHE_KEY = "furnace.fuels"

TAG_SECONDS = (("minecraft:logs_that_burn", 15.0), ("minecraft:planks", 15.0), ("minecraft:wooden_slabs", 7.5))
"""
按 tag 补的方块类燃料能烧多少秒：引擎给它们的燃料时长是 0（引擎结论 §11），这里写原版基岩版的数（原木、木板 15 秒，木台阶 7.5 秒）
"""

SMELT_SECONDS = 10.0
""" 熔炉烧一个物品要 10 秒（高炉、烟熏炉快一倍，燃料也烧得快一倍，能烧的个数一样）"""


def is_fuel(item):  # type: (any) -> bool
    """ 这个物品能不能当熔炉燃料（看缓存的 Info：燃料时长、tag）"""
    try:
        info = item.Info
        if (info.FuelDuration or 0) > 0:
            return True
        tags = info.Tags or ()
    except Exception:  # noqa  惰性字段取不到：不算燃料
        return False
    if any(tag in tags for tag in BURNING_TAGS):
        return True
    if any(tag in tags for tag in WOODEN_TAGS):
        name = (getattr(item, "ItemId", "") or "").split(":")[-1]
        return not any(wood in name for wood in NETHER_WOODS)
    return False


def burn_seconds(item):  # type: (any) -> float or None
    """ 一样燃料能烧多少秒：引擎给的燃料时长（秒，引擎结论 §44）；方块类燃料给 0 的按 tag 写原版的数；都没有给 None """
    if not is_fuel(item):
        return None  # 和「能燃烧」筛选一个口径：下界木的木板、台阶带着 planks / wooden_slabs 的 tag，却烧不了
    try:
        info = item.Info
        duration = float(info.FuelDuration or 0)
        tags = info.Tags or ()
    except Exception:  # noqa  惰性字段取不到：认不出时长
        return None
    if duration > 0:
        return duration
    for tag, seconds in TAG_SECONDS:
        if tag in tags:
            return seconds
    return None


def fuel_items():  # type: () -> list
    """ 全部燃料（物品表里的顺序）；物品表不变就只扫一遍 """
    return ItemManager.SearchByCondition(is_fuel, CACHE_KEY)


def fuel_ingredient():  # type: () -> Ingredient
    """ 燃料格的多候选原料（每次新建：几十个 stack 很便宜，也不和别的配方行共用可变对象）"""
    return Ingredient([item.stack(1) for item in fuel_items()], 1)
