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
from . import names


def Boot():  # type: () -> bool
    """ 把 MEI 分栏的代理挂到原版设置页上，UiInitFinished 之后调 """
    # 惰性 import：ProxyManager 用到引擎，names 要能离线给探针用
    from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
    return ProxyManager.RegisterProxyScript(names.SCREEN_DEF, names.PROXY_PATH)
