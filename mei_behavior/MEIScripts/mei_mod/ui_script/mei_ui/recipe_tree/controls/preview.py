# coding=utf-8

# ----------------------------------------------------------------------
#  preview.py is part of MoreEnoughItems.
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
配方树节点菜单里的配方预览（在配方树页面渲染配方 ui_script，不支持预览的用配方条兜底）。

照 tooltip 的配方预览（tooltip/recipe.py、docs/architecture/tooltip.md §4：每个类型一个 PREVIEW 控件，里面 1×1 的预览 grid，
格子就是这个类型的 content，配方页脚本照旧接在上面）：

- 控件建在菜单内容里的插槽 `preview` 下（插槽锚左上、尺寸跟内容，脚本只挪插槽 —— PREVIEW 的根没写锚点、是居中的，引擎结论 §39）。
  一次只建一个，同一类型下次直接复用，换类型先删再建；底图换成透明的（菜单的框已经画了一个）；生下来全透明（JSON 的 alpha 0 +
  propagate_alpha），脚本接上、尺寸两帧一样才算建齐，菜单这才排版、拉回不透明；等 0.5 秒还没齐、或脚本接坏了就用配方条（TreeMenu.Tick）。
- **建的时候菜单宿主和插槽都得亮着**：藏着的话引擎不建预览 grid 的格子，等多久都是空的（每一类都会等到超时，引擎结论 §38）。
  整个菜单框透明着建（框的 alpha 0 + propagate_alpha，TreeMenu），插槽在 Begin 里亮；Begin 建控件、挂绑定，只在每帧的 Tick 里调。
- **配方页脚本与 ItemPanel 认的是「当前主节点」**（context.GetMainNode()：拿界面节点、按路径取控件）。配方树是 PushScreen 的另一块界面 ——
  这里**不动主节点的栈**，只在预览自己的代码里临时把主节点顶成配方树的壳（TreeShell，context.Using）：建脚本、接脚本、拆脚本、节拍、
  以及预览格子的每一条绑定回调（ItemPanel 在绑定回调里建）。快捷键、悬浮窗这些问当前主节点的，照旧拿到下面那块界面的。
