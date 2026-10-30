# coding=utf-8

# ----------------------------------------------------------------------
#  recipe.py is part of MoreEnoughItems.
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
配方预览：在 tooltip 里只显示配方行 content 那一块，复用该类型自己的布局与配方页脚本，见 docs/architecture/tooltip.md §4。

做法（配方 JSON 规范，engineering.md §5）：每个类型的 wrapper 与 content 都写算出来的绝对尺寸、content 自包含，
类型 JSON 里一行 `"PREVIEW@mei_recipe_common.preview": {"$recipe_content_template": "<命名空间>.content_panel"}` ——
PREVIEW 就是整个 tooltip（背景、标题、1×1 的预览 grid），管理器显示一次只建它这一个控件；grid 的格子是
mei_recipe_common.preview_cell：骨架同样是 `wrapper/content`，content 就是该类型的 content_panel，格子跟着它的绝对尺寸走（100%c）。
配方页脚本照旧拿 `RecipeControl.GetChildByPath("/wrapper/content/...")` 取控件。
这里不建、不删控件，只在管理器给的 PREVIEW 里接上脚本：自己的 RecipesGridBind（集合 mei_tooltip_recipe）、格子长出来才 OnCreate、
第 0 帧立刻画、自己的节拍
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.common.classes.base import BaseRecipeUIScript
from MEIScripts.constants.ui import BindingConst, CollectionConst, TooltipPath
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.binding import RecipesGridBind
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.host import attach_script, detach_script, is_live
from MEIScripts.registry import RecipeManager, RecipeUIManager
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text

ViewBinder = clientApi.GetViewBinderCls()


def overrides_anim_tick(script_cls):  # type: (type) -> bool
    """ 脚本类覆写了 OnAnimTick 没有。比底下的函数对象 —— py2 的 unbound method 每次取都是新对象（配方页同一条）"""
    own = getattr(script_cls, "OnAnimTick", None)
    base = BaseRecipeUIScript.OnAnimTick
    return getattr(own, "__func__", own) is not getattr(base, "__func__", base)


