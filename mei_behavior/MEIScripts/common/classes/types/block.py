# coding=utf-8
# ----------------------------------------------------------------------
#  block.py is part of MoreEnoughItems.
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
积木（BlockType / BlockProp）：玩家自制配方页的排版单位 —— 物品格、流体槽、箭头、文字、底框……

MEI 编辑器的控件池按登记的积木出；配方页、编辑器的工作区都按页面的排版给每块积木建一个控件（ControlDef），
摆到它的位置上，再交给积木自己写内容（Paint）。一块积木在排版里是一个 dict：
    {"t": 积木的 Id, "x": 0, "y": 0, "role": "in"（装东西的积木才有）, 各个属性的键: 值}

纯契约，零引擎依赖：Paint / Tick 拿到的 view 是 UI 层的 BlockView（mei_ui/blocks/painter.py），按名字调它的方法。
第三方继承 ctx.Types.BlockType、经 ctx.UI.Blocks.Register 登记（docs/modding/api.md）
"""

ROLE_IN, ROLE_OUT, ROLE_CAT = "in", "out", "cat"
ROLES = (ROLE_IN, ROLE_OUT, ROLE_CAT)
""" 装东西的积木的角色：原料 / 产物 / 催化剂（不消耗）。配方的 in / out / cat 第 k 个对上同一角色的第 k 块（按排版里的先后）"""

POS_LIMIT = 1024
""" 坐标的上限（排版里的 x / y 读回来超出就夹回来）"""


def _int(value, default=0):  # type: (any, int) -> int
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, long)):
        return int(value)
    if isinstance(value, float) and value == value and abs(value) < 1e9:
        return int(round(value))
    return default


def _ascii(text):  # type: (any) -> bool
    try:
        text.encode("ascii")
    except UnicodeError:
        return False
    return True


def parse_item(value):  # type: (any) -> dict or None
    """
    物品属性（BlockProp.ITEM）的值：{"id": str, "aux": int[, "attr": dict]}。认 dict（编辑器从物品栏点的，带 attr）
    与字符串 "命名空间:名字" / "命名空间:名字:附加值"（玩家打的）；不成形给 None
    """
    if isinstance(value, dict):
        item_id, aux, attr = value.get("id"), value.get("aux", 0), value.get("attr")
    elif isinstance(value, basestring):
        text = _text(value)
        if text is None:
            return None
        parts = text.strip().split(u":")
        aux = 0
        if len(parts) == 3 and parts[2].isdigit():
            aux = int(parts[2])
            parts = parts[:2]
        if len(parts) != 2:
            return None
        item_id, attr = u":".join(parts), None
    else:
        return None
    item_id = _text(item_id)
    if not item_id or not _ascii(item_id) or u":" not in item_id or u" " in item_id:
        return None
    namespace, name = item_id.split(u":", 1)
    if not namespace or not name:
        return None
    aux = _int(aux, 0)
    result = {"id": item_id.encode("ascii"), "aux": aux if 0 <= aux < 32768 else 0}
    if isinstance(attr, dict) and attr:
        result["attr"] = attr
    return result


def item_text(value):  # type: (any) -> unicode
    """ 物品属性的值写成输入框里的样子："命名空间:名字"，附加值不是 0 再接 ":附加值"；没有给空串 """
    data = parse_item(value)
    if data is None:
        return u""
    text = data["id"].decode("ascii")
    return text + (u":{}".format(data["aux"]) if data["aux"] else u"")


def _text(value):  # type: (any) -> any
    """ 文字一律 unicode（存盘读回来的可能是字节串也可能是 unicode）；不是字符串、解不开给 None """
    if isinstance(value, unicode):
        return value
    if not isinstance(value, basestring):
        return None
    try:
        return value.decode("utf-8")
    except UnicodeError:
        return None


class BlockProp(object):
    """
    积木的一个属性：编辑器左栏照它出一行（步进器 / 左右切换 / 开关 / 输入框），值存在那块积木的 dict 上（键是 Key）。

    Kind     INT     整数，Min ~ Max、每次加减 Step
             CHOICE  从 Choices 里选一个：[(值, 本地化键), ...]
             BOOL    开关
             TEXT    一行字，最多 MaxLength 个字符（文字积木的内容里可以写 {字段}，见 view.Format）；ascii_only 为真只收 ASCII
                     （贴图路径这类：打到一半的中文不收）
             FIELD   这一页的一个数值字段（能量、时间……）或者空串（不用）；候选由编辑器按页面现有的字段给
             ITEM    一样物品 {"id", "aux"[, "attr"]} 或者 None：编辑器给一个输入框（打「命名空间:名字[:附加值]」）和「选」
                     （点 MEI 物品栏里的一样，带附魔这类 attr）；Paint 里用 parse_item 读
    """

    INT, CHOICE, BOOL, TEXT, FIELD, ITEM = "int", "choice", "bool", "text", "field", "item"
    KINDS = (INT, CHOICE, BOOL, TEXT, FIELD, ITEM)

    __slots__ = ("Key", "Kind", "NameKey", "Default", "Choices", "Min", "Max", "Step", "MaxLength", "Ascii")

    def __init__(self, key, kind, name_key="", default=None, choices=None, minimum=0, maximum=255, step=1, max_length=32,
                 ascii_only=False):
        # type: (str, str, str, any, list, int, int, int, int, bool) -> None
        if not key or kind not in self.KINDS:
            raise ValueError("bad block prop: {!r} {!r}".format(key, kind))
        self.Key = key  # type: str
        self.Kind = kind  # type: str
        self.NameKey = name_key or key  # type: str
        self.Choices = [(value, label) for value, label in (choices or ())]  # type: list
        self.Min = int(minimum)  # type: int
        self.Max = max(int(maximum), self.Min)  # type: int
        self.Step = max(1, int(step))  # type: int
        self.MaxLength = max(1, int(max_length))  # type: int
        self.Ascii = bool(ascii_only) or kind == self.ITEM  # type: bool
        if default is None and kind != self.ITEM:
            default = {self.INT: self.Min, self.BOOL: False, self.TEXT: u"", self.FIELD: ""}.get(
                kind, self.Choices[0][0] if self.Choices else None)
        self.Default = parse_item(default) if kind == self.ITEM else default

    def Normalize(self, value):  # type: (any) -> any
        """ 把存档里读回来、编辑器改过的值规整成这一项认的；认不出给缺省 """
        kind = self.Kind
        if kind == self.INT:
            return min(self.Max, max(self.Min, _int(value, self.Default)))
        if kind == self.BOOL:
            return bool(value) if isinstance(value, (bool, int, long)) else bool(self.Default)
        if kind == self.TEXT:
            text = _text(value)
            if text is None or (self.Ascii and not _ascii(text)):
                text = _text(self.Default) or u""
            return text[:self.MaxLength]
        if kind == self.ITEM:
            return parse_item(value) if value is not None else None
        if kind == self.FIELD:
            return value if isinstance(value, basestring) else ""
        for choice, _label in self.Choices:
            if choice == value:
                return choice
        return self.Default

    def Values(self):  # type: () -> list
        """ CHOICE 的几个值，按声明的先后 """
        return [value for value, _label in self.Choices]

    def LabelOf(self, value):  # type: (any) -> str
        """ CHOICE 的一个值的本地化键；不在里面给空串 """
        for choice, label in self.Choices:
            if choice == value:
                return label
        return ""

    def __repr__(self):
        return "<BlockProp {} {}>".format(self.Key, self.Kind)


class BlockType(object):
    """
    一种积木。

    Id          str    唯一标识，带命名空间："mei:slot"、"yourmod:gauge"（只用 ASCII）
    NameKey     str    显示名的本地化键（控件池的按钮、属性栏的标题）
    Icon        str    控件池按钮上的图标（白色贴图，由按钮染色），不给就只写名字
    ControlDef  str    每块积木建的控件的 JSON 定义名（namespace.name）。**锚点写左上**：MEI 用 SetPosition 摆它（引擎结论 §39）；
                       要换大小的写绝对尺寸（MEI 用 SetFullSize 改，引擎结论 §28）
    Size        tuple  缺省大小 (宽, 高)；跟着属性变的覆写 SizeOf
    Limit       int    一页最多几块（编辑器的控件池用完灰掉）
    Holds       bool   装东西（物品格、流体槽）：有角色（ROLES）与编号，配方填写时往里填；MEI 把这一格的内容交给 Paint（view.Entry）
    Unit        str    装东西的积木的数量单位：空串是个数，"mB" 是流体（编辑器的数量步进跟着换）
    Props       list   BlockProp：编辑器左栏照它出属性行；位置、角色是 MEI 自己管的，不用声明
    SortIndex   int    控件池里的先后，越小越靠前

    Paint(view) 写内容；Tick(view, ticks) 是动画的节拍（IsAnimated 为真的积木才调）。两者抛异常只丢那一块、记一行日志
    """

    TEMPLATE = {}
    """
    可选：新建的控件里各处本来的样子 {(写法, 子控件路径): 值}。写法是 "visible" / "text" / "tcolor"（字的颜色）/ "item"（值写 None：
    渲染器藏着、没有物品）/ "hover"（悬停文字）/ "sprite" / "color" / "alpha" / "clip" / "size"，和 view 的 SetVisible、SetText …… 一一对应；
    子控件路径 "" 是积木的控件自己（("size", "") 只在 JSON 尺寸等于 Size 时写）。
    MEI 照它把这些记成写过，第一次画时一样的值就不写 —— 一次引擎调用约 0.1 毫秒，一行十几块积木能省下一半；不写也对，只是第一次多写几次
    """

    def __init__(self, block_id, name_key="", control_def="", size=(18, 18), limit=4, holds=False, props=None,
                 icon=None, sort_index=0, unit=""):
        # type: (str, str, str, tuple, int, bool, list, str, int, str) -> None
        if not block_id or not isinstance(block_id, basestring):
            raise ValueError("block_id cannot be empty")
        self.Id = block_id  # type: str
        self.NameKey = name_key or block_id  # type: str
        self.ControlDef = control_def  # type: str
        self.Size = (max(1, _int(size[0], 18)), max(1, _int(size[1], 18)))  # type: tuple
        self.Limit = max(1, _int(limit, 4))  # type: int
        self.Holds = bool(holds)  # type: bool
        self.Unit = unit or ""  # type: str
        self.Props = list(props or ())  # type: list
        self.Icon = icon  # type: str or None
        self.SortIndex = _int(sort_index, 0)  # type: int

    # 排版
# ======================================================================================================================
    def SizeOf(self, block):  # type: (dict) -> tuple
        """ 这一块积木的大小 (宽, 高)：缺省是 Size，大小跟着属性变的（箭头的样式、底框的宽高）覆写它 """
        return self.Size

    def IsAnimated(self, block):  # type: (dict) -> bool
        """ 这一块要不要节拍（Tick）：缺省不要 """
        return False

    def Prop(self, key):  # type: (str) -> BlockProp or None
        for prop in self.Props:
            if prop.Key == key:
                return prop
        return None

    def Defaults(self):  # type: () -> dict
        """ 新放一块时各个属性的缺省值 """
        return dict((prop.Key, prop.Default) for prop in self.Props)

    def Normalize(self, block):  # type: (dict) -> dict
        """
        规整一块积木（存档读回来、编辑器改过之后）：给一个新的 dict —— 种类、位置、角色、声明过的属性都规整过；
        没声明的键原样留着（别的版本写的、以后才认得的东西不丢）
        """
        result = dict(block) if isinstance(block, dict) else {}
        result["t"] = self.Id
        result["x"] = min(POS_LIMIT, max(0, _int(result.get("x"), 0)))
        result["y"] = min(POS_LIMIT, max(0, _int(result.get("y"), 0)))
        if self.Holds:
            if result.get("role") not in ROLES:
                result["role"] = ROLE_IN
        else:
            result.pop("role", None)
        for prop in self.Props:
            result[prop.Key] = prop.Normalize(result.get(prop.Key, prop.Default))
        return result

    # 画
# ======================================================================================================================
    def Paint(self, view):  # type: (any) -> None
        """
        写这一块积木的内容。view 是 MEI 给的 BlockView：view.Data（这块积木的 dict）、view.Entry（装东西的积木：这一格的 Ingredient 或 None）、
        view.Stack（这一格现在显示哪一样，候选轮播到的）、view.Fields（这条配方的数值字段）、view.Editing（编辑器里排版时为真）、
        写控件的 SetText / SetSprite / SetItem / SetVisible / SetSize / SetClip / SetColor / SetHoverText 等（只写变了的）。
        排版、物品、字段变了都会再调一次
        """

    def Tick(self, view, ticks):  # type: (any, int) -> None
        """ 节拍（0.2 秒一拍，ticks 从显示起算）：动画用。IsAnimated 为真才调 """

    def ShownItem(self, view):  # type: (any) -> any
        """
        这一块上画着的物品（MEI 的 Item / Stack）：点它、悬停照 MEI 的格子处理（查来源 / 用途、工具 / 作弊模式）。
        缺省是装着的那一样（view.Stack，轮播到的候选）；不装东西、自己画一样物品的积木覆写它
        """
        return view.Stack

    def __repr__(self):
        return "<BlockType {}>".format(self.Id)
