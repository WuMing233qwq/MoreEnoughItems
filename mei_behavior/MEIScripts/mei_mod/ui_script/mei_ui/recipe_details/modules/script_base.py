# coding=utf-8
# ----------------------------------------------------------------------
#  script_base.py is part of MoreEnoughItems.
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
配方页脚本的**实现层** —— 契约层在 common/classes/base.py 的 BaseRecipeUIScript.

为什么要分两层:
  registry/recipes.py 的 RegisterScript 需要 issubclass 守卫, 因而必须能 import
  契约类; 若契约类自己 import 了 context / RecipeBinder, registry 的 import 链
  就会带起整个 UI 栈 —— 索引层将无法在无 UI 环境下建立与测试.
  ⇒ 契约留在 common(纯), 绑定器耦合的部分下沉到这里.

新增配方类型的界面时, 继承本类 (而不是 BaseRecipeUIScript).
"""
from MEIScripts.common.classes.base import BaseRecipeUIScript
from MEIScripts.mei_mod.ui_script.mei_ui import context
from MEIScripts.mei_mod.ui_script.mei_ui.recipe_details.modules.binding import RecipeBinder


class RecipeUIScript(BaseRecipeUIScript):
    """ 绑定器耦合的配方页脚本基类 """

    ACTIONS = None
    """
    本配方类型启用哪些**内置**动作按钮(收藏/置顶/转移/配方树)，元组形式，
    值取 recipe_details/actions.py 里的前缀常量。None 表示不限制、全部启用。

    只管内置的那四个 —— 自己加的按钮不受它约束，那是你自己的按钮。
    未启用的仍会注册绑定(JSON 里那个 toggle 少一条绑定会报错)，只是永不渲染。
    """

    def __init__(self, recipe):
        BaseRecipeUIScript.__init__(self, recipe)
        self.MainNode = context.GetMainNode()
        self.ScreenNode = self.MainNode.ScreenNode

    def AddBindingGroup(self, binding_name_prefix_list, item_panel_callback):
        """ 添加一个新绑定组 """
        return self.RecipesGridBind.AddGroup(
            collection_index=self.GridItemIndex,
            prefix_list=binding_name_prefix_list,
            item_panel_callback=item_panel_callback,
            cache_enabled=True
        )

    def RemoveBindingGroup(self, group_id):
        """ 移除绑定组 """
        return self.RecipesGridBind.RemoveGroup(
            self.GridItemIndex,
            group_id
        )

    def InitBindings(self):
        """按装饰器规则自动初始化绑定。"""
        if self._BindingsInited:
            return
        RecipeBinder.InitBindings(self)
        self._BindingsInited = True

    def DestroyBindings(self):
        """销毁由装饰器生成的绑定并重置状态。"""
        self.RecipesGridBind.RemoveGroupByIndex(self.GridItemIndex)
        RecipeBinder.DestroyBindings(self)
        self._BindingsInited = False
