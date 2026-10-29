# coding=utf-8

# ----------------------------------------------------------------------
#  slots.py is part of MoreEnoughItems.
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
配方槽位的渲染契约，所有配方页脚本共用，非原版专属。
自 extensions 化起由 api 门面导出给第三方（api/context.py 的 UI 组）。
"""
from MEIScripts.common.classes.types import Ingredient
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.controls.panel import MultiItemPanel

DEFAULT_KIND = "item"
""" 没有种类信息时的兜底。物品是 MEI 唯一内置的条目种类 """


class SlotPanelRegistry(object):
    """
    条目种类 -> 槽位面板类。`render_slot` 的分发表。

    这是 `structure.md` 决策 B′ 的 UI 那一半：**只把「渲染」这一件能力
    按种类分发**，比较与序列化继续走 `get_key()` / `to_dict()`
    —— 所以加一种 KIND 不会漂移 `Recipe.Id`。
    ⇒ MEI 核心不认识任何具体的流体/气体 id，贴图与配色是扩展自己的数据。

    面板类的契约(鸭子类型, 与 ItemPanel 一致)：
      · `from_empty(control)`                    —— 空格
      · `from_item_stack(control, stack)`        —— 单候选
      · `from_item_stack_list(control, stacks)`  —— 多候选, **只有注册了 multi 才会被调**
    """

    _PANELS = {}
    """ kind -> (单候选面板类, 多候选面板类 or None) """

    @classmethod
    def Register(cls, kind, panel_cls, multi_cls=None):
        # type: (str, type, type) -> None
        """
        注册一种条目的槽位面板。

        `multi_cls=None` 表示**该种类不参与多候选轮播** —— 多候选时退回单候选面板
        只画第一个。流体就是这样：一格流体永远是一种流体，轮播对它没有意义。

        之所以显式收两个类，而不是靠「面板类有没有 from_item_stack_list」鸭子判断：
        隐式契约在本仓栽过太多次(绑定名拼接、按钮 flag 分流)，
        **少写一个方法就静默退化、且零运行期信号**，不值省那几行。
        """
        if not kind:
            raise ValueError("kind must be a non-empty string")
        cls._PANELS[kind] = (panel_cls, multi_cls)

    @classmethod
    def Unregister(cls, kind):
        # type: (str) -> bool
        """ 撤掉一种条目的面板（扩展 OnUnload 用，extensions.md §5.2）；物品（DEFAULT_KIND）撤不掉，没注册过返回 False """
        if not kind or kind == DEFAULT_KIND or kind not in cls._PANELS:
            return False
        del cls._PANELS[kind]
        return True

    @classmethod
    def Get(cls, kind):
        # type: (str) -> tuple
        """ 取 (单候选类, 多候选类)。未注册的种类退回物品面板，不抛 """
        return cls._PANELS.get(kind) or cls._PANELS[DEFAULT_KIND]


SlotPanelRegistry.Register(DEFAULT_KIND, ItemPanel, MultiItemPanel)


def render_slot(control, slot, kind=None):
    """
    统一槽位渲染入口，slot 可为 Stack / Ingredient / None

    `kind` 显式指定条目种类，用于**空格**与**强制指定**两种场合：
    空格时没有 Stack 可问，而「这个控件是流体槽」是**调用方的界面事实**
    —— 写布局的人知道 `fluid0` 是流体控件，框架不该去猜。
    不传则从第一个候选的 `Stack.KIND` 推断，仍推不出就当物品。
    """
    # 0 候选 -> 空面板; 1 候选 -> 单候选面板; 多候选 -> 轮播(若该种类注册了 multi)
    # Stack 与 Ingredient 均实现 IngredientLike 契约, Stack 是单元素退化形态
    if slot is None:
        return SlotPanelRegistry.Get(kind or DEFAULT_KIND)[0].from_empty(control)
    stacks = [s for s in slot.get_stacks() if s and not s.is_empty()]
    if not stacks:
        return SlotPanelRegistry.Get(kind or DEFAULT_KIND)[0].from_empty(control)

    # 数量只由 Ingredient.Amount 承载, 候选 Stack 的 Count 一律归一化为 1,
    # 渲染时必须把 Amount 贴回去, 否则格子右下角的数字永远不显示
    amount = slot.get_amount() or 1
    if amount > 1:
        stacks = [_with_amount(s, amount) for s in stacks]

    single, multi = SlotPanelRegistry.Get(
        kind or getattr(stacks[0], "KIND", DEFAULT_KIND))
    if len(stacks) == 1 or multi is None:
        return single.from_item_stack(control, stacks[0])
    return multi.from_item_stack_list(control, stacks)


def _with_amount(stack, amount):
    """ 复制一份并把 Count 设为需求量，不改原对象 """
    # 原对象被配方与索引共享，就地改会污染所有引用方
    shown = stack.copy()
    shown.Count = amount
    return shown


def flatten_inputs(inputs):  # type: (list) -> list
    """
    按 Amount 把输入摊平：一份 Amount=4 的木板 -> 四份 Amount=1 的木板

    **无序配方专用。** 引擎给的是「这条配方吃 4 个木板」（一个 Ingredient，Amount=4），
    那是**正确的数据**；而"占 4 个格子"是**合成网格的呈现事实**。
    两者不该混：摊平只发生在这一层，`Recipe.Inputs` 一个字都不动 ——
    动了就等于改 to_canonical，全部无序配方的 Id 会漂移，
    玩家的置顶与配方书签集体作废（probe_identity 的 GOLDEN_IDS 就是守这个的）。
    """
    flat = []
    for ingredient in inputs or ():
        if ingredient is None:
            continue
        # 零候选的是"空格"而不是"需要一个什么都不是", 不占格子
        if not [s for s in (ingredient.get_stacks() or ()) if s and not s.is_empty()]:
            continue
        # 每格只放一个: 数量已由"占几格"表达, 再带 Amount 会让格子右下角显示 x4
        amount = max(1, int(ingredient.get_amount() or 1))
        single = Ingredient(ingredient.get_stacks(), 1,
                            ingredient.TagId, ingredient.get_chance())
        flat.extend([single] * amount)
    return flat


def resolve_input_slot(recipe, ui_index, columns):
    """ 把 UI 网格下标映射到配方输入 Ingredient，越界或空槽返回 None """
    # columns 必填: 「网格是几列」是**调用方的界面事实**, 不是框架的知识.
    # 原先这里默认 3, 等于把工作台的布局写进了通用模块
    inputs = recipe.GetInputs()
    shape = recipe.GetShape()

    if shape:
        # 有序: 按配方**真实宽度**在固定 columns 的网格里定位 ——
        # 2x2 的配方在 3 列网格里落在 0/1/3/4, 不是 0/1/2/3
        width, height = shape
        ui_row, ui_col = divmod(ui_index, columns)
        if ui_row < height and ui_col < width:
            flat = ui_row * width + ui_col
            if 0 <= flat < len(inputs):
                return inputs[flat]
        return None

    # 无序: 摊平后按顺序铺放, 一个格子一个物品
    flat_inputs = flatten_inputs(inputs)
    return flat_inputs[ui_index] if 0 <= ui_index < len(flat_inputs) else None