- 点预览里的一格：不走全局的点击策略（那会去开配方页），交给菜单 —— 和点配方条一样，灰字写它的名字与数量。
"""
from mod_log import logger

from MEIScripts.constants.ui import CollectionConst, TooltipPath
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.binding import RecipesGridBind
from MEIScripts.mei_mod.ui_script.mei_ui.tooltip.recipe import TooltipRecipeView
from MEIScripts.registry import RecipeManager
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text, native_str

MAX_TICKS = 15
""" 等预览建齐最多等几帧（每秒 30 帧，0.5 秒；和 tooltip 一样）：还没齐就用配方条 """

CASTS = {
    "item_renderer": "asItemRenderer", "label": "asLabel", "image": "asImage", "button": "asButton", "grid": "asGrid",
    "stack_panel": "asStackPanel", "input_panel": "asInputPanel", "progress_bar": "asProgressBar",
    "scroll_view": "asScrollView", "switch_toggle": "asSwitchToggle",
}
""" GetUIControl 的 cast（和 core/script.py 的 UIScriptMain._CastControl 同一套名字）"""


def control_name(control_def):  # type: (str) -> str
    """ PREVIEW 控件的名字：带定义名（换类型时新旧不同名，删和建在同一帧也撞不上）"""
    return "tip_" + native_str(control_def).replace(".", "_")


class TreeShell(object):
    """
    配方树当「主节点」用的壳：只给配方页脚本与 ItemPanel 要的几样 —— 界面节点、按路径取控件（路径都是这块界面里的绝对路径）。
    没有 Tooltip、Menu（格子的悬停、触屏菜单都不出）；点格子由 TreeRecipesGridBind 接走，走不到 ShowRecipeDetails
    """
    Tooltip = None
    Menu = None
    RootPath = ""

    def __init__(self, screen):
        self.ScreenNode = screen

    def GetUIControl(self, path, cast=None, use_root_path=True):  # noqa  use_root_path：路径本来就是绝对的
        try:
            control = self.ScreenNode.GetBaseUIControl(path)
        except Exception:  # noqa
            return None
        if control is None or not cast:
            return control
        method = getattr(control, CASTS.get(cast, ""), None)
        return method() if method is not None else control

    @staticmethod
    def ShowRecipeDetails(*_args, **_kwargs):
        return False


class ScopedBinder(ScreenBinder):
    """ 挂上去的每一条绑定，回调都在 context.Using(壳) 里跑：预览格子的 ItemPanel 是在绑定回调里建的 """

    def __init__(self, shell):
        ScreenBinder.__init__(self, shell.ScreenNode)
        self.Shell = shell

    def Bind(self, callback, flag, name, collection=None):
        shell = self.Shell

        def scoped(*args):
            with context.Using(shell):
                return callback(*args)
        return ScreenBinder.Bind(self, scoped, flag, name, collection)


class TreeRecipesGridBind(RecipesGridBind):
    """ 预览格子的绑定器：绑定都经 ScopedBinder 挂；点格子交给菜单（on_slot(面板)），不走全局的点击策略 """

    def __init__(self, shell, on_slot):
        RecipesGridBind.__init__(self, shell.ScreenNode, CollectionConst.TooltipRecipe,
                                 row_child_name=TooltipPath.PreviewCellName)
        self.Bindings = ScopedBinder(shell)  # 这时还一条绑定都没挂
        self.OnSlot = on_slot

    def _OnSlotClick(self, ctx):
        if self.OnSlot is not None:
            self.OnSlot(ctx.Panel)


class TreeRecipeView(TooltipRecipeView):
    """ tooltip 那一套的配方预览，只是建 / 接 / 拆脚本、节拍都在 context.Using(壳) 里，绑定器换成 TreeRecipesGridBind """
    LogTag = "tree"

    def __init__(self, shell, on_slot):
        TooltipRecipeView.__init__(self, shell)
        self.OnSlot = on_slot

    def MakeBinder(self):
        return TreeRecipesGridBind(self.MainNode, self.OnSlot)

    def Show(self, recipe, content_path):
        with context.Using(self.MainNode):
            return TooltipRecipeView.Show(self, recipe, content_path)

    def CreateScript(self, cell):
        with context.Using(self.MainNode):
            TooltipRecipeView.CreateScript(self, cell)

    def OnAnimTimer(self):
        with context.Using(self.MainNode):
            TooltipRecipeView.OnAnimTimer(self)

    def Hide(self):
        with context.Using(self.MainNode):
            TooltipRecipeView.Hide(self)

    def Broken(self):  # type: () -> bool
        """ 配方页脚本接的时候抛了（attach_script 记过一行 error）：这个预览画不出东西，菜单改用配方条 """
        return bool(getattr(self.Script, "_Broken", False))

    def Stage(self):  # type: () -> str
        """ 建到哪一步了（等太久时写进警告：日志里一眼看出卡在哪）"""
        if self.Script is None or self.GridControl is None:
            return "没开始建"
        cell = self.GridControl.GetChildByPath("/{}1".format(TooltipPath.PreviewCellName))
        if cell is None:
            return "预览 grid 的格子没长出来（宿主或插槽藏着时引擎不建）"
        if cell.GetChildByPath(TooltipPath.PreviewContentSub) is None:
            return "格子里没有 content"
        if not getattr(self.Script, "_Created", False):
            return "配方页脚本还没接上"
        if self.Broken():
            return "配方页脚本接的时候出错（见上面的 error）"
        return "尺寸没定下来（{}）".format(self.LastSize)


class TreePreview(object):
    """ 菜单内容里的配方预览：一个 PREVIEW 控件（同类型复用）+ 接在上面的配方页脚本 """

    def __init__(self, screen, slot_path, on_slot):
        self.Screen = screen
        self.SlotPath = slot_path
        self.Slot = screen.GetBaseUIControl(slot_path)
        self.Shell = TreeShell(screen)
        self.View = TreeRecipeView(self.Shell, on_slot)
        self.Path = None  # type: str or None  # 现在这个 PREVIEW 控件的路径
        self.Def = None  # type: str or None
        self.RecipeId = None  # type: str or None  # 正在预览 / 已经建好的那条配方
        self.Ready = False  # type: bool
        self.Ticks = 0  # type: int
        self.Size = (0, 0)  # type: tuple  # 建齐后量到的 PREVIEW 尺寸（含它自己四周各 4 的边）

    @staticmethod
    def Supports(recipe):  # type: (any) -> bool
        """ 这条配方的类型有预览（缺省就有，`preview_def=None` 的没有）、也注册了配方页脚本 """
        return recipe is not None and TooltipRecipeView.CanPreview(recipe)

    def Showing(self, recipe):  # type: (any) -> bool
        """ 这一条已经建齐、正亮着（菜单重排时不重建，当场排）"""
        return self.Ready and self.Path is not None and recipe is not None \
            and getattr(recipe, "Id", None) == self.RecipeId

    def Building(self, recipe):  # type: (any) -> bool
        """ 这一条已经开始建、还没齐（建的这几帧里菜单又排了一次：接着建，不从头来）"""
        return not self.Ready and self.Path is not None and self.View.Script is not None and recipe is not None \
            and getattr(recipe, "Id", None) == self.RecipeId

    def Begin(self, recipe, title):  # type: (any, any) -> bool
        """
        开始建这条配方的预览（透明着建，TreeMenu.Tick 每帧 Poll）；同一条已经建好的不重建。
        类型不支持、建不出来返回 False —— 菜单用配方条。
        **要在每帧的 Tick 里调，不在按钮回调里**：这里建控件、挂绑定（引擎结论 §27-2；TreeMenu.Show 只记下，下一帧再来）。
        插槽这时就亮出来：宿主、插槽藏着的话引擎不建预览 grid 的格子（引擎结论 §38），PREVIEW 自己是全透明的，亮着也看不见
        """
        if self.Slot is None or not self.Supports(recipe):
            self.Stop()
            return False
        if self.Showing(recipe):
            return True
        path = self.__Mount(RecipeManager.GetPreviewDef(recipe.Type))
        if path is None or not self.View.Show(recipe, path):
            self.Stop()
            return False
        self.__SetTitle(title)
        self.Slot.SetVisible(True)
        self.RecipeId, self.Ready, self.Ticks, self.Size = getattr(recipe, "Id", None), False, 0, (0, 0)
        return True

    def Poll(self):  # type: () -> bool
        """ 建齐了没有：脚本接上、尺寸两帧一样（TooltipRecipeView.Poll）；齐了量一次尺寸。脚本接坏了的不算齐（TimedOut 当场为真）"""
        if self.Ready:
            return True
        self.Ticks += 1
        if not self.View.Poll() or self.View.Broken():
            return False
        tip = self.Screen.GetBaseUIControl(self.Path) if self.Path is not None else None
        if tip is None:
            return False
        width, height = tip.GetSize()
        self.Size = (int(round(width)), int(round(height)))
        self.Ready = self.Size[0] > 0 and self.Size[1] > 0
        return self.Ready

    def TimedOut(self):  # type: () -> bool
        """ 不用再等了：等够 MAX_TICKS 帧还没齐，或者配方页脚本接坏了 """
        return not self.Ready and (self.Ticks >= MAX_TICKS or self.View.Broken())

    def Stage(self):  # type: () -> str
        return self.View.Stage()

    def Reveal(self, pos):  # type: (tuple) -> None
        """ 菜单排好了：插槽摆到 pos（菜单内容里的坐标），拉回不透明 """
        if self.Slot is not None:
            self.Slot.SetPosition((int(pos[0]), int(pos[1])))
            self.Slot.SetVisible(True)
        tip = self.Screen.GetBaseUIControl(self.Path) if self.Path is not None else None
        if tip is not None:
            tip.SetAlpha(1.0)

    def Stop(self):
        """ 收起：拆脚本、绑定器、节拍；控件藏着留给下一次同一类型（全透明） """
        self.View.Hide()
        self.RecipeId, self.Ready, self.Ticks = None, False, 0
        tip = self.Screen.GetBaseUIControl(self.Path) if self.Path is not None else None
        if tip is not None:
            tip.SetAlpha(0.0)
        if self.Slot is not None:
            self.Slot.SetVisible(False)

    def Destroy(self):
        """ 关配方树：拆完再删控件 """
        self.Stop()
        self.__Discard()

    def __Mount(self, preview_def):  # type: (str) -> str or None
        """ 同一类型复用（透明度先写回 0）；换类型先删旧的再建新的（生下来全透明、底图换成透明的）"""
        if self.Path is not None and self.Def == preview_def:
            tip = self.Screen.GetBaseUIControl(self.Path)
            if tip is not None:
                tip.SetAlpha(0.0)
                return self.Path
        self.__Discard()
        name = control_name(preview_def)
        try:
            self.Screen.CreateChildControl(preview_def, name, self.Slot, True)
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 配方预览 {} 建不出来: {}".format(native_str(preview_def), error_text(e)))
            return None
        path = self.SlotPath + "/" + name
        tip = self.Screen.GetBaseUIControl(path)
        if tip is None:
            logger.error("[MEI/tree] 配方预览 {} 建不出来".format(native_str(preview_def)))
            return None
        tip.SetAlpha(0.0)
        try:
            tip.asImage().SetSprite(TooltipPath.BlankSprite)  # 菜单的框已经画了一个，预览不再画自己的 purpleBorder
        except Exception as e:  # noqa
            logger.warn("[MEI/tree] 换不了配方预览的底图（会多画一层框）: {}".format(error_text(e)))
        self.Path, self.Def = path, preview_def
        return path

    def __Discard(self):
        path, self.Path, self.Def = self.Path, None, None
        control = self.Screen.GetBaseUIControl(path) if path is not None else None
        if control is not None:
            try:
                self.Screen.RemoveChildControl(control)
            except Exception as e:  # noqa
                logger.error("[MEI/tree] 删不掉配方预览: {}".format(error_text(e)))

    def __SetTitle(self, text):  # type: (any) -> None
        label = self.Screen.GetBaseUIControl(self.Path + TooltipPath.TitleSub) if self.Path is not None else None
        if label is not None:
            label.asLabel().SetText(native_str(text or ""))
