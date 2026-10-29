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
import re

from .core import is_hanzi, segments, to_unicode

MAX_PINYIN_LEN = 6
""" 拼音、首字母索引只存这么长的片段；更长的查询取前缀那一桶，再逐条核对 """

MAX_TEXT_LEN = 4
""" 原文索引只存这么长的片段，同上 """

MAX_PATHS = 32
""" 一个名字最多展开多少种读音组合来打分：主读音那种在前，其后按换掉的字数从少到多 """

SYLLABLE_SCORE = 0.85
""" 逐字匹配（首字母 / 整个读音 / 读音前缀混着打）全部吃完时的满分，再乘吃掉的字数占比 """

_LETTERS = re.compile(u"^[a-z]+$")
_EMPTY = frozenset()


def expand(units, limit=MAX_PATHS):  # type: (list, int) -> list
    """ 每段挑一个候选拼成一串的全部拼法：第一个全取第一个候选，其后按换掉的段数从少到多，最多 limit 种 """
    base = [unit[0] for unit in units]
    paths = [u"".join(base)]
    poly = [index for index, unit in enumerate(units) if len(unit) > 1]
    seen = set(paths)
    for size in range(1, len(poly) + 1):
        for chosen in _choose(poly, size):
            for picks in _product([units[index][1:] for index in chosen]):
                parts = list(base)
                for index, pick in zip(chosen, picks):
                    parts[index] = pick
                path = u"".join(parts)
                if path in seen:
                    continue
                seen.add(path)
                paths.append(path)
                if len(paths) >= limit:
                    return paths
    return paths


def substrings(text, max_len):  # type: (unicode, int) -> set
    """ 一串字里所有不长于 max_len 的连续片段 """
    found = set()
    size = len(text)
    for start in range(size):
        for end in range(start + 1, min(start + max_len, size) + 1):
            found.add(text[start:end])
    return found


def windows(units, max_len):  # type: (list, int) -> set
    """ 各种拼法里所有不长于 max_len 的连续片段（只在片段跨过的几段里分叉，不展开整串）"""
    if all(len(unit) == 1 for unit in units):
        return substrings(u"".join(unit[0] for unit in units), max_len)
    found = set()
    count = len(units)
    for start in range(count):
        for alternative in units[start]:
            for offset in range(len(alternative)):
                stack = [(alternative[offset:offset + max_len], start + 1)]
                while stack:
                    text, index = stack.pop()
                    if len(text) >= max_len or index >= count:
                        for end in range(1, len(text) + 1):
                            found.add(text[:end])
                        continue
                    for following in units[index]:
                        stack.append(((text + following)[:max_len], index + 1))
    return found


def _choose(items, size):
    if size == 0:
        yield ()
        return
    for index in range(len(items) - size + 1):
        for rest in _choose(items[index + 1:], size - 1):
            yield (items[index],) + rest


def _product(groups):
    if not groups:
        yield ()
        return
    for head in groups[0]:
        for rest in _product(groups[1:]):
            yield (head,) + rest


def _has_hanzi(text):  # type: (unicode) -> bool
    for char in text:
        if is_hanzi(char):
            return True
    return False


def _split_mixed(text):  # type: (unicode) -> tuple
    """ 按汉字 / 非汉字切成连续的几段，返回 (汉字段, 其余段) """
    hanzi, others = [], []
    current, kind = u"", None
    for char in text:
        now = "hanzi" if is_hanzi(char) else "other"
        if kind is not None and now != kind and current:
            (hanzi if kind == "hanzi" else others).append(current)
            current = u""
        kind = now
        current += char
    if current:
        (hanzi if kind == "hanzi" else others).append(current)
    return hanzi, others


def _weight(part):  # type: (unicode) -> float
    if _has_hanzi(part):
        return 1.2
    if len(part) <= 2:
        return 0.8
    return 1.0


