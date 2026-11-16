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
自制配方多人共享的客户端这一边（docs/architecture/user_recipes.md §22、§24；服务端在 network/protocol/share.py）：

- 进存档（OnWorldJoined，UiInitFinished）才开始干活：问一次列表；退出存档（OnWorldLeft）就停 —— 进存档之前收到的广播、每帧都不处理
  （那时按存档存的那份还是上一个存档的）。每次进存档、换维度都换一个代号（Generation）：在路上的请求回来时代号对不上就不认。
- 列表分块问（服务器上的分组多了一次事件里也就 CHUNK 个字），带版本号；服务器广播只说「列表变到第几版了」（OnPush），比手上的新才再问。
  问到了对一遍拿下来的（Reconcile）：订阅的内容指纹和服务器上的不一样就自动再下载（比指纹不比版本号）、
  服务器上没了标「已下架」留着；操作员统一生效的（设置「启用强制覆盖」开着）没订阅也自动下载，统一不生效了又没订阅的删掉。
  统一只认内容和服务器说统一生效时的那一份一样：拿下来的还是旧内容时不当统一的登记。
- 下载排队、上传也排队，各一次只一个（服务器按人限流、每人只留几个没传完的上传）；一块被限流、超时了，隔一会儿从这一块接着来（RESUMES 次），
  还不行才算这一趟失败（下载放回队头，上传隔一会儿从头再传）。
- 本地分组开了「共享」：存储一改（每帧只看版本号），这一包的指纹和这个存档里传过的不一样就排一次上传，UPLOAD_DELAY 秒内又改了往后推（防抖）；
  每次上传带一个会话号（sid）。服务器上的键每个存档各起一个（UserShareManager.KeyFor）。
  关了共享、删了分组：从服务器上撤掉（只撤这个存档里传过的）。服务器上丢了自己传过的、或者那份和自己传上去的不一样了（回档、被清）：忘掉指纹、重传。
  被操作员撤下（removed）：关掉本地的共享、丢掉这个键（再共享是新的一个）、记下给管理器看。
  服务器丢了这一次没传完的（order：被挤掉、过期）：隔一会儿从头再传。别的失败（太大、满了……）内容不变不自动重试，改了才再试。
