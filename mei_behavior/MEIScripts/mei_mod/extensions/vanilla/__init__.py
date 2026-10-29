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


class VanillaExtension(MeiExtension):
    """ 原版配方：工作台、熔炉家族（熔炉 / 高炉 / 烟熏炉 / 营火）、切石机、制图台、锻造台、酿造台与燃料页 """

    ID = "mei:vanilla"
    NAME = "mei.ext.vanilla.name"
    DESCRIPTION = "mei.ext.vanilla.desc"
    AUTHOR = "WuMing233qwq"
    VERSION = "0.1.0"
    MIN_API_VERSION = 2

    def __init__(self):
        self.Sources = []  # type: list
        self.Screens = []  # type: list  # 登记成挂 MEI 的原版界面（screens.py），卸载时逐个注销

    def OnRegister(self, ctx):
        for name in TYPES:
            module = self._ImportType(name)
            if module is None:
                continue
            category = module.CATEGORY
            source = module.SOURCE()
            # 有转移策略的类型才支持快捷合成; 没有的 plus 按钮一律不亮
            policy_cls = getattr(module, "POLICY", None)
            if policy_cls is not None:
                category.SetTransferPolicy(policy_cls())
            ctx.Registry.SourceRegistry.RegisterCategory(category)
            ctx.Registry.SourceRegistry.RegisterSource(source)
            ctx.Registry.RecipeUIManager.RegisterScript(category.Id, module.UI_SCRIPT)
            self.Sources.append(source)
            # 这个类型要的物品变体（药水的各种 aux、空定位地图）：物品表里每个 id 只有 aux 0（RegItemFromIdList），不加就画不出、点不到。
            # 不用撤：每次进世界物品表都重建；同一样再加一遍 AddItems 会跳过
            variants = getattr(module, "VARIANTS", None)
            if variants:
                ctx.Registry.ItemManager.AddItems(variants)
        self._RegisterScreens(ctx)

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
        """ 推进全量配方扫描；队列空时立即返回，不构成常驻开销 """
        from .tools.scanner import RecipeScanner
        RecipeScanner.Pump()

    def OnUnload(self, ctx):
        # 扫出来的配方引用的是旧世界的 Item 实例，重进世界必须清
        from .tools.scanner import RecipeScanner
        RecipeScanner.Reset()

        for source in self.Sources:
            ctx.Registry.RecipeUIManager.UnRegisterScript(source.CategoryId)
            ctx.Registry.SourceRegistry.UnRegisterCategory(source.CategoryId)
        self.Sources = []

        for screen_def in self.Screens:
            ctx.UI.Screens.Unregister(screen_def)
        self.Screens = []

    @staticmethod
    def _ImportType(name):  # type: (str) -> any
        """ 惰性导入类型子包；它们顶层拉引擎，不能在本模块顶层 import """
        # 装配器可能在引擎就绪前 import 本模块来探测 EXTENSION
        return __import__(
            "MEIScripts.mei_mod.extensions.vanilla." + name, {}, {},
            ["CATEGORY", "SOURCE", "UI_SCRIPT", "POLICY", "VARIANTS"])


EXTENSION = VanillaExtension
""" 装配器只认这个名字，第三方扩展的入口模块同样要导出它 """
