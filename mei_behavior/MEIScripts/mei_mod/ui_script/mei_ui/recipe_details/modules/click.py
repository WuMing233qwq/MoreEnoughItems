# coding=utf-8
# ----------------------------------------------------------------------
#  click.py is part of MoreEnoughItems.
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
配方槽位点击的**语义层** —— 与绑定层分体.

为什么要分开:
  绑定层只回答「哪一行、哪个槽、哪个键、槽里是什么」, 这部分是引擎机制, 不该变;
  而「点了之后干什么」是**产品语义**, 将来会随查询模式变化
  (作弊模式 / 工具模式 / 只读模式…). 把语义写死在绑定层, 换模式就得改绑定层.

⇒ 绑定层解出 SlotClickContext 交给可替换的 SlotClickPolicy, 换模式只换策略.

默认语义(与物品浏览器同构): 左键查来源, 右键查用途, 切换整套 RecipeDetails 的状态.

多查询模式本身尚未落地, 本模块只提供接缝.
"""
from mod_log import logger
from MEIScripts.utils.text import error_text

BUTTON_PRIMARY = "primary"
""" 左键 """

BUTTON_SECONDARY = "secondary"
""" 右键 """

# 查询方向(Output/Input)**不在这里定义** —— 它是 registry 与 ui_script 共用的概念,
# 按依赖方向只能落在 constants: 见 constants/codes.py 的 QueryConst.


class SlotClickContext(object):
    """ 一次槽位点击的全部已知信息. 由绑定层填充, 交给策略消费 """

    __slots__ = ("Button", "Panel", "Item", "Row", "GroupId", "Ordinal", "Binder")

    def __init__(self, button, panel, item, row, group_id, ordinal, binder):
        self.Button = button      # type: str   # BUTTON_PRIMARY / BUTTON_SECONDARY
        self.Panel = panel        # type: any   # 被点中的 ItemPanel
        self.Item = item          # type: any   # 面板**当前显示**的 Item(轮播面板即当前那个)
        self.Row = row            # type: int   # 第几行配方(0-based)
        self.GroupId = group_id   # type: str   # 哪个绑定组
        self.Ordinal = ordinal    # type: int   # 组内序号 —— 与 Group 回调收到的是同一个
        self.Binder = binder      # type: any   # RecipesGridBind 实例


class SlotClickPolicy(object):
    """ 点击语义策略. 想改点击行为就换这个, 不要动绑定层 """

    def OnSlotClick(self, context):  # type: (SlotClickContext) -> None
        raise NotImplementedError


class DefaultSlotClickPolicy(SlotClickPolicy):
    """
    默认语义: 左键查来源 / 右键查用途, 切换整套 RecipeDetails 状态.

    实现上**委托给面板自己的 OnPrimaryClick / OnSecondaryClick**, 而不是自己去调
    ShowRecipeDetails —— 这样三件事自动成立:
      · 触屏输入模式的守卫(ItemPanel 里那个 GetInputMode 判断)照样生效;
      · 子类面板的覆写(如 GroupItemPanel 的分组展开)被尊重;
      · 配方槽位与物品浏览器的点击语义天生同构, 不会各自漂移.
    """

    def OnSlotClick(self, context):
        if context.Item is None:
            return   # 空槽位, 什么都不做

        panel = context.Panel
        handler = (panel.OnPrimaryClick if context.Button == BUTTON_PRIMARY
                   else panel.OnSecondaryClick)
        try:
            handler(None)
        except Exception as e:  # noqa  点击不能把界面带崩
            logger.error("[MEI/click] 槽位点击处理失败(行 {} 组内序号 {}): {}".format(
                context.Row, context.Ordinal, error_text(e)))


_POLICY = [DefaultSlotClickPolicy()]


def GetPolicy():  # type: () -> SlotClickPolicy
    return _POLICY[0]


def SetPolicy(policy):  # type: (SlotClickPolicy) -> SlotClickPolicy
    """ 替换点击语义. 返回被替换掉的旧策略, 便于临时切换后还原 """
    if policy is None:
        raise ValueError("policy cannot be None; 用 ResetPolicy() 恢复默认")
    previous = _POLICY[0]
    _POLICY[0] = policy
    return previous


def ResetPolicy():
    _POLICY[0] = DefaultSlotClickPolicy()
