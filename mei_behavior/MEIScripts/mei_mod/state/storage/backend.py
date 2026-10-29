# coding=utf-8
# ----------------------------------------------------------------------
#  backend.py is part of MoreEnoughItems.
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
持久化的**引擎接触面** —— 全项目唯一直接调 ConfigClient 的地方.

⚠️ 本模块顶层 import 客户端引擎, 故 **storage/__init__.py 不得导出它**,
否则任何想用纯 Store 的人(含离线探针)都会被迫拉起客户端.
这是 utils/__init__.py 那个破口的同型问题(tasks_s1.md §6.4), 不能再犯.
消费方显式写 `from ...storage.backend import ConfigBackend`.

引擎契约:
    SetConfigData(configName, value, isGlobal) -> bool
    GetConfigData(configName, isGlobal)        -> dict
  · configName 只能含字母/数字/下划线, 须带命名空间前缀
  · isGlobal=True 为全局配置(**跨存档**), False 为存档配置
"""
import re

import mod.client.extraClientApi as clientApi

NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
""" 引擎对 configName 的字符集要求 """


def validate_name(config_name):  # type: (str) -> str
    """ 提前把非法命名拦在本地, 免得静默存不进去 """
    if not isinstance(config_name, basestring) or not NAME_RE.match(config_name):
        raise ValueError(
            "configName 只能含字母/数字/下划线, 收到: {!r}".format(config_name))
    return config_name


class ConfigBackend(object):
    """
    ConfigClient 后端. **组件惰性创建** —— 构造期不碰引擎.

    被删掉的 local_data.py 正是反面教材: 模块级单例的 __init__ 里就
    GetLevelId() + CreateConfigClient(), 把引擎构造拉进了脚本加载期.
    """

    def __init__(self):
        self._comp = None

    def _ensure(self):
        if self._comp is None:
            self._comp = clientApi.GetEngineCompFactory().CreateConfigClient(
                clientApi.GetLevelId())
        return self._comp

    def read(self, config_name, is_global):  # type: (str, bool) -> dict or None
        return self._ensure().GetConfigData(validate_name(config_name), is_global)

    def write(self, config_name, value, is_global):  # type: (str, dict, bool) -> bool
        return bool(self._ensure().SetConfigData(
            validate_name(config_name), value, is_global))


class EngineScheduler(object):
    """
    把 Store 的合并写排进引擎定时器. 同样惰性创建组件.

    Store 只认 schedule(delay, fn) 这一个鸭子方法, 因此离线测试可注入假调度器.
    """

    def __init__(self):
        self._comp = None

    def _ensure(self):
        if self._comp is None:
            self._comp = clientApi.GetEngineCompFactory().CreateGame(
                clientApi.GetLevelId())
        return self._comp

    def schedule(self, delay, func):
        return self._ensure().AddTimer(delay, func)
