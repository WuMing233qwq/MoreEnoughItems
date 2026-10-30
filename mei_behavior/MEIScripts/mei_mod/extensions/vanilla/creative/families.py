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
userData 一律用带类型的写法 {"__type__": NBT 类型, "__value__": 值}：普通字典引擎读不出来（附魔书显示「保护 0」、烟花「飞行时间：0」）。
颜色照创造栏的顺序排：旗帜、烟火之星的 aux 是染料下标、0 是黑色，床的 aux 0 却是白色 —— 照着床的 aux 数字排，颜色顺序就全乱了。
普通旗帜不带 userData（写成 {"Type": 0} 引擎也认）：和物品表里 aux 0 那面、配方做出来的一样，算同一样东西。
本模块不 import 别的模块（生成器按路径载入它，核对附魔种数）
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

ENCHANT_MAX_LEVEL = (
    4, 4, 4, 4, 4,  # 0 保护、1 火焰保护、2 摔落保护、3 爆炸保护、4 弹射物保护
    3, 3, 3, 1,     # 5 荆棘、6 水下呼吸、7 深海探索者、8 水下速掘
    5, 5, 5,        # 9 锋利、10 亡灵杀手、11 节肢杀手
    2, 2, 3,        # 12 击退、13 火焰附加、14 抢夺
    5, 1, 3, 3,     # 15 效率、16 精准采集、17 耐久、18 时运
    5, 2, 1, 1,     # 19 力量、20 冲击、21 火矢、22 无限
    3, 3, 2, 1,     # 23 海之眷顾、24 饵钓、25 冰霜行者、26 经验修补
    1, 1,           # 27 绑定诅咒、28 消失诅咒
    5, 3, 3, 1,     # 29 穿刺、30 激流、31 忠诚、32 引雷
    1, 4, 3,        # 33 多重射击、34 穿透、35 快速装填
    3, 3,           # 36 灵魂疾行、37 迅捷潜行
    3, 5, 4,        # 38 风爆、39 致密、40 破甲
)
"""
附魔（下标就是引擎 EnchantType 的 id）→ 最高等级。引擎不给最高等级、游戏目录里也没有，这是整个创造栏表里唯一手写的数：
原版加了新附魔就在末尾补一项（生成器换版本时会比 .lang 里的附魔种数，对不上就提醒）
"""

ALL_BOOK_LEVELS = False
"""
附魔书只收每种附魔的最高级（41 本）；改成 True 收 1 ~ 最高级的每一级（JEI / EMI 的做法，122 本）
"""

OMINOUS_BANNER_AUX = 15
""" 不祥旗帜：白色底（aux 15）+ {"Type": 1} """

PLAIN_REPLACED = (BOOK, ROCKET, STAR)
"""
这几样的原件（物品表里 aux 0、不带 userData 的那一样）创造栏里没有：没附魔的附魔书、没写飞行时间的烟花火箭、没上色的烟火之星。
这一族加上了的话，原件从物品栏藏起来（ItemManager.SetPlainHidden，带 userData 的照常显示）
"""


def typed(kind, value):  # type: (int, any) -> dict
    """ 带类型的一个值 """
    return {"__type__": kind, "__value__": value}


def book_data(enchant_id, level):  # type: (int, int) -> dict
    """ 一本附魔书的 userData：一条附魔（modEnchant 是模组附魔的名字，原版给空串）"""
    return {"ench": [{"id": typed(SHORT, enchant_id), "lvl": typed(SHORT, level), "modEnchant": typed(STRING, "")}]}


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


def entries(enchant_limit=None):  # type: (int or None) -> list
    """
    [(物品 id, aux, userData 或 None)]，每族照创造栏的顺序：旗帜 15 色（黑色 aux 0 物品表本来就有）+ 不祥旗帜、
    附魔书、烟花火箭（不带烟火之星的一支 + 16 色）、烟火之星 16 色（aux 就是染料下标）。
    enchant_limit 是引擎认识的附魔种数（EnchantType.NumEnchantments）：id 不小于它的附魔书不收 —— 表比游戏新的时候
    """
    rows = [(BANNER, dye, None) for dye in DYE_ORDER if dye]
    rows.append((BANNER, OMINOUS_BANNER_AUX, {"Type": typed(INT, 1)}))
    for enchant_id, top in enumerate(ENCHANT_MAX_LEVEL):
        if enchant_limit is not None and enchant_id >= enchant_limit:
            break
        levels = range(1, top + 1) if ALL_BOOK_LEVELS else (top,)
        rows.extend((BOOK, 0, book_data(enchant_id, level)) for level in levels)
    rows.append((ROCKET, 0, rocket_data()))
    rows.extend((ROCKET, 0, rocket_data(dye)) for dye in DYE_ORDER)
    rows.extend((STAR, dye, star_data(dye)) for dye in DYE_ORDER)
    return rows
