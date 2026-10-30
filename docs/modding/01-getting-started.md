# 01 · 从 0 开始接入 MEI

> 目录在 [README](README.md)，接口的签名在 [api.md](api.md)。

## 1. 先知道的四条规矩

1. **只能经组件接入，写不出 `import MEIScripts.xxx`。** MEI 的一切（包括扩展基类）都从 `CreateComponent` 拿到的实例上取。
2. **扩展类只能定义在拿到基类之后。** 基类是运行时取到的对象，写在模块顶层必然 NameError —— 包进函数里（下面的 `Build()`）。
3. **拿不到组件是正常情况，必须判空。** 玩家没装 MEI 时给不出实例，这就是软依赖。
4. **注册时机不用你管。** MEI 还没装配完时你的扩展会排队，装配完统一装；已经装配完就当场装。`RegisterExtension` 随时可调。

<a id="component"></a>
## 2. 拿到 MEI（[api §1](api.md#component)）

`CreateComponent` 要本地玩家 id，所以不能在客户端系统构造期调，挂到 `UiInitFinished` 这类稍晚的事件上：

```python
# YourModScripts/client/mei_bridge.py
import mod.client.extraClientApi as clientApi

Api = None


def Connect():  # type: () -> bool
    """ 拿 MEI 的组件；拿不到（没装 MEI）给 False，别抛 """
    global Api
    if Api is not None:
        return True
    try:
        player_id = clientApi.GetLocalPlayerId()
        component = clientApi.CreateComponent(player_id, "MoreEnoughItems", "MeiApi") if player_id else None
    except Exception:  # noqa  MEI 缺席时引擎的表现未必统一，一律当没装
        return False
    if not component:
        return False
    Api = component
    return True
```

拿到之后用 `Api.GetApiVersion()` 做能力判断（`GetModVersion()` 只给人看）。

## 3. 写扩展类

```python
# YourModScripts/client/mei_extension.py
from . import mei_bridge

_BUILT = None


def Build():  # type: () -> type or None
    """ 造出扩展类。**同一个游戏进程里只造一次** —— 每次进世界造一个新类，会被当成「另一个扩展抢同一个 ID」拒掉 """
    global _BUILT
    if _BUILT is not None or not mei_bridge.Connect():
        return _BUILT
    MeiExtension = mei_bridge.Api.GetExtensionCls()

    class MachinesExtension(MeiExtension):
        ID = "yourmod:machines"             # 必须带命名空间前缀
        NAME = "yourmod.mei.ext.machines"   # 本地化键
        AUTHOR = "You"
        VERSION = "1.0.0"
        MIN_API_VERSION = 2

        def __init__(self):
            self.Registered = []            # 构造期不碰引擎、不碰 MEI

        def OnRegister(self, ctx):
            ...                             # 注册类型、来源、配方页脚本（02、03 篇）

        def OnUnload(self, ctx):
            ...                             # 把 OnRegister 注册的逐条撤掉

    _BUILT = MachinesExtension
    return _BUILT


def Setup():
    """ UiInitFinished 之后调：每次进世界都注册同一个类 """
    cls = Build()
    if cls is not None:
        mei_bridge.Api.RegisterExtension(cls)
```

传**类**不传实例：MEI 控制构造时机，免得你在 `__init__` 里碰引擎撞上时序问题。
类型（`RecipeCategory`）、来源这些也是运行时从 `ctx.Types` 取的类，所以你的配方类型包也要包进函数里（蔚蓝的做法：每个机器包导出一个 `Build()`）。

<a id="lifecycle"></a>
## 4. 生命周期与反注册（[api §2](api.md#extension)）

| 阶段 | 干什么 | 什么时候必须用它 |
|---|---|---|
| `OnInit` | 登记 tag、比较器、序列化器 | 你的东西是别人注册时的前提 |
| `OnRegister` | 注册配方类型、配方页脚本、物品、界面 | **绝大多数扩展只要这个** |
| `OnReady` | 全部扩展都注册完之后 | 往**别人的**类型里加工作站、加来源（原版的类型是 `mei:vanilla` 在 OnRegister 注册的）|
| `OnUnload` | 撤掉 | 你在 OnRegister 注册过东西（重进世界、热重载都会调）|

`OnRegister` 注册的每一样都要能在 `OnUnload` 撤掉，不然重进世界时重复提交、被拒：

