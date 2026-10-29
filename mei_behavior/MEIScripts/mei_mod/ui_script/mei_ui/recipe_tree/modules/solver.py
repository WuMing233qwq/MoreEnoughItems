# coding=utf-8

# ----------------------------------------------------------------------
#  solver.py is part of MoreEnoughItems.
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
配方树的解算（纯逻辑：不 import 引擎、不认识 RecipeManager）。从根往下按层展开（BFS），按时间预算分帧推进（Step）；
配方经注入的取数对象拿（provider：Recipes(key) / IsItem(key) / IsPinned(recipe)），离线能用假配方表测（probe_recipe_tree.py）。

每一格：选一条配方 → 合成次数 = ⌈需要 ÷ 单次产出⌉、余料 = 次数 × 产出 − 需要 → 每样原料一个子格（需要 = 次数 × 用量）。

防无限递归三道（docs/design/recipe_tree.html「解算与防递归」）：
1. 路径排除（候选级，不是节点级）：从根到这一格的路上出现过的物品不许再当原料 —— 用到它们的候选不选；
   候选全都绕回才把这一格当原料（CYCLIC）。多候选的原料（标签）只要还有一个候选不在路上就不算绕回、换成那个候选
2. 还原识别：做 X 的候选 R 用到 Y，而 Y 能直接用 X 做出来 —— R 是「还原」（铁块 → 铁锭），有别的候选时默认不选
3. 护栏：深度 MAX_DEPTH、节点 MAX_NODES，触线的标 TRUNC

