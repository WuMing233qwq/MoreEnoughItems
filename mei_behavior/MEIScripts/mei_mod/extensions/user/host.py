# coding=utf-8
# ----------------------------------------------------------------------
#  host.py is part of MoreEnoughItems.
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
自制页面的配方页（托管配方页，common/classes/types/page_host.py）：一条配方一行（MeiBlocks.row），
行里按页面的排版建积木（mei_ui/blocks/painter.py，和编辑器的工作区同一套画法），内容区下面一排按钮（配方树、置顶、收藏、+），右边和内容区对齐。
按钮照配方页的标准按钮栏（mei_recipe_common.buttons_panel_horizontal）：13 × 13、隔 1 像素，置顶、收藏开着时是按下去的样子（JSON 里 *_on 那一个）；
+（配方转移）和配方行的一样：一律出，转移不了（这一类没人收、当前界面不收、材料不够）灰着（plus_off），悬停写原因 —— 状态与点了做什么都问配方页（HostedPage.PlusState / Transfer）。
改一条配方在编辑器的「配方」里翻到它（行上不放「修改」）。
行有多大由页面的内容区宽高算（mei_ui/blocks/row.py），运行时写（SetFullSize，写的是尺寸规则）：MEI 的容器是竖排的 stack_panel、
宽跟着最宽的那一行，配方页又跟着容器变宽 —— 行报出自己真正要的宽，配方页就让得开（右边的类型页签不压到按钮）。

同一个类型翻页时容器不换（page.Serial 一样），行留着给下一页接着用：只换内容；换了类型、刷新、关页时容器连同行一起删了，下次重建。
建行、建积木、改显隐都不当场刷新界面，每一轮画完刷新一次（blocks/writer.py 的 flush）；
刚建的行当场取不到子控件，没画好的隔一帧再画（PUMP_DELAY），直到画全。
格子的点击照 MEI 的格子处理（ctx.UI.Actions.ClickItem：工具 / 作弊模式、触屏菜单、PC 左右键查来源 / 用途）：JSON 里格子的按钮把左右键映射到
button.mei.block.primary / secondary，这里在配方页的界面上按名字绑，按 ButtonPath 里的控件名认是哪一行、哪一块
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.api.facades.types import RecipePageHost
from MEIScripts.constants.texts import UserText
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.painter import BlockPainter, template_values
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.row import row_layout
from MEIScripts.mei_mod.ui_script.mei_ui.blocks.writer import ControlWriter, flush, mark_dirty
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.text import error_text

ViewBinder = clientApi.GetViewBinderCls()

ROW_DEF = "MeiBlocks.row"
""" 一行的定义（尺寸按页面运行时写）"""

TOGGLES = {"pin": (UserText.Pin, UserText.Unpin), "star": (UserText.Star, UserText.Unstar)}
""" 有开关的两个按钮：(关着的悬停字, 开着的)；开着时显示 JSON 里 <名字>_on 那一个（按下去的样子）"""

CLICK_PRIMARY = "button.mei.block.primary"
CLICK_SECONDARY = "button.mei.block.secondary"
ROW_ACTIONS = (("button.mei.user.tree", "tree"), ("button.mei.user.pin", "pin"), ("button.mei.user.star", "star"),
               ("button.mei.user.plus", "plus"))

_DEFAULT = row_layout(172, 70)
ROW_TEMPLATE = dict([(("visible", "/buttons/" + name), True) for name in ("tree", "pin", "star", "plus")]
                    + [(("visible", "/buttons/{}_on".format(name)), False) for name in TOGGLES]
                    + [(("visible", "/buttons/plus_off"), False)]
                    + [(("size", ""), _DEFAULT["size"]), (("size", "/content"), (172, 70)),
                       (("pos", "/buttons"), _DEFAULT["buttons"])])
""" 刚建的行本来的样子（MeiBlocks.row 的 JSON：内容区 172 × 70 的那一行）：记成写过，一样的不写（写法同 BlockType.TEMPLATE）"""

PUMP_DELAY = 0.05
""" 没画好的隔多久再画（SDK 定时器最短 0.05 秒，引擎结论 §30）"""

STATE_TICKS = 5
""" 收藏、置顶的状态隔几拍对一次（别处改了也跟上）"""


class _Row(object):
    __slots__ = ("Name", "Control", "Writer", "Painter", "Recipe", "Ready")

    def __init__(self, name, control, writer, painter):
        self.Name = name  # type: str
        self.Control = control
        self.Writer = writer  # type: ControlWriter
        self.Painter = painter  # type: BlockPainter
        self.Recipe = None  # type: any  # 这一行显示的配方；None 是空行（这一页配方不够，藏着）
        self.Ready = False  # type: bool  # 画全了


