# coding=utf-8
# ----------------------------------------------------------------------
#  share.py is part of MoreEnoughItems.
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
自制配方的多人共享（docs/architecture/user_recipes.md §22、§24）：服务端存大家共享出来的分组，客户端列出、上传、下载、删除，
操作员把分组设成「统一」（玩家强制下载、同 Id 替换本地的）。

- 存：存档附加数据，一个索引键（SHARED_KEY）加每个分组一个内容键（GROUP_KEY），值都是 ASCII 的 JSON 字符串（不往引擎的附加数据里塞嵌套的中文字节串）。
  索引 {"v": FORMAT, "groups": {服务器上的键: 摘要}, "removed": {键: 墓碑}}；摘要 {"owner_uid", "owner_name", "name", "desc", "rev", "digest",
  "unified", "unified_digest", "time", "size", "npages", "nrecipes"}；内容键里是下载用的那一整串（state/user_share.content_text）。
  内存里只留摘要，内容按需从附加数据读（读过的留着）—— 几十个大分组不会把它们解开的对象都压在服务端的内存里。
  内容也写在索引里的旧写法（2；更早只有分组那一层的 1）照样认，读到了拆成每个分组一个键。
  写盘合并：变了的分组的内容键、索引各写一次（SetExtraData 不自动保存），最后 SaveExtraData 一次；删了的 CleanExtraData。
- 服务器上的键是上传的客户端起的（每个存档各起一个，"s" + uuid）；第一次传上来时记下上传者（uid 与名字），以后只有上传者与操作员能改、删。
- 鉴权只认引擎给的发起者（HandlerContext.Trusted，和作弊模式一样，modes.md §3）；操作员 GetPlayerOperation() == 2。
  上传者：两边都有 uid 只比 uid，不然比名字（uid 在局域网、租赁服可能拿不到）。
- 删了的键留墓碑（上传者、版本号、是不是操作员撤下的）：别人不能拿同一个键重建（抢注了订阅者会悄悄跟到别人的内容上）；
  操作员撤下的连上传者也不能原样再传（不然上传者的客户端一看服务器上没了就自动重传，删不掉）；再建时版本号接着墓碑往下数。
- 统一绑着内容：操作员统一时记下当时的内容指纹，之后上传者（不是操作员）改了内容，统一就不再生效（摘要里 unified 为假、review 为真），
  等操作员看过再统一；操作员自己传的照样统一。
- 列表、上传、下载都分块（每块 CHUNK 个字）：一次事件能带多大没查到官方的数，分组多了、大了一次事件里的字也不涨。
  列表有版本号，变了只广播版本号，客户端再分块来问。上传按顺序一块一块来（每次上传带一个会话号 sid，旧会话晚到的块不打断新的），
  最后一块到了才拼起来、照本地的规矩规整、查上限、版本加一、记下内容指纹。
- 每个玩家一个令牌桶限流（问列表、传、下载每块花 1，删、统一花 2），两次传完之间至少隔 COMMIT_INTERVAL；没传完的上传每人至多 MAX_PLAYER_SLOTS 个、
  全服至多 MAX_SLOTS 个、合起来至多 MAX_PENDING 个字，过期的每帧清（Tick）。存档、广播合并：一改当场做，接着改的攒到间隔到了再做一次。
- 上限：MAX_GROUPS 个分组、一个分组 MAX_GROUP_SIZE 个字、合起来 MAX_TOTAL_SIZE；每个上传者 MAX_OWNER_GROUPS 个、MAX_OWNER_SIZE 个字（操作员不算）；
  一个分组的页面、配方数照 user_share.MAX_SHARED_PAGES / MAX_SHARED_RECIPES（实机量过再调）。
