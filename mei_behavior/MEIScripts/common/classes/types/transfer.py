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
配方转移的数据形状。纯数据零引擎。

- TransferContext / TransferEntry / TransferPlan / TransferResult：两端共用 —— MEI 自己的快捷合成（只往玩家侧的格子里放：工作台、背包 2×2），
  客户端算出来、服务端核对并执行；MEI 内部用，不对外；
- TransferHandler / TransferRequest / TransferSlot / TransferError：只在客户端 —— 别的模组按界面登记的转移处理器（ctx.UI.Transfers），
  MEI 算好「每一格要什么、背包里凑得出多少」交给它，搬不搬、怎么搬是它自己的事（docs/modding/05-screens-and-tools.md §3）。
"""

class TransferContext(object):
    """
    一次转移的环境。纯数据 —— 两端各自填好后交给 ItemSource / SlotTarget

    Side 存在的理由：同一个来源在两端要做不同的事（客户端只 Collect 用于预检，
    服务端才真搬），来源自己按它分流，框架不替它判断。
    """

    __slots__ = ("PlayerId", "Side", "Extra")

    def __init__(self, player_id="", side="client", extra=None):
        # type: (str, str, dict) -> None
        self.PlayerId = player_id
        self.Side = side              # type: str  # "client" / "server"
        self.Extra = extra or {}      # type: dict # 策略要的环境（当前界面 screen_def），框架不解释

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
    只往玩家侧的格子里放（工作台、背包 2×2）：写入走 SetPlayerUIItem，引擎只让写玩家开着的那个界面。
    """

    __slots__ = ("Entries", "ClearSlots")

    def __init__(self, entries=None, clear_slots=None):
        # type: (list, list) -> None
        self.Entries = list(entries or ())  # type: list

        self.ClearSlots = list(clear_slots or ())  # type: list
        """
        转移前要整片清空的槽位。**由客户端算好带过来** ——
        服务端没有 Category 也没有转移策略（扩展只在客户端装配），
        它问不出"这个容器有哪些输入格"。
        """

    def to_dict(self):  # type: () -> dict
        return {"entries": [e.to_dict() for e in self.Entries],
                "clear": list(self.ClearSlots)}

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> TransferPlan
        return cls([TransferEntry.from_dict(e) for e in data.get("entries", ())],
                   data.get("clear", ()))

    def __repr__(self):
        return "<TransferPlan x{}>".format(len(self.Entries))


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


class TransferSlot(object):
    """
    配方的一格：要什么、要几个、背包里凑得出几个、挑中了哪一样。MEI 在客户端按背包算好放进 TransferRequest
    """

    __slots__ = ("Index", "Ingredient", "Need", "Have", "Stack", "Catalyst")

    def __init__(self, index, ingredient, need, have=0, stack=None, catalyst=False):
        # type: (int, any, int, int, any, bool) -> None
        self.Index = index            # type: int   # 第几格：处理器给了 GRID 是格子的下标（行优先），没给是配方输入的下标；催化剂另从 0 数
        self.Ingredient = ingredient  # type: any   # 这一格的 Ingredient
        self.Need = int(need)         # type: int   # 要几个（每份的数量 × 份数；催化剂只要一份）
        self.Have = int(have)         # type: int   # 背包里凑得出几个（几格要同一样东西时已经按全局配额分过）
        self.Stack = stack            # type: any   # 挑中的那一样（ItemStack，数量是 Need）：背包里有的候选优先，都没有就是第一个候选
        self.Catalyst = bool(catalyst)  # type: bool  # 催化剂（工具）：不消耗

    @property
    def Missing(self):  # type: () -> int
        """ 还缺几个 """
        return max(0, self.Need - self.Have)

    def __repr__(self):
        return "<TransferSlot {}{} {}/{}>".format("c" if self.Catalyst else "#", self.Index, self.Have, self.Need)


