# coding=utf-8
# ----------------------------------------------------------------------
#  __init__.py is part of MoreEnoughItems.
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
编辑器左栏按状态出哪几行、点了交给谁：界面模式没选积木是控件池（palette）或页面设置（page），选了积木是它的属性（block）；
预览时只有一行说明；配方模式是配方与格子（recipe）。每个模块 rows(editor) 给行、act(editor, 键, op, 值) 认得就处理
"""
from MEIScripts.constants.texts import EditorText

from ..form import TEXT, FormRow
from . import block, page, palette, recipe


def _modules(editor):  # type: (any) -> tuple
    if editor.Mode == editor.RECIPE:
        return (recipe,)
    if editor.Selected is not None:
        return (block,)
    return (palette, page)


def rows(editor):  # type: (any) -> list
    if editor.Mode == editor.RECIPE:
        return recipe.rows(editor)
    if editor.Preview:
        return [FormRow(TEXT, label=EditorText.PreviewHint)]
    if editor.Selected is not None:
        return block.rows(editor)
    return page.rows(editor) if editor.LeftTab == "page" else palette.rows(editor)


def act(editor, key, op, value):  # type: (any, str, str, any) -> bool
    for module in _modules(editor):
        if module.act(editor, key, op, value):
            return True
    return False