def _score_text(text, query):  # type: (unicode, unicode) -> float
    if query == text:
        return 1.0
    pos = text.find(query)
    if pos < 0:
        return 0.0
    return 0.7 if pos == 0 else 0.7 * len(query) / float(len(text))


def _score_contained(paths, query, head, rest):  # type: (list, unicode, float, float) -> float
    """
    query 是拼法的片段：开头命中给 head × 占比，中间命中给 rest × 占比。
    主读音那种拼法（paths[0]）含它就按它算，不含才看别的拼法、取最高的
    """
    pos = paths[0].find(query)
    if pos >= 0:
        return (head if pos == 0 else rest) * len(query) / float(len(paths[0]))
    score = 0.0
    for index in range(1, len(paths)):
        pos = paths[index].find(query)
        if pos >= 0:
            score = max(score, (head if pos == 0 else rest) * len(query) / float(len(paths[index])))
    return score


def _is_subsequence(query, text):  # type: (unicode, unicode) -> bool
    index = 0
    for char in query:
        pos = text.find(char, index)
        if pos < 0:
            return False
        index = pos + 1
    return True


def _is_subsequence_of_any(query, units):  # type: (unicode, list) -> bool
    """ query 是不是某种拼法的子序列：每段取吃掉最多的那个候选（吃得越多，后面越不会错过），一遍走完 """
    size = len(query)
    if not size:
        return True
    at = 0
    for unit in units:
        best = at
        for alternative in unit:
            pos = at
            for char in alternative:
                if char == query[pos]:
                    pos += 1
                    if pos == size:
                        return True
            if pos > best:
                best = pos
        at = best
    return False


def _match_syllables(query, units):  # type: (unicode, list) -> int
    """
    query 能不能从第一段起，每段按「首字母 / 整个读音 / 至少两个字母的读音前缀」吃一截，把 query 吃完；
    多音字的每个读音都试。返回吃完时用了几段，0 是吃不完
    """
    if not query or not units:
        return 0
    return _match_from(query, 0, units, 0, set())


def _match_from(query, qi, units, si, failed):  # type: (unicode, int, list, int, set) -> int
    if qi >= len(query):
        return si
    if si >= len(units) or (qi, si) in failed:
        return 0
    char = query[qi]
    for syllable in units[si]:
        if not syllable or syllable[0] != char:
            continue
        result = _match_from(query, qi + 1, units, si + 1, failed)
        if result > 0:
            return result
        size, limit = 2, min(len(syllable), len(query) - qi)
        while size <= limit and query[qi + size - 1] == syllable[size - 1]:
            result = _match_from(query, qi + size, units, si + 1, failed)
            if result > 0:
                return result
            size += 1
    failed.add((qi, si))
    return 0


def _initials(found):  # type: (tuple) -> tuple
    """ 几个读音的首字母，去重、保持先后 """
    result = []
    for reading in found:
        if reading[0] not in result:
            result.append(reading[0])
    return tuple(result)


class _Entry(object):
    """
    一条被索引的字：原样的对象、小写的字，各段的读音候选与展开好的几种拼法
    """
    __slots__ = ("Item", "Name", "Text", "Units", "Initials", "Paths", "Letters")

    def __init__(self, item):
        self.Item = item
        self.Name = to_unicode(item)  # type: unicode
        self.Text = self.Name.lower()  # type: unicode
        units, initials = [], []
        for seg, found in segments(self.Text):
            units.append(found or (seg,))
            initials.append(_initials(found) if found else (seg,))
        self.Units = units  # type: list  # 每段的候选：有读音的字是它的全部读音，其余是那一截原文
        self.Initials = initials  # type: list  # 每段的首字母候选，其余那一截原样
        self.Paths = expand(units)  # type: list  # 连起来的拼音，[0] 是全取主读音的
        self.Letters = expand(initials)  # type: list  # 首字母串，[0] 是全取主读音的


