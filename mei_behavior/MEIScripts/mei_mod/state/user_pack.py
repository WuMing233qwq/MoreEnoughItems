# coding=utf-8
# ----------------------------------------------------------------------
#  user_pack.py is part of MoreEnoughItems.
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
自制配方的一包（一个分组：名字、介绍、页面、配方，UserRecipeManager.ExportGroup 的样子）↔ 剪贴板里的一串字（docs/architecture/user_recipes.md §22）。
纯逻辑，零引擎依赖。

    MEI-RECIPES:1:<base64(JSON)>        不压缩
    MEI-RECIPES:1z:<base64(zlib(JSON))> 压缩（zlib 在、而且 JSON 够长时）

JSON 只有 ASCII（中文写成 \\uXXXX），base64 走 utils/b64.py。标准库被裁过（引擎结论 §8）：zlib 没核实过在不在 ——
写的时候没有就不压缩；读到压缩的、这台设备又没有 zlib，给 ERR_ZLIB（让对方在别的设备上导出，或者那边也没有 zlib 时本来就是不压缩的）。
读的时候前缀前后夹着别的字（聊天软件转发时带的）也认，base64 中间的空白跳过。
剪贴板里的字是别人给的：整串超过 MAX_TEXT、解出来（含解压）超过 MAX_JSON 的不认（ERR_BIG）—— 几十 KB 的压缩包能解出几十 MB；
解出来的逗号比正常的一包密得多的（几百万个小数字、短字串那种，解开的对象能占几百 MB）也不认
"""
import json

from MEIScripts.utils import b64
from MEIScripts.utils.text import to_native

PREFIX = "MEI-RECIPES:"
FORMAT = 1
""" 一包的格式版本：读到比它新的给 ERR_NEWER """

COMPRESS_OVER = 2048
""" JSON 比这长才压缩（短的压了也省不了几个字）"""

MAX_TEXT = 8 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
""" 剪贴板里的字最长多少、解出来的 JSON 最大多少（本地一个分组满额约 16 MB）"""

COMMA_EVERY = 6
""" 解出来的 JSON 里平均几个字才许有一个逗号：正常的一包十几个字一个（一格物品 {"aux":0,"id":"…","n":1} 就有二十几个字）"""

ERR_NONE, ERR_NEWER, ERR_BROKEN, ERR_ZLIB, ERR_BIG = "none", "newer", "broken", "zlib", "big"
""" 剪贴板里没有 MEI 的一包、格式比这一版新、数据坏了、压缩的解不开（这台设备没有 zlib）、太大了 """

_BASE64_CHARS = set(b64.ALPHABET + "=" + " \t\r\n")


def _zlib():
    try:
        import zlib
        return zlib if callable(getattr(zlib, "compress", None)) and callable(getattr(zlib, "decompress", None)) else None
    except Exception:  # noqa  标准库被裁掉了
        return None


def encode_pack(pack):  # type: (dict) -> str
    """ 一包 → 一串字 """
    text = json.dumps(pack, sort_keys=True, separators=(",", ":"))
    zlib = _zlib()
    if zlib is not None and len(text) > COMPRESS_OVER:
        try:
            return "{}{}z:{}".format(PREFIX, FORMAT, b64.encode(zlib.compress(text, 9)))
        except Exception:  # noqa  压不了就不压
            pass
    return "{}{}:{}".format(PREFIX, FORMAT, b64.encode(text))


def decode_pack(text):  # type: (any) -> tuple
    """ 一串字 → (一包, 错误)：认出来了是 (dict, None)，否则 (None, ERR_*) """
    if not isinstance(text, basestring):
        return None, ERR_NONE
    if len(text) > MAX_TEXT:
        return None, ERR_BIG
    if isinstance(text, unicode):
        text = text.encode("utf-8")
    start = text.find(PREFIX)
    if start < 0:
        return None, ERR_NONE
    head, sep, body = text[start + len(PREFIX):].partition(":")
    if not sep:
        return None, ERR_BROKEN
    compressed = head.endswith("z")
    try:
        version = int(head[:-1] if compressed else head)
    except ValueError:
        return None, ERR_BROKEN
    if version > FORMAT:
        return None, ERR_NEWER
    end = 0
    while end < len(body) and body[end] in _BASE64_CHARS:
        if body[end] == "=":  # 补位的 = 之后就不是这一包了
            while end < len(body) and body[end] == "=":
                end += 1
            break
        end += 1
    raw = b64.decode(body[:end])
    if not raw:
        return None, ERR_BROKEN
    if compressed:
        zlib = _zlib()
        if zlib is None or not callable(getattr(zlib, "decompressobj", None)):
            return None, ERR_ZLIB
        try:
            inflater = zlib.decompressobj()
            raw = inflater.decompress(raw, MAX_JSON)  # 解到上限就停：压缩炸弹解不满内存
            if inflater.unconsumed_tail:
                return None, ERR_BIG
        except Exception:  # noqa
            return None, ERR_BROKEN
    if len(raw) > MAX_JSON:
        return None, ERR_BIG
    if len(raw) > 65536 and raw.count(",") * COMMA_EVERY > len(raw):
        return None, ERR_BIG  # 塞满小值的：解开要占的内存比字数大一个数量级
    try:
        pack = to_native(json.loads(raw))
    except Exception:  # noqa  坏的、嵌套太深的
        return None, ERR_BROKEN
    if not isinstance(pack, dict) or not isinstance(pack.get("pages"), list):
        return None, ERR_BROKEN
    return pack, None
