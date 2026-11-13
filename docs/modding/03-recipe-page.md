# 03 · 配方页

> 上一篇：[02 · 注册配方](02-recipes.md)。接口签名：[api.md](api.md)。

<a id="json"></a>
## 1. JSON 规范

```json
"RECIPES_GRID@mei_recipe_common.recipes_grid": { "$recipe_ui_template": "YourModMei.recipe" },
"PREVIEW@mei_recipe_common.preview":           { "$recipe_content_template": "YourModMei.content_panel" },
"recipe": {
    "size": [188, 74],
    "controls": [
        { "wrapper": { "size": [134, 70], "controls": [ { "content@YourModMei.content_panel": {} } ] } },
        { "buttons@mei_recipe_common.buttons_panel_vertical": {} }
    ]
},
"content_panel": { "size": [134, 70], "controls": [ /* 格子、箭头、进度 */ ] }
```

1. 配方行的定义名叫 `recipe`，写绝对尺寸；里面是 `wrapper/content`。
2. **wrapper 与 content 都写算出来的绝对尺寸**，content 正好填满 wrapper（行 `[188, 74]` → wrapper、content `[134, 70]`）。
3. **content 自包含**：它用的变量写在它自己身上，别靠配方行往下传 —— tooltip 预览里只有 content。几种共用一个 content 的，每种派生一个。
4. **紧跟在 `RECIPES_GRID` 后面写 `PREVIEW` 那一行**（不写尺寸）：tooltip 的配方预览就有了，Python 一行不用写。
   不要预览（行里有交互、太大）：显式说不要 —— `RecipeCategory(..., preview_def=None)`；老版本 MEI 不认这个参数，兼容写法：
   ```python
   if "PreviewDef" in getattr(type(category), "__slots__", ()):
       category.PreviewDef = ""
   ```
5. **物品格一律用 MEI 自己的 20×20**（`mei_common.item_panel` 或从 `mei_common.slot_base` 组装，§6）—— 别照抄你机器界面的 18 / 26，MEI 的页面上格子大小要一样。
6. 配方行想多占地方，改 `wrapper` 的尺寸，不是 `recipe` 的；行比配方页最小宽（188）还宽时，给你的 grid 写上行宽。

<a id="script"></a>
## 2. 配方页脚本（[api §6.3](api.md#ui-binding)）

```python
def BuildUIScript(ctx):
    RecipeUIScript = ctx.UI.Binding.RecipeUIScript
    RecipeBinder = ctx.UI.Binding.RecipeBinder
    render_slot = ctx.UI.Slots.render_slot

    class GrinderUIScript(RecipeUIScript):
        def InitControls(self):
            self.InputControl = self.RecipeControl.GetChildByPath("/wrapper/content/input/0")
            self.OutputControl = self.RecipeControl.GetChildByPath("/wrapper/content/output/0")

        @RecipeBinder.Group(["mei_ui.recipe.input"])
        def InputPanelCallback(self, index):
            return render_slot(self.InputControl, self.Recipe.GetInputs()[0])

        @RecipeBinder.Group(["mei_ui.recipe.output"])
        def OutputPanelCallback(self, index):
            return render_slot(self.OutputControl, self.Recipe.GetPrimaryOutput())

    return GrinderUIScript
```

- 格子的 JSON 写 `"0@mei_common.item_panel": { "$binding_name_prefix": "mei_ui.recipe.input" }`，脚本里 `RecipeBinder.Group` 列同样的前缀。
- ⚠ `RecipeBinder.Group(prefix_list)` 的表**不能是空的**（空表在绑定那一刻抛错，后面的规则都不绑，整页断掉）：按数据动态造脚本类时，哪一组没有格子就别声明那一组。
- 只往 `/wrapper/content` 底下取控件：tooltip 预览里没有行，`/wrapper/buttons` 之类取不到（给 None，自己兜住）。

<a id="slots"></a>
## 3. 槽位：`render_slot` 与 `resolve_input_slot`（[api §6.2](api.md#ui-slots)）

- `render_slot(control, ingredient)`：0 个候选画空格、1 个画物品、多个画**轮播**；返回面板（都有 `SetLore`）。**回调不能返回 None**，空格返回 `render_slot(control, None)`。
- `resolve_input_slot(recipe, index, columns)`：界面网格的第几格对应配方的哪一格 —— 有序配方按**真实宽度**摆（2×2 的配方在 3 列网格里落在 0 / 1 / 3 / 4），无序的摊平按顺序。
- 几格画同一样东西（原版酿造台下面三瓶）：JSON 里写同一个绑定名前缀，画出第一格后对另外几格 `panel.AddMirror(control)`（探测）。

