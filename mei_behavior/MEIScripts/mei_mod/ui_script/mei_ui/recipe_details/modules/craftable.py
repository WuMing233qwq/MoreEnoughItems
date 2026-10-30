# coding=utf-8

# ----------------------------------------------------------------------
#  craftable.py is part of MoreEnoughItems.
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
可合成性预检 —— **开页时算一次，不是点了才说做不了**。

像 JEI 那样：进配方页就知道哪几条做得出来，做不出来的把 plus 按钮**灰掉**
（不是藏掉 —— 玩家要看见它并明白"有这个功能，但现在材料不够"）。

为什么必须缓存：可点性是**每帧集合绑定**回读的，而一次预检要问遍所有物品来源、
按全局配额跑一遍匹配。不缓存就是每帧扫一遍背包 —— 那正是 binding_cost.md 记的那类事故。
⇒ 一次会话算一次，在每次重建配方页脚本（开界面/切类型/翻页）时失效。

排序另有一条**一次性**的路（CraftableIds），它不进缓存 ——
排序发生在查询结果上，而缓存紧接着就会被页面重建清掉，进缓存等于白算。

当前界面登记了转移处理器（ctx.UI.Transfers）的，+ 亮不亮由处理器的检查说了算（Verdict，同样按 Recipe.Id 缓存）；
悬停文字（PlusHover）也在这里拼：能点时写点了会怎样，不能点写为什么、缺什么。
"""
from MEIScripts.common.classes.types.transfer import TransferContext, TransferError
from MEIScripts.constants.texts import TransferText
from MEIScripts.mei_mod.transfer import can_fulfill, copy_supply, index_supply, reachable
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.screen_transfers import ScreenTransfers
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.transfer_request import (
    build_request, describe_missing, match_slots,
)
from MEIScripts.mei_mod.ui_script.proxy.manager import ProxyManager
from MEIScripts.registry.transfer import TransferRegistry
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text


class CraftableCache(object):
    """
    一次配方页会话内的可合成性缓存

    键是 Recipe.Id —— 翻页、切类型都不必重算，同一条配方的答案不会因为换了页而变。
    """

    def __init__(self):
        self._verdict = {}   # type: dict  # Recipe.Id -> bool
        self._supply = None  # type: dict  # 供给表快照，None 表示还没采集过
        self._checks = {}    # type: dict  # (转移目标的记号, Recipe.Id) -> TransferError 或 None：处理器的检查结论
        self._hovers = {}    # type: dict  # (转移目标的记号或 None, Recipe.Id) -> + 的悬停文字

    def Invalidate(self):
        """ 丢弃全部结论。**转移成功后必须调** —— 那时玩家的物品真的变了 """
        self._verdict = {}
        self._supply = None
        self._checks = {}
        self._hovers = {}

    @staticmethod
    def TransferTarget(recipe, category_id=None):  # type: (any, str) -> any
        """
        当前开着的界面登记了接这一类配方的转移目标（ctx.UI.Transfers）就给它，没有给 None。每帧被问 —— 只是一次比较；
        类型优先取配方自己的，取不到用 category_id（配方页当前的类型）
        """
        category = getattr(recipe, "Type", None) or category_id
        return ScreenTransfers.Find(ProxyManager.GetCurrentScreen(), category)

    def Supply(self):  # type: () -> dict
        """ 这一次会话采集的供给表（物品键 -> 来源），第一次问时采集 """
        return self.__Supply(self.MakeContext())

    def Request(self, target, recipe, category_id=None, wants_max=False):  # type: (any, any, str, bool) -> any
        """ 交给转移处理器的清单（TransferRequest）：按处理器要的格子摊、拿开页时采集的供给配 """
        category = getattr(recipe, "Type", None) or category_id or ""
        return build_request(recipe, self.__Supply(self.MakeContext()), grid=target.Grid,
                             category_id=category, screen_def=target.ScreenDef, wants_max=wants_max)

    def Verdict(self, target, recipe, category_id=None):  # type: (any, any, str) -> TransferError or None
        """ 处理器对这一条的检查结论（None 是能点）；每帧回读，按（记号, Recipe.Id）缓存，算清单出错当不收 """
        key = (target.Token, _recipe_key(recipe))
        if key not in self._checks:
            try:
                self._checks[key] = ScreenTransfers.Check(target, self.Request(target, recipe, category_id))
            except Exception as e:  # noqa  算清单出错只灰掉这一条
                logger.error("[MEI/transfer] 给转移处理器算清单失败: {}".format(error_text(e)))
                self._checks[key] = TransferError()
        return self._checks[key]

    def Allows(self, target, recipe, category_id=None):  # type: (any, any, str) -> bool
        """ + 能不能点：处理器说能，或者只是提醒（Blocking 为假）"""
        verdict = self.Verdict(target, recipe, category_id)
        return verdict is None or not verdict.Blocking

    def PlusHover(self, target, category, recipe, category_id=None):  # type: (any, any, any, str) -> unicode
        """ + 的悬停文字：交给转移处理器的问它，否则问类型的转移策略（原版合成格）。按（记号, Recipe.Id）缓存 """
        key = (target.Token if target is not None else None, _recipe_key(recipe))
        if key not in self._hovers:
            try:
                if target is not None:
                    text = self.__HandlerHover(target, recipe, category_id)
                else:
                    text = self.__PolicyHover(category, recipe)
            except Exception as e:  # noqa  悬停文字出错不能带走这条绑定
                logger.error("[MEI/transfer] + 的悬停文字算不出来: {}".format(error_text(e)))
                text = ""
            self._hovers[key] = text
        return self._hovers[key]

    def MakeContext(self):  # type: () -> TransferContext
        """ 造一个客户端侧的转移环境，带上当前屏幕供策略判断 """
        import mod.client.extraClientApi as clientApi
        return TransferContext(
            player_id=clientApi.GetLocalPlayerId(), side="client",
            extra={"screen_def": ProxyManager.GetCurrentScreen()})

    def CanCraft(self, category, recipe):  # type: (any, any) -> bool
        """ 这条配方现在做不做得出来。第一次问会采集一次供给，之后走缓存 """
        if category is None or category.Transfer is None:
            return False

        recipe_id = getattr(recipe, "Id", None)
        if recipe_id is None:
            return False
        if recipe_id in self._verdict:
            return self._verdict[recipe_id]

        verdict = self.__Compute(category, recipe)
        self._verdict[recipe_id] = verdict
        return verdict

    # 内部
# ======================================================================================================================
    def __Compute(self, category, recipe):  # type: (any, any) -> bool
        policy = category.Transfer
        ctx = self.MakeContext()
        if not policy.CanTransfer(ctx):
            return False

        # 摊到槽位上整个交给策略 —— 与真正转移时走的是同一条路,
        # 所以"预检说能做"与"真做得成"必然一致
        mapped = policy.MapRecipe(ctx, recipe)
        if not mapped:
            return False

        # copy_supply: 匹配会就地扣减配额, 每条配方都得从同一份原始供给重新算
        return can_fulfill(mapped, copy_supply(self.__Supply(ctx)))

    def __HandlerHover(self, target, recipe, category_id):  # type: (any, any, str) -> unicode
        verdict = self.Verdict(target, recipe, category_id)
        if verdict is None:
            return target.Hint or TransferText.Default
        lines = []
        if not verdict.Blocking:
            lines.append(target.Hint or TransferText.Default)
        if verdict.Message:
            lines.append(verdict.Message)
        if verdict.Missing:
            lines.append(TransferText.Missing.format(describe_missing(verdict.Missing)))
        if not lines:
            lines.append(TransferText.Rejected)
        return u"\n".join(lines)

    def __PolicyHover(self, category, recipe):  # type: (any, any) -> unicode
        policy = getattr(category, "Transfer", None) if category is not None else None
        if policy is None:
            return u""
        ctx = self.MakeContext()
        if not policy.CanTransfer(ctx):
            return getattr(policy, "SCREEN_HINT", u"") or TransferText.WrongScreen
        mapped = policy.MapRecipe(ctx, recipe)
        if not mapped:
            return TransferText.TooBig
        missing = [slot for slot in match_slots(mapped, copy_supply(self.__Supply(ctx))) if slot.Missing > 0]
        if missing:
            return TransferText.Missing.format(describe_missing(missing))
        return getattr(policy, "HINT", u"") or TransferText.Default

    def __Supply(self, ctx):  # type: (any) -> dict
        if self._supply is None:
            try:
                self._supply = index_supply(TransferRegistry.Collect(ctx))
            except Exception as e:  # noqa  采集失败就当什么都没有, 按钮灰着
                logger.error("[MEI/transfer] 采集物品来源失败: {}".format(error_text(e)))
                self._supply = {}
        return self._supply


def _recipe_key(recipe):  # type: (any) -> any
    return getattr(recipe, "Id", None) or id(recipe)


def CraftableIds(result):  # type: (dict) -> set
    """
    一次性算出查询结果里**哪些配方现在做得出来**，返回 Recipe.Id 集合

    供 ordering 排序用。**刻意不进 CraftableCache** ——
    排序发生在 SetRecipesResult，而缓存会在紧随其后的页面重建里被清掉，
    进缓存等于算完就丢。这里只采集一次供给，然后逐条判定。

    顺序的语义是「**进页那一刻的推荐**」而不是实时排行：
    转移之后不重排，玩家刚点过的那条不会在他眼皮底下掉下去。

    逐条判之前先用 reachable 筛（有一格的候选背包里一样都没有的，不必复制供给表再试算）：
    查工作台的用途时结果是整个合成表，上千条里绝大多数在这一步就筛掉了（离线 1500 条约 50 → 23 毫秒）。
    """
    from MEIScripts.registry.sources import SourceRegistry

    if not result:
        return set()

    session = CraftableCache()
    ctx = session.MakeContext()
    try:
        supply = index_supply(TransferRegistry.Collect(ctx))
    except Exception as e:  # noqa  采集失败就当谁都做不了, 顺序退化为原序
        logger.error("[MEI/transfer] 排序前采集物品来源失败: {}".format(error_text(e)))
        return set()

    craftable = set()
    for crafting_type, recipes in result.items():
        category = SourceRegistry.GetCategory(crafting_type)
        if category is None or category.Transfer is None:
            continue
        policy = category.Transfer
        if not policy.CanTransfer(ctx):
            continue
        for recipe in recipes:
            recipe_id = getattr(recipe, "Id", None)
            if recipe_id is None or recipe_id in craftable:
                continue
            mapped = policy.MapRecipe(ctx, recipe)
            if mapped and reachable(mapped, supply) and can_fulfill(mapped, copy_supply(supply)):
                craftable.add(recipe_id)
    return craftable
