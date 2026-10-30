# coding=utf-8

# ----------------------------------------------------------------------
#  items.py is part of MoreEnoughItems.
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
from mod_log import logger

from MEIScripts.common.classes.types import Item, ItemInfo, ItemAttr, ItemSpec
from MEIScripts.common.classes.types import keys
from MEIScripts.utils.sequence import dedupe
from MEIScripts.utils.text import error_text
from .organizer import ItemOrganizer

_BROWSABLE_CACHE_KEY = "default_visible_items"
""" GetBrowsableItems 的结果缓存键，沿用旧实现的键名 """

_ALL_CACHE_KEY = "all_items"
""" GetBrowsableItems(include_hidden=True) 的结果缓存键 """


class __ItemFactory(object):
    def __init__(self):
        self.__ItemComp = None

    def InitComps(self):
        self.__ItemComp = clientApi.GetEngineCompFactory().CreateItem(clientApi.GetLevelId())

    def LoadInfo(self, item_id, aux_value=0, enchanted=False):  # type: (str, int, bool) -> ItemInfo or None
        """
        问引擎一个物品的基本信息；引擎不认识（这个 id，或这个 aux）给 None。
        追加物品前先拿它核对：问到的交给 ItemSpec(info=...)，注册时就不再问第二次
        """
        if not self.__ItemComp:
            self.InitComps()
        info_dict = self.__ItemComp.GetItemBasicInfo(item_id, aux_value, enchanted)
        if not info_dict:
            return None
        return ItemInfo(
            id_aux=info_dict.get("id_aux", 0),
            item_name=info_dict.get("itemName", item_id),
            tags=info_dict.get("tags", []),
            item_type=info_dict.get("itemType"),
            category=info_dict.get("itemCategory"),
            max_durability=info_dict.get("maxDurability"),
            max_stack_size=info_dict.get("maxStackSize"),
            tier_dict=info_dict.get("tierDict"),
            item_tier_level=info_dict.get("itemTierLevel"),
            fuel_duration=info_dict.get("fuelDuration"),
            food_nutrition=info_dict.get("foodNutrition"),
            food_saturation=info_dict.get("foodSaturation"),
            weapon_damage=info_dict.get("weaponDamage"),
            armor_defense=info_dict.get("armorDefense"),
            armor_slot=info_dict.get("armorSlot"),
            armor_toughness=info_dict.get("armorToughness"),
            armor_knockback_resistance=info_dict.get("armorKnockbackResistance"),
            enchant_slot_type=info_dict.get("enchant_slot_type"),
        )

    def _LazyLoader(self, item, kind):  # type: (Item, str) -> any
        """ 注入到每个 Item 的惰性加载回调; kind ∈ {"info", "hover"} """
        if not self.__ItemComp:
            self.InitComps()
        try:
            if kind == "info":
                info = self.LoadInfo(item.ItemId, item.AuxValue, item.IsEnchanted)
                if info is None:
                    raise ValueError("cannot get basic info for item: {}".format(item.ItemId))
                return info
            if kind == "hover":
                item_id = item.ItemId
                aux_value = item.AuxValue
                user_data = item.Attr.UserData
                return self.__ItemComp.GetItemFormattedHoverText(
                    itemName=item_id,
                    auxValue=aux_value,
                    userData=user_data,
                    showCategory=False
                ) or ""
        except Exception as e:
            logger.warn("lazy load '{}' for '{}' failed: {}".format(kind, item.ItemId, error_text(e)))
        return None

    def GetItemStackFromItemDict(self, item_dict):
        """
        通过 ModSdk 标准的 ItemDict 构造一个 ItemStack
        """
        count = item_dict.get("count")
        item_id = item_dict.get("newItemName")
        aux_value = item_dict.get("newAuxValue")
        attr = ItemAttr(
            user_data=item_dict.get("userData"),
            show_in_hand=item_dict.get("showInHand"),
            enchant_data=item_dict.get("enchantData"),
            mod_enchant_data=item_dict.get("modEnchantData"),
            custom_tips=item_dict.get("customTips"),
            extra_id=item_dict.get("extraId"),
            durability=item_dict.get("durability"),
        )
        item = self.GetItem(ItemId=item_id, AuxValue=aux_value, Attr=attr)
        if not item:
            return None
        return item.stack(count=count)

    def GetItem(self, **kwargs):  # type: (any) -> Item or None
        """
        通过传入的数据获取一个Item实例 会自动解析 kwargs
        """
        item_id = kwargs.get('ItemId', "")
        return self.CreateItem(item_id, kwargs)

    def GetStacksFromIds(self, item_ids, count=1):  # type: (any, int) -> list
        """ 批量把 id 表变成 ItemStack 表，拿不到的跳过 """
        # 类别声明工作站时在模块顶层调用, 那时 id 表未必已到(离线探针就是这样).
        # 抛出去会让整个配方类型 import 失败 —— 少一个图标远好过一个类型加载不了
        stacks = []
        for item_id in item_ids or ():
            try:
                item = self.GetItem(ItemId=item_id)
            except Exception as e:  # noqa
                logger.warn("stack for '{}' unavailable: {}".format(item_id, error_text(e)))
                continue
            if item:
                stacks.append(item.stack(count))
        return stacks

    def CreateFromSpec(self, spec):  # type: (ItemSpec) -> Item
        """ 按 ItemSpec 造物；spec 自带 Info/HoverText 时**不问引擎** """
        # 自定义物品引擎根本不认识, GetItemBasicInfo 只会返回空 —— 必须允许自带.
        # 走 loader 而不是造完再塞字段: 造物只有 Item.__init__ 一条路, 不开第二条
        loader = self._LazyLoader
        if spec.Info is not None or spec.HoverText is not None:
            def _own_loader(item, kind):  # 自带的用自带的, 没自带的仍回落引擎
                if kind == "info" and spec.Info is not None:
                    return spec.Info
                if kind == "hover" and spec.HoverText is not None:
                    return spec.HoverText
                return self._LazyLoader(item, kind)
            loader = _own_loader

        return Item(
            item_id=spec.ItemId,
            aux_value=spec.AuxValue,
            attr=spec.Attr,
            extra_data=spec.ExtraData,
            loader=loader,
        )

    def CreateItem(self, item_id, dict_data):  # type: (str, dict) -> Item
        """
        显式参数构造 Item: 注册/渲染必需字段构造期填充,
        Info 与 HoverText 通过 loader 惰性加载 (不在此处同步取).
        """
        if not ItemManager.LookUpItem(item_id):
            raise ValueError("item_id '{}' not found in loaded item ids".format(item_id))

        d = dict_data or {}
        aux = d.get("AuxValue", 0)

        return Item(
            item_id=item_id,
            aux_value=aux,
            attr=d.get("Attr"),  # 原实现丢弃调用方传入的 Attr, 致附魔/耐久/UserData 变体坍缩
            extra_data=d.get("ExtraData"),
            loader=self._LazyLoader,
        )