<a id="anim"></a>
## 4. 动画：覆写 `OnAnimTick`

```python
class MyUIScript(RecipeUIScript):
    def OnAnimTick(self, ticks):
        if ticks % 15:            # 节拍 0.2 秒一次，15 拍 = 3 秒
            return
        self.ArrowControl.StopAnimation()
        self.ArrowControl.PlayAnimation()
```

- 整页共用一个节拍（0.2 秒），**第一拍是 0、就在 `OnCreate` 之后立刻送到** —— 把第 0 拍当成初始外观来写，不用在 `OnCreate` 里另画一次。
- 不覆写就不会被调；**别在 `OnCreate` 里自己 `AddRepeatedTimer`**（每行一个 timer）。抛异常只记一行 `[MEI/ui]`。
- 裁剪的图：Python 每帧推就写 `clip_direction`、不写 `clip_ratio`；JSON 动画就写 `clip_ratio: "@ns.anim"`；写了字面的 `clip_ratio` 比例就钉死了。

<a id="lore"></a>
## 5. 给一格加说明：`SetLore`

「这条配方对这一格的额外要求」挂在那一格的悬停文字上，别另摆 label：

```python
@RecipeBinder.Group(["mei_ui.recipe.tool.wrench"])
def WrenchPanelCallback(self, index):
    return render_slot(self.WrenchControl, tool_ingredient).SetLore("§7需要 扳手等级: §f铁")
```

`SetLore(None)` 清空、`AddLore(line)` 追加；换物品（轮播）说明留着。说明属于这条配方，不属于物品 —— 物品是只读的。

<a id="kinds"></a>
## 6. 不是物品的条目（流体……）：`ctx.UI.Slots.Register`

① 给你的 Stack 一个 `KIND`：

```python
class FluidStack(ctx.Types.ItemStack):
    __slots__ = ()
    KIND = "fluid"                     # 身份、序列化沿用基类：加一种 KIND 不会让 Recipe.Id 变
```

② 登记面板：`ctx.UI.Slots.Register("fluid", FluidPanel)`（第三个参数是轮播的面板，不轮播不给）；`OnUnload` 里 `Unregister("fluid")`（探测）。
空格没有 Stack 可问：`render_slot(control, ingredient, kind="fluid")`。

面板**继承 `ctx.UI.Controls.ItemPanel`**，控件**从 `mei_common.slot_base` 组装**（槽位的绑定集是按那套结构写死的，自建的控件回调永远不会被调、零报错）：

```jsonc
"fluid_slot@mei_common.slot_base": {
    "$binding_name_prefix|default": "mei_ui.recipe.input0",
    "controls": [
        { "background@mei_common.slot_background": {} },
        { "item": { "controls": [ { "fluid": {} }, { "renderer": {} }, { "label": {} } ] } },
        { "overlay@mei_common.slot_overlay": {} }
    ]
}
```

路径别改名（`/item/renderer`、`/item/label`、`/overlay/btn_overlay`）；别写成 `@mei_common.item_panel` 再写 `controls`（派生控件写 `controls` 是替换，会把绑定一起抹掉）。
**能量、经验不做成 KIND**：没有身份（不在物品表里、点了查不出用途），在界面上放个 label 就行。

<a id="multi"></a>
## 7. 多候选格、tooltip、触屏菜单

