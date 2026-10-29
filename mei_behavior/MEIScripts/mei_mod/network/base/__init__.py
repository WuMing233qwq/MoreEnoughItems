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
通讯基础设施 —— **不认识任何业务**。加请求不需要动这里任何一行。
"""
from .channel import Channel, DEFAULT_TIMEOUT, REQUEST_EVENT, RESPONSE_EVENT
from .handler import Handler, HandlerContext
from .request import ERR_NO_HANDLER, ERR_RAISED, ERR_TIMEOUT, KEY_BODY, KEY_ERROR, KEY_OK

__all__ = [
    "Channel", "DEFAULT_TIMEOUT", "REQUEST_EVENT", "RESPONSE_EVENT",
    "Handler", "HandlerContext",
    "ERR_NO_HANDLER", "ERR_RAISED", "ERR_TIMEOUT",
    "KEY_BODY", "KEY_ERROR", "KEY_OK",
]
