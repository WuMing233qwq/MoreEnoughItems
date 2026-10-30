# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
#  main_sys.py is part of MoreEnoughItems.
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

import mod.server.extraServerApi as serverApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst
from MEIScripts.mei_mod.network.base import Channel, REQUEST_EVENT, RESPONSE_EVENT
from MEIScripts.mei_mod.network.protocol.cheat import CheatService
from MEIScripts.mei_mod.network.protocol.transfer import TransferService
from MEIScripts.mei_mod.transfer import RegisterBuiltinSources
from MEIScripts.utils.events import EventListener

ServerSystem = serverApi.GetServerSystemCls()

class MainSys(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self.Events = EventListener(self, "server")
        self.Events.Listen("ClientLoadAddonsFinishServerEvent", self.onAddonsLoaded)
        self.ItemIds = []

        # 通讯. 服务端在这一端只做两件事: 开局发 id 表 + 应答请求
        self.Channel = Channel("server")
        self.Channel.Attach(self.__SendToPlayer)
        self.Channel.RegisterAll(TransferService())
        self.Channel.RegisterAll(CheatService(self))
        self.Events.Listen(REQUEST_EVENT, self.OnRequest, NameConst.NameSpace, NameConst.ClientSysName)
        RegisterBuiltinSources()

    def onAddonsLoaded(self, args):
        """ 同步物品 仅进行简单兼容 实际注册自定义配方等都在客户端 """
        comp = serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())
        player_id = args["playerId"]
        if not self.ItemIds:
            items = set(comp.GetLoadItems(False))
            hidden_items = set(comp.GetLoadItems(True)) - items
            self.ItemIds = [list(items), list(hidden_items)]

        self.NotifyToClient(player_id, "SyncLoadedItems", {"items": self.ItemIds})

    def OnRequest(self, args):
        """ 引擎事件回调，转交 Channel """
        self.Channel.OnRequest(args)

    def __SendToPlayer(self, payload, player_id):
        """ Channel 的发送口。回执按请求里带回来的发起者投递 """
        if not player_id:
            logger.error("[MEI/net] 回执缺 playerId, 丢弃")
            return
        self.NotifyToClient(player_id, RESPONSE_EVENT, payload)

    # OnScriptTickServer的回调函数，会在引擎tick的时候调用，1秒30帧（被调用30次）
    def OnTickServer(self):
        """
        Driven by event, One tick way
        """
        pass

    # 这个Update函数是基类的方法，同样会在引擎tick的时候被调用，1秒30帧（被调用30次）
    def Update(self):
        """
        Driven by system manager, Two tick way
        """
        # 清超时的待响应. 表为空时是一次判空, 不构成常驻开销
        self.Channel.Tick()

    def Destroy(self):
        self.Channel.Detach()
        self.Events.UnlistenAll()