class UserPageHost(RecipePageHost):
    """ 全部自制页面共用一个（pages(类型 Id) 给 (页面, 字段最大值) 或 None）"""

    TREE = True
    """ 配方是 MEI 认得的原料 / 产物：配方树照常用（recipe_tree/provider.py 认这个标记）"""

    def __init__(self, pages):
        self.Pages = pages
        self.Rows = []  # type: list
        self.Serial = None  # type: any  # 现在这批行建在哪个容器里（page.Serial）
        self.Page = None  # type: any  # 正显示的 HostedPage
        self.Binder = None  # type: ScreenBinder or None
        self.BoundScreen = None
        self.Counter = 0
        self.Pumping = False
        self.Game = None

    # RecipePageHost
# ======================================================================================================================
    def PageSize(self, category, recipes, height):
        info = self.Pages(category.Id)
        row = row_layout(info[0]["w"], info[0]["h"])["size"][1] if info else _DEFAULT["size"][1]
        return max(1, int(height or 0) // row)

    def Show(self, page):
        self.Page = page
        if page.Serial != self.Serial:
            self.Serial = page.Serial
            self.Rows = []  # 旧的行跟着旧容器删了
        self.__Bind(page)
        if self.Pages(page.Category.Id) is None:
            return
        for index, recipe in enumerate(page.Recipes):
            row = self.Rows[index] if index < len(self.Rows) else self.__NewRow(page)
            if row is None:
                break
            row.Recipe = recipe
            row.Ready = False
            row.Writer.SetVisible("", True)
        for row in self.Rows[len(page.Recipes):]:
            row.Recipe = None
            row.Writer.SetVisible("", False)
        self.__Pump()

    def Hide(self, page):
        if page is self.Page:
            self.Page = None

    def Tick(self, page, ticks):
        if page is not self.Page:
            return
        for row in self.Rows:
            if row.Recipe is None:
                continue
            if row.Ready:
                row.Painter.Tick(ticks)
            if ticks % STATE_TICKS == 0:
                self.__PaintButtons(row)
        flush()

    def RecipeAt(self, page, x, y):
        for row in self.Rows:
            if row.Recipe is None:
                continue
            try:
                left, top = row.Control.GetGlobalPosition()
                width, height = row.Control.GetSize()
            except Exception:  # noqa
                continue
            if left <= x < left + width and top <= y < top + height:
                return row.Recipe
        return None

    # 行
# ======================================================================================================================
    def __NewRow(self, page):  # type: (any) -> _Row or None
        self.Counter += 1
        name = "ur{}x{}".format(page.Serial, self.Counter)
        control = page.CreateControl(ROW_DEF, name, update=False)
        if control is None:
            return None
        mark_dirty(page.ScreenNode)
        painter = BlockPainter(page.ScreenNode, self.__Create, self.__Remove)
        writer = ControlWriter(page.ScreenNode, control)
        writer.Prime(template_values(ROW_TEMPLATE))
        row = _Row(name, control, writer, painter)
        self.Rows.append(row)
        return row

    def __Create(self, control_def, name, parent):
        page = self.Page
        return page.CreateControl(control_def, name, parent, update=False) if page is not None else None

    def __Remove(self, control):
        page = self.Page
        if page is not None:
            page.RemoveControl(control)

    def __Fill(self, row):  # type: (_Row) -> bool
        """ 写一行：尺寸、按钮、积木与内容；都写上了给 True """
        info = self.Pages(self.Page.Category.Id) if self.Page is not None else None
        if info is None or row.Recipe is None:
            return True
        data, top = info
        layout = row_layout(data["w"], data["h"])
        row.Writer.Missed = False
        row.Writer.SetSize("", layout["size"])
        row.Writer.SetSize("/content", (data["w"], data["h"]))
        row.Writer.SetPos(layout["buttons"], "/buttons")
        content = row.Writer.Part("/content")
        if content is None:
            return False
        recipe = row.Recipe
        row.Painter.Attach(content)
        row.Painter.Layout(data["blocks"], data["fields"])
        row.Painter.SetContent({"in": recipe.Inputs, "out": recipe.Outputs, "cat": recipe.Catalysts},
                               (recipe.Data or {}).get("f"), top)
        self.__PaintButtons(row)
        return row.Painter.Paint() and not row.Writer.Missed

    def __Pump(self):
        """ 把没画好的行画上；还有没画好的，隔一帧再来 """
        self.Pumping = False
        if self.Page is None or not self.Page.Live:
            return
        pending = False
        for row in self.Rows:
            if row.Recipe is None or row.Ready:
                continue
            try:
                row.Ready = self.__Fill(row)
            except Exception as e:  # noqa  一行画坏了不拖垮配方页
                row.Ready = True
                logger.error("[MEI/user] 自制配方页画一行出错: {}".format(error_text(e)))
            pending = pending or not row.Ready
        flush()
        if pending and not self.Pumping:
            self.Pumping = True
            self.__Timer(PUMP_DELAY, self.__Pump)

    def __Timer(self, delay, callback):
        if self.Game is None:
            self.Game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        self.Game.AddTimer(delay, callback)

    def __PaintButtons(self, row):  # type: (_Row) -> None
        from MEIScripts.mei_mod.state import BookmarkManager, PinManager
        recipe = row.Recipe
        if recipe is None:
            return
        states = {"star": BookmarkManager.HasRecipe(recipe), "pin": PinManager.HasRecipe(recipe)}
        row.Writer.SetHoverText("/buttons/tree/hover/hover_text", UserText.Tree)
        for name, (tip_off, tip_on) in TOGGLES.items():
            on = states[name]
            row.Writer.SetVisible("/buttons/" + name, not on)
            row.Writer.SetVisible("/buttons/{}_on".format(name), on)
            row.Writer.SetHoverText("/buttons/{}/hover/hover_text".format(name), tip_off)
            row.Writer.SetHoverText("/buttons/{}_on/hover/hover_text".format(name), tip_on)
        enabled, hover = self.Page.PlusState(recipe) if self.Page is not None else (False, u"")
        row.Writer.SetVisible("/buttons/plus", enabled)
        row.Writer.SetVisible("/buttons/plus_off", not enabled)
        for name in ("plus", "plus_off"):
            row.Writer.SetHoverText("/buttons/{}/hover/hover_text".format(name), hover)

    # 点击
# ======================================================================================================================
    def __Bind(self, page):
        screen = page.ScreenNode
        if screen is None or screen is self.BoundScreen:
            return
        self.Dispose()
        try:
            binder = ScreenBinder(screen)
            binder.Bind(self.__OnPrimary, ViewBinder.BF_ButtonClickUp, CLICK_PRIMARY)
            binder.Bind(self.__OnSecondary, ViewBinder.BF_ButtonClickUp, CLICK_SECONDARY)
            for name, action in ROW_ACTIONS:
                binder.Bind(self.__RowCallback(action), ViewBinder.BF_ButtonClickUp, name)
        except Exception as e:  # noqa
            logger.error("[MEI/user] 自制配方页的点击绑不上: {}".format(error_text(e)))
            return
        self.Binder, self.BoundScreen = binder, screen

    def Dispose(self):
        """ 摘掉点击的绑定（换了界面、扩展卸载）"""
        binder, self.Binder, self.BoundScreen = self.Binder, None, None
        if binder is not None:
            try:
                binder.UnbindAll()
            except Exception:  # noqa  界面已经没了
                pass

    def __RowCallback(self, action):
        def callback(args):
            self.__OnRow(action, args)
        return callback

    def __Locate(self, args):  # type: (dict) -> tuple
        """ ButtonPath 里的控件名认出是哪一行、哪一块积木：(行, 积木的 BlockView 或 None)；引擎给的路径前面可能多一段，只认名字 """
        parts = [part for part in (args or {}).get("ButtonPath", "").split("/") if part]
        for index, part in enumerate(parts):
            for row in self.Rows:
                if row.Name != part:
                    continue
                view = None
                if index + 2 < len(parts) and parts[index + 1] == "content":
                    view = next((v for v in row.Painter.Views if v is not None and v.Name == parts[index + 2]), None)
                return row, view
        return None, None

    def __OnPrimary(self, args):
        self.__OnSlot(args, False)

    def __OnSecondary(self, args):
        self.__OnSlot(args, True)

    def __OnSlot(self, args, secondary):
        row, view = self.__Locate(args)
        stack = view.Type.ShownItem(view) if view is not None else None
        if stack is None or row.Recipe is None:
            return
        item = getattr(stack, "Item", stack)
        path = view.Path + ("/renderer" if view.Writer.Part("/renderer") is not None else "")
        view.Writer.Missed = False

        def click():
            from MEIScripts.api.facades.ui.actions import ClickItem
            ClickItem(item, path, secondary)
        # ClickItem 要在点击回调之后（下一帧）调
        self.__Timer(0.0, click)

    def __OnRow(self, action, args):
        row, _view = self.__Locate(args)
        recipe = row.Recipe if row is not None else None
        if recipe is None:
            return
        from MEIScripts.mei_mod.state import BookmarkManager, PinManager
        if action == "star":
            BookmarkManager.SetRecipe(recipe, not BookmarkManager.HasRecipe(recipe))
            self.__PaintButtons(row)
            flush()
        elif action == "pin":
            PinManager.ToggleRecipe(recipe)
            self.__PaintButtons(row)
            flush()
        elif action == "plus":
            if self.Page is not None:
                self.Page.Transfer(recipe)
        elif action == "tree":
            primary = recipe.GetPrimaryOutput()
            stack = primary.first() if primary is not None else None
            from MEIScripts.mei_mod.ui_script.mei_ui.recipe_tree import OpenRecipeTree
            OpenRecipeTree(item=getattr(stack, "Item", None), recipe=recipe)
