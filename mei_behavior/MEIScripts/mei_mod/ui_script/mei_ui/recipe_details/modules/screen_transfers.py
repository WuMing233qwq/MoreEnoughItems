# coding=utf-8

# ----------------------------------------------------------------------
#  screen_transfers.py is part of MoreEnoughItems.
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
按界面登记的配方转移（对外是 ctx.UI.Transfers，docs/modding/05-screens-and-tools.md §3）：别的模组登记「某个界面开着时，
哪些类型的配方交给我」，配方页上这些配方的 + 就不再搬材料，而是把配方交给它 —— callback(Recipe)，写成了返回 True，
MEI 关掉配方页回到那个界面。给样板、编码器、过滤器这类「记下一条配方」的界面用（照 JEI 的 recipe transfer handler）。

和类型上的转移策略（RecipeCategory.SetTransferPolicy，搬材料进格子，docs/architecture/quick_craft.md）是两回事：
策略按类型挂，这里按界面挂；同一个界面、同一个类型两样都有时这里优先 —— 登记的人明说了「这个界面开着时配方交给我」。

- 登记：界面名（与 PushScreenEvent 的 screenDef 一样）+ 回调，categories 是收哪些类型（类型 Id 的列表；不给是全部），
  accepts(Recipe) -> bool 说这一条收不收（不收的 + 灰掉；不给是都收）。Register 返回一个记号，Unregister(记号) 撤一个，
  owner 记在扩展名下，扩展卸载时装配器兜底撤掉。同一个界面、同一个类型登记了几个，后登记的优先。
- 回调、accepts 抛异常只记一行（同一个目标只记第一次）：accepts 抛了当不收，回调抛了当没写成。
- accepts 每帧被配方页回读（+ 灰不灰），配方页按 Recipe.Id 缓存，翻页、换类型时重算（CraftableCache）。
构造期不碰引擎
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str


class ScreenTransfer(object):
    """ 登记的一个转移目标 """

    __slots__ = ("Token", "ScreenDef", "Callback", "Categories", "Accept", "Owner", "Warned")

    def __init__(self, token, screen_def, callback, categories, accept, owner):
        self.Token = token  # type: str
        self.ScreenDef = screen_def  # type: str
        self.Callback = callback  # type: callable
        self.Categories = categories  # type: frozenset or None  # None 是全部类型
        self.Accept = accept  # type: callable or None
        self.Owner = owner  # type: str
        self.Warned = False  # type: bool

    def Takes(self, category_id):  # type: (str) -> bool
        return self.Categories is None or native_str(category_id or "") in self.Categories


def _categories(value):  # type: (any) -> frozenset or None
    """ categories 参数 -> 类型 Id 的集合；None 是全部，一个字符串当一个类型 """
    if value is None:
        return None
    if isinstance(value, basestring):
        value = [value]
    return frozenset(native_str(item) for item in value if isinstance(item, basestring) and item)


class __ScreenTransfers(object):  # noqa
    """ 转移目标的登记处 """

    def __init__(self):
        self._targets = []  # type: list  # 按登记的先后
        self._serial = 0  # type: int

    def Register(self, screen_def, callback, categories=None, accepts=None, owner=""):
        # type: (str, callable, any, callable, str) -> str or None
        """ 登记一个，返回记号；界面名不是字符串、回调不能调、accepts 给了却不能调的不收（给 None）"""
        if not isinstance(screen_def, basestring) or not screen_def or not callable(callback) \
                or (accepts is not None and not callable(accepts)):
            logger.warn("[MEI/transfer] 配方转移目标登记不上：界面 {!r}、回调 {!r}、accepts {!r}".format(screen_def, callback, accepts))
            return None
        try:
            kinds = _categories(categories)
        except TypeError:
            logger.warn("[MEI/transfer] 配方转移目标登记不上：categories 要是类型 Id 的列表，给的是 {!r}".format(categories))
            return None
        self._serial += 1
        token = "transfer:{}".format(self._serial)
        self._targets.append(ScreenTransfer(token, native_str(screen_def), callback, kinds, accepts, owner or ""))
        return token

    def Unregister(self, token):  # type: (str) -> bool
        before = len(self._targets)
        self._targets = [target for target in self._targets if target.Token != token]
        return len(self._targets) != before

    def UnregisterOwner(self, owner):  # type: (str) -> int
        """ 撤掉某个扩展登记的全部；空 owner 不撤 """
        if not owner:
            return 0
        before = len(self._targets)
        self._targets = [target for target in self._targets if target.Owner != owner]
        return before - len(self._targets)

    def Find(self, screen_def, category_id):  # type: (str, str) -> ScreenTransfer or None
        """ 这个界面开着时、这个类型的配方交给谁；后登记的优先，没有给 None。每帧被问 —— 只做比较 """
        if not screen_def:
            return None
        for target in reversed(self._targets):
            if target.ScreenDef == screen_def and target.Takes(category_id):
                return target
        return None

    def Accepts(self, target, recipe):  # type: (ScreenTransfer, any) -> bool
        """ 这一条收不收（+ 亮不亮）；accepts 抛了当不收 """
        if target.Accept is None:
            return True
        try:
            return bool(target.Accept(recipe))
        except Exception as e:  # noqa  别的模组的判断出错不能带走配方页
            self.__Warn(target, "accepts", e)
            return False

    def Deliver(self, target, recipe):  # type: (ScreenTransfer, any) -> bool
        """ 把配方交给它；写成了（回调返回真）给 True，抛了当没写成 """
        try:
            return bool(target.Callback(recipe))
        except Exception as e:  # noqa
            self.__Warn(target, "回调", e)
            return False

    def Reset(self):
        self._targets = []

    @staticmethod
    def __Warn(target, what, error):
        if target.Warned:
            return
        target.Warned = True
        logger.error("[MEI/transfer] 界面 {} 的配方转移目标的{}抛异常: {}".format(target.ScreenDef, what, error_text(error)))


ScreenTransfers = __ScreenTransfers()
