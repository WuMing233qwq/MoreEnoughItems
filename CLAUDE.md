# MEI 项目 —— 网易我的世界配方/物品浏览器

**MoreEnoughItems (MEI)** —— 网易《我的世界》中国版 ModSDK（Python 2.7）配方查询模组，
功能对标 JEI / EMI。命名空间 `MoreEnoughItems`，Addon 名 `EtrRecipeBrowser`，LGPL-3.0（`LICENSE`；它所依托的 GPL-3.0 原文在 `COPYING`，两份都要随仓库保留）。
仓库 https://github.com/WuMing233qwq/MoreEnoughItems ，约 9.2k 行 Python。
**不依赖任何前置模组**（2026-10-27 与 EterniaModCore 解耦，见下「架构关键点 · 自带的轮子」）。

## 必读（开工前）

- **`docs/engineering.md`** —— 工程规范唯一权威：目录蓝图、依赖方向、命名/代码风格、
  性能与健壮性守则、提交前自检清单、文档规范、提交纪律。**规范正文不复制进本文**，
  本文只做「必读指引 + 引擎实机结论 + 工程现状与路线图」。
- **`docs/architecture/README.md`** —— 全部专题的索引、依赖关系与总施工顺序 S0~S6，
  **以及每块的当前状态（2026-10-13 按代码重新核对）**。**动手前先读它定位自己在哪一阶段**；
  各专题分篇含现状盘点（带 file:line）、方案、分期与回归基准。
- **`docs/migration/`** —— 各阶段的**施工任务书**。S0~S3(U1/U2) 已全部完成，
  它们现在是**历史施工账**：只在需要某个决定的「为什么」时去查，**不要当成待办**。
  索引见 `docs/migration/README.md`。
- **`docs/architecture/item_model.md`** —— 物品模型与注册管线：`ItemManager` 是全仓
  **唯一的 Item 持有者**（`BrowsableItemManager` 已删）。**动物品注册链路前必读**：
  §5.2 的「物品有 L1(id 表) / L2(实例池) 两级就绪度」是判断「某段代码要等到哪一步」的依据；
  §6 是最终方案（**P1~P7 已全部落地**）——**`ItemPipeline` 已取消**，改走
  「可变状态搬旁表、Item 事实不可变」，时序问题因此消解。
  **`Item` 拿到手只读**；改物品只有两条路：`ItemManager.SetHidden()` 等**旁表写入**，
  与 `AddItems(specs)` **加变体**。身份字段（`ItemId`/`AuxValue`）一律不可事后修改
  ——要改就加变体 + 隐藏原件。`MeiItem` 已随 `Hidden` 旁表化删除。
  **带 userData 的变体和原件是同一个键**（`(id, aux)`），按键藏会连变体一起藏 —— 只藏原件用 `SetPlainHidden`（`Item.IsPlain`）。
  §9 是**创造栏的物品变体**（原版扩展的 `creative/`：游戏目录生成的 aux 表 + 手写的四族 userData），§9.8 是落地与换游戏版本时怎么维护。
- **`docs/architecture/quick_craft.md`** —— 快捷合成（配方转移）专项，**N1~Q5 已落地并实机通过**（工作台）；
  剩 Q6 对外文档与方块容器侧。
  写入只剩**玩家侧**一条：`SetPlayerUIItem`（工作台 32~40 行优先、背包 2×2 28~31；引擎只让写玩家开着的那个界面）。
  方块那条（`SpawnItemToContainer`，坐标由客户端给）**第三十八轮删了**（连同 `KIND_*` 与旧的快捷合成接口，§10.9）：模组机器、样板这类界面都交给
  **按界面登记的转移处理器**（`ctx.UI.Transfers`：MEI 算清单、处理器检查与执行，**第三十七轮落地**，§10.8；蔚蓝机件加工台、合成样板已接）。
  + 的悬停文字（为什么灰着、缺什么）走动作按钮的第五条绑定 `.hover`（JSON 挂 `common.hover_text`，PC 悬停、触屏按住都出）。
  **引擎没有「移动物品」接口** ⇒ 搬运只能拆成读+扣+写且无事务，安全模型是
  **逐格小事务 + 失败补偿**，不做整单原子。**原版方块拿不到坐标**，故第一版只做玩家侧。
  §0 那三条硬规矩（轮子不许枚举业务 / 贴合既有惯例 / 扩展性优先）适用于本项目所有新模块。
  打表工具 `debug/ingame/ui_slot_scan.py`。**动 plus 按钮或写 `mei_mod/network/` 前必读。**
- **`docs/modding/`** —— **面向第三方模组作者的文档**（2026-10-30 从 `extension_api.md` 整理）：五篇指南（`01-getting-started` 从 0 接入、
  `02-recipes` 注册配方、`03-recipe-page` 配方页、`04-items` 物品、`05-screens-and-tools` 界面与工具）+ **接口参考 `api.md`**，互相链着（显式锚点 `<a id>`）。
  改动 `MEIScripts/api/` 的任何对外签名都必须同步它（先改 `api.md`，再看哪篇指南讲到它），并考虑是否要升 `API_VERSION`（只有破坏性变更才升；
  纯新增写「探测」）。`docs/extension_api.md` 只剩「旧节号 → 新位置」的对照表，别处写着「`extension_api.md` §x」的照表找。
- **`docs/architecture/extensions.md`** —— 第三方接入设计：**「扩展」这个抽象存在的唯一理由
  是第三方模组在物理上无法 `import MEIScripts.xxx`**。通道是**自定义组件**
  （MEI 侧 `RegisterComponent("MoreEnoughItems", "MeiApi", …)`，第三方侧
  `CreateComponent(…)`）—— **不是 `ImportModule`**，后者会把 MEI 的内部模块路径
  变成事实上的公共 API，且只能做硬依赖；Comp 是**软依赖**，MEI 没装就降级。
  事件载荷不能带 Python 对象，故 API 也不能走事件。含 `MeiExtension` 基类、
  三阶段生命周期、`ctx.Scripts` 整包是**不承诺稳定的逃生舱**这条边界、
  标准目录编排与第三方单文件样例，以及 §8.5「解除前置依赖」（2026-10-27 做完：没有整包内置，只按项目习惯重写了用到的几样）。
  **动扩展面前必读。**
- **`docs/architecture/settings.md`** —— 设置系统专题（**P0，2026-10-26 实机可用**）：
  **游戏「设置」界面左栏的 MEI 分栏**（通用 / 关于），行控件复用原版 `settings_common` 模板；
  值在 `state/settings/`（独立存储 `mei_settings`），代理按登记表动态挂绑定。
  §3 是 **JSON 行必须照写的绑定名规则**，§5 是「加一个设置项」的四步，§6 是每项接到了哪，
  §6.1 是上下栏（搜索 / 翻页）避让与复位的做法，§6.2 是配方页开着时的避让与代理参数 `AllowChangeVisible` / `VisibleControlPath`。**动设置或栏的避让前必读。**
- **`docs/architecture/bookmarks.md`** —— 收藏系统专题（照 NEI 做）：§6 存储 v4、§7 分期与待办、
  §9 / §10 是四家与 NEI 的读源码记录、§11 收藏栏的排版与交互、§12 快捷键（10-29 起 MEI 自己的按键绑定：组合键、设置「按键绑定」页录键，键表只在这里；§12.3 是当时的组合键评估与 P0-1 实机结果）。**动收藏前必读。**
- **`docs/architecture/focus.md`** —— 焦点探针（`mei_mod/ui_script/proxy/focus/`）：一个点上是哪个物品格，**任何界面都认**
  （原版容器、HUD、别的模组的界面）。**查询时才递归找**（2026-10-28 重写）：从扫描根逐层 `GetChildrenName` 往下，不可见的、矩形不含这一点的
  整棵跳过，名字像物品渲染器的 custom 才读物品；**不用 `GetAllChildrenPath`**（别人家界面上会让游戏退出，引擎结论 §36）、不在后台扫。
  MEI 自己的格子不走控件树，`UIScriptMain.PanelAt` 直接问 grid 与配方页；入口 `UIScriptMain.FocusAt` / `FocusAtCursor`。
  §2 是各种界面从哪儿找，§5 是**崩溃证据在哪（UniSDK CrashHunter 日志）**，§8 是历史（第一版后台扫描、别人家界面上的崩溃）。
  **要知道「这一点上是什么」时用它，别再按 grid 原点推下标**（旧的 `SlotAtPoint` 就是这么坏的）。
- **`docs/architecture/tooltip.md`** —— MEI Tooltip（`mei_mod/ui_script/mei_ui/tooltip/`）：全局各一个的提示控件
  （接受物品、配方预览），原版 purpleBorder 底图，**PC、移动端两个宿主**（PC 跟光标、移动端停在格子旁），内容控件一次只建一个、收起不删、
  同一种复用，**透明着建齐再显示**（alpha 0 + `propagate_alpha`），界面代理每帧驱动。分三轮（作者 2026-10-27 定）：一轮控件 + 预览 + 调试键 T（✅ 实机）、
  二轮桌面悬停 + 原版名让位 + 多候选格重写（第十五次实机完成，加了设置「启用高级Tooltip」，待第十六次）、
  三轮移动端二级菜单（10-27 出了方案、作者定了八条；M1 菜单壳子第十七次实机基本没问题，M2 / M3 同日写完，M4 照 HTML 预览改成一个框、同日第二版按内容收宽并换扁平按钮，第十八次实机通过）。
  §2.1 是**调 tooltip 离光标的位置**（改 JSON 里 `cursor_gap` 的 offset，不用动代码），§3 有设置开关的接线，
  §6 是**移动端二级菜单**（minijei / MEI / SDK 三份读源码的结论、动作表、分期、作者定的十四条、§6.9 落位、§6.10 二次确认与
  「跟着这一条收藏走」、§6.11 样式预览、§6.12 一个框的排版），
  §4 是**配方 JSON 规范第三版与预览的做法**（所有配方 wrapper / content 写算出来的绝对尺寸、content 自包含；每个类型一行 PREVIEW
  指向自己的 content、不写尺寸；预览只建 content，格子跟着它的尺寸走；缺省有预览，不要的写 `preview_def=None`），
  §5 是悬停探针与「哪些格子出 MEI tooltip」，§8 是待实机确认的引擎行为。
  **动 tooltip、加配方类型、动槽位的悬停前必读。**
- **`docs/architecture/floating.md`** —— 悬浮窗与查找状态（`mei_mod/ui_script/mei_ui/floating/`，2026-10-28 立，第五次实机作者「目前无任何问题」）：
  物品栏搜索框旁的查询按钮（触屏上点一下进查找状态，下一次点哪就用焦点探针查哪、在那儿出二级菜单）、悬浮窗模式（收着 / 展开 / 点开带黑底三种样子，
  可拖、记位置，阈值看物品栏或收藏栏任一侧；**悬浮窗管事时不避让原版界面、照样避让配方页**）、HUD 与未支持界面的注入（跟着界面栈走，同一时间只注入栈顶那一个）、
  **HUD 上点 MEI 开 MEI 自己的界面**（PushScreen）。
  §1 是作者定的，§2 是三种样子与不避让，§5 是原生拖拽，§6 是注入（只在压栈时），§6.1 是 MEI 自己的界面，
  §7 是层级（**两栏的层级由根控件上的两个变量控制，在哪调**），§8 是待实机确认的事，§10 是四次实机的记录（崩溃的分析在 `focus.md` §8.2）。
  **动悬浮窗、查找状态、MEI 覆盖层的显隐、往原版界面注入控件前必读。**
- **`docs/architecture/modes.md`** —— 三种模式：普通 / 工具 / 作弊（`mei_mod/ui_script/mei_ui/modes/`，2026-10-30 第二十九轮写完，待实机）：
  收藏栏顶栏最左边的模式按钮（原 setting 占位）点一下轮换，工具染黄、作弊染红、全局存（prefs）；作弊每次开界面问服务端、给物品时服务端再查一次操作员，
  **只认引擎给的发起者 `__id__`**（§3；网络层原来认的 `__from` 是客户端自己写的、能冒充）；工具模式拿起物品、再点一下放到别的模组登记的控件上（`ctx.UI.Drops`，§5）。
  §2 是点格子时在哪接走（`ModeManager.Intercept`，所有 MEI 物品格），§4 是拿起 / 放下与**显隐全走绑定、开关界面写回藏着**，§7 是待实机确认的。
  §11 是 ItemRenderer 标准的评估（**第三十七轮作者定不做**，继续用 `ctx.UI.Drops`）；**§12 是放置目标的改进**（accepts；回调返回 False / 一句话是不收，手里的东西不放下、tip 提示）
  与蔚蓝那次被回退的实现的复查（七条缺陷、改了哪些）。
  **动模式、作弊的网络请求、工具模式的捕获层、放置目标前必读。**
- **`docs/design/item_filter.html`** —— 物品栏筛选菜单的排版预览（2026-10-30，本地网页；四种候选 A 单列分段 / B 两栏 / C 页签 / D 标签 + 步进器，
  每种都能点、能标「通过 / 有问题」写备注、导出）。菜单下一轮照作者选的写（`README.md` §8 P2-12）；生成器 `debug/scripts/gen_filter_preview.py`
  （从 `registry/filters.py` 与原版扩展读筛选与排序、从 `zh_CN.lang` 取名字）。
- **`docs/design/recipe_tree.html`** —— 配方树（S5）的**方案与交互预览**（2026-10-28，第二版；本地网页，浏览器直接打开；**第一版已按它写完，待实机**，
  现状与和本页的出入在 `docs/architecture/recipe_tree.md` §0 —— **动配方树前先读那一节**）：
  PushScreen 新界面、**自上而下**、照网易成就界面做原生拖动（`cut` → `dragpanel` → 可拖的 `input_panel`，引擎自己夹边）；
  **多格节点**（作者定：工作方块带边框和背景 + 原料组合并边框、无背景；折叠只剩主要产出那一格）；布局由 Python 算坐标
  （**不用每行一个 stack_panel**：要对齐还得自己算、藏了还占位、连线要等下一帧读位置），算法是「对锚点的逐层轮廓打包 + 父组落到子树群中间」，
  折线横段按区间分层；组模板 + 线池；防无限递归三道（路径排除 / 还原配方识别 / 护栏）、合并汇总、节点菜单、收藏。
  代码落点 `ui_script/mei_ui/recipe_tree/`（照现有界面包：`node.py` + `script.py` + `screen.py` + `controls/` + 纯逻辑的 `modules/`）。
  预览里的算法与布局是真算的。算法的老设计在 `recipe_tree.md`。
- **`docs/architecture/recipe_types.md`** —— 原版的七种配方类型（S6，2026-10-29 第十八轮写、第十九轮按作者意见重做配方页）：高炉、烟熏炉、营火、切石机、制图台、锻造台、酿造台
  各自怎么查、怎么画。§1 是引擎给的样子（引擎结论 §45 的摘要），**§2 是配方页的规矩（作者第十九轮定：每个类型自己的命名空间、布局照原版界面、
  进度条用原版控件、镜像格）**，§3 是物品变体（10-30 起统一由原版扩展的创造栏表加，`VARIANTS` 退役），§4 有营火模型（纸娃娃渲染方块几何体），§7 是**酿造**（药水 aux ↔ 类型名的映射表、
  全表自己凑、三种配方、桶、上 1 下 3 的配方页），§8 是已知的限制与待实机确认的。**动这几个类型、加药水类型、往原版扩展加类型、写新的配方页前必读。**
- **`docs/architecture/binding_cost.md`** —— 绑定回调开销专题：集合绑定是每帧全量拉取，
  每个 ItemPanel 槽位挂 6 个绑定、其中 5 个是最贵的 `always` 档。
  **改 UI 绑定前必读**，尤其两条负面结论：§3（`#visible` 类绑定不能降级为
  `always_when_visible`，会自举死锁）与 §1.1（那 5 个 `#visible` 是
  `ItemPanel` 上**互相独立的分层控制位**，不是冗余，砍掉会丢表达能力）。
- **`docs/architecture/structure.md`** —— 结构总纲：把 JEI/EMI/REI 解构成六条结构轴
  （条目代数 / 成对等价 / 自描述配方 / 一等 Category / 单一注册门面 / 布局分离），
  再按 py2 + JsonUI 的能力降维成 MEI 的目标类骨架。**改动类型体系或注册面前必读**——
  骨架定义以它为准，四篇分篇只引用不复制。
- **原前置仓 `32fc56101ffe49b0b15b199870391b88/docs/`**（2026-10-27 起 MEI 不再依赖它，只剩参考价值）——
  **`RECIPE_BROWSER_DESIGN.md`**（本项目 recipe/item 数据结构设计蓝本：EMI ingredient 代数 + REI 序列化
  + JEI 分桶索引，含 6 阶段迁移路线，是配方系统一切改动的判据）。
- **三条硬性规则**（`engineering.md` 开篇）：
  ① 所有源文件保留 LGPL-3.0 许可证头；
  ② 判定引擎返回字符串一律 `isinstance(x, basestring)`，**禁止 `isinstance(x, str)`**
  （引擎侧多为 unicode，str 分支必落空）；
  ③ 改变行为/结构的提交必须同步 `CLAUDE.md` 与 `docs/`（反漂移）。

## 工具链与路径

- Python 2.7 在 `C:\Python27\python.exe`（PATH 上**没有** `python` / `python2`）。
  无测试框架，**语法检查是唯一可用的静态检查**：
  ```
  C:\Python27\python.exe -m compileall -q mei_behavior\MEIScripts      # 全树
  C:\Python27\python.exe -m py_compile mei_behavior\MEIScripts\<file>  # 单文件
  ```
  `compileall` 会产出 `.pyc`（**不入库**），完事清理：
  ```
  find mei_behavior/MEIScripts -name '*.pyc' -delete
  ```
- `py_compile`/`compileall` **只解析语法**，不解析 `mod.client.*` / `mod.server.*` 导入，
  也**查不出 import 链断裂**（见下「当前断裂」——那几处语法全过，进游戏才炸）。

- **⚠️ 两个必须知道的工具链陷阱**（2026-08-21 实测，栽过三次）：

  1. **`python -m py_compile <file>` 的退出码恒为 0，完全不能用作判据。**
     py2.7 的 `py_compile.py` 末尾只有 `main()`，**没有 `sys.exit(main())`**，
     返回值被丢弃。只有 `compileall` 的退出码可信。

  2. **`compileall` 抓不到「含中文但缺编码声明」这一类错误。**
     内建 `compile()` 接受 `str`（字节）时**不执行 PEP 263 检查**，而
     `py_compile`/`compileall` 正是先把源码读成 `str` 再喂给 `compile()`；
     可 **import 机制是执行 PEP 263 的** —— 于是这类文件 `compileall` 报 OK、
     进游戏 `SyntaxError`。本项目中文注释密集，这是最容易反复踩的坑
     （`mei.py`、`utils/__init__.py`、`state/cache.py` 都栽过）。
     ⇒ **给任何文件加中文前先确认第一行有 `# coding=utf-8`**；
     全仓体检用 `debug/scripts/probe_encoding.py`。
  真正的 import/运行由引擎完成，跑模组必须用网易 MC Studio 启动配置的测试世界。
- **MC Studio 的 UI 编辑器（`MC_Editor.exe`）开着时会自己重写 `mei_resource/ui/_ui_defs.json`**（2026-10-27 实测）：
  `ui/` 下增删改名任何文件，一秒内就把全部 JSON 按字母重列一遍 —— 连 `ui/settings_screen.json` 也写进去。
  **这一行进不进 `_ui_defs` 都不影响**（作者 2026-10-28 实测）⇒ 不要删它、也不要再让作者删。
  编辑器里还开着的旧文件别再保存，会把脚本改过的 JSON 盖回去。
- **路径双视图**（同一目录）：
  - Windows（Read/Edit/Write 工具用这个）：
    `D:\MCStudioDownload\work\wuming233qwq@163.com\Cpp\AddOn\bb9ce455c824409faa2c53582c9fa4b7\`
  - MSYS/Bash（Bash 工具用这个）：
    `/d/MCStudioDownload/work/wuming233qwq@163.com/Cpp/AddOn/bb9ce455c824409faa2c53582c9fa4b7/`

## 工程现状（2026-10-13 对代码重新核对）

### 已落地

- **配方页节拍 `OnAnimTick`**：整页一个 timer（0.2 秒），按脚本单独对表；
  **第一帧是 `0`，在 `OnCreate` 之后立刻送到**（`PrimeAnimTick`）。
  > 旧实现是「等下一拍 + 那一拍只对表」，创建后有最长 **0.4 秒**的空窗，
  > 控件停在 layout 初值上，看着像“卡一下才开始动”（2026-09-04 作者反馈）。
  > ⇒ 写配方页时**把第 0 帧当成初始外观**，不要在 `OnCreate` 里另外手动画一次。

- **物品链路**：服务端 `ClientLoadAddonsFinishServerEvent` → `GetLoadItems(False/True)`
  分出可见/隐藏两表 → `NotifyToClient("SyncLoadedItems")` 只发 id；客户端
  `ItemManager` 建 id/name 双索引并**持有全部 Item**（含隐藏，可见集走
  `GetBrowsableItems()`）+ `registry/search.py` 的 `ItemSearchIndex` 拼音/模糊搜索
  （**全项目唯一的拼音库接触点**：`libs/pinyin_lite` 的 `PinyinIndex`，多音字每个读音都搜得到）+ `ItemOrganizer` 分组骨架。
  > **搜索语法**（2026-10-28，作者定，照 NEI）：空格隔开的几段都要满足、段里 `|` 隔开的满足其一、`-` 开头排除；
  > `@` 命名空间（模糊）、`#` 完整的悬停文字（原文或拼音）、`&` 整名相等（含拼音全拼）、`$` 英文 ID（模糊）。
  > 不带前缀、不带 `-` 的普通词**合起来**交给拼音引擎（它自己按空格拆、按分数排）—— 拼音加空格照旧能搜、顺序以它为准；
  > 悬停文字用到才向引擎要、按物品缓存，排在最后筛。搜索栏的悬停提示（`items_browser.json` 两处）写着这套语法。回归位 `probe_search.py`。
  > **悬停文字的缓存按物品实例记**（10-30 第三十五轮，作者报 `#保护` 出来全部附魔书、别的附魔名搜不出来）：原来按 (id, aux) 记，
  > 41 本附魔书同是 `enchanted_book:0`、共用了第一本的字。**名字索引收全部物品**（藏着的也收，平时的结果里滤掉）：物品栏的「隐藏物品」筛选要搜得到它们
  > （`Search(query, include_hidden)`）。
- **按 tag 查物品、方块（2026-10-30 第三十九轮，单独提交，待实机）**：MEI 自己不记 tag —— 组表里的标签记录（`ItemOrganizer.AddTag` 一族）与 `TagConst` 删了，
  tag 由引擎记（模组在 netease_tags 里注册，或物品的 `minecraft:tags` 组件）。`registry/tags.py` 的 `TagLookup`（对外 `ctx.Registry.TagLookup`）：
  `ItemIds(tag)` / `BlockNames(tag)` 3.10 起问引擎的 `LookupItemsByItemTag`（物品组件）/ `LookupBlocksByBlockTag`（方块信息组件），`getattr` 探测；
  引擎没有（3.10 之前）、给的结果认不出、调用出错时，物品退回物品表里缓存的 `Info.Tags`（每种只记一行），方块给空；每个 tag 只问一次，物品表换了版本就作废。
  走它的：`ItemManager.ResolveTag`、熔炉的燃料表（`furnace/fuels.py`）、list 原料的公共 tag（`tools/parser.common_tag` 里「带这个 tag 的正好是这些」那一步，
  候选 tag 仍看 `Info.Tags`）。返回值的样子官方文档还没有，按更新说明写的（引擎结论 §49），回归位 `probe_tags.py`。

- **UI 栈**：`mei_ui/core`（`UIScriptMain` / `UIMainNode` / `context` 主节点单例
  + `adaptive/` 自适应布局三件套 geometry/registry/rules）、
  `items_browser`（可翻页物品浏览器）、`items_sidebar`（侧栏）、
  `recipe_details`（配方详情，全项目最大模块，含 `binding.py` 的 `RecipeBinder`；**配方页脚本在每一行 `#visible` 的绑定回调里当场接**（作者原来的设计：
  翻页、换类型时新脚本在同一轮拉绑定里接上，格子直接覆盖、不闪；10-28 P0-2 推到主节点每帧的 `Tick`，中间那一帧格子回缺省值、翻页闪，**10-29 第二十轮改回来**）——
  接入 / 拆除走 `modules/host.py`，第三方的 `OnCreate` 抛了只丢那一行（回调照样返回 True，这条绑定不会被引擎扔掉）；动作按钮的推送缓存先记再推、推不上去撤回（第十轮）；
  **工作站格子没变就不清、不推行列数**，第二十轮；工作站 grid 不暂停绑定、推完行列数后核对 30 轮图标，第二十一轮）、
  `recipe_tree`（配方树，PushScreen 的新界面，下面单独一条）。
- **原版界面代理**：**23 个**原版容器/工作站屏幕（工作台/熔炉族/箱子族/铁砧/酿造台/信标…）的代理参数在
  `extensions/vanilla/screens.py`（2026-10-28 从核心层的 `constants/proxy.py` 搬进原版扩展），原版扩展装配时经
  `ctx.UI.Screens.Register` 逐个登记、卸载时注销（第三方的界面走同一个门面，`extension_api.md` §5.59）；
  `ui_script/proxy/manager.py` 的 `ProxyManager` 记参数、给 SDK 挂代理，以覆盖层注入，不替换原版屏幕。
  > 代理登记因此跟着扩展装配走（`SyncLoadedItems` 末尾），不再在 `UiInitFinished` 里。
- **配方渲染契约**：`recipe_details/modules/slots.py` 的 `render_slot(control, slot)` 统一收口——
  0 候选 → 空 `ItemPanel`；1 候选 → `ItemPanel`；多候选 → `MultiItemPanel`（轮播）；
  格位下标 → `Ingredient` 的映射由 `resolve_input_slot()` 按 shaped 配方**真实 Width**
  换算（**不**补齐到 3 列）。
- **数据模型拆包**：`common/classes/types.py` 已拆为 `types/` 包
  （`item.py` / `recipe.py` / `spec.py` / `category.py` / `ingredient.py` / `keys.py`），
  每个 `.py` 配 `.pyi` 存根。
- **物品表的两条写入路径**（看着同级，实现依赖完全不同，别混）：
  **造物路径** `RegItemFromIdList` / `AddItems` —— 经 `ItemFactory` 造实例、入池、建索引，
  依赖整条造物链；**旁表路径** `SetHidden` / `SetPlainHidden` / `ItemOrganizer` —— 只动集合，一个 Item 都不碰。
  两者都经 `__Touch()` 撞版本号，派生物（搜索索引、UI 分页缓存）按 `ItemManager.Version()`
  自愈，**registry 不反向通知上层**。
