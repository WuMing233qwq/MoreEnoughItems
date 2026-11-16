# coding=utf-8
# ----------------------------------------------------------------------
#  user_share.py is part of MoreEnoughItems.
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
多人共享的自制配方，客户端这一边按存档存的那份（docs/architecture/user_recipes.md §22、§24）：

subs     [{"key": 服务器上的键, "name", "desc", "owner_name": 上传者, "rev": 版本, "digest": 内容指纹（content_digest）,
           "subscribed": 自己订阅了没有, "enabled": 订阅的开着没有, "unified": 服务器说统一生效了没有, "gone": 服务器上已经没有了,
           "size": 内容有多少字, "pages": [页面], "recipes": [配方]}]
         从服务器拿下来的分组：订阅的（只读、跟着服务器更新）、操作员统一的（「启用强制覆盖」开着时自动下载）。
         页面、配方的样子和本地的一样（state/user_recipes.py 规整），另有上限（MAX_SHARED_PAGES / MAX_SHARED_RECIPES）；要改就「复制到本地」（导成新的一份）。
         跟不跟服务器比的是内容指纹、不是版本号：撤了共享再共享，服务器上的版本号可能重新数，比版本号会漏掉这一回的改动。
         拿下来的页面、配方 Id 在登记时前面加服务器上的键（qualify），和本地的、别的分组的都不撞。
keys     {本地分组 Id: 服务器上的键}  本地分组在这个存档的服务器上用哪个键（每个存档各起一个：别的服务器上的人猜不到、抢不了）。
uploaded {服务器上的键: {"l": 本地这一版的指纹, "s": 服务器存下的那一版的指纹}}
         这个存档里传过哪一版。"l" 是客户端自己算的（本地改了才再传），"s" 是服务器回的（服务器上那份变了 —— 存档回档、数据被清 —— 就重传）；
         两种指纹各比各的，客户端与服务端的规整不必逐字一样。不共享了按它从服务器上撤

