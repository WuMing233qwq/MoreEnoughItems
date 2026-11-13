# coding=utf-8

# ----------------------------------------------------------------------
#  ui.py is part of MoreEnoughItems.
#  Copyright (C) 2026 WuMing233qwq <2691068930@qq.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation, version 3 only.
#
#  This program is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program.
#  If not, see <https://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------
# 界面侧的字符串常量: 控件路径 / 集合名 / 绑定名 / 界面 def / 面板模板名.
#
# 为什么单独成文件: 这批值与 mei_resource/ui/*.json **逐字强绑定** ——
# 改界面结构就必须同步改 Python, 是全项目改动耦合度最高的一批字符串.
# 集中之后, 改 JSON 只需回到这一个文件对照.
#
# 路径用拼接而非全写: 层级关系直接可见, 改中间某一层只改一处.

class UiPathConst(object):
    # 原版界面（common.base_screen 派生的）的根面板：MEI 的覆盖层建在它下面，代理参数 RootPath 不写就是它
    ScreenRoot = "/variables_button_mappings_and_controls/safezone_screen_matrix/inner_matrix/safezone_screen_panel/root_screen_panel"
    # 根节点
    MeiRoot = "/mei_ui"
    LeftWrapper = MeiRoot + "/mei_left_wrapper"
    RightWrapper = MeiRoot + "/mei_right_wrapper"
    # 覆盖层的定义（mei_main 命名空间下）：支持的界面用 mei_proxy_ui，注入的界面（HUD、强制兼容）与 MEI 自己的界面用 mei_float_ui。
    # 两栏不写在覆盖层里，一律由主节点动态建（UIMainNode.EnsureScripts，名字取 LeftWrapper / RightWrapper 的最后一段）：
    # 按设置「两侧UI缩放」选 20 或 18 那一档（mei_ui/common/scale.py），支持的界面用平时那一档层级的定义，
    # 别的界面用悬浮窗那一档的（这几种界面两栏一露面就是悬浮窗管事），生下来就是要的层级，不用再 SetLayer
    ProxyRootDef = "mei_proxy_ui"
    FloatRootDef = "mei_float_ui"
    RightWrapperDef = "MeiItemsBrowser.items_browser_ui"  # 两栏本来的定义（格子 20 那一档的尺寸写在它们的变量缺省值上）
    LeftWrapperDef = "MeiItemsSidebar.items_sidebar_ui"
    SideRightWrapperDef = "mei_main.side_right_wrapper"  # 平时那一档层级（$mei_side_layer）
    SideLeftWrapperDef = "mei_main.side_left_wrapper"
    FloatRightWrapperDef = "mei_main.float_right_wrapper"  # 悬浮窗那一档层级（$mei_float_side_layer）
    FloatLeftWrapperDef = "mei_main.float_left_wrapper"
    SideRightWrapperSmallDef = "mei_main.side_right_wrapper_s18"  # 18 那一档：只换格子与上下栏的五个尺寸变量
    SideLeftWrapperSmallDef = "mei_main.side_left_wrapper_s18"
    FloatRightWrapperSmallDef = "mei_main.float_right_wrapper_s18"
    FloatLeftWrapperSmallDef = "mei_main.float_left_wrapper_s18"
    CellMark = "/cell_mark"  # 两栏根上的记号（接在两栏的路径后面）：大小就是建这一栏的那一档的格子（$mei_slot_size），主节点读它认出是哪一档
    # 悬浮窗（docs/architecture/floating.md）
    Backdrop = MeiRoot + "/mei_backdrop"  # 从悬浮窗点开 MEI 时盖住原版界面的黑底（30% 透明度，吞点击；点它收起）
    FindCapture = MeiRoot + "/mei_find"  # 查找状态：整屏透明的捕获层，下一次点哪就查哪（layer 95，在悬浮窗下面）
    FloatWindow = MeiRoot + "/mei_float"  # 悬浮窗：横条（握把 + 两个按钮），JSON 原生可拖的 input_panel，layer 100
    FloatMei = FloatWindow + "/buttons/mei"
    FloatQuerySlot = FloatWindow + "/buttons/query_slot"  # 查询按钮连同它前面的间隔：不在触屏时宽度写 0
    FloatQuery = FloatQuerySlot + "/query"
    # 工具模式（docs/architecture/modes.md）：拿起来的物品（比格子里的大一圈）与「下一下点哪就放到哪」的捕获层，显隐都绑在「拿着没有」上
    ToolLayer = MeiRoot + "/mei_tool"
    ToolCapture = ToolLayer + "/capture"  # 整屏透明（layer 96，在查找状态的捕获层上面、悬浮窗下面）
    ToolDesktop = ToolLayer + "/desktop"  # PC：follows_cursor 的 1×1 宿主，在 PC 上一直亮着（藏着的跟不住光标，引擎结论 §29）
    ToolDesktopItem = ToolDesktop + "/item"
    ToolTouchItem = ToolLayer + "/touch"  # 触屏：摆在点的那一格上（锚左上，SetPosition 给的是相对父控件左上角的坐标，引擎结论 §39）
    # 物品栏的筛选与排序菜单（mei_ui/filters/）：整屏一层，框由脚本摆在筛选按钮旁边，里面全部锚左上、绝对定位
    FilterLayer = MeiRoot + "/mei_filter"
    FilterFrame = FilterLayer + "/frame"
    FilterTitle = FilterFrame + "/title"
    FilterClose = FilterFrame + "/close"
    FilterSection = FilterFrame + "/filter_section"
    FilterScroll = FilterFrame + "/chips"  # common.scrolling_panel：标签块放不下时上下滚
    FilterSortSection = FilterFrame + "/sort_section"
    FilterPrev = FilterFrame + "/sort_prev"
    FilterValue = FilterFrame + "/sort_value"
    FilterNext = FilterFrame + "/sort_next"
    FilterDir = FilterFrame + "/sort_dir"
    FilterLine = FilterFrame + "/line"
    FilterClear = FilterFrame + "/clear"
    FilterDone = FilterFrame + "/done"
    # 两栏的层级：根控件的变量 $mei_side_layer（平时）/ $mei_float_side_layer（悬浮窗管事时）经这几个记号带给脚本，
    # 和层级为 0 的那个做差（floating/manager.py 的 side_layers）
    SideLayerZero = MeiRoot + "/side_layer_zero"
    SideLayerNormal = MeiRoot + "/side_layer_normal"
    SideLayerFloat = MeiRoot + "/side_layer_float"

