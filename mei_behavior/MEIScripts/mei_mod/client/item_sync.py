# coding=utf-8

# ----------------------------------------------------------------------
#  item_sync.py is part of MoreEnoughItems.
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
进存档时物品表什么时候建（CLAUDE.md 引擎结论 §51）。

服务端发来的物品列表（SyncLoadedItems）总在客户端重新加载资源包的半路到：那时本地化文字可能还没加载好，
GetItemBasicInfo 给的物品名是键名 —— 而名字在注册时读一次就记在 Item 上（Item.Info），这一局就一直是键名，
搜索、按名称排序全跟着错。所以收到列表先记下，文字加载好了再建：

1. MEI 自己 .lang 里的键查得到（pack_ready）：这个存档的资源包文字都在了（模组的物品名在这一层），马上建 ——
   多半还在加载画面里，建表那一下卡顿玩家看不见；
2. 查不到（资源包还在加载，或者当前语言没有 MEI 的翻译）就等界面初始化（UiInitFinished 总在资源加载完之后），
   那时原版的键查得到（ready）就建；还查不到，最多再等 WAIT 秒照建、记一行警告。

不直接等 UiInitFinished：它来的时候游戏界面已经出来了，建表那一下（一秒上下）就成了进世界后的卡顿。
纯逻辑：建表、两个探针、时钟都是注入的，离线能测（probe_item_sync.py）。
"""


class ItemSync(object):
    """ 客户端主系统一份：Receive 收列表、OnUiReady 记界面好了、Poll 每帧问一次；齐了调 build(items, hidden_items) 建表 """

    WAIT = 3.0
    """ 界面好了、原版的键还查不到时最多再等几秒 """

    def __init__(self, build, pack_ready, ready, clock, warn=None):  # type: (any, any, any, any, any) -> None
        self.Build = build
        self.PackReady = pack_ready  # () -> bool：MEI 自己 .lang 里的键查得到了没有
        self.Ready = ready  # () -> bool：原版的键查得到了没有
        self.Clock = clock  # () -> 秒
        self.Warn = warn  # (str) -> None
        self.Pending = None  # type: tuple or None  # 收到、还没建的 (可见 id 表, 隐藏 id 表)
        self.UiReady = False  # type: bool
        self.Since = None  # type: float or None  # 界面好了、原版的键第一次没查到的时刻

    def Receive(self, items, hidden_items):  # type: (list, list) -> bool
        """ 收下服务端的列表（再收到一次就换成新的）；文字已经加载好就当场建，返回建了没有 """
        self.Pending = (list(items or ()), list(hidden_items or ()))
        self.Since = None
        return self.Poll()

    def OnUiReady(self):  # type: () -> bool
        """ UiInitFinished：换维度时还会再来，那时没有等着建的列表，什么都不做 """
        self.UiReady = True
        return self.Poll()

    def Poll(self):  # type: () -> bool
        """ 每帧问一次：有等着建的列表、文字加载好了（或界面好了且已等够 WAIT 秒）就建，返回建了没有 """
        if self.Pending is None:
            return False
        if not self.PackReady():
            if not self.UiReady:
                return False
            if not self.Ready():
                now = self.Clock()
                if self.Since is None:
                    self.Since = now
                if now - self.Since < self.WAIT:
                    return False
                if self.Warn is not None:
                    self.Warn("[MEI/items] 界面初始化好了，本地化等了 {:.0f} 秒还查不到，照样建物品表（物品名可能是键名）".format(
                        self.WAIT))
        items, hidden_items = self.Pending
        # 先清再建：建表抛了也不会每帧再来一遍
        self.Pending = None
        self.Since = None
        self.Build(items, hidden_items)
        return True