存在 mei_user_share（按存档）：索引里是上面三张表，subs 只记摘要；每个拿下来的分组的页面、配方存在它自己的配置项里（content_name），
改一个分组只写它自己的那一项（一个分组最大 1 MB，几十个放在一项里每改一次都要整个重写）。内容也在索引里的旧写法（1）读到了就搬出去。
进存档时 ResetWorldStore（先写下手上的，换维度也会来），退出存档时 Close（写下、丢掉读过的表 ——
下一个存档在 ResetWorldStore 之前读到的是它自己的那份）。构造期不碰引擎
"""
import copy
import json

from MEIScripts.constants.codes import StorageConst
from MEIScripts.utils.log import logger
from MEIScripts.utils.stablehash import stable_digest
from MEIScripts.utils.text import error_text

from .storage import Store
from .user_recipes import LISTENER_ALL, _ident, _text, DESC_LENGTH, NAME_LENGTH, normalize_page, normalize_recipe

CONFIG_NAME = StorageConst.UserShareConfigName

VERSION = 2
MIGRATIONS = {1: lambda payload: payload}
""" 1 → 2：分组的页面、配方搬到各自的配置项里（要写别的配置项，在 _load 里搬，这里只升版）"""

KEY_SUBS = "subs"
KEY_UPLOADED = "uploaded"
KEY_KEYS = "keys"
KEY_CONTENT = "c"
""" 一个分组自己的配置项里存内容的键：{"pages", "recipes"} """

MAX_SUBS = 128
MAX_SHARED_PAGES = 256
MAX_SHARED_RECIPES = 4096
""" 一个共享分组最多几个页面、几条配方（服务端传上来时就拒，这里读回来再截一次）"""
MAX_SUBS_SIZE = 32 * 1024 * 1024
""" 一个存档里拿下来的分组的内容合起来最多多少字（满了先挤掉最早的「已下架」）"""

DIGEST_LENGTH = 32


def valid_digest(value):  # type: (any) -> str
    """ 指纹：只认字母数字（十六进制），别的给空串 """
    if not isinstance(value, basestring) or not value or len(value) > DIGEST_LENGTH:
        return ""
    try:
        value = value.encode("ascii") if isinstance(value, unicode) else value.decode("ascii").encode("ascii")
    except UnicodeError:
        return ""
    return value if value.isalnum() else ""


def qualify(namespace, item_id):  # type: (str, str) -> str
    """ 拿下来的页面、配方登记时用的 Id：前面加服务器上的键（本地的不加）"""
    return "{}/{}".format(namespace, item_id) if namespace else item_id


def content_name(key):  # type: (str) -> str
    """ 一个拿下来的分组的内容存在哪个配置项（配置名只能有字母数字下划线：_ 写成 _u、- 写成 _d，一一对应）"""
    return "{}_c_{}".format(CONFIG_NAME, "".join(ch if ch.isalnum() else ("_u" if ch == "_" else "_d") for ch in key))


def content_text(content):  # type: (dict) -> str
    """
    一个分组的内容（名字、介绍、页面、配方）写成的一串：服务端存的、下载给的就是它。
    ASCII 的 JSON（unicode 与非 ASCII 的 str 混着也照样编，同一段字是哪一种写出来都一样），不排序（C 编码器，1 MB 约 10 毫秒）——
    内容是规整过的，键的先后由规整的写法定，同样的内容写出来一样
    """
    return json.dumps({"name": content.get("name") or u"", "desc": content.get("desc") or u"",
                       "pages": content.get("pages") or [], "recipes": content.get("recipes") or []}, separators=(",", ":"))


def content_digest(content):  # type: (dict) -> str
    """
    一个分组的内容指纹：content_text 的 stable_digest（不含版本号、统一没有、上传者）。服务端存的时候算（规整过的那一份），
    列表、广播、下载都带着；客户端拿它和拿下来的那份比
    """
    return stable_digest(content_text(content))


def normalize_sub(sub):  # type: (any) -> dict or None
    """ 一个拿下来的分组：没有键的给 None；页面、配方照本地的规整并截到上限，配方只留页面在这一包里的 """
    if not isinstance(sub, dict):
        return None
    key = _ident(sub.get("key"))
    if not key:
        return None
    result = dict(sub)
    result["key"] = key
    result["name"] = _text(sub.get("name"), NAME_LENGTH)
    result["desc"] = _text(sub.get("desc"), DESC_LENGTH)
    result["owner_name"] = _text(sub.get("owner_name"), NAME_LENGTH)
    rev = sub.get("rev")
    result["rev"] = int(rev) if isinstance(rev, (int, long)) and not isinstance(rev, bool) and rev > 0 else 0
    result["digest"] = valid_digest(sub.get("digest"))
    result["subscribed"] = sub.get("subscribed") is True
    result["enabled"] = sub.get("enabled") is not False
    result["unified"] = sub.get("unified") is True
    result["gone"] = sub.get("gone") is True
    size = sub.get("size")
    result["size"] = int(size) if isinstance(size, (int, long)) and not isinstance(size, bool) and size > 0 else 0
    raw_pages = sub.get("pages") if isinstance(sub.get("pages"), list) else []
    raw_recipes = sub.get("recipes") if isinstance(sub.get("recipes"), list) else []
    pages, seen = [], set()
    for page in (normalize_page(raw) for raw in raw_pages[:MAX_SHARED_PAGES]):
        if page is not None and page["id"] not in seen:
            seen.add(page["id"])
            pages.append(page)
    result["pages"] = pages
    recipes, taken = [], set()
    for recipe in (normalize_recipe(raw) for raw in raw_recipes[:MAX_SHARED_RECIPES]):
        if recipe is not None and recipe["page"] in seen and recipe["id"] not in taken:
            taken.add(recipe["id"])
            recipes.append(recipe)
    result["recipes"] = recipes
    return result


def sub_meta(sub):  # type: (dict) -> dict
    """ 索引里记的那一份：除了页面、配方 """
    return dict((name, value) for name, value in sub.items() if name not in ("pages", "recipes"))


def page_ids(sub):  # type: (dict or None) -> set
    """ 这个拿下来的分组登记时的页面 Id（带服务器上的键）"""
    if not sub:
        return set()
    return set(qualify(sub["key"], page["id"]) for page in sub.get("pages") or ())


class __UserShareManager(object):  # noqa
    """ 拿下来的分组、服务器上的键与上传记录的门面，构造期不碰引擎 """

    def __init__(self):
        self._store = None
        self._factory = None
        self._contents = {}  # type: dict  # 服务器上的键 -> 它的内容那一项的 Store
        self._subs = None  # type: list or None
        self._uploaded = None  # type: dict or None
        self._keys = None  # type: dict or None
        self._revision = 0
        self._listeners = []  # type: list

    def _get_store(self):  # type: () -> Store
        if self._store is None:
            if self._factory is not None:
                self._store = self._factory()
            else:
                # 延迟到首次使用才 import backend，它顶层拉客户端引擎
                from .storage.backend import ConfigBackend, EngineScheduler
                self._store = Store(ConfigBackend(), CONFIG_NAME, is_global=False, version=VERSION, migrations=MIGRATIONS,
                                    scheduler=EngineScheduler())
        return self._store

    def _content_store(self, key):  # type: (str) -> Store
        """ 一个拿下来的分组的内容那一项：和索引同一个后端、同一种存法（按存档），写盘不排序 """
        store = self._contents.get(key)
        if store is None:
            index = self._get_store()
            store = Store(index.Backend, content_name(key), is_global=index.IsGlobal, version=1,
                          scheduler=index.Scheduler, delay=index.Delay, compact=True)
            self._contents[key] = store
        return store

    def SetStoreFactory(self, factory):
        """ 测试注入点：factory() -> Store（每次换存档调一次；各分组的内容项建在它的后端上）；换了就丢掉读过的表 """
        self._factory = factory
        self._drop()
        self._revision += 1
        self._notify(set([LISTENER_ALL]))

    def _drop(self):
        """ 丢掉读过的表；内容那几项先写下去（它们按需建在后端上，丢了就只能从后端读回来）"""
        for store in self._contents.values():
            try:
                store.Flush()
            except Exception as e:  # noqa
                logger.error("[MEI/share] 拿下来的分组没写下去: {}".format(error_text(e)))
        self._contents = {}
        self._store = None
        self._subs = None
        self._uploaded = None
        self._keys = None

    def _flush_quietly(self):
        if self._store is None:
            return
        try:
            self.Flush()
        except Exception as e:  # noqa  写不下去只丢这几秒的改动
            logger.error("[MEI/share] 共享的存档数据没写下去: {}".format(error_text(e)))

    def Close(self):
        """ 退出存档（client/main_sys 的 Destroy）：写下手上的、丢掉读过的表；下一个存档里先读到的就是它自己的那份 """
        self._flush_quietly()
        self._drop()

    def ResetWorldStore(self):
        """
        进了一个存档（UiInitFinished；换维度也会再来一次）：先把手上没写下去的写下去（换维度还是同一个存档；换存档时 Close 已经写过、丢过了），
        再从头读。拿下来的分组可能全换了：通知一次「整张表都可能变了」
        """
        self._flush_quietly()
        self._drop()
        self._revision += 1
        self._notify(set([LISTENER_ALL]))

    def _load(self):
        if self._subs is not None:
            return
        store = self._get_store()
        raw = store.Get(KEY_SUBS)
        subs, seen, moved = [], set(), []
        if raw is not None and not isinstance(raw, list):
            logger.warn("[MEI/share] 拿下来的分组不是列表({})，本轮按空处理".format(type(raw).__name__))
            raw = []
        for item in raw or ():
            key = _ident(item.get("key")) if isinstance(item, dict) else None
            if not key or key in seen or len(subs) >= MAX_SUBS:
                continue
            if "pages" in item or "recipes" in item:  # 旧写法：内容在索引里，搬到它自己的那一项
                moved.append(key)
            else:
                content = self._content_store(key).Get(KEY_CONTENT)
                if isinstance(content, dict):
                    item = dict(item, pages=content.get("pages"), recipes=content.get("recipes"))
                else:
                    item = dict(item, digest="")  # 内容那一项没了：指纹作废，下次对上服务器的列表时重新下载
            entry = normalize_sub(item)
            if entry is None:
                continue
            if not entry["size"] or key in moved:
                entry["size"] = len(content_text(entry))
            seen.add(key)
            subs.append(entry)
        self._subs = subs
        uploaded = store.Get(KEY_UPLOADED)
        self._uploaded = {}
        for key, value in (uploaded.items() if isinstance(uploaded, dict) else ()):
            if isinstance(value, basestring):
                value = {"l": value}  # 只记了本地指纹的旧写法
            if _ident(key) and isinstance(value, dict) and valid_digest(value.get("l")):
                self._uploaded[_ident(key)] = {"l": valid_digest(value.get("l")), "s": valid_digest(value.get("s"))}
        keys = store.Get(KEY_KEYS)
        self._keys = {}
        for group_id, key in (keys.items() if isinstance(keys, dict) else ()):
            if _ident(group_id) and _ident(key):
                self._keys[_ident(group_id)] = _ident(key)
        if moved:
            self._persist(set(), content=[key for key in moved if key in seen])

    def _persist(self, pages, keys=(KEY_SUBS,), content=()):  # type: (set, tuple, any) -> None
        """ 写回：keys 是索引里动了的几张表（subs 只写摘要）；content 是内容要写（还在）或要清（没了）的分组的键 """
        store = self._get_store()
        tables = {KEY_UPLOADED: self._uploaded, KEY_KEYS: self._keys}
        for key in keys:
            store.Set(key, [sub_meta(sub) for sub in self._subs] if key == KEY_SUBS else tables[key])
        if content:
            if KEY_SUBS not in keys:
                store.Set(KEY_SUBS, [sub_meta(sub) for sub in self._subs])
            for key in content:
                sub = self.Sub(key)
                target = self._content_store(key)
                if sub is not None:
                    target.Put(KEY_CONTENT, {"pages": sub["pages"], "recipes": sub["recipes"]})
                else:
                    target.Delete(KEY_CONTENT)
        self._revision += 1
        self._notify(pages)

    def _notify(self, pages):  # type: (set) -> None
        for listener in list(self._listeners):
            try:
                listener(set(pages))
            except Exception as e:  # noqa
                logger.error("[MEI/share] 改动通知出错: {}".format(error_text(e)))

    # 读
# ======================================================================================================================
    def Revision(self):  # type: () -> int
        return self._revision

    def Subs(self):  # type: () -> list
        """ 拿下来的全部分组（只读）"""
        self._load()
        return self._subs

    def Sub(self, key):  # type: (str) -> dict or None
        for sub in self.Subs():
            if sub["key"] == key:
                return sub
        return None

    def TotalSize(self):  # type: () -> int
        """ 拿下来的分组的内容合起来多少字 """
        return sum(sub["size"] for sub in self.Subs())

    def Pack(self, key):  # type: (str) -> dict or None
        """ 一个拿下来的分组打成一包（拷贝，ExportGroup 的样子）：「复制到本地」用 """
        sub = self.Sub(key)
        if sub is None:
            return None
        return {"name": sub["name"], "desc": sub["desc"], "pages": copy.deepcopy(sub["pages"]),
                "recipes": copy.deepcopy(sub["recipes"])}

    def Uploaded(self, key):  # type: (str) -> str or None
        """ 这个存档里传上去的那一版，本地算的指纹；没传过给 None """
        self._load()
        record = self._uploaded.get(key)
        return record["l"] if record else None

    def UploadedServer(self, key):  # type: (str) -> str
        """ 传上去以后服务器回的指纹（服务器存下的那一份）；没有给空串 """
        self._load()
        record = self._uploaded.get(key)
        return record["s"] if record else ""

    def UploadedKeys(self):  # type: () -> list
        self._load()
        return sorted(self._uploaded)

    def KeyFor(self, group_id):  # type: (str) -> str or None
        """ 本地分组在这个存档的服务器上用的键；还没起给 None """
        self._load()
        return self._keys.get(group_id)

    def GroupOfKey(self, key):  # type: (str) -> str or None
        self._load()
        for group_id, value in self._keys.items():
            if value == key:
                return group_id
        return None

    def KeyedGroups(self):  # type: () -> dict
        """ {本地分组 Id: 服务器上的键}（拷贝）"""
        self._load()
        return dict(self._keys)

    def MyKeys(self):  # type: () -> set
        """ 自己在这个存档的服务器上用过的键：起过的、传过的 """
        self._load()
        return set(self._keys.values()) | set(self._uploaded)

    # 写
# ======================================================================================================================
    def SaveSub(self, entry):  # type: (dict) -> bool
        """
        存一个拿下来的分组（同一个键的换掉，状态位不给的照旧）；个数或字数满了先挤掉最早的「已下架」，还不够就存不进。返回存没存进去
        """
        self._load()
        old = self.Sub(entry.get("key") if isinstance(entry, dict) else None)
        merged = dict(old or {})
        merged.update(entry or {})
        sub = normalize_sub(merged)
        if sub is None:
            return False
        sub["size"] = len(content_text(sub))
        others = [item for item in self._subs if item["key"] != sub["key"]]
        total = sum(item["size"] for item in others) + sub["size"]
        evicted = []
        while total > MAX_SUBS_SIZE or (old is None and len(others) - len(evicted) >= MAX_SUBS):
            victim = next((item for item in others if item["gone"] and item not in evicted), None)
            if victim is None:
                return False
            evicted.append(victim)
            total -= victim["size"]
        for victim in evicted:
            self._subs.remove(victim)
        if old is not None:
            self._subs[self._subs.index(old)] = sub
        else:
            self._subs.append(sub)
        changed = page_ids(old) | page_ids(sub)
        for victim in evicted:
            changed |= page_ids(victim)
        self._persist(changed, content=[sub["key"]] + [victim["key"] for victim in evicted])
        return True

    def UpdateSub(self, key, **fields):  # type: (str, ...) -> bool
        """ 改状态位（subscribed / enabled / unified / gone / rev / digest）；返回改没改（只写索引）"""
        old = self.Sub(key)
        if old is None:
            return False
        merged = dict(old)
        for name in ("subscribed", "enabled", "unified", "gone", "rev", "digest", "name", "desc", "owner_name"):
            if name in fields:
                merged[name] = fields[name]
        sub = normalize_sub(merged)
        if sub == old:
            return False
        self._subs[self._subs.index(old)] = sub
        self._persist(page_ids(sub))
        return True

    def RemoveSub(self, key):  # type: (str) -> bool
        old = self.Sub(key)
        if old is None:
            return False
        self._subs.remove(old)
        self._persist(page_ids(old), content=[key])
        return True

    def SetUploaded(self, key, digest, server_digest=""):  # type: (str, str, str) -> None
        """ 传上去了：记下本地这一版的指纹与服务器回的指纹 """
        self._load()
        record = {"l": valid_digest(digest), "s": valid_digest(server_digest)}
        if record["l"] and self._uploaded.get(key) != record:
            self._uploaded[key] = record
            self._persist(set(), keys=(KEY_UPLOADED,))

    def ForgetUploaded(self, key):  # type: (str) -> None
        self._load()
        if self._uploaded.pop(key, None) is not None:
            self._persist(set(), keys=(KEY_UPLOADED,))

    def AssignKey(self, group_id, key):  # type: (str, str) -> None
        """ 本地分组在这个存档的服务器上用这个键 """
        self._load()
        group_id, key = _ident(group_id), _ident(key)
        if group_id and key and self._keys.get(group_id) != key:
            self._keys[group_id] = key
            self._persist(set(), keys=(KEY_KEYS,))

    def ForgetKey(self, group_id):  # type: (str) -> None
        """ 这个本地分组不再用原来的键（分组删了；被操作员撤下了，再共享要起新键）"""
        self._load()
        if self._keys.pop(group_id, None) is not None:
            self._persist(set(), keys=(KEY_KEYS,))

    # 改动通知
# ======================================================================================================================
    def AddListener(self, listener):  # type: (callable) -> None
        """ listener(页面 Id 的集合)：这些页面（拿下来的分组里的，带服务器上的键）登记可能变了；有 LISTENER_ALL 是整张表都可能变了 """
        if callable(listener) and listener not in self._listeners:
            self._listeners.append(listener)

    def RemoveListener(self, listener):  # type: (callable) -> None
        if listener in self._listeners:
            self._listeners.remove(listener)

    def Flush(self, force=False):
        """ 索引与各分组的内容那几项都写下去 """
        if self._store is None:
            return True
        written = self._store.Flush(force)
        for store in self._contents.values():
            written = store.Flush(force) and written
        return written


UserShareManager = __UserShareManager()
