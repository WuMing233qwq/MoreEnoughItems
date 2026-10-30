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
创造栏目录里带附加值的物品与物品组 —— 由 debug/scripts/gen_creative_table.py --emit 从游戏的
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

GROUPS = (
    ("minecraft:itemGroup.name.planks", "itemGroup.name.planks", (
        "minecraft:oak_planks", "minecraft:spruce_planks", "minecraft:birch_planks", "minecraft:jungle_planks",
        "minecraft:acacia_planks", "minecraft:dark_oak_planks", "minecraft:mangrove_planks", "minecraft:cherry_planks",
        "minecraft:pale_oak_planks", "minecraft:bamboo_planks", "minecraft:bamboo_mosaic", "minecraft:crimson_planks",
        "minecraft:warped_planks")),
    ("minecraft:itemGroup.name.walls", "itemGroup.name.walls", (
        "minecraft:cobblestone_wall", "minecraft:mossy_cobblestone_wall", "minecraft:granite_wall",
        "minecraft:diorite_wall", "minecraft:andesite_wall", "minecraft:sandstone_wall", "minecraft:red_sandstone_wall",
        "minecraft:stone_brick_wall", "minecraft:mossy_stone_brick_wall", "minecraft:brick_wall",
        "minecraft:nether_brick_wall", "minecraft:red_nether_brick_wall", "minecraft:end_stone_brick_wall",
        "minecraft:prismarine_wall", "minecraft:blackstone_wall", "minecraft:polished_blackstone_wall",
        "minecraft:polished_blackstone_brick_wall", "minecraft:cobbled_deepslate_wall", "minecraft:deepslate_tile_wall",
        "minecraft:polished_deepslate_wall", "minecraft:deepslate_brick_wall", "minecraft:tuff_wall",
        "minecraft:tuff_brick_wall", "minecraft:polished_tuff_wall", "minecraft:mud_brick_wall",
        "minecraft:resin_brick_wall")),
    ("minecraft:itemGroup.name.fence", "itemGroup.name.fence", (
        "minecraft:oak_fence", "minecraft:spruce_fence", "minecraft:birch_fence", "minecraft:jungle_fence",
        "minecraft:acacia_fence", "minecraft:dark_oak_fence", "minecraft:mangrove_fence", "minecraft:cherry_fence",
        "minecraft:pale_oak_fence", "minecraft:bamboo_fence", "minecraft:nether_brick_fence", "minecraft:crimson_fence",
        "minecraft:warped_fence")),
    ("minecraft:itemGroup.name.fenceGate", "itemGroup.name.fenceGate", (
        "minecraft:fence_gate", "minecraft:spruce_fence_gate", "minecraft:birch_fence_gate",
        "minecraft:jungle_fence_gate", "minecraft:acacia_fence_gate", "minecraft:dark_oak_fence_gate",
        "minecraft:mangrove_fence_gate", "minecraft:cherry_fence_gate", "minecraft:pale_oak_fence_gate",
        "minecraft:bamboo_fence_gate", "minecraft:crimson_fence_gate", "minecraft:warped_fence_gate")),
    ("minecraft:itemGroup.name.stairs", "itemGroup.name.stairs", (
        "minecraft:normal_stone_stairs", "minecraft:stone_stairs", "minecraft:mossy_cobblestone_stairs",
        "minecraft:oak_stairs", "minecraft:spruce_stairs", "minecraft:birch_stairs", "minecraft:jungle_stairs",
        "minecraft:acacia_stairs", "minecraft:dark_oak_stairs", "minecraft:mangrove_stairs", "minecraft:cherry_stairs",
        "minecraft:pale_oak_stairs", "minecraft:bamboo_stairs", "minecraft:bamboo_mosaic_stairs",
        "minecraft:stone_brick_stairs", "minecraft:mossy_stone_brick_stairs", "minecraft:sandstone_stairs",
        "minecraft:smooth_sandstone_stairs", "minecraft:red_sandstone_stairs", "minecraft:smooth_red_sandstone_stairs",
        "minecraft:granite_stairs", "minecraft:polished_granite_stairs", "minecraft:diorite_stairs",
        "minecraft:polished_diorite_stairs", "minecraft:andesite_stairs", "minecraft:polished_andesite_stairs",
        "minecraft:brick_stairs", "minecraft:nether_brick_stairs", "minecraft:red_nether_brick_stairs",
        "minecraft:end_brick_stairs", "minecraft:quartz_stairs", "minecraft:smooth_quartz_stairs",
        "minecraft:purpur_stairs", "minecraft:prismarine_stairs", "minecraft:dark_prismarine_stairs",
        "minecraft:prismarine_bricks_stairs", "minecraft:crimson_stairs", "minecraft:warped_stairs",
        "minecraft:blackstone_stairs", "minecraft:polished_blackstone_stairs",
        "minecraft:polished_blackstone_brick_stairs", "minecraft:cobbled_deepslate_stairs",
        "minecraft:deepslate_tile_stairs", "minecraft:polished_deepslate_stairs", "minecraft:deepslate_brick_stairs",
        "minecraft:tuff_stairs", "minecraft:polished_tuff_stairs", "minecraft:tuff_brick_stairs",
        "minecraft:mud_brick_stairs", "minecraft:cut_copper_stairs", "minecraft:exposed_cut_copper_stairs",
        "minecraft:weathered_cut_copper_stairs", "minecraft:oxidized_cut_copper_stairs",
        "minecraft:waxed_cut_copper_stairs", "minecraft:waxed_exposed_cut_copper_stairs",
        "minecraft:waxed_weathered_cut_copper_stairs", "minecraft:waxed_oxidized_cut_copper_stairs",
        "minecraft:resin_brick_stairs")),
    ("minecraft:itemGroup.name.door", "itemGroup.name.door", (
        "minecraft:wooden_door", "minecraft:spruce_door", "minecraft:birch_door", "minecraft:jungle_door",
        "minecraft:acacia_door", "minecraft:dark_oak_door", "minecraft:mangrove_door", "minecraft:cherry_door",
        "minecraft:pale_oak_door", "minecraft:bamboo_door", "minecraft:iron_door", "minecraft:crimson_door",
        "minecraft:warped_door", "minecraft:copper_door", "minecraft:exposed_copper_door",
        "minecraft:weathered_copper_door", "minecraft:oxidized_copper_door", "minecraft:waxed_copper_door",
        "minecraft:waxed_exposed_copper_door", "minecraft:waxed_weathered_copper_door",
        "minecraft:waxed_oxidized_copper_door")),
    ("minecraft:itemGroup.name.trapdoor", "itemGroup.name.trapdoor", (
        "minecraft:trapdoor", "minecraft:spruce_trapdoor", "minecraft:birch_trapdoor", "minecraft:jungle_trapdoor",
        "minecraft:acacia_trapdoor", "minecraft:dark_oak_trapdoor", "minecraft:mangrove_trapdoor",
        "minecraft:cherry_trapdoor", "minecraft:pale_oak_trapdoor", "minecraft:bamboo_trapdoor",
        "minecraft:iron_trapdoor", "minecraft:crimson_trapdoor", "minecraft:warped_trapdoor",
        "minecraft:copper_trapdoor", "minecraft:exposed_copper_trapdoor", "minecraft:weathered_copper_trapdoor",
        "minecraft:oxidized_copper_trapdoor", "minecraft:waxed_copper_trapdoor",
        "minecraft:waxed_exposed_copper_trapdoor", "minecraft:waxed_weathered_copper_trapdoor",
        "minecraft:waxed_oxidized_copper_trapdoor")),
    ("minecraft:itemGroup.name.bars", "itemGroup.name.bars", (
        "minecraft:iron_bars", "minecraft:copper_bars", "minecraft:exposed_copper_bars",
        "minecraft:weathered_copper_bars", "minecraft:oxidized_copper_bars", "minecraft:waxed_copper_bars",
        "minecraft:waxed_exposed_copper_bars", "minecraft:waxed_weathered_copper_bars",
        "minecraft:waxed_oxidized_copper_bars")),
    ("minecraft:itemGroup.name.glass", "itemGroup.name.glass", (
        "minecraft:glass", "minecraft:white_stained_glass", "minecraft:light_gray_stained_glass",
        "minecraft:gray_stained_glass", "minecraft:black_stained_glass", "minecraft:brown_stained_glass",
        "minecraft:red_stained_glass", "minecraft:orange_stained_glass", "minecraft:yellow_stained_glass",
        "minecraft:lime_stained_glass", "minecraft:green_stained_glass", "minecraft:cyan_stained_glass",
        "minecraft:light_blue_stained_glass", "minecraft:blue_stained_glass", "minecraft:purple_stained_glass",
        "minecraft:magenta_stained_glass", "minecraft:pink_stained_glass", "minecraft:tinted_glass")),
    ("minecraft:itemGroup.name.glassPane", "itemGroup.name.glassPane", (
        "minecraft:glass_pane", "minecraft:white_stained_glass_pane", "minecraft:light_gray_stained_glass_pane",
        "minecraft:gray_stained_glass_pane", "minecraft:black_stained_glass_pane", "minecraft:brown_stained_glass_pane",
        "minecraft:red_stained_glass_pane", "minecraft:orange_stained_glass_pane",
        "minecraft:yellow_stained_glass_pane", "minecraft:lime_stained_glass_pane",
        "minecraft:green_stained_glass_pane", "minecraft:cyan_stained_glass_pane",
        "minecraft:light_blue_stained_glass_pane", "minecraft:blue_stained_glass_pane",
        "minecraft:purple_stained_glass_pane", "minecraft:magenta_stained_glass_pane",
        "minecraft:pink_stained_glass_pane")),
    ("minecraft:itemGroup.name.slab", "itemGroup.name.slab", (
        "minecraft:smooth_stone_slab", "minecraft:normal_stone_slab", "minecraft:cobblestone_slab",
        "minecraft:mossy_cobblestone_slab", "minecraft:oak_slab", "minecraft:spruce_slab", "minecraft:birch_slab",
        "minecraft:jungle_slab", "minecraft:acacia_slab", "minecraft:dark_oak_slab", "minecraft:mangrove_slab",
        "minecraft:cherry_slab", "minecraft:pale_oak_slab", "minecraft:bamboo_slab", "minecraft:bamboo_mosaic_slab",
        "minecraft:stone_brick_slab", "minecraft:mossy_stone_brick_slab", "minecraft:sandstone_slab",
        "minecraft:cut_sandstone_slab", "minecraft:smooth_sandstone_slab", "minecraft:red_sandstone_slab",
        "minecraft:cut_red_sandstone_slab", "minecraft:smooth_red_sandstone_slab", "minecraft:granite_slab",
        "minecraft:polished_granite_slab", "minecraft:diorite_slab", "minecraft:polished_diorite_slab",
        "minecraft:andesite_slab", "minecraft:polished_andesite_slab", "minecraft:brick_slab",
        "minecraft:nether_brick_slab", "minecraft:red_nether_brick_slab", "minecraft:end_stone_brick_slab",
        "minecraft:quartz_slab", "minecraft:smooth_quartz_slab", "minecraft:purpur_slab", "minecraft:prismarine_slab",
        "minecraft:dark_prismarine_slab", "minecraft:prismarine_brick_slab", "minecraft:crimson_slab",
        "minecraft:warped_slab", "minecraft:blackstone_slab", "minecraft:polished_blackstone_slab",
        "minecraft:polished_blackstone_brick_slab", "minecraft:cobbled_deepslate_slab",
        "minecraft:polished_deepslate_slab", "minecraft:deepslate_tile_slab", "minecraft:deepslate_brick_slab",
        "minecraft:tuff_slab", "minecraft:polished_tuff_slab", "minecraft:tuff_brick_slab", "minecraft:mud_brick_slab",
        "minecraft:cut_copper_slab", "minecraft:exposed_cut_copper_slab", "minecraft:weathered_cut_copper_slab",
        "minecraft:oxidized_cut_copper_slab", "minecraft:waxed_cut_copper_slab",
        "minecraft:waxed_exposed_cut_copper_slab", "minecraft:waxed_weathered_cut_copper_slab",
        "minecraft:waxed_oxidized_cut_copper_slab", "minecraft:resin_brick_slab")),
    ("minecraft:itemGroup.name.stoneBrick", "itemGroup.name.stoneBrick", (
        "minecraft:stone_bricks", "minecraft:mossy_stone_bricks", "minecraft:cracked_stone_bricks",
        "minecraft:chiseled_stone_bricks", "minecraft:smooth_stone", "minecraft:end_bricks",
        "minecraft:polished_blackstone_bricks", "minecraft:cracked_polished_blackstone_bricks",
        "minecraft:gilded_blackstone", "minecraft:chiseled_polished_blackstone", "minecraft:deepslate_tiles",
        "minecraft:cracked_deepslate_tiles", "minecraft:deepslate_bricks", "minecraft:tuff_bricks",
        "minecraft:cracked_deepslate_bricks", "minecraft:chiseled_deepslate", "minecraft:chiseled_tuff",
        "minecraft:chiseled_tuff_bricks")),
    ("minecraft:itemGroup.name.sandstone", "itemGroup.name.sandstone", (
        "minecraft:sandstone", "minecraft:chiseled_sandstone", "minecraft:cut_sandstone", "minecraft:smooth_sandstone",
        "minecraft:red_sandstone", "minecraft:chiseled_red_sandstone", "minecraft:cut_red_sandstone",
        "minecraft:smooth_red_sandstone")),
    ("minecraft:itemGroup.name.copper", "itemGroup.name.copper", (
        "minecraft:copper_block", "minecraft:exposed_copper", "minecraft:weathered_copper", "minecraft:oxidized_copper",
        "minecraft:waxed_copper", "minecraft:waxed_exposed_copper", "minecraft:waxed_weathered_copper",
        "minecraft:waxed_oxidized_copper", "minecraft:copper_grate", "minecraft:exposed_copper_grate",
        "minecraft:weathered_copper_grate", "minecraft:oxidized_copper_grate", "minecraft:waxed_copper_grate",
        "minecraft:waxed_exposed_copper_grate", "minecraft:waxed_weathered_copper_grate",
        "minecraft:waxed_oxidized_copper_grate", "minecraft:cut_copper", "minecraft:exposed_cut_copper",
        "minecraft:weathered_cut_copper", "minecraft:oxidized_cut_copper", "minecraft:waxed_cut_copper",
        "minecraft:waxed_exposed_cut_copper", "minecraft:waxed_weathered_cut_copper",
        "minecraft:waxed_oxidized_cut_copper", "minecraft:chiseled_copper", "minecraft:exposed_chiseled_copper",
        "minecraft:weathered_chiseled_copper", "minecraft:oxidized_chiseled_copper", "minecraft:waxed_chiseled_copper",
        "minecraft:waxed_exposed_chiseled_copper", "minecraft:waxed_oxidized_chiseled_copper",
        "minecraft:waxed_weathered_chiseled_copper", "minecraft:copper_bulb", "minecraft:exposed_copper_bulb",
        "minecraft:weathered_copper_bulb", "minecraft:oxidized_copper_bulb", "minecraft:waxed_copper_bulb",
        "minecraft:waxed_exposed_copper_bulb", "minecraft:waxed_weathered_copper_bulb",
        "minecraft:waxed_oxidized_copper_bulb")),
    ("minecraft:itemGroup.name.wool", "itemGroup.name.wool", (
        "minecraft:white_wool", "minecraft:light_gray_wool", "minecraft:gray_wool", "minecraft:black_wool",
        "minecraft:brown_wool", "minecraft:red_wool", "minecraft:orange_wool", "minecraft:yellow_wool",
        "minecraft:lime_wool", "minecraft:green_wool", "minecraft:cyan_wool", "minecraft:light_blue_wool",
        "minecraft:blue_wool", "minecraft:purple_wool", "minecraft:magenta_wool", "minecraft:pink_wool")),
    ("minecraft:itemGroup.name.woolCarpet", "itemGroup.name.woolCarpet", (
        "minecraft:white_carpet", "minecraft:light_gray_carpet", "minecraft:gray_carpet", "minecraft:black_carpet",
        "minecraft:brown_carpet", "minecraft:red_carpet", "minecraft:orange_carpet", "minecraft:yellow_carpet",
        "minecraft:lime_carpet", "minecraft:green_carpet", "minecraft:cyan_carpet", "minecraft:light_blue_carpet",
        "minecraft:blue_carpet", "minecraft:purple_carpet", "minecraft:magenta_carpet", "minecraft:pink_carpet")),
    ("minecraft:itemGroup.name.concretePowder", "itemGroup.name.concretePowder", (
        "minecraft:white_concrete_powder", "minecraft:light_gray_concrete_powder", "minecraft:gray_concrete_powder",
        "minecraft:black_concrete_powder", "minecraft:brown_concrete_powder", "minecraft:red_concrete_powder",
        "minecraft:orange_concrete_powder", "minecraft:yellow_concrete_powder", "minecraft:lime_concrete_powder",
        "minecraft:green_concrete_powder", "minecraft:cyan_concrete_powder", "minecraft:light_blue_concrete_powder",
        "minecraft:blue_concrete_powder", "minecraft:purple_concrete_powder", "minecraft:magenta_concrete_powder",
        "minecraft:pink_concrete_powder")),
    ("minecraft:itemGroup.name.concrete", "itemGroup.name.concrete", (
        "minecraft:white_concrete", "minecraft:light_gray_concrete", "minecraft:gray_concrete",
        "minecraft:black_concrete", "minecraft:brown_concrete", "minecraft:red_concrete", "minecraft:orange_concrete",
        "minecraft:yellow_concrete", "minecraft:lime_concrete", "minecraft:green_concrete", "minecraft:cyan_concrete",
        "minecraft:light_blue_concrete", "minecraft:blue_concrete", "minecraft:purple_concrete",
        "minecraft:magenta_concrete", "minecraft:pink_concrete")),
    ("minecraft:itemGroup.name.stainedClay", "itemGroup.name.stainedClay", (
        "minecraft:hardened_clay", "minecraft:white_terracotta", "minecraft:light_gray_terracotta",
        "minecraft:gray_terracotta", "minecraft:black_terracotta", "minecraft:brown_terracotta",
        "minecraft:red_terracotta", "minecraft:orange_terracotta", "minecraft:yellow_terracotta",
        "minecraft:lime_terracotta", "minecraft:green_terracotta", "minecraft:cyan_terracotta",
        "minecraft:light_blue_terracotta", "minecraft:blue_terracotta", "minecraft:purple_terracotta",
        "minecraft:magenta_terracotta", "minecraft:pink_terracotta")),
    ("minecraft:itemGroup.name.glazedTerracotta", "itemGroup.name.glazedTerracotta", (
        "minecraft:white_glazed_terracotta", "minecraft:silver_glazed_terracotta", "minecraft:gray_glazed_terracotta",
        "minecraft:black_glazed_terracotta", "minecraft:brown_glazed_terracotta", "minecraft:red_glazed_terracotta",
        "minecraft:orange_glazed_terracotta", "minecraft:yellow_glazed_terracotta", "minecraft:lime_glazed_terracotta",
        "minecraft:green_glazed_terracotta", "minecraft:cyan_glazed_terracotta",
        "minecraft:light_blue_glazed_terracotta", "minecraft:blue_glazed_terracotta",
        "minecraft:purple_glazed_terracotta", "minecraft:magenta_glazed_terracotta",
        "minecraft:pink_glazed_terracotta")),
    ("minecraft:itemGroup.name.ore", "itemGroup.name.ore", (
        "minecraft:iron_ore", "minecraft:gold_ore", "minecraft:diamond_ore", "minecraft:lapis_ore",
        "minecraft:redstone_ore", "minecraft:coal_ore", "minecraft:copper_ore", "minecraft:emerald_ore",
        "minecraft:quartz_ore", "minecraft:nether_gold_ore", "minecraft:ancient_debris", "minecraft:deepslate_iron_ore",
        "minecraft:deepslate_gold_ore", "minecraft:deepslate_diamond_ore", "minecraft:deepslate_lapis_ore",
        "minecraft:deepslate_redstone_ore", "minecraft:deepslate_emerald_ore", "minecraft:deepslate_coal_ore",
        "minecraft:deepslate_copper_ore")),
    ("minecraft:itemGroup.name.stone", "itemGroup.name.stone", (
        "minecraft:stone", "minecraft:granite", "minecraft:diorite", "minecraft:andesite", "minecraft:blackstone",
        "minecraft:deepslate", "minecraft:tuff", "minecraft:basalt", "minecraft:polished_granite",
        "minecraft:polished_diorite", "minecraft:polished_andesite", "minecraft:polished_blackstone",
        "minecraft:polished_deepslate", "minecraft:polished_tuff", "minecraft:polished_basalt",
        "minecraft:smooth_basalt")),
    ("minecraft:itemGroup.name.log", "itemGroup.name.log", (
        "minecraft:oak_log", "minecraft:stripped_oak_log", "minecraft:spruce_log", "minecraft:stripped_spruce_log",
        "minecraft:birch_log", "minecraft:stripped_birch_log", "minecraft:jungle_log", "minecraft:stripped_jungle_log",
        "minecraft:acacia_log", "minecraft:stripped_acacia_log", "minecraft:dark_oak_log",
        "minecraft:stripped_dark_oak_log", "minecraft:mangrove_log", "minecraft:stripped_mangrove_log",
        "minecraft:cherry_log", "minecraft:stripped_cherry_log", "minecraft:pale_oak_log",
        "minecraft:stripped_pale_oak_log", "minecraft:crimson_stem", "minecraft:stripped_crimson_stem",
        "minecraft:warped_stem", "minecraft:stripped_warped_stem")),
    ("minecraft:itemGroup.name.wood", "itemGroup.name.wood", (
        "minecraft:oak_wood", "minecraft:stripped_oak_wood", "minecraft:spruce_wood", "minecraft:stripped_spruce_wood",
        "minecraft:birch_wood", "minecraft:stripped_birch_wood", "minecraft:jungle_wood",
        "minecraft:stripped_jungle_wood", "minecraft:acacia_wood", "minecraft:stripped_acacia_wood",
        "minecraft:dark_oak_wood", "minecraft:stripped_dark_oak_wood", "minecraft:mangrove_wood",
        "minecraft:stripped_mangrove_wood", "minecraft:cherry_wood", "minecraft:stripped_cherry_wood",
        "minecraft:pale_oak_wood", "minecraft:stripped_pale_oak_wood", "minecraft:crimson_hyphae",
        "minecraft:stripped_crimson_hyphae", "minecraft:warped_hyphae", "minecraft:stripped_warped_hyphae",
        "minecraft:bamboo_block", "minecraft:stripped_bamboo_block")),
    ("minecraft:itemGroup.name.leaves", "itemGroup.name.leaves", (
        "minecraft:oak_leaves", "minecraft:spruce_leaves", "minecraft:birch_leaves", "minecraft:jungle_leaves",
        "minecraft:acacia_leaves", "minecraft:dark_oak_leaves", "minecraft:mangrove_leaves", "minecraft:cherry_leaves",
        "minecraft:pale_oak_leaves", "minecraft:azalea_leaves", "minecraft:azalea_leaves_flowered")),
    ("minecraft:itemGroup.name.sapling", "itemGroup.name.sapling", (
        "minecraft:oak_sapling", "minecraft:spruce_sapling", "minecraft:birch_sapling", "minecraft:jungle_sapling",
        "minecraft:acacia_sapling", "minecraft:dark_oak_sapling", "minecraft:mangrove_propagule",
        "minecraft:cherry_sapling", "minecraft:pale_oak_sapling")),
    ("minecraft:itemGroup.name.seed", "itemGroup.name.seed", (
        "minecraft:wheat_seeds", "minecraft:pumpkin_seeds", "minecraft:melon_seeds", "minecraft:beetroot_seeds",
        "minecraft:torchflower_seeds", "minecraft:pitcher_pod")),
    ("minecraft:itemGroup.name.crop", "itemGroup.name.crop", (
        "minecraft:wheat", "minecraft:beetroot", "minecraft:potato", "minecraft:poisonous_potato", "minecraft:carrot",
        "minecraft:golden_carrot", "minecraft:apple", "minecraft:golden_apple", "minecraft:enchanted_golden_apple",
        "minecraft:melon_block", "minecraft:melon_slice", "minecraft:glistering_melon_slice", "minecraft:sweet_berries",
        "minecraft:glow_berries", "minecraft:pumpkin")),
    ("minecraft:itemGroup.name.grass", "itemGroup.name.grass", (
        "minecraft:fern", "minecraft:large_fern", "minecraft:short_grass", "minecraft:tall_grass",
        "minecraft:short_dry_grass", "minecraft:tall_dry_grass", "minecraft:bush", "minecraft:nether_sprouts")),
    ("minecraft:itemGroup.name.coral_decorations", "itemGroup.name.coral_decorations", (
        "minecraft:fire_coral", "minecraft:brain_coral", "minecraft:bubble_coral", "minecraft:tube_coral",
        "minecraft:horn_coral", "minecraft:dead_fire_coral", "minecraft:dead_brain_coral",
        "minecraft:dead_bubble_coral", "minecraft:dead_tube_coral", "minecraft:dead_horn_coral",
        "minecraft:fire_coral_fan", "minecraft:brain_coral_fan", "minecraft:bubble_coral_fan",
        "minecraft:tube_coral_fan", "minecraft:horn_coral_fan", "minecraft:dead_fire_coral_fan",
        "minecraft:dead_brain_coral_fan", "minecraft:dead_bubble_coral_fan", "minecraft:dead_tube_coral_fan",
        "minecraft:dead_horn_coral_fan")),
    ("minecraft:itemGroup.name.flower", "itemGroup.name.flower", (
        "minecraft:crimson_roots", "minecraft:warped_roots", "minecraft:dandelion", "minecraft:poppy",
        "minecraft:blue_orchid", "minecraft:allium", "minecraft:azure_bluet", "minecraft:red_tulip",
        "minecraft:orange_tulip", "minecraft:white_tulip", "minecraft:pink_tulip", "minecraft:oxeye_daisy",
        "minecraft:cornflower", "minecraft:lily_of_the_valley", "minecraft:sunflower", "minecraft:lilac",
        "minecraft:rose_bush", "minecraft:peony", "minecraft:pitcher_plant", "minecraft:pink_petals",
        "minecraft:wildflowers", "minecraft:wither_rose", "minecraft:torchflower", "minecraft:cactus_flower",
        "minecraft:closed_eyeblossom", "minecraft:open_eyeblossom")),
    ("minecraft:itemGroup.name.dye", "itemGroup.name.dye", (
        "minecraft:white_dye", "minecraft:light_gray_dye", "minecraft:gray_dye", "minecraft:black_dye",
        "minecraft:brown_dye", "minecraft:red_dye", "minecraft:orange_dye", "minecraft:yellow_dye",
        "minecraft:lime_dye", "minecraft:green_dye", "minecraft:cyan_dye", "minecraft:light_blue_dye",
        "minecraft:blue_dye", "minecraft:purple_dye", "minecraft:magenta_dye", "minecraft:pink_dye")),
    ("minecraft:itemGroup.name.rawFood", "itemGroup.name.rawFood", (
        "minecraft:chicken", "minecraft:porkchop", "minecraft:beef", "minecraft:mutton", "minecraft:rabbit",
        "minecraft:cod", "minecraft:salmon", "minecraft:tropical_fish", "minecraft:pufferfish")),
    ("minecraft:itemGroup.name.mushroom", "itemGroup.name.mushroom", (
        "minecraft:brown_mushroom", "minecraft:red_mushroom", "minecraft:crimson_fungus", "minecraft:warped_fungus",
        "minecraft:brown_mushroom_block", "minecraft:red_mushroom_block", "minecraft:mushroom_stem")),
    ("minecraft:itemGroup.name.monsterStoneEgg", "itemGroup.name.monsterStoneEgg", (
        "minecraft:infested_stone", "minecraft:infested_cobblestone", "minecraft:infested_stone_bricks",
        "minecraft:infested_mossy_stone_bricks", "minecraft:infested_cracked_stone_bricks",
        "minecraft:infested_chiseled_stone_bricks", "minecraft:infested_deepslate")),
    ("minecraft:itemGroup.name.mobEgg", "itemGroup.name.mobEgg", (
        "minecraft:chicken_spawn_egg", "minecraft:bee_spawn_egg", "minecraft:cow_spawn_egg", "minecraft:pig_spawn_egg",
        "minecraft:sheep_spawn_egg", "minecraft:wolf_spawn_egg", "minecraft:polar_bear_spawn_egg",
        "minecraft:ocelot_spawn_egg", "minecraft:cat_spawn_egg", "minecraft:mooshroom_spawn_egg",
        "minecraft:bat_spawn_egg", "minecraft:parrot_spawn_egg", "minecraft:rabbit_spawn_egg",
        "minecraft:llama_spawn_egg", "minecraft:horse_spawn_egg", "minecraft:donkey_spawn_egg",
        "minecraft:mule_spawn_egg", "minecraft:skeleton_horse_spawn_egg", "minecraft:zombie_horse_spawn_egg",
        "minecraft:tropical_fish_spawn_egg", "minecraft:cod_spawn_egg", "minecraft:pufferfish_spawn_egg",
        "minecraft:salmon_spawn_egg", "minecraft:dolphin_spawn_egg", "minecraft:turtle_spawn_egg",
        "minecraft:panda_spawn_egg", "minecraft:fox_spawn_egg", "minecraft:creeper_spawn_egg",
        "minecraft:enderman_spawn_egg", "minecraft:silverfish_spawn_egg", "minecraft:skeleton_spawn_egg",
        "minecraft:wither_skeleton_spawn_egg", "minecraft:stray_spawn_egg", "minecraft:slime_spawn_egg",
        "minecraft:spider_spawn_egg", "minecraft:zombie_spawn_egg", "minecraft:zombie_pigman_spawn_egg",
        "minecraft:husk_spawn_egg", "minecraft:drowned_spawn_egg", "minecraft:squid_spawn_egg",
        "minecraft:glow_squid_spawn_egg", "minecraft:cave_spider_spawn_egg", "minecraft:witch_spawn_egg",
        "minecraft:guardian_spawn_egg", "minecraft:elder_guardian_spawn_egg", "minecraft:endermite_spawn_egg",
        "minecraft:magma_cube_spawn_egg", "minecraft:strider_spawn_egg", "minecraft:hoglin_spawn_egg",
        "minecraft:piglin_spawn_egg", "minecraft:zoglin_spawn_egg", "minecraft:piglin_brute_spawn_egg",
        "minecraft:goat_spawn_egg", "minecraft:axolotl_spawn_egg", "minecraft:warden_spawn_egg",
        "minecraft:allay_spawn_egg", "minecraft:frog_spawn_egg", "minecraft:tadpole_spawn_egg",
        "minecraft:trader_llama_spawn_egg", "minecraft:camel_spawn_egg", "minecraft:ghast_spawn_egg",
        "minecraft:blaze_spawn_egg", "minecraft:shulker_spawn_egg", "minecraft:vindicator_spawn_egg",
        "minecraft:evoker_spawn_egg", "minecraft:vex_spawn_egg", "minecraft:villager_spawn_egg",
        "minecraft:wandering_trader_spawn_egg", "minecraft:zombie_villager_spawn_egg", "minecraft:phantom_spawn_egg",
        "minecraft:pillager_spawn_egg", "minecraft:ravager_spawn_egg", "minecraft:iron_golem_spawn_egg",
        "minecraft:copper_golem_spawn_egg", "minecraft:snow_golem_spawn_egg", "minecraft:sniffer_spawn_egg",
        "minecraft:breeze_spawn_egg", "minecraft:armadillo_spawn_egg", "minecraft:bogged_spawn_egg",
        "minecraft:creaking_spawn_egg", "minecraft:happy_ghast_spawn_egg")),
    ("minecraft:itemGroup.name.coral", "itemGroup.name.coral", (
        "minecraft:tube_coral_block", "minecraft:brain_coral_block", "minecraft:bubble_coral_block",
        "minecraft:fire_coral_block", "minecraft:horn_coral_block", "minecraft:dead_tube_coral_block",
        "minecraft:dead_brain_coral_block", "minecraft:dead_bubble_coral_block", "minecraft:dead_fire_coral_block",
        "minecraft:dead_horn_coral_block")),
    ("minecraft:itemGroup.name.sculk", "itemGroup.name.sculk", (
        "minecraft:sculk", "minecraft:sculk_vein", "minecraft:sculk_catalyst", "minecraft:sculk_shrieker",
        "minecraft:sculk_sensor", "minecraft:calibrated_sculk_sensor")),
    ("minecraft:itemGroup.name.helmet", "itemGroup.name.helmet", (
        "minecraft:leather_helmet", "minecraft:copper_helmet", "minecraft:chainmail_helmet", "minecraft:iron_helmet",
        "minecraft:golden_helmet", "minecraft:diamond_helmet", "minecraft:netherite_helmet")),
    ("minecraft:itemGroup.name.chestplate", "itemGroup.name.chestplate", (
        "minecraft:leather_chestplate", "minecraft:copper_chestplate", "minecraft:chainmail_chestplate",
        "minecraft:iron_chestplate", "minecraft:golden_chestplate", "minecraft:diamond_chestplate",
        "minecraft:netherite_chestplate")),
    ("minecraft:itemGroup.name.leggings", "itemGroup.name.leggings", (
        "minecraft:leather_leggings", "minecraft:copper_leggings", "minecraft:chainmail_leggings",
        "minecraft:iron_leggings", "minecraft:golden_leggings", "minecraft:diamond_leggings",
        "minecraft:netherite_leggings")),
    ("minecraft:itemGroup.name.boots", "itemGroup.name.boots", (
        "minecraft:leather_boots", "minecraft:copper_boots", "minecraft:chainmail_boots", "minecraft:iron_boots",
        "minecraft:golden_boots", "minecraft:diamond_boots", "minecraft:netherite_boots")),
    ("minecraft:itemGroup.name.sword", "itemGroup.name.sword", (
        "minecraft:wooden_sword", "minecraft:stone_sword", "minecraft:copper_sword", "minecraft:iron_sword",
        "minecraft:golden_sword", "minecraft:diamond_sword", "minecraft:netherite_sword")),
    ("minecraft:itemGroup.name.axe", "itemGroup.name.axe", (
        "minecraft:wooden_axe", "minecraft:stone_axe", "minecraft:copper_axe", "minecraft:iron_axe",
        "minecraft:golden_axe", "minecraft:diamond_axe", "minecraft:netherite_axe")),
    ("minecraft:itemGroup.name.pickaxe", "itemGroup.name.pickaxe", (
        "minecraft:wooden_pickaxe", "minecraft:stone_pickaxe", "minecraft:copper_pickaxe", "minecraft:iron_pickaxe",
        "minecraft:golden_pickaxe", "minecraft:diamond_pickaxe", "minecraft:netherite_pickaxe")),
    ("minecraft:itemGroup.name.shovel", "itemGroup.name.shovel", (
        "minecraft:wooden_shovel", "minecraft:stone_shovel", "minecraft:copper_shovel", "minecraft:iron_shovel",
        "minecraft:golden_shovel", "minecraft:diamond_shovel", "minecraft:netherite_shovel")),
    ("minecraft:itemGroup.name.hoe", "itemGroup.name.hoe", (
        "minecraft:wooden_hoe", "minecraft:stone_hoe", "minecraft:copper_hoe", "minecraft:iron_hoe",
        "minecraft:golden_hoe", "minecraft:diamond_hoe", "minecraft:netherite_hoe")),
    ("minecraft:itemGroup.name.arrow", "itemGroup.name.arrow", ("minecraft:arrow",)),
    ("minecraft:itemGroup.name.cookedFood", "itemGroup.name.cookedFood", (
        "minecraft:cooked_chicken", "minecraft:cooked_porkchop", "minecraft:cooked_beef", "minecraft:cooked_mutton",
        "minecraft:cooked_rabbit", "minecraft:cooked_cod", "minecraft:cooked_salmon")),
    ("minecraft:itemGroup.name.miscFood", "itemGroup.name.miscFood", (
        "minecraft:bread", "minecraft:mushroom_stew", "minecraft:beetroot_soup", "minecraft:rabbit_stew",
        "minecraft:suspicious_stew", "minecraft:baked_potato", "minecraft:cookie", "minecraft:pumpkin_pie",
        "minecraft:cake", "minecraft:dried_kelp")),
    ("minecraft:itemGroup.name.goatHorn", "itemGroup.name.goatHorn", ("minecraft:goat_horn",)),
    ("minecraft:itemGroup.name.harnesses", "itemGroup.name.harnesses", (
        "minecraft:white_harness", "minecraft:light_gray_harness", "minecraft:gray_harness", "minecraft:black_harness",
        "minecraft:brown_harness", "minecraft:red_harness", "minecraft:orange_harness", "minecraft:yellow_harness",
        "minecraft:lime_harness", "minecraft:green_harness", "minecraft:cyan_harness", "minecraft:light_blue_harness",
        "minecraft:blue_harness", "minecraft:purple_harness", "minecraft:magenta_harness", "minecraft:pink_harness")),
    ("minecraft:itemGroup.name.bundles", "itemGroup.name.bundles", (
        "minecraft:bundle", "minecraft:white_bundle", "minecraft:light_gray_bundle", "minecraft:gray_bundle",
        "minecraft:black_bundle", "minecraft:brown_bundle", "minecraft:red_bundle", "minecraft:orange_bundle",
        "minecraft:yellow_bundle", "minecraft:lime_bundle", "minecraft:green_bundle", "minecraft:cyan_bundle",
        "minecraft:light_blue_bundle", "minecraft:blue_bundle", "minecraft:purple_bundle", "minecraft:magenta_bundle",
        "minecraft:pink_bundle")),
    ("minecraft:itemGroup.name.horseArmor", "itemGroup.name.horseArmor", (
        "minecraft:leather_horse_armor", "minecraft:copper_horse_armor", "minecraft:iron_horse_armor",
        "minecraft:golden_horse_armor", "minecraft:diamond_horse_armor")),
    ("minecraft:itemGroup.name.potion", "itemGroup.name.potion", ("minecraft:potion",)),
    ("minecraft:itemGroup.name.splashPotion", "itemGroup.name.splashPotion", ("minecraft:splash_potion",)),
    ("minecraft:itemGroup.name.lingeringPotion", "itemGroup.name.lingeringPotion", ("minecraft:lingering_potion",)),
    ("minecraft:itemGroup.name.ominousBottle", "itemGroup.name.ominousBottle", ("minecraft:ominous_bottle",)),
    ("minecraft:itemGroup.name.bed", "itemGroup.name.bed", ("minecraft:bed",)),
    ("minecraft:itemGroup.name.lanterns", "itemGroup.name.lanterns", (
        "minecraft:lantern", "minecraft:soul_lantern", "minecraft:copper_lantern", "minecraft:exposed_copper_lantern",
        "minecraft:weathered_copper_lantern", "minecraft:oxidized_copper_lantern", "minecraft:waxed_copper_lantern",
        "minecraft:waxed_exposed_copper_lantern", "minecraft:waxed_weathered_copper_lantern",
        "minecraft:waxed_oxidized_copper_lantern")),
    ("minecraft:itemGroup.name.candles", "itemGroup.name.candles", (
        "minecraft:candle", "minecraft:white_candle", "minecraft:orange_candle", "minecraft:magenta_candle",
        "minecraft:light_blue_candle", "minecraft:yellow_candle", "minecraft:lime_candle", "minecraft:pink_candle",
        "minecraft:gray_candle", "minecraft:light_gray_candle", "minecraft:cyan_candle", "minecraft:purple_candle",
        "minecraft:blue_candle", "minecraft:brown_candle", "minecraft:green_candle", "minecraft:red_candle",
        "minecraft:black_candle")),
    ("minecraft:itemGroup.name.anvil", "itemGroup.name.anvil", (
        "minecraft:anvil", "minecraft:chipped_anvil", "minecraft:damaged_anvil")),
    ("minecraft:itemGroup.name.shelf", "itemGroup.name.shelf", (
        "minecraft:oak_shelf", "minecraft:spruce_shelf", "minecraft:birch_shelf", "minecraft:jungle_shelf",
        "minecraft:acacia_shelf", "minecraft:dark_oak_shelf", "minecraft:mangrove_shelf", "minecraft:cherry_shelf",
        "minecraft:pale_oak_shelf", "minecraft:bamboo_shelf", "minecraft:crimson_shelf", "minecraft:warped_shelf")),
    ("minecraft:itemGroup.name.chest", "itemGroup.name.chest", (
        "minecraft:chest", "minecraft:trapped_chest", "minecraft:ender_chest", "minecraft:copper_chest",
        "minecraft:exposed_copper_chest", "minecraft:weathered_copper_chest", "minecraft:oxidized_copper_chest",
        "minecraft:waxed_copper_chest", "minecraft:waxed_exposed_copper_chest",
        "minecraft:waxed_weathered_copper_chest", "minecraft:waxed_oxidized_copper_chest")),
    ("minecraft:itemGroup.name.shulkerBox", "itemGroup.name.shulkerBox", (
        "minecraft:undyed_shulker_box", "minecraft:white_shulker_box", "minecraft:light_gray_shulker_box",
        "minecraft:gray_shulker_box", "minecraft:black_shulker_box", "minecraft:brown_shulker_box",
        "minecraft:red_shulker_box", "minecraft:orange_shulker_box", "minecraft:yellow_shulker_box",
        "minecraft:lime_shulker_box", "minecraft:green_shulker_box", "minecraft:cyan_shulker_box",
        "minecraft:light_blue_shulker_box", "minecraft:blue_shulker_box", "minecraft:purple_shulker_box",
        "minecraft:magenta_shulker_box", "minecraft:pink_shulker_box")),
    ("minecraft:itemGroup.name.copper_golem_statue", "itemGroup.name.copper_golem_statue", (
        "minecraft:copper_golem_statue", "minecraft:exposed_copper_golem_statue",
        "minecraft:weathered_copper_golem_statue", "minecraft:oxidized_copper_golem_statue",
        "minecraft:waxed_copper_golem_statue", "minecraft:waxed_exposed_copper_golem_statue",
        "minecraft:waxed_weathered_copper_golem_statue", "minecraft:waxed_oxidized_copper_golem_statue")),
    ("minecraft:itemGroup.name.record", "itemGroup.name.record", (
        "minecraft:music_disc_13", "minecraft:music_disc_cat", "minecraft:music_disc_blocks",
        "minecraft:music_disc_chirp", "minecraft:music_disc_far", "minecraft:music_disc_mall",
        "minecraft:music_disc_mellohi", "minecraft:music_disc_stal", "minecraft:music_disc_strad",
        "minecraft:music_disc_ward", "minecraft:music_disc_11", "minecraft:music_disc_wait",
        "minecraft:music_disc_otherside", "minecraft:music_disc_5", "minecraft:music_disc_pigstep",
        "minecraft:music_disc_relic", "minecraft:music_disc_creator", "minecraft:music_disc_creator_music_box",
        "minecraft:music_disc_precipice", "minecraft:music_disc_tears", "minecraft:music_disc_lava_chicken")),
    ("minecraft:itemGroup.name.sign", "itemGroup.name.sign", (
        "minecraft:oak_sign", "minecraft:spruce_sign", "minecraft:birch_sign", "minecraft:jungle_sign",
        "minecraft:acacia_sign", "minecraft:dark_oak_sign", "minecraft:mangrove_sign", "minecraft:cherry_sign",
        "minecraft:pale_oak_sign", "minecraft:bamboo_sign", "minecraft:crimson_sign", "minecraft:warped_sign")),
    ("minecraft:itemGroup.name.hanging_sign", "itemGroup.name.hanging_sign", (
        "minecraft:oak_hanging_sign", "minecraft:spruce_hanging_sign", "minecraft:birch_hanging_sign",
        "minecraft:jungle_hanging_sign", "minecraft:acacia_hanging_sign", "minecraft:dark_oak_hanging_sign",
        "minecraft:mangrove_hanging_sign", "minecraft:cherry_hanging_sign", "minecraft:pale_oak_hanging_sign",
        "minecraft:bamboo_hanging_sign", "minecraft:crimson_hanging_sign", "minecraft:warped_hanging_sign")),
    ("minecraft:itemGroup.name.skull", "itemGroup.name.skull", (
        "minecraft:player_head", "minecraft:zombie_head", "minecraft:creeper_head", "minecraft:dragon_head",
        "minecraft:skeleton_skull", "minecraft:wither_skeleton_skull", "minecraft:piglin_head")),
    ("minecraft:itemGroup.name.lightning_rod", "itemGroup.name.lightning_rod", (
        "minecraft:lightning_rod", "minecraft:exposed_lightning_rod", "minecraft:weathered_lightning_rod",
        "minecraft:oxidized_lightning_rod", "minecraft:waxed_lightning_rod", "minecraft:waxed_exposed_lightning_rod",
        "minecraft:waxed_weathered_lightning_rod", "minecraft:waxed_oxidized_lightning_rod")),
    ("minecraft:itemGroup.name.boat", "itemGroup.name.boat", (
        "minecraft:oak_boat", "minecraft:spruce_boat", "minecraft:birch_boat", "minecraft:jungle_boat",
        "minecraft:acacia_boat", "minecraft:dark_oak_boat", "minecraft:mangrove_boat", "minecraft:cherry_boat",
        "minecraft:pale_oak_boat", "minecraft:bamboo_raft")),
    ("minecraft:itemGroup.name.chestboat", "itemGroup.name.chestboat", (
        "minecraft:oak_chest_boat", "minecraft:spruce_chest_boat", "minecraft:birch_chest_boat",
        "minecraft:jungle_chest_boat", "minecraft:acacia_chest_boat", "minecraft:dark_oak_chest_boat",
        "minecraft:mangrove_chest_boat", "minecraft:cherry_chest_boat", "minecraft:pale_oak_chest_boat",
        "minecraft:bamboo_chest_raft")),
    ("minecraft:itemGroup.name.rail", "itemGroup.name.rail", (
        "minecraft:rail", "minecraft:golden_rail", "minecraft:detector_rail", "minecraft:activator_rail")),
    ("minecraft:itemGroup.name.minecart", "itemGroup.name.minecart", (
        "minecraft:minecart", "minecraft:chest_minecart", "minecraft:hopper_minecart", "minecraft:tnt_minecart")),
    ("minecraft:itemGroup.name.buttons", "itemGroup.name.buttons", (
        "minecraft:wooden_button", "minecraft:spruce_button", "minecraft:birch_button", "minecraft:jungle_button",
        "minecraft:acacia_button", "minecraft:dark_oak_button", "minecraft:mangrove_button", "minecraft:cherry_button",
        "minecraft:pale_oak_button", "minecraft:bamboo_button", "minecraft:stone_button", "minecraft:crimson_button",
        "minecraft:warped_button", "minecraft:polished_blackstone_button")),
    ("minecraft:itemGroup.name.pressurePlate", "itemGroup.name.pressurePlate", (
        "minecraft:wooden_pressure_plate", "minecraft:spruce_pressure_plate", "minecraft:birch_pressure_plate",
        "minecraft:jungle_pressure_plate", "minecraft:acacia_pressure_plate", "minecraft:dark_oak_pressure_plate",
        "minecraft:mangrove_pressure_plate", "minecraft:cherry_pressure_plate", "minecraft:pale_oak_pressure_plate",
        "minecraft:bamboo_pressure_plate", "minecraft:crimson_pressure_plate", "minecraft:warped_pressure_plate",
        "minecraft:stone_pressure_plate", "minecraft:light_weighted_pressure_plate",
        "minecraft:heavy_weighted_pressure_plate", "minecraft:polished_blackstone_pressure_plate")),
    ("minecraft:itemGroup.name.banner_pattern", "itemGroup.name.banner_pattern", (
        "minecraft:creeper_banner_pattern", "minecraft:skull_banner_pattern", "minecraft:flower_banner_pattern",
        "minecraft:mojang_banner_pattern", "minecraft:field_masoned_banner_pattern",
        "minecraft:bordure_indented_banner_pattern", "minecraft:piglin_banner_pattern",
        "minecraft:globe_banner_pattern", "minecraft:flow_banner_pattern", "minecraft:guster_banner_pattern")),
    ("minecraft:itemGroup.name.potterySherds", "itemGroup.name.potterySherds", (
        "minecraft:angler_pottery_sherd", "minecraft:archer_pottery_sherd", "minecraft:arms_up_pottery_sherd",
        "minecraft:blade_pottery_sherd", "minecraft:brewer_pottery_sherd", "minecraft:burn_pottery_sherd",
        "minecraft:danger_pottery_sherd", "minecraft:explorer_pottery_sherd", "minecraft:flow_pottery_sherd",
        "minecraft:friend_pottery_sherd", "minecraft:guster_pottery_sherd", "minecraft:heart_pottery_sherd",
        "minecraft:heartbreak_pottery_sherd", "minecraft:howl_pottery_sherd", "minecraft:miner_pottery_sherd",
        "minecraft:mourner_pottery_sherd", "minecraft:plenty_pottery_sherd", "minecraft:prize_pottery_sherd",
        "minecraft:scrape_pottery_sherd", "minecraft:sheaf_pottery_sherd", "minecraft:shelter_pottery_sherd",
        "minecraft:skull_pottery_sherd", "minecraft:snort_pottery_sherd")),
    ("minecraft:itemGroup.name.smithing_templates", "itemGroup.name.smithing_templates", (
        "minecraft:netherite_upgrade_smithing_template", "minecraft:sentry_armor_trim_smithing_template",
        "minecraft:vex_armor_trim_smithing_template", "minecraft:wild_armor_trim_smithing_template",
        "minecraft:coast_armor_trim_smithing_template", "minecraft:dune_armor_trim_smithing_template",
        "minecraft:wayfinder_armor_trim_smithing_template", "minecraft:shaper_armor_trim_smithing_template",
        "minecraft:raiser_armor_trim_smithing_template", "minecraft:host_armor_trim_smithing_template",
        "minecraft:ward_armor_trim_smithing_template", "minecraft:silence_armor_trim_smithing_template",
        "minecraft:tide_armor_trim_smithing_template", "minecraft:snout_armor_trim_smithing_template",
        "minecraft:rib_armor_trim_smithing_template", "minecraft:eye_armor_trim_smithing_template",
        "minecraft:spire_armor_trim_smithing_template", "minecraft:flow_armor_trim_smithing_template",
        "minecraft:bolt_armor_trim_smithing_template")),
    ("minecraft:itemGroup.name.chains", "itemGroup.name.chains", (
        "minecraft:iron_chain", "minecraft:copper_chain", "minecraft:exposed_copper_chain",
        "minecraft:weathered_copper_chain", "minecraft:oxidized_copper_chain", "minecraft:waxed_copper_chain",
        "minecraft:waxed_exposed_copper_chain", "minecraft:waxed_weathered_copper_chain",
        "minecraft:waxed_oxidized_copper_chain")),
)
"""
创造栏的物品组（目录里带 group_identifier 的那些）：(组的键, .lang 的键, (物品 id, ...))，组与组里的物品都照创造栏的顺序。
带附加值的几样（药水、药箭、床……）按 id 算一个 —— 物品栏的分组按 id 记，同一个 id 的变体一起进组
"""
