# coding=utf-8

# ----------------------------------------------------------------------
#  screens.py is part of MoreEnoughItems.
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
挂 MEI 的原版界面与它们的代理参数。
扩展装配时经 ctx.UI.Screens.Register 一个个登记，卸载时注销；纯数据，不碰引擎。参数的意思见 docs/extension_api.md §5.59：

- ContentPaths：原版界面里要被 MEI 避让的几块（相对原版根面板），第一项就是主内容；
- VisibleControlPath：配方页开着时藏起来的那一块，不写就是主内容；
- AllowChangeVisible：能不能藏它，不写就是能（docs/architecture/settings.md §6.2）
"""

SCREENS = {
    "crafting.crafting_screen": {  # 工作台
        "ContentPaths": [
            "/content_stack_panel/player_inventory",  # 背包栏
            "/content_stack_panel/toolbar_anchor/toolbar_panel/toolbar_background",  # 背包栏上方
            "/content_stack_panel/recipe_book",  # 配方栏
            "/content_stack_panel/recipe_book/tab_navigation_panel",  # 配方栏上方
            "/content_stack_panel/recipe_book/category_tab_left_arrow",  # 网易的切换分类页按钮左
            "/content_stack_panel/recipe_book/category_tab_right_arrow"  # 网易的切换分类页按钮右
        ],
        "VisibleControlPath": "/content_stack_panel",  # 配方页开着时整块藏起来（背包栏、配方栏连同上方的栏）
    },
    "cartography.cartography_screen": {  # 制图台
        "ContentPaths": ["/root_panel"]
    },
    "smithing_table.smithing_table_screen": {  # 锻造台
        "ContentPaths": ["/root_panel"]
    },
    "furnace.furnace_screen": {  # 熔炉
        "ContentPaths": ["/root_panel"]
    },
    "blast_furnace.blast_furnace_screen": {  # 高炉
        "ContentPaths": ["/root_panel"]
    },
    "smoker.smoker_screen": {  # 烟熏炉
        "ContentPaths": ["/root_panel"]
    },
    "enchanting.enchanting_screen": {  # 附魔台
        "ContentPaths": ["/root_panel"]
    },
    "chest.small_chest_screen": {  # 普通箱子
        "ContentPaths": ["/root_panel"]
    },
    "beacon.beacon_screen": {  # 信标
        "ContentPaths": ["/root_panel"]
    },
    "chest.barrel_screen": {  # 木桶
        "ContentPaths": ["/root_panel"]
    },
    "chest.ender_chest_screen": {  # 末影箱
        "ContentPaths": ["/root_panel"]
    },
    "redstone.hopper_screen": {  # 漏斗
        "ContentPaths": ["/root_panel"]
    },
    "redstone.dispenser_screen": {  # 发射器
        "ContentPaths": ["/root_panel"]
    },
    "redstone.crafter_screen": {  # 合成器
        "ContentPaths": ["/root_panel"]
    },
    "loom.loom_screen": {  # 织布机
        "ContentPaths": ["/screen_stack_panel"]
    },
    "redstone.dropper_screen": {  # 投掷器
        "ContentPaths": ["/root_panel"]
    },
    "stonecutter.stonecutter_screen": {  # 切石机
        "ContentPaths": ["/screen_stack_panel"]
    },
    "crafting.inventory_screen": {  # 玩家背包
        "ContentPaths": [  # 因为某些原因 这里选择拆出背包中的各个主要控件
            "/content_stack_panel/player_inventory",  # 背包栏
            # "/content_stack_panel/player_inventory/common_panel",  # 背包栏背景
            # "/content_stack_panel/player_inventory/inventory_panel_top_half",  # 背包栏物品上(盔甲 合成栏等)
            # "/content_stack_panel/player_inventory/inventory_panel_bottom_half",  # 背包栏物品中(背包物品)
            # "/content_stack_panel/player_inventory/hotbar_grid",  # 背包快捷栏
            "/content_stack_panel/toolbar_anchor/toolbar_panel/toolbar_background",  # 背包栏上方

            # "/content_stack_panel/center_fold/center_bg",  # 背包中间
            # "/content_stack_panel/survival_padding",  # 生存模式填充

            "/content_stack_panel/recipe_book",  # 配方栏
            # "/content_stack_panel/recipe_book/tab_content_panel"  # 配方内容(创造模式物品栏内容)
            # "/content_stack_panel/recipe_book/bg"  # 配方内容背景
            "/content_stack_panel/recipe_book/creative_hotbar_panel",   # 创造模式快捷栏
            "/content_stack_panel/recipe_book/tab_navigation_panel",  # 配方栏上方
            "/content_stack_panel/recipe_book/category_tab_left_arrow",  # 网易的切换分类页按钮左
            "/content_stack_panel/recipe_book/category_tab_right_arrow"  # 网易的切换分类页按钮右
        ],
        "VisibleControlPath": "/content_stack_panel",  # 同工作台
    },
    "anvil.anvil_screen": {  # 铁砧
        "ContentPaths": ["/root_panel"]
    },
    "grindstone.grindstone_screen": {  # 砂轮
        "ContentPaths": ["/root_panel"]
    },
    "brewing_stand.brewing_stand_screen": {  # 酿造台
        "ContentPaths": ["/root_panel"]
    },
    "chest.shulker_box_screen": {  # 潜影盒
        "ContentPaths": ["/root_panel"]
    },
    "chest.large_chest_screen": {  # 大箱子
        "ContentPaths": ["/root_panel"]
    }
}
