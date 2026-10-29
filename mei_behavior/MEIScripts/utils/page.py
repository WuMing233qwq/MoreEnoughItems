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

class Page(object):

    def __init__(self, items, page_size):
        self.items = items  # type: list
        self.index = 0  # type: int
        self.page_size = max(1, int(page_size))  # type: int

    @property
    def all_items(self):
        return self.items

    @property
    def length(self):
        return len(self.items)

    @property
    def current_items(self):  # type: (Page) -> list
        end_index = min(self.index + self.page_size, self.length)
        return self.items[self.index:end_index]

    @property
    def current_page_number(self):
        if self.page_size <= 0:
            return 1
        return (self.index // self.page_size) + 1

    @property
    def total_page(self):
        if self.page_size <= 0:
            return 1
        return max(1, (self.length + self.page_size - 1) // self.page_size)

    def update_page(self):  # type: () -> None
        self._clamp_index(strict=True)

    def set_page_size(self, page_size):  # type: (int) -> None
        self.page_size = max(1, int(page_size))
        self._clamp_index(strict=True)

    def _clamp_index(self, strict=False):  # type: (bool) -> None
        if self.length <= 0:
            self.index = 0
            return

        if strict:
            self.index = max(0, min(self.index, self.length - 1))
            return

        if self.index >= self.length:
            self.index = 0
        elif self.index < 0:
            step = max(1, self.page_size)
            self.index = max(0, ((self.length - 1) // step) * step)

    def PageUp(self):  # type: (Page) -> list
        self.index += self.page_size
        self._clamp_index(strict=False)
        return self.current_items

    def GoToPage(self, page_num):  # type: (int) -> list
        page_num = max(1, int(page_num))
        self.index = self.page_size * (page_num - 1)
        self._clamp_index(strict=True)
        return self.current_items

    def PageDown(self):  # type: (Page) -> list
        self.index -= self.page_size
        self._clamp_index(strict=False)
        return self.current_items

    def UpdatePage(self):  # type: () -> None
        self.update_page()


def BuildPage(items, num):  # type: (list, int) -> Page
    return Page(items, num)