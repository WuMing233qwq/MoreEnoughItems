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
菜单的纯计算：框里每样东西摆在哪、多大。不碰引擎。两种排版：

**信息卡 + 图标操作条**（card_layout，触屏菜单用，tooltip.md §6.14）：

  顶栏    [物品图标] 种类（灰字，收藏格带数量）……………… x
  内容    标题（悬停文字）/ 配方预览 / 接受物品列表 —— 和 PC 的 tooltip 一模一样
  ────    分隔线
  翻页行  ‹        2 / 86        ›          只有多候选格有
  操作条  [图标/字][图标/字]…               等宽的大按钮，一排最多 BAR_LIMIT 个（含「更多」）
  ────    「更多」展开时才有：分隔线 + 两列文字按钮

框宽至少 CARD_MIN_INNER（物品菜单、收藏菜单一样宽），内容、操作条、「更多」里的字放不下才变宽；
「更多」展开、收起时宽度不变（按它的字算过了），只是变高。

**按段排的一个框**（box_layout，配方树的节点菜单在用，tooltip.md §6.12）：

  顶栏    种类（灰字）……………………… x（大小、偏移在 JSON 里调，见 CLOSE_SIZE / CLOSE_OFFSET）
  内容    标题（悬停文字）/ 配方预览 / 接受物品列表
  ────    分隔线
  按钮区  一段一行：左边一列段名（灰字），右边按钮；数量、候选做成步进器：[-1]  ×2  [+1]、 ‹  2 / 86  ›

按钮的宽按字算（字宽估算 + 两边留白），框宽取「内容、顶栏、最宽的那一段」里宽的那个，别的段再拉满到这个宽。

