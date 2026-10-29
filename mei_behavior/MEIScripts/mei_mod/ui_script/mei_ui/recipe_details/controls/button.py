# coding=utf-8

# ----------------------------------------------------------------------
#  button.py is part of MoreEnoughItems.
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
配方行上的动作按钮(收藏 / 置顶 / 转移 / 配方树)。

JSON 侧它们是**套了按钮外观的 toggle**(`common_toggles.switch_toggle_collection`),
所以天生有状态 —— 收藏、置顶正需要这个。但转移、配方树是无状态的一次触发,
于是这里给出两种用法, 由两个类方法构造:

    ActionButton.toggle(...)   有状态开关: 亮不亮由代码说了算
    ActionButton.button(...)   无状态按钮: 按下即触发, 视觉上立刻弹回

三种接线方式, 由易到难任选:

    1. 声明式(推荐, 与 RecipeBinder 同一个路子) —— 在脚本类上写装饰器:
           @RecipeAction.State("mymod.zap")
           def IsZapped(self, row, recipe): ...
           @RecipeAction.Toggle("mymod.zap", path="/header/zap")
           def OnZap(self, ctx): ...
       然后 `binder.Interpret(script)` 一次接完。

    2. 组表式 —— 自己造 ActionButton 丢进 `binder.Install([...])`。

**开发者一行绑定机制都不用写。**

--------------------------------------------------------------------------
两个参数就是全部: prefix 与 path
--------------------------------------------------------------------------
  prefix  绑定名前缀. 三条绑定名 = prefix + BINDING_SUFFIXES 里的后缀,
          JSON 侧 `mei_recipe_common.action_button` 用同一个 $binding_name_prefix
          派生同样三个名字 —— **后缀表就是代码层与 UI 层的统一契约**,
          与 utilities.GetItemPanelBindingConfigs() 是同一个路子。
  path    控件路径, **相对配方行控件**. 取控件走 RecipeControl.GetChildByPath,
          与 CraftingTableUIScript.InitControls 同一个路子, 不拼绝对路径也不带行号。

本模块**没有任何内置动作的知识** —— 收藏/置顶/转移/配方树的 prefix 与 path
在 recipe_details/actions.py, 那里才是 buttons_panel 的对应层。

--------------------------------------------------------------------------
身份是怎么解出来的(与槽位点击**不是一回事**, 别照抄)
--------------------------------------------------------------------------
  槽位点击 BF_ButtonClickUp : 绑定名按槽位 prefix 区分, 但 args 里**没有行号**,
                              必须解析 args["ButtonPath"] 才知道第几行。
  动作按钮 BF_ToggleChanged : 绑定名按 prefix 区分, 行号**直接在 args["index"]**。

后者能白拿行号, 是因为基类是 `switch_toggle_collection` —— 集合感知的控件,
配上 `$toggle_grid_collection_name` 后引擎会把集合下标随事件一起投递。
普通 button 没有这个变体, 所以那边才要解路径。
⇒ prefix 只承担二维地址里的一维(哪个动作), 另一维(哪一行)引擎白给。

--------------------------------------------------------------------------
引擎契约
--------------------------------------------------------------------------
  状态 Python->UI  `$toggle_state_binding_name` + BF_BindBool     可集合绑定
  交互 UI->Python  `$toggle_name`               + BF_ToggleChanged **仅普通绑定**
两者能力不对称, 注册时必须按 flag 分流（ScreenBinder.Bind 按 utilities.IsBindFlag 分）——
弄反了会"注册成功、零报错、引擎永不投递"(CLAUDE.md 引擎结论 §9)。
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.bindname import make_binding_name
from MEIScripts.utils.text import error_text

ViewBinder = clientApi.GetViewBinderCls()

# 官方接口名是 GetView**View**RequestCls(多一个 View, 是官方的笔误但那就是真名).
# 按 CLAUDE.md 引擎结论「版本/平台敏感接口一律 getattr 能力探测」两个名字都试;
# 都取不到时退化为 0(Nothing), 只损失一次刷新, 不至于让整个模块 import 失败.
_REQUEST_CLS = (getattr(clientApi, "GetViewViewRequestCls", None)
                or getattr(clientApi, "GetViewRequestCls", None))
VIEW_REQUEST_REFRESH = getattr(_REQUEST_CLS(), "Refresh", 1) if _REQUEST_CLS else 1