class ItemsSidebarPath(object):
    Root = UiPathConst.LeftWrapper + "/items_sidebar"
    Top = Root + "/top"
    Bottom = Root + "/bottom"
    PageUpBtn = Bottom + "/page_up/button"
    PageDownBtn = Bottom + "/page_down/button"
    PageIndexLabel = Bottom + "/page_index/label"
    PageIndexBar = Bottom + "/page_index/progress_bar"
    TabPrevBtn = Top + "/tab_prev/button"
    TabNextBtn = Top + "/tab_next/button"
    TabLabel = Top + "/tab_index/label"
    TabIndexBar = Top + "/tab_index/progress_bar"
    BookmarksGrid = Root + "/items/grids/bookmarks"
    HistoryGrid = Root + "/items/grids/panel/history"
    ModePanel = Top + "/mode"  # 顶栏最左边的模式按钮那一格（普通 / 工具 / 作弊，点一下轮换；原来的 setting 占位）
    ModeButton = ModePanel + "/button"

class ItemsBrowserPath(object):
    Root = UiPathConst.RightWrapper + "/items_browser"
    Top = Root + "/top"
    Bottom = Root + "/bottom"
    PageUpBtn = Bottom + "/page_up/button"
    PageDownBtn = Bottom + "/page_down/button"
    PageIndexLabel = Bottom + "/page_index/label"
    PageIndexBar = Bottom + "/page_index/progress_bar"
    ItemsGrid = Root + "/items/items_grid"
    SearchEditBox = Top + "/search_box/edit_box"
    SearchClearBtn = Top + "/search_box/clear"
    FindPanel = Top + "/query"  # 顶栏最右边的查询按钮那一格（只在触屏、设置开着时显示）
    FindButton = FindPanel + "/button"
    FilterPanel = Top + "/filter"  # 搜索框右边的筛选按钮那一格（原来的 setting 占位）
    FilterButton = FilterPanel + "/button"

