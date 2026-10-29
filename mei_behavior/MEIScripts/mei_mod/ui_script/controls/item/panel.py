# coding=utf-8

# ----------------------------------------------------------------------
#  panel.py is part of MoreEnoughItems.
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

from MEIScripts.common.classes.types import Item, ItemStack
from MEIScripts.constants.codes import NameConst, QueryConst
from MEIScripts.constants.texts import MenuKindText
from MEIScripts.constants.ui import MenuKey
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.utils import utilities
from MEIScripts.utils.text import native_str


def panel_controls(panel):  # type: (any) -> list
    """ 一个格子面板画在哪几个控件上：自己 + 镜像格（ItemPanel.Controls）；不是 ItemPanel 的看 Control """
    controls = getattr(panel, "Controls", None)
    if callable(controls):
        return [control for control in controls() if control is not None]
    control = getattr(panel, "Control", None)
    return [control] if control is not None else []


class ItemPanel(object):
    """
    使用python代码逻辑控制的用于展示物品的Panel控件
    负责维护传入的Control对象
    """
    def __init__(self, control):
        main_node = context.GetMainNode()
        self.MainNode = main_node

        self.UiNameSpace = NameConst.CommonUiNameSpace
        self.ScreenNode = main_node.ScreenNode
        self.Control = control

        self.BackgroundControl = None
        self.RendererControl = None
        self.RendererPath = ""  # type: str  # 物品渲染器的完整路径
        self.LabelControl= None
        self.Mirrors = []  # type: list
        """
        镜像格 [(控件, 它的物品渲染器), ...]：画同一样东西的别的格子（比如酿造台下面三瓶）。JSON 里写同一个绑定名前缀 ——
        可见、数量、悬停文字、点击都走同一组绑定；只有物品图标是脚本逐个渲染器设的，换物品（轮播）时这里一起设
        """

        self.ItemHoverText = ""
        self.ItemLore = []  # type: list
        """
        追加到 hover text 末尾的说明行。**由使用方设置，与物品本身无关**。

        用途是「这个格子在这条配方里的额外约束」—— 比如机件加工台的工具格要说明
        「需要 扳手等级: 铁」。那种信息不属于物品，属于**这条配方对这一格的要求**，
        所以既不该去改 Item(它是不可变的)，也不该在界面上另找地方摆一个 label。
        """
        self.LabelText = ""
        self.ItemControlVisible = True
        self.OverlayControlVisible = True
        self.ItemRendererVisible = True
        self.BackgroundVisible = False
        self.LabelVisible = False

        self.InitControls()

        self.Item = None  # type: Item or None
        self.Stack = None  # type: ItemStack or None
        self.Destroyed = False  # type: bool  # grid 清缓存、配方页重建时置上：tooltip 认它收起自己挂上的那个

    def InitControls(self):
        # 注意: 这里**不持有 overlay 按钮控件**.
        # 点击走的是 JSON 侧 button_mappings -> #<prefix>.overlay.btn.click_<collection>
        # 的集合绑定(见 ItemsGrid / RecipesGridBind), 不需要 SetButtonTouchDownCallback.
        path = self.Control.GetPath()
        self.RendererPath = path + "/item/renderer"
        self.RendererControl = self.MainNode.GetUIControl(self.RendererPath, "item_renderer", False)

    def OnPrimaryClick(self, _):
        if utilities.GetInputMode() == 1:
            self.OpenTouchMenu()
            return
        self.MainNode.ShowRecipeDetails(self.Item, QueryConst.Output)

    def OnSecondaryClick(self, _):
        if utilities.GetInputMode() == 1:
            return
        self.MainNode.ShowRecipeDetails(self.Item, QueryConst.Input)

    # 触屏二级菜单（docs/architecture/tooltip.md §6）：触屏上点一下格子不直接查，先出菜单
