# ----------------------------------------------------------------------
#  recipe.pyi is part of MoreEnoughItems.
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
from typing import Dict, List, Tuple, Any, Optional, Type

from .ingredient import IngredientLike
from .item import Stack

ID_NAMESPACE: str
ID_HASH_LEN: int


def register_recipe_class(cls: Type["Recipe"]) -> Type["Recipe"]: ...
def get_recipe_class(name: str) -> Optional[Type["Recipe"]]: ...


class Ingredient(IngredientLike):
    __slots__ = ("Stacks", "Amount", "TagId", "Chance")

    Stacks: List[Stack]
    Amount: int
    TagId: Optional[str]
    Chance: float

    def __init__(
            self,
            stacks: List[Stack],
            amount: int = 1,
            tag_id: Optional[str] = None,
            chance: float = 1.0
    ): ...

    @classmethod
    def of(cls, stack: Stack, amount: int = 1) -> Ingredient: ...
    @classmethod
    def from_tag(cls, stacks: List[Stack], amount: int = 1,
                 tag_id: Optional[str] = None) -> Ingredient: ...
    def is_empty(self) -> bool: ...
    def get_stacks(self) -> List[Stack]: ...
    def get_amount(self) -> int: ...
    def get_chance(self) -> float: ...
    def get_tag_id(self) -> Optional[str]: ...
    def first(self) -> Optional[Stack]: ...
    def accepts(self, stack: Stack) -> bool: ...
    def to_dict(self) -> Dict[str, Any]: ...

    # 身份计算用的规范形: 与 to_dict 只差「tag 先折叠」
    def to_canonical(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ingredient: ...


class Recipe(object):
    __slots__ = ("Id", "Type", "Inputs", "Outputs", "Catalysts", "Data")

    INPUTS_ORDERED: bool

    Id: str
    Type: str
    Inputs: List[Ingredient]
    Outputs: List[Ingredient]
    Catalysts: List[Ingredient]
    Data: Dict

    def __init__(self, recipe_type: str, inputs: List[Ingredient],
                 outputs: List[Ingredient], catalysts: List[Ingredient] = None,
                 data: Dict = None, recipe_id: Optional[str] = None): ...

    def GetInputs(self) -> List[Ingredient]: ...
    def GetOutputs(self) -> List[Ingredient]: ...
    def GetPrimaryOutput(self) -> Optional[Ingredient]: ...
    def GetByproducts(self) -> List[Ingredient]: ...
    def GetCatalysts(self) -> List[Ingredient]: ...
    def GetShownCatalysts(self) -> List[Ingredient]: ...
    def GetShape(self) -> Optional[Tuple[int, int]]: ...

    def ComputeId(self) -> str: ...
    def _to_canonical(self) -> Dict[str, Any]: ...
    def _extra_to_canonical(self) -> Dict[str, Any]: ...
    def _extra_to_dict(self) -> Dict[str, Any]: ...
    def ToDict(self) -> Dict[str, Any]: ...
    @classmethod
    def FromDict(cls, data: Dict[str, Any]) -> Recipe: ...
    @classmethod
    def _build(cls, data: Dict[str, Any], inputs: List[Ingredient],
               outputs: List[Ingredient], catalysts: List[Ingredient]) -> Recipe: ...