class RecipeDetailsPath(object):
    # 注意: Root 与 Screen 差一层 —— Root 是 CreateChildControl 建出来的容器,
    # Screen 是界面 json 自身的根控件名(与 NameConst.RecipeDetailsUiNameSpace 同名).
    Root = UiPathConst.MeiRoot + "/recipe_details"
    Screen = Root + "/RecipeDetails"

    # 配方页本体（content）加上右边伸出去的竖页签（crafting_stations）：content_panel 宽 = content + 竖页签伸出的那一截
    ContentPanel = Screen + "/content_panel"
    Content = ContentPanel + "/content"
    Recipes = Content + "/recipes"
    FirstRecipe = Recipes + "/recipe1"

    # 顶栏只有一行：返回 · 类型名 · ◀ 页码 ▶ · 关闭
    HeaderLine = Content + "/top/bg/line"
    BackBtn = HeaderLine + "/back/button"
    DisplayNameLabel = HeaderLine + "/title/display_name"
    PageDownBtn = HeaderLine + "/page_down/button"
    PageIndexLabel = HeaderLine + "/page_index/label"
    PageUpBtn = HeaderLine + "/page_up/button"
    CloseBtn = HeaderLine + "/close/button"

    # 左边的工作站一列（伸出面板左边）
    CraftingItems = ContentPanel + "/crafting_items"
    CraftingItemsGrid = CraftingItems + "/grid"

    # 右边的竖页签（配方类型）：上下两头是页签的翻页按钮（page_down 在上、翻到上一页；page_up 在下、翻到下一页），中间是页签
    CraftingStations = Screen + "/crafting_stations"
    StationsPageUpBtn = CraftingStations + "/overlay/page_up/button"
    StationsPageDownBtn = CraftingStations + "/overlay/page_down/button"
    TypeTabArea = CraftingStations + "/type_tab"
    TypeTabGrid = TypeTabArea + "/grid"

    # 配方行子控件名. 造控件(script.py)与解析按钮路径(binding.py)必须用同一个值 ——
    # 点击绑定拿不到 collection_index, 行号只能从路径里解出来.
    RowChildName = "recipe"

    # 这里原先有 ActionButtonSubPath / ActionButtonPath / RowPath / ToggleInnerPath 四样,
    # 用「绝对路径 + 行号」拼动作按钮的位置 —— 全项目独一份的取控件方式.
    # 已全删: 取控件一律走 RecipeControl.GetChildByPath(相对路径),
    # 与 CraftingTableUIScript.InitControls 同一个路子; 相对路径见
    # recipe_details/actions.py 的 SLOT_PATHS.
    # (ToggleInnerPath 当时就已经零调用, 一并清掉.)

    # 配方页开着时，物品栏、收藏栏避让的是配方页自己的这几块。**第一块就是这时的主内容**，顺序别动；
    # JSON 里是 recipe_details_ui/RecipeDetails/…，建出来的控件叫 recipe_details（Root），所以这里是运行时的路径。
    # Screen 的宽跟着 content_panel，已经含右边的竖页签；左边的工作站一列伸在外面，单独一块
    AdaptivePaths = (
        Screen,
        CraftingItems,
    )


class FloatConst(object):
    """
    悬浮窗与查找状态（docs/architecture/floating.md）
    """
    MeiTexture = "textures/ui/mei/button/float_window/mei"
    MeiPressedTexture = "textures/ui/mei/button/float_window/mei_pressed"
    QueryTexture = "textures/ui/mei/button/float_window/query"
    QueryPressedTexture = "textures/ui/mei/button/float_window/query_pressed"
    FaceSubs = ("/default", "/hover")  # 「按下」要常亮时（展开着、查找中）换这两张图的贴图
    IconSubs = ("/default/wrapper/button_content", "/hover/wrapper/button_content")  # 顶栏查询按钮的图标（ore_style_button）
    IconColor = (0.4784313725490196, 0.4784313725490196, 0.4784313725490196)  # 图标平时的灰，与 mei_icons 一致
    IconActiveColor = (0.4824, 0.6078, 0.8667)  # 查找中：与 ore_style_button 按下时的图标同色
    # 拖动是 JSON 原生的（input_panel 的 draggable + contained，引擎结论 §32）：脚本只管记位置、建的时候摆回去
    Width = 52  # 悬浮窗的宽：边 2 + 握把 8 + 间隔 2 + MEI 18 + 查询那一格（间隔 2 + 18）20 + 边 2，与 JSON 一致
    Height = 22  # 悬浮窗的高：按钮 18 + 上下各 2，与 JSON 一致
    QuerySlotWidth = 20  # 查询那一格（含前面的间隔）：不在触屏时整格收成 0，悬浮窗跟着窄 20
    DefaultAnchor = (0.5, 0.0)  # 没拖过时：可用范围里水平居中、贴着顶（比例；默认屏幕上方正中、横着排）
    DefaultTopGap = 4  # 没拖过时离顶边几像素
    SaveTicks = 15  # 隔这么多帧（约 0.5 秒）看一眼拖拽偏移，变了才记（不用太频繁）
    PlaceTicks = 10  # 显示后（屏幕尺寸变了也算）这么多帧里，覆盖层的尺寸变了就按记下的位置重摆：刚建的覆盖层要一两帧才排好尺寸
    HudScreen = "hud.hud_screen"
    SkipNamespaces = ("progress", "toast_screen", "debug_screen", "start")  # 强制兼容不注入：加载 / 进度、提示条、调试、主菜单
    # MEI 自己的界面（HUD 上点 MEI 不在游戏界面里展开，PushScreen 开它，floating.md §6.1）
    ScreenDef = "mei_main.mei_screen"  # 画布（common.base_screen 派生，路径结构与原版界面相同，主节点的 RootPath 用缺省的就行）
    ScreenKey = "MeiScreen"  # RegisterUI / PushScreen 的 uiKey，命名空间是 NameConst.NameSpace
    ScreenClose = "button.mei.screen.close"  # ESC、背包键在画布上 global 映射到它：关掉这个界面
    BackDropClickBinding = "#mei.backdrop.click"  # backdrop的button mapping绑定id

