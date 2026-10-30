# coding=utf-8

# ----------------------------------------------------------------------
#  binder.py is part of MoreEnoughItems.
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
from collections import OrderedDict

from .utilities import IsBindFlag

_PROBE = "{}"
"""
转发函数进门先 format 一次它：py2 的 str.format 解析自动编号的 {} 时会查一次 PyErr_Occurred，
引擎在 C 层留下、没清掉的异常（CLAUDE.md 引擎结论 §48）就在这里被接出来、清掉 —— 不然它会抛在回调里随便哪个 format 上，
回调抛异常引擎就扔掉那条绑定（§15）
"""


def collection_capable(flag):  # type: (int) -> bool
    """ 这个 flag 能不能集合绑定；不认识的 flag 照调用方说的挂，由 SDK 决定 """
    try:
        return IsBindFlag(flag)
    except ValueError:
        return True


class ScreenBinder(object):
    """
    在不是 ScreenNode 的类里给界面挂绑定：转发函数挂到界面节点上（引擎按名字找回调），记着挂过什么，能逐条摘、整体摘
    """
    def __init__(self, screen_node):
        self.ScreenNode = screen_node
        self.__Bound = OrderedDict()  # type: OrderedDict  # id(转发函数) -> 转发函数，按挂的先后（整体摘时照这个顺序）

    def Bind(self, callback, flag, name, collection=None):  # type: (any, int, str, str) -> any
        """
        挂一条绑定，返回转发函数（Unbind 用它）。给了 collection 且 flag 能集合绑定（BF_Bind*）就是集合绑定；
        按钮、输入框、开关、滑条只能普通绑定（引擎结论 §9），给了 collection 也按普通绑定挂。
        转发函数进门先静默接住引擎留下、没清掉的异常（_PROBE，引擎结论 §48）
        """
        if collection is not None and not collection_capable(flag):
            collection = None

        probe = _PROBE

        def wrapper(*args):
            try:
                probe.format(0)
            except Exception:  # noqa  引擎留下的异常（不是回调抛的）：接住即清掉
                pass
            return callback(*args)
        wrapper.__name__ = "{}_binding_{}".format(getattr(callback, "__name__", "callback"), id(wrapper))
        wrapper.binding_flags = flag
        wrapper.binding_name = name
        if collection is not None:
            wrapper.collection_name = collection

        node = self.ScreenNode
        setattr(node, wrapper.__name__, wrapper)
        try:
            if collection is not None:
                node._process_collection(wrapper, node.screen_name)  # noqa
            else:
                node._process_default(wrapper, node.screen_name)  # noqa
        except Exception:
            delattr(node, wrapper.__name__)
            raise
        self.__Bound[id(wrapper)] = wrapper
        return wrapper

    def Unbind(self, wrapper):  # type: (any) -> bool
        """ 摘掉 Bind 挂上的一条；不是这里挂的（或已经摘过）返回 False """
        if self.__Bound.get(id(wrapper)) is not wrapper:
            return False
        del self.__Bound[id(wrapper)]
        node = self.ScreenNode
        try:
            if hasattr(wrapper, "collection_name"):
                node._process_collection_unregister(wrapper, node.screen_name)  # noqa
            else:
                node._process_default_unregister(wrapper, node.screen_name)  # noqa
        finally:
            if hasattr(node, wrapper.__name__):
                delattr(node, wrapper.__name__)
        return True

    def UnbindAll(self):
        """ 摘掉这里挂过的全部绑定，按挂的先后 """
        for wrapper in list(self.__Bound.values()):
            self.Unbind(wrapper)

    def Count(self):  # type: () -> int
        return len(self.__Bound)