_UNSET = object()  # 推送缓存里「这一格原来没记过」

BINDING_SUFFIXES = (".state", ".visible", ".toggle", ".enabled")
"""
一个动作按钮的四条绑定后缀 —— **代码层与 UI 层的统一契约**。

`.enabled` 走的是**基类自带的那条绑定**(`$toggle_enabled_binding_name` ->
`#enabled`)，不是我们手写的：`common_toggles` 的 toggle 模板里本来就留了这个口子，
默认 `$toggle_enabled_binding_type` 为 `"none"` 所以一直没生效。
置成 `collection` 之后基类会自己切到 `$unchecked_locked_control`，
而我们的 `ore_style_toggle_button` 早就把它指向了 `ore_style_button_disabled_wrapper`。
⇒ **锁定态的外观零成本白拿**，不必像 state 那样 Python 直推。

调用方只给 prefix, 名字由 prefix + 后缀拼出; JSON 侧
`mei_recipe_common.action_button` 用同一个 $binding_name_prefix 拼出同样三个。
形制照抄 utilities.GetItemPanelBindingConfigs(): 前缀由调用方给, 后缀表是契约。
"""


class ActionContext(object):
    """ 一次动作交互的全部已知信息. 由绑定层填好, 交给开发者的回调消费 """

    __slots__ = ("Prefix", "Row", "Recipe", "State", "Binder")

    def __init__(self, prefix, row, recipe, state, binder):
        self.Prefix = prefix       # type: str   # 哪个动作(绑定名前缀)
        self.Row = row             # type: int   # 第几行配方(0-based)
        self.Recipe = recipe       # type: any   # 该行对应的 Recipe; 解析不出时为 None
        self.State = state         # type: bool  # 交互后的新状态
        self.Binder = binder       # type: any   # RecipeActionBind, 便于回调里刷新


class ActionButton(object):
    """
    一个动作按钮的**声明**. 不持有控件, 不碰绑定 —— 那是 RecipeActionBind 的事.

    直接构造也可以, 但推荐用两个类方法, 它们把"有状态/无状态"这件事说清楚。
    """

    __slots__ = ("Prefix", "Path", "GetState", "OnAction", "IsVisible", "IsEnabled",
                 "Momentary")

    def __init__(self, prefix, get_state=None, on_action=None,
                 is_visible=None, momentary=False, path=None, is_enabled=None):
        # type: (str, any, any, any, bool, str, any) -> None
        if not prefix:
            raise ValueError("prefix cannot be empty")
        self.Prefix = prefix         # type: str   # 绑定名前缀, 三条绑定名由它 + 后缀拼出
        self.Path = path             # type: str   # 控件路径, **相对配方行控件**; 不给则由绑定器回落
        self.GetState = get_state    # type: any   # fn(row, recipe) -> bool
        self.OnAction = on_action    # type: any   # fn(ActionContext) -> None
        self.IsVisible = is_visible  # type: any   # fn(row, recipe) -> bool
        self.IsEnabled = is_enabled  # type: any   # fn(row, recipe) -> bool; 假 = 渲染但不可点
        self.Momentary = momentary   # type: bool  # 真 = 无状态按钮

    @classmethod
    def toggle(cls, prefix, get_state, on_toggle, is_visible=None, path=None):
        """
        **有状态开关** —— 收藏、置顶这类.

        get_state(row, recipe) -> bool    每帧回读, 决定按钮亮不亮(代码控制状态)
        on_toggle(ctx) -> None            玩家切换时调用, 新状态在 ctx.State
        is_visible(row, recipe) -> bool   可选; 返回假则该按钮不渲染
        """
        if get_state is None:
            raise ValueError("toggle 用法必须给 get_state; 无状态的按钮用 ActionButton.button")
        return cls(prefix, get_state=get_state, on_action=on_toggle,
                   is_visible=is_visible, momentary=False, path=path)

    @classmethod
    def button(cls, prefix, on_click, is_visible=None, path=None):
        """
        **无状态按钮** —— 快捷转移、配方树这类"按一下做一件事".

        底层仍是 toggle(JSON 就长那样), 但状态恒为假, 所以视觉上按下即弹回;
        只在"被按亮"那一次触发 on_click, 弹回时不会再触发一遍。
        """
        if on_click is None:
            raise ValueError("button 用法必须给 on_click")
        return cls(prefix, get_state=None, on_action=on_click,
                   is_visible=is_visible, momentary=True, path=path)

    def ResolveState(self, row, recipe):  # type: (int, any) -> bool
        """ 状态绑定的取值口. 无状态按钮恒返回 False, 于是按下即弹回 """
        if self.Momentary or self.GetState is None:
            return False
        try:
            return bool(self.GetState(row, recipe))
        except Exception as e:  # noqa  单个按钮的取值失败不能拖垮整帧
            logger.error("[MEI/action] {} 取状态失败(行 {}): {}".format(
                self.Prefix, row, error_text(e)))
            return False

    def ResolveEnabled(self, row, recipe):  # type: (int, any) -> bool
        """
        可点性取值口。**与可见性是两回事**：不可见是"这一行没有这个动作"，
        不可点是"有，但现在做不了" —— 后者要让玩家看见按钮并明白为什么灰着。
        """
        if self.IsEnabled is None:
            return True
        try:
            return bool(self.IsEnabled(row, recipe))
        except Exception as e:  # noqa
            logger.error("[MEI/action] {} 取可点性失败(行 {}): {}".format(
                self.Prefix, row, error_text(e)))
            return True

    def ResolveVisible(self, row, recipe):  # type: (int, any) -> bool
        """
        可见性取值口. **没有 on_action 的按钮一律不渲染** ——
        哑按钮比没有按钮更糟, 用户会以为坏了(recipe_ui_api.md §4.6)。
        """
        if self.OnAction is None:
            return False
        if self.IsVisible is None:
            return True
        try:
            return bool(self.IsVisible(row, recipe))
        except Exception as e:  # noqa
            logger.error("[MEI/action] {} 取可见性失败(行 {}): {}".format(
                self.Prefix, row, error_text(e)))
            return False


