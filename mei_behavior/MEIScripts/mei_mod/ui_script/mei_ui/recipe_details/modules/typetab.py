# coding=utf-8

# ----------------------------------------------------------------------
#  typetab.py is part of MoreEnoughItems.
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
配方类型 tab 的导航算术 —— **零引擎、零控件**，所以探针能全量驱动它。

单独成模块的理由：这套东西真正难的地方不在算术，而在算术之后推控件时的
`SetToggleState` 回灌（见 recipe_ui_api.md §4.8）。把算术摘干净，
剩下的那点控件操作才看得清；也才能在配方类型还不够多的时候先离线验完。

**两份状态必须分开**（这是全模块的关键）：

  · **选中**（`_selected`，全局下标）—— 玩家正在看哪个类型；
  · **视图**（`_page`，第几页）—— tab 条现在显示哪 8 个。

它们**可以不一致**：翻页只换视图不换选择（玩家想找找别的类型，但还没决定切）。
现有代码把两者混在一起（选中态靠 `GetTypeTabIdAux` 撞见 `CurrentType` 时推一次），
所以从来翻不了页。
"""
from MEIScripts.utils.page import BuildPage


class TypeTabNav(object):
    """
    类型 tab 的导航。**只管算，不碰控件。**

    条目是**不透明**的：本类不关心一个「类型」长什么样（现状是
    `(crafting_type, id_aux)` 二元组）。要按业务键定位就在 Reset 时给 `key_of`。
    """

    __slots__ = ("_page", "_selected", "_key_of")

    def __init__(self):
        self._page = None     # type: any  # Page，承载「视图在第几页」
        self._selected = 0    # type: int  # **全局**下标，不是页内下标
        self._key_of = None   # type: any

    # 装载
# ======================================================================================================================
    def SetTypes(self, items, page_size, key_of=None, current_key=None):
        # type: (any, int, any, any) -> None
        """ 重新装载类型表。current_key 命中则选中它，否则选第一个 """
        self._page = BuildPage(list(items or ()), page_size)
        self._key_of = key_of
        self._selected = 0
        if current_key is not None:
            self.SelectByKey(current_key)
        # 开页时 tab 条要能看见选中项 —— 否则玩家看到的是"没有一个是亮的"
        self.__SyncPageToSelection()

    def IsEmpty(self):  # type: () -> bool
        return self._page is None or self._page.length <= 0

    # 选中态
# ======================================================================================================================
    @property
    def Count(self):  # type: () -> int
        return self._page.length if self._page else 0

    @property
    def Index(self):  # type: () -> int
        """ 选中项的**全局**下标 """
        return self._selected

    @property
    def Current(self):  # type: () -> any
        if self.IsEmpty():
            return None
        return self._page.all_items[self._selected]

    @property
    def CurrentKey(self):  # type: () -> any
        return self.KeyOf(self.Current)

    def KeyOf(self, item):  # type: (any) -> any
        if item is None:
            return None
        return self._key_of(item) if self._key_of else item

    def SelectByKey(self, key):  # type: (any) -> bool
        """ 按业务键选中，找不到不动。返回是否命中 """
        if self.IsEmpty():
            return False
        for index, item in enumerate(self._page.all_items):
            if self.KeyOf(item) == key:
                self._selected = index
                return True
        return False

    # 导航
# ======================================================================================================================
    def Step(self, delta):  # type: (int) -> tuple
        """
        逐个切换。返回 `(选中项, 视图是否翻页了)`

        **到头循环**（末尾→开头）。这与既有的 `Page` 一致 ——
        `Page._clamp_index(strict=False)` 本来就是越过末尾回第一页，
        所以配方翻页早就是循环的，两处同一个语义。

        跨页时**自己把视图翻过去**：选中了一个看不见的 tab 是没有意义的。
        """
        if self.IsEmpty():
            return None, False
        # py2 的 % 对负数取正，(0 - 1) % 5 == 4，正好就是要的循环
        self._selected = (self._selected + int(delta)) % self.Count
        changed = self.__SyncPageToSelection()
        return self.Current, changed

    def SelectByPageIndex(self, page_index):  # type: (int) -> any
        """
        按**页内**下标选中（玩家点了 tab 条上第几个）。视图不动

        页内 → 全局的换算只此一处。现有代码在两个回调里各写了一遍
        `current_items[index]`，那是同一个换算的两份实现。
        """
        if self.IsEmpty():
            return None
        items = self._page.current_items
        if page_index < 0 or page_index >= len(items):
            return None
        self._selected = self._page.index + page_index
        return self.Current

    def PageUp(self):  # type: () -> bool
        """ 视图翻到下一页。**不动选中** —— 玩家只是想看看有什么 """
        return self.__Turn(1)

    def PageDown(self):  # type: () -> bool
        return self.__Turn(-1)

    # 视图
# ======================================================================================================================
    @property
    def PageItems(self):  # type: () -> list
        return self._page.current_items if self._page else []

    @property
    def PageNumber(self):  # type: () -> int
        return self._page.current_page_number if self._page else 1

    @property
    def TotalPages(self):  # type: () -> int
        return self._page.total_page if self._page else 1

    @property
    def PageSize(self):  # type: () -> int
        return self._page.page_size if self._page else 1

    def PageIndexOfSelected(self):  # type: () -> int
        """
        选中项在**当前视图**里的下标；不在当前页则 -1

        推 toggle 状态要用它：不在当前页就一个都不该亮。
        """
        if self.IsEmpty():
            return -1
        offset = self._selected - self._page.index
        if offset < 0 or offset >= len(self._page.current_items):
            return -1
        return offset

    # 按钮可用性 —— 判据一律取**全局**数量, 不是页内
# ======================================================================================================================
    def CanStep(self):  # type: () -> bool
        """ 逐个切换可不可用。**看全局总数** —— 它能跨页，页内只有一个不代表不能切 """
        # 现有 UpdateButtons 用的是 len(current_items) <= 1, 那是页内数量。
        # 类型少的时候两者恰好相等, 所以一直没暴露(recipe_ui_api.md §4.8)
        return self.Count > 1

    def CanTurnPage(self):  # type: () -> bool
        return self.TotalPages > 1

    # 内部
# ======================================================================================================================
    def __SyncPageToSelection(self):  # type: () -> bool
        """ 把视图挪到能看见选中项的那一页。返回视图是否真的动了 """
        if self.IsEmpty():
            return False
        want = (self._selected // self._page.page_size) + 1
        if want == self._page.current_page_number:
            return False
        self._page.GoToPage(want)
        return True

    def __Turn(self, delta):  # type: (int) -> bool
        if self.IsEmpty():
            return False
        before = self._page.current_page_number
        if delta > 0:
            self._page.PageUp()
        else:
            self._page.PageDown()
        return self._page.current_page_number != before

    def __repr__(self):
        return "<TypeTabNav {}/{} page {}/{}>".format(
            self._selected, self.Count, self.PageNumber, self.TotalPages)
