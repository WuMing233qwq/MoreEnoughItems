# coding=utf-8
# ----------------------------------------------------------------------
#  recipe.py is part of MoreEnoughItems.
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
配方模式的左栏：这一页的第几条（新建、删除）；选中一格时是这一格 —— 物品、数量（积木的单位是 mB 的按 mB 步进）、概率（产物）、填法（单个 / 候选 / 标签）、
清空；没选格子时是这条配方的数值字段与备注。催化剂是排版里定的角色（不消耗），这里不用另外设
"""
from MEIScripts.constants.texts import EditorText, UserText
from MEIScripts.mei_mod.state import UserRecipeManager
from MEIScripts.mei_mod.state.user_recipes import MAX_AMOUNT, NOTE_LENGTH, TAG_LENGTH
from MEIScripts.utils.text import to_unicode

from ..form import BUTTONS, CHOICE, EDIT, ITEM, OFF, RED, STEP, TEXT, TITLE, FormRow
from ..modules import draft

CHANCES = (1.0, 0.9, 0.75, 0.5, 0.33, 0.25, 0.1, 0.05, 0.01)
MODES = ("one", "alts", "tag")
FIELD = "f:"


def _number(text):  # type: (str) -> any
    """ 输入框里的数：整数、小数，别的给 None """
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value != value or abs(value) > 1e15:
        return None
    return int(value) if value == int(value) else value


def rows(editor):  # type: (any) -> list
    page, recipe = editor.RPage, editor.RDraft
    total = len(UserRecipeManager.Recipes(page["id"]))
    label = EditorText.RecipeOf.format(editor.RIndex + 1, total) if recipe.get("id") else EditorText.NewRecipe
    result = [FormRow(CHOICE, "recipe", value=label, buttons=[("prev", u"<", None if editor.RIndex > 0 else OFF),
                                                             ("next", u">", None)]),
              FormRow(BUTTONS, "rops", buttons=[
                  ("new", EditorText.Add, None),
                  ("delete", EditorText.Confirm if editor.Confirming("delete_recipe") else EditorText.DeleteRecipe,
                   RED if recipe.get("id") else OFF)])]
    holder = draft.holder_of(page["blocks"], editor.Cell, editor.Holds) if editor.Cell is not None else None
    if holder is None:
        result.append(FormRow(TEXT, label=EditorText.NoCellHint))
        if page.get("fields"):
            result.append(FormRow(TITLE, label=EditorText.Values))
            values = recipe.get("f") or {}
            for field in page["fields"]:
                name, unit = UserText.Fields.get(field, (field, u""))
                value = values.get(field)
                result.append(FormRow(EDIT, FIELD + field, label=name, text=u"" if value is None else str(value)))
        result.append(FormRow(EDIT, "note", label=EditorText.Note, text=recipe.get("note") or u""))
        return result
    role, number = holder
    entry = draft.cell(recipe, role, number)
    item = editor.Resolve(entry)
    result.append(FormRow(TITLE, label=u"{} {}".format(UserText.RoleName.get(role, u""), number + 1),
                          value=UserText.LoreCatalyst if role == "cat" else u""))
    result.append(FormRow(ITEM, "cell", item=item, value=editor.ItemName(item) if item is not None else EditorText.CellEmpty,
                          buttons=[("clear", EditorText.Clear, None if entry else OFF)]))
    if entry is None:
        result.append(FormRow(TEXT, label=EditorText.CellHint))
        return result
    fluid = editor.CellUnit() == "mB"
    small, big = (100, 1000) if fluid else (1, 10)
    count = entry.get("n", 1)
    result.append(FormRow(STEP, "count", label=EditorText.Count, value=str(count) if not fluid else u"{}".format(count),
                          buttons=[("-{}".format(big), u"-1k" if fluid else u"-10", None), ("-{}".format(small), u"-", None),
                                   ("+{}".format(small), u"+", None), ("+{}".format(big), u"+1k" if fluid else u"+10", None)]))
    if role == "out":
        chance = entry.get("chance", 1.0)
        result.append(FormRow(CHOICE, "chance", label=EditorText.Chance, value=u"{}%".format(int(round(chance * 100))),
                              buttons=[("prev", u"<", None), ("next", u">", None)]))
    mode = editor.CellMode()
    result.append(FormRow(CHOICE, "mode", label=EditorText.Fill, value=EditorText.FillModes[mode],
                          buttons=[("prev", u"<", None), ("next", u">", None)]))
    if mode == "tag":
        result.append(FormRow(EDIT, "tag", label=EditorText.Tag, text=entry.get("tag") or u""))
    elif mode == "alts":
        result.append(FormRow(TEXT, label=EditorText.AltsHint.format(1 + len(entry.get("alts") or ()))))
    result.append(FormRow(BUTTONS, "clear", buttons=[("clear", EditorText.ClearCell, RED)]))
    return result


def act(editor, key, op, value):  # type: (any, str, str, any) -> bool
    recipe = editor.RDraft
    if key == "recipe":
        editor.LoadRecipe(editor.RIndex + (1 if op == "next" else -1))
        return True
    if key == "rops":
        if op == "new":
            editor.LoadRecipe(len(UserRecipeManager.Recipes(editor.RPage["id"])))
        elif recipe.get("id") and editor.Confirm("delete_recipe"):
            UserRecipeManager.DeleteRecipe(recipe["id"])
            editor.Toast(EditorText.Deleted)
            editor.LoadRecipe(editor.RIndex, force=True)
        return True
    if key == "note" and op == "text":
        text = to_unicode(value or u"")
        recipe["note"] = text.strip()[:NOTE_LENGTH]
        editor.Changed(form=False)
        return True
    if key.startswith(FIELD) and op == "text":
        number = _number(value)
        fields = recipe.setdefault("f", {})
        if number is None:
            fields.pop(key[len(FIELD):], None)
        else:
            fields[key[len(FIELD):]] = number
        editor.Changed(form=False)
        return True
    holder = draft.holder_of(editor.RPage["blocks"], editor.Cell, editor.Holds) if editor.Cell is not None else None
    if holder is None:
        return False
    role, number = holder
    entry = draft.cell(recipe, role, number)
    if key in ("clear", "cell"):
        draft.set_cell(recipe, role, number, None)
        editor.SetCellMode("one")
        editor.Changed()
        return True
    if entry is None:
        return True
    if key == "count":
        entry["n"] = int(max(1, min(MAX_AMOUNT, int(entry.get("n", 1)) + int(op))))
    elif key == "chance":
        chance = entry.get("chance", 1.0)
        index = min(range(len(CHANCES)), key=lambda i: abs(CHANCES[i] - chance))
        chance = CHANCES[(index + (1 if op == "next" else -1)) % len(CHANCES)]
        if chance >= 1:
            entry.pop("chance", None)
        else:
            entry["chance"] = chance
    elif key == "mode":
        mode = MODES[(MODES.index(editor.CellMode()) + (1 if op == "next" else -1)) % len(MODES)]
        if mode != "alts":
            entry.pop("alts", None)
        if mode != "tag":
            entry.pop("tag", None)
        editor.SetCellMode(mode)
    elif key == "tag" and op == "text":
        text = to_unicode(value or u"").strip()
        try:
            text.encode("ascii")
        except UnicodeError:
            return True  # 标签名只有 ASCII（minecraft:logs 这样）：打到一半的中文不收
        if text:
            entry["tag"] = text[:TAG_LENGTH].encode("ascii")
        else:
            entry.pop("tag", None)
        editor.Changed(form=False)
        return True
    else:
        return False
    editor.Changed()
    return True
