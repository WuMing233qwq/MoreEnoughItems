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
MEI 编辑器的控制器（docs/architecture/user_recipes.md §12、§13）。两种模式：
- 界面：给一个页面（= 一台机器 = 一个配方类型）排版 —— 控件池里点一下放一块积木、拖动挪位置、选中改属性；页面设置（名字、工作站、行高、字段、预设）；
  预览配方页上的样子；保存页面。新页面一开始是工作台的排版。
- 配方：选一个存好的页面，点一格（黄框）再点右边物品栏的物品填进去（填好跳到同一类的下一个空格），改数量、概率、填法（单个 / 候选 / 标签），
  不选格子时填数值字段与备注；保存配方。
左栏是表单（form.py，内容由 panels/ 按状态给），中间是工作区（workspace.py，积木和配方页同一套画法），右栏是 MEI 自己的物品栏（主节点建的，
点物品经 ModeManager.Intercept 交给 PickItem）。草稿是 state/user_recipes.py 里那份的拷贝，「保存」才交回去；
存了以后 user 扩展马上重登记那一页（配方页、配方树查得到）。
建控件、改显隐都不当场刷新界面（blocks/writer.py）：每次 Refresh、每帧 Tick 写完 flush 一次
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.texts import EditorText, UserText
from MEIScripts.constants.ui import EditorConst, EditorPath, UiPathConst
from MEIScripts.mei_mod.state import BookmarkResolver, UserRecipeManager
from MEIScripts.mei_mod.state.bookmarks import item_data, item_key
from MEIScripts.mei_mod.state.user_recipes import MAX_ALTS, MAX_BLOCKS, MAX_STATIONS, make_ingredient
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import ControlWriter, flush, forget_screen, mark_dirty
from MEIScripts.registry import ItemManager
from MEIScripts.registry.blocks import BlockRegistry
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.lang import localize
from MEIScripts.utils.text import error_text, native_str

from . import panels
from .form import Form, fit
from .modules import draft
from .workspace import Workspace
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.row import row_layout

ViewBinder = clientApi.GetViewBinderCls()

WORK_MARGIN = 8
""" 工作区比一行宽出这么多（两边各 4）：放不下就收起一边（界面模式收物品栏、配方模式收左栏）"""

MIN_WINDOW = 310
""" 窗口至少这么宽：顶栏左右两排按钮（174 + 128）不叠在一起 """

PAGE_NAME_W = 62
""" 顶栏页面名那一格（page_slot 64 宽）：长名字截短，不盖住两边的箭头 """

LAYOUT_FRAMES = 10
""" 隔这么多帧看一眼屏幕、物品栏的尺寸变没变（刚建的物品栏要几帧才排好）"""


def _unicode(text):  # type: (any) -> unicode
    if isinstance(text, unicode):
        return text
    return native_str(text or "").decode("utf-8", "replace")


class EditorScript(object):

    UI, RECIPE = "ui", "recipe"

    def __init__(self, screen, main, request):
        self.Screen = screen
        self.Main = main
        self.Request = dict(request or {})
        self.Bindings = None  # type: ScreenBinder or None
        self.Mode = self.UI
        self.LeftOpen = True
        self.ItemsOpen = False
        self.LeftTab = "blocks"
        self.Preview = False
        self.PickStation = None  # type: any  # 等着点物品栏的工作站：第几个（换它）/ "new"（加一个）/ "icon"（这一页的图标）；不等是 None
        self.PickProp = None  # type: tuple or None  # (第几块, 属性的键)：物品属性正在等着点物品栏
        self.Typed = {}  # type: dict  # (第几块, 属性的键) -> 输入框里打的物品（和存的对得上时照它显示，不把玩家打的字改写掉）
        self.PresetName = draft.DEFAULT_PRESET
        self.Group = self.Request.get("group")  # type: str or None  # 这一回新建的页面放进哪个分组（从管理器开的）
        # 界面模式：正在排的页面（拷贝）
        self.Draft = None  # type: dict or None
        self.Dirty = False
        self.Selected = None  # type: int or None
        # 配方模式：哪一页、第几条、那一条的拷贝、选中的格子（积木的下标）
        self.RPage = None  # type: dict or None
        self.RIndex = 0
        self.RDraft = None  # type: dict or None
        self.RDirty = False
        self.Cell = None  # type: int or None
        self.CellModes = {}  # type: dict  # 积木下标 -> 填法（候选、标签刚切过去、还没填东西时要记着）
        self.ToastLeft = 0
        self.ConfirmKey = None
        self.ConfirmLeft = 0
        self.LayoutKey = None
        self.Frame = 0
        self.Form = None  # type: Form or None
        self.Work = None  # type: Workspace or None
        self.Top = {}  # type: dict

    # 生命周期
