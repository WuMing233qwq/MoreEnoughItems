# coding=utf-8
# ----------------------------------------------------------------------
#  recipe.py is part of MoreEnoughItems.
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
from MEIScripts.utils import HashableMaker
from MEIScripts.utils.stablehash import stable_digest, stable_text
from .ingredient import IngredientLike
from .item import Stack, ItemStack

to_hashable = HashableMaker.to_hashable

ID_NAMESPACE = "mei"
""" 合成 Id 的命名空间前缀 (EMI 的 "ns:/path" 约定) """

ID_HASH_LEN = 16
"""
指纹的十六进制位数. 16 位 = 64 bit.

原为 md5 前 8 位(32 bit) —— 但 32 bit 在 10^4 条配方量级的碰撞概率已达 1%,
换算法时一并提到 64 bit(约 3e-10).
"""

_RECIPE_CLASSES = {}
""" {类名: 类} 反序列化分发注册表 —— 基类 classmethod 自己认不出 Shaped """


def register_recipe_class(cls):
    """ 注册配方子类以支持 FromDict 分发; 可作装饰器用 """
    _RECIPE_CLASSES[cls.__name__] = cls
    return cls


def get_recipe_class(name):  # type: (str) -> type or None
    return _RECIPE_CLASSES.get(name)


class Ingredient(IngredientLike):
    """
    配方槽位规格: 一组可替代的 Stack (标签/任选其一) + 需求数量.

    与 Stack 的分界线是「有身份 vs 无身份」—— Ingredient 是**规格/谓词**,
    一组候选无法作为索引键有意义地存在, 故它永远没有 get_key();
    索引一律展开 get_stacks() 后逐个 Stack 入桶.

    数量约定: 数量只由 Amount 承载, 候选 Stack 的 Count 一律为 1 (由构造方归一化).
    """

    __slots__ = ("Stacks", "Amount", "TagId", "Chance")

    def __init__(self, stacks, amount=1, tag_id=None, chance=1.0):
        self.Stacks = list(stacks) if stacks else []  # type: list
        self.Amount = amount
        self.TagId = tag_id  # type: str or None
        self.Chance = chance  # type: float

    @classmethod
    def of(cls, stack, amount=1):
        """ 由单个 Stack 构造 """
        return cls([stack], amount)

    @classmethod
    def from_tag(cls, stacks, amount=1, tag_id=None):
        """ 由一组可替代 Stack 构造 (标签); tag_id 为符号化引用, 可留空表示字面多选 """
        return cls(stacks, amount, tag_id=tag_id)

    def is_empty(self):
        return not self.Stacks or all(s is None or s.is_empty() for s in self.Stacks)

    def get_stacks(self):  # type: () -> list
        return self.Stacks

    def get_amount(self):  # type: () -> int
        return self.Amount

    def get_chance(self):  # type: () -> float
        return self.Chance

    def get_tag_id(self):  # type: () -> str or None
        return self.TagId

    def first(self):  # type: () -> Stack or None
        return self.Stacks[0] if self.Stacks else None

    def accepts(self, stack):  # type: (Stack) -> bool
        """ 规格匹配: 本槽位是否接受该 Stack (不对称). 与 Stack.same_as 语义不同 """
        return any(s.same_as(stack) for s in self.Stacks if s)

    def to_dict(self):  # type: () -> dict
        """
        序列化为贫血 dict.
        候选**排序**后输出 —— 候选集本身无序, 排序保证同一规格恒得同一表示,
        这是 Recipe.Id 稳定性的前提之一.
        """
        return {
            "stacks": sorted((s.to_dict() for s in self.Stacks if s), key=stable_text),
            "amount": self.Amount,
            "tag": self.TagId,
            "chance": self.Chance,
        }

    def to_canonical(self):  # type: () -> dict
        """
        **身份计算**用的规范形 —— 与 to_dict 的区别只有一条: **tag 先折叠**.

        有 TagId 时只发标签引用, 不展开成员. 这是必需的:
        像 mei:fuels 这种 tag 的成员是**异步分帧扫描**出来的, 若把成员写进 canonical,
        同一条熔炉配方在"扫到一半"和"扫完"两个时刻会算出不同的 Recipe.Id,
        索引会把它当成两条配方.
        (蓝本 前置仓 docs/RECIPE_BROWSER_DESIGN.md §4.3 的「tag 先折叠」)

        无 TagId 的字面多候选**照常参与身份** —— 它们是配方内容本身, 不是符号引用.
        """
        if self.TagId:
            return {"tag": self.TagId, "amount": self.Amount, "chance": self.Chance}
        return self.to_dict()

    @classmethod
    def from_dict(cls, data):  # type: (dict) -> Ingredient
        if not isinstance(data, dict):
            raise ValueError("ingredient data must be dict")
        stacks = [ItemStack.from_dict(s) for s in data.get("stacks", [])]
        return cls(
            stacks,
            data.get("amount", 1),
            tag_id=data.get("tag"),
            chance=data.get("chance", 1.0),
        )

    def __eq__(self, other):
        return (
            isinstance(other, Ingredient)
            and self.Amount == other.Amount
            and self.TagId == other.TagId
            and self.Chance == other.Chance
            and self.Stacks == other.Stacks
        )

    def __hash__(self):
        return hash((self.Amount, self.TagId, self.Chance, to_hashable(self.Stacks)))

    def __ne__(self, other):
        return not self.__eq__(other)

