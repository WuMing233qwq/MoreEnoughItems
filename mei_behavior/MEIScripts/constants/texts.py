# coding=utf-8

# ----------------------------------------------------------------------
#  texts.py is part of MoreEnoughItems.
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
# 玩家可见、直接写成中文串的文案集中在这里.
#
# 走 .lang 的字(类型名、配方页的说明行这类)不在这里, 一律经 utils/lang.localize 查(CLAUDE.md「界面文字」).
# 集中放是为了改字、改成走 .lang 时都「只改一处」, 调用方一行都不用动.
#
# ⚠ 文本的两个方向都会出事, 靠"统一用哪种字面量"是解不掉的:
#   · 字节串模板 .format(unicode) -> py2 按 ASCII 解码模板 -> UnicodeDecodeError;
#   · 拼出 unicode 递给引擎     -> 引擎不抛不报, 只是安静地取不到东西(引擎结论 §2).
#   ⇒ 本模块的模板用 u"...", 好让 .format(引擎给的 unicode) 安全;
#     **而在递给引擎之前必须经 utils/text.py 的 native_str 收敛成 str**.
#     那才是唯一的规矩 —— 收敛点在边界, 不在字面量.

class RecipeText(object):
    # 查询无结果时的提示. {} 为物品显示名.
    NoRecipesForOutput = u"没有能做出 {} 的配方"
    NoRecipesForInput = u"没有用到 {} 的配方"
    # 配方页第二行: 查工作站的用途时这个类型的全表还在扫. {} 是页码 (1/37).
    Scanning = u"{} · 扫描中"

class ItemText(object):
    # 物品分组面板的悬浮文本. {} 依次为分组名、物品数量.
    GroupHover = u"物品分组: {}\n\n§7包含 {} 物品\n§7单击展开/收起"
    # 悬停文字最后两行（设置「启用显示物品ID」「启用显示物品命名空间」）. {} 是英文 ID / 命名空间.
    # 颜色照 Java 版: 高级提示框的 ID 是深灰 §8; JEI / REI 写模组名是蓝色斜体 §9§o. 开头的 §r 把上一行的格式清掉
    IdLine = u"§r§8{}"
    NamespaceLine = u"§r§9§o{}"

class BookmarkText(object):
    # 收藏栏. Invalid / InvalidRecipe 的 {} 是存下来的物品 id 或配方 Id.
    Invalid = u"§c已失效: {}"
    InvalidRecipe = u"§c配方已失效: {}"
    RecipeLore = u"§7收藏配方"
    TreeLore = u"§7收藏的配方树"
    RecipeIngredient = u"§7配方原料"
    TabLabel = u"{}/{}"
    TabNew = u"新页签"
    TabFull = u"当前页签已满 {} 条"
    TooManyTabs = u"页签已到上限 {} 个"

class TooltipText(object):
    # tooltip 的标题行. Accepts 的 {} 是候选物品种数; AcceptsCut 再加一个实际显示的种数.
    Accepts = u"§7可用以下任一物品（{} 种）"
    AcceptsCut = u"§7可用以下任一物品（{} 种，只显示前 {} 种）"
    # 配方预览: {} 依次为类型名、主产物名.
    Recipe = u"{} §7· §r{}"
    # 多候选格的接受物品: 标题（当前候选完整的悬停文字）下面加的那一行灰色说明.
    AcceptsLore = u"§7接受以下物品: "


