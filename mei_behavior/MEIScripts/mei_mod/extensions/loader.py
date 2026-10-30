# coding=utf-8

# ----------------------------------------------------------------------
#  loader.py is part of MoreEnoughItems.
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
扩展装配器：拉内置清单 + 收第三方注册 + 驱动三阶段 + 逐扩展异常隔离。
装配时序与推拉混合模型见 docs/architecture/extensions.md §4。
"""
from MEIScripts.api.version import API_VERSION
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text

from .base import MeiExtension

PHASES = ("OnInit", "OnRegister", "OnReady")
""" 驱动顺序；OnUnload 不在此列，它由 Shutdown 单独逆序调用 """


class __ExtensionLoader(object):  # noqa
    """ 扩展装配器，构造期不碰引擎也不加载任何扩展 """

    def __init__(self):
        self._pending = []      # type: list  # 尚未装配的扩展类
        self._loaded = []       # type: list  # 已装配的实例，按装配顺序（实例化成功就算：某个阶段抛了只跳过那一阶段，卸载照样要卸）
        self._tick_warned = set()  # type: set  # OnTick 抛过异常的扩展 ID：每帧路径，同一个扩展只记一行
        self._contexts = {}     # type: dict  # id(ext) -> ExtensionContext
        self._booted = False

        self._external = []     # type: list
        """
        第三方注册过的扩展类名册，**跨 Shutdown 保留**。

        重进世界时 MEI 走 Shutdown + Boot（`SyncLoadedItems`），而第三方**不会**
        重新注册 —— 它们的模块在同一个游戏进程里不会被重新 import。
        没有这份名册，第二次进世界起第三方扩展就全部消失，
        且没有任何报错(Boot 只会去拉内置清单)。
        """

    def IsBooted(self):  # type: () -> bool
        return self._booted

    def ListLoaded(self):  # type: () -> list
        return list(self._loaded)

    # 注册入口
# ======================================================================================================================
    def RegisterExtension(self, extension_cls):  # type: (type) -> bool
        """ 收下一个扩展类；已 Boot 过则立即装配它，否则排队 """
        # 加载顺序不可控，两种情况都必须能工作，见 extensions.md §1.3

        # **同一个类重复注册是幂等的，不是错误。** 第三方常把注册挂在每次进世界
        # 都会触发的钩子上(UiInitFinished 之类)，第二次进来时它还在名册里 ——
        # 那时什么都没出错，不该回 False 更不该往日志里灌"ID 已被占用"。
        # 「另一个类来抢同一个 ID」才是错，那条仍由 _Accept 拒掉。
        if extension_cls in self._external:
            return True
        if not self._Accept(extension_cls):
            return False

        # 同 ID 的旧类**换掉**而不是并存 —— 这条只在 Shutdown 之后走得到
        # (还挂着的时候 _Accept 已经按 _loaded 拒了), 即第三方热重载自己的代码。
        # 并存的话 Boot 会把同一个 ID 装配两遍。
        stale = self._IndexOfExternal(getattr(extension_cls, "ID", ""))
        if stale is None:
            self._external.append(extension_cls)
        else:
            self._external[stale] = extension_cls

        if not self._booted:
            self._pending.append(extension_cls)
            return True
        instance = self._Instantiate(extension_cls)
        if instance is None:
            return False
        self._loaded.append(instance)
        for phase in PHASES:
            self._Drive(instance, phase)
        return True

    def Boot(self):  # type: () -> int
        """ 装配内置清单与已排队的第三方扩展，返回成功装配的个数 """
        if self._booted:
            logger.warn("[MEI/ext] Boot 重复调用, 已忽略")
            return len(self._loaded)

        from . import EXTENSIONS
        builtins = []
        for name in EXTENSIONS:
            cls = self._ImportBuiltin(name)
            if cls is not None and self._Accept(cls):
                builtins.append(cls)
        # 内置的排在最前：第三方在第一次 Boot 之前就注册了的话，不这样排第一个世界与之后的装配顺序不一样（类型的先后跟着翻）
        self._pending = builtins + [cls for cls in self._pending if cls not in builtins]

        # 第三方名册补回来 —— 重进世界时它们不会重新注册, 见 _external 的注释
        for cls in self._external:
            if cls not in self._pending:
                self._pending.append(cls)

        instances = []
        for cls in self._pending:
            instance = self._Instantiate(cls)
            if instance is not None:
                instances.append(instance)
                self._loaded.append(instance)
        self._pending = []
        self._booted = True

        # 三阶段各自跑完一轮再进下一阶段：OnReady 的意义就是"所有人都注册完了"
        for phase in PHASES:
            for instance in instances:
                self._Drive(instance, phase)

        logger.info("[MEI/ext] 装配完成, 共 {} 个扩展: {}".format(
            len(self._loaded), ", ".join(e.ID for e in self._loaded)))
        return len(self._loaded)

    def Tick(self):
        """ 把节拍派发给全部已装配扩展，由客户端主系统的 Update 调 """
        # 不走 _Drive: 那里每次都要取 ctx 并做 phase 判断, 这是每帧路径
        for instance in self._loaded:
            try:
                instance.OnTick(self._ContextOf(instance))
            except Exception as e:  # noqa  一个扩展的每帧逻辑炸了不能拖垮整帧
                if instance.ID not in self._tick_warned:
                    self._tick_warned.add(instance.ID)
                    logger.error("[MEI/ext] {} 的 OnTick 抛异常（之后同样的不再记）: {}".format(instance.ID, error_text(e)))

    def Shutdown(self):
        """ 逆序卸载全部扩展，供热重载与重进世界 """
        from MEIScripts.mei_mod.ui_script.mei_ui.modes.drops import DropTargets
        from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.screen_transfers import ScreenTransfers
        from MEIScripts.registry.filters import ItemFilters
        for instance in reversed(self._loaded):
            self._Drive(instance, "OnUnload")
            # 工具模式的放置目标、按界面登记的配方转移都记在扩展 ID 名下（ctx.UI.Drops / Transfers），扩展自己没撤的这里撤掉：
            # 不然重进世界后旧的回调还挂着、还先被命中
            DropTargets.UnregisterOwner(instance.ID)
            ScreenTransfers.UnregisterOwner(instance.ID)
        # 物品栏的筛选与排序只有内置的与扩展登记的：扩展都卸了就回到只有内置的 ——
        # 扩展没撤的旧函数不留到下一个世界，重复的 Id 也就不会挡住它下次的登记
        ItemFilters.Reset()
        self._loaded = []
        self._tick_warned = set()
        self._contexts = {}
        self._booted = False
        # **`_external` 不清** —— 它是第三方名册，清了就等于下次 Boot 只剩内置扩展。
        # 看着像漏了一行，其实是这里唯一的关键点，别"顺手补上"。

    # 内部
# ======================================================================================================================
    def _Accept(self, extension_cls):  # type: (type) -> bool
        """ 准入校验：类型、ID 命名空间、API 版本、重复 ID """
        if not isinstance(extension_cls, type) or not issubclass(extension_cls, MeiExtension):
            logger.error("[MEI/ext] 拒绝: {!r} 不是 MeiExtension 子类".format(extension_cls))
            return False

        ext_id = getattr(extension_cls, "ID", "")
        if not isinstance(ext_id, basestring) or not ext_id or ":" not in ext_id:
            logger.error("[MEI/ext] 拒绝: ID {!r} 必须带命名空间前缀, 形如 yourmod:xxx".format(ext_id))
            return False
        try:
            ext_id.encode("ascii") if isinstance(ext_id, unicode) else ext_id.decode("ascii")  # noqa  py2 的 unicode
        except UnicodeError:
            # 日志前缀、存档的键都按 str 拼：非 ASCII 的 ID 一拼就抛 UnicodeError，连异常隔离的那一行日志都会再抛一次
            logger.error("[MEI/ext] 拒绝: ID {!r} 只能用 ASCII 字符".format(ext_id))
            return False

        required = getattr(extension_cls, "MIN_API_VERSION", 1)
        if required > API_VERSION:
            logger.error(
                "[MEI/ext] 拒绝 {}: 它要求扩展 API v{}, 当前只有 v{}, 请更新 MEI".format(
                    ext_id, required, API_VERSION))
            return False

        if self._FindById(ext_id) is not None or any(
                getattr(c, "ID", None) == ext_id for c in self._pending):
            logger.error("[MEI/ext] 拒绝 {}: 该 ID 已被占用".format(ext_id))
            return False
        return True

    def _FindById(self, ext_id):  # type: (str) -> any
        for instance in self._loaded:
            if instance.ID == ext_id:
                return instance
        return None

    def _IndexOfExternal(self, ext_id):  # type: (str) -> int or None
        """ 第三方名册里该 ID 的下标，没有返回 None """
        for index, cls in enumerate(self._external):
            if getattr(cls, "ID", None) == ext_id:
                return index
        return None

    def _ImportBuiltin(self, name):  # type: (str) -> type or None
        """ 内置扩展与 MEI 同在一个 addon，普通 import 即可 """
        try:
            module = __import__(
                "MEIScripts.mei_mod.extensions." + name, {}, {}, ["EXTENSION"])
        except Exception as e:  # noqa  一个内置扩展炸了不该带走其余的
            logger.error("[MEI/ext] 内置扩展 {} 导入失败: {}".format(name, error_text(e)))
            return None
        cls = getattr(module, "EXTENSION", None)
        if cls is None:
            logger.error("[MEI/ext] 内置扩展 {} 没有导出 EXTENSION".format(name))
        return cls

    def _Instantiate(self, extension_cls):  # type: (type) -> any
        # 传类而不是实例，由装配器控制构造时机，避免第三方在 __init__ 里碰引擎
        try:
            return extension_cls()
        except Exception as e:  # noqa
            logger.error("[MEI/ext] {} 实例化失败: {}".format(
                getattr(extension_cls, "ID", extension_cls), error_text(e)))
            return None

    def _ContextOf(self, instance):  # type: (any) -> any
        ctx = self._contexts.get(id(instance))
        if ctx is None:
            from MEIScripts.api.context import ExtensionContext
            ctx = ExtensionContext(instance)
            self._contexts[id(instance)] = ctx
        return ctx

    def _Drive(self, instance, phase):  # type: (any, str) -> bool
        """ 驱动一个扩展的一个阶段，异常就地吞掉 """
        # 第三方代码质量不可控，一个坏扩展不能拖垮 MEI，见 extensions.md §1.4
        try:
            getattr(instance, phase)(self._ContextOf(instance))
        except Exception as e:  # noqa
            logger.error("[MEI/ext] {} 的 {} 抛异常: {}".format(instance.ID, phase, error_text(e)))
            return False
        return True


ExtensionLoader = __ExtensionLoader()
