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
对外 API 层。第三方**不经过本包**，他们只拿 comp.MeiApiComponent 的实例。
本门面是给 MEI 自身与内置扩展用的，见 docs/extension_api.md。
"""

# 只导常量：comp 顶层拉客户端引擎（GetComponentCls），context 拉 registry 与 ui_script，
# 在门面里急加载会把整套设施拖进任何 import 本包的人（engineering.md 的「包门面急加载」）
from .version import API_VERSION, COMP_CLS_PATH, COMP_NAME, COMP_NAMESPACE

__all__ = [
    "API_VERSION",
    "COMP_CLS_PATH",
    "COMP_NAME",
    "COMP_NAMESPACE",
]