选哪条（确定性：同样的输入永远得到同一棵树）：根配方（从配方行打开时）→ 在当前类型里挑：本树的选择 → 全局首选 → 置顶 →
启发（不还原 → 原料种类少 → 单次产出多 → 类型顺序 → 注册顺序）。当前类型 = 本树为这个物品选的类型，没选过就不限；
类型由点工作方块换，点原料格只在当前类型里翻配方
"""
import collections
import math
import time

STATE_PENDING = "pending"
""" 分帧展开中，还没轮到 """
STATE_OK = "ok"
""" 选好配方、往下展开了 """
STATE_LEAF = "leaf"
""" 查不到配方：原料 """
STATE_STOP = "stop"
""" 这棵树里「不再展开」 """
STATE_RAW = "raw"
""" 全局「当原料」 """
STATE_CYCLIC = "cyclic"
""" 候选配方全都会绕回：当原料 """
STATE_TRUNC = "trunc"
""" 触到深度 / 节点上限 """
STATE_NONITEM = "nonitem"
""" 流体、能量这类不是物品的条目：当原料 """

MAX_DEPTH = 256
""" 深度上限（16、64 都嫌低，256 的开销也没那么大） """
MAX_NODES = 2000
""" 节点上限（400 不够用） """


class TreeRecipe(object):
    """
    解算用的配方，由 provider 从 MEI 的 Recipe 改造出来：
    Id、类型 Type、原料 Inputs = [(候选物品键的元组, 数量), ...]（同样的原料已合并、顺序固定）、
    单次产出 Output（做出这一格的物品几个）、工具 Tools（催化剂：不消耗、不展开）、原配方 Source（预览、查看配方页用）、
    排序键 Order（类型顺序、注册顺序）、
    其他产出 Byproducts = ((物品键, 单次几个, 概率), ...)：这条配方除了这一格的物品还出的东西（不画在树上，汇总的「副产物」算它）
    """
    __slots__ = ("Id", "Type", "Inputs", "Output", "Tools", "Source", "Order", "Byproducts")

    def __init__(self, recipe_id, type_id, inputs, output, tools=(), source=None, order=(0, 0), byproducts=()):
        self.Id = recipe_id
        self.Type = type_id
        self.Inputs = [(tuple(choices), int(count)) for choices, count in inputs if choices]
        self.Output = max(1, int(output or 1))
        self.Tools = tuple(tools or ())
        self.Byproducts = tuple((key, max(1, int(count or 1)), min(1.0, max(0.0, float(chance))))
                                for key, count, chance in byproducts or () if key and chance > 0)
        self.Source = source
        self.Order = tuple(order)

    def Uses(self, key):  # type: (str) -> bool
        return any(key in choices for choices, _ in self.Inputs)

    def __repr__(self):
        return "TreeRecipe({!r})".format(self.Id)


class Candidate(object):
    """ 一格的一条候选配方：会不会绕回（Stuck 是绕回的那几样原料）、是不是还原 """
    __slots__ = ("Recipe", "Stuck", "Reverse")

    def __init__(self, recipe, stuck=(), reverse=False):
        self.Recipe = recipe  # type: TreeRecipe
        self.Stuck = tuple(stuck)  # type: tuple
        self.Reverse = reverse  # type: bool

    @property
    def Cyclic(self):  # type: () -> bool
        return bool(self.Stuck)


class TreeNode(object):
    """
    树上的一格。Key 是物品键（provider 给的），Choices 是这一格的原料有哪几个候选（标签；根是它自己），
    Sig 是从根往下的路径签名（重算后 Id 会变，折叠、菜单靠它找回同一格），Path 是从根到这一格的物品键集合
    """
    __slots__ = ("Id", "Key", "Choices", "Need", "Depth", "Parent", "Slot", "Children", "Sig", "Path", "State",
                 "Recipe", "Candidates", "Crafts", "Surplus", "Type")

    def __init__(self, node_id, key, need, depth=0, parent=None, slot=0, choices=None, sig="r", path=frozenset()):
        self.Id = node_id  # type: int
        self.Key = key  # type: str
        self.Choices = tuple(choices) if choices else (key,)  # type: tuple
        self.Need = int(need)  # type: int
        self.Depth = depth  # type: int
        self.Parent = parent  # type: int or None
        self.Slot = slot  # type: int  # 在父格配方的原料里排第几
        self.Children = []  # type: list  # 子格的 Id，和配方原料同一个顺序
        self.Sig = sig  # type: str
        self.Path = path | frozenset((key,))  # type: frozenset
        self.State = STATE_PENDING  # type: str
        self.Recipe = None  # type: TreeRecipe or None
        self.Candidates = []  # type: list  # 全部候选（各类型），和 provider 给的同一个顺序
        self.Crafts = 0  # type: int
        self.Surplus = 0  # type: int
        self.Type = None  # type: str or None  # 当前类型（选中的那条配方的类型）

    def Types(self):  # type: () -> list
        """ 有候选的类型，按候选顺序去重（工作方块的菜单翻它）"""
        seen, types = set(), []
        for candidate in self.Candidates:
            if candidate.Recipe.Type not in seen:
                seen.add(candidate.Recipe.Type)
                types.append(candidate.Recipe.Type)
        return types

    def InType(self, type_id):  # type: (str) -> list
        """ 这个类型的候选（原料格的菜单只翻它们）"""
        return [c for c in self.Candidates if c.Recipe.Type == type_id]

    def IsLeaf(self):  # type: () -> bool
        return self.State != STATE_OK


class Solver(object):
    """
    一次解算。构造时只建根；Step 按时间预算往下展开，Done 了 Nodes 就是整棵树（Nodes[0] 是根）。
    state 是这棵树的选择（choices.TreeState），prefs 是全局表（IsRaw / Default），provider 给配方
    """

    def __init__(self, provider, state, prefs, max_depth=MAX_DEPTH, max_nodes=MAX_NODES, clock=None):
        self.Provider = provider
        self.State = state
        self.Prefs = prefs
        self.MaxDepth = max_depth  # type: int
        self.MaxNodes = max_nodes  # type: int
        self.Clock = clock or time.time
        self.Nodes = []  # type: list
        self.Truncated = False  # type: bool
        self.__Queue = collections.deque()
        self.__Recipes = {}  # type: dict  # 物品键 -> [TreeRecipe]
        self.__Reverse = {}  # type: dict  # (配方 Id, 物品键) -> 是不是还原
        root = TreeNode(0, state.Root, state.Qty)
        self.Nodes.append(root)
        self.__Queue.append(root)

    @property
    def Done(self):  # type: () -> bool
        return not self.__Queue

    def Step(self, budget_ms=None):  # type: (float or None) -> bool
        """ 往下展开一段：budget_ms 毫秒用完就停（None 是一口气做完）；做完了返回 True """
        deadline = None if budget_ms is None else self.Clock() + budget_ms / 1000.0
        while self.__Queue:
            self.__Expand(self.__Queue.popleft())
            if deadline is not None and self.Clock() >= deadline:
                break
        return not self.__Queue

    def Find(self, sig):  # type: (str) -> TreeNode or None
        for node in self.Nodes:
            if node.Sig == sig:
                return node
        return None

    def MaxDepthReached(self):  # type: () -> int
        return max(node.Depth for node in self.Nodes)

    def RecipesOf(self, key):  # type: (str) -> list
        """ 做这个物品的配方（同一棵树里只向 provider 要一次）"""
        recipes = self.__Recipes.get(key)
        if recipes is None:
            recipes = self.__Recipes[key] = list(self.Provider.Recipes(key) or ())
        return recipes

    # 展开一格
# ======================================================================================================================
    def __Expand(self, node):  # type: (TreeNode) -> None
        key = node.Key
        if not self.Provider.IsItem(key):
            node.State = STATE_NONITEM
            return
        if node.Depth > 0 and self.Prefs.IsRaw(key):
            node.State = STATE_RAW
            return
        if node.Depth > 0 and key in self.State.Stop:
            node.State = STATE_STOP
            return
        if node.Depth >= self.MaxDepth or len(self.Nodes) >= self.MaxNodes:
            node.State = STATE_TRUNC
            self.Truncated = True
            return
        recipes = self.RecipesOf(key)
        if not recipes:
            node.State = STATE_LEAF
            return
        node.Candidates = [Candidate(recipe, self.__Stuck(recipe, node.Path)) for recipe in recipes]
        if len(node.Candidates) > 1:
            for candidate in node.Candidates:
                candidate.Reverse = self.__IsReverse(candidate.Recipe, key)
        chosen = self.__Choose(node)
        if chosen is None:
            node.State = STATE_CYCLIC
            return
        recipe = chosen.Recipe
        node.State = STATE_OK
        node.Recipe = recipe
        node.Type = recipe.Type
        node.Crafts = int(math.ceil(node.Need / float(recipe.Output)))
        node.Surplus = node.Crafts * recipe.Output - node.Need
        for slot, (choices, count) in enumerate(recipe.Inputs):
            child_key = self.__Pick(choices, node.Path)
            child = TreeNode(len(self.Nodes), child_key, node.Crafts * count, node.Depth + 1, node.Id, slot, choices,
                             "{}/{}:{}".format(node.Sig, slot, child_key), node.Path)
            self.Nodes.append(child)
            node.Children.append(child.Id)
            self.__Queue.append(child)

    @staticmethod
    def __Stuck(recipe, path):  # type: (TreeRecipe, frozenset) -> list
        """ 这条配方里会绕回的原料：候选全在路上（多候选的还有一个不在路上就不算）"""
        return [choices[0] for choices, _ in recipe.Inputs if all(key in path for key in choices)]

    def __IsReverse(self, recipe, target):  # type: (TreeRecipe, str) -> bool
        """
        还原：配方用到的某样原料 Y 能直接用 target 做出来（铁块 → 铁锭：铁块的配方用铁锭）。
        只看单候选的原料 —— 拆块、拆粒都是单候选；标签原料逐个去查太贵，也几乎不会是还原
        """
        cache_key = (recipe.Id, target)
        reverse = self.__Reverse.get(cache_key)
        if reverse is None:
            reverse = any(len(choices) == 1 and choices[0] != target and
                          any(other.Uses(target) for other in self.RecipesOf(choices[0]))
                          for choices, _ in recipe.Inputs)
            self.__Reverse[cache_key] = reverse
        return reverse

    def __Choose(self, node):  # type: (TreeNode) -> Candidate or None
        usable = [c for c in node.Candidates if not c.Stuck]
        if not usable:
            return None
        pool = usable
        selected = self.State.Types.get(node.Key)
        if selected is not None:
            typed = [c for c in usable if c.Recipe.Type == selected]
            if typed:
                pool = typed
        wanted = []
        if node.Depth == 0 and self.State.RootRecipe:
            wanted.append(self.State.RootRecipe)
        wanted.append(self.State.Choices.get(node.Key))
        wanted.append(self.Prefs.Default(node.Key))
        for recipe_id in wanted:
            if recipe_id is None:
                continue
            for candidate in pool:
                if candidate.Recipe.Id == recipe_id:
                    return candidate
        pinned = [c for c in pool if self.Provider.IsPinned(c.Recipe)]
        if pinned:
            return min(pinned, key=lambda c: c.Recipe.Order)
        return min(pool, key=lambda c: (c.Reverse, len(c.Recipe.Inputs), -c.Recipe.Output, c.Recipe.Order))

    def __Pick(self, choices, path):  # type: (tuple, frozenset) -> str
        """ 多候选的原料（标签）选哪个：本树选过的（不在路上）→ 第一个不在路上的 → 第一个 """
        if len(choices) == 1:
            return choices[0]
        picked = self.State.Picks.get(choice_sig(choices))
        if picked in choices and picked not in path:
            return picked
        for key in choices:
            if key not in path:
                return key
        return choices[0]


def choice_sig(choices):  # type: (tuple) -> str
    """ 一组候选的签名：本树的「换候选」按它记（同一个标签在树里哪儿出现都用同一个选择）"""
    return "|".join(choices)
