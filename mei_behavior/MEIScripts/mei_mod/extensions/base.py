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
"""
扩展基类，纯契约零引擎依赖。第三方经 MeiApi 组件的 GetExtensionCls() 取到它再继承。
"""


class MeiExtension(object):
    """ 所有扩展的基类，四个生命周期方法全部可选覆写 """

    ID = ""
    """ 唯一标识，必须带命名空间前缀，如 "yourmod:machines" """

    NAME = ""
    """ 显示名，走本地化键，不硬编码中文 """

    DESCRIPTION = ""

    AUTHOR = ""

    VERSION = "0.0.1"
    """ 扩展自身版本，StrictVersion 可解析格式 """

    MIN_API_VERSION = 1
    """ 要求的最低 MEI 扩展 API 版本，不满足则装配器拒绝加载 """

    # 生命周期，由 ExtensionLoader 按序驱动
# ======================================================================================================================
    def OnInit(self, ctx):
        """ 登记元数据类的东西：tag、比较器、序列化器 """
        # 这些是后续注册的前提，必须全部就位才能开始注册配方

    def OnRegister(self, ctx):
        """ 注册类别、配方来源、UI 脚本、自定义配方 """

    def OnReady(self, ctx):
        """ 全部扩展都注册完之后调用，做需要看得见别人的事 """
        # 跨扩展依赖只能放这里：往别人的类别里塞配方，必须等对方 OnRegister 结束

    def OnTick(self, ctx):
        """ 每帧调用，扩展要跑后台任务(分帧构建之类)挂这里 """
        # 框架只给节拍不定策略；默认空实现，绝大多数扩展用不上
        # 它在每帧路径上：不要在这里做没有预算控制的事

    def OnUnload(self, ctx):
        """ 反注册，供热重载与重进世界 """
        # OnRegister 注册的每一样都要能在这里撤掉，否则热重载会累积重复注册

    def __repr__(self):
        return "<MeiExtension {} v{}>".format(self.ID or "?", self.VERSION)
