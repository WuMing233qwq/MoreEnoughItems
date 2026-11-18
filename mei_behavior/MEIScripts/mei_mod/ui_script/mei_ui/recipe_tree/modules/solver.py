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

防无限递归（docs/design/recipe_tree.html「解算与防递归」；按配方排，不按物品排）：
1. 路径排除（候选级，不是节点级）：同一条配方在一条路上只用一次 —— 上面用过的这一格不能再用，那才是无限递归。
   用到路上已有物品的候选是「绕回」：那样物品还有一条没用过、原料不碰路上任何物品的配方（出口）才能用，排在不绕回的后面；
   于是一样物品在一条路上最多出现两次，第二次那一格只用不碰路上物品的配方（直接出环；本树选的类型不套在它上面）。
   候选全都用不了才把这一格当原料（CYCLIC）。多候选的原料（标签）先挑不在路上的候选，全在路上时挑有出口的。
   **强制展开**（玩家点了「展开递归」，按物品记在 TreeState.Force）：这样物品的红格照样挑一条配方展开一层 ——
   绕回出不来的那几样原料当原料（红格，Loop：要再展开就对那样物品再点一次），别的原料照常展开；
   同一样物品在一条路上只强制展开一次（ForcedKeys），几样物品互相绕也停得下来；本树选的类型在这一格只有递归配方时，
   展开递归的物品照这个类型强制展开（没点过的照旧退回别的类型）
2. 还原识别：做 X 的候选 R 用到 Y，而 Y 两步之内能用 X 做出来 —— R 是「还原」（铁块 → 铁锭、拆涂蜡的铜块 → 铜锭），
   有别的候选时默认不选
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
""" 物品表里认不出的条目（provider.IsItem 为假，查不了配方）：当原料。流体登记成了隐藏物品，不算这一类、照常展开 """

MAX_DEPTH = 256
""" 深度上限（16、64 都嫌低，256 的开销也没那么大） """
MAX_NODES = 20000
""" 节点上限（400、2000 都不够用：毕业级的配方整棵展开上万格。画布只给视口附近的格子建控件，格子再多也不多建）"""
REVERSE_STEPS = 2
""" 还原识别往下看几步配方：1 只认两步的环（铁块 ⇄ 铁锭），2 还认三步的（铜锭 → 涂蜡的铜块 → 铜块 → 铜锭）"""


class TreeRecipe(object):
    """
    解算用的配方，由 provider 从 MEI 的 Recipe 改造出来：
    Id、类型 Type、原料 Inputs = [(候选物品键的元组, 数量), ...]（同样的原料已合并、顺序固定）、
    单次产出 Output（做出这一格的物品几个）、工具 Tools（催化剂：不消耗、不展开）、原配方 Source（预览、查看配方页用）、
    排序键 Order（类型顺序、注册顺序）、
    其他产出 Byproducts = ((物品键, 单次几个, 概率), ...)：这条配方除了这一格的物品还出的东西（不画在树上，汇总的「副产物」算它）
    """
    __slots__ = ("Id", "Type", "Inputs", "Output", "Tools", "Source", "Order", "Byproducts", "Keys")

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
        self.Keys = frozenset(key for choices, _ in self.Inputs for key in choices)  # 原料的全部候选：判绕回的快路

    def Uses(self, key):  # type: (str) -> bool
        return key in self.Keys

    def __repr__(self):
        return "TreeRecipe({!r})".format(self.Id)


class Candidate(object):
    """
    一格的一条候选配方：在这一格用不用得了（Stuck 是让它用不了的那几样原料：在上面用过这条配方、或者绕回去出不来）、
    会不会绕回（Loops：用到路上已有的物品，但那样物品出得了环，照样能用）、是不是还原
    """
    __slots__ = ("Recipe", "Stuck", "Reverse", "Loops")

    def __init__(self, recipe, stuck=(), reverse=False, loops=False):
        self.Recipe = recipe  # type: TreeRecipe
        self.Stuck = tuple(stuck)  # type: tuple
        self.Reverse = reverse  # type: bool
        self.Loops = loops  # type: bool

    @property
    def Cyclic(self):  # type: () -> bool
        return bool(self.Stuck)


