# coding=utf-8

# ----------------------------------------------------------------------
#  context.py is part of MoreEnoughItems.
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
交给扩展的上下文。内容全在 facades/，本模块只负责组装与逃生舱。
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import native_str

from .version import API_VERSION


class _ExtensionLogger(object):
    """ 给扩展的 logger，自动带 [MEI/ext:<id>] 前缀 """

    __slots__ = ("_prefix",)

    def __init__(self, extension_id):
        self._prefix = "[MEI/ext:{}] ".format(extension_id or "?")

    def info(self, message):
        logger.info(self._prefix + _text(message))

    def warn(self, message):
        logger.warn(self._prefix + _text(message))

    def error(self, message):
        logger.error(self._prefix + _text(message))


def _text(message):  # type: (any) -> str
    """ 日志一行：unicode 收成 utf-8 的 str（原来 str(u"中文") 直接抛），别的照 str """
    text = native_str(message)
    return text if isinstance(text, basestring) else str(text)


class ExtensionContext(object):
    """ 生命周期方法的唯一参数，扩展不自己去取 MEI 的任何模块 """

    __slots__ = ("Registry", "Types", "UI", "Utils", "Const",
                 "Log", "Extension", "ApiVersion", "Scripts")

    def __init__(self, extension=None):
        # 门面各自顶层拉 registry / ui_script，只能在构造时 import
        from .facades.const import ConstFacade
        from .facades.registry import RegistryFacade
        from .facades.types import TypesFacade
        from .facades.ui import UiFacade
        from .facades.utils import UtilsFacade

        self.Registry = RegistryFacade()
        self.Types = TypesFacade()
        self.UI = UiFacade()
        self.Utils = UtilsFacade()
        self.Const = ConstFacade()
        self.Log = _ExtensionLogger(getattr(extension, "ID", None))
        self.Extension = extension
        self.ApiVersion = API_VERSION

        # 逃生舱：整个 MEIScripts 包。**不承诺任何稳定性** ——
        # 用它写出来的扩展在 MEI 任意一次内部重构后可能失效，且这是预期行为。
        # 上面五个分组门面才是跨 API 版本承诺兼容的公共面。
        import MEIScripts
        self.Scripts = MEIScripts
