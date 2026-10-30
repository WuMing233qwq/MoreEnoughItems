# coding=utf-8

# ----------------------------------------------------------------------
#  table.py is part of MoreEnoughItems.
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
创造栏目录里带附加值的物品 —— 由 debug/scripts/gen_creative_table.py --emit 从游戏的
behavior_packs/vanilla/item_catalog/crafting_item_catalog.json 生成；换游戏版本时重跑，**不要手改**。
"""

GAME_VERSION = "3.9.0.401155"
""" 生成时读的游戏版本 """

AUX_VARIANTS = (
    ("minecraft:brown_mushroom_block", (14,)),
    ("minecraft:red_mushroom_block", (14,)),
    ("minecraft:arrow", (6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                         31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47)),
    ("minecraft:suspicious_stew", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)),
    ("minecraft:goat_horn", (1, 2, 3, 4, 5, 6, 7)),
    ("minecraft:empty_map", (2,)),
    ("minecraft:potion", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 42, 19, 20, 21, 22, 23, 24, 25,
                          26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46)),
    ("minecraft:splash_potion", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 42, 19, 20, 21, 22, 23,
                                 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45,
                                 46)),
    ("minecraft:lingering_potion", (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 42, 19, 20, 21, 22,
                                    23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44,
                                    45, 46)),
    ("minecraft:ominous_bottle", (1, 2, 3, 4)),
    ("minecraft:bed", (8, 7, 15, 12, 14, 1, 4, 5, 13, 9, 3, 11, 10, 2, 6)),
    ("minecraft:dropper", (3,)),
    ("minecraft:dispenser", (3,)),
    ("minecraft:piston", (1,)),
    ("minecraft:sticky_piston", (1,)),
)
"""
(物品 id, 带附加值的那几个 aux)，照创造栏的顺序（药水的 42 迟缓 IV 排在 18 后面）；aux 0 那一样物品表本来就有（RegItemFromIdList）
"""

AUX_ONLY = (
    "minecraft:brown_mushroom_block",
    "minecraft:red_mushroom_block",
    "minecraft:dropper",
    "minecraft:dispenser",
    "minecraft:piston",
    "minecraft:sticky_piston",
)
"""
创造栏里只有带附加值那一样、没有 aux 0 的物品（活塞、发射器这类拿方块朝向当图标，蘑菇方块是六面菌盖那一种）：
物品表里 aux 0 那份从物品栏藏起来，不然看着像有两个
"""