# ======================================================================================================================
    def OpenTouchMenu(self):
        """ 触屏上点了这一格：交给菜单（只记下，下一帧开 —— 这里是在点击绑定的回调里）。没有可做的事（空格子）不出 """
        menu = getattr(self.MainNode, "Menu", None)
        if menu is not None and self.MenuActions():
            menu.Request(self)

    def MenuActions(self):  # type: () -> tuple
        """
        触屏菜单里这一格出哪些动作（constants.ui.MenuKey，按顺序；「关闭」菜单自己加在最后）。
        缺省：有物品就来源、用途、收藏。别的面板按需覆写（收藏栏的格子出移除、配方收藏出打开这条配方…）；
        第三方面板继承 ItemPanel，不覆写就是缺省这一套
        """
        if self.Item is None:
            return ()
        return MenuKey.Source, MenuKey.Uses, MenuKey.Bookmark, MenuKey.RecipeTree

    def MenuKind(self):  # type: () -> any
        """ 触屏菜单顶栏左边写的「这是哪种格子」（MenuKindText）。缺省是物品；收藏格、多候选格覆写 """
        return MenuKindText.Item

    def ContentKey(self):  # type: () -> any
        """
        这一格现在显示的是什么：tooltip / 菜单显示时记下，之后变了（翻页、重排）就收起。缺省是物品；
        自己会换显示的面板（轮播的多候选格）要覆写成不随轮播变
        """
        return self.Item

    def SetItemStack(self, item_stack):  # type: (ItemStack) -> bool
        """ 初始化物品的信息 需要传入Item实例 """
        self.Stack = item_stack
        self.Item = item_stack.Item
        if not self.Item:
            return False

        self.SetUiItem()
        count = self.Stack.Count

        self.LabelVisible = True if count > 1 else False
        self.LabelText = str(count)

        self.RefreshHoverText()
        return True

    # hover 文本 —— 物品自带的部分 + 使用方追加的 lore
# ======================================================================================================================
    def SetLore(self, lore):  # type: (any) -> any
        """
        设置追加说明行；传 None 或空表示清空。可传单行字符串或字符串列表

        返回 self，所以能接在 `render_slot(...)` 后面一路写下去。

        字节串还是 unicode 都收 —— 拼接前统一经 `native_str` 收敛，见 `RefreshHoverText`。
        """
        if not lore:
            self.ItemLore = []
        elif isinstance(lore, basestring):
            self.ItemLore = [lore]
        else:
            self.ItemLore = [line for line in lore if line]
        self.RefreshHoverText()
        return self

    def AddLore(self, line):  # type: (any) -> any
        """ 追加一行说明 """
        if line:
            self.ItemLore.append(line)
            self.RefreshHoverText()
        return self

    def RefreshHoverText(self):
        """
        重算 hover 文本并**存下来**。

        这条绑定是 `always_when_visible`，会被每帧回读；在 property 里现拼
        就是每行每帧拼一遍（docs/architecture/binding_cost.md §4-A 的配套改动）。
        ⇒ 凡是会影响它的东西（换物品、改 lore）都要回来调这里。

        **每一段都先经 `native_str`**：`Item.HoverText` 是引擎给的、多为 unicode，
        而 lore 一般是源文件里的 utf-8 字节串 —— 直接相加两个方向都会出事：
          · `unicode + 含中文的字节串` → py2 按 ASCII 解码后者，UnicodeDecodeError；
          · 拼出 unicode 递给引擎 → **不抛不报，只是安静地取不到东西**（引擎结论 §2）。
        收敛到 str 之后两条都不成立。这正是 `utils/text.py` 存在的理由，不另发明规矩。
        """
        if self.Item is None:
            self.ItemHoverText = ""
            return
        text = native_str(self.Item.HoverText or "")
        if self.ItemLore:
            text += "\n\n" + "\n".join(native_str(line) for line in self.ItemLore)
        self.ItemHoverText = text

    @classmethod
    def from_item(cls, control, item):
        """ 通过传入的Item实例创建ItemPanel实例 """
        if not isinstance(item, Item):
            raise ValueError("item must be an instance of Item")
        ins = cls(control)
        if not ins.GetChildVisible():
            ins.SetChildVisible(True)
        ins.SetItemStack(item.stack(count=1))
        return ins

    @classmethod
    def from_item_stack(cls, control, item_stack):
        """ 通过传入的ItemStack实例创建ItemPanel实例 """
        if not isinstance(item_stack, ItemStack):
            raise ValueError("item must be an instance of ItemStack")
        ins = cls(control)
        if not ins.GetChildVisible():
            ins.SetChildVisible(True)
        ins.SetItemStack(item_stack)
        return ins

    @classmethod
    def from_empty(cls, control):
        """ 创建一个空的ItemPanel实例 """
        ins = cls(control)
        ins.SetChildVisible(False)
        return ins

    def SetUiItem(self):  # type: () -> 'bool'
        """ 设置Renderer控件显示的物品 (渲染四元组由 Stack 提供, 为 FluidStack 铺路) """
        item_id, aux_value, is_enchanted, user_data = self.Stack.get_render_data()
        suc = self.RendererControl.SetUiItem(item_id, aux_value, is_enchanted, user_data)
        if not suc:
            # 如果某些情况无法正确 SetUiItem 则直接隐藏 Renderer 控件 (例如 minecraft:air 就无法正常渲染)
            self.ItemRendererVisible = False
        for _control, renderer in getattr(self, "Mirrors", ()):
            renderer.SetUiItem(item_id, aux_value, is_enchanted, user_data)
        return suc

    def AddMirror(self, control):  # type: (any) -> bool
        """
        再挂一个画同一样东西的格子（JSON 里和本格写同一个绑定名前缀）。记下它的物品渲染器，已经有物品就当场画上；
        挂上了给 True（控件不在、已经挂过、取不到渲染器给 False）
        """
        if control is None or any(control is other for other in self.Controls()):
            return False
        renderer = self.MainNode.GetUIControl(control.GetPath() + "/item/renderer", "item_renderer", False)
        if renderer is None:
            return False
        self.Mirrors.append((control, renderer))
        if self.Stack is not None:
            renderer.SetUiItem(*self.Stack.get_render_data())
        return True

    def Controls(self):  # type: () -> list
        """ 这一格画在哪几个控件上：自己 + 镜像格（按矩形认格子的地方都问它：焦点查询、悬停核对）"""
        return [self.Control] + [control for control, _ in getattr(self, "Mirrors", ())]

    def SetChildVisible(self, is_visible):  # type: (bool) -> None
        """ 设置主要的子控件(/overlay, /item)是否可见 """
        self.ItemControlVisible = is_visible
        self.OverlayControlVisible = is_visible

    def GetChildVisible(self):  # type: () -> bool
        """ 获取主要的子控件(/overlay, /item)可见状态 """
        return self.ItemControlVisible

    def Destroy(self):
        self.Destroyed = True

    # MEI tooltip（docs/architecture/tooltip.md）