class ModeConst(object):
    """
    普通 / 工具 / 作弊三种模式（docs/architecture/modes.md）：收藏栏顶栏最左边的按钮点一下轮换，全局记住（prefs）。
    作弊要操作员：开界面时问一次服务端，给物品时服务端再查一次
    """
    Normal = "normal"  # 照常：点格子查配方，触屏出菜单
    Tool = "tool"  # 点格子把它拿起来，再点一下放到别的模组登记过的控件上（ctx.UI.Drops）；点空处放下
    Cheat = "cheat"  # 点格子给一组（PC 右键给一个），不出菜单、不二次确认
    Order = (Normal, Tool, Cheat)  # 点按钮的轮换顺序；没有操作员权限时跳过作弊
    IconSubs = FloatConst.IconSubs  # 按钮图标（ore_style_button 平时、悬停两张脸；贴图写在 mei_common.btn_mode）
    Colors = {  # 按钮图标的颜色：普通是图标平时的灰（与 mei_icons 一致），工具深黄、作弊深红（浅了在灰按钮上看不清）
        Normal: FloatConst.IconColor,
        Tool: (0.86, 0.6, 0.0),
        Cheat: (0.8, 0.13, 0.13),
    }
    HoverBinding = "#mei.mode.hover_text"  # 模式按钮悬停文字的绑定名（mei_common.mode_hover_tip，ToolHost 挂）


class FilterConst(object):
    """ 物品栏的筛选与排序菜单（mei_ui/filters/，docs/architecture/modes.md §8）"""
    ChipCount = 24  # 标签块池几个，必须与 mei_main.json 的 filter_chips 里 chip_0 … chip_23 一致；登记的筛选比它多，多的不显示
    ChipName = "button.mei.filter.chip.{}"  # 第 i 个标签块的 $pressed_button_name，也是 BF_ButtonClickUp 绑定名
    CloseName = "button.mei.filter.close"
    PrevName = "button.mei.filter.sort_prev"
    NextName = "button.mei.filter.sort_next"
    DirName = "button.mei.filter.sort_dir"
    ClearName = "button.mei.filter.clear"
    DoneName = "button.mei.filter.done"
    ScrollContents = (  # common.scrolling_panel 里放内容的那一层（PC / 触屏、滚动条在不在里面四种），按顺序找第一个在的
        "/scroll_mouse/scroll_view/stack_panel/background_and_viewport/scrolling_view_port/scrolling_content",
        "/scroll_touch/scroll_view/panel/background_and_viewport/scrolling_view_port/scrolling_content",
        "/scroll_mouse/scroll_view/panel/background_and_viewport/scrolling_view_port/scrolling_content",
        "/scroll_touch/scroll_view/stack_panel/background_and_viewport/scrolling_view_port/scrolling_content",
    )
    ChipSub = "/chip_{}"  # 标签块相对内容那一层的路径
    LabelSub = "/label"  # 按钮上的字（mei_common.flat_button）
    FaceSub = "/default"  # 按钮平时的底图：按下的标签块换成选中的样子
    FaceNormal = "textures/ui/mei/flat/btn"  # 与 MenuConst.FaceNormal 同一张
    FaceOn = "textures/ui/mei/flat/btn_on"  # 扁平风的选中：绿色下划线（与 MenuConst.FaceOn 同一张）


class FocusConst(object):
    """ 焦点探针（proxy/focus，docs/architecture/focus.md）"""
    CompatRoots = (UiPathConst.ScreenRoot,)
    """ 强制兼容的界面递归找的起点：先试这些常见的内容面板（base_screen 派生的界面都有），一个都没有就退到界面最根上 """


