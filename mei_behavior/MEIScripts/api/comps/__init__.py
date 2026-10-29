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
对外组件：跨 addon 边界的唯一通道，一个文件一个组件。
"""
from MEIScripts.utils.log import logger


def RegisterAll():  # type: () -> bool
    """ 把全部对外组件注册进引擎，由 modMain 在 InitClient 阶段调一次 """
    # 注册要在任何扩展逻辑之前：第三方靠 CreateComponent 拿它
    import mod.client.extraClientApi as clientApi

    from ..version import COMP_CLS_PATH, COMP_NAME, COMP_NAMESPACE

    ok = clientApi.RegisterComponent(COMP_NAMESPACE, COMP_NAME, COMP_CLS_PATH)
    if not ok:
        logger.error("[MEI/api] 对外组件 {}:{} 注册失败, 第三方将无法接入".format(
            COMP_NAMESPACE, COMP_NAME))
    return ok
