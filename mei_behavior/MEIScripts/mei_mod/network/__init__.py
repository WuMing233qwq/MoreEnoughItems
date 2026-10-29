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
双端通讯。base/ 是不认识业务的轮子，protocol/ 是具体请求的定义与处理。

**门面刻意不急加载 protocol** —— 只想用 Channel 的人不该被拖起全部业务模块
(engineering.md 的「包门面急加载」那条债)。要用具体协议就
`from MEIScripts.mei_mod.network.protocol import xxx`。
"""
from .base import Channel, Handler, HandlerContext

__all__ = ["Channel", "Handler", "HandlerContext"]
