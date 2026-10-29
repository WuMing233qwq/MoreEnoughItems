# ----------------------------------------------------------------------
#  recipes.pyi is part of MoreEnoughItems.
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
from typing import Dict, List, Optional, Literal, Type, Tuple, Any

from MEIScripts.common.classes.base import BaseRecipeUIScript
from MEIScripts.common.classes.types import Item, ItemStack, Recipe, RecipeCategory


class __RecipeManager(object):
    """ 配方查询编排 """

    def __init__(self):
        self._query_cache: Optional[Any] = None

    # 由装配层注入的查询缓存(鸭子类型: Get/Put), 传 None 即关闭
    def SetQueryCache(self, cache: Optional[Any]) -> None:...

    @staticmethod
    def GetAllCraftingTypes() -> List[str]:...

    @staticmethod
    def GetCategory(crafting_type: str) -> Optional[RecipeCategory]:...

    @staticmethod
    def GetDisplayText(crafting_type: str) -> unicode:...

    @staticmethod
    def GetDisplayItemData(crafting_type: str) -> Optional[Tuple[str, int]]:...

    # JSON UI 的 namespace.control_name, 交给 CreateChildControl 实例化
    @staticmethod
    def GetControlDef(crafting_type: str) -> Optional[str]:...

    # tooltip 配方预览的 grid 定义名; 类型没声明给 None
    @staticmethod
    def GetPreviewDef(crafting_type: str) -> Optional[str]:...

    @staticmethod
    def GetCraftingStations(crafting_type: str) -> List[ItemStack]:...

    def QueryRecipe(self, item: Item, query_by: Literal["output", "input"]="output",
                    types: List[str]=None) -> Dict[str, List[Recipe]]:...

    # 一个类别的全部配方 + 是否完整; 怎么凑出全量是各来源自己的事
    @staticmethod
    def QueryAll(category_id: str) -> Tuple[List[Recipe], bool]:...

    # 同 QueryRecipe, 但多返回一个「结果是否完整」标志
    def QueryRecipeEx(self, item: Item, query_by: Literal["output", "input"]="output",
                      types: List[str]=None) -> Tuple[Dict[str, List[Recipe]], bool]:...

class __RecipeUIManager(object):
    def __init__(self):
        Dict
        self.scripts: Dict[str, Tuple[Type[BaseRecipeUIScript], Dict[str, Any]]] = {}

    # 键是类别 id; 控件定义名走 RecipeManager.GetControlDef
    def RegisterScript(self, category_id: str, script: Type[BaseRecipeUIScript], params: Dict[str, Any]=None) -> bool:...

    def UnRegisterScript(self, category_id: str) -> bool:...

    def GetScriptData(self, category_id: str) -> Optional[Tuple[Type[BaseRecipeUIScript], Dict[str, Any]]]:...


RecipeUIManager: __RecipeUIManager

RecipeManager: __RecipeManager