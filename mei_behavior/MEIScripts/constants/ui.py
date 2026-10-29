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
    # 覆盖层的定义（mei_main 命名空间下）：支持的界面两栏写在 JSON 里；注入的界面（HUD、强制兼容）用不带两栏的那个，
    # 第一次展开才按下面两个定义把两栏建出来（UIMainNode.EnsureScripts）
    ProxyRootDef = "mei_proxy_ui"
    FloatRootDef = "mei_float_ui"
    RightWrapperDef = "MeiItemsBrowser.items_browser_ui"
    LeftWrapperDef = "MeiItemsSidebar.items_sidebar_ui"
    # 悬浮窗（docs/architecture/floating.md）
    Backdrop = MeiRoot + "/mei_backdrop"  # 从悬浮窗点开 MEI 时盖住原版界面的黑底（30% 透明度，吞点击；点它收起）
    FindCapture = MeiRoot + "/mei_find"  # 查找状态：整屏透明的捕获层，下一次点哪就查哪（layer 95，在悬浮窗下面）
    FloatWindow = MeiRoot + "/mei_float"  # 悬浮窗：横条（握把 + 两个按钮），JSON 原生可拖的 input_panel，layer 100
    FloatMei = FloatWindow + "/buttons/mei"
    FloatQuerySlot = FloatWindow + "/buttons/query_slot"  # 查询按钮连同它前面的间隔：不在触屏时宽度写 0
    FloatQuery = FloatQuerySlot + "/query"
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

