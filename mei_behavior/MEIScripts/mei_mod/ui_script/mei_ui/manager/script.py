# coding=utf-8
# ----------------------------------------------------------------------
#  script.py is part of MoreEnoughItems.
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
自定义配方管理器的控制器（docs/architecture/user_recipes.md §22）。

一个居中的窗口：左栏分组一列，右栏选中分组的详情（行由 panels.py 给，表单是编辑器那一套）。改动当场交给 UserRecipeManager
（它通知 user 扩展重登记、合并着落盘）；这里每帧看它的版本号，变了就重排两栏 —— 编辑器（压在上面开的）存了东西回来也跟着变。
「改」：编辑器就在下面（管理器是从编辑器开的）时让它换到这一页再关掉管理器，否则压一个编辑器上来。剪贴板走 state/user_pack.py 的格式。
「服务器共享」那一栏照 ShareClient（client/share.py）：开管理器时问一次列表；订阅、统一、删除都交给它，回来了提示一句
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.texts import ManagerText
from MEIScripts.constants.ui import EditorPath, ManagerConst, ManagerPath
from MEIScripts.mei_mod.client.share import ShareClient
from MEIScripts.mei_mod.state import UserRecipeManager, UserShareManager
from MEIScripts.mei_mod.state.user_pack import decode_pack, encode_pack
from MEIScripts.mei_mod.state.user_recipes import DEFAULT_GROUP
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import ControlWriter, flush, forget_screen
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text, native_str

from ..editor.form import Form
from . import panels

ViewBinder = clientApi.GetViewBinderCls()

TOP = ManagerConst.TopHeight + ManagerConst.Pad * 2 - 2
""" 两栏从窗口顶上往下这么多（顶栏 20 + 上下留边）"""


def _game():
    return clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())


def set_clipboard(content):  # type: (str) -> bool
    """ 写系统剪贴板（SDK 3.3 起；旧版本没有这个接口给 False）"""
    try:
        setter = getattr(_game(), "SetClipboardContent", None)
        return bool(setter(native_str(content))) if callable(setter) else False
    except Exception as e:  # noqa
        logger.error("[MEI/manager] 写剪贴板失败: {}".format(error_text(e)))
        return False


def get_clipboard():  # type: () -> any
    """ 读系统剪贴板：读不了给 None，没有文字给空串 """
    try:
        getter = getattr(_game(), "GetClipboardContent", None)
        return getter() if callable(getter) else None
    except Exception as e:  # noqa
        logger.error("[MEI/manager] 读剪贴板失败: {}".format(error_text(e)))
        return None


class ManagerScript(object):

    def __init__(self, screen, request):
        self.Screen = screen
        self.Request = dict(request or {})
        self.Bindings = None  # type: ScreenBinder or None
        self.Left = None  # type: Form or None
        self.Right = None  # type: Form or None
        self.Top = {}  # type: dict
        self.Selected = DEFAULT_GROUP  # type: str  # 选中的本地分组
        self.Server = None  # type: str or None  # 选中的服务器上的分组（选了它右栏就是它，不是 Selected）
        self.Moving = None  # type: str or None  # 正在挪窝的页面：等着点左栏的分组
        self.Typed = {}  # type: dict  # (分组 Id, "name" / "desc") -> 输入框里打的字（和存下的对得上时照它显示，不把正在打的空格吞掉）
        self.ToastLeft = 0
        self.ConfirmKey = None
        self.ConfirmLeft = 0
        self.Seen = None  # 上次排两栏时的版本号
        self.LayoutKey = None
        self.Frame = 0
        self.Alive = True  # 拆了以后回来的回执不再提示

    # 生命周期
