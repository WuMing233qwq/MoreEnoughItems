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

# 注意: 这里**不要**写 `import utilities`.
# utilities.py 顶层就要客户端引擎 (`ViewBinder = clientApi.GetViewBinderCls()`),
# 一旦在包门面里急加载, 任何 import 本包子模块的人(例如 types/item.py 只想要
# hashable)都会被迫拉起客户端引擎 —— 这曾使整个 types 包在服务端/离线环境
# 无法 import, 违反 engineering.md §2「数据模型可独立 compileall、
# 可被服务端/测试环境加载」. 消费方写 `from MEIScripts.utils import utilities`
# 时 Python 会自然加载该子模块, 不需要在此预先 import.
from .budget import BudgetQueue
from .history import LRUCache, LRUHistory
from .page import BuildPage
from .hashable import HashableMaker
from .codec import Codec
from .patcher import LogPatcher
from .polygon import RectPolygon
from .sequence import dedupe, recipe_id
from .stablehash import stable_digest, stable_hash64
from .tag import TagParser
from .text import native_str, to_native

__all__ = [
    "utilities",
    "BudgetQueue",
    "BuildPage",
    "HashableMaker",
    "Codec",
    "LogPatcher",
    "RectPolygon",
    "LRUCache",
    "LRUHistory",
    "TagParser",
    "dedupe",
    "native_str",
    "recipe_id",
    "stable_digest",
    "stable_hash64",
    "to_native",
]