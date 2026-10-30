# coding=utf-8

# ----------------------------------------------------------------------
#  cheat.py is part of MoreEnoughItems.
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
作弊模式的两个请求（docs/architecture/modes.md）：问自己是不是操作员、给自己一样物品。

**两个都在服务端按引擎给的发起者鉴权**（HandlerContext.Trusted：服务端收客户端事件时引擎自带 "__id__"；
客户端自己写的 "__from" 能冒充别人，不认）。给物品之前再查一次操作员（GetPlayerOperation() == 2）——
客户端开界面时问的那一次只决定模式按钮能不能轮到作弊，不算数。
给多少由服务端定：客户端只说要一组还是一个；一组 = 这样物品的最大堆叠（GetItemBasicInfo 给 0 的按 64）。背包放不下的掉在脚下。
服务端接口一律在处理器里才 import：本模块客户端也要 import（拿请求名）。
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

from ..base import Handler

REQUEST_CHEAT_ACCESS = "mei:cheat_access"
""" 问服务端：我是不是操作员。回 {"allowed": bool} """

REQUEST_CHEAT_GIVE = "mei:cheat_give"
"""
给我一样物品。请求 {"item": "ns:id", "aux": int, "all": bool（一组还是一个）, "user_data": dict（可选，物品自带的）}；
回 {"allowed": bool, "given": 给了几个, "where": "inv" / "ground" / ""}
"""

OPERATOR = 2
""" GetPlayerOperation 的返回：访客 0、成员 1、操作员 2、自定义 3 —— 只认操作员 """

DEFAULT_STACK = 64
""" 最大堆叠读不到（引擎给 0，CLAUDE.md 引擎结论 §11）时按它 """


def is_operator(player_id):  # type: (str) -> bool
    """ 这个玩家现在是不是操作员；查不到按不是 """
    import mod.server.extraServerApi as serverApi
    try:
        return serverApi.GetEngineCompFactory().CreatePlayer(player_id).GetPlayerOperation() == OPERATOR
    except Exception as e:  # noqa
        logger.error("[MEI/cheat] 查不到 {} 的权限: {}".format(player_id, error_text(e)))
        return False


def max_stack(item_name, aux):  # type: (str, int) -> int
    import mod.server.extraServerApi as serverApi
    try:
        info = serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId()).GetItemBasicInfo(item_name, aux)
        size = int((info or {}).get("maxStackSize") or 0)
    except Exception:  # noqa  拿不到就按 64，给多了引擎自己会截
        size = 0
    return size if size > 0 else DEFAULT_STACK


def make_item_dict(body, stack_of=max_stack):  # type: (dict, any) -> dict or None
    """ 请求里的物品 → 物品信息字典（itemName / auxValue / count / userData）；不像个物品给 None """
    body = body if isinstance(body, dict) else {}
    name = body.get("item")
    if not isinstance(name, basestring) or ":" not in name:
        return None
    name = native_str(name)  # 递给引擎的必须是 str：unicode 不抛不报、只是给不出来（CLAUDE.md 引擎结论 §2）
    try:
        aux = int(body.get("aux") or 0)
    except (TypeError, ValueError):
        return None
    item = {"itemName": name, "auxValue": aux, "count": stack_of(name, aux) if body.get("all") else 1}
    user_data = body.get("user_data")
    if isinstance(user_data, dict) and user_data:
        item["userData"] = user_data
    return item


class CheatService(object):
    """ 服务端侧的作弊服务。挂在服务端 MainSys 上，由 Channel.RegisterAll 扫出处理器 """

    def __init__(self, system=None):
        self.System = system  # type: any  # 服务端 MainSys：背包放不下时用它的 CreateEngineItemEntity 掉在脚下

    @staticmethod
    def Allowed(ctx):  # type: (any) -> bool
        """ 发起者是引擎给的、而且现在是操作员 """
        return bool(getattr(ctx, "Trusted", False)) and bool(ctx.PlayerId) and is_operator(ctx.PlayerId)

    @Handler(REQUEST_CHEAT_ACCESS)
    def OnAccess(self, ctx, _body):  # type: (any, dict) -> dict
        return {"allowed": self.Allowed(ctx)}

    @Handler(REQUEST_CHEAT_GIVE)
    def OnGive(self, ctx, body):  # type: (any, dict) -> dict
        if not self.Allowed(ctx):
            logger.warn("[MEI/cheat] {} 不是操作员（或者发起者不是引擎给的），不给".format(ctx.PlayerId))
            return {"allowed": False, "given": 0, "where": ""}
        item = make_item_dict(body)
        if item is None:
            return {"allowed": True, "given": 0, "where": ""}
        return {"allowed": True, "given": item["count"], "where": self.Give(ctx.PlayerId, item)}

    def Give(self, player_id, item):  # type: (str, dict) -> str
        """ 先进背包；放不下掉在脚下。返回落在哪（"inv" / "ground"），都不成给空串 """
        import mod.server.extraServerApi as serverApi
        factory = serverApi.GetEngineCompFactory()
        try:
            if factory.CreateItem(serverApi.GetLevelId()).SpawnItemToPlayerInv(dict(item), player_id):
                return "inv"
        except Exception as e:  # noqa
            logger.error("[MEI/cheat] 给 {} 放进背包失败: {}".format(item.get("itemName"), error_text(e)))
        try:
            pos = factory.CreatePos(player_id).GetFootPos()
            dimension = factory.CreateDimension(player_id).GetEntityDimensionId()
            create = getattr(self.System, "CreateEngineItemEntity", None)
            if callable(create) and create(dict(item), dimension, pos):
                return "ground"
            if factory.CreateItem(serverApi.GetLevelId()).SpawnItemToLevel(dict(item), dimension, pos):
                return "ground"
        except Exception as e:  # noqa
            logger.error("[MEI/cheat] 给 {} 掉在脚下失败: {}".format(item.get("itemName"), error_text(e)))
        return ""