ItemFactory = __ItemFactory()

class __ItemManager(object):
    """ 全项目唯一的 Item 持有者，其余模块只借不存 """

    def __init__(self):
        self.items = []  # type: list
        """
        **唯一的 Item 实例池**。要物品都从这里拿，不要另存一份。

        含隐藏物品，取可见集走 GetBrowsableItems。
        不变量: 与 item_ids 同集(索引期抛异常的除外) —— 这条正是隐藏物品也要入池的理由。
        注意 Info **一定读得到但不一定有内容**: 引擎取不到时它静默降级成空 ItemInfo。
        """

        self.item_ids = set()  # type: set
        """
        引擎报上来的**全部**物品 id(可见 + 隐藏)，LookUpItem 查的就是它。

        它必须与 items 的 id 集同集: LookUpItem 说有、GetItemById 说没有，
        消费方无从判断 —— 隐藏物品曾经只进这里不进 items，造出过一批游离 Item。
        """

        self.hidden_keys = set()  # type: set
        """
        隐藏物品的键集合（`keys.make_key(id, aux)`）—— **旁表，不是 Item 上的字段**。

        隐藏是「事后想改」的属性，长在 Item 上就意味着 Item 可变，
        而 Item 被配方/书签/缓存到处持有，可变就等于到处埋雷。
        放旁表则随时可写、零时序约束，见 docs/architecture/item_model.md §6.3。
        """

        self.hidden_plain_keys = set()  # type: set
        """
        只藏原件的键集合 —— 原件是这个键下不带 userData、附魔这些区分变体属性的那一样（`Item.IsPlain`，id 表注册的就是它）。
        带 userData 的变体顶替原件时用（附魔书、烟花）：hidden_keys 按键藏，会把同一个键下的变体一起藏掉
        """

        self._version = 0  # type: int
        """
        物品表版本号，池或旁表**任何**变更都 +1。

        派生物(搜索索引、UI 分页缓存)不在本层，本层不能反向去通知它们；
        它们各自记住「按哪个版本建的」，不一致自己重建。拉模型，无反向依赖。
        """

        self.item_name_index = {}  # type: dict
        """
        ItemName -> [Item]；一名多物是常态(同名不同 aux)，所以值是表不是单个。
        不变量: **没有空字符串键** —— 取不到信息的物品不进这里，见 __AppendToIndex。
        """

        self.item_id_index = {}  # type: dict
        """ ItemId -> [Item]；现在恒为一对一，aux 变体落地后会变成一对多 """

        self.__search_cache = {}  # type: dict
        """ SearchByCondition 的结果缓存，键由调用方给；任何注册/清空都必须作废它 """

    def Version(self):  # type: () -> int
        """ 物品表版本；派生物拿它判断自己有没有过期 """
        return self._version

    def LoadItemIds(self, item_ids, hidden_ids=None):  # type: (list, list or None) -> None
        """ 收下引擎的 id 表；hidden_ids 是其中隐藏的那部分 """
        # 只动 id 表, 不碰已注册的物品 —— 清物品是 Reset 的事, 调用序是
        # LoadItemIds -> Reset -> RegItemFromIdList, Reset 若连 id 表一起清就断链了
        self.item_ids = set(item_ids)
        # 引擎的隐藏表是按 id 给的, 而此刻只会造出 aux=0 的默认物品;
        # 之后追加的 aux 变体各自在 ItemSpec 里声明可见性, 不继承这里
        self.hidden_keys = set(keys.make_key(item_id, 0) for item_id in (hidden_ids or ()))
        self.hidden_plain_keys = set()  # 和 hidden_keys 一样每次进世界从头来：扩展装配时再藏
        self.__Touch()

    def LookUpItem(self, item_id):  # type: (str) -> bool
        """ 查找一个物品是否存在 """
        return item_id in self.item_ids

    def GetItems(self):  # type: () -> list
        return self.items

    def GetBrowsableItems(self, include_hidden=False):  # type: (bool) -> list
        """ 默认候选集: 非隐藏物品，按 ItemId 升序；include_hidden 连藏着的一起（物品栏选了「隐藏物品」筛选时）"""
        # 不持有这份表: 过滤结果本来就带缓存, 再存一份只多一个要同步作废的地方
        # (被删掉的 BrowsableItemManager.current_items_list 就是那份多余副本)
        if include_hidden:
            items = self.SearchByCondition(lambda item: True, cache_key=_ALL_CACHE_KEY)
        else:
            items = self.SearchByCondition(lambda item: not self.IsHidden(item), cache_key=_BROWSABLE_CACHE_KEY)
        items.sort(key=lambda item: item.ItemId)
        return items

    def GetItemsById(self, item_id):  # type: (str) -> list
        return self.item_id_index.get(item_id, [])

    def GetItemById(self, item_id):  # type: (str) -> Item or None
        items = self.GetItemsById(item_id)
        return items[0] if items else None

    def GetItemsByName(self, item_name):  # type: (str) -> list
        return self.item_name_index.get(item_name, [])

    def SearchByCondition(self, condition, cache_key=None):  # type: (any, str or None) -> list
        """ 按条件搜索，可选使用缓存键减少重复线性扫描 """
        if cache_key and cache_key in self.__search_cache:
            return list(self.__search_cache[cache_key])

        result = [item for item in self.items if condition(item)]

        if cache_key:
            self.__search_cache[cache_key] = tuple(result)

        return result

    def ResolveTag(self, tag):  # type: (str) -> list
        """ 获取标签对应的已注册物品列表 """
        item_ids = ItemOrganizer.GetTagItems(tag)
        if not item_ids:
            return []
        items = []
        for item_id in item_ids:
            items.extend(self.GetItemsById(item_id))
        # 按实例身份去重：同一个 Item 实例可能被多个 id 索引到
        return dedupe(items, key=id)

    # 造物路径 —— 经 ItemFactory 造实例、入池、建索引。依赖 L1(id 表)与惰性加载
