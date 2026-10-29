# coding=utf-8

# ----------------------------------------------------------------------
#  binding.py is part of MoreEnoughItems.
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

import re
import types
import uuid

import mod.client.extraClientApi as clientApi
from mod_log import logger

# 包内同级引用走**子模块路径**, 不吃 modules/__init__ 的再导出 ——
# __init__ 正在导入 binding 时 click 这个名字可能尚未绑定 (engineering.md §9-3)
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.click import (
    BUTTON_PRIMARY, BUTTON_SECONDARY, SlotClickContext, GetPolicy,
)
from MEIScripts.mei_mod.ui_script.controls.item.panel import panel_controls
from MEIScripts.mei_mod.ui_script.proxy.focus.search import contains, control_rect
from MEIScripts.utils import utilities
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.bindname import make_binding_name
from MEIScripts.utils.text import error_text

ViewBinder = clientApi.GetViewBinderCls()

KIND_ATTR = "attr"
""" 普通属性绑定: 回调签名 fn(collection_index), 走 GetBindingValue """

KIND_CLICK = "click"
""" 点击绑定: 回调签名 fn(args), 拿不到 collection_index, 行号只能从路径解 """


class RecipeBinder(object):
    """装饰器与自动初始化入口，统一管理配方脚本中的声明式绑定。"""

    _RULES_ATTR = "__recipe_binder_rules__"
    _DEFAULT_RECIPES_COLLECTION = "__recipes_grid_default__"
    _RULES_CACHE = {}

    @staticmethod
    def __PushRule(func, rule):
        rules = func.__dict__.get(RecipeBinder._RULES_ATTR)
        if rules is None:
            rules = []
            func.__dict__[RecipeBinder._RULES_ATTR] = rules
        rules.append(rule)

    @staticmethod
    def Group(prefix_list, cache_enabled=True):
        """ 声明一个 AddGroup 规则，回调函数签名为: fn(self, prefix_index) """
        def _decorator(func):
            RecipeBinder.__PushRule(func, {
                "kind": "group",
                "prefix_list": prefix_list,
                "cache_enabled": bool(cache_enabled),
            })
            return func
        return _decorator

    @staticmethod
    def Binding(binding_name, bind_flag, collection_name=None, index=None):
        """ 声明一个按 index 绑定规则，回调函数签名为: fn(self, collection_index, index) """
        def _decorator(func):
            RecipeBinder.__PushRule(func, {
                "kind": "index_binding",
                "binding_name": binding_name,
                "bind_flag": bind_flag,
                "collection_name": collection_name,
                "index": index,
            })
            return func
        return _decorator

    @staticmethod
    def __GetRules(script_cls):
        cached = RecipeBinder._RULES_CACHE.get(script_cls)
        if cached is not None:
            return cached

        rules = []
        for cls in reversed(script_cls.mro()):
            if cls is object:
                continue

            for method_name, value in cls.__dict__.items():
                if isinstance(value, staticmethod) or isinstance(value, classmethod):
                    func = value.__func__
                elif callable(value):
                    func = value
                else:
                    continue

                if not hasattr(func, "__dict__"):
                    continue

                declared_rules = func.__dict__.get(RecipeBinder._RULES_ATTR)
                if not declared_rules:
                    continue

                for declared in declared_rules:
                    rule = dict(declared)
                    rule["method_name"] = method_name
                    rules.append(rule)

        RecipeBinder._RULES_CACHE[script_cls] = rules
        return rules

    @staticmethod
    def __ResolvePrefixList(script_ins, raw):
        value = raw
        if callable(value):
            value = value(script_ins)
        elif isinstance(value, basestring) and hasattr(script_ins, value):
            method = object.__getattribute__(script_ins, value)  # noqa
            if callable(method):
                value = method()

        if not isinstance(value, (list, tuple)):
            raise TypeError("prefix_list must be list or tuple")

        prefix_list = []
        for prefix in value:
            if not isinstance(prefix, basestring):
                raise TypeError("prefix_list element must be string")
            if not prefix:
                raise ValueError("prefix cannot be empty")
            prefix_list.append(prefix)

        if not prefix_list:
            raise ValueError("prefix_list cannot be empty")

        return prefix_list

    @staticmethod
    def __ResolveIndexes(script_ins, raw):
        value = raw
        if callable(value):
            value = value(script_ins)

        if value is None:
            return [script_ins.GridItemIndex]
        if isinstance(value, int):
            return [value]
        if isinstance(value, (list, tuple)):
            indexes = []
            for index in value:
                if not isinstance(index, int):
                    raise TypeError("index list element must be int")
                indexes.append(index)
            if not indexes:
                raise ValueError("index list cannot be empty")
            return indexes

        raise TypeError("index must be int/list/tuple/callable/None")

    @staticmethod
    def InitBindings(script_ins):
        grid_bind = script_ins.RecipesGridBind
        if not grid_bind:
            return

        if not hasattr(script_ins, "_AutoBindingGroupIds"):
            script_ins._AutoBindingGroupIds = []
        if not hasattr(script_ins, "_AutoIndexedBindingKeys"):
            script_ins._AutoIndexedBindingKeys = []

        rules = RecipeBinder.__GetRules(script_ins.__class__)
        if not isinstance(rules, list):
            raise TypeError("rules must be list")

        for rule in rules:
            method = object.__getattribute__(script_ins, rule["method_name"])
            kind = rule["kind"]

            if kind == "group":
                prefix_list = RecipeBinder.__ResolvePrefixList(script_ins, rule["prefix_list"])
                group_id = grid_bind.AddGroup(
                    collection_index=script_ins.GridItemIndex,
                    prefix_list=prefix_list,
                    item_panel_callback=method,
                    cache_enabled=rule["cache_enabled"],
                )
                script_ins._AutoBindingGroupIds.append(group_id)  # noqa
            elif kind == "index_binding":
                collection_name = rule["collection_name"]
                if collection_name is None:
                    collection_name = RecipeBinder._DEFAULT_RECIPES_COLLECTION

                for index in RecipeBinder.__ResolveIndexes(script_ins, rule["index"]):
                    key = grid_bind.AddIndexedBinding(
                        binding_name=rule["binding_name"],
                        bind_flag=rule["bind_flag"],
                        callback=method,
                        ins=script_ins,
                        index=index,
                        collection_name=collection_name,
                        owner=script_ins,
                    )
                    script_ins._AutoIndexedBindingKeys.append(key)  # noqa

    @staticmethod
    def DestroyBindings(script_ins):
        grid_bind = script_ins.RecipesGridBind
        if not grid_bind:
            return

        auto_group_ids = list(getattr(script_ins, "_AutoBindingGroupIds", []))
        for group_id in auto_group_ids:
            grid_bind.RemoveGroup(script_ins.GridItemIndex, group_id)

        auto_index_keys = list(getattr(script_ins, "_AutoIndexedBindingKeys", []))
        for key in auto_index_keys:
            grid_bind.RemoveIndexedBindingByKey(key)

        script_ins._AutoBindingGroupIds = []
        script_ins._AutoIndexedBindingKeys = []