class Recipe(object):
    """
    配方基类

    Id        str               稳定身份 "mei:/<type>/<16 位十六进制指纹>", 见 ComputeId
                                (来源可在构造时传 recipe_id 指定; 不用 md5 —— 运行时被裁掉了)
    Type      str               所属合成类型 (由 RecipeCategory 承载)
    Inputs    list[Ingredient]  原料 (可含可替代候选)
    Outputs   list[Ingredient]  输出, index 0 = 主输出, 其余为副产物
    Catalysts list[Ingredient]  不消耗物品 (工作站/催化剂)
    Data      dict              展示元数据 (经验值/烧炼时间等), **不进 Id 的 canonical**

    身份规则: __eq__/__hash__ **只看 Id**. 内容变则 Id 变, 故内容比较由 Id 代理.
    """

    __slots__ = ("Id", "Type", "Inputs", "Outputs", "Catalysts", "Data")

    INPUTS_ORDERED = True
    """
    Inputs 的**列表顺序**是否承载语义.
    True (有序配方): 顺序即布局, canonical 时保序 —— 2x2 四角互换是另一条配方.
    False(无序配方): 顺序无意义, canonical 时排序 —— 同配方不同书写顺序应得同一 Id.
    """

    def __init__(
            self,
            recipe_type,
            inputs,
            outputs,
            catalysts=None,
            data=None,
            recipe_id=None
    ):
        self.Type = recipe_type
        self.Inputs = list(inputs) if inputs else []
        self.Outputs = list(outputs) if outputs else []
        self.Catalysts = list(catalysts) if catalysts else []
        self.Data = data if data is not None else {}
        # 注意: 子类必须在调用本构造之前赋值自己的 Extra 字段,
        # 因为 ComputeId 会经 _extra_to_canonical() 读取它们.
        self.Id = recipe_id if recipe_id else self.ComputeId()

    # 语义出口 —— 索引/配方树/可合成过滤只依赖这四个
# ======================================================================================================================
    def GetInputs(self):  # type: () -> list
        """ 原料 list[Ingredient] """
        return self.Inputs

    def GetOutputs(self):  # type: () -> list
        """ 全部输出 list[Ingredient] (含主输出与副产物) """
        return self.Outputs

    def GetPrimaryOutput(self):  # type: () -> Ingredient or None
        """ 主输出 """
        return self.Outputs[0] if self.Outputs else None

    def GetByproducts(self):  # type: () -> list
        """ 副产物 list[Ingredient] """
        return self.Outputs[1:]

    def GetCatalysts(self):  # type: () -> list
        """ 不消耗物品 list[Ingredient] """
        return self.Catalysts

    def GetShownCatalysts(self):  # type: () -> list
        """
        收藏栏展开这条配方时跟在原料后面显示的不消耗物品（工具），数量固定 1、不乘倍数。
        缺省是全部催化剂；催化剂其实是「任选一种」的一大类时（熔炉的燃料）子类覆写成 []
        """
        return self.Catalysts

    def GetShape(self):  # type: () -> tuple or None
        """
        有序配方返回 (Width, Height), 无序返回 None.

        消费端 (resolve_input_slot / 布局生成器 / 配方树) 一律调本方法判定形状,
        禁止用 getattr(recipe, "Width", None) 探测属性.
        """
        return None

    # 身份与序列化
