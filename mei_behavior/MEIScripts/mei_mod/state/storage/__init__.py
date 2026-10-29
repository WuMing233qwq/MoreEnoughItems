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
# 这里**只导出纯逻辑**. backend.py 顶层 import 客户端引擎, 一旦在包门面里
# 急加载, 任何想用纯 Store 的人(含离线探针)都会被迫拉起客户端 ——
# 与 utils/__init__.py 曾经的破口同型(tasks_s1.md §6.4).
# 需要后端的消费方显式写: from ...storage.backend import ConfigBackend
from .store import Store

__all__ = [
    "Store",
]
