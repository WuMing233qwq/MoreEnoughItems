# 05 · 界面与工具

> 上一篇：[04 · 物品](04-items.md)。接口签名：[api.md](api.md)。

<a id="screens"></a>
## 1. 让你的界面挂上 MEI：`ctx.UI.Screens`（[api §6.4](api.md#ui-screens)）

原版的工作台、熔炉、箱子……开着时旁边出物品栏、收藏栏，是原版扩展装配时登记的；你的界面用同一个门面（探测）：

```python
def OnRegister(self, ctx):
    screens = getattr(ctx.UI, "Screens", None)
    if screens is None:
        return
    if screens.Register("YourMachineUI.main", {"ContentPaths": ["/root_panel"]}):
        self.Screens.append("YourMachineUI.main")

def OnUnload(self, ctx):
    for screen_def in self.Screens:
        ctx.UI.Screens.Unregister(screen_def)
    self.Screens = []
```

**每次进世界都要登记**（SDK 退出存档时把代理表清了）。挂的是 SDK 的界面代理：方块容器（`netease:block_container`）的界面、
你用 `RegisterUI` + `PushScreen` 开的自己的界面都一样（SDK 压栈时按全名取界面节点）。参数（全都可以不写）：

- **`ContentPaths`** —— 要被 MEI 避让的几块（相对 `RootPath`，缺省是界面的 `$screen_content` 那一层），第一项是主内容；`[]` 是不避让、物品栏铺满。
- **`Conditions`** —— `{路径: condition(get) -> bool}`：这一块**看得见还不够**、要条件成立才避让。藏起来以后会挪到别处、却还看得见的控件用它（原版配方书上方的页签就是：配方书开着才算）：
  ```python
  def BookShown(get):                       # get(路径) 按 RootPath 取同一个界面里的控件，取不到给 None
      book = get("/content_stack_panel/recipe_book")
      return book is not None and book.GetVisible()
  params = {"ContentPaths": [...], "Conditions": {"/content_stack_panel/recipe_book/tab_navigation_panel": BookShown}}
  ```
  条件抛异常当「不避让」；同一个条件函数一轮只算一次。
- `VisibleControlPath` / `AllowChangeVisible` —— 配方页开着时藏起来哪一块（缺省主内容）、能不能藏；`RootPath` —— MEI 的覆盖层建在哪（原版界面都是 `…/root_screen_panel`）。

> 触屏的查找状态（点查询按钮再点一格）、`ctx.UI.Actions.ItemAt` 要认得出你界面上的物品格：物品渲染器的控件名要带 `item` 或者就叫 `renderer`。

<a id="drops"></a>
## 2. 工具模式的放置目标：`ctx.UI.Drops`（[api §6.5](api.md#ui-drops)）

MEI 的收藏栏左上角有个模式按钮：普通 / 工具（黄）/ 作弊（红）。**工具模式**下玩家点 MEI 的一格就把那样物品拿起来，
再点一下别处 —— 点到你登记的控件上，MEI 回调你。这是从 MEI 的物品到你的界面的跨模组通讯（设机器的过滤器、填你的配方编辑器……）。探测：

```python
def OnRegister(self, ctx):
    drops = getattr(ctx.UI, "Drops", None)
    if drops is None:
        return
    base = "/variables_button_mappings_and_controls/safezone_screen_matrix/inner_matrix/safezone_screen_panel/root_screen_panel"
    drops.Register("YourMachineUI.main", base + "/main/filter_slot", self.OnDropFilter, alias="filter")
    drops.Register("YourMachineUI.main", base + "/main/grid", self.OnDropGrid, alias="grid", point=True)
    drops.Register("YourMachineUI.main", base + "/main/blocks", self.OnDropBlock, alias="blocks",
                   accepts=lambda stack: IsBlock(stack))     # 2026-10-30 起：不收的东西当这个目标不在

def OnDropFilter(self, name, stack):            # name 是别名（没给就是路径）；stack 是 ItemStack，数量 1
    SetFilter(stack.Item.ItemId, stack.Item.AuxValue)

def OnDropGrid(self, name, stack, pos):         # point=True：多给点下去那一点的全局坐标，自己算点中第几格
    cell = CellAt(pos)                          # 按每一格控件自己的矩形认，别按网格均分（格子之间有缝）
    if cell is None:
        return False                            # 不收：玩家手里的东西不放下
    ...

def OnDropBlock(self, name, stack):
    if stack.Item.ItemId in self.Blocks:
        return "已经在列表里了"                   # 一句话也是不收：MEI 用引擎的 tip 消息提示玩家
    ...
```