- **全量配方扫描与工作站的用途（10-29 第二十七轮写，第二十八轮按作者意见改成要全表时才扫，离线探针全过，待实机）**：
  **有人要某个类型的全表时才扫**（`EngineRecipeSource.GetAll` → `RecipeScanner.Request(urgent=True)`；查工作站的用途就是要全表），
  **不在进存档时扫**（作者 10-30：游戏有动态注册配方的接口，开局扫了，以后为了兼容只能每加一条就整个作废重扫，反而更费）。
  `extensions/vanilla/tools/scanner.py`：一个类型一趟，按物品表逐个问，每帧 10 毫秒（有人在等）；锻造台按原料扫 —— 纹饰配方没有产物，
  `EngineRecipeSource.SCAN_BY`；酿造、燃料自己有全表，不扫。实机第一次（进存档全扫的那一版，2463 个物品的整合包）：八个类型 19704 次、平均每次 0.13 毫秒，
  工作台 2564 条 —— 只扫工作台约 2463 次 ≈ 0.3 秒查询。
  **单配方查过的也记下**（`tools/answers.py` 的 `EngineAnswers`）：引擎的每个回答按（来源, 方向, 物品）记下，平时查来源、用途问过的不问第二次，
  扫描再问到也直接用；按原料查（官方说昂贵）同样记 —— 记的是「引擎对这个物品答了什么」，不拿产物反推（反推对不上方块态 data，`state/cache.py`）。
  扫描结果与记下的答案一起在 `RecipeScanner.Reset()` 作废（重进世界；SDK 没有「配方变了」的事件，以后要兼容动态注册的配方也是调它）。
  **查工作站的用途带上整个类型的配方**（JEI / EMI 的做法）：`RecipeManager.QueryRecipeFull` 返回（结果, 还在凑的类型）——
  它服务的类型排最前（`SourceRegistry.FindCategoriesByStation`，按 `RecipeCategory.Stations` 现查），每个类型里先是真用到它的、后面接 `QueryAll` 的全表；
  全表还在凑的类型不进查询缓存，要全表的类型插到扫描最前、那几帧预算 10 毫秒；配方页这个类型的页码后面写「扫描中」，
  扫完自动刷新一次、按那一页第一条定位（`RecipeDetailsScript.PollScan`）。给不出全表的来源（只实现了 `QueryBy*`）不算在凑（`IsCategoryBuilding`），
  只出真用到它的那几条。工作台的用途是整个合成表，开页排序的「现在做得出来」先用 `matcher.reachable` 筛（离线 1500 条约 50 → 23 毫秒）。
  第三个查询方向没加（并进了「用途」）；工作站图标的点击照旧（右键用途就是全表）。
  扫完记一行 `[MEI/scan] 全量配方扫描完成: …`（每个类型几条、问了几次、其中真问引擎几次、多久扫完）。
  回归位 `probe_extensions.py` X-11 ~ X-11d、`probe_transfer.py` T-6；历史见 `docs/migration/tasks_s4.md` §8.6。
- **快捷合成（N1~Q5 已落地）**：`mei_mod/network/`（`base/` 是**不认识业务**的通讯轮子
  —— codec/channel/request/handler；`protocol/` 放具体请求）+ `mei_mod/transfer/`
  （`matcher` 全局配额 / `targets` 两种写入口 / `inventory` 内置来源 / `executor` **派发器**）
  + `registry/transfer.py`（`TransferRegistry`，形制对齐 `SourceRegistry`）。
  **搬运归来源做**（`ItemSource.MoveTo`），框架只派发——加一个物品源不动框架一行。
  开页预检把做不了的配方 **灰掉而非藏掉**（`@RecipeAction.Enabled` + 基类自带的
  `#enabled` 绑定），结论在**每次重建配方页脚本**时失效（覆盖开页/切类型/翻页）。
  排序三级稳定分区 **置顶 → 可合成 → 其余**，置顶绝对优先、TypeTab 顺序不受影响；
  顺序是「进页那一刻的推荐」，**转移后不重排**。**动它前读 `quick_craft.md`。**
  > **10-30 第三十五轮全仓审查后的服务端核对**（`quick_craft.md` §6.6）：只认引擎给的发起者（`Trusted`）；**方块容器的清单不收**（第三十八轮整条路删了）
  > （坐标是客户端给的，收了谁都能清空、塞满任意一个加载着的箱子）；整张清单先核对再动格子（来源没登记、写的格不在要清的那片里、条数超限都在清空前拒掉）；
  > 只放清单这一条要的东西；**搬的带着附魔 / 耐久 / 自定义名字 / userData 原样过去**（原来只写 id、aux、数量 —— 损坏的工具搬进合成格就成了新的、
  > 潜影盒里的东西没了）；背包扣不掉就撤回目标格（`SlotTarget.Restore`）。回归位 `probe_transfer.py` T-7。
  > **第三十六轮定 1.0 之后大改**（`quick_craft.md` §10，未施工）：玩家侧留着；方块容器那条删；不搬物品的界面走 ItemRenderer 标准；往模组机器里搬交给模组自己的处理器。
  > **第三十七轮**：转移处理器落地（`quick_craft.md` §10.8）—— `TransferHandler` / `TransferRequest` / `TransferSlot` / `TransferError`（`ctx.Types`），`ctx.UI.Transfers.Register(界面, 处理器)` 与 `Request(recipe, grid)`；老写法 `callback(Recipe)` 照样认；+ 的悬停文字、点了没成的原因挂在页码后面。ItemRenderer 标准作者定不做，样板这类也走处理器（`CONSUMES` 假）。
- **槽位控件基件化**（`mei_resource/ui/mei/mei_common.json`）：
  `slot_base`（根：全部派生绑定名 + `#visible` 集合绑定）/
  `slot_background(_bordered)` / `slot_item(_marked)` / `slot_overlay`
  + 两个按钮变体（`slot_overlay_button` 按下闪白、`_flat` 不闪）。
  `item_panel` / `group_item_panel` / `bordered_item_panel` **改为组装**，
  不再各拄一份 `background/item/overlay`。
  > 守它的是 `debug/scripts/probe_ui_slots.py`：按引擎的继承规则把槽位
  > **展开成实际生效的树**再比金标准（`_golden_slots.json`），
  > 并交叉校验「JSON 引用的绑定名 ⊆ Python 注册的那一套」。
  > 展开器在 `debug/scripts/uiexpand.py`，第三方的槽位也过同一套检查。

- **条目种类（第二种槽位条目）**：`Stack.KIND`（纯字符串，在 `types/`）
  + `SlotPanelRegistry`（UI 层，`KIND → (单候选面板, 多候选面板)`）
  + `ctx.UI.Slots.Register(kind, panel, multi=None)`。`render_slot` 多了一个可选 `kind=`
  （**空格靠它** —— 没有 Stack 可问时，“这个控件是什么格”是调用方的界面事实）。
  纯新增，**不升 `API_VERSION`**，第三方用 `getattr` 探测。
  > 两条配套约束：① **自定义槽位面板必须继承 `ItemPanel`、控件必须长在
  > `mei_common.item_panel` 上** —— 槽位前缀的绑定集是按它的结构写死的，
  > 自建控件的回调**永远不会被调且零报错**（`engineering.md` §5.1e）；
  > ② `ItemStack.copy()` / `take_*` 已改 `type(self)`，因为 `render_slot` 在数量 > 1 时
  > **先 copy 再取 KIND**，写死基类等于在分发前一刻把种类丢了。
  > 能量/经验**不该做成 KIND**（没有身份、不进物品表、点了查不出用途）。
- **扩展系统骨架**：`api/`（对外组件 `MoreEnoughItems:MeiApi` + `ExtensionContext`
  五组门面）+ `mei_mod/extensions/`（`MeiExtension` 基类 / `ExtensionLoader` 三阶段装配
  + 异常隔离 / `EXTENSIONS` 显式清单）。**`common/recipes/` 已整体迁入
  `extensions/vanilla/`**（`sources.py` + `ui_scripts.py`），槽位渲染契约
  `render_slot` / `resolve_input_slot` 留在框架侧
  （`recipe_details/modules/slots.py`）。装配点在 `SyncLoadedItems` 末尾。
- **设置系统（2026-10-26，P0，作者实机验收 ✅）**：游戏「设置」界面左栏的 MEI 分栏（通用 / 关于两页）。
  `state/settings/`（`Toggle` / `Slider` / `Choice` / `Action` + `SettingsManager`，独立存储 `mei_settings`）
  + `ui_script/settings/`（`SettingsProxy` 挂在 `settings.screen_world_controls_and_settings`，
  `OnCreate` 按登记表挂普通绑定）+ `mei_resource/ui/settings_screen.json`（原版命名空间，
  `modifications` 追加）与 `ui/mei/mei_settings.json`。
  通用页「布局设置」两项：**每行最大物品显示数量**（1~12，默认 6，物品栏与侧栏共用，开界面时读）、
  **启用自适应**（默认开；关掉时 `UIScriptMain` 的遮挡检测与避让都返回空）；另有「恢复全部默认」。
  **10-29 加了第二页「按键绑定」**（标题「键盘与鼠标-快捷键绑定」，上面「快捷键」；实机通过）与通用页的「配方树 → 启用节点配方预览Tooltip」（默认开，实机通过）；
  通用页的「恢复全部默认」不动按键绑定（`RESET_WITH_ALL`），按键页自己有「恢复全部默认按键」。
  「信息显示」两项（2026-10-27 加）：**启用高级Tooltip**（默认开；关掉时 MEI tooltip 一律不出、格子照常出原版悬停文字，
  tooltip 根与 PC 宿主也藏，开界面时读、两个方向都写）、**触控tooltip是否沿对面侧显示**（默认关；开着时触屏菜单摆到点的那一格
  另一侧的屏幕边上，方便双手操作，`tooltip.md` §3）。
  10-30 又加两项：**启用显示物品命名空间**（默认开；悬停文字最底下一行深蓝斜体 `§9§o`）、**启用显示物品ID**（默认关；倒数第二行深灰 `§8`，aux 不是 0 写 `id:aux`）——
  写在格子的悬停文字里（`controls/item/panel.py` 的 `identity_lines`，原版悬停文字与 MEI tooltip 的标题都是它），不另画在 tooltip 底部（`settings.md` §6）。
  关于页：「模组信息」（版本、作者、开源地址、LGPL-3.0）+「许可证」（`LICENSE` 全文，一段一行，
  原文写死在 JSON 里、不进 `.lang`）。读设置走 `state/settings` 的 `GetRowItems()` / `IsAdaptiveEnabled()` / `IsAdvancedTooltipEnabled()` /
  `IsTouchOppositeSide()` 等读值函数。
  2026-10-28 又加了六项（作者定稿的文案，`floating.md` §3）：「布局设置」里的**在搜索框旁启用查询按钮**（默认开），
  新分组「悬浮窗」里的**启用悬浮窗模式**（默认关）、**自动收起阈值**（滑条 0~11，默认 0）、**启用快速收起悬浮窗**（默认关 ——
  作者第三次实机后加：点黑底收起太容易误触）、**在游戏界面展示悬浮窗**（默认关）、**启用悬浮窗强制兼容**（默认关）。
  10-30 第三十九轮「布局设置」查询按钮后面加**启用物品分组**（默认开；「关闭后，物品浏览器不再有可收起/展开的物品分组」）：关着时物品栏平铺、组表照旧，分页记着自己分没分组、缓存的对不上就重排（`IsItemGroupsEnabled()`，下次打开容器生效，`settings.md` §6）。
  > 选项（N 选 1）是「带档位的滑条 + 文字」，不是下拉框；滑条**松手才提交**。
  > JSON 行的绑定名、本地化键、定稿文案与许可证全文由 `probe_settings.py` 对账 —— 拼错在游戏里是静默的。
  >
  > **上下栏的避让**（`mei_ui/common/base.py`）：不避让时的宽度**从布局算**（`GridLayout.GridWidth`），
  > 障碍没了用 `SetFullSize` 把栏切回父控件 100%。**不要再记「读到过的宽度」** —— 旧实现记历史最大值，
  > 读到过期的 JSON 默认 140 后，每行格数 ≤ 6 时复位就比面板宽（`settings.md` §6.1，回归位 `probe_avoidance.py`）。

- **收藏一期（2026-10-26 写完，前后十次实机，`bookmarks.md` §12.2）**：存储 v4（`state/bookmarks.py`：多页签、分组 `g`、数量 `n`、全局 / 按存档，v3 → v4 迁移）；
  收藏栏（`items_sidebar/`：`modules/layout.py` 纯函数排版、`controls/bookmark.py` 格子、顶栏页签切换）；
  配方页 `FocusRecipe`（从收藏点开翻到那一条）；收藏的键盘入口原是调试按键，10-28 改成正式快捷键（下面「快捷键」）。
  > 收藏栏格子改用 `MeiItemsSidebar.bookmark_item_panel`（多 4 条边框、2 条标记绑定），
  > `common/base.py` 多了 `GetGridRows` / `BuildSlots` 两个钩子 —— 收藏栏的 grid 比整体布局矮（下面是最近浏览），
  > 原先遮挡与分页都按整体行数算，收藏栏一直是空的所以没暴露。
  > 还多了 `GetItemGrids`（脚本持有的全部 `ItemsGrid`，关界面逐个解绑、定时自检都按它）与 `CheckGrids` ——
  > 收藏栏有两个 grid，基类原先只收拾 `ItemsGridIns`，最近浏览关界面从没解绑过（引擎结论 §27-4）。
  > **C 两用**（作者 2026-10-27 定）：配方收藏上展开 / 收起这一条（条目字段 `x`，没按过的跟视图走：竖排展开、横排收起；
  > 横排里展开的自己占整行），物品收藏上折叠 / 展开所在的组；不在分组里的展开配方照分组画框（`layout.frame_key`）。
  > 展开的一行最后是**工具**（`Recipe.GetShownCatalysts()`，缺省全部催化剂、熔炉覆写成空），数量固定 1、不乘倍数（作者 2026-10-27 定；
  > 起因是蔚蓝模版成型机的刻印模版被塞进了原料，已挪到催化剂）。
  > 物品栏、收藏栏、最近浏览三个 grid 的高在 JSON 里写 `default`（行数 × 20）：grid 按 JSON 的尺寸规则均摊行距，
  > `SetSize` 管不到（引擎结论 §28；原先收藏栏分组底色上下行之间有缝，`bookmarks.md` §11 第 8 条）。

- **焦点探针（2026-10-26 第一版后台分帧扫描 + 点查索引，多轮实机可用；10-28 在别人家界面上一挂上就崩，作者定改成查询时递归，同日重写；第五次悬浮窗实机作者「目前无任何问题」）**：
  `mei_mod/ui_script/proxy/focus/`（`search` 递归找，纯逻辑 / `manager` 入口 `FocusManager.Query`、`GetCursorPos`；查崩溃时用过的诊断开关 `trace` 10-28 问题查清后删了）。
  没有挂 / 摘、后台推进、点名、标脏、动态根（第一版的 `index` / `scanner` / `tracker` 整个删了）。MEI 侧 `UIScriptMain.FocusAt(x, y)`：
  `PanelAt` 先认 MEI 自己的格子（`ItemsGrid.PanelAt`：grid 整块 → 按行列估格 → 逐格量真实矩形，藏着的栏不算；配方页 `RecipesGridBind.PanelAt`），
  不是再递归找（扫描根 `FocusRoots`：RootPath，强制兼容先试 `FocusConst.CompatRoots`、没有就退到最根；跳过 `FocusExclude`：MEI 的覆盖层），
  给 `FocusTarget(Pos, Hit, Panel, Item)`；`FocusAtCursor` 是 PC 光标那一点（快捷键用它）。设计见 `focus.md`，回归位 `probe_focus.py`。
  > **两遍查找**（10-28 作者报背包最左、最右的「死区」，`focus.md` §8.3）：第一遍严格按矩形剪枝；没找到再把矩形放宽 `OVERFLOW_MARGIN`（64）找第二遍
  > —— 子控件可以伸出父控件（引擎结论 §41），原版背包 grid 两边各伸出 `inventory_panel` 37。名字规则补上了合成器输出格的 `output_slot`。
  > 读物品前按名字筛（`item_named`：带 item 不带 flying，或就叫 renderer）—— 格子里的 `durability_bar` / `hover_text`、HUD 的心形条这些
  > custom 不读；别的模组把物品渲染器起了别的名字的认不到，要放开改 `item_named`。

- **MEI Tooltip（第一轮 2026-10-27 第十一次实机完全成功；第二轮第十二次实机基本可用，修正同日写完；第十三次实机后又改了跟随与建控件；第十四次实机效果很好，修了切换时的闪动、离光标的位置挪进 JSON；第十五次实机完成，加了设置开关；第三轮 M1 触屏菜单第十七次实机基本没问题，标题改成完整悬停文字；M2 / M3 同日写完，M4 一个框照预览实现、第二版按内容收宽并换扁平按钮与图标；10-28 加了触屏划进就开菜单，作者「目前无任何问题」）**：
  `mei_ui/tooltip/`（`layout` 纯函数 / `items` 接受物品 / `recipe` 配方预览 / `manager` 管理器，挂在主节点 `main.Tooltip`）
  + `mei_common` 的 `tooltip_background` / `tooltip_title` / `tooltip_items` / `tooltip_root`（`mei_main` 里只挂一份 `mei_tooltip`）
  + `mei_recipe_common.preview`（配方预览的整个 tooltip，每个类型的 PREVIEW 派生自它）。
  > **配方 JSON 规范（第三版，作者 10-27 定）**：所有配方的 wrapper 与 content 写**算出来的绝对尺寸**（原来是绝对父控件的相对尺寸），
  > content 自包含（变量写在它自己身上，不靠配方行传）；`RECIPES_GRID` 后面紧跟一行
  > `"PREVIEW@mei_recipe_common.preview": {"$recipe_content_template": "<命名空间>.content_panel"}`，不写尺寸。
  > PREVIEW 就是整个 tooltip（背景、标题、预览 grid），显示一条配方预览只建它这一个控件；预览只建 content：格子
  > `mei_recipe_common.preview_cell` 骨架同为 `wrapper/content`、尺寸 `100%c` 跟着 content 走，脚本一行不用改。
  > `RecipeCategory` 缺省按 `control_def` 推出 `<命名空间>.PREVIEW`，不适合预览的**显式写 `preview_def=None`**。
  > MEI 两个类型与蔚蓝 20 台都按它改了（配方页逐像素不变；蔚蓝共用行的 5 台与 HydroponicSand 把行上的变量挪进各自的 content；
  > 蔚蓝 Python 一行没改）。第二版拿整行在运行时裁，外面一圈照 JSON 规则排、尺寸对不上（作者指出），撤了。
  > 第三方没写那一行的，建不出来记一行警告、这一局不再试（`TooltipRecipeView.BROKEN`）。
  >
  > **两个宿主**：PC 是 `follows_cursor` 的 input_panel，偏移与贴边翻转改它里面的 `frame`（引擎结论 §29）；移动端是脚本摆在格子旁的
  > panel，里面竖排「内容 + 动作按钮行」（按钮第三轮接）。开界面按输入方式选一个。**PC 那个跟随的宿主一律不碰**（`SetPosition` 会让
  > follows_cursor 停掉，引擎结论 §29）：tooltip 的位置只改 frame 的偏移，按宿主**实际**位置算差 —— 宿主不在光标处或不跟也摆得对。
  > **PC 宿主在 PC 上一直亮着、藏 tooltip 只藏 frame**：藏着的宿主不跟光标，显出来那一刻停在旧位置、下一帧才跳到光标处，
  > 补过的差叠上去就闪到屏幕右下（第十四次实机）。**离光标多远、默认在哪边写在 JSON 里**：`tooltip_root/desktop/cursor_gap` 的 `offset`
  > （绝对值是距离、正负号是方向；作者 10-27 调成 11, 0：右边隔 11、顶边与光标齐平），脚本每次显示读一次，改位置不用动代码（`tooltip.md` §2.1）。
  > **设置「启用高级Tooltip」**（通用 → 信息显示，默认开）：`TooltipManager.OnCreate` 读一次（`Enabled`），关着时每个入口都不出、
  > `ReplacesVanillaName` 为假（原版名照常）、根与 PC 宿主也藏；每次开界面两个方向都写（`tooltip.md` §3）。
  > **内容控件**（作者 10-27）：一次显示只建一个控件；收起不删（拆掉 Python 的绑定、藏 frame）；同一种（接受物品 / 同一类型的
  > 预览）下次直接复用，换一种才先删再建（卡顿集中在显示新的那一下）；名字带定义名（`tip_<定义名>`）；关界面才删。
  > **透明着建齐再显示**（作者 10-27，他的常用手段）：`tooltip_background` 的 `alpha: 0` + `propagate_alpha`，内容控件生下来全透明、
  > 子控件跟着透明，照常建（不可见的话 `always_when_visible` 不拉，建不全；摆到屏幕外则可能画不出物品）；视图说齐了、尺寸两帧一样
  > 就摆到位并 `SetAlpha(1)`，最多等 0.5 秒。复用的显示前先写回 alpha 0；frame 收起、开界面写回不可见。
  > **每帧驱动**：界面代理 `OnTick` → 主节点 `OnTick` → `Tooltip.Update`（每秒 30 次；SDK 定时器最短 0.05 秒，引擎结论 §30）。
  > **PC 悬停**：探针挂在格子按钮现成的 hover 控件（`mei_common.highlight_panel`）自己身上，`always_when_visible` 集合绑定，
  > 悬停期间每帧报一次（Python 侧 `.overlay.hover`、`can_pause: False`）；`Update` 里按光标核对才显示，错过一帧下一帧还有。
  > 第二轮挂在多建的子控件上、按 `visibility_changed` 只报一次，第一次停上去常常要动一下鼠标才出（第十二次实机）。
  > 光标离开那一格、格子被拆（`ItemPanel.Destroyed`）就收起；快捷键 T 钉住的不被悬停换掉；没建成的那一格光标离开前不重试。
  > 出不出由格子自己说（`ItemPanel.HasMeiTooltip` / `TooltipContent`）：多候选格 → 接受物品，**标题是当前轮播到的候选完整的悬停文字**
  > （`ItemHoverText`：物品自带的几行 + 格子追加的说明；PC 上原版悬停文字让位给了它，只写名字会丢东西 —— 作者 10-27 指出），
  > 下面一行灰色「接受以下物品: 」；列表放不下（> 54）时**最后一格写「+N」、不画物品** —— 格子用自己的模板 `mei_common.tooltip_item_panel`、
  > 那两条绑定只挂在这张 grid 上（`TooltipItemsGrid`），**全局的 `item_panel` 不动**（作者 10-27：每格多一条绑定就是每帧多拉一次）；
  > 有预览的配方收藏 → 配方预览。这两类格子在 PC 上不出原版名（`HoverText` 给空，`MeiTooltipHidesName` 问管理器的 `HidesVanillaName`）；
  > **触屏上一律不出原版悬停文字、白色高亮保留**，**手指划进一格就开菜单**（作者 10-28：只检测移入，`tooltip.md` §6.13）。
  > `MultiItemPanel` 重写：`Select` / `Next` / `Prev`（手动选过就停轮播）/ `ResumeRotate` / `AddListener`（`extension_api.md` §5.57）。
  > **触屏二级菜单（第三轮 M1 ~ M3，`mei_ui/menu/`，`tooltip.md` §6）**：触屏上点格子不直接查，`ItemPanel.OpenTouchMenu` 交给 `main.Menu`
  > （`TouchMenu`，只记下、下一帧开）。菜单就是 tooltip 的移动端宿主：内容由 tooltip 建（有 `TooltipContent` 且设置开着 → 预览 / 候选，
  > 否则只有标题，标题是这一格完整的悬停文字）。**M4 起菜单是一个框**（作者看过 HTML 预览「非常满意新排版」）：`touch/frame` 是 purpleBorder，
  > 里面顶栏（种类 `MenuKind()` + 关闭的小 x：只有图标的 `menu_icon_button`，照搜索框的清空按钮，点击名 `button.mei.menu.close`；
  > 包在 `close_slot` 里，**大小与偏移只在 JSON 里调**（`$menu_icon_size` / `offset`，作者调成 14×14、往上 2），脚本排版时读回来）、
  > 内容（触屏上 `SetSprite` 换透明底、不画自己的框）、分隔线（白图要写 `fill`，不然只画出一个点；alpha 0.75）、
  > 按段排的按钮区（每个动作说自己在哪一段 `MenuAction.Section`，相邻同段并成一段、一段一行、左边灰字段名；数量与候选是步进器、中间写数字，
  > 候选用 mei_icons 的左右箭头 `MenuAction(icon=…)`；删除类红字 `Danger`、灰掉的灰字 `mute`）。按钮池是 JSON 里静态的 16 个按钮
  > （`button.mei.menu.<i>`，`BF_ButtonClickUp` 单个绑定），换成新画的扁平贴图（`textures/ui/mei/button/tooltip_button/`，外形照 hover content 的内凹，
  > 作者会重画）、14 高，**宽按字算**（`layout.text_width`：汉字估 9、半角估 6），框宽取内容、顶栏、最宽那段里宽的那个，别的段拉满
  > （普通格子 156 → 90，物品收藏 156 → 128）。位置全由 `menu.layout.box_layout` 算、绝对定位：菜单把 `TouchMenu.Layout` 交给 tooltip（`SetTouchLayout`），
  > tooltip 摆框时用内容尺寸调它、拿回框的尺寸（`tooltip.md` §6.12）。设置「触控tooltip是否沿对面侧显示」开着时，菜单摆到点的那一格另一侧的屏幕边上。
  > 这一格出哪些动作由面板说（`MenuActions()` 返回 `MenuKey`），动作在 `menu/actions.py`；**改收藏的写法是一组 `op_*`，快捷键与菜单共用**，
  > 菜单改完看 `BookmarkManager.Revision()` 变没变才让收藏栏重排。收藏格的动作全了：−1 / +1、上移 / 下移 / 移到组首（`MoveAt` 等，组内只在组里动、
  > 组外整个跳过组）、并组、移出、折叠、展开、横竖排、移除、删除整组（**点两下**）。−1 / +1 与排序点了不收：收藏栏一重排格子全是新的，
  > 先 `Tooltip.Release()`、再按「条目身份 + 角色」找新格子 `Adopt`（`tooltip.md` §6.10）。多候选格开菜单时停轮播，「上一个 / 下一个」、
  > 点接受物品列表里的一格都是选中候选。**落位按区域**（作者 10-27）：物品栏的格子摆在物品栏左边、收藏栏的摆在右边、配方页的摆在配方页右边，
  > 竖直跟着那一格，放不下贴着格子、贴屏幕边兜底；摆位置与宿主尺寸按「内容 + 菜单算好的按钮区」算（`tooltip.md` §6.9）。
  > 格子换了内容（`ContentKey()` 变了）就收起，翻页这类不用一个个去接；点空白处不收；PC 不受影响（作者定的在 `tooltip.md` §6.8）。

- **不依赖前置（2026-10-27，作者实机：运行基本无问题）**：`modRequire` 为空，`mei_mod/eternia/` 删了；事件、绑定、界面代理、拼音搜索都换成本仓自己的
  （`utils/events.py` / `utils/binder.py` / `ui_script/proxy/base.py` / `libs/pinyin_lite`），对照与拼音库的细节见「架构关键点 · 自带的轮子」。
  回归位 `probe_standalone.py`（没有前置的痕迹、两个工具的行为）与 `probe_pinyin.py`（字表、多读音、三处修掉的错）。