# ======================================================================================================================
    def Start(self):
        self.Main.Editor = self
        self.Form = Form(self.Screen, self.OnForm)
        self.Work = Workspace(self.Screen, self.OnBlock, self.OnBlank, self.OnMoved, self.ClampAt)
        self.Bindings = ScreenBinder(self.Screen)
        for name in EditorConst.TopButtons:
            path = EditorPath.LeftBar if name in ("tab_ui", "tab_recipe", "page_prev", "page_next", "page_new") \
                else EditorPath.RightBar
            control = self.Screen.GetBaseUIControl("{}/{}".format(path, name))
            if control is not None:
                self.Top[name] = ControlWriter(self.Screen, control)
            self.Bindings.Bind(self.__TopHandler(name), ViewBinder.BF_ButtonClickUp, EditorConst.ButtonName.format(name))
        self.__Begin()
        # 物品栏的显隐归编辑器：两个方向都显式写一遍（界面状态跨开关存活，引擎结论 §22）
        self.Main.ShowEditorBrowser(self.ItemsOpen)

    def __Begin(self):
        """ 按打开时带的请求定从哪开始：改某条配方、给某样物品加配方、改某个页面；什么都没带就是界面模式的第一个页面 """
        request = self.Request
        recipe = UserRecipeManager.Recipe(request.get("recipe")) if request.get("recipe") else None
        if recipe is not None and UserRecipeManager.Page(recipe["page"]) is not None:
            self.__EnterRecipe(UserRecipeManager.Page(recipe["page"]))
            ids = [entry["id"] for entry in UserRecipeManager.Recipes(recipe["page"])]
            self.LoadRecipe(ids.index(recipe["id"]), force=True)
            return
        item = request.get("item")
        if item is not None and UserRecipeManager.Pages():
            self.__EnterRecipe(UserRecipeManager.Pages()[-1])
            self.LoadRecipe(len(UserRecipeManager.Recipes(self.RPage["id"])), force=True)
            holders = self.__Holders()
            outputs = [block_index for block_index, role, _number in holders if role == "out"]
            if outputs:
                self.Cell = outputs[0]
                self.PickItem(item, False)
            inputs = [block_index for block_index, role, _number in holders if role == "in"]
            self.Cell = inputs[0] if inputs else None
            self.Refresh()
            return
        pages = [page["id"] for page in UserRecipeManager.Pages()]
        self.LoadPage(pages.index(request["page"]) if request.get("page") in pages else 0)
        if item is not None:
            self.Toast(EditorText.NeedPage)

    def Destroy(self):
        if self.Main is not None and getattr(self.Main, "Editor", None) is self:
            self.Main.Editor = None
        bindings, self.Bindings = self.Bindings, None
        if bindings is not None:
            try:
                bindings.UnbindAll()
            except Exception as e:  # noqa
                logger.warn("[MEI/editor] 摘编辑器顶栏的绑定失败: {}".format(error_text(e)))
        if self.Work is not None:
            self.Work.Clear()
        forget_screen(self.Screen)

    def Tick(self):
        """ 每帧（编辑器界面的 Update 调）"""
        self.Frame += 1
        try:
            if self.Frame % LAYOUT_FRAMES == 1:
                self.Layout()
            self.Form.Poll()
            moving = self.Work.Update()
            if moving is not None:
                index, x, y = moving
                block_type = self.TypeOf(self.Draft["blocks"][index]) if self.Mode == self.UI else None
                if block_type is not None:
                    self.Work.SetStatus(EditorText.Moved.format(localize(block_type.NameKey), x, y))
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
                logger.error("[MEI/editor] 编辑器每帧处理出错: {}".format(error_text(e)))
        flush()

    def TextSnapshot(self):  # type: () -> tuple
        """ 快捷键判断这一下是不是打进了输入框（hotkeys/manager.py）"""
        return self.Form.TextSnapshot() if self.Form is not None else ()

    # 摆
