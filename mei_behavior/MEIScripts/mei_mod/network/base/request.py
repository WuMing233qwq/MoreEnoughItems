# coding=utf-8

# ----------------------------------------------------------------------
#  request.py is part of MoreEnoughItems.
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
请求/回执的数据形状与待响应表。纯逻辑，零引擎依赖 —— 收发由 channel 负责。
"""
from MEIScripts.utils.log import logger

KEY_ID = "rid"
""" 请求 id 在载荷里的键名。短是因为它每条消息都带 """

KEY_NAME = "name"
""" 请求名，形如 "yourmod:something" """

KEY_BODY = "body"
""" 业务载荷。**轮子不看它一眼** """

KEY_OK = "ok"
""" 回执：处理器有没有正常跑完 """

KEY_ERROR = "err"
""" 回执：失败原因，给玩家看的话由上层翻译 """

ERR_NO_HANDLER = "no_handler"
""" 对面没有注册这个请求名的处理器 """

ERR_RAISED = "raised"
""" 处理器抛异常了 """

ERR_TIMEOUT = "timeout"
""" 超时。**注意它不是"失败"** —— 请求可能已经执行了, 只是回执没回来 """


class Pending(object):
    """ 一条已发出、等回执的请求 """

    __slots__ = ("Id", "Name", "OnReply", "Deadline")

    def __init__(self, request_id, name, on_reply, deadline):
        # type: (int, str, any, float) -> None
        self.Id = request_id
        self.Name = name
        self.OnReply = on_reply    # type: any  # fn(response_dict) -> None
        self.Deadline = deadline   # type: float  # 绝对时刻, 由调用方按自己的时钟给


class PendingTable(object):
    """
    待响应表。**超时是常态不是异常** —— 玩家关界面、切世界、服务端崩，
    回执都可能永远不来；不清就是内存泄漏。
    """

    def __init__(self):
        self._next_id = 1     # type: int
        self._pending = {}    # type: dict  # request_id -> Pending

    def Count(self):  # type: () -> int
        return len(self._pending)

    def Put(self, name, on_reply, deadline):  # type: (str, any, float) -> int
        """ 登记一条待响应，返回分配的请求 id """
        request_id = self._next_id
        self._next_id += 1
        self._pending[request_id] = Pending(request_id, name, on_reply, deadline)
        return request_id

    def Take(self, request_id):  # type: (int) -> Pending or None
        """ 取出并移除；回执只认一次，重复投递直接落空 """
        return self._pending.pop(request_id, None)

    def Expire(self, now):  # type: (float) -> list
        """ 摘出所有已超时的条目并移除，调用方负责通知它们 """
        dead = [p for p in self._pending.values() if p.Deadline <= now]
        for pending in dead:
            self._pending.pop(pending.Id, None)
        return dead

    def Clear(self):
        """ 全清。重进世界/界面销毁时调，剩下的回调一律不再触发 """
        if self._pending:
            logger.info("[MEI/net] 丢弃 {} 条未回执的请求".format(len(self._pending)))
        self._pending = {}


def make_request(request_id, name, body):  # type: (int, str, any) -> dict
    return {KEY_ID: request_id, KEY_NAME: name, KEY_BODY: body}


def make_response(request_id, name, ok, body=None, error=""):
    # type: (int, str, bool, any, str) -> dict
    return {KEY_ID: request_id, KEY_NAME: name, KEY_OK: bool(ok),
            KEY_BODY: body, KEY_ERROR: error}


def make_timeout(pending):  # type: (Pending) -> dict
    return make_response(pending.Id, pending.Name, False, None, ERR_TIMEOUT)
