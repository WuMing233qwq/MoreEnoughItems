# coding=utf-8

# ----------------------------------------------------------------------
#  page_host.py is part of MoreEnoughItems.
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
托管配方页（RecipePageHost）：一个类型的配方页内容区整块交给别人画。

用在配方页由别的模组自己的 JSON 控件、自己的脚本画、MEI 不认识里面格子的类型上。MEI 照旧管配方页的框 ——
顶栏（返回、类型名、页码与翻页、关闭）、右边的类型页签、左边的工作站一列、滚轮翻页、导航；
内容区里建一个容器（CONTAINER），一页放几条、这一页怎么画交给托管者。

这种类型没有 MEI 的配方行，所以行上的动作按钮（收藏、置顶、+、配方树）没有，tooltip 不出配方预览；配方树缺省不用它的配方（TREE）。

只是约定，零引擎依赖：MEI 按名字调下面这几个方法，没写的照这里的缺省。第三方继承 ctx.Types.RecipePageHost，
或者写一个有同样方法的类都行；登记在类型上（RecipeCategory(page_host=…)）
"""


class RecipePageHost(object):

    CONTAINER = "mei_recipe_common.hosted_page"
    """
    MEI 在配方页内容区建的容器（这一页的控件建在它下面）的 JSON 定义名。缺省是竖排的 stack_panel：
    宽取里面最宽的那个控件、高是它们加起来，摆在顶栏下面、水平居中。
    建在里面的控件**宽不要写父控件的百分比** —— 容器（和配方页）的宽跟着它们，写了就绕成圈，引擎排不出来
    """

    TREE = False
    """
    配方树用不用这个类型的配方：缺省不用 —— 托管页的配方往往只是个壳（原料、产物在托管者自己的数据里）。
    配方的 Inputs / Outputs / Catalysts 是 MEI 认得的 Ingredient 时写 True，配方树照常展开、汇总
    """

    def PageSize(self, category, recipes, height):  # type: (any, list, int) -> int
        """ 一页放几条：recipes 是这个类型的全部配方，height 是内容区能用的高（顶栏下面到配方页底边）。少于 1 按 1 """
        return 1

    def Show(self, page):  # type: (any) -> None
        """ 画这一页。page 是 MEI 给的 HostedPage：容器、这一页的配方、建控件的方法，见 docs/modding/03-recipe-page.md """

    def Hide(self, page):  # type: (any) -> None
        """
        收回这一页：翻页、换类型、刷新、关配方页之前都先调它。容器下面建的控件可以留着给下一页接着用 ——
        同一个类型翻页时容器不换（page.Serial 一样）；换了类型、刷新、关页时容器连同里面的控件一起删
        """

    def Tick(self, page, ticks):  # type: (any, int) -> None
        """ 配方页的节拍（0.2 秒一拍），ticks 从这一页显示起算（显示那一刻是 0，不派）"""

    def RecipeAt(self, page, x, y):  # type: (any, float, float) -> any
        """ 屏幕上这一点落在这一页的哪条配方上（快捷键「收藏这条配方」用）；不知道给 None """
        return None
