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
原版扩展，也是给第三方看的参考实现：目录编排与生命周期写法照抄即可。
"""
from MEIScripts.api.facades.extension import MeiExtension

TYPES = ("crafting_table", "furnace", "blast_furnace", "smoker", "campfire", "stonecutter", "cartography_table",
         "smithing_table", "brewing_stand", "fuel")
"""
本扩展提供的配方类型，每个名字对应一个同名子包。

加一个配方类型 = 加一个文件夹（source.py + ui_script.py + 门面的 CATEGORY/SOURCE/UI_SCRIPT）
+ 在这里加一个名字。清单显式而不扫描目录，理由同 extensions/__init__.py。
"""

FUEL_FILTER = "mei:fuel"
""" 物品栏筛选「能燃烧」的 Id（扩展登记的带命名空间，免得和别人撞）"""

BURN_SORT = "mei:burn"
""" 物品栏排序「燃烧时长」的 Id """

FILTER, SORT = "filter", "sort"


class VanillaExtension(MeiExtension):
    """ 原版配方：工作台、熔炉家族（熔炉 / 高炉 / 烟熏炉 / 营火）、切石机、制图台、锻造台、酿造台与燃料页 """

    ID = "mei:vanilla"
    NAME = "mei.ext.vanilla.name"
    DESCRIPTION = "mei.ext.vanilla.desc"
    AUTHOR = "WuMing233qwq"
    VERSION = "1.0.0"
    MIN_API_VERSION = 2

    def __init__(self):
        self.Sources = []  # type: list
        self.Screens = []  # type: list  # 登记成挂 MEI 的原版界面（screens.py），卸载时逐个注销
        self.ItemViews = []  # type: list  # 登记上的物品栏筛选 / 排序 [(FILTER 或 SORT, Id)]，卸载时逐个撤
        self.Groups = []  # type: list  # 登记上的物品分组的键，卸载时逐个撤（组表不随物品表重建）

    def OnRegister(self, ctx):
        # 一步一隔离、挂 MEI 的原版界面最先登记：后面哪一步抛了，MEI 照样挂得上原版界面，别的类型照常
        self._Step("挂 MEI 的原版界面", self._RegisterScreens, ctx)
        for name in TYPES:
            self._Step(name, self._RegisterType, ctx, name)
        self._Step("创造栏的变体", self._RegisterCreativeItems, ctx)
        self._Step("物品分组", self._RegisterItemGroups, ctx)
        self._Step("物品栏筛选", self._RegisterItemFilters, ctx)

    @staticmethod
    def _Step(label, step, *args):
        """ 装配的一步：抛了只记一行 """
        try:
            step(*args)
        except Exception as e:  # noqa
            from MEIScripts.api.facades.utils import error_text, logger
            logger.error("[MEI/vanilla] 装配「{}」出错: {}".format(label, error_text(e)))

    def _RegisterType(self, ctx, name):
        """ 一个配方类型：类型、来源、配方页脚本，有转移策略的才支持快捷合成（没有的 plus 按钮一律不亮）"""
        module = self._ImportType(name)
        category = module.CATEGORY
        source = module.SOURCE()
        policy_cls = getattr(module, "POLICY", None)
        if policy_cls is not None:
            category.SetTransferPolicy(policy_cls())
        if not ctx.Registry.SourceRegistry.RegisterCategory(category):
            ctx.Log.warn("原版类型 {} 注册不上（同名的类型已经在了），跳过它的来源与配方页".format(category.Id))
            return
        ctx.Registry.SourceRegistry.RegisterSource(source)
        ctx.Registry.RecipeUIManager.RegisterScript(category.Id, module.UI_SCRIPT)
        self.Sources.append(source)

    @staticmethod
    def _RegisterCreativeItems(ctx):
        """
        创造栏里有、物品表里没有的物品（creative/）：物品表每个 id 只有 aux 0（RegItemFromIdList）——
        目录里带附加值的（药水、药箭、床……）与引擎自己加的带 userData 的几族（附魔书、烟花、旗帜）。
        先问引擎认不认识，不认识的跳过；目录里只有带附加值那一样的（活塞这类拿方块朝向当图标），aux 0 那份从物品栏藏起来；
        附魔书、烟花的原件（不带 userData 的）也藏起来。不用撤：每次进世界物品表都重建；同一样再加一遍 AddItems 会跳过
        """
        from MEIScripts.api.facades.utils import logger
        from .creative import GAME_VERSION, build, enchant_limit
        items = ctx.Registry.ItemManager
        plan = build(items.LookUpItem, ctx.Registry.ItemFactory.LoadInfo, enchant_limit())
        added = items.AddItems(plan.Specs)
        for item_id, aux in plan.Hide:
            items.SetHidden(item_id, aux, True)
        for item_id, aux in plan.HidePlain:
            items.SetPlainHidden(item_id, aux, True)
        logger.info("[MEI/items] 创造栏的变体: 加了 {} 个(表按游戏 {} 生成), 引擎不认识跳过 {} 个".format(
            added, GAME_VERSION, plan.Unknown))

    def _RegisterItemGroups(self, ctx):
        """
        物品栏的分组（creative/ 的 item_groups）：创造栏的物品组（镐、剑、木板……）、引擎自己加的几族（附魔书、旗帜……）、
        MEI 补的同类组（锭、粗矿……）。物品表里没有的 id 不进组；同一个键别人先登记了就不动它
        """
        from MEIScripts.api.facades.utils import logger
        from .creative import item_groups
        organizer = ctx.Registry.ItemOrganizer
        members = 0
        for key, name_key, ids in item_groups(ctx.Registry.ItemManager.LookUpItem):
            if not organizer.AddGroup(key, name=name_key):
                continue
            organizer.AddGroupItemFromList(key, ids)
            self.Groups.append(key)
            members += len(ids)
        logger.info("[MEI/items] 物品分组: {} 组、{} 种物品".format(len(self.Groups), members))

    def _RegisterItemFilters(self, ctx):
        """
        物品栏的「能燃烧」筛选与「燃烧时长」排序：用熔炉的燃料表（furnace/fuels.py）——
        引擎给方块类燃料的燃烧时长是 0，只看物品信息会漏掉木头这些（CLAUDE.md 引擎结论 §11）
        """
        from .furnace.fuels import burn_seconds, is_fuel
        filters = ctx.Registry.ItemFilters
        if filters.RegisterFilter(ctx.Registry.ItemFilter(FUEL_FILTER, "mei.filter.fuel", is_fuel, 35)):
            self.ItemViews.append((FILTER, FUEL_FILTER))
        if filters.RegisterSort(ctx.Registry.ItemSort(BURN_SORT, "mei.sort.burn", burn_seconds, 65)):
            self.ItemViews.append((SORT, BURN_SORT))

    def _RegisterScreens(self, ctx):
        """
        挂 MEI 的原版界面（工作台、熔炉族、箱子族……23 个）。归原版扩展、不写死在核心层：
        第三方的界面也走同一个门面（ctx.UI.Screens），核心层不认识任何具体的界面
        """
        from .screens import SCREENS
        for screen_def, params in SCREENS.items():
            if ctx.UI.Screens.Register(screen_def, params):
                self.Screens.append(screen_def)

    def OnTick(self, ctx):
        """
        推进全量配方扫描；队列空时立即返回，不构成常驻开销。**进存档不扫**，有人要某个类型的全表时才排上（查工作站的用途，
        EngineRecipeSource.GetAll）—— 游戏有动态注册配方的接口，开局扫了，以后为了兼容只能每加一条就整个作废重扫，反而更费
        """
        from .tools.scanner import RecipeScanner
        RecipeScanner.Pump()

    def OnUnload(self, ctx):
        # 扫出来的配方、记下的引擎答案引用的是旧世界的 Item 实例，重进世界必须清（tools/answers.py 一起清）
        from .tools.scanner import RecipeScanner
        RecipeScanner.Reset()

        for source in self.Sources:
            ctx.Registry.RecipeUIManager.UnRegisterScript(source.CategoryId)
            ctx.Registry.SourceRegistry.UnRegisterCategory(source.CategoryId)
        self.Sources = []

        for screen_def in self.Screens:
            ctx.UI.Screens.Unregister(screen_def)
        self.Screens = []

        for key in self.Groups:
            ctx.Registry.ItemOrganizer.RemoveGroup(key)
        self.Groups = []

        for kind, view_id in self.ItemViews:
            if kind == FILTER:
                ctx.Registry.ItemFilters.UnregisterFilter(view_id)
            else:
                ctx.Registry.ItemFilters.UnregisterSort(view_id)
        self.ItemViews = []

    @staticmethod
    def _ImportType(name):  # type: (str) -> any
        """ 惰性导入类型子包（引擎的 ImportModule）；它们顶层拉引擎，不能在本模块顶层 import """
        # 装配器可能在引擎就绪前 import 本模块来探测 EXTENSION
        import mod.client.extraClientApi as clientApi
        path = "MEIScripts.mei_mod.extensions.vanilla." + name
        module = clientApi.ImportModule(path)
        if module is None:
            raise ImportError("找不到模块 {}".format(path))
        return module


EXTENSION = VanillaExtension
""" 装配器只认这个名字，第三方扩展的入口模块同样要导出它 """
