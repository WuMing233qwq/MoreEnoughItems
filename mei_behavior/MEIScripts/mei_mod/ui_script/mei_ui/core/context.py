# coding=utf-8

# ----------------------------------------------------------------------
#  context.py is part of MoreEnoughItems.
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
# 当前的主节点（UIMainNode）。同一时间可能有几份 MEI 活着：注入在 HUD 上的那份一直在，上面再开一个界面（支持的界面的代理、
# 强制兼容注入的）就压在它上面，关掉后回到它 —— 所以是个栈，最上面的是当前的（docs/architecture/floating.md §6）

_MAIN_NODES = []  # type: list  # 底 → 顶
_SCOPED = []  # type: list  # 临时顶上的（Using）：只在一段代码里算当前的，不进栈（配方树菜单里的配方预览，recipe_tree/controls/preview.py）


def SetMainNode(node):
    # type: (object) -> None
    """ 这个主节点成为当前的：已经在栈里的先挪出来，再压到最上面 """
    _Remove(node)
    _MAIN_NODES.append(node)


def GetMainNode():
    # type: () -> any
    if _SCOPED:
        return _SCOPED[-1]
    return _MAIN_NODES[-1] if _MAIN_NODES else None


class Using(object):
    """
    with Using(node): ... —— 这一段代码里 GetMainNode() 给 node，出来就还原（抛异常也还原）；不动主节点的栈。
    给「不是主节点的界面」借用配方页脚本与 ItemPanel 用：它们构造时问 GetMainNode() 拿界面节点、控件路径
    （配方树是 PushScreen 的另一块界面，菜单里的配方预览在自己的绑定回调、建脚本、节拍里套它）
    """

    def __init__(self, node):
        self.Node = node

    def __enter__(self):
        _SCOPED.append(self.Node)
        return self.Node

    def __exit__(self, *_exc):
        for index in range(len(_SCOPED) - 1, -1, -1):
            if _SCOPED[index] is self.Node:
                del _SCOPED[index]
                break
        return False


def ClearMainNode(node=None):
    # type: (object) -> None
    """ 去掉这个主节点（不在最上面也去掉，下面那个就成了当前的）；不给就全清 """
    if node is None:
        del _MAIN_NODES[:]
    else:
        _Remove(node)


def _Remove(node):
    # type: (object) -> None
    # 按身份比，不用 ==：主节点没定义相等，以后定义了也不该影响这里
    for index in range(len(_MAIN_NODES) - 1, -1, -1):
        if _MAIN_NODES[index] is node:
            del _MAIN_NODES[index]

