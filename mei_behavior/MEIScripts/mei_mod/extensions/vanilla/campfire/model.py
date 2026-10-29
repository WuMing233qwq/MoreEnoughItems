# coding=utf-8

# ----------------------------------------------------------------------
#  model.py is part of MoreEnoughItems.
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
营火页中间那个点着的营火（营火不要合成条，用动态渲染的着火状态模型）：纸娃娃控件（netease_paper_doll_renderer）
渲染方块几何体模型（RenderBlockGeometryModel）。几何体模型要从方块调色板合（CombineBlockPaletteToGeometry），可没有「凭空造一个方块」的接口 ——
拿玩家脚下那一格做一个只有一格的调色板（GetBlockPaletteBetweenPos，不剔除空气），把那一格换成点着的营火（ReplaceBlockInBlockPalette），
再合成模型。全是客户端接口、不动世界；一局合一次，之后每一行的纸娃娃直接画（画不出来就重合一次再画）。
哪一步不成都退回营火的物品图标（记一行警告，同一局只记一次；隔 10 秒才再试）。
能调的都在这里：朝向、缩放（RENDER）；营火的附加值（LIT_AUX：朝南、没熄灭）
"""
import math
import time

import mod.client.extraClientApi as clientApi

from MEIScripts.api.facades.utils import error_text, logger

BLOCK = "minecraft:campfire"
LIT_AUX = 0
""" 营火的附加值：低两位是朝向，4 那一位是熄灭 —— 0 是朝南、点着的 """

GEOMETRY = "mei_campfire_lit"
""" 合出来的几何体模型名（同名会覆盖，所以 MEI 自己起一个）"""

RENDER = {"scale": 3.0, "init_rot_x": -75.0, "init_rot_y": 0.0, "init_rot_z": 45.0, }
""" 纸娃娃画模型的参数：缩放、绕 x / y 轴的初始朝向（度）—— 游戏里看着大小、角度不合适就改这里 """

RETRY_SECONDS = 10.0

_STATE = {"built": False, "retry_at": 0.0, "warned": False}


def _foot_block():  # type: () -> tuple
    x, y, z = clientApi.GetEngineCompFactory().CreatePos(clientApi.GetLocalPlayerId()).GetFootPos()
    return int(math.floor(x)), int(math.floor(y)), int(math.floor(z))


def build():  # type: () -> None
    """ 合一次「点着的营火」几何体模型；失败抛异常（说清楚卡在哪一步）"""
    level = clientApi.GetLevelId()
    factory = clientApi.GetEngineCompFactory()
    pos = _foot_block()
    palette = factory.CreateBlock(level).GetBlockPaletteBetweenPos(pos, pos, False)
    if palette is None:
        raise RuntimeError("拿不到 {} 的方块调色板".format(pos))
    block = factory.CreateBlockInfo(level).GetBlock(pos)
    name = block[0] if block else None
    if not name:
        raise RuntimeError("拿不到 {} 是什么方块".format(pos))
    if isinstance(name, unicode):  # noqa  递给引擎的字一律 str（引擎结论 §2）
        name = name.encode("utf-8")
    if not palette.ReplaceBlockInBlockPalette(BLOCK, LIT_AUX, name):
        raise RuntimeError("调色板里的 {} 换不成营火".format(name))
    if not factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette, GEOMETRY):
        raise RuntimeError("合不成几何体模型")


def _draw(doll):  # type: (any) -> bool
    params = dict(RENDER)
    params["block_geometry_model_name"] = GEOMETRY
    return bool(doll.RenderBlockGeometryModel(params))


def render(control):  # type: (any) -> bool
    """ 让这个纸娃娃画点着的营火；画上了给 True（画不出来的由调用方退回物品图标）"""
    if control is None or (not _STATE["built"] and time.time() < _STATE["retry_at"]):
        return False
    try:
        doll = control.asNeteasePaperDoll()
        if doll is None:
            return False
        if not _STATE["built"]:
            build()
            _STATE["built"] = True
        if _draw(doll):
            return True
        build()  # 模型可能跟着上一局没了（换了世界）：重合一次再画
        return _draw(doll)
    except Exception as e:  # noqa  画不出模型只退回图标，不能让配方行建不出来
        _STATE["built"] = False
        _STATE["retry_at"] = time.time() + RETRY_SECONDS
        if not _STATE["warned"]:
            _STATE["warned"] = True
            logger.warn("[MEI/campfire] 营火模型画不出来，改画物品图标: {}".format(error_text(e)))
        return False


def render_icon(control):  # type: (any) -> None
    """ 退回去画营火的物品图标 """
    if control is None:
        return
    try:
        renderer = control.asItemRenderer()
        if renderer is not None:
            renderer.SetUiItem(BLOCK, 0, False, None)
    except Exception as e:  # noqa
        logger.warn("[MEI/campfire] 营火图标也画不出来: {}".format(error_text(e)))
