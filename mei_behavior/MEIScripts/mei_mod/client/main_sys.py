# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
#  main_sys.py is part of MoreEnoughItems.
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

from MEIScripts.mei_mod.extensions.loader import ExtensionLoader
from MEIScripts.constants.codes import NameConst
from MEIScripts.mei_mod.network.base import Channel, REQUEST_EVENT, RESPONSE_EVENT
from MEIScripts.mei_mod.transfer import RegisterBuiltinSources
from MEIScripts.mei_mod.ui_script import settings as settings_ui
from MEIScripts.mei_mod.ui_script.controls.item import grid as item_grid
from MEIScripts.mei_mod.ui_script.mei_ui.floating.hosts import FloatHosts
from MEIScripts.mei_mod.ui_script.mei_ui.floating.screen import register_screen
from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys import binds as hotkey_binds
from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys import manager as hotkeys
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import register_screen as register_tree_screen
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.mei_mod.state import (
    BookmarkManager, CacheManager, PinManager, PrefsManager, SettingsManager, TreePrefsManager)
from MEIScripts.mei_mod.state.settings import IsBookmarksWorldSpecific, RegisterBuiltinSettings
from MEIScripts.mei_mod.state.settings.builtin import BOOKMARKS_WORLD
from MEIScripts.registry import ItemManager, RecipeManager
from MEIScripts.registry.search import ItemSearchIndex
from MEIScripts.utils.events import EventListener
from MEIScripts.utils.text import to_native

ClientSystem = clientApi.GetClientSystemCls()


def OnBookmarksWorldChanged(_key, value):
    """ 设置页切换收藏的保存位置：先写下手上的，再从另一边读；模块级函数，重进世界不会重复订阅 """
    BookmarkManager.SetWorldSpecific(value is True)