- 多候选格（`MultiItemPanel`）在 PC 上悬停出「接受物品」tooltip，标题是当前候选完整的悬停文字（含你加的说明）；触屏上点格子出二级菜单。**你什么都不用做**。
- 选候选：`Select(i)` / `Next()` / `Prev()`（手动选过就停轮播）、`ResumeRotate()`、`AddListener(fn)`（[api §6.1](api.md#ui-controls)）。
  覆写 `Rotate` 的子类记得调回基类。
- 自己的面板想出 MEI tooltip、改触屏菜单的动作：钩子（`HasMeiTooltip` / `TooltipContent` / `MenuActions` / `ContentKey` / `MenuKind`）**暂不作为 API 承诺**，要用先提 issue。
- 触屏上格子不出原版悬停文字：覆写 `HoverText` 的面板开头照写 `if self.MeiTooltipHidesName(): return ""`。

<a id="buttons"></a>
## 8. 配方行右边的动作按钮条

```json
{ "buttons@mei_recipe_common.buttons_panel_vertical": { "$plus_button_ignored": false } }
```

竖排（挂在内容右边，`buttons_panel_vertical`）与横排（行很矮时挂在下面，`buttons_panel_horizontal`）是两个控件。每颗按钮一个开关：
`$tree_button_ignored`（配方树，缺省 `false` 的类型才有）/ `$top_button_ignored`（置顶）/ `$star_button_ignored`（收藏）/ `$plus_button_ignored`（快捷转移，**缺省关**）。
转移按钮要两件事都做（[02 §8](02-recipes.md#transfer)）。**你自己加的按钮没做完就两层都关**：Python 不注册、JSON 里也 `"ignored": true` ——
只关 Python 那层，控件照样建出来、绑定每帧照拉，`stack_panel` 里还空出一格。

<a id="hosted"></a>
## 9. 托管配方页：内容区整块交给你画（[api §5](api.md#types)）

配方页本来就是你自己的 JSON 控件、自己的脚本（比如转接别的配方浏览器的接口），MEI 不认识里面的格子，又不想照 §1 ~ §8 改写的，
在类型上登记一个托管者：`RecipeCategory(…, page_host=host)`，`host` 继承 `ctx.Types.RecipePageHost`（或者写一个有同样方法的类）。
MEI 照旧管配方页的框 —— 顶栏（返回、类型名、页码与翻页、关闭）、类型页签、左边的工作站一列、滚轮翻页、导航；内容区里建一个容器交给你：

| 方法 / 属性 | 什么时候调 | 你做什么 |
|---|---|---|
| `CONTAINER` | 换到这个类型时 | 容器的 JSON 定义，缺省 `"mei_recipe_common.hosted_page"`：竖排的 `stack_panel`，宽取里面最宽的控件、高是它们加起来，摆在顶栏下面、水平居中 |
| `PageSize(category, recipes, height)` | 每次分页（开页、换类型、改界面尺寸）| 一页放几条；`height` 是内容区能用的高。少于 1 按 1 |
| `Show(page)` | 画这一页 | 在 `page.Container` 里建你的控件、画这一页的配方 |
| `Hide(page)` | 翻页、换类型、刷新、关配方页之前 | 收回这一页（拆你的脚本）。同一个类型翻页时容器不换（`page.Serial` 一样），控件可以留着给下一页接着用；换了类型、刷新、关页时容器连同里面的控件一起删 |
| `Tick(page, ticks)` | 配方页的节拍（0.2 秒一拍），`ticks` 从这一页显示起算 | 轮播、动画；不要就不写 |
| `RecipeAt(page, x, y)` | 快捷键「收藏这条配方」问屏幕上这一点是哪条配方 | 给那条 `Recipe`；不知道给 None（缺省）|

`page`（HostedPage）：`Container` / `ContainerPath`（MEI 建的容器）、`Recipes`（这一页的配方）、`Start`（第一条是第几条）、`Total`、`Height`、
`Serial`（容器的代号）、`ScreenNode`、`ScreenName`（配方页挂在哪个界面上，比如 `"crafting.crafting_screen"`）、`Live`（收回以后为假）；
`CreateControl(定义, 名字, parent=None)` / `RemoveControl(control)` 在容器里建、删控件（经 MEI 的主节点，控件缓存跟着作废，**不要自己 `CreateChildControl`**），
`Notice(text)` 在顶栏挂一句话几秒，`Close()` 关掉配方页（排到下一拍）。收回以后这几个方法什么都不做。

几条约束：

- 容器里的控件**宽不要写父控件的百分比**：容器和配方页的宽都跟着它们，写了就绕成圈，引擎排不出来、断言后崩溃（MEI 引擎结论 §56）。高同理。
- 刚建的容器量不到配方页的高：MEI 等下一帧（排好了）才分页、调 `Show`，你不用自己等。
- 托管类型**没有 MEI 的配方行**：行上的收藏、置顶、+、配方树按钮都没有（要转移就在你自己的控件里放按钮、自己接）；
  tooltip 不出配方预览（`preview_def` 缺省就是空）；**配方树不用这个类型的配方**（MEI 不知道它的原料）。
  格子要照 MEI 的交互（工具 / 作弊模式、触屏菜单、左右键查来源 / 用途），点了交给 `ctx.UI.Actions.ClickItem`；光标下的格子要让快捷键认得，登记焦点提供器（`ctx.UI.Focus`，[05 §4.1](05-screens-and-tools.md#focus)）。
- `Show` / `Hide` / `Tick` 抛了 MEI 只记一行（`[MEI/ui] 托管配方页 … 画不出来`），配方页照常，那一页是空的。

下一篇：[04 · 物品](04-items.md)。