class RecipeAction(object):
    """
    声明式接线的装饰器入口 —— 与 modules/binding.py 的 RecipeBinder 同一个路子:
    装饰器只把**声明**推到函数上, 真正的接线由 RecipeActionBind.Interpret 统一做。

    用法(写在配方页脚本或任何持有回调的对象上)::

        @RecipeAction.State("mymod.zap")
        def IsZapped(self, row, recipe):
            return MyState.Has(recipe)

        @RecipeAction.Toggle("mymod.zap", path="/header/zap")
        def OnZap(self, ctx):
            MyState.Set(ctx.Recipe, ctx.State)

        @RecipeAction.Button("mymod.info", path="/header/info")
        def OnInfo(self, ctx):
            ...

        @RecipeAction.Visible("mymod.info")      # 可选
        def CanShowInfo(self, row, recipe):
            return recipe is not None

    同一个 prefix 的 State / Toggle / Visible 会被合成一个 ActionButton;
    只有 Button 而没有 State 的就是无状态按钮。

    path 只在 Toggle / Button 上给(它俩是必写的那个); 内置动作可以不给,
    绑定器会回落到 SetPathResolver 注入的默认表(见 recipe_details/actions.py)。
    """

    _RULES_ATTR = "__mei_action_rules__"

    @staticmethod
    def __Push(func, rule):
        rules = func.__dict__.get(RecipeAction._RULES_ATTR)
        if rules is None:
            rules = []
            func.__dict__[RecipeAction._RULES_ATTR] = rules
        rules.append(rule)
        return func

    @staticmethod
    def Toggle(prefix, path=None):
        """ 有状态开关的交互回调: fn(self, ctx). 需与同 prefix 的 @State 配对 """
        def _decorator(func):
            return RecipeAction.__Push(func, {"kind": "action", "prefix": prefix,
                                              "path": path, "momentary": False})
        return _decorator

    @staticmethod
    def Button(prefix, path=None):
        """ 无状态按钮的回调: fn(self, ctx) """
        def _decorator(func):
            return RecipeAction.__Push(func, {"kind": "action", "prefix": prefix,
                                              "path": path, "momentary": True})
        return _decorator

    @staticmethod
    def State(prefix):
        """ 状态回读: fn(self, row, recipe) -> bool """
        def _decorator(func):
            return RecipeAction.__Push(func, {"kind": "state", "prefix": prefix})
        return _decorator

    @staticmethod
    def Visible(prefix):
        """ 可见性: fn(self, row, recipe) -> bool. 不写则默认可见 """
        def _decorator(func):
            return RecipeAction.__Push(func, {"kind": "visible", "prefix": prefix})
        return _decorator

    @staticmethod
    def Enabled(prefix):
        """
        可点性: fn(self, row, recipe) -> bool. 不写则默认可点

        返回假时按钮**照常渲染但灰掉不可点**(基类的 locked 态)，
        用于"这条配方现在做不了"这种要让玩家看见的情况。
        """
        def _decorator(func):
            return RecipeAction.__Push(func, {"kind": "enabled", "prefix": prefix})
        return _decorator

    @staticmethod
    def Collect(owner):  # type: (any) -> list
        """
        扫描 owner 的类, 把装饰器声明合成 ActionButton 列表.

        绑定到实例而不是类 —— 回调里能直接用 self, 这是"易用"的一半。
        """
        parts = {}
        order = []
        for name in dir(type(owner)):
            if name.startswith("__"):
                continue
            try:
                member = getattr(type(owner), name)
            except Exception:  # noqa  property 之类取值可能抛
                continue
            func = getattr(member, "im_func", member)
            rules = getattr(func, RecipeAction._RULES_ATTR, None)
            if not rules:
                continue
            bound = getattr(owner, name)
            for rule in rules:
                prefix = rule["prefix"]
                if prefix not in parts:
                    parts[prefix] = {}
                    order.append(prefix)
                parts[prefix][rule["kind"]] = bound
                if rule["kind"] == "action":
                    parts[prefix]["momentary"] = rule["momentary"]
                    parts[prefix]["path"] = rule.get("path")

        buttons = []
        for prefix in order:
            part = parts[prefix]
            buttons.append(ActionButton(
                prefix,
                get_state=part.get("state"),
                on_action=part.get("action"),
                is_visible=part.get("visible"),
                momentary=bool(part.get("momentary")) and part.get("state") is None,
                path=part.get("path"),
                is_enabled=part.get("enabled"),
            ))
        return buttons


