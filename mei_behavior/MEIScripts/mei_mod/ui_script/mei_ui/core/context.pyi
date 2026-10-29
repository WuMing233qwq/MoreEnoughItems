# ----------------------------------------------------------------------
#  context.pyi is part of MoreEnoughItems.
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
from MEIScripts.mei_mod.ui_script.mei_ui.core.node import UIMainNode


def SetMainNode(node: UIMainNode):...

def GetMainNode() -> UIMainNode:...

def ClearMainNode(node: UIMainNode):...

class Using(object):
    Node: UIMainNode
    def __init__(self, node: UIMainNode):...
    def __enter__(self) -> UIMainNode:...
    def __exit__(self, *_exc) -> bool:...
