# coding=utf-8

# ----------------------------------------------------------------------
#  handler.py is part of MoreEnoughItems.
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
请求处理器的声明与登记 —— 与 RecipeBinder / RecipeAction 同一个路子：
装饰器只把**声明**推到函数上，真正的接线由 Channel 统一做。

    @Handler("yourmod:something")
    def OnSomething(ctx, body):
        return {"filled": 7}

返回值即回执的 body；抛异常则回执标失败。**本模块不认识任何业务请求名** ——
名字是调用方给的字符串，轮子只做名字到函数的映射。
"""
from MEIScripts.utils.log import logger

_RULES_ATTR = "__mei_net_handler__"
""" 装饰器把请求名挂在函数上，Collect 再扫出来 """


class HandlerContext(object):
    """ 一次请求的环境。由 Channel 填好交给处理器 """

    __slots__ = ("Name", "RequestId", "PlayerId", "Channel")

    def __init__(self, name, request_id, player_id, channel):
        # type: (str, int, str, any) -> None
        self.Name = name              # type: str
        self.RequestId = request_id   # type: int
        self.PlayerId = player_id     # type: str  # 服务端侧是发起者; 客户端侧为空
        self.Channel = channel        # type: any


def Handler(name):  # type: (str) -> any
    """ 声明一个请求处理器。name 须带命名空间前缀，如 "yourmod:xxx" """
    if not name or ":" not in name:
        raise ValueError("handler name must be namespaced, got {!r}".format(name))

    def _decorator(func):
        func.__dict__[_RULES_ATTR] = name
        return func
    return _decorator


def Collect(owner):  # type: (any) -> dict
    """ 扫 owner 上的 @Handler 声明，返回 {请求名: 绑定方法} """
    # 绑到实例而不是类, 回调里能直接用 self —— 与 RecipeAction.Collect 同一个理由
    found = {}
    for attr in dir(type(owner)):
        if attr.startswith("__"):
            continue
        try:
            member = getattr(type(owner), attr)
        except Exception:  # noqa  property 之类取值可能抛
            continue
        func = getattr(member, "im_func", member)
        name = getattr(func, _RULES_ATTR, None)
        if not name:
            continue
        if name in found:
            logger.error("[MEI/net] 重复的处理器名: {}".format(name))
            continue
        found[name] = getattr(owner, attr)
    return found