- 命中：控件看得见、点在它的全局矩形里；几个都中取面积最小的。路径从**界面最根上**算（`ScreenNode.GetBaseUIControl` 用的那种）。
- **回调的返回值**（2026-10-30 起）：None / 真是收下了，玩家手里的东西放下；**False 是不收、一句话是不收并说为什么** ——
  手里的东西不放下（玩家可以换个地方再点），那句话用引擎的 tip 消息提示（物品栏上方；开着容器界面时看不看得见还没实机确认）。
  老写法没有返回值（None）照旧当收下了。抛异常当不收、只记一行。
- **`accepts(ItemStack) -> bool`**（可选）：不收的东西点上去当这个目标不在，套在外面的目标照样能接。只想说「不收」就在回调里返回原因，比 accepts 好用 —— accepts 筛掉的什么都不提示。
- **只给 ItemStack**：收藏的配方、配方树给的是它们显示的那样物品；流体这类别的条目拿不起来。
- 回调在 MEI 每帧的处理里调。`Held()` 是当前拿着的东西 —— 想在玩家拿着时亮出放置区，就在你界面的每帧里问它。
- 你的界面要先能挂上 MEI（§1）：拿起与捕获点击的那一层在 MEI 的覆盖层里。卸载时 MEI 兜底撤掉记在你名下的放置目标。
- 一个目标盖住一片会滚动的列表时（过滤列表），在回调里按每一行控件的全局矩形认点中的是哪一行（滚动了也对），别按行高推。

<a id="transfers"></a>
## 3. 配方页的 + 交给你的界面：`ctx.UI.Transfers`（[api §6.7](api.md#ui-transfers)）

你的界面开着时，玩家在配方页上点某条配方的 +，MEI 不自己搬，而是交给你登记的**转移处理器** —— 照 NEI / JEI 的 recipe transfer handler：

- MEI 算好**清单**（`TransferRequest`）：每一格要什么、要几个、背包里凑得出几个、挑了哪一样（背包里有的候选优先；几格要同一样东西时按全局配额分），催化剂（工具）另算；
- 你的 `Check(request)` 说这一条能不能做：+ 亮不亮、悬停写什么（PC 悬停、触屏按住都出）；
- 玩家点了，你的 `Transfer(request)` 去做 —— 往你自己的机器里放材料就**发你自己的请求、由你自己的服务端照你的规矩搬**（只有你知道玩家开着哪台机器、哪几格是输入、搬完要不要同步）；
  样板、编码器、过滤器这类只记配方的，把清单写进界面就行。

```python
class PatternHandler(object):          # 也可以继承 ctx.Types.TransferHandler（拿到下面三个类属性的缺省值和缺省的 Check）
    GRID = (3, 3)                       # 配方按 3×3 摊：有序配方照形状摆、无序一格一个（和配方页、原版工作台同一个摊法）；不写按配方输入的顺序
    CONSUMES = False                    # 只记配方、不拿东西：材料够不够都能点（真：缺省的检查材料不够就灰掉）
    HINT = "§7把这条配方写进样板"          # + 能点时的悬停文字
    SCREEN_HINT = "§7打开样板后可用"        # 可选：玩家不在你的界面时 + 灰着，悬停写它

    def Check(self, request):           # 可选。None 是能点；一句话 / TransferError 说为什么不行
        return None if request.Recipe.GetShape() != (4, 4) else "§7样板只有 3×3"

    def Transfer(self, request):        # 成了返回 True（MEI 关掉配方页回到你的界面）；没成返回 False 或一句话（写在配方页顶上）
        cells = [request.Cell(i) for i in range(9)]           # 每格一个 TransferSlot 或 None（空格）
        WriteCells([(c.Stack.Item.ItemId, c.Stack.Item.AuxValue) if c else None for c in cells])
        return True


def OnRegister(self, ctx):
    transfers = getattr(ctx.UI, "Transfers", None)        # 2026-10-30 起
    if transfers is None:
        return
    self.Token = transfers.Register("YourPatternUI.main", PatternHandler(), categories=["crafting_table"])
```