# ======================================================================================================================
    def Layout(self, force=False):
        """ 窗口占满屏幕里物品栏左边的地方；左栏、物品栏开合时工作区跟着变；太窄收起一边 """
        root = self.Screen.GetBaseUIControl(EditorPath.Root)
        if root is None:
            return
        width, height = (int(v) for v in root.GetSize())
        items = self.__ItemsWidth()
        min_work = self.MinWork()
        if self.LeftOpen and self.ItemsOpen and width - 8 - items - 8 - EditorConst.LeftWidth < min_work:
            if self.Mode == self.UI and not self.Picking():
                self.OpenItems(False, layout=False)
            else:
                self.LeftOpen = False
            items = self.__ItemsWidth()
        key = (width, height, items, self.LeftOpen, self.ItemsOpen, min_work)
        if key == self.LayoutKey and not force:
            return
        self.LayoutKey = key
        least = max(MIN_WINDOW, (EditorConst.LeftWidth if self.LeftOpen else 0) + min_work + EditorConst.Pad * 2)
        window_w, window_h = max(least, width - 8 - items), max(80, height - 8)
        top = EditorConst.TopHeight + EditorConst.Pad * 2 - 2
        window = self.Screen.GetBaseUIControl(EditorPath.Window)
        if window is not None:
            window.SetFullSize("x", {"absoluteValue": window_w})
            window.SetFullSize("y", {"absoluteValue": window_h})
        body_h = window_h - top - EditorConst.Pad
        left = self.Screen.GetBaseUIControl(EditorPath.Left)
        if left is not None:
            left.SetVisible(self.LeftOpen, False)
            mark_dirty(self.Screen)
            left.SetFullSize("y", {"absoluteValue": body_h})
        self.Form.Height = body_h
        left_w = EditorConst.LeftWidth if self.LeftOpen else 0
        self.Work.Place((EditorConst.Pad + left_w, top), (window_w - EditorConst.Pad * 2 - left_w, body_h))
        self.Refresh()

    def MinWork(self):  # type: () -> int
        """ 工作区至少多宽：正在看的这一页的一行（跟着内容区的宽变）+ 两边留的 """
        page = self.ShownPage() or self.Draft or {}
        return row_layout(*draft.area(page))["size"][0] + WORK_MARGIN

    def __ItemsWidth(self):  # type: () -> int
        if not self.ItemsOpen:
            return 0
        wrapper = self.Main.GetUIControl(UiPathConst.RightWrapper)
        try:
            return int(wrapper.GetSize()[0]) if wrapper is not None else 0
        except Exception:  # noqa
            return 0

    def OpenItems(self, on, layout=True):
        """ 右栏（MEI 的物品栏）开 / 收 """
        self.ItemsOpen = bool(on)
        self.Main.ShowEditorBrowser(self.ItemsOpen)
        if layout:
            self.LayoutKey = None
            self.Layout()

    # 刷新
