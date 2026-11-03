# coding=utf-8

# ----------------------------------------------------------------------
#  lang.py is part of MoreEnoughItems.
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
.lang 的键查成文字 —— **整个模组只有这一处向引擎要本地化文字、只有这一份缓存**：各处各记一张表，
同一个类型名就会在两个界面上是两样。
查到了才记着；接口抛了不记，下次再问。引擎给回键本身（这个键没有翻译）也记着 —— 除非本地化还没加载好（texts_ready 为假：
进存档时客户端重新加载资源包，那期间查什么都给回键本身），那时不记，加载好了再问。
引擎接口用到时才 import，这个模块离线也能 import
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str, to_unicode

_CACHE = {}  # 键（str）-> 文字（unicode）

PROBE_KEY = "item.diamond.name"
""" 问本地化加载好了没有用的原版键：各种语言都有翻译（钻石 / Diamond），查回来还是它自己就是还没加载好 """

PACK_PROBE_KEY = "mei.lang.probe"
"""
MEI 自己 .lang 里专门留的键：查得到说明这个存档的资源包（模组的物品名在这一层）的文字都加载好了。
只有 zh_CN.lang 有它 —— 别的语言下永远查不到，调用方要有退路（item_sync.py 退回等界面初始化）
"""


def _game():  # type: () -> any
    import mod.client.extraClientApi as clientApi
    return clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())


def texts_ready(key=PROBE_KEY):  # type: (str) -> bool
    """
    这个键查得到翻译了没有 —— 拿来问本地化加载好了没有。进存档时客户端要重新加载资源包（含 .lang），
    那期间引擎查什么都给回键本身，物品名（GetItemBasicInfo 的 itemName）也一样（CLAUDE.md 引擎结论 §51）。
    接口抛了当没好（调用方自己有等多久的上限）
    """
    try:
        text = _game().GetChinese(key)
    except Exception:  # noqa
        return False
    return isinstance(text, basestring) and bool(text) and text != key


def pack_texts_ready():  # type: () -> bool
    """ 这个存档的资源包（模组的物品名在这一层）文字加载好了没有：问 MEI 自己 .lang 里的键 """
    return texts_ready(PACK_PROBE_KEY)


def localize(key):  # type: (any) -> unicode
    """ 键 -> 文字（unicode）；空键给空串，取不到给键本身 """
    if not key:
        return u""
    key = native_str(key)
    text = _CACHE.get(key)
    if text is not None:
        return text
    try:
        text = _game().GetChinese(key)
    except Exception as e:  # noqa  取不到本地化文字就写键，不能让界面建不出来；不记着，下次再问
        logger.warn("[MEI/lang] 取不到 {} 的本地化文字: {}".format(key, error_text(e)))
        return to_unicode(key)
    text = to_unicode(text if isinstance(text, basestring) and text else key)
    if text == to_unicode(key) and not texts_ready():
        return text  # 本地化还没加载好：这次先给键本身，不记着
    _CACHE[key] = text
    return text