要搬材料的机器（`CONSUMES = True`）一般这样检查：材料不够也让点、照样放有的那些，就回一个**只是提醒**的错误：

```python
    def Check(self, request):
        if not request.Complete():
            return ctx.Types.TransferError(message="§7材料不够的格子会空着", missing=request.Missing(), blocking=False)
        return None

    def Transfer(self, request):
        x, y, z = self.OpenMachinePos()                          # 你自己记着的、玩家开着的那台
        YourTransferRequest(x, y, z, RecipeKeyOf(request.Recipe), request.MaxTimes() if request.Max else 1).send()
        return True
```

- **清单**（`TransferRequest`）：`Recipe` / `CategoryId` / `ScreenDef`；`Slots`（输入格：给了 GRID 是格子的下标、空格不在里面，没给是配方输入的下标）、
  `Catalysts`（催化剂）；每格（`TransferSlot`）`Index` / `Ingredient` / `Need`（要几个）/ `Have`（背包里凑得出几个）/ `Missing`（还缺几个）/ `Stack`（挑中的那一样，数量是 Need）/ `Catalyst`。
  `Cell(i)` 取第 i 格，`Missing()` 缺东西的格子，`Complete()` 一份够不够，`Times` 份数（1），`Max` 玩家要「尽量多」（现在的 + 一律是），`MaxTimes()` 背包最多够几份（问的时候才算）。
  **一格只用一种候选**（几种加起来不算 —— 一格只放得下一种东西）：凑不齐的格子 `Have` 是剩得最多的那一种有几个，`MaxTimes()` 也这么算。
  `Fits`：配方摊不摊得进你的 `GRID`（没写 GRID 恒为真）—— 摊不进的 MEI 直接灰掉、悬停写「放不进当前的合成格」，不问你的 Check（2026-10-30 起，探测）。
- **检查的返回值**：None / 真是能点；False、一句话、`TransferError(message, missing, blocking=True)` 是灰掉（悬停写原因和缺的东西）；
  `blocking=False` 是能点、悬停把原因和缺的写出来。不写 Check：`CONSUMES` 真的材料不够就灰掉，假的一律能点。结论 MEI 按 `Recipe.Id` 缓存，翻页、换类型、转移成了以后重问。
  `HINT`、那句话写 py2 源文件里的字面量（utf-8 字节串）也行，MEI 收成 unicode 再拼。
- **玩家不在你的界面时**：你登记的那几类配方，+ 照样出、**灰着**（悬停写 `SCREEN_HINT`，没写是「当前界面不能转移这一类配方」）——
  玩家看得到这条配方能转移，只是要先打开你的界面。没有任何界面收、类型也没有转移策略的，+ 才不出（2026-10-30 起；原来不在你的界面时整个藏起来）。
- **`ctx.UI.Transfers.Request(recipe, grid=None)`**：不经过 + 也能拿到同一种清单（按背包现在有的东西算）—— 比如拿着一样物品点到你的「产物格」、要照它的配方写满格子。
- **老写法照样认**：第二个参数给一个函数 `callback(Recipe)`（写成了返回 True），当作不拿东西、按配方输入顺序的处理器；`accepts(Recipe) -> bool` 两种写法都能再筛一道。
  想兼顾老版本 MEI，处理器对象自己写个 `__call__(recipe)`：新 MEI 认 `Transfer`，老 MEI 当它是回调。
