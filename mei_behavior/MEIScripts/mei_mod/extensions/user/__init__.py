# coding=utf-8
# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
内置扩展 mei:user：玩家在 MEI 编辑器里做的页面与配方（docs/architecture/user_recipes.md）。

- OnRegister：登记 MEI 自带的积木（经 ctx.UI.Blocks，和第三方走同一个接口，blocks/）。
- OnReady：每个页面登记成一个配方类型（托管配方页，host.py）和一个来源（build.py）。放在 OnReady：原版扩展在 OnRegister 里才把
  创造栏的变体加进物品表，配方里的药水、附魔书要等它们在了才找得回；第三方的积木也都登记完了，格子才编得对号。
- 登记哪些页面照计划（plan.py）：本地开着的分组里的页面（关着的分组不登记）、订阅的服务器分组（开着的）、操作员统一的分组
  （「启用强制覆盖」开着时；同 Id 替换本地的、排在所有类型最前，user_recipes.md §22）；页面、配方、排序都没变的不重登记。
- 编辑器、管理器存了东西（UserRecipeManager 的改动通知）：照计划重来一遍，只动变了的页面。类型、来源一变 SourceRegistry 的版本就变，
  查询缓存、收藏找回、开着的配方页与配方树跟着它重查。
- 设置「启用自定义配方」（缺省关，mei_ui/editor/settings.py）：关着时一个页面都不登记；在设置里打开当场全部登记，关掉当场全部撤掉。
  积木照样登记（不碰引擎，第三方的积木也走这个接口）
