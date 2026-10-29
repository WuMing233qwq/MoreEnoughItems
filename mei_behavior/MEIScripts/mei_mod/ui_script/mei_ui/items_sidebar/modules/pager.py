# coding=utf-8

# ----------------------------------------------------------------------
#  pager.py is part of MoreEnoughItems.
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


class BookmarkPager(object):
    """
    收藏栏的分页器：页已经由 build_pages 排好，这里只记停在第几页；接口对齐 BaseItemsGridScript 会碰的那几样
    """
    def __init__(self):
        self.Cols = 0
        self.Rows = 0
        self.Pages = [{}]  # type: list
        self.Index = 0

    def SetPages(self, pages, index):  # type: (list, int) -> None
        self.Pages = pages or [{}]
        self.Index = max(0, min(index, len(self.Pages) - 1))

    def Current(self):  # type: () -> dict
        return self.Pages[self.Index]

    def UpdatePage(self):
        """ 排版在 BuildSlots 里做，这里无事可做 """

    def SetViewCapacity(self, capacity):
        """ 同上：容量由排版时的遮挡格决定 """

    def PageUp(self):
        """ 下一页，到底回到第一页（与 utils/page.Page 同向）"""
        self.Index = (self.Index + 1) % len(self.Pages)

    def PageDown(self):
        self.Index = (self.Index - 1) % len(self.Pages)

    @property
    def current_page_number(self):  # type: () -> int
        return self.Index + 1

    @property
    def total_page(self):  # type: () -> int
        return len(self.Pages)
