# coding=utf-8
from collections import OrderedDict

# ----------------------------------------------------------------------
#  utilities.py is part of MoreEnoughItems.
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

import mod.client.extraClientApi as clientApi
from mod.client.ui.viewBinder import ViewBinder

def GetItemPanelBindingConfigs():
    return  [
        {
            "suffix": ".item.renderer.visible",
            "flag": ViewBinder.BF_BindBool,
            "attr": "ItemRendererVisible",
            "default": False,
            "can_pause": True,
        },
        {
            "suffix": ".item.visible",
            "flag": ViewBinder.BF_BindBool,
            "attr": "ItemControlVisible",
            "default": False,
            "can_pause": True,
        },
        {
            "suffix": ".overlay.visible",
            "flag": ViewBinder.BF_BindBool,
            "attr": "OverlayControlVisible",
            "default": False,
            "can_pause": True,
        },
        {
            "suffix": ".item.label.visible",
            "flag": ViewBinder.BF_BindBool,
            "attr": "LabelVisible",
            "default": False,
            "can_pause": True,
        },
        {
            "suffix": ".item.label.text",
            "flag": ViewBinder.BF_BindString,
            "attr": "LabelText",
            "default": "",
            "can_pause": True,
        },
        {
            "suffix": ".overlay.btn.hover_text",
            "flag": ViewBinder.BF_BindString,
            "attr": "HoverText",
            "default": "",
            "can_pause": True,
        },
        {
            # 悬停探针（挂在 hover 控件 mei_common.highlight_panel 自己身上，always_when_visible）：只有光标下那一格每帧来一次，
            # 不暂停 —— grid 写满暂停绑定后也得知道光标停在了哪一格（docs/architecture/tooltip.md §5）
            "suffix": ".overlay.hover",
            "flag": ViewBinder.BF_BindBool,
            "attr": "HoverProbe",
            "default": False,
            "can_pause": False,
        },
        {
            "suffix": ".item.background.visible",
            "flag": ViewBinder.BF_BindBool,
            "attr": "BackgroundVisible",
            "default": False,
            "can_pause": True,
        }
    ]

def GetScreenSizeInt():  # type: () -> (int, int)
    comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
    return comp.GetScreenSize()

def GetControlPosInt(control):  # type(any) -> tuple
    x, y = control.GetGlobalPosition()
    return int(x), int(y)

def GetControlSizeInt(control):
    size = control.GetSize()
    return int(size[0]), int(size[1])

def GetGridItemPos(index, cols):  # type: (int, int) -> tuple
    index += 1
    y = index // cols if index % cols == 0 else index // cols + 1
    x = index % cols if index % cols else cols
    return x - 1,  y - 1

def GetMousePosInt():  # type: () -> tuple
    comp = clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())
    x, y = comp.GetMousePosition()
    return int(x), int(y)

def GetInputMode():  # type: () -> int
    comp = clientApi.GetEngineCompFactory().CreatePlayerView(clientApi.GetLevelId())
    return comp.GetToggleOption(clientApi.GetMinecraftEnum().OptionId.INPUT_MODE)

def GetControlRectSize(control):  # type: (any) -> tuple
    pos_x, pos_y = control.GetGlobalPosition()
    size_x, size_y = GetControlSizeInt(control)
    return (int(pos_x), int(pos_y)), (size_x + int(pos_x), size_y + int(pos_y))

def SetButtonEnable(control, enable):
    """ 设置按钮是否可用 """
    control.SetTouchEnable(enable)
    disabled_overlay = control.GetChildByPath("/disabled")
    if disabled_overlay:
        disabled_overlay.SetVisible(not enable, False)

def RectContains(outer_rect, inner_rect):
    # type: (tuple, tuple) -> bool
    """ 判断outer_rect是否完整包裹inner_rect """
    return (
        outer_rect[0][0] <= inner_rect[0][0] and
        outer_rect[0][1] <= inner_rect[0][1] and
        outer_rect[1][0] >= inner_rect[1][0] and
        outer_rect[1][1] >= inner_rect[1][1]
    )

def RectOverlap(rect_a, rect_b):
    # type: (tuple, tuple) -> bool
    return not (
        rect_a[1][0] <= rect_b[0][0]
        or rect_b[1][0] <= rect_a[0][0]
        or rect_a[1][1] <= rect_b[0][1]
        or rect_b[1][1] <= rect_a[0][1]
    )

def CalEdge(width, idx1, idx2):
    # type: (int, int, int) -> dict
    """
    计算从索引1到索引2中间所有网格需要显示的边
    """
    # 确保 idx1 <= idx2
    start_idx = min(idx1, idx2)
    end_idx = max(idx1, idx2)

    # 存储结果的字典
    results = {}

    for i in range(start_idx, end_idx + 1):
        # 计算当前网格的行和列
        row = i // width
        col = i % width

        # 计算四个方向上相邻网格的索引
        top_idx = i - width if row > 0 else -1
        bottom_idx = i + width
        left_idx = i - 1 if col > 0 else -1
        right_idx = i + 1 if col < width - 1 else -1

        # 确定当前网格应该显示哪些边
        edges_to_show = []

        # 检查上边
        if top_idx < start_idx or top_idx > end_idx:
            edges_to_show.append(0)

        # 检查下边
        if bottom_idx < start_idx or bottom_idx > end_idx:
            edges_to_show.append(1)

        # 检查左边
        if left_idx < start_idx or left_idx > end_idx:
            edges_to_show.append(2)

        # 检查右边
        if right_idx < start_idx or right_idx > end_idx:
            edges_to_show.append(3)

        # 存储结果
        results[i] = edges_to_show

    return results

def GetVerticalRightLeftItem(index, rows, cols, items, default=None):
    # type: (int, int, int, list, any) -> any
    r = index // cols
    c = index % cols
    new_idx = (cols - 1 - c) * rows + r
    return items[new_idx] if new_idx < len(items) else default

def GetEditBoxRawText(control):  # type: (any) -> str
    """ 输入框里的原文：读显示文字控件的 #item_name，拿到的是网易屏蔽词处理之前的字 """
    display_text_control = control.GetChildByPath("/centering_panel/clipper_panel/display_text")
    return display_text_control.GetPropertyBag().get("#item_name", "")

def IsBindFlag(flag):
    # type: (int) -> bool
    """
    真 = 该 flag 支持集合绑定, 假 = 只支持普通绑定(ScreenBinder.Bind 按它分流).

    注意 SliderFilter 用 getattr 取: **官方枚举里没有这个属性**
    (只有 ButtonFilter / BindFilter / EditFilter / ToggleFilter)。
    原先直接写 ViewBinder.SliderFilter, 靠 `or` 短路侥幸没炸 ——
    按钮类在 ButtonFilter 处就为真、根本走不到它; 但 **BF_ToggleChanged
    会一路求值过去**, 于是第一个走分流的 toggle 使用者(配方动作按钮)
    触发了 AttributeError。
    """
    if flag & ViewBinder.BindFilter:
        return True
    elif (
        (flag & ViewBinder.ButtonFilter)
        or (flag & ViewBinder.EditFilter)
        or (flag & getattr(ViewBinder, "SliderFilter", 0))
        or (flag & ViewBinder.ToggleFilter)
    ):
        return False
    else:
        raise ValueError("invalid flag: {}".format(flag))