# ======================================================================================================================
    def Start(self):
        self.Left = Form(self.Screen, self.OnLeft, root=ManagerPath.Left, counts=ManagerConst.LeftPool,
                         width=ManagerConst.LeftWidth - ManagerConst.Pad - 3)
        self.Right = Form(self.Screen, self.OnRight, root=ManagerPath.Right, counts=ManagerConst.RightPool, width=200)
        self.Bindings = ScreenBinder(self.Screen)
        for name in ManagerConst.TopButtons:
            control = self.Screen.GetBaseUIControl("{}/{}".format(ManagerPath.RightBar, name))
            if control is not None:
                self.Top[name] = ControlWriter(self.Screen, control)
            self.Bindings.Bind(self.__TopHandler(name), ViewBinder.BF_ButtonClickUp, ManagerConst.ButtonName.format(name))
        group = self.Request.get("group")
        if group and UserRecipeManager.Group(group) is not None:
            self.Selected = group
        ShareClient.RequestList()  # 服务器上的分组、自己是不是操作员：开一次问一次
        self.Layout(force=True)

    def Destroy(self):
        self.Alive = False
        bindings, self.Bindings = self.Bindings, None
        if bindings is not None:
            try:
                bindings.UnbindAll()
            except Exception as e:  # noqa
                logger.warn("[MEI/manager] 摘顶栏的绑定失败: {}".format(error_text(e)))
        forget_screen(self.Screen)
        UserRecipeManager.Flush()
        UserShareManager.Flush()

    def Tick(self):
        """ 每帧（界面的 Update 调）"""
        self.Frame += 1
        try:
            if self.Frame % ManagerConst.LayoutFrames == 1:
                self.Layout()
            self.Right.Poll()
            if self.Revision() != self.Seen:
                self.Refresh()
            if self.ToastLeft > 0:
                self.ToastLeft -= 1
                if self.ToastLeft == 0:
                    self.__ToastText(u"")
            if self.ConfirmLeft > 0:
                self.ConfirmLeft -= 1
                if self.ConfirmLeft == 0:
                    self.ConfirmKey = None
                    self.Refresh()
        except Exception as e:  # noqa
            if self.Frame % 300 == 1:
                logger.error("[MEI/manager] 管理器每帧处理出错: {}".format(error_text(e)))
        flush()

    @staticmethod
    def Revision():  # type: () -> any
        """ 两栏的内容跟着谁变：自制配方的存储、拿下来的分组、共享的状态（列表、上传下载的进度）"""
        return UserRecipeManager.Revision(), UserShareManager.Revision(), ShareClient.Revision()

    # 摆
# ======================================================================================================================
    def Layout(self, force=False):
        """ 窗口居中，最大 MaxWidth × MaxHeight，屏幕小了照屏幕；右栏占左栏剩下的宽 """
        root = self.Screen.GetBaseUIControl(ManagerPath.Root)
        if root is None:
            return
        width, height = (int(v) for v in root.GetSize())
        window_w = max(240, min(ManagerConst.MaxWidth, width - 8))
        window_h = max(120, min(ManagerConst.MaxHeight, height - 8))
        key = (window_w, window_h)
        if key == self.LayoutKey and not force:
            return
        self.LayoutKey = key
        window = self.Screen.GetBaseUIControl(ManagerPath.Window)
        if window is not None:
            window.SetFullSize("x", {"absoluteValue": window_w})
            window.SetFullSize("y", {"absoluteValue": window_h})
        body_h = window_h - TOP - ManagerConst.Pad
        right_w = window_w - ManagerConst.LeftWidth - ManagerConst.Pad * 2
        left = self.Screen.GetBaseUIControl(ManagerPath.Left)
        if left is not None:
            left.SetFullSize("y", {"absoluteValue": body_h})
        right = self.Screen.GetBaseUIControl(ManagerPath.Right)
        if right is not None:
            right.SetFullSize("x", {"absoluteValue": right_w})
            right.SetFullSize("y", {"absoluteValue": body_h})
        self.Left.Height = self.Right.Height = body_h
        self.Right.Width = right_w - 3
        self.Refresh()

    # 刷新
# ======================================================================================================================
    def Refresh(self):
        """ 顶栏、两栏照现在的状态写一遍（只写变了的）"""
        self.Seen = self.Revision()
        try:
            if UserRecipeManager.Group(self.Selected) is None:
                self.Selected = DEFAULT_GROUP
            if self.Server is not None and ShareClient.Server(self.Server) is None and UserShareManager.Sub(self.Server) is None:
                self.Server = None
            if self.Moving and UserRecipeManager.Page(self.Moving) is None:
                self.Moving = None
            self.__RefreshTop()
            self.Left.Show(panels.left_rows(self))
            self.Right.Show(panels.right_rows(self))
        except Exception as e:  # noqa
            logger.error("[MEI/manager] 管理器刷新出错: {}".format(error_text(e)))
        flush()

    def __RefreshTop(self):
        writer = self.Top.get("editor")
        if writer is not None:
            writer.SetText(EditorPath.ButtonLabel, ManagerText.Editor)
            writer.SetVisible(EditorPath.ButtonMask, not self.UserRecipesEnabled())

    @staticmethod
    def UserRecipesEnabled():  # type: () -> bool
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import IsUserRecipesEnabled
        return IsUserRecipesEnabled()

    # 提示与确认
