# coding=utf-8

# ----------------------------------------------------------------------
#  bookmark.py is part of MoreEnoughItems.
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
"""
收藏栏的格子：物品或配方收藏，带数量、左上角标记、分组边框与修饰键高亮。格子内容来自 modules/layout.py 的 Cell。
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import BookmarkText, MenuKindText
from MEIScripts.constants.ui import MenuKey, TooltipKind
from MEIScripts.mei_mod.state import BookmarkResolver
from MEIScripts.mei_mod.state.bookmarks import KIND_RECIPE, KIND_TREE, entry_identity
from MEIScripts.mei_mod.ui_script.controls.item import ItemPanel, ItemsGrid
from MEIScripts.mei_mod.ui_script.mei_ui.items_sidebar.modules.layout import (
    ROLE_ITEM, ROLE_OUTPUT, ROLE_RECIPE, ROLE_TREE, ROLE_TREE_ROOT, frame_key,
)
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.recipe import TooltipRecipeView
from MEIScripts.registry import RecipeManager
from MEIScripts.utils import utilities
from MEIScripts.utils.text import native_str, to_unicode

ViewBinder = clientApi.GetViewBinderCls()


def format_amount(amount):  # type: (int) -> str
    """ 格子右下角的数量，一万起缩写成 k """
    if amount >= 10000:
        return "{}k".format(amount // 1000)
    return str(amount)


class BookmarkItemsGrid(ItemsGrid):
    """
    收藏栏的 grid：通用槽位绑定之外再挂四条边框、左上角标记与高亮，绑定名与 bookmark_item_panel 的 JSON 一一对应
    """
    BORDER_ATTRS = (
        ("left", "BorderLeftVisible"),
        ("right", "BorderRightVisible"),
        ("top", "BorderTopVisible"),
        ("bottom", "BorderBottomVisible"),
    )

    def InitBindings(self):
        configs = self.GetDefaultBindingConfigs()
        for side, attr in self.BORDER_ATTRS:
            configs.append({
                "suffix": ".item.background.border.{}.visible".format(side),
                "flag": ViewBinder.BF_BindBool,
                "attr": attr,
                "default": False,
                "can_pause": True,
            })
        configs.extend([
            {
                "suffix": ".item.marker.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "MarkerVisible",
                "default": False,
                "can_pause": True,
            },
            {
                "suffix": ".item.marker.text",
                "flag": ViewBinder.BF_BindString,
                "attr": "MarkerText",
                "default": "",
                "can_pause": True,
            },
            {
                # 按住 Ctrl / Shift 悬停时同一条收藏的格子着色：值变了由脚本 Wake 这个 grid 再拉一遍
                "suffix": ".item.highlight.visible",
                "flag": ViewBinder.BF_BindBool,
                "attr": "HighlightVisible",
                "default": False,
                "can_pause": True,
            },
        ])
        self.BindConfigs(self.BuildConfigs(configs))


class BookmarkItemPanel(ItemPanel):
    """
    收藏栏的一格：物品找不回时不画图标，左上角打问号，悬停写存下的 id
    """
    def __init__(self, control):
        ItemPanel.__init__(self, control)
        self.Cell = None
        self.BorderLeftVisible = False
        self.BorderRightVisible = False
        self.BorderTopVisible = False
        self.BorderBottomVisible = False
        self.MarkerVisible = False
        self.MarkerText = ""
        self.HighlightVisible = False  # type: bool  # 修饰键高亮：脚本按光标下那一条写
        self.RecipePreview = False  # type: bool  # 这一格悬停时出配方预览（SetCell 时算好：悬停文字每帧都会问）

    @classmethod
    def from_cell(cls, control, cell, edges):
        ins = cls(control)
        ins.SetCell(cell, edges)
        return ins

    def SetCell(self, cell, edges):
        self.Cell = cell
        self.RecipePreview = False
        self.SetEdges(edges)
        # 分组的格子、不在分组里的展开配方都画底色（框见 layout.frame_key）
        self.BackgroundVisible = frame_key(cell) is not None
        self.MarkerText = cell.Marker or ""
        self.MarkerVisible = bool(cell.Marker)
        item = self.__ResolveItem(cell)
        if item is None:
            self.ShowInvalid(cell)
            return
        self.SetChildVisible(True)
        self.SetItemStack(item.stack(count=1))
        self.LabelVisible = cell.Amount > 1
        self.LabelText = format_amount(cell.Amount)
        if cell.Entry.get("k") == KIND_RECIPE and cell.Role in (ROLE_RECIPE, ROLE_OUTPUT):
            self.SetLore(BookmarkText.RecipeLore)
            # 类型有预览（缺省就有）就出配方预览；找不回的配方、建不出来的预览显示时才知道，那时改回原版名，见 ResolveRecipe
            preview_def = RecipeManager.GetPreviewDef(cell.Entry.get("cat"))
            self.RecipePreview = bool(preview_def) and preview_def not in TooltipRecipeView.BROKEN
        elif self.IsTreeCell():
            self.SetLore(BookmarkText.TreeLore)

    @staticmethod
    def __ResolveItem(cell):  # type: (any) -> any
        if cell.Stack is not None:
            return getattr(cell.Stack, "Item", None)
        if cell.Data is not None:
            return BookmarkResolver.ResolveItem(cell.Data)
        return None

    def ShowInvalid(self, cell):
        # 格子是 grid 复用的：上一页留下的物品要清掉，不然点失效格会查到别的物品、触屏菜单也会当它还有物品
        self.Item = None
        self.Stack = None
        self.SetChildVisible(True)
        self.ItemRendererVisible = False
        self.LabelVisible = False
        self.MarkerText = "?"
        self.MarkerVisible = True
        data = cell.Data if isinstance(cell.Data, dict) else cell.Entry
        name = data.get("id") or "?"
        self.ItemHoverText = native_str(BookmarkText.Invalid.format(to_unicode(name)))

    def SetEdges(self, edges):
        """ 分组外轮廓：0 上、1 下、2 左、3 右，同 GroupBorderCalculator """
        self.BorderTopVisible = 0 in edges
        self.BorderBottomVisible = 1 in edges
        self.BorderLeftVisible = 2 in edges
        self.BorderRightVisible = 3 in edges

    def IsRecipeCell(self):  # type: () -> bool
        """ 点开的是不是这条配方收藏本身（横排那一格，或竖排清单里的产物格）"""
        cell = self.Cell
        return cell is not None and cell.Entry.get("k") == KIND_RECIPE and cell.Role in (ROLE_RECIPE, ROLE_OUTPUT)

    def IsTreeCell(self):  # type: () -> bool
        """ 点开的是不是这条配方树收藏本身（收起时那一格，或展开那一行打头的根）"""
        cell = self.Cell
        return cell is not None and cell.Entry.get("k") == KIND_TREE and cell.Role in (ROLE_TREE, ROLE_TREE_ROOT)

    def OnPrimaryClick(self, _):
        if self.Cell is None:
            return
        if utilities.GetInputMode() == 1:
            self.OpenTouchMenu()
            return
        if self.IsTreeCell():
            from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree  # 配方树用到才 import
            OpenRecipeTree(saved=self.Cell.Entry)
        elif self.IsRecipeCell():
            self.MainNode.ShowBookmarkedRecipe(self.Cell.Entry)
        elif self.Item is not None:
            self.MainNode.ShowRecipeDetails(self.Item, QueryConst.Output)

    def OnSecondaryClick(self, _):
        if utilities.GetInputMode() == 1 or self.Item is None:
            return
        self.MainNode.ShowRecipeDetails(self.Item, QueryConst.Input)

    RECIPE_ACTIONS = (MenuKey.OpenRecipe, MenuKey.Expand, MenuKey.CountDown, MenuKey.CountUp,
                      MenuKey.MoveUp, MenuKey.MoveDown, MenuKey.MoveHead, MenuKey.JoinGroup, MenuKey.LeaveGroup,
                      MenuKey.View, MenuKey.Remove, MenuKey.RemoveGroup)
    """ 配方收藏的菜单动作（顺序就是按钮的顺序，两列从上往下填）"""

    TREE_ACTIONS = (MenuKey.OpenTree, MenuKey.Expand, MenuKey.MoveUp, MenuKey.MoveDown, MenuKey.MoveHead,
                    MenuKey.JoinGroup, MenuKey.LeaveGroup, MenuKey.View, MenuKey.Remove, MenuKey.RemoveGroup)
    """ 配方树收藏的菜单动作：打开、展开（原料汇总）、排序、分组、横竖排、删除；数量在树里改（存在条目的 count 里）"""

    ITEM_ACTIONS = (MenuKey.Source, MenuKey.Uses, MenuKey.RecipeTree, MenuKey.CountDown, MenuKey.CountUp,
                    MenuKey.MoveUp, MenuKey.MoveDown, MenuKey.MoveHead, MenuKey.JoinGroup, MenuKey.LeaveGroup,
                    MenuKey.FoldGroup, MenuKey.View, MenuKey.Remove, MenuKey.RemoveGroup)
    """ 物品收藏的菜单动作 """

    def MenuActions(self):  # type: () -> tuple
        """
        触屏菜单（tooltip.md §6.6）：配方收藏、物品收藏各一套（数量、排序、分组、横竖排、移除、删除整组；配方多「打开配方 / 展开」，
        物品多「来源 / 用途 / 折叠」）；失效的只有移除；展开配方里的原料 / 工具格是配方里的物品、不是收藏条目，按普通格子来
        """
        cell = self.Cell
        if cell is None:
            return ()
        if self.IsRecipeCell():
            return self.RECIPE_ACTIONS
        if self.IsTreeCell():
            return self.TREE_ACTIONS
        if cell.Role != ROLE_ITEM:
            return ItemPanel.MenuActions(self)
        if self.Item is None:
            return (MenuKey.Remove,)
        return self.ITEM_ACTIONS

    def MenuKind(self):  # type: () -> any
        """ 触屏菜单顶栏：收藏的物品 / 配方 / 失效的收藏；展开配方里的原料、工具格是配方里的物品 """
        cell = self.Cell
        if cell is None:
            return ItemPanel.MenuKind(self)
        if self.IsRecipeCell():
            return MenuKindText.BookmarkRecipe
        if self.IsTreeCell():
            return MenuKindText.BookmarkTree
        if cell.Role != ROLE_ITEM:
            return MenuKindText.RecipePart
        if self.Item is None:
            return MenuKindText.BookmarkInvalid
        return MenuKindText.BookmarkItem

    def ContentKey(self):  # type: () -> any
        """
        收藏格显示的是哪一条：页签里的位置、角色、条目的身份。数量变了、重排出新的 Cell 都不算换（菜单不收），
        翻页、切页签、删掉了才算
        """
        cell = self.Cell
        if cell is None:
            return None
        return cell.Index, cell.Role, entry_identity(cell.Entry)

    def HasMeiTooltip(self):  # type: () -> bool
        return self.RecipePreview

    def TooltipContent(self):  # type: () -> tuple or None
        """ 配方收藏：显示时才去找回那条配方（悬停到了才查，不在建格子时查）"""
        if not self.RecipePreview or self.Cell is None:
            return None
        return TooltipKind.Recipe, self.ResolveRecipe

    def ResolveRecipe(self):  # type: () -> any
        """
        找不回（配方 Id 变了、类型没了），或这个类型的预览建不出来（第三方没写 PREVIEW 那一行）就不再出预览：
        不然 PC 上悬停什么都不出，原版名下一帧起照常
        """
        recipe = BookmarkResolver.ResolveRecipe(self.Cell.Entry) if self.Cell is not None else None
        if recipe is None or not TooltipRecipeView.CanPreview(recipe):
            self.RecipePreview = False
            return None
        return recipe

    @property
    def HoverText(self):  # type: () -> str
        """ 失效格没有 Item 也要有悬停文字，所以不走基类「没物品就空」的判断；由 MEI tooltip 代替时给空 """
        if self.MeiTooltipHidesName():
            return ""
        return self.ItemHoverText or ""