class RecipeActionBind(object):
    """
    把一组 ActionButton 接到 recipes_grid 上.

    每个动作注册几条绑定, 且**必须分流**（ScreenBinder.Bind 按 flag 分）:
      state   BF_BindBool      集合绑定
      visible BF_BindBool      集合绑定
      toggle  BF_ToggleChanged **普通绑定**
    """

    def __init__(self, screen_node, collection_name):
        self.Bindings = ScreenBinder(screen_node)  # type: ScreenBinder
        self.CollectionName = collection_name

        self.Buttons = {}          # type: dict  # action_id -> ActionButton
        self.Wrappers = []         # type: list  # 解绑用
        self._row_resolver = None      # type: any  # fn(row) -> Recipe or None
        self._control_resolver = None  # type: any  # fn(row) -> 配方行控件
        self._path_resolver = None     # type: any  # fn(prefix) -> 相对路径, 供无 path 的按钮回落
        self._enabled_resolver = None  # type: any  # fn(prefix) -> bool, ACTIONS 开关
        self._pushed = {}          # type: dict  # (row, prefix) -> 上次推给控件的状态
        self._controls = {}        # type: dict  # (row, prefix) -> 按钮控件, 每帧路径不重复取
        self._path_warned = set()  # type: set   # 取不到控件的 (行, prefix), 只记一次

    def SetControlResolver(self, resolver):
        """
        注入 行号 -> **配方行控件** 的解析, 由屏幕提供(它才持有 RecipeUIScript 表).

        **为什么需要它**: toggle 的选中态靠绑定驱动这条路走不通(引擎结论 §10:
        状态回调每帧被调 1033 次、回读值全对, 按钮外观纹丝不动) ——
        绑定名是自己拼的字符串, 与真实控件路径是两回事。
        改为 Python 直接 SetToggleState, 那就必须拿到**真的那个控件**。
        不注入时退化为"只喂绑定", 行为与改动前一致。

        给的是**行控件**而不是按钮控件: 按钮在行内的相对路径由 ActionButton.Path
        承担, 本绑定器再 GetChildByPath 下去 —— 与 CraftingTableUIScript.InitControls
        取输入格子完全同一个路子, 全项目不出现第二种取控件方式。
        """
        self._control_resolver = resolver

    def SetPathResolver(self, resolver):
        """
        注入 prefix -> 默认相对路径 的解析, 供**没有自带 path** 的按钮回落.

        内置四个动作用它(表在 recipe_details/actions.py), 于是屏幕上的装饰器
        不必每个都重复写一遍路径。第三方按钮自带 path, 走不到这里。
        """
        self._path_resolver = resolver

    def SetEnabledResolver(self, resolver):
        """
        注入 prefix -> 是否启用. 不注入时一律启用.

        供 RecipeUIScript.ACTIONS 这类"这个配方类型不要某个内置按钮"的开关。
        **在每帧的可见性回调里问, 不在 Interpret 时问** —— 配方类型是切换的,
        Interpret 只跑一次(屏幕初始化), 那时问到的答案切一次类型就过期了。
        """
        self._enabled_resolver = resolver

    def SetRowResolver(self, resolver):
        """
        注入 行号 -> Recipe 的解析. 由配方页脚本提供(它才知道当前页有哪些配方).

        不注入时 ctx.Recipe 恒为 None, 按钮仍可用 —— 便于离线验证与纯 UI 试验.
        """
        self._row_resolver = resolver

    def Interpret(self, owner, extra=None, placeholders=None):  # type: (any, any, any) -> int
        """
        **解释器入口**: 读 owner 类上的 @RecipeAction 声明并接线, 返回装上的个数.

        extra 里可以再塞调用方自己造的 ActionButton。
        placeholders 是"兜底声明": 已声明的同 prefix 会盖掉它, 没声明的用它补上。
        **本方法不知道有哪些内置动作** —— 兜底清单由调用方给(见 recipe_details/actions.py),
        因为「JSON 里有哪几个格子」是 JSON 拥有者的知识, 不是绑定机制的知识。
        """
        declared = RecipeAction.Collect(owner)
        declared.extend(extra or ())

        known = set(b.Prefix for b in declared)
        fill = [b for b in (placeholders or ()) if b.Prefix not in known]
        return self.Install(declared + fill)

    def Install(self, buttons):  # type: (list) -> int
        """ 注册一组按钮, 返回真正注册上的个数. 重复的 action_id 直接拒绝 """
        count = 0
        for button in buttons or ():
            if button.Prefix in self.Buttons:
                logger.error("[MEI/action] 重复的绑定前缀: {}".format(button.Prefix))
                continue
            self.Buttons[button.Prefix] = button
            self.__BindOne(button)
            count += 1
        return count

    def Get(self, prefix):  # type: (str) -> ActionButton or None
        return self.Buttons.get(prefix)

    def Destroy(self):
        for wrapper in self.Wrappers:
            self.Bindings.Unbind(wrapper)
        self.Wrappers = []
        self.Buttons = {}
        self._pushed = {}
        self._controls = {}
        self._path_warned = set()

    def InvalidatePushCache(self, row=None):
        """
        丢弃"上次推过的状态"缓存, 使下一帧重新推.

        翻页 / 切配方类型 / 重建行控件之后**必须调** —— 控件是新的, 而缓存
        还记着旧控件上的值, 不清就会以为"没变"从而不推, 新控件保持默认态。
        """
        # 控件缓存与推送缓存必须一起失效: 行控件重建后旧控件对象已经不是界面上那个了,
        # 只清推送缓存会把新状态推给一个已经不在树上的控件
        if row is None:
            self._pushed = {}
            self._controls = {}
            self._path_warned = set()
            return
        self._pushed = dict((k, v) for k, v in self._pushed.items() if k[0] != row)
        self._controls = dict((k, v) for k, v in self._controls.items() if k[0] != row)
        self._path_warned -= set(k for k in self._path_warned if k[0] == row)

    # 内部