class MainSys(ClientSystem):
    def __init__(self, namespace, system_name):
        ClientSystem.__init__(self, namespace, system_name)
        self.Events = EventListener(self)

        # 通讯. 客户端是请求发起方, 也是回执接收方
        self.Channel = Channel("client")
        self.Channel.Attach(self.__SendToServer)

        # 设置项只是声明，不碰引擎；任何地方读设置之前都得先登记好。快捷键的键位也是设置项（设置「按键绑定」页）
        RegisterBuiltinSettings()
        hotkey_binds.RegisterSettings()

        self.InitClientListenEvents()


    def InitClientListenEvents(self):
        """ 初始化客户端事件监听 """
        self.Events.Listen("OnKeyPressInGame", self.onKeyPress)
        # 滚轮类的快捷键（Ctrl+滚轮改收藏数量这类）；各界面的滚轮翻页另外自己听，先问 binds.WheelTaken()
        self.Events.Listen("MouseWheelClientEvent", self.onWheel)
        self.Events.Listen("UiInitFinished", self.onUiInit)
        self.Events.Listen("PushScreenEvent", self.onPushScreen)
        self.Events.Listen("PopScreenEvent", self.onPopScreen)
        self.Events.Listen("PopScreenAfterClientEvent", self.onPopScreenAfter)
        # grid 的格子重新排列了（行列数变了等）：MEI 的 grid 把格子上的图标重设一遍（新格子上没有图标，引擎结论 §46）
        self.Events.Listen("GridComponentSizeChangedClientEvent", self.onGridRearranged)
        self.Events.Listen("SyncLoadedItems", self.SyncLoadedItems, NameConst.NameSpace, NameConst.ServerSysName)
        self.Events.Listen(RESPONSE_EVENT, self.OnResponse, NameConst.NameSpace, NameConst.ServerSysName)

    def DestroyClientListenEvents(self):
        """ 销毁客户端事件监听 """
        self.Events.UnlistenAll()

    def OnResponse(self, args):
        """ 引擎事件回调，转交 Channel """
        self.Channel.OnResponse(args)

    def __SendToServer(self, payload, _player_id):
        """ Channel 的发送口 """
        # 服务端拿不到"这条请求是谁发的", 必须自己带上 —— 回执按它投递回来
        payload["__from"] = clientApi.GetLocalPlayerId()
        self.NotifyToServer(REQUEST_EVENT, payload)

    def onPushScreen(self, args):
        # 记下当前屏幕: 快捷合成靠它判断"现在开着的是不是工作台"
        ProxyManager.SetCurrentScreen(args.get("screenDef", ""))
        # 悬浮窗（HUD、强制兼容）：只在这里注入 —— 压上来的界面要注入就当场注入，已经注入的被盖住（docs/architecture/floating.md §6）
        FloatHosts.OnPush(args.get("screenDef", ""))
        # 快捷键：按着的修饰键、按住的键都当已松开（切界面时松开多半收不到）；正在录键就放弃
        hotkeys.ResetInput()
        hotkeys.CancelCapture()

    def onPopScreen(self, args):
        FloatHosts.OnPop(args.get("screenDef", ""))

    def onPopScreenAfter(self, args):
        # 参数是弹出之后的栈顶：当前屏幕跟着回到它（从工作台开的配方树关掉后，快捷合成认的还得是工作台），
        # 回到 HUD、回到被盖住的注入界面时把它的悬浮窗显回来（不重新注入）
        ProxyManager.SetCurrentScreen(args.get("screenDef", ""))
        FloatHosts.OnPopAfter(args.get("screenDef", ""))
        hotkeys.ResetInput()
        hotkeys.CancelCapture()

    def onUiInit(self, _):
        # 挂 MEI 的原版界面不在这里登记了：归原版扩展（extensions/vanilla/screens.py），扩展装配时经 ctx.UI.Screens 登记
        settings_ui.Boot()
        # MEI 自己的界面（HUD 上点 MEI 时 PushScreen 开它）：每次进存档都要注册，SDK 进存档时把注册表清了
        register_screen()
        # 配方树（PushScreen 的新界面，docs/architecture/recipe_tree.md）：同样每次进存档注册
        register_tree_screen()
        # 进了一个存档：按存档的那份收藏重新读，保存位置照设置页来
        BookmarkManager.ResetWorldStore()
        BookmarkManager.SetWorldSpecific(IsBookmarksWorldSpecific())
        SettingsManager.Watch(BOOKMARKS_WORLD, OnBookmarksWorldChanged)
        # 快捷键：MEI 自己的按键绑定（设置「按键绑定」页改键，docs/architecture/bookmarks.md §12），不注册给引擎
        hotkeys.ResetInput()

    def onKeyPress(self, args):
        # 快捷键：裸按键（修饰键自己记、组合精确匹配；设置页正在录键时交给录键）
        hotkeys.OnKeyPress(args)

    def onWheel(self, args):
        # 滚轮类的快捷键（按着修饰键滚）；设置页正在录滚轮类的键时交给录键
        hotkeys.OnWheel(args)

    def onGridRearranged(self, args):  # noqa
        # path：grid 所在的路径（从 UI 根节点算起，SDK 2.9 起有）；没给就通知全部
        get = getattr(args, "get", None)
        item_grid.grid_rearranged(get("path") if get is not None else None)

    def SyncLoadedItems(self, args):  # noqa
        """ 加载来自服务端的物品列表 """
        # 事件载荷里的字符串可能是 unicode（连远程服务器时），物品 id 都要递给引擎：先收成 str（CLAUDE.md 引擎结论 §2）
        items, hidden_items = to_native(args.get("items", [[], []]))
        item_list = items + hidden_items

        ItemManager.LoadItemIds(item_list, hidden_items)

        # 隐藏物品也一并注册: LookUpItem 认它们, items 不认它们, 那道口子会造出
        # 索引不到的游离 Item(物品书签反查踩过). 可见集由 GetBrowsableItems 过滤
        ItemManager.Reset()
        ItemManager.RegItemFromIdList(item_list)
        # 上一个世界的东西全清：搜索结果页（开物品栏时会还原它）、最近浏览、配方页的返回栈里都是旧的 Item 实例；
        # 配方查询缓存**必须清** —— 重进世界会重建全部 Item 对象, 而缓存键是值语义的 Item,
        # 旧世界的条目会"匹配上"新世界的物品, 拿到的却是上一个世界的 Recipe 对象.
        CacheManager.ResetWorld()
        RecipeManager.SetQueryCache(CacheManager.GetRecipeQueryCache())

        # 扩展装配点：内置的 vanilla 与已排队的第三方在这里一起起来。
        # 重进世界会再次走到这里, 先卸再装, 否则重复注册会被管理器拒绝。
        #
        # 排在物品之后**不是硬约束**: 三个装配阶段一处都不读物品表(只有运行期的
        # QueryByOutput / OnTick 里的扫描器才读). 物品管线要落地时这里会重排 ——
        # 钩子必须早于 RegItemFromIdList, 方案见 docs/architecture/item_model.md §5
        ExtensionLoader.Shutdown()
        ExtensionLoader.Boot()

        # 物品来源: 客户端这份只用于预检(按钮亮不亮), 服务端那份才是真理
        RegisterBuiltinSources()

        # 搜索索引放在扩展装配之后建：装配会加物品变体（创造栏表）、改隐藏表，先建的话第一次搜索又要整个重建一遍。
        # 藏着的也进索引：物品栏的「隐藏物品」筛选要搜得到
        ItemSearchIndex.Rebuild(ItemManager.GetItems())

    # 被引擎直接执行的父类的重写函数，引擎会执行该Update回调，1秒钟30帧
    def Update(self):
        """
        Driven by system manager, Two tick way

        > 备忘: **引擎调的是本方法**, 不是自定义的 `OnTickClient` ——
        > 后者既不在 InitClientListenEvents 的监听列表里, 也不是引擎回调名,
        > 曾经把后台队列泵在那里, 结果一次都没执行过且毫无日志.
        > 以后要挂每帧逻辑, 挂这里.
        """
        # 扩展的每帧节拍(vanilla 用它推进全量配方扫描); 没有扩展要跑时是空转
        ExtensionLoader.Tick()
        self.Channel.Tick()
        # 注入在 HUD / 未支持界面上的 MEI 没有代理来调 OnTick，在这里推
        FloatHosts.Tick()

    def Destroy(self):
        FloatHosts.Reset()
        # 改完设置马上退出世界时，防抖还没来得及写盘；收藏、置顶、偏好、配方树的首选同理
        # （SDK 退出存档时把模组的定时器全清了，排着的合并写不会再跑）。有改动的才写
        SettingsManager.Flush()
        BookmarkManager.Flush()
        PrefsManager.Flush()
        PinManager.Flush()
        TreePrefsManager.Flush()
        self.Channel.Detach()
        self.DestroyClientListenEvents()
