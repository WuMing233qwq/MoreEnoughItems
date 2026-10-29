# ----------------------------------------------------------------------
#  item.pyi is part of MoreEnoughItems.
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

from typing import Dict, List, Tuple, Any, Callable, Optional, Hashable

from .ingredient import IngredientLike


def set_item_factory(factory: Optional[Callable[[str, int], Item]]) -> None: ...


class Stack(IngredientLike):
    KIND: str
    __slots__ = (
        "Count",
    )

    def __init__(
            self,
            count: int=1,
    ):
        self.Count = count

    def get_stacks(self) -> List[Stack]: ...
    def get_amount(self) -> int: ...
    def is_empty(self) -> bool: ...
    def copy(self) -> Stack: ...
    def same_as(self, other: Stack) -> bool: ...
    def get_render_data(self) -> Any: ...
    def get_key(self) -> Tuple[str, int]: ...
    def to_dict(self) -> Dict[str, Any]: ...

class ItemStack(Stack):
    __slots__ = (
        "Item",
    )

    def __init__(
            self,
            item: Item,
            count: int = 1,
    ):
        super(ItemStack).__init__(count)
        self.Item: Item = item

    def is_empty(self) -> bool: ...
    def take(self, count: int=1) -> ItemStack: ...
    def take_all(self) -> ItemStack: ...
    def take_stack(self) -> ItemStack: ...
    def take_half(self) -> ItemStack: ...
    def copy(self) -> ItemStack: ...
    def same_as(self, other: ItemStack) -> bool: ...
    def get_render_data(self) -> Tuple[str, int, bool, Optional[Dict[str, Any]]]: ...
    def get_key(self) -> Tuple[str, int]: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ItemStack: ...

class Item(object):
    __slots__ = (
        "ItemId", "AuxValue", "NameSpace", "Attr",
        "ExtraData", "_Info", "_HoverText",
        "_InfoLoaded", "_HoverLoaded", "_Loader"
    )

    def __init__(
            self,
            item_id: str,
            aux_value: int = 0,
            attr: Optional[ItemAttr] = None,
            extra_data: Dict[Hashable, Hashable] = None,
            loader: Callable = None
    ):
        self.ItemId: str = item_id
        self.AuxValue: int = aux_value
        self.NameSpace: str = str
        self.Attr: ItemAttr = attr
        self.ExtraData: Any = extra_data

        self._Loader: Optional[Callable] = loader
        self._Info: Optional[ItemInfo] = None
        self._InfoLoaded: bool = False
        self._HoverText: Optional[str] = None
        self._HoverLoaded: bool = False

    @property
    def IsEnchanted(self) -> bool: ...
    @property
    def Info(self) -> ItemInfo: ...
    @property
    def HoverText(self) -> str: ...
    def matches(self, other: Item) -> bool: ...
    def invalidate(self): ...
    def stack(self, count: int = 1) -> ItemStack: ...
    def stack_max(self) -> ItemStack: ...
    def copy(self) -> Item: ...
    def _load_info(self):...
    def _load_hover(self):...


class ItemInfo(object):
    __slots__ = (
        "Tags", "IdAux", "ItemName", "ItemType", "Category", "MaxDurability",
        "MaxStackSize", "TierDict", "ItemTierLevel", "FuelDuration", "FoodNutrition",
        "FoodSaturation", "WeaponDamage", "ArmorDefense", "ArmorSlot",
        "ArmorToughness", "ArmorKnockbackResistance", "EnchantSlotType"
    )

    def __init__(
            self,
            id_aux: int = 0,
            item_name: str = "",
            tags: List[str] = None,
            item_type: Optional[str] = None,
            category: Optional[str] = None,
            max_durability: Optional[int] = None,
            max_stack_size: Optional[int] = None,
            tier_dict: Dict[str, Any]=None,
            item_tier_level: Optional[int] = None,
            fuel_duration: Optional[float] = None,
            food_nutrition: Optional[int] = None,
            food_saturation: Optional[float] = None,
            weapon_damage: Optional[int] = None,
            armor_defense: Optional[int] = None,
            armor_slot: Optional[int] = None,
            armor_toughness: Optional[int] = None,
            armor_knockback_resistance: Optional[float] = None,
            enchant_slot_type: Optional[int] = None,

    ):
        self.IdAux: int = id_aux
        self.ItemName: str = item_name
        self.Tags: List[str] = tags
        self.ItemType: Optional[str] = item_type
        self.Category: Optional[str] = category
        self.MaxDurability: Optional[int] = max_durability
        self.MaxStackSize: Optional[int] = max_stack_size
        self.TierDict: Optional[Dict] = tier_dict
        self.ItemTierLevel: Optional[int] = item_tier_level
        self.FuelDuration: Optional[float] = fuel_duration
        self.FoodNutrition: Optional[int] = food_nutrition
        self.FoodSaturation: Optional[float] = food_saturation
        self.WeaponDamage: Optional[int] = weapon_damage
        self.ArmorDefense: Optional[int] = armor_defense
        self.ArmorSlot: Optional[int] = armor_slot
        self.ArmorToughness: Optional[int] = armor_toughness
        self.ArmorKnockbackResistance: Optional[float] = armor_knockback_resistance
        self.EnchantSlotType: Optional[int] = enchant_slot_type

    def copy(self) -> ItemInfo: ...

class ItemAttr(object):
    __slots__ = (
        "UserData", "ShowInHand", "EnchantData", "ModEnchantData",
        "CustomTips", "ExtraId", "Durability"
    )

    def __init__(
            self,
            user_data: Dict[str, Any] = None,
            show_in_hand: bool = True,
            enchant_data: Optional[List[Tuple[int, int]]] = None,
            mod_enchant_data: Optional[List[Tuple[str, int]]] = None,
            custom_tips: str = "",
            extra_id: str = "",
            durability: int = 0,
        ):
        if mod_enchant_data is None:
            mod_enchant_data = []
        if enchant_data is None:
            enchant_data = []
        self.UserData: Optional[Dict[str, Any]] = user_data
        self.ShowInHand: bool = show_in_hand
        self.EnchantData: List[Tuple[int, int]] = enchant_data
        self.ModEnchantData: List[Tuple[str, int]] = mod_enchant_data
        self.CustomTips: str = custom_tips
        self.ExtraId: str = extra_id
        self.Durability: int = durability

    def copy(self) -> ItemAttr:...