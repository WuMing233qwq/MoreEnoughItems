# coding=utf-8

# ----------------------------------------------------------------------
#  types.py is part of MoreEnoughItems.
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
工作台的配方数据模型：有序（按网格铺平）与无序两种。
"""
from MEIScripts.api.facades.types import Recipe, register_recipe_class


@register_recipe_class
class ShapedRecipe(Recipe):
    """
    有序配方. Inputs 按**真实 Width** 行主序铺平 (不补齐到固定列数),
    因此 Width 不是可选的展示信息, 而是 Inputs 的解码密钥 —— 消费端必须经 GetShape() 取得.

    身份规则: Width/Height **计入** canonical (布局的充要信息);
    Pattern **不计入** —— 它只是原始字符标签, 两条 flatten 后完全相同、
    仅 key 字符不同的配方本就该同 Id.
    """

    __slots__ = ("Width", "Height", "Pattern")

    def __init__(
            self,
            recipe_type,
            inputs,
            outputs,
            width,
            height,
            pattern,
            catalysts=None,
            data=None,
            recipe_id=None
    ):
        # Extra 字段必须**先于**基类构造赋值: 基类末尾要算 Id, 而 canonical 会读它们
        self.Width = width  # type: int
        self.Height = height  # type: int
        self.Pattern = list(pattern) if pattern else []  # type: list
        Recipe.__init__(self, recipe_type, inputs, outputs, catalysts, data, recipe_id)

    def GetShape(self):  # type: () -> tuple
        return self.Width, self.Height

    def _extra_to_canonical(self):
        return {"width": self.Width, "height": self.Height}

    def _extra_to_dict(self):
        return {"width": self.Width, "height": self.Height, "pattern": list(self.Pattern)}

    @classmethod
    def _build(cls, data, inputs, outputs, catalysts):
        extra = data.get("extra") or {}
        return cls(
            data.get("type", ""),
            inputs,
            outputs,
            extra.get("width", 0),
            extra.get("height", 0),
            extra.get("pattern", []),
            catalysts,
            data.get("data"),
            data.get("id"),
        )

@register_recipe_class
class ShapelessRecipe(Recipe):
    """ 无序配方: 输入顺序不承载语义, 故 canonical 时排序, 保证同配方不同书写顺序同 Id """

    __slots__ = ()

    INPUTS_ORDERED = False