# ======================================================================================================================
    def Refresh(self, form=True):
        """ 顶栏、工作区、左栏、状态栏照现在的状态写一遍（都只写变了的）"""
        try:
            self.__RefreshTop()
            page = self.ShownPage()
            if page is None:
                return
            self.Work.HoldersFirst = self.Mode == self.RECIPE
            self.Work.Show(page, not self.Preview)
            entries, fields, top = self.__ShownContent(page)
            self.Work.SetContent(entries, fields, top)
            if self.Mode == self.UI:
                self.Work.Select(None if self.Preview else self.Selected, True)
            else:
                self.Work.Select(self.Cell, False)
            self.Work.Painter.Paint()
            if form:
                self.Form.Show(panels.rows(self))
            self.Work.SetStatus(self.__StatusText(page), self.__HintText())
        except Exception as e:  # noqa
            logger.error("[MEI/editor] 编辑器刷新出错: {}".format(error_text(e)))
        flush()

    def ShownPage(self):  # type: () -> dict or None
        if self.Mode == self.UI:
            return self.Draft
        return self.RPage

    def __ShownContent(self, page):  # type: (dict) -> tuple
        """ 工作区里显示哪条配方：界面模式是空的（预览时是这一页存着的第一条），配方模式是正在填的那条 """
        if self.Mode == self.UI:
            if not self.Preview or not page.get("id"):
                return {}, {}, {}
            saved = UserRecipeManager.Recipes(page["id"])
            recipe = saved[0] if saved else None
        else:
            saved = UserRecipeManager.Recipes(page["id"])
            recipe = self.RDraft
        if recipe is None:
            return {}, {}, {}
        top = {}
        for entry in list(saved) + [recipe]:
            for field, value in (entry.get("f") or {}).items():
                if field not in top or value > top[field]:
                    top[field] = value
        return draft.entries_of(recipe, self.__Ingredient), recipe.get("f") or {}, top

    def __Ingredient(self, entry):
        return make_ingredient(entry, BookmarkResolver.ResolveItem, ItemManager.ResolveTag)

    def __RefreshTop(self):
        ui = self.Mode == self.UI
        texts = {"tab_ui": EditorText.TabUi, "tab_recipe": EditorText.TabRecipe, "save": EditorText.Save,
                 "preview": EditorText.EndPreview if self.Preview else EditorText.Preview}
        for name, text in texts.items():
            writer = self.Top.get(name)
            if writer is not None:
                writer.SetText(EditorPath.ButtonLabel, text)
        for name, on in (("tab_ui", ui), ("tab_recipe", not ui), ("preview", self.Preview)):
            writer = self.Top.get(name)
            if writer is not None:
                writer.SetVisible("/on", on)
        for name in ("preview", "page_new"):
            writer = self.Top.get(name)
            if writer is not None:
                writer.SetVisible(EditorPath.ButtonMask, not ui)
        page = self.ShownPage() or {}
        name = _unicode(page.get("name")) or (EditorText.NewPage if not page.get("id") else EditorText.Unnamed)
        if (self.Dirty if ui else self.RDirty):
            name += EditorText.Dirty
        label = self.Screen.GetBaseUIControl(EditorPath.PageName)
        if label is not None:
            label.asLabel().SetText(native_str(fit(name, PAGE_NAME_W)))

    def __StatusText(self, page):  # type: (dict) -> any
        if self.Mode == self.RECIPE:
            total = len(UserRecipeManager.Recipes(page["id"]))
            where = EditorText.RecipeOf.format(self.RIndex + 1, total) if self.RDraft.get("id") else EditorText.NewRecipe
            return EditorText.StatusRecipe.format(_unicode(page.get("name")), where)
        text = EditorText.Status.format(len(page.get("blocks") or []), *draft.area(page))
        problems = draft.page_problems(page, self.Holds, lambda block: self.TypeOf(block) is not None)
        if problems:
            text += u" · " + u"、".join(EditorText.Problems[key].format(count) for key, count in problems)
        return text

    def __HintText(self):  # type: () -> any
        if self.Mode == self.UI:
            if self.PickStation == "icon":
                return EditorText.PickIconHint
            if self.PickStation is not None:
                return EditorText.PickStationHint
            return EditorText.PickItemHint if self.PickProp is not None else u""
        if self.Cell is None:
            return EditorText.NoCellHint
        return EditorText.CellHint

    # 提示与确认
# ======================================================================================================================
    def Toast(self, text):
        self.ToastLeft = EditorConst.ToastFrames
        self.__ToastText(text)

    def __ToastText(self, text):
        label = self.Screen.GetBaseUIControl(EditorPath.Toast)
        if label is not None:
            label.asLabel().SetText(native_str(text))

    def Confirming(self, key):  # type: (str) -> bool
        return self.ConfirmKey == key and self.ConfirmLeft > 0

    def Confirm(self, key):  # type: (str) -> bool
        """ 要点两下的事：第一下记下、按钮写「再点一次确认」，限定时间里再点一下才给 True """
        if self.Confirming(key):
            self.ConfirmKey, self.ConfirmLeft = None, 0
            return True
        self.ConfirmKey, self.ConfirmLeft = key, EditorConst.ConfirmFrames
        self.Refresh()
        return False

    # 给 panels 用的