- 你的界面要先能挂上 MEI（§1），配方页开在 MEI 的覆盖层里；`screen_def` 写同一个界面名。
- `categories` 不给是全部类型；同一个界面、同一个类型登记了几个，后登记的优先，也比类型上的转移策略（`SetTransferPolicy`，MEI 自己往玩家侧的合成格里放）优先。
- + 只出现在配方行打开了它的类型上（原版工作台打开了；你自己的配方页要 + 就在行上写 `$plus_button_ignored: false`，[03 §8](03-recipe-page.md#buttons)）。
- 处理器、`accepts` 抛异常只记一行：检查抛了当不收，Transfer 抛了当没写成。卸载时 MEI 兜底撤掉记在你名下的（`UnregisterAll` 也行）。

<a id="actions"></a>
## 4. 在 MEI 里做事：`ctx.UI.Actions`（[api §6.6](api.md#ui-actions)）

你的界面上想放个「查配方」按钮、或者知道光标下是什么物品：

```python
actions = getattr(ctx.UI, "Actions", None)        # 探测（2026-10-30 起）
if actions is not None:
    actions.ShowRecipes(item)                     # 开配方页：怎么做（可以先翻到某个类型：category="yourmod:grinder"）
    actions.ShowUses(item)                        # 用在哪
    actions.OpenTree(item, 4)                     # 配方树：要 4 个
    item = actions.ItemUnderCursor()              # PC 光标下是哪样物品（MEI、原版、别的模组的物品格都认）
    if actions.Mode() == ctx.Const.ModeConst.Cheat:
        ...
```

作用在当前挂着 MEI 的界面上，没有就给 False / None；**别在绑定回调里调**（会重排格子），挪到下一帧。收藏：`IsBookmarked(item)` / `SetBookmarked(item, on)`。

<a id="modes"></a>
## 5. 三种模式与作弊

- **模式**全局一份、关界面不复位；`ctx.UI.Actions.Mode()` 读。作弊模式要操作员权限：每次开界面问一次服务端，给物品时服务端再查一次（只认引擎给的发起者）。
- 作弊给物品走 MEI 自己的请求，你的模组不用做什么；工具模式见 §2。设计在 `docs/architecture/modes.md`。

<a id="example"></a>
## 6. 实例：蔚蓝科技

蔚蓝的几台机器、几个「选一样物品」的界面都只在蔚蓝的 MEI 扩展里接上，**没改蔚蓝自己的代码、没打补丁**，用的都是蔚蓝现成的界面实例与请求：

**机件加工台**（配方转移，`workstation.py`）：登记 `MachineryWorkstationUI.main` 的转移处理器（加工台那一类，`CONSUMES` 真）。
点 + 发加工台自己的请求（坐标 + 产物 id，和点加工台右边的配方栏同一个），由蔚蓝的服务端把背包里的材料、够用的扳手和钳放进去；
产物被禁用、背包里一样材料都没有的灰掉，材料不够照样能点（蔚蓝放有的那些），悬停写缺什么。

**合成样板**（`skybluetech:crafting_template`，蔚蓝用 `RegisterUI` + `PushScreen` 开的设置界面，`crafting_template.py`）：

1. 界面登记：`ctx.UI.Screens.Register("CraftingTemplateSettingsUI.main", {"ContentPaths": ["/panel"]})`；
2. 配方转移：处理器 `GRID = (3, 3)`、`CONSUMES = False` —— 配方页上工作台配方的 + 把 MEI 摊好的 9 格写进样板（标签原料是背包里有的那一样）；
3. 两个放置目标：3×3 网格（`point=True`，按每一格自己的矩形认点中第几格，点在缝上不收）、
   产物格（这样物品只有一条工作台配方就照它写满，几条就开它的配方页让玩家挑 +，没有就不收、说为什么）；
4. 都发蔚蓝自己的上传请求（服务端照旧认配方、回产物）。

**另外四个**（放置目标，`selectors.py`；不收的回原因，玩家手里的东西不放下）：

| 界面 | 点到哪 | 做什么 |
|---|---|---|
| 电动机件加工台 | 机器面板任何地方 | 选产物是这样物品的那条加工台配方（和点右侧配方栏一样）|
| 冷冻机 | 机器面板任何地方 | 切到产物是这样物品的那一档 |
| 物品分流器 | 设置列表的某一行 | 那一行的物品换成它 |
| 连锁挖矿设置 | 方块列表 | 是方块就加进列表（这个界面由这里登记挂 MEI）|

代码在蔚蓝仓 `skybluetech_scripts/skybluetech/external/mei/` 的 `workstation.py`、`crafting_template.py`、`selectors.py`（三处共用的取界面 / 认格子的小工具在 `ui_access.py`）。
