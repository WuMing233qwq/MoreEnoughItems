# coding=utf-8

# ----------------------------------------------------------------------
#  search.py is part of MoreEnoughItems.
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
物品搜索：拼音 / 模糊索引（libs/pinyin_lite）+ 搜索语法。拼音库在全项目**只有这一个接触点**，
换搜索实现只动本文件。原属 BrowsableItemManager，见 docs/architecture/item_model.md §3。

搜索语法（照 NEI）：
- **空格**隔开的几段都要满足；段里用 **|** 隔开的几项满足其一；**-** 开头排除这一项（`-@minecraft`、`-#附魔`）。
- 不带前缀：物品名，拼音 / 首字母 / 原文的模糊匹配（PinyinIndex）。只有一项、不带 - 的那几段**合起来**交给拼音引擎
  （它自己按空格拆、每个词都要命中、按分数排序）—— 所以「lv bao shi」这种拼音加空格照旧能搜，结果的顺序也以它为准。
- @ 命名空间（minecraft、skybluetech …）、$ 英文 ID（冒号后面那段；带冒号时比整个 ID）：模糊 —— 大小写、下划线这类符号不论，
  连续包含就算；谁都不连续包含时退一步，按顺序出现也算（`@mc` → minecraft，`$emblk` → emerald_block）。
- # 物品完整的悬停文字（去掉 § 颜色码）：原文包含，或拼音（每个字取主读音连写）包含（`#shanghai` 搜得到写着「伤害」的）。
  悬停文字第一次用到才向引擎要（Item.HoverText 惰性），拼音按物品缓存；别的段能先筛掉的先筛掉，它排在最后。
