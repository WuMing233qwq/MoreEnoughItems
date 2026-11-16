# coding=utf-8
# ----------------------------------------------------------------------
#  palette.py is part of MoreEnoughItems.
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
界面模式、没选积木时左栏的「控件」页签：控件池 —— 登记的每种积木一格（MEI 自带的与第三方经 ctx.UI.Blocks 登记的都在），
写着这一页用了几块、最多几块，用完了灰掉（这一种用完了，或者一页的积木满了）；点一下放一块
"""
from MEIScripts.constants.texts import EditorText
from MEIScripts.mei_mod.state.user_recipes import MAX_BLOCKS
from MEIScripts.registry.blocks import BlockRegistry
from MEIScripts.utils.lang import localize

from ..form import BUTTONS, OFF, ON, TEXT, TILE, FormRow
from ..modules import draft

TAB = "tab"
ADD = "add:"


def tabs(editor):  # type: (any) -> FormRow
    """ 控件 / 页面两个页签 """
    return FormRow(BUTTONS, TAB, buttons=[("blocks", EditorText.TabBlocks, ON if editor.LeftTab == "blocks" else None),
                                          ("page", EditorText.TabPage, ON if editor.LeftTab == "page" else None)])


def rows(editor):  # type: (any) -> list
    result = [tabs(editor)]
    used = draft.counts(editor.Draft.get("blocks"))
    full = len(editor.Draft.get("blocks") or ()) >= MAX_BLOCKS
    for block_type in BlockRegistry.List():
        count = used.get(block_type.Id, 0)
        result.append(FormRow(TILE, ADD + block_type.Id, label=localize(block_type.NameKey),
                              value=u"{}/{}".format(count, block_type.Limit), icon=block_type.Icon,
                              buttons=[("add", u"", OFF if full or count >= block_type.Limit else None)]))
    if full:
        result.append(FormRow(TEXT, label=EditorText.BlocksFull.format(MAX_BLOCKS)))
    result.append(FormRow(TEXT, label=EditorText.PaletteHint))
    return result


def act(editor, key, op, _value):  # type: (any, str, str, any) -> bool
    """ 认得这个键就处理、给 True """
    if key == TAB:
        editor.LeftTab = op
        editor.Refresh()
        return True
    if key.startswith(ADD):
        editor.AddBlock(key[len(ADD):])
        return True
    return False
