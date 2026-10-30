# coding=utf-8

# ----------------------------------------------------------------------
#  inventory.py is part of MoreEnoughItems.
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
内置物品来源：玩家背包。**给第三方存储模组看的参考实现**。

两件事按 ctx.Side 分流：
  · 客户端只 Collect（预检按钮亮不亮），客户端版 GetPlayerAllItems 只能读本地玩家；
  · 服务端 Collect + MoveTo，**且服务端的 Collect 才是真理** —— 客户端说的一律重算。

handle 是**背包槽位号**（int）。它要过跨端边界，故必须是标量（引擎结论 §6）。
"""
from MEIScripts.common.classes.base import ItemSource
from MEIScripts.common.classes.types import Item, ItemAttr, ItemStack
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

SOURCE_ID = "mei:inventory"
""" 内置来源的标识 """


def _enum():
    """ ItemPosType 两端都有，按 Side 取对应的 api 模块 """
    import mod.server.extraServerApi as serverApi
    return serverApi.GetMinecraftEnum()


def _server_comp(player_id):
    import mod.server.extraServerApi as serverApi
    return serverApi.GetEngineCompFactory().CreateItem(player_id)


def _client_comp(player_id):
    import mod.client.extraClientApi as clientApi
    return clientApi.GetEngineCompFactory().CreateItem(player_id)


class InventorySource(ItemSource):
    """ 玩家背包。优先级最高 —— 手边的东西先用 """

    Id = SOURCE_ID
    Priority = 0

    def Collect(self, ctx):  # type: (any) -> list
        """ 列出背包里的东西，返回 [(ItemStack, 槽位号), ...]，空格跳过 """
        try:
            comp = (_server_comp(ctx.PlayerId) if ctx.Side == "server"
                    else _client_comp(ctx.PlayerId))
            items = comp.GetPlayerAllItems(_enum().ItemPosType.INVENTORY, False)
        except Exception as e:  # noqa  读不到就当没有, 不能让预检把界面带崩
            logger.error("[MEI/transfer] 读背包失败: {}".format(error_text(e)))
            return []

        collected = []
        for slot, item_dict in enumerate(items or ()):
            stack = self.__ToStack(item_dict)
            if stack is not None:
                collected.append((stack, slot))
        return collected

    def MoveTo(self, ctx, handle, count, target):  # type: (any, any, int, any) -> int
        """
        从背包第 handle 格搬 count 个到 target，返回实际搬了几个

        **先放后扣**：`target.Put` 是唯一会失败且原因不可控的一步(容器被关了)，
        把它放前面，失败时玩家的背包还没动过。扣减 SetInvItemNum 失败（抛异常或返回 False）的话，
        目标格里多出来的就是复制出来的 —— 按放之前的样子写回去（Restore）；撤不回才大声报错。
        搬的是这一格原样的东西：带 userData 读、附魔 / 耐久 / 自定义名字 / userData 原样写过去（targets._to_dict）
        """
        if ctx.Side != "server":
            logger.error("[MEI/transfer] MoveTo 只能在服务端调")
            return 0
        if isinstance(handle, bool) or not isinstance(handle, (int, long)):
            return 0

        slot = int(handle)
        comp = _server_comp(ctx.PlayerId)
        item_dict = self.__Read(comp, slot)
        if item_dict is None:
            return 0

        have = int(item_dict.get("count", 0) or 0)
        take = min(have, int(count))
        if take <= 0:
            return 0

        stack = self.__ToStack(item_dict, with_attr=True)
        if stack is None:
            return 0
        stack.Count = take

        previous = target.Peek()
        if not target.Put(stack):
            return 0

        deducted = False
        try:
            deducted = bool(comp.SetInvItemNum(slot, have - take))
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 扣减背包槽位 {} 抛异常: {}".format(slot, error_text(e)))
        if deducted:
            return take
        if target.Restore(previous):
            logger.error("[MEI/transfer] 背包槽位 {} 扣不掉，已撤回放进目标格的那些".format(slot))
            return 0
        logger.error("[MEI/transfer] **扣减失败、目标格也撤不回，可能已复制物品** 槽位 {}".format(slot))
        return take

    # 内部
# ======================================================================================================================
    @staticmethod
    def __Read(comp, slot):  # type: (any, int) -> dict or None
        """ 带 userData 读：搬过去的要和这一格一模一样 """
        try:
            import mod.server.extraServerApi as serverApi
            return comp.GetPlayerItem(
                serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slot, True)
        except Exception as e:  # noqa
            logger.error("[MEI/transfer] 读背包槽位 {} 失败: {}".format(slot, error_text(e)))
            return None

    @staticmethod
    def __ToStack(item_dict, with_attr=False):  # type: (dict, bool) -> any
        """ 引擎 itemDict -> ItemStack。空气与零数量视为空格；with_attr 带上附魔、耐久、userData 这些（搬运时要原样写过去）"""
        if not item_dict:
            return None
        item_id = item_dict.get("newItemName") or item_dict.get("itemName")
        count = int(item_dict.get("count", 0) or 0)
        if not item_id or count <= 0 or item_id == "minecraft:air":
            return None
        # 不走 ItemFactory.CreateItem: 那条要过 ItemManager.LookUpItem, 而服务端没有物品表.
        # 背包里真有的东西不需要 MEI 的表来认证(item_model.md §6 的同一条理由)
        aux = int(item_dict.get("newAuxValue", item_dict.get("auxValue", 0)) or 0)
        attr = None
        if with_attr:
            attr = ItemAttr(
                user_data=item_dict.get("userData"),
                show_in_hand=item_dict.get("showInHand", True) is not False,
                enchant_data=item_dict.get("enchantData"),
                mod_enchant_data=item_dict.get("modEnchantData"),
                custom_tips=item_dict.get("customTips") or "",
                extra_id=item_dict.get("extraId") or "",
                durability=item_dict.get("durability") or 0,
            )
        return ItemStack(Item(item_id=item_id, aux_value=aux, attr=attr), count)


EXPORT = InventorySource
""" 装配方按这个名字取，与 vanilla 扩展的 EXTENSION 同一个约定 """