- **悬浮窗与查找状态（2026-10-28；第一次实机注入 HUD 必崩、悬浮窗拖不动，同日按作者意见改完；第二次实机查出 HUD 上展开问题多、焦点查询在没有代理的界面上崩，同日改完；第三、四次实机后又改了两轮（见下）；第五次实机作者「目前无任何问题」）**：
  `mei_ui/floating/`（`state` 纯计算 / `find` 查找状态与原版格子的替身 `SlotTarget` /
  `window` 悬浮窗 / `manager` 每个界面一份的 `FloatController`，挂在主节点 `main.Float` / `hosts` HUD 与强制兼容的注入 `FloatHosts`）
  + `mei_main.json` 里两种覆盖层（支持的界面 `mei_proxy_ui`；注入的界面 `mei_float_ui`，不带两栏）下的黑底、捕获层、悬浮窗
  + 物品栏顶栏最右边的查询按钮（`top/query`）+ 六个设置项。
  > **只在界面压栈时注入**（作者 10-28）：照 NetEase 往 HUD 加控件的写法，`PushScreenEvent` 里当场 `GetTopUINode()`、核对名字、建在原版根面板下
  > （已有就不建、没有就不注入、这一局不再试）。每个界面一份、跟着界面活：被盖住时收起藏好（`Cover`），露出来时显回（`Uncover`），出栈时放掉；
  > HUD 那份从进存档活到退出存档。**当前主节点改成了栈**（`core/context.py`），每帧由 `FloatHosts.Tick` 推当前那份。
  > 注入的界面里：两栏的控件与脚本第一次展开才建（`UIMainNode.EnsureScripts`），**不扫别人家的控件树、没有查找状态**（第三次实机后，
  > 引擎结论 §36），HUD 上不用 PC 的跟随宿主。
  > **悬浮窗是 JSON 原生可拖的 input_panel**（横条：握把 + MEI + 查询，默认屏幕上方正中；按在按钮上不拖、按握把拖，引擎结论 §32），
  > 隔约 0.5 秒读一次拖拽偏移、变了才按比例记，显示时 `SetOffsetDelta` 摆回去。
  > 物品栏、收藏栏的显隐从主节点挪到了 `FloatController.Apply`（每次开界面按样子两个方向都写）；拆的时候存储只在有改动时写。
  > 查找时 MEI 自己的格子出它自己的菜单，别的界面的物品格由 `SlotTarget` 替它出（来源 / 用途 / 收藏），认不出什么都不做。
  > **自动收起阈值比的是被原版界面挡住后每行还剩几格**（`BaseItemsGridScript.RowRoom`，取最少的那一行）—— 避让**不改列数**
  > （`GridLayout.ApplyCols` 没人调，列数恒等于「每行最大物品显示数量」，被挡的格子只是空着）。**悬浮窗管事时不避让**
  > （作者 10-28 第二次实机后：悬浮窗模式开着、从悬浮窗点开着、HUD / 强制兼容 / MEI 自己的界面；`UIScriptMain.AvoidanceSuppressed`），
  > 满格压在原版界面上；阈值仍按「要是避让会剩几格」算，免得一点开就被自动收回。
  > 用触摸回调的按钮（悬浮窗按钮、黑底、捕获层）JSON 里都写 `button_mappings: []`（项目里设置按钮一直是这个写法，
  > `common.button` 自带的映射会把点击截给按钮名）。
  > **第二次实机后（作者 10-28）**：① HUD 上点 MEI 不再在游戏界面里展开，**PushScreen 开 MEI 自己的界面**（`floating/screen.py` 的 `MeiScreen`；
  > 画布 `mei_main.mei_screen` 派生自 `common.base_screen`；主节点第四种 `KIND_SCREEN`：一打开就是点开的样子，点 MEI / 点黑底 / ESC / 背包键关掉；
  > HUD 上查到配方也带着那一条开它，`floating.md` §6.1）；② 焦点探针在没有代理的界面上走保守模式（第三次实机证明无效，已撤）；
  > ③ 代理参数 **`AllowChangeVisible`**：配方页开着时藏原版主内容、关了显回，配方页自己的四块加入自适应、被藏的那块不再避让（`settings.md` §6.2）；
  > ④ 层级先不改，作者自己调。
  > **第三次实机后（作者 10-28）**：① 还崩 —— 这次找到了落盘的 Python 日志（`log_storages`），坐实崩在焦点探针扫别人家界面的第一遍里、
  > 读物品之前 ⇒ 保守模式整个撤掉，**注入的界面不扫别人家的控件树、不出查找状态**（`UIMainNode.FindAvailable`），诊断开关
  > `mod_info.FocusForeignTrace`（`focus.md` §8.2，引擎结论 §36；第四次实机后又改了，见下）；② 悬浮窗管事时**照样避让配方页**（登记时 `always=True`），
  > 两栏从藏着变成显示时**当场补推**（`ShowSides` → 脚本 `SetShown` → `ItemsGrid.Revive`；推完行列数、格子被拉过两轮才核对一次）；③ 挂 MEI 的原版界面表搬进原版扩展，
  > 新门面 `ctx.UI.Screens`；④ 代理参数 **`VisibleControlPath`**（配方页开着时藏哪一块，兜底主内容；工作台、背包写 `/content_stack_panel`）；
  > ⑤ 两栏的层级由 `mei_main.json` 两个根上的变量 `$mei_side_layer`（0）/ `$mei_float_side_layer`（30）控制，悬浮窗管事时调高
  > （`floating.md` §7；10-30 起 `SetLayer` 只在两栏露着、真要换时才调，注入的界面与 MEI 自己的界面的两栏按悬浮窗那一档的定义建，引擎结论 §47）；
  > ⑥ 设置「启用快速收起悬浮窗」（默认关）。
  > **第四次实机后（作者 10-28）**：第三轮的几项「基本没问题」；诊断开关复现的崩溃由 UniSDK CrashHunter 坐实是焦点探针第一次开扫时
  > 引擎抛的 C++ 异常（`focus.md` §8.2）⇒ **焦点探针改成查询时递归，注入的界面上也能查了**（`FindAvailable` / `CanFind` 删掉，诊断开关改名 `FocusTrace`，第五次实机后连同别的调试代码一起删了）；
  > 触屏划过格子就开菜单（`tooltip.md` §6.13）；开界面时 grid 刷 `cannot find position` —— 「推完行列数核对」改成格子真被拉过两轮才问、
  > 藏着的栏不自检（`floating.md` §2，引擎结论 §38）。
  > **第五次实机后（作者 10-28）**：「目前无任何问题了」⇒ 删掉调试代码与调试输出：焦点探针的诊断开关（`mod_info.FocusTrace` + `proxy/focus/trace.py`）、
  > tooltip 的 follows_cursor 判定与「悬停探针一大批」的警告、构建超时 / 注入前后 / 转移成交 / 查询无结果这几行日志、动作按钮「仅用于诊断」的 `Order`；
  > 出错、警告、开局的几行汇总与收藏的调试按键留着。顺手修了没有置顶时每次进存档误报「置顶表不是列表(tuple)」（`state/pins.py`，`floating.md` §10.5）。
  > 回归位 `probe_floating.py`（纯计算、查找、悬浮窗的位置、三种样子与被盖住、两栏层级、注入的生命周期、JSON、接线、行物品数与不避让、
  > MEI 自己的界面、配方页的避让与两个代理参数、挂 MEI 的界面登记、各种界面的扫描根）。

- **配方树（S5，2026-10-28 第一版写完，四次实机后作者回报全部通过）**：`mei_ui/recipe_tree/`（`screen` PushScreen 的界面类 / `node` 配置 / `script` 控制器 / `provider` 取数 /
  `controls/` 格子、画布、菜单、汇总 / `modules/` 纯逻辑 solver·summary·layout·choices）+ `mei_resource/ui/mei/recipe_tree.json`（命名空间 `MeiRecipeTree`）
  + `state/tree_prefs.py`（全局表 `mei_tree_prefs`：首选、当原料、工作方块显示哪个）。作者 10-28 定的全照做：自上而下、多格节点（工作方块 + 原料组，可折叠）、
  根单独一格、默认全展开、深度上限 256 / 节点上限 2000（第二次实机后从 64 / 400 提上来）、**点工作方块换类型 / 选显示的工作站，点原料格只在当前类型里换配方**、PC 与触屏都用菜单、对照背包只在汇总里、
  「查看配方页」关掉树回去翻到它、收藏一整棵（展开是原料快照）。现状、和预览的出入、实机记录在 `recipe_tree.md` §0。
  > 拖动照网易成就界面（`cut` → `dragpanel`（2I − V）→ 可拖的 `input_panel` contained，拖拽偏移就是视野）；画布里的格子 / 框 / 线是**动态建、不挂绑定**的控件池，
  > 内容由脚本直接写（只写变了的），一帧画不完先整块藏起；改了东西重新解算（provider 按物品缓存配方）后把刚点的那一格摆回原处、菜单跟着它重开。
  > 菜单里的配方：**10-28 起先渲染这个类型自己的配方预览**（配方 ui_script，和 tooltip 的 PREVIEW 同一套，`controls/preview.py`），不支持预览、
  > 建不出来、0.5 秒没建齐就用配方条（工作方块 + 原料 → 产物）。配方页脚本与 ItemPanel 认「当前主节点」，配方树**不动主节点的栈**，只在预览自己的
  > 代码里临时把主节点顶成配方树的壳（`TreeShell` + `context.Using`，绑定回调经 `ScopedBinder`）；点预览里的一格写灰字，不开配方页。
  > 第一次实机全是配方条（建的时候宿主、插槽藏着，引擎不建格子，§38）；第九轮改成 `Show` 只记下、下一帧 `Tick` 才建，建的时候宿主亮着、整个菜单框透明着
  > （框带 `propagate_alpha`），兜底的警告写卡在哪一步。第二次实机（10-29）作者「无问题」，又改了三样：设置开关「启用节点配方预览Tooltip」（切换时闪一下太晃眼）、
  > 标题合成一行「类型名 · 物品名」（用预览时就是预览自己的标题）、第二行灰字只剩「第 x/y 条」和附加状态（「首选」不写）。
  > 切换时的闪动评估了三个做法（`recipe_tree.md` §0.0.1：建议给配方页脚本加可选的 `SwapRecipe`，同一批格子换物品、一点都不透明），等作者点头。
  > 第三次实机（10-29）作者「配方树无问题」。
  > 入口：配方行的树按钮（工作台、熔炉的 JSON 打开了 `$tree_button_ignored`）、物品格触屏菜单「配方树」（查询那一段）、收藏栏的树收藏、快捷键 Y；
  > `OpenRecipeTree` 一律排到下一拍压栈（入口多在点击绑定的回调里）。收藏的树条目身份按根，同一个根再存就更新（`BookmarkManager.SaveTree`，`bookmarks.md` §4）。
  > 顺手修了：出栈后 `ProxyManager` 记的当前屏幕跟着回到栈顶（原先从工作台开配方树再关掉，plus 一直灰着）；强制兼容不往配方树里注入。
  > 回归位 `probe_recipe_tree.py`（纯逻辑）、`probe_recipe_tree_ui.py`（界面冒烟：控件路径都在 JSON 里、建控件、分帧画、菜单与全部动作、汇总、收藏的树条目与收藏栏排版）。
  > **第一次实机（10-28）作者「做的非常好」**，提了五条，同日改完（`recipe_tree.md` §0.1）：大树一开始偏下、拉不到剩下的 —— dragpanel / canvas 在 JSON 里写 `100%`、
  > 脚本用 `SetSize` 撑大，排版一刷新又回去（引擎结论 §28 同一类，推断），改成 JSON 写绝对尺寸 + `SetFullSize`，加了自检警告；顶栏、汇总的根格不画槽位底图
  > （格子模板的 `$cell_bg_ignored`）；格子上的标记颜色压暗（`TreeConst.BadgeColors` / `MultiColor`），试过圆点贴图、「·」字符，**第三次实机后定成 2×2 小方块、离边 2 像素**；
  > 左右箭头 12 → 14，**只在 `mei_common.json` 的 `menu_icon_button` 缺省里调**，两个菜单、汇总翻页排版时读回来。
  > 标记的意思、界面文字对照（都在 `constants/texts.py` 的 `TreeText`）、能调的东西在哪：`recipe_tree.md` §0.2 ~ §0.4。
  > **第二次实机（10-28）**：作者改了配方树的字 → 顶栏按钮、数量格、汇总页签、页码、菜单段名一列都改成**按字算宽**（stack_panel 里的用 `SetFullSize`），
  > 根物品名按剩下的宽截短；触屏菜单一段多于三个按钮时每行尽量一样多（普通格子的四个按钮排 2×2）；上限提到 256 层 / 2000 格。
  > **第三次实机（10-28）**：汇总右上的说明被 `SetPosition` 拽到左边（引擎结论 §39）→ 改成 JSON 里两个锚好的标签、脚本只切显隐；上标改回方块。
  > **汇总只剩四页**（作者 10-28：玩家要看的只有原料和副产物，中间物不单列）：所需原料 / 副产物 / 工具 / 缺少材料。
  > **副产物 = 照着树做完手里多出来的**：合成多出来的（要 1 根木棍、一次出 4 根，多 3 根）+ 配方的其他产出（`TreeRecipe.Byproducts`，
  > provider 认出这一格是哪个产出、别的产出格都算，不画在树上的也算）；概率产出按每次都出算、另记最多 / 平均（`Summary.Chance`），
  > 格子右上标 `TreeConst.ChanceColor` 的小方块。
  > **10-29 第十六轮（P1-1，实机通过）副产物拿去抵**：汇总改成**深度优先走一遍、带一个库存**（照 EMI，`modules/summary.py`，`recipe_tree.md` §0.5.1）——
  > 一格的余量与必出的其他产出等它的子树走完才进库存（喂不到自己子树，只喂之后的兄弟、表亲）；拿库存时标签原料哪个候选都行；概率产出不进库存；
  > 工具只算真做了的格子；和原先「合并再取整」一样省，同一物品不同配方也能抵 ⇒ 「逐个相加（上界）」与 `Pooled` 没了，右上只剩「部分结果」。
  > **背包扣减是同一套**（`shortfall`）：背包放进库存再走一遍，中间物也扣、根不扣；「缺少材料」页与「所需原料」页的红绿都看它，菜单写「背包里的中间材料抵掉 N」。

- **快捷键（2026-10-28 由调试按键改成正式；10-29 起是 MEI 自己的按键绑定，实机通过）**：`mei_ui/hotkeys/`（`keys` 键码与显示 / `table` 快捷键表 /
  `binds` 现在的键位与修饰键状态 / `capture` 录键 / `actions` 每个键做什么 / `manager` 收键、派发、录键）。作者 10-29 定：组合键，单键也移进来，
  照 NEI 学；**不再注册给引擎的自定义按键**。键位是设置项（`KeyBind`，key `hotkey_<id>`，值 `[修饰位, 主键]`），设置 MEI 分栏第二页「按键绑定」
  （标题「键盘与鼠标-快捷键绑定」）每个快捷键一行：**点一下开始录、按过的键都记下（修饰键按过就算）、再点一下保存**，单按 Delete 清除，撞键标红不拦。
  只收裸按键与滚轮（`main_sys` 转来）：修饰键自己记、切界面清掉（按住不连发，引擎结论 §42）；修饰键**精确匹配**；滚轮类要带修饰键，
  各界面的滚轮翻页先问 `binds.WheelTaken()`。**id 定了别改**（设置按它记改键）；**键表只在 `bookmarks.md` §12**。
  回归位 `probe_bookmark_ui.py` K-0 / K-16 ~ K-19、`probe_settings.py` G-9。
  > **`DebugMode` 10-29 删了**（P1-4：它最后只剩配方树顶栏的性能统计，配方树性能实机已通过；统计一并删掉）。要临时看数就临时加日志、问题清了删掉。
  > **按着修饰键悬停（10-29 第十六轮 P2-5，照 NEI，只在 PC 上，实机通过）**：`hotkeys/hover.py`，主节点每帧调 `Tick` ——
  > 按住 **Ctrl / Shift** 悬停在一条配方 / 配方树收藏的某一格上，这一条的全部格子着色（收藏格多了一条可暂停的绑定 `.item.highlight.visible`，
  > 值变了 `ItemsGrid.Wake` 再拉一遍；颜色在 `items_sidebar.json` 的 `bookmark_highlight`）；**只按住 Alt**，tooltip 列出光标下这一格能用的快捷键
  > （`actions.APPLIES` 判能不能做、键位跟着改键走、没绑的不列；借「只有标题」那一种，设置关着「启用高级Tooltip」不出，松开 Alt 收起）。
  > 回归位 `probe_bookmark_ui.py` K-19、`probe_tooltip.py` T-13。
  > **帮助亮着时原版悬停文字让位**（10-30 第三十一轮，作者报两段字叠在一起）：MEI 的格子 `HidesVanillaName` 一律给真（悬停文字绑定给空），
  > 写满后暂停了的 grid 在帮助亮 / 灭时各 `Wake` 一次；原版 / 别的模组的格子按焦点探针给的渲染器路径找那一格的 `hover_text`（`proxy/focus/search.nearby`：
  > 往上三层、每层往下四层、最多列 40 次）藏起来，帮助收起、光标换了格子、关界面时显回（`TooltipManager.__SyncHelp`，每帧对一次）。回归位 `probe_tooltip.py` T-14。

- **燃料页（2026-10-29 第十六轮 P2-11，实机通过）**：原版扩展的第三个类型 `fuel`（`extensions/vanilla/fuel/`，JSON `recipes/fuel.json`，命名空间 `MeiFuel`）：
  查一样东西的**用途**时它能当熔炉燃料就多一页「燃料」—— 燃料格 + 火焰 + 两行字「燃烧 N 秒」「可烧炼 N 个物品」（熔炉一个物品 10 秒）。
  燃料表与熔炉燃料格共用 `furnace/fuels.py`；方块类燃料引擎给 0 秒，按 tag 写原版的数（原木、木板 15 秒，木台阶 7.5 秒，`TAG_SECONDS`）。
  只答用途、能给全量（`CAN_ENUMERATE`）；配方没有产物，收藏时显示与找回用那样燃料。字在 `zh_CN.lang`（`mei.recipe.fuel.*`）。回归位 `probe_fuels.py` F-4。
- **原版的七种配方类型（S6，2026-10-29 第十八轮写、第十九轮重做配方页，待实机）**：作者定的文案 —— 高炉「高炉烧炼」、烟熏炉「烟熏炉烧炼」、营火「营火烘烤」、
  切石机「切制」、制图台「制图」、锻造台「锻造」、酿造台「药水酿造」；引擎给的样子由第十七轮的实机片段查清（引擎结论 §45）。专题 `docs/architecture/recipe_types.md`。
  > **熔炉家族**：`FurnaceSource(category_id)` 换 tag；高炉、烟熏炉用熔炉那一套（`MeiFurnace`，带燃料格；作者：过关）；灵魂营火并进营火当第二个工作站。
  > **切石机、制图台、锻造台**是无序配方的形状，解析走 `EngineRecipeSource.ParseShapelessParts`。
  > **第十九轮（作者看过第一版）**：共用的一进一出界面（`MeiSingle`）删了，**每个类型自己的命名空间、布局照原版界面**（`recipe_types.md` §2）——
  > 切石机照原版右半边、制图台照原版（原料 / 加号 / 附加原料一列、箭头、地图、箭头、26 的产物格）、锻造台三格挨着 + 原版箭头、
  > 酿造台照原版的图「上 1 下 3」（下三瓶写同一个绑定名前缀，**镜像格** `ItemPanel.AddMirror`；产物照 JEI 在右上）；
  > 进度条 / 箭头**用原版控件**（不带绑定的直接 `@原版命名空间.控件`，绑着容器进度的照原版写一份、换成自己的 clip 动画）；
  > **营火不要合成条**：原料、点着的营火模型、熟的 —— 纸娃娃（`netease_paper_doll_renderer`）渲染方块几何体模型（`campfire/model.py`：
  > 玩家脚下一格的调色板换成点着的营火 → `CombineBlockPaletteToGeometry` → `RenderBlockGeometryModel`），画不出来退回物品图标。
  > 制图台只有两条（复制 / 扩大 / 锁定写死在引擎里）；锻造纹饰的 `result` 是空的 → 产物格就是「物品」那一格的同一组候选（整页轮播同相位，一一对上），说明行写着。
  > **酿造**：药水的 aux ↔ 类型名直接映射（`brewing_stand/potions.py`，作者定）；按催化剂查不到 ⇒ 第一次用到时自己凑全表（每种药水类型、每种瓶子各按原料查一次，
  > 共 50 次）、自己建桶；混合配方的药水格是三种瓶子的同一种药水（同相位轮播）、换容配方按药水类型一条一条列（火药、龙息各 47 条）。
  > **物品变体**：原来是类型包导出 `VARIANTS`（三种瓶子 aux 1 ~ 46、空定位地图）；**10-30 第三十四轮起统一由原版扩展的创造栏表加**
  > （下面「创造栏的物品变体」），`VARIANTS` 退役；`AddItems` 遇到一模一样的跳过（10-29 加，热重载、扩展重装时会再加一遍）。
  > 配方页脚本的底子 `tools/pages.py`（`RecipePageScript`：格子路径的最后一段 = 绑定组前缀的最后一段、说明行、镜像格、重播动画）、
  > 本地化经 `utils/lang.localize`（第二十轮把原版扩展自己的 `tools/lang.py` 删了，下面「架构关键点 · 界面文字」）。回归位 `probe_recipe_types.py`（R-1 ~ R-12，含新类型的 Id 金标准、镜像格、营火模型）。
  > **第二十轮（作者实机后）**：作者自己调了制图台（去掉两个箭头、宽 148）、酿造台（高 68，燃料 / 催化剂 / 产物三格的坐标）与营火模型的参数
  > （`campfire/model.py` 的 `RENDER`），wrapper 与配方行跟着对齐；配方页脚本上的 `TYPE` 删了（不读：高炉、烟熏炉用的是熔炉的脚本，写在脚本上的类型名对不上）。
- **三种模式：普通 / 工具 / 作弊（2026-10-30 第二十九轮写完，离线探针全过，待实机）**：专题 `docs/architecture/modes.md`。
  > **按钮**：收藏栏顶栏最左边（JSON 里 `setting` 改名 `mode`，图标 `mei_common.btn_mode`，扳手）点一下轮换普通 → 工具 → 作弊（`ModeManager.Cycle`），
  > 颜色 `ModeConst.Colors`（普通是图标平时的灰、工具黄、作弊红），每个界面的 `ToolHost.Update` 按 `ModeManager.Revision` 变了才染。模式全局存在 prefs（`mode`），关界面不复位。
  > **作弊**：每次开界面问服务端（`mei:cheat_access`），没有权限而存着作弊 → 退回普通并存盘；「不知道」（超时）不当没有。点格子给物品（`mei:cheat_give`）：
  > 触屏一组；PC 左键一组、右键一个；一组 = 最大堆叠（引擎给 0 按 64），背包放不下掉在脚下。**服务端只信引擎给的发起者**：`Channel.OnRequest` 先认 `__id__`、
  > `HandlerContext.Trusted`，`CheatService` 再查 `GetPlayerOperation() == 2`（`network/protocol/cheat.py`）。
  > **工具**：点格子拿起（数量 1 的 ItemStack，配方收藏、配方树收藏给它们显示的那样），PC 上 follows_cursor 的宿主带着走、触屏摆在格子上抬 6，都是 24（格子里 18）；
  > 再点一下：别的模组登记的放置目标（`ctx.UI.Drops`，`modes/drops.py`）→ 回调（别名或路径, ItemStack）；MEI 别的物品格 → 换着拿；别处 → 放下。
  > `mei_main.json` 两个根里的 `mei_tool`（`tool_layer`：捕获层 96、两个物品 40 —— 装物品渲染器，97、78 都画不出来，引擎结论 §31）**显隐全走绑定**（`#mei.tool.*`），开 / 关界面脚本写回藏着（引擎结论 §22）。
  > **接在哪**：`ItemsGrid` 的左右键派发、配方页的 `_DispatchSlotClick`（配方树菜单的预览也走它）先问 `ModeManager.Intercept`；触屏划进格子在工具 / 作弊模式不开菜单；
  > 配方树的格子作弊时给物品不开菜单。扩展卸载时装配器兜底撤掉记在它名下的放置目标。回归位 `probe_modes.py`（M-1 ~ M-8）。
  > **第三十轮**：颜色加深（工具 `(0.86, 0.6, 0)`、作弊 `(0.8, 0.13, 0.13)`）；悬停文字三种（`ModeText`，`ore_style_button` 的悬停态多了可替换的 `$button_hover_extra_control`，
  > 模式按钮换 `mei_common.mode_hover_tip`、字绑 `ModeConst.HoverBinding`）；放置目标可以要点的位置（`point=True`）；
  > 蔚蓝合成样板接上工具模式（蔚蓝仓 `external/mei/crafting_template.py`，不打补丁、复用蔚蓝自己的上传请求，`modes.md` §9）；
  > 对外加 **`ctx.UI.Actions`**（开配方页 / 用途 / 配方树、`ItemAt` / `ItemUnderCursor`、`Mode` / `CheatAllowed`、收藏），`ctx.Const` 加 `ModeConst` / `ItemsBrowserPath`。
  > **第三十一轮**：上一轮为 PushScreen 开的界面加的注入挂载（`Mount = "inject"`）**删了** —— 作者：只要是 PushScreen 就挂得上代理（SDK 压栈时按全名
  > `uiManager.get_pushed_screen` 取界面节点），MEI 纯靠代理兼容；`ctx.UI.Screens.Register` 照常登记就行。
  > 新接口 **`ctx.UI.Transfers`**（按界面登记的配方转移，`recipe_details/modules/screen_transfers.py`）：这个界面开着时，配方页上登记的那几类配方的 +
  > 不搬材料，而是回调 `callback(Recipe)`，写成了 MEI 关掉配方页；`accepts(Recipe)` 说收不收（不收的灰掉，`CraftableCache.Accepts` 按 Recipe.Id 缓存）；
  > 同一个界面、同一个类型后登记的优先，比类型上的转移策略（`SetTransferPolicy`）优先。蔚蓝合成样板接上它（工作台配方的 + 写进样板）；
  > 另找了蔚蓝里四个「选一样物品」的界面接上工具模式（蔚蓝仓 `external/mei/selectors.py`）：电动机件加工台（选产物是它的配方）、冷冻机（切到产物是它的那一档）、
  > 物品分流器（点到哪一行换哪一行）、连锁挖矿设置（方块加进列表，界面这里登记）。流体分流器不接（工具模式拿不起流体）。回归位 `probe_modes.py` M-13、M-17，
  > `probe_skyblue_ext.py` S-14 / S-15。
  > **第三十六轮**：蔚蓝侧把工具模式那一套（`selectors.py`、样板的两个放置目标）删了，等 ItemRenderer 标准重写（`modes.md` §11）；样板的 + 那一套第三十六轮定可以删（`quick_craft.md` §10.7）。
  > **第三十七轮**：作者定继续用 `ctx.UI.Drops`（ItemRenderer 标准不做）；放置目标加了 accepts、回调返回 False / 一句话是不收（`modes.md` §12）；蔚蓝的工具模式按改进后的写法恢复、样板改用转移处理器、机件加工台接上配方转移（蔚蓝仓 `external/mei/`，`docs/thirdparty/skybluetech.md` §8.16）。
