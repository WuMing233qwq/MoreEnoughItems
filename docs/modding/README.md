# 为 MEI 编写美丽的扩展!

> 面向**第三方模组作者**：你的模组要让 MEI 显示你的配方、在你的界面上挂 MEI、接 MEI 的工具模式……从这里开始。  
> 关于设计上的取舍（为什么是组件、为什么传类不传实例）在 `docs/architecture/extensions.md`。

## 读的顺序

| 篇 | 讲什么                                          | 什么时候读 |
|---|----------------------------------------------|---|
| [01-getting-started.md](01-getting-started.md) | 前置准备：检测MEI组件、写扩展类、生命周期、资源包怎么放、缺接口怎么办         | **先读这篇** |
| [02-recipes.md](02-recipes.md) | 注册配方：类型、来源、配方对象、`Recipe.Id` 要稳定、往别人的类型里加、查配方 | 要让 MEI 显示你的配方 |
| [03-recipe-page.md](03-recipe-page.md) | 配方页：JSON 规范、配方页脚本、槽位、动画、说明行、多候选格、动作按钮、托管配方页 | 要画你的配方页 |
| [04-items.md](04-items.md) | 物品：Item 只读、加变体、藏物品、分组、搜索、物品栏的筛选与排序           | 要改物品栏里显示什么 |
| [05-screens-and-tools.md](05-screens-and-tools.md) | 界面与工具：让你的界面挂上 MEI、工具模式的放置目标、在 MEI 里开配方页      | MEI 的界面互动 |
| [api.md](api.md) | **接口参考**：每个门面、每个名字的签名与说明                     | 查某个接口 |

指南讲「怎么做」，每用到一个接口就链到 [api.md](api.md) 的那一条；api.md 每条后面写「见 ……」链回讲它的那一节。

## 概览图

```
你的客户端系统 ── CreateComponent("MoreEnoughItems", "MeiApi") ──► MEI（没装就给不出，判空，软依赖）
        │                                                              │
        └── RegisterExtension(你的扩展类) ──────────────────────────► 装配器：OnInit → OnRegister → OnReady（重进世界前 OnUnload）
                                                                       │
                                       每个阶段给你一个 ctx：Registry（注册与查询）· Types（类）· UI（界面）· Utils · Const · Log
```

- **工程示例**：`docs/samples/mei_sample/`（一个配方类型「研磨」，入口、扩展、配方页 JSON、`.lang` 都有）。
- **可参考的项目**：蔚蓝科技（SkyblueTech）最早支持了MEI的科技类型模组（[05 §6](05-screens-and-tools.md#example)）。

## 对 MEI 自己的维护者

改 `mei_behavior/MEIScripts/api/` 的任何对外签名，都要同步这个目录（先改 [api.md](api.md)，再看哪篇指南讲到它），并想清楚要不要升 `API_VERSION`：
**仅破坏性变更才考虑提升**
