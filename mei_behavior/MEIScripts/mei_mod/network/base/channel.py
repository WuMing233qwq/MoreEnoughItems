# coding=utf-8

# ----------------------------------------------------------------------
#  channel.py is part of MoreEnoughItems.
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
收发与路由。一端一个 Channel，由该端的 MainSys 在初始化时装好。

**本模块不认识任何业务** —— 它只做四件事：发请求、收请求转给处理器、
发回执、收回执唤醒等待者。业务名是调用方给的字符串。

引擎侧只用两个事件名（`REQUEST_EVENT` / `RESPONSE_EVENT`），
所有请求复用它们，靠载荷里的 `name` 分流 —— 不为每个业务注册一个引擎事件，
那会让"加一个请求"变成"改两端的事件监听表"。
"""
import time

from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from . import codec
from . import request as req
from .handler import Collect, HandlerContext

REQUEST_EVENT = "MeiNetRequest"
""" 引擎事件名：请求。**所有**请求共用它，靠载荷里的 name 分流 """

RESPONSE_EVENT = "MeiNetResponse"
""" 引擎事件名：回执 """

DEFAULT_TIMEOUT = 5.0
""" 秒。够一次往返有余，又不至于让玩家对着一个没反应的按钮等太久 """


class Channel(object):
    """
    一端的收发口。构造期不碰引擎 —— 装配由 Attach 完成。

    两端用法对称，差别只在 `_send_*` 注入的发送函数：
      客户端  send_request(payload)              -> NotifyToServer
      服务端  send_response(player_id, payload)  -> NotifyToClient
    """

    def __init__(self, side):  # type: (str) -> None
        if side not in ("client", "server"):
            raise ValueError("side must be 'client' or 'server'")
        self.Side = side          # type: str
        self._handlers = {}       # type: dict  # 请求名 -> fn(ctx, body)
        self._pending = req.PendingTable()
        self._send = None         # type: any   # fn(payload, player_id) -> None
        self._attached = False    # type: bool

    # 装配
# ======================================================================================================================
    def Attach(self, send):  # type: (any) -> None
        """ 注入发送函数。fn(payload, player_id) —— 客户端侧忽略 player_id """
        self._send = send
        self._attached = True

    def Detach(self):
        """ 卸载。未回执的请求一律丢弃，它们的回调不会再被调用 """
        self._pending.Clear()
        self._send = None
        self._attached = False

    def Register(self, name, func):  # type: (str, any) -> bool
        """ 登记一个处理器。重名拒绝，先到先得 """
        if name in self._handlers:
            logger.error("[MEI/net] 重复的处理器名: {}".format(name))
            return False
        self._handlers[name] = func
        return True

    def RegisterAll(self, owner):  # type: (any) -> int
        """ 扫 owner 上的 @Handler 声明并全部登记，返回登记数 """
        return len([n for n, f in Collect(owner).items() if self.Register(n, f)])

    def UnRegister(self, name):  # type: (str) -> bool
        return self._handlers.pop(name, None) is not None

    # 发
# ======================================================================================================================
    def Request(self, name, body=None, on_reply=None, timeout=DEFAULT_TIMEOUT, player_id=None):
        # type: (str, any, any, float, str) -> int
        """
        发一条请求，返回请求 id。on_reply(response) 在回执到达或超时时调用一次。

        **超时也会调 on_reply**，`response[KEY_OK]` 为假、`KEY_ERROR` 是 "timeout"。
        调用方必须处理这种情况 —— 忽略它就等于"按钮点了没反应"。
        """
        if not self._attached:
            logger.error("[MEI/net] 未装配就发请求: {}".format(name))
            return 0
        request_id = self._pending.Put(name, on_reply, time.time() + timeout)
        self._send(codec.sanitize(req.make_request(request_id, name, body)), player_id)
        return request_id

    def Tick(self):
        """ 清超时。挂在双端的 Update 上；表为空时是一次 len() 判空，不构成常驻开销 """
        if not self._pending.Count():
            return
        for pending in self._pending.Expire(time.time()):
            logger.warn("[MEI/net] 请求超时: {} (id={})".format(pending.Name, pending.Id))
            self.__Invoke(pending, req.make_timeout(pending))

    # 收
# ======================================================================================================================
    def OnRequest(self, args):
        """ 引擎事件回调：收到对面的请求。挂在 REQUEST_EVENT 上 """
        payload = codec.restore(args or {})
        request_id = payload.get(req.KEY_ID, 0)
        name = payload.get(req.KEY_NAME, "")
        player_id = payload.get("__from", "")

        func = self._handlers.get(name)
        if func is None:
            logger.error("[MEI/net] 没有处理器: {}".format(name))
            self.__Reply(req.make_response(
                request_id, name, False, None, req.ERR_NO_HANDLER), player_id)
            return

        context = HandlerContext(name, request_id, player_id, self)
        try:
            body = func(context, payload.get(req.KEY_BODY))
        except Exception as e:  # noqa  处理器炸了要回执, 否则对面只能等超时
            logger.error("[MEI/net] {} 的处理器抛异常: {}".format(name, error_text(e)))
            self.__Reply(req.make_response(
                request_id, name, False, None, req.ERR_RAISED), player_id)
            return
        self.__Reply(req.make_response(request_id, name, True, body), player_id)

    def OnResponse(self, args):
        """ 引擎事件回调：收到回执。挂在 RESPONSE_EVENT 上 """
        payload = codec.restore(args or {})
        pending = self._pending.Take(payload.get(req.KEY_ID, 0))
        if pending is None:
            # 超时后又回来了, 或者重复投递. 不是错误, 但值得知道
            logger.info("[MEI/net] 回执没有对应的等待者: {}".format(
                payload.get(req.KEY_NAME)))
            return
        self.__Invoke(pending, payload)

    # 内部
# ======================================================================================================================
    def __Reply(self, payload, player_id):
        if not self._attached:
            return
        self._send(codec.sanitize(payload), player_id)

    @staticmethod
    def __Invoke(pending, response):
        if pending.OnReply is None:
            return
        try:
            pending.OnReply(response)
        except Exception as e:  # noqa  业务回调炸了不能把整条通道带走
            logger.error("[MEI/net] {} 的回执回调抛异常: {}".format(pending.Name, error_text(e)))
