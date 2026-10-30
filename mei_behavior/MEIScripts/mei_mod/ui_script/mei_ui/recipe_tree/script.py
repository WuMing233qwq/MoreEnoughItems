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
配方树的控制器：把解算（分帧）、画（分帧）、节点菜单、底部汇总、顶栏、收藏串在一起。界面类（screen.py）每帧调 OnTick。

一次改动的路子：菜单 / 顶栏的动作改这一棵树的选择（TreeState）或全局表（TreePrefsManager）→ Resolve 重新解算（配方查过的
不再查，provider 按物品缓存）→ 解算完汇总、顶栏照新的写 → 画布分帧重画，画完把刚才点的那一格摆回原处、菜单跟着它重开。
只是看的东西（折叠、全部展开、折到 2 层）不重新解算，只重画。

交互（docs/architecture/recipe_tree.md）：点原料格出菜单 —— 在当前类型里翻配方、用这条 / 设为首选、换候选、
不再展开 / 当原料（全局）、折叠、以它为根、收藏、查看配方页（关掉树、回到下面的界面开它的配方页）；点工作方块出菜单 ——
换类型、换显示的工作站（只起显示作用，按类型全局记）；PC 和触屏一样用菜单，不做快捷键
"""
import mod.client.extraClientApi as clientApi
from mod_log import logger

from MEIScripts.constants.codes import NameConst, QueryConst
from MEIScripts.constants.texts import TooltipText, TreeText
from MEIScripts.constants.ui import ModeConst, TreeConst, TreePath
from MEIScripts.mei_mod.state import BookmarkManager, TreePrefsManager
from MEIScripts.mei_mod.ui_script.mei_ui.menu.actions import op_toggle_item
from MEIScripts.mei_mod.ui_script.mei_ui.modes.manager import ModeManager
from MEIScripts.utils.binder import ScreenBinder
from MEIScripts.utils.events import EventListener
from MEIScripts.utils.text import error_text, native_str, to_unicode

from .controls.canvas import Scene, TreeCanvas
from .controls.cell import CellSpec, TreeCell, short_count
from .controls.menu import (STRIP_PREVIEW, TreeMenuButton, TreeMenuModel, TreeMenuRow, TreeMenu, control_width, fit_text,
                            fit_width, stepper)
from .controls.summary import TAB_BYPRODUCT, TAB_LACK, TAB_RAW, TAB_TOOL, TreeSummary, tab_rows
from .modules import (DEFAULT, STATE_LEAF, STATE_OK, Solver, TreeState, choice_sig, clamp_qty, key_of, place, shortfall,
                      summarize)
from .provider import TreeProvider

ViewBinder = clientApi.GetViewBinderCls()

TARGET_NODE = "node"  # (TARGET_NODE, 路径签名)：树上的一格（根或原料格）
TARGET_WS = "ws"  # (TARGET_WS, 路径签名)：那一格下面那组的工作方块
TARGET_SUM = "sum"  # 汇总里的一格：物品键
STRIP_ITEM = "item"  # 菜单配方条里的一格：(STRIP_ITEM, 物品键, 数量)
STRIP_STATION = "station"  # 工作方块菜单里的一个工作站：(STRIP_STATION, 物品键)
ROOT_SIG = "r"


def subtree_sizes(nodes):  # type: (list) -> list
    """ 每一格下面一共几格（折叠了左下写「+N」）。BFS 的顺序里父格的 Id 总比子格小，倒着加一遍就行 """
    sizes = [0] * len(nodes)
    for node in reversed(nodes):
        if node.Parent is not None:
            sizes[node.Parent] += sizes[node.Id] + 1
    return sizes


class RecipeTreeScript(object):
    """ param：{"item", "recipe", "saved", "qty"}（recipe_tree.OpenRecipeTree）；provider / prefs 给探针换成假的 """

    SolveBudgetMs = 4.0  # 每帧解算多久（node.py 里调）
    DrawBudgetMs = 6.0  # 每帧画多久
    ToastTicks = 60  # 提示留多少帧（每秒 30 帧）
    TitleX = 24  # 顶栏根物品名从哪儿开始（根格 20 + 间隔 4，与 JSON 里 title 的 offset 一致）
    BarGaps = ("gap_0", "gap_1", "gap_2", "gap_3", "gap_4", "gap_5", "gap_6", "gap_7", "gap_8", "close")
    """ 顶栏按钮条里不随字变的那几个（间隔、小 x）：宽在 JSON 里，脚本读回来算按钮条一共多宽 """
    HistoryMax = 16  # 「返回」最多记几棵

    def __init__(self, screen, param=None, provider=None, prefs=None):
        self.Screen = screen
        self.Param = param or {}
        self.Provider = provider or TreeProvider()
        self.Prefs = prefs or TreePrefsManager
        self.Metrics = DEFAULT
        self.State = None  # type: TreeState or None
        self.Solver = None  # type: Solver or None
        self.Summary = None  # type: any
        self.Subtree = []  # type: list
        self.Have = {}  # type: dict  # 背包：{物品键: 有几个}
        self.Lack = {}  # type: dict  # 背包放进库存走一遍还缺的原料（中间物也扣，「缺少材料」页）
        self.History = []  # type: list  # 「以它为根」之前的那几棵（TreeState）
        self.Tab = TAB_RAW
        self.Bindings = None  # type: ScreenBinder or None
        self.Events = None  # type: EventListener or None
        self.Canvas = None  # type: TreeCanvas or None
        self.Menu = None  # type: TreeMenu or None
        self.SummaryPanel = None  # type: TreeSummary or None
        self.RootCell = None  # type: TreeCell or None
        self.TopControls = {}  # type: dict
        self.TopWidths = {}  # type: dict  # 顶栏每个按钮按字算出的宽
        self.BarFixed = 0  # type: int  # 顶栏按钮条里间隔、小 x 的宽
        self.Labels = {}  # type: dict
        self.MenuTarget = None  # type: tuple or None
        self.MenuBrowse = None  # type: str or None  # 菜单里翻到的那条配方（Id；None 是正在用的那条）
        self.MenuCell = None  # type: any  # 点开菜单的那一格（找不到新格子时按它摆菜单）
        self.SolveAnchor = None  # type: any
        self.SolveReset = False  # type: bool
        self.ToastLeft = 0  # type: int
        self.CloseRequested = False  # type: bool
        self.AfterClose = None  # type: tuple or None  # (物品, 查询方向)：关掉之后在下面的界面开它的配方页
        self.Ready = False  # type: bool

    # 生命周期
# ======================================================================================================================
    def InitScript(self):
        self.Bindings = ScreenBinder(self.Screen)
        get = self.Screen.GetBaseUIControl
        for name, path in (("status", TreePath.Status), ("title", TreePath.Title), ("qty", TreePath.Qty),
                           ("toast", TreePath.Toast), ("busy", TreePath.Busy)):
            self.Labels[name] = get(path)
        self.Canvas = TreeCanvas(self.Screen, self.OnCanvasClick)
        self.Menu = TreeMenu(self.Screen, self.Bindings, self.CloseMenu, self.OnStripClick)
        self.SummaryPanel = TreeSummary(self.Screen, self.Bindings, self.OnTab, self.OnRefresh, self.OnSummaryCell)
        self.__InitTop()
        self.Bindings.Bind(self.OnCloseKey, ViewBinder.BF_ButtonClickUp, TreeConst.CloseName)
        self.Bindings.Bind(self.OnCloseButton, ViewBinder.BF_ButtonClickUp, TreeConst.TopClose)
        system = clientApi.GetSystem(NameConst.NameSpace, NameConst.ClientSysName)
        if system is not None:
            self.Events = EventListener(system)
            self.Events.Listen("MouseWheelClientEvent", self.OnWheel)
            self.Events.Listen("PointerPressReleaseClientEvent", self.OnPointerRelease)
        self.Menu.Hide()
        self.__SetLabel("toast", "", False)
        self.Have = self.Provider.Supply()
        self.State = self.__InitialState()
        self.Ready = True
        if self.State is None:
            self.ShowToast(TreeText.NoRoot)
            return
        self.Resolve(reset=True)

    def DestroyScript(self):
        self.Ready = False
        try:
            # 首选、当原料：关配方树就写（排着的合并写等不到退出存档 —— SDK 那时把模组的定时器全清了）
            self.Prefs.Flush()
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 写配方树的首选失败: {}".format(error_text(e)))
        if self.Menu is not None:
            self.Menu.Destroy()  # 配方预览的脚本、绑定、控件
        if self.Events is not None:
            self.Events.UnlistenAll()
            self.Events = None
        if self.Bindings is not None:
            self.Bindings.UnbindAll()
            self.Bindings = None

    def OnTick(self):
        """ 每帧（界面的 Update，每秒 30 次）：推进解算、画布，提示倒计时 """
        if not self.Ready:
            return
        if self.ToastLeft > 0:
            self.ToastLeft -= 1
            if self.ToastLeft == 0:
                self.__SetLabel("toast", "", False)
        solver = self.Solver
        if solver is not None and not solver.Done:
            if solver.Step(self.SolveBudgetMs):
                self.__OnSolved()
            else:
                self.__SetLabel("status", TreeText.Solving.format(len(solver.Nodes)))
        if self.Canvas.Tick(self.DrawBudgetMs):
            self.__OnDrawn()
        self.Menu.Tick()  # 菜单里的配方预览建齐了才排版、显示

    def __InitialState(self):  # type: () -> TreeState or None
        param = self.Param
        saved = param.get("saved")
        if saved:
            state = TreeState.FromEntry(saved)
            if state is not None:
                return state
        item, recipe = param.get("item"), param.get("recipe")
        if item is None and recipe is not None:
            primary = recipe.GetPrimaryOutput() if hasattr(recipe, "GetPrimaryOutput") else None
            stacks = primary.get_stacks() if primary is not None else ()
            item = getattr(stacks[0], "Item", None) if stacks else None
        key = self.Provider.Remember(item)
        if key is None:
            return None
        return TreeState(key, param.get("qty") or 1, getattr(recipe, "Id", None) if recipe is not None else None)

    # 解算、画
# ======================================================================================================================
    def Resolve(self, anchor=None, reset=False):
        """ 重新解算（分帧，OnTick 推进）；解算完重画，anchor 那一格摆回原处，reset 时根回到上方正中 """
        self.Solver = Solver(self.Provider, self.State, self.Prefs)
        self.SolveAnchor = anchor
        self.SolveReset = reset
        if self.Menu is not None:
            # 菜单还亮着，按钮抓着的是上一版的格子（下标、父格子都对不上新的这一版）：解算、重画完 RenderMenu 再排一份
            self.Menu.Freeze()
        self.__SetLabel("status", TreeText.Solving.format(1))

    def __OnSolved(self):
        nodes = self.Solver.Nodes
        self.Subtree = subtree_sizes(nodes)
        self.Summary = summarize(nodes, self.State.Qty)
        self.Lack = shortfall(nodes, self.State.Qty, self.Have)
        self.__RefreshTop()
        self.__RefreshSummary()
        self.Draw(self.SolveAnchor, self.SolveReset)

    def Draw(self, anchor=None, reset=False):
        if self.Solver is None or not self.Solver.Done:
            return
        placement = place(self.Solver.Nodes, self.State.Fold, self.Metrics)
        if reset:
            self.Canvas.Scene = None
        self.Canvas.Draw(self.__Scene(placement), anchor)

    def __OnDrawn(self):
        solver = self.Solver
        depth = solver.MaxDepthReached() if solver.Nodes else 0
        self.__SetLabel("status", TreeText.Status.format(len(solver.Nodes), depth))
        if self.MenuTarget is not None:
            self.RenderMenu()

    def __Scene(self, placement):  # type: (any) -> Scene
        nodes = self.Solver.Nodes
        m = self.Metrics
        scene = Scene((placement.Width, placement.Height))
        # 根排第一个：画布按第一格认根（回到根、找不到锚点时摆回它）
        for node_id in [0] + [i for i in placement.Cells if i != 0]:
            pos = placement.Cells.get(node_id)
            if pos is not None:
                scene.Cells.append(self.__NodeSpec(nodes[node_id], pos))
        for node_id, (x, y) in placement.Groups.items():
            node = nodes[node_id]
            scene.Cells.append(self.__WsSpec(node, (x, y)))
            scene.WsFrames.append((x - m.Frame, y - m.Frame))
            if node.Children:
                scene.IngFrames.append(((x + m.Cell + m.WsGap - m.Frame, y - m.Frame),
                                        (len(node.Children) * m.Cell + 2 * m.Frame, m.Cell + 2 * m.Frame)))
        scene.Lines = list(placement.Lines)
        return scene

    def __NodeSpec(self, node, pos):  # type: (any, tuple) -> CellSpec
        fold = ""
        if node.State == STATE_OK and node.Sig in self.State.Fold:
            fold = TreeText.Hidden.format(self.Subtree[node.Id])
        usable = [c for c in self.__TypeCandidates(node) if not c.Stuck]
        return CellSpec((TARGET_NODE, node.Sig), pos, self.Provider.RenderData(node.Key), count=short_count(node.Need),
                        fold=fold, badge=TreeConst.BadgeColors.get(node.State),
                        multi=node.State == STATE_OK and len(usable) > 1)

    def __WsSpec(self, node, pos):  # type: (any, tuple) -> CellSpec
        station = self.__Station(node.Type)
        return CellSpec((TARGET_WS, node.Sig), pos, self.Provider.RenderData(station) if station else None,
                        crafts=short_count(node.Crafts), multi=len(node.Types()) > 1)

    def __Station(self, type_id):  # type: (str) -> str or None
        """ 工作方块格显示哪个工作站：全局表里这个类型记的（还在工作站里的话）→ 第一个 """
        if not type_id:
            return None
        stations = self.Provider.Stations(type_id)
        chosen = self.Prefs.Station(type_id)
        if chosen in stations:
            return chosen
        return stations[0] if stations else None

    def __TypeCandidates(self, node):  # type: (any) -> list
        """
        原料格的菜单只在当前类型里翻配方：正在用的那条的类型 → 本树选的类型（这一格没解出配方时）；都没有就全部。
        **先看正在用的**：要是先看本树选的类型 —— 那个类型在这一格只有递归配方、解算器退回了别的类型时，
        菜单写的是选的类型、工作方块格与它的菜单写的是实际的类型，一格两个类型名
        """
        type_id = node.Type or self.State.Types.get(node.Key)
        if type_id:
            typed = node.InType(type_id)
            if typed:
                return typed
        return list(node.Candidates)

    # 顶栏
# ======================================================================================================================
    def __InitTop(self):
        get = self.Screen.GetBaseUIControl
        control = get(TreePath.RootCell)
        if control is not None:
            self.RootCell = TreeCell(self.Screen, control, -1)
            button = self.RootCell.Button()
            if button is not None:
                button.AddTouchEventParams({"isSwallow": True})
                button.SetButtonTouchUpCallback(self.OnRootCellUp)
        texts = {"minus": TreeText.Minus, "plus": TreeText.Plus, "x64": TreeText.X64, "center": TreeText.Center,
                 "unfold": TreeText.Unfold, "fold2": TreeText.Fold2, "back": TreeText.Back, "save": TreeText.Save}
        for name in TreeConst.TopButtons:
            control = get(TreePath.Bar + "/" + name)
            self.TopControls[name] = control
            label = control.GetChildByPath(TreePath.ButtonLabel) if control is not None else None
            if label is not None:
                label.asLabel().SetText(native_str(texts.get(name, "")))
            # 按字改宽（「收藏」那个也放得下「更新」）。按钮在 stack_panel 里：用 SetFullSize 改尺寸规则，stack_panel 才跟着重排（引擎结论 §28）
            width = fit_width([texts.get(name, "")] + ([TreeText.Update] if name == "save" else []))
            self.TopWidths[name] = width
            if control is not None:
                control.SetFullSize("x", {"absoluteValue": width})
            self.Bindings.Bind(self.__TopHandler(name), ViewBinder.BF_ButtonClickUp, TreeConst.ButtonName.format(name))
        self.BarFixed = sum(control_width(get(TreePath.Bar + "/" + name)) for name in self.BarGaps)

    def __TopHandler(self, name):
        def handler(_args=None):
            try:
                self.OnTop(name)
            except Exception as e:  # noqa  按钮回调里抛出去引擎不给日志（引擎结论 §15）
                logger.error("[MEI/tree] 顶栏按钮 {} 出错: {}".format(name, error_text(e)))
        return handler

    def OnTop(self, name):  # type: (str) -> None
        if self.State is None:
            return
        if name == "minus":
            self.SetQty(self.State.Qty - 1)
        elif name == "plus":
            self.SetQty(self.State.Qty + 1)
        elif name == "x64":
            self.SetQty(1 if self.State.Qty == 64 else 64)
        elif name == "center":
            self.Canvas.CenterRoot()
        elif name == "unfold":
            self.State.Fold = set()
            self.Draw(self.__CanvasTarget())
        elif name == "fold2":
            if self.Solver is None or not self.Solver.Done:
                return  # 解算中 Nodes 只有一部分：折出来的不全，解算完画的就是这一份
            self.State.Fold = set(node.Sig for node in self.Solver.Nodes if node.State == STATE_OK and node.Depth == 2)
            self.Draw(self.__CanvasTarget())
        elif name == "back":
            self.Back()
        elif name == "save":
            self.Save()

    def __RefreshTop(self):
        root = self.State.Root
        if self.RootCell is not None:
            self.RootCell.Apply(CellSpec((TARGET_NODE, ROOT_SIG), (0, 0), self.Provider.RenderData(root),
                                         count=short_count(self.State.Qty)))
        qty_text = TreeText.Qty.format(self.State.Qty)
        qty_w = fit_width([qty_text], 20)
        qty_panel = self.Screen.GetBaseUIControl(TreePath.Bar + "/qty")
        if qty_panel is not None:
            qty_panel.SetFullSize("x", {"absoluteValue": qty_w})
        self.__SetLabel("qty", qty_text)
        # 根物品名：顶栏减去右边那一排按钮剩下多宽就写多长，放不下截短
        bar_w = sum(self.TopWidths.values()) + qty_w + self.BarFixed
        room = control_width(self.Screen.GetBaseUIControl(TreePath.Top)) - self.TitleX - bar_w - 4
        self.__SetLabel("title", fit_text(self.Provider.NameOf(root), max(0, room)))
        self.__SetEnabled("back", bool(self.History))
        save = self.TopControls.get("save")
        label = save.GetChildByPath(TreePath.ButtonLabel) if save is not None else None
        if label is not None:
            label.asLabel().SetText(native_str(TreeText.Update if self.__SavedIndex() is not None else TreeText.Save))

    def __SetEnabled(self, name, enabled):
        control = self.TopControls.get(name)
        mask = control.GetChildByPath(TreePath.ButtonMask) if control is not None else None
        if mask is not None:
            mask.SetVisible(not enabled)

    def SetQty(self, qty):  # type: (int) -> None
        qty = clamp_qty(qty)
        if qty == self.State.Qty:
            return
        self.State.Qty = qty
        self.Resolve(self.__CanvasTarget())

    def Back(self):
        if not self.History:
            return
        self.State = self.History.pop()
        self.CloseMenu()
        self.Resolve(reset=True)

    # 收藏这一棵树（一整棵存成一条收藏，能展开，展开就是原料汇总）
# ======================================================================================================================
    def __SavedIndex(self):  # type: () -> int or None
        finder = getattr(BookmarkManager, "TreeIndex", None)
        return finder(self.State.Root) if finder is not None and self.State is not None else None

    def Save(self):
        # 解算中 Summary 还是上一版的（数量、选择已经改了）：存进去的展开对不上这棵树
        if self.Summary is None or self.State is None or self.Solver is None or not self.Solver.Done:
            return
        entry = self.State.ToEntry(self.Summary.Raw)
        result = BookmarkManager.SaveTree(entry)
        self.ShowToast({"added": TreeText.Saved, "updated": TreeText.Updated}.get(result, TreeText.SaveFailed))
        self.__RefreshTop()

    # 汇总
# ======================================================================================================================
    def __RefreshSummary(self):
        if self.Summary is None:
            return
        summary = self.Summary
        rows = tab_rows(self.Tab, summary, self.Have, summary.Flags, self.Lack)
        # 右上的说明只在数字有保留时写：树太大没算完（部分结果）。副产物抵扣之后不再有「逐个相加（上界）」
        note = TreeText.Partial if self.Solver.Truncated else u""
        lacking = sum(1 for key in summary.Raw if self.Lack.get(key, 0) > 0)
        foot = TreeText.Foot.format(len(summary.Raw), len(summary.Raw) - lacking, lacking)
        self.SummaryPanel.SetRows(self.Tab, rows, note, foot, self.Provider.RenderData)

    def OnTab(self, tab):  # type: (str) -> None
        if tab == self.Tab:
            return
        self.Tab = tab
        if self.MenuTarget is not None and self.MenuTarget[0] == TARGET_SUM:
            self.CloseMenu()
        self.__RefreshSummary()

    def OnRefresh(self):
        self.Have = self.Provider.Supply()
        if self.Solver is not None and self.Solver.Done and self.State is not None:
            self.Lack = shortfall(self.Solver.Nodes, self.State.Qty, self.Have)
        self.__RefreshSummary()
        if self.MenuTarget is not None and self.MenuTarget[0] == TARGET_SUM:
            self.RenderMenu()

    # 点格子、菜单
# ======================================================================================================================
    def OnCanvasClick(self, target, cell):
        self.OpenMenu(target, cell)

    def OnRootCellUp(self, _args=None):
        self.OpenMenu((TARGET_NODE, ROOT_SIG), self.RootCell)

    def OnSummaryCell(self, key, cell):
        self.OpenMenu((TARGET_SUM, key), cell)

    def OpenMenu(self, target, cell=None):  # type: (tuple, any) -> None
        if self.Solver is None or not self.Solver.Done:
            return
        # 作弊模式：点哪一格就给那一样（一组），不开菜单。工具模式在配方树里没有拿起的宿主，照平时（docs/architecture/modes.md）
        if ModeManager.Current() == ModeConst.Cheat and ModeManager.Give(self.TargetItem(target), True):
            return
        self.MenuTarget = target
        self.MenuBrowse = None
        self.MenuCell = cell
        self.RenderMenu()

    def CloseMenu(self):
        self.MenuTarget = None
        self.MenuBrowse = None
        self.MenuCell = None
        if self.Menu is not None:
            self.Menu.Hide()
        if self.Canvas is not None:
            self.Canvas.Select(None)
        if self.SummaryPanel is not None:
            self.SummaryPanel.Select(None)
        if self.RootCell is not None:
            self.RootCell.SetSelected(False)

    def RenderMenu(self):
        """ 按 MenuTarget 重排菜单（改完东西、重画完都会再来一次，菜单跟着那一格走）；那一格没了就收起 """
        target = self.MenuTarget
        if target is None or self.Solver is None or not self.Solver.Done:
            return
        kind, ident = target
        model = None
        try:
            if kind == TARGET_SUM:
                model = self.__SumMenu(ident)
            else:
                node = self.Solver.Find(ident)
                if node is not None:
                    model = self.__WsMenu(node) if kind == TARGET_WS else self.__NodeMenu(node)
        except Exception as e:  # noqa
            logger.error("[MEI/tree] 排菜单出错: {}".format(error_text(e)))
        if model is None or not self.__TargetShown(target):
            self.CloseMenu()
            return
        self.Menu.Show(model, self.__AnchorRect(target))
        self.Canvas.Select(target if kind != TARGET_SUM else None)
        self.SummaryPanel.Select(ident if kind == TARGET_SUM else None)
        if self.RootCell is not None:
            self.RootCell.SetSelected(target == (TARGET_NODE, ROOT_SIG))

    def __TargetShown(self, target):  # type: (tuple) -> bool
        """
        菜单跟着的那一格还画着吗：画布画完了却找不到它（顶栏「折两层」把它折了进去），汇总里那一格不在这一页了（刷新后它不缺了）——
        这时退回点开时的那个格子控件，摆的是池里别的格子的位置。画布正画着的时候池里还是上一版，等画完（__OnDrawn 再排一次）再判
        """
        kind, ident = target
        if kind == TARGET_SUM:
            return any(c.Target == ident for c in self.SummaryPanel.Cells)
        if target == (TARGET_NODE, ROOT_SIG) or self.Canvas.IsDrawing():
            return True
        return self.Canvas.CellOf(target) is not None

    def __AnchorRect(self, target):  # type: (tuple) -> tuple
        """ 点开菜单的那一格在界面根面板里的矩形：重画后按 target 找新格子，找不到用点的那一格 """
        kind, ident = target
        if kind == TARGET_SUM:
            cell = next((c for c in self.SummaryPanel.Cells if c.Target == ident), None)
        else:
            cell = self.Canvas.CellOf(target)
            if cell is None and target == (TARGET_NODE, ROOT_SIG):
                cell = self.RootCell
        cell = cell or self.MenuCell
        try:
            x, y = cell.Control.GetGlobalPosition()
            rx, ry = self.Screen.GetBaseUIControl(TreePath.Root).GetGlobalPosition()
            return x - rx, y - ry, self.Metrics.Cell, self.Metrics.Cell
        except Exception:  # noqa
            return 4, 4, 0, 0

    def __CanvasTarget(self):  # type: () -> tuple or None
        """ 重画时摆回原处的那一格：菜单开着的那一格（汇总里的不算）"""
        target = self.MenuTarget
        return target if target is not None and target[0] != TARGET_SUM else None

    def OnStripClick(self, target):
        if target[0] == STRIP_STATION:
            if self.Solver is None or not self.Solver.Done:
                return
            node = self.Solver.Find(self.MenuTarget[1]) if self.MenuTarget is not None else None
            if node is not None and node.Type:
                self.SetStation(node.Type, target[1])
            return
        if target[0] == STRIP_ITEM:
            self.Menu.SetInfo(TreeText.StripItem.format(self.Provider.NameOf(target[1]).decode("utf-8", "replace"),
                                                        target[2]))
            return
        if target[0] == STRIP_PREVIEW:
            # 配方预览里的一格：格子给的是 Item，换成物品键再取名字（和配方条一样写灰字）
            item = target[1]
            key = key_of(getattr(item, "ItemId", ""), getattr(item, "AuxValue", 0))
            self.Menu.SetInfo(TreeText.StripItem.format(self.Provider.NameOf(key).decode("utf-8", "replace"), target[2]))

    def __Item(self, key):  # type: (str) -> any
        return self.Provider.ItemOf(key)

    def TargetItem(self, target):  # type: (tuple) -> any
        """ 一格显示的那一样物品：树上的格子是它的物品、工作方块格是显示着的那个工作站、汇总里的是那一样；认不出给 None """
        kind, ident = target
        if kind == TARGET_SUM:
            return self.__Item(ident)
        node = self.Solver.Find(ident) if self.Solver is not None else None
        if node is None:
            return None
        if kind == TARGET_WS:
            station = self.__Station(node.Type)
            return self.__Item(station) if station else None
        return self.__Item(node.Key)

    # 菜单：原料格 / 根
# ======================================================================================================================
    def __NodeMenu(self, node):  # type: (any) -> TreeMenuModel
        provider = self.Provider
        is_root = node.Id == 0
        rows, strip, arrow = [], [], None
        preview = None
        title = provider.HoverOf(node.Key)
        if node.State == STATE_OK:
            info = TreeText.NeedInfo.format(node.Need, node.Crafts) + (
                TreeText.Surplus.format(node.Surplus) if node.Surplus else u"")
        else:
            info = TreeText.NeedState.format(node.Need, TreeText.States.get(node.State, TreeText.NoRecipe))
        candidates = self.__TypeCandidates(node)
        if candidates:
            index = self.__BrowseIndex(node, candidates)
            candidate = candidates[index]
            strip, arrow = self.__RecipeStrip(node, candidate)
            # 先试这条配方的类型自己的配方预览，预览不了菜单用上面的配方条（controls/preview.py）
            preview = candidate.Recipe.Source
            # 标题「类型名 · 物品名」一行（照收藏的配方预览）：配方预览、配方条两种都是它，灰字里不再写类型名
            title = TooltipText.Recipe.format(to_unicode(provider.TypeName(candidate.Recipe.Type)), to_unicode(title))
            info += u"\n" + self.__CandidateInfo(node, candidate, index, len(candidates))
            many = len(candidates) > 1
            rows.append(stepper(TreeText.SecRecipe, TreeText.Value.format(index + 1, len(candidates)),
                                lambda: self.BrowseRecipe(-1), lambda: self.BrowseRecipe(1), many, many))
            in_use = node.Recipe is not None and candidate.Recipe.Id == node.Recipe.Id
            is_default = self.Prefs.Default(node.Key) == candidate.Recipe.Id
            recipe = candidate.Recipe
            rows.append(TreeMenuRow(TreeText.SecChoose, [
                TreeMenuButton(TreeText.InUse if in_use else TreeText.Use, lambda: self.UseRecipe(node, recipe),
                               enabled=not in_use and not candidate.Stuck),
                TreeMenuButton(TreeText.UnsetDefault if is_default else TreeText.SetDefault,
                               lambda: self.SetDefault(node, None if is_default else recipe),
                               enabled=is_default or not candidate.Stuck),
            ]))
        picks = self.__PickChoices(node) if not is_root else []
        if len(picks) > 1:
            index = picks.index(node.Key) if node.Key in picks else 0
            rows.append(stepper(TreeText.SecPick, TreeText.Value.format(index + 1, len(picks)),
                                lambda: self.StepPick(node, -1), lambda: self.StepPick(node, 1)))
        expand = []
        if not is_root:
            stopped = node.Key in self.State.Stop
            expand.append(TreeMenuButton(TreeText.Resume if stopped else TreeText.Stop, lambda: self.ToggleStop(node)))
            raw = self.Prefs.IsRaw(node.Key)
            expand.append(TreeMenuButton(TreeText.UnsetRaw if raw else TreeText.SetRaw, lambda: self.ToggleRaw(node.Key)))
        if node.State == STATE_OK:
            folded = node.Sig in self.State.Fold
            expand.append(TreeMenuButton(TreeText.UnfoldOne if folded else TreeText.Fold, lambda: self.ToggleFold(node)))
        if expand:
            rows.append(TreeMenuRow(TreeText.SecExpand, expand))
        rows.append(TreeMenuRow(TreeText.SecOther, self.__OtherButtons(node.Key, None if is_root else node.Need)))
        return TreeMenuModel(TreeText.KindRoot if is_root else TreeText.KindNode, title,
                             strip=strip, arrow=arrow, info=info, rows=rows, recipe=preview, preview_title=title)

    def __OtherButtons(self, key, qty):  # type: (str, int or None) -> list
        """ 以它为根（qty 给 None 就不出：已经是根）、收藏 / 取消收藏、查看配方页 """
        buttons = []
        if qty is not None:
            buttons.append(TreeMenuButton(TreeText.AsRoot, lambda: self.AsRoot(key, qty)))
        item = self.__Item(key)
        had = item is not None and BookmarkManager.HasItem(item)
        buttons.append(TreeMenuButton(TreeText.Unbookmark if had else TreeText.Bookmark, lambda: self.ToggleBookmark(key),
                                      enabled=item is not None and (had or not BookmarkManager.IsTabFull())))
        buttons.append(TreeMenuButton(TreeText.ViewRecipes, lambda: self.ViewRecipes(key), enabled=item is not None))
        return buttons

    def __BrowseIndex(self, node, candidates):  # type: (any, list) -> int
        ids = [c.Recipe.Id for c in candidates]
        for wanted in (self.MenuBrowse, node.Recipe.Id if node.Recipe is not None else None):
            if wanted in ids:
                return ids.index(wanted)
        return 0

    def __RecipeStrip(self, node, candidate):  # type: (any, any) -> tuple
        """ 菜单里那一条配方：工作方块、原料（单次的用量，会绕回的暗一点）→ 产物；格子不够时原料只放得下前几样 """
        recipe = candidate.Recipe
        render = self.Provider.RenderData
        specs = []
        station = self.__Station(recipe.Type)
        if station:
            specs.append(CellSpec((STRIP_ITEM, station, 1), render=render(station)))
        room = TreeConst.StripCells - len(specs) - 1
        for choices, count in recipe.Inputs[:room]:
            picked = self.State.Picks.get(choice_sig(choices))
            key = picked if picked in choices else choices[0]
            specs.append(CellSpec((STRIP_ITEM, key, count), render=render(key), count=short_count(count),
                                  dim=choices[0] in candidate.Stuck))
        arrow = len(specs)
        specs.append(CellSpec((STRIP_ITEM, node.Key, recipe.Output), render=render(node.Key),
                              count=short_count(recipe.Output)))
        return specs, arrow

    def __CandidateInfo(self, node, candidate, index, total):  # type: (any, any, int, int) -> unicode
        """
        第二行灰字：第几条 + 附加状态（类型名在标题那一行；「首选」不写 —— 下面「设为首选 / 取消首选」的按钮看得出来）
        """
        recipe = candidate.Recipe
        text = TreeText.RecipeInfo.format(index + 1, total)
        if node.Recipe is not None and recipe.Id == node.Recipe.Id:
            text += TreeText.Current
        if candidate.Reverse:
            text += TreeText.Reverse
        if candidate.Stuck:
            names = TreeText.NameSep.join(self.Provider.NameOf(key).decode("utf-8", "replace") for key in candidate.Stuck[:2])
            text += TreeText.Stuck.format(names)
        if self.Provider.IsPinned(recipe):
            text += TreeText.Pinned
        return text

    # 菜单：工作方块（点它换类型、换显示的工作站）
# ======================================================================================================================
    def __WsMenu(self, node):  # type: (any) -> TreeMenuModel or None
        if node.State != STATE_OK:
            return None
        provider = self.Provider
        types = node.Types()
        current = node.Type
        index = types.index(current) if current in types else 0
        stations = provider.Stations(current) if current else []
        shown = self.__Station(current)
        strip = [CellSpec((STRIP_STATION, key), render=provider.RenderData(key), selected=key == shown)
                 for key in stations[:TreeConst.StripCells]]
        name = provider.TypeName(current).decode("utf-8", "replace") if current else u""
        rows = []
        if types:
            many = len(types) > 1
            rows.append(stepper(TreeText.SecType, TreeText.TypeValue.format(name, index + 1, len(types)),
                                lambda: self.SetType(node, types[(index - 1) % len(types)]),
                                lambda: self.SetType(node, types[(index + 1) % len(types)]), many, many))
        if len(stations) > 1:
            at = stations.index(shown) if shown in stations else 0
            rows.append(stepper(TreeText.SecStation, TreeText.Value.format(at + 1, len(stations)),
                                lambda: self.SetStation(current, stations[(at - 1) % len(stations)]),
                                lambda: self.SetStation(current, stations[(at + 1) % len(stations)])))
        info = TreeText.StationInfo.format(provider.NameOf(shown).decode("utf-8", "replace")) if shown else u""
        return TreeMenuModel(TreeText.KindWs, TreeText.Crafts.format(name, node.Crafts), strip=strip, info=info,
                             rows=rows)

    # 菜单：汇总里的一格
# ======================================================================================================================
    def __SumMenu(self, key):  # type: (str) -> TreeMenuModel or None
        summary = self.Summary
        if summary is None:
            return None
        have = int(self.Have.get(key, 0) or 0)
        if self.Tab in (TAB_RAW, TAB_LACK) and (key in summary.Raw or key in self.Lack):
            # 还缺几个看背包放进库存走的那一遍：背包里的中间材料（铁锭）抵掉的原料（粗铁）不算缺，菜单里写抵掉了几个
            need = summary.Raw.get(key, 0)
            lack = self.Lack.get(key, 0)
            info = TreeText.SumRaw.format(need, have, lack)
            if need - have > lack:
                info += TreeText.SumCovered.format(need - have - lack)
            if self.Tab == TAB_LACK:
                need = lack
        elif self.Tab == TAB_BYPRODUCT and key in summary.Byproducts:
            need = summary.Byproducts[key]
            info = TreeText.SumByproduct.format(need)
            chance = summary.Chance.get(key)
            if chance:
                info += TreeText.SumChance.format(chance[0], "{:g}".format(round(chance[1], 1)))
        elif self.Tab == TAB_TOOL and key in summary.Tools:
            need = 1
            info = TreeText.SumTool
        else:
            return None
        raw = self.Prefs.IsRaw(key)
        rows = [
            TreeMenuRow(TreeText.SecExpand, [TreeMenuButton(TreeText.UnsetRaw if raw else TreeText.SetRaw,
                                                            lambda: self.ToggleRaw(key))]),
            TreeMenuRow(TreeText.SecOther, self.__OtherButtons(key, need if key != self.State.Root else None)),
        ]
        return TreeMenuModel(TreeText.KindSum, self.Provider.HoverOf(key), info=info, rows=rows)

    # 动作
# ======================================================================================================================
    def BrowseRecipe(self, step):  # type: (int) -> None
        node = self.Solver.Find(self.MenuTarget[1]) if self.MenuTarget is not None else None
        if node is None:
            return
        candidates = self.__TypeCandidates(node)
        if candidates:
            index = (self.__BrowseIndex(node, candidates) + step) % len(candidates)
            self.MenuBrowse = candidates[index].Recipe.Id
            self.RenderMenu()

    def UseRecipe(self, node, recipe):
        """ 这棵树里这个物品用这条（同一个物品在树里别处也跟着换）"""
        if node.Id == 0:
            self.State.RootRecipe = None
        self.State.Choices[node.Key] = recipe.Id
        self.MenuBrowse = None
        self.Resolve((TARGET_NODE, node.Sig))

    def SetDefault(self, node, recipe):
        """ 设为首选 / 取消首选：写全局表，以后每棵树先用它；这棵树里对它的单独选择清掉 """
        if recipe is not None:
            if not self.Prefs.SetDefault(node.Key, recipe.Id) and self.Prefs.Default(node.Key) != recipe.Id:
                self.ShowToast(TreeText.PrefsFull)  # 全局表记满了：什么都没存，这棵树里的选择也别动
                return
            self.State.Choices.pop(node.Key, None)
            if node.Id == 0 and self.State.RootRecipe != recipe.Id:
                self.State.RootRecipe = None
            self.ShowToast(TreeText.DefaultSet)
        else:
            self.Prefs.SetDefault(node.Key, None)
            self.ShowToast(TreeText.DefaultUnset)
        self.MenuBrowse = None
        self.Resolve((TARGET_NODE, node.Sig))

    def __Parent(self, node):  # type: (any) -> any
        """ 父格子：按签名找（签名是「父格子的签名/格位:物品键」），不按 node.Parent 的下标 —— 下标只在算出它的那一版里对 """
        if self.Solver is None or not self.Solver.Done or node.Parent is None or "/" not in node.Sig:
            return None
        return self.Solver.Find(node.Sig.rsplit("/", 1)[0])

    def __PickChoices(self, node):  # type: (any) -> list
        """
        这一格能换成的候选：从根到父格子的路上已经有的不算 —— 选了它就绕回自己，解算器不用它（换成第一个不在路上的），
        菜单还会按新键找那一格、找不到就收起；全在路上的话照全部（解算器那时也只能用第一个）
        """
        choices = list(node.Choices or ())
        parent = self.__Parent(node)
        if parent is None:
            return choices
        return [key for key in choices if key not in parent.Path] or choices

    def StepPick(self, node, step):
        """ 换候选：多候选的原料（标签）这棵树里用哪一个（树里同一组候选都跟着换）"""
        parent = self.__Parent(node)
        choices = self.__PickChoices(node)
        if parent is None or len(choices) < 2:
            return
        index = choices.index(node.Key) if node.Key in choices else 0
        new_key = choices[(index + step) % len(choices)]
        self.State.Picks[choice_sig(node.Choices)] = new_key
        # 格子的路径签名带着物品键：换了候选签名就变了，菜单跟着新的那一格
        self.MenuTarget = (TARGET_NODE, "{}/{}:{}".format(parent.Sig, node.Slot, new_key))
        self.MenuBrowse = None
        self.Resolve((TARGET_NODE, parent.Sig))

    def ToggleStop(self, node):
        """ 这棵树里不再展开 / 恢复展开（树里同一个物品都跟着）"""
        if node.Key in self.State.Stop:
            self.State.Stop.discard(node.Key)
        else:
            self.State.Stop.add(node.Key)
        self.Resolve((TARGET_NODE, node.Sig))

    def ToggleRaw(self, key):
        """ 当原料（全局）/ 取消：写全局表，每棵树都不再展开它 """
        raw = not self.Prefs.IsRaw(key)
        if not self.Prefs.SetRaw(key, raw) and self.Prefs.IsRaw(key) != raw:
            self.ShowToast(TreeText.PrefsFull)
            return
        self.ShowToast(TreeText.RawSet if raw else TreeText.RawUnset)
        self.Resolve(self.__CanvasTarget())

    def ToggleFold(self, node):
        """ 折叠 / 展开这一格下面的配方：只是不画，汇总照算（随收藏存）"""
        if node.Sig in self.State.Fold:
            self.State.Fold.discard(node.Sig)
        else:
            self.State.Fold.add(node.Sig)
        self.Draw((TARGET_NODE, node.Sig))

    def SetType(self, node, type_id):
        """ 点工作方块换类型：这个物品在这棵树里只在这个类型的配方里挑 """
        if not type_id or type_id == node.Type:
            return
        if not any(not candidate.Stuck for candidate in node.InType(type_id)):
            # 这个类型在这一格只有递归配方：解算器用不了它、会退回别的类型 —— 不记这个选择，说一声（不让菜单与树各说一个类型）
            self.ShowToast(TreeText.TypeUnusable.format(self.Provider.TypeName(type_id).decode("utf-8", "replace")))
            return
        self.State.SetType(node.Key, type_id)
        choice = self.State.Choices.get(node.Key)
        if choice is not None and not any(c.Recipe.Id == choice for c in node.InType(type_id)):
            self.State.Choices.pop(node.Key, None)
        self.Resolve((TARGET_WS, node.Sig))

    def SetStation(self, type_id, key):
        """ 工作方块格显示哪个工作站：只起显示作用，按类型全局记 —— 不重新解算，只重画 """
        if self.Prefs.SetStation(type_id, key):
            self.Draw(self.__CanvasTarget())
        if self.MenuTarget is not None:
            self.RenderMenu()

    def AsRoot(self, key, qty):
        """ 以它为根：换一棵树重算（这棵树里的选择带过去，折叠不带 —— 路径签名对不上了），顶栏「返回」回到原来那棵 """
        if self.State is None or key == self.State.Root:
            return
        self.History.append(self.State.Copy())
        del self.History[:-self.HistoryMax]
        state = TreeState(key, qty)
        state.Choices = dict(self.State.Choices)
        state.Types = dict(self.State.Types)
        state.Picks = dict(self.State.Picks)
        state.Stop = set(self.State.Stop) - {key}
        self.State = state
        self.CloseMenu()
        self.Resolve(reset=True)

    def ToggleBookmark(self, key):
        item = self.__Item(key)
        if item is None:
            return
        had, now = op_toggle_item(item)
        self.ShowToast(TreeText.Unbookmarked if had and not now else
                       (TreeText.Bookmarked if now else TreeText.BookmarkFull))
        self.RenderMenu()

    def ViewRecipes(self, key):
        """ 查看配方页：关掉配方树，回到下面的界面开它的配方页 """
        item = self.__Item(key)
        if item is None:
            return
        self.AfterClose = (item, QueryConst.Output)
        self.RequestClose()

    # 关闭、事件、提示
# ======================================================================================================================
    def OnCloseKey(self, _args=None):
        """ ESC、背包键：菜单开着先关菜单 """
        if self.Menu is not None and self.Menu.Open:
            self.CloseMenu()
        else:
            self.RequestClose()

    def OnCloseButton(self, _args=None):
        self.RequestClose()

    def RequestClose(self):
        """ 只记下：界面下一帧在自己的 Update 里出栈（不在按钮回调里当场拆整个界面）"""
        self.CloseRequested = True

    def OnWheel(self, args):
        from MEIScripts.mei_mod.ui_script.mei_ui.hotkeys.binds import WheelTaken
        if WheelTaken():
            return  # 按着修饰键、正好有滚轮类的快捷键：这一下归快捷键，不滚画布
        if self.Ready and self.Canvas is not None:
            self.Canvas.Scroll(20 if args.get("direction") == 1 else -20)

    def OnPointerRelease(self, _args=None):
        if self.Ready and self.Canvas is not None:
            self.Canvas.ResetDrag()

    def ShowToast(self, text):  # type: (any) -> None
        self.__SetLabel("toast", text, True)
        self.ToastLeft = self.ToastTicks

    def __SetLabel(self, name, text, visible=None):
        control = self.Labels.get(name)
        if control is None:
            return
        if text is not None:
            control.asLabel().SetText(native_str(text))
        if visible is not None:
            control.SetVisible(visible)
