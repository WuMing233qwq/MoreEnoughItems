# coding=utf-8
# ----------------------------------------------------------------------
#  panels.py is part of MoreEnoughItems.
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
管理器两栏按状态出哪几行（表单是编辑器那一套，editor/form.py）：
- 左栏：本地分组一列（一个分组一格，点了选中；正在给页面挪窝时点了就是挪过去）+「新建分组」「导入」；
  下面「服务器共享」：服务器上的分组一格一个（订阅了的、统一的、自己的标出来；服务器上没了的订阅照样列着）+「刷新」。
- 右栏，本地分组：名字、介绍、开关（启用、共享）、上传的状态，下面一个页面一行（图标、名字、几条配方，「移」「改」），最下面「导出」「解散」「删除」。
- 右栏，服务器上的分组：上传者、介绍、版本，订阅 / 启用，操作员的「统一配方」，「复制到本地」「从服务器删除」，订阅了的列出页面（只读）。
行的键：左栏 "group:<分组 Id>"、"local"、"server:<服务器上的键>"、"servers"；右栏 "name"、"desc"、"flags"、"page:<页面 Id>"、"group"、
"sub"、"op"、"remote"。点了交给 ManagerScript.OnLeft / OnRight
"""
from MEIScripts.constants.texts import ManagerText
from MEIScripts.constants.ui import ManagerConst
from MEIScripts.mei_mod.client.share import DONE, FAILED, ShareClient
from MEIScripts.mei_mod.state import BookmarkResolver, UserRecipeManager, UserShareManager
from MEIScripts.mei_mod.state.user_recipes import DEFAULT_GROUP, DESC_LENGTH, NAME_LENGTH, page_icon
from MEIScripts.utils.text import native_str

from ..editor.form import BUTTONS, EDIT, ITEM, OFF, ON, RED, TEXT, TILE, TITLE, FormRow

GROUP = "group:"
PAGE = "page:"
SERVER = "server:"

MUTE = (0.6, 0.62, 0.66)
WARN = (1.0, 0.8, 0.45)
HINT = (0.55, 0.85, 1.0)


def text(value):  # type: (any) -> unicode
    """ 一律 unicode（存储读回来的是 utf-8 的字节串）"""
    if isinstance(value, unicode):
        return value
    return native_str(value or "").decode("utf-8", "replace")


def group_name(group):  # type: (dict) -> unicode
    if group["id"] == DEFAULT_GROUP:
        return ManagerText.DefaultName
    return text(group.get("name")) or ManagerText.Unnamed


def page_name(page):  # type: (dict) -> unicode
    return text(page.get("name")) or ManagerText.UnnamedPage


def edit_text(view, key, stored, limit):  # type: (any, str, any, int) -> unicode
    """ 输入框里写什么：玩家打的字规整完（去两头空白、截长）和存下的一样就照打的写（不把正在打的空格吞掉），不然写存下的 """
    stored = text(stored)
    typed = view.Typed.get((view.Selected, key))
    if typed is not None and text(typed).strip()[:limit] == stored:
        return text(typed)
    return stored


def left_rows(view):  # type: (any) -> list
    groups = UserRecipeManager.Groups()
    rows = [FormRow(TITLE, label=ManagerText.Local, value=str(len(groups)))]
    moving_from = UserRecipeManager.GroupOf(view.Moving) if view.Moving else None
    for group in groups:
        selected = view.Selected == group["id"]
        if moving_from is not None:
            style = OFF if group["id"] == moving_from else None  # 挪窝时：原来那个分组点不了，别的都是去处
        else:
            style = ON if selected else None
        pages, _recipes = UserRecipeManager.GroupCounts(group["id"])
        rows.append(FormRow(TILE, GROUP + group["id"], label=group_name(group), value=str(pages),
                            buttons=[("pick", u"", style)],
                            icon=ManagerConst.GroupIcon if group["enabled"] else ManagerConst.GroupOffIcon,
                            color=None if group["enabled"] else MUTE))
    rows.append(FormRow(BUTTONS, "local", buttons=[("new", ManagerText.NewGroup, None), ("import", ManagerText.Import, None)]))
    rows.extend(server_list_rows(view))
    return rows


def server_entries():  # type: () -> list
    """ 「服务器共享」里列哪些：服务器上的（按共享的先后），加上服务器上没了、订阅还留着的 → [(键, 摘要或 None, 拿下来的或 None)] """
    listed = [(entry["key"], entry, UserShareManager.Sub(entry["key"])) for entry in ShareClient.Servers]
    keys = set(key for key, _server, _sub in listed)
    listed += [(sub["key"], None, sub) for sub in UserShareManager.Subs() if sub["key"] not in keys and sub["subscribed"]]
    return listed


def server_list_rows(view):  # type: (any) -> list
    entries = server_entries()
    value = ManagerText.Asking if ShareClient.Asking else str(len(entries))
    rows = [FormRow(TITLE, label=ManagerText.Server, value=value)]
    if ShareClient.Failed and not ShareClient.Listed:
        rows.append(FormRow(TEXT, label=ManagerText.NoAnswer, color=WARN))
    mine = ShareClient.MyKeys()
    for key, server, sub in entries:
        info = server or sub
        if key in mine:
            tag = ManagerText.Mine
        elif server is None:
            tag = ManagerText.GoneTag
        elif server["unified"]:
            tag = ManagerText.UnifiedTag
        else:
            tag = u""
        followed = sub is not None and (sub["subscribed"] or sub["unified"])
        style = OFF if view.Moving else (ON if view.Server == key else None)
        rows.append(FormRow(TILE, SERVER + key, label=text(info.get("name")) or ManagerText.Unnamed, value=tag,
                            buttons=[("pick", u"", style)],
                            icon=ManagerConst.GroupIcon if followed or key in mine else ManagerConst.ServerIcon,
                            color=None if followed or key in mine else MUTE))
    rows.append(FormRow(BUTTONS, "servers", buttons=[("refresh", ManagerText.Refresh, OFF if ShareClient.Asking else None)]))
    return rows


def share_status(group):  # type: (dict) -> any
    """ 本地分组开了共享时右栏写的那一句：等待上传 / 正在上传 / 已共享（版本）/ 失败的原因 / 等连上服务器 """
    state, info = ShareClient.StatusOf(group["id"])
    if not ShareClient.Listed:
        return ManagerText.ShareStatus["offline"], WARN
    if state == DONE:
        return ManagerText.ShareStatus[DONE].format(info if info else u"-"), HINT
    if state == FAILED:
        return ManagerText.ShareStatus[FAILED].format(ManagerText.ShareErrors.get(info, text(info))), WARN
    if state in ManagerText.ShareStatus:
        return ManagerText.ShareStatus[state], MUTE
    return ManagerText.ShareHint, MUTE


def right_rows(view):  # type: (any) -> list
    if view.Server is not None:
        return server_rows(view, view.Server)
    group = UserRecipeManager.Group(view.Selected)
    if group is None:
        return [FormRow(TEXT, label=ManagerText.PickGroup)]
    gid = group["id"]
    pages = UserRecipeManager.GroupPages(gid)
    _count, recipes = UserRecipeManager.GroupCounts(gid)
    rows = [FormRow(TITLE, label=group_name(group), value=ManagerText.Counts.format(len(pages), recipes))]
    if not view.UserRecipesEnabled():
        rows.append(FormRow(TEXT, label=ManagerText.Off, color=WARN))
    if gid == DEFAULT_GROUP:
        rows.append(FormRow(TEXT, label=ManagerText.DefaultHint))
    else:
        rows.append(FormRow(EDIT, "name", label=ManagerText.Name, text=edit_text(view, "name", group.get("name"), NAME_LENGTH)))
    rows.append(FormRow(EDIT, "desc", label=ManagerText.Desc, text=edit_text(view, "desc", group.get("desc"), DESC_LENGTH)))
    rows.append(FormRow(BUTTONS, "flags", buttons=[
        ("enabled", ManagerText.Enabled if group["enabled"] else ManagerText.Disabled, ON if group["enabled"] else None),
        ("shared", ManagerText.Sharing if group["shared"] else ManagerText.NotShared, ON if group["shared"] else None)]))
    if group["shared"]:
        status, color = share_status(group)
        rows.append(FormRow(TEXT, label=status, color=color))
    elif ShareClient.Removed.get(gid):
        rows.append(FormRow(TEXT, label=ManagerText.RemovedHint, color=WARN))
    rows.append(FormRow(TITLE, label=ManagerText.Pages))
    if view.Moving:
        moving = UserRecipeManager.Page(view.Moving)
        if moving is not None:
            rows.append(FormRow(TEXT, label=ManagerText.MoveHint.format(page_name(moving)), color=HINT))
    can_edit = view.UserRecipesEnabled()
    counts = {}
    for recipe in UserRecipeManager.Recipes():
        counts[recipe["page"]] = counts.get(recipe["page"], 0) + 1
    for page in pages:
        icon = page_icon(page)
        rows.append(FormRow(ITEM, PAGE + page["id"], item=BookmarkResolver.ResolveItem(icon) if icon else None,
                            value=page_name(page), text=ManagerText.RecipeCount.format(counts.get(page["id"], 0)),
                            buttons=[("move", ManagerText.Move, ON if view.Moving == page["id"] else None),
                                     ("edit", ManagerText.Edit, None if can_edit else OFF)]))
    if not pages:
        rows.append(FormRow(TEXT, label=ManagerText.Empty))
    actions = [("export", ManagerText.Export, None if pages else OFF)]
    if gid != DEFAULT_GROUP:
        actions.append(("disband", ManagerText.Confirm if view.Confirming("disband") else ManagerText.Disband, None))
        actions.append(("delete", ManagerText.Confirm if view.Confirming("delete") else ManagerText.Delete, RED))
    rows.append(FormRow(BUTTONS, "group", buttons=actions))
    return rows


def server_rows(view, key):  # type: (any, str) -> list
    """ 右栏：服务器上的一个分组 """
    from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import IsForceOverride
    server, sub = ShareClient.Server(key), UserShareManager.Sub(key)
    info = server or sub
    if info is None:
        return [FormRow(TEXT, label=ManagerText.PickGroup)]
    mine = ShareClient.IsMine(key)
    rows = [FormRow(TITLE, label=text(info.get("name")) or ManagerText.Unnamed, value=ManagerText.Version.format(info.get("rev") or u"-"))]
    rows.append(FormRow(TEXT, label=ManagerText.Owner.format(text(info.get("owner_name")) or u"?") + (ManagerText.You if mine else u"")))
    rows.append(FormRow(TEXT, label=text(info.get("desc")) or ManagerText.NoDesc, color=MUTE))
    if server is not None:
        rows.append(FormRow(TEXT, label=ManagerText.ServerCounts.format(server["pages"], server["recipes"],
                                                                         max(1, (server["size"] + 1023) // 1024)), color=MUTE))
    else:
        rows.append(FormRow(TEXT, label=ManagerText.Gone, color=WARN))
    if server is not None and server["unified"]:
        rows.append(FormRow(TEXT, label=ManagerText.UnifiedHint, color=HINT))
        if not IsForceOverride() and not mine:
            rows.append(FormRow(TEXT, label=ManagerText.OverrideOff, color=WARN))
    elif server is not None and server.get("review"):
        rows.append(FormRow(TEXT, label=ManagerText.Review, color=WARN))
    busy = bool(ShareClient.Busy.get(key))
    if mine:
        rows.append(FormRow(TEXT, label=ManagerText.MineHint, color=HINT))
    else:
        subscribed = sub is not None and sub["subscribed"]
        buttons = [("subscribe", ManagerText.Subscribed if subscribed else ManagerText.Subscribe,
                    ON if subscribed else (OFF if busy or server is None else None))]
        if subscribed:
            buttons.append(("enabled", ManagerText.Enabled if sub["enabled"] else ManagerText.Disabled, ON if sub["enabled"] else None))
        rows.append(FormRow(BUTTONS, "sub", buttons=buttons))
    if server is not None and ShareClient.IsOp:
        if server.get("review"):  # 统一以后内容改过：看过了再统一一次，或者取消
            buttons = [("unify", ManagerText.Reunify, OFF if busy else None), ("ununify", ManagerText.Unified, OFF if busy else ON)]
        else:
            buttons = [("unify", ManagerText.Unified if server["unified"] else ManagerText.Unify,
                        OFF if busy else (ON if server["unified"] else None))]
        rows.append(FormRow(BUTTONS, "op", buttons=buttons))
    actions = []
    if sub is not None:
        actions.append(("copy", ManagerText.CopyToLocal, None))
    if server is not None and (mine or ShareClient.IsOp):
        actions.append(("delete", ManagerText.Confirm if view.Confirming("remote") else ManagerText.DeleteRemote, OFF if busy else RED))
    if actions:
        rows.append(FormRow(BUTTONS, "remote", buttons=actions))
    rows.append(FormRow(TITLE, label=ManagerText.Pages))
    if sub is None:
        rows.append(FormRow(TEXT, label=ManagerText.SubscribeHint if not mine else ManagerText.MineHint, color=MUTE))
        return rows
    counts = {}
    for recipe in sub["recipes"]:
        counts[recipe["page"]] = counts.get(recipe["page"], 0) + 1
    for page in sub["pages"]:
        icon = page_icon(page)
        rows.append(FormRow(ITEM, PAGE + page["id"], item=BookmarkResolver.ResolveItem(icon) if icon else None,
                            value=page_name(page), text=ManagerText.RecipeCount.format(counts.get(page["id"], 0))))
    return rows
