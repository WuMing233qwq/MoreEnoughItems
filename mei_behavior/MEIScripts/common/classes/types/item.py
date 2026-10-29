# coding=utf-8
# ----------------------------------------------------------------------
#  item.py is part of MoreEnoughItems.
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
import abc
import math

from MEIScripts.utils.hashable import HashableMaker
from MEIScripts.utils.slots import copy_slots
from . import keys
from .ingredient import IngredientLike

to_hashable = HashableMaker.to_hashable

_ITEM_FACTORY = [None]
""" 反序列化时构造 Item 的工厂钩子; 见 set_item_factory """


def set_item_factory(factory):  # type: (callable or None) -> None
    """
    注入 Item 构造工厂, 供 ItemStack.from_dict 使用.

    不注入时 from_dict 退化为构造裸 Item(无 loader), 惰性字段取不到真实值 ——
    够做往返自检, 但不足以还原可渲染的物品. 上层(registry)应在初始化后注入
    带 _LazyLoader 的工厂, 使书签/存档反序列化能拿到完整物品.
    签名: factory(item_id, aux_value) -> Item
    """
    _ITEM_FACTORY[0] = factory

class Stack(IngredientLike):
    """
    物料堆抽象基类.

    实现 IngredientLike 契约的单元素退化形态: 一个 Stack 即只有一个候选的槽位内容.
    与 Ingredient 的分界线是「有身份 vs 无身份」—— Stack 是具体的东西 (由它提供
    get_key(), 作为索引/书签的寻址依据); Ingredient 是规格, 永远没有身份.
    """
    __slots__ = (
        "Count",
    )

    KIND = "item"
    """
    条目种类, 子类覆写 (structure.md 决策 B′).

    **是字符串, 不是 UI 类** —— 本层零 UI 依赖, probe_types_offline 守着这条。
    渲染时 render_slot 按它分发到 SlotPanelRegistry 注册的面板;
    **比较与序列化不看它**, 那两件事继续走已经泛化好的 get_key() / to_dict()
    —— 所以加一种 KIND 不会漂移 Recipe.Id。

    ⚠ 已知边界: Ingredient.from_dict 无条件走 ItemStack.from_dict,
    **反序列化拿不回 KIND**。目前不阻塞(配方本体不落盘, 书签只存 Recipe.Id),
    真要持久化配方那天须在 to_dict 里补判别码 —— 而那**会**改 canonical 形状,
    要与 recipe_model.md §7.5 的上线前硬门槛一起做。
    """

    def __init__(
            self,
            count=1,
    ):
        self.Count = count

    def get_stacks(self):  # type: () -> list
        """ 单元素退化: 自己就是唯一候选 """
        return [self]

    def get_amount(self):  # type: () -> int
        """ 配方语境下 Count 即需求量/产出量 """
        return self.Count

    @abc.abstractmethod
    def is_empty(self):  # type: () -> bool
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self):  # type: () -> Stack
        raise NotImplementedError

    @abc.abstractmethod
    def same_as(self, other):  # type: (Stack) -> bool
        """ 身份比较: 两者是不是同一种东西 (对称). 与 Ingredient.accepts 语义不同 """
        raise NotImplementedError

    @abc.abstractmethod
    def get_render_data(self):  # type: () -> tuple
        """ 返回渲染数据 """
        raise NotImplementedError

    @abc.abstractmethod
    def get_key(self):  # type: () -> tuple
        """
        身份键 (make_key 的返回值). **只有 Stack 有身份, Ingredient 没有** ——
        一组候选无法作为索引键有意义地存在, 故本方法不在 IngredientLike 契约上.

        返回的是 tuple, 仅限进程内内存; 过序列化边界须经 keys.key_to_str().
        """
        raise NotImplementedError

    # to_dict / to_canonical 的契约在 IngredientLike 上声明, 此处不重复

    def __ne__(self, other):
        return not self.__eq__(other)


