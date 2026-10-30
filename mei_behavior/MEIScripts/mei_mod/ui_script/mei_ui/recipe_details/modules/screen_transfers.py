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
按界面登记的配方转移（对外是 ctx.UI.Transfers，docs/modding/05-screens-and-tools.md §3），照 NEI / JEI 的 transfer handler：
别的模组登记「某个界面开着时，哪些类型的配方交给我」，配方页上这些配方的 + 就交给它的**转移处理器**（TransferHandler）——
MEI 算好清单（TransferRequest：每一格要什么、背包里凑得出多少、挑哪一样，modules/transfer_request.py），
处理器说这一条能不能做（Check：+ 亮不亮、悬停写什么）、玩家点了以后自己去做（Transfer：发自己的请求、自己的服务端照自己的规矩搬）。
写成了 MEI 关掉配方页回到那个界面。

和类型上的转移策略（RecipeCategory.SetTransferPolicy，MEI 自己的服务端把背包里的材料放进玩家侧的合成格，docs/architecture/quick_craft.md）是两回事：
策略按类型挂，这里按界面挂；同一个界面、同一个类型两样都有时这里优先 —— 登记的人明说了「这个界面开着时配方交给我」。

- 登记：界面名（与 PushScreenEvent 的 screenDef 一样）+ 处理器（有 Transfer 方法的对象），categories 是收哪些类型（类型 Id 的列表；不给是全部），
  accepts(Recipe) -> bool 可以再筛一道（不收的 + 灰掉）。Register 返回一个记号，Unregister(记号) 撤一个，
  owner 记在扩展名下，扩展卸载时装配器兜底撤掉。同一个界面、同一个类型登记了几个，后登记的优先。
