# coding=utf-8
# ----------------------------------------------------------------------
#  image.py is part of MoreEnoughItems.
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
图片：一张贴图，路径玩家自己填（资源包里的，比如 textures/blocks/stone、textures/ui/arrow_large，不带 .png），宽高自己定、拉伸铺满。
路径不对引擎画它的缺图；没填的在编辑器里画一个问号
"""
from MEIScripts.api.facades.types import BlockProp, BlockType
from MEIScripts.mei_mod.state.user_recipes import HEIGHT_RANGE, WIDTH_RANGE
from MEIScripts.utils.text import native_str

BLANK = "textures/ui/mei/blank"
PATH_LENGTH = 96


def image_path(value):  # type: (any) -> str
    """ 玩家填的路径规整一下：去掉两头空白、反斜杠换正斜杠、去掉开头的 / 与结尾的 .png；不是 ASCII 给空串 """
    text = native_str(value or "").strip().replace("\\", "/").lstrip("/")
    try:
        text.decode("ascii")
    except UnicodeError:
        return ""
    if text.lower().endswith(".png"):
        text = text[:-4]
    return text


class ImageBlock(BlockType):

    TEMPLATE = {("size", ""): (16, 16), ("sprite", "/image"): BLANK, ("visible", "/missing"): False}

    def __init__(self):
        BlockType.__init__(self, "mei:image", name_key="mei.block.image", control_def="MeiBlocks.image", size=(16, 16),
                           limit=32, icon="textures/items/painting", sort_index=75, props=[
                               BlockProp("tex", BlockProp.TEXT, "mei.block.prop.texture", default=u"",
                                         max_length=PATH_LENGTH, ascii_only=True),
                               BlockProp("w", BlockProp.INT, "mei.block.prop.width", default=16, minimum=1, maximum=WIDTH_RANGE[1]),
                               BlockProp("h", BlockProp.INT, "mei.block.prop.height", default=16, minimum=1, maximum=HEIGHT_RANGE[1]),
                           ])

    def SizeOf(self, block):
        return int(block.get("w") or 16), int(block.get("h") or 16)

    def Paint(self, view):
        path = image_path(view.Data.get("tex"))
        view.SetSprite("/image", path or BLANK)
        view.SetVisible("/missing", view.Editing and not path)