class TooltipPath(object):
    # tooltip 的两个宿主（mei_common.tooltip_root，挂在 mei_main.mei_proxy_ui 下），见 docs/architecture/tooltip.md §2
    Root = UiPathConst.MeiRoot + "/mei_tooltip"
    Desktop = Root + "/desktop"  # PC：跟着光标走的那 1 像素（follows_cursor）；开着界面就一直亮着、脚本从不挪它
    DesktopFrame = Desktop + "/frame"  # 偏移与贴边翻转改这一层（直接改跟随控件的偏移会被 follows_cursor 盖掉）；藏 tooltip 就藏它
    DesktopGap = Desktop + "/cursor_gap"  # 只是个记号：它的 offset 就是 tooltip 离光标的距离（横, 竖），改 JSON 就行，脚本只读不改
    Touch = Root + "/touch"  # 移动端（触屏菜单）：脚本摆在点开的格子所在区域外侧（或格子旁），不动；本身是吞点击的 input_panel（点菜单空白处不落到下面的格子上）
    # 菜单是一张信息卡 + 图标操作条（tooltip.md §6.14）：顶栏（物品图标、种类、关闭）、内容、分隔线、按钮区
    # （候选的翻页行、一排图标按钮、「更多」展开的两列文字按钮），子控件全部绝对定位，位置与尺寸由菜单按排版写
    # （menu.layout.card_layout），不靠 stack_panel 收拢
    TouchFrame = Touch + "/frame"  # 框：扁平弹出层的底（flat/pop），也是透明着建的那一层（alpha 0 + propagate_alpha，建齐了一起拉回）
    TouchIcon = TouchFrame + "/icon"  # 顶栏左边：这一格的物品图标（扁平格子底 + 物品渲染器），没有物品时藏着
    TouchIconItem = TouchIcon + "/item"  # 图标里的物品渲染器（SetUiItem）
    TouchKind = TouchFrame + "/kind"  # 顶栏：这是哪种格子（灰字），收藏格后面跟着数量「×2」
    TouchCloseSlot = TouchFrame + "/close_slot"  # 顶栏右边小 x 的插槽：脚本只摆它（右上角），小 x 自己的大小、偏移写在 JSON 里
    TouchClose = TouchCloseSlot + "/close"  # 小 x（扁平图标按钮；点击名 MenuConst.CloseName）：$flat_icon_size 与 offset 在 JSON 里调
    TouchContent = TouchFrame + "/content"  # 内容控件建在这里（尺寸跟内容）；触屏上内容不画自己的底，框画（BlankSprite）
    TouchDivider = TouchFrame + "/divider"  # 内容与按钮区之间的分隔线
    TouchActions = TouchFrame + "/actions"  # 按钮区（panel）：候选的翻页行、图标操作条、「更多」的分隔线与文字按钮
    MenuBar = TouchActions + "/bar_{}"  # 图标操作条里第 i 个按钮（format）：图标在上、字在下，位置、尺寸、图标、文字、显隐都由脚本写
    MenuBarIconSub = "/icon"  # 操作条按钮里的图标（image：SetSprite 换图、SetSpriteColor 染色）
    MenuButtonFaceSub = "/default"  # 按钮平时的底：选中（收藏着、展开着、「更多」开着）换成带绿色下划线的那张
    MenuButton = TouchActions + "/button_{}"  # 「更多」里第 i 个文字按钮（format）；位置、尺寸、文字、显隐都由脚本写
    MenuMoreLine = TouchActions + "/more_line"  # 「更多」展开时操作条下面的分隔线
    MenuIcon = TouchActions + "/icon_{}"  # 图标按钮（format 槽名，MenuConst.Icons）：候选的左右箭头，尺寸写在 JSON 里，位置由脚本写
    MenuNumber = TouchActions + "/num_{}"  # 翻页行中间的数字（format）：候选「2 / 86」
    MenuButtonLabelSub = "/label"
    MenuButtonMaskSub = "/mask"  # 暗色遮罩：动作暂时用不了时盖上（点了不执行）
    BlankSprite = "textures/ui/mei/blank"  # 1×1 的透明图：触屏上内容控件换成它，不画自己的底（框已经画了）

    # 内容控件（接受物品 / 某个类型的配方预览）显示时建进宿主；收起时藏着不删，下次同一种直接复用、换一种才先删再建 ——
    # 同一时刻只有一个。名字 = ContentName + 定义名（换一种时新旧不同名，删和建在同一帧也撞不上）
    ContentName = "tip"
    # 内容控件里面：接受物品（mei_common.tooltip_items）与配方预览（类型的 PREVIEW，派生自 mei_recipe_common.preview）同一个骨架
    TitleSub = "/stack/title"
    ItemsGridSub = "/stack/grid"
    PreviewGridSub = "/stack/grid"  # 配方预览：PREVIEW 自己带着预览 grid，显示一次只建这一个控件

    # 预览格子 mei_recipe_common.preview_cell（格子是 preview_cell1）：骨架是 wrapper/content，content 是该类型自己的
    # content_panel（绝对尺寸），格子跟着它的尺寸走 —— 配方页脚本照旧 RecipeControl + "/wrapper/content/..."（统一的根路径）
    PreviewCellName = "preview_cell"
    PreviewContentSub = "/wrapper/content"


class TooltipKind(object):
    # tooltip 内容的种类：面板的 TooltipContent() 返回 (种类, 数据)，管理器按种类建内容控件
    Items = "items"  # 接受物品：数据是多候选面板（标题跟着它当前的候选走）
    Recipe = "recipe"  # 配方预览：数据是配方，或取配方的函数（显示时才找回）；控件是该类型的 PREVIEW（RecipeCategory.PreviewDef）
    Title = "title"  # 只有标题一行：触屏菜单给普通格子、设置里关了高级 Tooltip 时用（面板不返回它，菜单自己挑）

    Defs = {
        Items: "mei_common.tooltip_items",
        Title: "mei_common.tooltip_title_only",
    }


