# coding=utf-8

# ----------------------------------------------------------------------
#  hosted.py is part of MoreEnoughItems.
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
托管配方页的一页（HostedPage）：MEI 交给托管者（RecipePageHost，common/classes/types/page_host.py）的东西。

托管者拿它在容器里建控件、删控件（经主节点建，主节点的控件缓存跟着作废）、在顶栏挂一句话、关掉配方页；
Live 为假以后（这一页被收回了）这几个方法什么都不做。

一次建很多控件的：CreateControl 给 update=False（不当场刷新界面），建完调一次 UpdateScreen —— 缺省每建一个就把整个界面重排一遍
（开着 MEI 的工作台两万多个控件），一页几十个控件就是一秒（引擎结论 §57）
"""
from mod_log import logger

from MEIScripts.utils.text import error_text


class HostedPage(object):

    __slots__ = ("Host", "Category", "Recipes", "Start", "Total", "Height", "Container", "ContainerPath",
                 "Serial", "ScreenNode", "ScreenName", "Live", "Born", "_Owner")

    def __init__(self, owner, host, category, recipes, start, total, height, container, serial):
        self._Owner = owner  # type: any  # RecipeDetailsScript
        self.Host = host  # type: any
        self.Category = category  # type: any  # RecipeCategory
        self.Recipes = list(recipes or ())  # type: list  # 这一页的配方（MEI 的 Recipe）
        self.Start = int(start or 0)  # type: int  # 这一页第一条是这个类型的第几条（从 0 起）
        self.Total = int(total or 0)  # type: int  # 这个类型一共几条
        self.Height = int(height or 0)  # type: int  # 内容区能用的高
        self.Container = container  # type: any  # MEI 建的容器（CONTAINER 那个定义）
        self.ContainerPath = container.GetPath() if container else ""  # type: str
        self.Serial = serial  # type: int  # 容器的代号：同一个类型翻页时不变，换了类型、刷新、重开配方页就换（旧容器连同里面的控件已经删了）
        self.ScreenNode = getattr(owner, "ScreenNode", None)
        self.ScreenName = _screen_name(owner)  # type: str  # 配方页挂在哪个界面上（界面定义名，比如 "crafting.crafting_screen"）
        self.Live = True  # type: bool  # 收回以后为假
        self.Born = 0  # type: int  # 显示这一刻配方页的节拍数（Tick 的 ticks 从它算起）

    def CreateControl(self, control_def, name, parent=None, update=True):  # type: (str, str, any, bool) -> any
        """
        在容器（或给的父控件）下面建一个控件；建不出来给 None。update 为假不当场刷新界面（一批建完调一次 UpdateScreen）；
        刚建的控件不管刷没刷新，当场都可能取不到子控件（GetChildByPath 给 None），下一帧再取
        """
        if not self.Live:
            return None
        parent = parent or self.Container
        main = getattr(self._Owner, "MainNode", None)
        if not parent or main is None:
            return None
        try:
            return main.CreateChildControl(control_def, name, parent, bool(update))
        except Exception as e:  # noqa
            logger.error("[MEI/ui] 托管配方页建不出控件 {}: {}".format(control_def, error_text(e)))
            return None

    def UpdateScreen(self):  # type: () -> None
        """ 刷新一次界面（CreateControl(update=False)、SetVisible(…, False) 这类没当场刷新的改动一起生效）"""
        screen = self.ScreenNode
        if not self.Live or screen is None:
            return
        try:
            screen.UpdateScreen(True)
        except Exception as e:  # noqa
            logger.warn("[MEI/ui] 托管配方页刷新界面失败: {}".format(error_text(e)))

    def RemoveControl(self, control):  # type: (any) -> bool
        """ 删一个建过的控件 """
        main = getattr(self._Owner, "MainNode", None)
        if not control or main is None:
            return False
        try:
            main.RemoveChildControl(control)
        except Exception:  # noqa  已经跟着容器没了
            return False
        return True

    def PlusState(self, recipe):  # type: (any) -> tuple
        """
        这一条配方的 +（配方转移）现在什么样子：(能不能点, 悬停字) —— 和 MEI 配方行的 + 一样：这一类转移不了、当前界面不收、材料不够的灰着，
        悬停写为什么；能点的写点了会怎样。结论走配方页的缓存（开页时采的背包），每帧问也不贵
        """
        getter = getattr(self._Owner, "PlusState", None)
        if not self.Live or not callable(getter):
            return False, u""
        return getter(recipe)

    def Transfer(self, recipe):  # type: (any) -> None
        """
        点了这一条配方的 +：和 MEI 配方行的 + 一样（交给当前界面登记的转移处理器，或照类型的转移策略往合成格里搬；成了关掉配方页，
        没成在顶栏挂原因）。灰着的什么都不做。从按钮回调里调就行（关页 MEI 自己排到下一拍）
        """
        transfer = getattr(self._Owner, "TransferRecipe", None)
        if self.Live and callable(transfer):
            transfer(recipe)

    def Notice(self, text):  # type: (any) -> None
        """ 顶栏的类型名换成一句话挂几秒（比如点了转移没成的原因）"""
        if self.Live:
            self._Owner.ShowNotice(text)

    def Close(self):  # type: () -> None
        """ 关掉配方页（排到下一拍，不在按钮回调里当场拆控件）"""
        if not self.Live:
            return
        owner = self._Owner
        owner.GameComp.AddTimer(0.0, owner.Close)


def _screen_name(owner):  # type: (any) -> str
    main = getattr(owner, "MainNode", None)
    if main is None:
        return ""
    try:
        return main.GetScreenDef() or ""
    except Exception:  # noqa
        return ""