class PinyinIndex(object):
    """
    拼音 / 首字母 / 原文的模糊搜索索引；多音字的每个读音都能搜到
    """
    def __init__(self):
        self.__Entries = []  # type: list
        self.__Pinyin = {}  # type: dict  # 拼音片段 → 条目下标
        self.__Letters = {}  # type: dict  # 首字母片段 → 条目下标
        self.__Text = {}  # type: dict  # 原文（小写）片段 → 条目下标
        self.__Heads = {}  # type: dict  # 第一段的首字母 → 条目下标

    def Add(self, items):  # type: (list) -> None
        """ 加一批字（str 或 unicode）；Search 返回的就是这里给的对象 """
        for item in items:
            entry = _Entry(item)
            doc = len(self.__Entries)
            self.__Entries.append(entry)
            heads = set(reading[0] for reading in entry.Units[0] if reading) if entry.Units else ()
            for index, keys in ((self.__Pinyin, windows(entry.Units, MAX_PINYIN_LEN)),
                                (self.__Letters, windows(entry.Initials, MAX_PINYIN_LEN)),
                                (self.__Text, substrings(entry.Text, MAX_TEXT_LEN)),
                                (self.__Heads, heads)):
                for key in keys:
                    bucket = index.get(key)
                    if bucket is None:
                        index[key] = {doc}
                    else:
                        bucket.add(doc)

    def Search(self, query, min_score=0.0):  # type: (any, float) -> list
        """ 搜索，按分数从高到低返回 Add 时给的对象（同名的只留一个）；空格隔开的几个词要都命中 """
        query = to_unicode(query).strip().lower()
        parts = query.split()
        if not parts:
            return []
        found = [self.__SearchPart(part) for part in parts]
        common = set(found[0])
        for result in found[1:]:
            common &= set(result)
        if not common:
            return []
        compact = query.replace(u" ", u"")
        weights = [_weight(part) for part in parts]
        scored = []
        for doc in common:
            total, scores = 0.0, []
            for index in range(len(parts)):
                score = found[index].get(doc, 0.0)
                scores.append(score)
                total += score * weights[index]
            bonus = 0.1 if all(score > 0.7 for score in scores) else 0.0
            if compact == self.__Entries[doc].Text:
                bonus += 0.2
            final = min(1.0, total / len(parts) + bonus)
            if final >= min_score:
                scored.append((final, doc))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        seen, items = set(), []
        for _, doc in scored:
            entry = self.__Entries[doc]
            if entry.Name not in seen:
                seen.add(entry.Name)
                items.append(entry.Item)
        return items

    def Count(self):  # type: () -> int
        return len(self.__Entries)

    def Clear(self):
        del self.__Entries[:]
        self.__Pinyin.clear()
        self.__Letters.clear()
        self.__Text.clear()
        self.__Heads.clear()

    def __Find(self, index, key, max_len, field):  # type: (dict, unicode, int, str) -> set
        """ 查一个片段；比索引存的长时取前缀那一桶，再按 field（Text / Paths / Letters）逐条核对。返回的集合不许改 """
        if len(key) <= max_len:
            return index.get(key, _EMPTY)
        result = set()
        for doc in index.get(key[:max_len], _EMPTY):
            value = getattr(self.__Entries[doc], field)
            if field == "Text":
                hit = key in value
            else:
                hit = any(key in path for path in value)
            if hit:
                result.add(doc)
        return result

    def __SearchPart(self, part):  # type: (unicode) -> dict
        """ 一个词命中了哪些条目、各多少分 """
        results = {}
        chinese = _has_hanzi(part)
        letters = bool(_LETTERS.match(part))
        hanzi_part = pinyin_part = None
        mixed = False
        candidates = set()
        pinyin_hits = letter_hits = head_hits = _EMPTY
        if chinese:
            hanzi, others = _split_mixed(part)
            if hanzi and others:
                hanzi_part, pinyin_part, mixed = hanzi[0], others[0], True
                text_hits = self.__Find(self.__Text, hanzi_part, MAX_TEXT_LEN, "Text")
                candidates.update(text_hits & self.__Find(self.__Pinyin, pinyin_part, MAX_PINYIN_LEN, "Paths"))
                candidates.update(text_hits & self.__Find(self.__Letters, pinyin_part, MAX_PINYIN_LEN, "Letters"))
            elif hanzi:
                hanzi_part = hanzi[0]
                candidates.update(self.__Find(self.__Text, hanzi_part, MAX_TEXT_LEN, "Text"))
        elif letters:
            pinyin_hits = self.__Find(self.__Pinyin, part, MAX_PINYIN_LEN, "Paths")
            letter_hits = self.__Find(self.__Letters, part, MAX_PINYIN_LEN, "Letters")
            head_hits = self.__Heads.get(part[0], _EMPTY)
            candidates.update(pinyin_hits)
            candidates.update(letter_hits)
            candidates.update(head_hits)
        else:
            candidates.update(self.__Find(self.__Text, part, MAX_TEXT_LEN, "Text"))

        for doc in candidates:
            entry = self.__Entries[doc]
            score = 0.0
            if mixed:
                score = self.__ScoreMixed(entry, hanzi_part, pinyin_part)
            if not letters:
                score = max(score, _score_text(entry.Text, part))
            else:
                score = self.__ScorePinyin(entry, part, doc in pinyin_hits, doc in letter_hits, doc in head_hits)
            if score > 0:
                if len(entry.Name) < 3:
                    score *= 0.9
                results[doc] = min(1.0, score)
        return results

    @staticmethod
    def __ScoreMixed(entry, hanzi_part, pinyin_part):  # type: (_Entry, unicode, unicode) -> float
        hanzi_score = _score_text(entry.Text, hanzi_part) if hanzi_part else 0.0
        pinyin_score = 0.0
        if pinyin_part:
            if pinyin_part in entry.Paths:
                pinyin_score = 1.0
            else:
                pinyin_score = _score_contained(entry.Paths, pinyin_part, 0.9, 0.7)
                if not pinyin_score:
                    pinyin_score = _score_contained(entry.Letters, pinyin_part, 0.7, 0.5)
        if hanzi_score > 0 and pinyin_score > 0:
            return min(1.0, 0.5 * (hanzi_score + pinyin_score))
        return max(hanzi_score, pinyin_score)

    @staticmethod
    def __ScorePinyin(entry, part, in_pinyin, in_letters, in_heads):  # type: (_Entry, unicode, bool, bool, bool) -> float
        """
        拼音词的分：整串相同 1.0 > 拼音片段 > 首字母整串 0.8 > 首字母片段 > 子序列 0.4 × 占比；逐字匹配最高 SYLLABLE_SCORE。
        in_* 是检索时它在不在拼音桶 / 首字母桶 / 首段那一桶里 —— 不在就不可能有那一项分，省得逐个拼法扫
        """
        score = 0.0
        if in_pinyin:
            if part in entry.Paths:
                return 1.0
            score = _score_contained(entry.Paths, part, 0.9, 0.7)
            if score >= SYLLABLE_SCORE:
                return score
        if in_letters:
            if part in entry.Letters:
                score = max(score, 0.8)
            score = max(score, _score_contained(entry.Letters, part, 0.7, 0.5))
        if in_heads and score < SYLLABLE_SCORE:
            matched = _match_syllables(part, entry.Units)
            if matched > 0:
                score = max(score, SYLLABLE_SCORE * matched / float(len(entry.Units)))
        primary = entry.Paths[0]
        if primary:
            loose = 0.4 * len(part) / float(len(primary))
            if score < loose and (_is_subsequence(part, primary) or
                                  len(entry.Paths) > 1 and _is_subsequence_of_any(part, entry.Units)):
                score = loose
        return score