class MenuConst(object):
    # 触屏二级菜单（docs/architecture/tooltip.md §6、§6.14）
    BarSize = 6  # 图标操作条几个按钮，必须与 mei_common.json 的 bar_0 … bar_5 一致（含「更多」）
    PoolSize = 16  # 「更多」里的文字按钮几个，必须与 button_0 … button_15 一致（收藏格最多 13 个动作，关闭在顶栏）
    NumberCount = 1  # 翻页行的数字标签几个，与 num_0 一致
    BarName = "button.mei.menu.bar.{}"  # 操作条第 i 个按钮的 $pressed_button_name，也是 BF_ButtonClickUp 绑定名（只能单个绑定，§9）
    ButtonName = "button.mei.menu.{}"  # 「更多」里第 i 个按钮的 $pressed_button_name 与绑定名
    CloseName = "button.mei.menu.close"  # 顶栏关闭按钮的 $pressed_button_name 与绑定名
    Icons = ("prev", "next")  # 图标按钮的槽名，与 mei_common.json 的 icon_prev / icon_next 一致；动作用 MenuAction(icon=槽名) 认领
    IconName = "button.mei.menu.icon.{}"  # 图标按钮的 $pressed_button_name 与绑定名（format 槽名）
    BackdropName = "button.mei.menu.backdrop"  # 宿主底板吞点击用的名字，不挂绑定
    GlyphPath = "textures/ui/mei/icons/{}"  # 操作条按钮的图标（format MenuAction.Glyph）：白图，脚本按状态染色
    FaceNormal = "textures/ui/mei/flat/btn"  # 按钮平时的底
    FaceOn = "textures/ui/mei/flat/btn_on"  # 选中的底（绿色下划线）
    GlyphColor = (0.85, 0.86, 0.89)  # 图标平时的颜色（深色底上的浅灰）
    GlyphOnColor = (0.49, 0.77, 0.5)  # 选中：扁平风的强调绿，和 btn_on 的下划线一个颜色
    GlyphDangerColor = (0.91, 0.45, 0.37)  # 删除类：红
    GlyphMutedColor = (0.48, 0.48, 0.51)  # 用不了：灰


class MenuKey(object):
    # 菜单动作的名字：面板的 MenuActions() 返回这些，菜单按名字找动作（和 TooltipKind 同一个路子，面板不用 import 菜单）
    Source = "source"  # 来源
    Uses = "uses"  # 用途
    Bookmark = "bookmark"  # 收藏 / 取消收藏
    Remove = "remove"  # 收藏格：移除这一条
    OpenRecipe = "open_recipe"  # 配方收藏：打开这条配方
    CountDown = "count_down"  # 收藏格：数量 −1（配方是倍数）
    CountUp = "count_up"  # 收藏格：数量 +1
    JoinGroup = "join_group"  # 收藏格：并入上一组
    LeaveGroup = "leave_group"  # 收藏格：移出分组
    FoldGroup = "fold_group"  # 收藏格（物品）：折叠 / 展开所在的组
    Expand = "expand"  # 收藏格（配方）：展开 / 收起这一条（组折叠着时先把组展开）
    View = "view"  # 收藏格：所在的组（或不分组的那部分）横排 / 竖排
    RemoveGroup = "remove_group"  # 收藏格：删除整组（要二次确认）
    MoveUp = "move_up"  # 收藏格：上移
    MoveDown = "move_down"  # 收藏格：下移
    MoveHead = "move_head"  # 收藏格：移到组首
    PrevCandidate = "prev_candidate"  # 多候选格：上一个候选
    NextCandidate = "next_candidate"  # 多候选格：下一个候选
    RecipeTree = "recipe_tree"  # 以这个物品为根开配方树（docs/architecture/recipe_tree.md）
    OpenTree = "open_tree"  # 配方树收藏：打开这棵树
    More = "more"  # 「更多」：操作条放不下的动作收在它下面，点一下展开 / 收起（菜单自己加，面板不用写）
    Close = "close"  # 关闭：菜单自己加在最后，面板不用写


class CollectionConst(object):
    # grid 的 collection_name. **必须与 JSON 的 collection_name 逐字一致**,
    # 且引擎不解析变量、运行期不可改(见 docs/architecture/recipe_ui_api.md §6.5).
    ItemsBrowser = "items_browser"
    SidebarBookmarks = "items_sidebar_bookmarks"
    SidebarHistory = "items_sidebar_history"
    CraftingStationItems = "crafting_station_items_grid"
    Recipes = "recipes_grid"
    TooltipItems = "mei_tooltip_items"
    TooltipRecipe = "mei_tooltip_recipe"

class BindingConst(object):
    # Python 侧注册的绑定名, 必须与 JSON 的 binding_name 逐字一致.
    RecipeVisible = "#mei_ui.recipe_details.recipe.visible"
    CraftingStationTypeTab = "#mei_ui.recipe_details.crafting_station_type_tab"
    TypeTabItemIdAux = "#mei_ui.recipe_details.type_tab.item_id_aux"
    TypeTabTexture = "#mei_ui.recipe_details.type_tab.texture"

class ControlDefConst(object):
    # CreateChildControl 的 <namespace>.<control> 串.
    RecipeDetailsUi = "MeiRecipeDetails.recipe_details_ui"