# ======================================================================================================================
    def Toast(self, content):
        self.ToastLeft = ManagerConst.ToastFrames
        self.__ToastText(content)

    def __ToastText(self, content):
        label = self.Screen.GetBaseUIControl(ManagerPath.Toast)
        if label is not None:
            label.asLabel().SetText(native_str(content))

    def Confirming(self, key):  # type: (str) -> bool
        return self.ConfirmKey == key and self.ConfirmLeft > 0

    def Confirm(self, key):  # type: (str) -> bool
        """ 要点两下的事：第一下记下（按钮写「再点一次」），限定时间里再点一下才给 True """
        if self.Confirming(key):
            self.ConfirmKey, self.ConfirmLeft = None, 0
            return True
        self.ConfirmKey, self.ConfirmLeft = key, ManagerConst.ConfirmFrames
        self.Refresh()
        return False

    # 点击
# ======================================================================================================================
    def __TopHandler(self, name):
        def handler(_args=None):
            try:
                self.OnTop(name)
            except Exception as e:  # noqa
                logger.error("[MEI/manager] 顶栏 {} 处理出错: {}".format(name, error_text(e)))
        return handler

    def OnTop(self, name):
        if name == "close_button":
            self.Screen.RequestClose()
        elif name == "editor":
            self.OpenEditor()

    def OnLeft(self, key, op, _value):
        try:
            if key == "__pager":
                self.Refresh()
            elif key.startswith(panels.GROUP) and op == "pick":
                self.PickGroup(key[len(panels.GROUP):])
            elif key.startswith(panels.SERVER) and op == "pick":
                self.PickServer(key[len(panels.SERVER):])
            elif key == "servers" and op == "refresh":
                ShareClient.RequestList()
            elif key == "local" and op == "new":
                self.NewGroup()
            elif key == "local" and op == "import":
                self.ImportClipboard()
        except Exception as e:  # noqa
            logger.error("[MEI/manager] 左栏 {} {} 处理出错: {}".format(key, op, error_text(e)))

    def OnRight(self, key, op, value):
        try:
            if key == "__pager":
                self.Refresh()
            elif key in ("name", "desc") and op == "text":
                self.Typed[(self.Selected, key)] = value
                UserRecipeManager.UpdateGroup(self.Selected, **{key: value})
            elif key == "flags" and op in ("enabled", "shared"):
                group = UserRecipeManager.Group(self.Selected)
                if group is not None:
                    UserRecipeManager.UpdateGroup(self.Selected, **{op: not group[op]})
            elif key in ("sub", "op", "remote"):
                self.OnServerAction(op)
            elif key.startswith(panels.PAGE):
                self.OnPage(key[len(panels.PAGE):], op)
            elif key == "group":
                self.OnGroupAction(op)
        except Exception as e:  # noqa
            logger.error("[MEI/manager] 右栏 {} {} 处理出错: {}".format(key, op, error_text(e)))

    # 分组
# ======================================================================================================================
    def PickGroup(self, group_id):
        """ 点了左栏的一个分组：正在挪窝就挪过去，否则选中它 """
        if self.Moving:
            page = UserRecipeManager.Page(self.Moving)
            group = UserRecipeManager.Group(group_id)
            self.Moving = None
            if page is not None and group is not None and UserRecipeManager.MovePage(page["id"], group_id):
                self.Toast(ManagerText.Moved.format(panels.page_name(page), panels.group_name(group)))
            self.Refresh()
            return
        if group_id != self.Selected or self.Server is not None:
            self.Selected = group_id
            self.Server = None
            self.Right.Page = 0
            self.ConfirmKey, self.ConfirmLeft = None, 0
        self.Refresh()

    def PickServer(self, key):
        """ 点了「服务器共享」里的一个分组：选中它（正在挪窝就算了 —— 页面挪不到服务器上）"""
        self.Moving = None
        if key != self.Server:
            self.Server = key
            self.Right.Page = 0
            self.ConfirmKey, self.ConfirmLeft = None, 0
        self.Refresh()

    # 服务器上的分组