class ItemStack(Stack):
    """ 物品堆 用于维护堆叠的物品对象 """
    __slots__ = (
        "Item",
    )

    def __init__(
            self,
            item,
            count = 1,
    ):
        super(ItemStack, self).__init__(count)  # noqa
        self.Item = item
        """ 物品实例 """

    def take(self, count=1):
        # type: (int) -> ItemStack
        """ 从堆中取出指定数量 返回一个新的堆 """
        if self.is_empty():
            raise ValueError("this stack is empty")
        if count > self.Count:
            raise ValueError("take count cannot greater than current count")
        self.Count -= count
        return type(self)(self.Item, count)

    def take_all(self):
        # type: () -> ItemStack
        """ 从堆中取出全部 返回一个新的堆 """
        if self.is_empty():
            raise ValueError("this stack is empty")
        count = self.Count
        self.Count -= count
        return type(self)(self.Item, count)

    def take_stack(self):
        # type: () -> ItemStack
        """ 从堆中取出一组的物品(假设堆超过了堆叠上限) 返回一个新的堆 """
        if self.is_empty():
            raise ValueError("this stack is empty")
        max_stack = self.Item.Info.MaxStackSize if self.Item.Info.MaxStackSize else self.Count
        count = min(max_stack, self.Count)
        self.Count -= count
        return type(self)(self.Item, count)

    def take_half(self):
        # type: () -> ItemStack
        """ 从堆中取出一半的物品 返回一个新的堆 """
        if self.is_empty():
            raise ValueError("this stack is empty")
        count = int(math.ceil(self.Count / 2.0))
        self.Count -= count
        return type(self)(self.Item, count)

    def is_empty(self):
        return self.Count <= 0

    def copy(self):
        # type(self) 而不是 ItemStack: 兄弟类(如扩展的 FluidStack)靠覆写 KIND 区分种类,
        # 写死基类会在这里把 KIND 弄丢 —— 而 render_slot 的分发正好在 copy 之后
        # (数量 > 1 时先 _with_amount 复制一份再取 KIND)。同理适用于上面几个 take_*。
        return type(self)(
            self.Item.copy(),
            self.Count,
        )

    def same_as(self, other):
        return isinstance(other, ItemStack) and self.Item == other.Item

    def get_render_data(self):
        item = self.Item
        return item.ItemId, item.AuxValue, item.IsEnchanted, item.Attr.UserData

    def get_key(self):  # type: () -> tuple
        return keys.make_key(self.Item.ItemId, self.Item.AuxValue)

    def to_dict(self):  # type: () -> dict
        return {
            "key": keys.key_to_str(self.get_key()),
            "count": self.Count,
        }

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> ItemStack
        """ 反序列化. Item 经 set_item_factory 注入的工厂构造, 未注入则退化为裸 Item """
        if not isinstance(data, dict):
            raise ValueError("stack data must be dict")
        item_id, aux = keys.key_from_str(data["key"])
        factory = _ITEM_FACTORY[0]
        item = factory(item_id, aux) if factory else Item(item_id, aux)
        return cls(item, data.get("count", 1))

    def __eq__(self, other):
        return (
            isinstance(other, ItemStack)
            and self.Item == other.Item
            and self.Count == other.Count
        )

    def __hash__(self):
        return hash((
            self.Item,
            self.Count,
        ))