class TransferRequest(object):
    """
    玩家点 + 时 MEI 交给转移处理器的东西 —— 检查（+ 亮不亮、悬停写什么）与真做用的是同一份。

    Slots 是输入格（处理器给了 GRID 就按格子摊开，空格不在里面；没给按配方输入的顺序），Catalysts 是催化剂（工具）。
    数量按一份算（Times）；玩家要「尽量多」时 Max 为真，背包最多够几份问 MaxTimes()。
    """

    __slots__ = ("Recipe", "CategoryId", "ScreenDef", "Slots", "Catalysts", "Times", "Max", "Fits", "_max_times")

    def __init__(self, recipe, category_id="", screen_def="", slots=None, catalysts=None, times=1,
                 wants_max=False, max_times=None, fits=True):
        # type: (any, str, str, list, list, int, bool, any, bool) -> None
        self.Recipe = recipe              # type: any
        self.CategoryId = category_id     # type: str
        self.ScreenDef = screen_def       # type: str   # 当前开着的界面（就是登记时给的那个）
        self.Slots = list(slots or ())    # type: list  # TransferSlot
        self.Catalysts = list(catalysts or ())  # type: list  # TransferSlot（Catalyst 为真）
        self.Times = max(1, int(times or 1))  # type: int
        self.Max = bool(wants_max)        # type: bool  # 玩家要「尽量多」
        self.Fits = bool(fits)            # type: bool  # 配方摊得进处理器的 GRID（没给 GRID 恒真）；假的时候 Slots 少了摊不进的那些
        self._max_times = max_times       # type: any   # int，或者第一次问时才算的 fn() -> int

    def MaxTimes(self):  # type: () -> int
        """ 背包里的材料最多够做几份（只看输入格，按每格的堆叠上限封顶；一份都凑不齐是 0）"""
        if callable(self._max_times):
            try:
                self._max_times = int(self._max_times() or 0)
            except Exception:  # noqa  算不出来当一份都凑不齐，不带走调用方
                self._max_times = 0
        return int(self._max_times or 0)

    def Cell(self, index):  # type: (int) -> TransferSlot or None
        """ 第 index 格（GRID 布局里空着的格子、超出范围给 None）"""
        for slot in self.Slots:
            if slot.Index == index:
                return slot
        return None

    def Missing(self):  # type: () -> list
        """ 缺东西的格子：输入格在前、催化剂在后 """
        return [slot for slot in self.Slots + self.Catalysts if slot.Missing > 0]

    def Complete(self):  # type: () -> bool
        """ 背包里的东西够做一份（催化剂也算）"""
        return not self.Missing()

    def __repr__(self):
        return "<TransferRequest {} slots={} missing={}>".format(self.CategoryId, len(self.Slots), len(self.Missing()))


class TransferError(object):
    """
    转移处理器说「这一条现在做不了」或「做了，但有话要说」。

    Blocking 为真（缺省）：+ 灰掉不让点，悬停写原因；为假：照样能点（比如材料不够也照样把有的放进去），悬停把缺的写出来。
    Message 是给玩家看的一句话（+ 的悬停文字、点了没成时配方页顶上那一行）；不给的话 MEI 按 Missing 写「缺少：……」。
    """

    __slots__ = ("Message", "Missing", "Blocking")

    def __init__(self, message="", missing=None, blocking=True):
        # type: (str, list, bool) -> None
        self.Message = message or ""            # type: str
        self.Missing = list(missing or ())      # type: list  # 缺东西的 TransferSlot
        self.Blocking = bool(blocking)          # type: bool

    def __repr__(self):
        return "<TransferError {} {!r} missing={}>".format(
            "blocking" if self.Blocking else "notice", self.Message, len(self.Missing))


class TransferHandler(object):
    """
    按界面登记的配方转移处理器（ctx.UI.Transfers.Register(界面, 处理器, categories=...)），照 NEI / JEI 的 transfer handler：
    这个界面开着时，配方页上这几类配方的 + 交给它。MEI 只算清单（每一格要什么、背包里凑得出多少）、管 + 亮不亮和悬停文字，
    搬不搬、怎么搬是处理器自己的事 —— 往自己的机器里放材料就发自己的请求，由自己的服务端照自己的规矩搬。

    可以继承它，也可以照着写一个有 Transfer 方法的对象（鸭子类型，下面几个类属性不写就是缺省值）。
    """

    GRID = None
    """ (列, 行)：配方按格子摊开（和配方页、原版工作台同一个摊法：有序配方照形状摆，无序配方一格一个）；None 按配方输入的顺序 """

    CONSUMES = True
    """ 真：要拿背包里的东西，缺省的检查材料不够就灰掉；假：只记配方不拿东西（样板、过滤器），缺省的检查一律放行 """

    HINT = ""
    """ + 能点时的悬停文字（点了会怎样），空的话 MEI 写一句通用的 """

    def Check(self, request):  # type: (TransferRequest) -> TransferError or None
        """ + 亮不亮：None 是能点；TransferError 说为什么不行（Blocking 为假是能点、但把缺的写出来）。每条配方每次开页问一次，会被缓存 """
        if self.CONSUMES and not request.Complete():
            return TransferError(missing=request.Missing())
        return None

    def Transfer(self, request):  # type: (TransferRequest) -> any
        """ 玩家点了 +：成了返回 True（MEI 关掉配方页回到你的界面）；没成返回 False，或者 TransferError 说为什么（写在配方页顶上）"""
        return False
