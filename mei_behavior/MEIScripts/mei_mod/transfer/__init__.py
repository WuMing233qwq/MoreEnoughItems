# coding=utf-8

# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
配方转移的实现层。契约在 common/classes/base.py，注册面在 registry/transfer.py。

**门面刻意只导出纯逻辑与装配入口** —— targets/executor 顶层拉服务端引擎，
只想算匹配的人(客户端预检)不该被拖起服务端 api(engineering.md 的包门面急加载那条债)。
"""
from .matcher import (
    can_fulfill, copy_supply, index_supply, max_multiplier, max_stack_of, plan_entries,
)

__all__ = ["can_fulfill", "copy_supply", "index_supply", "max_multiplier",
           "max_stack_of", "plan_entries"]


def RegisterBuiltinSources():  # type: () -> int
    """ 装上内置来源。两端各调一次，客户端用于预检、服务端用于执行 """
    # 惰性 import: 放这里是为了让"注册"这个动作有明确的时机而不是 import 副作用
    from MEIScripts.registry.transfer import TransferRegistry
    from .inventory import InventorySource, SOURCE_ID

    # **幂等**: 客户端每次重进世界都会走一遍装配点, 不判就每次报一条"Id 已被占用"
    if TransferRegistry.Get(SOURCE_ID) is not None:
        return 0
    return 1 if TransferRegistry.RegisterSource(InventorySource()) else 0
