# 04 · 物品

> 上一篇：[03 · 配方页](03-recipe-page.md)。接口签名：[api.md](api.md)。

<a id="immutable"></a>
## 1. `Item` 是只读的（[api §4.5](api.md#item-manager)）

物品表里的 `Item` 被配方、收藏、各级缓存到处持有，就地改一个，那些地方全跟着变、还不知情。所以**拿到手的 `Item` 只读**，想改只有两条路：

**旁表**（隐藏、分组这类「事后想改」的，任何时候都能调）：

```python
ctx.Registry.ItemManager.SetHidden("yourmod:debug_block", 0, True)      # 从物品栏藏掉
ctx.Registry.ItemOrganizer.AddGroupItem("yourmod:machines", "yourmod:crusher")
```

**加物品**（aux 变体、引擎不认识的自定义物品）：

```python
ItemSpec = ctx.Types.ItemSpec
ctx.Registry.ItemManager.AddItems([ItemSpec("minecraft:wool", aux_value=i) for i in range(16)])
ctx.Registry.ItemManager.AddItems([ItemSpec("yourmod:ore", info=ctx.Types.ItemInfo(item_name="你的矿石"))])   # 引擎不认识的要自带 Info
```

- 一模一样的再加一遍会跳过：每次进世界、热重载都来一遍也不会多一份。
- **不提供「改某个物品的 aux」**（`ItemId` / `AuxValue` 参与相等、哈希、`Recipe.Id`，改了收藏与置顶会集体错位）：要这个效果就**加目标 aux 的变体、再把原件藏起来**。
- **带 userData 的变体**（附魔书、烟花这种同一个 id、aux 靠 userData 区分的）和原件是同一个键 `(id, aux)`：`SetHidden` 按键藏，会连变体一起藏掉。
  只想藏原件（id 表注册的、不带 userData 的那一样）用 `SetPlainHidden`（探测）：

  ```python
  user_data = {"MyLevel": {"__type__": 3, "__value__": 5}}   # 带类型的写法（NBT 的标签类型 + 值），普通字典引擎多半读不出来
  ctx.Registry.ItemManager.AddItems([ItemSpec("yourmod:core", attr=ctx.Types.ItemAttr(user_data=user_data))])
  hide_plain = getattr(ctx.Registry.ItemManager, "SetPlainHidden", None)
  if hide_plain:
      hide_plain("yourmod:core", 0, True)
  ```

  原版的附魔书、烟花火箭、烟火之星就是这么做的（原版扩展的创造栏表）。
- **不提供删物品**（配方里的 Stack 可能正持有它）：要它消失就 `SetHidden`。
- 取物品：`GetItemsById(id)`、`GetItemById(id)`；只给 id 的 ItemStack：`ctx.Registry.ItemFactory.GetStacksFromIds([...])`；特定 aux：`ItemFactory.GetItem(ItemId=..., AuxValue=...)`。

<a id="organizer"></a>
## 2. 分组、标签、类别（[api §4.7](api.md#item-organizer)）

物品栏里一组物品折成一格（点开展开）。组里的物品照你加进来的顺序排（物品栏没选排序时；2026-10-30 起，`GetGroupOrder` 读得到）；原版物品也分了组（镐、剑、木板……与锭、粗矿这类同类组），你的组里放了原版物品，它就归你的组：

```python
organizer = ctx.Registry.ItemOrganizer
organizer.AddGroup("yourmod:machines", name="yourmod.group.machines")
organizer.AddGroupItemFromList("yourmod:machines", ["yourmod:crusher", "yourmod:grinder"])
# OnUnload：
remove = getattr(organizer, "RemoveGroup", None)     # 探测
if remove is not None:
    remove("yourmod:machines")
```