- & 整名相等：名字（去掉空格）等于它，或名字的拼音全拼（多音字任取一个读音）等于它（`&铁锭`、`&tieding` 只出铁锭）。
"""
import re

from mod_log import logger

from MEIScripts.libs.pinyin_lite import PinyinIndex, lazy_pinyin, segments, to_unicode
from MEIScripts.utils.sequence import dedupe
from MEIScripts.utils.text import native_str
from .items import ItemManager

KIND_NAME = "name"
KIND_NAMESPACE = "namespace"
KIND_TEXT = "text"
KIND_EXACT = "exact"
KIND_ID = "id"

PREFIXES = {u"@": KIND_NAMESPACE, u"#": KIND_TEXT, u"&": KIND_EXACT, u"$": KIND_ID}
""" 前缀 → 这一项比什么；不带前缀的比物品名 """
NEGATE = u"-"
ALTERNATIVE = u"|"

COSTS = {KIND_NAMESPACE: 0, KIND_ID: 0, KIND_EXACT: 1, KIND_NAME: 2, KIND_TEXT: 3}
""" 几段的筛选顺序：便宜的先筛，悬停文字（要向引擎要）放最后 """

DEFAULT_NAMESPACE = u"minecraft"
""" ID 里没写命名空间时按原版算（基岩版的缺省命名空间） """

_COLOR_CODE = re.compile(u"§.", re.S)
_SYMBOLS = re.compile(u"[\\W_]+", re.U)
_LAST = float("inf")


class Term(object):
    """ 一项：比什么（Kind）、比的字（小写 unicode）、是不是排除 """
    __slots__ = ("Kind", "Text", "Negate")

    def __init__(self, kind, text, negate=False):
        self.Kind = kind  # type: str
        self.Text = text  # type: unicode
        self.Negate = negate  # type: bool

    def Key(self):  # type: () -> tuple
        """ 同一次搜索里比的东西一样就共用结果（排不排除不影响命中谁）"""
        return self.Kind, self.Text

    def __repr__(self):
        return "Term({}, {!r}, {})".format(self.Kind, self.Text, self.Negate)


def parse_term(piece):  # type: (unicode) -> Term or None
    """ 一项：可选的 -，可选的前缀，后面的字。只打了 - 或前缀（还在输入）的不算一项 """
    negate = piece.startswith(NEGATE)
    if negate:
        piece = piece[1:]
    kind = PREFIXES.get(piece[:1])
    if kind is None:
        kind = KIND_NAME
    else:
        piece = piece[1:]
    return Term(kind, piece, negate) if piece else None


def parse_query(query):  # type: (any) -> list
    """ 查询串 → 几段（都要满足），每段是几项（满足其一）：[[Term, ...], ...]。空项、空段去掉 """
    plan = []
    for chunk in to_unicode(query).lower().split():
        terms = [term for term in (parse_term(piece) for piece in chunk.split(ALTERNATIVE)) if term is not None]
        if terms:
            plan.append(terms)
    return plan


def _is_plain(segment):  # type: (list) -> bool
    """ 只有一项、比名字、不排除：这种段合起来交给拼音引擎 """
    return len(segment) == 1 and segment[0].Kind == KIND_NAME and not segment[0].Negate


def _loose(text):  # type: (any) -> unicode
    """ 模糊比较用：小写，去掉下划线、连字符、冒号、点这类符号 """
    return _SYMBOLS.sub(u"", to_unicode(text).lower())


def _in_order(needle, text):  # type: (unicode, unicode) -> bool
    """ needle 的字按顺序都在 text 里出现（不必连续）"""
    position = 0
    for char in needle:
        position = text.find(char, position) + 1
        if not position:
            return False
    return True


def _fuzzy(needle, texts):  # type: (unicode, dict) -> set
    """
    @ / $ 的模糊：texts 是 {键: 要比的字}，返回命中的键。去掉符号后连续包含的算；
    谁都不连续包含时退一步，按顺序出现也算 —— 先严后宽，免得宽的那一档把好结果淹掉
    """
    needle = _loose(needle)
    if not needle:
        return set(texts)
    loose = dict((key, _loose(text)) for key, text in texts.items())
    hits = set(key for key, text in loose.items() if needle in text)
    if hits:
        return hits
    return set(key for key, text in loose.items() if _in_order(needle, text))


def _spells_exactly(needle, text):  # type: (unicode, unicode) -> bool
    """ text 的拼音全拼（每个字任取一个读音，别的字原样）有没有一种正好等于 needle """
    parts = segments(text)
    failed = set()

    def _walk(position, index):
        if index == len(parts):
            return position == len(needle)
        if (position, index) in failed:
            return False
        seg, found = parts[index]
        for option in (found or (seg,)):
            option = option.lower()
            if needle.startswith(option, position) and _walk(position + len(option), index + 1):
                return True
        failed.add((position, index))
        return False

    return _walk(0, 0)


def _exact_name(needle, name):  # type: (unicode, any) -> bool
    """ & 整名相等：名字去掉空格后等于它，或名字的拼音全拼等于它 """
    text = u"".join(to_unicode(name).lower().split())
    return bool(text) and (needle == text or _spells_exactly(needle, text))


def _namespace(item):  # type: (any) -> unicode
    item_id = to_unicode(item.ItemId)
    return item_id.split(u":", 1)[0] if u":" in item_id else DEFAULT_NAMESPACE


def _id_text(item, full):  # type: (any, bool) -> unicode
    """ $ 比的字：冒号后面那段；查询里带冒号时比整个 ID """
    item_id = to_unicode(item.ItemId)
    return item_id if full or u":" not in item_id else item_id.split(u":", 1)[1]


class __ItemSearchIndex(object):  # noqa
    """ 物品搜索：「查询串 → Item」这一件事。名字走拼音/模糊索引，别的前缀现比 """

    def __init__(self):
        self._engine = PinyinIndex()  # type: PinyinIndex
        """
        拼音搜索索引。它索引的是 **ItemName 文本**而不是 Item ——
        所以 Search 拿回名字（就是喂进去的那个对象）后还要经 ItemManager 反查实例。
        """

        self._count = 0  # type: int
        """ 上次 Rebuild 喂进去的名字条数，只用于日志与判空 """

        self._version = -1  # type: int
        """
        建索引时的 ItemManager 版本号。与当前版本不一致就说明物品表变过，
        本索引已过期 —— 拉模型，物品表不需要认识我。
        """

        self._texts = {}  # type: dict
        """
        id(Item) -> (Item, 悬停文字：小写、去掉颜色码, 它的拼音连写)。# 用到才算；物品表一变就清。
        按实例记、不按 (ItemId, AuxValue)：附魔书、烟花这些同一个 id、aux 靠 userData 区分的，悬停文字各不一样。
        值里留着物品本身、取的时候核对是同一个实例（留着引用，这个 id 就不会被别的对象占用）
        """

    def Rebuild(self, items=None):  # type: (list or None) -> int
        """
        重建索引，返回索引到的名字条数；items 省略时取全部物品 —— 藏着的也收（物品栏选了「隐藏物品」时要搜得到），
        平时的结果里再滤掉（__ByName）
        """
        if items is None:
            items = ItemManager.GetItems()
        # 空名字要滤掉: Item.Info 取不到时会静默降级成空 ItemInfo(item.py:294),
        # 空条目喂进搜索引擎会变成一个能被任意查询命中的垃圾结果
        names = dedupe([item.Info.ItemName for item in items if item.Info.ItemName])
        self._engine.Clear()
        self._engine.Add(names)
        self._count = len(names)
        self._version = ItemManager.Version()
        self._texts.clear()
        logger.info("[MEI/search] 索引重建完成, {} 个名字 / {} 个物品".format(self._count, len(items)))
        return self._count

    def Search(self, query, include_hidden=False):  # type: (str, bool) -> list
        """
        按搜索语法找物品（模块说明），返回 Item 表。有普通名字段时按拼音引擎的分数排；没有时按可浏览表的顺序，
        段里有比名字的项（`铁|金`）就按它们的名次往前排。只打了前缀（还在输入）时给全部。索引过期会先自愈。
        include_hidden：藏着的物品也要（物品栏选了「隐藏物品」这类加法筛选时）
        """
        if self._version != ItemManager.Version():
            self.Rebuild()
        if not self._count:
            return []
        plan = parse_query(query)
        names = [segment[0].Text for segment in plan if _is_plain(segment)]
        filters = sorted((segment for segment in plan if not _is_plain(segment)),
                         key=lambda segment: max(COSTS[term.Kind] for term in segment))
        universe = (self.__ByName(u" ".join(names), include_hidden) if names
                    else ItemManager.GetBrowsableItems(include_hidden))
        if not filters:
            return universe
        cache = {}
        items = [item for item in universe if all(self.__Passes(segment, item, universe, cache) for segment in filters)]
        if names:
            return items
        return self.__RankByNames(items, filters, cache)

    def Count(self):  # type: () -> int
        return self._count

    def Clear(self):
        self._engine.Clear()
        self._count = 0
        self._texts.clear()
        # 版本号也要清: 否则下次 Search 看版本没变, 会认为空索引是最新的
        self._version = -1

    # 比对
# ======================================================================================================================
    def __ByName(self, query, include_hidden=False):  # type: (unicode, bool) -> list
        """
        拼音引擎搜名字，按分数排好的 Item 表（按实例去重；藏着的滤掉，include_hidden 时留着）。
        查询照原来收成 str 递过去（引擎两种都收）
        """
        names = self._engine.Search(native_str(query))
        if not names:
            return []
        items = []
        for name in names:
            items.extend(ItemManager.GetItemsByName(name))
        # 名字索引里有藏着的物品(全部物品都进索引), 平时的结果必须滤掉
        if not include_hidden:
            items = [item for item in items if not ItemManager.IsHidden(item)]
        # 按实例身份去重: 一个 Item 实例可能被多个搜索结果名索引到
        return dedupe(items, key=id)

    def __Passes(self, segment, item, universe, cache):  # type: (list, any, list, dict) -> bool
        """ 一段：几项里有一项满足（排除的项是「不命中」才算满足）"""
        for term in segment:
            if self.__Matches(term, item, universe, cache) != term.Negate:
                return True
        return False

    def __Matches(self, term, item, universe, cache):  # type: (Term, any, list, dict) -> bool
        if term.Kind == KIND_TEXT:
            return self.__TextMatches(term.Text, item)
        if term.Kind == KIND_EXACT:
            return _exact_name(term.Text, item.Info.ItemName)
        hits = cache.get(term.Key())
        if hits is None:
            hits = cache[term.Key()] = self.__Hits(term, universe)
        return id(item) in hits

    def __Hits(self, term, universe):  # type: (Term, list) -> any
        """ 名字 / 命名空间 / ID 一次算出这一次搜索里命中的实例（id(item) 的集合；名字给 {id: 名次}）"""
        if term.Kind == KIND_NAME:
            # 藏着的也算进名次：比的只是候选里的物品，候选本来就按 include_hidden 取过了
            return dict((id(item), rank) for rank, item in enumerate(self.__ByName(term.Text, True)))
        if term.Kind == KIND_NAMESPACE:
            spaces = _fuzzy(term.Text, dict((space, space) for space in set(_namespace(item) for item in universe)))
            return set(id(item) for item in universe if _namespace(item) in spaces)
        full = u":" in term.Text
        return _fuzzy(term.Text, dict((id(item), _id_text(item, full)) for item in universe))

    def __TextMatches(self, needle, item):  # type: (unicode, any) -> bool
        cached = self._texts.get(id(item))
        if cached is None or cached[0] is not item:
            try:
                text = _COLOR_CODE.sub(u"", to_unicode(item.HoverText)).lower()
            except Exception:  # noqa  悬停文字取不到（物品信息都没有）就当没有字
                text = u""
            cached = self._texts[id(item)] = (item, text, u"".join(lazy_pinyin(text)))
        return needle in cached[1] or needle in cached[2]

    def __RankByNames(self, items, filters, cache):  # type: (list, list, dict) -> list
        """ 没有普通名字段时：段里比名字、不排除的项按拼音引擎的名次排在前面，其余照可浏览表的顺序跟在后面（sorted 是稳定的）"""
        ranks = []
        for segment in filters:
            for term in segment:
                if term.Kind == KIND_NAME and not term.Negate:
                    if term.Key() not in cache:  # 这一项可能一次都没比到（同段前面的项已经满足了）
                        cache[term.Key()] = self.__Hits(term, items)
                    ranks.append(cache[term.Key()])
        if not ranks:
            return items
        return sorted(items, key=lambda item: min(rank.get(id(item), _LAST) for rank in ranks))


ItemSearchIndex = __ItemSearchIndex()
