# coding=utf-8

# ----------------------------------------------------------------------
#  groups.py is part of MoreEnoughItems.
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
MEI 自己补的同类物品组：创造栏没分组、却明显是同一类的（锭、粗矿、粒……）。创造栏自己的组在 table.GROUPS（生成的），
引擎自己加的几族（附魔书、旗帜、烟花）在 families.GROUPS。写法和它们一样：(组的键, .lang 的键, (物品 id, ...))，组里照这里的顺序排。
收组的规矩：同一类、至少三样（两样一组，折起来还不如直接摆着）；一样东西只进一个组。
换游戏版本时生成器（debug/scripts/gen_creative_table.py）核对这里的 id 都还在目录里、没和创造栏的组重了。
本模块不 import 别的模块（生成器按路径载入它）
"""

EXTRA = (
    ("mei:group.ingot", "mei.group.ingot", (
        "minecraft:copper_ingot", "minecraft:iron_ingot", "minecraft:gold_ingot", "minecraft:netherite_ingot")),
    ("mei:group.raw_ore", "mei.group.raw_ore", (
        "minecraft:raw_copper", "minecraft:raw_iron", "minecraft:raw_gold")),
    ("mei:group.nugget", "mei.group.nugget", (
        "minecraft:copper_nugget", "minecraft:iron_nugget", "minecraft:gold_nugget")),
    ("mei:group.raw_ore_block", "mei.group.raw_ore_block", (
        "minecraft:raw_copper_block", "minecraft:raw_iron_block", "minecraft:raw_gold_block")),
    ("mei:group.mineral_block", "mei.group.mineral_block", (
        "minecraft:coal_block", "minecraft:iron_block", "minecraft:gold_block", "minecraft:redstone_block",
        "minecraft:emerald_block", "minecraft:lapis_block", "minecraft:diamond_block", "minecraft:netherite_block")),
    ("mei:group.bucket", "mei.group.bucket", (
        "minecraft:bucket", "minecraft:water_bucket", "minecraft:lava_bucket", "minecraft:powder_snow_bucket",
        "minecraft:milk_bucket", "minecraft:cod_bucket", "minecraft:salmon_bucket", "minecraft:tropical_fish_bucket",
        "minecraft:pufferfish_bucket", "minecraft:axolotl_bucket", "minecraft:tadpole_bucket")),
    ("mei:group.torch", "mei.group.torch", (
        "minecraft:torch", "minecraft:soul_torch", "minecraft:copper_torch")),
    ("mei:group.egg", "mei.group.egg", (
        "minecraft:egg", "minecraft:brown_egg", "minecraft:blue_egg")),
    ("mei:group.froglight", "mei.group.froglight", (
        "minecraft:pearlescent_froglight", "minecraft:verdant_froglight", "minecraft:ochre_froglight")),
    ("mei:group.amethyst", "mei.group.amethyst", (
        "minecraft:amethyst_block", "minecraft:budding_amethyst", "minecraft:amethyst_cluster",
        "minecraft:large_amethyst_bud", "minecraft:medium_amethyst_bud", "minecraft:small_amethyst_bud")),
    ("mei:group.quartz_block", "mei.group.quartz_block", (
        "minecraft:quartz_block", "minecraft:quartz_bricks", "minecraft:quartz_pillar", "minecraft:chiseled_quartz_block",
        "minecraft:smooth_quartz")),
    ("mei:group.prismarine", "mei.group.prismarine", (
        "minecraft:prismarine", "minecraft:prismarine_bricks", "minecraft:dark_prismarine")),
    ("mei:group.nether_brick", "mei.group.nether_brick", (
        "minecraft:nether_brick", "minecraft:red_nether_brick", "minecraft:chiseled_nether_bricks",
        "minecraft:cracked_nether_bricks")),
    ("mei:group.resin_block", "mei.group.resin_block", (
        "minecraft:resin_block", "minecraft:resin_bricks", "minecraft:chiseled_resin_bricks")),
    ("mei:group.brick", "mei.group.brick", (
        "minecraft:brick", "minecraft:netherbrick", "minecraft:resin_brick")),
    ("mei:group.ice", "mei.group.ice", (
        "minecraft:ice", "minecraft:packed_ice", "minecraft:blue_ice")),
    ("mei:group.dirt", "mei.group.dirt", (
        "minecraft:grass_block", "minecraft:podzol", "minecraft:mycelium", "minecraft:grass_path", "minecraft:dirt",
        "minecraft:coarse_dirt", "minecraft:dirt_with_roots", "minecraft:farmland")),
    ("mei:group.moss", "mei.group.moss", (
        "minecraft:moss_block", "minecraft:moss_carpet", "minecraft:pale_moss_block", "minecraft:pale_moss_carpet",
        "minecraft:pale_hanging_moss")),
    ("mei:group.vine", "mei.group.vine", (
        "minecraft:vine", "minecraft:weeping_vines", "minecraft:twisting_vines")),
    ("mei:group.fishing_rod", "mei.group.fishing_rod", (
        "minecraft:fishing_rod", "minecraft:carrot_on_a_stick", "minecraft:warped_fungus_on_a_stick")),
)
"""
(组的键, .lang 的键, (物品 id, ...))。组的键带 mei: 前缀，免得和创造栏的组（minecraft:itemGroup.name.*）、别的模组登记的组撞；
组里的先后照材料的档次（铜 → 铁 → 金 → 下界合金）或创造栏里的顺序
"""