# ======================================================================================================================
    @staticmethod
    def Resolve(data):  # type: (any) -> any
        return BookmarkResolver.ResolveItem(data) if isinstance(data, dict) else None

    @staticmethod
    def ItemName(item):  # type: (any) -> unicode
        info = getattr(item, "Info", None)
        name = getattr(info, "ItemName", None) if info is not None else None
        return _unicode(name or getattr(item, "ItemId", u""))

    @staticmethod
    def TypeOf(block):  # type: (dict) -> any
        return BlockRegistry.Get(block.get("t")) if isinstance(block, dict) else None

    def SizeOf(self, block):  # type: (dict) -> tuple
        block_type = self.TypeOf(block)
        return block_type.SizeOf(block) if block_type is not None else (16, 16)

    def ClampAt(self, index, x, y):  # type: (int, int, int) -> tuple
        """ 第 index 块摆到 (x, y) 的话夹回内容区是哪儿（拖动时每帧问）"""
        page = self.ShownPage() or {}
        blocks = page.get("blocks") or []
        if not 0 <= index < len(blocks):
            return x, y
        probe = draft.clamp({"x": x, "y": y}, self.SizeOf(blocks[index]), draft.area(page))
        return probe["x"], probe["y"]

    def Picking(self):  # type: () -> bool
        """ 正等着点物品栏（工作站、图标、物品属性）"""
        return self.PickStation is not None or self.PickProp is not None

    def StartPick(self, prop):  # type: (tuple or None) -> None
        """ 物品属性的「选」：再点一下取消；开着时物品栏打开 """
        self.PickProp = None if prop is None or prop == self.PickProp else prop
        self.PickStation = None
        if self.PickProp is not None:
            self.OpenItems(True)
        self.Refresh()
    @staticmethod
    def Holds(block):  # type: (dict) -> bool
        return BlockRegistry.Holds(block)

    @staticmethod
    def HolderLabel(holder):  # type: (tuple or None) -> unicode
        if holder is None:
            return u""
        return u"{}{}".format(UserText.RoleShort.get(holder[0], u""), holder[1] + 1)

    def __Holders(self):  # type: () -> list
        from MEIScripts.mei_mod.state.user_recipes import holder_index
        page = self.ShownPage() or {}
        return holder_index(page.get("blocks"), self.Holds)

    def Changed(self, layout=True, form=True):
        """ 草稿改了：记成没存，刷新 """
        if self.Mode == self.UI:
            self.Dirty = True
        else:
            self.RDirty = True
        self.Refresh(form=form)

    def AddBlock(self, block_id):
        block_type = BlockRegistry.Get(block_id)
        if block_type is None or self.Draft is None:
            return
        if draft.counts(self.Draft["blocks"]).get(block_id, 0) >= block_type.Limit:
            self.Toast(EditorText.Limit.format(localize(block_type.NameKey), block_type.Limit))
            return
        if len(self.Draft["blocks"]) >= MAX_BLOCKS:  # 第三方的积木加进来，几种的上限加起来会超过一页的上限（存的时候多出来的会被截掉）
            self.Toast(EditorText.BlocksFull.format(MAX_BLOCKS))
            return
        block = block_type.Normalize({"t": block_id})
        fields = self.Draft.get("fields") or []
        for prop in block_type.Props:
            if prop.Kind == prop.FIELD and fields and not block.get(prop.Key):
                block[prop.Key] = fields[0]
        self.Selected = draft.add_block(self.Draft, block, self.SizeOf)
        self.Changed()

    def CopyBlock(self, index):
        block_type = self.TypeOf(self.Draft["blocks"][index])
        if block_type is None:
            return
        if draft.counts(self.Draft["blocks"]).get(block_type.Id, 0) >= block_type.Limit:
            self.Toast(EditorText.Limit.format(localize(block_type.NameKey), block_type.Limit))
            return
        if len(self.Draft["blocks"]) >= MAX_BLOCKS:
            self.Toast(EditorText.BlocksFull.format(MAX_BLOCKS))
            return
        copied = draft.copy_block(self.Draft, index, self.SizeOf)
        if copied is not None:
            self.Selected = copied
            self.Changed()

    def CellMode(self):  # type: () -> str
        if self.Cell in self.CellModes:
            return self.CellModes[self.Cell]
        holder = draft.holder_of(self.RPage["blocks"], self.Cell, self.Holds) if self.Cell is not None else None
        entry = draft.cell(self.RDraft, holder[0], holder[1]) if holder else None
        if entry and entry.get("tag"):
            return "tag"
        if entry and entry.get("alts"):
            return "alts"
        return "one"

    def SetCellMode(self, mode):
        if self.Cell is not None:
            self.CellModes[self.Cell] = mode

    def CellUnit(self):  # type: () -> str
        block_type = self.TypeOf(self.RPage["blocks"][self.Cell]) if self.Cell is not None else None
        return block_type.Unit if block_type is not None else ""

    # 页面与配方的切换
