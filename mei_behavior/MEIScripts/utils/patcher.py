# coding=utf-8
# ----------------------------------------------------------------------
#  patcher.py is part of MoreEnoughItems.
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
import mod_log


def _engine_logger():  # type: () -> any
    """
    引擎自己的 logger：SDK 登记 / 摘掉一条界面绑定都往它记一行 info。
    它不在公开接口里（官方存根的 mod_log 只有 logger），所以用到时才取、取不到就不屏蔽
    """
    return getattr(mod_log, "engine_logger", None)


class LogPatcher(object):
    """ 通过上下文管理器来屏蔽log处理 可以屏蔽log输出 以及优化执行耗时；取不到引擎的 logger 时什么都不做 """
    def __init__(self):
        def patch(*_, **__):
            return None
        self.Patched = False
        self.Target = None
        self.RawFunc = None
        self.PatchFunc = patch

    def Enable(self):
        if self.Patched:
            return False
        target = _engine_logger()
        if target is not None:
            self.RawFunc = target.info
            target.info = self.PatchFunc
        self.Target = target
        self.Patched = True
        return True

    def Disable(self):
        if not self.Patched:
            return False
        if self.Target is not None:
            self.Target.info = self.RawFunc
        self.Target = None
        self.RawFunc = None
        self.Patched = False
        return True

    def __enter__(self):
        if not self.Enable():
            self.Disable()
            raise RuntimeError("failed to enable log patcher")

    def __exit__(self, *args):
        if not self.Disable():
            raise RuntimeError("failed to disable log patcher")