# ======================================================================================================================
    def RegItemFromIdList(self, item_id_list):  # type: (list) -> None
        """ 通过传入的Id表注册默认物品表，每个 id 一个 aux=0 的实例 """
        # 默认表一次建好, 之后**只追加不重来**(AddItems), 见 item_model.md §2.2:
        # 重建会换掉全部 Item 实例, 而配方缓存/书签/扫描器产物都持有旧实例
        skipped = 0
        for item_id in item_id_list:
            item = ItemFactory.CreateItem(item_id, {"ItemId": item_id})
            if not item or not self.__RegItem(item):
                skipped += 1

        self.__Touch()
        # 池子总数而不是可见数: 搜索索引那条日志报的是可见集, 单看它验不出隐藏物品有没有入池
        logger.info("[MEI/items] 注册完成: {} 个物品(隐藏 {}, 跳过 {})".format(
            len(self.items), len(self.hidden_keys), skipped))

    def AddItems(self, specs):  # type: (any) -> int
        """ 事后追加物品(aux 变体 / 自定义物品)，返回成功个数 """
        # 与 SetHidden 那组看着同级, 实现上完全是两回事: 这条要造实例、要建索引、
        # 要把新 id 并进 item_ids, 依赖整条造物链; 那组只动一个 set
        added = 0
        for spec in specs or ():
            try:
                item = ItemFactory.CreateFromSpec(spec)
            except Exception as e:  # noqa
                logger.error("[MEI/items] 追加 {} 失败: {}".format(spec, error_text(e)))
                continue
            if any(existing == item for existing in self.GetItemsById(item.ItemId)):
                continue  # 一模一样的已经在表里（扩展重装、热重载时会再加一遍）：不重复加
            if not self.__RegItem(item):
                continue
            # 认下 id 必须在入池**之后**: 提前认, 一旦造物或索引失败,
            # item_ids 里就多出一个 GetItemById 拿不到的 id —— 正是要焊死的那道口子
            self.item_ids.add(spec.ItemId)
            if spec.Hidden:
                # 只往藏起来那边写：hidden=False（缺省）不该把别处 SetHidden 藏起来的同一个键又显回来
                self.__SetHiddenKey(keys.make_key(spec.ItemId, spec.AuxValue), True)
            added += 1

        if added:
            self.__Touch()
        return added

    def Reset(self):  # type: () -> None
        """ 清空已注册物品与索引，避免重复注册累积；不动 LoadItemIds 给的 id 表 """
        self.items = []
        self.item_name_index = {}
        self.item_id_index = {}
        self.__Touch()

    # 旁表路径 —— 只动集合，**一个 Item 都不碰**。没有造物、没有索引、没有引擎调用