# ======================================================================================================================
    def ComputeId(self):  # type: () -> str
        """
        由内容算出稳定身份.

        指纹算法见 utils/stablehash.py. 两条禁令:
          · **禁止内置 hash()** —— py2 的 str hash 在 32 位(Android/iOS)与
            64 位(Windows)上结果不同;
          · **禁止 hashlib** —— 网易运行时的 hashlib
            没有 md5 属性(被裁剪), 且"能力探测+退化"会让不同平台算出不同 Id.

        Id 已被置顶(state/pins.py)与配方书签用作**跨存档的持久身份**:
        改动本方法或 to_canonical 会静默作废所有玩家的置顶与收藏.
        """
        return "{}:/{}/{}".format(
            ID_NAMESPACE, self.Type,
            stable_digest(stable_text(self._to_canonical()), ID_HASH_LEN),
        )

    def _payload(self, canonical):  # type: (bool) -> dict
        """
        三组 Ingredient 的公共序列化骨架.

        canonical=True  用于**算 Id**: Ingredient 走 to_canonical(tag 折叠);
        canonical=False 用于**存盘**:   Ingredient 走 to_dict(完整候选, 否则 FromDict 还不回来).
        两者必须分家 —— 曾经 ToDict 是"基于 canonical 再补字段"拼出来的,
        tag 折叠一上线就会让存盘丢掉候选.

        Catalysts 顺序无语义故排序; Outputs 的 0 号是主输出故保序;
        Inputs 按 INPUTS_ORDERED 决定保序还是排序.
        """
        emit = (lambda ing: ing.to_canonical()) if canonical else (lambda ing: ing.to_dict())
        inputs = [emit(i) for i in self.Inputs]
        if not self.INPUTS_ORDERED:
            inputs = sorted(inputs, key=stable_text)
        return {
            "cls": type(self).__name__,
            "type": self.Type,
            "inputs": inputs,
            "outputs": [emit(o) for o in self.Outputs],
            "catalysts": sorted((emit(c) for c in self.Catalysts), key=stable_text),
        }

    def _to_canonical(self):  # type: () -> dict
        """
        Id 计算用的规范形.

        与 ToDict 的区别有三, 都不能合并:
          1. **不含 Data** —— Data 是展示元数据, 改一个显示字段不该换一条配方;
          2. **不含 Id 自身** —— 否则自引用;
          3. **tag 折叠** —— 见 Ingredient.to_canonical.
        """
        data = self._payload(True)
        data["extra"] = self._extra_to_canonical()
        return data

    def _extra_to_canonical(self):  # type: () -> dict
        """ 子类钩子: **参与身份**的额外字段 """
        return {}

    def _extra_to_dict(self):  # type: () -> dict
        """ 子类钩子: **参与存盘**的额外字段 (默认与 canonical 相同) """
        return self._extra_to_canonical()

    def ToDict(self):  # type: () -> dict
        """
        序列化为贫血 dict —— 只含 dict/list/str/int/float/bool/None,
        **无 tuple、无 Python 对象** (engineering.md §7-3).
        """
        data = self._payload(False)
        data["extra"] = self._extra_to_dict()
        data["id"] = self.Id
        data["data"] = self.Data
        return data

    @classmethod
    def FromDict(cls, data):  # type: (dict) -> Recipe
        """ 反序列化, 经 _RECIPE_CLASSES 分发到具体子类 """
        if not isinstance(data, dict):
            raise ValueError("recipe data must be dict")
        cls_name = data.get("cls")
        target = _RECIPE_CLASSES.get(cls_name)
        if target is None:
            raise ValueError("unknown recipe class: {!r}".format(cls_name))

        inputs = [Ingredient.from_dict(i) for i in data.get("inputs", [])]
        outputs = [Ingredient.from_dict(o) for o in data.get("outputs", [])]
        catalysts = [Ingredient.from_dict(c) for c in data.get("catalysts", [])]
        return target._build(data, inputs, outputs, catalysts)

    @classmethod
    def _build(cls, data, inputs, outputs, catalysts):  # type: (dict, list, list, list) -> Recipe
        """ 子类钩子: 由贫血 dict 与已还原的三组 Ingredient 构造实例 """
        return cls(
            data.get("type", ""),
            inputs,
            outputs,
            catalysts,
            data.get("data"),
            data.get("id"),
        )

    def __eq__(self, other):
        return isinstance(other, Recipe) and self.Id == other.Id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.Id)
