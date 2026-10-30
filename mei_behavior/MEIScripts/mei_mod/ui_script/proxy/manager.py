# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
#  manager.py is part of MoreEnoughItems.
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
from mod_log import logger as logger

from MEIScripts.utils.text import error_text

CUSTOM_PROXY_SCRIPT = "MEIScripts.mei_mod.ui_script.proxy.custom_ui.script.CustomProxyScript"
""" 挂 MEI 的界面统一用这一个代理类（ctx.UI.Screens.Register 登记的那些）"""


class __ProxyManager(object):
    """ 用于管理所有UI代理 """
    def __init__(self):
        self.CustomProxy = {}  # type: dict
        self.ModUIProxy = []  # type: list

        self.CurrentScreenDef = ""  # type: str
        """
        当前压在栈顶的原版屏幕 screenDef，由 PushScreenEvent 更新。

        快捷合成靠它判断"现在开着的是不是工作台" —— 那是**唯一**能知道
        玩家正对着哪个容器的途径(GetOpenContainerItem 只在特定事件里有效，
        PushScreenEvent 又只给 screenDef 不给坐标，见 quick_craft.md §5.3)。
        """

    def RegisterCustomUIScreen(self, screen_def, params):  # type: (str, dict) -> bool
        """
        让这个界面挂上 MEI（代理 CustomProxyScript）并记下它的代理参数。扩展装配时调（原版那 23 个由原版扩展登记，
        extensions/vanilla/screens.py），SDK 退出存档时把代理表清了，所以每次进存档都要重新登记。
        别的模组 RegisterUI + PushScreen 开的界面一样挂得上：SDK 压栈时按全名取界面节点（uiManager.get_pushed_screen）
        """
        if not self.RegisterProxyScript(screen_def, CUSTOM_PROXY_SCRIPT):
            return False
        self.CustomProxy[screen_def] = params
        return True

    def UnregisterCustomUIScreen(self, screen_def):  # type: (str) -> bool
        """ 撤掉 RegisterCustomUIScreen（扩展卸载时）；没登记过返回 False。SDK 那边退出存档时已经清过的话，摘不到也不算错 """
        if screen_def not in self.CustomProxy:
            return False
        del self.CustomProxy[screen_def]
        try:
            clientApi.GetNativeScreenManagerCls().instance().UnRegisterScreenProxy(screen_def, CUSTOM_PROXY_SCRIPT)
        except Exception:  # noqa  已经没了（OnQuitLevel 清过）：SDK 用 set.remove，找不到会抛
            pass
        return True

    def IsCustomUIScreen(self, screen_def):  # type: (str) -> bool
        """ 这个界面是不是登记过挂 MEI 的（支持的界面）"""
        return screen_def in self.CustomProxy

    def RegisterProxyScript(self, screen_def, script_path):  # type: (str, str) -> bool
        """ 给原生屏幕挂一个指定的代理类；SDK 拒绝（类找不到、不是代理类、这一局已经挂过）时返回 False """
        try:
            registered = clientApi.GetNativeScreenManagerCls().instance().RegisterScreenProxy(screen_def, script_path)
        except Exception as e:
            logger.error("Failed To Register Screen Proxy: {}, error: {}".format(screen_def, error_text(e)))
            return False
        if registered is False:
            logger.warn("[MEI/proxy] SDK 没接受 {} 的代理 {}（类找不到、不是代理类，或这一局已经挂过）".format(
                screen_def, script_path))
            return False
        return True

    def SetCurrentScreen(self, screen_def):  # type: (str) -> None
        """ 记下当前屏幕。**只记不判** —— 谁需要谁自己解释这个字符串 """
        self.CurrentScreenDef = screen_def or ""

    def GetCurrentScreen(self):  # type: () -> str
        return self.CurrentScreenDef

    def GetCustomUIParams(self, screen_def):  # type: (str) -> dict
        """ 获取对应原生UI的配置参数 """
        return self.CustomProxy.get(screen_def, {})

ProxyManager = __ProxyManager()