**同一类的并进原版的组**（锭、粗矿、矿石、镐、桶……，键见 [api §4.7](api.md#item-organizer)）：物品栏里一个「锭」组头，原版的在前、你的接在后面。原版的组在原版扩展的 OnRegister 里建，**你在 OnReady 加**（三个阶段一个阶段跑完一轮，到 OnReady 一定都在）；组在就加、不在就建（`AddGroup` 给 False 就是在了）；卸载时**只撤自己加的**（`RemoveGroupItem`，探测）—— 别人先放进去的不是你的，原版的组也不是你的：

```python
SHARED = (("mei:group.ingot", "mei.group.ingot", ["yourmod:tin_ingot", "yourmod:lead_ingot"]),
          ("minecraft:itemGroup.name.pickaxe", "itemGroup.name.pickaxe", ["yourmod:bronze_pickaxe"]),
          ("mei:group.dust", "mei.group.dust", ["yourmod:tin_dust", "yourmod:lead_dust", "yourmod:iron_dust"]))

def OnReady(self, ctx):
    organizer = ctx.Registry.ItemOrganizer
    self.Joined = []
    for key, name_key, ids in SHARED:
        created = organizer.AddGroup(key, name=name_key)     # 在了给 False：直接往里加
        present = organizer.GetGroupItems(key)
        added = [i for i in ids if i not in present]         # 别人先放进去的不归你撤
        organizer.AddGroupItemFromList(key, added)
        self.Joined.append((key, created, added))

def OnUnload(self, ctx):
    organizer = ctx.Registry.ItemOrganizer
    remove_item = getattr(organizer, "RemoveGroupItem", None)   # 探测
    for key, created, added in self.Joined:
        if remove_item is None:
            if created:
                organizer.RemoveGroup(key)        # 老版本 MEI：只撤自己建的组
            continue
        for item_id in added:
            remove_item(key, item_id)
        if created and not organizer.GetGroupItems(key):
            organizer.RemoveGroup(key)            # 自己建的、没别人用了才撤组
    self.Joined = []
```

规矩照原版的：**同一类、至少三样**（两样一组，折起来还不如直接摆着），一样东西只进一个组；工具、盔甲按种类进（青铜镐进「镐」，不按材料另开一组）。原版没有的一类、几个模组都可能有的（金属粉）用通用键 `mei:group.dust`。蔚蓝科技那份（蔚蓝仓 `external/mei/groups.py`）是完整的例子：16 个并进原版 / 共用的组、23 个照它创造栏分的自己的组。玩家可以在设置里关掉分组（「启用物品分组」，关掉时平铺），你照常登记就行。

类别（`AddCategory` / `AddCategoryItem`）同理，有 `RemoveCategory`（探测）—— **目前只登记、MEI 还没用到它**（物品栏只认分组）。

**标签不在 MEI 里登记了**（2026-10-30 起，原来的 `AddTag` / `AddTagItem` 一族删了）：tag 由引擎记，你的物品在 netease_tags 里注册
（网易文档「自定义标签」），或者在物品的 `minecraft:tags` 组件里写。MEI 按 tag 查走 `ItemManager.ResolveTag(tag)` / `ctx.Registry.TagLookup`
（3.10 起问引擎的 `LookupItemsByItemTag`，[api §4.10](api.md#tag-lookup)）—— 比如熔炉的燃料表认 `minecraft:logs_that_burn`，
你的原木注册进这个 tag 就会出现在燃料格里。分组 2026-10-30 起修好了：原来登记了分组物品栏会整个抛异常（组表存的是 id，排的时候拿它当 Item）。

<a id="search"></a>
## 3. 搜索（[api §4.8](api.md#search)）

`ctx.Registry.ItemSearchIndex.Search(query)` 用的是玩家在搜索栏里用的同一套语法：

| 写法 | 意思 | 例 |
|---|---|---|
| 不带前缀 | 名字：拼音 / 首字母 / 原文的模糊匹配，多音字每个读音都搜得到 | `lvbaos`、`lv bao shi` |
| `@xxx` | 命名空间（模糊）| `@skyblue_tech` |
| `#xxx` | 完整的悬停文字（原文或拼音）| `#攻击伤害` |
| `&xxx` | 名字整个相等（含拼音全拼）| `&铁锭` |
| `$xxx` | 英文 ID（模糊）| `$emerald` |
| 空格 / `\|` / `-` | 几段都要满足 / 段里满足其一 / 排除 | `@minecraft -铁` |

<a id="filters"></a>
## 4. 物品栏的筛选与排序（[api §4.9](api.md#item-filters)）

物品栏搜索框右边的筛选按钮打开一个菜单：上面一排排标签块（按下就是选中，几项都要满足，和搜索一起用 —— 先搜、再筛、再排），
下面一行步进器选排序与升 / 降。选的东西全局记住。你的模组可以往里加：

```python
def OnRegister(self, ctx):
    filters = getattr(ctx.Registry, "ItemFilters", None)            # 探测（2026-10-30 起）
    if filters is None:
        return
    filters.AddFilter("yourmod:machine", "yourmod.filter.machine", self.IsMachine, 90)   # 名字是本地化键，也可以直接写字
    filters.AddSort("yourmod:tier", "yourmod.sort.tier", self.TierOf, 90)

def IsMachine(self, item):          # 这样物品算不算；抛异常当「不算」
    return item.ItemId.startswith("yourmod:") and "machine" in item.ItemId

def TierOf(self, item):             # 排序值，没有给 None（排在最后）
    return MY_TIERS.get(item.ItemId)
```

- `order` 是菜单里的先后（内置 10 ~ 80，原版扩展的「燃料」35，加法的「隐藏物品」1000 排最后）；Id 带命名空间，**重复的不收**（不能覆盖别人的）。
- 选了的几项都要满足（减法）；`AddFilter(..., additive=True)` 登记的是**加法**：选了不把表筛小，而是把平时不显示的物品（藏起来的）里它认的加进来，
  别的筛选照样再筛 —— 内置的「隐藏物品」就是这样。`additive` 参数是 2026-10-30 加的，老版本 MEI 传它会 TypeError，要兼容就先 `try`。
- 菜单最多放 24 个标签块，超过 8 行才上下滚。
- 卸载时 `UnregisterFilter` / `UnregisterSort`；不写也行：扩展都卸载时 MEI 回到只有内置的那几项。
- `item.Info` 里的数值（攻击力、护甲、耐久……）对部分原版物品引擎给 0 而不是没有（方块类燃料的燃烧时长、弓的攻击力）—— 按「大于 0」筛时想一下有没有这种例外。

下一篇：[05 · 界面与工具](05-screens-and-tools.md)。
