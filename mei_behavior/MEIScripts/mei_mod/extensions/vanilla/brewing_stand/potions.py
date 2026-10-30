# coding=utf-8

# ----------------------------------------------------------------------
#  potions.py is part of MoreEnoughItems.
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
药水的 aux 与引擎酿造配方里的药水类型名（minecraft:potion_type:<名字>）一一对应：下标就是 aux（逐个对过 ——
物品名、悬停文字里的时长、配方都对得上，CLAUDE.md 引擎结论 §45）。引擎的酿造查询不认 tag 与 aux、药水要传类型全名，
所以 aux → 名字要自己映射（别的模组也都直接映射）。36 衰变药水没有酿造配方，名字查不到（写的 wither 没核实，用不上）
"""
POTION_TYPE = "minecraft:potion_type:"

CONTAINERS = ("minecraft:potion", "minecraft:splash_potion", "minecraft:lingering_potion")
""" 三种瓶子（普通、喷溅、滞留）：同一个 aux 是同一种药水 """

TYPES = (
    "water", "mundane", "long_mundane", "thick", "awkward",
    "nightvision", "long_nightvision", "invisibility", "long_invisibility",
    "leaping", "long_leaping", "strong_leaping", "fire_resistance", "long_fire_resistance",
    "swiftness", "long_swiftness", "strong_swiftness", "slowness", "long_slowness",
    "water_breathing", "long_water_breathing", "healing", "strong_healing", "harming", "strong_harming",
    "poison", "long_poison", "strong_poison", "regeneration", "long_regeneration", "strong_regeneration",
    "strength", "long_strength", "strong_strength", "weakness", "long_weakness",
    "wither", "turtle_master", "long_turtle_master", "strong_turtle_master",
    "slow_falling", "long_slow_falling", "strong_slowness",
    "wind_charged", "weaving", "oozing", "infested",
)
""" 下标就是药水的 aux（0 水瓶 ~ 46 虫蚀）"""

AUX_OF = dict((name, aux) for aux, name in enumerate(TYPES))


def type_name(value):  # type: (any) -> str or None
    """ 'minecraft:potion_type:strength' -> 'strength'（str）；不是药水类型给 None """
    if not isinstance(value, basestring) or not value.startswith(POTION_TYPE):
        return None
    name = value[len(POTION_TYPE):]
    return name.encode("utf-8") if isinstance(name, unicode) else name  # noqa  拣出 unicode，同 utils/text.native_str
