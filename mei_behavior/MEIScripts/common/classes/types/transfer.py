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
配方转移的数据形状。纯数据零引擎，两端共用 —— 客户端算出来、服务端核对并执行。
"""

KIND_PLAYER = "player"
""" 槽位归玩家：工作台九格、背包 2x2。走 SetPlayerUIItem """

KIND_BLOCK = "block"
""" 槽位归方块：熔炉、任何 netease:block_container。走 SpawnItemToContainer """


class TransferContext(object):
    """
    一次转移的环境。纯数据 —— 两端各自填好后交给 ItemSource / SlotTarget

    Side 存在的理由：同一个来源在两端要做不同的事（客户端只 Collect 用于预检，
    服务端才真搬），来源自己按它分流，框架不替它判断。
    """

    __slots__ = ("PlayerId", "Side", "Dimension", "Position", "Extra")

    def __init__(self, player_id="", side="client", dimension=0, position=None, extra=None):
        # type: (str, str, int, any, dict) -> None
        self.PlayerId = player_id
        self.Side = side              # type: str  # "client" / "server"
        self.Dimension = int(dimension or 0)
        self.Position = position      # type: any  # (x, y, z)，仅方块容器有意义
        self.Extra = extra or {}      # type: dict # 第三方自己塞的东西，框架不解释

    def __repr__(self):
        return "<TransferContext {} {}>".format(self.Side, self.PlayerId)


class TransferEntry(object):
    """
    搬运清单里的一条：把 Count 个 Item 从 SourceId/Handle 搬到 Slot

    Handle 是来源自己的凭据，本类**不解释它**，只负责带过跨端边界 ——
    所以它必须是 dict/list/标量（引擎结论 §6）。
    """

    __slots__ = ("Slot", "ItemId", "AuxValue", "Count", "SourceId", "Handle")

    def __init__(self, slot, item_id, aux_value=0, count=1, source_id="", handle=None):
        # type: (int, str, int, int, str, any) -> None
        self.Slot = int(slot)
        self.ItemId = item_id
        self.AuxValue = int(aux_value or 0)
        self.Count = int(count)
        self.SourceId = source_id
        self.Handle = handle

    def to_dict(self):  # type: () -> dict
        return {"slot": self.Slot, "id": self.ItemId, "aux": self.AuxValue,
                "count": self.Count, "src": self.SourceId, "handle": self.Handle}

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> TransferEntry
        return cls(data["slot"], data["id"], data.get("aux", 0),
                   data.get("count", 1), data.get("src", ""), data.get("handle"))

    def __repr__(self):
        return "<TransferEntry {}x{} -> slot {}>".format(self.ItemId, self.Count, self.Slot)


class TransferPlan(object):
    """
    一次转移的完整请求。**客户端算，服务端核对后执行** —— 客户端说的一律不可信。

    Kind 决定走哪条写入路径；Position 只有 KIND_BLOCK 才有意义。
    """

    __slots__ = ("Kind", "Entries", "Position", "Dimension", "ClearSlots")

    def __init__(self, kind=KIND_PLAYER, entries=None, position=None, dimension=0,
                 clear_slots=None):
        # type: (str, list, any, int, list) -> None
        self.Kind = kind
        self.Entries = list(entries or ())  # type: list

        self.ClearSlots = list(clear_slots or ())  # type: list
        """
        转移前要整片清空的槽位。**由客户端算好带过来** ——
        服务端没有 Category 也没有转移策略（扩展只在客户端装配），
        它问不出"这个容器有哪些输入格"。
        """
        self.Position = position            # type: any  # (x, y, z)，仅 KIND_BLOCK
        self.Dimension = int(dimension or 0)

    def to_dict(self):  # type: () -> dict
        # Position 若是 tuple 必须转 list —— 引擎事件不支持 tuple(引擎结论 §6)
        return {"kind": self.Kind,
                "entries": [e.to_dict() for e in self.Entries],
                "clear": list(self.ClearSlots),
                "pos": list(self.Position) if self.Position else None,
                "dim": self.Dimension}

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> TransferPlan
        pos = data.get("pos")
        return cls(data.get("kind", KIND_PLAYER),
                   [TransferEntry.from_dict(e) for e in data.get("entries", ())],
                   tuple(pos) if pos else None,
                   data.get("dim", 0),
                   data.get("clear", ()))

    def __repr__(self):
        return "<TransferPlan {} x{}>".format(self.Kind, len(self.Entries))


class TransferResult(object):
    """
    一次转移的结果。**逐格提交** —— 所以"成功几格"是主结果，不是布尔。

    没有整单原子性(引擎没有移动物品的接口，见 quick_craft.md §5.4)，
    Filled 与 Failed 加起来才是全部，中途停下时后面的既没扣也没放。
    """

    __slots__ = ("Filled", "Failed", "Reason")

    def __init__(self, filled=0, failed=0, reason=""):
        # type: (int, int, str) -> None
        self.Filled = int(filled)   # type: int  # 成功填入的格数
        self.Failed = int(failed)   # type: int  # 尝试了但失败的格数
        self.Reason = reason        # type: str  # 失败原因键，展示层翻译

    def is_ok(self):  # type: () -> bool
        return self.Filled > 0 and self.Failed == 0

    def to_dict(self):  # type: () -> dict
        return {"filled": self.Filled, "failed": self.Failed, "reason": self.Reason}

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> TransferResult
        data = data or {}
        return cls(data.get("filled", 0), data.get("failed", 0), data.get("reason", ""))

    def __repr__(self):
        return "<TransferResult {}/{} {}>".format(
            self.Filled, self.Filled + self.Failed, self.Reason)