class MenuText(object):
    # 触屏二级菜单的按钮文字（两到四个字；按钮按字算宽）
    Source = u"来源"
    Uses = u"用途"
    Bookmark = u"收藏"
    Unbookmark = u"取消收藏"
    Remove = u"移除"
    OpenRecipe = u"打开配方"
    Close = u"关闭"
    CountDown = u"-1"
    CountUp = u"+1"
    JoinGroup = u"并入上一组"
    LeaveGroup = u"移出分组"
    Fold = u"折叠"
    Unfold = u"展开"
    ExpandRecipe = u"展开"
    CollapseRecipe = u"收起"
    UnfoldGroup = u"展开分组"
    ToList = u"纵向排列"
    ToGrid = u"横向排列"
    RemoveGroup = u"删除整组"
    ConfirmRemoveGroup = u"§c确认删除？"
    MoveUp = u"上移"
    MoveDown = u"下移"
    MoveHead = u"移到组首"
    PrevCandidate = u"上一个"
    NextCandidate = u"下一个"
    RecipeTree = u"配方树"
    OpenTree = u"打开配方树"


class MenuSectionText(object):
    # 触屏菜单按用途分段，段名写在每段左边，灰字
    Query = u"查询"
    Recipe = u"配方"
    Count = u"数量"
    Multiple = u"倍数"  # 配方收藏的数量是倍数
    Sort = u"排序"
    Group = u"分组"
    View = u"显示"
    Delete = u"删除"
    Candidate = u"候选"
    # 步进器中间的数字：数量、第几个候选（{} 依次为当前、总数）
    CountValue = u"×{}"
    CandidateValue = u"{} / {}"


class MenuKindText(object):
    # 触屏菜单顶栏左边：这是哪种格子
    Item = u"物品"
    Candidates = u"可选物品"
    BookmarkItem = u"收藏 · 物品"
    BookmarkRecipe = u"收藏 · 配方"
    BookmarkTree = u"收藏 · 配方树"
    BookmarkInvalid = u"收藏 · 已失效"
    RecipePart = u"收藏 · 配方原料"  # 展开配方里的原料 / 工具格


class ModeText(object):
    # 收藏栏顶栏模式按钮的悬停文字（docs/architecture/modes.md）：模式名的颜色照按钮图标（工具金、作弊红），说明一行灰字
    Normal = u"§f默认模式"
    Tool = u"§6工具模式\n§7点击物品后可拖拽至支持的模组"
    Cheat = u"§c作弊模式\n§7点击直接获取物品"


class FilterText(object):
    # 物品栏的筛选与排序菜单（mei_ui/filters/，docs/architecture/modes.md §8）
    Title = u"筛选与排序"
    FilterSection = u"筛选（按下的都要满足）"
    SortSection = u"排序"
    NoSort = u"不排序"
    Ascending = u"升序"
    Descending = u"降序"
    Clear = u"清除"
    Done = u"确定"
    On = u"§b{}"  # 按下的那一项：名字染浅蓝（底图换成按下的样子）
    Mute = u"§7{}"  # 不能点的（不排序时的升 / 降）


class HotkeyText(object):
    # 快捷键（mei_ui/hotkeys/）：按住 Alt 出的帮助
    HelpTitle = u"§e快捷键§r（松开 Alt 收起）"
    HelpLine = u"§7{}§r  {}"  # 依次为键位（「Ctrl + C」）、名字（.lang 的 key.mei.<id>）