class Item(object):
    """
    存储物品信息的类型
    """

    __slots__ = (
        "ItemId", "AuxValue", "NameSpace", "Attr",
        "ExtraData", "_Info", "_HoverText",
        "_InfoLoaded", "_HoverLoaded", "_Loader"
    )

    def __init__(
            self,
            item_id,
            aux_value=0,
            attr=None,
            extra_data=None,
            loader=None
    ):  # type: (...) -> None
        self.ItemId = item_id  # type: str
        """ 物品唯一英文ID """
        self.AuxValue = aux_value  # type: int
        """ 物品特殊值 """
        self.NameSpace = item_id.split(":")[0]  # type: str
        """ 物品ID的命名空间 """

        self.Attr = attr if attr is not None else ItemAttr({})  # type: ItemAttr
        """ 物品属性 """
        self.ExtraData = extra_data  # type: any

        # 惰性字段
        self._Loader = loader  # type: callable or None
        self._Info = None  # type: ItemInfo or None
        self._InfoLoaded = False
        self._HoverText = None  # type: str or None
        self._HoverLoaded = False

    @property
    def Info(self):  # type: () -> ItemInfo
        """ 物品信息 """
        if not self._InfoLoaded:
            self._Info = self._load_info()
            self._InfoLoaded = True
        if not self._Info:
            raise ValueError("Info not loaded")
        return self._Info

    @property
    def HoverText(self):  # type: () -> str
        """ 物品的悬浮文本描述 """
        if not self._HoverLoaded:
            self._HoverText = self._load_hover()
            self._HoverLoaded = True

        if not self._HoverText:
            if self._HoverLoaded:
                item_name = self.Info.ItemName
                self._HoverText = item_name if item_name else "unknown item"
            else:
                raise ValueError("HoverText not loaded")

        return self._HoverText  # type: ignore

    @property
    def IsEnchanted(self):  # type: () -> bool
        if not self.Attr.EnchantData and not self.Attr.ModEnchantData:
            return False
        return True

    def matches(self, other):  # type: (Item) -> bool
        """ 匹配两个物品是否相同 和__eq__不同 这里只匹配ItemId和AuxValue """
        return (
            isinstance(other, Item)
            and self.ItemId == other.ItemId
            and self.AuxValue == other.AuxValue
        )

    def invalidate(self, field=None):
        if field is None or field == "info":
            self._Info = None
            self._InfoLoaded = False
        if field is None or field == "hover":
            self._HoverText = None
            self._HoverLoaded = False

    def _load_info(self):  # type: () -> ItemInfo
        if self._Loader is not None:
            info = self._Loader(self, "info")
            if info is not None:
                return info
        return ItemInfo()

    def _load_hover(self):  # type: () -> str
        if self._Loader is not None:
            hover = self._Loader(self, "hover")
            if hover is not None:
                return hover
        return ""

    def stack(self, count=1):  # type: (int) -> ItemStack
        """ 转化为物品堆 """
        if count < 1:
            raise ValueError("count must be greater than 0")
        return ItemStack(self, count=count)

    def stack_max(self):
        """ 转化为最大堆叠上限的物品堆 """
        count = self.Info.MaxStackSize
        if not count:
            raise ValueError("cannot get max stack size")
        return ItemStack(self, count=count)

    def copy(self):
        """
        按槽位复制（utils/slots.py）：Attr、已加载的 Info 各自 copy，ExtraData 深拷，加载器与惰性字段的状态照搬；
        同一个类（原先写死构造 Item，子类一 copy 就降级）
        """
        return copy_slots(self, deep=("ExtraData",), copied=("Attr", "_Info"))

    def __eq__(self, other):
        return (
            isinstance(other, Item)
            and self.ItemId == other.ItemId
            and self.AuxValue == other.AuxValue
            and self.IsEnchanted == other.IsEnchanted
            and self.Attr == other.Attr
            and self.ExtraData == other.ExtraData
        )

    def __hash__(self):
        return hash((
            self.ItemId,
            self.AuxValue,
            self.IsEnchanted,
            self.Attr,
            to_hashable(self.ExtraData)
        ))

    def __ne__(self, other):
        return not self.__eq__(other)


