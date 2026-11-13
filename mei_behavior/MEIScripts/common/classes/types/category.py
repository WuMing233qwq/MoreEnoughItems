# coding=utf-8
# ----------------------------------------------------------------------
#  category.py is part of MoreEnoughItems.
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

PREVIEW_AUTO = "auto"
""" preview_def 的缺省值：按 control_def 的命名空间推出 "<namespace>.PREVIEW"（配方 JSON 规范，tooltip.md §4） """

PREVIEW_DEF_NAME = "PREVIEW"


def icon_texture(icon):  # type: (any) -> str or None
    """ 类型图标是贴图路径（字符串，如 "textures/ui/xxx"）就给它（utf-8 的 str）；是物品（元组）、没有给 None """
    if isinstance(icon, unicode):
        return icon.encode("utf-8") or None
    if isinstance(icon, basestring):
        return icon or None
    return None


def icon_item(icon):  # type: (any) -> tuple or None
    """ 类型图标是物品（(ItemId, AuxValue) 元组 / 列表）就给 (id, aux)；是贴图路径、没有给 None """
    if not isinstance(icon, (tuple, list)) or not icon or not isinstance(icon[0], basestring):
        return None
    aux = icon[1] if len(icon) > 1 and isinstance(icon[1], (int, long)) and not isinstance(icon[1], bool) else 0
    return icon[0], aux


def derive_preview_def(control_def):  # type: (str) -> str
    """ "MeiCraftingTable.RECIPES_GRID" -> "MeiCraftingTable.PREVIEW"；不是 namespace.name 形式的给空串 """
    if not control_def or "." not in control_def:
        return ""
    return control_def.split(".", 1)[0] + "." + PREVIEW_DEF_NAME


class RecipeCategory(object):
    """
    配方类型的唯一载体，收编原先散在五处的字符串

    Id         str              类型标识, 同时是 Recipe.Type 的值
    NameKey    str              显示名的本地化键
    Icon       tuple / str      tab 图标：物品 (ItemId, AuxValue)，或者一张贴图的路径（"textures/ui/xxx"，不带扩展名）——
                                贴图画在 TypeTab 与配方树的工作方块格上；物品与贴图分别用 IconItem / IconTexture 读
    ControlDef str              配方页控件定义名, JSON UI 的 namespace.control_name
    PreviewDef str              tooltip 配方预览的 grid 定义名，缺省按 ControlDef 的命名空间推出；空串 = 不出预览
    Stations   List[ItemStack]  工作站展示物, 查用途时按它反查类型(只读属性)
    SortIndex  int              tab 排序权重, 越小越靠前
    PageHost   RecipePageHost   托管配方页：这个类型的配方页内容区整块交给它画（没有 MEI 的配方行，见 page_host.py）；None 是 MEI 自己画

    `Stations` 只收 ItemStack —— 只给 id 的简易写法请走
    `ItemFactory.GetStacksFromIds()`，那是注册面的事，不该由本类去认识 ItemFactory。
    """

    __slots__ = ("Id", "NameKey", "Icon", "ControlDef", "PreviewDef", "SortIndex", "_stations",
                 "Transfer", "PageHost")

    def __init__(
            self,
            category_id,
            name_key="",
            icon=None,
            control_def="",
            stations=None,
            sort_index=0,
            preview_def=PREVIEW_AUTO,
            page_host=None
    ):  # type: (str, str, tuple, str, list, int, str, any) -> None
        if not category_id:
            raise ValueError("category_id cannot be empty")
        self.Id = category_id  # type: str
        self.NameKey = name_key or category_id  # type: str
        self.Icon = icon  # type: tuple or str or None
        self.ControlDef = control_def  # type: str
        self.PageHost = page_host  # type: any
        """
        托管配方页（RecipePageHost，page_host.py）：配方页内容区里建它的容器、一页放几条和怎么画都问它；配方页脚本（RegisterScript）不用登记。
        这种类型没有配方行，tooltip 不出配方预览（preview_def 缺省时就是空），配方树不用它的配方
        """
        if preview_def == PREVIEW_AUTO:
            preview_def = "" if page_host is not None else derive_preview_def(control_def)
        self.PreviewDef = preview_def or ""  # type: str
        """
        配方预览（tooltip 里只显示配方行的 content 那一块）用的 grid 定义名，形如 "MeiCraftingTable.PREVIEW"。
        **缺省就有**：按 ControlDef 的命名空间推出，类型 JSON 里照规范写一行
        `"PREVIEW@mei_recipe_common.preview_grid": {"$recipe_ui_template": "<命名空间>.recipe"}` 就行，不碰尺寸。
        配方行不适合放进 tooltip 的，显式写 preview_def=None 不出预览。见 docs/architecture/tooltip.md §4
        """
        self.SortIndex = sort_index  # type: int

        self.Transfer = None  # type: any
        """
        转移策略（TransferPolicy），决定本类型能不能快捷合成、材料放到哪个槽位（MEI 自己往玩家侧的合成格里放）。

        None 表示**不支持转移**，plus 按钮对这个类型一律不亮（当前界面登记了转移处理器的除外，ctx.UI.Transfers）。
        原版扩展在装配时 SetTransferPolicy 挂上，见 quick_craft.md §5.5b。第三方的机器用 ctx.UI.Transfers 的转移处理器。
        """

        self._stations = []  # type: list
        """
        [(owner, ItemStack)]，按加入顺序。

        owner 是**登记者的扩展 ID**，空串表示「类别自带」。分主的理由只有一个:
        第三方把自己的机器挂成工作站之后，它 OnUnload 时得撤干净，
        而撤的人不能顺手把类别自带的那些也撤了。
        """
        self.AddStations(stations)

    @property
    def IconItem(self):  # type: () -> tuple or None
        """ 图标是物品时的 (ItemId, AuxValue)；是贴图、没声明给 None """
        return icon_item(self.Icon)

    @property
    def IconTexture(self):  # type: () -> str or None
        """ 图标是贴图时的路径；是物品、没声明给 None """
        return icon_texture(self.Icon)

    # 工作站 —— 可动态增删, 多方块结构预览这类要按状态换图标
