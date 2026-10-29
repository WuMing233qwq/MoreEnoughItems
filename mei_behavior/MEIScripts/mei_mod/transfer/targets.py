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
两种可写目标槽位的实现 —— **服务端**。

判据是「这个槽位属于玩家还是属于方块」，不是「是不是原版」：
工作台九格关掉界面退回背包(归玩家)，熔炉输入栏关掉界面东西还在里面(归方块)。
详见 docs/architecture/quick_craft.md §5。
"""
import mod.server.extraServerApi as serverApi

from MEIScripts.common.classes.base import SlotTarget
from MEIScripts.common.classes.types.transfer import KIND_BLOCK, KIND_PLAYER
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text


def _item_comp():
    """ 容器接口挂 LevelId，不是 playerId —— 两条路径都一样 """
    return serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())


def _to_dict(stack, count=None):  # type: (any, int) -> dict
    """ ItemStack -> 引擎的 itemDict。递给引擎的字符串必须是 str 不能是 unicode """
    item = stack.Item
    return {"itemName": str(item.ItemId), "auxValue": int(item.AuxValue),
            "count": int(stack.Count if count is None else count)}


def _merged_count(existing, stack):  # type: (dict, any) -> int or None
    """
    算出"写进去之后这一格应该有几个"。**同物品累加，异物品返回 None（拒绝）**

    为什么要累加而不是覆盖：最大化转移时**一格的需求可能来自多个背包槽** ——
    要 32 个木板而背包里是 20+12 两摞，清单里就是同一个目标槽位的两条 entry。
    覆盖写的话只有最后一摞落地，前面的被吃掉（而来源那边已经扣了）。
    倍数为 1 时每格只要 1 个、只会有一条 entry，所以这个坑到最大化转移才暴露。
    """
    if not existing:
        return int(stack.Count)

    item = stack.Item
    exist_id = existing.get("newItemName") or existing.get("itemName")
    exist_aux = int(existing.get("newAuxValue", existing.get("auxValue", 0)) or 0)
    if exist_id != str(item.ItemId) or exist_aux != int(item.AuxValue):
        # 清单把两种物品排到了同一格 —— 那是规划错了, 覆盖会白吃掉一摞.
        # 拒绝并让来源知道(它就不会扣), 比悄悄丢东西好
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
        try:
            return _item_comp().GetPlayerUIItem(self.PlayerId, self.Slot, False)
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 读玩家槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return None


class BlockSlotTarget(SlotTarget):
    """
    方块容器槽位：熔炉、箱子、任何 `netease:block_container` 方块

    **第三方机器用了那个组件就自动可写**，不需要为 MEI 写代码。
    但引擎在这条路上**没有**时序保护，且直写会绕过模组的
    PlayerTryPutCustomContainerItemServerEvent 校验 ——
    所以"哪几个槽位可写"必须由 TransferPolicy 说了算，不能乱塞。
    """

    def __init__(self, dimension, position, slot):  # type: (int, any, int) -> None
        self.Dimension = int(dimension)
        self.Position = tuple(position)
        self.Slot = int(slot)

    def Put(self, stack):  # type: (any) -> bool
        try:
            # SpawnItemToContainer 会不会自己合并未经实测, 所以按 Player 侧同样处理 ——
            # 假设它合并而实际是覆盖, 丢的是玩家的东西
            total = _merged_count(self.Peek(), stack)
            if total is None:
                logger.error("[MEI/transfer] 方块槽位 {} 已有别的物品, 拒绝覆盖".format(self.Slot))
                return False
            return bool(_item_comp().SpawnItemToContainer(
                _to_dict(stack, total), self.Slot, self.Position, self.Dimension))
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 写方块槽位 {}@{} 失败: {}".format(
                self.Slot, self.Position, error_text(e)))
            return False

    def Clear(self):  # type: () -> bool
        """ count=0 视为清空。**不退回玩家** —— 方块里的东西不归玩家 """
        try:
            return bool(_item_comp().SpawnItemToContainer(
                {"itemName": "minecraft:air", "count": 0, "auxValue": 0},
                self.Slot, self.Position, self.Dimension))
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 清方块槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return False

    def Peek(self):  # type: () -> any
        try:
            return _item_comp().GetContainerItem(
                self.Position, self.Slot, self.Dimension, False)
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 读方块槽位 {} 失败: {}".format(self.Slot, error_text(e)))
            return None


def make_target(ctx, kind, slot):  # type: (any, str, int) -> SlotTarget or None
    """ 按 Kind 造对应的目标。**这是全项目唯一决定走哪条写入路径的地方** """
    if kind == KIND_PLAYER:
        return PlayerSlotTarget(ctx.PlayerId, slot)
    if kind == KIND_BLOCK:
        if not ctx.Position:
            logger.error("[MEI/transfer] 方块目标缺坐标, 无法定位容器")
            return None
        return BlockSlotTarget(ctx.Dimension, ctx.Position, slot)
    logger.error("[MEI/transfer] 未知的目标种类: {}".format(kind))
    return None
