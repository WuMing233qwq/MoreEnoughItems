# coding=utf-8

# ----------------------------------------------------------------------
#  transfer.py is part of MoreEnoughItems.
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
物品来源的注册面与查询出口 —— 与 SourceRegistry / RecipeManager 同一个形制。

形制是刻意对齐的：**注册面只管登记，查询出口只管合并**。
配方那边是「Category 收 Source，RecipeManager 合并去重」；
这边是「Registry 收 ItemSource，Query 合并按优先级排序」。
两处的心智模型一样，读过一边就会用另一边。

本模块零引擎依赖：它只碰 ItemSource 契约与纯数据，真正的读写在
mei_mod/transfer/ 那层。故服务端可直接 import。
"""
from MEIScripts.common.classes.base import ItemSource
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text


class __TransferRegistry(object):  # noqa
    """ 物品来源的登记处，两端各一份（客户端用于预检，服务端用于执行） """

    def __init__(self):
        self._sources = {}   # type: dict  # Id -> ItemSource
        self._order = []     # type: list  # 注册序，用于同优先级时的稳定排序

    # 注册
# ======================================================================================================================
    def RegisterSource(self, source):  # type: (ItemSource) -> bool
        """ 登记一个来源，Id 重复则拒绝 """
        if not isinstance(source, ItemSource):
            logger.error("[MEI/transfer] 拒绝: {!r} 不是 ItemSource".format(source))
            return False
        source_id = getattr(source, "Id", "")
        if not source_id or ":" not in source_id:
            logger.error("[MEI/transfer] 拒绝: Id {!r} 必须带命名空间前缀".format(source_id))
            return False
        if source_id in self._sources:
            logger.error("[MEI/transfer] 拒绝 {}: 该 Id 已被占用".format(source_id))
            return False
        self._sources[source_id] = source
        self._order.append(source_id)
        return True

    def UnRegisterSource(self, source_id):  # type: (str) -> bool
        if source_id not in self._sources:
            return False
        del self._sources[source_id]
        self._order.remove(source_id)
        return True

    def Get(self, source_id):  # type: (str) -> ItemSource or None
        return self._sources.get(source_id)

    def ListSources(self):  # type: () -> list
        """ 按 Priority 升序、同优先级按注册序 —— **顺序必须稳定** """
        # 不稳定就意味着"同一次点击两次挑出不同的材料", 玩家会看到材料乱跳
        return sorted(
            (self._sources[i] for i in self._order),
            key=lambda s: (getattr(s, "Priority", 0), self._order.index(s.Id)))

    def Reset(self):
        self._sources = {}
        self._order = []

    # 查询出口
# ======================================================================================================================
    def Collect(self, ctx):  # type: (any) -> list
        """
        问遍所有来源，合并成 [(ItemStack, source_id, handle), ...]

        单个来源抛异常只跳过它 —— 一个坏的存储模组不该让整个快捷合成失效。
        """
        merged = []
        for source in self.ListSources():
            try:
                entries = source.Collect(ctx)
            except Exception as e:  # noqa
                logger.error("[MEI/transfer] {} 的 Collect 抛异常: {}".format(source.Id, error_text(e)))
                continue
            for item in entries or ():
                if not item:
                    continue
                stack, handle = item
                merged.append((stack, source.Id, handle))
        return merged


TransferRegistry = __TransferRegistry()
