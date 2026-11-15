# coding=utf-8

# ----------------------------------------------------------------------
#  families.py is part of MoreEnoughItems.
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
创造栏里引擎自己加的几族：旗帜、附魔书、烟花火箭、烟火之星 —— 创造栏目录（table.py 的来源）里没有它们，
游戏目录里也找不到别的来源，只能手写在这里（docs/architecture/item_model.md §9.8）。
附魔书例外：全照引擎给的附魔信息出（GetAllEnchantsInfo，原版与模组的附魔都在里面），这里不记任何附魔的表。
userData 一律用带类型的写法 {"__type__": NBT 类型, "__value__": 值}：普通字典引擎读不出来（附魔书显示「保护 0」、烟花「飞行时间：0」）。
颜色照创造栏的顺序排：旗帜、烟火之星的 aux 是染料下标、0 是黑色，床的 aux 0 却是白色 —— 照着床的 aux 数字排，颜色顺序就全乱了。
普通旗帜不带 userData（写成 {"Type": 0} 引擎也认）：和物品表里 aux 0 那面、配方做出来的一样，算同一样东西。
本模块不 import 别的模块（生成器按路径载入它）
"""

BYTE, SHORT, INT, BYTES, STRING = 1, 2, 3, 7, 8
""" userData 里 __type__ 的取值：NBT 的标签类型（字节、短整数、整数、字节数组、字符串）"""

BANNER = "minecraft:banner"
BOOK = "minecraft:enchanted_book"
ROCKET = "minecraft:firework_rocket"
STAR = "minecraft:firework_star"

DYE_ORDER = (15, 7, 8, 0, 3, 1, 14, 11, 10, 2, 6, 12, 4, 5, 13, 9)
""" 创造栏的颜色顺序：白、淡灰、灰、黑、棕、红、橙、黄、黄绿、绿、青、淡蓝、蓝、紫、品红、粉红（值是染料下标：0 黑 … 15 白）"""

DYE_COLORS = (
    -14869215,  # 0 黑     #1D1D21
    -5231066,   # 1 红     #B02E26
    -10585066,  # 2 绿     #5E7C16
    -8170446,   # 3 棕     #835432
    -12827478,  # 4 蓝     #3C44AA
    -7785800,   # 5 紫     #8932B8
    -15295332,  # 6 青     #169C9C
    -6447721,   # 7 淡灰   #9D9D97
    -12103854,  # 8 灰     #474F52
    -816214,    # 9 粉红   #F38BAA
    -8337633,   # 10 黄绿  #80C71F
    -75715,     # 11 黄    #FED83D
    -12930086,  # 12 淡蓝  #3AB3DA
    -3715395,   # 13 品红  #C74EBD
    -425955,    # 14 橙    #F9801D
    -986896,    # 15 白    #F0F0F0
)
""" 染料下标 → 颜色，0xAARRGGBB 按有符号 32 位整数写（烟火之星的 customColor 就是它）"""

MOD_ENCHANT_ID = 255
""" 模组附魔在附魔书 userData 里的 id（EnchantType.ModEnchant），附魔的名字写在 modEnchant 里 """

ALL_BOOK_LEVELS = False
"""
附魔书只收每种附魔的最高级；改成 True 收 1 ~ 最高级的每一级（JEI / EMI 的做法）
"""

OMINOUS_BANNER_AUX = 15
""" 不祥旗帜：白色底（aux 15）+ {"Type": 1} """

PLAIN_REPLACED = (BOOK, ROCKET, STAR)
"""
这几样的原件（物品表里 aux 0、不带 userData 的那一样）创造栏里没有：没附魔的附魔书、没写飞行时间的烟花火箭、没上色的烟火之星。
这一族加上了的话，原件从物品栏藏起来（ItemManager.SetPlainHidden，带 userData 的照常显示）
"""

GROUPS = (
    ("minecraft:itemGroup.name.banner", "itemGroup.name.banner", (BANNER,)),
    ("minecraft:itemGroup.name.enchantedBook", "itemGroup.name.enchantedBook", (BOOK,)),
    ("minecraft:itemGroup.name.firework", "itemGroup.name.firework", (ROCKET,)),
    ("minecraft:itemGroup.name.fireworkStars", "itemGroup.name.fireworkStars", (STAR,)),
)
"""
这几族在创造栏里各是一个物品组（.lang 有 itemGroup.name.*，目录里没有），写法同 table.GROUPS：(组的键, .lang 的键, (物品 id, ...))；
一个 id 就是一组 —— 物品栏的分组按 id 记，同一个 id 的变体（41 本附魔书、16 色旗帜……）一起进组
"""


def typed(kind, value):  # type: (int, any) -> dict
    """ 带类型的一个值 """
    return {"__type__": kind, "__value__": value}


def book_data(enchant_id, level, mod_enchant=""):  # type: (int, int, str) -> dict
    """ 一本附魔书的 userData：一条附魔（modEnchant 是模组附魔的名字，原版给空串）"""
    return {"ench": [{"id": typed(SHORT, enchant_id), "lvl": typed(SHORT, level), "modEnchant": typed(STRING, mod_enchant)}]}


def mod_enchant_of(user_data):  # type: (any) -> str
    """ 一本附魔书 userData 里的模组附魔名（book_data 写的那样）；原版附魔、认不出给空串 """
    try:
        return user_data["ench"][0]["modEnchant"]["__value__"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _native(text):  # type: (any) -> str or None
    """ 递给引擎的字符串一律 str（unicode 引擎安静地认不出）；不是字符串、空串给 None """
    if isinstance(text, unicode):
        text = text.encode("utf-8")
    return text if isinstance(text, str) and text else None


def _level(value):  # type: (any) -> int
    if isinstance(value, bool) or not isinstance(value, (int, long)):
        return 0
    return max(0, int(value))


def split_enchants(enchants):  # type: (any) -> tuple
    """
    引擎给的附魔信息（GetAllEnchantsInfo：[{"identifier", "max_level", ...}]）→
    ([(原版附魔的 id, 最高等级)], [(模组附魔的名字, 最高等级)], [排不出 id 的名字])。
    原版附魔排在最前、照 EnchantType 的 id 排（protection 在 0）、名字不带命名空间 —— 在表里的下标就是 id；
    带命名空间的是模组附魔（「minecraft:」开头的照原版算）。模组附魔之后又出现不带命名空间的，排不出 id，单独给出来。
    最高等级照引擎的 max_level，没给按 1；同一个名字只认第一次
    """
    vanilla, mods, skipped, seen = [], [], [], set()
    modded = False
    for index, info in enumerate(enchants or ()):
        name = _native(info.get("identifier")) if isinstance(info, dict) else None
        if name is None or name in seen:
            continue
        seen.add(name)
        top = _level(info.get("max_level")) or 1
        bare = name[len("minecraft:"):] if name.startswith("minecraft:") else name
        if ":" in bare:
            modded = True
            mods.append((name, top))
        elif modded:
            skipped.append(bare)
        else:
            vanilla.append((index, top))
    return vanilla, mods, skipped


def book_rows(enchants):  # type: (any) -> list
    """ 附魔书那一族：[(物品 id, aux, userData)]，原版的照 id 排在前、模组的照引擎给的先后接在后面；没有附魔信息就没有 """
    vanilla, mods, _skipped = split_enchants(enchants)
    rows = []
    for enchant_id, top in vanilla:
        rows.extend((BOOK, 0, book_data(enchant_id, level)) for level in book_levels(top))
    for name, top in mods:
        rows.extend((BOOK, 0, book_data(MOD_ENCHANT_ID, level, name)) for level in book_levels(top))
    return rows


def book_levels(top):  # type: (int) -> list
    """ 一种附魔出哪几级的书：缺省只出最高级，ALL_BOOK_LEVELS 打开出每一级 """
    return range(1, top + 1) if ALL_BOOK_LEVELS else [top]


def explosion(dye):  # type: (int) -> dict
    """ 烟火之星的效果：小型球状、这一种颜色，不淡出、不闪烁、没有拖尾 """
    return {
        "FireworkColor": typed(BYTES, [dye]),
        "FireworkFade": typed(BYTES, []),
        "FireworkFlicker": typed(BYTE, 0),
        "FireworkTrail": typed(BYTE, 0),
        "FireworkType": typed(BYTE, 0),
    }


def rocket_data(dye=None):  # type: (int or None) -> dict
    """ 一支烟花火箭的 userData：飞行时间 1；dye 给了就带一颗这种颜色的烟火之星 """
    return {"Fireworks": {"Flight": typed(BYTE, 1), "Explosions": [explosion(dye)] if dye is not None else []}}


def star_data(dye):  # type: (int) -> dict
    """ 一颗烟火之星的 userData：效果，加上物品图标上那一点的颜色 """
    return {"FireworksItem": explosion(dye), "customColor": typed(INT, DYE_COLORS[dye])}


def entries(enchants=None):  # type: (list or None) -> list
    """
    [(物品 id, aux, userData 或 None)]，每族照创造栏的顺序：旗帜 15 色（黑色 aux 0 物品表本来就有）+ 不祥旗帜、
    附魔书（book_rows，照引擎给的附魔信息；没给就没有）、烟花火箭（不带烟火之星的一支 + 16 色）、烟火之星 16 色（aux 就是染料下标）
    """
    rows = [(BANNER, dye, None) for dye in DYE_ORDER if dye]
    rows.append((BANNER, OMINOUS_BANNER_AUX, {"Type": typed(INT, 1)}))
    rows.extend(book_rows(enchants))
    rows.append((ROCKET, 0, rocket_data()))
    rows.extend((ROCKET, 0, rocket_data(dye)) for dye in DYE_ORDER)
    rows.extend((STAR, dye, star_data(dye)) for dye in DYE_ORDER)
    return rows
