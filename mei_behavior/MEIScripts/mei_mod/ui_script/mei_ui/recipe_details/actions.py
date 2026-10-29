# coding=utf-8

# ----------------------------------------------------------------------
#  actions.py is part of MoreEnoughItems.
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
内置动作按钮的定义 —— `recipes/common.json` 的 `buttons_panel` 在 Python 侧的对应物。

**这里是那张镜像表唯一该待的地方。** 它曾经躺在 controls/button.py 里，
可那是通用轮子，不该认识「收藏」「置顶」这些东西；而这张表描述的恰恰是
「buttons_panel 那四个格子各是谁、在哪」——它与 JSON 同层、同一个人维护，
改 JSON 的人一眼能看到要同步改这里。

镜像本身暂时消不掉：`buttons_panel` 是静态四格，而 JSON 里声明了的 toggle
必须有对应绑定，否则报错。要让「没声明就没有那个控件」，得把 buttons_panel
改成数据驱动 grid —— 那是**嵌套 collection**，引擎支不支持还不清楚。

第三方按钮**完全不受本表约束**：自带 prefix 与 path，爱放哪放哪，见
docs/extension_api.md §4.5。
"""
from collections import OrderedDict

from .controls.button import ActionButton

PREFIX_ROOT = "mei_ui.recipe.action"
""" 内置动作的绑定名前缀根；与 recipes/common.json 的 buttons_panel 逐字一致 """

PLUS = PREFIX_ROOT + ".plus"
""" 快捷转移（调用合成）。只在有转移策略的类型上出现，见 quick_craft.md """

TOP = PREFIX_ROOT + ".top"
""" 置顶配方 """

STAR = PREFIX_ROOT + ".star"
""" 收藏配方 """

TREE = PREFIX_ROOT + ".tree"
""" 配方树：以这条配方的主产物为根、根就用这一条（docs/architecture/recipe_tree.md）"""

SLOT_PATHS = OrderedDict([
    (TREE, "/wrapper/buttons/0/toggle_button"),
    (TOP, "/wrapper/buttons/1/toggle_button"),
    (STAR, "/wrapper/buttons/2/toggle_button"),
    (PLUS, "/wrapper/buttons/3/toggle_button"),
])
"""
前缀 -> 控件路径，**相对配方行控件**（RecipeUIScript.RecipeControl）。

顺序即 buttons_panel 里 0/1/2/3 四个格子的顺序，改 JSON 必须同步改这里。
（比如 plus 与 tree 对调：JSON 改了这张表也得跟着改，否则按钮错位。）
路径写相对而非绝对，是跟 CraftingTableUIScript.InitControls 一个路子 ——
全项目取控件都走 `RecipeControl.GetChildByPath(相对路径)`。
"""


def ResolvePath(prefix):  # type: (str) -> str or None
    """ 内置动作的默认控件路径；非内置返回 None，由声明方自带 path """
    return SLOT_PATHS.get(prefix)


def BuildPlaceholders():  # type: () -> list
    """
    给每个内置动作建一个**占位**声明。

    占位没有 OnAction，于是 ResolveVisible 恒假、不渲染，但绑定照建 ——
    JSON 里那四个 toggle 少一条绑定就会报错，占位就是为这个存在的。
    业务实现补上（在脚本上写装饰器）时界面自动出现，不用改 JSON。
    """
    # 不给 path: 占位不渲染也就不需要推状态, 给了反而会白白去取一次控件
    return [ActionButton(prefix) for prefix in SLOT_PATHS]


def IsEnabled(prefix, allow):  # type: (str, any) -> bool
    """ allow 为 None 表示不限制；否则只有列在里面的内置动作才启用 """
    # 非内置的动作不受 ACTIONS 约束 —— 那是第三方自己加的按钮, 它自己决定生死
    if allow is None or prefix not in SLOT_PATHS:
        return True
    return prefix in allow
