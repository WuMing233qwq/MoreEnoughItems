# 给 MEI 写扩展

> 面向**第三方模组作者**：你的模组要让 MEI 显示你的配方、在你的界面上挂 MEI、接 MEI 的工具模式……从这里开始。
> 2026-10-30 整理成这个目录；原来的 `docs/extension_api.md` 的内容都搬进来了（那一篇只留一张「旧节号 → 新位置」的对照表）。
> 设计上的取舍（为什么是组件、为什么传类不传实例）在 `docs/architecture/extensions.md`。

## 读的顺序

| 篇 | 讲什么 | 什么时候读 |
|---|---|---|
| [01-getting-started.md](01-getting-started.md) | 从 0 开始：拿到 MEI、写扩展类、生命周期、资源包怎么放、缺接口怎么办 | **先读这篇** |
| [02-recipes.md](02-recipes.md) | 注册配方：类型、来源、配方对象、`Recipe.Id` 要稳定、往别人的类型里加、查配方 | 要让 MEI 显示你的配方 |
| [03-recipe-page.md](03-recipe-page.md) | 配方页：JSON 规范、配方页脚本、槽位、动画、说明行、多候选格、动作按钮 | 要画你的配方页 |
| [04-items.md](04-items.md) | 物品：Item 只读、加变体、藏物品、分组、搜索、物品栏的筛选与排序 | 要改物品栏里显示什么 |
| [05-screens-and-tools.md](05-screens-and-tools.md) | 界面与工具：让你的界面挂上 MEI、工具模式的放置目标、在 MEI 里开配方页 | 要和 MEI 的界面互动 |
| [api.md](api.md) | **接口参考**：每个门面、每个名字的签名与说明 | 查某个接口 |

指南讲「怎么做」，每用到一个接口就链到 [api.md](api.md) 的那一条；api.md 每条后面写「见 ……」链回讲它的那一节。

## 一张图

```
你的客户端系统 ── CreateComponent("MoreEnoughItems", "MeiApi") ──► MEI（没装就给不出，判空，软依赖）
        │                                                            │
        └── RegisterExtension(你的扩展类) ──────────────────────────► 装配器：OnInit → OnRegister → OnReady（重进世界前 OnUnload）
                                                                     │
                                       每个阶段给你一个 ctx：Registry（注册与查询）· Types（类）· UI（界面）· Utils · Const · Log
```

- **只能经组件接入**：你的模组写不出 `import MEIScripts.xxx`（Python 的 import 只在本 addon 包根下解析）。
- **软依赖**：玩家没装 MEI 时组件给不出来，你的模组照常跑；不用在 `netease_require.json` 里声明。
- **能拷走的样例工程**：`docs/samples/mei_sample/`（一个配方类型「研磨」，入口、扩展、配方页 JSON、`.lang` 都有）。
- **真实的大例子**：蔚蓝科技（SkyblueTech）接了 30 多台机器，含流体槽、产电、多产物、自写配方页脚本；合成样板接了工具模式与配方转移，另有四个选物品的界面接了工具模式（[05 §6](05-screens-and-tools.md#example)）。

## 对 MEI 自己的维护者

改 `mei_behavior/MEIScripts/api/` 的任何对外签名，都要同步这个目录（先改 [api.md](api.md)，再看哪篇指南讲到它），并想清楚要不要升 `API_VERSION`：
**只有破坏性变更才升**；纯新增不升，在 api.md 那一条写「探测」，指南里的写法用 `getattr` 探测。