| 注册 | 撤 |
|---|---|
| `SourceRegistry.RegisterCategory` / `RegisterSource` | `UnRegisterCategory`（连同名下来源）/ `UnRegisterSource` |
| `RecipeUIManager.RegisterScript` | `UnRegisterScript` |
| `category.AddStation(stack, owner=self.ID)` | `category.RemoveStationsByOwner(self.ID)` |
| `ctx.UI.Screens.Register` | `ctx.UI.Screens.Unregister` |
| `ctx.UI.Slots.Register` | `ctx.UI.Slots.Unregister`（探测）|
| `ctx.UI.Drops.Register` | `ctx.UI.Drops.Unregister` / `UnregisterAll`（不写 MEI 也会兜底撤）|
| `ItemFilters.AddFilter` / `AddSort` | `UnregisterFilter` / `UnregisterSort`（不写 MEI 也会回到只有内置的）|
| `ItemOrganizer.AddGroup` / `AddCategory` | `RemoveGroup` / `RemoveCategory`（探测）|
| 往别人的组（原版的锭、镐……）里 `AddGroupItem` | `RemoveGroupItem`（探测，只撤自己加的那几样，[04 §2](04-items.md#organizer)）|
| `ItemManager.AddItems` / `SetHidden` | 不用撤：每次进世界物品表重建、隐藏表重读，你的 OnRegister 会再来一遍 |

**准入**（不过就拒、记日志）：`ID` 带 `:`、`MIN_API_VERSION` 不高于当前、`ID` 不重复、传的是类。
**异常隔离**：任一阶段抛异常，记 `[MEI/ext:<你的 id>]`、跳过这一阶段、别的扩展照常 —— 你的 bug 拖不垮 MEI，也没人替你修，看日志。

## 5. 能力探测

**纯新增的接口不升 `API_VERSION`**，老版本 MEI 没有它。用之前 `getattr` 探一下，没有就退化（别让整个扩展加载失败）：

```python
screens = getattr(ctx.UI, "Screens", None)
if screens is None:
    ctx.Log.warn("这个版本的 MEI 没有 ctx.UI.Screens，界面不挂 MEI")
else:
    screens.Register("yourmod.machine_screen", {"ContentPaths": ["/root_panel"]})
```

api.md 里写了「探测」的都要这么用。`MIN_API_VERSION` 写你**实际需要**的最低值：写高了老版本拒绝加载你，写低了可能在老版本上撞到缺的接口。

## 6. 资源包怎么放

配方页是 JSON UI，放进**你自己的**资源包，单开一个目录：

```
resource_pack/ui/
  mei_recipes/            ← 和 MEI 有关的 layout 都收在这里（玩家没装 MEI 时整块用不上，好认）
    common.json
    GrinderUI.json
  _ui_defs.json           ← 每个文件都要登记
```

可以直接 `@` 引用 MEI 的控件（`"0@mei_common.item_panel"`、`"buttons@mei_recipe_common.buttons_panel_vertical"`）：JSON UI 的命名空间跨资源包是全局的；
MEI 没装时只是那几个控件解析不出来，不会让你的 json 整个失败（那时你的扩展也没注册、配方页不会被打开）。
**贴图**同理是全局的：引用 `textures/ui/mei/...` 在 MEI 缺席时是缺图，那个控件没 MEI 时也会显示的话自己带一份。

<a id="ask"></a>
## 7. 缺接口的时候：先问，不绕

`ctx` 上没有你要的东西时，**不要**：用 `ctx.Scripts` 逃生舱够内部模块；自己调引擎实现一遍；照抄内置扩展里的绕法。
**开 issue 说清楚**：谁需要、你现在只能怎么凑、凑出来的东西错在哪。判据是「下一个第三方还会不会需要它」—— 会就该进 API；
只有你用得到的（你自己的流体配色表）本来就是你的数据，不该进 MEI。

## 8. 参考实现

MEI 内置的原版扩展就是样板（`mei_behavior/MEIScripts/mei_mod/extensions/vanilla/`）：**一个配方类型一个包**（门面导出 `CATEGORY` / `SOURCE` / `UI_SCRIPT`，
支持快捷合成的再加 `POLICY`），它对 MEI 的每一处依赖都走对外门面 `MEIScripts.api.facades.*` —— 你能用的东西它才用。
vanilla 能在模块顶层写 `RecipeCategory(...)` 是因为它在 MEI 包内；你写不出这一行，包进函数里。

下一篇：[02 · 注册配方](02-recipes.md)。
