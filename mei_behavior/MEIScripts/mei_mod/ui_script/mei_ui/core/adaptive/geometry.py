# coding=utf-8

# ----------------------------------------------------------------------
#  geometry.py is part of MoreEnoughItems.
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

import time

from MEIScripts.utils.polygon import RectPolygon
from MEIScripts.utils import utilities


class AdaptiveGeometryCache(object):
    """ 维护自适应控件的可见矩形快照，降低重复 ModSDK 调用频率 """

    def __init__(self, adaptive_registry, refresh_interval=0.12):
        self._AdaptiveRegistry = adaptive_registry
        self._RefreshInterval = max(0.0, float(refresh_interval))

        self._VisibleControls = []
        self._VisibleRects = []
        self._OcclusionPolygon = RectPolygon()
        # 悬浮窗管事时照样避让的那几块（登记时 always=True，配方页）：单独一份矩形与多边形
        self._AlwaysFlags = []
        self._AlwaysRects = []
        self._AlwaysPolygon = RectPolygon()

        self._Dirty = True
        self._Version = 0
        self._RegistryVersion = -1
        self._LastRefreshTs = 0.0

    def SetRefreshInterval(self, refresh_interval):
        self._RefreshInterval = max(0.0, float(refresh_interval))

    def MarkDirty(self):
        self._Dirty = True

    def GetVersion(self):
        return self._Version

    def Refresh(self, screen_node, root_getter, force=False):
        now = time.time()
        registry_version = self._AdaptiveRegistry.GetVersion()

        should_refresh = force or self._Dirty or (registry_version != self._RegistryVersion)
        if not should_refresh and self._RefreshInterval > 0.0:
            should_refresh = (now - self._LastRefreshTs) >= self._RefreshInterval

        if not should_refresh:
            return False

        tagged = self._AdaptiveRegistry.ResolveControlsTagged(
            screen_node=screen_node,
            root_getter=root_getter
        )

        controls, rects, flags = [], [], []
        for control, always in tagged:
            try:
                rect = utilities.GetControlRectSize(control)
            except Exception:  # noqa
                continue
            controls.append(control)
            rects.append(rect)
            flags.append(always)

        prev_controls_signature = tuple([id(control) for control in self._VisibleControls])
        prev_rects_signature = tuple(self._VisibleRects)
        next_controls_signature = tuple([id(control) for control in controls])
        next_rects_signature = tuple(rects)
        changed = (prev_controls_signature != next_controls_signature) or (prev_rects_signature != next_rects_signature) \
            or (tuple(self._AlwaysFlags) != tuple(flags))

        self._VisibleControls = controls
        self._VisibleRects = rects
        self._AlwaysFlags = flags
        if changed:
            self._OcclusionPolygon.Clear()
            self._AlwaysPolygon.Clear()
            self._AlwaysRects = []
            for rect, always in zip(rects, flags):
                self._OcclusionPolygon.MergeRect(rect)
                if always:
                    self._AlwaysRects.append(rect)
                    self._AlwaysPolygon.MergeRect(rect)

        self._RegistryVersion = registry_version
        self._LastRefreshTs = now
        self._Dirty = False

        if changed:
            self._Version += 1
            return True

        return False

    def GetVisibleControls(self):
        return list(self._VisibleControls)

    def GetVisibleRects(self, always_only=False):
        """ always_only：只要悬浮窗管事时照样避让的那几块 """
        return list(self._AlwaysRects if always_only else self._VisibleRects)

    def GetOcclusionPolygon(self, always_only=False):
        return self._AlwaysPolygon if always_only else self._OcclusionPolygon

    def DetectOccludedSlots(self, grid_x, grid_y, cols, rows, item_size, always_only=False):
        """ 基于多边矩形与 Grid 交叠区间的遮挡检测；always_only 只看悬浮窗管事时照样避让的那几块 """
        result = set()

        if cols <= 0 or rows <= 0 or item_size <= 0:
            return result

        grid_x2 = grid_x + cols * item_size
        grid_y2 = grid_y + rows * item_size
        polygon = self._AlwaysPolygon if always_only else self._OcclusionPolygon
        intersections = polygon.GetIntersections((grid_x, grid_y, grid_x2, grid_y2))
        if not intersections:
            return result

        max_col = cols - 1
        max_row = rows - 1

        for inter in intersections:
            ix1, iy1, ix2, iy2 = inter

            start_col = int((ix1 - grid_x) // item_size)
            end_col = int(((ix2 - 1) - grid_x) // item_size)
            start_row = int((iy1 - grid_y) // item_size)
            end_row = int(((iy2 - 1) - grid_y) // item_size)

            if end_col < 0 or end_row < 0 or start_col > max_col or start_row > max_row:
                continue

            if start_col < 0:
                start_col = 0
            if start_row < 0:
                start_row = 0
            if end_col > max_col:
                end_col = max_col
            if end_row > max_row:
                end_row = max_row

            for row in range(start_row, end_row + 1):
                base = row * cols
                for col in range(start_col, end_col + 1):
                    result.add(base + col)

        return result

