# coding=utf-8

# ----------------------------------------------------------------------
#  polygon.py is part of MoreEnoughItems.
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


class RectPolygon(object):
    """
    由多个不重叠矩形组成的“多边形集合”对象
    这里针对 UI 遮挡场景 矩形均为轴对齐矩形
    """

    def __init__(self, screen_size=None, cell_size=64):
        self.ScreenSize = screen_size  # type: tuple or None
        self.CellSize = max(1, int(cell_size))  # type: int

        self._rects = {}  # type: dict
        self._next_id = 1  # type: int
        self._cell_index = {}  # type: dict

    # -----------------------------
    # 基础工具
    # -----------------------------
    @staticmethod
    def _normalize_rect(rect):
        """统一矩形结构为 (x1, y1, x2, y2)，并保证 x1<x2, y1<y2。"""
        if rect is None:
            return None

        if len(rect) == 2 and len(rect[0]) == 2 and len(rect[1]) == 2:
            x1, y1 = rect[0]
            x2, y2 = rect[1]
        elif len(rect) == 4:
            x1, y1, x2, y2 = rect
        else:
            raise ValueError("rect must be ((x1,y1),(x2,y2)) or (x1,y1,x2,y2)")

        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        if x1 == x2 or y1 == y2:
            return None

        return x1, y1, x2, y2

    @staticmethod
    def _intersection(rect_a, rect_b):
        x1 = max(rect_a[0], rect_b[0])
        y1 = max(rect_a[1], rect_b[1])
        x2 = min(rect_a[2], rect_b[2])
        y2 = min(rect_a[3], rect_b[3])
        if x1 >= x2 or y1 >= y2:
            return None
        return x1, y1, x2, y2

    @staticmethod
    def _area(rect):
        return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])

    @staticmethod
    def _subtract_one(source_rect, cut_rect):
        """ 返回 source_rect 减去 cut_rect 后的碎片(最多 4 块) """
        inter = RectPolygon._intersection(source_rect, cut_rect)
        if not inter:
            return [source_rect]

        sx1, sy1, sx2, sy2 = source_rect
        ix1, iy1, ix2, iy2 = inter

        result = []

        # 上
        if sy1 < iy1:
            result.append((sx1, sy1, sx2, iy1))
        # 下
        if iy2 < sy2:
            result.append((sx1, iy2, sx2, sy2))
        # 左（中段）
        if sx1 < ix1:
            result.append((sx1, iy1, ix1, iy2))
        # 右（中段）
        if ix2 < sx2:
            result.append((ix2, iy1, sx2, iy2))

        return result

    def _rebuild_index(self):
        self._cell_index = {}
        for rect_id, rect in self._rects.items():
            for cell in self._iter_cells_for_rect(rect):
                ids = self._cell_index.get(cell)
                if ids is None:
                    ids = set()
                    self._cell_index[cell] = ids
                ids.add(rect_id)

    def _iter_cells_for_rect(self, rect):
        size = self.CellSize
        start_cx = rect[0] // size
        end_cx = (rect[2] - 1) // size
        start_cy = rect[1] // size
        end_cy = (rect[3] - 1) // size

        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                yield cx, cy

    def _query_candidate_ids(self, rect):
        ids = set()
        for cell in self._iter_cells_for_rect(rect):
            local_ids = self._cell_index.get(cell)
            if not isinstance(local_ids, set):
                continue
            for rect_id in local_ids:
                ids.add(rect_id)
        return ids

    def _next_rect_id(self):
        rect_id = self._next_id
        self._next_id += 1
        return rect_id

    def SetScreenSize(self, screen_size):
        self.ScreenSize = screen_size

    def GetRects(self):
        return list(self._rects.values())

    def GetVertices(self):
        """ 返回当前所有矩形顶点坐标 """
        vertices = []
        for x1, y1, x2, y2 in self._rects.values():
            vertices.append(((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
        return vertices

    def GetIntersections(self, rect):
        """ 返回与 rect 相交的所有交叠矩形片段 """
        rect = self._normalize_rect(rect)
        if rect is None:
            return []

        intersections = []
        candidate_ids = self._query_candidate_ids(rect)
        for rect_id in candidate_ids:
            inter = self._intersection(rect, self._rects[rect_id])
            if inter:
                intersections.append(inter)
        return intersections

    def Clear(self):
        self._rects = {}
        self._cell_index = {}
        self._next_id = 1

    def MergeRect(self, rect):
        """
        矩形合并: 将 rect 并入当前区域
        为保持不重叠存储, 会先剔除已覆盖部分再写入
        """
        rect = self._normalize_rect(rect)
        if rect is None:
            return False

        pending = [rect]
        for existing in self._rects.values():
            if not pending:
                break

            next_pending = []
            for piece in pending:
                next_pending.extend(self._subtract_one(piece, existing))
            pending = next_pending

        if not pending:
            return False

        for piece in pending:
            self._rects[self._next_rect_id()] = piece

        self._rebuild_index()
        return True

    def SubtractRect(self, rect):
        """矩形删减：从当前区域中删除与 rect 重合部分。"""
        rect = self._normalize_rect(rect)
        if rect is None:
            return False

        if not self._rects:
            return False

        new_rects = []
        changed = False

        for existing in self._rects.values():
            pieces = self._subtract_one(existing, rect)
            if len(pieces) != 1 or pieces[0] != existing:
                changed = True
            new_rects.extend(pieces)

        if not changed:
            return False

        self._rects = {}
        for piece in new_rects:
            self._rects[self._next_rect_id()] = piece

        self._rebuild_index()
        return True

    def DetectOcclusion(self, rect, return_uncovered=False):
        """
        矩形遮挡检测。

        返回结构:
        {
            "occluded": bool,
            "fully_occluded": bool,
            "overlaps": [rect...],
            "uncovered": [rect...]  # 仅 return_uncovered=True 时返回
        }
        """
        rect = self._normalize_rect(rect)
        if rect is None:
            return {
                "occluded": False,
                "fully_occluded": False,
                "overlaps": [],
                "uncovered": [rect] if return_uncovered else [],
            }

        overlaps = self.GetIntersections(rect)

        if not overlaps:
            return {
                "occluded": False,
                "fully_occluded": False,
                "overlaps": [],
                "uncovered": [rect] if return_uncovered else [],
            }

        # 判断是否完全遮挡：用 overlap 对查询矩形做减法后是否为空
        fragments = [rect]
        for overlap in overlaps:
            next_fragments = []
            for piece in fragments:
                next_fragments.extend(self._subtract_one(piece, overlap))
            fragments = next_fragments
            if not fragments:
                break

        fully_occluded = len(fragments) == 0

        return {
            "occluded": True,
            "fully_occluded": fully_occluded,
            "overlaps": overlaps,
            "uncovered": fragments if return_uncovered else [],
        }


