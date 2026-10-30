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
  1. 造目标槽位（玩家侧的格子，targets.make_target）；
  2. 把「你的 handle 那份，搬 N 个到这个 target」派给对应的 ItemSource；
  3. 数成功了几格。

**搬运本身归来源做**（`ItemSource.MoveTo`）—— 只有来源知道怎么安全地从自己身上取，
框架横插一手就等于把每个来源的内部规则都学一遍。见 common/classes/base.py 的契约。

没有整单原子性（引擎没有移动物品的接口，quick_craft.md §5.4），
所以是**逐格提交**：某格失败就停下，前面成功的保持原样。
"""
from MEIScripts.common.classes.base import SlotTarget
from MEIScripts.common.classes.types.transfer import TransferResult
from MEIScripts.registry.transfer import TransferRegistry
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

from .targets import make_target

REASON_NO_SOURCE = "no_source"
""" 清单里点名的来源没注册 —— 客户端与服务端的来源表不一致 """

REASON_NO_TARGET = "no_target"
""" 造不出目标槽位 """

REASON_PUT_FAILED = "put_failed"
""" 来源报告搬了 0 个。容器被关了、材料被别人抢先拿走都会走到这 """

REASON_EMPTY = "empty"
""" 清单是空的 """

REASON_BAD_PLAN = "bad_plan"
""" 清单本身不对：太长、槽位不是整数或越界、要写的格子不在要清的那片里、数量不是正数、清单看不懂 """

REASON_UNTRUSTED = "untrusted"
""" 发起者不是引擎给的（HandlerContext.Trusted 为假）：客户端自己写的发起者能冒充别人 """

MAX_SLOTS = 64
""" 一张清单最多几条、最多清几格（工作台 9 格，再大的机器也用不了这么多）：防一个请求把服务端卡住 """

MAX_SLOT_INDEX = 128
""" 玩家侧槽位号的上限（工作台 32 ~ 40、背包 2x2 28 ~ 31）"""


def Execute(ctx, plan):  # type: (any, any) -> TransferResult
    """
    执行一张搬运清单，返回逐格统计的结果

    **先整片清空再填**：只清要放的那几格不够 —— 上一条配方留下的材料会和新的混在
    一起，玩家看到的是一个既不是旧配方也不是新配方的网格。要清哪些格由客户端在
    plan.ClearSlots 里算好带过来（服务端没有转移策略，问不出容器布局）。
    """
    if not plan.Entries:
        return TransferResult(0, 0, REASON_EMPTY)
    reason = check(plan)
    if reason:
        # 动任何格子之前就拒掉：清空在前，带着毛病的清单清完再失败，玩家的合成格就白清了
        logger.warn("[MEI/transfer] 清单不收（{}）: {}".format(reason, plan))
        return TransferResult(0, 0, reason)

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


def _slot_ok(slot):  # type: (any) -> bool
    return isinstance(slot, (int, long)) and not isinstance(slot, bool) and 0 <= slot < MAX_SLOT_INDEX


def check(plan):  # type: (any) -> str
    """
    动任何格子之前把整张清单核对一遍，返回失败原因（没问题给空串）：条数、清的格数有上限；
    槽位是玩家侧范围内的整数；每一条点名的来源服务端登记过、写的格子在要清的那片里、数量是正数
    """
    clear = plan.ClearSlots
    if len(plan.Entries) > MAX_SLOTS or len(clear) > MAX_SLOTS or not all(_slot_ok(slot) for slot in clear):
        return REASON_BAD_PLAN
    for entry in plan.Entries:
        if TransferRegistry.Get(entry.SourceId) is None:
            logger.error("[MEI/transfer] 清单点名了未注册的来源: {}".format(entry.SourceId))
            return REASON_NO_SOURCE
        if entry.Slot not in clear or entry.Count <= 0:
            return REASON_BAD_PLAN
    return ""


class _Expected(SlotTarget):
    """
    包一层目标：来源放进来的必须是清单这一条说的那样东西（id、aux），不是就不放 —— 来源看到放不进去，也就不扣。
    清单里的 handle 是客户端给的，指到哪一格都行：不核对的话，能把背包里任意一样东西搬进任意一格
    """

    def __init__(self, target, entry):
        self.Target = target
        self.Entry = entry
        self.Slot = target.Slot

    def Put(self, stack):  # type: (any) -> bool
        item = getattr(stack, "Item", None)
        if item is None or native_str(item.ItemId) != native_str(self.Entry.ItemId) \
                or int(item.AuxValue) != int(self.Entry.AuxValue):
            logger.error("[MEI/transfer] 来源给的 {} 不是清单这一条要的 {}".format(
                getattr(item, "ItemId", None), self.Entry))
            return False
        return self.Target.Put(stack)

    def Clear(self):  # type: () -> bool
        return self.Target.Clear()

    def Peek(self):  # type: () -> any
        return self.Target.Peek()

    def Restore(self, previous):  # type: (any) -> bool
        return self.Target.Restore(previous)


def _clear_all(ctx, plan):  # type: (any, any) -> None
    """ 整片清空。玩家侧由引擎把原有物品退回背包，背包满则掉在脚下（原版行为）"""
    for slot in plan.ClearSlots:
        make_target(ctx, slot).Clear()


def _fill_one(ctx, plan, entry):  # type: (any, any, any) -> tuple
    """ 填一格，返回 (成功与否, 失败原因) """
    source = TransferRegistry.Get(entry.SourceId)
    if source is None:
        logger.error("[MEI/transfer] 清单点名了未注册的来源: {}".format(entry.SourceId))
        return False, REASON_NO_SOURCE

    target = make_target(ctx, entry.Slot)
    if target is None:
        return False, REASON_NO_TARGET

    try:
        moved = int(source.MoveTo(ctx, entry.Handle, entry.Count, _Expected(target, entry)) or 0)
    except Exception as e:  # noqa  第三方来源的实现不可控, 一个坏来源不能带走整轮
        logger.error("[MEI/transfer] {} 的 MoveTo 抛异常: {}".format(entry.SourceId, error_text(e)))
        return False, REASON_PUT_FAILED

    if moved <= 0:
        return False, REASON_PUT_FAILED
    return True, ""
