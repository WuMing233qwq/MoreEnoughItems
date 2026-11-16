# coding=utf-8
# ----------------------------------------------------------------------
#  block.py is part of MoreEnoughItems.
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
界面模式、选中一块积木时左栏是它的属性：位置（横 / 纵）、装东西的积木的角色，再按积木声明的属性（BlockProp）一项一行 ——
整数是步进、选一个是左右切换、开关是开 / 关、一行字是输入框、字段是这一页的字段里选一个、
物品是两行（画着的物品 + 选 / 清，下面一个输入框打「命名空间:名字[:附加值]」）；最后复制、删除、完成
"""
from MEIScripts.common.classes.types.block import ROLES, BlockProp, item_text, parse_item
from MEIScripts.constants.texts import EditorText, UserText
from MEIScripts.mei_mod.state.user_recipes import MAX_BLOCKS
from MEIScripts.utils.lang import localize
from MEIScripts.utils.text import to_unicode

from ..form import BUTTONS, CHOICE, EDIT, ITEM, OFF, ON, RED, TITLE, FormRow, step_row
from ..modules import draft

POS_STEP = 5
""" 位置的大步（小步 1）"""

PROP = "p:"


def _choice(key, label, value):
    return FormRow(CHOICE, key, label=label, value=value, buttons=[("prev", u"<", None), ("next", u">", None)])


def rows(editor):  # type: (any) -> list
    block = editor.Draft["blocks"][editor.Selected]
    block_type = editor.TypeOf(block)
    if block_type is None:
        return []
    title = u"{} #{}".format(localize(block_type.NameKey), editor.Selected + 1)
    holder = draft.holder_of(editor.Draft["blocks"], editor.Selected, editor.Holds)
    result = [FormRow(TITLE, label=title, value=editor.HolderLabel(holder)),
              step_row("x", EditorText.X, block.get("x", 0), 1, POS_STEP),
              step_row("y", EditorText.Y, block.get("y", 0), 1, POS_STEP)]
    if block_type.Holds:
        result.append(_choice("role", EditorText.Role, UserText.RoleName.get(block.get("role"), u"")))
    for prop in block_type.Props:
        result.extend(_prop_rows(editor, prop, block.get(prop.Key, prop.Default)))
    room = block_type.Limit > draft.counts(editor.Draft["blocks"]).get(block_type.Id, 0)         and len(editor.Draft["blocks"]) < MAX_BLOCKS
    result.append(FormRow(BUTTONS, "ops", buttons=[("copy", EditorText.Copy, None if room else OFF),
                                                   ("delete", EditorText.Delete, RED),
                                                   ("done", EditorText.Done, None)]))
    return result


def _same_item(a, b):  # type: (dict, dict) -> bool
    return a is not None and b is not None and a.get("id") == b.get("id") and a.get("aux", 0) == b.get("aux", 0)


def _prop_rows(editor, prop, value):  # type: (any, BlockProp, any) -> list
    key, label = PROP + prop.Key, localize(prop.NameKey)
    if prop.Kind == BlockProp.INT:
        return [step_row(key, label, value, prop.Step, prop.Step * 5)]
    if prop.Kind == BlockProp.BOOL:
        return [_choice(key, label, EditorText.On if value else EditorText.Off)]
    if prop.Kind == BlockProp.TEXT:
        return [FormRow(EDIT, key, label=label, text=value or u"")]
    if prop.Kind == BlockProp.FIELD:
        return [_choice(key, label, UserText.Fields.get(value, (EditorText.NoField,))[0] if value else EditorText.NoField)]
    if prop.Kind == BlockProp.ITEM:
        data = parse_item(value)
        item = editor.Resolve(data) if data is not None else None
        name = editor.ItemName(item) if item is not None else (EditorText.ItemMissing if data is not None else u"—")
        picking = editor.PickProp == (editor.Selected, prop.Key)
        typed = editor.Typed.get((editor.Selected, prop.Key))
        text = typed if typed is not None and _same_item(parse_item(typed), data) else item_text(data)
        return [FormRow(ITEM, key, label=label, item=item, value=name,
                        buttons=[("pick", EditorText.Pick, ON if picking else None),
                                 ("clear", EditorText.Clear, None if data is not None else OFF)]),
                FormRow(EDIT, key, text=text)]
    return [_choice(key, label, localize(prop.LabelOf(value)))]


def _ascii(text):  # type: (unicode) -> bool
    try:
        text.encode("ascii")
    except UnicodeError:
        return False
    return True


def _act_item(editor, block, block_type, prop, op, value):  # type: (any, dict, any, BlockProp, str, any) -> bool
    """ 物品属性：选（再点物品栏）、清、打字（打成形了才收，打到一半、带中文的不收）"""
    index = editor.Selected
    if op == "pick":
        editor.StartPick((index, prop.Key))
        return True
    if op == "clear":
        block[prop.Key] = None
        editor.Typed.pop((index, prop.Key), None)
        editor.Changed()
        return True
    if op != "text":
        return True
    text = to_unicode(value or u"").strip()
    if not _ascii(text):
        return True
    if not text:
        block[prop.Key] = None
    else:
        data = parse_item(text)
        if data is None:
            return True
        block[prop.Key] = prop.Normalize(data)
    editor.Typed[(index, prop.Key)] = text
    editor.Changed()
    return True


def _cycle(values, value, forward):  # type: (list, any, bool) -> any
    if not values:
        return value
    index = values.index(value) if value in values else -1
    return values[(index + (1 if forward else -1)) % len(values)]


def act(editor, key, op, value):  # type: (any, str, str, any) -> bool
    blocks = editor.Draft["blocks"]
    index = editor.Selected
    if index is None or not 0 <= index < len(blocks):
        return False
    block = blocks[index]
    block_type = editor.TypeOf(block)
    if block_type is None:
        return False
    if key in ("x", "y"):
        block[key] = int(block.get(key) or 0) + int(op)
        draft.clamp(block, block_type.SizeOf(block), draft.area(editor.Draft))
        editor.Changed()
        return True
    if key == "role":
        block["role"] = _cycle(list(ROLES), block.get("role"), op == "next")
        editor.Changed()
        return True
    if key == "ops":
        if op == "copy":
            editor.CopyBlock(index)
        elif op == "delete":
            draft.remove_block(editor.Draft, index)
            editor.Selected = None
            editor.Changed()
        else:
            editor.Selected = None
            editor.Refresh()
        return True
    if not key.startswith(PROP):
        return False
    prop = block_type.Prop(key[len(PROP):])
    if prop is None:
        return False
    current = block.get(prop.Key, prop.Default)
    forward = op in ("next",) or (op or u"").startswith("+")
    if prop.Kind == BlockProp.ITEM:
        return _act_item(editor, block, block_type, prop, op, value)
    if prop.Kind == BlockProp.TEXT and op == "text" and prop.Ascii and not _ascii(to_unicode(value or u"")):
        return True  # 只收 ASCII 的（贴图路径）：打到一半的中文不收
    if prop.Kind == BlockProp.INT:
        current = prop.Normalize(int(current or 0) + int(op))
    elif prop.Kind == BlockProp.BOOL:
        current = not current
    elif prop.Kind == BlockProp.TEXT:
        if op != "text":
            return True
        text = to_unicode(value or u"")
        current = prop.Normalize(text)
        block[prop.Key] = current
        draft.clamp(block, block_type.SizeOf(block), draft.area(editor.Draft))
        editor.Changed(form=False)
        return True
    elif prop.Kind == BlockProp.FIELD:
        current = _cycle([""] + list(editor.Draft.get("fields") or []), current or "", forward)
    else:
        current = _cycle(prop.Values(), current, forward)
    block[prop.Key] = current
    draft.clamp(block, block_type.SizeOf(block), draft.area(editor.Draft))
    editor.Changed()
    return True