两种都全部绝对定位、不靠 stack_panel 收拢：藏起来的子控件收不收拢还没实证（tooltip.md §6.4），
脚本改过尺寸的控件、外面的 stack_panel 也不一定跟着重排（表现是贴边时按钮区没算进去）
"""

BUTTON_H = 14
""" 按钮高 """

BUTTON_SIZE = (40, BUTTON_H)
""" mei_common.menu_button 的 $menu_button_size 缺省值（探针对账）；池里的按钮显示时由脚本按字改宽 """

GAP = 2
""" 按钮之间、行与行之间的空隙 """

PAD = 4
""" 框四周留白：和 tooltip 内容四周自带的 4 像素一样，内容里的字和段名、种类落在同一条竖线上 """

COLUMNS = 3
""" 一行最多几个按钮，多了换行 """

CJK_W = 9
""" 估算字宽：一个汉字（含全角标点）多宽。按钮的宽靠它算，字宽对不上时改这里 """

ASCII_W = 6
""" 估算字宽：一个半角字符（数字、字母、+ - × / 空格）多宽 """

BUTTON_PAD = 4
""" 按钮里字的两边各留多少 —— 也给字宽估算留了余量 """

MIN_BUTTON_W = 20
""" 文字按钮最窄多宽（「-1」「+1」）"""

ICON_SIZE = (14, 14)
"""
按钮区里的图标按钮（候选的左右箭头）多大。**以 JSON 为准**：触屏菜单读 mei_common.json 里 flat_icon_button 的
$flat_icon_size|default，配方树的菜单与汇总的翻页读 menu_icon_button 的 $menu_icon_size|default（要调只改 JSON），
排版时读回来；这里只是读不到时的缺省（探针对账两边一致）
"""

LABEL_W = 2 * CJK_W
""" 段名那一列（段名都是两个字）"""

NUMBER_MIN_W = 16
""" 步进器中间的数字最窄多宽；数字本身按字算，再加 BUTTON_PAD 的余量 """

CLOSE_SIZE = (14, 14)
"""
顶栏的小 x 多大。**以 JSON 为准**：触屏菜单是 tooltip_root 里 close 的 $flat_icon_size（配方树的是 $menu_icon_size），
菜单开的时候读回来；这里只是读不到时的缺省（探针对账两边一致）
"""

CLOSE_OFFSET = (0, -2)
"""
小 x 相对它那个插槽（顶栏右上角）的偏移，负数往上 / 往左。**以 JSON 为准**：close 的 offset，
菜单开的时候读回来；这里只是读不到时的缺省
"""

MIN_INNER_W = 60
""" 框里最窄多宽（内容、按钮都很短时也别缩成一条）"""

LINE_GAP = 3
""" 分隔线上下各空几格 """

TEXT_DY = 3
""" 段名、数字摆在按钮那一行里往下挪多少（字高 8~9，行高 14）"""

TEXT_H = 10
""" 数字标签的高（宽由脚本按格子算，字居中）"""


def text_width(text):  # type: (any) -> int
    """ 估算一段字有多宽：汉字 CJK_W、半角 ASCII_W，§ 颜色码不占宽 """
    if not text:
        return 0
    if not isinstance(text, unicode):  # noqa: F821  py2 的 unicode
        text = text.decode("utf-8", "replace")
    width, skip = 0, False
    for char in text:
        if skip:
            skip = False
            continue
        if char == u"§":
            skip = True
            continue
        width += CJK_W if ord(char) >= 0x2e80 else ASCII_W
    return width


def button_width(labels):  # type: (list) -> int
    """ 文字按钮放得下这几种字（开着菜单时会变的字都给上，比如二次确认）要多宽 """
    return max([MIN_BUTTON_W] + [text_width(label) + 2 * BUTTON_PAD for label in labels if label])


def number_width(text):  # type: (any) -> int
    """ 步进器中间的数字至少要多宽 """
    return max(NUMBER_MIN_W, text_width(text) + BUTTON_PAD)


def _lines(items):
    """
    一段的按钮怎么分行：一行最多 COLUMNS 个，多了换行，**每行尽量一样多**（四个按钮排 2×2，不是 3 + 1；五个是 3 + 2）
    """
    if not items:
        return [[]]
    count = -(-len(items) // COLUMNS)
    per = -(-len(items) // count)
    return [items[index:index + per] for index in range(0, len(items), per)]


def row_width(items, stepper=False, number=0):  # type: (list, bool, int) -> int
    """ 一段按自然宽排要多宽（items 是每个按钮的 (宽, 高, 定宽)）；超过 COLUMNS 个的换行，取最宽的那一行 """
    if stepper and len(items) == 2:
        return items[0][0] + GAP + number + GAP + items[1][0]
    return max(sum(item[0] for item in line) + GAP * max(0, len(line) - 1) for line in _lines(items))


def stretch(items, avail):  # type: (list, int) -> list
    """
    一行按钮拉满 avail：多出来的平均分给能拉的按钮（除不尽的给后面的）；只有一个按钮时最多拉到半行；定宽的（图标）不拉
    """
    widths = [item[0] for item in items]
    flexible = [index for index, item in enumerate(items) if not item[2]]
    if not flexible:
        return widths
    if len(items) == 1:
        return [max(widths[0], (avail - GAP) // 2)]
    extra = max(0, avail - sum(widths) - GAP * (len(items) - 1))
    count = len(flexible)
    for order, index in enumerate(flexible):
        widths[index] += extra // count + (1 if order >= count - extra % count else 0)
    return widths


def rows_layout(rows, width, labels=True, label_w=None):  # type: (list, int, bool, int) -> tuple
    """
    按段排按钮。rows 是每段的 (items, 是不是步进器, 数字至少多宽)：items 是这一段每个按钮的 (宽, 高, 定宽) ——
    文字按钮是按字算出的自然宽、高 BUTTON_H、能拉；图标按钮是它的尺寸、定宽。width 是按钮区的宽（不比每段的自然宽窄）；
    labels 为真时左边留一列写段名。返回 (buttons, names, numbers, height)，坐标都相对按钮区的左上角：
      buttons  每个按钮的 (x, y, 宽, 高)，按段、段内按顺序（矮的按钮在行里竖直居中）；
      names    每段段名的 (x, y)，labels 为假时都是 None；
      numbers  每段步进器数字的 (x, y, 宽)，不是步进器的是 None；
      height   按钮区的高（没有段是 0）
    步进器只认两个按钮的段：两头的按钮贴着两边，数字占中间剩下的地方
    """
    left = ((LABEL_W if label_w is None else label_w) + GAP) if labels else 0
    avail = max(0, width - left)
    buttons, names, numbers = [], [], []
    y = 0
    for items, stepper, number in rows:
        names.append((0, y + TEXT_DY) if labels else None)
        if stepper and len(items) == 2:
            (w0, h0, _), (w1, h1, _) = items
            buttons.append((left, y + (BUTTON_H - h0) // 2, w0, h0))
            buttons.append((left + avail - w1, y + (BUTTON_H - h1) // 2, w1, h1))
            numbers.append((left + w0 + GAP, y + TEXT_DY, max(number, avail - w0 - w1 - 2 * GAP)))
            y += BUTTON_H + GAP
            continue
        numbers.append(None)
        for line in _lines(items):
            x = left
            for item, w in zip(line, stretch(line, avail)):
                buttons.append((x, y + (BUTTON_H - item[1]) // 2, w, item[1]))
                x += w + GAP
            y += BUTTON_H + GAP
    return buttons, names, numbers, (y - GAP if rows else 0)


def head_height(close_size=CLOSE_SIZE, close_offset=CLOSE_OFFSET):  # type: (tuple, tuple) -> int
    """ 顶栏多高：放得下一行字，也放得下小 x（往上偏的那几像素伸进框的留白里，不算）"""
    return max(TEXT_H, int(close_size[1]) + min(0, int(close_offset[1])))


def box_layout(content_size, rows, labels=True, kind_width=0, close_size=CLOSE_SIZE, close_offset=CLOSE_OFFSET,
               label_w=None):
    # type: (tuple, list, bool, int, tuple, tuple) -> dict
    """
    整个菜单（一个框）里每样东西摆在哪。content_size 是内容控件的尺寸（含它四周自带的 4 像素）；rows、labels 同 rows_layout；
    kind_width 是顶栏种类那几个字的宽；close_size / close_offset 是小 x 的尺寸与偏移（JSON 里读回来的）。
    返回 dict，坐标相对框的左上角（框本身摆到屏幕上归 tooltip 管理器）：
      size     框的 (宽, 高)
      kind     种类标签的 (x, y)
      close    小 x 插槽的 (x, y, 宽, 高)：右上角；小 x 在插槽里再按自己的 offset 偏
      content  内容控件的 (x, y)：它自带 4 像素，所以摆在 x = 0，字正好落在 PAD 那条竖线上
      divider  分隔线的 (x, y, 宽)；没有按钮时是 None
      actions  按钮区的 (x, y, 宽, 高)
      buttons / names / numbers  同 rows_layout，坐标相对按钮区
    宽取内容、顶栏、最宽的那一段里宽的那个（最窄 MIN_INNER_W），别的段拉满到这个宽
    """
    content_w, content_h = int(round(content_size[0])), int(round(content_size[1]))
    left = ((LABEL_W if label_w is None else label_w) + GAP) if labels else 0
    widest = max([0] + [left + row_width(items, stepper, number) for items, stepper, number in rows])
    close_w, close_h = int(close_size[0]), int(close_size[1])
    head_h = head_height(close_size, close_offset)
    head = kind_width + 2 * GAP + close_w
    inner = max(content_w - 2 * PAD, widest, head, MIN_INNER_W)
    width = inner + 2 * PAD
    content_y = head_h + GAP  # 即 PAD + 顶栏高 + GAP - PAD：内容自带的 4 像素抵掉框的 PAD，字落在顶栏下面隔 GAP 的地方
    bottom = content_y + max(0, content_h - PAD)  # 内容最后一行字的底
    buttons, names, numbers, rows_h = rows_layout(rows, inner, labels, label_w)
    if rows:
        line_y = bottom + LINE_GAP
        divider = (PAD, line_y, inner)
        actions_y = line_y + 1 + LINE_GAP
    else:
        divider = None
        actions_y = bottom
    return {
        "size": (width, actions_y + rows_h + PAD),
        "kind": (PAD, PAD + (head_h - TEXT_H) // 2),
        "close": (width - PAD - close_w, PAD, close_w, close_h),
        "content": (0, content_y),
        "divider": divider,
        "actions": (PAD, actions_y, inner, rows_h),
        "buttons": buttons,
        "names": names,
        "numbers": numbers,
    }


# 信息卡 + 图标操作条（触屏菜单）
# ======================================================================================================================
CARD_MIN_INNER = 142
""" 卡片里最窄多宽（框 150）：物品菜单、收藏菜单一样宽，正好放下 134 宽的配方预览 """

HEAD_ICON = 18
""" 顶栏左边物品图标的格子多大（JSON 里 touch/frame/icon 的尺寸，渲染器 16 居中）"""

HEAD_ICON_GAP = 4
""" 物品图标与种类之间空多少 """

CARD_CLOSE_OFFSET = (0, 0)
""" 卡片顶栏小 x 的偏移缺省（以 JSON 为准，菜单打开时读回来）；它的插槽在顶栏里竖直居中 """

BAR_H = 26
""" 操作条按钮的高：图标 15 在上、一行字在下 """

BAR_MIN_W = 22
""" 操作条按钮最窄多宽（两个汉字 + 两边各 BAR_PAD）"""

BAR_MAX_W = 48
""" 操作条按钮最宽多宽：按钮少（一两个）时不拉成长条，整排居中 """

BAR_PAD = 2
""" 操作条按钮里字的两边各留多少 """

BAR_LIMIT = 6
""" 操作条一排最多几个按钮（含「更多」）：150 宽的卡片里每个 22 宽 """

MORE_COLUMNS = 2
""" 「更多」里的文字按钮排几列 """

DIVIDER_H = 2
""" 分隔线控件的高：扁平贴图 flat/divider 是 1×2（上面一行是线、下面一行透明），按原尺寸画才清楚；看得见的只有 1 像素 """


def bar_width(labels):  # type: (list) -> int
    """ 操作条按钮放得下这几种字要多宽（最窄 BAR_MIN_W）"""
    return max([BAR_MIN_W] + [text_width(label) + 2 * BAR_PAD for label in labels if label])


def bar_natural(widths):  # type: (list) -> int
    """ 一排操作条按钮至少要多宽：等宽，都按最宽的那个算 """
    return max(widths) * len(widths) + GAP * (len(widths) - 1) if widths else 0


def more_natural(widths):  # type: (list) -> int
    """ 「更多」两列至少要多宽：每列都按最宽的那个按钮算 """
    return max(widths) * MORE_COLUMNS + GAP * (MORE_COLUMNS - 1) if widths else 0


def bar_row(widths, avail):  # type: (list, int) -> list
    """
    一排等宽的操作条按钮怎么摆：返回每个按钮的 (x, 宽)。宽 = avail 平分（除不尽的给后面的），不比最宽的那个自然宽窄；
    平分出来比 BAR_MAX_W 还宽就都取 BAR_MAX_W、整排居中
    """
    count = len(widths)
    if not count:
        return []
    gaps = GAP * (count - 1)
    natural = max(widths)
    share = (avail - gaps) // count
    if share >= BAR_MAX_W:
        each = max(BAR_MAX_W, natural)
        x = max(0, (avail - each * count - gaps) // 2)
        return [(x + index * (each + GAP), each) for index in range(count)]
    if share < natural:
        return [(index * (natural + GAP), natural) for index in range(count)]
    extra = avail - gaps - share * count
    row, x = [], 0
    for index in range(count):
        width = share + (1 if index >= count - extra else 0)
        row.append((x, width))
        x += width + GAP
    return row


def card_head_height(close_size=CLOSE_SIZE, close_offset=CARD_CLOSE_OFFSET):  # type: (tuple, tuple) -> int
    """ 顶栏多高：放得下物品图标、一行字、小 x（小 x 往上偏的那几像素伸进框的留白里，不算）"""
    return max(HEAD_ICON, TEXT_H, int(close_size[1]) + min(0, int(close_offset[1])))


def card_layout(content_size, bar, more=(), expanded=False, pager=None, icon=True, kind_width=0,
                close_size=CLOSE_SIZE, close_offset=CARD_CLOSE_OFFSET):
    # type: (tuple, list, list, bool, tuple or None, bool, int, tuple, tuple) -> dict
    """
    信息卡 + 图标操作条：每样东西摆在哪。
      content_size  内容控件的尺寸（含它四周自带的 4 像素）
      bar           操作条每个按钮的自然宽（bar_width），按显示顺序
      more          「更多」里每个文字按钮的自然宽（button_width）；收起时也给 —— 卡片宽按它算过，展开、收起宽度不变
      expanded      「更多」展开着没有
      pager         候选的翻页行：(箭头宽, 箭头高, 数字至少多宽)；没有给 None
      icon          顶栏有没有物品图标
      kind_width    顶栏种类那几个字多宽；close_size / close_offset：小 x 的尺寸与偏移（JSON 里读回来的）
    返回 dict，坐标相对框的左上角（框本身摆到屏幕上归 tooltip 管理器）：
      size       框的 (宽, 高)
      icon       物品图标的 (x, y)；没有图标是 None
      kind       种类的 (x, y)：有图标时在图标右边
      close      小 x 插槽的 (x, y, 宽, 高)：右上角、在顶栏里竖直居中；小 x 在插槽里再按自己的 offset 偏
      content    内容控件的 (x, y)：它自带 4 像素，摆在 x = 0，字正好落在 PAD 那条竖线上
      divider    分隔线的 (x, y, 宽)；下面什么都没有时是 None
      actions    按钮区的 (x, y, 宽, 高)；下面这些坐标都相对它
      pager      {"prev": (x, y), "next": (x, y), "number": (x, y, 宽)}：箭头在两头、数字占中间；没有翻页行是 None
      bar        操作条每个按钮的 (x, y, 宽, 高)
      more_line  「更多」上面那条分隔线的 (x, y, 宽)；收起时 None
      more       「更多」里每个按钮的 (x, y, 宽, 高)，两列、从左到右再往下；收起时是空的
    宽取 CARD_MIN_INNER、内容、顶栏、操作条、「更多」、翻页行里宽的那个
    """
    bar, more = list(bar), list(more)
    content_w, content_h = int(round(content_size[0])), int(round(content_size[1]))
    close_w, close_h = int(close_size[0]), int(close_size[1])
    head_h = card_head_height(close_size, close_offset)
    left = PAD + (HEAD_ICON + HEAD_ICON_GAP if icon else 0)
    head = left - PAD + kind_width + 2 * GAP + close_w
    pager_w = 2 * int(pager[0]) + 2 * GAP + int(pager[2]) if pager else 0
    inner = max(CARD_MIN_INNER, content_w - 2 * PAD, head, bar_natural(bar), more_natural(more), pager_w)
    width = inner + 2 * PAD
    content_y = head_h + GAP  # 即 PAD + 顶栏高 + GAP - PAD：内容自带的 4 像素抵掉框的 PAD
    bottom = content_y + max(0, content_h - PAD)  # 内容最后一行字的底
    y, pager_geo = 0, None
    if pager:
        arrow_w, arrow_h = int(pager[0]), int(pager[1])
        row_h = max(arrow_h, BUTTON_H)
        arrow_y = (row_h - arrow_h) // 2
        pager_geo = {
            "prev": (0, arrow_y),
            "next": (inner - arrow_w, arrow_y),
            "number": (arrow_w + GAP, (row_h - TEXT_H) // 2, inner - 2 * arrow_w - 2 * GAP),
        }
        y += row_h + GAP
    bar_geo = [(x, y, w, BAR_H) for x, w in bar_row(bar, inner)]
    y += BAR_H if bar_geo else (-GAP if pager else 0)
    more_line, more_geo = None, []
    if expanded and more:
        y += LINE_GAP
        more_line = (0, y, inner)
        y += 1 + LINE_GAP
        column_w = (inner - GAP * (MORE_COLUMNS - 1)) // MORE_COLUMNS
        for index in range(len(more)):
            row, column = divmod(index, MORE_COLUMNS)
            x = column * (column_w + GAP)
            last = column == MORE_COLUMNS - 1
            more_geo.append((x, y + row * (BUTTON_H + GAP), inner - x if last else column_w, BUTTON_H))
        y += -(-len(more) // MORE_COLUMNS) * (BUTTON_H + GAP) - GAP
    if y > 0:
        line_y = bottom + LINE_GAP
        divider = (PAD, line_y, inner)
        actions_y = line_y + 1 + LINE_GAP
    else:
        divider = None
        actions_y = bottom
    return {
        "size": (width, actions_y + max(0, y) + PAD),
        "icon": (PAD, PAD + (head_h - HEAD_ICON) // 2) if icon else None,
        "kind": (left, PAD + (head_h - TEXT_H) // 2),
        "close": (width - PAD - close_w, PAD + max(0, (head_h - close_h) // 2), close_w, close_h),
        "content": (0, content_y),
        "divider": divider,
        "actions": (PAD, actions_y, inner, max(0, y)),
        "pager": pager_geo,
        "bar": bar_geo,
        "more_line": more_line,
        "more": more_geo,
    }
