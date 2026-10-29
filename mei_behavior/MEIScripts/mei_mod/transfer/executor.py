# coding=utf-8

# ----------------------------------------------------------------------
#  executor.py is part of MoreEnoughItems.
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
搬运的**派发者** —— 服务端。它自己不搬东西。

职责只有三件：
  1. 造目标槽位（决定走玩家侧还是方块侧）；
  2. 把「你的 handle 那份，搬 N 个到这个 target」派给对应的 ItemSource；
  3. 数成功了几格。

**搬运本身归来源做**（`ItemSource.MoveTo`）—— 只有来源知道怎么安全地从自己身上取，
框架横插一手就等于把每个来源的内部规则都学一遍。见 common/classes/base.py 的契约。

没有整单原子性（引擎没有移动物品的接口，quick_craft.md §5.4），
所以是**逐格提交**：某格失败就停下，前面成功的保持原样。
"""
from MEIScripts.common.classes.types.transfer import TransferResult
from MEIScripts.registry.transfer import TransferRegistry
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from .targets import make_target

REASON_NO_SOURCE = "no_source"
""" 清单里点名的来源没注册 —— 客户端与服务端的来源表不一致 """

REASON_NO_TARGET = "no_target"
""" 造不出目标槽位，通常是方块目标缺坐标 """

REASON_PUT_FAILED = "put_failed"
""" 来源报告搬了 0 个。容器被关了、材料被别人抢先拿走都会走到这 """

REASON_EMPTY = "empty"
""" 清单是空的 """


def Execute(ctx, plan):  # type: (any, any) -> TransferResult
    """
    执行一张搬运清单，返回逐格统计的结果

    **先整片清空再填**：只清要放的那几格不够 —— 上一条配方留下的材料会和新的混在
    一起，玩家看到的是一个既不是旧配方也不是新配方的网格。要清哪些格由客户端在
    plan.ClearSlots 里算好带过来（服务端没有转移策略，问不出容器布局）。
    """
    if not plan.Entries:
        return TransferResult(0, 0, REASON_EMPTY)

    _clear_all(ctx, plan)

    filled = 0
    for entry in plan.Entries:
        ok, reason = _fill_one(ctx, plan, entry)
        if ok:
            filled += 1
            continue
        # 逐格提交: 停在这一格, 前面成功的保持原样. 不回滚 —— 回滚需要回滚
        return TransferResult(filled, 1, reason)
    return TransferResult(filled, 0, "")


def _clear_all(ctx, plan):  # type: (any, any) -> None
    """ 整片清空。玩家侧由引擎把原有物品退回背包，背包满则掉在脚下（原版行为）"""
    for slot in plan.ClearSlots:
        target = make_target(ctx, plan.Kind, slot)
        if target is not None:
            target.Clear()


def _fill_one(ctx, plan, entry):  # type: (any, any, any) -> tuple
    """ 填一格，返回 (成功与否, 失败原因) """
    source = TransferRegistry.Get(entry.SourceId)
    if source is None:
        logger.error("[MEI/transfer] 清单点名了未注册的来源: {}".format(entry.SourceId))
        return False, REASON_NO_SOURCE

    target = make_target(ctx, plan.Kind, entry.Slot)
    if target is None:
        return False, REASON_NO_TARGET

    try:
        moved = int(source.MoveTo(ctx, entry.Handle, entry.Count, target) or 0)
    except Exception as e:  # noqa  第三方来源的实现不可控, 一个坏来源不能带走整轮
        logger.error("[MEI/transfer] {} 的 MoveTo 抛异常: {}".format(entry.SourceId, error_text(e)))
        return False, REASON_PUT_FAILED

    if moved <= 0:
        return False, REASON_PUT_FAILED
    return True, ""
