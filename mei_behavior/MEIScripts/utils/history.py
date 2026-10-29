# coding=utf-8
# ----------------------------------------------------------------------
#  history.py is part of MoreEnoughItems.
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
class _Node(object):
    __slots__ = ('key', 'prev', 'next')

    def __init__(self, key):
        self.key = key
        self.prev = None
        self.next = None


class _ValueNode(object):
    """ LRUCache 用. 与 _Node 分开是**刻意的** —— 不去动已在用的 LRUHistory """
    __slots__ = ('key', 'value', 'prev', 'next')

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache(object):
    """
    键值 LRU 缓存: O(1) 读写, 超容量淘汰**最久未使用**的一项.

    与同文件的 LRUHistory 的区别: 那个只记键(用于"最近浏览过什么"),
    这个存值(用于"这个键上次算出来的结果是什么").
    """

    def __init__(self, maxsize):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self.maxsize = maxsize
        self._dict = {}  # key -> _ValueNode
        self._head = _ValueNode(None, None)  # 哨兵头(最近端)
        self._tail = _ValueNode(None, None)  # 哨兵尾(最旧端)
        self._head.next = self._tail
        self._tail.prev = self._head

    @staticmethod
    def _unlink(node):
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = node.next = None

    def _link_head(self, node):
        first = self._head.next
        self._head.next = node
        node.prev = self._head
        node.next = first
        first.prev = node

    def get(self, key, default=None):
        """ 命中则把该项移到最近端并返回值; 未命中返回 default """
        node = self._dict.get(key)
        if node is None:
            return default
        self._unlink(node)
        self._link_head(node)
        return node.value

    def put(self, key, value):
        """ 写入/更新. 已存在则覆盖并移到最近端; 超容量则淘汰最旧的一项 """
        node = self._dict.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
            self._link_head(node)
            return

        node = _ValueNode(key, value)
        self._dict[key] = node
        self._link_head(node)

        if len(self._dict) > self.maxsize:
            oldest = self._tail.prev
            if oldest is not self._head:
                self._unlink(oldest)
                del self._dict[oldest.key]

    def pop(self, key, default=None):
        """ 移除一项并返回其值; 不存在返回 default """
        node = self._dict.pop(key, None)
        if node is None:
            return default
        self._unlink(node)
        return node.value

    def clear(self):
        self._dict = {}
        self._head.next = self._tail
        self._tail.prev = self._head

    def keys(self):
        """ 从最近到最旧 """
        out = []
        cur = self._head.next
        while cur is not self._tail:
            out.append(cur.key)
            cur = cur.next
        return out

    def __contains__(self, key):
        return key in self._dict

    def __len__(self):
        return len(self._dict)


class LRUHistory(object):
    """ 支持 O(1) 头插/移动、尾部删除、去重的历史记录容器 """

    def __init__(self, maxsize):
        self.maxsize = maxsize
        self._dict = {}  # key -> node
        self._head = None  # 虚拟头节点（哨兵）
        self._tail = None  # 虚拟尾节点（哨兵）
        self._init_sentinel()

    def _init_sentinel(self):
        """ 初始化哨兵节点，简化边界处理 """
        self._head = _Node(None)
        self._tail = _Node(None)
        self._head.next = self._tail
        self._tail.prev = self._head

    @staticmethod
    def _remove_node(node):
        """ 从链表中移除一个节点（O(1)） """
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node
        node.prev = node.next = None

    def _add_to_head(self, node):
        """将节点插入到头部（紧挨哨兵头之后）"""
        first = self._head.next
        self._head.next = node
        node.prev = self._head
        node.next = first
        first.prev = node

    def _pop_tail(self):
        """ 移除尾部节点（哨兵尾之前）并返回其 key """
        if self._tail.prev is self._head:
            return None  # 空链表
        tail_node = self._tail.prev
        self._remove_node(tail_node)
        return tail_node.key

    def add(self, key):
        """ 添加/移动元素到头部；如果超出容量则淘汰尾部元素 """
        # 1. 如果 key 已经存在，先删除旧节点
        if key in self._dict:
            node = self._dict[key]
            self._remove_node(node)
        else:
            node = _Node(key)

        # 2. 插入到头部
        self._add_to_head(node)
        self._dict[key] = node

        # 3. 超出容量则淘汰尾部
        if len(self._dict) > self.maxsize:
            removed_key = self._pop_tail()
            if removed_key is not None:
                del self._dict[removed_key]

    def peek(self):
        """ 看一眼最近加入的 key(头部), 不移除; 空时返回 None """
        if self._head.next is self._tail:
            return None
        return self._head.next.key

    def pop(self):
        """
        弹出并返回最近加入的 key(头部), 空时返回 None.

        有了它, LRUHistory 就能当**去重的栈**用: add 是"压栈且去重"
        (已存在的 key 是移动而非追加), pop 是"出栈"。
        配方页的返回栈正是这么用的 —— 见 state/cache.py 的 RecipeNav。

        > 注意: 空栈与"存了一个 None" 无法区分。调用方请先看 len()/peek(),
        > 或干脆别拿 None 当 key(本仓的 key 都是 tuple 或对象)。
        """
        if self._head.next is self._tail:
            return None
        node = self._head.next
        self._remove_node(node)
        del self._dict[node.key]
        return node.key

    def remove(self, key):
        """ 按键删除, 返回是否删掉了. 收藏取消要用它 —— pop 只能弹头部 """
        node = self._dict.pop(key, None)
        if node is None:
            return False
        self._remove_node(node)
        return True

    def clear(self):
        self._dict = {}
        self._init_sentinel()

    def __contains__(self, key):
        return key in self._dict

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        """按从最近到最远的顺序遍历"""
        cur = self._head.next
        while cur is not self._tail:
            yield cur.key
            cur = cur.next

    def to_list(self):
        """ 返回列表（头部为最近）"""
        return list(self)

    def __repr__(self):
        return "LRUHistory({})".format(self.to_list())
