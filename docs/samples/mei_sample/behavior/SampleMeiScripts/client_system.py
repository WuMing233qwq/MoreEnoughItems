# coding=utf-8

# ----------------------------------------------------------------------
#  client_system.py is part of MoreEnoughItems.
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
接 MEI 的地方（唯一的接入点）。MEI 是**软依赖**：玩家没装 MEI 时 CreateComponent 拿不到东西，什么都不做。

- 什么时候接：UiInitFinished（每次进世界都会来）。MEI 自己排队：它还没就绪就等它就绪，已经就绪就当场装配（extensions.md §4.2）。
- 每次进世界都注册一遍没关系 —— 注册的是**同一个类**（mei_extension.build 缓存着）就是幂等的；
  每次造一个新类才会被当成「另一个扩展抢同一个 ID」拒掉。
- 版本：先问 GetApiVersion()，太旧就不接、留一行日志（MEI 自己也会按 MIN_API_VERSION 拒，那时日志在 MEI 那边）。
"""
import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()

MEI_NAMESPACE = "MoreEnoughItems"
MEI_COMPONENT = "MeiApi"
MIN_MEI_API = 2
""" 本样例用到的写法要求 MEI 的扩展 API v2（RegisterCategory / RegisterSource）"""


class SampleClientSystem(ClientSystem):
    def __init__(self, namespace, system_name):
        ClientSystem.__init__(self, namespace, system_name)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), "UiInitFinished",
                            self, self.OnUiInitFinished)

    def OnUiInitFinished(self, args):
        mei = clientApi.CreateComponent(clientApi.GetLocalPlayerId(), MEI_NAMESPACE, MEI_COMPONENT)
        if not mei:
            return  # 没装 MEI：当无事发生
        version = mei.GetApiVersion()
        if version < MIN_MEI_API:
            print "[SampleMei] MEI 的扩展 API 是 v{}，本样例要 v{}，请更新 MEI".format(version, MIN_MEI_API)
            return
        from SampleMeiScripts.mei_extension import build
        mei.RegisterExtension(build(mei.GetExtensionCls()))

    def Destroy(self):
        self.UnListenAllEvents()