class TreeNode(object):
    """
    树上的一格。Key 是物品键（provider 给的），Choices 是这一格的原料有哪几个候选（标签；根是它自己），
    Sig 是从根往下的路径签名（重算后 Id 会变，折叠、菜单靠它找回同一格），Path 是从根到这一格的物品键集合；
    Used 是上面各格用了的配方 Id，Repeat 是这样物品在上面已经出现过（这一格是它第二次出现），Twice 是路上出现了两次的物品；
    Loop 是强制展开的那一格里绕回出不来的原料（不按常规展开），Forced 是这一格是强制展开的，ForcedKeys 是从根到这一格强制展开过的物品
    """
    __slots__ = ("Id", "Key", "Choices", "Need", "Depth", "Parent", "Slot", "Children", "Sig", "Path", "State",
                 "Recipe", "Candidates", "Crafts", "Surplus", "Type", "Used", "Repeat", "Twice", "Loop", "Forced",
                 "ForcedKeys")

    def __init__(self, node_id, key, need, depth=0, parent=None, slot=0, choices=None, sig="r", path=frozenset(),
                 used=frozenset(), twice=frozenset(), forced=frozenset()):
        self.Id = node_id  # type: int
        self.Key = key  # type: str
        self.Choices = tuple(choices) if choices else (key,)  # type: tuple
        self.Need = int(need)  # type: int
        self.Depth = depth  # type: int
        self.Parent = parent  # type: int or None
        self.Slot = slot  # type: int  # 在父格配方的原料里排第几
        self.Children = []  # type: list  # 子格的 Id，和配方原料同一个顺序
        self.Sig = sig  # type: str
        self.Repeat = key in path  # type: bool
        self.Path = path | frozenset((key,))  # type: frozenset
        self.Used = used  # type: frozenset
        self.Twice = twice | frozenset((key,)) if self.Repeat else twice  # type: frozenset
        self.State = STATE_PENDING  # type: str
        self.Recipe = None  # type: TreeRecipe or None
        self.Candidates = []  # type: list  # 全部候选（各类型），和 provider 给的同一个顺序
        self.Crafts = 0  # type: int
        self.Surplus = 0  # type: int
        self.Type = None  # type: str or None  # 当前类型（选中的那条配方的类型）
        self.Loop = False  # type: bool
        self.Forced = False  # type: bool
        self.ForcedKeys = forced  # type: frozenset

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
        self.__Reach = {}  # type: dict  # (物品键, 目标物品键, 几步) -> 几步之内能不能用目标做出来
        self.__BySig = {}  # type: dict  # 路径签名 -> 节点（菜单、折叠按签名找，上万格时不能一格格比）
        self.__Depth = 0  # type: int  # 到过的最深一层
        self.__Add(TreeNode(0, state.Root, state.Qty))

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
        return self.__BySig.get(sig)

    def MaxDepthReached(self):  # type: () -> int
        return self.__Depth

    def __Add(self, node):  # type: (TreeNode) -> None
        self.Nodes.append(node)
        self.__BySig[node.Sig] = node
        if node.Depth > self.__Depth:
            self.__Depth = node.Depth
        self.__Queue.append(node)

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
        node.Candidates = []
        for recipe in recipes:
            stuck, loops = self.__Judge(recipe, node)
            node.Candidates.append(Candidate(recipe, stuck, loops=loops))
        if len(node.Candidates) > 1:
            for candidate in node.Candidates:
                candidate.Reverse = self.__IsReverse(candidate.Recipe, key)
        if node.Loop:
            # 强制展开那一格里绕回出不来的原料：不按常规挑（照常挑会成这样物品在路上第三次展开）；候选都算绕回，菜单里灰着
            for candidate in node.Candidates:
                if not candidate.Stuck:
                    candidate.Stuck = (key,)
            chosen = None
        else:
            chosen = self.__Choose(node)
        blocked = ()
        if chosen is None:
            if not self.__CanForce(node):
                node.State = STATE_CYCLIC
                return
            chosen, blocked = self.__Force(node)
            node.Forced = True
        recipe = chosen.Recipe
        node.State = STATE_OK
        node.Recipe = recipe
        node.Type = recipe.Type
        node.Crafts = int(math.ceil(node.Need / float(recipe.Output)))
        node.Surplus = node.Crafts * recipe.Output - node.Need
        used = node.Used | frozenset((recipe.Id,))
        forced = node.ForcedKeys | frozenset((key,)) if node.Forced else node.ForcedKeys
        for slot, (choices, count) in enumerate(recipe.Inputs):
            child_key = self.__Pick(choices, node.Path, lambda key: self.__CanExit(key, node, recipe))
            child = TreeNode(len(self.Nodes), child_key, node.Crafts * count, node.Depth + 1, node.Id, slot, choices,
                             "{}/{}:{}".format(node.Sig, slot, child_key), node.Path, used, node.Twice, forced)
            child.Loop = slot in blocked
            node.Children.append(child.Id)
            self.__Add(child)

    def __CanForce(self, node):  # type: (TreeNode) -> bool
        """ 这样物品点了展开递归，而且这条路上还没强制展开过它（一条路只许一次）"""
        return node.Key in self.State.Force and node.Key not in node.ForcedKeys

    def __Force(self, node):  # type: (TreeNode) -> tuple
        """
        强制展开一层：在全部候选里挑一条，给 (候选, 绕回出不来的那几样原料的下标)。
        挑法：根配方 / 本树选的 / 首选照认（在当前类型里）；不然上面没用过的、绕回出不来的原料少的先，再照常的启发
        """
        pool = node.Candidates
        selected = None if node.Repeat else self.State.Types.get(node.Key)
        if selected is not None:
            pool = [c for c in pool if c.Recipe.Type == selected] or pool
        wanted = [self.State.RootRecipe] if node.Depth == 0 and self.State.RootRecipe else []
        wanted += [self.State.Choices.get(node.Key), self.Prefs.Default(node.Key)]
        for recipe_id in wanted:
            for candidate in pool:
                if recipe_id is not None and candidate.Recipe.Id == recipe_id:
                    return candidate, self.__Blocked(candidate.Recipe, node)
        best = min(pool, key=lambda c: (c.Recipe.Id in node.Used, len(self.__Blocked(c.Recipe, node)), c.Reverse,
                                        len(c.Recipe.Inputs), -c.Recipe.Output, c.Recipe.Order))
        return best, self.__Blocked(best.Recipe, node)

    def __Blocked(self, recipe, node):  # type: (TreeRecipe, TreeNode) -> tuple
        """
        强制展开时这条配方的哪几样原料（下标）当原料、不往下展开：这条配方在上面用过的，用到路上物品的那几样；
        不然全部候选都在路上、又出不了环的那几样（第二次出现的那一格、Loop 的那一格，在路上的都算出不了环）
        """
        blocked = []
        for slot, (choices, _) in enumerate(recipe.Inputs):
            on_path = [key in node.Path for key in choices]
            if recipe.Id in node.Used:
                if any(on_path):
                    blocked.append(slot)
            elif all(on_path) and (node.Repeat or not any(self.__CanExit(key, node, recipe) for key in choices)):
                blocked.append(slot)
        return tuple(blocked)

    def __Judge(self, recipe, node):  # type: (TreeRecipe, TreeNode) -> tuple
        """
        这条候选在这一格：(Stuck, Loops)。原料一样都不在路上的（绝大多数）直接给空。
        用不了（Stuck 给出卡住的原料）：上面已经用过这条配方（无限递归）；第二次出现的那一格还要绕回；绕回的那样物品出不了环
        """
        path = node.Path
        if path.isdisjoint(recipe.Keys):
            return (), False
        if recipe.Id in node.Used:
            return tuple(next(key for key in choices if key in path) for choices, _ in recipe.Inputs
                         if any(key in path for key in choices)), False
        looping = [choices for choices, _ in recipe.Inputs if all(key in path for key in choices)]
        if not looping:
            return (), False
        if node.Repeat:
            return tuple(choices[0] for choices in looping), True
        return tuple(choices[0] for choices in looping
                     if not any(self.__CanExit(key, node, recipe) for key in choices)), True

    def __CanExit(self, key, node, recipe):  # type: (str, TreeNode, TreeRecipe) -> bool
        """
        这一格用 recipe 时，原料 key（路上已有的物品）能不能出环：key 在路上只出现过一次，
        还有一条没用过、原料不碰路上任何物品的配方（下一格是它第二次出现，只能用这样的配方）；当原料、不再展开的本来就不往下展开
        """
        if key in node.Twice:
            return False
        if self.Prefs.IsRaw(key) or key in self.State.Stop or not self.Provider.IsItem(key):
            return True
        for other in self.RecipesOf(key):
            if other.Id in node.Used or other.Id == recipe.Id:
                continue
            if all(any(choice not in node.Path for choice in choices) for choices, _ in other.Inputs):
                return True
        return False

    def __IsReverse(self, recipe, target):  # type: (TreeRecipe, str) -> bool
        """
        还原：配方用到的某样原料 Y 在 REVERSE_STEPS 步配方之内能用 target 做出来
        （铁块 → 铁锭：铁块的配方用铁锭；拆涂蜡的铜块 → 铜锭：涂蜡的铜块用铜块，铜块用铜锭）。
        只看单候选的原料 —— 拆块、拆粒都是单候选；标签原料逐个去查太贵，也几乎不会是还原
        """
        cache_key = (recipe.Id, target)
        reverse = self.__Reverse.get(cache_key)
        if reverse is None:
            reverse = any(len(choices) == 1 and choices[0] != target and self.__Reaches(choices[0], target, REVERSE_STEPS)
                          for choices, _ in recipe.Inputs)
            self.__Reverse[cache_key] = reverse
        return reverse

    def __Reaches(self, key, target, steps):  # type: (str, str, int) -> bool
        """ key 的某条配方用到 target，或者（还能往下看时）某条配方的某样单候选原料 steps - 1 步之内用到 target """
        cache_key = (key, target, steps)
        reach = self.__Reach.get(cache_key)
        if reach is None:
            reach = any(other.Uses(target) or steps > 1 and any(
                len(choices) == 1 and choices[0] not in (key, target) and self.__Reaches(choices[0], target, steps - 1)
                for choices, _ in other.Inputs) for other in self.RecipesOf(key))
            self.__Reach[cache_key] = reach
        return reach

    def __Choose(self, node):  # type: (TreeNode) -> Candidate or None
        usable = [c for c in node.Candidates if not c.Stuck]
        if not usable:
            return None
        pool = usable
        # 第二次出现的那一格是出环用的：类型不硬套（那是给第一次出现选的，套上可能只剩还原）。
        # 本树、全局选的照样认 —— 菜单里点得动的「用这条」在这一格都要落得下来
        selected = None if node.Repeat else self.State.Types.get(node.Key)
        if selected is not None:
            typed = [c for c in usable if c.Recipe.Type == selected]
            if typed:
                pool = typed
            elif self.__CanForce(node) and any(c.Recipe.Type == selected for c in node.Candidates):
                # 选的类型在这一格只有递归配方，这样物品又点了展开递归：不退回别的类型，照这个类型强制展开（__Force 按类型筛）
                return None
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
        # 没人选过：不绕回的先挑（绕回的只在别无选择时用）
        calm = [c for c in pool if not c.Loops] or pool
        pinned = [c for c in calm if self.Provider.IsPinned(c.Recipe)]
        if pinned:
            return min(pinned, key=lambda c: c.Recipe.Order)
        return min(calm, key=lambda c: (c.Reverse, len(c.Recipe.Inputs), -c.Recipe.Output, c.Recipe.Order))

    def __Pick(self, choices, path, can_exit=None):  # type: (tuple, frozenset, callable) -> str
        """
        多候选的原料（标签）选哪个：本树选过的（不在路上）→ 第一个不在路上的；
        全在路上（这条配方是绕回、出得了环才选上的）：本树选过的能出环就用它 → 第一个能出环的 → 第一个
        """
        if len(choices) == 1:
            return choices[0]
        picked = self.State.Picks.get(choice_sig(choices))
        if picked in choices and picked not in path:
            return picked
        for key in choices:
            if key not in path:
                return key
        if can_exit is not None:
            if picked in choices and can_exit(picked):
                return picked
            for key in choices:
                if can_exit(key):
                    return key
        return choices[0]


def choice_sig(choices):  # type: (tuple) -> str
    """ 一组候选的签名：本树的「换候选」按它记（同一个标签在树里哪儿出现都用同一个选择）"""
    return "|".join(choices)