class RecipesGridBind(object):
    """
    统一管理 recipes_grid 的 prefix 绑定, 用于批量绑定ItemPanel属性
    """

    ROW_PATH_RE_TEMPLATE = r"/{}(\d+)(?:/|$)"
    """ 从按钮路径里抠行号用. 行子控件名由构造参数给出 """

    def __init__(self, screen_node, collection_name, row_child_name="recipe"):
        self.Bindings = ScreenBinder(screen_node)  # type: ScreenBinder
        self.CollectionName = collection_name

        # 行子控件名. 与 recipe_details/script.py 造控件时的 "/recipe{}" 必须一致 ——
        # 点击绑定拿不到 collection_index, 行号只能从按钮路径里解出来.
        # 第三方换配方页模板时可覆盖.
        self.RowChildName = row_child_name
        self._row_re = re.compile(self.ROW_PATH_RE_TEMPLATE.format(re.escape(row_child_name)))

        self.BindingWrappers = {}  # type: dict
        self.BindingConfigs = {}  # type: dict
        self.RegisteredPrefixes = set()  # type: set

        # {collection_index: {group_id: {"prefix_list": list, "prefix_to_index": dict, "callback": callable, "cache_enabled": bool}}}
        self.RecipeGroups = {}  # type: dict

        # {(collection_index, group_id, prefix_index): ItemPanel}
        self.ItemPanels = {}  # type: dict

        # {collection_index: {prefix: (group_id, prefix_index) or None(冲突)}}
        self.PrefixContextByCollection = {}  # type: dict
        # {(collection_index, group_id): set((collection_index, group_id, prefix_index))}
        self.GroupPanelKeys = {}  # type: dict
        # {collection_index: set((collection_index, group_id, prefix_index))}
        self.CollectionPanelKeys = {}  # type: dict
        # {collection_index: int}
        self.PanelCountByCollection = {}  # type: dict

        # {(collection_name, binding_name, bind_flag, index, owner_token): wrapper}
        self.IndexedBindingWrappers = {}  # type: dict
        self.IndexedBindingConfigs = {}  # type: dict
        self.OwnerIndexedBindingKeys = {}  # type: dict

        self.SaturatedCollectionIndexes = set()  # type: set

    def __RebuildPrefixContext(self, collection_index):
        groups = self.RecipeGroups.get(collection_index)
        if not groups:
            self.PrefixContextByCollection.pop(collection_index, None)
            return

        context_map = {}
        for group_id, group in groups.items():
            for prefix, prefix_index in group.get("prefix_to_index", {}).items():
                if prefix in context_map:
                    context_map[prefix] = None
                else:
                    context_map[prefix] = (group_id, prefix_index)

        self.PrefixContextByCollection[collection_index] = context_map

    def __IsGroupCounted(self, collection_index, group_id):
        """
        该组的面板是否计入配额.

        cache_enabled=False 的语义是「**不参与配额管理**」——
        既不计入 PanelCountByCollection, 也不受上限限制.
        只不计入**上限**却照样占用计数的话, 混用时
        disabled 组会吃掉 enabled 组的配额、导致后者的槽位永远建不出来(空白).
        """
        group = self.RecipeGroups.get(collection_index, {}).get(group_id)
        return bool(group and group.get("cache_enabled"))

    def __AddPanelIndex(self, key):
        collection_index, group_id, _ = key

        group_keys = self.GroupPanelKeys.setdefault((collection_index, group_id), set())
        group_keys.add(key)

        collection_keys = self.CollectionPanelKeys.setdefault(collection_index, set())
        collection_keys.add(key)

        if not self.__IsGroupCounted(collection_index, group_id):
            return
        self.PanelCountByCollection[collection_index] = self.PanelCountByCollection.get(collection_index, 0) + 1

    def __RemovePanelIndex(self, key):
        collection_index, group_id, _ = key

        group_key = (collection_index, group_id)
        group_keys = self.GroupPanelKeys.get(group_key)
        if group_keys:
            group_keys.discard(key)
            if not group_keys:
                del self.GroupPanelKeys[group_key]

        collection_keys = self.CollectionPanelKeys.get(collection_index)
        if collection_keys:
            collection_keys.discard(key)
            if not collection_keys:
                del self.CollectionPanelKeys[collection_index]

        if not self.__IsGroupCounted(collection_index, group_id):
            return
        count = self.PanelCountByCollection.get(collection_index, 0)
        if count <= 1:
            self.PanelCountByCollection.pop(collection_index, None)
        else:
            self.PanelCountByCollection[collection_index] = count - 1

    @staticmethod
    def _DestroyPanel(panel):
        """
        拆一个面板。**`Destroy` 是可选的** —— 面板契约的必需面是
        「绑定要读的那几个属性」，不是一整套 ItemPanel。

        拆除跑在重建配方页的路径上(ClearUICache -> DestroyBindings)，
        而那条路径又是从绑定/点击回调里进来的 ——
        在这里抛 AttributeError 会把那条绑定当场带走且引擎不给日志
        (引擎结论 §15)，表现是“切个 TypeTab 整页就死了”。
        第三方的面板可能没写 Destroy(比如蔚蓝的电力条), 不兜着的话一切页就炸。
        """
        destroy = getattr(panel, "Destroy", None)
        if not callable(destroy):
            return
        try:
            destroy()
        except Exception as e:  # noqa  一个面板拆不掉不能卡住整页重建
            logger.error("[MEI/ui] 面板 Destroy 抛异常: {}".format(error_text(e)))

    def __DestroyPanelByKey(self, key):
        panel = self.ItemPanels.pop(key, None)
        if panel:
            self._DestroyPanel(panel)
            self.__RemovePanelIndex(key)
            return True
        return False

    @staticmethod
    def __BindCallbackToInstance(callback, ins):
        if ins is None:
            return callback

        if isinstance(callback, types.MethodType):
            original = callback.im_func if hasattr(callback, "im_func") else callback
            return types.MethodType(original, ins, type(ins))  # type: ignore

        return types.MethodType(callback, ins, type(ins))  # type: ignore

    @staticmethod
    def __BuildIndexedBindingName(binding_name, index):
        if "{index}" in binding_name:
            return binding_name.format(index=index)
        return binding_name

    @staticmethod
    def __BuildOwnerToken(owner):
        if owner is None:
            return ""
        return "owner_{}".format(id(owner))

    def AddIndexedBinding(
            self,
            binding_name,
            bind_flag,
            callback,
            ins=None,
            index=0,
            collection_name=None,
            owner=None,
    ):
        """按 index 注册普通/集合绑定，支持重复注册去重和生命周期管理。"""
        if not isinstance(binding_name, basestring):
            raise TypeError("binding_name must be string")
        if not binding_name:
            raise ValueError("binding_name cannot be empty")
        if not isinstance(index, int):
            raise TypeError("index must be int")
        if collection_name is not None and collection_name == RecipeBinder._DEFAULT_RECIPES_COLLECTION:  # noqa
            collection_name = self.CollectionName
        if collection_name is not None and not isinstance(collection_name, basestring):
            raise TypeError("collection_name must be string or None")
        if not callable(callback):
            raise TypeError("callback must be callable")

        callback = self.__BindCallbackToInstance(callback, ins)

        real_binding_name = self.__BuildIndexedBindingName(binding_name, index)
        owner_token = self.__BuildOwnerToken(owner)

        key = (
            collection_name if collection_name else "",
            real_binding_name,
            bind_flag,
            index,
            owner_token,
        )

        exists = self.IndexedBindingWrappers.get(key)
        if exists:
            return key

        if collection_name:
            def _collection_callback(collection_index):
                return callback(collection_index, index)

            wrapper = self.Bindings.Bind(_collection_callback, bind_flag, real_binding_name, collection_name)
        else:
            def _control_callback():
                return callback(None, index)

            wrapper = self.Bindings.Bind(_control_callback, bind_flag, real_binding_name)

        self.IndexedBindingWrappers[key] = wrapper
        self.IndexedBindingConfigs[key] = {
            "binding_name": real_binding_name,
            "bind_flag": bind_flag,
            "index": index,
            "collection_name": collection_name,
            "owner_token": owner_token,
        }

        if owner_token:
            keys = self.OwnerIndexedBindingKeys.setdefault(owner_token, set())
            keys.add(key)

        return key

    def RemoveIndexedBindingByKey(self, key):
        wrapper = self.IndexedBindingWrappers.pop(key, None)
        config = self.IndexedBindingConfigs.pop(key, None)
        if not wrapper:
            return False

        self.Bindings.Unbind(wrapper)

        if config:
            owner_token = config.get("owner_token")
            if owner_token and owner_token in self.OwnerIndexedBindingKeys:
                self.OwnerIndexedBindingKeys[owner_token].discard(key)
                if not self.OwnerIndexedBindingKeys[owner_token]:
                    del self.OwnerIndexedBindingKeys[owner_token]

        return True

    def RemoveIndexedBinding(
            self,
            binding_name,
            bind_flag,
            index=0,
            collection_name=None,
            owner=None,
    ):
        if collection_name is not None and collection_name == RecipeBinder._DEFAULT_RECIPES_COLLECTION:  # noqa
            collection_name = self.CollectionName

        owner_token = self.__BuildOwnerToken(owner)
        key = (
            collection_name if collection_name else "",
            self.__BuildIndexedBindingName(binding_name, index),
            bind_flag,
            index,
            owner_token,
        )
        return self.RemoveIndexedBindingByKey(key)

    def RemoveIndexedBindingsByOwner(self, owner):
        owner_token = self.__BuildOwnerToken(owner)
        keys = self.OwnerIndexedBindingKeys.get(owner_token)
        if not keys or not isinstance(keys, set):
            return

        for key in list(keys):
            self.RemoveIndexedBindingByKey(key)

    def ClearIndexedBindings(self):
        for key in list(self.IndexedBindingWrappers.keys()):
            self.RemoveIndexedBindingByKey(key)

    def _get_base_binding_configs(self):
        configs = utilities.GetItemPanelBindingConfigs()
        for config in configs:
            config["kind"] = KIND_ATTR
        configs.insert(0, {
            "suffix": ".visible",
            "flag": ViewBinder.BF_BindBool,
            "resolver": self.__EnsureItemPanelVisible,
            "default": True,
            "kind": KIND_ATTR,
        })
        # 点击绑定. 绑定名与 mei_common.item_panel 里
        # $overlay_btn_primary_click_binding_name 的构造完全一致 ——
        # JSON 侧早就声明好了(含 button_mappings), 一直缺的只是这里的注册.
        configs.append({
            "suffix": ".overlay.btn.click_" + self.CollectionName,
            "flag": ViewBinder.BF_ButtonClickUp,
            "kind": KIND_CLICK,
            "button": BUTTON_PRIMARY,
            "can_pause": False,   # 面板缓存饱和后仍要能点
        })
        configs.append({
            "suffix": ".overlay.btn.right_click_" + self.CollectionName,
            "flag": ViewBinder.BF_ButtonClickUp,
            "kind": KIND_CLICK,
            "button": BUTTON_SECONDARY,
            "can_pause": False,
        })
        return configs

    def __EnsureBindingsForPrefix(self, prefix):
        if prefix in self.RegisteredPrefixes:
            return

        for base_config in self._get_base_binding_configs():
            config = dict(base_config)
            binding_name = make_binding_name(prefix, config["suffix"])
            config["name"] = binding_name
            config["prefix"] = prefix

            if config.get("kind") == KIND_CLICK:
                # 点击回调签名是 fn(args), 且必须闭包住 prefix ——
                # 引擎不给 collection_index, 槽位身份只能靠"是哪条绑定被触发"来确定
                callback = self.__CreateClickCallback(prefix, config["button"])
            else:
                callback = self.__CreateBindingCallback(binding_name)

            # 点击类（BF_ButtonClickUp）只能普通绑定，集合绑定会「注册成功、引擎永不投递」——
            # ScreenBinder 按 flag 分流（引擎结论 §9）
            wrapper = self.Bindings.Bind(callback, config["flag"], binding_name, self.CollectionName)
            self.BindingWrappers[binding_name] = wrapper
            self.BindingConfigs[binding_name] = config

        self.RegisteredPrefixes.add(prefix)

    def AddGroup(self, collection_index, prefix_list, item_panel_callback, cache_enabled=True):
        if not isinstance(collection_index, int):
            raise TypeError("collection_index must be int")
        if not isinstance(prefix_list, (list, tuple)):
            raise TypeError("prefix_list must be list or tuple")
        if not prefix_list:
            raise ValueError("prefix_list cannot be empty")
        if not callable(item_panel_callback):
            raise TypeError("item_panel_callback must be callable")

        normalized = []
        for prefix in prefix_list:
            if not isinstance(prefix, basestring):
                raise TypeError("prefix_list element must be string")
            if not prefix:
                raise ValueError("prefix cannot be empty")
            normalized.append(prefix)
            self.__EnsureBindingsForPrefix(prefix)

        group_id = uuid.uuid4().hex
        groups = self.RecipeGroups.setdefault(collection_index, {})
        groups[group_id] = {
            "prefix_list": normalized,
            "prefix_to_index": {prefix: i for i, prefix in enumerate(normalized)},
            "callback": item_panel_callback,
            "cache_enabled": bool(cache_enabled),
        }
        self.__RebuildPrefixContext(collection_index)
        self.__RefreshSaturatedState(collection_index)
        return group_id

    def RemoveGroup(self, collection_index, group_id):
        groups = self.RecipeGroups.get(collection_index)
        if not groups or group_id not in groups:
            return

        self.__ClearPanelsByGroup(collection_index, group_id)
        del groups[group_id]
        if not groups:
            del self.RecipeGroups[collection_index]
            self.PrefixContextByCollection.pop(collection_index, None)
        else:
            self.__RebuildPrefixContext(collection_index)
        self.__RefreshSaturatedState(collection_index)

    def RemoveGroupByIndex(self, collection_index):
        groups = self.RecipeGroups.get(collection_index)
        if not groups:
            return

        for key in list(self.CollectionPanelKeys.get(collection_index, ())):
            self.__DestroyPanelByKey(key)

        del self.RecipeGroups[collection_index]
        self.PrefixContextByCollection.pop(collection_index, None)
        self.__RefreshSaturatedState(collection_index)

    def TickPanels(self, ticks):  # type: (int) -> None
        """
        把配方页的渲染节拍转给自己持有的面板。

        **写在这里而不是让 script 去遍历 `ItemPanels`**：面板的生命周期归本类
        （懒建、配额上限、`ClearCache` 里销毁），拿节拍这件事也该由持有者转发，
        不然 script 就要伸手进来读私有缓存。

        **不给 `ItemPanel` 加契约**: 只有轮播面板需要推进, 用 `getattr` 挑出来即可。
        在导出给第三方的控件基类上铸一条与 `BaseRecipeUIScript.OnAnimTick` 同名的契约,
        会让"同一个名字在两层各有一份语义", 得不偿失。
        """
        for panel in self.ItemPanels.values():
            rotate = getattr(panel, "Rotate", None)
            if not callable(rotate):
                continue
            # 与脚本侧同一条: 第一拍只对表, 让 ticks 相对面板自己出生的时刻。
            # 不对表的话, 中途建出来的槽位会撞上任意相位 -> 第一次轮播提前
            if panel.AnimBase is None:
                panel.AnimBase = ticks
                continue
            try:
                rotate(ticks - panel.AnimBase)
            except Exception as e:  # noqa  一个面板炸了不能停掉整页的节拍
                logger.error("[MEI/ui] 面板轮播抛异常: {}".format(error_text(e)))

    def PanelAt(self, x, y):  # type: (float, float) -> any
        """
        这一点落在本绑定器的哪个槽位面板上（显示着物品的），没有返回 None。
        配方页的槽位不在 ItemsGrid 里，UIScriptMain.PanelAt 认物品栏、收藏栏之外还要问这里
        """
        for panel in self.ItemPanels.values():
            if getattr(panel, "Item", None) is None:
                continue
            for control in panel_controls(panel):  # 镜像格（酿造台下面三瓶）也算这一格
                rect = control_rect(control)
                if rect is not None and contains(rect, x, y):
                    return panel
        return None

    def ClearCache(self):
        for _, panel in self.ItemPanels.items():
            self._DestroyPanel(panel)
        self.ItemPanels = {}
        self.GroupPanelKeys = {}
        self.CollectionPanelKeys = {}
        self.PanelCountByCollection = {}
        self.SaturatedCollectionIndexes = set()

    def Destroy(self):
        self.ClearCache()
        self.ClearIndexedBindings()
        for _, wrapper in list(self.BindingWrappers.items()):
            self.Bindings.Unbind(wrapper)
        self.BindingWrappers = {}
        self.BindingConfigs = {}
        self.RegisteredPrefixes = set()
        self.RecipeGroups = {}
        self.PrefixContextByCollection = {}

        self.IndexedBindingWrappers = {}
        self.IndexedBindingConfigs = {}
        self.OwnerIndexedBindingKeys = {}

    def __ClearPanelsByGroup(self, collection_index, group_id):
        group_key = (collection_index, group_id)
        for key in list(self.GroupPanelKeys.get(group_key, ())):
            self.__DestroyPanelByKey(key)

    def __CreateBindingCallback(self, binding_name):
        def _callback(collection_index):
            return self.GetBindingValue(collection_index, binding_name)
        return _callback

    def __CreateClickCallback(self, prefix, button):
        def _callback(args):
            return self._DispatchSlotClick(prefix, button, args)
        return _callback

    def _ParseRowFromPath(self, btn_path):  # type: (str) -> int or None
        """
        从按钮路径里取出行号(0-based).

        为什么只能这么取: BF_ButtonClickUp **根本不能做集合绑定**(官方绑定方式表:
        按钮类仅支持 binding), 所以回调里压根没有 collection_index 这个东西 ——
        对照 ItemsGrid.PrimaryClickHandler, 它同样是解 args["ButtonPath"].
        而槽位身份不必从路径解 —— 每个 prefix 有自己的点击绑定, 回调已闭包住它.
        JSON 侧行子控件是 recipe1 起算, 故减 1.
        """
        if not btn_path:
            return None
        match = self._row_re.search(btn_path)
        if not match:
            return None
        try:
            row = int(match.group(1)) - 1
        except ValueError:
            return None
        return row if row >= 0 else None

    def _DispatchSlotClick(self, prefix, button, args):
        """
        解出 (行, 组, 组内序号) 与被点中的面板, 交给可替换的点击策略.

        三个失败出口都**留日志**: 点击是低频的用户动作, 不存在刷屏风险;
        而"点了没反应"这个症状在没有日志时完全无法区分是哪一段断的
        (绑定没投递 / 路径形态不符 / 上下文没建 / 面板没建).
        """
        btn_path = (args or {}).get("ButtonPath")
        row = self._ParseRowFromPath(btn_path)
        if row is None:
            logger.error(
                "[MEI/click] 行号解析失败 prefix={} button={} 期望路径含 /{}N/ "
                "实际 ButtonPath={!r}".format(
                    prefix, button, self.RowChildName, btn_path))
            return

        context = self.__FindGroupContext(row, prefix)
        if not context:
            logger.error("[MEI/click] 找不到组上下文 row={} prefix={}".format(row, prefix))
            return
        group_id, _group, ordinal = context

        panel = self.ItemPanels.get((row, group_id, ordinal))
        if not panel:
            logger.error("[MEI/click] 面板未建 addr=({}, {}, {})".format(row, group_id, ordinal))
            return

        self._OnSlotClick(SlotClickContext(
            button=button,
            panel=panel,
            item=getattr(panel, "Item", None),   # 轮播面板给的是**当前显示**的那个
            row=row,
            group_id=group_id,
            ordinal=ordinal,
            binder=self,
        ))

    def _OnSlotClick(self, ctx):  # type: (SlotClickContext) -> None
        """ 点了一格：缺省交给全局的点击策略（modules/click.py）。配方树菜单里的预览覆写成自己的（recipe_tree/controls/preview.py）"""
        GetPolicy().OnSlotClick(ctx)

    def __FindGroupContext(self, collection_index, prefix):
        context_map = self.PrefixContextByCollection.get(collection_index)
        if context_map is not None:
            fast_context = context_map.get(prefix)
            if fast_context is not None:
                group_id, prefix_index = fast_context
                group = self.RecipeGroups.get(collection_index, {}).get(group_id)
                if group is not None:
                    return group_id, group, prefix_index

        groups = self.RecipeGroups.get(collection_index)
        if not groups:
            return None

        for group_id, group in groups.items():
            prefix_index = group["prefix_to_index"].get(prefix)
            if prefix_index is not None:
                return group_id, group, prefix_index
        return None

    def GetBindingValue(self, collection_index, binding_name):
        config = self.BindingConfigs.get(binding_name)
        if not config:
            return False

        prefix = config.get("prefix")
        context = self.__FindGroupContext(collection_index, prefix)
        if not context:
            if config.get("suffix") == ".visible":
                return False
            return config.get("default")

        group_id, _, prefix_index = context

        resolver = config.get("resolver")
        if resolver:
            return resolver(collection_index, group_id, prefix_index)

        key = (collection_index, group_id, prefix_index)
        panel = self.ItemPanels.get(key)
        if not panel:
            return config.get("default")

        attr_name = config.get("attr")
        if not attr_name:
            return config.get("default")

        return getattr(panel, attr_name, config.get("default"))

    def __GetCollectionCacheLimit(self, collection_index):
        groups = self.RecipeGroups.get(collection_index)
        if not groups:
            return None

        limit = 0
        enabled = False
        for group in groups.values():
            if group.get("cache_enabled"):
                enabled = True
                limit += len(group.get("prefix_list", []))

        if not enabled:
            return None
        return limit

    def __CountPanelsByCollection(self, collection_index):
        return self.PanelCountByCollection.get(collection_index, 0)

    def __RefreshSaturatedState(self, collection_index):
        limit = self.__GetCollectionCacheLimit(collection_index)
        if limit is None:
            self.SaturatedCollectionIndexes.discard(collection_index)
            return

        if self.__CountPanelsByCollection(collection_index) >= limit:
            self.SaturatedCollectionIndexes.add(collection_index)
        else:
            self.SaturatedCollectionIndexes.discard(collection_index)

    def __CanCreateItemPanel(self, collection_index):
        self.__RefreshSaturatedState(collection_index)
        return collection_index not in self.SaturatedCollectionIndexes

    def __EnsureItemPanelVisible(self, collection_index, group_id, prefix_index):
        key = (collection_index, group_id, prefix_index)
        if key in self.ItemPanels:
            return True

        # 不参与配额管理的组(cache_enabled=False)不受上限限制, 见 __IsGroupCounted
        if (self.__IsGroupCounted(collection_index, group_id)
                and not self.__CanCreateItemPanel(collection_index)):
            return True

        groups = self.RecipeGroups.get(collection_index)
        if not groups:
            return False

        group = groups.get(group_id)
        if not group:
            return False

        panel = group["callback"](prefix_index)
        if not panel:
            # **不能 raise**: 这里是绑定回调的内部, 抛出去会把那条绑定当场带走
            # 且引擎不给日志(引擎结论 §15) —— 表现是"那一格永远不显示",
            # 与"这条配方本来就没那一格"完全一样, 没有任何排查线索。
            # 记一条再返回 False(那一格不可见), 让写错的人看得见。
            logger.error(
                "[MEI/ui] 槽位回调没有返回面板 addr=({}, {}, {}) —— "
                "回调必须返回一个面板对象(带绑定要读的属性), 空格请返回 "
                "ItemPanel.from_empty(control)".format(
                    collection_index, group_id, prefix_index))
            return False

        self.ItemPanels[key] = panel
        self.__AddPanelIndex(key)
        self.__RefreshSaturatedState(collection_index)
        return True


