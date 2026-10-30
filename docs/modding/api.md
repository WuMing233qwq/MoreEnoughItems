# MEI 接口参考

> 面向**第三方模组作者**：MEI 对外给了哪些东西、每样怎么调。**怎么用**（从 0 接入、注册配方、写配方页……）在同目录的几篇指南里，
> 每条都链回这里；这里也在每条后面写「见 ……」链回指南。当前 `API_VERSION = 2`。
>
> 约定：**纯新增的接口不升 `API_VERSION`**，老版本 MEI 没有它 —— 用 `getattr` 探测（每条写了「探测」的就是这种）。
> 签名里的类型是 py2 的写法；物品、配方等对象的类都从 `ctx.Types` 取。

目录：[组件](#component) · [扩展基类](#extension) · [ctx](#ctx) · [ctx.Registry](#registry) · [ctx.Types](#types) ·
[ctx.UI](#ui) · [ctx.Utils](#utils) · [ctx.Const](#const) · [ctx.Log / Extension / ApiVersion / Scripts](#ctx-misc) · [限制](#limits)

---

<a id="component"></a>
## 1. 组件 `MoreEnoughItems:MeiApi`

`clientApi.CreateComponent(本地玩家 id, "MoreEnoughItems", "MeiApi")` 给的实例（MEI 没装给不出，**判空**）。见 [01 §2](01-getting-started.md#component)。

| 方法 | 返回 | 说明 |
|---|---|---|
| `GetExtensionCls()` | `type` | 扩展基类，继承它写扩展 |
| `RegisterExtension(cls)` | `bool` | 注册扩展**类**（不是实例）；MEI 没装配完就排队，装配完当场装配 |
| `GetApiVersion()` | `int` | 扩展 API 版本，做能力判断用 |
| `GetModVersion()` | `str` | MEI 自身版本，**只给人看** |
| `IsReady()` | `bool` | 装配完了没有（有排队，一般不用管） |
| `ListExtensions()` | `list` | 已装配的扩展 `(id, name, version, author)` |

<a id="extension"></a>
## 2. 扩展基类 `MeiExtension`

```python
class MeiExtension(object):
    ID = ""              # 必须带命名空间前缀，如 "yourmod:machines"
    NAME = ""            # 显示名（本地化键）
    DESCRIPTION = ""
    AUTHOR = ""
    VERSION = "0.0.1"
    MIN_API_VERSION = 1  # 你要求的最低 API 版本

    def OnInit(self, ctx): ...      # 登记别人注册时要用的前提（tag、比较器）
    def OnRegister(self, ctx): ...  # 注册类型、来源、配方页脚本 —— 绝大多数扩展只要这个
    def OnReady(self, ctx): ...     # 全部扩展都注册完：往别人的类型里加东西
    def OnUnload(self, ctx): ...    # 撤掉 OnRegister 注册的（重进世界、热重载）
```

准入（不过就拒、记日志）：`ID` 带 `:`、`MIN_API_VERSION` 不高于当前、`ID` 不重复、传的是子类**本身**。
任一阶段抛异常：记 `[MEI/ext:<你的 id>]`、跳过这一阶段、别的扩展照常。注册与反注册的对照表在 [01 §4](01-getting-started.md#lifecycle)。

<a id="ctx"></a>
## 3. `ctx`

生命周期方法的唯一参数，**每个扩展一份**（四个阶段拿到的是同一个）。不要自己去 import MEI 的任何模块。

| 字段 | 是什么 |
|---|---|
| `ctx.Registry` | 注册表与查询（[§4](#registry)）|
| `ctx.Types` | 物品、配方、快捷合成的类（[§5](#types)）|
| `ctx.UI` | 控件、槽位、绑定、挂 MEI 的界面、放置目标、在 MEI 里做事、按界面登记的配方转移（[§6](#ui)）|
| `ctx.Utils` | 小工具（[§7](#utils)）|
| `ctx.Const` | 常量（[§8](#const)）|
| `ctx.Log` / `ctx.Extension` / `ctx.ApiVersion` / `ctx.Scripts` | 见 [§9](#ctx-misc) |

---

<a id="registry"></a>
## 4. `ctx.Registry`

<a id="source-registry"></a>
### 4.1 `SourceRegistry` —— 配方类型与来源（[02 §2、§3](02-recipes.md#category)）

| 方法 | 说明 |
|---|---|
| `RegisterCategory(category)` → `bool` | 注册一个类型；**Id 重复拒掉**（不能覆盖别人的，原版的也一样），记警告 |
| `UnRegisterCategory(category_id)` | 撤类型，连同它名下的来源 |
| `RegisterSource(source)` → `bool` | 来源挂在**已注册的**类型下；类型不在返回 False（记警告）|
| `UnRegisterSource(source)` | 撤一个来源 |
| `GetCategory(category_id)` → `RecipeCategory or None` | 取类型（往别人的类型里加工作站时用）|
| `ListCategoryIds()` → `list` | 全部类型 Id |
| `GetSources(category_id)` → `list` | 一个类型下的来源 |
| `FindCategoriesByStation(item)` → `list` | 这样物品是哪些类型的工作站（按 id + aux 认）|
| `Revision()` → `int` | 类型、来源每注册 / 撤掉一次加一：自己缓存了查询结果的按它作废（MEI 的查询缓存、收藏找回就是这么做的）。2026-10-30 起，探测 |

<a id="recipe-ui-manager"></a>
### 4.2 `RecipeUIManager` —— 配方页脚本（[03 §2](03-recipe-page.md#script)）

| 方法 | 说明 |
|---|---|
| `RegisterScript(category_id, script_cls, params=None)` → `bool` | 这个类型的配方页用哪个 `RecipeUIScript` 子类；**同一个类型注册第二次拒掉** |
| `UnRegisterScript(category_id)` → `bool` | 撤掉 |
| `GetScriptData(category_id)` → `tuple or None` | 注册的脚本与参数 |

<a id="recipe-manager"></a>
### 4.3 `RecipeManager` —— 查配方（[02 §7](02-recipes.md#query)）

| 方法 | 返回 | 说明 |
|---|---|---|
| `QueryRecipe(item, query_by="output", types=None)` | `OrderedDict{类型 id: [Recipe]}` | 查来源（`"output"`）或用途（`"input"`），按类型的 `sort_index` 再按注册序；`types` 只查这几个类型。**查工作站的用途**带上它服务的类型的全部配方 |
| `QueryRecipeFull(item, query_by="output", types=None)` | `(结果, 还在凑全表的类型集合)` | 同上，多给一个集合：全表还没凑齐的类型（凑齐后再查一次就全了）。探测 |
| `QueryAll(category_id)` | `(配方表, 是否完整)` | **一个类型的全部配方**（各来源 `GetAll()` 的合并）；原版的引擎来源第一次要时才分帧扫，扫完之前给「不完整」。探测 |
| `IsCategoryBuilding(category_id)` | `bool` | 这个类型的全表还在凑没有。探测 |
| `GetDisplayText(category_id)` | `unicode` | 类型的显示名（本地化后的），MEI 自己的界面都用它 |
| `GetAllCraftingTypes()` | `list` | 全部类型 Id（按 sort_index）|
| `GetCategory(category_id)` / `GetCraftingStations(category_id)` | | 类型对象 / 它的工作站 |
| `GetControlDef(category_id)` / `GetPreviewDef(category_id)` | `str or None` | 配方页 / tooltip 预览用的控件定义 |

> 引擎的配方查询很贵：MEI 把引擎的每个回答按物品记下（查过的不问第二次），**但缓存未命中时是同步直查** —— 别在每帧、每个绑定回调里查。

<a id="transfer-registry"></a>
### 4.4 ~~`TransferRegistry`~~ —— 收回了

快捷合成的物品来源登记处 2026-10-30 起是 MEI 内部的，`ctx.Registry` 上没有了。你的机器要支持 +，用 `ctx.UI.Transfers` 的转移处理器（[§6.7](#ui-transfers)）。

<a id="item-manager"></a>
### 4.5 `ItemManager` —— 物品表（[04 §1](04-items.md#immutable)）

| 方法 | 说明 |
|---|---|
| `AddItems(specs)` → `int` | 加物品（aux 变体、引擎不认识的自定义物品）：`[ItemSpec]`；一模一样的再加一遍跳过 |
| `SetHidden(item_id, aux_value=0, hidden=True)` | 从物品栏藏掉 / 显回（旁表，任何时候都能调）；按 `(id, aux)` 藏，同一个键下带 userData 的变体一起藏 |
| `SetPlainHidden(item_id, aux_value=0, hidden=True)` → `bool` | 只藏 / 显回**原件**（`Item.IsPlain` 的那一样：没有 userData、附魔、自定义 ID、耐久），带 userData 的变体照常显示（[04 §1](04-items.md#immutable)）。探测 |
| `IsHidden(item)` → `bool` | |
| `GetBrowsableItems(include_hidden=False)` → `list` | 物品栏里那些（不含藏起来的，按 id 排）；`include_hidden=True` 连藏着的一起（第三十五轮起）|
| `GetItems()` / `GetItemsById(item_id)` / `GetItemById(item_id)` / `GetItemsByName(name)` | 取物品（`Item` 只读）|
| `LookUpItem(item_id)` → `bool` | 物品表里有没有这个 id |
| `ResolveTag(tag)` → `list` | 带这个物品 tag 的物品（物品表的顺序，同一个 id 的变体都在）。tag 由引擎记：3.10 起问引擎的 `LookupItemsByItemTag`（模组在 netease_tags 里注册的、`#` 引用的、几个模组合并的都认，没注册的原版 tag 也能查），之前的版本退回物品信息里的 tags（[§4.10](#tag-lookup)）|
| `Version()` → `int` | 物品表每改一次加一：加物品、藏 / 显、分组 / 标签 / 分类的归属变了（派生的缓存按它自愈）|
| `Touch()` | 旁表变了，撞一次版本号。`ItemOrganizer` 的写入自己会调（2026-10-30 起），一般用不着。探测 |

<a id="item-factory"></a>
### 4.6 `ItemFactory`

| 方法 | 说明 |
|---|---|
| `GetStacksFromIds(item_ids, count=1)` → `[ItemStack]` | 只给 id 的简便写法（aux 0）|
| `GetItem(ItemId=..., AuxValue=...)` → `Item` | 取特定 aux 的物品；id 不在物品表里**抛 `ValueError`** |
| `GetItemStackFromItemDict(item_dict)` → `ItemStack` | 引擎的物品信息字典 → ItemStack |
| `LoadInfo(item_id, aux_value=0, enchanted=False)` → `ItemInfo or None` | 问引擎一个物品的基本信息；引擎不认识这个 id / aux 给 `None`。加物品前拿它核对，问到的交给 `ItemSpec(info=...)` 就不会再问第二次。探测 |

<a id="item-organizer"></a>
### 4.7 `ItemOrganizer` —— 物品分组、类别（[04 §2](04-items.md#organizer)）

`AddGroup(group, name="")`（组已经在了给 False）/ `RemoveGroup(group)` / `SetGroupName` / `AddGroupItem(group, item_id)` / `AddGroupItemFromList` /
`RemoveGroupItem(group, item_id)`（从组里撤一样，组不在、本来没有给 False；往别人的组里加过东西的扩展卸载时用；2026-10-30 起，探测）/
`GetGroupItems` / `GetGroupName` / `GetAllGroups` / `GetGroupOrder(group)`（组里的物品 id，按加进来的顺序；2026-10-30 起，探测）；
`AddCategory(category)` / `RemoveCategory` / `AddCategoryItem`。`Remove*` 是 2026-10-29 加的，探测。
**标签不在这里记了**（2026-10-30 起，原来的 `AddTag` / `RemoveTag` / `AddTagItem` / `AddTagFromList` / `GetTagItems` 删了）：tag 由引擎记 —— 你的物品在 netease_tags 里注册（网易文档「自定义标签」），查的时候用 `ItemManager.ResolveTag` 或 [`TagLookup`](#tag-lookup)。
组名 `name` 写 `.lang` 的键（物品栏分组头的悬停文字取它的本地化文字；不给就写组的 id）。物品栏没选排序时**组里照你加进来的顺序排**，选了排序照排好的先后（2026-10-30 起）。原版物品 2026-10-30 起也分了组（创造栏的物品组 + 锭、粗矿这类同类组），你的组里放原版物品的话，那个物品归你的组（后登记的组为准）。
**并进原版的组**：你的物品和原版是同一类的（锭、矿石、镐、桶……），往原版扩展的组里加 —— 键是创造栏的组 `minecraft:itemGroup.name.<名字>`（`ore`、`pickaxe`、`sword`、`axe`、`shovel`、`hoe`、`helmet`、`chestplate`、`leggings`、`boots`……）与 MEI 补的 `mei:group.<名字>`（`ingot`、`raw_ore`、`nugget`、`raw_ore_block`、`mineral_block`、`bucket`……，全表在 `item_model.md` §10.4）；原版没有、几个模组都可能有的用通用键 `mei:group.dust`（「粉」，组名 `mei.group.dust`，MEI 自己不建，谁先用谁建）。在 OnReady 加（原版的组在原版扩展的 OnRegister 里建），卸载时只撤自己加的（`RemoveGroupItem`），自己建的组撤空了再撤组（[04 §2](04-items.md#organizer)）。物品栏的分组可以被玩家关掉（设置「启用物品分组」，关掉时平铺），组表照旧。增删、成员、改名都撞物品表的版本（物品栏当场重排，2026-10-30 起）；展开 / 收起不撞。

<a id="search"></a>
### 4.8 `ItemSearchIndex` —— 物品搜索（[04 §3](04-items.md#search)）

`Search(query, include_hidden=False)` → `[Item]`，查询串用玩家在搜索栏里用的同一套语法；`include_hidden=True` 藏着的物品也要（第三十五轮起）。

<a id="item-filters"></a>
### 4.9 `ItemFilters` / `ItemFilter` / `ItemSort` —— 物品栏的筛选与排序（[04 §4](04-items.md#filters)）

探测（2026-10-30 起）。

| 方法 | 说明 |
|---|---|
| `AddFilter(filter_id, name, test, order=90, additive=False)` → `bool` | 加一项筛选：`name` 是本地化键（查不到就照写这几个字），`test(item) -> bool`；Id 重复不收。`additive=True` 是**加法**：选了不把表筛小，而是把平时不显示的物品里 `test` 为真的加进来（内置的「隐藏物品」就是，order 1000）；`additive` 参数 2026-10-30 第三十五轮起有 |
| `AddSort(sort_id, name, key, order=90)` → `bool` | 加一种排序：`key(item)` 给可比较的值，没有给 None（排最后）|
| `RegisterFilter(ItemFilter(...))` / `RegisterSort(ItemSort(...))` | 同上的完整写法 |
| `UnregisterFilter(filter_id)` / `UnregisterSort(sort_id)` | 撤（扩展都卸载时 MEI 也会回到只有内置的）|
| `ListFilters()` / `ListSorts()` | 按 order 排好的全部 |
| `Apply(items, filter_ids=(), sort=None)` | 先筛（都要满足）再排；`sort` 是 `(Id, "asc" / "desc")` |

内置的筛选：防具、武器、食物、有耐久、可附魔、已附魔、不可堆叠、模组物品（order 10 ~ 80；原版扩展加「燃料」35）；
排序：名称、ID、攻击力、护甲值、耐久、营养值、最大堆叠、挖掘等级（原版扩展加「燃烧时长」65）。

<a id="tag-lookup"></a>
### 4.10 `TagLookup` —— 按 tag 查物品、方块

探测（2026-10-30 起）。MEI 自己不记 tag：3.10 起问引擎的 `LookupItemsByItemTag` / `LookupBlocksByBlockTag` ——
netease_tags 里注册的 tag（`#` 引用的自动展开，几个模组注册了同一个 tag 自动合并去重），没注册的原版 tag 也能直接查。

| 方法 | 说明 |
|---|---|
| `ItemIds(tag)` → `frozenset` | 带这个物品 tag 的物品 id（str）；引擎没有这个接口（3.10 之前）、给的结果认不出、调用出错时，退回物品表里物品信息的 tags（就是 `GetItemTags` 给的）|
| `BlockNames(tag)` → `frozenset` | 带这个方块 tag 的方块名（str）；3.10 之前给空 |
| `EngineHas(kind="item")` → `bool` | 引擎有没有按 tag 查的接口（`"item"` / `"block"`）|

每个 tag 只问一次引擎，进世界（物品表换了版本）自动作废。要物品实例用 `ItemManager.ResolveTag(tag)`（[§4.5](#item-manager)）。

---

<a id="types"></a>
## 5. `ctx.Types`

| 名字 | 是什么 | 见 |
|---|---|---|
| `Item` / `ItemStack` / `Stack` / `ItemAttr` / `ItemInfo` / `ItemSpec` | 物品（`Item` 只读；`IsPlain` 是不是原件，探测）、一堆物品、条目基类、附加属性、基本信息、加物品的描述 | [04](04-items.md) |
| `Ingredient` / `IngredientLike` | 配方的一格：几个候选（tag 折叠）、数量、概率 | [02 §4](02-recipes.md#recipe) |
| `Recipe` | 配方（`Type` / `Inputs` / `Outputs` / `Catalysts` / `Data` / `Id`）| [02 §4](02-recipes.md#recipe) |
| `RecipeCategory` | 配方类型 | [02 §2](02-recipes.md#category) |
| `RecipeSource` / `StaticRecipeSource` | 来源：按需查 / 一次给全 | [02 §3](02-recipes.md#source) |
| `register_recipe_class` / `get_recipe_class` / `keys` | 配方子类的序列化登记、物品键工具 | [02 §4](02-recipes.md#recipe) |
| `TransferHandler` / `TransferRequest` / `TransferSlot` / `TransferError` | 按界面登记的转移处理器：处理器基类、清单、清单的一格、「做不了 / 有话要说」（2026-10-30 起，探测；清单的 `Fits` 第三十八轮加）| [05 §3](05-screens-and-tools.md#transfers) |

`Recipe` 的读法：`GetInputs()` / `GetOutputs()` / `GetPrimaryOutput()` / `GetByproducts()` / `GetCatalysts()` / `GetShownCatalysts()` / `GetShape()`（有序配方给 `(宽, 高)`，无序给 None）。
`Ingredient`：`get_stacks()`（候选）/ `get_amount()` / `get_chance()` / `get_tag_id()` / `first()` / `accepts(stack)` / `is_empty()`。

---

<a id="ui"></a>
## 6. `ctx.UI`

<a id="ui-controls"></a>
### 6.1 `ctx.UI.Controls`

`ItemPanel` / `MultiItemPanel` / `GroupItemPanel` / `BroderItemPanel` / `ItemsGrid` / `HistoryItemsGrid`。
常用的 `ItemPanel` 成员：`SetLore(lines)` / `AddLore(line)`（[03 §5](03-recipe-page.md#lore)）、`AddMirror(control)`（镜像格，探测）、`Controls()`；
`MultiItemPanel`：`Candidates` / `Current` / `Select(i, manual=True)` / `Next()` / `Prev()` / `AutoRotate` / `ResumeRotate()` / `AddListener(fn)` / `RemoveListener(fn)`（[03 §7](03-recipe-page.md#multi)）。
`ItemsGrid` / `HistoryItemsGrid` / `RecipesGridBind` / `RecipeActionBind` 的绑定经它们身上的 `Bindings`（MEI 自己的 `ScreenBinder`）：`Bind(回调, flag, 绑定名, 集合名=None)` 返回句柄、`Unbind(句柄)` 摘掉；flag 只能普通绑定（按钮、开关）时给了集合名也按普通绑定挂。

<a id="ui-slots"></a>
### 6.2 `ctx.UI.Slots` —— 槽位渲染（[03 §3、§6](03-recipe-page.md#slots)）

| 名字 | 说明 |
|---|---|
| `render_slot(control, slot, kind=None)` → 面板 | 一格：0 候选空格、1 候选、多候选轮播；`kind` 是空格时这一格是什么条目 |
| `resolve_input_slot(recipe, ui_index, columns)` → `Ingredient or None` | 界面网格的第几格 → 配方的哪一格（有序配方按真实宽度摆，无序摊平）|
| `Register(kind, panel_cls, multi_cls=None)` / `Unregister(kind)` | 新的条目种类（流体……）用哪个面板；`Unregister` 探测 |
| `DEFAULT_KIND` | `"item"` |

<a id="ui-binding"></a>
### 6.3 `ctx.UI.Binding` —— 配方页脚本（[03 §2、§8](03-recipe-page.md#script)）

`RecipeUIScript`（配方页脚本的基类）/ `RecipeBinder`（`Group(prefix_list)` 装饰器：哪几个绑定前缀归这个回调；**表不能是空的**）/
`RecipesGridBind` / `RecipeAction` / `RecipeActionBind` / `ActionButton` / `ActionContext`（动作按钮）。

<a id="ui-screens"></a>
### 6.4 `ctx.UI.Screens` —— 让一个界面挂上 MEI（[05 §1](05-screens-and-tools.md#screens)）

探测。`Register(screen_def, params=None)` → `bool` / `Unregister(screen_def)` → `bool` / `IsRegistered(screen_def)` → `bool`。
挂的是 SDK 的界面代理：原版界面、`netease:block_container` 方块的界面、你用 `RegisterUI` + `PushScreen` 开的界面都一样登记（SDK 压栈时按全名取界面节点）。

| 参数（都可以不写）| 不写时 | 意思 |
|---|---|---|
| `ContentPaths` | `["/"]` | 要被 MEI 避让的几块（相对 `RootPath`），第一项是主内容；`[]` 是不避让 |
| `Conditions` | `{}` | `{路径: condition(get) -> bool}`：这一块看得见还不够、要条件成立才避让（藏起来会挪位置的控件）；`get(路径)` 按 `RootPath` 取同一个界面的控件。2026-10-30 加 |
| `MainPath` | `ContentPaths[0]` | 主内容 |
| `VisibleControlPath` | 主内容 | 配方页开着时藏起来的那一块 |
| `AllowChangeVisible` | `True` | 能不能藏它（布尔，或 `{"main_content_control": False}`）|
| `RootPath` | 原版根面板 `…/root_screen_panel` | MEI 的覆盖层建在哪、上面几个路径从哪算 |

<a id="ui-drops"></a>
### 6.5 `ctx.UI.Drops` —— 工具模式的放置目标（[05 §2](05-screens-and-tools.md#drops)）

探测（2026-10-30 起）。

| 方法 | 说明 |
|---|---|
| `Register(screen_def, path, callback, alias=None, point=False, accepts=None)` → 记号 or None | 那个界面（`ANY_SCREEN` / None 是哪个都算）里的那个控件（从界面最根上算的路径）：玩家在工具模式下拿着 MEI 的物品点到它，就回调 `callback(名字, ItemStack)`（名字是 alias，没给就是路径）；`point=True` 时多给第三个参数：点的全局坐标 `(x, y)`；`accepts(ItemStack) -> bool` 不收的东西当这个目标不在 |
| `Unregister(token)` → `bool` | 撤一个 |
| `UnregisterAll()` → `int` | 撤掉记在你名下的全部（扩展卸载时 MEI 也会兜底撤）|
| `Held()` → `ItemStack or None` | 当前界面拿着的东西 |
| `ANY_SCREEN` | `"*"` |

回调的返回值：None / 真是收下了（玩家手里的东西放下）；**False 是不收、一句话是不收并说为什么**（手里的东西不放下，那句话用引擎的 tip 消息提示）；抛异常当不收。

<a id="ui-actions"></a>
### 6.6 `ctx.UI.Actions` —— 在 MEI 里做事（[05 §4](05-screens-and-tools.md#actions)）

探测（2026-10-30 起）。作用在当前挂着 MEI 的界面上；没有就给 False / None。**别在绑定回调里调**。

| 方法 | 说明 |
|---|---|
| `ShowRecipes(item, category=None)` → `bool` | 开这样物品的配方页（怎么做）；`category` 给了就先翻到那个类型 |
| `ShowUses(item, category=None)` → `bool` | 开它的用途（工作站带上它服务的类型的全部配方）|
| `OpenTree(item, count=1)` → `bool` | 开配方树（排到下一拍压栈）|
| `ItemAt(x, y)` → `Item or None` | 屏幕上这一点是哪样物品：MEI 的格子、原版和别的模组界面里的物品格都认 |
| `ItemUnderCursor()` → `Item or None` | PC 光标下的那样 |
| `Mode()` → `str` | 现在的模式：`ctx.Const.ModeConst.Normal / Tool / Cheat` |
| `CheatAllowed()` → `bool or None` | 服务端最近一次答的：有没有作弊模式的权限（操作员）|
| `IsBookmarked(item)` / `SetBookmarked(item, on=True)` → `bool` | 收藏（当前页签）；收了收藏栏当场重排 |

<a id="ui-transfers"></a>
### 6.7 `ctx.UI.Transfers` —— 按界面登记的配方转移（[05 §3](05-screens-and-tools.md#transfers)）

探测（2026-10-30 起）。你的界面开着时，配方页上这些类型的配方点 + 交给你的转移处理器：MEI 算清单，你说能不能做、自己去做（[05 §3](05-screens-and-tools.md#transfers)）。

| 方法 | 说明 |
|---|---|
| `Register(screen_def, handler, categories=None, accepts=None)` → 记号 or None | `screen_def` 是你的界面（要先能挂上 MEI，[§6.4](#ui-screens)）；`handler` 是转移处理器（`ctx.Types.TransferHandler` 的子类，或有 `Transfer` 方法的对象；老写法给函数 `callback(Recipe)` 也认）；`categories` 是收哪些类型（类型 Id 的列表，一个字符串也行，不给是全部）；`accepts(Recipe) -> bool` 再筛一道（不收的 + 灰掉）。登记了的类型，在别的界面里 + 也出、灰着（2026-10-30 起；原来是藏起来）|
| `Request(recipe, grid=None)` → `TransferRequest` | 按背包现在有的东西给一条配方算清单（和 + 交给处理器的同一种）；`grid=(列, 行)` 按格子摊 |
| `Unregister(token)` → `bool` | 撤一个 |
| `UnregisterAll()` → `int` | 撤掉记在你名下的全部（扩展卸载时 MEI 也会兜底撤）|

**处理器**（鸭子类型，类属性不写就是缺省值）：

| 成员 | 说明 |
|---|---|
| `GRID` | `(列, 行)`：配方按格子摊（`resolve_input_slot`）；缺省 None 按配方输入的顺序 |
| `CONSUMES` | 缺省真：要拿背包里的东西（缺省的检查材料不够就灰掉）；假：只记配方 |
| `HINT` | + 能点时的悬停文字 |
| `SCREEN_HINT` | 可选。玩家**不在你的界面**时这一类配方的 + 灰着，悬停写它；不写是「当前界面不能转移这一类配方」（2026-10-30 起，探测）|
| `Check(request)` | 可选。None / 真是能点；False / 一句话 / `TransferError` 说为什么（`blocking=False` 是能点、只把原因和缺的写在悬停里）|
| `Transfer(request)` | 玩家点了 +：成了返回 True（MEI 关掉配方页）；False / 一句话 / `TransferError` 是没成（原因写在配方页顶上几秒）|

- 同一个界面、同一个类型登记了几个，后登记的优先；比类型上的转移策略（`RecipeCategory.SetTransferPolicy`）优先。
- 检查的结论每帧被回读（+ 灰不灰、悬停文字），MEI 按 `Recipe.Id` 缓存、翻页 / 换类型 / 转移成了以后重问；处理器、`accepts` 抛异常只记一行：检查抛了当不收，Transfer 抛了当没写成。
- + 只在配方行的 JSON 打开了它的类型上出现（原版工作台打开了：`$plus_button_ignored: false`，[03 §8](03-recipe-page.md#buttons)）；你自己的配方页要 + 就在行上打开它。

---

<a id="utils"></a>
## 7. `ctx.Utils`

`localize(key)`（`.lang` 的键 → 文字，unicode；查不到给键本身）/ `native_str(text)`（unicode → utf-8 的 str，**递给引擎前必须收成 str**）/
`to_native(value)`（容器里的也一起收）/ `error_text(e)`（except 里拼日志用，绝不抛）/ `dedupe` / `recipe_id` / `stable_text` / `stable_digest`（稳定指纹，处处一样）/
`LRUHistory` / `LRUCache` / `TagParser` / `BudgetQueue`（分帧做事）/ `Page` / `logger`。

<a id="const"></a>
## 8. `ctx.Const`

`NameConst` / `QueryConst`（`Output = "output"`、`Input = "input"`）/ `CollectionConst` / `RecipeDetailsPath` / `ItemsSidebarPath` /
`ItemsBrowserPath`（2026-10-30 加）/ `ModeConst`（`Normal` / `Tool` / `Cheat`，2026-10-30 加）/ `BindingConst` / `PanelProtoConst` / `UiPathConst`。
`TagConst`（只有一个 `Fuels = "mei:fuels"`，旧的燃料 tag，MEI 早就不用了）2026-10-30 删了。

<a id="ctx-misc"></a>
## 9. `ctx.Log` / `ctx.Extension` / `ctx.ApiVersion` / `ctx.Scripts`

- `ctx.Log`：`info` / `warn` / `error`，自动带 `[MEI/ext:<你的 id>]`。
- `ctx.Extension`：你自己；`ctx.ApiVersion`：当前 API 版本。
- `ctx.Scripts`：⚠ **整个 `MEIScripts` 包，逃生舱，不是 API** —— 不承诺任何稳定性，MEI 任何一次内部重构都可能让它失效。非用它不可，说明公共面缺东西，先提 issue（[01 §7](01-getting-started.md#ask)）。

<a id="limits"></a>
## 10. 版本与已知限制

- **三个版本号别混用**：`GetApiVersion()`（扩展 API，只在破坏性变更时加一，用它判断能力）/ `GetModVersion()`（MEI 自己，只给人看）/ `MeiExtension.VERSION`（你的）。
  `MIN_API_VERSION` 写你实际需要的最低值。
- **只有客户端**：MEI 服务端只发物品 id 表、做快捷合成的写入、作弊模式给物品；扩展面没有服务端半边。
- **不能覆盖别人的类型**：同一个类型 Id、同一个类型的配方页脚本注册第二次都拒掉。要往别人的类型里加配方，在 `OnReady` 里对已存在的类型 `RegisterSource`。
- v1 的 `RegisterProcessor` 已移除，没有过渡期。
