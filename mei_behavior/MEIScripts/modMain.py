# -*- coding: utf-8 -*-

README_PLZ =\
"""
------------------------------------------------------------------------
| 本模组已开源于Github (https://github.com/WuMing233qwq/MoreEnoughItems) |
| 并且遵循 GNU Lesser General Public License v3.0 许可协议               |
| 如果你是解包获取此源代码内容的, 请在遵守许可的规范下使用分发, 感谢理解       |
| 若需额外的授权, 请在GitHub仓库页面的联系方式中通过社交软件联系我            |
------------------------------------------------------------------------
"""

# ----------------------------------------------------------------------
#  modMain.py is part of MoreEnoughItems.
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

from mod.common.mod import Mod

from MEIScripts.constants import mod_info
from MEIScripts.constants.codes import NameConst, PathConst

@Mod.Binding(name="MoreEnoughItemsScript", version=mod_info.Version)
class MoreEnoughItemsScript(object):

    def __init__(self):
        pass

    @Mod.InitServer()
    def ServerInit(self):
        # 两端的 API 都在各自的初始化里取：服务端可达的 import 链里不能有顶层 mod.client（engineering.md §2）
        import mod.server.extraServerApi as serverApi
        serverApi.RegisterSystem(NameConst.NameSpace, NameConst.ServerSysName, PathConst.ServerMainSysPath)

    @Mod.DestroyServer()
    def ServerDestroy(self):
        pass

    @Mod.InitClient()
    def ClientInit(self):
        import mod.client.extraClientApi as clientApi
        # 对外 API 组件必须在此注册: 第三方靠 CreateComponent 拿它, 早于任何扩展逻辑
        from MEIScripts.api.comps import RegisterAll
        RegisterAll()
        clientApi.RegisterSystem(NameConst.NameSpace, NameConst.ClientSysName, PathConst.ClientMainSysPath)

    @Mod.DestroyClient()
    def ClientDestroy(self):
        pass
