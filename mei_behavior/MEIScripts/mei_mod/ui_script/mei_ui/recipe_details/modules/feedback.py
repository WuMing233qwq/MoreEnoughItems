# coding=utf-8

# ----------------------------------------------------------------------
#  feedback.py is part of MoreEnoughItems.
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
查询无结果时给玩家的反馈。

为什么单独一层: 查空时"什么都不发生"对玩家来说和"点坏了"没有区别
(recipe_ui_api.md §2.7-6)。但反馈形式是会变的, 所以这里只定契约,
实现可整体替换, 和 click.py 的点击策略同一个路子。
"""
from MEIScripts.constants.codes import QueryConst
from MEIScripts.constants.texts import RecipeText
from mod_log import logger


def DescribeItem(item):
    """
    取一个能给玩家看的名字。

    `Item.HoverText` 是**惰性字段, 未加载时会抛 ValueError**, 所以必须兜底 ——
    这条反馈路径本身就是异常路径, 不能在这里二次翻车。
    """
    try:
        text = item.HoverText
    except Exception:
        text = None
    if text:
        return text.split("\n")[0]
    return getattr(item, "ItemId", None) or str(item)


class NoRecipesNotifier(object):
    """查询无结果时的反馈契约。"""

    def Notify(self, item, query_by):  # type: (any, str) -> None
        raise NotImplementedError


class LogNotifier(NoRecipesNotifier):
    """ 只记日志。要给玩家别的反馈形式，换一个实现即可 """

    MESSAGES = {
        QueryConst.Output: RecipeText.NoRecipesForOutput,
        QueryConst.Input: RecipeText.NoRecipesForInput,
    }

    def Notify(self, item, query_by):
        template = self.MESSAGES.get(query_by) or self.MESSAGES[QueryConst.Output]
        logger.info("[MEI/feedback] " + template.format(DescribeItem(item)))


_notifier = LogNotifier()


def GetNotifier():  # type: () -> NoRecipesNotifier
    return _notifier


def SetNotifier(notifier):  # type: (NoRecipesNotifier) -> NoRecipesNotifier
    """ 替换反馈实现, 返回旧的便于还原 """
    if notifier is None:
        raise ValueError("notifier must not be None")
    global _notifier
    old = _notifier
    _notifier = notifier
    return old


def ResetNotifier():
    global _notifier
    _notifier = LogNotifier()


def NotifyNoRecipes(item, query_by):
    """
    统一入口。**不放进 ResolveQuery** —— 那是纯查询, 第三方拿它自己做判断时
    不该被弹一脸提示; 由"确实是用户发起的查询"那两个调用点显式调。
    """
    GetNotifier().Notify(item, query_by)
