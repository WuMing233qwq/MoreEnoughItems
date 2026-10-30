# coding=utf-8

# ----------------------------------------------------------------------
#  targets.py is part of MoreEnoughItems.
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
可写目标槽位的实现 —— **服务端**。只有玩家侧的格子（工作台 32~40、背包 2×2 28~31）：
SetPlayerUIItem 只让写玩家开着的那个界面，等于引擎替我们核对了「开着哪个容器」。
方块容器（熔炉、箱子、别的模组的机器）MEI 不写 —— 坐标只能客户端给、服务端核对不了，直写还绕过模组自己的校验与同步；
往模组机器里搬交给它自己的转移处理器（ctx.UI.Transfers，docs/architecture/quick_craft.md §10）。
"""
import mod.server.extraServerApi as serverApi

from MEIScripts.common.classes.base import SlotTarget
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str, to_native

ATTR_KEYS = (
    ("UserData", "userData"),
    ("EnchantData", "enchantData"),
    ("ModEnchantData", "modEnchantData"),
    ("CustomTips", "customTips"),
    ("ExtraId", "extraId"),
    ("Durability", "durability"),
)
"""
ItemAttr 的字段 → 引擎物品信息字典的键。写进槽位时这几样一样不落（只写 id、aux、数量的话，附魔、耐久、自定义名字、
userData 里的潜影盒内容、烟火之星的效果全丢 —— 损坏的工具搬进合成格就成了新的）；同一格累加时这几样也要都一样才算同一种东西
"""


def _item_comp():
    """ 容器接口挂 LevelId，不是 playerId —— 两条路径都一样 """
    return serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())


def _to_dict(stack, count=None):  # type: (any, int) -> dict
    """ ItemStack -> 引擎的 itemDict，带上 ItemAttr 里有的那几样（ATTR_KEYS）。递给引擎的字符串必须是 str 不能是 unicode """
    item = stack.Item
    data = {"itemName": native_str(item.ItemId), "auxValue": int(item.AuxValue),
            "count": int(stack.Count if count is None else count)}
    attr = getattr(item, "Attr", None)
    for field, key in ATTR_KEYS:
        value = getattr(attr, field, None)
        if value:
            data[key] = to_native(value)
    if attr is not None and getattr(attr, "ShowInHand", True) is False:
        data["showInHand"] = False
    return data


def _plain(value):  # type: (any) -> any
    """ 比较用：unicode 收成 str、tuple 与 list 一样、dict 不论键的先后 """
    if isinstance(value, dict):
        return tuple(sorted((native_str(key), _plain(one)) for key, one in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_plain(one) for one in value)
    return native_str(value)


def _identity(item_dict):  # type: (dict) -> tuple
    """ 一格里是什么东西（不算数量）：id、aux 与 ATTR_KEYS 那几样，空的都当没有 """
    item_id = item_dict.get("newItemName") or item_dict.get("itemName")
    aux = int(item_dict.get("newAuxValue", item_dict.get("auxValue", 0)) or 0)
    extras = tuple((key, _plain(item_dict.get(key))) for _field, key in ATTR_KEYS if item_dict.get(key))
    return native_str(item_id), aux, extras


def _merged_count(existing, stack):  # type: (dict, any) -> int or None
    """
    算出"写进去之后这一格应该有几个"。**同物品累加，异物品返回 None（拒绝）**

    为什么要累加而不是覆盖：最大化转移时**一格的需求可能来自多个背包槽** ——
    要 32 个木板而背包里是 20+12 两摞，清单里就是同一个目标槽位的两条 entry。
    覆盖写的话只有最后一摞落地，前面的被吃掉（而来源那边已经扣了）。
    倍数为 1 时每格只要 1 个、只会有一条 entry，所以这个坑到最大化转移才暴露。
    """
    if not existing or int(existing.get("count", 0) or 0) <= 0:
        return int(stack.Count)
    if _identity(existing) != _identity(_to_dict(stack)):
        # 清单把两种物品（或同一种物品的两个变体：附魔、耐久、userData 不一样）排到了同一格 —— 那是规划错了，
        # 覆盖会白吃掉一摞、合并会抹掉一边的数据。拒绝并让来源知道(它就不会扣), 比悄悄丢东西好
        return None
    return int(existing.get("count", 0) or 0) + int(stack.Count)


class PlayerSlotTarget(SlotTarget):
    """
    玩家侧槽位：工作台 32~40(行优先)、背包 2x2 28~31，以及铁砧/附魔台等

    引擎自带时序保护：**没打开容器或打开了别的容器，写入直接返回 False**，
    所以这里不必自己判"现在能不能写"。
    """

    def __init__(self, player_id, slot):  # type: (str, int) -> None
        self.PlayerId = player_id
        self.Slot = int(slot)

    def Put(self, stack):  # type: (any) -> bool
        try:
            total = _merged_count(self.Peek(), stack)
            if total is None:
                logger.error("[MEI/transfer] 槽位 {} 已有别的物品, 拒绝覆盖".format(self.Slot))
                return False
            return bool(_item_comp().SetPlayerUIItem(
                self.PlayerId, self.Slot, _to_dict(stack, total), False))
        except Exception as e:  # noqa  写失败不能把整轮搬运带走
            logger.error("[MEI/transfer] 写玩家槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return False

    def Clear(self):  # type: () -> bool
        """ 腾空并把原有物品退回背包 —— needBack=True 时由**引擎**负责退回 """
        # 背包满了引擎会在玩家脚下生成掉落物, 那是原版行为, 不必自己算空位
        try:
            return bool(_item_comp().SetPlayerUIItem(
                self.PlayerId, self.Slot, None, True))
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 腾空玩家槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return False

    def Peek(self):  # type: () -> any
        """ 带 userData 读（累加前要比 userData、撤回时要原样写回）"""
        try:
            return _item_comp().GetPlayerUIItem(self.PlayerId, self.Slot, True)
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 读玩家槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return None

    def Restore(self, previous):  # type: (any) -> bool
        """ 写回 previous、不退回背包（needBack=False）：撤回刚放进来的那些 """
        try:
            return bool(_item_comp().SetPlayerUIItem(self.PlayerId, self.Slot, previous or None, False))
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 撤回玩家槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return False


def make_target(ctx, slot):  # type: (any, int) -> SlotTarget
    """ 造目标槽位（玩家侧）"""
    return PlayerSlotTarget(ctx.PlayerId, slot)