- **物品栏筛选（2026-10-30 第二十九轮骨架，第三十轮照排版 D 写完菜单，待实机）**：`registry/filters.py`（`ItemFilters`：内置九项筛选、八种排序，`Apply` 先加、再筛、再排、None 排最后、同值稳定；
  **第三十五轮加了「隐藏物品」**（作者：添加而不是减法）—— **加法的筛选**（`ItemFilter.Additive`，`AddFilter(..., additive=True)` 也能登记）：选了不把表筛小，
  而是把平时不显示的物品里它认的加进来，别的筛选照样再筛；物品栏的候选这时连藏着的一起拿（`ItemsBrowserScript.ItemSource` → `GetBrowsableItems(include_hidden)` /
  `ItemSearchIndex.Search(…, include_hidden)`），排在菜单最后（order 1000）；
  `AddFilter` / `AddSort` 简便接口）+ prefs 的 `item_filters` / `item_sort` + `ItemsBrowserScript.ApplyItemView`（先搜、再筛、再排）/ `RefreshItemView`（改了当场重排）
  + 原版扩展登记「燃料」「燃烧时长」（用 `furnace/fuels.py`）+ 对外 `ctx.Registry.ItemFilters` / `ItemFilter` / `ItemSort`（`docs/modding/04-items.md` §4）。
  文案照作者给的：防具 武器 食物 燃料 有耐久 可附魔 已附魔 不可堆叠 模组物品（顺序同）。扩展都卸了筛选表回到只有内置的（`ExtensionLoader.Shutdown`）。
  **菜单**（`mei_ui/filters/`：`state` / `layout` 纯计算、`menu` 的 `FilterMenu`，主节点 `main.Filters`；`mei_main.json` 的 `filter_menu` / `filter_chips`）：
  搜索框右边的 `filter` 按钮开 / 关；purpleBorder 框里标签块（按下就选中）+ 排序步进器 + 升 / 降 + 清除 / 确定；标签区是原版 `common.scrolling_panel`、**超过 8 行才滚**；
  改了就存、物品栏当场重排；选了东西按钮图标染蓝；物品栏藏起来时跟着关；开 / 关界面都写回藏着。设计在 `modes.md` §8。回归位 `probe_modes.py` M-9 ~ M-12。
- **自适应的生效条件（2026-10-30 第三十轮）**：`core/adaptive/rules.py` 精简成一个 `holds(condition, get, memo)` —— 避让目标看得见还不够时由代码说了算
  （`condition(get) -> bool`，`get(路径)` 按 RootPath 取控件）；条件从代理参数 **`Conditions`** 来（`{路径: 条件}`，`core/params.adaptive_conditions`），
  或 `RegisterAdaptiveControl(..., condition=...)`。原版配方书的条件挪进原版扩展（`extensions/vanilla/screens.py` 的 `recipe_book_shown`），
  核心层原来写死的字符串规则、路径前缀、静态缓存都删了（`settings.md` §6.3）。回归位 `probe_modes.py` M-15。
- **创造栏的物品变体（2026-10-30 第三十四轮，离线探针全过，待实机）**：物品表按 id 注册、每个 id 只有 aux 0，带附加值、带 userData 的创造栏物品原来要手写。
  作者定：拿一遍游戏的创造栏目录（id + aux），带 userData 的照一份现成的创造栏物品表补全，写进原版扩展，以后只盯着物品更新（`item_model.md` §9.8）。
  `extensions/vanilla/creative/`：`table.py` 由 `debug/scripts/gen_creative_table.py --emit` 从游戏的 `behavior_packs/vanilla/item_catalog/crafting_item_catalog.json` 生成
  （3.9：225 样 —— 药箭、谜之炖菜、山羊角、空定位地图、三种药水、不祥之瓶、床，**不要手改**）；`families.py` 手写引擎自己往创造栏加的四族（游戏目录里没有来源）：
  旗帜 15 色 + 不祥旗帜、附魔书 41 本（每种最高级，`ENCHANT_MAX_LEVEL` 是唯一手写的数）、烟花火箭 17 支、烟火之星 16 颗，userData 一律带类型的写法；
  `build()` 每个 (id, aux) 问一次引擎（`ItemFactory.LoadInfo`，问到的信息交给 `ItemSpec`、注册时不问第二次），不认识的跳过（表与游戏版本对不上不出错；
  附魔 id 不小于 `EnchantType.NumEnchantments` 的不收）；装配时记一行 `[MEI/items] 创造栏的变体: 加了 N 个…`（全认识是 315）。
  > 目录里只有带附加值那一样的六种（活塞 / 黏性活塞 :1、发射器 / 投掷器 :3、两种蘑菇方块 :14 —— 拿方块朝向、菌盖当图标）把 aux 0 藏起来；
  > 附魔书、烟花火箭、烟火之星的**原件**（不带 userData 的那一样）藏起来 —— 新的 `ItemManager.SetPlainHidden`：只藏 `Item.IsPlain` 的那一样
  > （`SetHidden` 按 (id, aux) 藏，变体和原件同一个键，会一起藏掉）。酿造台、制图台各自的 `VARIANTS` 退役（物品变体只有这一处）。
  > 物品栏筛选「已附魔」也认 userData 里存着的附魔（附魔书的 `ench`；`IsEnchanted` 只看附魔表，没动）。
  > **换游戏版本**：先不带 `--emit` 跑生成器，它对比现在的 `table.py`、`.lang` 里的附魔种数（3.10 多了突进 `enchantment.lunge`）、目录里没有的新物品组，再 `--emit`。
  > 回归位 `probe_creative.py`（C-1 ~ C-6，含生成器重跑与 `table.py` 一字不差）、`probe_recipe_types.py` R-3 / R-5 / R-9、`probe_samples.py` E-3。

- **物品分组（2026-10-30 第三十九轮，离线探针全过，待实机）**：作者让照补全的物品表把原版物品按同类型分组（镐一组、剑一组、锭一组、粗矿一组……）。
  三个来源（`item_model.md` §10）：创造栏的物品组 81 个（`creative/table.py` 的 `GROUPS`，和带附加值的变体同一次生成）、引擎自己加的四族（`families.GROUPS`）、
  MEI 补的同类组 20 个（`creative/groups.py` 的 `EXTRA`：锭、粗矿、粒、粗矿块、矿物块、桶、火把、蛋、蛙明灯、紫水晶、石英块、海晶石、下界砖块、树脂块、砖、冰、泥土、苔藓、藤蔓、钓竿；
  同一类、至少三样，名字在 `.lang` 的 `mei.group.*`）。分组按 id 记（变体跟着 id 进组）；`creative.item_groups` 合并，一个 id 只进第一个组。
  原版扩展装配时登记、卸载时撤；组表多记加入的顺序（`ItemOrganizer.GetGroupOrder`），物品栏没选排序时组里照它排（木 → 石 → 铜 → 铁 → 金 → 钻石 → 下界合金）。
  **搜索时照旧**（作者定）：搜到的物品所在的组照样折成组头、组里别的跟着；同一个 id 在几个组里归最后登记的组、不再在别的组里重复出现。
  换版本时生成器核对 `groups.py` 的 id 还在、没和创造栏的组重。设置「启用物品分组」（默认开）关掉时物品栏平铺（上面「设置系统」）。
  > **第三方并进原版的组**（作者让给蔚蓝也分组，「包括一些和 vanilla 一起的」，`item_model.md` §10.5）：组的键就是约定（`minecraft:itemGroup.name.*`、`mei:group.*`），在就加、不在就建；原版的组在原版扩展的 OnRegister 里建，第三方**在 OnReady 加**；卸载只撤自己加的 —— 新接口 `ItemOrganizer.RemoveGroupItem`（探测），自己建的共用组撤空了再撤组。原版没有、几个模组都可能有的用通用键 `mei:group.dust`（「粉」，`.lang` 在 MEI，MEI 自己不建）。
  > **蔚蓝**（蔚蓝仓 `external/mei/groups.py`，§10.6）：16 个并进原版 / 共用的组（锭、粗矿、粗矿块、矿石、矿物块、桶、五种工具、四种盔甲、粉）+ 23 个照它创造栏分的自己的组（机器七类、金属板、线缆……多方块结构一个结构一组；成员、顺序、组名照创造栏）；两样一组的（扇叶、海水蓄水池、矿锤）不进组。
  回归位 `probe_creative.py` C-6 / C-7、`probe_items.py` I-12、`probe_samples.py` E-3、`probe_settings.py`、`probe_skyblue_ext.py` S-17。

### 历史断裂（已全部修复，勿再当作现状）

S0 止血的四个必炸点 —— `Recipe` 子类缺失导致 import 链断裂、`MeiItem` 构造缺 `self`、
输出槽 `get_stacks()` 协议不存在、熔炉解析被 `isinstance(..., str)` 打空 ——
**2026-08-21 已修复并游戏内验收**，逐条经过见 `docs/migration/tasks.md`。

> **熔炉燃料的来回**（别再照旧说法理解）：2026-08-22 改成 `mei:fuels` tag + 分帧扫描，
> **2026-09-01 撤回** —— 当时的理由「点熔炉产物会击穿全表惰性 `Info`」被证伪
> （物品注册时 `__AppendToIndex` 已读过每个物品的 `Info`），现在燃料是**字面展开**
> （`furnace/source.py:80`）。`TagConst.Fuels` 因此零引用（第三十九轮连同组表里的标签记录一起删了）。
> ⚠ 撤回的只是**性能**理由；tag 折叠还有一个**身份**理由没被证伪：catalysts 计入
> `Recipe.Id`，字面展开的燃料让**每条熔炉配方的 Id 都绑着当前全部燃料物品**，
> 装卸任何带燃料的模组都会让它们全部变 Id。见下「路线图」的上线前硬门槛。
> **2026-10-29 作者定了最后的做法：燃料不进配方本身**（驱动机器的东西不是配方的内容 —— 能量、燃料都一样，第三方的机器也照这个规矩），
> 配方页的燃料格问熔炉扩展的燃料表（`extensions/vanilla/furnace/fuels.py`）：`FuelDuration > 0` ∪ `minecraft:logs_that_burn` ∪ 木板 / 木台阶去掉下界木，
> 原先只看已缓存的 `Info.Tags`；**第三十九轮起按 tag 认走 `TagLookup`**（`registry/tags.py`，3.10 问引擎的 `LookupItemsByItemTag`，模组注册进这几个 tag 的木头也认）。**同日写完**，`FurnaceRecipe` 不带燃料，熔炉配方的 Id 不再绑燃料。
>
> 通用规则仍然成立：`Ingredient.to_canonical()` 对 tag **折叠不展开**
> （tag 成员是异步到的，展开会让同一条配方前后算出两个 Id，见 `tasks_s2b.md` §2）。

### 待偿还（规范违例，非阻塞）

> 完整清单（含 UI 层与持久化层的历史遗留）在 `docs/architecture/` 四篇的「现状盘点」节，
> 此处只留跨议题的通用违例。

- **加新配方类型的界面时继承 `RecipeUIScript`**
  （`ui_script/mei_ui/recipe_details/modules/script_base.py`，绑定器耦合的实现层），
  **不是 `BaseRecipeUIScript`**（`common/classes/base.py` 里的纯契约，零 UI 依赖）。
  > 反向边原有 7 条：6 条在 `common/recipes/`（装错位置的扩展包）——
  > **该包已于 2026-09-02 整体迁入 `extensions/vanilla/`，这 6 条随之消失**；
  > 剩下那 1 条 `registry → bridge`（前置桥）**随 2026-10-27 与前置解耦消失**。
- ~~一处「层归属本身错了」~~（`structure.md` §1.2）：`mei_mod/eternia/`（前置桥）名义在装配层、
  却被 registry 反向 import —— **2026-10-27 随解耦整个删掉**，拼音搜索用的库在 `libs/`（最底层，谁都能 import）。
  > 另一处（`common/recipes/` 装错位置）**已于 2026-09-02 随 vanilla 扩展化偿还**。
- **包门面急加载把引擎拖进纯逻辑层**（同一类债，已遇到三次）：
  `utils/__init__.py`（S1 修）、`state/storage/__init__.py`（S1.5 建时就避开）、
  **`registry/__init__.py`（仍欠着，4 个顶层 import）**。它使 registry 下任何纯逻辑模块
  都无法脱离客户端 import —— 清 `registry` 门面要动很多消费方，属 S7 级别，见 `tasks_s2a.md` §9.4。
  （当初的受害者 `registry/index.py` 已随 2026-09-02 的索引回退删除，但债还在。）
  ⇒ **新建包门面时先问一句：这个 `__init__` 会不会把引擎拖给只想用纯逻辑的人。**
- ~~**命名违例**、**老式类**~~ —— **10-29 第十六轮偿还**（P3-1）：`ui_script/mainUINode.py` 是没人用的空壳（真正的主节点是 `mei_ui/core/node.py`），删了；
  `proxy/customUI/` 改名 `proxy/custom_ui/`（代理类路径 `CUSTOM_PROXY_SCRIPT` 跟着改）；`organizer.py` 三个、`__ProxyManager`、`LogPatcher` 都写成 `(object)`。
  守它们的是 `probe_cleanup.py`（全树没有老式类、文件 / 目录名都是蛇形，`modMain.py` 是网易要求的入口名除外）。
- **扩展系统**：已完整落地并经第三方实机验证（蔚蓝科技接入 20 台机器，2026-09）。
  跨 addon `CreateComponent` **不需要 `modRequire`**（蔚蓝没声明也能用 —— 软依赖成立）；
  `API_VERSION = 2`，`RegisterCategory` / `RegisterSource` 已取代 v1 的 `RegisterProcessor`。
  **10-29 第十六轮（P3-3）**：E3 反注册补齐（`ctx.UI.Slots.Unregister`、`ItemOrganizer.RemoveGroup / RemoveTag / RemoveCategory`；物品与隐藏表每次进世界重建、不用撤）
  + 离线热重载验证；E4 样例工程 `docs/samples/mei_sample/`（一个配方类型「研磨」，不 import MEI、每次进世界注册同一个类）；
  §9：服务端扩展面先不做、每个扩展一个 ctx 与「传类」都已落地，**第三方不能覆盖别人的类型**（重复注册拒掉、补了警告日志，作者待定）。
  回归位 `probe_samples.py`（样例与原版扩展装上 → 卸下回到原样 → 再装上不多一份）。剩余见 `docs/architecture/extensions.md` §8 / §9。
  > **2026-10-25 蔚蓝 next 框架适配**（蔚蓝仓 `mei-next`，基于 `origin/new-frame-test`）：
  > 扩展取数改为**只走蔚蓝正式导出 `common.export.*`**，内部模块一处不碰
  > （旧写法 `machinery.MACERATOR` 在 next 里已是 `machinery.Machinery.MACERATOR`，
  > 20 台机器的 `Build()` 全部 AttributeError）。MEI 侧**零改动**、`API_VERSION` 不变。
  > 经过、导出缺口与两处蔚蓝侧问题见本地文档 `docs/thirdparty/skybluetech.md` §8（不入库）；
  > **逐台 review 表**（已接 20 台的入口 / 代表配方 / 预期，加未接的新机器）在其 §8.8。
- **已偿还，勿再当作现状**：`contract → ui` / `state → ui` 依赖违例（S1b）、
  `state/local_data.py` 模块级引擎调用（S1.5-P0，文件已删）、
  `utils/__init__.py` 急加载（S1）。回归分别由 `probe_layering.py` 与
  `probe_types_offline.py` 守护 —— 后者刻意只桩 `mod_log`、**不桩 `mod.*`**，
  `types/` 若再被拖回客户端依赖会立刻失败。
  （各处顶层的 `ViewBinder = clientApi.GetViewBinderCls()` 是取类，不算违例。）
- ~~`utils/codec.py` 的 `Codec._register_defaults()` 空实现~~ —— **10-29 偿还**：照 `persistence.md` §3.3 删了空钩子、留着 Codec 本体。
- **三处「原版专属物残留在核心层」**（2026-09-02 扫出；三处都偿还了，② 第三十九轮）：
  ① ~~`registry/items.py` 的 `_SPAWN_EGG_IDS`~~ —— **10-29 删了**（零使用的死代码）；
  ② ~~`constants/codes.py` 的 `TagConst.Fuels`（`"mei:fuels"`）~~ —— **第三十九轮删了**（连同组表里的标签记录；还没正式发布，不升 `API_VERSION`）；
  ③ ~~`constants/proxy.py` 的 `ProxyScreenDefs`（23 个原版屏幕）~~ —— **2026-10-28 已偿还**（作者：按规范内置进原版扩展）：
  搬到 `extensions/vanilla/screens.py`，经新门面 `ctx.UI.Screens` 登记。
  > 配方子类（`ShapedRecipe` 等）已于同日迁出，见 `docs/migration/tasks_s4.md` §8.5。
- **局部工具函数重复**（2026-09-02 全仓扫描，清单与处置见 `docs/architecture/structure.md` §5.2）：
  去重与 `Recipe.Id` 取值已归口 `utils/sequence.py`；**仍欠三条**，其中
  稳定 JSON 序列化原本写了三遍，**已归口 `utils/stablehash.py::stable_text`**，
  金标准 Id 钉在 `probe_identity.py` 的 `GOLDEN_IDS`（它变红即意味着有人正在
  作废所有玩家的置顶与配方书签，**先查改动意图，不要改常量**）。
  另两条 **10-29 第十六轮也偿还了**：`copy()` 样板改用 `utils/slots.py::copy_slots`（按 `__slots__` 复制，同一个类、新字段自动带上，
  深浅按名单；`ItemStack` 照旧走构造 —— 扩展的兄弟类靠它保住 KIND）；绑定名拼接归口 `utils/bindname.py::make_binding_name`。
  > 新写小工具前先在 `utils/` 找一遍：这类重复是"就近写在文件里、写第二遍时不知道第一遍在哪"。
  > 家在 `utils/` 的**纯函数模块**，不是 `utils/utilities.py`（那个顶层拉引擎）。

### 路线图

**权威在 `docs/architecture/README.md` §3 的 S0~S6 阶段表**（含各阶段任务书链接与验收状态），
此处只记当前位置：

> **2026-10-28 起：接下来做什么以 `docs/architecture/README.md` §8 的「待办 P 列表」为准**（作者让把剩下的计划全部评估一遍后重排，评估稿待作者确认）：
> P0 组合键实机验证、配方脚本宿主统一；P1 配方树副产物抵扣 + 背包扣减、组合键方案、上线前的 `Recipe.Id` 三件事、删 `DebugMode`；
> P2 S4 工作站视图、配方树的预览与悬停、收藏的几样；P3 清理；S6、快捷合成、蔚蓝扩展搁置；U0 / U3 / U5 原方案建议作废。
> **10-28 第八轮**：P0 两项写完（修饰键探针 `hotkeys/keyprobe.py` 待实机、验完删；配方页不在绑定回调里建脚本，`recipe_details/modules/host.py`），
> 配方树菜单渲染配方预览（原 P2-2，作者提前）也写完；作者定 P0-1 通过就自制按键绑定（含组合键，顺带补上移 / 下移等缺的快捷键）。
> **10-28 第九轮**：P0-1 实机通过（修饰键收得到、按住不连发，中文输入法吃掉的键报 229；探针删了），录键照游戏的做法「点一下开始录、按过的键都记下、
> 再点一下保存」（`bookmarks.md` §12.3）；P0-2 实机正常，修了动作按钮推状态的时序（日志刷屏 + 推不上去也记成推过）；配方树菜单的预览第一次实机
> 全是兜底 —— 建的时候宿主、插槽藏着，改了，待第二次实机。
> **10-29 第十轮**：配方页**无限闪烁**（第九轮「推上去才记推过」让置顶的回灌漏了过去 → 重排 → 重建 → 再推 → 再回灌）—— 改回先记再推（推不上去撤回），
> 回声再加一道「上报值等于业务状态就吞」（引擎结论 §10）；配方树：设置开关、标题一行、灰字精简，闪动评估了没改；**自制按键绑定写完**（上面「快捷键」，待实机）；
> Recipe.Id：给了作者一段游戏里动态执行的查询片段（`debug/ingame/recipe_id_probe.py`，本地不入库），等结果再定 P1-3。
> **10-29 第十一轮（只评估）**：作者实机：配方页闪烁修好了、配方树无问题、按键绑定无问题（设置界面里也收得到按键）。Recipe.Id 的查询结果回来了
> （引擎结论 §43）：`GetRecipesByResult` **不给配方 identifier** ⇒ 硬门槛 #1 关掉，`Recipe.Id` 继续用内容哈希；接下来是 #2（燃料折叠成 `mei:fuels`）
> 与 #4（list 原料按公共 tag 折叠，先等 `GetItemTags` 的实机结果，片段 `debug/ingame/item_tags_probe.py`），见 `README.md` §8 P1-3；
> 另查出原版的重复 / 被包含的配方（P3-5）。
> **10-29 第十二轮（只评估）**：作者定燃料不进配方本身、也不用存（驱动机器的东西不是配方的内容），可以用 tag 补燃料、不要额外索引，3.10 起有原生的 tag 查找
> —— 写进了 P1-3 #2（`FurnaceRecipe` 不带燃料、燃料格问 `furnace/fuels.py`）；片段 `item_tags_probe.py` 加了燃料那一组，一次看两件事；
> 顺带查出熔炉解析的两处缺口（输出数量大于 1 时 output 是 dict、没认；input 是 list 时只取第一个）。
> **10-29 第十三轮（只评估）**：tag 片段的结果回来了（引擎结论 §44）：燃料表用 `FuelDuration > 0` ∪ `logs_that_burn` ∪ 木板 / 木台阶去掉下界木，
> 楼梯、工作台这些没 tag 的先缺着（3.10 再换原生 tag 查找）；list 原料按公共 tag 折叠可行（木板 → `minecraft:planks`、煤 → `minecraft:coals`），
> 不调引擎。P1-3 的几件都定了，待作者点头开工（`README.md` §8）。
> **10-29 第十四轮**：作者「动工」—— P1-3 写完、待实机：熔炉配方不带燃料（燃料格问 `furnace/fuels.py`）、list 原料按公共 tag 折叠（`tools/parser.py`）、
> 熔炉 list 形态的 input 改成多候选、output 是 dict（数量大于 1）也认；**Id 定义冻结**。熔炉配方、带木板 / 煤这类 list 原料的配方 Id 都变了一次。
> 作者另说下一轮列待办表。
> **10-29 第十五轮**：列待办（`README.md` §8 顶上的「10-29 现状一览」）。
> **10-29 第十六轮**：作者「这轮做 P1-1 P1-4 P2-11 P2-5 P3-1 P3-3」—— 全部写完、离线探针全过，**实机通过**（作者「本轮无问题」）：配方树副产物抵扣 + 背包扣减（P1-1）、
> 删 `DebugMode`（P1-4）、燃料页（P2-11）、Ctrl / Shift 高亮同一条配方收藏 + Alt 快捷键帮助（P2-5）、待偿还清掉六样（P3-1）、
> 扩展的反注册补齐 + 热重载验证 + 样例工程（P3-3；§9-3「不许覆盖别人的类型」先这么定，作者待定）。
> **10-29 第十七轮（只出摸底片段，不开工）**：作者「本轮无问题」—— 第十六轮的六项实机通过。接着开 **S6 新配方类型**（作者定的七种与界面文案：
> 酿造台「药水酿造」（混合酿造、换容酿造）、锻造台「锻造」（锻造转换、锻造纹饰）、切石机「切制」、制图台「制图」、高炉「高炉烧炼」、烟熏炉「烟熏炉烧炼」、
> 营火「营火烘烤」；引擎配方 tag：`brewing_stand` / `smithing_table` / `stonecutter` / `cartography_table` / `blast_furnace` / `smoker` / `campfire`）。
> 先给了一段游戏里动态执行的片段 `debug/ingame/recipe_types_probe.py`（本地不入库，输出带 `[MEI/rt]`），等结果下一轮直接写。
> 查文档得到的（片段核实）：**酿造的查询不认 tag 与 aux，药水要传类型全名** `minecraft:potion_type:<名字>`（SDK `GetRecipesByResult` / `GetRecipesByInput` 备注）
> ⇒ 药水 aux → 类型名要自己**直接映射**（作者：别的模组都这么做）；混合配方是 `input / reagent / output` 三个药水类型 / 物品，换容配方是
> `minecraft:potion → minecraft:splash_potion` 这类容器；锻造转换 `template / base / addition / result`，纹饰没有 `result`；切石机、制图台是无序配方
> （`ingredients / result`，带 `data`）；高炉、烟熏炉、营火、灵魂营火都是熔炉配方换 tag。MEI 的物品表每个 id 只有 aux 0（`RegItemFromIdList`），
> 药水的各种 aux 多半不在表里，要在扩展里加变体 —— 片段第 ① 节核实。
> **10-29 第十八轮**：作者贴回片段结果（引擎结论 §45）、「开始实现」—— **S6 七种全部写完、离线探针全过，待实机**（上面「已落地」的 S6 一条、
> `recipe_types.md`）。药水 aux 直接映射；酿造按催化剂查不到，自己凑全表建桶；`AddItems` 加了去重。
> **10-29 第十九轮**：作者看过第一版：「不该复用 single 这种东西，这类控件应该删除；除了两个炉，新加的配方 UI 都不行；UI 都应该学原版 UI 的布局，
> 进度条也应该复用原版 UI 的（不能复用的写在自己的命名空间下）；酿造台上 1 下 3（下三是同一个物品，可以用相同的绑定名）；营火不要合成条，
> 改用动态渲染营火的着火状态模型」—— 五个配方页照原版界面重做、`MeiSingle` 删掉、镜像格、营火模型，离线探针全过，**待实机**（`recipe_types.md` §2 / §8）。
> **10-29 第二十轮**：作者实机报了三个以前没有的 bug 与一处文案（营火模型的参数作者自己改好了）：① **翻页闪** —— 10-28 P0-2 把接配方页脚本推到下一帧的 `Tick`，
> 中间那一帧格子的绑定找不到这一行、回缺省值（藏起来）；改回作者原来的设计，在 `#visible` 回调里当场接（`host.attach_script` 照样兜住异常）；
> ② **TypeTab 与内容不是一个类型**（看下界合金装备时点下界合金锭：TypeTab 停在锻造台、内容是工作台）—— 导航按旧的类型选、内容显示第一个；
> `SetRecipesResult` 先定显示哪个类型，导航跟着它选；③ **工作站少一两个、普遍是第一个** —— 行列数变了引擎重建格子，重建之前建的面板把图标设在旧控件上
> （引擎结论 §46）：工作站没变就不清、不推，`ItemsGrid` 推完行列数后第 2、3 轮拉到某一格时补画图标；④ **配方树里一条高炉配方两个类型名**
> （菜单「高炉烧炼」、预览「熔炉」）—— 本地化文字收成一处（`utils/lang.localize`，类型名 `RecipeManager.GetDisplayText`；tooltip、配方树、快捷键帮助、
> 设置页、原版扩展各自的表都删了，作者：不要两个地方两个文案表），节点菜单先看正在用的那条的类型，换到只有递归配方的类型不记并提示；
> 代码里没走出预览写「熔炉」的那条路，再出现要截图。离线探针全过（蔚蓝 PowerBar 两项除外，另一个 agent 在改蔚蓝），**待实机**。
> **10-29 第二十一轮**：作者实机「其他没问题了」—— 翻页不闪、TypeTab、配方树的类型名都好了；剩**熔炉 → 高炉（工作站 2 格 → 1 格）高炉那一格空着**：
> 格子重建得比补画的第 2、3 轮晚（引擎结论 §46）。改成收引擎的 `GridComponentSizeChangedClientEvent`（格子重新排列了）当场重设图标、
> 核对窗口里 `GetUiItem` 读回来不对才设、工作站 grid 不暂停绑定并核对 30 轮。离线探针全过，**待实机**。

