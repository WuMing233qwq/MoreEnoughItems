# coding=utf-8

# ----------------------------------------------------------------------
#  mei_api.py is part of MoreEnoughItems.
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
对外的唯一入口：第三方 CreateComponent("MoreEnoughItems", "MeiApi") 拿到本类实例。
接入方式与硬约束见 docs/modding/（从 01-getting-started.md 读起，接口参考在 api.md）。
"""
import mod.client.extraClientApi as clientApi

from MEIScripts.utils.log import logger

from ..version import API_VERSION

ClientComponentCls = clientApi.GetComponentCls()


class MeiApiComponent(ClientComponentCls):
    """ MEI 对外 API 组件，方法签名即公共契约，跨 API_VERSION 承诺兼容 """

    def __init__(self, entityId):  # noqa  引擎按此名传参，不可改
        ClientComponentCls.__init__(self, entityId)

    # 版本
# ======================================================================================================================
    @staticmethod
    def GetApiVersion():  # type: () -> int
        """ 扩展 API 版本，第三方据此判断能力 """
        return API_VERSION

    @staticmethod
    def GetModVersion():  # type: () -> str
        """ MEI 自身版本，仅供展示，不要拿它做能力判断 """
        from MEIScripts.constants import mod_info
        return mod_info.Version

    # 扩展
# ======================================================================================================================
    @staticmethod
    def GetExtensionCls():  # type: () -> type
        """ 取扩展基类；第三方继承它来写扩展 """
        # 第三方写不出 import MEIScripts...，基类只能这样交到他们手上
        from MEIScripts.mei_mod.extensions.base import MeiExtension
        return MeiExtension

    @staticmethod
    def RegisterExtension(extension_cls):  # type: (type) -> bool
        """ 注册一个扩展类；MEI 尚未就绪则排队，已就绪则立即装配 """
        from MEIScripts.mei_mod.extensions.loader import ExtensionLoader
        return ExtensionLoader.RegisterExtension(extension_cls)

    @staticmethod
    def IsReady():  # type: () -> bool
        """ MEI 是否已完成装配；排队机制使得第三方通常不需要关心它 """
        from MEIScripts.mei_mod.extensions.loader import ExtensionLoader
        return ExtensionLoader.IsBooted()

    @staticmethod
    def ListExtensions():  # type: () -> list
        """ 已装配扩展的 (id, name, version, author) 四元组表，供调试与设置界面 """
        from MEIScripts.mei_mod.extensions.loader import ExtensionLoader
        return [(e.ID, e.NAME, e.VERSION, e.AUTHOR)
                for e in ExtensionLoader.ListLoaded()]
