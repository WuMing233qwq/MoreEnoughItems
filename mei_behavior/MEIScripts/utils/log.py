# coding=utf-8

# ----------------------------------------------------------------------
#  log.py is part of MoreEnoughItems.
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
日志入口的**唯一**兜底点。

纯逻辑模块(types / utils / registry/index …)要能脱离客户端引擎被 import
(engineering.md §2), 而 `mod_log` 只在游戏进程里存在。原先每个这类模块
各自抄了一份 try/except 兜底, 全仓共 5 份 —— 收敛到这里。

用法与直接 import 完全一致::

    from MEIScripts.utils.log import logger

> 仍在引擎内运行的模块(UI 脚本、双端 System)照旧写 `from mod_log import logger`
> 即可, 它们本来就不可能脱离引擎, 不必绕这一层。
"""

__all__ = ["logger"]


class _NullLogger(object):
    """ 离线环境下的空实现: 吞掉任何调用, 保持调用方代码不变 """

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


try:
    from mod_log import logger
except ImportError:  # 离线 / 探针环境
    logger = _NullLogger()
