# coding=utf-8
# ----------------------------------------------------------------------
#  version.py is part of MoreEnoughItems.
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

API_VERSION = 2
"""
扩展 API 版本，纯整数，**只在破坏性变更时 +1**。

与 mod_info.Version 是两码事：MEI 会因 bugfix 频繁发版，而 API 的破坏性变更应当罕见，
绑在一起会逼第三方每次都改声明。扩展用 MIN_API_VERSION 声明自己要求的下限。
"""

COMP_NAMESPACE = "MoreEnoughItems"
""" 对外组件的命名空间，第三方 CreateComponent 的第二个参数 """

COMP_NAME = "MeiApi"
""" 对外组件名，第三方 CreateComponent 的第三个参数 """

COMP_CLS_PATH = "MEIScripts.api.comps.mei_api.MeiApiComponent"
""" 注册给引擎的组件类路径，从脚本第一层算起 """