# ======================================================================================================================
    def LoadPage(self, index):
        """ 界面模式：换到第 index 个存着的页面（拷贝一份来改）；一个都没有就是新页面 """
        pages = UserRecipeManager.Pages()
        self.Mode = self.UI
        if pages:
            page = pages[index % len(pages)]
            self.Draft = UserRecipeManager.PageCopy(page["id"])
        else:
            self.Draft = draft.new_page()
        self.Dirty = False
        self.Selected = None
        self.Preview = False
        self.PickStation = None
        self.PickProp = None
        self.Typed = {}
        self.Refresh()

    def __EnterRecipe(self, page):
        self.Mode = self.RECIPE
        self.RPage = page
        self.Selected = None
        self.Preview = False
        self.PickStation = None
        self.PickProp = None
        self.OpenItems(True, layout=False)
        self.LayoutKey = None

    def LoadRecipe(self, index, force=False):
        """ 配方模式：换到这一页的第 index 条（等于条数就是新的一条）；正在填的没存，第一下只提示 """
        if self.RDirty and not force and not self.Confirm("discard_recipe"):
            self.Toast(EditorText.Discard)
            return
        page = UserRecipeManager.Page(self.RPage["id"]) if self.RPage is not None else None
        if page is None:
            self.SwitchMode(self.UI)
            return
        self.RPage = page
        recipes = UserRecipeManager.Recipes(page["id"])
        self.RIndex = max(0, min(int(index), len(recipes)))
        if self.RIndex < len(recipes):
            self.RDraft = UserRecipeManager.RecipeCopy(recipes[self.RIndex]["id"])
            self.Cell = None
        else:
            self.RDraft = draft.new_recipe(page["id"])
            holders = self.__Holders()
            self.Cell = holders[0][0] if holders else None
        self.RDirty = False
        self.CellModes = {}
        self.Refresh()

    def OpenPage(self, page_id, force=False):  # type: (str, bool) -> bool
        """
        换到这个页面（界面模式）：管理器里点了「改」、编辑器就在它下面时用。有没存的改动、又没 force 给 False（不换）；页面不在也给 False
        """
        if (self.Dirty or self.RDirty) and not force:
            return False
        ids = [page["id"] for page in UserRecipeManager.Pages()]
        if page_id not in ids:
            return False
        self.Cell = None
        self.RDirty = False
        self.LoadPage(ids.index(page_id))
        self.OpenItems(False)
        return True

    def SwitchMode(self, mode):
        if mode == self.Mode:
            return
        if mode == self.RECIPE:
            pages = UserRecipeManager.Pages()
            if not pages:
                self.Toast(EditorText.NeedPage)
                return
            current = self.Draft.get("id") if self.Draft else None
            page = UserRecipeManager.Page(current) if current else None
            self.__EnterRecipe(page or pages[0])
            self.LoadRecipe(0, force=True)
            self.Layout(force=True)
            return
        self.Mode = self.UI
        self.Cell = None
        if self.Draft is None:
            self.LoadPage(0)
        self.OpenItems(False)

    def StepPage(self, step):
        pages = UserRecipeManager.Pages()
        if not pages:
            return
        if self.Mode == self.UI:
            if self.Dirty and not self.Confirm("discard_page"):
                self.Toast(EditorText.Discard)
                return
            ids = [page["id"] for page in pages]
            current = ids.index(self.Draft["id"]) if self.Draft and self.Draft.get("id") in ids else -1
            self.LoadPage((current + step) % len(pages) if current >= 0 else (0 if step > 0 else len(pages) - 1))
            return
        if self.RDirty and not self.Confirm("discard_recipe"):
            self.Toast(EditorText.Discard)
            return
        ids = [page["id"] for page in pages]
        current = ids.index(self.RPage["id"]) if self.RPage and self.RPage["id"] in ids else 0
        self.RPage = pages[(current + step) % len(pages)]
        self.LoadRecipe(0, force=True)

    def NewPage(self):
        if self.Mode != self.UI:
            return
        if self.Dirty and not self.Confirm("discard_page"):
            self.Toast(EditorText.Discard)
            return
        self.Draft = draft.new_page()
        self.Dirty = False
        self.Selected = None
        self.Preview = False
        self.PickProp = None
        self.Typed = {}
        self.LeftTab = "page"
        self.Refresh()

    def Save(self):
        if self.Mode == self.UI:
            problems = [key for key, _count in draft.page_problems(self.Draft, self.Holds, lambda b: self.TypeOf(b) is not None)
                        if key in draft.BLOCKING]
            if problems:
                self.Toast(EditorText.Errors[problems[0]])
                return
            page_id, error = UserRecipeManager.SavePage(dict(self.Draft), group_id=self.Group)
            if error:
                self.Toast(EditorText.Errors.get(error, EditorText.Errors["bad"]))
                return
            self.Draft = UserRecipeManager.PageCopy(page_id)
            self.Dirty = False
            self.Toast(EditorText.SavedPage)
        else:
            recipe_id, error = UserRecipeManager.SaveRecipe(dict(self.RDraft))
            if error:
                self.Toast(EditorText.Errors.get(error, EditorText.Errors["bad"]))
                return
            ids = [entry["id"] for entry in UserRecipeManager.Recipes(self.RPage["id"])]
            self.RIndex = ids.index(recipe_id) if recipe_id in ids else self.RIndex
            self.RDraft = UserRecipeManager.RecipeCopy(recipe_id)
            self.RDirty = False
            self.Toast(EditorText.SavedRecipe)
        self.Refresh()

    def Close(self):
        if (self.Dirty or self.RDirty) and not self.Confirm("close"):
            self.Toast(EditorText.Discard)
            return
        self.Screen.RequestClose()

    # 点击
