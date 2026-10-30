# coding=utf-8

# ----------------------------------------------------------------------
#  transfer.py is part of MoreEnoughItems.
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
配方转移请求的协议定义与服务端处理器。

**协议在这里，轮子在 base/** —— base/ 不认识 "mei:transfer" 这个名字，
加一个新请求只要在本目录再放一个文件，base/ 一行都不用动。
"""
from MEIScripts.common.classes.types.transfer import TransferContext, TransferPlan, TransferResult
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from ..base import Handler

REQUEST_TRANSFER = "mei:transfer"
""" 请求名。客户端发清单，服务端核对后执行并回执 TransferResult """


class TransferService(object):
    """
    服务端侧的转移服务。挂在服务端 MainSys 上，由 Channel.RegisterAll 扫出处理器。

    **客户端报的一律不可信** —— 清单里的 handle 与数量都要由来源在服务端重新核对。
    但这不构成提权面：玩家手动把背包里的东西拖进合成格本来就能做，
    服务端只是在替他做同一件事(quick_craft.md §6.4)。所以：只认引擎给的发起者（ctx.Trusted）、
    方块容器的清单不收、整张清单先核对再动格子（executor.check）、搬的东西原样带着附魔与 userData（targets._to_dict）
    """

    @Handler(REQUEST_TRANSFER)
    def OnTransfer(self, ctx, body):  # type: (any, dict) -> dict
        from MEIScripts.mei_mod.transfer.executor import REASON_BAD_PLAN, REASON_UNTRUSTED, Execute

        if not getattr(ctx, "Trusted", False) or not ctx.PlayerId:
            return TransferResult(0, 0, REASON_UNTRUSTED).to_dict()
        try:
            plan = TransferPlan.from_dict(body if isinstance(body, dict) else {})
        except Exception as e:  # noqa  客户端给的看不懂（槽位不是数字、缺字段）：什么都不动
            logger.warn("[MEI/transfer] 清单看不懂: {}".format(error_text(e)))
            return TransferResult(0, 0, REASON_BAD_PLAN).to_dict()
        context = TransferContext(
            player_id=ctx.PlayerId, side="server",
            dimension=plan.Dimension, position=plan.Position)
        return Execute(context, plan).to_dict()
