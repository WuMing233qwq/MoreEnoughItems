# coding=utf-8

# ----------------------------------------------------------------------
#  utils.py is part of MoreEnoughItems.
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
通用件：纯函数与容器，零引擎依赖（localize 用到时才 import 引擎接口，离线也能 import 这个门面）。
"""
from MEIScripts.utils.budget import BudgetQueue
from MEIScripts.utils.history import LRUCache, LRUHistory
from MEIScripts.utils.lang import localize
from MEIScripts.utils.log import logger
from MEIScripts.utils.page import Page
from MEIScripts.utils.sequence import dedupe, recipe_id
from MEIScripts.utils.stablehash import stable_digest, stable_text
from MEIScripts.utils.tag import TagParser
from MEIScripts.utils.text import error_text, native_str, to_native

__all__ = [
    "BudgetQueue", "LRUCache", "LRUHistory", "Page", "TagParser", "dedupe", "error_text",
    "localize", "logger", "native_str", "recipe_id", "stable_digest", "stable_text", "to_native",
]
""" logger 也导出: 模块级代码拿不到 ctx.Log(它只存在于生命周期方法里)；error_text 是 except 里拼日志用的（纯新增）"""


class UtilsFacade(object):
    """ ctx.Utils """

    __slots__ = tuple(__all__)

    def __init__(self):
        for name in __all__:
            setattr(self, name, globals()[name])
