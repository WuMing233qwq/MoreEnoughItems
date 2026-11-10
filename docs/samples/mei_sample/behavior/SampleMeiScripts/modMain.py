# coding=utf-8

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
"""
样例 addon 的入口（网易 ModSDK 的写法）：客户端注册一个系统，MEI 的接入在那个系统里做。
"""
from mod.common.mod import Mod


@Mod.Binding(name="SampleMeiScripts", version="1.0.0")
class SampleMeiScripts(object):

    @Mod.InitClient()
    def ClientInit(self):
        import mod.client.extraClientApi as clientApi
        clientApi.RegisterSystem("SampleMei", "SampleClientSystem", "SampleMeiScripts.client_system.SampleClientSystem")

    @Mod.DestroyClient()
    def ClientDestroy(self):
        pass