# ======================================================================================================================
    def OnServerAction(self, op):
        key = self.Server
        if key is None:
            return
        name = panels.text((ShareClient.Server(key) or UserShareManager.Sub(key) or {}).get("name")) or ManagerText.Unnamed
        sub = UserShareManager.Sub(key)
        if op == "subscribe":
            if sub is not None and sub["subscribed"]:
                ShareClient.Unsubscribe(key)
                self.Toast(ManagerText.UnsubscribedToast)
            else:
                ShareClient.Subscribe(key, on_done=self.__Done(ManagerText.SubscribedToast.format(name)))
        elif op == "enabled" and sub is not None:
            ShareClient.SetSubEnabled(key, not sub["enabled"])
        elif op in ("unify", "ununify"):
            server = ShareClient.Server(key)
            if server is not None:
                on = op == "unify" and not server["unified"]  # 待重新统一的：「重新统一」开、「已统一」那颗取消
                ShareClient.SetUnified(key, on, on_done=self.__Done(ManagerText.UnifiedToast if on else ManagerText.UnunifiedToast))
        elif op == "copy":
            group_id, error = ShareClient.CopyToLocal(key)
            if error:
                self.Toast(ManagerText.Errors.get(error, ManagerText.ShareErrors.get(error, ManagerText.Errors["broken"])))
                return
            self.Server = None
            self.Selected = group_id
            self.Right.Page = 0
            self.Toast(ManagerText.Copied.format(name))
        elif op == "delete" and self.Confirm("remote"):
            ShareClient.DeleteRemote(key, on_done=self.__Done(ManagerText.RemoteDeleted))
        self.Refresh()

    def __Done(self, success):
        """ 请求回来了：成了提示 success，不成提示原因（界面关了就不提示）"""
        def done(ok, error):
            if not self.Alive:
                return
            self.Toast(success if ok else ManagerText.ShareErrors.get(error, panels.text(error)))
        return done

    def NewGroup(self):
        count = len(UserRecipeManager.Groups())
        group_id, error = UserRecipeManager.CreateGroup(ManagerText.NewName.format(count))
        if error:
            self.Toast(ManagerText.Errors.get(error, ManagerText.Errors["broken"]))
            return
        self.Selected = group_id
        self.Right.Page = 0
        self.Toast(ManagerText.Created)
        self.Refresh()

    def ImportClipboard(self):
        content = get_clipboard()
        if content is None:
            self.Toast(ManagerText.ClipboardFail)
            return
        pack, error = decode_pack(content)
        if error is None:
            group_id, error = UserRecipeManager.ImportGroup(pack)
        if error:
            self.Toast(ManagerText.Errors.get(error, ManagerText.Errors["broken"]))
            return
        pages, recipes = UserRecipeManager.GroupCounts(group_id)
        self.Selected = group_id
        self.Right.Page = 0
        self.Toast(ManagerText.Imported.format(panels.group_name(UserRecipeManager.Group(group_id)), pages, recipes))
        self.Refresh()

    def OnGroupAction(self, op):
        group = UserRecipeManager.Group(self.Selected)
        if group is None:
            return
        if op == "export":
            pack = UserRecipeManager.ExportGroup(group["id"])
            if pack is None:
                return
            pack["name"] = panels.group_name(group)
            content = encode_pack(pack)
            if set_clipboard(content):
                self.Toast(ManagerText.Exported.format(len(content)))
            else:
                self.Toast(ManagerText.ClipboardFail)
        elif op == "disband" and self.Confirm("disband"):
            moved = UserRecipeManager.DisbandGroup(group["id"])
            if moved >= 0:
                self.Selected = DEFAULT_GROUP
                self.Toast(ManagerText.Disbanded.format(moved))
            self.Refresh()
        elif op == "delete" and self.Confirm("delete"):
            result = UserRecipeManager.DeleteGroup(group["id"])
            if result is not None:
                self.Selected = DEFAULT_GROUP
                self.Toast(ManagerText.Deleted.format(*result))
            self.Refresh()

    # 页面
# ======================================================================================================================
    def OnPage(self, page_id, op):
        if op == "move":
            self.Moving = None if self.Moving == page_id else page_id
            self.Refresh()
        elif op == "edit":
            self.EditPage(page_id)

    def EditPage(self, page_id):
        """ 在编辑器里改这一页：编辑器就在下面就让它换过去、关掉管理器；不然压一个编辑器上来 """
        from MEIScripts.mei_mod.ui_script.mei_ui.editor import ActiveEditor, OpenMeiEditor
        if not self.UserRecipesEnabled():
            self.Toast(ManagerText.NeedEnable)
            return
        editor = ActiveEditor()
        if editor is not None:
            key = "editor_dirty:" + page_id
            if not editor.OpenPage(page_id, force=self.Confirming(key)):
                self.Confirm(key)  # 编辑器里有没存的改动：第一下只提示，限定时间里再点一次就丢掉它们
                self.Toast(ManagerText.EditorDirty)
                return
            self.ConfirmKey, self.ConfirmLeft = None, 0
            self.Screen.RequestClose()
            return
        OpenMeiEditor(page_id=page_id, group=self.Selected)

    def OpenEditor(self):
        """ 顶栏「编辑器」：编辑器就在下面就关掉管理器回去，不然压一个上来（停在选中分组的第一页）"""
        from MEIScripts.mei_mod.ui_script.mei_ui.editor import ActiveEditor, OpenMeiEditor
        if not self.UserRecipesEnabled():
            self.Toast(ManagerText.NeedEnable)
            return
        if ActiveEditor() is not None:
            self.Screen.RequestClose()
            return
        pages = UserRecipeManager.GroupPages(self.Selected)
        OpenMeiEditor(page_id=pages[0]["id"] if pages else None, group=self.Selected)
