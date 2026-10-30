# coding=utf-8

# ----------------------------------------------------------------------
#  registry.py is part of MoreEnoughItems.
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

from collections import OrderedDict

from .rules import holds


class AdaptiveControlRegistry(object):
    """
    登记的避让目标（按路径或控件），按需取出「这会儿要避让的」：登记着、开着（enabled）、看得见、条件成立（rules.holds）的那些
    """

    def __init__(self):
        self._controls = OrderedDict()  # type: OrderedDict  # 按登记的先后：第一条就是主内容（ContentPaths[0]，配方页开着时是配方页本身）
        self._version = 0  # type: int

    def _BumpVersion(self):
        self._version += 1

    def GetVersion(self):
        return self._version

    @staticmethod
    def _BuildKey(path=None, key=None):
        if key:
            return key
        return path

    def register_control(self, path=None, key=None, use_root_path=True, condition=None, enabled=True, control=None,
                         always=False):
        """
        condition：生效条件 condition(get) -> bool（rules.py），不给就只看看不看得见；
        always：悬浮窗管事、不避让原版界面的时候也照样避让它（配方页那几块）
        """
        if control is None and not path:
            raise ValueError("either control or path must be provided")

        entry_key = self._BuildKey(path, key)
        self._controls[entry_key] = {
            "path": path,
            "use_root_path": bool(use_root_path),
            "condition": condition if callable(condition) else None,
            "enabled": bool(enabled),
            "control": control,
            "always": bool(always),
        }
        self._BumpVersion()
        return entry_key

    def UnregisterControl(self, key_or_path):
        if key_or_path in self._controls:
            del self._controls[key_or_path]
            self._BumpVersion()

    def SetEnabled(self, key_or_path, enabled):
        entry = self._controls.get(key_or_path)
        if entry is None:
            return
        enabled = bool(enabled)
        if entry.get("enabled", True) == enabled:
            return
        entry["enabled"] = enabled
        self._BumpVersion()

    def Clear(self):
        self._controls = OrderedDict()
        self._BumpVersion()

    def ListKeys(self):
        return list(self._controls.keys())

    def InitFromPaths(self, paths, use_root_path=True, clear=True, conditions=None):
        """ 按代理参数登记：ContentPaths 的每一条，带上 Conditions 里给它的条件 """
        if clear:
            self.Clear()

        conditions = conditions or {}
        for path in paths or []:
            self.register_control(
                path=path,
                use_root_path=use_root_path,
                condition=conditions.get(path),
                enabled=True,
            )

    def ResolveControls(self, screen_node, root_getter):
        return [control for control, _ in self.ResolveControlsTagged(screen_node, root_getter)]

    def ResolveControlsTagged(self, screen_node, root_getter):
        """ 同 ResolveControls，每个控件带上 always 标记：[(控件, always)] """
        controls = []
        memo = {}  # 这一轮里每个条件函数只问一次
        for _, entry in self._controls.items():
            if not entry.get("enabled", True):
                continue

            control = entry.get("control")
            if control is None:
                path = entry.get("path")
                if not path:
                    continue

                try:
                    if entry.get("use_root_path", True):
                        control = root_getter(path)
                    else:
                        control = screen_node.GetBaseUIControl(path)
                except Exception:  # noqa
                    control = None

            if not control:
                continue

            try:
                if not control.GetVisible():
                    continue
            except Exception:  # noqa
                pass

            if not holds(entry.get("condition"), root_getter, memo):
                continue

            controls.append((control, bool(entry.get("always", False))))

        return controls

