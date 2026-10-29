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
# 配方树的界面（PushScreen 一个全新的界面）。生命周期照 MEI 自己的界面（floating/screen.py，引擎结论 §35）：
# Create 只记一笔、第一次 Update 再建（SDK 在 Create 之后按 dir(self) 挂绑定，那时建的转发函数会被挂两遍）；
# 出栈时先拆（process_unbinding），Update / Destroy 一律接住异常（Destroy 抛出去界面就弹不掉）
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst, PathConst
from MEIScripts.constants.ui import TreeConst
from MEIScripts.utils.text import error_text

ScreenNode = clientApi.GetScreenNodeCls()

AFTER_CLOSE_DELAY = 0.1
""" 「查看配方页」：关掉配方树后过这么久再在下面的界面开配方页（等它露出来、悬浮窗显回来）"""


def register_screen():  # type: () -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    try:
        ok = clientApi.RegisterUI(NameConst.NameSpace, TreeConst.ScreenKey, PathConst.RecipeTreeScreenClsPath,
                                  TreeConst.ScreenDef)
    except Exception as e:  # noqa
        logger.error("[MEI/tree] 注册配方树界面失败: {}".format(error_text(e)))
        return False
    if not ok:
        logger.warn("[MEI/tree] 注册配方树界面失败：RegisterUI 返回 False")
    return bool(ok)


def open_screen(param):  # type: (dict) -> bool
    """ 开配方树（param 见 recipe_tree.OpenRecipeTree）。已经开着就开不出来（SDK 不让同一个界面压两次），返回 False """
    try:
        node = clientApi.PushScreen(NameConst.NameSpace, TreeConst.ScreenKey, param)
    except Exception as e:  # noqa
        logger.error("[MEI/tree] 打开配方树失败: {}".format(error_text(e)))
        return False
    if node is None:
        logger.warn("[MEI/tree] 打开配方树失败：PushScreen 返回 None（没注册上，或已经开着）")
        return False
    return True


def open_later(param):  # type: (dict) -> bool
    """ 排到下一拍再开（SDK 的定时器最短 0.05 秒，引擎结论 §30）：不在按钮回调里当场压栈 """
    try:
        game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        game.AddTimer(0.0, open_screen, param)
    except Exception as e:  # noqa
        logger.error("[MEI/tree] 排不上打开配方树: {}".format(error_text(e)))
        return False
    return True


def show_recipes(item, query_by):
    """ 配方树关掉之后：在下面的界面开这个物品的配方页（下面没有 MEI 时开 MEI 自己的界面）"""
    from MEIScripts.mei_mod.ui_script.mei_ui import context
    try:
        main = context.GetMainNode()
        if main is not None:
            main.ShowRecipeDetails(item, query_by)
            return
        from MEIScripts.mei_mod.ui_script.mei_ui.floating.screen import open_screen as open_mei
        open_mei({"item": item, "query_by": query_by})
    except Exception as e:  # noqa
        logger.error("[MEI/tree] 回去开配方页失败: {}".format(error_text(e)))


class RecipeTreeScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.Param = param if isinstance(param, dict) else {}
        self.Tree = None  # type: any  # RecipeTreeNode，第一次 Update 时建
        self.Created = False  # type: bool
        self.Failed = False  # type: bool  # 建不起来：不再试，关掉这个界面
        self.PopPending = False  # type: bool
        self._ready = True  # 引擎会吞 __init__ 的异常、拿半成品继续回调（引擎结论 §7）

    def Create(self):
        if getattr(self, "_ready", False):
            self.Created = True

    def Update(self):
        """ 每帧（每秒 30 次）。出错只记日志 —— 抛出去会带走 SDK 同一帧里别的界面 """
        if not getattr(self, "_ready", False) or not self.Created:
            return
        try:
            self.__Update()
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 每帧处理失败: {}".format(error_text(e)))

    def __Update(self):
        tree = self.Tree
        if self.PopPending or (tree is not None and tree.CloseRequested):
            self.PopPending = False
            if tree is not None:
                tree.CloseRequested = False
            self.__Pop()
            return
        if tree is None:
            if not self.Failed:
                self.__Build()
            return
        tree.OnTick()

    def __Build(self):
        from .node import RecipeTreeNode  # 控制器拉起一整套控件，用到才 import
        tree = RecipeTreeNode(self, self.Param)
        try:
            tree.OnCreate()
        except Exception as e:  # noqa
            self.Failed = True
            logger.error("[MEI/tree] 配方树建不起来，关掉这个界面: {}".format(error_text(e)))
            try:
                tree.OnDestroy()
            except Exception:  # noqa
                pass
            self.PopPending = True  # 别让玩家困在一个空界面里
            return
        self.Tree = tree

    def __Pop(self):
        """ 出栈。只在自己就是栈顶时 —— 上面压着别的界面时 PopScreen 弹掉的是别人 """
        if clientApi.GetTopScreen() is not self:
            logger.warn("[MEI/tree] 配方树不在栈顶，这次不关")
            return
        clientApi.PopScreen()

    def process_unbinding(self, *args, **kwargs):
        """ SDK 出栈时先按 dir(self) 摘一遍绑定、再调 Destroy：先把配方树拆了 —— 它挂的转发函数自己摘 """
        if getattr(self, "_ready", False):
            self.__TearDown()
        return ScreenNode.process_unbinding(self, *args, **kwargs)

    def Destroy(self):
        if getattr(self, "_ready", False):
            self.__TearDown()

    def __TearDown(self):
        tree, self.Tree = self.Tree, None
        if tree is None:
            return
        after = tree.AfterClose
        try:
            tree.OnDestroy()
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 拆配方树失败: {}".format(error_text(e)))
        if after is not None:
            try:
                game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
                game.AddTimer(AFTER_CLOSE_DELAY, show_recipes, after[0], after[1])
            except Exception as e:  # noqa
                logger.error("[MEI/tree] 排不上回去开配方页: {}".format(error_text(e)))