class PanelProtoConst(object):
    # ItemPanel 在 grid 里的模板控件名.
    Group = "group_item_panel"
    Bordered = "bordered_item_panel"
    Bookmark = "bookmark_item_panel"
    Tooltip = "tooltip_item_panel"  # 接受物品列表的一格（多一个居中的「+N」，见 tooltip/items.py）


class TreeConst(object):
    """ 配方树（mei_ui/recipe_tree/，docs/architecture/recipe_tree.md）"""
    UiNameSpace = "MeiRecipeTree"  # recipe_tree.json 的命名空间：悬浮窗的强制兼容不往这个界面里注入（floating/hosts.py）
    ScreenDef = UiNameSpace + ".tree_screen"  # 画布（common.base_screen 派生，根面板的路径与原版界面相同：UiPathConst.ScreenRoot）
    ScreenKey = "MeiRecipeTree"  # RegisterUI / PushScreen 的 uiKey，命名空间是 NameConst.NameSpace
    CloseName = "button.mei.tree.close"  # ESC、背包键在画布上 global 映射到它：菜单开着先关菜单，否则关掉配方树
    # 画布里动态建的控件（CreateChildControl 的定义名）：格子、工作方块的框、原料组的框、连线
    CellDef = UiNameSpace + ".cell"
    WsFrameDef = UiNameSpace + ".ws_frame"
    IngFrameDef = UiNameSpace + ".ing_frame"
    LineDef = UiNameSpace + ".line"
    BucketDef = UiNameSpace + ".bucket"  # 分桶用的空 panel（左上对齐、0×0、层级 0）：一个父控件下挂太多子控件引擎会断言（引擎结论 §54）
    # 静态按钮的点击名（$pressed_button_name，也是 BF_ButtonClickUp 绑定名 —— 只能单个绑定，引擎结论 §9）
    ButtonName = "button.mei.tree.{}"  # 顶栏、汇总的按钮（format 名字，与 JSON 里的控件名相同）
    TopButtons = ("minus", "plus", "x64", "center", "unfold", "fold2", "back", "save", "side")
    TopTextButtons = ("minus", "plus", "x64")  # 顶栏里写字的那几个（按字改宽）；其余是 14×14 的图标按钮，悬停出字
    TopClose = "button.mei.tree.close_button"  # 顶栏右上角的 x
    TabButtons = ("tab_raw", "tab_byproduct", "tab_tool", "tab_lack")
    SummaryButtons = ("refresh", "page_prev", "page_next")
    MenuButtonName = "button.mei.tree.menu.{}"  # 菜单按钮池第 i 个
    MenuIconName = "button.mei.tree.menu.icon.{}"  # 菜单的图标按钮（format 槽名）
    MenuCloseName = "button.mei.tree.menu.close"
    MenuPool = 16  # 与 recipe_tree.json 的 button_0 … button_15 一致
    MenuSections = 6  # sec_0 … sec_5
    MenuNumbers = 2  # num_0 … num_1
    MenuIcons = (("prev_0", "next_0"), ("prev_1", "next_1"))  # 两个步进器的左右箭头
    StripCells = 14  # 菜单里那一条配方最多几格（c0 … c13）
    SummaryRows = 16  # 右侧汇总清单一页最多几行（r0 … r15），实际按高度摆得下几行
    SummaryRowH = 22  # 一行的高（格子 20 + 间隔 2，与 JSON 里 r{i} 的 offset 一致）
    SummaryTop = 18  # 清单从汇总栏的哪儿开始（页签 14 + 上下各 2，与 JSON 里 rows 的 offset 一致）
    SummaryBottom = 20  # 汇总栏底下翻页 / 刷新背包那一行占的高（14 + 上下留白）
    SideMinWidth = 128  # 右侧汇总栏最窄多宽（页签按字算宽，比它宽就跟着页签）
    SideGap = 4  # 汇总栏与视口之间的空
    SideFrames = 6  # 展开 / 收起的过渡帧数（每秒 30 帧，约 0.2 秒）
    IconColor = (0.86, 0.87, 0.9)  # 顶栏图标平时的颜色（JSON 里 flat_icon_button 的 icon 也是它）
    IconOnColor = (0.49, 0.77, 0.5)  # 图标按钮「开着」：汇总栏展开着、这棵树收藏过
    # 格子上的上标：2×2 的白色小方块（离格子边 2 像素），按下面的颜色染（不用圆点贴图或「·」字符：都不好看）；
    # 颜色压暗一点，配这套灰色界面
    BadgeColors = {  # 右上角：这一格为什么停在这儿、当原料算（solver 的 STATE_*）；正常展开的、真没配方的不画
        "cyclic": (0.75, 0.15, 0.15),  # 红：它的配方都要用到上面已经出现过的东西（会绕圈），只好当原料
        "stop": (0.35, 0.35, 0.4),  # 灰：你在这棵树里点了「不再展开」
        "raw": (0.15, 0.35, 0.8),  # 蓝：你设了「当原料（全局）」，每棵树都不展开它
        "trunc": (0.8, 0.55, 0.05),  # 黄：树太深 / 太大，到上限了没再往下算
        "nonitem": (0.1, 0.55, 0.55),  # 青：不是物品（物品表里认不出、查不了配方；流体是隐藏物品，照常展开）
    }
    MultiColor = (0.4, 0.25, 0.85)  # 左上角的紫色小方块：原料格 = 当前类型里还有别的配方可换；工作方块 = 还有别的合成类型可换
    HaveColor = (0.4, 0.9, 0.4)  # 汇总：背包里够
    LackColor = (1.0, 0.4, 0.4)  # 汇总：还缺
    ChanceColor = (0.75, 0.2, 0.6)  # 汇总「副产物」页右上的小方块：里面有概率产出（按每次都出算，点开看平均）
    TabOnColor = (1.0, 1.0, 1.0)  # 汇总：选中的页签（另有一条绿色下划线，按钮的 on）
    TabOffColor = (0.62, 0.63, 0.67)