- 自己共享出去的分组（这个存档里起过的、传过的键，加上服务器列表里说是自己的）不订阅、统一了也不下载：本地的就是源头。
拿下来的分组存在 UserShareManager（按存档）；user 扩展照它登记（extensions/user/plan.py）。构造期不碰引擎
"""
import json
import time
import uuid

from MEIScripts.constants.texts import ManagerText
from MEIScripts.mei_mod.network.base import KEY_BODY, KEY_ERROR, KEY_OK
from MEIScripts.mei_mod.network.protocol.share import (
    CHUNK, ERR_ORDER, ERR_RATE, ERR_REMOVED, MAX_PARTS, REQUEST_SHARE_DELETE, REQUEST_SHARE_DOWNLOAD, REQUEST_SHARE_LIST,
    REQUEST_SHARE_UNIFY, REQUEST_SHARE_UPLOAD, valid_key)
from MEIScripts.mei_mod.state.user_recipes import DEFAULT_GROUP, UserRecipeManager
from MEIScripts.mei_mod.state.user_share import UserShareManager, valid_digest
from MEIScripts.utils.log import logger
from MEIScripts.utils.stablehash import stable_digest
from MEIScripts.utils.text import error_text, native_str, to_native

UPLOAD_DELAY = 2.0
""" 改了以后隔这么久才传（这段时间里又改了就往后推）"""

LIST_RETRY = 30.0
""" 列表没问到（服务器没回）：隔这么久再问一次 """

RETRY_DELAY = 5.0
RETRY_MAX = 60.0
""" 被限流、超时：隔这么久再试（接连失败的话一次比一次久，最多 RETRY_MAX）"""

RETRYABLE = (ERR_RATE, "timeout")

RESUMES = 6
""" 传、下载、问列表时一块被限流或超时：从这一块接着来，接连这么多次还不行才算这一趟失败 """

LIST_PARTS = 64
LIST_ROWS = 1024
""" 列表最多问几块、认几行（服务器上的分组远没有这么多）"""

PENDING, UPLOADING, DONE, FAILED = "pending", "uploading", "done", "failed"
""" 本地分组的上传状态 """


def new_share_key():  # type: () -> str
    return "s" + uuid.uuid4().hex


def new_sid():  # type: () -> str
    return uuid.uuid4().hex[:12]


def normalize_summary(entry):  # type: (any) -> dict or None
    """ 服务器给的一行摘要（列表）：认不出的给 None """
    if not isinstance(entry, dict):
        return None
    key = valid_key(entry.get("key"))
    if key is None:
        return None
    result = {"key": key}
    for name in ("name", "desc", "owner_name"):
        value = entry.get(name)
        result[name] = native_str(value) if isinstance(value, basestring) else ""
    for name in ("rev", "size", "pages", "recipes"):
        value = entry.get(name)
        result[name] = int(value) if isinstance(value, (int, long, float)) and not isinstance(value, bool) \
            and value == value and abs(value) < 1e12 else 0
    result["digest"] = valid_digest(entry.get("digest"))
    result["unified"] = entry.get("unified") is True
    result["review"] = entry.get("review") is True
    return result


def outdated(server, sub):  # type: (dict, dict) -> bool
    """ 拿下来的这一份和服务器上的不是同一份：比内容指纹（服务器没给指纹才退回比版本号）"""
    if server["digest"]:
        return server["digest"] != sub.get("digest")
    return server["rev"] != sub.get("rev")


def group_label(group):  # type: (dict) -> unicode
    """ 传上去的分组名：默认分组写「默认」"""
    if group["id"] == DEFAULT_GROUP:
        return ManagerText.DefaultName
    return group.get("name") or ManagerText.Unnamed


def _count(value):  # type: (any) -> int
    """ 回执里的「一共几块」：正整数，认不出给 1 """
    if isinstance(value, bool) or not isinstance(value, (int, long, float)) or value != value or value < 1 or value > 1e6:
        return 1
    return int(value)


def _version(value):  # type: (any) -> int or None
    """ 列表的版本号：整数，认不出给 None """
    if isinstance(value, bool) or not isinstance(value, (int, long, float)) or value != value or abs(value) > 1e15:
        return None
    return int(value)


class __ShareClient(object):  # noqa

    def __init__(self):
        self.Channel = None  # type: any  # 测试注入；None 时用客户端 MainSys 上的
        self.Clock = time.time
        self._revision = 0
        self.Generation = 0
        self.Joined = False  # type: bool  # 进了存档（UiInitFinished）、还没退出
        self.Removed = {}  # type: dict  # 本地分组 Id -> True：被操作员从服务器撤下了（这一局记着给管理器看）
        self.Reset()

    def Reset(self):
        """ 进存档、换维度、退出存档：从头来；在路上的请求回来了也不认（代号变了）"""
        self.Generation += 1
        self.Servers = []  # type: list  # 服务器上的分组（摘要），按共享的先后
        self.ServerMine = set()  # type: set  # 服务器列表里说是自己传的键
        self.Listed = False  # type: bool  # 这个存档里拿到过列表没有
        self.ListVersion = None  # 手上这份列表的版本
        self.PushedVersion = None  # 服务器广播说列表到了第几版
        self.ListStale = False  # type: bool  # 手上的列表旧了，没在问的时候再问
        self.Asking = False  # type: bool
        self.Failed = False  # type: bool  # 上一次问列表没问到（超时、出错）
        self.IsOp = False  # type: bool  # 自己是不是操作员（问列表时服务器说的）
        self.Status = {}  # type: dict  # 本地分组 Id -> (状态, 附带：版本或原因)
        self.Due = {}  # type: dict  # 本地分组 Id -> 什么时候传
        self.Scheduled = {}  # type: dict  # 本地分组 Id -> 排上的那一版的指纹
        self.Attempts = {}  # type: dict  # 本地分组 Id -> 接连被限流 / 超时几次
        self.Busy = {}  # type: dict  # 服务器上的键 -> "up" / "down" / "del" / "unify"
        self.UploadingKey = None  # 正在传的那个服务器上的键（一次只传一个）
        self.Downloads = {}  # type: dict  # 服务器上的键 -> {"subscribe", "unified", "callbacks"}：正在下的
        self.Pending = []  # type: list  # 排着下的 [{"key", "subscribe", "unified", "callbacks"}]
        self.QueueAt = 0.0  # type: float  # 下载被限流了：什么时候再下
        self.Later = []  # type: list  # [(什么时候, 代号, 回调)]：隔一会儿接着传、下、问的那一块
        self.Seen = None  # 上次看到的 UserRecipeManager.Revision()
        self.RescanAt = 0.0  # type: float  # 撤回失败了：什么时候再看一遍
        self.RetryAt = 0.0  # type: float  # 列表没问到时什么时候再问
        self.Contents = {}  # type: dict  # 本地分组 Id -> (存储的版本号, 一整串, 指纹)
        self._touch()

    def Revision(self):  # type: () -> int
        """ 每变一次加一（管理器据此重排）"""
        return self._revision

    def _touch(self):
        self._revision += 1

    def _live(self, generation):  # type: (int) -> bool
        return self.Joined and generation == self.Generation

    def _channel(self):
        if self.Channel is not None:
            return self.Channel
        from MEIScripts.mei_mod.network.protocol.client import GetChannel
        return GetChannel()

    @staticmethod
    def _body(response):  # type: (dict) -> tuple
        """ 回执 → (body, 失败原因)：通道层失败（超时）、处理器说不行，都给原因 """
        if not response.get(KEY_OK):
            return None, response.get(KEY_ERROR) or "timeout"
        body = response.get(KEY_BODY)
        if isinstance(body, dict) and body.get("ok") is False:
            return body, body.get("error") or "bad"
        return body if isinstance(body, dict) else {}, None

    def _backoff(self, group_id):  # type: (str) -> float
        attempts = self.Attempts.get(group_id, 0) + 1
        self.Attempts[group_id] = attempts
        return min(RETRY_MAX, RETRY_DELAY * attempts)

    def _after(self, delay, generation, callback):
        """ 隔 delay 秒（Tick 里）调 callback；代号变了就不调了 """
        self.Later.append((self.Clock() + delay, generation, callback))

    # 进出存档、列表与广播
# ======================================================================================================================
    def OnWorldJoined(self):
        """ 进了一个存档（client/main_sys 的 UiInitFinished；换维度也会再来一次）：从头来，问一次列表 """
        self.Reset()
        self.Joined = True
        self.RequestList()

    def OnWorldLeft(self):
        """ 退出存档（client/main_sys 的 Destroy）：在路上的都不认了，进下一个存档之前不干活 """
        self.Joined = False
        self.Reset()
        self.Removed = {}

    def RequestList(self):  # type: () -> bool
        """ 分块问一遍列表（问到一半服务器上又变了就从头再问）"""
        channel = self._channel()
        if channel is None or self.Asking or not self.Joined:
            return False
        self.Asking = True
        self.ListStale = False
        self._touch()
        generation = self.Generation
        chunks, state = [], {"version": None, "restarts": 0, "resumes": 0, "op": False, "mine": []}

        def request(part):
            channel.Request(REQUEST_SHARE_LIST, {"part": part}, on_reply=lambda response: reply(part, response))

        def reply(part, response):
            if not self._live(generation):
                return
            body, error = self._body(response)
            if error is not None:
                if error == ERR_RATE and state["resumes"] < RESUMES:  # 被限流：从这一块接着问（超时是服务器没回，隔久一点从头问）
                    state["resumes"] += 1
                    return self._after(RETRY_DELAY, generation, lambda: request(part))
                return fail(error)
            version = _version(body.get("version"))
            if part == 0:
                state["version"] = version
                state["op"] = body.get("op") is True
                mine = body.get("mine")
                state["mine"] = mine[:LIST_ROWS] if isinstance(mine, list) else []
            elif version != state["version"]:  # 问到一半列表变了：从头再问
                state["restarts"] += 1
                if state["restarts"] > 3:
                    return fail("busy")
                del chunks[:]
                return request(0)
            chunks.append(native_str(body.get("data") or ""))
            if part + 1 < min(_count(body.get("parts")), LIST_PARTS):
                return request(part + 1)
            try:
                groups = json.loads("".join(chunks))
            except Exception:  # noqa
                return fail("bad")
            self.Asking = False
            self.Failed = False
            self.IsOp = state["op"]
            self.ServerMine = set(key for key in (valid_key(item) for item in state["mine"]) if key)
            self.ListVersion = state["version"]
            if self.PushedVersion is not None and (self.ListVersion is None or self.PushedVersion > self.ListVersion):
                self.ListStale = True  # 问的工夫里又变了
            self.Apply(groups)

        def fail(reason):
            self.Asking = False
            self.Failed = True
            self.ListStale = self.Listed  # 拿到过列表的：隔一会儿再问；没拿到过的由 Tick 按 RetryAt 再问
            self.RetryAt = self.Clock() + (RETRY_DELAY if reason == ERR_RATE else LIST_RETRY)
            self._touch()
            logger.warn("[MEI/share] 问服务器上的共享分组失败: {}".format(reason))

        request(0)
        return True

    def OnPush(self, args):
        """ 服务器广播：列表到了第几版（进存档之前收到的不处理）；比手上的新就再问一遍 """
        if not self.Joined:
            return
        try:
            version = _version((args or {}).get("version")) if isinstance(args, dict) else None
            if version is None:
                return
            self.PushedVersion = version if self.PushedVersion is None else max(self.PushedVersion, version)
            if self.ListVersion is not None and version <= self.ListVersion:
                return
            if self.Asking:
                self.ListStale = True
            else:
                self.RequestList()
        except Exception as e:  # noqa
            logger.error("[MEI/share] 处理共享分组的变化出错: {}".format(error_text(e)))

    def Apply(self, groups):
        """ 服务器上的分组（摘要）来了：记下、对一遍拿下来的 """
        rows = groups[:LIST_ROWS] if isinstance(groups, list) else []
        self.Servers = [entry for entry in (normalize_summary(raw) for raw in rows) if entry is not None]
        self.Listed = True
        self._touch()
        self.Reconcile()

    def Server(self, key):  # type: (str) -> dict or None
        for entry in self.Servers:
            if entry["key"] == key:
                return entry
        return None

    def MyKeys(self):  # type: () -> set
        """ 自己共享出去的分组在服务器上的键：这个存档里起过的、传过的，加上服务器说是自己的 """
        return UserShareManager.MyKeys() | self.ServerMine

    def IsMine(self, key):  # type: (str) -> bool
        return key in self.MyKeys()

    def Reconcile(self):
        """ 拿下来的对着服务器的列表过一遍；自己传过、服务器上却没有或者不是那一份了的忘掉（下一帧会重传）"""
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import IsForceOverride
        if not self.Joined:
            return
        by_key = dict((entry["key"], entry) for entry in self.Servers)
        override = IsForceOverride()
        forgot = False
        for key in UserShareManager.UploadedKeys():
            if self.Busy.get(key):
                continue
            server, sent = by_key.get(key), UserShareManager.UploadedServer(key)
            if server is None or (server["digest"] and sent and server["digest"] != sent):
                UserShareManager.ForgetUploaded(key)
                forgot = True
        if forgot:
            self.Seen = None  # 下一帧再看一遍要不要传
        for sub in list(UserShareManager.Subs()):
            server = by_key.get(sub["key"])
            if server is None:
                if sub["subscribed"]:
                    UserShareManager.UpdateSub(sub["key"], gone=True, unified=False)
                else:
                    UserShareManager.RemoveSub(sub["key"])
                continue
            if not sub["subscribed"] and not (server["unified"] and override):
                UserShareManager.RemoveSub(sub["key"])  # 只是因为统一才拿下来的：统一不生效了（或者自己关了强制覆盖）
                continue
            fresh = not outdated(server, sub)
            unified = server["unified"] and fresh  # 拿下来的还是旧内容：先不当统一的登记，等新内容下好
            if sub["gone"] or sub["unified"] != unified:
                UserShareManager.UpdateSub(sub["key"], gone=False, unified=unified)
            if not fresh:
                self.Download(sub["key"])
            elif server["rev"] != sub["rev"]:
                UserShareManager.UpdateSub(sub["key"], rev=server["rev"])  # 内容一样、版本号不一样：只记版本号
        if override:
            mine = self.MyKeys()
            for server in self.Servers:
                if server["unified"] and server["key"] not in mine and UserShareManager.Sub(server["key"]) is None:
                    self.Download(server["key"], unified=True)

    # 下载、订阅
# ======================================================================================================================
    def Download(self, key, subscribe=False, unified=False, on_done=None):  # type: (str, bool, bool, any) -> bool
        """
        把服务器上的一个分组拿下来存进这个存档：排队，一次只下一个（分块，一块一块要）。subscribe：顺带订阅上，unified：因为统一才拿的；
        同一个键已经在下 / 排着的，标志与回调并进去。on_done(成没成, 失败的原因) 在完了时调一次
        """
        if not self.Joined or self._channel() is None:
            return False
        record = self.Downloads.get(key) or next((item for item in self.Pending if item["key"] == key), None)
        if record is None:
            if self.Busy.get(key):
                return False  # 正在删、正在统一
            record = {"key": key, "subscribe": False, "unified": False, "callbacks": []}
            self.Pending.append(record)
        record["subscribe"] = record["subscribe"] or subscribe
        record["unified"] = record["unified"] or unified
        if on_done is not None:
            record["callbacks"].append(on_done)
        self._touch()
        self.__Next()
        return True

    def __Next(self):
        """ 没在下、也没被限流：下排着的第一个 """
        if self.Downloads or not self.Pending or self.Clock() < self.QueueAt:
            return
        record = self.Pending.pop(0)
        self.__Start(record)

    def __Start(self, record):
        key = record["key"]
        channel = self._channel()
        generation = self.Generation
        self.Downloads[key] = record
        self.Busy[key] = "down"
        chunks, state = [], {"version": None, "owner": "", "restarts": 0, "resumes": 0}

        def request(part):
            channel.Request(REQUEST_SHARE_DOWNLOAD, {"key": key, "part": part}, on_reply=lambda response: reply(part, response))

        def reply(part, response):
            if not self._live(generation):
                return
            body, error = self._body(response)
            if error is not None:
                if error in RETRYABLE and state["resumes"] < RESUMES:  # 从这一块接着要
                    state["resumes"] += 1
                    return self._after(min(RETRY_MAX, RETRY_DELAY * state["resumes"]), generation, lambda: request(part))
                return finish(error)
            version = (body.get("rev"), body.get("digest"), body.get("unified") is True)
            if state["version"] is None:
                state["version"] = version
                state["owner"] = body.get("owner") if isinstance(body.get("owner"), basestring) else ""
            elif version != state["version"]:  # 下到一半服务器上换了一版（删了再传版本号可能一样，所以连指纹一起比）：从头再要
                state["restarts"] += 1
                if state["restarts"] > 3:
                    return finish("busy")
                del chunks[:]
                state["version"] = None
                return request(0)
            chunks.append(native_str(body.get("data") or ""))
            if part + 1 < min(_count(body.get("parts")), MAX_PARTS):
                return request(part + 1)
            finish(None)

        def finish(reason):
            self.Downloads.pop(key, None)
            self.Busy.pop(key, None)
            if reason in RETRYABLE:
                self.Pending.insert(0, record)  # 接着来了几次还是被限流、超时：放回队头，过一会儿从头再下
                self.QueueAt = self.Clock() + RETRY_DELAY
                self._touch()
                return
            if reason is None:
                rev, digest, unified = state["version"]
                reason = self.__Save(key, "".join(chunks), rev, digest, unified, state["owner"], record["subscribe"],
                                     record["unified"])
            if reason is not None:
                logger.warn("[MEI/share] 下载共享分组 {} 失败: {}".format(key, reason))
            self._touch()
            for callback in record["callbacks"]:
                try:
                    callback(reason is None, reason)
                except Exception as e:  # noqa
                    logger.error("[MEI/share] 下载完的回调出错: {}".format(error_text(e)))
            self.__Next()

        request(0)

    @staticmethod
    def __Save(key, content, rev, digest, unified, owner, subscribe, for_unified):
        # type: (str, str, int, str, bool, str, bool, bool) -> str or None
        try:
            data = to_native(json.loads(content))
        except Exception:  # noqa
            return "bad"
        if not isinstance(data, dict):
            return "bad"
        entry = {"key": key, "name": data.get("name"), "desc": data.get("desc"), "owner_name": owner or data.get("owner_name"),
                 "rev": rev, "digest": digest, "unified": unified is True, "gone": False,
                 "pages": data.get("pages"), "recipes": data.get("recipes")}
        if subscribe:
            entry["subscribed"] = True
            entry["enabled"] = True
        elif UserShareManager.Sub(key) is None and not (for_unified and unified):
            return None  # 没订阅、也不是（还）统一的：不存
        return None if UserShareManager.SaveSub(entry) else "full_local"

    def Subscribe(self, key, on_done=None):  # type: (str, any) -> bool
        """ 订阅：没拿下来过就下载；自己共享出去的不订阅 """
        if self.IsMine(key):
            return False
        sub = UserShareManager.Sub(key)
        if sub is None:
            return self.Download(key, subscribe=True, on_done=on_done)
        UserShareManager.UpdateSub(key, subscribed=True, enabled=True)
        server = self.Server(key)
        if server is not None and outdated(server, sub):
            self.Download(key)
        self._touch()
        return True

    def Unsubscribe(self, key):  # type: (str) -> bool
        """ 取消订阅：删掉拿下来的这一份（统一生效、强制覆盖开着时留着，只是不算订阅）"""
        from MEIScripts.mei_mod.ui_script.mei_ui.editor.settings import IsForceOverride
        sub = UserShareManager.Sub(key)
        if sub is None:
            return False
        if sub["unified"] and not sub["gone"] and IsForceOverride():
            UserShareManager.UpdateSub(key, subscribed=False)
        else:
            UserShareManager.RemoveSub(key)
        self._touch()
        return True

    def SetSubEnabled(self, key, on):  # type: (str, bool) -> bool
        return UserShareManager.UpdateSub(key, enabled=bool(on))

    def CopyToLocal(self, key):  # type: (str) -> tuple
        """ 拿下来的一份导成本地的新分组（新 Id，能改）：返回 (分组 Id, 错误) """
        pack = UserShareManager.Pack(key)
        if pack is None:
            return None, "gone"
        return UserRecipeManager.ImportGroup(pack)

    def DeleteRemote(self, key, on_done=None):  # type: (str, any) -> bool
        """ 从服务器上删（上传者、操作员）；删的是自己的分组就顺带关掉本地的共享（不然又会自动传上去）"""
        channel = self._channel()
        if channel is None or self.Busy.get(key) or not self.Joined:
            return False
        group_id = UserShareManager.GroupOfKey(key)
        group = UserRecipeManager.Group(group_id) if group_id else None
        if group is not None and group["shared"]:
            UserRecipeManager.UpdateGroup(group_id, shared=False)
        self.Busy[key] = "del"
        self._touch()
        generation = self.Generation

        def reply(response):
            if not self._live(generation):
                return
            self.Busy.pop(key, None)
            _body, error = self._body(response)
            if error is None:
                UserShareManager.ForgetUploaded(key)
            self._touch()
            if on_done is not None:
                on_done(error is None, error)
        channel.Request(REQUEST_SHARE_DELETE, {"key": key}, on_reply=reply)
        return True

    def SetUnified(self, key, on, on_done=None):  # type: (str, bool, any) -> bool
        """ 操作员：把服务器上的一个分组设成统一 / 取消（统一的是此刻这一份内容；服务器再查一次是不是操作员）"""
        channel = self._channel()
        if channel is None or self.Busy.get(key) or not self.Joined:
            return False
        self.Busy[key] = "unify"
        self._touch()
        generation = self.Generation

        def reply(response):
            if not self._live(generation):
                return
            self.Busy.pop(key, None)
            _body, error = self._body(response)
            self._touch()
            if on_done is not None:
                on_done(error is None, error)
        channel.Request(REQUEST_SHARE_UNIFY, {"key": key, "on": bool(on)}, on_reply=reply)
        return True

    # 上传
# ======================================================================================================================
    def Tick(self):
        """
        每帧（client/main_sys 的 Update）：没进存档不干活；到点的接着传、下、问；列表没问到隔一会儿再问、旧了再问；
        存储变了才看要不要传；到点的传（一次一个）；下载队列被限流的到点了接着下
        """
        if not self.Joined:
            return
        now = self.Clock()
        if self.Later:
            due = [item for item in self.Later if item[0] <= now]
            if due:
                self.Later = [item for item in self.Later if item[0] > now]
                for _when, generation, callback in due:
                    if self._live(generation):
                        callback()
        if not self.Listed:
            if self.Failed and not self.Asking and now >= self.RetryAt:
                self.RequestList()
            return
        if self.ListStale and not self.Asking and now >= self.RetryAt:
            self.RequestList()
        if self.RescanAt and now >= self.RescanAt:
            self.RescanAt = 0.0
            self.Seen = None
        revision = UserRecipeManager.Revision()
        if revision != self.Seen:
            self.Seen = revision
            try:
                self.__Scan(now)
            except Exception as e:  # noqa
                logger.error("[MEI/share] 看共享分组要不要上传时出错: {}".format(error_text(e)))
        if self.Due and self.UploadingKey is None:
            for group_id, when in sorted(self.Due.items(), key=lambda item: item[1]):
                if now >= when:
                    del self.Due[group_id]
                    if self.Upload(group_id):
                        break
        if self.Pending and not self.Downloads and now >= self.QueueAt:
            self.__Next()

    def StatusOf(self, group_id):  # type: (str) -> tuple
        return self.Status.get(group_id, (None, None))

    def Content(self, group_id):  # type: (str) -> tuple
        """ 一个本地分组要传的一整串（ASCII 的 JSON）与它的指纹（存储没变就用上次算的）"""
        revision = UserRecipeManager.Revision()
        cached = self.Contents.get(group_id)
        if cached is not None and cached[0] == revision:
            return cached[1], cached[2]
        group = UserRecipeManager.Group(group_id)
        pack = UserRecipeManager.ExportGroup(group_id)
        pack["name"] = group_label(group)
        content = json.dumps(pack, sort_keys=True, separators=(",", ":"))
        digest = stable_digest(content)
        self.Contents[group_id] = (revision, content, digest)
        return content, digest

    def __Scan(self, now):
        shared = {}
        groups = list(UserRecipeManager.Groups())
        alive = set(group["id"] for group in groups)
        for group_id in [gid for gid in self.Contents if gid not in alive]:
            del self.Contents[group_id]
        for group in groups:
            group_id = group["id"]
            if not group["shared"]:
                for table in (self.Due, self.Status, self.Scheduled, self.Attempts):
                    table.pop(group_id, None)
                continue
            key = UserShareManager.KeyFor(group_id)
            if key is None:
                key = new_share_key()  # 这个存档的服务器上第一次共享：起一个这里用的键
                UserShareManager.AssignKey(group_id, key)
            shared[key] = group_id
            self.Removed.pop(group_id, None)
            _content, digest = self.Content(group_id)
            state = self.StatusOf(group_id)[0]
            if UserShareManager.Uploaded(key) == digest:
                self.Due.pop(group_id, None)
                self.Status[group_id] = (DONE, (self.Server(key) or {}).get("rev"))
            elif self.Scheduled.get(group_id) == digest and (group_id in self.Due or state in (UPLOADING, FAILED)):
                pass  # 这一版已经排上了 / 正在传 / 传过、失败了（内容不变不自动重试，改了才再试）
            else:
                self.Scheduled[group_id] = digest
                self.Due[group_id] = now + UPLOAD_DELAY
                self.Status[group_id] = (PENDING, None)
                self.Attempts.pop(group_id, None)
        uploaded = set(UserShareManager.UploadedKeys())
        for key in uploaded:
            if key not in shared and not self.Busy.get(key):
                self.__Unshare(key)
        for group_id, key in UserShareManager.KeyedGroups().items():
            if group_id not in alive and key not in uploaded:
                UserShareManager.ForgetKey(group_id)  # 分组删了、服务器上也撤了
        self._touch()

    def Upload(self, group_id):  # type: (str) -> bool
        """ 把一个本地分组传上去（分块，一块一块传，带会话号；一次只传一个）。开始传了给 True """
        group = UserRecipeManager.Group(group_id)
        channel = self._channel()
        key = UserShareManager.KeyFor(group_id)
        if not self.Joined or group is None or not group["shared"] or not key or channel is None:
            self.Status.pop(group_id, None)
            return False
        if self.Busy.get(key) or (self.UploadingKey is not None and self.UploadingKey != key):
            self.Due[group_id] = self.Clock() + UPLOAD_DELAY  # 在撤、在传别的：等一会儿
            return False
        content, digest = self.Content(group_id)
        if UserShareManager.Uploaded(key) == digest:
            self.Status[group_id] = (DONE, (self.Server(key) or {}).get("rev"))  # 这一版传过了（推送先于回执到的那一下又排了一次）
            self._touch()
            return False
        chunks = [content[start:start + CHUNK] for start in range(0, len(content), CHUNK)] or [""]
        sid = new_sid()
        generation = self.Generation
        state = {"resumes": 0}
        self.Busy[key] = "up"
        self.UploadingKey = key
        self.Status[group_id] = (UPLOADING, None)
        self._touch()

        def send(part):
            channel.Request(REQUEST_SHARE_UPLOAD, {"key": key, "sid": sid, "part": part, "parts": len(chunks), "data": chunks[part]},
                            on_reply=lambda response: reply(part, response))

        def release():
            self.Busy.pop(key, None)
            if self.UploadingKey == key:
                self.UploadingKey = None

        def reply(part, response):
            if not self._live(generation):
                return  # 换了维度 / 存档：这一趟不认了（服务器那边下一次上传换了会话号，旧的块不打断它）
            body, error = self._body(response)
            if error is not None:
                if error in RETRYABLE and state["resumes"] < RESUMES:  # 从这一块接着传（服务器那边这一次的会话还留着）
                    state["resumes"] += 1
                    return self._after(min(RETRY_MAX, RETRY_DELAY * state["resumes"]), generation, lambda: send(part))
                release()
                self.__Failed(group_id, key, error)
                return
            if part + 1 < len(chunks):
                return send(part + 1)
            release()
            self.Attempts.pop(group_id, None)
            UserShareManager.SetUploaded(key, digest, body.get("digest"))
            self.Status[group_id] = (DONE, body.get("rev"))
            self._touch()

        send(0)
        return True

    def __Failed(self, group_id, key, reason):
        """
        上传没成：限流、超时（接着传了几次还不行）、服务器丢了这一次的会话（order）隔一会儿从头再传；
        被操作员撤下关掉本地的共享；别的记下原因（改了才再试）
        """
        if reason in RETRYABLE or reason == ERR_ORDER:
            self.Due[group_id] = self.Clock() + self._backoff(group_id)
            self.Status[group_id] = (PENDING, None)
        elif reason == ERR_REMOVED:
            self.Removed[group_id] = True
            UserShareManager.ForgetUploaded(key)
            UserShareManager.ForgetKey(group_id)  # 再共享就是新的一个
            UserRecipeManager.UpdateGroup(group_id, shared=False)
            self.Status[group_id] = (FAILED, reason)
        else:
            self.Status[group_id] = (FAILED, reason)
        self._touch()
        logger.warn("[MEI/share] 上传共享分组 {} 失败: {}".format(key, reason))

    def __Unshare(self, key):
        """ 不共享了 / 分组删了：从服务器上撤掉（服务器上已经没有也算撤掉了）；没撤成过一会儿再看一遍 """
        channel = self._channel()
        if channel is None:
            return
        self.Busy[key] = "del"
        generation = self.Generation

        def reply(response):
            if not self._live(generation):
                return
            self.Busy.pop(key, None)
            _body, error = self._body(response)
            if error in RETRYABLE:
                self.RescanAt = self.Clock() + RETRY_DELAY
                logger.warn("[MEI/share] 从服务器上撤掉共享分组 {} 失败，过一会儿再试: {}".format(key, error))
            elif error is not None:
                UserShareManager.ForgetUploaded(key)  # 撤不了（不归自己了）：不再试
                logger.warn("[MEI/share] 从服务器上撤掉共享分组 {} 失败: {}".format(key, error))
            else:
                UserShareManager.ForgetUploaded(key)
            self._touch()
        channel.Request(REQUEST_SHARE_DELETE, {"key": key}, on_reply=reply)


ShareClient = __ShareClient()