- 老的写法照样认：第二个参数给一个函数 callback(Recipe)（写成了返回 True），当作不拿东西、按配方输入顺序的处理器（LegacyHandler）。
- 处理器、accepts 抛异常只记一行（同一个目标只记第一次）：检查抛了当不收，Transfer 抛了当没写成。
- 检查的结论配方页按 Recipe.Id 缓存（+ 每帧回读），翻页、换类型时重问（CraftableCache）。
构造期不碰引擎
"""
from MEIScripts.common.classes.types.transfer import TransferError
from MEIScripts.constants.texts import TransferText
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str, to_unicode


class LegacyHandler(object):
    """ 老的写法 callback(Recipe) 包成的处理器：不拿东西（只记配方）、按配方输入的顺序 """

    GRID = None
    CONSUMES = False
    HINT = ""

    def __init__(self, callback):
        self.Callback = callback  # type: callable

    def Check(self, _request):
        return None

    def Transfer(self, request):
        return bool(self.Callback(request.Recipe))


class ScreenTransfer(object):
    """ 登记的一个转移目标 """

    __slots__ = ("Token", "ScreenDef", "Handler", "Categories", "Accept", "Owner", "Warned")

    def __init__(self, token, screen_def, handler, categories, accept, owner):
        self.Token = token  # type: str
        self.ScreenDef = screen_def  # type: str
        self.Handler = handler  # type: any  # 有 Transfer 方法的对象
        self.Categories = categories  # type: frozenset or None  # None 是全部类型
        self.Accept = accept  # type: callable or None
        self.Owner = owner  # type: str
        self.Warned = False  # type: bool

    def Takes(self, category_id):  # type: (str) -> bool
        return self.Categories is None or native_str(category_id or "") in self.Categories

    @property
    def Grid(self):  # type: () -> tuple or None
        """ 处理器要的格子 (列, 行)；没给、给得不对是 None（按配方输入的顺序）"""
        return grid_of(self.Handler)

    @property
    def Consumes(self):  # type: () -> bool
        return bool(getattr(self.Handler, "CONSUMES", True))

    @property
    def Hint(self):  # type: () -> str
        return _text_attr(self.Handler, "HINT")

    @property
    def ScreenHint(self):  # type: () -> str
        """ 不在这个界面时 + 灰着的悬停文字（处理器可选的 SCREEN_HINT，和类型转移策略的同名属性一个意思）"""
        return _text_attr(self.Handler, "SCREEN_HINT")


def _text_attr(handler, name):  # type: (any, str) -> unicode
    """ 处理器上的一句字；第三方 py2 源文件里写的 "§7…" 是 utf-8 字节串，拼进 u"" 之前先解开，不然非 ASCII 的一碰就抛 """
    text = getattr(handler, name, "")
    return to_unicode(text) if isinstance(text, basestring) else u""


def grid_of(handler):  # type: (any) -> tuple or None
    """ 处理器的 GRID：两个正整数 (列, 行) 才算，别的当没给 """
    return valid_grid(getattr(handler, "GRID", None))


def valid_grid(grid):  # type: (any) -> tuple or None
    """ (列, 行) 两个正整数才算格子，别的给 None """
    try:
        columns, rows = int(grid[0]), int(grid[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    if columns <= 0 or rows <= 0:
        return None
    return columns, rows


def _categories(value):  # type: (any) -> frozenset or None
    """ categories 参数 -> 类型 Id 的集合；None 是全部，一个字符串当一个类型 """
    if value is None:
        return None
    if isinstance(value, basestring):
        value = [value]
    return frozenset(native_str(item) for item in value if isinstance(item, basestring) and item)


def _as_error(result):  # type: (any) -> TransferError or None
    """
    检查的返回值 -> TransferError：None / 真是能点；False 是不收；一句话是不收、说这句话；TransferError 原样。
    原因一律收成 unicode（第三方给的多半是 utf-8 字节串，拼进 u"" 模板会抛）
    """
    if result is None or result is True:
        return None
    if isinstance(result, TransferError):
        result.Message = to_unicode(result.Message) if result.Message else u""
        return result
    if result is False:
        return TransferError()
    if isinstance(result, basestring):
        return TransferError(message=to_unicode(result))
    return None


class __ScreenTransfers(object):  # noqa
    """ 转移目标的登记处 """

    def __init__(self):
        self._targets = []  # type: list  # 按登记的先后
        self._serial = 0  # type: int

    def Register(self, screen_def, handler, categories=None, accepts=None, owner=""):
        # type: (str, any, any, callable, str) -> str or None
        """ 登记一个，返回记号；界面名不是字符串、处理器不对、accepts 给了却不能调的不收（给 None）"""
        if callable(getattr(handler, "Transfer", None)):
            resolved = handler
        elif callable(handler):
            resolved = LegacyHandler(handler)
        else:
            resolved = None
        if not isinstance(screen_def, basestring) or not screen_def or resolved is None \
                or (accepts is not None and not callable(accepts)):
            logger.warn("[MEI/transfer] 配方转移目标登记不上：界面 {!r}、处理器 {!r}、accepts {!r}".format(
                screen_def, handler, accepts))
            return None
        try:
            kinds = _categories(categories)
        except TypeError:
            logger.warn("[MEI/transfer] 配方转移目标登记不上：categories 要是类型 Id 的列表，给的是 {!r}".format(categories))
            return None
        self._serial += 1
        token = "transfer:{}".format(self._serial)
        self._targets.append(ScreenTransfer(token, native_str(screen_def), resolved, kinds, accepts, owner or ""))
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

    def Covering(self, category_id):  # type: (str) -> ScreenTransfer or None
        """
        有没有哪个界面登记了收这一类配方（不管它现在开没开）；后登记的优先，没有给 None。
        配方页拿它决定 + 出不出：有就出，当前界面不是它就灰掉。每帧被问 —— 只做比较
        """
        for target in reversed(self._targets):
            if target.Takes(category_id):
                return target
        return None

    def Check(self, target, request):  # type: (ScreenTransfer, any) -> TransferError or None
        """
        这一条能不能做（+ 亮不亮、悬停写什么）：先问 accepts，再问处理器的 Check（没写的话按 CONSUMES：要拿东西的材料不够就不收）。
        抛了当不收
        """
        recipe = getattr(request, "Recipe", None)
        if not getattr(request, "Fits", True):
            return TransferError(message=TransferText.TooBig)
        if target.Accept is not None:
            try:
                if not target.Accept(recipe):
                    return TransferError()
            except Exception as e:  # noqa  别的模组的判断出错不能带走配方页
                self.__Warn(target, "accepts", e)
                return TransferError()
        check = getattr(target.Handler, "Check", None)
        if not callable(check):
            if target.Consumes and not request.Complete():
                return TransferError(missing=request.Missing())
            return None
        try:
            return _as_error(check(request))
        except Exception as e:  # noqa
            self.__Warn(target, "检查", e)
            return TransferError()

    def Deliver(self, target, request):  # type: (ScreenTransfer, any) -> tuple
        """ 交给它做：返回 (写成了没有, TransferError 或 None)；抛了当没写成 """
        try:
            result = target.Handler.Transfer(request)
        except Exception as e:  # noqa
            self.__Warn(target, "Transfer", e)
            return False, None
        if isinstance(result, (TransferError, basestring)):
            return False, _as_error(result)
        return bool(result), None

    def Reset(self):
        self._targets = []

    @staticmethod
    def __Warn(target, what, error):
        if target.Warned:
            return
        target.Warned = True
        logger.error("[MEI/transfer] 界面 {} 的配方转移处理器的{}抛异常: {}".format(target.ScreenDef, what, error_text(error)))


ScreenTransfers = __ScreenTransfers()
