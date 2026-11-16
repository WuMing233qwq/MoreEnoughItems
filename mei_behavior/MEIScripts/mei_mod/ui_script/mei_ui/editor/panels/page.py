# coding=utf-8
# ----------------------------------------------------------------------
#  page.py is part of MoreEnoughItems.
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
界面模式、没选积木时左栏的「页面」页签：名字、工作站（一个一行，「选」换、「删」删，「+ 工作站」加；点「选」再点物品栏）、
图标（单独设，清掉用第一个工作站）、内容区的宽高（步进 + 贴合积木）、这一页的数值字段、换预设排版、删除页面
"""
from MEIScripts.constants.texts import EditorText, UserText
from MEIScripts.mei_mod.state import UserRecipeManager
from MEIScripts.mei_mod.state.user_recipes import FIELDS, MAX_STATIONS, NAME_LENGTH, page_icon
from MEIScripts.utils.text import to_unicode

from ..form import BUTTONS, CHOICE, EDIT, ITEM, OFF, ON, RED, TEXT, FormRow, step_row
from ..modules import draft
from .palette import tabs

PRESET_NAMES = list(draft.PRESETS)

SIZE_STEP, SIZE_BIG_STEP = 2, 10
""" 内容区宽高的小步、大步 """


def rows(editor):  # type: (any) -> list
    page = editor.Draft
    stations = page.get("stations") or []
    result = [tabs(editor), FormRow(EDIT, "name", label=EditorText.Name, text=page.get("name") or u"")]
    for index, data in enumerate(stations):
        station = editor.Resolve(data)
        result.append(FormRow(ITEM, "station:{}".format(index), label=EditorText.Station if index == 0 else u"", item=station,
                              value=editor.ItemName(station) if station is not None else u"?",
                              buttons=[("pick", EditorText.Pick, ON if editor.PickStation == index else None),
                                       ("remove", EditorText.Remove, None)]))
    full = len(stations) >= MAX_STATIONS
    result.append(FormRow(BUTTONS, "stations", label=u"" if stations else EditorText.Station, buttons=[
        ("add", EditorText.AddStation, OFF if full else (ON if editor.PickStation == "new" else None))]))
    if editor.PickStation in ("new", "icon") or isinstance(editor.PickStation, int):
        result.append(FormRow(TEXT, label=EditorText.PickIconHint if editor.PickStation == "icon" else EditorText.PickStationHint))
    icon = editor.Resolve(page_icon(page))
    if page.get("icon"):
        icon_text = editor.ItemName(icon) if icon is not None else u"?"
    else:
        icon_text = EditorText.IconFirst if stations else u"—"
    result.append(FormRow(ITEM, "icon", label=EditorText.Icon, item=icon, value=icon_text,
                          buttons=[("pick", EditorText.Pick, ON if editor.PickStation == "icon" else None),
                                   ("clear", EditorText.Clear, None if page.get("icon") else OFF)]))
    width, height = draft.area(page)
    result.append(step_row("w", EditorText.Width, width, SIZE_STEP, SIZE_BIG_STEP))
    result.append(step_row("h", EditorText.Height, height, SIZE_STEP, SIZE_BIG_STEP))
    result.append(FormRow(BUTTONS, "fit", buttons=[("fit", EditorText.Fit, None if page.get("blocks") else OFF)]))
    result.append(FormRow(TEXT, label=EditorText.Fields))
    fields = page.get("fields") or []
    result.append(FormRow(BUTTONS, "fields", buttons=[(field, UserText.Fields[field][0], ON if field in fields else None)
                                                      for field in FIELDS]))
    result.append(FormRow(CHOICE, "preset", label=EditorText.Preset, value=EditorText.Presets.get(editor.PresetName, u""),
                          buttons=[("prev", u"<", None), ("next", u">", None)]))
    result.append(FormRow(BUTTONS, "apply", buttons=[
        ("apply", EditorText.Confirm if editor.Confirming("apply") else EditorText.Apply, None)]))
    saved = bool(page.get("id"))
    result.append(FormRow(BUTTONS, "delete", buttons=[
        ("delete", EditorText.Confirm if editor.Confirming("delete_page") else EditorText.DeletePage, RED if saved else OFF)]))
    return result


def _start_pick(editor, target):  # type: (any, any) -> None
    """ 「选」：等着点物品栏（target：第几个工作站 / "new" 加一个 / "icon" 图标）；再点一下同一个取消。开着时物品栏打开 """
    editor.PickStation = None if editor.PickStation == target else target
    editor.PickProp = None
    if editor.PickStation is not None:
        editor.OpenItems(True)


def act(editor, key, op, value):  # type: (any, str, str, any) -> bool
    page = editor.Draft
    if key == "name":
        text = to_unicode(value or u"")
        page["name"] = text.strip()[:NAME_LENGTH]
        editor.Changed(layout=False, form=False)
        return True
    if key.startswith("station:"):
        index = int(key.split(":", 1)[1])
        stations = page.setdefault("stations", [])
        if not 0 <= index < len(stations):
            return True
        if op == "pick":
            _start_pick(editor, index)
        else:
            del stations[index]
            editor.PickStation = None
            editor.Changed(layout=False)
        editor.Refresh()
        return True
    if key == "stations":
        if len(page.get("stations") or []) >= MAX_STATIONS:
            editor.Toast(EditorText.StationFull.format(MAX_STATIONS))
            return True
        _start_pick(editor, "new")
        editor.Refresh()
        return True
    if key == "icon":
        if op == "pick":
            _start_pick(editor, "icon")
        else:
            page["icon"] = None
            editor.PickStation = None
            editor.Changed(layout=False)
        editor.Refresh()
        return True
    if key in ("w", "h"):
        draft.resize(page, key, int(op))
        draft.clamp_all(page, editor.SizeOf)
        editor.Changed()
        return True
    if key == "fit":
        if draft.fit(page, editor.SizeOf):
            editor.Changed()
        return True
    if key == "fields":
        fields = page.setdefault("fields", [])
        if op in fields:
            fields.remove(op)
        else:
            fields.append(op)
        page["fields"] = [field for field in FIELDS if field in fields]
        editor.Changed()
        return True
    if key == "preset":
        index = PRESET_NAMES.index(editor.PresetName) if editor.PresetName in PRESET_NAMES else 0
        editor.PresetName = PRESET_NAMES[(index + (1 if op == "next" else -1)) % len(PRESET_NAMES)]
        editor.Refresh()
        return True
    if key == "apply":
        if not editor.Confirm("apply"):
            return True
        page["w"], page["h"], page["blocks"] = draft.preset(editor.PresetName)
        editor.Selected = None
        editor.Changed()
        return True
    if key == "delete":
        if not page.get("id") or not editor.Confirm("delete_page"):
            return True
        UserRecipeManager.DeletePage(page["id"])
        editor.Toast(EditorText.Deleted)
        editor.LoadPage(0)
        return True
    return False