# ======================================================================================================================
    def HasMeiTooltip(self):  # type: () -> bool
        """
        悬停时出不出 MEI tooltip。悬停文字的绑定每帧都会问到这里（MeiTooltipHidesName），只能做便宜的判断：
        不碰引擎、不查配方。会出的面板覆写它（多候选格、配方收藏）
        """
        return False

    def TooltipContent(self):  # type: () -> tuple or None
        """
        (TooltipKind, 数据)：接受物品给多候选面板本身（标题跟着它当前的候选走），配方预览给配方或取配方的函数
        （显示时才找回）。不出 MEI tooltip 给 None。和 HasMeiTooltip 成对覆写
        """
        return None

    def MeiTooltipHidesName(self):  # type: () -> bool
        """
        这一格悬停时不出原版悬停文字（TooltipManager.HidesVanillaName）：PC 上由 MEI tooltip 代替的格子；
        触屏上一律不出 —— 划过就开菜单，菜单标题就是完整的悬停文字。白色高亮照常亮
        """
        tooltip = getattr(self.MainNode, "Tooltip", None)
        hides = getattr(tooltip, "HidesVanillaName", None) if tooltip is not None else None
        return bool(hides(self)) if callable(hides) else False

    @property
    def HoverProbe(self):  # type: () -> bool
        """
        悬停探针：格子按钮（btn_overlay）现成的 hover 控件上的绑定，条件 always_when_visible —— hover 只在光标下那一格亮，
        所以悬停期间每帧来一次。这里只报给 tooltip 管理器：PC 上它在每帧的 Update 里按光标位置核对、出 MEI tooltip；
        触屏上手指划过也会亮 hover，它认出「移进」的那一格就开菜单（绑定回调里不建控件、不绑定，引擎结论 §27-2）。返回值没人用
        """
        tooltip = getattr(self.MainNode, "Tooltip", None)
        if tooltip is not None:
            tooltip.Probe(self)
        return True

    @property
    def HoverText(self):  # type: () -> str
        """ 获取物品的 HoverText. 内容在 SetItemStack 时已算好, 这里只做纯返回；由 MEI tooltip 代替时给空 """
        if self.Item is None or self.MeiTooltipHidesName():
            return ""
        return self.ItemHoverText or ""
