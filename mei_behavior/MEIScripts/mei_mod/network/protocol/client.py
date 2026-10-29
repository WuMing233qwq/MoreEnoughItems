# coding=utf-8

# ----------------------------------------------------------------------
#  client.py is part of MoreEnoughItems.
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
客户端侧的请求发起口 —— UI 层只调这里，不必认识 Channel 与 MainSys。

拿 Channel 的方式刻意做成**运行期查一次**而不是 import 期持有：
客户端 MainSys 是引擎造的，import 期它还不存在。
"""
from MEIScripts.common.classes.types.transfer import TransferPlan, TransferResult
from MEIScripts.mei_mod.transfer import index_supply, max_multiplier, plan_entries
from MEIScripts.registry.transfer import TransferRegistry
from MEIScripts.utils.log import logger

from ..base import KEY_BODY, KEY_ERROR, KEY_OK
from .transfer import REQUEST_TRANSFER


def _channel():  # type: () -> any
    """ 取客户端 MainSys 上的 Channel，取不到返回 None """
    import mod.client.extraClientApi as clientApi
    from MEIScripts.constants.codes import NameConst
    system = clientApi.GetSystem(NameConst.NameSpace, NameConst.ClientSysName)
    return getattr(system, "Channel", None) if system else None


def BuildPlan(category, recipe, ctx, multiplier=None):
    # type: (any, any, any, int) -> TransferPlan or None
    """
    算一张搬运清单。凑不齐或装不下返回 None —— **不做半张单**

    「配方怎么摊到容器槽位上」整个交给转移策略的 MapRecipe：
    有序配方的形状换算、无序配方的摊平，都是那一层的事，本函数不猜。

    multiplier 是"这条配方做几次"；**传 None 表示最大化** —— 由 max_multiplier
    按"材料够几倍"与"格子放得下几倍"两个上限算出来。
    """
    policy = category.Transfer
    if policy is None or not policy.CanTransfer(ctx):
        return None

    mapped = policy.MapRecipe(ctx, recipe)
    if not mapped:
        logger.info("[MEI/transfer] 当前容器装不下这条配方")
        return None

    supply = index_supply(TransferRegistry.Collect(ctx))
    if multiplier is None:
        multiplier = max_multiplier(mapped, supply)
        if multiplier <= 0:
            logger.info("[MEI/transfer] 材料不足, 一次都做不了")
            return None

    entries, missing = plan_entries(mapped, supply, multiplier)
    if missing:
        logger.info("[MEI/transfer] 材料不足, 缺 {} 个格位".format(len(missing)))
        return None
    return TransferPlan(kind=policy.Kind, entries=entries,
                        position=ctx.Position, dimension=ctx.Dimension,
                        clear_slots=policy.AllSlots(ctx))


def SendTransfer(plan, on_result):  # type: (TransferPlan, any) -> bool
    """
    把清单发给服务端。on_result(TransferResult) 在回执或**超时**时调一次

    超时也会回调 —— 忽略它就等于"按钮点了没反应"(base/channel.py 的契约)。
    """
    channel = _channel()
    if channel is None:
        logger.error("[MEI/transfer] 拿不到客户端 Channel, 转移取消")
        return False

    def __on_reply(response):
        if not response.get(KEY_OK):
            logger.error("[MEI/transfer] 转移失败: {}".format(response.get(KEY_ERROR)))
            on_result(TransferResult(0, len(plan.Entries), response.get(KEY_ERROR, "")))
            return
        on_result(TransferResult.from_dict(response.get(KEY_BODY)))

    channel.Request(REQUEST_TRANSFER, plan.to_dict(), on_reply=__on_reply)
    return True
