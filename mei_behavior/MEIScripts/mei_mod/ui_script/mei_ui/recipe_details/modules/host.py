# coding=utf-8

# ----------------------------------------------------------------------
#  host.py is part of MoreEnoughItems.
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
配方页脚本的接入与拆除，三个宿主共用：配方页（recipe_details/script.py）、tooltip 的配方预览（tooltip/recipe.py）、
配方树菜单里的预览（recipe_tree/controls/preview.py）。

- **什么时候接**：配方页在每一行的 `#visible` 回调里当场接 —— 翻页、换类型时
  新脚本在同一轮拉绑定里接上，格子直接覆盖、不闪；推到下一帧的 Tick 再接的话，中间那一帧格子回缺省值，翻页就闪。
  在回调里接是安全的：绑定器只在第一次见到某个绑定前缀时才向引擎注册（RecipesGridBind.AddGroup），之后只改 Python 这边的表；
  两个预览（tooltip、配方树菜单）没有这一帧的讲究，在自己每帧的 Poll 里接。
- **出错只丢这一行，而且绝不往外抛**：记一行 error、返回 False，别的行照常；`_Created` 先标上（抛了也不每帧重来），
  `_Broken` 标上（节拍不再派给它）。回调里抛异常，引擎会当场扔掉那条绑定、不给日志（引擎结论 §15）—— 第三方的 OnCreate
  抛一次整列配方就空了，所以接入一律经这里。
"""
from mod_log import logger

from MEIScripts.utils.text import error_text


def attach_script(script, index, binder, control, tag="ui"):  # type: (any, int, any, any, str) -> bool
    """ 把配方页脚本接到一行控件上：注入行号、绑定器、行控件，OnCreate、InitBindings。成了返回 True """
    script.GridItemIndex = index
    script.RecipesGridBind = binder
    script.RecipeControl = control
    script._Created = True  # noqa  先标上：下面抛了也别每帧重来
    try:
        script.OnCreate()
        script.InitBindings()
    except Exception as e:  # noqa  第三方的配方页脚本出错不能带走整页
        script._Broken = True  # noqa
        logger.error("[MEI/{}] 配方页脚本 {} 接不上第 {} 行，这一行不画: {}".format(
            tag, type(script).__name__, index + 1, error_text(e)))
        return False
    return True


def detach_script(script, tag="ui"):  # type: (any, str) -> None
    """ 拆掉接上的脚本（翻页、换类型、关界面、收起预览）：解绑定、OnDestroy；出错只记一行，不影响拆别的 """
    if not getattr(script, "_Created", False):
        return
    try:
        script.DestroyBindings()
        script.OnDestroy()
    except Exception as e:  # noqa
        logger.error("[MEI/{}] 配方页脚本 {} 拆的时候出错: {}".format(tag, type(script).__name__, error_text(e)))


def is_live(script):  # type: (any) -> bool
    """ 接上了、也没出错：节拍只派给这种 """
    return bool(getattr(script, "_Created", False)) and not getattr(script, "_Broken", False)