# ======================================================================================================================
    @staticmethod
    def BindingNameOf(prefix, suffix):  # type: (str, str) -> str
        """ prefix + 后缀, 与 JSON 的 action_button 用同一个 $binding_name_prefix 拼法 """
        # 只有一段前缀, 不再是 "根 + id" 两段拼 —— 与 item_panel 的
        # $binding_name_prefix 完全同形, 后缀表(BINDING_SUFFIXES)才是契约
        return make_binding_name(prefix, suffix)

    def __BindOne(self, button):
        specs = (
            (".state", ViewBinder.BF_BindBool,
             lambda row, b=button: self.__SyncState(b, row)),
            (".visible", ViewBinder.BF_BindBool,
             lambda row, b=button: self.__SyncVisible(b, row)),
            (".toggle", ViewBinder.BF_ToggleChanged,
             lambda args, b=button: self.__Dispatch(b, args)),
            (".enabled", ViewBinder.BF_BindBool,
             lambda row, b=button: b.ResolveEnabled(row, self.__RecipeOf(row))),
        )
        for suffix, flag, callback in specs:
            name = self.BindingNameOf(button.Prefix, suffix)
            # 分流是硬性的: BF_ToggleChanged 带的是 ToggleFilter 而非 BindFilter,
            # 官方绑定方式表里它**只支持 binding**, 误用集合绑定会静默失效 —— ScreenBinder 按 flag 分
            self.Wrappers.append(self.Bindings.Bind(callback, flag, name, self.CollectionName))

    def __SyncVisible(self, button, row):
        """ 可见性绑定的回调: 先问启用开关, 再问按钮自己 """
        if self._enabled_resolver is not None:
            try:
                if not self._enabled_resolver(button.Prefix):
                    return False
            except Exception as e:  # noqa
                logger.error("[MEI/action] {} 问启用状态失败: {}".format(button.Prefix, error_text(e)))
        return button.ResolveVisible(row, self.__RecipeOf(row))

    def __SyncState(self, button, row):
        """
        状态绑定的回调, 兼作**每帧心跳**: 算出应有状态, 变了就推给控件.

        为什么要推而不只是返回: 见 SetControlResolver 的说明 —— 返回值这条路
        走不通。返回值仍然照给, 万一某个版本它是通的就白赚。

        **只在值变化时才碰控件** —— 这是每帧路径, GetChildByPath + asSwitchToggle
        不便宜; 缓存上次推过的值, 没变就一个引擎调用都不做。
        """
        recipe = self.__RecipeOf(row)
        # 翻页后每页行数不同, 引擎仍会为上一页的行下标求值一帧 —— 那一行没有配方,
        # 自然也没有状态要推. 不拦的话每次翻页都刷一串"暂时取不到控件".
        # 判 _row_resolver 非空是为了不影响"不注入 resolver 时按钮仍可用"那条离线路径
        if recipe is None and self._row_resolver is not None:
            return False

        desired = button.ResolveState(row, recipe)
        cache_key = (row, button.Prefix)
        if self._pushed.get(cache_key) != desired:
            # **先记再推**：SetToggleState 的回灌要是当场就到，也得认得出是自己的回声（「推上去才记」的话
            # 整个配方页无限闪烁 —— 置顶的回灌漏过去 → 重排 → 重建 → 再推 → 再回灌）
            previous = self._pushed.get(cache_key, _UNSET)
            self._pushed[cache_key] = desired
            if not self.__PushState(button, row, desired):
                # 没推上去（行还没接上配方页脚本）：撤回，下一帧再推 ——
                # 记着「推过」的话这一行就再也不补推，收藏 / 置顶过的按钮停在未选中
                if previous is _UNSET:
                    self._pushed.pop(cache_key, None)
                else:
                    self._pushed[cache_key] = previous
        return desired

    def __PushState(self, button, row, on):  # type: (any, int, bool) -> bool
        """
        直接把选中态写给控件，返回「这个状态算处理完了没有」：拿不到控件（行还没接上是常态）给 False，下一帧再推；
        推成了、或者推不了也不会好（控件不是 toggle、推的时候抛了：只记一行）给 True，免得每帧重试刷屏
        """
        try:
            control = self.__ControlOf(button, row)
            if not control:
                return False
            toggle = control.asSwitchToggle()
            if not toggle:
                logger.error("[MEI/action] {} 行 {} 的控件不是 toggle, 拿不到 asSwitchToggle".format(
                    button.Prefix, row))
                return True
            toggle.SetToggleState(bool(on))
        except Exception as e:  # noqa  推状态失败不能拖垮整帧
            logger.error("[MEI/action] {} 行 {} 推状态失败: {}".format(
                button.Prefix, row, error_text(e)))
        return True

    def __ControlOf(self, button, row):
        """ 取按钮控件: 行控件 + 相对路径, 结果缓存(这是每帧路径) """
        cache_key = (row, button.Prefix)
        if cache_key in self._controls:
            return self._controls[cache_key]

        path = button.Path
        if path is None and self._path_resolver is not None:
            path = self._path_resolver(button.Prefix)
        if not path or self._control_resolver is None:
            return None

        row_control = self._control_resolver(row)
        if not row_control:
            # 行还没接上（配方页脚本在下一帧的 Tick 里接）：常态，安静跳过，下一帧再问
            return None
        control = row_control.GetChildByPath(path)
        if not control:
            # 行在、按钮取不到：多半是路径写错了。每个 (行, 动作) 只记一次 —— 这是每帧路径, 不能刷屏;
            # **不进缓存**: 行控件是懒建的, 这一帧没有不代表下一帧没有
            if cache_key not in self._path_warned:
                self._path_warned.add(cache_key)
                logger.info("[MEI/action] {} 行 {} 暂时取不到控件({})".format(
                    button.Prefix, row, path))
            return None

        self._controls[cache_key] = control
        return control

    def __RecipeOf(self, row):
        if self._row_resolver is None:
            return None
        try:
            return self._row_resolver(row)
        except Exception as e:  # noqa
            logger.error("[MEI/action] 解析第 {} 行的配方失败: {}".format(row, error_text(e)))
            return None

    def __Dispatch(self, button, args):
        """
        交互回调. 行号来自 args["index"] —— 引擎随事件投递的集合下标,
        因为基类是集合感知的 switch_toggle_collection(见模块 docstring)。
        """
        args = args or {}
        row = args.get("index")
        state = bool(args.get("state"))
        if row is None:
            logger.error("[MEI/action] {} 的交互回调没有 index, args={!r}".format(
                button.Prefix, args))
            return

        # SetToggleState 会被引擎当成一次状态变化**回灌**到这里. 上报值与刚推下去的
        # 一致就是自己的回声, 不是玩家操作 —— 必须吞掉, 否则:
        #   · 回声带着 state=False 进 star 回调, 会把已收藏的行悄悄取消收藏;
        #   · 若某个动作的回调会重建行控件(top 就是), 重建 -> 失效推送缓存 -> 再推
        #     -> 再回灌, 就是一个每帧都在跑的死循环(表现是 TypeTab 与
        #     工作站格全部消失, 日志每帧一条).
        # 判"值相同"而不是加时序标志: 回灌是下一帧才到的, 同步标志盖不住.
        if self._pushed.get((row, button.Prefix)) == state:
            return

        # 回声第二道: 上报的值和这一行此刻的业务状态一样 = 什么都不用改 —— 自己推下去的回灌, 或者控件慢了一拍.
        # 不靠推送缓存: 缓存会被重建清掉(置顶的回调就会重建), 回灌赶在清缓存之后到, 第一道就认不出来,
        # 漏过去就是「重排 → 重建 → 再推 → 再回灌」的死循环(整页无限闪烁). 无状态按钮没有业务状态, 不在这里判
        recipe = self.__RecipeOf(row)
        if not button.Momentary and button.GetState is not None and button.ResolveState(row, recipe) == state:
            return

        # 无实现的动作直接吞掉. 正常情况下它压根不该被点到(ResolveVisible 会隐藏它),
        # 但**可见性绑定是 UI 侧的事, 不能拿它当唯一防线** ——
        # 可见性没生效时四个未实现的按钮全部可点, 每次点击都
        # `'NoneType' object is not callable`. 判空放在这里才是兜得住的那一层.
        if button.OnAction is None:
            return

        # 无状态按钮只认"被按亮"那一次, 弹回时不重复触发
        if button.Momentary and not state:
            return

        context = ActionContext(
            prefix=button.Prefix,
            row=row,
            recipe=recipe,
            state=state,
            binder=self,
        )
        try:
            button.OnAction(context)
        except Exception as e:  # noqa  开发者的回调炸了不能把界面带崩
            logger.error("[MEI/action] {} 的回调失败(行 {}): {}".format(
                button.Prefix, row, error_text(e)))

        # **必须返回 Refresh** —— 官方 toggle 示例就是这么写的.
        # 回调改完业务状态后, 要让引擎重新回读 $toggle_state_binding_name,
        # 否则按钮显示的是它自己的内部状态, 而不是代码算出来的那个.
        return VIEW_REQUEST_REFRESH
