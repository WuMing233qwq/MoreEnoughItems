# coding=utf-8

# ----------------------------------------------------------------------
#  hosts.py is part of MoreEnoughItems.
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
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst
from MEIScripts.constants.ui import FloatConst, TreeConst
from MEIScripts.mei_mod.state.settings import IsFloatCompat, IsFloatOnHud
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.floating.state import KIND_COMPAT, KIND_HUD
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.mei_mod.ui_script.settings import names as settings_names
from MEIScripts.utils.text import error_text

INJECTED_PARAMS = {"ContentPaths": []}
""" 注入的界面不知道哪块是原版内容：不登记避让目标（一律以悬浮窗起步，展开时铺满）。根面板用主节点缺省的原版根（HUD 也是它）"""


def host_kind(screen_def):  # type: (str) -> str or None
    """
    这个界面要不要由这里注入 MEI：支持的界面有自己的代理（不归这里）、MEI 的设置页、MEI 自己的界面（mei_main 命名空间，
    floating/screen.py）与配方树（MeiRecipeTree 命名空间，recipe_tree/screen.py）不注入；HUD 看「在游戏界面展示悬浮窗」；
    其余的看「启用悬浮窗强制兼容」，加载 / 进度、提示条、调试、主菜单这几类不注入（FloatConst.SkipNamespaces）。不注入给 None
    """
    if not screen_def or ProxyManager.IsCustomUIScreen(screen_def) or screen_def == settings_names.SCREEN_DEF:
        return None
    if screen_def.split(".", 1)[0] in (NameConst.MainUiNameSpace, TreeConst.UiNameSpace):
        return None
    if screen_def == FloatConst.HudScreen:
        return KIND_HUD if IsFloatOnHud() else None
    if screen_def.split(".", 1)[0] in FloatConst.SkipNamespaces:
        return None
    return KIND_COMPAT if IsFloatCompat() else None


def pushed_node(screen_def):  # type: (str) -> any
    """ 刚压上来的那个界面的节点：栈顶，且名字对得上（对不上就是栈顶不是它，不注入）"""
    try:
        node = clientApi.GetTopUINode()
        name = node.GetScreenName() if node is not None else None
    except Exception as e:  # noqa
        logger.warn("[MEI/float] 取不到栈顶界面: {}".format(error_text(e)))
        return None
    return node if name == screen_def else None


class InjectedProxy(object):
    """
    注入的界面没有 MEI 的代理：给主节点一个带 ScreenNode 的壳（主节点只认这一个属性）
    """
    def __init__(self, screen_node):
        self.ScreenNode = screen_node


