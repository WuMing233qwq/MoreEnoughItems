# coding=utf-8

# ----------------------------------------------------------------------
#  screen.py is part of MoreEnoughItems.
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
# MEI 自己的界面：HUD 上点悬浮窗的 MEI、在 HUD 上查到配方时不在游戏界面里展开，PushScreen 开这个空界面，
# MEI 照支持的界面那样建在它的根面板下（docs/architecture/floating.md §6.1）
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst, PathConst, QueryConst
from MEIScripts.constants.ui import FloatConst
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.floating.hosts import InjectedProxy
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_SCREEN
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text

ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()

SCREEN_PARAMS = {"ContentPaths": []}
""" 这个界面没有原版内容：不登记避让目标。画布派生自 common.base_screen，根面板的路径与原版界面相同，用主节点缺省的那条 """

RECIPE_DELAY = 3
""" 带着配方开的：MEI 建好后再等这么多帧才开配方页，让刚建的两栏先排好 """


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    try:
        ok = clientApi.RegisterUI(NameConst.NameSpace, FloatConst.ScreenKey, PathConst.MeiScreenClsPath, FloatConst.ScreenDef)
    except Exception as e:  # noqa
        logger.error("[MEI/screen] 注册 MEI 界面失败: {}".format(error_text(e)))
        return False
    if not ok:
        logger.warn("[MEI/screen] 注册 MEI 界面失败：RegisterUI 返回 False")
    return bool(ok)


def open_screen(recipe=None):  # type: (dict or None) -> bool
    """
    开 MEI 自己的界面。recipe 是开好后要打开的配方页：{"item", "query_by", "prefer_type", "focus_id"}。
    栈里已经有它就开不出来（SDK 不让同一个界面压两次），返回 False
    """
    try:
        node = clientApi.PushScreen(NameConst.NameSpace, FloatConst.ScreenKey, {"recipe": recipe} if recipe else None)
    except Exception as e:  # noqa
        logger.error("[MEI/screen] 打开 MEI 界面失败: {}".format(error_text(e)))
        return False
    if node is None:
        logger.warn("[MEI/screen] 打开 MEI 界面失败：PushScreen 返回 None（没注册上，或已经开着）")
        return False
    return True


def request_close(node):  # type: (any) -> bool
    """ 关掉 MEI 自己的界面：只记下，它下一帧在自己的 Update 里出栈 —— 不在按钮回调、别人的每帧处理里当场拆掉整个界面 """
    if not isinstance(node, MeiScreen):
        return False
    node.CloseRequested = True
    return True


class MeiScreen(ScreenNode):
    """
    PushScreen 开的空界面，MEI 建在它的根面板下（主节点 KIND_SCREEN）：一打开就是从悬浮窗点开的样子（带黑底），
    点悬浮窗的 MEI、点黑底、按 ESC 或背包键都是关掉它
    """
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        param = param or {}
        self.Recipe = param.get("recipe")  # type: dict or None  # 开好后要打开的配方页，开过就清掉
        self.RecipeDelay = RECIPE_DELAY  # type: int
        self.Main = None  # type: any  # UIMainNode，第一次 Update 时建
        self.Bindings = None  # type: ScreenBinder or None  # 关闭键的绑定
        self.Created = False  # type: bool  # 引擎调过 Create 了
        self.Failed = False  # type: bool  # MEI 没建起来：不再试，关掉这个界面
        self.CloseRequested = False  # type: bool
        self._ready = True  # 引擎会吞 __init__ 的异常、拿半成品继续回调（引擎结论 §7）

    def Create(self):
        """
        MEI 不在这里建：SDK 调完 Create 紧接着按 dir(self) 把带绑定标记的属性挂一遍（process_binding），
        这时 ScreenBinder 已经挂在界面上的转发函数会被再挂一遍 —— 第一次 Update 再建
        """
        if getattr(self, "_ready", False):
            self.Created = True

    def Update(self):
        """ 每帧（每秒 30 次）。出错只记日志 —— 抛出去会带走 SDK 同一帧里别的界面 """
        if not getattr(self, "_ready", False) or not self.Created:
            return
        try:
            self.__Update()
        except Exception as e:  # noqa
            logger.error("[MEI/screen] 每帧处理失败: {}".format(error_text(e)))

    def __Update(self):
        if self.CloseRequested:
            self.CloseRequested = False
            self.__Pop()
            return
        if self.Main is None:
            if not self.Failed:
                self.__Build()
            return
        if self.Recipe is not None:
            self.RecipeDelay -= 1
            if self.RecipeDelay <= 0:
                recipe, self.Recipe = self.Recipe, None
                self.Main.ShowRecipeDetails(recipe.get("item"), recipe.get("query_by") or QueryConst.Output,
                                            prefer_type=recipe.get("prefer_type"), focus_id=recipe.get("focus_id"))
        # 上面又压了一个开着 MEI 的界面时，归它推（主节点的栈，core/context.py）
        if context.GetMainNode() is self.Main:
            self.Main.OnTick()

    def __Build(self):
        from MEIScripts.mei_mod.ui_script.mei_ui.core.node import UIMainNode  # 主节点拉起整个界面栈，用到才 import
        self.Bindings = ScreenBinder(self)
        self.Bindings.Bind(self.OnCloseKey, ViewBinder.BF_ButtonClickUp, FloatConst.ScreenClose)
        main = UIMainNode(InjectedProxy(self), kind=KIND_SCREEN, params=dict(SCREEN_PARAMS))
        try:
            main.OnCreate()
        except Exception as e:  # noqa
            self.Failed = True
            logger.error("[MEI/screen] MEI 界面里建不起 MEI，关掉这个界面: {}".format(error_text(e)))
            try:
                main.OnDestroy()
            except Exception:  # noqa
                pass
            self.CloseRequested = True  # 别让玩家困在一个空界面里
            return
        self.Main = main

    def OnCloseKey(self, _args=None):
        """ ESC、背包键（画布上 global 映射到 FloatConst.ScreenClose）"""
        self.CloseRequested = True

    def __Pop(self):
        """ 出栈。只在自己就是栈顶时 —— 上面压着别的界面时 PopScreen 弹掉的是别人 """
        if clientApi.GetTopScreen() is not self:
            logger.warn("[MEI/screen] MEI 界面不在栈顶，这次不关")
            return
        clientApi.PopScreen()

    def process_unbinding(self, *args, **kwargs):
        """
        SDK 出栈时先按 dir(self) 摘一遍绑定、再调 Destroy：先把 MEI 拆了 —— 它挂的转发函数自己摘、从界面上删掉，
        不然要被摘两遍
        """
        if getattr(self, "_ready", False):
            self.__TearDown()
        return ScreenNode.process_unbinding(self, *args, **kwargs)

    def Destroy(self):
        """ 出栈之后（SDK 不接这里的异常：抛出去界面就弹不掉，一律接住）"""
        if getattr(self, "_ready", False):
            self.__TearDown()

    def __TearDown(self):
        main, self.Main = self.Main, None
        self.Recipe = None
        if main is not None:
            try:
                main.OnDestroy()
            except Exception as e:  # noqa
                logger.error("[MEI/screen] 拆 MEI 界面里的 MEI 失败: {}".format(error_text(e)))
        bindings, self.Bindings = self.Bindings, None
        if bindings is not None:
            try:
                bindings.UnbindAll()
            except Exception as e:  # noqa
                logger.warn("[MEI/screen] 摘 MEI 界面的关闭键失败: {}".format(error_text(e)))