# ======================================================================================================================
    def IsHidden(self, item):  # type: (Item) -> bool
        key = keys.make_key(item.ItemId, item.AuxValue)
        return key in self.hidden_keys or (key in self.hidden_plain_keys and item.IsPlain)

    def SetHidden(self, item_id, aux_value=0, hidden=True):  # type: (str, int, bool) -> bool
        """ 改一个物品的可见性，任何时候都能调 """
        if self.__SetHiddenKey(keys.make_key(item_id, aux_value), hidden):
            self.__Touch()
            return True
        return False

    def SetPlainHidden(self, item_id, aux_value=0, hidden=True):  # type: (str, int, bool) -> bool
        """ 只藏 / 显回原件（Item.IsPlain 的那一样），同一个键下带 userData 等属性的变体照常显示；任何时候都能调 """
        key = keys.make_key(item_id, aux_value)
        if bool(hidden) == (key in self.hidden_plain_keys):
            return False
        if hidden:
            self.hidden_plain_keys.add(key)
        else:
            self.hidden_plain_keys.discard(key)
        self.__Touch()
        return True

    def GetHiddenKeys(self):  # type: () -> set
        return set(self.hidden_keys)

    def __SetHiddenKey(self, key, hidden):  # type: (tuple, bool) -> bool  # noqa
        """ 写一个键的隐藏位，返回是否真的变了(没变就别让调用方白白撞版本号) """
        if hidden:
            if key in self.hidden_keys:
                return False
            self.hidden_keys.add(key)
        else:
            if key not in self.hidden_keys:
                return False
            self.hidden_keys.discard(key)
        return True

    # 内部