class TreeText(object):
    # 配方树（mei_ui/recipe_tree/）。按钮两到四个字，和触屏菜单一样
    # 顶栏
    Minus = u"-"
    Plus = u"+"
    X64 = u"×64"
    Center = u"回到顶部"
    Unfold = u"全部展开"
    Fold2 = u"折叠2层"
    Back = u"返回"
    Save = u"收藏"
    Update = u"更新"  # 这个根已经收藏过：再存就是更新那一条
    Qty = u"×{}"
    # 汇总
    TabRaw = u"所需原料"
    TabByproduct = u"副产物"  # 合成多出来的 + 配方的其他产出（中间物不单列）
    TabTool = u"工具"
    TabLack = u"缺少材料"
    Refresh = u"刷新背包"
    Empty = u"暂无"
    EmptyLack = u"材料已集齐"
    # 汇总右上的说明：只在树太大没算完时写
    Partial = u"部分结果 (已到达计算上限)"
    Foot = u"原料 {} 种 · 背包已有 {} 种 · 缺少 {} 种"
    Page = u"{}/{}"
    # 画布
    Status = u"{} 格 · {} 层"
    Solving = u"计算中… {} 格"
    Drawing = u"绘制中… {}/{}"
    # 菜单：顶栏的种类
    KindRoot = u"配方树 · 合成目标"
    KindNode = u"配方树 · 原料"
    KindWs = u"配方树 · 工作方块"
    KindSum = u"配方树 · 汇总"
    # 菜单：段名（两个字，和触屏菜单一样）
    SecRecipe = u"配方"
    SecChoose = u"选择"
    SecPick = u"候选"
    SecExpand = u"展开"
    SecOther = u"其他"
    SecType = u"类型"
    SecStation = u"显示"  # 工作方块格显示哪个工作站（只起显示作用）
    # 菜单：按钮
    Use = u"选择配方"
    InUse = u"已选择"
    SetDefault = u"设为首选"
    UnsetDefault = u"取消首选"
    Stop = u"在此截断"
    Resume = u"恢复展开"
    SetRaw = u"设为原料"
    UnsetRaw = u"取消原料"
    Fold = u"隐藏子节点"
    UnfoldOne = u"显示子节点"
    AsRoot = u"打开配方树"
    Bookmark = u"收藏"
    Unbookmark = u"取消收藏"
    ViewRecipes = u"查看配方"
    # 菜单：步进器中间的数字
    Value = u"{}/{}"
    TypeValue = u"{} {}/{}"
    # 菜单：信息行
    NeedInfo = u"需要 {} 个· 合成 {} 次"
    Surplus = u" · 剩余 {}"
    RecipeInfo = u"第 {}/{} 条"  # 类型名在标题那一行（TooltipText.Recipe「类型名 · 物品名」）
    Current = u" · 当前使用"
    Reverse = u" · 还原"
    Stuck = u" · 递归配方：{}"
    Pinned = u" · 置顶"
    NoRecipe = u"没有配方"
    NeedState = u"需要 {} · {}"  # 没往下展开的格子：要几个 · 为什么没展开（下面 States 里的一句，或 NoRecipe）
    Hidden = u"+{}"  # 折叠了的格子左下：下面藏了几格
    NameSep = u"、"  # 几个名字连在一起时的分隔（「会绕回：铁锭、铁块」）
    States = {
        "stop": u"该节点下不再展开",
        "raw": u"全局当原料",
        "cyclic": u"配方会无限递归",
        "trunc": u"已达到上限，无法再往下展开",
        "nonitem": u"不是物品",
    }
    Crafts = u"{} · 合成 {} 次"
    StationInfo = u"显示：{}"
    SumRaw = u"需要 {} · 背包 {} · 还缺 {}"
    SumCovered = u" · 已有(包括中间产物) {}"  # 背包里有铁锭，粗铁就少缺几个
    SumByproduct = u"副产物 ×{}"
    SumChance = u" · 含概率产出：最多 {} 平均约 {}"  # 依次为最多几个、平均几个
    SumTool = u"工具：不消耗"
    StripItem = u"{} ×{}"
    # 提示
    Saved = u"已保存到收藏"
    Updated = u"已更新收藏"
    SaveFailed = u"收藏页签已满，保存失败"
    DefaultSet = u"已设为首选，其他配方树也会优先使用"
    DefaultUnset = u"已取消首选"
    RawSet = u"已设为全局原料，其他配方树默认不会展开该材料"
    RawUnset = u"已取消全局原料"
    PrefsFull = u"记满了（首选、全局原料各最多 1024 个），先取消一些"
    Bookmarked = u"已收藏"
    Unbookmarked = u"已取消收藏"
    BookmarkFull = u"收藏页签满了"
    TypeUnusable = u"{}此处只有递归配方"  # 工作方块菜单换类型：这个类型在这一格用不了
    NoRoot = u"无法识别该物品，打开配方树失败"