"""
from MEIScripts.api.facades.extension import MeiExtension


class UserExtension(MeiExtension):
    """ 玩家自制配方：MEI 编辑器做的页面与配方 """

    ID = "mei:user"
    NAME = "mei.ext.user.name"
    DESCRIPTION = "mei.ext.user.desc"
    AUTHOR = "WuMing233qwq"
    VERSION = "1.0.0"
    MIN_API_VERSION = 2

    def __init__(self):
        self.Ctx = None
        self.Host = None  # type: any  # 全部自制页面共用的托管者
        self.Pages = {}  # type: dict  # 类型 Id -> (页面, 字段最大值)
        self.Signatures = {}  # type: dict  # 类型 Id -> 登记时的 Entry.Signature()（plan.py）：没变就不重登记
        self.Listening = False
        self.Enabled = False  # 设置「启用自定义配方」

    def OnRegister(self, ctx):
        from .blocks import make_blocks
        for block in make_blocks():
            if not ctx.UI.Blocks.Register(block):
                ctx.Log.warn("自带的积木 {} 登记不上".format(block.Id))

    def OnReady(self, ctx):
        from MEIScripts.mei_mod.state import SettingsManager, UserRecipeManager, UserShareManager
        from MEIScripts.mei_mod.state.user_recipes import LISTENER_ALL
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import FORCE_OVERRIDE, USER_RECIPES, IsUserRecipesEnabled
        from .host import UserPageHost
        self.Ctx = ctx
        self.Host = UserPageHost(self.PageInfo)
        self.Enabled = IsUserRecipesEnabled()
        if self.Enabled:
            self._Sync(set([LISTENER_ALL]))
        UserRecipeManager.AddListener(self._OnChanged)
        UserShareManager.AddListener(self._OnChanged)
        SettingsManager.Watch(USER_RECIPES, self._OnToggled)
        SettingsManager.Watch(FORCE_OVERRIDE, self._OnOverride)
        self.Listening = True

    def OnUnload(self, ctx):
        from MEIScripts.mei_mod.state import SettingsManager, UserRecipeManager, UserShareManager
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import FORCE_OVERRIDE, USER_RECIPES
        if self.Listening:
            UserRecipeManager.RemoveListener(self._OnChanged)
            UserShareManager.RemoveListener(self._OnChanged)
            SettingsManager.Unwatch(USER_RECIPES, self._OnToggled)
            SettingsManager.Unwatch(FORCE_OVERRIDE, self._OnOverride)
            self.Listening = False
        self._Clear()
        if self.Host is not None:
            self.Host.Dispose()
            self.Host = None
        ctx.UI.Blocks.UnregisterAll()
        self.Ctx = None

    # 页面
# ======================================================================================================================
    def PageInfo(self, category_id):  # type: (str) -> tuple or None
        """ 托管者问：这个类型的 (页面, 字段最大值) """
        return self.Pages.get(category_id)

    def _OnChanged(self, pages):  # type: (set) -> None
        if self.Ctx is not None and self.Enabled:
            self._Sync(pages)

    def _OnOverride(self, _key, _value):
        """ 「启用强制覆盖」开 / 关：统一的分组登不登记跟着变；开了的话没拿下来的统一分组要去拿（ShareClient 对一遍）"""
        from MEIScripts.mei_mod.client.share import ShareClient
        from MEIScripts.mei_mod.state.user_recipes import LISTENER_ALL
        if self.Ctx is not None and self.Enabled:
            self._Sync(set([LISTENER_ALL]))
        ShareClient.Reconcile()

    def _OnToggled(self, _key, value):
        """ 设置里开 / 关了自定义配方：开了全部登记，关了全部撤掉 """
        from MEIScripts.mei_mod.state.user_recipes import LISTENER_ALL
        enabled = bool(value)
        if self.Ctx is None or enabled == self.Enabled:
            return
        self.Enabled = enabled
        if enabled:
            self._Sync(set([LISTENER_ALL]))
        else:
            self._Clear()
            self.Ctx.Log.info("自制配方：关了，撤掉了全部页面")

    def _Clear(self):  # type: () -> None
        """ 撤掉登记过的全部页面 """
        if self.Ctx is None:
            return
        for cid in list(self.Pages):
            self.Ctx.Registry.SourceRegistry.UnRegisterCategory(cid)
        self.Pages = {}
        self.Signatures = {}

    def _Plan(self):  # type: () -> list
        """
        这一刻要登记的页面（plan.make_plan）：本地开着的分组里的页面（排序按建的先后）；拿下来的分组（UserShareManager）里，
        统一的（「启用强制覆盖」开着时）、订阅了又开着的（按拿下来的先后）
        """
        from MEIScripts.mei_mod.state import UserRecipeManager, UserShareManager
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import IsForceOverride
        from .plan import LOCAL, SUBSCRIBED, UNIFIED, by_page, make_plan
        order = dict((page["id"], index) for index, page in enumerate(UserRecipeManager.Pages()))
        recipes = by_page(UserRecipeManager.Recipes())
        local = [(page, recipes.get(page["id"], []), order[page["id"]], "") for page in UserRecipeManager.ActivePages()]
        unified, subscribed, count = [], [], 0
        override = IsForceOverride()
        for sub in UserShareManager.Subs():
            sub_recipes = by_page(sub["recipes"])
            entries = [(page, sub_recipes.get(page["id"], []), count + index, sub["key"])
                       for index, page in enumerate(sub["pages"])]
            count += len(entries)
            if sub["unified"] and not sub["gone"] and override:
                unified.extend(entries)
            elif sub["subscribed"] and sub["enabled"]:
                subscribed.extend(entries)
        return make_plan({LOCAL: local, SUBSCRIBED: subscribed, UNIFIED: unified})

    def _Sync(self, changed):  # type: (set) -> None
        """
        照计划重登记：计划里没有的（删了、分组关了）撤掉；页面、配方、排序都没变的不动；changed 里点名的页面照样重登记
        （有 LISTENER_ALL 就全部重来；拿下来的页面点名时带服务器上的键，Entry.PageId）
        """
        from MEIScripts.mei_mod.state.user_recipes import LISTENER_ALL
        from .build import category_id
        from .plan import same
        everything = LISTENER_ALL in changed
        entries = self._Plan()
        wanted = set(category_id(entry.PageId()) for entry in entries)
        for stale in [cid for cid in self.Pages if cid not in wanted]:
            self.Ctx.Registry.SourceRegistry.UnRegisterCategory(stale)
            self.Pages.pop(stale, None)
            self.Signatures.pop(stale, None)
        dropped = 0
        for entry in entries:
            cid = category_id(entry.PageId())
            signature = entry.Signature()
            if everything or entry.PageId() in changed or not same(self.Signatures.get(cid), signature):
                dropped += self._Register(entry)
                if cid in self.Pages:
                    self.Signatures[cid] = signature
        if everything:
            self.Ctx.Log.info("自制配方：登记了 {} 个页面、{} 条配方{}".format(
                len(entries), sum(len(entry.Recipes) for entry in entries),
                "，{} 条的产物找不回、没登记".format(dropped) if dropped else ""))

    def _Register(self, entry):  # type: (any) -> int
        """ 登记（或重登记）计划里的一个页面（plan.Entry）；返回产物找不回、没登记的配方几条 """
        from MEIScripts.mei_mod.state import BookmarkResolver
        from MEIScripts.registry.blocks import BlockRegistry
        from .build import category_id, field_max, make_category, make_source
        registry = self.Ctx.Registry.SourceRegistry
        page, recipes = entry.Page, entry.Recipes
        cid = category_id(entry.PageId())
        if cid in self.Pages:
            registry.UnRegisterCategory(cid)
            self.Pages.pop(cid, None)
            self.Signatures.pop(cid, None)
        resolve = BookmarkResolver.ResolveItem
        category = make_category(page, 0, self.Host, resolve, sort_index=entry.Sort, ns=entry.Ns)
        source, dropped = make_source(page, recipes, BlockRegistry.Holds, resolve, self.Ctx.Registry.ItemManager.ResolveTag,
                                      ns=entry.Ns)
        if not registry.RegisterCategory(category):
            self.Ctx.Log.warn("自制页面 {} 登记不上（类型 Id 被占用了）".format(cid))
            return 0
        registry.RegisterSource(source)
        self.Pages[cid] = (page, field_max(page, recipes))
        return dropped


EXTENSION = UserExtension
""" 装配器只认这个名字 """