> **2026-10-27 起：MEI Tooltip**（`tooltip.md`，作者定分三轮）—— 第一轮（控件、配方预览的原生 content 机制、管理器、调试键 T）
> 第十一次实机完全成功；第二轮（PC / 移动端两个宿主、桌面悬停立刻出、原版名让位、多候选格重写、标题跟着当前候选）第十二次实机基本可用，
> 作者提的三处（第一次停上去要动一下才出、闪现滞后、配方 JSON 规范）同日改了两版（最后是透明着建、所有配方绝对尺寸 + 预览只建 content）；
> 第十三次实机查出 follows_cursor 被第三轮的 `SetPosition` 弄失效、每次指向配方建两个控件 → 宿主一律不碰、一次只建一个控件、收起不删
> （同一种复用、换一种先删再建）；第十四次实机作者「这轮效果非常好」，剩切换配方时屏幕右下角闪一下 → PC 宿主一直亮着、只藏 frame，
> 离光标多远挪进 JSON（`cursor_gap`）；第十五次实机作者「完成」（`cursor_gap` 调成 `[11, 0]`），加了设置「启用高级Tooltip」，待第十六次实机；
> 第三轮（移动端二级菜单）出了方案、作者定了八条（`tooltip.md` §6.8），M1 菜单壳子第十七次实机基本没问题；只有标题时改写完整悬停文字、
> 多候选格的标题同一个错一并改了；之后作者「M2M3 一起做」：收藏格的全部动作 + 排序 + 二次确认 + 跟着这一条走、多候选格换候选，
> 落位改成按区域、贴边算上按钮区，接受物品列表加灰色说明行与「+N」格，**第十八次实机通过**（作者 10-28 回报）；
> 菜单样式出了一版 HTML 预览，作者「非常满意新排版」，M4 照它改成一个框（顶栏种类 + 关闭、分段、步进器、红字删除类，按钮缩小到 14 高）；
> 作者看过实机又改了第二版（分隔线补 fill、宽度按内容收、扁平按钮贴图、关闭换小 x、候选换左右箭头），加了设置「触控tooltip是否沿对面侧显示」，
> 同样第十八次实机通过。
> 同一天：ui 下的 JSON 改成蛇形文件名（`items_browser.json` 等，命名空间不动），删了 grid 尺寸冗余代码、轮盘测试控件与旧的触屏提示残骸。
> 作者看过第二版：「本轮很完美」；接着把小 x 调成 14×14、往上 2（大小与偏移只在 JSON 里调，脚本排版时读回来），
> 两个宿主的 layer 由作者调成 80（layer 太高有的物品渲染器画不出来，引擎结论 §31）；**同日与前置 EterniaModCore 解耦**
> （上面「自带的轮子」），作者实机运行基本无问题。菜单样式的 HTML 预览网页已删（实现即准，`tooltip.md` §6.12）。
>
> **2026-10-28 悬浮窗与查找状态**（`floating.md`）：物品栏顶栏最右边的查询按钮（触屏）、悬浮窗模式（可拖、点 MEI 展开带 30% 黑底、
> 再点 MEI 或点黑底收起、阈值看任一侧）、HUD 与强制兼容的注入、五个设置项全部写完并接线。第一次实机：开着 HUD 悬浮窗进存档三次都在注入后
> 约 1 秒崩溃（原因未实证，头号嫌疑是焦点探针扫 HUD，`floating.md` §10）、悬浮窗拖不动；作者给了排查点（创建路径、重复创建、只在 OnPushScreen 注入）
> 与拖动的做法（JSON 原生拖拽、默认上方正中横排），同日改完。第二次实机（同日）：作者查出 HUD 上展开 MEI 问题多、焦点查询的崩溃
> 只在没有代理的界面上出现，另提了悬浮窗管事时不避让与配方页的 `AllowChangeVisible` —— 同日改完（HUD 上改 PushScreen 开 MEI 自己的界面、
> 焦点探针的保守模式）。第三次实机（同日）：还崩，保守模式无效 —— 落盘的 Python 日志坐实崩在焦点探针扫别人家界面的第一遍里，
> 改成注入的界面不扫、不出查找状态（留诊断开关）；另按作者意见做了配方页照样避让、展开当场复位、`VisibleControlPath`、
> 原版界面表搬进原版扩展（`ctx.UI.Screens`）、两栏层级的根变量、「启用快速收起悬浮窗」。第四次实机（同日）：作者「基本没问题」，
> 开着诊断开关复现的崩溃由 CrashHunter 坐实（焦点探针第一次开扫时的 C++ 异常）；作者定焦点探针改成查询时递归（注入的界面也能查了），
> 另加触屏划过格子就开菜单、修开界面时 grid 的报错，同日写完。第五次实机（同日）：作者「目前无任何问题了」，
> 随后删掉调试代码与调试输出（`floating.md` §10.5）。
>
> **2026-10-28 搜索语法与配方树方案**：物品搜索支持 NEI 式的混合搜索（`@` `#` `&` `$` 前缀、空格且、`|` 或、`-` 排除，上面「物品链路」），
> 离线探针全过，实机通过（10-28）。配方树（S5）出了方案与交互预览 `docs/design/recipe_tree.html`（只在本地）；作者先定了两条：
> 树里的「换配方 / 不再展开」默认只管这一棵、节点菜单另给「设为首选」「当原料（全局）」写全局表；收藏一整棵树，**能展开，展开就是原料汇总**
> （`bookmarks.md` §4）。作者看过第一版又定：**自上而下**、**多格节点**（工作方块 + 原料组，可折叠成主要产出），代码写在 `ui_script/mei_ui/recipe_tree/`
> （照别的界面的编排）；本轮只评估、不写代码 —— 设计页出了第二版（布局改成 Python 算坐标的逐层轮廓打包，评估了每行 stack_panel 的写法与它的三个问题）。
> 作者看完第二版定了剩下的（根单独一格、默认全展开、深度上限 64、对照背包只在汇总里、查看配方页 = 关掉树回去翻到它；工作方块格能换显示的工作站、
> 点工作方块换类型、点原料格换配方、PC 也用菜单），说「这轮直接开工」—— **同日第一版写完**（上面「已落地」的配方树一条、`recipe_tree.md` §0），
> 两个离线探针全过；之后四次实机（大树建控件的耗时、拖动、视口、菜单落位、回工作台、收藏树都看过），作者回报全部通过。
>
> **2026-10-26 P0 设置系统完成**（框架、通用页两项、定稿文案、许可证全文、上下栏复位修复，全部作者实机验收）。
> 收藏（照 NEI）的一期已写完并多轮实机，进度见下。
>
> **10-29 第二十二轮：蔚蓝机器新界面的 MEI 适配（写完、离线探针全过，待实机）**。蔚蓝那边按「UI 规范 v2」重做了机器界面
> （蔚蓝仓 `.claude/ui-review/ui-spec-v2.md`，§12 / §13 是给 MEI 的：配方行 = 机器内容区的静态快照，部件之间的相对位置照机器）。
> 作者看过两版网页预览（四周留 4、能量条在左上、主体整组平移、部件大小不动；冷冻机缩成 S、配方没用到的格子也预留、真空冷却仓与发酵池纵向居中）
> 后「直接开工」。**生成器同一次运行写预览与游戏里的文件**（蔚蓝仓 `.claude/ui-review/tools/gen_mei_recipes.py`，坐标从 `assets/machines.js` 算、
> 部件引用的组件照机器界面的 JSON）：`resource_pack/ui/mei_recipes/<机器>.json` 27 页、`common.json` 的三个组件（流体格换 fluid_tank 外观、
> 不平铺的能量条、进度悬停）、`_ui_defs.json` 登记、给脚本的布局事实表 `external/mei/machines/_layouts.py`；扩展的 `_common.BuildMachine`
> 查到布局就用 `_LayoutScriptFor`（格子按布局表、能量条分段、进度方向、火焰、能量与进度两个悬停）。重做 15 页、新接 N1 ~ N6 / N8 与电解机 / 卤水池，
> 提案的发酵池 / 火力 / 地热发电机也做了（这三台与卤水池的数据不在 `common.export`，导出缺口）；N7 挂成机件加工台的第二个工作站；不改的五页照旧。
> 顺带修了上游合进来的流体贴图接口变化（旧写法每种流体都退回白贴图）。`RecipeBinder.Group([])` 会抛、整页断 —— 没有格子的那一组不声明（`extension_api.md`）。
> 记录与每页的典型物品在 `docs/thirdparty/skybluetech.md` §8.11（本地文档）。
> **10-29 第二十三轮**：作者指出配方行用了蔚蓝机器的格子尺寸（18 / 26）—— **物品格一律用 MEI 自己的 20×20**（`mei_common.item_panel`），
> 大号产物格也换成普通的 20×20，行因此略加大。作者让先在网页上改（生成器加了 `--preview-only`），看过预览「就这版」，
> **同步到了 JSON**（22 页的格子、6 页的能量条分段）。
> **10-29 第二十四轮**（作者实机九条）：合金炉两个产物上下排；模版成型机侧槽照改之前放右上、进度与产物右下；**进度（含内凹管道）压到格子与流体槽下面**
> （精密切割机、真空冷却仓、固液搅拌机、热力反应发电机）；蚀刻机、电解机超出页面 —— 配方 grid 不写 size 是父控件的 100%、被配方页最小宽 188 卡住，
> 比 188 宽的行给 grid 写上行宽（「给 RECIPE 层扩宽」）；水培床两页换新控件（生成器 `emit_hydroponic` 出、脚本走基类的 `LAYOUT`，旧的 `power_slot` 退役）。
> 离线探针全过，待实机（`skybluetech.md` §8.11.3）。作者实机「完成」。
> **10-29 第二十五轮**：作者让全仓审查注释 —— 代码注释与 docstring 里的会话指向（会话轮次、第几次实机 / 第几版、待办与阶段编号、
> 「作者某天定 / 指出」、日期）全部改成只解释代码的写法（蔚蓝仓不在范围内）；规矩写进 `engineering.md` §4.1b-8 与 §8 自检清单，
> 体检 `debug/scripts/probe_comments.py`。`CLAUDE.md` 与 `docs/` 是记录，照旧写轮次与日期。
> **10-29 第二十六轮**：列待办（`docs/architecture/README.md` §8 一览）；作者让重建提交历史 —— 旧提交全部清掉，工作区整个提交成一个 `init commit`（`master`），
> `.gitignore` 忽略了却还在版本管理里的 `docs/`（28 个文件）与 `world_icon.jpeg` 移出版本管理（文件留在本地）；之后的改动在 `dev` 分支上做（下面「交付纪律」第 5 条）。
> **10-29 第二十七轮**：作者让先讲 P2-10（切换配方不重建）的影响范围、做法与副作用（只评估，`recipe_tree.md` §0.0.1 补了实查出的出入），
> 这轮做 P2-1 的两件：**原版全量配方扫描 + 缓存**、**查工作站的用途带上全部配方** —— 写完、离线探针全过，待实机（上面「已落地」的「全量配方扫描与工作站的用途」）。
> **10-30 第二十八轮**：作者实机贴回扫描日志（2463 个物品、19704 次、平均 0.13 毫秒、24.7 秒扫完），提了两条：① 悬浮窗为什么有 `SetLayer`（开销极大、不建议用）
> —— `Apply` 每次开界面都给两栏写一遍，改成只在露着、且真要换时写，注入的界面与 MEI 自己的界面的两栏生下来就是悬浮窗那一档（引擎结论 §47、`floating.md` §7）；
> ② 不在进存档时扫、首次要全表时扫，单配方查过的也记下（游戏有动态注册配方的接口）—— 照做（上面「已落地」那一条）。离线探针全过，待实机。
> **10-30 第二十九轮**：作者「MEI 已经接近发布完成度，接下来做的可能是本体发布前最后几个功能」—— 三件（先问了四个问题，作者都选推荐项）：
> ① **普通 / 工具 / 作弊三种模式**（`modes.md`）写完、离线探针全过，待实机；顺带查出网络层的发起者认的是客户端自己写的 `__from`（能冒充），
> 改成先认引擎给的 `__id__`（`quick_craft.md` §6.5）；② **物品栏筛选**只做骨架与网页预览（`docs/design/item_filter.html` 四种排版），
> 作者选了排版下一轮写菜单；③ 设置「信息显示」加「启用显示物品命名空间」「启用显示物品ID」，写完待实机（上面「已落地」三条）。
> **10-30 第三十轮**：作者实机第二十九轮后五件：① 模式按钮颜色加深 + 悬停文字；② 工具模式接蔚蓝合成样板 —— 先评估：只在蔚蓝的 MEI 扩展里加一个文件、不打补丁、
> 不改服务端（复用蔚蓝自己的上传请求），MEI 侧加了注入挂载（`Mount = "inject"`，第三十一轮删了）与 `point=True`，已接上（`docs/thirdparty/skybluetech.md` §8.12）；
> ③ 补导出（`ctx.UI.Actions` 等）、第三方文档整理成 `docs/modding/`（`extension_api.md` 只留对照表），顺带把自适应规则精简成「生效条件」；
> ④ 物品栏第 0 格偶尔建不出来（`TypeError: bad argument type for built-in operation`，开着大面积遮挡的界面时）—— 离线没能复现、没找到确定的原因：
> grid 回调异常的日志加了抛出的位置（`utils/text.error_where`）、一格接连一秒建不出来先放空格（`ItemsGrid.CREATE_RETRIES`）、递给渲染器的参数规整（`controls/item/panel.render_args`），等作者贴回带位置的日志；
> ⑤ 筛选菜单照排版 D 实现（上面「已落地」）。离线探针全过，待实机。
> **10-30 第三十一轮**：作者实机第三十轮后五件：① 按住 Alt 的快捷键帮助和原版悬停文字叠在一起 —— 帮助亮着时原版悬停文字让位（上面「快捷键」）；
> ② 作者：PushScreen 开的界面也挂得上代理、MEI 纯靠代理兼容 ⇒ 上一轮的注入挂载删了（上面「三种模式」）；③ 第 0 格的异常有了位置：
> `grid.py` 的 `"/{}{}".format(...)` —— 这一行本身不会错，是**引擎在 C 层留下、没清掉的异常**被 format 的 `PyErr_Occurred` 检查撞上（引擎结论 §48）；
> MEI 的绑定回调进门先接一次（`utils/binder.py`）、主节点每帧的几步之间各接一次（`core/node.py`），接住了记一行 `[MEI/stray]`：在哪接住的、
> 上一条跑完的 MEI 绑定 —— 下次实机据此找是谁留下的；④ 蔚蓝里另外四个选物品的界面接上工具模式；⑤ 合成样板接上配方转移（新接口 `ctx.UI.Transfers`）。
> 离线探针全过，待实机。
> **10-30 第三十二轮**：作者实机「本轮其他功能无问题」，三件：① 遗留异常的 `[MEI/stray]` 日志回来了，定位到 MEI 之外：多半是蔚蓝机器界面的颜色绑定只给了 RGB 三个分量
> （引擎结论 §48，蔚蓝侧的改法在 `skybluetech.md` §8.14，没动蔚蓝的代码）；② 工具模式拿着的物品层级 97 / 98 画不出来 → 降到 78（引擎结论 §31）；
> ③ 调研「每个版本都稳定拿到创造栏全物品表」：SDK 没有接口，但游戏数据里的 `item_catalog/crafting_item_catalog.json` 列着创造栏的全部 aux 变体，
> 带 userData 的几族（附魔书、烟花、旗帜……）不在里面；服务端 `GetModConfigJson` 的实现没限制路径、可能读得到它 —— 给了片段 `debug/ingame/creative_items_probe.py`
> 等结果再实现（`item_model.md` §9）。
> **10-30 第三十三轮**：① 第 0 格作者定**暂不修、进待办**（`README.md` §8 P3-7），诊断输出删了（`[MEI/stray]`、`utils/stray.py`、主节点每帧的检查、grid 的「先放空格」与抛出位置），
> 绑定入口的静默接住留着；② 工具模式拿着的物品在 78 实机还是画不出来 → 取保守值 40（引擎结论 §31）；③ 片段结果：运行时读不到原版包里的文件，
> 扫创造栏界面作者否了（滚动视图会剔除）；按作者建议查了整个游戏目录 —— 带 userData 的条目（附魔书、烟花、烟火之星、不祥旗帜）哪儿都没有，
> 目录里的 aux 变体能在开发期读：`debug/scripts/gen_creative_table.py`（3.9 → 225 项）。做法写在 `item_model.md` §9.7，待作者点头。
> **10-30 第三十四轮**：作者定创造栏表的做法 ——「拿一遍 json 的 id+aux 表，再照一份现成的物品表补全带 userData 的，总结后写进 vanilla 扩展，后续版本维护只要盯着物品更新」。
> 写完（上面「已落地」的「创造栏的物品变体」）：那份表 2130 项里带 userData 的正好是四族 91 样（附魔书 41 本最高级、旗帜 17 面、烟花火箭 17 支、烟火之星 16 颗），逐条对过；
> 颜色照创造栏的顺序改过（那份表用了床的 aux 顺序，旗帜、烟火之星的 aux 却是染料下标）、普通旗帜不带 userData；
> 新加 `ItemManager.SetPlainHidden` / `ItemFactory.LoadInfo` / `Item.IsPlain`（对外，探测）；生成器换版本时提醒三样。离线探针全过，待实机。
> **10-30 第三十五轮**：作者实机第三十四轮「没问题」，报了一个 bug：`#保护` 出来全部附魔书、别的附魔名搜不出来 —— 搜索的悬停文字缓存按 (id, aux) 记，
> 改成按物品实例（上面「物品链路」）；物品栏筛选加「隐藏物品」（加法，上面「物品栏筛选」）；整理这几轮、推荐提交标题；全仓审查一次（不含蔚蓝），
> 审出来的问题核实后改了能改的（`docs/architecture/README.md` §8 记着审查结论与剩下的）：**快捷合成的服务端**（上面那条）、
> **存储的强制刷盘拿空表盖掉没读过的数据**（`Store.Flush` 没读过的不写、读炸了这一局只读 —— 原来一局里没开过配方页就关界面，置顶全没了；`persistence.md` §8）、
> **第三方登记物品分组后物品栏整个抛异常**（组表存的是 id，排物品栏时拿它当 Item）、**配方行的树 / + 按钮按过一次后同一行要点两下**（无状态按钮停在「按下」、
> 推送缓存没清，下一下点击被当回声吞掉）、第三方配方页脚本的构造抛了整页空白、没图标的类型进不了 TypeTab、关配方页重复执行抛异常、
> 配方解析一条认不出就整个类型出不来、配方树的首选 / 当原料退出存档时丢、名称排序 str / unicode 混着抛、搜索结果页跨世界不过期、搜索索引开局建两遍。离线探针全过，待实机。
> **10-30 第三十六轮**：作者把第二十七 ~ 三十五轮提交了（`dev` 上的 `d4532cb`），版本统一改成 **1.0.0**（两个 manifest、`mod_info.Version`、原版扩展的 `VERSION`）；问了三件事 ——
> ① 蔚蓝怎么搬物品、MEI 的配方转移有哪些设计缺陷与接口缺口（照 NEI 对比）；② 配方转移要不要大改：**要**（`quick_craft.md` §10：玩家侧留着、方块容器那条删、
> 不搬物品的界面换 ItemRenderer 标准、往模组机器里搬交给模组自己的处理器；蔚蓝样板的 + 现在就能删）；③ 工具模式换成和别的模组作者约定的 ItemRenderer 标准 ——
> 只评估、不接入（`modes.md` §11：`GetUiItem` 读不回 userData 与数量，事件要每次发、带完整物品；声明建议写在 `property_bag`；对方刷新会盖掉 MEI 写的）。
> 核对了蔚蓝侧删工具模式的提交（c2b82c85）：干净，过时的只在 MEI 的本地探针与文档，本轮改了。代码只改了版本号。
> **10-30 第三十七轮**：作者：「（ItemRenderer 标准）还不如继续用之前的接口，顺带看蔚蓝那次被回退的实现有哪些缺陷、能否改进」「实现新的配方转移接口，实现到蔚蓝的机件加工台，改之前的合成样板的逻辑」「按钮 hover 用 hover text，PC 触控都能用」——
> ① **转移处理器落地**（`quick_craft.md` §10.8）：MEI 算清单（按格子摊、全局配额、挑背包里有的、缺几个），处理器 `Check` / `Transfer`；+ 的悬停文字（动作按钮第五条绑定 `.hover`）；点了没成原因挂在页码后面；`ctx.UI.Transfers.Request`；
> ② **蔚蓝**：机件加工台接上（发加工台自己的请求）、样板改用处理器（标签原料挑背包里有的）、`Workstation.json` 打开 +；③ **放置目标改进**（`modes.md` §12：复查出七条缺陷）：accepts、回调返回 False / 一句话是不收（手里的东西不放下、tip 提示），蔚蓝的工具模式按改进后的写法恢复（selectors、样板两个放置目标，公共小工具 `ui_access.py`）；
> ④ 探针共用的 `_boot.py` 关掉了字节码写入（探针导入蔚蓝的模块会在蔚蓝仓留 .pyc，挂在它的 git status 里；本轮又清了一次）。离线探针全过，待实机。
> **10-30 第三十八轮**：作者实机第三十七轮「其他基本没问题」—— ① **方块容器那条路删了**（作者：还没正式发布，抓紧少创造遗留问题）：`BlockSlotTarget`、`KIND_*` 与「种类」、清单上的坐标维度；旧的快捷合成接口（`ctx.Registry.TransferRegistry`、`ctx.Types` 的 `ItemSource` / `SlotTarget` / `TransferPlan` 等）收回成内部的（`quick_craft.md` §10.9）；
> ② 提交「refactor: 重构配方转移处理器」（第三十六 ~ 三十八轮）并打 tag `v0.0.1`；③ 之后全仓审查一次（不含蔚蓝，`docs/architecture/README.md` §8「第三十八轮全仓审查」）：
> 34 条、没有阻断级的，除两条小的都改了（提交 `9635c68`「fix(ui, registry, state): 审查并修复诸多问题」）—— 快捷合成一格只用一种候选、处理器的 GRID 摊不进就灰掉（`TransferRequest.Fits`）、只放进去一部分不关页、背包 2×2 放得下 3、4 格的无序配方（`quick_craft.md` §10.10）；
> 配方树解算中冻结旧菜单、换候选跳过路上的、预览的解绑挪到每帧（`recipe_tree.md` §0.7）；类型 / 来源一变作废查询缓存与收藏找回（`SourceRegistry.Revision`）、分组写入撞物品表版本（`ItemManager.Touch`）；
> 存储的原文没备份成就只读、盘上的无穷大不再抛（`persistence.md` §9）；扩展 ID 只收 ASCII、内置扩展排最前、阶段抛了照样卸载（`extensions.md` §5.2）；工具模式的放置目标看外层显隐（`modes.md` §12.4）。离线探针全过，待实机。
> **10-30 第三十九轮**：作者让按 tag 查换成 3.10 的接口、单独一个提交 —— `registry/tags.py` 的 `TagLookup`，组表里的标签记录与 `TagConst` 删了（上面「已落地」那一条，提交「chore: 使用3.10新的tags相关接口替换原tags查询设计」）；
> ② **物品分组**（作者：一直有这项功能、现在才有补全的物品表，照同类型分组）—— 创造栏的物品组 + 那四族 + MEI 补的 20 个同类组，组里照创造栏的顺序；搜索时的分组显示作者定照旧（上面「已落地」的「物品分组」、`item_model.md` §10）；接着作者让加设置「启用物品分组」（通用 → 布局设置，默认开），并给蔚蓝也分组（并进原版的组 + 蔚蓝自己的组，`item_model.md` §10.5 / §10.6，蔚蓝仓 `external/mei/groups.py`，新接口 `ItemOrganizer.RemoveGroupItem`）。离线探针全过，待实机（提交「feat(ext, ui, registry): 新增分组和分组相关设置与 RemoveGroupItem 接口」并推送）。
> **10-30 第四十轮**：第一次自测上架被机审拦下（引擎结论 §50）—— 两处 `__import__` 换成 `clientApi.ImportModule`、`utilities.py` 的 ViewBinder 改成 `clientApi.GetViewBinderCls()`、配方页的提示不再对 `getattr(…, None)` 的结果取下标（拆成 `NoticeText` / `NoticeUntil`）、`LogPatcher` 不再 import `mod_log.engine_logger`；新探针 `probe_review.py`（机审会拦的写法，设 `MEI_PYLINT` 连 pylint 一起跑）。提交「fix: 修复机审失败问题」。
> **蔚蓝扩展列入待办**（2026-10-26 起不主动推进）。next 适配已提交在蔚蓝仓 `mei-next`
> （`0b1605e4`，未推送），剩下的：
> ① ~~作者按 `docs/thirdparty/skybluetech.md` §8.8 逐台实机 review~~（第二十二 ~ 二十四轮换成新界面后逐页实机过了，作者「完成」）；
> ② ~~未接的 N1~N11~~（10-29 第二十二轮随新界面一起接完，见上）；
> ③ 两处蔚蓝侧问题（集合被同名集合顶掉、金属锤的表客户端加载时不建）要不要提给蔚蓝；
> ④ 机器模块 docstring 里过时的「典型配方」；⑤ `mei-next` 要不要推送（第二十二 ~ 二十四轮 MEI 配方页的改动在蔚蓝仓还没提交）。
>
> **已完成**：S0 / S1 / S1b / S1.5-P0 / S2a / S2b；S3 的 U1 止损、U2 槽位点击、
> U2c 类型导航（实机条件「类型 ≥ 9」已满足）；**U4 动作总线实质已落地**
> （`RecipeAction` 分发 + 行索引 + 回灌吞掉，star / top / plus 都在用，只剩 tree）；
> **S4 主体**（`RecipeCategory` + `RecipeSource` + `SourceRegistry`，`API_VERSION = 2`）；
> **快捷合成 N1~Q5**（工作台实机通过）；置顶（`state/pins.py`，全局 / 最近在前 / 上限 64）。
>
> **收藏（书签）—— 照 NEI 的设计做，一期 2026-10-26 写完；第一次实机后修了数量 / 角标丢失、页签黑底、左侧栏开关三处，调试键换成字母；第二次实机字母键仍全无反应，加了 Q 对照路径与逐步日志；第三次实机 Q 可用、字母键没反应 ⇒ 光标认格子改用焦点探针（`focus.md`），加了 R / U；第四次实机焦点探针扫出 0 个渲染器；第五次实机焦点探针可用，按作者要求键位重排成无冲突的一套、Q 撤掉；「收藏栏操作后别的 grid 只剩一个物品」第五轮改绑定前缀没治好，第六轮堵了四个口子并加了自检日志（引擎结论 §27，`bookmarks.md` §11 第 4 条），第七次实机没再出现；第七次实机发现收藏栏改动后焦点探针认不到新格子（补上「空格填上物品」的唤醒）、C 改为两用（配方展开 / 收起、物品所在的组折叠，不在分组里的展开配方带框）、竖排多出一个木板（加了排版日志待对照）；第八次实机快捷键与焦点探针通过、调试日志删掉，展开配方的工具改为不乘倍数（蔚蓝模版成型机的刻印模版挪到催化剂）；第九次实机的行距日志坐实了收藏栏分组底色上下行的缝 —— grid 按 JSON 的尺寸规则均摊行距（引擎结论 §28），三个物品 grid 的高改写 `default`、临时日志删掉，第十次实机确认缝没了（排查经过在 §12.2）**（`bookmarks.md` §6 / §11 / §12）。
> 作者 10-26 圈定：§10 评 ✅ 的先做，🟡 与 ❌ 全进待办（§7）；**快捷键交互先做成调试功能**（以后自己写快捷键绑定系统，
> 引擎不支持组合键）；存储升 v4；合成链的原料现查；菜单与触屏先不做。
> - **一期**：存储 v4（页签、分组、数量、全局 / 按存档）；收藏栏接线（数量、配方角标、分组画框、横排 / 竖排清单、
>   折叠、页签、点开配方收藏翻到那一条）；两个设置项；调试按键（`DebugMode = True` 才生效，B / R / U，收藏格上 X / K / = / - / G / L / V / C；10-27 加了看 tooltip 的 T，键表与预期在 §12）。
> - **二期**（未开工）：合成链与组汇总面板、子链折叠、首选配方 + 保存配方树、填充合成格、分享码、缩进列表树。
> - **待办**：PC 上的菜单、拖拽、合成树窗口、拉取物品等，清单在 §7（快捷键正式版 10-28 做了，见上「快捷键」；悬停预览的 PC 那一半 10-27 由 tooltip 第二轮做了；
>   触屏的操作 10-27 由 tooltip 第三轮的二级菜单做了：收藏格的数量、排序、分组、折叠、展开、横竖排、移除、删除整组都在菜单里）。
> 方案见 `docs/architecture/bookmarks.md`；其 §9 是 JEI / EMI / REI / NEI 收藏存法的**读源码记录**
> （2026-10-14），§10 是 NEI 收藏**功能**的读源码记录与评级（2026-10-26）—— 讨论收藏先查这两节，不必重读源码。
>
> **作者定的原则**（2026-10-14，规范见 `engineering.md` §7-9）：**配方数据可以因版本更迭、
> 模组切换而丢失，但不能阻塞加载。** 存储与找回的每一层都按它写：逐条容错、看不懂的原样留着、
> 不在加载时批量找回、except 里拼日志一律 `error_text(e)`。
>
> **未开工**：~~U0 实机验证、U3 layout 解释器、U5 显式生命周期~~（10-28 审核：建议作废，U5 剩的一个真问题改名「配方脚本宿主统一」，`README.md` §3 / §8）、
> S4 剩余（~~`WorkstationIndex`、全量扫描接线~~ 10-29 第二十七轮做了：查工作站的用途就是它服务的类型的全表；第三查询方向不另做、并进了「用途」；
> 剩工作站图标左键的入口与扫描结果的持久化，`README.md` §8 P2-1）、~~S6 新配方类型~~
> （**10-29 第十八轮写完原版七种、第十九轮配方页照原版界面重做**，待实机，见上；第三方的类型照旧走扩展）、模组/类型筛选。（组合键 10-29 做了，上面「快捷键」。）

