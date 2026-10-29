# coding=utf-8
# ----------------------------------------------------------------------
#  ingredient.py is part of MoreEnoughItems.
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
import abc


class IngredientLike(object):
    """
    槽位内容的唯一契约. Stack 与 Ingredient 均实现它,
    消费端 (render_slot / 索引 / 配方树 / 书签) 只认这个契约, 永不 isinstance 判类型.

    语义边界: 本契约只用于**配方语境** —— get_amount() 是 "这个槽位需要/产出多少",
    不是 "背包里有多少". MEI 不读背包、不做配方转移, 因此 Stack.Count 与
    Ingredient.Amount 在本契约下是同一个概念.

    身份不在本契约上: 一组候选无法作为索引键有意义地存在,
    故 get_key() 只属于 Stack, 绝不上提到这里.

    实现约束: 本类的 __slots__ 必须保持为空元组, 且**每个子类都必须显式声明 __slots__**,
    漏写的子类会重新长出 __dict__ (py2.7.18 实测确认).
    """
    __metaclass__ = abc.ABCMeta
    __slots__ = ()

    @abc.abstractmethod
    def get_stacks(self):  # type: () -> list
        """ 候选 Stack 列表; 单元素实现返回 [self] """
        raise NotImplementedError

    @abc.abstractmethod
    def is_empty(self):  # type: () -> bool
        """ 是否为空槽 """
        raise NotImplementedError

    @abc.abstractmethod
    def get_amount(self):  # type: () -> int
        """ 数量的唯一出口 (需求量 / 产出量) """
        raise NotImplementedError

    @abc.abstractmethod
    def to_dict(self):  # type: () -> dict
        """
        序列化为贫血 dict —— 只含 dict/list/标量, **无 tuple、无 Python 对象**
        (engineering.md §7-3: 引擎事件数据不支持 tuple).
        这是**存盘**用的完整形态.
        """
        raise NotImplementedError

    def to_canonical(self):  # type: () -> dict
        """
        **身份计算**用的规范形. 缺省与 to_dict 相同.

        只有需要「符号折叠」的实现才覆盖它 —— 目前是 Ingredient 的 tag 折叠:
        tag 的成员是异步扫出来的, 若把成员写进身份, 同一条配方在扫描前后会算出
        不同的 Recipe.Id. Stack 没有符号引用, 故用缺省实现即可.
        """
        return self.to_dict()

    def get_chance(self):  # type: () -> float
        """ 产出概率, 默认必得 """
        return 1.0

    def get_tag_id(self):  # type: () -> str or None
        """ 符号化标签引用 (如 "mei:fuels"), 仅 Ingredient 覆盖 """
        return None
