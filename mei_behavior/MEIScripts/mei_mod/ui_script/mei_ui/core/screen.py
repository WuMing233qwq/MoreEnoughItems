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
"""
MEI 压栈开的界面（PushScreen）的通用部分：界面里建一个 MEI 主节点（UIMainNode，KIND 定种类），照支持的界面那样建在它的根面板下。
MEI 自己的界面（floating/screen.py）、MEI 编辑器（editor/screen.py）都继承它；不要主节点的（自定义配方管理器）继承 PlainScreen。

时序照引擎结论 §35：SDK 调完 Create 紧接着按 dir(self) 把带绑定标记的属性挂一遍，所以 Create 只记一笔、第一次 Update 再建；
Update 在 Create 之前就开始被调；出栈时先 process_unbinding、再 Destroy，Destroy 抛了界面就弹不掉 —— 一律接住。
关界面只记下，下一帧在自己的 Update 里出栈（不在按钮回调、别人的每帧处理里当场拆掉整个界面），而且只在自己是栈顶时
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text

ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()


def register(namespace, key, cls_path, screen_def, label):  # type: (str, str, str, str, str) -> bool
    """ 每次进存档（UiInitFinished）注册一次：SDK 进存档重建界面管理器时把注册表清了 """
    try:
        ok = clientApi.RegisterUI(namespace, key, cls_path, screen_def)
    except Exception as e:  # noqa
        logger.error("[MEI/screen] 注册{}失败: {}".format(label, error_text(e)))
        return False
    if not ok:
        logger.warn("[MEI/screen] 注册{}失败：RegisterUI 返回 False".format(label))
    return bool(ok)


def push(namespace, key, param, label):  # type: (str, str, any, str) -> bool
    """ 开一个注册过的界面。栈里已经有它就开不出来（SDK 不让同一个界面压两次），返回 False """
    try:
        node = clientApi.PushScreen(namespace, key, param)
    except Exception as e:  # noqa
        logger.error("[MEI/screen] 打开{}失败: {}".format(label, error_text(e)))
        return False
    if node is None:
        logger.warn("[MEI/screen] 打开{}失败：PushScreen 返回 None（没注册上，或已经开着）".format(label))
        return False
    return True


class MainScreen(ScreenNode):
    """
    子类给 KIND（主节点的种类）、PARAMS（界面参数）、CLOSE_NAME（ESC、背包键在画布上 global 映射到的按钮名）、LABEL（日志里叫什么），
    覆写 OnBuilt（主节点建好以后）、OnFrame（每帧，主节点推过之后）、OnTearDown（拆主节点之前）
    """

    KIND = ""
    PARAMS = {"ContentPaths": []}
    """ 压栈开的界面没有原版内容：不登记避让目标。画布派生自 common.base_screen，根面板的路径与原版界面相同，用主节点缺省的那条 """
    CLOSE_NAME = ""
    LABEL = "MEI 界面"

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.Main = None  # type: any  # UIMainNode，第一次 Update 时建
        self.Bindings = None  # type: ScreenBinder or None
        self.Created = False  # type: bool  # 引擎调过 Create 了
        self.Failed = False  # type: bool  # MEI 没建起来：不再试，关掉这个界面
        self.CloseRequested = False  # type: bool
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
            logger.error("[MEI/screen] {}每帧处理失败: {}".format(self.LABEL, error_text(e)))

    def __Update(self):
        if self.CloseRequested:
            self.CloseRequested = False
            self.__Pop()
            return
        if self.Main is None:
            if not self.Failed:
                self.__Build()
            return
        # 上面又压了一个开着 MEI 的界面时，归它推（主节点的栈，core/context.py）
        if context.GetMainNode() is self.Main:
            self.Main.OnTick()
        self.OnFrame()

    def __Build(self):
        from MEIScripts.mei_mod.ui_script.mei_ui.core.node import UIMainNode  # 主节点拉起整个界面栈，用到才 import
        from MEIScripts.mei_mod.ui_script.mei_ui.floating.hosts import InjectedProxy
        self.Bindings = ScreenBinder(self)
        if self.CLOSE_NAME:
            self.Bindings.Bind(self.OnCloseKey, ViewBinder.BF_ButtonClickUp, self.CLOSE_NAME)
        main = UIMainNode(InjectedProxy(self), kind=self.KIND, params=dict(self.PARAMS))
        try:
            main.OnCreate()
            self.Main = main
            self.OnBuilt()
        except Exception as e:  # noqa
            self.Failed = True
            logger.error("[MEI/screen] {}里建不起 MEI，关掉这个界面: {}".format(self.LABEL, error_text(e)))
            self.Main = None
            try:
                main.OnDestroy()
            except Exception:  # noqa
                pass
            self.CloseRequested = True  # 别让玩家困在一个空界面里

    def OnBuilt(self):
        """ 主节点建好以后（子类覆写）"""

    def OnFrame(self):
        """ 每帧，主节点推过之后（子类覆写）"""

    def OnTearDown(self):
        """ 拆主节点之前（子类覆写）"""

    def OnCloseKey(self, _args=None):
        """ ESC、背包键（画布上 global 映射到 CLOSE_NAME）"""
        self.RequestClose()

    def RequestClose(self):
        self.CloseRequested = True

    def __Pop(self):
        """ 出栈。只在自己就是栈顶时 —— 上面压着别的界面时 PopScreen 弹掉的是别人 """
        if clientApi.GetTopScreen() is not self:
            logger.warn("[MEI/screen] {}不在栈顶，这次不关".format(self.LABEL))
            return
        clientApi.PopScreen()

    def process_unbinding(self, *args, **kwargs):
        """
        SDK 出栈时先按 dir(self) 摘一遍绑定、再调 Destroy：先把 MEI 拆了 —— 它挂的转发函数自己摘、从界面上删掉，不然要被摘两遍
        """
        if getattr(self, "_ready", False):
            self.__TearDown()
        return ScreenNode.process_unbinding(self, *args, **kwargs)

    def Destroy(self):
        """ 出栈之后（SDK 不接这里的异常：抛出去界面就弹不掉，一律接住）"""
        if getattr(self, "_ready", False):
            self.__TearDown()

    def __TearDown(self):
        try:
            self.OnTearDown()
        except Exception as e:  # noqa
            logger.error("[MEI/screen] 拆{}失败: {}".format(self.LABEL, error_text(e)))
        main, self.Main = self.Main, None
        if main is not None:
            try:
                main.OnDestroy()
            except Exception as e:  # noqa
                logger.error("[MEI/screen] 拆{}里的 MEI 失败: {}".format(self.LABEL, error_text(e)))
        bindings, self.Bindings = self.Bindings, None
        if bindings is not None:
            try:
                bindings.UnbindAll()
            except Exception as e:  # noqa
                logger.warn("[MEI/screen] 摘{}的绑定失败: {}".format(self.LABEL, error_text(e)))


class PlainScreen(ScreenNode):
    """
    不建 MEI 主节点的压栈界面（自定义配方管理器，manager/screen.py）：生命周期和 MainScreen 一样 —— Create 只记一笔、第一次 Update 再建、
    出栈先拆、关界面下一帧在自己的 Update 里出栈；只是不建主节点，主节点的栈不动（下面那个界面的主节点照旧是当前的）。
    子类给 CLOSE_NAME、LABEL，覆写 OnBuilt（第一次 Update）、OnFrame（之后每帧）、OnTearDown（出栈前）、OnCloseKey
    """

    CLOSE_NAME = ""
    LABEL = "MEI 界面"

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.Bindings = None  # type: ScreenBinder or None
        self.Created = False  # type: bool  # 引擎调过 Create 了
        self.Built = False  # type: bool
        self.Failed = False  # type: bool  # 建不起来：不再试，关掉这个界面
        self.CloseRequested = False  # type: bool
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
            logger.error("[MEI/screen] {}每帧处理失败: {}".format(self.LABEL, error_text(e)))

    def __Update(self):
        if self.CloseRequested:
            self.CloseRequested = False
            self.__Pop()
            return
        if not self.Built:
            if not self.Failed:
                self.__Build()
            return
        self.OnFrame()

    def __Build(self):
        self.Bindings = ScreenBinder(self)
        if self.CLOSE_NAME:
            self.Bindings.Bind(self.OnCloseKey, ViewBinder.BF_ButtonClickUp, self.CLOSE_NAME)
        try:
            self.OnBuilt()
            self.Built = True
        except Exception as e:  # noqa
            self.Failed = True
            logger.error("[MEI/screen] {}建不起来，关掉这个界面: {}".format(self.LABEL, error_text(e)))
            self.CloseRequested = True  # 别让玩家困在一个空界面里

    def OnBuilt(self):
        """ 第一次 Update（子类覆写）"""

    def OnFrame(self):
        """ 之后每帧（子类覆写）"""

    def OnTearDown(self):
        """ 出栈前（子类覆写）"""

    def OnCloseKey(self, _args=None):
        """ ESC、背包键（画布上 global 映射到 CLOSE_NAME）"""
        self.RequestClose()

    def RequestClose(self):
        self.CloseRequested = True

    def __Pop(self):
        """ 出栈。只在自己就是栈顶时 —— 上面压着别的界面时 PopScreen 弹掉的是别人 """
        if clientApi.GetTopScreen() is not self:
            logger.warn("[MEI/screen] {}不在栈顶，这次不关".format(self.LABEL))
            return
        clientApi.PopScreen()

    def process_unbinding(self, *args, **kwargs):
        """ SDK 出栈时先按 dir(self) 摘一遍绑定、再调 Destroy：先拆 —— 挂的转发函数自己摘 """
        if getattr(self, "_ready", False):
            self.__TearDown()
        return ScreenNode.process_unbinding(self, *args, **kwargs)

    def Destroy(self):
        """ 出栈之后（SDK 不接这里的异常：抛出去界面就弹不掉，一律接住）"""
        if getattr(self, "_ready", False):
            self.__TearDown()

    def __TearDown(self):
        if self.Built:
            self.Built = False
            try:
                self.OnTearDown()
            except Exception as e:  # noqa
                logger.error("[MEI/screen] 拆{}失败: {}".format(self.LABEL, error_text(e)))
        bindings, self.Bindings = self.Bindings, None
        if bindings is not None:
            try:
                bindings.UnbindAll()
            except Exception as e:  # noqa
                logger.warn("[MEI/screen] 摘{}的绑定失败: {}".format(self.LABEL, error_text(e)))