依赖关系与顺序不可调换的硬依赖见 `docs/architecture/README.md` §2。

> **上线前的硬门槛**（都关系到 `Recipe.Id`，而书签与置顶存的就是它 —— **必须在书签之前定**）：
> 1. **引擎 identifier**（**2026-10-29 实机查清：拿不到**，引擎结论 §43）：`GetRecipesByResult` 的返回只有 `key / pattern / result`
>    （熔炉 `input / output`），没有 identifier；identifier 只能拿 `GetRecipeByRecipeId` 反着查，没有列全部的接口
>    ⇒ **`Recipe.Id` 继续用内容哈希**。剩下的是让哈希不随装卸模组变：第 2 条与 list 原料的折叠（`README.md` §8 P1-3）。
> 2. **熔炉配方的 Id 绑着全部燃料**（2026-10-13 查出）：catalysts 计入 Id，
>    燃料是字面展开 ⇒ 装卸任何带燃料的模组，所有熔炉配方变 Id。**作者 10-29 定：燃料是驱动机器的、不参与合成，不进配方本身**
>    （也不用存）—— 熔炉配方不带燃料，配方页的燃料格问熔炉扩展的燃料表（只给显示），Id 就不再绑燃料。**10-29 写完**。
>    同日另做了 **list 原料的折叠**：引擎把 tag 展开成的物品列表（木板、煤）带上它们的公共 tag（`tools/parser.common_tag`），
>    `Recipe.Id` 只写 tag 名，模组往 tag 里加物品 Id 不变。**到这里 Id 的定义冻结**（`probe_identity.py` 的 `GOLDEN_IDS`），再改要先想好迁移。
> 3. **收藏不能只存 Id**（**已落地**，B1）：连带存显示物品与类型，失效时能显示「已失效：铁锭」
>    而不是空格子。**不存**每格输入代表物（作者 2026-10-14 定：接受丢失），所以 Id 的定义
>    一改，旧收藏就找不回了 —— 第 1、2 条 10-29 都定了（Id 的定义冻结），置顶也只认 Id。

## 引擎关键结论（实机固化，勿重新踩坑）

> 这些是**引擎事实**；由其推出的**项目守则**在 `docs/engineering.md` §6/§7，改动前两处都看。

1. **物品图标必须动态设置**：`ItemRenderer.SetUiItem(itemName, auxValue, …)`。
   **禁止**在 json 里静态写 `#item_id_aux` —— id_aux 随平台/Mod 组合/版本漂移，必错位。
2. **引擎配方 dict 的 `item` 字段是 str 或 list 双形态**（1.20+），且字符串**多为 unicode**。
   解析层必须 `basestring` + 双形态兼容，**一处都不能漏**（这正是当前断裂第 5 条的根因）。

   > **反向的同一个坑（2026-09-01 实测，代价一整轮排查）：递给引擎的字符串必须是 `str`，
   > 不能是 `unicode`。** 引擎是 C++ 绑定，收到 unicode **不抛不报，只是安静地取不到东西**。
   > 而 unicode 与 str 对 ASCII 内容 `==` 相等、`hash` 也相等，能一路骗过所有等值判断与
   > dict/set 查找，只在真正调引擎那一刻露馅。
   > **py2 的 `json.loads` 只产 unicode** ⇒ 任何"存盘 → 读回 → 递给引擎"的字符串都会中招，
   > 且表现为「当场用没事、**重启后每次都坏**」。
   > 收口点是 `state/storage/store.py` 的 `Load`/`Set`（走 `utils/text.py` 的 `to_native`），
   > 新增别的外部数据入口（引擎事件载荷、网络包）时**必须同样规约**。
   > 转换用 `.encode("utf-8")` 而非 `str()` —— 后者遇非 ASCII id 直接抛。
3. **配方查询开销大**：`GetRecipesByInput` 官方明示昂贵，`GetRecipesByResult` 同样不得进入
   点击/绑定回调的同步路径 —— 一律走内存索引/缓存，未命中转异步（下一 tick + loading 态）。
   > ⚠ **现状与这条有出入**：2026-09-02 自建索引（`RecipeIndex` 三桶）**已回退**，
   > 现在是「直查 + `RecipeQueryCache`（LRU 256 条，`state/cache.py`）」，
   > **缓存未命中时是同步直查**，并没有转异步。回退是有意的决定
   > （`structure.md:467`、`tasks_s4.md:13`），目前没有卡顿报告；
   > 但配方树要逐节点查询，那时这条会重新变成真问题（见 `recipe_tree.md`）。
   > **10-30 起**原版的引擎来源把每个回答按（来源, 方向, 物品）记下（「已落地」的「全量配方扫描与工作站的用途」）：
   > 查过的物品不论按产物还是按原料都不再问引擎，未命中的那一次仍是同步直查；全表要的时候才分帧扫。
4. **UI 时序**：`RegisterUI`/`CreateUI`/`PushScreen` 只能在 `UiInitFinished` 之后；
   `PushScreen` 的界面 json 须 `is_showing_menu: true`；控件在 `ScreenNode.Create` 之后才可操作。
5. **grid + scroll_view 有格子复用机制**：数据驱动一律走集合绑定（binding_collection），
   **禁止**直接对 grid 子控件 `SetVisible`；滚动错位要监听
   `GridComponentSizeChangedClientEvent` 全量重刷；grid 子控件**首次渲染前不可访问**（延迟一帧）。
6. **引擎事件数据不支持 tuple、不能传 Python 对象**（`CreateEventData`/`NotifyTo*`）：
   跨端与存盘载荷只用 dict/list/标量；内存里的 tuple 键在边界处转字符串（`"item_id#aux"`）。
7. **ScreenNode 部分初始化陷阱**：引擎会吞 `__init__` 异常并保留半成品实例继续回调。
   防御：纯数据属性前置 + 末尾 `_ready = True` + 所有回调入口
   `getattr(self, "_ready", False)` 守卫（顺带覆盖脚本热重载残留的旧实例）；
   引擎 API 调用不进模块顶层、不进构造函数早期。
8. **标准库被裁剪过 —— `hashlib` 能 import 但没有 `md5`。**
   2026-08-23 实机报错：`'module' object has no attribute 'md5'`。
   其余摘要函数是否可用**未验证**。
   > 更要紧的是**不能用「能用哪个就用哪个」的能力探测来绕**：可用集合取决于
   > 引擎版本与平台构建，探测会让同一份内容在 PC 与手机上、或引擎升级前后
   > 算出**不同的哈希** —— 一切以哈希为身份的东西（配方 Id、书签、索引主键）全部错位。
   > ⇒ 需要稳定指纹时一律用 `utils/stablehash.py`（纯 Python，处处一致）。
   > 内置 `hash()` 同样出局：py2 的 str hash 在 32/64 位平台结果不同。
   >
   > 当前已确认可用的标准库：`abc / collections / copy / json / math / re /
   > struct / time / types / uuid`。**引入新的标准库依赖前先假设它可能被裁**，
   > 并准备纯 Python 兜底。
9. **按钮/输入框/开关类 flag 只能做单个绑定，不能做集合绑定。**
   官方绑定方式表：`BF_ButtonClick*` / `BF_InteractButtonClick` / `BF_BindGridSize` /
   `BF_Edit*` / `BF_ToggleChanged` 一律**仅 `binding`**；只有
   `BF_BindBool/Int/Float/String/Color` 才是 `binding | binding_collection`。
   ⇒ 注册前**必须**按 `utilities.IsBindFlag(flag)` 分流：真走集合绑定，假走普通绑定
   （SDK 里是 `_process_collection` / `_process_default` 两条**完全不同**的引擎注册路径）。
   **2026-10-27 起分流收进 `ScreenBinder.Bind`**（`utils/binder.py`）：给了集合名、flag 却只能普通绑定时按普通绑定挂，
   调用方不再自己分两支写。
   > 2026-08-31 实机：配方槽位点击全无反应。根因就是点击类 flag 被无条件
   > 送进了集合绑定 —— **注册"成功"、零报错、引擎永不投递**。
   > 这类错误没有任何运行期信号，只能靠注册期分流杜绝。
   >
   > 推论：按钮回调**拿不到 `collection_index`**，槽位身份只能靠
   > 「哪条绑定被触发」或解析 `args["ButtonPath"]` 还原。
10. **grid item 内的 toggle：状态**必须**由 Python 直推控件，不能指望绑定驱动。**
    2026-09-01 实机双向证死（配方行的收藏按钮，`common_toggles.switch_toggle_collection`）：

    | 配置 | 状态回调被调用 | 按钮外观跟随 |
    |---|---|---|
    | 只设 `$toggle_state_binding_name`，靠基类接管 | **0 次** | ✗ |
    | 在 `bindings` 里**显式**加一条同名集合绑定 | 1033 次 | ✗ |

    ⇒ 两件事都要做，且各管各的：
    - **显式 `bindings` 条目**才能让状态回调真的被引擎每帧调用（基类的
      `$toggle_state_binding_name` 在 grid item 内不会自己建出可用绑定）；
    - **外观**只能靠 `control.asSwitchToggle().SetToggleState(on)` 直接推 ——
      绑定的返回值进的是基类不读的属性。
    > 推论：**绑定名是自己拼的字符串，与真实控件路径是两回事**，别默认它们对得上。
    > 直推要拿真控件，路径由声明方给（`ActionButton.Path`，**相对配方行控件**，
    > 走 `RecipeControl.GetChildByPath`，与 `InitControls` 取格子同一个路子）；
    > 且要缓存"上次推过的值"，只在变化时才碰控件 —— 这是每帧路径。
    > 行控件重建后**必须失效该缓存**，否则新控件停在默认态。

    **⚠ 直推的另一半（2026-09-01 实机，代价是一次每帧死循环）：
    `SetToggleState()` 会被引擎当成一次状态变化，把 `ToggleChanged` **回灌**给你。**
    于是「推状态」和「玩家点击」在回调里长得一模一样。两个后果：
    - 回灌带着 `state=False` 进收藏回调，会把**已收藏的行悄悄取消收藏**（静默数据损坏）；
    - 若某个动作的回调会**重建行控件**（置顶就是），就成环：
      重建 → 失效推送缓存 → 再推 → 再回灌 → 每帧循环。实机表现是
      TypeTab 与工作站格全部消失、日志每帧一条。
    > ⇒ **在派发漏斗处比对"上次推下去的值"**：与上报值相同即自己的回声，吞掉。
    > 不能用同步的"正在推送"标志——回灌是**下一帧**才到的，标志盖不住。
    > **推送缓存要「先记再推」**，推不上去（行控件还没接上）再撤回（2026-10-29 实机：第九轮改成「推上去才记」后整页无限闪烁，置顶的回灌漏了过去）；
    > 另加一道**不靠缓存**的：上报值等于这一行此刻的业务状态（`ResolveState`）就是「什么都不用改」，吞掉 —— 重建会清缓存，晚到的回灌第一道认不出
    > （无状态按钮不判这一道）。回归位 `probe_action_button.py` A-15 / A-16。
    > 另：动作回调里**不要同步重建自己所在的控件**，挪到下一帧（`AddTimer`）。
    > 实现见 `recipe_details/controls/button.py` 的 `__Dispatch`，
    > 回归位 `probe_action_button.py` A-11。
11. **`GetItemBasicInfo` 对部分原版物品拿不到个别字段，且返回 0 而不是 None。**
    官方备注原文：**方块类燃料获取不到燃料时长**，弓/弩获取不到武器攻击力，
    蛋糕获取不到饱和度与饱食度，马铠获取不到防具防御力 —— 一律返回 **0**。
    > 推论：**「返回 0」与「该物品确实没有这个属性」在这个接口上不可区分**，
    > 任何按 `> 0` 过滤的地方都要问一句「这一类物品是不是恰好在豁免名单里」。
    > 例如熔炉按 `FuelDuration > 0` 筛燃料（`extensions/vanilla/furnace/source.py:80`），
    > 木头/木板这类**方块燃料按文档就该被漏掉** —— 熔炉配方页的燃料格里可能没有它们。
    > **2026-10-29 实机确认**（§44）：木板、原木、台阶、楼梯、栅栏、工作台、箱子、书架、梯子、树苗、脚手架、煤炭块、干海带块、竹子的燃料时长都是 0；
    > 物品类燃料照常（煤 / 木炭 80、木棍 5、木镐 10、烈焰棒 120、岩浆桶 1000，单位秒）。
12. **版本/平台敏感接口一律 `getattr` 能力探测后调用。**
13. **SDK 按函数名在 instance 上取回调**：事件是 `EventHandler.Call` 里 `getattr(instance, func.__name__)`，
   绑定是 `gui` 按名字在界面节点上找。直接调 `ListenForEvent` 时回调必须是 instance 自己的同名方法
   （2026-09-03 实机：传 `self.Channel.OnRequest` 得到 `'MainSys' object has no attribute 'OnRequest'`），
   名字被改写过的私有方法同样取不到。
   ⇒ 一律经 `EventListener` / `ScreenBinder`（`utils/events.py` / `utils/binder.py`）：它们起一个唯一名字的转发函数、
   挂在自己 / 界面节点上再交给 SDK，回调随便什么可调用对象都行（回归位 `probe_standalone.py`）。
   > 原来的 §13「前置桥时序」随 2026-10-27 与前置解耦作废。
14. **JSON UI 的 `size`/`offset`/`max_size` 里，变量只能整体替换，不能做数组元素。**
   `"size": "$my_size"`（`$my_size = [188, 76]`）合法，原版几十处；
   `"size": [188, "$h"]` **零先例**，引擎把 `"$h"` 原样丢给 `ui::parseLayoutAxis`，
   触发断言 `% modifier given without '%' symbol!` 并**直接崩溃**。
   > 2026-09-04 实机，代价是一次崩溃 + 一轮误判。**要按机型改高度就在实例化处整体覆盖
   > `"size"`** —— 那是 `@` 扩展的标准用法。
   > 反之，控件引用用变量（`"child@$var"`）是**合法**的，原版 118 处，别一起怀疑。
15. **挂在绑定回调里的代码抛异常 = 那条绑定当场失效，且引擎不给日志。**
   界面会回落到 `property_bag` 里的默认值，看起来像"渲染错了"而不是"报错了"。
   > 2026-09-04：`GetTypeTabIdAux`（图标绑定）里顺带推了 toggle 状态，
   > 推送在控件未就绪时抛 → 图标绑定被一起带走 → 全部 tab 显示
   > `#item_id_aux: 131072` 的兜底（一个草方块）。**排查时完全看不出是异常。**
   > ⇒ 绑定回调里做"顺带的事"必须自带 try/except，且**先算返回值再做那件事**。

16. **JSON UI 里派生控件写 `controls` 是「替换」不是「追加」。**
   `"a@ns.b": {"controls": […]}` 会把 `ns.b` 自带的子控件**连同它们身上的绑定
   一起丢掉**。官方的追加机制是 `modifications`
   (`{"array_name":"controls","operation":"insert_back","value":[…]}`)。
   > ⥠ 但 `modifications` 在**本引擎的资产里零先例**(vanilla_netease 全包搜不到),
   > 官方文档的例子也都是「同名覆盖原版控件」而非「派生控件」。
   > **需要给现成控件加子控件时，最稳的写法是把它嵌进自己的 panel**
   > （变量在 JSON UI 里是向下传递的，`$binding_name_prefix` 这类不用手动转交）。
   > 2026-09-05 的流体格就是这么做的，代价只是控件路径多一层。
   >
   > **例外：改原版控件本身**（资源包里放与原版**同路径**的文件、用原版命名空间）时，
   > `modifications` 正是官方举例的用法。MEI 的设置页
   > （`mei_resource/ui/settings_screen.json`）走的就是这条；它进不进 `_ui_defs` 都不影响（作者 10-28 实测，MC_Editor 会自己写进去）。
   > 2026-10-26 实机确认可用（作者验收设置页）。

17. **JSON UI 引用一个不存在的控件 → 弹断言框，不是静默失败。**
   ```
   UIControlFactory parent control "X" failed to create child control "Y",
   did you add a new type?
   ```
   引擎拿到一个解析不出 `type` 的 def 就断言。
   消息里 **parent 是父控件、child 是子控件名** ——
   真正出错的是子控件那个 `@引用` / `$xxx_control` 指向的东西。
   > 2026-09-05：合金炉一直开不开，因为 `$progress_control` 指向
   > `AlloyFurnaceUI.alloy_furnace_progress` —— **那个控件从来就不存在**。
   > 名字看着很合理，胉看完全看不出来；但它**机械上完全可验**。
   > 回归位 `debug/scripts/probe_ui_slots.py` L-7（1500+ 条引用全解析一遍）。

18. **不要在 grid item 里每帧去改一张 `tiled` 图 —— 引擎会在 grid 模板上断言。**
   ```
   You shouldn't try to update control collections on a template.
   Control Name: .../RECIPES_GRID/recipe/wrapper/content/power/bar/bar/mask
   ```
   路径里是 `/recipe`（**模板**）而不是 `/recipe1`（实例）。
   `tiled` 图在引擎里是**内部控件集合**（重复贴片），每帧改它就要重建那个集合，
   而重建会走到模板控件上。

   **六次实机的分离表**（蔚蓝的电力条）：

   | # | 控件 | 含 `tiled` | 脚本每帧碰它 | 断言 |
   |---|---|---|---|---|
   | 1 | `PowerBar` | 有 | 否（仅 OnCreate 一次）| 无 |
   | 2 | `PowerBar` | 有 | 是（`SetFullSize`）| **有** |
   | 3 | `PowerBar` | 有（拿**变量**关过，未必生效）| 是（裁剪）| **有** |
   | 4 | `ProgressBar` | 无（字面）| 是（裁剪）| 无 |
   | 5 | 自制副本 | 无（字面）| 是（裁剪）| 无 |
   | 6 | `PowerBar` | 有 | 是（`SetFullSize`）| **有** |

   第 5 行很要紧：那个自制副本已经带着 `frame`/`nineslice`/`uv`/`keep_ratio`/锚点
   跑过且无断言 ⇒ **那些属性全被排除**，剩下的差异只有 `tiled` 与多一层嵌套。
   > ⥠ 第 3 行是唯一的反例，但它用的是 `"tiled": "$var"` ——
   > 同一轮里我对同一个文件的另一处 regex 编辑**打错了控件**，
   > 而§14 已记过引擎在某些字段上不解析变量。⇒ **那次关 tiled 很可能根本没生效**。
   > 字面去掉 tiled 的两次（4、5）都无断言。

   做法：需要每帧驱动的那张图自己拄一份非平铺的副本（共享控件别动）。
   贴图很小时视觉几乎无损：蔚蓝的 `energy_bar_top` 是 **16×1 单行**，
   纵向平铺与纵向拉伸**像素完全一样**。
   > **排查教训**：我先后归因为 `SetFullSize`、外层的集合绑定、裁剪字段，
   > **四轮都没堆对**，每轮都要作者跑一次实机。真正解开它的是作者一句
   > 「一开始其实无断言，是后面出现的」——
   > **排查应该先建分离表，而不是盯着断言消息里那个控件猜属性。**
   > 另外：**改共享 JSON 不要用 regex**，要解成结构再改 ——
   > 打错控件会让一整轮实验作废且难以发现。

19. **图的裁剪有三种驱动方式，写错一半就“不报错也不动”。**

    | 想怎么驱动 | JSON 里写什么 | Python 写什么 |
    |---|---|---|
    | Python 每帧推 | `clip_direction`，**不写 `clip_ratio`** | `SetClipDirection` + `SetSpriteClipRatio` |
    | JSON 动画 | `clip_ratio: "@ns.anim"` + `clip_direction` | `PlayAnimation()` |
    | 静态不动 | `clip_ratio: 0.0` + `clip_direction` | 无 |

    不写 `clip_direction` ⇒ 没开裁剪；写了**字面** `clip_ratio` ⇒ 比例被钉死。
    两者现象一样：调用不报错、图一动不动。
    > MEI 熔炉的火焰与箭头走的是**第二条路**（`anim_type: "clip"` + `PlayAnimation`），
    > 不是 `SetSpriteClipRatio`。而 `PowerBar.mask` 写了字面 `clip_ratio` ⇒
    > **它只能用 `SetFullSize` 撑高度**，机器界面的 `UpdatePowerBar` 也是这么干的。

20. **配方行想多占地方，要改的是 `wrapper` 而不是 `recipe` 的 size。**
   行本身并没有顶满最外层包装；真正卡住内容的是里面那个
   `wrapper` 的 `["100%+-54px", "100%+-4px"]` —— 那 54px 是给右侧动作按钮留的，
   而按钮只占 13px。把它改小（如 `-34px`）就多出 20px 内容宽，行宽不用动。
   *（2026-09-05 作者实测；改 `recipe` 的 size 是无效功。）*

21. **`ignored: true` 与 `visible: false` 不是一回事。**
   前者把控件**从布局里拿掉**；后者只是不画，**控件依然存在、依然占位** ——
   在 `stack_panel` 里就是空出一格。
   > 2026-09-09：配方行的转移按钮靠 Python 侧 `RecipeAction.Visible` 隐藏，
   > 结果蔚蓝那 20 台机器的按钮列**每行都空着一格**（作者从布局上看出来的）。
   > ⇒ 「默认用不上」的控件要在 **JSON 层 `ignored`**，适用的布局显式开；
   > 运行期条件（材料够不够）才归 Python 的 `Enabled`（灰掉而非藏掉）。
   > 三档判据见 `engineering.md` §5.1f。
   > ⚠ 2026-10-27 复查（**未实证**）：那次藏的是 `toggle_button`，它外面那层固定尺寸的 `N@action_button` 面板没藏，空出来的是那层面板；
   > NetEase 自己的玩家信息弹框在 stack_panel 里 `SetVisible(False)` 的是直接子控件，看样子会收拢。
   > 「直接子控件藏了收不收拢」等 tooltip 第三轮 M1 顺手验（`tooltip.md` §6.4），在那之前照旧按「会占位」设计。

22. **界面状态不随界面关闭而复位。** MEI 的根控件（`mei_ui`）建一次就一直挂在原版容器界面上，
   关掉再开不会重建 —— 脚本改过的显隐、尺寸、文字，下次打开时**还是改过的样子**。
   > 2026-10-26 实机踩了两次：上下栏避让后宽度回不去（`settings.md` §6.1）；
   > 「显示左侧栏」关掉时 `SetVisible(False)`，再打开设置也回不来 —— 开的时候从没写过 `SetVisible(True)`。
   > ⇒ **改控件状态的代码要同时设计复位**：每次开界面按当前状态**两个方向都显式写**（`SetVisible(flag)`，
   > 不要只在某个分支里写 False），关界面时把尺寸还回设计值。守则见 `engineering.md` §7-10。

