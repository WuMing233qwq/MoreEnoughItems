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
查到了（引擎给回键本身也算）才记着；接口抛了不记，下次再问。引擎接口用到时才 import，这个模块离线也能 import
"""
from MEIScripts.utils.log import logger
from MEIScripts.utils.text import error_text, native_str, to_unicode

_CACHE = {}  # 键（str）-> 文字（unicode）


def localize(key):  # type: (any) -> unicode
    """ 键 -> 文字（unicode）；空键给空串，取不到给键本身 """
    if not key:
        return u""
    key = native_str(key)
    text = _CACHE.get(key)
    if text is not None:
        return text
    try:
        import mod.client.extraClientApi as clientApi
        game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        text = game.GetChinese(key)
    except Exception as e:  # noqa  取不到本地化文字就写键，不能让界面建不出来；不记着，下次再问
        logger.warn("[MEI/lang] 取不到 {} 的本地化文字: {}".format(key, error_text(e)))
        return to_unicode(key)
    text = to_unicode(text if isinstance(text, basestring) and text else key)
    _CACHE[key] = text
    return text
