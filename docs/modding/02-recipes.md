# 02 · 注册配方

> 上一篇：[01 · 从 0 开始](01-getting-started.md)。接口签名：[api.md](api.md)。

## 1. 一个配方类型是三样东西

| 样 | 类 | 回答什么 |
|---|---|---|
| **类型** | `ctx.Types.RecipeCategory` | 标识、名字、图标、用哪个 JSON 控件画、工作站 |
| **来源** | `ctx.Types.RecipeSource`（或现成的 `StaticRecipeSource`）| 「有哪些配方」：按产物查、按原料查、给全表 |
| **配方页脚本** | `ctx.UI.Binding.RecipeUIScript` 的子类 | 把一条配方画进那个控件（[03 篇](03-recipe-page.md)）|

```python
def OnRegister(self, ctx):
    category = ctx.Types.RecipeCategory(
        category_id="yourmod:grinder",                 # 全局唯一，带命名空间
        name_key="yourmod.mei.category.grinder",       # 本地化键，别写死中文
        icon=("yourmod:grinder", 0),
        control_def="YourModMei.RECIPES_GRID",          # 你资源包里的配方页控件
        stations=ctx.Registry.ItemFactory.GetStacksFromIds(["yourmod:grinder"]),
    )
    source = ctx.Types.StaticRecipeSource(category.Id)
    source.AddAll(BuildMyRecipes(ctx))                 # 你的配方表 -> [Recipe]

    ctx.Registry.SourceRegistry.RegisterCategory(category)   # 先注册类型
    ctx.Registry.SourceRegistry.RegisterSource(source)       # 来源挂在类型下
    ctx.Registry.RecipeUIManager.RegisterScript(category.Id, GrinderUIScript)
    self.Registered.append(category.Id)

def OnUnload(self, ctx):
    for category_id in self.Registered:
        ctx.Registry.RecipeUIManager.UnRegisterScript(category_id)
        ctx.Registry.SourceRegistry.UnRegisterCategory(category_id)
    self.Registered = []
```

<a id="category"></a>
## 2. 类型 `RecipeCategory`（[api §4.1](api.md#source-registry)）

`RecipeCategory(category_id, name_key="", icon=None, control_def="", stations=None, sort_index=0, preview_def=自动)`