# ======================================================================================================================
    def __TopHandler(self, name):
        def handler(_args=None):
            try:
                self.OnTop(name)
            except Exception as e:  # noqa
                logger.error("[MEI/editor] 顶栏 {} 处理出错: {}".format(name, error_text(e)))
        return handler

    def OnTop(self, name):
        if name == "tab_ui":
            self.SwitchMode(self.UI)
        elif name == "tab_recipe":
            self.SwitchMode(self.RECIPE)
        elif name in ("page_prev", "page_next"):
            self.StepPage(1 if name == "page_next" else -1)
        elif name == "page_new":
            self.NewPage()
        elif name == "preview" and self.Mode == self.UI:
            self.Preview = not self.Preview
            self.Selected = None
            self.Refresh()
        elif name == "save":
            self.Save()
        elif name == "left":
            self.LeftOpen = not self.LeftOpen
            self.Layout(force=True)
        elif name == "items":
            self.OpenItems(not self.ItemsOpen)
        elif name == "close_button":
            self.Close()
        elif name == "manager":
            self.OpenManager()

    def OpenManager(self):
        """ 顶栏的分组按钮：管理器就在下面（编辑器是从它开的）就关掉编辑器回去，不然压一个上来（选中这一页所在的分组）"""
        from MEIScripts.mei_mod.ui_script.mei_ui.manager import ActiveManager, OpenManager
        if ActiveManager() is not None:
            self.Close()
            return
        page = self.ShownPage() or {}
        OpenManager(group=UserRecipeManager.GroupOf(page["id"]) if page.get("id") else None)

    def OnForm(self, key, op, value):
        try:
            if key == "__pager":
                self.Refresh()
                return
            panels.act(self, key, op, value)
        except Exception as e:  # noqa
            logger.error("[MEI/editor] 左栏 {} {} 处理出错: {}".format(key, op, error_text(e)))

    def OnBlock(self, index):
        if self.Mode == self.UI:
            if self.Preview:
                return
            if index != self.Selected:
                self.PickProp = None
            self.Selected = index
        else:
            page = self.RPage or {}
            blocks = page.get("blocks") or []
            if not (0 <= index < len(blocks)) or not self.Holds(blocks[index]):
                return
            self.Cell = index
        self.Refresh()

    def OnBlank(self):
        if self.Mode == self.UI:
            self.Selected = None
            self.PickProp = None
        else:
            self.Cell = None
        self.Refresh()

    def OnMoved(self, index, x, y):
        blocks = self.Draft["blocks"] if self.Draft else []
        if self.Mode != self.UI or not 0 <= index < len(blocks):
            return
        block = blocks[index]
        block["x"], block["y"] = x, y
        draft.clamp(block, self.SizeOf(block), draft.area(self.Draft))
        self.Changed()

    def __PickProp(self, item, data):
        """ 物品属性的「选」开着时点了物品栏：写进那块积木（连 attr 一起，数量不要）"""
        index, key = self.PickProp
        self.PickProp = None
        blocks = self.Draft["blocks"] if self.Draft else []
        block_type = self.TypeOf(blocks[index]) if 0 <= index < len(blocks) else None
        prop = block_type.Prop(key) if block_type is not None else None
        if prop is None:
            self.Refresh()
            return
        data = dict(data)
        data.pop("n", None)
        blocks[index][key] = prop.Normalize(data)
        self.Typed.pop((index, key), None)
        draft.clamp(blocks[index], block_type.SizeOf(blocks[index]), draft.area(self.Draft))
        self.Toast(EditorText.ItemSet.format(self.ItemName(item)))
        self.Changed()

    def __PickStation(self, item, data):
        """ 等着的那个工作站 / 图标填上这一样：换第几个、加一个（不重复）、当图标 """
        target, self.PickStation = self.PickStation, None
        stations = self.Draft.setdefault("stations", [])
        if target == "icon":
            self.Draft["icon"] = data
            self.Toast(EditorText.IconSet.format(self.ItemName(item)))
            self.Changed(layout=False)
            return
        key = item_key(data)
        others = [item_key(s) for index, s in enumerate(stations) if index != target]
        if key in others:
            self.Toast(EditorText.StationDup)
            self.Refresh()
            return
        if target == "new":
            if len(stations) >= MAX_STATIONS:
                self.Toast(EditorText.StationFull.format(MAX_STATIONS))
                self.Refresh()
                return
            stations.append(data)
        elif isinstance(target, int) and 0 <= target < len(stations):
            stations[target] = data
        self.Toast(EditorText.StationSet.format(self.ItemName(item)))
        self.Changed(layout=False)

    def PickItem(self, item, _secondary):  # type: (any, bool) -> bool
        """ 点了物品栏里的一样（ModeManager.Intercept 交过来）：当工作站、填进选中的格子 """
        if item is None:
            return True
        data = item_data(item)
        if data is None:
            return True
        if self.Mode == self.UI:
            if self.PickStation is not None:
                self.__PickStation(item, data)
            elif self.PickProp is not None:
                self.__PickProp(item, data)
            else:
                self.Toast(EditorText.PickInUi)
            return True
        holder = draft.holder_of(self.RPage["blocks"], self.Cell, self.Holds) if self.Cell is not None else None
        if holder is None:
            self.Toast(EditorText.NoCellHint)
            return True
        role, number = holder
        entry = draft.cell(self.RDraft, role, number)
        mode = self.CellMode()
        if mode == "alts" and entry:
            alts = entry.setdefault("alts", [])
            keys = set([item_key(entry)] + [item_key(alt) for alt in alts])
            if item_key(data) not in keys and len(alts) < MAX_ALTS:
                alts.append(data)
        else:
            filled = dict(data)
            filled["n"] = int(entry.get("n", 1)) if entry else (1000 if self.CellUnit() == "mB" else 1)
            for key in ("chance", "tag"):
                if entry and key in entry:
                    filled[key] = entry[key]
            draft.set_cell(self.RDraft, role, number, filled)
            if entry is None and mode == "one":
                following = draft.next_empty(self.RPage["blocks"], self.RDraft, self.Cell, self.Holds)
                if following is not None:
                    self.Cell = following
        self.Changed()
        return True
