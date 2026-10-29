# coding=utf-8
# ----------------------------------------------------------------------
#  proxy.py is part of MoreEnoughItems.
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
import mod.client.extraClientApi as clientApi

from MEIScripts.constants import mod_info
from MEIScripts.mei_mod.state import SettingsManager
from MEIScripts.mei_mod.ui_script.proxy.base import ScreenProxy
from MEIScripts.utils.lang import localize
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str

from . import names

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()

SLIDER_FLAGS = getattr(ViewBinder, "BF_SliderChanged", 0) | getattr(ViewBinder, "BF_SliderFinished", 0)
""" 官方绑定类型表里没列这两个，取不到时滑条只显示不响应 """


class SettingsProxy(ScreenProxy):
    """
    原版设置页的代理，给 MEI 分栏里的每个设置项挂绑定
    """

    def __init__(self, screen_name, screen_node):
        ScreenProxy.__init__(self, screen_name, screen_node)
        self.Pending = {}  # type: dict  # 拖动中的滑条位置，松手才提交
        self.Failed = set()  # type: set  # 报过错的绑定名，免得每帧刷日志
        self._ready = True

    def OnCreate(self):
        if not getattr(self, "_ready", False):
            return
        self.Bindings.Bind(self._Safe(names.ENABLED, lambda: True, True), ViewBinder.BF_BindBool, names.ENABLED)
        self.Bindings.Bind(
            self._Safe(names.DEGRADED, SettingsManager.IsDegraded, False), ViewBinder.BF_BindBool, names.DEGRADED)
        self.Bindings.Bind(self._Safe(names.ABOUT, self.AboutText, ""), ViewBinder.BF_BindString, names.ABOUT)
        binders = {"toggle": self._BindToggle, "slider": self._BindSlider,
                   "choice": self._BindSlider, "action": self._BindAction, "keybind": self._BindKey}
        for spec in SettingsManager.GetSpecs():
            binder = binders.get(spec.KIND)
            if binder is None:
                logger.warn("[MEI/settings] 不认识的设置项类型 {}".format(spec.KIND))
                continue
            try:
                binder(spec)
            except Exception as e:  # noqa  一项挂不上不该带走整页
                logger.error("[MEI/settings] {} 的绑定没挂上: {}".format(spec.Key, error_text(e)))

    def OnDestroy(self):
        if not getattr(self, "_ready", False):
            return
        self.Pending.clear()
        # 正在录键就放弃（关了设置页再按的键不该存进去）
        from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys import manager as hotkeys
        hotkeys.CancelCapture()
        SettingsManager.Flush()
        try:
            self.Bindings.UnbindAll()
        except Exception as e:  # noqa  屏幕已在销毁，解绑失败无所谓
            logger.warn("[MEI/settings] 解绑失败: {}".format(error_text(e)))

    # 各类设置项的绑定
# ======================================================================================================================
    def _BindToggle(self, spec):
        key = spec.Key

        def changed(args):
            SettingsManager.Set(key, bool((args or {}).get("state")))
            return ViewRequest.Refresh

        self.Bindings.Bind(changed, ViewBinder.BF_ToggleChanged, names.toggle_changed(key))
        state = names.toggle_state(key)
        self.Bindings.Bind(
            self._Safe(state, lambda: bool(SettingsManager.Get(key)), False), ViewBinder.BF_BindBool, state)

    def _BindSlider(self, spec):
        key = spec.Key

        def changed(position, is_finish, *_unused):
            # 拖动中只记位置给显示用，松手才算改；否则每一帧都会写盘、通知订阅方
            if is_finish:
                self.Pending.pop(key, None)
                SettingsManager.Set(key, spec.FromPosition(position))
            else:
                self.Pending[key] = position
            return ViewRequest.Refresh

        def value():
            position = self.Pending.get(key)
            if position is None:
                position = spec.ToPosition(SettingsManager.Get(key))
            return float(position)

        def label():
            position = self.Pending.get(key)
            current = SettingsManager.Get(key) if position is None else spec.FromPosition(position)
            return "{}: {}".format(self.Text(spec.Label), self.ValueText(spec, current))

        if SLIDER_FLAGS:
            self.Bindings.Bind(changed, SLIDER_FLAGS, names.slider_changed(key))
        else:
            logger.error("[MEI/settings] 引擎没有滑条绑定类型, {} 只能看不能拖".format(key))
        for name, func, fallback, flag in (
            (names.slider_value(key), value, 0.0, ViewBinder.BF_BindFloat),
            (names.slider_steps(key), lambda: int(spec.Steps), 1, ViewBinder.BF_BindInt),
            (names.slider_label(key), label, "", ViewBinder.BF_BindString),
        ):
            self.Bindings.Bind(self._Safe(name, func, fallback), flag, name)

    def _BindAction(self, spec):
        key = spec.Key

        def pressed(_args):
            SettingsManager.Run(key)
            return ViewRequest.Refresh

        self.Bindings.Bind(pressed, ViewBinder.BF_InteractButtonClick, names.button_pressed(key))

    def _BindKey(self, spec):
        """
        按键绑定的一行（docs/architecture/bookmarks.md §12）：点按钮开始录键、再点一下保存（录键在快捷键那边，manager.ToggleCapture）；
        右边的按钮恢复默认；按钮上的字每帧读（正在录的黄字、和别的快捷键撞了红字）
        """
        from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys import manager as hotkeys  # 设置页用到才 import
        key = spec.Key

        def pressed(_args):
            hotkeys.ToggleCapture(key)
            return ViewRequest.Refresh

        def reset(_args):
            hotkeys.CancelCapture()
            SettingsManager.Reset(key)
            return ViewRequest.Refresh

        self.Bindings.Bind(pressed, ViewBinder.BF_InteractButtonClick, names.button_pressed(key))
        self.Bindings.Bind(reset, ViewBinder.BF_InteractButtonClick, names.key_reset(key))
        text = names.key_text(key)
        self.Bindings.Bind(self._Safe(text, lambda: hotkeys.KeyText(key), ""), ViewBinder.BF_BindString, text)

    # 文字
# ======================================================================================================================
    def Text(self, key):  # type: (str) -> str
        """ 本地化文字，查不到给 key 本身（查字走 utils/lang.py，和别处同一份缓存）"""
        return native_str(localize(key)) or key

    def ValueText(self, spec, value):  # type: (any, any) -> str
        if spec.KIND == "choice":
            return self.Text(spec.OptionLabel(value))
        return spec.Format(value)

    def AboutText(self):  # type: () -> str
        return "\n".join([
            "{} {}".format(mod_info.ModName, mod_info.Version),
            self.Text("options.mei.about.author").format(mod_info.Author),
            self.Text("options.mei.about.repo").format(mod_info.Repository),
            self.Text("options.mei.about.license").format(mod_info.License),
        ])

    def _Safe(self, name, func, fallback):
        """ 包一层：绑定回调抛异常会让那条绑定当场失效且没有日志（CLAUDE.md 引擎结论 §15） """
        def safe():
            try:
                return func()
            except Exception as e:  # noqa
                if name not in self.Failed:
                    self.Failed.add(name)
                    logger.error("[MEI/settings] 绑定 {} 取值失败: {}".format(name, error_text(e)))
                return fallback
        return safe