23. **grid 的集合绑定：`always_when_visible` 要等控件变可见的下一帧才拉。**
   `ItemsGrid` 在面板写满后会解绑（省每帧开销）；写满当帧就解绑的话，数量、角标、悬停文字这类
   `always_when_visible` 的绑定还没拉到新值，就停在上一页的值上。
   > 2026-10-26 实机：收藏栏翻页、第一次收藏后数量与上标经常丢，要多翻几次才对。
   > ⇒ 写满后再等 `PAUSE_AFTER_PASSES`（3）轮完整拉取才解绑（`controls/item/grid.py`，回归位
   > `probe_bookmark_ui.py` K-7）。以后把暂停上提到配方页（`binding_cost.md` 杠杆 B1）时同样要守这一条。

24. **`GetAllChildrenPath` 给的路径「从主节点算起」**：少了开头的 `/variables_button_mappings_and_controls`
   （2026-10-26 实机，工作台：`/safezone_screen_matrix/…/root_screen_panel/content_stack_panel`），
   原样拿去 `GetBaseUIControl` 一条都取不到，补上那一层前缀才对（第一版焦点探针自己认前缀）。
   > 它给的条数比逐层 `GetChildrenName` 少约 2000（18650 vs 20630）—— 少的是运行中建的控件还是 grid 生成的格子**未定**。
   > ⚠ 10-28 起**不再用它**：在 MEI 注入的别人家界面上它抛 C++ 异常、游戏直接退出（§36）；遍历一律逐层 `GetChildrenName`。

25. **引擎调用很贵：实机约 0.1 毫秒一次**（逐层列 20361 次用了 2231 ms）。一个开着 MEI 的工作台有两万个控件 ——
   任何「逐个控件问一遍」的做法都要先算账：能按名字、按可见、按矩形整棵剪掉的先剪掉，只在需要时做（焦点探针 10-28 起查询时才找、
   沿着含那一点的一条往下，一次几十到一两百个控件，`focus.md` §6）；非得全量的分帧做、每帧限时。

26. **每个 grid 用自己的绑定名前缀**（规矩照样守，但它**不是**「只剩一个物品」的病根）。
   SDK 解绑时传的是（界面, 集合名, 绑定名）三样（`mod/client/ui/screenBase.py` 的 `_process_collection_unregister`
   → `gui.unbind_for_collection_handler`），所以原先四个 grid 共用 `meiui.item_panel` 多半无害。
   > 2026-10-26 第五轮按「解绑按名字连带」改成 `binding_prefix(集合名)`（`meiui.<集合名>`），**第六次实机问题还在** ——
   > 真正查出的口子见 §27。前缀照样分开：排查时一眼分得清是谁的绑定
   > （JSON 在 grid 上写同样的 `$binding_name_prefix`，`engineering.md` §5.1e-4，回归位 `probe_ui_slots.py` L-8）。

27. **grid「只显示一个物品」的四个口子**（2026-10-26 第六轮从代码与 SDK 源码查出；哪一个先中**未实证**，四个都堵了，另加自检；
   **10-27 第七次实机没再出现**）：
   1. **JSON 里 grid 的 `grid_dimensions` 是 `[1, 1]`，而行列数只在「尺寸变了」才推给引擎** —— 尺寸碰巧对得上
      （新建的 grid 按百分比撑开后正好等于算出来的尺寸）就一次都不推，引擎停在 1×1。最近浏览更甚：它推不推看的是**收藏栏**的尺寸。
      ⇒ `ItemsGrid` 记住自己推过的行列数，没推过就推（`update_control=False` 也推）。
   2. **在绑定回调里改绑定表**：写满后的暂停是在第 0 格的 `.visible` 回调里数出来的，原先当场解绑 ——
      引擎正挨个拉绑定时改它的表，解掉的还包括正在执行的那一条。收藏栏每次改动都要重排、再写满、再暂停，次数成倍。
      ⇒ 暂停排到下一帧（定时器里）做，期间清过缓存、解过绑就作废。**任何绑定回调里都不要绑定 / 解绑**。
   3. **回调抛异常 = 引擎扔掉那条绑定（§15）**：扔掉的若是 `.visible`，grid 停在已建的几格上，这边还以为绑着、翻页也回不来。
      ⇒ `ItemsGrid` 的回调一律接住异常、记一行 error（同一条绑定只记第一次）、返回默认值，下一帧照常再试。
   4. **一个脚本持有几个 grid，基类却只收拾一个**：收藏栏的最近浏览关界面时从没解绑，绑定留在跨开关存活的界面上（§22），
      下次开界面同名再绑一遍。⇒ `BaseItemsGridScript.GetItemGrids()` 列出全部 grid，关界面逐个**先解绑再清缓存**。
   > 兜底：脚本定时器每 0.2 秒调 `ItemsGrid.SelfCheck` —— 面板没建全又停住 1 秒以上就修（引擎没有最后一格 → 重推行列数；
   > 格子在、`.visible` 却没被拉 → 整套重绑），记 `[MEI/grid] <集合名>: …`；回调异常记 `[MEI/grid] … 抛异常`。
   > **下次实机出现这两种日志，就知道是哪个口子**（`bookmarks.md` §11 第 4 条；回归位 `probe_bookmark_ui.py` K-7 / K-13）。

28. **grid 按 JSON 的尺寸规则摆格子，`SetSize` 管不到**（2026-10-27 第九次实机，日志实测）。
   行距 = 规则算出的高 ÷ 行数：物品栏 `"100%"` → 289 ÷ 14 = **20.64**；收藏栏 `"100%+-60px"` → 229 ÷ 11 = **20.82**；
   最近浏览写死 `60` → 正好 20。MEI 用 `SetSize` 设的「行数 × 20」只改了 `GetSize` 读到的数（日志里 grid 是 280 / 220；`ItemsGrid.SetSize` 10-27 已删，尺寸只靠推行列数），
   stack_panel 怎么排也照规则：收藏栏 grid 顶在 27，最近浏览从 27 + 229 = 256 开始（按 220 该是 247）。
   多出来的高度被均摊进每一行，就是分组底色上下行之间的缝 ——
   物品栏也有，只是更细（每行 0.64 像素，收藏栏 0.82）。
   ⇒ **跟着行列数走的那一轴在 JSON 里写 `"default"`**（行列数 × 格子模板），别写父控件的百分比再拿 `SetSize` 改；
   > 同一类（推断，10-28 配方树第一次实机，待确认）：`SetSize` 是旧接口，只改当前的值、不改尺寸规则 —— JSON 里写相对尺寸（`100%`）的控件排版一刷新就回去，
   > 脚本要撑大它就用 `SetFullSize` 写绝对值（悬浮窗、成就界面都这么写；配方树的 dragpanel / canvas 因此在 JSON 里改写绝对尺寸）。
   grid 比所在面板矮时写锚点（物品栏顶对齐，居中会落在半像素上）。
   > 横向没出事，是因为父控件的宽本来就是「列数 × 20」：包装器的宽由脚本按 `GridWidth` 设（`SetSize(…, True)`）。
   > 先前「stack_panel 把高度改回去了」的推断只对了一半 —— 物品栏的 grid 在普通 panel 里照样均摊，所以「包进普通 panel」治不好。
   > 守则 `engineering.md` §5.1e-7，回归位 `probe_ui_slots.py` L-9。

29. **`follows_cursor` 在 MEI 的覆盖层里管用，但它会盖掉自己的偏移**（2026-10-27 第十一次实机，日志 `跟随光标: follows_cursor 生效`）。
   挂在 `CreateChildControl` 建在原版界面根下的 MEI 覆盖层里、做成 `input_panel`（原版只在输入控件上用过它）就会跟着光标走。
   跟随的控件被引擎摆到光标处，**直接改它的 `offset` 会被盖掉**（作者 10-27 指出）——
   ⇒ 跟随的那层只管跟，里面再包一层 panel，偏移与贴边翻转改里面那层（作者 10-27 的建议，`tooltip.md` §2）。
   > 宿主只有 1 像素、layer −10、`consume_hover_events: false`，免得光标下那一点吃掉格子的点击和悬停 ——
   > 只在 tooltip 显示时亮的那几轮没人报过点不了；一直亮着之后吃不吃待第十五次实机（`tooltip.md` §8 第 2 条）。
   > **给 follows_cursor 的控件 `SetPosition`，它就此不再跟光标**（2026-10-27 第十三次实机）：第三轮在每次显示前给宿主 `SetPosition`
   > （怕它藏着时停在旧位置），之后日志成了 `follows_cursor 不生效`；第二轮从没碰过宿主，判定是「生效」。
   > ⇒ **跟随的控件一律不碰**，位置靠它里面那层的偏移、按它**实际**位置算差（它停在旧位置也摆得对）。
   > **藏着的 follows_cursor 控件多半不跟光标**（2026-10-27 第十四次实机，推断）：宿主跟着 tooltip 一起藏的时候，切换配方会在屏幕右下角闪一下 ——
   > 显出来那一刻它还停在旧位置，偏移照它补了差，下一帧被带到光标处、补的差叠上去。⇒ **要它随时在光标处，就一直亮着**，藏里面那层；
   > 原版跟手的物品图标（`common.inventory_selected_icon_button`）也是常驻光标下、不挡格子的。第十五次实机不再闪即坐实。

30. **SDK 的定时器最短 0.05 秒：`AddTimer(0.0)` 不是「下一帧」**（2026-10-27 读 SDK 源码）。
   `mod/common/utils/timer.py`：`MIN_CALL_TIME = 0.05`，`CallLater` 把小于它的延迟一律抬到 0.05 秒（`AddRepeatedTimer` 同一个类）；
   调度在 `clientApp.TickAppNonChaseFrame` 里跑。⇒ 「排到下一帧」的写法（ItemsGrid 的暂停、动作按钮的重建）其实是 50 毫秒后 ——
   只为离开绑定回调的照用，**要跟手的挂每帧的钩子**：界面代理 `OnTick`（SDK `NativeScreenManager.OnScriptTickClient` 每个脚本帧
   对每个代理调一次，每秒 30 次）或 `MainSys.Update`（同样每秒 30 次）。tooltip 第二轮用 0 秒定时器做悬停核对和摆位置，
   多半是第十二次实机「闪现滞后」的来源之一（未单独实证）。守则 `engineering.md` §7-11。

31. **layer 太高时，有的 `ItemRenderer` 画不出来；100 以下比较安全**（作者 2026-10-27 实测）。
   两个 tooltip 宿主原来是 1000（触屏）/ 1010（PC 的 frame），作者调成 80 之后运行基本无问题。
   ⇒ **装着物品渲染器的控件（格子、tooltip、菜单）layer 不超过 100**；不画物品的控件（悬浮窗的按钮、黑底）不受这条限制。
   守则 `engineering.md` §7-14。
   > **算的是一路累加的有效层级**（JSON 的 `layer` 相对父控件）：tooltip 的 PC frame 是宿主 −10 + 80 = 70、触屏宿主 70 ~ 76，能画；
   > 工具模式拿着的物品原来是 97 / 98（宿主 97 + 物品 1），作者 2026-10-30 第三十二轮实机报画不出来 ⇒ 降到 78，**第三十三轮实机还是画不出来** ⇒ 降到 40
   > （`mei_main.json` 的 `tool_layer`：PC 跟光标的宿主 39、物品 +1，触屏那个 40 —— 刚好压在两栏的格子上：悬浮窗模式下两栏 30、格子里的渲染器再 +7 ~ 9）。
   > 同一个覆盖层里 tooltip（70 多）、配方页的格子（56 ~ 82）照样画得出来，**界线不只是一个数**（推断：算的是一路累加到界面根的层级，各界面的底数不同）——
   > **新加装物品渲染器的控件取保守值，压得住要压的东西就行，别往 80 附近凑**。不画物品的捕获层（96）、悬浮窗（100）不受限。

32. **input_panel 原生拖拽**（NetEase 官方文档 + SDK 源码，2026-10-28；MEI 的悬浮窗实机可拖）：`"draggable": "both"`（或 `horizontal` / `vertical`），
   **必须写 `button_mappings`** 才能拖（官方例子 `button.menu_select → #netease_to_button_id`），`contained: true` 把它夹在父控件里。
   **按在它里面的按钮上不拖**（官方原话：按钮、滚动列表这类接受点击的控件会先接住），要留出能抓的地方（MEI 悬浮窗的握把）。
   引擎记的是「拖拽偏移」—— 相对出生点、**与 `offset` 无关**，`contained` 时夹在 0 到「父控件减自身」之间 ⇒ 放在父控件左上角出生，
   位置用 `asInputPanel().SetOffsetDelta / GetOffsetDelta` 读写（NetEase 的成就界面就这么恢复位置）。
   > 在按钮上用 Python 接按下 / 移动来拖的那条路（NetEase 的 `draggableButton.py`），还得运行时调 `gui.set_handle_button_move_event`，
   > 只写 JSON 的 `is_handle_button_move_event` 多半收不到移动 —— MEI 悬浮窗第一版拖不动大概就是这样（`floating.md` §10）。

33. **`CreateChildControl` 拿「父控件路径 + / + 名字」查重**（SDK `screenNode.py`，2026-10-28 读源码，引擎日志坐实）：
   父控件的路径带结尾的「/」时就成了 `…//名字`，**查重永远查不到**（再调一次就再建一份同名的），**返回值也是 None**（它最后按这条路径取控件）。
   引擎日志里的 `can't not get ctrl, path:…root_screen_panel//mei_ui` 就是它 —— MEI 的 `GetRootControl` 原来按 `RootPath + "/"` 取根面板。
   ⇒ **父控件的路径不带结尾的「/」**（`UIScriptMain.GetRootControl` 已改），建之前自己按正确的路径查一下有没有。

34. **往原版界面注入控件：在 `PushScreenEvent` 里当场做**（读 SDK 源码 2026-10-28，NetEase 自己的 `hudScreenAIFuncManager` / `pauseScreenMgr` 都这么写）。
   那一刻 `clientApi.GetTopUINode()` 就是刚压上来的界面（核对 `GetScreenName()` == 事件的 `screenDef`）；没有 Python 节点的原版界面它会**现建一个**
   `ScreenNode` 并 `process_binding`，出栈时 SDK 自己 `destroy_pushed_screen`（`process_unbinding` 会把挂在节点上的绑定一起摘掉）。
   ⇒ 不要在别的时机「过几帧看栈顶」去注入（每次都会给栈顶界面现建节点，包括有代理的界面）；HUD 只在进存档时压栈一次。
   > MEI 第一版就是「压栈 / 出栈后过两帧看栈顶、每次回到 HUD 都拆了重建」，开着 HUD 悬浮窗进存档三次都崩（原因未实证，`floating.md` §10）。

35. **PushScreen 开的界面：`Create` 之后 SDK 紧接着 `process_binding`**（读 SDK `uiManager.py` 2026-10-28，MEI 自己的界面与配方树实机可用）：
   `CheckInit` 里先 `node.Create()`、再 `node.process_binding(node.screen_name)` —— 按 `dir(self)` 把带 `binding_flags` 的属性全挂一遍。
   `ScreenBinder`（`utils/binder.py`）的转发函数就挂在界面节点上、带着这个标记 ⇒ **在 `Create` 里经 `ScreenBinder` 挂的绑定会被挂两遍**。
   节点在 `PushScreen` 那一刻就进了栈，**`Update` 在 `Create` 之前就开始被调**。出栈（`PopScreen`）是 `process_unbinding` → `Destroy` → `gui.pop_screen`，
   **`Destroy` 抛异常界面就弹不掉**（SDK 不接）。注册表（`RegisterUI`）每次进存档时被清空。`PushScreen` 的第三个参数原样交给界面类的 `__init__`
   （Python 对象也行）；同一个界面已经在栈里时再压给 None。
   ⇒ MEI 自己的界面（`floating/screen.py`）：`Create` 只记一笔、第一次 `Update` 再建；覆写 `process_unbinding` 先拆 MEI；
   `Update` / `Destroy` 一律接住异常；每次 `UiInitFinished` 注册。

36. **在 MEI 注入的别人家界面（HUD、强制兼容）上用 `GetAllChildrenPath` 列整棵树，引擎在主线程上抛一个没人接的 C++ 异常，游戏退出**
   （2026-10-28，UniSDK CrashHunter 坐实；是 `GetAllChildrenPath` 本身还是紧跟着的 `GetBaseUIControl` **未单独实证**，头号嫌疑前者）。
   CrashHunter（游戏目录的 `CrashHunter_PC3.dll`）的日志在 `%LOCALAPPDATA%\UniSDK\CrashDump\1.7.0\crashHunterLog_<日期>_<pid>.txt`：
   今天 11 次都是 `code = 0xe06d7363`，发生在第一版焦点探针挂上后 **0.30 秒**（后台第一次开扫那一帧，那一帧只调了这两样）；
   之后约 0.6 秒是 CrashHunter 写转储、**上传到网易并删掉本地文件** —— 所以 WER、事件日志里都没有，Python 日志里像是「挂上后约 1 秒断开」。
   能扫的树（23 个支持的界面、MEI 自己的界面、蔚蓝给 MEI 的配方页）里**一张 `tiled` 图都没有**，崩的树（HUD 的经验条、蔚蓝机器的电力条 / 流体显示）
   里**都有**（相关性推断，§18 记过 tiled 是内部控件集合）。保守模式（只认名字带 item 的、先看可见再读）管的是读物品那一步，无效，已撤。
   ⇒ **不用 `GetAllChildrenPath`，要遍历就逐层 `GetChildrenName`**（网易自己的代码也这么写；别的模组在 HUD 上这么递归没出事）。
   焦点探针 10-28 改成查询时递归、只逐层列（`focus.md`）。
   > **Python 日志（`MCSafaiaServer\log_storages\<hash>.txt`）的最后一行不一定是崩溃前写的最后一行**：游戏这边每行当场发出，可异常前几毫秒写的
   > 那一行没落进来（多半丢在 Safaia 那头，推断）—— 查崩溃要和 CrashHunter 的毫秒时间（`g79\Backup\exception_handle_stat.txt`）对着看。

37. **原版格子的高亮与悬停文字绑在 `#show_persistent_bundle_hover_text` 上**（2026-10-28 读原版 JSON，作者实机看到现象）：
   `common.highlight_slot_panel` 里白色高亮 `highlight`（悬停文字 `hover_text` 是它的子控件）与 `white_border` 的 `#visible` 都绑它。
   容器界面的控制器在触屏上给 false（高亮、悬停文字一起藏）；**HUD 和 PushScreen 开的界面没有容器的控制器，这个绑定没人给，按默认值亮着** ——
   于是 MEI 在那里的格子，触屏划过会和 PC 一样亮出高亮和原版悬停文字。
   ⇒ MEI 的 `highlight_panel` 去掉了这条绑定（触屏上也亮高亮），原版悬停文字在触屏上靠 `HoverText` 给空串藏（`tooltip.md` §6.13）。

38. **SDK 的 `GridUIControl.GetGridItem` 在格子还没建出来时 `print` 一行 `error: cannot find position (x, y) in grid, grid item may not be created`**
   （`mod/client/ui/controls/gridUIControl.py`，2026-10-28 作者报每次开界面都刷）。刚推完行列数的那几帧、所在那一栏藏着时（引擎不建格子）都问不到。
   ⇒ 拿它判断「行列数推上去没有」之前，先等格子真被拉过绑定（`ItemsGrid` 数第 0 格 `.visible` 的轮数，`DIMS_CHECK_PASSES`），藏着的栏不问。
   > 推论（10-28 配方树菜单的配方预览，第一次实机每一类都等到超时）：**透明着建的东西，一路上的父控件都得亮着** —— 建在 `visible: false` 的插槽里、
   > 或宿主还藏着，里面的 grid 一个格子都不长。要藏就把外面那层的 alpha 写 0（带 `propagate_alpha`），不要 `SetVisible(False)`（`engineering.md` §7-12）。

39. **`SetPosition` 给的是相对父控件左上角的坐标，不是相对锚点的偏移**（SDK 文档原话「设置控件相对父节点的坐标」；2026-10-28 配方树第三次实机，作者看到的现象坐实）。
   汇总右上那句说明在 JSON 里锚右上、`offset [0, 3]`，脚本 `SetPosition((0, 3))` 想让它留在原处 —— 结果被拽到父控件最左、挡在页签底下。
   ⇒ **脚本只挪锚在左上的控件**（MEI 的菜单、配方树的画布都是这么写的）；要右对齐、换一行这类，就在 JSON 里放好锚点的几个控件，脚本只换字、切显隐。
   回归位：`probe_recipe_tree_ui.py` 的假控件对每一次 `SetPosition` 断言 JSON 锚点是左上（不写锚点就是居中，同样不许）。

40. **自定义按键**（ModSDK 3.7 起；读 SDK 源码与原版 JSON 2026-10-28，作者实机通过：设置里显示中文名、改键生效、重进存档还在）：PlayerView 组件
   `RegisterCustomKeyMapping(name, key, category)` 只收 `KeyBoardType` 枚举里有的**整数**（SDK 先比对枚举，不在里面直接返回 False、打一行 print）；
   `GetKeyMappings(name)` 给当前键码，没有给 0（玩家没改过就是默认键）。事件 `OnCustomKeyPressInGame`（name / key / category / isDown / screenName，
   和 `OnKeyPressInGame` 同属 ControlClientEvent）、`OnCustomKeyChangedEvent`（name / oldKey / newKey）。
   网易在控制设置里加了「自定义按键」区（`controls_section.json` 的 `#ntes_custom_keymapping_name` / `#ntes_custom_category_label`），名字由 label 显示 ——
   MEI 注册名直接写成 `.lang` 的键（`key.mei.*`），label 自己本地化 —— 实机设置里显示的是中文名。
   姊妹工程 Truth 实测过**修饰键（Alt 等）的按名事件可能不下发** ⇒ 按名事件之外再按 `GetKeyMappings` 认裸按键，两路去重（`mei_ui/hotkeys/manager.py`）。


41. **子控件可以伸出父控件的矩形，按父控件的矩形剪枝会漏**（读原版 JSON 2026-10-28，作者实机报的焦点死区与它吻合；两遍查找修好后实机通过）。
   JSON UI 不裁剪（除非 `clips_children`），父控件的 `GetSize` 只是它自己的尺寸。原版 `ui_common.json` 的 `inventory_panel` 写死 `[88, 83]`，
   里面的 `inventory_grid` 写死 `[162, 54]`、都锚底边中间 —— grid 两边各伸出 37，经典布局的容器界面背包最左两列、最右两列都在 panel 外面。
   ⇒ **任何「按矩形逐层往下找」都要防这一手**：焦点探针第一遍严格剪枝、没找到再放宽 64 找第二遍（`focus.md` §1、§8.3）；尺寸为 0 的锚点不拿来剪枝。

42. **裸按键里的修饰键**（2026-10-28 第九轮实机，背包界面；探针验完已删，细节在 `bookmarks.md` §12.3）：Shift / Ctrl / Alt 在 `OnKeyPressInGame` 里报
   16 / 17 / 18，按下、松开都有，**按住不连发**；按着修饰键按字母，字母照常来、按住会接连来「按下」（约 0.15 秒一次）；**中文输入法吃掉的键报 229**
   （VK_PROCESSKEY，真正的键不知道）；按着修饰键滚滚轮，滚轮事件照常来（只有方向）。引擎没有「这个键按着没有」的接口，也没有窗口失焦的事件。
   ⇒ 修饰键状态自己记、界面压栈 / 出栈时清掉；**不能拿「多久没收到按下」判断松开**（不连发，按住和卡住分不开）；229 不当快捷键、录键时提示切英文。
   设置界面里也收得到（10-29 按键绑定实机通过，录键就靠它）；HUD、MEI 自己的界面没单独验。

43. **引擎的配方查询不给配方 identifier**（2026-10-29 实机，片段 `debug/ingame/recipe_id_probe.py`）：`GetRecipesByResult` 的每一条是 dict ——
   有序配方 `{key, pattern, result}`（`key` 的每一格 `{item: str 或 list, data?}`；`result` 是 `[{item, data, count?}]`，不写 count 就是 1），
   熔炉 `{input, output}`（两个字符串；第三方注册的带 `:附加值` 后缀，如 `skybluetech:iron_dust:0`）—— **没有 identifier**。
   `GetRecipeByRecipeId(identifier)` 查得到、返回里带 `identifier`（`minecraft:stick`、`minecraft:iron_ingot_from_nuggets`），可**没有列全部 identifier 的接口**，
   按产物猜的名字（`minecraft:chest`、`minecraft:crafting_table`）给 `{}`。list 形态的原料是引擎把 tag 展开了（箱子、木棍的木板是 12 种、火把的煤是
   `[charcoal, coal]`），模组往这个 tag 里加物品，list 就跟着变。原版还有**重复与被包含的配方**：火把 #0 与 #2 一模一样（合并点按 Id 去重了）；
   箱子除了「任意木板」还有只收绯红木板、红树木板的几条（基岩版按木种分开的老配方）。
   ⇒ `Recipe.Id` 只能用内容哈希；要它不随装卸模组变，得把燃料、list 原料折叠成 tag（`README.md` §8 P1-3）。

44. **物品的 tag 与燃料时长**（2026-10-29 实机，片段 `debug/ingame/item_tags_probe.py`）：`GetItemTags` 与 `GetItemBasicInfo` 的 `tags`
   **一模一样**（MEI 注册物品时已经缓存在 `Item.Info.Tags`，要用不用再调引擎）。燃料时长（`fuelDuration`，单位秒）：物品类燃料照常
   （煤 / 木炭 80、木棍 5、木镐 10、烈焰棒 120、岩浆桶 1000），**方块类燃料全是 0**（§11）。和燃料有关的 tag：`minecraft:logs_that_burn`
   正好是能烧的原木（绯红菌柄只有 `crimson_stems` / `logs`）；`minecraft:planks`、`minecraft:wooden_slabs` **连不能烧的绯红 / 诡异木也带**；
   楼梯、栅栏、工作台、箱子、书架、梯子、树苗、脚手架、煤炭块、干海带块、竹子**没有 tag**。煤 / 木炭带 `minecraft:coals`。
   引擎展开成 list 的原料，成员的公共 tag 正好是配方里写的那一个（木板 12 种 → `minecraft:planks`，煤 / 木炭 → `minecraft:coals`）。
   ⇒ 燃料表 = `fuelDuration > 0` ∪ `logs_that_burn` ∪ 木板 / 木台阶去掉下界木（按名字）；list 原料按公共 tag 折叠（`README.md` §8 P1-3）。