class RecipeDetailsPath(object):
    # 注意: Root 与 Screen 差一层 —— Root 是 CreateChildControl 建出来的容器,
    # Screen 是界面 json 自身的根控件名(与 NameConst.RecipeDetailsUiNameSpace 同名).
    Root = UiPathConst.MeiRoot + "/recipe_details"
    Screen = Root + "/RecipeDetails"

    ContentPanel = Screen + "/content_panel"
    Content = ContentPanel + "/content"
    Recipes = Content + "/recipes"
    FirstRecipe = Recipes + "/recipe1"

    DisplayNameLabel = Content + "/top/line1/bg/display_name"
    Line1PageUpBtn = Content + "/top/line1/bg/page_up/button"
    Line1PageDownBtn = Content + "/top/line1/bg/page_down/button"
    Line2PageIndexLabel = Content + "/top/line2/page_index"
    Line2PageUpBtn = Content + "/top/line2/bg/page_up/button"
    Line2PageDownBtn = Content + "/top/line2/bg/page_down/button"

    CraftingItems = ContentPanel + "/crafting_items"
    CraftingItemsGrid = CraftingItems + "/grid"

    BackBtn = ContentPanel + "/right/back/button"
    CloseBtn = ContentPanel + "/right/close/button"

    CraftingStations = Screen + "/crafting_stations"
    StationsPageUpBtn = CraftingStations + "/overlay/page_up/button"
    StationsPageDownBtn = CraftingStations + "/overlay/page_down/button"
    TypeTabGrid = CraftingStations + "/type_tab/grid"

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
    # JSON 里是 recipe_details_ui/RecipeDetails/…，建出来的控件叫 recipe_details（Root），所以这里是运行时的路径
    AdaptivePaths = (
        Screen,
        CraftingStations + "/overlay",
        ContentPanel + "/right",
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
    # 菜单是一个框（tooltip.md §6.12）：顶栏（种类 + 关闭）、内容、分隔线、分段的按钮区，
    # 子控件全部绝对定位，位置与尺寸由菜单按排版写（menu.layout.box_layout），不靠 stack_panel 收拢
    TouchFrame = Touch + "/frame"  # 框：purpleBorder 的底，也是透明着建的那一层（alpha 0 + propagate_alpha，建齐了一起拉回）
    TouchKind = TouchFrame + "/kind"  # 顶栏左边：这是哪种格子（灰字）
    TouchCloseSlot = TouchFrame + "/close_slot"  # 顶栏右边小 x 的插槽：脚本只摆它（右上角），小 x 自己的大小、偏移写在 JSON 里
    TouchClose = TouchCloseSlot + "/close"  # 小 x（照搜索框的清空按钮，只有图标；点击名 MenuConst.CloseName）：$menu_icon_size 与 offset 在 JSON 里调
    TouchContent = TouchFrame + "/content"  # 内容控件建在这里（尺寸跟内容）；触屏上内容不画自己的底，框画（BlankSprite）
    TouchDivider = TouchFrame + "/divider"  # 内容与按钮区之间的分隔线
    TouchActions = TouchFrame + "/actions"  # 按钮区（panel）：段名、步进器的数字、按钮池
    MenuButton = TouchActions + "/button_{}"  # 按钮池里第 i 个（format）；位置、尺寸、文字、显隐都由脚本写
    MenuIcon = TouchActions + "/icon_{}"  # 图标按钮（format 槽名，MenuConst.Icons）：候选的左右箭头，尺寸写在 JSON 里，位置由脚本写
    MenuSection = TouchActions + "/sec_{}"  # 第 i 段的段名（format），灰字
    MenuNumber = TouchActions + "/num_{}"  # 第 i 个步进器中间的数字（format）：数量「×2」、候选「2 / 86」
    MenuButtonLabelSub = "/label"
    MenuButtonMaskSub = "/mask"  # 灰色遮罩：动作暂时用不了时盖上（点了不执行）
    BlankSprite = "textures/ui/mei/blank"  # 1×1 的透明图：触屏上内容控件换成它，不画自己的 purpleBorder（框已经画了）

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
    # 触屏二级菜单（docs/architecture/tooltip.md §6）
    PoolSize = 16  # 按钮池几个按钮，必须与 mei_common.json 的 button_0 … button_15 一致（收藏格最多 13 个动作，关闭在顶栏）
    SectionCount = 6  # 段名标签几个，与 sec_0 … sec_5 一致；段比它多就不写段名
    NumberCount = 2  # 步进器的数字标签几个，与 num_0 … num_1 一致；多出来的步进器照普通按钮排
    ButtonName = "button.mei.menu.{}"  # 第 i 个按钮的 $pressed_button_name，也是 BF_ButtonClickUp 绑定名（只能单个绑定，§9）
    CloseName = "button.mei.menu.close"  # 顶栏关闭按钮的 $pressed_button_name 与绑定名
    Icons = ("prev", "next")  # 图标按钮的槽名，与 mei_common.json 的 icon_prev / icon_next 一致；动作用 MenuAction(icon=槽名) 认领
    IconName = "button.mei.menu.icon.{}"  # 图标按钮的 $pressed_button_name 与绑定名（format 槽名）
    BackdropName = "button.mei.menu.backdrop"  # 宿主底板吞点击用的名字，不挂绑定


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
    # 静态按钮的点击名（$pressed_button_name，也是 BF_ButtonClickUp 绑定名 —— 只能单个绑定，引擎结论 §9）
    ButtonName = "button.mei.tree.{}"  # 顶栏、汇总的按钮（format 名字，与 JSON 里的控件名相同）
    TopButtons = ("minus", "plus", "x64", "center", "unfold", "fold2", "back", "save")
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
    SummaryCells = 24  # 汇总一页最多几格（s0 … s23），实际按宽度摆得下几格
    # 格子上的上标：2×2 的白色小方块（离格子边 2 像素），按下面的颜色染（不用圆点贴图或「·」字符：都不好看）；
    # 颜色压暗一点，配这套灰色界面
    BadgeColors = {  # 右上角：这一格为什么停在这儿、当原料算（solver 的 STATE_*）；正常展开的、真没配方的不画
        "cyclic": (0.75, 0.15, 0.15),  # 红：它的配方都要用到上面已经出现过的东西（会绕圈），只好当原料
        "stop": (0.35, 0.35, 0.4),  # 灰：你在这棵树里点了「不再展开」
        "raw": (0.15, 0.35, 0.8),  # 蓝：你设了「当原料（全局）」，每棵树都不展开它
        "trunc": (0.8, 0.55, 0.05),  # 黄：树太深 / 太大，到上限了没再往下算
        "nonitem": (0.1, 0.55, 0.55),  # 青：不是物品（流体之类），不查配方
    }
    MultiColor = (0.4, 0.25, 0.85)  # 左上角的紫色小方块：原料格 = 当前类型里还有别的配方可换；工作方块 = 还有别的合成类型可换
    HaveColor = (0.4, 0.9, 0.4)  # 汇总：背包里够
    LackColor = (1.0, 0.4, 0.4)  # 汇总：还缺
    ChanceColor = (0.75, 0.2, 0.6)  # 汇总「副产物」页右上的小方块：里面有概率产出（按每次都出算，点开看平均）
    TabOnColor = (1.0, 0.88, 0.4)  # 汇总：选中的页签
    TabOffColor = (1.0, 1.0, 1.0)


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
    Cut = Window + "/cut"  # 视口（clips_children）
    DragPanel = Cut + "/dragpanel"  # 大小 = 画布 ×2 − 视口（成就界面的做法），居中在视口里
    Canvas = DragPanel + "/canvas"  # 可拖的 input_panel（contained）：拖拽偏移就是视野
    Content = Canvas + "/content"  # 画布比视口小时整体挪到中间
    Lines = Content + "/lines"
    Frames = Content + "/frames"
    Cells = Content + "/cells"
    Status = Cut + "/status"
    Busy = Cut + "/busy"
    Summary = Window + "/summary"
    Tabs = Summary + "/tabs"
    Note = Summary + "/note"  # 右边那句说明：和页签同一行（锚右上）
    NoteLow = Summary + "/note_low"  # 同一句放不下时用这个：底下一行（锚右下），和左边的统计同一行
    Slots = Summary + "/slots"
    SummaryCell = Slots + "/s{}"
    PagePrev = Summary + "/prev"
    PageNext = Summary + "/next"
    Page = Summary + "/page"
    Empty = Summary + "/empty"
    Foot = Summary + "/foot"
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