服务端接口一律在用到时才 import：本模块客户端也要 import（拿请求名与上限）
"""
import json
import time

from MEIScripts.utils.log import logger
from MEIScripts.utils.stablehash import stable_digest
from MEIScripts.utils.text import error_text, native_str, to_native

from ..base import Handler
from .cheat import is_operator

REQUEST_SHARE_LIST = "mei:share_list"
"""
问服务器上的分组（分块）。请求 {"part": 第几块}；回 {"version": 列表的版本, "part", "parts", "data": 摘要列表（JSON）的这一块,
"op": 自己是不是操作员, "mine": [自己传的分组的键]（只在第 0 块）}
"""

REQUEST_SHARE_UPLOAD = "mei:share_upload"
"""
传一个分组（分块）。请求 {"key", "sid": 这一次上传的会话号, "part": 第几块, "parts": 一共几块, "data": 这一块的字}；
回 {"ok": bool, "error": 原因, "done": 拼齐了没有, "rev": 拼齐后的版本, "digest": 存下的那一份的内容指纹}
"""

REQUEST_SHARE_DOWNLOAD = "mei:share_download"
""" 下载一个分组的第几块。请求 {"key", "part"}；回 {"ok", "error", "rev", "digest", "unified", "owner": 上传者的名字, "part", "parts", "data"} """

REQUEST_SHARE_DELETE = "mei:share_delete"
""" 从服务器上删一个分组（上传者、操作员）。请求 {"key"}；回 {"ok", "error"} """

REQUEST_SHARE_UNIFY = "mei:share_unify"
""" 设「统一」（只有操作员）。请求 {"key", "on"}；回 {"ok", "error"} """

PUSH_EVENT = "MeiShareChanged"
""" 服务端 → 全部客户端：服务器上的分组变了。{"version": 列表的版本}（客户端再分块问列表；摘要见 summary，不带上传者是谁）"""

SHARED_KEY = "mei_shared_groups"
""" 存档附加数据：索引 """

GROUP_KEY = "mei_shared_group_{}"
""" 存档附加数据：一个分组的内容（{} 是服务器上的键）"""

FORMAT = 3
""" 索引的格式（2：内容也在索引里；1：只有分组那一层）"""

CHUNK = 8000
MAX_GROUPS = 128
MAX_GROUP_SIZE = 1024 * 1024
MAX_TOTAL_SIZE = 16 * 1024 * 1024
MAX_OWNER_GROUPS = 16
MAX_OWNER_SIZE = 2 * 1024 * 1024
MAX_PARTS = MAX_GROUP_SIZE // CHUNK + 2
UPLOAD_TTL = 60.0
""" 一次分块上传最后一块之后这么久没来下一块就作废 """
MAX_PLAYER_SLOTS = 2
MAX_SLOTS = 64
MAX_PENDING = 8 * 1024 * 1024
""" 没传完的上传合起来最多占多少字（开头按 块数 × CHUNK 预留）"""
MAX_REMOVED = 1024
""" 墓碑最多记这么多（多了丢最早的）"""
SAVE_INTERVAL = 2.0
PUSH_INTERVAL = 1.0
SWEEP_INTERVAL = 5.0
COMMIT_INTERVAL = 2.0
BUCKET = (400.0, 80.0)
""" 每个玩家的令牌桶：容量、每秒补多少（一个 1 MB 的分组约 133 块，传、下载一次用不完一桶）"""
COSTS = {"list": 1, "upload": 1, "download": 1, "delete": 2, "unify": 2}
KEY_LENGTH = 64

ERR_TRUST, ERR_BAD, ERR_OWNER, ERR_FULL, ERR_SIZE, ERR_TOTAL, ERR_EMPTY, ERR_ORDER, ERR_GONE, ERR_OP = (
    "trust", "bad", "owner", "full", "size", "total", "empty", "order", "gone", "op")
ERR_RATE, ERR_REMOVED, ERR_QUOTA, ERR_MANY = "rate", "removed", "quota", "many"
""" 失败的原因：发起者不是引擎给的、请求不成形、不是上传者（也不是操作员）、分组满了、太大、服务器上放不下了、一个页面都没有、
分块乱了序（重新传）、服务器上没有这个分组、不是操作员；请求太频繁、被操作员撤下了、自己共享的太多了、页面或配方太多 """

META_KEYS = ("owner_uid", "owner_name", "name", "desc", "rev", "digest", "unified", "unified_digest", "time", "size",
             "npages", "nrecipes")
""" 索引里一个分组记的（内容在它自己的键里）"""


def effective_unified(entry):  # type: (dict) -> bool
    """ 统一生效：操作员统一过，而且内容还是统一时的那一份 """
    return bool(entry.get("unified")) and bool(entry.get("digest")) and entry.get("unified_digest") == entry.get("digest")


def summary(key, entry):  # type: (str, dict) -> dict
    """ 列表里的一行：不带上传者的 uid，只带名字。unified 是生效的统一；review：统一过、内容又变了，等操作员再看 """
    unified = effective_unified(entry)
    return {"key": key, "name": entry.get("name") or "", "desc": entry.get("desc") or "",
            "owner_name": entry.get("owner_name") or "", "rev": entry.get("rev", 0), "digest": entry.get("digest") or "",
            "unified": unified, "review": bool(entry.get("unified")) and not unified,
            "size": entry.get("size", 0), "pages": entry.get("npages", 0), "recipes": entry.get("nrecipes", 0)}


def _int(value):  # type: (any) -> int or None
    """ 事件里的整数（引擎可能给成浮点）：整的给 int，别的给 None """
    if isinstance(value, bool) or not isinstance(value, (int, long, float)) or value != value or abs(value) > 1e9 \
            or value != int(value):
        return None
    return int(value)


def _uid(value):  # type: (any) -> int
    """ 网易账号的 uid：正整数，别的给 0 """
    if isinstance(value, bool) or not isinstance(value, (int, long)) or value <= 0:
        return 0
    return int(value)


def valid_key(value):  # type: (any) -> str or None
    if not isinstance(value, basestring) or not value or len(value) > KEY_LENGTH:
        return None
    try:
        value = value.encode("ascii") if isinstance(value, unicode) else value.decode("ascii").encode("ascii")
    except UnicodeError:
        return None
    return value if all(ch.isalnum() or ch in "_-" for ch in value) else None


def player_identity(player_id):  # type: (str) -> tuple
    """ (uid, 名字)：网易账号的 uid 拿不到给 0 """
    import mod.server.extraServerApi as serverApi
    factory = serverApi.GetEngineCompFactory()
    name = ""
    try:
        name = native_str(factory.CreateName(player_id).GetName() or "")
    except Exception:  # noqa
        name = ""
    uid = 0
    try:
        getter = getattr(factory.CreateHttp(serverApi.GetLevelId()), "GetPlayerUid", None)
        uid = getter(player_id) if callable(getter) else 0
    except Exception:  # noqa
        uid = 0
    return _uid(uid), name


def same_owner(identity, record):  # type: (tuple, dict) -> bool
    """ 发起者是不是这条记录（分组、墓碑）的上传者：两边都有 uid 只比 uid，不然比名字 """
    uid, name = identity
    if uid and record.get("owner_uid"):
        return uid == record.get("owner_uid")
    return bool(name) and name == record.get("owner_name")


def _migrate_owner(entry):  # type: (dict) -> None
    """ 旧写法的上传者 "uid:N" / "name:X" 拆成 owner_uid / owner_name """
    owner = entry.pop("owner", None)
    if isinstance(owner, basestring) and "owner_uid" not in entry:
        kind, _sep, value = owner.partition(":")
        entry["owner_uid"] = _uid(int(value)) if kind == "uid" and value.isdigit() else 0
        if kind == "name" and not entry.get("owner_name"):
            entry["owner_name"] = value
    entry["owner_uid"] = _uid(entry.get("owner_uid"))
    entry["owner_name"] = native_str(entry.get("owner_name") or "")


def _meta(entry):  # type: (dict) -> dict
    """ 索引里的一条：只留 META_KEYS，数都规整成整数 """
    meta = dict((key, entry.get(key)) for key in META_KEYS)
    for key in ("rev", "size", "npages", "nrecipes"):
        meta[key] = max(0, _int(meta.get(key)) or 0)
    meta["time"] = meta.get("time") if isinstance(meta.get("time"), (int, long, float)) else 0
    meta["unified"] = bool(meta.get("unified"))
    for key in ("name", "desc", "digest", "unified_digest"):
        meta[key] = native_str(meta.get(key) or "")
    return meta


def _split(entry):  # type: (dict) -> tuple
    """ 旧写法（内容在索引里）的一个分组 → (摘要, 内容那一串)；有指纹就留着（拿下来的人手里是它）"""
    from MEIScripts.mei_mod.state.user_share import content_text  # 纯逻辑，用到才 import
    text = content_text(entry)
    meta = _meta(entry)
    meta["size"] = len(text)
    meta["npages"] = len(entry.get("pages") or ())
    meta["nrecipes"] = len(entry.get("recipes") or ())
    if not meta["digest"]:
        meta["digest"] = stable_digest(text)
    return meta, text


class ShareService(object):
    """ 服务端侧的共享服务。挂在服务端 MainSys 上（Channel.RegisterAll 扫出处理器；每帧 Tick、退出时 Flush）"""

    def __init__(self, system=None):
        self.System = system  # type: any  # 服务端 MainSys：广播用它的 BroadcastToAllClient
        self.Groups = None  # type: dict or None  # 读进来的 {键: 摘要}
        self.Removed = {}  # type: dict  # 键 -> 墓碑 {"owner_uid", "owner_name", "op", "rev", "time"}
        self.Texts = {}  # type: dict  # 键 -> 内容那一串（从附加数据读过的、刚传上来的）
        self.DirtyKeys = set()  # type: set  # 内容要写（还在）或要清（删了）的键
        self.Uploads = {}  # type: dict  # (玩家, 键) -> {"sid", "parts", "chunks": [], "time"}
        self.Buckets = {}  # type: dict  # 玩家 -> [令牌, 上次补的时间]
        self.LastCommit = {}  # type: dict  # 玩家 -> 上次传完的时间
        self.ListVersion = 1  # type: int  # 列表的版本：分组变了就加一
        self.ListText = None  # type: str or None  # 摘要列表的 JSON（版本变了重算）
        self.Dirty = False
        self.PushPending = False
        self.LastSave = self.LastPush = self.LastSweep = -1e9
        self.Clock = time.time
        self.Identity = player_identity
        self.IsOperator = is_operator
        # 限流与上限（测试换掉）
        self.Bucket = BUCKET
        self.CommitInterval = COMMIT_INTERVAL

    # 存
# ======================================================================================================================
    @staticmethod
    def _comp():
        import mod.server.extraServerApi as serverApi
        return serverApi.GetEngineCompFactory().CreateExtraData(serverApi.GetLevelId())

    def Read(self, name):  # type: (str) -> any
        """ 存档附加数据里的一个键（测试替换）"""
        return self._comp().GetExtraData(name)

    def Write(self, name, value):  # type: (str, str) -> bool
        """ 写一个键，先不保存（批量写完 Commit 一次）"""
        comp = self._comp()
        try:
            return bool(comp.SetExtraData(name, value, False))
        except TypeError:  # 没有 autoSave 参数的版本：写一次存一次
            return bool(comp.SetExtraData(name, value))

    def Clean(self, name):  # type: (str) -> bool
        return bool(self._comp().CleanExtraData(name))

    def Commit(self):  # type: () -> bool
        save = getattr(self._comp(), "SaveExtraData", None)
        return bool(save()) if callable(save) else True

    def Broadcast(self, payload):  # type: (dict) -> None
        if self.System is not None:
            self.System.BroadcastToAllClient(PUSH_EVENT, payload)

    def _groups(self):  # type: () -> dict
        if self.Groups is None:
            self.Groups, self.Removed = {}, {}
            try:
                raw = self.Read(SHARED_KEY)
                data = to_native(json.loads(raw)) if isinstance(raw, basestring) and raw else {}
                data = data if isinstance(data, dict) else {}
                if data.get("v") in (2, FORMAT):
                    groups, removed = data.get("groups"), data.get("removed")
                else:
                    groups, removed = data, {}  # 旧写法：只有分组那一层
                for key, entry in (groups.items() if isinstance(groups, dict) else ()):
                    if not valid_key(key) or not isinstance(entry, dict):
                        continue
                    _migrate_owner(entry)
                    if "pages" in entry or "recipes" in entry:  # 内容还在索引里：拆到它自己的键里（下一次存档时写）
                        entry, text = _split(entry)
                        self.Texts[key] = text
                        self.DirtyKeys.add(key)
                        self.Dirty = True
                    self.Groups[key] = _meta(entry)
                for key, tomb in (removed.items() if isinstance(removed, dict) else ()):
                    if valid_key(key) and isinstance(tomb, dict) and key not in self.Groups:
                        _migrate_owner(tomb)
                        self.Removed[key] = tomb
            except Exception as e:  # noqa  读不懂就从空的开始（数据可以丢，加载不能卡）
                logger.error("[MEI/share] 读不懂存档里的共享分组，从空的开始: {}".format(error_text(e)))
                self.Groups, self.Removed = {}, {}
                self.Texts.clear()
                self.DirtyKeys.clear()
                self.Dirty = False
        return self.Groups

    def _text(self, key):  # type: (str) -> str or None
        """ 一个分组的内容那一串：读过的直接给，没读过的从附加数据读 """
        text = self.Texts.get(key)
        if text is None and key in self._groups():
            try:
                raw = self.Read(GROUP_KEY.format(key))
            except Exception as e:  # noqa
                logger.error("[MEI/share] 读共享分组 {} 的内容失败: {}".format(key, error_text(e)))
                raw = None
            if isinstance(raw, basestring) and raw:
                text = native_str(raw)
                self.Texts[key] = text
        return text

    def _save(self):
        self.Dirty = False
        self.LastSave = self.Clock()
        try:
            written = True
            for key in sorted(self.DirtyKeys):
                if key in self._groups():
                    text = self.Texts.get(key)
                    if text is not None:
                        written = self.Write(GROUP_KEY.format(key), text) and written
                else:
                    self.Clean(GROUP_KEY.format(key))  # 删了的：没有这个键也不算失败
            self.DirtyKeys.clear()
            # 不排序：sort_keys 让 json 走纯 Python 的编码器
            index = json.dumps({"v": FORMAT, "groups": self.Groups, "removed": self.Removed}, separators=(",", ":"))
            written = self.Write(SHARED_KEY, index) and written
            if not (self.Commit() and written):
                logger.error("[MEI/share] 共享分组没完整存进存档")
        except Exception as e:  # noqa
            logger.error("[MEI/share] 共享分组存进存档失败: {}".format(error_text(e)))

    def _push(self):
        self.PushPending = False
        self.LastPush = self.Clock()
        try:
            self.Broadcast({"version": self.ListVersion})
        except Exception as e:  # noqa
            logger.error("[MEI/share] 广播共享分组的变化失败: {}".format(error_text(e)))

    def _changed(self, key=None, content=False):
        """ 改了：content 为真时这个分组的内容键要写（还在）或要清（删了）；列表的版本加一；存档、广播隔得够久就当场做，不然攒到 Tick """
        if key is not None and content:
            self.DirtyKeys.add(key)
        self.ListVersion += 1
        self.ListText = None
        self.Dirty = self.PushPending = True
        now = self.Clock()
        if now - self.LastSave >= SAVE_INTERVAL:
            self._save()
        if now - self.LastPush >= PUSH_INTERVAL:
            self._push()

    def Tick(self):
        """ 每帧（服务端 MainSys.Update）：攒着的存档、广播到点了就做；隔一会儿清一次过期的上传、闲着的令牌桶 """
        now = self.Clock()
        if self.Dirty and now - self.LastSave >= SAVE_INTERVAL:
            self._save()
        if self.PushPending and now - self.LastPush >= PUSH_INTERVAL:
            self._push()
        if now - self.LastSweep >= SWEEP_INTERVAL:
            self.LastSweep = now
            for slot in [slot for slot, upload in self.Uploads.items() if now - upload["time"] > UPLOAD_TTL]:
                del self.Uploads[slot]
            capacity = self.Bucket[0]
            for player in [p for p, b in self.Buckets.items() if b[0] + (now - b[1]) * self.Bucket[1] >= capacity]:
                del self.Buckets[player]
            for player in [p for p, t in self.LastCommit.items() if now - t > self.CommitInterval]:
                del self.LastCommit[player]

    def Flush(self):
        """ 退出时（服务端 MainSys.Destroy）：攒着的存档写下去 """
        if self.Dirty or self.DirtyKeys:
            self._save()

    def Summaries(self):  # type: () -> list
        groups = self._groups()
        return [summary(key, groups[key]) for key in sorted(groups, key=lambda k: groups[k].get("time", 0))]

    def _list_text(self):  # type: () -> str
        if self.ListText is None:
            self.ListText = json.dumps(self.Summaries(), separators=(",", ":"))
        return self.ListText

    # 鉴权与限流
# ======================================================================================================================
    @staticmethod
    def _trusted(ctx):  # type: (any) -> bool
        return bool(getattr(ctx, "Trusted", False)) and bool(getattr(ctx, "PlayerId", None))

    def _allow(self, player, kind):  # type: (str, str) -> bool
        """ 令牌桶：够花就扣、给 True """
        now = self.Clock()
        capacity, refill = self.Bucket
        bucket = self.Buckets.get(player)
        if bucket is None:
            bucket = self.Buckets[player] = [capacity, now]
        tokens = min(capacity, bucket[0] + max(0.0, now - bucket[1]) * refill)
        bucket[1] = now
        cost = COSTS.get(kind, 1)
        if tokens < cost:
            bucket[0] = tokens
            return False
        bucket[0] = tokens - cost
        return True

    def _owned(self, identity, exclude=None):  # type: (tuple, str) -> tuple
        """ 这个上传者现在有几个分组、合起来多大（不算 exclude 那个键）"""
        count, size = 0, 0
        for key, entry in self._groups().items():
            if key != exclude and same_owner(identity, entry):
                count += 1
                size += entry.get("size", 0)
        return count, size

    def _bury(self, key, entry, by_op):  # type: (str, dict, bool) -> None
        """ 删了的键留墓碑；多了丢最早的 """
        self.Removed[key] = {"owner_uid": entry.get("owner_uid") or 0, "owner_name": entry.get("owner_name") or "",
                             "op": bool(by_op), "rev": entry.get("rev", 0), "time": self.Clock()}
        while len(self.Removed) > MAX_REMOVED:
            del self.Removed[min(self.Removed, key=lambda k: self.Removed[k].get("time", 0))]

    def _drop(self, key, by_op):  # type: (str, bool) -> None
        """ 从服务器上撤掉一个分组：摘要、内容都去掉，留墓碑，内容键下次存档时清 """
        entry = self._groups().pop(key)
        self.Texts.pop(key, None)
        self._bury(key, entry, by_op)
        self._changed(key, content=True)

    # 请求
# ======================================================================================================================
    @Handler(REQUEST_SHARE_LIST)
    def OnList(self, ctx, body):  # type: (any, dict) -> dict
        if not self._trusted(ctx):
            return {"ok": False, "error": ERR_TRUST}  # 不给空列表：客户端会当成服务器上什么都没了
        if not self._allow(ctx.PlayerId, "list"):
            return {"ok": False, "error": ERR_RATE}
        body = body if isinstance(body, dict) else {}
        part = _int(body.get("part")) if body.get("part") is not None else 0
        text = self._list_text()
        parts = max(1, (len(text) + CHUNK - 1) // CHUNK)
        if part is None or not 0 <= part < parts:
            return {"ok": False, "error": ERR_BAD}
        mine = []
        if part == 0:
            identity = self.Identity(ctx.PlayerId)
            mine = [key for key, entry in self._groups().items() if same_owner(identity, entry)]
        return {"version": self.ListVersion, "part": part, "parts": parts, "data": text[part * CHUNK:(part + 1) * CHUNK],
                "op": bool(self.IsOperator(ctx.PlayerId)), "mine": mine}

    @Handler(REQUEST_SHARE_UPLOAD)
    def OnUpload(self, ctx, body):  # type: (any, dict) -> dict
        if not self._trusted(ctx):
            return {"ok": False, "error": ERR_TRUST}
        body = body if isinstance(body, dict) else {}
        key, sid = valid_key(body.get("key")), valid_key(body.get("sid")) or ""
        part, parts, data = _int(body.get("part")), _int(body.get("parts")), body.get("data")
        if key is None or part is None or parts is None or not isinstance(data, basestring) \
                or not 0 < parts <= MAX_PARTS or not 0 <= part < parts or len(data) > CHUNK:
            return {"ok": False, "error": ERR_BAD}
        player = ctx.PlayerId
        if not self._allow(player, "upload"):
            return {"ok": False, "error": ERR_RATE}
        now = self.Clock()
        slot = (player, key)
        if part == 0:
            refused = self._Admit(ctx, key)
            if refused:
                return {"ok": False, "error": refused}
            if now - self.LastCommit.get(player, -1e9) < self.CommitInterval:
                return {"ok": False, "error": ERR_RATE}
            mine = sorted((s for s in self.Uploads if s[0] == player and s != slot), key=lambda s: self.Uploads[s]["time"])
            while len(mine) >= MAX_PLAYER_SLOTS:
                del self.Uploads[mine.pop(0)]  # 一个人同时没传完的至多这么几个：挤掉最早的
            if slot not in self.Uploads and len(self.Uploads) >= MAX_SLOTS:
                return {"ok": False, "error": ERR_RATE}
            pending = sum(upload["parts"] for s, upload in self.Uploads.items() if s != slot) * CHUNK
            if pending + parts * CHUNK > MAX_PENDING:
                return {"ok": False, "error": ERR_RATE}  # 全服在传的字太多了：过一会儿再来
            self.Uploads[slot] = {"sid": sid, "parts": parts, "chunks": [], "time": now}
        upload = self.Uploads.get(slot)
        if upload is None or upload["sid"] != sid:
            return {"ok": False, "error": ERR_ORDER}  # 不是这一次的（旧会话晚到的块）：不动正在传的
        if upload["parts"] != parts or len(upload["chunks"]) != part:
            del self.Uploads[slot]
            return {"ok": False, "error": ERR_ORDER}
        upload["chunks"].append(native_str(data))
        upload["time"] = now
        if part + 1 < parts:
            return {"ok": True, "done": False}
        del self.Uploads[slot]
        refused = self._Admit(ctx, key)  # 传的工夫里分组可能被删、被别人建了
        if refused:
            return {"ok": False, "error": refused}
        return self._Store(ctx, key, "".join(upload["chunks"]))

    def _Admit(self, ctx, key):  # type: (any, str) -> str or None
        """ 这个人能不能往这个键上传：给不行的原因，行给 None """
        identity = self.Identity(ctx.PlayerId)
        entry = self._groups().get(key)
        if entry is not None:
            if same_owner(identity, entry) or self.IsOperator(ctx.PlayerId):
                return None
            return ERR_OWNER
        tomb = self.Removed.get(key)
        op = self.IsOperator(ctx.PlayerId)
        if tomb is not None and not op:
            if not same_owner(identity, tomb):
                return ERR_OWNER  # 删了的键别人不能拿去重建
            if tomb.get("op"):
                return ERR_REMOVED  # 操作员撤下的，上传者也不能原样再传
        if len(self._groups()) >= MAX_GROUPS:
            return ERR_FULL
        if not op and self._owned(identity)[0] >= MAX_OWNER_GROUPS:
            return ERR_QUOTA
        return None

    def _Store(self, ctx, key, content):  # type: (any, str, str) -> dict
        """
        拼齐了：照本地的规矩规整、查上限、记下（版本加一）、广播。内容只编码一次（不排序的 C 编码器），指纹就是它的 stable_digest
        """
        from MEIScripts.mei_mod.state.user_share import (  # 规整用客户端那一套（纯逻辑），用到才 import
            MAX_SHARED_PAGES, MAX_SHARED_RECIPES, content_text, normalize_sub)
        try:
            data = json.loads(content)
        except Exception:  # noqa  坏的、嵌套太深的
            return {"ok": False, "error": ERR_BAD}
        if not isinstance(data, dict):
            return {"ok": False, "error": ERR_BAD}
        pages, recipes = data.get("pages"), data.get("recipes")
        if (isinstance(pages, list) and len(pages) > MAX_SHARED_PAGES) or (
                isinstance(recipes, list) and len(recipes) > MAX_SHARED_RECIPES):
            return {"ok": False, "error": ERR_MANY}
        sub = normalize_sub({"key": key, "name": data.get("name"), "desc": data.get("desc"), "pages": pages, "recipes": recipes})
        if sub is None or not sub["pages"]:
            return {"ok": False, "error": ERR_EMPTY}
        text = content_text(sub)
        size = len(text)
        if size > MAX_GROUP_SIZE:
            return {"ok": False, "error": ERR_SIZE}
        identity = self.Identity(ctx.PlayerId)
        op = bool(self.IsOperator(ctx.PlayerId))
        if not op and self._owned(identity, exclude=key)[1] + size > MAX_OWNER_SIZE:
            return {"ok": False, "error": ERR_QUOTA}
        others = sum(value.get("size", 0) for k, value in self._groups().items() if k != key)
        if others + size > MAX_TOTAL_SIZE:
            return {"ok": False, "error": ERR_TOTAL}
        old = self._groups().get(key)
        tomb = self.Removed.get(key)
        base = old or {"owner_uid": identity[0], "owner_name": native_str(identity[1]), "unified": False, "unified_digest": "",
                       "time": self.Clock(), "rev": (tomb or {}).get("rev", 0)}
        digest = stable_digest(text)
        entry = _meta({"owner_uid": base.get("owner_uid") or 0, "owner_name": base.get("owner_name") or "",
                       "name": sub["name"], "desc": sub["desc"], "rev": base.get("rev", 0) + 1, "digest": digest,
                       "unified": bool(base.get("unified")), "unified_digest": base.get("unified_digest") or "",
                       "time": base.get("time"), "size": size, "npages": len(sub["pages"]), "nrecipes": len(sub["recipes"])})
        if op and entry["unified"]:
            entry["unified_digest"] = digest  # 操作员自己传的：统一着的照样统一
        self._groups()[key] = entry
        self.Texts[key] = text
        self.Removed.pop(key, None)
        self.LastCommit[ctx.PlayerId] = self.Clock()
        self._changed(key, content=True)
        logger.info("[MEI/share] {} 共享了分组 {}（版本 {}，{} 个页面、{} 条配方、{} 字）".format(
            entry["owner_name"] or ctx.PlayerId, key, entry["rev"], entry["npages"], entry["nrecipes"], size))
        return {"ok": True, "done": True, "rev": entry["rev"], "digest": digest}

    @Handler(REQUEST_SHARE_DOWNLOAD)
    def OnDownload(self, ctx, body):  # type: (any, dict) -> dict
        if not self._trusted(ctx):
            return {"ok": False, "error": ERR_TRUST}
        if not self._allow(ctx.PlayerId, "download"):
            return {"ok": False, "error": ERR_RATE}
        body = body if isinstance(body, dict) else {}
        key, part = valid_key(body.get("key")), _int(body.get("part"))
        entry = self._groups().get(key) if key else None
        if entry is None:
            return {"ok": False, "error": ERR_GONE}
        text = self._text(key)
        if not text:
            logger.error("[MEI/share] 共享分组 {} 的内容在存档里找不到了，撤下它".format(key))
            self._drop(key, by_op=False)
            return {"ok": False, "error": ERR_GONE}
        parts = max(1, (len(text) + CHUNK - 1) // CHUNK)
        if part is None or not 0 <= part < parts:
            return {"ok": False, "error": ERR_BAD}
        return {"ok": True, "rev": entry.get("rev"), "digest": entry.get("digest") or "", "unified": effective_unified(entry),
                "owner": entry.get("owner_name") or "", "part": part, "parts": parts,
                "data": text[part * CHUNK:(part + 1) * CHUNK]}

    @Handler(REQUEST_SHARE_DELETE)
    def OnDelete(self, ctx, body):  # type: (any, dict) -> dict
        if not self._trusted(ctx):
            return {"ok": False, "error": ERR_TRUST}
        if not self._allow(ctx.PlayerId, "delete"):
            return {"ok": False, "error": ERR_RATE}
        key = valid_key((body or {}).get("key") if isinstance(body, dict) else None)
        entry = self._groups().get(key) if key else None
        if entry is None:
            return {"ok": True}  # 已经没有了：删的目的达到了
        owner = same_owner(self.Identity(ctx.PlayerId), entry)
        if not owner and not self.IsOperator(ctx.PlayerId):
            return {"ok": False, "error": ERR_OWNER}
        self._drop(key, by_op=not owner)
        return {"ok": True}

    @Handler(REQUEST_SHARE_UNIFY)
    def OnUnify(self, ctx, body):  # type: (any, dict) -> dict
        if not self._trusted(ctx):
            return {"ok": False, "error": ERR_TRUST}
        if not self._allow(ctx.PlayerId, "unify"):
            return {"ok": False, "error": ERR_RATE}
        if not self.IsOperator(ctx.PlayerId):
            return {"ok": False, "error": ERR_OP}
        body = body if isinstance(body, dict) else {}
        key = valid_key(body.get("key"))
        entry = self._groups().get(key) if key else None
        if entry is None:
            return {"ok": False, "error": ERR_GONE}
        on = body.get("on") is True
        approved = entry.get("digest") if on else ""
        if bool(entry.get("unified")) != on or entry.get("unified_digest") != approved:
            entry["unified"] = on
            entry["unified_digest"] = approved  # 统一的是此刻这一份内容；之后上传者改了要再统一一次
            self._changed(key)
        return {"ok": True}