class TreePath(object):
    # 配方树界面里的控件（recipe_tree.json）。根面板就是 $screen_content（common.base_screen 的 root_screen_panel）
    Root = UiPathConst.ScreenRoot
    Window = Root + "/window"
    Top = Window + "/top"
    RootCell = Top + "/root"
    Title = Top + "/title"
    Bar = Top + "/bar"
    Qty = Bar + "/qty/label"
    TopClose = Bar + "/close"
    TopBack = Top + "/back"  # 「返回」在顶栏最左边，不在按钮条里
    Cut = Window + "/cut"  # 视口（clips_children）
    DragPanel = Cut + "/dragpanel"  # 大小 = 画布 ×2 − 视口（成就界面的做法），居中在视口里
    Canvas = DragPanel + "/canvas"  # 可拖的 input_panel（contained）：拖拽偏移就是视野
    Content = Canvas + "/content"  # 画布比视口小时整体挪到中间
    Lines = Content + "/lines"
    Frames = Content + "/frames"
    Cells = Content + "/cells"
    Status = Cut + "/status"
    Busy = Cut + "/busy"
    Summary = Window + "/summary"  # 右侧汇总栏（锚右上、clips_children）：宽由脚本改，展开 / 收起有过渡
    SummaryBody = Summary + "/body"  # 定宽的内容：汇总栏变窄时从右边裁掉，像抽屉
    Tabs = SummaryBody + "/tabs"
    Rows = SummaryBody + "/rows"
    SummaryRow = Rows + "/r{}"  # 清单的一行：格子 + 名字 + 一行「需 · 有 · 缺」
    SummaryCell = SummaryRow + "/cell"
    RowName = "/name"
    RowInfo = "/info"
    PagePrev = SummaryBody + "/prev"
    PageNext = SummaryBody + "/next"
    Page = SummaryBody + "/page"
    Refresh = SummaryBody + "/refresh"
    Empty = SummaryBody + "/empty"
    Foot = SummaryBody + "/foot"  # 统计（锚左下、宽是汇总栏的宽，放不下自己换行；部分结果的说明写在它前面一行）
    Menu = Root + "/menu"  # 节点菜单：吞点击的 input_panel，尺寸跟着框
    MenuFrame = Menu + "/frame"
    MenuKind = MenuFrame + "/kind"
    MenuCloseSlot = MenuFrame + "/close_slot"
    MenuClose = MenuCloseSlot + "/close"
    MenuContent = MenuFrame + "/content"
    MenuTitle = MenuContent + "/title"
    MenuStrip = MenuContent + "/strip"
    MenuStripCell = MenuStrip + "/c{}"
    MenuArrow = MenuStrip + "/arrow"
    MenuInfo = MenuContent + "/info"
    MenuPreview = MenuContent + "/preview"  # 配方预览的插槽（锚左上、尺寸跟内容）：PREVIEW 建在它下面（recipe_tree/controls/preview.py）
    MenuDivider = MenuFrame + "/divider"
    MenuActions = MenuFrame + "/actions"
    MenuButton = MenuActions + "/button_{}"
    MenuIcon = MenuActions + "/icon_{}"
    MenuSection = MenuActions + "/sec_{}"
    MenuNumber = MenuActions + "/num_{}"
    Toast = Root + "/toast"
    # 一格里的子控件（cell 模板）
    CellRenderer = "/renderer"
    CellIcon = "/icon"  # 类型图标是贴图时画它（工作方块格没有工作站可画的时候）
    CellCount = "/count"
    CellCrafts = "/crafts"
    CellHave = "/have"
    CellFold = "/fold"
    CellBadge = "/badge"
    CellMulti = "/multi"
    CellDim = "/dim"
    CellSel = "/sel"
    CellButton = "/btn"
    ButtonLabel = "/label"  # mei_common.menu_button 的字
    ButtonMask = "/mask"  # mei_common.menu_button 的灰色遮罩
