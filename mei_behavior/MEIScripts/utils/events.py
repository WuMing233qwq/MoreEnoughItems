# coding=utf-8

# ----------------------------------------------------------------------
#  events.py is part of MoreEnoughItems.
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


class EventListener(object):
    """
    在一个 System 上挂事件：回调可以是任意可调用对象；记着自己挂过什么，UnlistenAll 只摘自己挂的
    """
    def __init__(self, system, side="client"):  # type: (any, str) -> None
        if side not in ("client", "server"):
            raise ValueError("side must be 'client' or 'server', got {!r}".format(side))
        self.System = system
        self.Side = side
        self.__Hooks = {}  # type: dict  # (命名空间, 系统名, 事件, 回调) -> (转发函数, 优先级)

    def Listen(self, event, callback, namespace=None, system_name=None, priority=0):
        # type: (str, any, str, str, int) -> bool
        """ 挂一个事件，namespace / system_name 缺省是引擎事件；同一个回调重复挂同一个事件返回 False """
        key = self.__Key(event, callback, namespace, system_name)
        if key in self.__Hooks:
            return False
        hook = self.__Hook(callback)
        self.System.ListenForEvent(key[0], key[1], event, self, hook, priority)
        self.__Hooks[key] = (hook, priority)
        return True

    def Unlisten(self, event, callback, namespace=None, system_name=None):  # type: (str, any, str, str) -> bool
        """ 摘一个事件；没挂过返回 False """
        key = self.__Key(event, callback, namespace, system_name)
        found = self.__Hooks.pop(key, None)
        if found is None:
            return False
        hook, priority = found
        try:
            self.System.UnListenForEvent(key[0], key[1], event, self, hook, priority)
        finally:
            self.__dict__.pop(hook.__name__, None)
        return True

    def UnlistenAll(self):
        """ 摘掉自己挂过的全部事件；别人挂在同一个 System 上的不动（System.UnListenAllEvents 会连别人的一起摘）"""
        for namespace, system_name, event, callback in list(self.__Hooks):
            self.Unlisten(event, callback, namespace, system_name)

    def Count(self):  # type: () -> int
        return len(self.__Hooks)

    def __Key(self, event, callback, namespace, system_name):  # type: (str, any, str, str) -> tuple
        if namespace is None or system_name is None:
            api = self.__Api()
            namespace = api.GetEngineNamespace() if namespace is None else namespace
            system_name = api.GetEngineSystemName() if system_name is None else system_name
        return namespace, system_name, event, callback

    def __Api(self):
        # 按端懒 import：服务端可达的 import 链里不能有 mod.client（engineering.md §2）
        if self.Side == "client":
            import mod.client.extraClientApi as api
        else:
            import mod.server.extraServerApi as api
        return api

    def __Hook(self, callback):
        # SDK 投递事件时按函数名在 instance 上取回调，所以转发函数起个唯一的名字、挂在自己身上
        def hook(*args):
            return callback(*args)
        hook.__name__ = "on_event_{}".format(id(hook))
        setattr(self, hook.__name__, hook)
        return hook