class ItemInfo(object):
    """ 物品基本信息 来自 basic info """
    __slots__ = (
        "Tags", "IdAux", "ItemName", "ItemType", "Category", "MaxDurability",
        "MaxStackSize", "TierDict", "ItemTierLevel", "FuelDuration", "FoodNutrition",
        "FoodSaturation", "WeaponDamage", "ArmorDefense", "ArmorSlot",
        "ArmorToughness", "ArmorKnockbackResistance", "EnchantSlotType"
    )

    def __init__(
            self,
            id_aux = 0,
            item_name = "",
            tags=None,
            item_type = None,
            category = None,
            max_durability = None,
            max_stack_size = None,
            tier_dict=None,
            item_tier_level = None,
            fuel_duration = None,
            food_nutrition = None,
            food_saturation = None,
            weapon_damage = None,
            armor_defense = None,
            armor_slot = None,
            armor_toughness = None,
            armor_knockback_resistance = None,
            enchant_slot_type = None,
    ):
        if tier_dict is None:
            tier_dict = {}
        if tags is None:
            tags = []

        self.IdAux = id_aux # type: int
        """ 物品的ID AUX 主要用于客户端的ui绑定 """
        self.ItemName = item_name  # type: str
        """ 物品的本地化名称 """
        self.Tags = tags  # type: list
        """ 物品的标签 """
        self.ItemType = item_type  # type: str
        """ 物品类型 """
        self.Category = category  # type: str
        """ 物品的创造栏分类 """
        self.MaxDurability = max_durability  # type: int
        """ 物品最大耐久度 """
        self.MaxStackSize = max_stack_size  # type: int
        """ 物品最大堆叠数量 """
        self.TierDict = tier_dict # type: dict
        """ 物品自定义方块定义的挖掘相关的属性 """
        self.ItemTierLevel = item_tier_level  # type: int
        """ 物品挖掘等级 """
        self.FuelDuration = fuel_duration  # type: float
        """ 物品燃料时长 """
        self.FoodNutrition = food_nutrition # type: int
        """ 物品食物营养值 """
        self.FoodSaturation = food_saturation  # type: float
        """ 物品食物饱食度 """
        self.WeaponDamage = weapon_damage # type: int
        """ 物品武器伤害 """
        self.ArmorDefense = armor_defense  # type: int
        """ 物品护甲防御 """
        self.ArmorSlot = armor_slot  # type: int
        """ 物品护甲槽位 """
        self.ArmorToughness = armor_toughness  # type: int
        """ 物品护甲韧性 """
        self.ArmorKnockbackResistance = armor_knockback_resistance  # type: float
        """ 物品击退抗性 """
        self.EnchantSlotType = enchant_slot_type  # type: int
        """ 物品附魔槽位类型 """

    def copy(self):
        """ 按槽位复制（utils/slots.py）：Tags 浅拷、TierDict 深拷，别的照搬（新加的字段自动带上）"""
        return copy_slots(self, deep=("TierDict",), shallow=("Tags",))

    def __eq__(self, other):
        return (
            isinstance(other, ItemInfo)
            and self.IdAux == other.IdAux
            and self.ItemName == other.ItemName
            and self.Tags == other.Tags
            and self.ItemType == other.ItemType
            and self.Category == other.Category
            and self.MaxDurability == other.MaxDurability
            and self.MaxStackSize == other.MaxStackSize
            and self.TierDict == other.TierDict
            and self.ItemTierLevel == other.ItemTierLevel
            and self.FuelDuration == other.FuelDuration
            and self.FoodNutrition == other.FoodNutrition
            and self.FoodSaturation == other.FoodSaturation
            and self.WeaponDamage == other.WeaponDamage
            and self.ArmorDefense == other.ArmorDefense
            and self.ArmorSlot == other.ArmorSlot
            and self.ArmorToughness == other.ArmorToughness
            and self.ArmorKnockbackResistance == other.ArmorKnockbackResistance
            and self.EnchantSlotType == other.EnchantSlotType
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((
            self.IdAux,
            self.ItemName,
            to_hashable(self.Tags),
            self.ItemType,
            self.MaxDurability,
            self.MaxStackSize,
            to_hashable(self.TierDict),
            self.ItemTierLevel,
            self.FuelDuration,
            self.FoodNutrition,
            self.FoodSaturation,
            self.WeaponDamage,
            self.ArmorDefense,
            self.ArmorSlot,
            self.ArmorToughness,
            self.ArmorKnockbackResistance,
            self.EnchantSlotType
        ))


class ItemAttr(object):
    """ 物品的属性类 """
    __slots__ = (
        "UserData", "ShowInHand", "EnchantData", "ModEnchantData",
        "CustomTips", "ExtraId", "Durability"
    )

    def __init__(
            self,
            user_data= None,
            show_in_hand=True,
            enchant_data=None,
            mod_enchant_data=None,
            custom_tips="",
            extra_id="",
            durability=0,
        ):
        if enchant_data is None:
            enchant_data = []
        if mod_enchant_data is None:
            mod_enchant_data = []
        self.UserData = user_data  # type: dict
        """ 物品的UserData """
        self.ShowInHand = show_in_hand  # type: bool
        """ 物品是否显示在手上 """
        self.EnchantData = enchant_data  # type: list
        """ 物品的附魔信息 """
        self.ModEnchantData = mod_enchant_data  # type: list
        """ 物品的模组附魔信息 """
        self.CustomTips = custom_tips  # type: str
        """ 物品的自定义tips """
        self.ExtraId = extra_id  # type: str
        """ 物品的自定义ID """
        self.Durability = durability  # type: int
        """ 物品耐久值 """

    def copy(self):
        """ 按槽位复制（utils/slots.py）：UserData 深拷、两份附魔表浅拷，别的照搬（新加的字段自动带上）"""
        return copy_slots(self, deep=("UserData",), shallow=("EnchantData", "ModEnchantData"))

    def __eq__(self, other):
        if not isinstance(other, ItemAttr):
            return NotImplemented
        return (
            self.UserData == other.UserData
            and self.ShowInHand == other.ShowInHand
            and self.EnchantData == other.EnchantData
            and self.ModEnchantData == other.ModEnchantData
            and self.CustomTips == other.CustomTips
            and self.ExtraId == other.ExtraId
            and self.Durability == other.Durability
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((
            to_hashable(self.UserData),
            self.ShowInHand,
            to_hashable(self.EnchantData),
            to_hashable(self.ModEnchantData),
            self.CustomTips,
            self.ExtraId,
            self.Durability
        ))