class TooltipRecipeView(object):
    """ 一次只预览一条配方；收起时把绑定器、脚本一并拆掉，不留每帧的绑定（控件归管理器：藏着、复用或删） """

    BROKEN = set()  # type: set
    """
    建不出来、或建出来没有预览 grid 的 PREVIEW 定义名（第三方没照规范写那一行）：记下来，这一局不再试 ——
    悬停每帧都会报，不记的话每帧建一次、报一次错
    """
    LogTag = "tooltip"  # 接 / 拆脚本出错时日志的前缀（[MEI/tooltip]）；配方树菜单里的预览覆写成 tree

    def __init__(self, main_node):
        self.Bindings = ScreenBinder(main_node.ScreenNode)  # type: ScreenBinder  # 格子的 #visible 那一条
        self.MainNode = main_node
        self.GameComp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

        self.Recipe = None  # type: any
        self.Script = None  # type: any  # 该类型的配方页脚本实例，GridItemIndex 恒为 0
        self.Binder = None  # type: RecipesGridBind or None
        self.GridControl = None  # type: any
        self.VisibleWrapper = None  # type: any  # 格子的 #visible 绑定（恒为真；脚本在 Poll 里建）
        self.Timer = None  # type: any
        self.Ticks = 0  # type: int
        self.LastSize = None  # type: tuple or None  # 上一帧量到的 content 尺寸：两帧一样才算排好

    @classmethod
    def CanPreview(cls, recipe):  # type: (any) -> bool
        """ 这条配方的类型有预览 grid（缺省就有，见 RecipeCategory.PreviewDef）、建得出来、也注册了配方页脚本 """
        return cls.CanPreviewType(getattr(recipe, "Type", None))

    @classmethod
    def CanPreviewType(cls, category_id):  # type: (str) -> bool
        """ 同 CanPreview，只看类型（配方收藏建格子时还没找回配方）"""
        if not category_id:
            return False
        preview_def = RecipeManager.GetPreviewDef(category_id)
        return bool(preview_def) and preview_def not in cls.BROKEN \
            and RecipeUIManager.GetScriptData(category_id) is not None

    def Show(self, recipe, content_path):  # type: (any, str) -> bool
        """
        在 content_path（管理器建好或复用的、这个类型的 PREVIEW 控件）里预览这条配方；
        类型没有预览、或 PREVIEW 里没有预览 grid 返回 False
        """
        self.Hide()
        if not self.CanPreview(recipe):
            return False
        category_id = recipe.Type
        self.GridControl = self.MainNode.GetUIControl(content_path + TooltipPath.PreviewGridSub)
        if self.GridControl is None:
            preview_def = RecipeManager.GetPreviewDef(category_id)
            self.BROKEN.add(preview_def)
            logger.warn("[MEI/tooltip] 类型 {} 的 {} 里没有预览 grid：没派生自 mei_recipe_common.preview？（这一局不再试）".format(
                category_id, preview_def))
            return False

        script_cls = RecipeUIManager.GetScriptData(category_id)[0]
        try:
            script = script_cls(recipe)
        except Exception as e:  # noqa  第三方配方页脚本的构造抛了：这一条不出预览，调用方照「建不出来」处理、不每帧重试
            logger.error("[MEI/tooltip] 类型 {} 的配方页脚本建不出来: {}".format(category_id, error_text(e)))
            return False
        self.Binder = self.MakeBinder()
        self.Script = script
        self.Recipe = recipe
        self.VisibleWrapper = self.Bindings.Bind(
            self.GetPreviewVisible, ViewBinder.BF_BindBool, BindingConst.RecipeVisible, CollectionConst.TooltipRecipe)
        self.Ticks = 0
        self.Timer = self.GameComp.AddRepeatedTimer(BaseRecipeUIScript.ANIM_TICK_INTERVAL, self.OnAnimTimer)
        return True

    def MakeBinder(self):  # type: () -> RecipesGridBind
        """ 预览格子的绑定器（集合 mei_tooltip_recipe、行叫 preview_cell）；配方树菜单里的预览覆写成自己的 """
        return RecipesGridBind(self.MainNode.ScreenNode, CollectionConst.TooltipRecipe,
                               row_child_name=TooltipPath.PreviewCellName)

    def Poll(self):  # type: () -> bool
        """
        建好了没有（管理器构建期间每帧问一次，不在绑定回调里）：格子长出来就把脚本接上；
        content 的尺寸量得到、两帧一样大才算建好（尺寸是 JSON 里的绝对值，这里只是等它排出来）
        """
        script = self.Script
        if script is None or self.GridControl is None:
            return False
        cell = self.GridControl.GetChildByPath("/{}1".format(TooltipPath.PreviewCellName))
        content = cell.GetChildByPath(TooltipPath.PreviewContentSub) if cell is not None else None
        if content is None:
            return False
        if not getattr(script, "_Created", False):
            self.CreateScript(cell)
            return False
        width, height = content.GetSize()
        size = (int(round(width)), int(round(height)))
        ready = size[0] > 0 and size[1] > 0 and size == self.LastSize
        self.LastSize = size
        return ready

    def GetPreviewVisible(self, index):
        """
        预览格子的 #visible：恒为真。脚本不在这里建 —— 绑定回调里不建控件、不绑定（引擎结论 §27-2），
        挪到 Poll（管理器每帧调）里，等格子长出来再建
        """
        return True

    def CreateScript(self, cell):
        """ 格子长出来了（grid 子控件首次渲染前取不到，引擎结论 §5）：把配方页脚本接到这一格上、画第 0 帧 """
        script = self.Script
        if attach_script(script, 0, self.Binder, cell, self.LogTag):
            self.PrimeAnimTick(script)

    def PrimeAnimTick(self, script):
        """ 建好立刻画第 0 帧（配方页 PrimeAnimTick 同一条：不然有最长 0.4 秒停在布局初值上） """
        if not overrides_anim_tick(type(script)):
            return
        script._AnimBase = self.Ticks  # noqa
        self.DispatchAnimTick(script, 0)

    @staticmethod
    def DispatchAnimTick(script, ticks):
        try:
            script.OnAnimTick(ticks)
        except Exception as e:  # noqa  预览炸了不能停掉节拍
            logger.error("[MEI/tooltip] {} 的 OnAnimTick 抛异常: {}".format(type(script).__name__, error_text(e)))

    def OnAnimTimer(self):
        """ 预览自己的节拍：熔炉的火焰、多候选格的轮播照常动 """
        self.Ticks += 1
        script = self.Script
        if script is not None and is_live(script) and overrides_anim_tick(type(script)):
            if getattr(script, "_AnimBase", None) is None:
                self.PrimeAnimTick(script)
            else:
                self.DispatchAnimTick(script, self.Ticks - script._AnimBase)  # noqa
        if self.Binder is not None:
            self.Binder.TickPanels(self.Ticks)

    def Hide(self):
        """ 拆脚本、绑定、绑定器、节拍；控件不删（PREVIEW 归管理器：藏着，下次同一类型直接复用） """
        if self.Timer is not None:
            self.GameComp.CancelTimer(self.Timer)
            self.Timer = None
        script, self.Script = self.Script, None
        if script is not None:
            detach_script(script, self.LogTag)
        if self.VisibleWrapper is not None:
            self.Bindings.Unbind(self.VisibleWrapper)
            self.VisibleWrapper = None
        if self.Binder is not None:
            self.Binder.Destroy()
            self.Binder = None
        self.GridControl = None
        self.Recipe = None
        self.LastSize = None
