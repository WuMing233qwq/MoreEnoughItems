# coding=utf-8

# ----------------------------------------------------------------------
#  mei_extension.py is part of MoreEnoughItems.
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
MEI 扩展的最小样例（docs/samples/mei_sample）：一个配方类型「研磨」—— 类型、来源（自己的配方表）、配方页脚本，
以及卸载时的反注册（热重载、重进世界都靠它）。

**整个文件不 import MEI 的任何东西**（第三方物理上做不到，extensions.md §1.1）：基类从 MEI 的组件拿（client_system.py），
别的一律从生命周期方法的 ctx 拿 —— 所以扩展类、配方页脚本都写在函数里。
"""

CATEGORY_ID = "sample:grinding"
""" 类型 Id：全局唯一、带命名空间（同一个 Id 不能注册两次，也不能覆盖原版的工作台、熔炉） """

RECIPES = (
    # (原料, 产物, 产物几个)
    ("minecraft:cobblestone", "minecraft:gravel", 1),
    ("minecraft:gravel", "minecraft:sand", 1),
    ("minecraft:bone", "minecraft:bone_meal", 4),
)

_BUILT = {}
""" 造好的类缓存在这里：每次进世界都注册同一个类，MEI 才认得出是同一个扩展（重复注册是幂等的）"""


def build(MeiExtension):
    """ 拿到 MEI 的扩展基类（mei.GetExtensionCls()）后造出扩展类；同一个基类只造一次 """
    cls = _BUILT.get(MeiExtension)
    if cls is None:
        cls = _BUILT[MeiExtension] = _make_extension(MeiExtension)
    return cls


def _make_extension(MeiExtension):

    class SampleExtension(MeiExtension):
        ID = "sample:grinding"
        NAME = "sample.mei.ext.name"  # 本地化键（resource/texts/zh_CN.lang）
        DESCRIPTION = "sample.mei.ext.desc"
        AUTHOR = "MEI Sample"
        VERSION = "1.0.0"
        MIN_API_VERSION = 2

        def OnRegister(self, ctx):
            category = ctx.Types.RecipeCategory(
                category_id=CATEGORY_ID,
                name_key="sample.mei.category.grinding",
                icon=("minecraft:grindstone", 0),
                control_def="SampleMei.RECIPES_GRID",  # resource/ui/sample_mei.json
                stations=ctx.Registry.ItemFactory.GetStacksFromIds(["minecraft:grindstone"]),
                sort_index=50,
            )
            registry = ctx.Registry.SourceRegistry
            if not registry.RegisterCategory(category):
                ctx.Log.warn("类型 {} 注册不上（Id 被占了？），不接了".format(CATEGORY_ID))
                return
            source = ctx.Types.StaticRecipeSource(CATEGORY_ID)
            source.AddAll(_recipes(ctx))
            registry.RegisterSource(source)  # 来源挂在类型下：必须先注册类型
            ctx.Registry.RecipeUIManager.RegisterScript(CATEGORY_ID, _make_ui_script(ctx))

        def OnUnload(self, ctx):
            # 注册过的每一样都要撤（extensions.md §5.2）：不撤的话热重载、重进世界会叠一份
            ctx.Registry.RecipeUIManager.UnRegisterScript(CATEGORY_ID)
            ctx.Registry.SourceRegistry.UnRegisterCategory(CATEGORY_ID)  # 连同名下的来源一起撤

    return SampleExtension


def _recipes(ctx):  # type: (any) -> list
    """ 配方表 -> MEI 的配方；物品表里没有的（别的版本、没装的模组）跳过 """
    stacks_of = ctx.Registry.ItemFactory.GetStacksFromIds
    Ingredient = ctx.Types.Ingredient
    recipes = []
    for source_id, result_id, count in RECIPES:
        inputs, outputs = stacks_of([source_id]), stacks_of([result_id], count)
        if not inputs or not outputs:
            continue
        recipes.append(ctx.Types.Recipe(CATEGORY_ID, [Ingredient(inputs, 1)], [Ingredient(outputs, count)]))
    return recipes


def _make_ui_script(ctx):
    """ 配方页脚本：一格原料、一格产物（控件路径在 sample_mei.json 里，绑定前缀也是）"""
    binding = ctx.UI.Binding
    render_slot = ctx.UI.Slots.render_slot

    class GrindingUIScript(binding.RecipeUIScript):
        def __init__(self, recipe):
            binding.RecipeUIScript.__init__(self, recipe=recipe)
            self.InputControl = None
            self.OutputControl = None

        def OnCreate(self):
            self.InputControl = self.RecipeControl.GetChildByPath("/wrapper/content/input/0")
            self.OutputControl = self.RecipeControl.GetChildByPath("/wrapper/content/output/0")

        @binding.RecipeBinder.Group(["sample_mei.recipe.input"])
        def InputPanel(self, _):
            inputs = self.Recipe.GetInputs()
            return render_slot(self.InputControl, inputs[0] if inputs else None)

        @binding.RecipeBinder.Group(["sample_mei.recipe.output"])
        def OutputPanel(self, _):
            return render_slot(self.OutputControl, self.Recipe.GetPrimaryOutput())

        def OnDestroy(self):
            self.DestroyBindings()

    return GrindingUIScript