# ======================================================================================================================
    def __RegItem(self, item):  # type: (Item) -> bool  # noqa
        """ 收下一个物品；索引抛异常就拒收，不让半成品进池 """
        # 惰性字段在这里会被首次触发(__AppendToIndex 读 ItemName), 引擎调用就在那后面.
        # 一个物品把整轮注册带走是不可接受的 —— 那会让物品表整个空掉
        try:
            self.__AppendToIndex(item)
        except Exception as e:  # noqa
            logger.warn("register item '{}' skipped: {}".format(item.ItemId, error_text(e)))
            return False

        self.items.append(item)
        return True

    def __Touch(self):  # noqa
        """ 唯一的变更收口：作废内部缓存 + 撞版本号 """
        # 两件事必须在一起做, 分开写迟早会漏一半 —— 漏了缓存是脏读,
        # 漏了版本号是派生物不知道自己过期了, 两种都很难查
        self.__search_cache = {}
        self._version += 1

    def __AppendToIndex(self, item):  # noqa
        item_id = item.ItemId
        item_name = item.Info.ItemName

        if item_id not in self.item_id_index:
            self.item_id_index[item_id] = []
        self.item_id_index[item_id].append(item)

        # 空名字不是名字, 不进名字索引.
        # Item.Info 在取不到时**不抛异常**, 而是静默降级成一个空 ItemInfo(item.py:294) ——
        # 于是所有取不到信息的物品会共用 "" 这一个键挤成一堆, GetItemsByName("") 返回
        # 一坨互不相干的东西, 搜索索引里也会多一条空条目. 隐藏物品入池后这类会变多
        if not item_name:
            return
        if item_name not in self.item_name_index:
            self.item_name_index[item_name] = []
        self.item_name_index[item_name].append(item)

    # 这里原先有 __RegOrganizer / __RegTags / __RegCategory / __RegGroup 四个方法,
    # 想从 item.Tags / .Category / .Group 反向填 ItemOrganizer. **双重死代码**:
    # 首行就是 return, 而且 Item.__slots__ 里根本没有这三个字段, 去掉 return 就是
    # AttributeError. 分组归属本来就该是以 id 为键的旁表(ItemOrganizer 自己那套),
    # 不该长在 Item 上 —— 已整段删除, 见 item_model.md §6.4


ItemManager = __ItemManager()