45. **原版七种工作站的配方查询**（2026-10-29 实机，片段 `debug/ingame/recipe_types_probe.py`；S6 照它写，`docs/architecture/recipe_types.md`）：
   - **熔炉家族**：`blast_furnace` / `smoker` / `campfire` / `soul_campfire` 四个 tag 给的都是熔炉的形状 `{input, output}`（两个字符串，第三方的带 `:附加值`）；
     高炉是矿石与金属工具 / 盔甲回炉，烟熏炉与营火是食物，**和熔炉查到的那几条一模一样**；**营火与灵魂营火查到的一条不差**。
   - **切石机、制图台、锻造台**：无序配方的形状 `{ingredients: [{item, data?}], result: [{item, data, count?}]}`（有的格子不写 data）。
     切石机按产物查用 aux 0；产物 id 是拍平的（`stone_brick_slab`、`normal_stone_slab`，一次 2 个的写 count）。
     制图台**只有两条**：纸 → 空地图、纸 + 指南针 → 空定位地图（`empty_map` 的 aux 2）；复制、扩大、锁定地图写死在引擎里，拿空地图 / 地图 / 玻璃板查都是 0 条。
     锻造台：转换是三格（模板、物品、材料）单个物品 → 一个产物（原版九样下界合金升级）；**纹饰只有一条**，三格是引擎展开的物品列表
     （全部模板、全部能加纹饰的盔甲、全部材料）、**`result` 是空表** —— 按产物查只给转换，纹饰只在按原料查（模板、盔甲、材料）时出来。
   - **酿造**：混合配方 `{input: 'minecraft:potion_type:awkward', reagent: 'minecraft:blaze_powder', output: 'minecraft:potion_type:strength'}`，
     换容配方 `{input: 'minecraft:potion', reagent: 'minecraft:gunpowder', output: 'minecraft:splash_potion'}`（喷溅 + 龙息 → 滞留同理）。
     药水按**类型全名**查、不认 aux（拿药水物品按原料查，任何 aux 都只给换容那一条；按产物查 `minecraft:potion` aux 31 给 0 条）；
     **拿催化剂按原料查一条都没有**（烈焰粉、火药、龙息……）⇒ 用途只能自己建桶。药水类型名的查询**会串到别的 tag**（拿 `potion_type:awkward`
     查 `crafting_table` 给 16 条酿造配方），按物品查不串。从水开始按原料一路查：45 种药水类型、69 条混合配方、19 种催化剂
     （含旋风棒、黏液块 `minecraft:slime`、石头、蜘蛛网、海龟壳、幻翼膜、河豚）。
   - **药水的 aux ↔ 类型名**（下标就是 aux；物品名、悬停里的时长、两个方向的条数逐个对过）：0 水瓶、1 平凡、2 长久平凡、3 浓稠、4 粗制、5 / 6 夜视、
     7 / 8 隐身、9 ~ 11 跳跃、12 / 13 抗火、14 ~ 16 迅捷、17 / 18 迟缓、19 / 20 水肺、21 / 22 治疗、23 / 24 伤害、25 ~ 27 剧毒、28 ~ 30 再生、
     31 ~ 33 力量、34 / 35 虚弱、36 衰变（没有酿造配方，名字查不到）、37 ~ 39 神龟、40 / 41 缓降、42 迟缓 IV（`strong_slowness`，不按顺序）、
     43 蓄风、44 盘丝、45 渗浆、46 虫蚀；47 往后没有。名字写法 `nightvision`（不是 `night_vision`）；`long_mundane` 引擎认（按原料查有 1 条），不在全集里。
   - **MEI 的物品表**里药水、喷溅、滞留、地图都只有 aux 0（`RegItemFromIdList` 每个 id 造一个）⇒ 要显示别的 aux 得 `AddItems` 加变体；
     `GetItemBasicInfo(药水, aux)` 给的名字各不一样，但没有药水类型的字段。七个工作站都在物品表里（切石机有新旧两个 id，`stonecutter_block` 是现在用的那个）。
   ⇒ 熔炉家族换 tag、切石机 / 制图台 / 锻造台走一个无序形状的解析、酿造自己凑全表建桶、药水 aux 直接映射、要显示的变体由类型包加（`recipe_types.md`）。

46. **grid 的行列数变了，引擎重建格子；之前设在格子上的物品图标跟着旧控件没了**（2026-10-29 第二十轮，作者实机的现象 + SDK 源码推断，未单独实证）。
   SDK 的控件对象只是「界面名 + 路径」（`ItemRendererUIControl.SetUiItem` → `gui.set_ui_item(界面, FullPath(), …)`），引擎那边换了一个控件，路径一样也分不出来。
   `ItemsGrid` 的面板在 `.visible` 回调里建、建的时候 `SetUiItem` 一次 —— 推完行列数、引擎还没重建的那一轮拉到的格子，面板建在旧控件上，
   重建出来的新控件没有图标（可见、数量、悬停文字走绑定，会自己拉到）。实机：配方页的工作站有时候少一两个，**普遍是第一个**（从 1 格变 2 格，第一格是旧的）。
   **第二十一轮实机**：熔炉 → 高炉（工作站 2 格 → 1 格）第 2、3 轮补画过了，高炉那一格还是空的 —— 格子重建得比第 3 轮晚
   （§38 记过推完行列数要「那几帧」格子才建出来）；写满后暂停了绑定的话，晚建的新格子连可见、数量这些也拉不到值。
   ⇒ 行列数没变就别推（`SetGridDimension(…, False)` 推过同一组就不推）；跟着内容走的 grid，内容没变就什么都不动；推了的：
   - 引擎在格子重新排列后发 **`GridComponentSizeChangedClientEvent`**（参数 `path`：grid 的路径，从 UI 根节点算起，SDK 2.9 起有；
     网易自己的宠物背包界面收到它就把格子里的东西重设一遍）—— 客户端主系统转给 `grid.grid_rearranged`，路径对得上的 `ItemsGrid`
     当场重设缓存里的图标（`OnRearranged`），暂停了的绑定排到下一帧恢复；
   - 推完行列数、格子重新排列之后的几轮里**核对**图标（`REPAINT_PASSES`，实例的 `RepaintPasses`）：`GetUiItem` 读回来不是这一格的物品才重设，
     按拉绑定的轮数数、不按时间（换类型那一帧很重，定时器可能赶在重建之前到）；
   - 只有几格的 grid（配方页的工作站）不暂停绑定、核对 30 轮（约一秒）。
   这个事件对 MEI 覆盖层里的 grid 发不发、路径长什么样**未实证**（路径按「一边是另一边的结尾」认，开头那一层有没有都行）。
   回归位 `probe_bookmark_ui.py` K-13b / K-13c、`probe_script_host.py` H-5。

47. **`SetLayer` 开销极大，不建议用**（作者 2026-10-30 审代码时指出）。SDK 文档：缺省 `syncRefresh=True` 同一帧就按这个控件的层级重算，
   一帧里大量设置要传 False、完事调一次 `ScreenNode.UpdateScreen` —— 开着 MEI 的工作台有两万多个控件（§25），重算一次就不便宜。
   ⇒ 层级尽量写在 JSON 里、让控件生下来就是要的那一档；非换不可的，先 `GetLayer` 比一比、一样就不写（悬浮窗的两栏，`floating.md` §7）。
   **游戏也没有「配方变了」的客户端事件**（同日查 SDK：配方相关的只有 `ShapedRecipeTriggeredClientEvent`）—— 服务端 `AddRecipe` / `RemoveRecipe` /
   `AddBrewingRecipes` 动态改了配方，客户端收不到通知，MEI 记下的答案要到重进世界才换新。

48. **引擎会在 C 层留下没清掉的异常，抛在后面随便哪一行上**（2026-10-30 第三十一轮，作者贴回的日志 + CPython 源码推断，未单独实证）。
   物品栏第 0 格建面板时 `"/{}{}".format(self.ChildName, index + 1)` 抛 `TypeError: bad argument type for built-in operation` ——
   这一行只有字符串、整数，自己不会错；这句话是 C 层 `PyErr_BadArgument()` 的（unicode 那一族接口拿到了不是 unicode 的东西），而 py2 的 `str.format`
   解析自动编号的 `{}` 时会查一次 `PyErr_Occurred`（stringlib 的 `field_name_split`）：**某个 C 函数设了错误却照常返回了值**，错误一直挂着，
   直到下一个查它的操作把它抛出来。只坏第 0 格，是因为每一轮第 0 格最先建、最先撞上（撞上即清，后面的格子就好了）；只在开着大面积遮挡的界面时坏，
   说明留下它的那个调用只在那时跑（多半是那个界面上的绑定或引擎调用，没查清）。
   ⇒ MEI 的绑定回调进门先用同一种操作静默接住一次（`utils/binder.py` 的转发函数，`_PROBE`），第 0 格因此不再空着。
   **以后看到某一行莫名抛 C 层的 TypeError，先想这一条**。回归位 `probe_modes.py` M-18。
   > 第三十一 ~ 三十二轮为了找来源加过诊断：接住时记一行 `[MEI/stray]`（在哪接住、哪个界面、上一条跑完的 MEI 绑定）、主节点每帧的几步之间各查一次（`utils/stray.py`）。
   > **第三十三轮删了**（作者：暂不修，进待办 —— `README.md` §8 P3-7），静默接住留着。
   > **第三十二轮实机的日志定了方向**：接住处各不相同（物品栏、收藏栏、配方页的第 0 格、悬停探针、模式按钮的悬停字……，都是那一轮第一个被拉的 MEI 绑定），
   > 「上一条跑完的 MEI 绑定」**一律是 `#mei.tool.touch`**（MEI 覆盖层里最后一条），主节点每帧的几处一次也没接住 ⇒ 不是 MEI 的绑定、也不是 MEI 每帧的处理留下的，
   > 是每一轮拉绑定开头、MEI 覆盖层之前的 Python 绑定（原版 / 别的模组的控件在树里排在前面）。当时开着**蔚蓝的电动机件加工台**：
   > 蔚蓝机器界面的颜色绑定（`BF_BindColor`）一律返回三元组 `(r, g, b)`，网易的颜色接口都是 RGBA 四元组（`GetFogColor`、告示牌颜色……）——
   > 引擎多半按四个分量读、第四个取空，`PyFloat_AsDouble(NULL)` 设的正是这句 `bad argument type for built-in operation`（推断，未单独实证）。
   > 蔚蓝那边返回 `(r, g, b, 1.0)` 应该就没了（`docs/thirdparty/skybluetech.md` §8.14）；MEI 这边已经接住，不影响。

49. **3.10 的按 tag 查接口**（2026-10-30 第三十九轮，**未实证** —— 官方网页文档、MC Studio 的接口提示、SDK 源码副本里都还没有，照作者贴的更新说明写的）：
   「新增方块tag查询接口 `LookupBlocksByBlockTag`（服务端 / 客户端），根据 netease_tags 中注册的方块 tag 名查找该 tag 下所有方块，支持 # 引用的标签自动展开；
   同一 tag 名被多个模组注册时自动合并去重；未注册的原版 tag 也可直接查询」，物品的 `LookupItemsByItemTag` 同理。
   MEI 的写法（`registry/tags.py`）：物品在物品组件（`CreateItem`，和 `GetItemTags` 一处）、方块在方块信息组件（`CreateBlockInfo`，再试 `CreateBlock`）上找，
   `getattr` 探测；返回值认名字的列表、带名字的字典（`itemName` / `name` / `identifier` / `blockName`）、「id:附加值」、字典的键，None 当空，别的写法退回物品信息里的 tags。
   ⇒ 片段 `debug/ingame/tag_lookup_probe.py`（输出带 `[MEI/tl]`）跑一次，看挂在哪个组件上、返回值长什么样、和 `GetItemTags` 对不对得上，再把这一条改成实测的。

50. **上架机审：api_check 与 code_check**（2026-10-30 第四十轮，第一次自测上架被拦，错误码 18；回归位 `probe_review.py`，守则 `engineering.md` §7-21）：
   - **api_check 不许 `__import__`**（报了三条，仓里只有两处：装配器导内置扩展、原版扩展导类型子包；第三条没找到对应，多半是同一处按打包的变体重复计了）⇒ 动态导入一律 `clientApi.ImportModule(路径)` / `serverApi.ImportModule`（SDK 2.8 起；内部就是 `importlib.import_module`，只认已加载的 mod 里的模块，不在就给 None，导入时抛的照样抛）。
   - **code_check 是 pylint 的错误级检查**，带一套 `mod` 的存根：`from mod.client.ui.viewBinder import ViewBinder` 报 E0401 / E0611（机审的存根里没有这个模块 —— 本机装的 mc_netease_sdk 3.4 倒是有，以机审为准）⇒ **引擎只从公开入口 import**（`mod.client.extraClientApi`、`mod.server.extraServerApi`、`mod.common.mod`、`mod_log` 的 `logger`），ViewBinder 用 `clientApi.GetViewBinderCls()` 取（EterniaModCore 也这么取）。
   - **E1136 unsubscriptable-object**：`notice = getattr(self, "Notice", None)`，判了空再 `notice[0]` 也被拦 —— astroid 推断 `getattr` 只拿那个属性**第一次赋的值**（`__init__` 里的 None），认定 `notice` 就是 None。直接读 `self.Notice` 不拦（几处赋值推出几个值，不确定就不报），最稳的是**不对可能是 None 的东西取下标、解包**：拆成单独的字段（配方页的提示拆成了 `NoticeText` / `NoticeUntil`）。
   - 本地 pylint 1.9.5 报、机审没报的：E1111（存根里的接口都只有 `pass`）、E1102 / E1101（推断成 None 的可调用、抽象基类上的 `__eq__`）—— 机审没开这几种。
   - **本地复现**：`C:\Python27\python.exe -m pip install --target <目录> pylint==1.9.5`（py2 的最后一版），设 `MEI_PYLINT=<目录>` 跑 `probe_review.py`（只开 E0401 / E0611 / E1136 / E0633）；拿旧代码试过，它报的 E1136 与机审同一行。
   - 机审过了不等于接口开放：MEI 还用着 `ScreenNode._process_collection` 一族（动态绑定，`utils/binder.py`，和 EterniaModCore 的 ScreenTool 同一个做法）、覆写 `process_unbinding`（MEI 自己的界面、配方树）、`mod_log.engine_logger`（`LogPatcher` 批量绑定时静音 SDK 每条绑定一行的 info；第四十轮改成用到时 `getattr` 取、取不到就不静音，不再 `from mod_log import engine_logger`）—— 这次都没被拦。

## 架构关键点

### 自带的轮子（2026-10-27 与前置 EterniaModCore 解耦）

作者定：本仓不再有 Eternia 的概念，用到的工具按项目习惯**重新封装**（改名、继承改组合），拼音提炼成轻量库。
玩家只装 MEI 一个 addon；`netease_require.json` 的 `modRequire` 是空的，原来的跨仓契约（`EterniaMods` 登记表、
`StrictVersion` 版本格式）与「早于前置加载就是时序 bug」一并作废。

| 原来（前置） | 现在 | 要点 |
|---|---|---|
| `coreModManager.RegisterMod` | `modMain.py` 在 `@Mod.InitServer` / `@Mod.InitClient` 里 `RegisterSystem` | 命名空间 `NameConst.NameSpace`（"MoreEnoughItems"）、系统名与路径取 `NameConst` / `PathConst`；客户端先 `RegisterAll` 对外组件；两端的 API 在各自初始化里才 import |
| `EtrClientSystem` / `EtrServerSystem` | SDK 的 `GetClientSystemCls()` / `GetServerSystemCls()` | 主系统里组合一个 `self.Events` |
| `EventTool` | `utils/events.py` 的 `EventListener` | 组合着用（`self.Events = EventListener(system, "client"/"server")`）；`Listen(事件, 回调, 命名空间=引擎, 系统名=引擎)`，自定义事件也走它；按（事件, 回调）记账，`UnlistenAll` 只摘自己挂的；回调可以是任意可调用对象（引擎结论 §13） |
| `ScreenTool` | `utils/binder.py` 的 `ScreenBinder` | 组合着用（`self.Bindings`）；`Bind(回调, flag, 绑定名, 集合名=None)` 按 flag 自动分普通 / 集合（引擎结论 §9）、`Unbind` / `UnbindAll`；只给客户端用，所以 `utils` 门面不导出它 |
| `EtrCustomUIScreenProxy` | `ui_script/proxy/base.py` 的 `ScreenProxy` | SDK 代理类 + `ScreenNode` + `Bindings`；`CustomProxyScript`、`SettingsProxy` 都继承它 |
| `ScreenTool.GetEditBoxRawText` | `utilities.GetEditBoxRawText(control)` | 输入框原文（屏蔽词处理之前的字） |
| `coreUtils.GetNativeUIManagerIns()` | `clientApi.GetNativeScreenManagerCls().instance()` | `ProxyManager.RegisterProxyScript` 里；SDK 返回 False（类找不到、不是代理类、这一局已挂过）也算没挂上 |
| `PinyinSearchEngine` + pypinyin（3.4 MB） | `libs/pinyin_lite`（`PinyinIndex`，字表 111 KB） | 见下 |

**`libs/pinyin_lite`**（作者定：多读音候选、只收基本区、打分照搬、只修明显的错）：
字表 `table.py` 由 `debug/scripts/gen_pinyin_lite.py` 从 pypinyin 0.55.0 的 `pinyin_dict.py` 生成（MIT，许可全文
`LICENSE.txt` 随表放着）—— U+4E00–U+9FFF 共 20924 字、去声调、ü 写 v，4940 个字有不止一个读音，第一次用到才建表。
`PinyinIndex` 照搬旧引擎的四个索引与全部打分，多读音这样接：索引收各种读法的片段；打分时主读音那种拼法含它就按它算，
不含才看别的拼法（最多展开 32 种）；逐字匹配与子序列认每个读音。顺手修了三处（旧引擎都是静默零结果）：5 个字以上的汉字查询、
大小写（查询转小写、原文没转）、带数字符号的半角查询（那一支从不打分）；`Search` 返回喂进去的那个对象（物品名索引拿它反查，
类型对不上就查不到）。离线对照原版 1558 个物品名、3015 条查询：旧引擎的结果一条没丢，个别分数因主读音不同略变；
桌面上建索引约 1.2 倍、搜索约 1.45 倍耗时，内存反而少一半（不再加载 pypinyin 31 MB 的词组表）。
库只用相对 import、不碰引擎也不碰 MEIScripts 的其他包，物品搜索只经 `registry/search.py` 用它（回归位 `probe_pinyin.py`）。
> `libs/pinyin-lite` 是作者给的名字，Python 包名不能带连字符，落地成 `pinyin_lite`。
> 包名 `libs` 留给以后别的自带库；第三方库照这个样子放：自包含、带上游许可。

### 双端分工

服务端做三件事：`ClientLoadAddonsFinishServerEvent` 时把 `[可见 id 表, 隐藏 id 表]`
发给客户端（`server/main_sys.py`，结果缓存在 `self.ItemIds`）；应答快捷合成的搬运与作弊模式的给物品（`network/protocol/`，
发起者只信引擎给的 `__id__`，`modes.md` §3）。
**所有配方处理与 UI 逻辑都在客户端**。

客户端 `SyncLoadedItems` 的初始化序列（`client/main_sys.py`）：
`ItemManager.LoadItemIds(可见+隐藏)` → `ItemManager.Reset()` →
`ItemManager.RegItemFromIdList(可见 + 隐藏)` →
`ItemSearchIndex.Rebuild(ItemManager.GetBrowsableItems())` →
配方查询缓存注入 → `ExtensionLoader.Shutdown()/Boot()`。
> **隐藏物品也要注册**：`LookUpItem` 认它们而 `items` 不认，那道口子会造出
> 索引不到的游离 `Item`（物品书签反查踩过）。不变量是 **`items` 的 id 集 == `item_ids`**。
> 装配排在物品之后**不是硬约束**，三个装配阶段一处都不读物品表 —— 见 `item_model.md` §5.3。

### 分层与依赖方向

```
ui_script（UI 层）→ registry → common → constants
                        ↑
mei_mod/{client,server,extensions,state}（装配层）→ 以上全部
libs/（自带库）在最底层：谁都能 import，它不 import MEIScripts 的任何包
```
`ui_script` 物理上是 `mei_mod` 的子包，但**逻辑上是最上层**，下层不得反向 import 它
（现存两处违例见上「待偿还」）。完整规则见 `engineering.md` §2。

### 界面文字（2026-10-29 第二十轮）

**界面上要从 `.lang` 查的字一律经 `utils/lang.localize(键)`**（对外 `ctx.Utils.localize`）—— 整个模组只有这一处向引擎要本地化文字（`GetChinese`）、
只有这一份缓存；**类型名一律 `RecipeManager.GetDisplayText(类型)`**（配方页顶上、tooltip 的配方预览、配方树都是它）。不要自己调 `GetChinese`、
不要自己记一张名字表：原先 tooltip、配方树、快捷键帮助、设置页、原版扩展各查各的、各记一份，配方树里一条高炉配方出了两个类型名
（作者：「不要出现两个地方两个文案表这种明显是设计失误的问题」）。交给 JSON 标签自己本地化的（`text` 写键）不算，那是引擎的一条路。
守它的是 `probe_cleanup.py` C-4（全仓只有 `utils/lang.py` 调 `GetChinese`、几张旧表都没了）。

### 加一个新配方类型

内置类型在 `mei_mod/extensions/vanilla/` 下**一个类型一个包**，照 `furnace/` 抄：

| 文件 | 内容 |
|---|---|
| `__init__.py` | 门面导出 `CATEGORY`（`RecipeCategory`：`category_id` / `name_key` 本地化键**不硬编码中文** / `icon` / `control_def` / `stations` / `sort_index`）、`SOURCE`（`RecipeSource` 子类）、`UI_SCRIPT`，支持快捷合成的再加 `POLICY` |
| `types.py` | 该类型的 `Recipe` 子类（**不在 `common/classes/types/` 里** —— 那里只放框架通用类型）|
| `source.py` | `QueryByOutput` / `QueryByInput`（能给全表的再实现 `GetAll` + `CAN_ENUMERATE`）|
| `ui_script.py` | 继承 `RecipeUIScript` 的配方页脚本（不写 `TYPE`：类型由装配器 `RegisterScript` 定，几个类型可以共用一个脚本）|
| JSON | 配方 JSON 规范（`engineering.md` §5）：行叫 `recipe`、里面 `wrapper/content`，wrapper 与 content 写算出来的绝对尺寸、content 自包含；`RECIPES_GRID` 后紧跟一行 `"PREVIEW@mei_recipe_common.preview": {"$recipe_content_template": "<命名空间>.content_panel"}`，不写尺寸。tooltip 预览缺省就有，不要的在 `CATEGORY` 写 `preview_def=None`（`tooltip.md` §4）|

**两条规矩**（2026-10-29）：① **驱动机器的东西（燃料、能量）不进配方本身** —— 不放 `Inputs`、也不放 `Catalysts`（作者定：它们不是配方的内容，
放进去还会让 `Recipe.Id` 跟着它们变），界面要画就由类型自己的配方页脚本去取（熔炉的燃料格问 `furnace/fuels.py`）；
② 引擎给的 list 形态原料（它把 tag 展开成的物品列表）走 `EngineRecipeSource.MakeListIngredient`（按公共 tag 折叠，`tools/parser.py`），别自己 `Ingredient(stacks)`。

**配方页的规矩**（作者 2026-10-29 第十九轮定，`recipe_types.md` §2）：**每个类型自己的 JSON 命名空间、自己的配方页脚本**，不做「一进一出」那种几个类型共用的界面；
**布局照原版的界面**（`vanilla/ui/*_screen.json`），**进度条 / 箭头用原版的控件**（不带绑定的直接 `@原版命名空间.控件`；绑着容器进度的在自己的命名空间里照原版写一份，
换成自己的 clip 动画）；几格画同一样东西就写同一个绑定名前缀（镜像格，物品图标由 `ItemPanel.AddMirror` 一起设）。

**几样现成的**（2026-10-29 S6）：配方页脚本可以继承 `tools/pages.py` 的 `RecipePageScript`（只是 Python 这一侧的便利）—— `Slot("<格子路径>")` 取
`/wrapper/content/<格子路径>/0`，**格子路径的最后一段与绑定组前缀 `mei_ui.recipe.<名字>` 的最后一段一致**（镜像格名字后面带数字）；
`Render(name, slot, mirrors)` 画一格并挂镜像，`Lore(panel)` 按配方类上的 `LORE`（`.lang` 的键）加一行说明，`ANIMATIONS` 列要重播的 clip 动画。
引擎给无序配方的形状（`ingredients` + `result`）的，解析用 `ParseShapelessParts`。
物品表里没有、这个类型又要显示的变体（药水的各种 aux）**不用类型自己加**：创造栏里有的都由原版扩展的创造栏表加（`creative/`，`item_model.md` §9.8），
创造栏里没有、又要显示的写进 `creative/families.py`（原来的 `VARIANTS` 10-30 退役）。

然后把包名加进 `vanilla/__init__.py` 的 `TYPES`。装配器会 `RegisterCategory` →
`RegisterSource` → `RegisterScript(category.Id, ...)`，**不要自己在别处注册**。
第三方的写法见 `docs/modding/02-recipes.md`（相同的三样东西，只是要包进函数里）。
查询入口：`RecipeManager.QueryRecipe(item, query_by="output"/"input", types=None)`
返回 `OrderedDict{category_id: [Recipe, ...]}`（按 `sort_index` 再按注册序）。

## 本地参考资源

- 原前置库源码（2026-10-27 已解耦；拼音字表从它的 `libs/pypinyin/pinyin_dict.py` 生成，生成器默认读这里）：
  `D:\MCStudioDownload\work\wuming233qwq@163.com\Cpp\AddOn\32fc56101ffe49b0b15b199870391b88\`
  （其 `etr_mod_core_behavior/` 被 `.git/info/exclude` 本地排除，git 历史停在 2025-09-03；
  目录里有引擎生成的 `.pyc`，桌面 Python 加载会段错误，要跑它的代码先把 `.py` 拷出来）。
- 同作者姊妹工程 Truth（世界编辑模组，文档体系与本项目同源可互相借鉴）：
  `...\Cpp\AddOn\14486e0d2b014283ae6e4965f3e63811\`。
- 引擎资产：`D:\MCStudioDownload\game\MinecraftPE_Netease\3.8.0.313307\data\resource_packs\vanilla_netease\`。
- 官方 Demo 工程：`D:\MCStudio\data\demo\AwesomeMod\`（UI/触摸/骨骼模型样例）。
- 文档查询：`mcdk_assistant` 系列 MCP 工具（`search_api` / `search_event` /
  `get_netease_jsonui` / `search_wiki` 等）。

## 交付纪律

1. **不自动提交** —— 任务完成时一律不直接 `git commit`，先交付 review。
   除「用户明确跳过 review」与「本轮即提交上轮已 review 内容」两种情形外，
   输出末尾须写明：**「因工程规范要求，本轮不会直接提交，请 review 后提交」**，
   并**列出本轮改了哪些文件**。（`engineering.md` §10）
2. **约定式提交** —— `<type>(<scope>): <描述>`，scope 取分层名
   （`model`/`registry`/`ui`/`ext`/`bridge`/`docs`）；标题写**实际改了什么**，
   不得用会话任务状态（如「完成某任务」「修复 review 问题」）充当标题。
3. **行动项必须具体到可执行** —— 结尾单独起一段写「你要做什么」：
   改哪个文件哪一行、改成什么值、进游戏做什么操作、回传哪些日志/截图。不要只给结论摘要。
4. 交付前过一遍 `engineering.md` §8 提交前自检清单（compileall + 依赖方向 +
   `isinstance str` 零命中 + `.pyi` 同步 + 文档反漂移 + 游戏内回归）。
5. **分支与只在本地的目录** —— 改动在 `dev` 分支上做（`master` 是 2026-10-29 重建历史时的单提交基线）。
   `docs/` 与 `debug/` 被 `.gitignore` 忽略、不入库：文档照旧要同步（规则③），只是 `git status` 里看不到，
   交付时把改过的文档、探针单独列进「本轮改了哪些文件」。