# ======================================================================================================================
    @property
    def Stations(self):  # type: () -> list
        """ 工作站 ItemStack 表，UI 直接拿去用的成品 """
        return [stack for _owner, stack in self._stations]

    def AddStation(self, stack, owner=""):  # type: (any, str) -> bool
        """ 追加一个工作站，已有同一物品则不动 """
        if not stack or stack.is_empty() or self.__Find(stack) is not None:
            return False
        self._stations.append((owner, stack))
        return True

    def AddStations(self, stacks, owner=""):  # type: (any, str) -> int
        return len([s for s in (stacks or ()) if self.AddStation(s, owner=owner)])

    def RemoveStation(self, stack):  # type: (any) -> bool
        index = self.__Find(stack)
        if index is None:
            return False
        del self._stations[index]
        return True

    def RemoveStationsByOwner(self, owner):  # type: (str) -> int
        """ 撤掉某个扩展加的全部工作站，供它 OnUnload 用 """
        # 空 owner 是类别自带的, 不给撤 —— 那等于把类别的工作站清空
        if not owner:
            return 0
        before = len(self._stations)
        self._stations = [entry for entry in self._stations if entry[0] != owner]
        return before - len(self._stations)

    def SetStations(self, stacks, owner=""):  # type: (any, str) -> int
        """ 整体替换；动态改工作站(按结构状态换图标)走这里 """
        self._stations = []
        return self.AddStations(stacks, owner=owner)

    # 转移策略
# ======================================================================================================================
    def SetTransferPolicy(self, policy):  # type: (any) -> None
        """ 挂上转移策略；传 None 表示撤掉（本类型不再支持快捷合成）。给 MEI 自己的原版合成格用，第三方用 ctx.UI.Transfers """
        self.Transfer = policy

    def CanTransfer(self, ctx):  # type: (any) -> bool
        """ 当前环境下这个类型能不能转移。没挂策略一律不能 """
        if self.Transfer is None:
            return False
        return bool(self.Transfer.CanTransfer(ctx))

    def __Find(self, stack):  # noqa
        """ 按物品身份找已登记的下标，没有返回 None """
        key = stack.get_key()
        for index, entry in enumerate(self._stations):
            if entry[1].get_key() == key:
                return index
        return None

    def __eq__(self, other):
        return isinstance(other, RecipeCategory) and self.Id == other.Id

    def __hash__(self):
        # 身份只看 Id：同一个类型被替换实现时仍是同一个 tab
        return hash(self.Id)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<RecipeCategory {}>".format(self.Id)
