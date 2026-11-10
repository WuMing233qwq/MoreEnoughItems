# MEI 扩展样例工程

最小可用的第三方接入（`extensions.md` §8 的 E4，2026-10-29）：给 MEI 加一个配方类型「研磨」——
圆石 → 沙砾 → 沙子、骨头 → 骨粉，带配方页、tooltip 预览、收藏、置顶。**MEI 是软依赖**：玩家没装 MEI 时这个 addon 什么都不做。

接口说明在 `docs/extension_api.md`；这里是能直接拷走的骨架。离线回归：`debug/scripts/probe_samples.py`
（不进游戏：用 MEI 真的装配器把它装上、卸下、再装上，看注册表是不是干干净净 —— 也就是「热重载验证」）。

## 目录

| 文件 | 拷到你的 addon 哪里 | 做什么 |
|---|---|---|
| `behavior/SampleMeiScripts/modMain.py` | 行为包的脚本根目录 | 入口：客户端注册一个系统 |
| `behavior/SampleMeiScripts/client_system.py` | 同上 | **唯一的接入点**：`UiInitFinished` 时 `CreateComponent("MoreEnoughItems", "MeiApi")`，问版本、注册扩展 |
| `behavior/SampleMeiScripts/mei_extension.py` | 同上 | 扩展本体：类型、来源、配方页脚本、反注册。**不 import MEI 的任何东西**，要用的都从 `ctx` 拿 |
| `resource/ui/sample_mei.json` | 资源包 `ui/` | 配方页的控件（照配方 JSON 规范第三版：wrapper 与 content 写一样的绝对尺寸、`PREVIEW` 那一行） |
| `resource/ui/_ui_defs.json` | 资源包 `ui/_ui_defs.json` | 把上面那个 JSON 加进你自己的 `_ui_defs` |
| `resource/texts/zh_CN.lang` | 资源包 `texts/` | 名字一律本地化键，不写死中文 |

改成你自己的：把 `sample` / `SampleMei` / `sample_mei` 换成你的命名空间（类型 Id、扩展 ID 都要带命名空间前缀），
`RECIPES` 换成你的配方表；机器类的配方页照蔚蓝科技的接入（20 台机器）去写。

## 要点（都在代码注释里，这里列一遍）

- **扩展类写在函数里**：基类要等拿到 MEI 的组件才有（`mei.GetExtensionCls()`），没法写在模块顶层。
- **每次进世界都注册同一个类**：`build()` 缓存着造好的类；MEI 认同一个类是幂等的，换一个新类会被当成「另一个扩展抢同一个 ID」拒掉。
- **注册过的都要撤**：`OnUnload` 里 `UnRegisterScript` + `UnRegisterCategory`（连同来源）。加了工作站、槽位种类、物品分组的，
  也各自撤（`RemoveStationsByOwner`、`ctx.UI.Slots.Unregister`、`ctx.Registry.ItemOrganizer.RemoveGroup`）。
  追加的物品（`ItemManager.AddItems`）、隐藏（`SetHidden`）不用撤：MEI 每次进世界都重建物品表。
- **不能覆盖别人的类型**：同一个类型 Id 注册第二次会被拒、MEI 记一行警告（原版的 `crafting_table` / `furnace` / `fuel` 也一样）。
- **版本**：`MIN_API_VERSION` 写你用到的写法要求的版本；新加的接口（比如 `ctx.UI.Slots.Unregister`）老版本 MEI 没有，用 `getattr` 探测。
- **驱动机器的东西（燃料、能量）不进配方本身**：要画就在配方页脚本里自己取（`extension_api.md` §5.46）。

## 许可

和 MEI 一样是 LGPL-3.0（文件头）。只是样例，照着写你自己的不受影响；要原样拷走，记得留着文件头。