- `category_id`：带命名空间。**不能覆盖别人的**：同一个 Id 注册第二次返回 False、记警告（原版的 `crafting_table` / `furnace` / `fuel` 也一样）。
- `icon`：`(物品 id, aux)`，类型页签上画它。`sort_index`：类型页签的先后，小的在前（原版 0 ~ 20）。
- `control_def`：配方页的控件定义（`"命名空间.RECIPES_GRID"`）；tooltip 里的配方预览缺省按它推出 `"命名空间.PREVIEW"`，不要预览写 `preview_def=None`（[03 §1](03-recipe-page.md#json)）。
- `stations`：工作站，**只收 `ItemStack`**；它们画在配方页顶上，玩家**查工作站的用途**时这个类型排在最前、带上它的全部配方。

<a id="source"></a>
## 3. 来源（[api §5](api.md#types)）

- **一次给全**：`StaticRecipeSource(category_id)`，`Add(recipe)` / `AddAll(recipes)` / `Remove(recipe_id)` / `Clear()`；按产物、按原料（含催化剂）的索引它自己建。
- **按需查**（配方表在引擎里、或太大）：继承 `RecipeSource`，实现 `QueryByOutput(item)` / `QueryByInput(item)`（返回 `[Recipe]`）。
  能给全表的再把 `CAN_ENUMERATE` 置真、实现 `GetAll()`；全表要慢慢凑的（边扫边给）覆写 `IsAllComplete()`，凑齐之前给 False ——
  配方页的页码后面写「扫描中」，凑齐后自动刷新一次。只实现了 `QueryBy*` 的来源，工作站的用途里只出真用到它的那几条。
- `RegisterSource` 只认**已注册的**类型：顺序反了返回 False（记警告）。

<a id="recipe"></a>
## 4. 配方对象（[api §5](api.md#types)）

`Recipe(recipe_type, inputs, outputs, catalysts=None, data=None, recipe_id=None)`：

- `inputs` / `outputs` / `catalysts` 是 `[Ingredient]`；一格的候选用 `Ingredient(stacks, amount=1, tag_id=None, chance=1.0)`，单个物品 `Ingredient.of(stack, amount)`。
- `data` 放展示用的数值（耗电、耗时）—— **不进 `Recipe.Id`**。
- 要网格语义（有序配方）就继承 `Recipe`，覆写 `GetShape()`（给 `(宽, 高)`）与 `_extra_to_canonical()`；并 `register_recipe_class` 登记以便序列化。
  ⚠ `_extra_to_canonical()` 写错会毁掉 `Recipe.Id` 的稳定性，照着原版的写。
  ⚠ 配方对象的存盘 / 读回（`ToDict` / `FromDict`）MEI 自己没用（收藏、置顶只存 `Recipe.Id`），读回的物品没有物品信息、也不带 userData —— 别拿它存配方。
- 物品的 userData 不进 `Recipe.Id`、也不进按物品查配方的索引：两条配方只差在原料是哪一本附魔书，Id 一样（后登记的那条被当成重复）。

### 4.1 `Recipe.Id` 要稳定

收藏、置顶存的就是 `Recipe.Id`（配方内容的稳定哈希）。它变了，玩家的收藏与置顶就找不回来。所以：

- **tag 原料别展开**：引擎把 tag 展开成物品列表给你的，折回 tag（`Ingredient(..., tag_id="minecraft:planks")`）—— 模组往 tag 里加物品，Id 不变。
- **驱动机器的东西不进配方**：燃料、能量（RF / EU）、流体动力这类**每条配方都一样、任选其一就能开机**的东西，不放 `inputs`、也不放 `catalysts`。
  它们不是这条配方的内容，放进去还会让 Id 跟着它们变（装卸一个带燃料的模组，所有配方都变 Id）。界面上要画就在配方页脚本里自己取（MEI 的熔炉：燃料格问熔炉扩展的燃料表）。

<a id="catalysts"></a>
## 5. 不消耗的东西放 `catalysts`

工具、模具、刻印模版这类**做配方时不扣**的放 `catalysts=[...]`，别为了对槽位塞进 `inputs`：

- MEI 把 `inputs` 当成消耗品 —— 收藏栏展开配方时原料乘倍数，塞进去的工具会跟着乘；
- 催化剂照样查得到用途（`StaticRecipeSource` 把它一并索引进「按原料查」）；界面上从 `recipe.GetCatalysts()` 取来画；
- 收藏栏展开时 `GetShownCatalysts()` 给的排在行尾、数量固定 1。缺省是全部催化剂；「任选一种」的一大类在子类里覆写成 `[]`。

<a id="stations"></a>
## 6. 往别人的类型里加东西

```python
def OnReady(self, ctx):                          # 原版的类型在 OnRegister 才注册，跨扩展的放 OnReady
    category = ctx.Registry.SourceRegistry.GetCategory("crafting_table")
    if category is not None:
        category.AddStation(my_machine_stack, owner=self.ID)    # 你的机器也能开工作台配方

def OnUnload(self, ctx):
    category = ctx.Registry.SourceRegistry.GetCategory("crafting_table")
    if category is not None:
        category.RemoveStationsByOwner(self.ID)                 # 只撤你自己的
```

- `owner` 填自己的扩展 ID：`RemoveStationsByOwner` 只撤这个 owner 的；空 owner 是类型自带的，撤不动。
- 要特定 aux 的工作站：`ctx.Registry.ItemFactory.GetItem(ItemId=..., AuxValue=...).stack()`（id 不在物品表里抛 `ValueError`，自己兜一层）。
- 往别人的类型里加**配方**：对已存在的类型 `RegisterSource` 一个你的来源。
- `Stations` 是只读的产物，对返回的表 append 不进去；要整体换用 `SetStations(stacks, owner=self.ID)`。

<a id="query"></a>
## 7. 查配方（[api §4.3](api.md#recipe-manager)）

```python
manager = ctx.Registry.RecipeManager
by_type = manager.QueryRecipe(item, "output")                      # 怎么做：OrderedDict{类型: [Recipe]}
uses = manager.QueryRecipe(item, "input", types=["crafting_table"])  # 用在哪（只看工作台）
recipes, complete = manager.QueryAll("crafting_table")             # 一个类型的全部配方（探测）
name = manager.GetDisplayText("crafting_table")                    # 类型的显示名
```

- 查**工作站的用途**会带上它服务的类型的全部配方（JEI / EMI 的做法）；`QueryRecipeFull` 多给「全表还在凑」的类型（探测）。
- 原版的全表第一次要的时候才分帧扫（不在进世界时扫）；扫完之前 `QueryAll` 给「不完整」，`IsCategoryBuilding` 为真。
- 查询有缓存，但未命中时是同步问引擎 —— 别在每帧、每个绑定回调里查。

<a id="transfer"></a>
## 8. 快捷合成（配方转移）

配方行右边的 + 按钮。**你的机器要支持它，用 `ctx.UI.Transfers` 的转移处理器**（[05 §3](05-screens-and-tools.md#transfers)）：
你的界面开着时，MEI 算好清单（每一格要什么、背包里凑得出多少、挑哪一样）交给你，你说能不能做（+ 亮不亮、悬停写什么），
玩家点了你发自己的请求、由你自己的服务端照你的规矩搬 —— 只有你知道玩家开着哪台机器、哪几格是输入、搬完要不要同步。
你的配方行要出 +，在行上写 `"$plus_button_ignored": false`（[03 §8](03-recipe-page.md#buttons)）。

MEI 自己的快捷合成只管原版工作台、背包 2×2（玩家侧的格子：`SetPlayerUIItem` 只让写玩家开着的那个界面），
物品来源、转移策略、清单这些都是 MEI 内部的，不对外（2026-10-30 起；原来的 `ctx.Registry.TransferRegistry`、`ctx.Types.ItemSource` / `SlotTarget` /
`KIND_*` / `TransferPlan` 等收回了）。设计与安全模型见 `docs/architecture/quick_craft.md`。

下一篇：[03 · 配方页](03-recipe-page.md)。
