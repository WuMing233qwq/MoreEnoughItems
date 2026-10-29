# coding=utf-8
# ----------------------------------------------------------------------
#  base.py is part of MoreEnoughItems.
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

from MEIScripts.common.classes.types import Item

# 注意: 本模块**不得** import ui_script 下的任何东西.
# 它被 registry 层(recipes.py 的 issubclass 守卫)依赖, 一旦拉进 UI,
# registry 的 import 链就会带起整个 UI 栈, 索引层将无法在无 UI 环境下建立与测试
# (engineering.md §2).
# 绑定器耦合的实现层在 ui_script 侧: recipe_details/modules/script_base.py 的 RecipeUIScript.


class RecipeSource(object):
    """
    配方来源：只回答「有哪些配方」，不管类型标识与展示

    类型标识与展示元数据在 RecipeCategory；一个 Category 可绑多个 Source，
    合并与去重由 RecipeManager 负责。拆分理由见 docs/migration/tasks_s4.md。
    """
    CategoryId = ""
    """ 本来源供给哪个配方类型，值取 RecipeCategory.Id """

    CAN_ENUMERATE = False
    """
    GetAll() 能否给出**完整**的配方表。

    引擎源给不出（没有枚举接口），故默认为假，全量只能靠 RecipeScanner 逐个物品反查凑。
    自建表的来源应置真，它知道自己有哪些配方。
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def QueryByOutput(self, item):  # type: (Item) -> list
        """ 按产物查来源 """
        raise NotImplementedError

    @abc.abstractmethod
    def QueryByInput(self, item):  # type: (Item) -> list
        """ 按材料查用途 """
        raise NotImplementedError

    def GetAll(self):  # type: () -> list
        """ 全部配方；给不出全量的来源返回空表，故这里不是抽象方法 """
        return []

    def IsAllComplete(self):  # type: () -> bool
        """ GetAll 这一次给的是否已是完整表 """
        # 边扫边给的来源要覆写它: 扫完之前 GetAll 返回的是部分结果
        return self.CAN_ENUMERATE


class BaseRecipeUIScript(object):
    """
    配方 UI 逻辑的**契约层** —— 纯声明, 零 UI 依赖.

    它只回答「一个配方页脚本必须提供什么」, 不回答「怎么提供」:
      · 绑定器耦合的实现在 ui_script 侧的 RecipeUIScript
        (recipe_details/modules/script_base.py);
      · registry 的 RegisterScript 用本类做 issubclass 守卫, 故本类必须留在
        common 且不得 import ui_script —— 否则 registry 会被拽进 UI 依赖.

    生命周期字段 (GridItemIndex / RecipesGridBind / RecipeControl / _Created)
    目前是**类属性 + 运行期注入**: 实例在 PrepareRecipeUIScript 里被造出来时是半成品,
    要等引擎渲染到那一行、由 GetRecipeVisible 的绑定回调补齐.
    这是绕开「grid 子控件首次渲染前不可访问」的必要手段, 但契约是隐式的.
    ⇒ 显式化方案见 docs/architecture/recipe_ui_api.md §4.7 (RecipeUIContext).
    """
    TYPE = ""
    """
    **不读**：配方页脚本属于哪个类型由 RegisterScript(category_id, 脚本类) 决定，
    几个类型可以共用一个脚本类（高炉、烟熏炉用熔炉的），所以写在脚本类上的类型名不可能总是对的。留着只为老的第三方脚本照写不报错
    """

    _Created = False
    """ 是否已经执行了生命周期的 OnCreate """

    GridItemIndex = 0
    """ 当前UIScript在Recipes网格控件下的索引 在初始化前会自动传入 """
    RecipesGridBind = None
    """ RecipesGridBind实例 用于快速进行批量绑定管理物品 """
    RecipeControl = None
    """ 配方的BaseUIControl实例 """

    __metaclass__ = abc.ABCMeta

    def __init__(self, recipe):
        self.Recipe = recipe

        self._BindingsInited = False
        self._AutoBindingGroupIds = []
        self._AutoIndexedBindingKeys = []

    @abc.abstractmethod
    def InitBindings(self):
        """ 按装饰器规则初始化绑定 (由实现层提供) """
        raise NotImplementedError

    @abc.abstractmethod
    def DestroyBindings(self):
        """ 销毁绑定并重置状态 (由实现层提供) """
        raise NotImplementedError

    @abc.abstractmethod
    def OnCreate(self):
        pass

    @abc.abstractmethod
    def OnDestroy(self):
        pass

    ANIM_TICK_INTERVAL = 0.2
    """
    `OnAnimTick` 的间隔（秒），**只读**：节拍由配方详情页统一驱动，改这个类属性不会改变它。
    取 0.2 是沿用 `BaseItemsGridScript` 的既有节拍，不另发明一个。
    """

    _AnimBase = None
    """ 节拍对表基准，由驱动方在第一拍写入。见 `OnAnimTick` 的相位说明 """

    def OnAnimTick(self, ticks):
        """
        渲染节拍，每 `ANIM_TICK_INTERVAL` 秒一次。

        **`ticks` 是相对本脚本的**：从它自己出生那一刻算起。
        不是整页的绝对计数 —— 那样的话，一个中途才创建出来的配方行会撞上
        任意相位，`ticks % 15` 可能只等了 1 拍就命中，表现为**动画跳帧**
        （旧的 `AddRepeatedTimer` 从自己创建那刻起算，天然没这问题）。
        ⇒ 驱动方对每个脚本单独对表，`ticks % N` 因此总是「我出生后第 N 拍」。

        **第一次收到的是 `0`，而且就在 `OnCreate` 之后立刻送到**（不等 timer）。
        旧实现是第一拍只对表、第二拍才给 1，于是创建后有一段最长 **0.4 秒**
        的空窗，控件停在 layout 初值上，看着像“卡一下才开始动”。
        ⇒ **把第 0 帧当成初始外观来写**：它应该与你希望刚打开时看到的样子一致。

        **不覆写就完全不会被调用** —— 一个配方页里没有任何脚本覆写它时，
        驱动方连遍历都不做（判据是 `OnAnimTick` 是否仍是本基类的那个函数）。

        用来做进度条、箭头动画、多候选轮播这类**持续更新**。
        `OnCreate` 里请不要再自己起 `AddRepeatedTimer` ——
        那会变成「每个配方行一个 timer」，正是 `recipe_ui_api.md` §2.7-5 记的那类问题；
        而且这条节拍是**整页共享一个** timer。

        本方法抛异常会被驱动方吞掉并记一条日志，不会拖垮同页其它脚本，
        但也不会有人替你修。
        """
        # 默认空实现: 绝大多数配方页是静态的, 不需要节拍



class SlotTarget(object):
    """
    一个可写的目标槽位 —— **物品搬过去之后落在哪**

    存在的理由：让 ItemSource 能自己完成整次搬运，而不必认识
    SetPlayerUIItem / SpawnItemToContainer 这些写入手段。
    实现在 mei_mod/transfer/targets.py（那层才碰引擎），第三方工作站可以自带。
    """

    Slot = 0
    """ 目标槽位号，含义由实现决定（玩家侧共享编号 / 方块容器内下标）"""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def Put(self, stack):  # type: (any) -> bool
        """ 把 stack 写进本槽位，返回是否成功 """
        raise NotImplementedError

    def Clear(self):  # type: () -> bool
        """ 腾空本槽位，已有物品退回玩家。默认不支持 """
        return False

    def Peek(self):  # type: () -> any
        """ 看一眼当前槽位里是什么，空则 None。默认不支持 """
        return None


class ItemSource(object):
    """
    物品来源：既回答「玩家能拿到什么」，也**负责把东西搬过去**

    与 RecipeSource 同构：契约在这里(纯)，实现在各自的层。
    内置背包来源在 mei_mod/transfer/inventory.py，第三方存储模组自己注册。

    **搬运由来源自己做，不是框架取出来再写进去。** 框架只派发
    「你的 handle 那份东西，搬 N 个到这个 target」——
    因为只有来源自己知道怎么安全地从自己身上取：
      · 背包扣一格数量、存储模组可能是一次事务性提取；
      · 中途失败该怎么还回去，也只有它自己知道。
    框架横插一手就等于把每个来源的内部规则都学一遍，加一个来源就要改框架。
    """

    Id = ""
    """ 来源标识，须带命名空间前缀，如 "mei:inventory" / "yourmod:backpack" """

    Priority = 0
    """ 取用顺序，小的先取。同优先级按注册序，保证同一次查询两次结果一致 """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def Collect(self, ctx):  # type: (any) -> list
        """
        列出当前可用的物品，返回 [(ItemStack, handle), ...]。**只看不动**

        handle 是**本来源自己的取用凭据**(背包是槽位号，存储模组可能是记录 id)，
        框架不解释它，MoveTo 时原样还给你。它要过跨端边界，
        故只能是 dict/list/标量(引擎结论 §6)。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def MoveTo(self, ctx, handle, count, target):  # type: (any, any, int, SlotTarget) -> int
        """
        把 handle 指向的东西搬 count 个到 target，返回**实际搬了几个**

        返回值必须诚实 —— 上层靠它统计成功格数并决定要不要继续。
        搬不动返回 0，别抛；**失败时必须保证自己这边没少东西**。
        """
        raise NotImplementedError
