# coding=utf-8
# ----------------------------------------------------------------------
#  store.py is part of MoreEnoughItems.
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
持久化门面 —— **纯逻辑, 零引擎依赖**, 后端由构造注入.

分层理由: 命名空间/版本/迁移/脏标记/节流这些规则与「用什么存」无关,
把它们和 ConfigClient 绑在一起就再也没法离线验证. 后端只需满足鸭子契约:
    read(config_name, is_global)         -> dict or None
    write(config_name, value, is_global) -> bool

内存权威 + 脏标记 + 合并写: SetConfigData 是磁盘 IO, 不能每次改动都落一次盘.
"""
import json

from MEIScripts.utils.log import logger
from MEIScripts.utils.stablehash import stable_text
from MEIScripts.utils.text import error_text, to_native

KEY_VERSION = "v"
""" 载荷版本号. 留在**外层**(不进 payload 字符串), 这样即使 payload 解析失败也知道是哪版 """

KEY_PAYLOAD = "payload"
""" 业务数据整体 json.dumps 后的字符串 —— 绕开引擎对嵌套/非字符串键/tuple 的不确定支持 """

BAK_SUFFIX = "_bak"
""" 载荷损坏时的备份键后缀 (仍满足 configName 只含字母数字下划线的要求) """

RETRY_ONCE = True
""" 写失败时退避重试一次 """


class Store(object):
    """
    一个 configName 的读写门面.

    构造**完全不碰引擎**, 后端组件由 backend 自己惰性创建 ——
    这是被删掉的 local_data.py 留下的教训: 模块级单例在 import 期调
    GetLevelId()/CreateConfigClient(), 会把引擎构造拉进脚本加载期.
    """

    def __init__(self, backend, config_name, is_global=True,
                 version=1, migrations=None, scheduler=None, delay=2.0):
        # type: (any, str, bool, int, dict, any, float) -> None
        self.Backend = backend
        self.ConfigName = config_name
        self.IsGlobal = bool(is_global)
        self.Version = int(version)
        self.Migrations = migrations or {}
        self.Scheduler = scheduler  # schedule(delay, fn); 为空则只标脏、不自动落盘
        self.Delay = delay

        self._data = {}
        self._loaded = False
        self._dirty = False
        self._degraded = False   # 写失败, 已转内存态
        self._readonly = False   # 读到未来版本, 拒绝覆盖
        self._pending = False    # 已排了一次合并写

    # 状态查询
# ======================================================================================================================
    def IsDirty(self):  # type: () -> bool
        return self._dirty

    def IsDegraded(self):  # type: () -> bool
        """ 写失败后转内存态: 数据本轮仍可用, 但**不会落盘** """
        return self._degraded

    def IsReadOnly(self):  # type: () -> bool
        """
        读到比本版更新的载荷(用户降级了 Mod), 拒绝覆盖以免毁掉新版数据.

        **必须先 Load** —— 只读与否取决于盘上的内容, 而 Load 是惰性的;
        不加这一句, 调用方构造完就问会拿到恒为 False 的陈旧答案.
        (IsDirty/IsDegraded 只反映内存与写结果, 无需 Load.)
        """
        self.Load()
        return self._readonly

    # 读写
# ======================================================================================================================
    def Load(self, force=False):  # type: (bool) -> dict
        """ 读取并解析; 幂等. 任何失败都**不清空**用户数据, 见 §5 失败处置 """
        if self._loaded and not force:
            return self._data

        self._loaded = True
        self._data = {}
        self._readonly = False

        record = None
        try:
            record = self.Backend.read(self.ConfigName, self.IsGlobal)
        except Exception as e:  # noqa  引擎异常不能把界面带崩
            logger.error("[MEI/store] 读取 {} 失败: {}".format(self.ConfigName, error_text(e)))
            return self._data

        if not record:
            return self._data

        raw_version = record.get(KEY_VERSION, 0)
        try:
            raw_version = int(raw_version)
        except (TypeError, ValueError):
            raw_version = 0

        if raw_version > self.Version:
            # 用户装过更新的版本: 不解析、不覆盖, 只读运行
            self._readonly = True
            logger.warn(
                "[MEI/store] {} 的载荷版本 {} 高于当前 {}, 转只读以免覆盖新版数据".format(
                    self.ConfigName, raw_version, self.Version)
            )
            return self._data

        text = record.get(KEY_PAYLOAD)
        if not text:
            return self._data

        try:
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("payload 顶层必须是 dict")
        except Exception as e:  # noqa
            # **不静默清空** —— 备份原文, 主键留空, 报错
            self._backup(record, e)
            return self._data

        # json.loads 只产 unicode，而引擎只认 str，这是外部字符串进内存的唯一入口
        # 见 CLAUDE.md 引擎结论 §2
        payload = to_native(payload)

        try:
            self._data = self._migrate(payload, raw_version)
        except Exception as e:  # noqa
            # 数据可以丢，加载不能卡（engineering.md §7-9）：与 JSON 损坏同一处置
            self._backup(record, e)
            self._data = {}
        return self._data

    def Get(self, key, default=None):
        self.Load()
        return self._data.get(key, default)

    def Set(self, key, value):
        self.Load()
        # 写入端也规约，否则「本次写进去的」与「下次读回来的」类型不一致，会出现当场能用重开就坏
        key = to_native(key)
        value = to_native(value)
        if self._data.get(key, _MISSING) == value:
            return False
        self._data[key] = value
        self._dirty = True
        self._request_flush()
        return True

    def Delete(self, key):
        self.Load()
        if key not in self._data:
            return False
        del self._data[key]
        self._dirty = True
        self._request_flush()
        return True

    def All(self):  # type: () -> dict
        self.Load()
        return dict(self._data)

    def Flush(self, force=False):  # type: (bool) -> bool
        """ 落盘. force=True 时跳过脏标记检查(用于关界面等强制刷盘点) """
        self._pending = False
        if self._readonly:
            return False
        if not self._dirty and not force:
            return True

        record = {
            KEY_VERSION: self.Version,
            KEY_PAYLOAD: stable_text(self._data),
        }

        if self._write(record):
            self._dirty = False
            self._degraded = False
            return True

        self._degraded = True
        logger.error(
            "[MEI/store] {} 写入失败, 已转内存态 —— 本轮改动不会保留".format(self.ConfigName)
        )
        return False

    # 内部
# ======================================================================================================================
    def _write(self, record):  # type: (dict) -> bool
        for attempt in range(2 if RETRY_ONCE else 1):
            try:
                if self.Backend.write(self.ConfigName, record, self.IsGlobal):
                    return True
            except Exception as e:  # noqa
                logger.error("[MEI/store] 写 {} 抛异常(第 {} 次): {}".format(
                    self.ConfigName, attempt + 1, error_text(e)))
        return False

    def _backup(self, record, error):
        logger.error("[MEI/store] {} 载荷解析失败({}), 原文备份到 {}".format(
            self.ConfigName, error_text(error), self.ConfigName + BAK_SUFFIX))
        try:
            self.Backend.write(self.ConfigName + BAK_SUFFIX, record, self.IsGlobal)
        except Exception as e:  # noqa
            logger.error("[MEI/store] 备份也失败了: {}".format(error_text(e)))

    def _migrate(self, payload, from_version):  # type: (dict, int) -> dict
        """ 逐版升级；某一步抛异常时整体放弃，由 Load 兜底，见那里 """
        version = from_version
        while version < self.Version:
            step = self.Migrations.get(version)
            if step is None:
                # 没有对应迁移步: 保留数据原样升版, 不丢用户内容
                logger.warn("[MEI/store] {} 缺少 v{} 的迁移步, 按原样升版".format(
                    self.ConfigName, version))
                break
            payload = step(payload)
            if not isinstance(payload, dict):
                raise ValueError("v{} 的迁移步没有返回 dict".format(version))
            version += 1
        return payload

    def _request_flush(self):
        """ 合并写: 已排过就不再排, 把一串连续 Set 合成一次落盘 """
        if self._pending:
            return
        if not self.Scheduler:
            return          # 无调度器时只标脏, 等显式 Flush
        self._pending = True
        self.Scheduler.schedule(self.Delay, self.Flush)


class _Missing(object):
    """ 区分「键不存在」与「值是 None」 """
    def __repr__(self):
        return "<missing>"


_MISSING = _Missing()
