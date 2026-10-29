# coding=utf-8

# ----------------------------------------------------------------------
#  layout.py is part of MoreEnoughItems.
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
配方树的布局（纯函数，单位是游戏里的 GUI 像素）。多格节点：根单独一格在最上面；
一格展开 = 它下面挂一组「工作方块 + 原料组」，原料组里的格子就是子节点；折叠 = 只剩那一格（主要产出）。

为什么由 Python 算坐标、不用每行一个 stack_panel（docs/design/recipe_tree.html「布局怎么不打架」）：子树要对齐父格还得自己算、
藏了的子控件在 stack_panel 里多半还占位（引擎结论 §21）、连线要等下一帧读回位置。

算法：对锚点的逐层轮廓打包 ——
1. 一组的子树记成逐层轮廓：从这一组往下第 t 层最左 / 最右（相对这一组的左边）；
2. 子树挨个从左往右放：先想摆在原料格正下方（工作方块中心对着原料格中心），再往右挪到每一层都不压着左边已放好的
   （只比两边都有的层，浅的子树能贴着深的子树放）；
3. 放完把这一群子树整体平移，让「落点 − 锚点」的中位数为 0（父组落到子树群中间，折线总长最短；兄弟之间相对位置不变，不会重叠）；
4. 自上而下按相对位置摆，最左出了界整体右移。坐标都是半格的倍数。
连线：原料格下边 → 子组工作方块上边；正对着是一根竖线，否则「竖 — 横 — 竖」，横段在两层之间的空里（不穿过任何一组），
同一层间隙里的横段按区间分层（区间不相交的共用一层），横段不会叠在一起
"""
from .solver import STATE_OK


class Metrics(object):
    """
    尺寸（GUI 像素）：格子 Cell、工作方块与原料组的间隔 WsGap、兄弟子树的间距 HGap、层与层之间的空 VGap（画折线用）、
    四周留白 Pad、对齐单位 Half、工作方块的框比格子大出 Frame、横段分层的最大间距 Step、线粗 Line
    """
    __slots__ = ("Cell", "WsGap", "HGap", "VGap", "Pad", "Half", "Frame", "Step", "Line")

    def __init__(self, cell=20, ws_gap=5, hgap=10, vgap=24, pad=18, half=5, frame=2, step=4, line=1):
        self.Cell = cell
        self.WsGap = ws_gap
        self.HGap = hgap
        self.VGap = vgap
        self.Pad = pad
        self.Half = half
        self.Frame = frame
        self.Step = step
        self.Line = line

    @property
    def Row(self):  # type: () -> int
        return self.Cell + self.VGap


DEFAULT = Metrics()


class Placement(object):
    """
    Groups：{节点 Id: (x, y)} 展开了的那一格下面那组的左上角（工作方块在这儿，原料 j 在 x + Cell + WsGap + j × Cell）；
    Cells：{节点 Id: (x, y)} 画出来的每一格（根和各组里的原料格）；Lines：[(x, y, 宽, 高)] 连线的矩形；Width / Height：画布大小
    """
    __slots__ = ("Groups", "Cells", "Lines", "Width", "Height")

    def __init__(self):
        self.Groups = {}  # type: dict
        self.Cells = {}  # type: dict
        self.Lines = []  # type: list
        self.Width = 0  # type: int
        self.Height = 0  # type: int


def group_width(node, metrics=DEFAULT):  # type: (any, Metrics) -> int
    return metrics.Cell + metrics.WsGap + len(node.Children) * metrics.Cell


def anchor_of(slot, metrics=DEFAULT):  # type: (int, Metrics) -> int
    """ 原料格 slot 的中心（相对组的左边）"""
    return metrics.Cell + metrics.WsGap + slot * metrics.Cell + metrics.Cell // 2


def place(nodes, fold=(), metrics=DEFAULT):  # type: (list, any, Metrics) -> Placement
    """ nodes 是 solver 的 Nodes（[0] 是根），fold 是折叠了的格子的路径签名 """
    m = metrics
    folded = set(fold)
    result = Placement()

    def has_group(node):
        return node.State == STATE_OK and node.Sig not in folded

    def measure(node):
        parts, rows_l, rows_r = [], [], []
        for slot, child_id in enumerate(node.Children):
            child = nodes[child_id]
            if not has_group(child):
                continue
            sub = measure(child)
            x = anchor_of(slot, m) - m.Cell // 2
            for t in range(min(len(sub[0]), len(rows_r))):
                x = max(x, rows_r[t] + m.HGap - sub[0][t])
            x = -(-x // m.Half) * m.Half
            parts.append([child_id, slot, sub, x])
            for t in range(len(sub[0])):
                if t < len(rows_r):
                    rows_l[t] = min(rows_l[t], x + sub[0][t])
                    rows_r[t] = max(rows_r[t], x + sub[1][t])
                else:
                    rows_l.append(x + sub[0][t])
                    rows_r.append(x + sub[1][t])
        if parts:
            diffs = sorted(part[3] + m.Cell // 2 - anchor_of(part[1], m) for part in parts)
            shift = (diffs[(len(diffs) - 1) // 2] // m.Half) * m.Half
            for part in parts:
                part[3] -= shift
            rows_l = [value - shift for value in rows_l]
            rows_r = [value - shift for value in rows_r]
        return [0] + rows_l, [group_width(node, m)] + rows_r, parts

    root = nodes[0]
    edges = []
    if has_group(root):
        lefts, rights, parts = measure(root)
        min_l, max_r = min(lefts), max(rights)
        root_x = m.Pad - min_l

        def put(node, sub, origin_x, top):
            result.Groups[node.Id] = (origin_x, top)
            for slot, child_id in enumerate(node.Children):
                result.Cells[child_id] = (origin_x + m.Cell + m.WsGap + slot * m.Cell, top)
            for child_id, _, child_sub, x in sub[2]:
                edges.append((child_id, child_id))
                put(nodes[child_id], child_sub, origin_x + x, top + m.Row)

        put(root, (lefts, rights, parts), root_x, m.Pad + m.Row)
        edges.append((0, 0))
        width = max_r - min_l
    else:
        root_x = m.Pad
        width = m.Cell
    result.Cells[0] = (root_x, m.Pad)
    bottom = m.Pad + m.Cell
    for _, top in result.Groups.values():
        bottom = max(bottom, top + m.Cell)
    result.Width = width + m.Pad * 2
    result.Height = bottom + m.Pad
    result.Lines = route(edges, result, m)
    return result


def route(edges, placement, metrics=DEFAULT):  # type: (list, Placement, Metrics) -> list
    """
    连线的矩形：edges 是 [(原料格的节点 Id, 它那组的节点 Id)]（同一个节点：格子在父组里，组在它下面）。
    线从原料组边框的外沿（根格没有边框：格子下边）连到工作方块边框的外沿，不和框叠着 —— 不靠画的先后盖住
    """
    m = metrics
    lines, gaps = [], {}
    for cell_id, group_id in edges:
        cell_x, cell_y = placement.Cells[cell_id]
        group_x, group_y = placement.Groups[group_id]
        cx, cy = cell_x + m.Cell // 2, cell_y + m.Cell + (m.Frame if cell_id else 0)
        lx, gy = group_x + m.Cell // 2, group_y - m.Frame
        if cx == lx:
            lines.append((cx, cy, m.Line, gy - cy))
            continue
        gaps.setdefault(group_y, []).append([min(cx, lx), max(cx, lx), cx, cy, lx, gy, 0])
    for group_y in sorted(gaps):
        segs = sorted(gaps[group_y], key=lambda seg: (seg[0], seg[1]))
        ends = []
        for seg in segs:
            level = 0
            while level < len(ends) and ends[level] > seg[0] - 4:
                level += 1
            if level == len(ends):
                ends.append(seg[1])
            else:
                ends[level] = seg[1]
            seg[6] = level
        span = segs[0][5] - segs[0][3]
        step = max(1, min(m.Step, (span - 6) // max(1, len(ends))))
        for lo, hi, cx, cy, lx, gy, level in segs:
            y = cy + span // 2 + int(round((level - (len(ends) - 1) / 2.0) * step))
            lines.append((cx, cy, m.Line, y - cy))
            lines.append((lo, y, hi - lo + m.Line, m.Line))
            lines.append((lx, y, m.Line, gy - y))
    return lines