class __FloatHosts(object):  # noqa
    """
    往 HUD、未支持 MEI 的界面里注入 MEI（以悬浮窗起步）。**只在界面压栈时注入**，照 NetEase 自己往 HUD 加控件的写法：
    压栈事件里当场取栈顶节点、核对名字、建在原版界面的根面板下（已经有了就不再建，根面板没有就不注入、这一局不再试）。
    每个界面一份，跟着界面活：别的界面压上来时收起、藏好（Cover），它重新露出来时显回（Uncover），它出栈时放掉 ——
    HUD 那份从进存档一直活到退出存档，不反复拆了重建（docs/architecture/floating.md §6）
    """
    def __init__(self):
        self.Hosts = []  # type: list  # [(screenDef, 主节点)]，底 → 顶
        self.Failed = set()  # type: set  # 注入失败过的界面（没有原版根面板这类），这一局不再试

    def OnPush(self, screen_def):
        """ 有界面压上来：已经注入的（它自己除外）都被盖住了；这个界面要注入就当场注入 """
        self.CoverAll(except_def=screen_def)
        kind = host_kind(screen_def)
        if kind is None or self.Find(screen_def) is not None or screen_def in self.Failed:
            return
        node = pushed_node(screen_def)
        if node is None:
            self.__Fail(screen_def, "栈顶不是它，取不到它的界面节点")
            return
        self.Inject(node, screen_def, kind)

    def OnPop(self, screen_def):
        """ 有界面要弹出：注入在它上面的那份跟着它一起没 """
        for index in range(len(self.Hosts) - 1, -1, -1):
            if self.Hosts[index][0] == screen_def:
                _, main = self.Hosts.pop(index)
                self.Release(main, screen_def)
                return

    def OnPopAfter(self, screen_def):
        """ 弹出之后露出来的栈顶是注入过的界面（比如回到 HUD）：显回来；设置关掉了就放掉它 """
        main = self.Find(screen_def)
        if main is None:
            return
        if host_kind(screen_def) is None:
            self.Remove(screen_def)
            return
        try:
            main.Uncover()
        except Exception as e:  # noqa
            logger.error("[MEI/float] {} 显回悬浮窗失败: {}".format(screen_def, error_text(e)))

    def Tick(self):
        """ 客户端主系统每帧调：推当前那份注入的主节点（它没有代理来调 OnTick）；被盖着的不推 """
        main = context.GetMainNode()
        if main is None or getattr(main, "Covered", False) or not self.Owns(main):
            return
        try:
            main.OnTick()
        except Exception as e:  # noqa
            logger.error("[MEI/float] 注入的界面每帧处理失败: {}".format(error_text(e)))

    def Reset(self):
        """ 退出世界：全部放掉 """
        hosts, self.Hosts = self.Hosts, []
        for screen_def, main in reversed(hosts):
            self.Release(main, screen_def)
        self.Failed = set()

    # 内部
    # ==================================================================================================================
    def Find(self, screen_def):  # type: (str) -> any
        for name, main in self.Hosts:
            if name == screen_def:
                return main
        return None

    def Owns(self, main):  # type: (any) -> bool
        return any(owned is main for _, owned in self.Hosts)

    def CoverAll(self, except_def=None):
        for screen_def, main in self.Hosts:
            if screen_def == except_def or getattr(main, "Covered", False):
                continue
            try:
                main.Cover()
            except Exception as e:  # noqa
                logger.warn("[MEI/float] 收起 {} 上的悬浮窗失败: {}".format(screen_def, error_text(e)))

    def Inject(self, node, screen_def, kind):
        from MEIScripts.mei_mod.ui_script.mei_ui.core.node import UIMainNode  # 主节点拉起整个界面栈，用到才 import
        main = UIMainNode(InjectedProxy(node), kind=kind, params=dict(INJECTED_PARAMS))
        try:
            main.OnCreate()
        except Exception as e:  # noqa
            self.__Fail(screen_def, error_text(e))
            try:
                main.OnDestroy()
            except Exception:  # noqa
                pass
            return
        self.Hosts.append((screen_def, main))

    def Release(self, main, screen_def):
        """ 界面出栈 / 退出世界：拆主节点（和支持的界面关界面时一样）"""
        try:
            main.OnDestroy()
        except Exception as e:  # noqa
            logger.warn("[MEI/float] 拆 {} 上注入的 MEI 失败: {}".format(screen_def, error_text(e)))

    def Remove(self, screen_def):
        """ 界面还在、设置关掉了：拆主节点，覆盖层藏起来（界面还活着，控件能碰）"""
        main = self.Find(screen_def)
        if main is None:
            return
        self.Hosts = [(name, owned) for name, owned in self.Hosts if owned is not main]
        root = None
        try:
            root = main.GetMEIRootControl()
        except Exception:  # noqa
            root = None
        self.Release(main, screen_def)
        if root is not None:
            try:
                root.SetVisible(False)
            except Exception:  # noqa
                pass

    def __Fail(self, screen_def, why):
        self.Failed.add(screen_def)
        logger.warn("[MEI/float] 在 {} 上注入 MEI 失败（这一局不再试）: {}".format(screen_def, why))


FloatHosts = __FloatHosts()
