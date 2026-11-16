# coding=utf-8
# ----------------------------------------------------------------------
#  painter.py is part of MoreEnoughItems.
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
积木的画法：玩家自制配方页的每一行、MEI 编辑器的工作区共用一套（docs/architecture/user_recipes.md §13）。

按页面的排版给每块积木建一个控件（BlockType.ControlDef），摆到它的位置上，交给积木写内容（BlockType.Paint，拿到的 view 是 BlockView）。
控件按（第几块, 种类）复用：排版改了只挪位置、重写内容，种类换了才删了重建；名字带流水号 ——
同一帧里删了再建同名的，CreateChildControl 会认成还在的那个（引擎结论 §33）。
控件建出来不当场刷新界面（建的人给 forceUpdate=False），记下界面（writer.mark_dirty），一批建完、写完由调用方 writer.flush() 刷新一次；
刚建的控件当场取不到子控件：那一块记成没画好，Paint 下一帧再调一遍就补上（Pending）。新建的控件按积木的 TEMPLATE 把模板的样子记成写过，
一样的值不再写（省引擎调用）。
点中了哪一块由 PickAt 按画面算：谁画在上面（JSON 的层级大的、同层后建的）就是谁 —— 编辑器的工作区上只盖一个拾取层，
不给每块积木各盖一个按钮（那样同层的按钮按建的先后叠，后放的底框会挡住它上面的格子）。
排版里认不出种类的积木（登记它的模组没装了）不画，数据原样留着
"""
from mod_log import logger

from MEIScripts.common.classes.types.block import ROLE_CAT, ROLES, parse_item
from MEIScripts.constants.texts import UserText
from MEIScripts.mei_mod.state.user_recipes import holder_index
from MEIScripts.registry.blocks import BlockRegistry
from MEIScripts.utils.text import error_text, native_str

from .writer import ControlWriter, mark_dirty

ROTATE_TICKS = 5
""" 装着几样候选的格子：节拍 0.2 秒一拍，5 拍换一样 """

_warned = set()


def _warn_once(key, text):  # type: (any, str) -> None
    if key not in _warned:
        _warned.add(key)
        logger.error(text)


def format_number(value):  # type: (any) -> str
    """ 字段的数：整数不带小数点，别的最多两位小数 """
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return ("%.2f" % value).rstrip("0").rstrip(".")
    return str(value)


def _unicode(text):  # type: (any) -> unicode
    return text if isinstance(text, unicode) else str(text).decode("utf-8", "replace")


def template_values(template):  # type: (dict) -> dict
    """ 控件本来的样子（积木的 TEMPLATE：{(写法, 子控件路径): 值}）换成 ControlWriter 记的样子（Prime）"""
    values = {}
    for (kind, sub), value in (template or {}).items():
        if kind == "item":
            values["item" + sub] = None  # 渲染器在模板里藏着、没有物品
            values["item.shown" + sub] = False
        elif kind == "visible":
            values["visible" + sub] = bool(value)
        elif kind in ("text", "hover", "sprite"):
            values[kind + sub] = native_str(value or "")
        elif kind in ("size", "pos"):
            values[kind + sub] = (int(value[0]), int(value[1]))
        elif kind in ("color", "tcolor"):
            values[kind + sub] = tuple(value)
        else:
            values[kind + sub] = value
    return values


def holds(block):  # type: (dict) -> bool
    """ 这一块积木装不装东西（BlockRegistry.Holds）"""
    return BlockRegistry.Holds(block)


def field_info(field_id):  # type: (str) -> tuple
    """ 字段的 (名字, 单位)；不认识的字段名字就是 Id、没有单位 """
    return UserText.Fields.get(field_id, (native_str(field_id), u""))


class BlockView(object):
    """ 交给 BlockType.Paint / Tick 的东西：这块积木的数据、它装的东西、写控件的方法（只写变了的，见 writer.ControlWriter）"""

    __slots__ = ("Painter", "Index", "Type", "Data", "Writer", "Role", "Number", "Entry", "Rotation", "Dirty", "Name", "Layer",
                 "Order")

    def __init__(self, painter, index, block_type, data, writer, name):
        self.Painter = painter
        self.Index = index  # type: int  # 第几块（排版里的下标）
        self.Type = block_type
        self.Data = data  # type: dict  # 这块积木（规整过的）。只读
        self.Writer = writer  # type: ControlWriter
        self.Layer = 0  # type: int  # 控件在 JSON 里的层级（同一个父控件下谁画在上面）
        self.Order = 0  # type: int  # 第几个建的（同层时后建的画在上面）
        self.Role = None  # type: str or None  # 装东西的积木：角色
        self.Number = 0  # type: int  # 装东西的积木：同一角色里排第几（从 0 起）
        self.Entry = None  # type: any  # 装东西的积木：这一格的 Ingredient（空格是 None）
        self.Rotation = 0  # type: int  # 候选轮播到第几样
        self.Dirty = True  # type: bool  # 要（重新）画
        self.Name = name  # type: str  # 控件名

    # 读
# ======================================================================================================================
    @property
    def Fields(self):  # type: () -> dict
        """ 这条配方的数值字段 {字段 Id: 数} """
        return self.Painter.Fields

    @property
    def Editing(self):  # type: () -> bool
        """ 在编辑器里排版（空格子写「原1」这类占位）"""
        return self.Painter.Editing

    @property
    def Ticks(self):  # type: () -> int
        return self.Painter.Ticks

    @property
    def Size(self):  # type: () -> tuple
        return self.Type.SizeOf(self.Data)

    @property
    def Control(self):
        return self.Writer.Control

    @property
    def Path(self):  # type: () -> str
        return self.Writer.Path

    @property
    def Stacks(self):  # type: () -> list
        """ 这一格的候选（非空的）"""
        entry = self.Entry
        if entry is None:
            return []
        return [stack for stack in entry.get_stacks() if stack is not None and not stack.is_empty()]

    @property
    def Stack(self):  # type: () -> any
        """ 这一格现在显示哪一样（候选按节拍轮播）；空格给 None """
        stacks = self.Stacks
        return stacks[self.Rotation % len(stacks)] if stacks else None

    @property
    def Amount(self):  # type: () -> int
        return int(self.Entry.get_amount() or 0) if self.Entry is not None else 0

    @property
    def Chance(self):  # type: () -> float
        return float(self.Entry.get_chance()) if self.Entry is not None else 1.0

    @property
    def Label(self):  # type: () -> any
        """ 编辑器里空格子写的占位：角色的简称 + 编号（原1、产2、催1）"""
        if self.Role is None:
            return u""
        return u"{}{}".format(UserText.RoleShort.get(self.Role, u""), self.Number + 1)

    def FieldValue(self, field):  # type: (str) -> any
        return self.Painter.Fields.get(field)

    def FieldRatio(self, field):  # type: (str) -> float
        """ 字段的值占这一页里最大的那个的多少（条画满多少）：没有值给 0；编辑器里排版时没有配方，画一半 """
        value = self.FieldValue(field)
        if value is None:
            return 0.5 if self.Editing and field else 0.0
        top = self.Painter.FieldMax.get(field) or value
        return max(0.0, min(1.0, float(value) / float(top))) if top else 0.0

    def FieldText(self, field):  # type: (str) -> any
        """ 「能量：3200 FE」；这条配方没填这个字段给空串 """
        value = self.FieldValue(field)
        if value is None:
            return u""
        name, unit = self.Painter.FieldInfo(field)
        return UserText.FieldLine.format(name, format_number(value), unit).strip()

    def Format(self, text):  # type: (any) -> any
        """ 文字里的 {字段} 换成这条配方的值；没填的换成空（编辑器里排版时留着字段名，好认）"""
        if not isinstance(text, basestring):
            return text
        result = _unicode(text)
        if u"{" not in result:
            return result
        for field in self.Painter.PageFields:
            token = u"{" + _unicode(field) + u"}"
            value = self.FieldValue(field)
            if value is None:
                shown = token if self.Editing else u""
            else:
                shown = _unicode(format_number(value))
            result = result.replace(token, shown)
        return result

    def EntryLore(self):  # type: () -> list
        """ 这一格悬停文字里物品名下面的说明：数量、概率、标签或候选、催化剂不消耗 """
        if self.Entry is None:
            return []
        lines = []
        amount = self.Amount
        if self.Type.Unit:
            lines.append(UserText.LoreFluid.format(amount))
        elif amount > 1:
            lines.append(UserText.LoreAmount.format(amount))
        chance = self.Chance
        if 0 < chance < 1:
            lines.append(UserText.LoreChance.format(format_number(round(chance * 100, 2))))
        tag = self.Entry.get_tag_id()
        if tag:
            lines.append(UserText.LoreTag.format(_unicode(tag)))
        elif len(self.Stacks) > 1:
            lines.append(UserText.LoreAlts.format(len(self.Stacks)))
        if self.Role == ROLE_CAT:
            lines.append(UserText.LoreCatalyst)
        return lines

    def EntryHoverText(self):  # type: () -> str
        """ 这一格的悬停文字：和 MEI 自己的格子一样（物品的几行 + 说明 + ID / 命名空间）；空格在编辑器里写角色 """
        stack = self.Stack
        if stack is None:
            return native_str(u"{} {}".format(UserText.RoleName.get(self.Role, u""), self.Number + 1)) if self.Editing else ""
        return self.HoverOf(stack, self.EntryLore())

    @staticmethod
    def HoverOf(item, lore=None):  # type: (any, list) -> str
        """ 一样物品（Item / Stack）的悬停文字：和 MEI 自己的格子一样（物品的几行 + lore + ID / 命名空间）"""
        from MEIScripts.api.facades.ui.actions import HoverText
        return HoverText(getattr(item, "Item", item), list(lore or ()))

    def PropItem(self, key):  # type: (str) -> any
        """ 物品属性（BlockProp.ITEM）对上的 MEI 物品；没填、物品表里找不到（模组卸了）给 None """
        data = parse_item(self.Data.get(key))
        if data is None:
            return None
        from MEIScripts.mei_mod.state import BookmarkResolver
        return BookmarkResolver.ResolveItem(data)

    # 写（ControlWriter 的同名方法，sub 是相对这块积木控件的路径）
# ======================================================================================================================
    def Part(self, sub="", cast=None):
        return self.Writer.Part(sub, cast)

    def SetText(self, sub, text, color=None):
        self.Writer.SetText(sub, text, color)

    def SetSprite(self, sub, texture):
        self.Writer.SetSprite(sub, texture)

    def SetColor(self, sub, color):
        self.Writer.SetColor(sub, color)

    def SetAlpha(self, sub, alpha):
        self.Writer.SetAlpha(sub, alpha)

    def SetVisible(self, sub, on):
        self.Writer.SetVisible(sub, on)

    def SetSize(self, sub, size):
        self.Writer.SetSize(sub, size)

    def SetClip(self, sub, ratio):
        self.Writer.SetClip(sub, ratio)

    def SetItem(self, sub, stack):
        return self.Writer.SetItem(sub, stack)

    def SetHoverText(self, sub, text):
        self.Writer.SetHoverText(sub, text)

    def Replay(self, sub):
        self.Writer.Replay(sub)


class BlockPainter(object):
    """ 一组积木（一行配方、编辑器的工作区）。create(定义名, 控件名, 父控件) → 控件或 None；remove(控件) """

    def __init__(self, screen, create, remove, editing=False, info=None):
        self.Screen = screen
        self.Create = create
        self.Remove = remove
        self.Editing = bool(editing)  # type: bool
        self.FieldInfo = info or field_info  # type: callable
        self.Parent = None  # type: any  # 积木建在它下面
        self.Prefix = "b"  # type: str
        self.Views = []  # type: list  # 每块积木一个 BlockView（种类不认识的是 None）
        self.Fields = {}  # type: dict  # 这条配方的数值字段
        self.FieldMax = {}  # type: dict  # 这一页每个字段最大的值（条画满多少）
        self.PageFields = []  # type: list  # 这一页用到的字段（文字里的 {字段} 按它换）
        self.Ticks = 0  # type: int
        self.Serial = 0  # type: int
        self.Unknown = 0  # type: int  # 排版里认不出种类的积木几块

    # 排版
# ======================================================================================================================
    def Attach(self, parent, prefix="b"):  # type: (any, str) -> None
        """ 积木建在 parent 下面；换了父控件先把旧的拆掉 """
        if parent is self.Parent:
            return
        self.Clear()
        self.Parent = parent
        self.Prefix = prefix or "b"

    def Layout(self, blocks, page_fields=None):  # type: (list, list) -> None
        """
        照排版建 / 挪控件。blocks 是这一页的积木（存的 dict；这里按种类规整一遍）。
        种类认不出的跳过（原样留在数据里）
        """
        self.PageFields = [native_str(field) for field in (page_fields or ())]
        numbering = dict((index, (role, number)) for index, role, number in holder_index(blocks, holds))
        views, self.Unknown = [], 0
        for index, raw in enumerate(blocks or ()):
            block_type = BlockRegistry.Get(raw.get("t")) if isinstance(raw, dict) else None
            old = self.Views[index] if index < len(self.Views) else None
            if block_type is None:
                self.Unknown += 1
                self.__Drop(old)
                views.append(None)
                continue
            data = block_type.Normalize(raw)
            if old is not None and old.Type is block_type:
                view = old
                if view.Data != data:
                    view.Data = data
                    view.Dirty = True
            else:
                self.__Drop(old)
                view = self.__Make(index, block_type, data)
                if view is None:
                    views.append(None)
                    continue
            view.Index = index
            role, number = numbering.get(index, (None, 0))
            if (view.Role, view.Number) != (role, number):
                view.Role, view.Number, view.Dirty = role, number, True
            self.__Place(view)
            views.append(view)
        for old in self.Views[len(views):]:
            self.__Drop(old)
        self.Views = views

    def __Make(self, index, block_type, data):  # type: (int, any, dict) -> BlockView or None
        if self.Parent is None:
            return None
        self.Serial += 1
        name = "{}{}".format(self.Prefix, self.Serial)
        control = self.Create(block_type.ControlDef, name, self.Parent)
        if control is None:
            _warn_once(("make", block_type.Id), "[MEI/blocks] 积木 {} 的控件 {} 建不出来".format(block_type.Id, block_type.ControlDef))
            return None
        mark_dirty(self.Screen)
        writer = ControlWriter(self.Screen, control)
        writer.Prime(template_values(getattr(block_type, "TEMPLATE", None)))
        view = BlockView(self, index, block_type, data, writer, name)
        view.Order = self.Serial
        try:
            view.Layer = int(control.GetLayer())
        except Exception:  # noqa  取不到当 0（只影响叠着的几块谁先被点中）
            view.Layer = 0
        return view

    def __Place(self, view):  # type: (BlockView) -> None
        view.Writer.SetPos((view.Data.get("x", 0), view.Data.get("y", 0)))
        view.Writer.SetSize("", view.Size)

    def Move(self, index, pos):  # type: (int, tuple) -> None
        """ 拖动中：只挪这一块，不重排、不重画 """
        view = self.ViewAt(index)
        if view is not None:
            view.Writer.SetPos(pos)

    def __Drop(self, view):  # type: (BlockView) -> None
        if view is None or view.Writer.Control is None:
            return
        try:
            self.Remove(view.Writer.Control)
        except Exception:  # noqa  已经跟着父控件没了
            pass

    def Clear(self):
        for view in self.Views:
            self.__Drop(view)
        self.Views = []

    def ViewAt(self, index):  # type: (int) -> BlockView or None
        return self.Views[index] if index is not None and 0 <= index < len(self.Views) else None

    def Covered(self, index):  # type: (int) -> bool
        """ 第 index 块上面还压着别的积木（和它重叠、画在它上面的）"""
        view = self.ViewAt(index)
        if view is None:
            return False
        left, top = view.Data.get("x", 0), view.Data.get("y", 0)
        width, height = view.Size
        for other in self.Views:
            if other is None or other is view or (other.Layer, other.Order) < (view.Layer, view.Order):
                continue
            o_left, o_top = other.Data.get("x", 0), other.Data.get("y", 0)
            o_width, o_height = other.Size
            if o_left < left + width and left < o_left + o_width and o_top < top + height and top < o_top + o_height:
                return True
        return False

    def PickAt(self, x, y, holders_first=False):  # type: (float, float, bool) -> int or None
        """
        相对父控件左上角的这一点上点中的是第几块：画在最上面的那块（JSON 的层级大的，同层后建的）。
        holders_first 时装东西的积木优先（配方模式点格子：盖在格子上的文字、图片不挡）。没有给 None
        """
        best, best_key = None, None
        for view in self.Views:
            if view is None:
                continue
            left, top = view.Data.get("x", 0), view.Data.get("y", 0)
            width, height = view.Size
            if not (left <= x < left + width and top <= y < top + height):
                continue
            key = (holders_first and view.Role is not None, view.Layer, view.Order)
            if best_key is None or key > best_key:
                best, best_key = view.Index, key
        return best

    # 内容
# ======================================================================================================================
    def SetContent(self, entries, fields=None, field_max=None):  # type: (dict, dict, dict) -> None
        """
        这一行显示哪条配方：entries {角色: [Ingredient 或 None]}（同一角色第 k 个对上第 k 块），fields 这条配方的数值字段，
        field_max 这一页每个字段最大的值。空的 entries（编辑器排版时）就是全空
        """
        entries = entries or {}
        self.Fields = dict(fields or {})
        self.FieldMax = dict(field_max or {})
        for view in self.Views:
            if view is None:
                continue
            entry = None
            if view.Role in ROLES:
                cells = entries.get(view.Role) or ()
                entry = cells[view.Number] if view.Number < len(cells) else None
                if entry is not None and entry.is_empty():
                    entry = None
            if entry is not view.Entry:
                view.Entry, view.Rotation = entry, 0
            view.Dirty = True

    def Invalidate(self):
        """ 全部重画一遍（换了配方、字段变了）"""
        for view in self.Views:
            if view is not None:
                view.Dirty = True

    def Paint(self):  # type: () -> bool
        """ 画要画的（新的、变了的、上次没画全的）；都画好了给 True —— 不然调用方下一帧再调 """
        done = True
        for view in self.Views:
            if view is None or not view.Dirty:
                continue
            view.Writer.Missed = False
            try:
                view.Type.Paint(view)
            except Exception as e:  # noqa  一块积木画坏了只丢这一块
                _warn_once(("paint", view.Type.Id), "[MEI/blocks] 积木 {} 画的时候出错（之后不再记）: {}".format(
                    view.Type.Id, error_text(e)))
            view.Dirty = view.Writer.Missed
            if view.Dirty:
                done = False
        return done

    def Pending(self):  # type: () -> bool
        """ 有没画好的 """
        return any(view is not None and view.Dirty for view in self.Views)

    def Tick(self, ticks):  # type: (int) -> None
        """ 节拍（0.2 秒一拍）：候选轮播、积木自己的动画，再把没画好的补上 """
        self.Ticks = ticks
        for view in self.Views:
            if view is None:
                continue
            if len(view.Stacks) > 1 and ticks % ROTATE_TICKS == 0:
                view.Rotation += 1
                view.Dirty = True
            if view.Type.IsAnimated(view.Data):
                try:
                    view.Type.Tick(view, ticks)
                except Exception as e:  # noqa
                    _warn_once(("tick", view.Type.Id), "[MEI/blocks] 积木 {} 的节拍出错（之后不再记）: {}".format(
                        view.Type.Id, error_text(e)))
        self.Paint()
