#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站评论爬虫 · Ember 焰火版
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
设计哲学：温暖 · 大字体 · 自适应 · 零边框 · 纯净分层
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re, json, csv, math, time, queue, shutil, sqlite3, threading, os as _os, webbrowser, requests
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, filedialog, font as tkfont
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from bilibili_api import video, Credential, sync, user as bili_user
from bilibili_api.dynamic import Dynamic
from bilibili_api.comment import get_comments_lazy, CommentResourceType, OrderType, Comment
from bilibili_api.video import VideoDownloadURLDataDetecter


# ═══════════════════════════════════════════════════════════════
#  Ember Design Tokens
# ═══════════════════════════════════════════════════════════════

class Color:
    """暖色系 · 高对比 · 呼吸感"""
    void    = "#F0EFED"   # 画布 · 暖灰
    card    = "#FFFFFF"   # 卡片 · 纯白
    fill    = "#F7F6F4"   # 填充区 · 微暖
    hover   = "#EBE9E5"  # 悬停 · 暖灰
    line    = "#E2DFDA"   # 分割线 · 浅暖
    title   = "#1E1C1A"   # 标题 · 暖黑
    body    = "#3D3B38"   # 正文 · 深灰
    muted   = "#8B8884"   # 辅助 · 中灰
    dim     = "#B8B5B0"   # 占位 · 浅灰
    accent  = "#E2573A"   # 强调 · 焰火橙
    glow    = "#FF6B4A"   # 发光 · 亮橙
    red     = "#D03A2A"
    green   = "#2A8C5A"


# ═══════════════════════════════════════════════════════════════
#  自适应字体系统
# ═══════════════════════════════════════════════════════════════

FONT_FAMILY = "Segoe UI"

class FontSys:
    """带缩放的字体管理 · 窗口宽度 < 1000: 小号 · >1200: 大号 · 中间平滑"""

    BASE_WIDTH = 1060  # 设计基准宽度

    def __init__(self):
        self.scale = 1.0        # 当前缩放比
        self.refs = {}          # name -> tkfont.Font

        # 字体定义 {name: (size_pt, weight)}
        self._specs = {
            "big":    (22, "bold"),
            "title":  (16, "bold"),
            "head":   (13, "bold"),
            "body":   (12, "normal"),
            "small":  (10, "normal"),
            "tiny":   (9, "normal"),
            "mono":   (11, "normal"),
            "btn":    (11, "bold"),
            "btn_s":  (10, "normal"),
            "input":  (12, "normal"),
        }

    def rebuild(self, window_width):
        """根据窗口宽度重建所有字体"""
        s = max(0.78, min(1.35, window_width / self.BASE_WIDTH))
        if abs(s - self.scale) < 0.03:
            return  # 变化太小，跳过
        self.scale = s
        for name, (pt, wgt) in self._specs.items():
            sz = max(8, int(round(pt * s)))
            if name in self.refs:
                self.refs[name].configure(size=sz)
            else:
                self.refs[name] = tkfont.Font(
                    family=FONT_FAMILY, size=sz, weight=wgt
                )

    def get(self, name):
        return self.refs.get(name, tkfont.Font())

    def size(self, name):
        if name in self.refs:
            return self.refs[name].actual()["size"]
        return 10


# ── 全局单例 ──
_fonts = FontSys()


# ═══════════════════════════════════════════════════════════════
#  全局 ttk 样式引擎
# ═══════════════════════════════════════════════════════════════

def _rebuild_styles(scale=1.0):
    """根据当前缩放参数重建全套样式"""
    s = ttk.Style()
    s.theme_use("clam")

    def f(pt, w="normal"):
        return (FONT_FAMILY, max(8, int(round(pt * scale))), w)

    C = Color

    s.configure(".", font=f(12), background=C.void)

    s.configure("TFrame", background=C.void)
    s.configure("Card.TFrame", background=C.card)
    s.configure("Fill.TFrame", background=C.fill)

    s.configure("TLabel", background=C.card, foreground=C.body)
    s.configure("CardTitle.TLabel", font=f(13, "bold"), foreground=C.title)
    s.configure("CardLabel.TLabel", font=f(12), foreground=C.body)
    s.configure("CardSub.TLabel", font=f(10), foreground=C.muted)
    s.configure("CardDim.TLabel", font=f(10), foreground=C.dim)
    s.configure("Muted.TLabel", font=f(10), foreground=C.muted, background=C.void)

    s.configure("TButton",
                font=f(11, "bold"),
                background=C.accent, foreground="white",
                borderwidth=0, padding=(20, 9), relief="flat")
    s.map("TButton",
          background=[("active", C.glow), ("disabled", C.dim)],
          foreground=[("disabled", "white")])

    s.configure("Second.TButton",
                font=f(10),
                background=C.fill, foreground=C.body,
                borderwidth=0, padding=(14, 7))
    s.map("Second.TButton",
          background=[("active", C.hover)])

    s.configure("Ghost.TButton",
                font=f(10),
                background=C.void, foreground=C.muted,
                borderwidth=0, padding=(10, 5))
    s.map("Ghost.TButton",
          background=[("active", C.hover)], foreground=[("active", C.body)])

    s.configure("Danger.TButton",
                font=f(11, "bold"),
                background=C.red, foreground="white",
                borderwidth=0, padding=(16, 9))
    s.map("Danger.TButton",
          background=[("active", "#E05040"), ("disabled", C.dim)])

    s.configure("TEntry",
                font=f(12),
                fieldbackground=C.fill, foreground=C.body,
                insertcolor=C.accent,
                borderwidth=0, padding=(10, 8))

    s.configure("TCombobox",
                font=f(11),
                fieldbackground=C.fill, foreground=C.body,
                arrowcolor=C.muted,
                borderwidth=0, padding=(8, 6))

    s.configure("TCheckbutton",
                font=f(11), background=C.card, foreground=C.body)

    s.configure("TProgressbar",
                background=C.accent, troughcolor=C.hover,
                borderwidth=0, thickness=8)

    s.configure("TSeparator", background=C.line)

    s.configure("Vertical.TScrollbar",
                background=C.line, troughcolor=C.void,
                arrowcolor=C.dim, borderwidth=0, width=10)
    s.map("Vertical.TScrollbar",
          background=[("active", C.accent)])

    return s


# ═══════════════════════════════════════════════════════════════
#  自定义 Canvas 进度条
# ═══════════════════════════════════════════════════════════════

class ProgressBar(Canvas):
    """圆角胶囊进度条 · 纯 Canvas 自绘"""

    def __init__(self, master, **kw):
        super().__init__(master, height=8, highlightthickness=0, **kw)
        self._pct = 0

    def set(self, pct):
        self._pct = pct
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 10:
            return
        h = 8
        r = h // 2
        # 轨道
        self.create_oval(0, 0, h, h, fill=Color.hover, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=Color.hover, outline="")
        self.create_oval(w - h, 0, w, h, fill=Color.hover, outline="")
        # 填充
        if self._pct > 0:
            fw = max(h, int(w * self._pct / 100))
            self.create_oval(0, 0, h, h, fill=Color.accent, outline="")
            if fw > r:
                self.create_rectangle(r, 0, fw - r, h, fill=Color.accent, outline="")
            if fw > w - h:
                self.create_oval(w - h, 0, w, h, fill=Color.accent, outline="")
            else:
                self.create_oval(fw - h, 0, fw, h, fill=Color.accent, outline="")
            # 百分比文字
            if fw > 50:
                self.create_text(fw // 2, h // 2, text=f"{int(self._pct)}%",
                                 fill="white", font=_fonts.get("tiny"),
                                 anchor=CENTER)


# ═══════════════════════════════════════════════════════════════
#  Cookie 持久化
# ═══════════════════════════════════════════════════════════════

_COOKIE_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "bilibili_cookie.txt")


def _save_cookie(cookie_str):
    try:
        with open(_COOKIE_PATH, "w", encoding="utf-8") as f:
            f.write(cookie_str)
    except Exception:
        pass


def _load_cookie():
    try:
        if _os.path.exists(_COOKIE_PATH):
            with open(_COOKIE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


# ═══════════════════════════════════════════════════════════════
#  浏览器 Cookie 读取 (Windows)
#  新版 Chrome (v127+) 使用 v20 加密，SQLite 直读无法解密。
#  唯一可靠方式：用户在 Chrome DevTools 手动复制。
# ═══════════════════════════════════════════════════════════════

def _read_browser_cookie():
    """尝试自动读取 Cookie（Chrome 关闭时 SQLite 直读；新版 Chrome 很可能失败）"""
    needed = {'SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid', 'buvid3', 'buvid4'}

    # ── 方法 1: browser_cookie3（新版 Chrome 需管理员权限）──
    try:
        import browser_cookie3
        for _fn in [browser_cookie3.chrome, browser_cookie3.edge]:
            try:
                cj = _fn(domain_name='bilibili.com')
                pairs = [f'{c.name}={c.value}' for c in cj if c.name in needed]
                if pairs:
                    return '; '.join(pairs)
            except Exception:
                pass
    except ImportError:
        pass

    # ── 方法 2: Chrome 关闭时 SQLite 直读 ──
    if not _chrome_is_running():
        r = _try_read_via_sqlite(needed)
        if r:
            return r

    return ''


def _chrome_is_running():
    import subprocess
    try:
        r = subprocess.run('tasklist /FI "IMAGENAME eq chrome.exe" 2>NUL',
                           capture_output=True, shell=True)
        return b'chrome.exe' in r.stdout.lower()
    except Exception:
        return False


def _try_read_via_sqlite(needed):
    """Chrome 关闭时直接读 SQLite（仅 v10/v11 格式有效，v20 需 COM 接口无法直解）"""
    import json, base64, ctypes, ctypes.wintypes
    try:
        key = _crypto_key_for('Google\\Chrome')
    except Exception:
        try:
            key = _crypto_key_for('Microsoft\\Edge')
        except Exception:
            return ''
    for db in _find_cookie_dbs():
        r = _read_cookie_db(db, key, needed)
        if r:
            return r
    return ''


def _crypto_key_for(browser):
    import json, base64, ctypes, ctypes.wintypes
    local_state = _os.path.expandvars(
        rf'%LOCALAPPDATA%\{browser}\User Data\Local State'
    )
    with open(local_state, 'r', encoding='utf-8') as f:
        enc_key_b64 = json.load(f)['os_crypt']['encrypted_key']
    enc_key = base64.b64decode(enc_key_b64)[5:]

    class DB(ctypes.Structure):
        _fields_ = [('cb', ctypes.wintypes.DWORD),
                     ('pb', ctypes.wintypes.LPVOID)]
    bi = DB(len(enc_key), ctypes.cast(
        ctypes.create_string_buffer(enc_key, len(enc_key)),
        ctypes.wintypes.LPVOID))
    bo = DB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)
    ):
        raise OSError('CryptUnprotectData failed')
    key = ctypes.string_at(bo.pb, bo.cb)
    return key


def _find_cookie_dbs():
    paths = []
    for browser in ['Google\\Chrome', 'Microsoft\\Edge']:
        base = _os.path.expandvars(rf'%LOCALAPPDATA%\{browser}\User Data')
        if _os.path.isdir(base):
            for p in ['Default', 'Profile 1', 'Profile 2']:
                fp = _os.path.join(base, p, 'Network', 'Cookies')
                if _os.path.isfile(fp):
                    paths.append(fp)
    return paths


def _read_cookie_db(db_path, key, needed):
    tmp = db_path + '.tmp'
    try:
        shutil.copy2(db_path, tmp)
    except OSError:
        return ''
    try:
        conn = sqlite3.connect(tmp)
        rows = conn.execute(
            "SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%bilibili.com'"
        ).fetchall()
        conn.close()
        pairs = {}
        for n, v in rows:
            if n in needed and v:
                try:
                    if v[:3] in (b'v10', b'v11', b'v20'):
                        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                        val = AESGCM(key).decrypt(v[3:15], v[15:], None).decode('utf-8')
                    else:
                        val = _dpapi_decrypt_raw(v)
                    if val:
                        pairs[n] = val
                except Exception:
                    pass
        if 'SESSDATA' in pairs:
            return '; '.join(f'{k}={v}' for k, v in pairs.items())
    except Exception:
        return ''
    finally:
        try:
            _os.unlink(tmp)
        except Exception:
            pass
    return ''


def _dpapi_decrypt_raw(enc):
    import ctypes, ctypes.wintypes
    class DB(ctypes.Structure):
        _fields_ = [('cb', ctypes.wintypes.DWORD),
                     ('pb', ctypes.wintypes.LPVOID)]
    bi = DB(len(enc), ctypes.cast(
        ctypes.create_string_buffer(enc, len(enc)),
        ctypes.wintypes.LPVOID))
    bo = DB()
    if ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)
    ):
        r = ctypes.string_at(bo.pb, bo.cb).decode('utf-8', errors='ignore')
        return r
    return ''


# ═══════════════════════════════════════════════════════════════
#  Bilibili API
# ═══════════════════════════════════════════════════════════════

_SORT_MAP = {0: OrderType.TIME, 1: OrderType.LIKE, 2: OrderType.LIKE}


def _parse_cookie_to_credential(cookie_str: str) -> Credential:
    fields = {}
    if cookie_str:
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                fields[k.strip()] = v.strip()
        if "SESSDATA" not in fields and "=" not in cookie_str:
            fields["SESSDATA"] = cookie_str
    return Credential(
        sessdata=fields.get("SESSDATA", ""),
        bili_jct=fields.get("bili_jct", ""),
        buvid3=fields.get("buvid3", ""),
        buvid4=fields.get("buvid4", ""),
        dedeuserid=fields.get("DedeUserID", ""),
    )


class BilibiliAPI:
    REQUEST_DELAY = 1.0

    def __init__(self, cookie=""):
        self._credential = _parse_cookie_to_credential(cookie)

    @staticmethod
    def parse_video_id(u):
        u = u.strip()
        m = re.search(r"BV[a-zA-Z0-9]{10}", u)
        if m:
            return (None, m.group())
        m = re.search(r"av(\d+)", u, re.IGNORECASE)
        if m:
            return (int(m.group(1)), None)
        if u.isdigit():
            return (int(u), None)
        if u.startswith("BV") and len(u) == 12:
            return (None, u)
        return (None, None)

    @staticmethod
    def parse_dynamic_id(u):
        """从动态链接或纯数字提取动态ID"""
        u = u.strip()
        m = re.search(r'(?:t\.bilibili\.com|bilibili\.com/opus)/(\d+)', u)
        if m:
            return m.group(1)
        if u.isdigit():
            return u
        return None

    def get_video_info(self, aid=None, bvid=None):
        v = video.Video(aid=aid, bvid=bvid, credential=self._credential)
        info = sync(v.get_info())
        return {
            "title": info["title"],
            "aid": info["aid"],
            "bvid": info["bvid"],
            "reply_count": info.get("stat", {}).get("reply", 0),
        }

    def get_dynamic_rid(self, dynamic_id):
        """获取动态的 oid 和 CommentResourceType"""
        d = Dynamic(dynamic_id, credential=self._credential)
        oid = sync(d.get_rid())
        resource_type = CommentResourceType.DYNAMIC
        try:
            info = sync(d.get_info())
            # comment_type 位于 info.item.basic.comment_type
            item = info.get("item") or {}
            basic = item.get("basic") or {}
            ct = basic.get("comment_type", 0)
            if ct == 12:
                resource_type = CommentResourceType.ARTICLE
            elif ct == 11:
                resource_type = CommentResourceType.DYNAMIC_DRAW
            elif ct == 17:
                resource_type = CommentResourceType.DYNAMIC
            elif ct == 1:
                resource_type = CommentResourceType.VIDEO
            elif ct:
                # 尝试按值获取
                try:
                    resource_type = CommentResourceType(ct)
                except Exception:
                    resource_type = CommentResourceType.DYNAMIC
        except Exception:
            resource_type = CommentResourceType.DYNAMIC
        return oid, resource_type

    def fetch_comments(self, oid, sort=2, max_pages=None, cb=None, stop_check=None, resource_type=CommentResourceType.VIDEO):
        order = _SORT_MAP.get(sort, OrderType.LIKE)
        all_c, offset, page = [], "", 0
        while True:
            if stop_check and stop_check():
                break
            time.sleep(self.REQUEST_DELAY)
            try:
                d = sync(get_comments_lazy(
                    oid=oid, type_=resource_type,
                    offset=offset, order=order, credential=self._credential,
                ))
            except Exception as e:
                raise RuntimeError(f"获取评论失败: {e}")
            page += 1
            replies = d.get("replies") or []
            parsed = _parse_replies(replies)
            all_c.extend(parsed)
            cursor = d.get("cursor", {})
            raw_end = cursor.get("is_end", True)
            is_end = raw_end if isinstance(raw_end, bool) else str(raw_end).lower() in ("true", "1")
            next_offset = (cursor.get("pagination_reply") or {}).get("next_offset", "")
            all_cnt = cursor.get("all_count", 0)
            if cb:
                cb(page, all_cnt, len(all_c))
            if max_pages and page >= max_pages:
                break
            if is_end or not next_offset or not replies:
                break
            offset = next_offset
        if sort == 1:
            all_c.sort(key=lambda x: x["likes"], reverse=True)
        return all_c

    def fetch_sub_replies(self, oid, root_rpid, max_sub=20, stop_check=None, resource_type=CommentResourceType.VIDEO):
        subs, page = [], 1
        while True:
            if stop_check and stop_check():
                break
            time.sleep(self.REQUEST_DELAY)
            try:
                cmt = Comment(
                    oid=oid, type_=resource_type,
                    rpid=root_rpid, credential=self._credential,
                )
                d = sync(cmt.get_sub_comments(page_index=page, page_size=20))
            except Exception:
                break
            replies = d.get("replies") or []
            if not replies or page >= max_sub:
                break
            subs.extend(_parse_sub_replies(replies, root_rpid))
            page += 1
        return subs

    def get_video_detail_summary(self, aid=None, bvid=None):
        v = video.Video(aid=aid, bvid=bvid, credential=self._credential)
        result = {"aid": aid, "bvid": bvid}
        try:
            info = sync(v.get_info())
            owner_mid = info.get("owner", {}).get("mid", 0)
            result.update({
                "title": info.get("title", ""),
                "desc": info.get("desc", ""),
                "pic": info.get("pic", ""),
                "owner": {"mid": owner_mid, "name": info.get("owner", {}).get("name", "")},
                "stat": info.get("stat", {}),
                "aid": info.get("aid", aid),
                "bvid": info.get("bvid", bvid),
            })
            try:
                u = bili_user.User(uid=owner_mid, credential=self._credential)
                rel = sync(u.get_relation_info())
                result["owner"]["follower"] = rel.get("follower", 0)
            except Exception:
                result["owner"]["follower"] = 0
        except Exception as e:
            result["error"] = f"获取基本信息失败: {e}"
        try:
            tags = sync(v.get_tags())
            result["tags"] = [t.get("tag_name", "") for t in tags]
        except Exception:
            result["tags"] = []
        try:
            pages = sync(v.get_pages())
            result["pages"] = [{
                "cid": p.get("cid", 0),
                "page": p.get("page", 0),
                "part": p.get("part", ""),
                "duration": p.get("duration", 0),
            } for p in pages]
        except Exception:
            result["pages"] = []
        return result

    def get_download_urls(self, cid, aid=None, bvid=None):
        v = video.Video(aid=aid, bvid=bvid, credential=self._credential)
        try:
            raw = sync(v.get_download_url(cid=cid))
            detecter = VideoDownloadURLDataDetecter(raw)
            stream_objects = detecter.detect_all()
            streams = []
            dash_data = raw.get("dash", {})
            q_to_bw = {}
            for dv in dash_data.get("video", []):
                qid = dv.get("id", 0)
                bw = dv.get("bandwidth", 0)
                if qid not in q_to_bw or bw > q_to_bw[qid]:
                    q_to_bw[qid] = bw
            for s_obj in stream_objects:
                entry = {"url": s_obj.url}
                if hasattr(s_obj, 'video_quality'):
                    entry["type"] = "dash_video"
                    q = s_obj.video_quality
                    qv = q.value if hasattr(q, 'value') else 0
                    entry["quality"] = qv
                    entry["description"] = q.name.lstrip("_") if hasattr(q, 'name') else str(q)
                    if hasattr(s_obj, 'video_codecs'):
                        entry["codecs"] = s_obj.video_codecs.value if hasattr(s_obj.video_codecs, 'value') else str(s_obj.video_codecs)
                        entry["description"] += f" ({entry['codecs']})"
                    entry["size"] = q_to_bw.get(qv, 0)
                elif hasattr(s_obj, 'audio_quality'):
                    entry["type"] = "dash_audio"
                    q = s_obj.audio_quality
                    qv = q.value if hasattr(q, 'value') else 0
                    entry["quality"] = qv
                    entry["description"] = q.name.lstrip("_") if hasattr(q, 'name') else str(q)
                    for da in dash_data.get("audio", []):
                        if da.get("id") == qv:
                            entry["size"] = da.get("bandwidth", 0)
                            break
                else:
                    entry["type"] = "flv"
                    entry["description"] = "FLV"
                streams.append(entry)
            is_dash = bool(raw.get("dash"))
            is_flv = raw.get("durl") is not None
            if is_flv and not streams:
                for d in raw.get("durl", []):
                    streams.append({
                        "type": "flv",
                        "url": d.get("url", ""),
                        "description": "FLV",
                        "size": d.get("size", 0),
                    })
            return {"is_dash": is_dash, "is_flv": is_flv, "streams": streams}
        except Exception as e:
            return {"is_dash": False, "is_flv": False, "streams": [], "error": str(e)}


def _parse_replies(replies):
    return [{
        "rpid": r.get("rpid", 0),
        "user": r.get("member", {}).get("uname", "未知"),
        "mid": r.get("member", {}).get("mid", ""),
        "content": _clean(r.get("content", {}).get("message", "")),
        "likes": r.get("like", 0),
        "reply_count": r.get("rcount", 0),
        "time": datetime.fromtimestamp(r.get("ctime", 0)).strftime("%Y-%m-%d %H:%M"),
        "ctime": r.get("ctime", 0),
    } for r in replies]


def _parse_sub_replies(replies, parent_rpid):
    return [{
        "rpid": r.get("rpid", 0), "parent": parent_rpid,
        "user": r.get("member", {}).get("uname", "未知"),
        "mid": r.get("member", {}).get("mid", ""),
        "content": _clean(r.get("content", {}).get("message", "")),
        "likes": r.get("like", 0), "reply_count": r.get("rcount", 0),
        "time": datetime.fromtimestamp(r.get("ctime", 0)).strftime("%Y-%m-%d %H:%M"),
        "ctime": r.get("ctime", 0),
    } for r in replies]


def _clean(t):
    t = t.replace("\r", "").replace("\n", " ")
    return re.sub(r"\s{2,}", " ", t).strip()


# ═══════════════════════════════════════════════════════════════
#  导出
# ═══════════════════════════════════════════════════════════════

class Exporter:
    @staticmethod
    def _fns():
        return ["rpid", "parent", "user", "mid", "content", "likes", "reply_count", "time"]

    @staticmethod
    def csv(comments, path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=Exporter._fns())
            w.writeheader()
            for c in comments:
                w.writerow({k: c.get(k, "") for k in Exporter._fns()})

    @staticmethod
    def json(comments, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

    @staticmethod
    def txt(comments, path):
        with open(path, "w", encoding="utf-8") as f:
            for i, c in enumerate(comments, 1):
                p = "  [二级]" if c.get("parent") else ""
                f.write(f"[{i}]{p} {c['user']}  {c['time']}\n  +{c['likes']}  {c['reply_count']}\u56de\u590d\n  {c['content']}\n\n")

    @staticmethod
    def excel(comments, path):
        try:
            import openpyxl
        except ImportError:
            Exporter.csv(comments, path.rsplit(".", 1)[0] + ".csv")
            messagebox.showinfo("提示", "已导出为 CSV")
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "B站评论"
        ws.append(["rpid", "父ID", "用户", "UID", "内容", "点赞", "回复", "时间"])
        for c in comments:
            ws.append([c["rpid"], c.get("parent", ""), c["user"], c["mid"],
                       c["content"], c["likes"], c["reply_count"], c["time"]])
        for i, w in enumerate([12, 14, 18, 14, 60, 8, 8, 20], 1):
            ws.column_dimensions[chr(64 + i)].width = w
        wb.save(path)


# ═══════════════════════════════════════════════════════════════
#  EmberApp · 主界面
# ═══════════════════════════════════════════════════════════════
#
#     ┌──────────────────────────────────────────────┐
#     │  B站评论爬虫 · Ember          ⋮              │  ← 暖灰顶栏
#     ├────────────────────┬─────────────────────────┤
#     │  爬取设置          │  AI 深度分析            │
#     │  [视频链接] [开始] │  ┌──────────────────┐   │
#     │  排序 页数 二级    │  │  分析结果区域     │   │
#     │  Cookie _________ │  │                   │   │
#     │  API Key ________ │  │                   │   │
#     │                    │  │                   │   │
#     │  视频信息          │  └──────────────────┘   │
#     │  ─────────────    │                         │
#     │  进度 ████████░░  │                         │
#     └────────────────────┴─────────────────────────┘
#     │  运行日志  ⋮                                │
#     └──────────────────────────────────────────────┘
#
# ═══════════════════════════════════════════════════════════════

class EmberApp:
    P = 24  # 基础间距单元

    def __init__(self, root):
        self.root = root
        self.root.title("B站评论爬虫 · Ember")
        self.root.geometry("1060x760")
        self.root.minsize(880, 640)
        self.root.configure(bg=Color.void)

        # ── 状态 ──
        self.comments = []
        self.video_info = None
        self.is_running = False
        self._stop_event = None
        self._fetch_thread = None
        self._fetch_start_time = 0
        self.task_queue = queue.Queue()
        self._download_streams = []
        # 下载状态
        self._download_cancel_event = threading.Event()
        self._download_thread = None
        self._downloading = False
        self._ffmpeg_available = None   # None=未检查, True/False

        self._saved_cookie = _load_cookie()
        self._api_key_path = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "deepseek_api_key.txt"
        )

        # ── 建立字体系统 ──
        _fonts.rebuild(self.root.winfo_width() or 1060)

        # ── 建立样式 ──
        self._reapply_styles()

        # ── 构建 UI ──
        self._build()

        # ── 绑定缩放 ──
        self.root.bind("<Configure>", self._on_resize, add="+")

        # ── 加载持久化 ──
        if self._saved_cookie:
            self.cookie_entry.insert(0, self._saved_cookie)
        sk = self._load_api_key()
        if sk:
            self.api_key_entry.insert(0, sk)

        self._log("就绪")
        self._poll_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── 字体缩放 ──────────────────────────────────

    def _reapply_styles(self):
        self.style = _rebuild_styles(_fonts.scale if hasattr(_fonts, 'scale') and _fonts.scale else 1.0)

    def _on_resize(self, e):
        if e.widget is not self.root:
            return
        old_s = _fonts.scale
        _fonts.rebuild(e.width)
        if abs(_fonts.scale - old_s) > 0.03:
            self._reapply_styles()
            self._log(f"字体缩放: {_fonts.scale:.0%}")

    # ─── 布局 ──────────────────────────────────────

    def _build(self):
        # 顶栏
        self._build_topbar()

        # 主体
        body = Frame(self.root, bg=Color.void)
        body.pack(fill=BOTH, expand=True, padx=self.P, pady=(self.P, 0))

        left = Frame(body, bg=Color.void)
        left.pack(side=LEFT, fill=Y, padx=(0, self.P))

        self._build_settings(left)
        self._build_info(left)

        right = Frame(body, bg=Color.void)
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        notebook = ttk.Notebook(right)
        notebook.pack(fill=BOTH, expand=True)
        tab1 = Frame(notebook, bg=Color.card)
        notebook.add(tab1, text="AI 深度分析")
        self._build_analysis(tab1)
        tab2 = Frame(notebook, bg=Color.card)
        notebook.add(tab2, text="视频解析")
        self._build_video_analysis_tab(tab2)
        self._notebook = notebook

        # 日志 + 底栏
        self._build_log()

    # ─── 顶栏 ──────────────────────────────────────

    def _build_topbar(self):
        bar = Frame(self.root, bg=Color.card, height=52)
        bar.pack(fill=X)
        bar.pack_propagate(False)

        Frame(bar, bg=Color.line, height=1).pack(fill=X, side=BOTTOM)

        inner = Frame(bar, bg=Color.card)
        inner.pack(fill=BOTH, expand=True, padx=self.P)

        Label(inner, text="B站评论爬虫", font=_fonts.get("title"),
              bg=Color.card, fg=Color.title).pack(side=LEFT)

        # 版本标签
        ver = Frame(inner, bg=Color.fill)
        Label(ver, text="Ember", font=_fonts.get("tiny"),
              bg=Color.fill, fg=Color.muted).pack(padx=8, pady=2)
        ver.pack(side=LEFT, padx=(8, 0), pady=(4, 0))

    # ─── 设置区 ────────────────────────────────────

    def _build_settings(self, parent):
        card = Frame(parent, bg=Color.card)
        card.pack(fill=X, pady=(0, 12))

        inner = Frame(card, bg=Color.card)
        inner.pack(fill=X, padx=self.P, pady=18)

        # 标题
        hdr = Frame(inner, bg=Color.card)
        hdr.pack(fill=X, pady=(0, 14))
        Label(hdr, text="爬取设置", font=_fonts.get("head"),
              bg=Color.card, fg=Color.title).pack(side=LEFT)
        Label(hdr, text="CRAWL", font=_fonts.get("tiny"),
              bg=Color.card, fg=Color.dim).pack(side=RIGHT, pady=(2, 0))

        # ── 模式 ──
        Label(inner, text="模式", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(anchor=W, pady=(0, 4))
        self.mode_var = StringVar(value="视频评论")
        mode_cb = ttk.Combobox(inner, textvariable=self.mode_var,
                               values=["视频评论", "动态评论"],
                               state="readonly", width=10)
        mode_cb.pack(anchor=W, pady=(0, 10))
        mode_cb.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())

        # ── 输入 ──
        self.url_label = Label(inner, text="视频链接 / BV号", font=_fonts.get("small"),
                               bg=Color.card, fg=Color.muted)
        self.url_label.pack(anchor=W, pady=(0, 4))
        self.url_entry = ttk.Entry(inner, font=_fonts.get("input"))
        self.url_entry.pack(fill=X, pady=(0, 2))
        self.url_entry.bind("<Return>", lambda e: self._start_fetch())
        self.url_hint = Label(inner, text="支持 BV号 / av号 / 完整链接",
                              font=_fonts.get("tiny"), bg=Color.card, fg=Color.dim)
        self.url_hint.pack(anchor=W, pady=(0, 10))

        # ── 按钮 ──
        br = Frame(inner, bg=Color.card)
        br.pack(fill=X, pady=(0, 14))
        self.start_btn = ttk.Button(br, text="开始爬取", command=self._start_fetch)
        self.start_btn.pack(side=LEFT, padx=(0, 6))
        self.stop_btn = ttk.Button(br, text="停止", style="Danger.TButton",
                                   command=self._stop_fetch, state=DISABLED)
        self.stop_btn.pack(side=LEFT)

        Frame(inner, bg=Color.line, height=1).pack(fill=X, pady=(0, 14))

        # ── 排序 + 页数 + 二级 ──
        opt = Frame(inner, bg=Color.card)
        opt.pack(fill=X, pady=(0, 10))
        Label(opt, text="排序", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self.sort_var = StringVar(value="2")
        ttk.Combobox(opt, textvariable=self.sort_var,
                     values=["0=时间", "1=点赞", "2=热度"],
                     state="readonly", width=8).pack(side=LEFT, padx=6)

        Label(opt, text="页数", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT, padx=(8, 4))
        self.max_pages_var = StringVar(value="")
        ttk.Entry(opt, textvariable=self.max_pages_var, width=5).pack(side=LEFT)
        Label(opt, text="(全部)", font=_fonts.get("tiny"),
              bg=Color.card, fg=Color.dim).pack(side=LEFT, padx=(3, 0))

        self.sub_var = BooleanVar(value=True)
        ttk.Checkbutton(opt, text="二级回复", variable=self.sub_var).pack(side=RIGHT)

        # ── Cookie ──
        Label(inner, text="Cookie", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(anchor=W, pady=(0, 4))
        ck = Frame(inner, bg=Color.card)
        ck.pack(fill=X, pady=(0, 10))
        self.cookie_entry = ttk.Entry(ck, font=_fonts.get("small"))
        self.cookie_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(ck, text="自动获取", style="Second.TButton",
                   command=self._get_cookie).pack(side=LEFT)

        # ── API Key ──
        Label(inner, text="DeepSeek API Key", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(anchor=W, pady=(0, 4))
        ak = Frame(inner, bg=Color.card)
        ak.pack(fill=X)
        self.api_key_entry = ttk.Entry(ak, show="*", font=_fonts.get("small"))
        self.api_key_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(ak, text="显示", style="Second.TButton",
                   command=self._toggle_key).pack(side=LEFT, padx=(0, 4))
        ttk.Button(ak, text="保存", style="Second.TButton",
                   command=self._save_and_verify_key).pack(side=LEFT)

    # ─── 信息区 ────────────────────────────────────

    def _build_info(self, parent):
        card = Frame(parent, bg=Color.card)
        card.pack(fill=X)

        inner = Frame(card, bg=Color.card)
        inner.pack(fill=X, padx=self.P, pady=18)

        # 标题
        self.info_header_label = Label(inner, text="视频信息", font=_fonts.get("head"),
                                       bg=Color.card, fg=Color.title)
        self.info_header_label.pack(anchor=W, pady=(0, 12))

        self.vid_title = Label(inner, text="", font=_fonts.get("body"),
                               bg=Color.card, fg=Color.body,
                               wraplength=280, anchor=W, justify=LEFT)
        self.vid_title.pack(fill=X, pady=(0, 2))

        self.vid_stat = Label(inner, text="", font=_fonts.get("small"),
                              bg=Color.card, fg=Color.muted, anchor=W)
        self.vid_stat.pack(fill=X)

        Frame(inner, bg=Color.line, height=1).pack(fill=X, pady=(14, 14))

        # 进度
        Label(inner, text="进度", font=_fonts.get("head"),
              bg=Color.card, fg=Color.title).pack(anchor=W, pady=(0, 8))

        self.progress_bar = ProgressBar(inner, bg=Color.card)
        self.progress_bar.pack(fill=X)

        self.count_label = Label(inner, text="", font=_fonts.get("small"),
                                 bg=Color.card, fg=Color.muted, anchor=W)
        self.count_label.pack(fill=X, pady=(4, 0))

        self.status_label = Label(inner, text="", font=_fonts.get("small"),
                                  bg=Color.card, fg=Color.muted, anchor=W)
        self.status_label.pack(fill=X, pady=(4, 0))

    # ─── AI 分析区 ─────────────────────────────────

    def _build_analysis(self, parent):
        card = Frame(parent, bg=Color.card)
        card.pack(fill=BOTH, expand=True)

        inner = Frame(card, bg=Color.card)
        inner.pack(fill=BOTH, expand=True, padx=self.P, pady=18)

        hdr = Frame(inner, bg=Color.card)
        hdr.pack(fill=X, pady=(0, 12))

        Label(hdr, text="AI 深度分析", font=_fonts.get("head"),
              bg=Color.card, fg=Color.title).pack(side=LEFT)
        Label(hdr, text="DeepSeek", font=_fonts.get("tiny"),
              bg=Color.card, fg=Color.dim).pack(side=RIGHT, pady=(2, 0))

        self.ai_status = Label(inner, text="", font=_fonts.get("small"),
                               bg=Color.card, fg=Color.muted)
        self.ai_status.pack(anchor=E, pady=(0, 6))

        tf = Frame(inner, bg=Color.card)
        tf.pack(fill=BOTH, expand=True)

        self.analysis = Text(tf, wrap=WORD, borderwidth=0,
                             font=_fonts.get("body"), padx=16, pady=12,
                             state=DISABLED, relief=FLAT)
        self.analysis.pack(fill=BOTH, expand=True, side=LEFT)

        sc = ttk.Scrollbar(tf, orient=VERTICAL, command=self.analysis.yview)
        sc.pack(side=RIGHT, fill=Y)
        self.analysis.configure(yscrollcommand=sc.set)

        self._show_placeholder()

    def _show_placeholder(self):
        self.analysis.configure(state=NORMAL)
        self.analysis.delete("1.0", END)
        self.analysis.configure(bg=Color.fill, fg=Color.dim)
        self.analysis.insert("1.0",
            "\n    输入 DeepSeek API Key 并点击「保存」，\n"
            "    爬取完成将自动调用 AI 舆情分析。\n\n"
            "    · 情感倾向分析\n"
            "    · 高频关键词提取\n"
            "    · 代表性评论\n"
            "    · 舆论总结"
        )
        self.analysis.configure(state=DISABLED)

    # ─── 视频解析 Tab ──────────────────────────────

    def _build_video_analysis_tab(self, parent):
        card = Frame(parent, bg=Color.card)
        card.pack(fill=BOTH, expand=True)
        inner = Frame(card, bg=Color.card)
        inner.pack(fill=BOTH, expand=True, padx=self.P, pady=18)

        # 按钮行
        btn_row = Frame(inner, bg=Color.card)
        btn_row.pack(fill=X, pady=(0, 12))
        self._v_parse_btn = ttk.Button(btn_row, text="解析视频信息",
                                       command=self._start_video_parse)
        self._v_parse_btn.pack(side=LEFT, padx=(0, 6))
        self._v_download_btn = ttk.Button(btn_row, text="获取下载链接",
                                          command=self._start_get_download,
                                          state=DISABLED)
        self._v_download_btn.pack(side=LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="清空", style="Second.TButton",
                   command=self._clear_video_analysis).pack(side=LEFT)

        # 视频详情
        detail_lf = LabelFrame(inner, text="视频详情", font=_fonts.get("head"),
                               bg=Color.card, fg=Color.title, padx=14, pady=10)
        detail_lf.pack(fill=BOTH, expand=True, pady=(0, 10))

        title_frame = Frame(detail_lf, bg=Color.card)
        title_frame.pack(fill=X, pady=(0, 6))
        Label(title_frame, text="标题:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT, anchor=N)
        self._v_title_label = Label(title_frame, text="", font=_fonts.get("body"),
                                    bg=Color.card, fg=Color.body, wraplength=400,
                                    anchor=W, justify=LEFT)
        self._v_title_label.pack(side=LEFT, fill=X, expand=True, padx=(6, 0))

        desc_frame = Frame(detail_lf, bg=Color.card)
        desc_frame.pack(fill=X, pady=(0, 6))
        Label(desc_frame, text="简介:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT, anchor=N)
        self._v_desc_text = Text(desc_frame, height=4, wrap=WORD, borderwidth=0,
                                 font=_fonts.get("small"), padx=8, pady=4,
                                 relief=FLAT, bg=Color.fill, fg=Color.body,
                                 state=DISABLED)
        self._v_desc_text.pack(side=LEFT, fill=X, expand=True, padx=(6, 0))

        cover_frame = Frame(detail_lf, bg=Color.card)
        cover_frame.pack(fill=X, pady=(0, 6))
        Label(cover_frame, text="封面:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self._v_cover_label = Label(cover_frame, text="", font=_fonts.get("small"),
                                    bg=Color.card, fg=Color.accent, cursor="hand2")
        self._v_cover_label.pack(side=LEFT, padx=(6, 0))
        self._v_cover_label.bind("<Button-1>", lambda e: self._open_cover_url())

        up_frame = Frame(detail_lf, bg=Color.card)
        up_frame.pack(fill=X, pady=(0, 6))
        Label(up_frame, text="UP主:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self._v_up_label = Label(up_frame, text="", font=_fonts.get("small"),
                                 bg=Color.card, fg=Color.body)
        self._v_up_label.pack(side=LEFT, padx=(6, 0))

        stat_frame = Frame(detail_lf, bg=Color.card)
        stat_frame.pack(fill=X, pady=(0, 6))
        Label(stat_frame, text="统计:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self._v_stat_label = Label(stat_frame, text="", font=_fonts.get("small"),
                                   bg=Color.card, fg=Color.body)
        self._v_stat_label.pack(side=LEFT, padx=(6, 0))

        tag_frame = Frame(detail_lf, bg=Color.card)
        tag_frame.pack(fill=X, pady=(0, 6))
        Label(tag_frame, text="标签:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT, anchor=N)
        self._v_tag_label = Label(tag_frame, text="", font=_fonts.get("small"),
                                  bg=Color.card, fg=Color.body, wraplength=400,
                                  justify=LEFT)
        self._v_tag_label.pack(side=LEFT, padx=(6, 0))

        page_label = Label(detail_lf, text="分P列表:", font=_fonts.get("small"),
                           bg=Color.card, fg=Color.muted)
        page_label.pack(anchor=W, pady=(0, 4))
        tree_frame = Frame(detail_lf, bg=Color.card)
        tree_frame.pack(fill=BOTH, expand=True)
        self._v_page_tree = ttk.Treeview(tree_frame,
                                         columns=("cid", "page", "part", "duration"),
                                         show="headings", height=5)
        self._v_page_tree.heading("cid", text="CID")
        self._v_page_tree.heading("page", text="P")
        self._v_page_tree.heading("part", text="标题")
        self._v_page_tree.heading("duration", text="时长(秒)")
        self._v_page_tree.column("cid", width=80)
        self._v_page_tree.column("page", width=40, anchor=CENTER)
        self._v_page_tree.column("part", width=200)
        self._v_page_tree.column("duration", width=80, anchor=CENTER)
        self._v_page_tree.pack(side=LEFT, fill=BOTH, expand=True)
        tree_sc = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self._v_page_tree.yview)
        tree_sc.pack(side=RIGHT, fill=Y)
        self._v_page_tree.configure(yscrollcommand=tree_sc.set)

        # ── 视频下载 ──
        dl_lf = LabelFrame(inner, text="视频下载", font=_fonts.get("head"),
                           bg=Color.card, fg=Color.title, padx=14, pady=10)
        dl_lf.pack(fill=X)

        dl_row = Frame(dl_lf, bg=Color.card)
        dl_row.pack(fill=X, pady=(0, 8))
        Label(dl_row, text="分P:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self._v_page_combo = ttk.Combobox(dl_row, state="readonly", width=10)
        self._v_page_combo.pack(side=LEFT, padx=(6, 16))
        self._v_page_combo.bind("<<ComboboxSelected>>", self._on_quality_select)
        Label(dl_row, text="清晰度:", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self._v_quality_combo = ttk.Combobox(dl_row, state="readonly", width=20)
        self._v_quality_combo.pack(side=LEFT, padx=(6, 0))
        self._v_quality_combo.bind("<<ComboboxSelected>>", self._on_quality_select)

        dl_btn_row = Frame(dl_lf, bg=Color.card)
        dl_btn_row.pack(fill=X, pady=(0, 6))
        ttk.Button(dl_btn_row, text="复制链接", style="Second.TButton",
                   command=self._copy_download_url).pack(side=LEFT, padx=(0, 4))
        self._dl_start_btn = ttk.Button(dl_btn_row, text="下载视频",
                                        command=self._start_download)
        self._dl_start_btn.pack(side=LEFT, padx=(0, 4))
        self._dl_cancel_btn = ttk.Button(dl_btn_row, text="取消下载",
                                         style="Danger.TButton",
                                         command=self._cancel_download,
                                         state=DISABLED)
        self._dl_cancel_btn.pack(side=LEFT)

        dl_progress_frame = Frame(dl_lf, bg=Color.card)
        dl_progress_frame.pack(fill=X, pady=(0, 4))
        self._dl_progress = ProgressBar(dl_progress_frame, bg=Color.card)
        self._dl_progress.pack(side=LEFT, fill=X, expand=True)
        self._dl_status_label = Label(dl_progress_frame, text="",
                                      font=_fonts.get("small"),
                                      bg=Color.card, fg=Color.accent)
        self._dl_status_label.pack(side=LEFT, padx=(8, 0))

        self._dl_log_label = Label(dl_lf, text="", font=_fonts.get("tiny"),
                                   bg=Color.card, fg=Color.muted, anchor=W)
        self._dl_log_label.pack(fill=X, pady=(0, 6))

        self._v_url_text = Text(dl_lf, height=3, wrap=WORD, borderwidth=0,
                                font=("Consolas", 9), padx=8, pady=6,
                                relief=FLAT, bg=Color.fill, fg=Color.body,
                                state=DISABLED)
        self._v_url_text.pack(fill=X)

    def _open_cover_url(self):
        url = self._v_cover_label.cget("text")
        if url:
            webbrowser.open(url)

    def _copy_download_url(self):
        url = self._v_url_text.get("1.0", END).strip()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self._log("下载链接已复制")

    def _on_quality_select(self, event=None):
        if self._downloading:
            self._log("[下载] 请先完成或取消当前下载")
            return
        sel = self._v_quality_combo.get()
        if not sel or not self._download_streams:
            return
        for s in self._download_streams:
            desc = s.get("description", s.get("type", "未知"))
            q = s.get("quality", "")
            label = f"{desc} ({q})" if q else desc
            if label == sel:
                url = s.get("url", "")
                self._v_url_text.configure(state=NORMAL)
                self._v_url_text.delete("1.0", END)
                self._v_url_text.insert("1.0", url)
                self._v_url_text.configure(state=DISABLED)
                break
        if not self._downloading:
            self._dl_progress.set(0)
            self._dl_status_label.config(text="")
            self._dl_log_label.config(text="")

    def _clear_video_analysis(self):
        if self._downloading:
            self._download_cancel_event.set()
            if self._download_thread and self._download_thread.is_alive():
                self._download_thread.join(timeout=2)
            self._downloading = False
        self.video_detail = None
        self._download_streams = []
        self._v_title_label.config(text="")
        self._v_desc_text.configure(state=NORMAL)
        self._v_desc_text.delete("1.0", END)
        self._v_desc_text.configure(state=DISABLED)
        self._v_cover_label.config(text="")
        self._v_up_label.config(text="")
        self._v_stat_label.config(text="")
        self._v_tag_label.config(text="")
        for row in self._v_page_tree.get_children():
            self._v_page_tree.delete(row)
        self._v_page_combo.set("")
        self._v_page_combo["values"] = []
        self._v_quality_combo.set("")
        self._v_quality_combo["values"] = []
        self._v_download_btn.configure(state=DISABLED)
        self._v_url_text.configure(state=NORMAL)
        self._v_url_text.delete("1.0", END)
        self._v_url_text.configure(state=DISABLED)
        self._dl_progress.set(0)
        self._dl_status_label.config(text="")
        self._dl_log_label.config(text="")
        self._log("视频解析已清空")

    # ─── 日志区 ────────────────────────────────────

    def _build_log(self):
        frame = Frame(self.root, bg=Color.card)
        frame.pack(fill=X, pady=(12, 0))

        Frame(frame, bg=Color.line, height=1).pack(fill=X, padx=self.P)

        hdr = Frame(frame, bg=Color.card)
        hdr.pack(fill=X, padx=self.P, pady=(8, 6))
        Label(hdr, text="运行日志", font=_fonts.get("small"),
              bg=Color.card, fg=Color.muted).pack(side=LEFT)
        self.log_cnt = Label(hdr, text="", font=_fonts.get("tiny"),
                             bg=Color.card, fg=Color.dim)
        self.log_cnt.pack(side=RIGHT)

        lf = Frame(frame, bg=Color.fill)
        lf.pack(fill=X, padx=self.P, pady=(0, self.P))

        self.log_text = Text(lf, height=3, wrap=WORD, borderwidth=0,
                             font=("Consolas", 9), padx=14, pady=10,
                             state=DISABLED, relief=FLAT,
                             bg=Color.fill, fg=Color.muted,
                             insertbackground=Color.body)
        self.log_text.pack(fill=X, expand=True, side=LEFT)

        ls = ttk.Scrollbar(lf, orient=VERTICAL, command=self.log_text.yview)
        ls.pack(side=RIGHT, fill=Y)
        self.log_text.configure(yscrollcommand=ls.set)

        # 底栏（导出）
        bar = Frame(self.root, bg=Color.void, height=36)
        bar.pack(fill=X)
        inner = Frame(bar, bg=Color.void)
        inner.pack(fill=BOTH, expand=True, padx=self.P)

        Label(inner, text="导出:", font=_fonts.get("tiny"),
              bg=Color.void, fg=Color.dim).pack(side=LEFT, padx=(0, 6))
        for fmt, label in [("csv", "CSV"), ("json", "JSON"),
                           ("txt", "TXT"), ("excel", "Excel")]:
            ttk.Button(inner, text=label, style="Ghost.TButton",
                      command=lambda f=fmt: self._export(f)).pack(side=LEFT, padx=(2, 0))

    # ─── 辅助 ──────────────────────────────────────

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(END, line)
        self.log_text.see(END)
        self.log_text.configure(state=DISABLED)
        c = self.log_text.get("1.0", END).strip()
        self.log_cnt.config(text=f"{len(c.split(chr(10)))} 行")

    def _set_running(self, v):
        self.is_running = v
        self.start_btn.configure(state=DISABLED if v else NORMAL)
        self.stop_btn.configure(state=NORMAL if v else DISABLED)

    def _toggle_key(self):
        e = self.api_key_entry
        e.configure(show="" if e.cget("show") == "*" else "*")

    def _on_mode_change(self):
        """切换视频/动态模式时更新标签文字"""
        mode = self.mode_var.get()
        if mode == "动态评论":
            self.url_label.config(text="动态链接 / 动态ID")
            self.url_hint.config(text="支持 t.bilibili.com / opus / 纯数字ID")
            self.info_header_label.config(text="动态信息")
        else:
            self.url_label.config(text="视频链接 / BV号")
            self.url_hint.config(text="支持 BV号 / av号 / 完整链接")
            self.info_header_label.config(text="视频信息")

    def _get_cookie(self):
        """自动获取 Cookie：强杀 Chrome → DrissionPage 启动 → 用户登录 → CDP 读取"""
        self._log("准备获取 Cookie...")
        threading.Thread(target=self._dp_cookie_worker, daemon=True).start()

    def _dp_cookie_worker(self):
        """后台：杀 Chrome → 启动浏览器 → 等用户登录 → CDP 读 Cookie"""
        import subprocess, os as _os
        try:
            # ── 1. 强杀 Chrome ──
            self.task_queue.put(("log", "关闭 Chrome..."))
            subprocess.run('taskkill /F /T /IM chrome.exe 2>NUL',
                           capture_output=True, shell=True)
            time.sleep(0.8)

            # ── 2. DrissionPage 启动（用原 Profile 保留密码/书签）──
            from DrissionPage import ChromiumPage, ChromiumOptions
            co = ChromiumOptions()
            co.auto_port()
            co.set_argument('--disable-session-crashed-bubble')
            profile = _os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
            co.set_argument(f'--user-data-dir={profile}')
            co.set_argument('--profile-directory=Default')

            page = ChromiumPage(co)
            self._dp_page = page  # 存下来给对话框用
            page.get('https://passport.bilibili.com/login')
            time.sleep(2)

            # ── 3. 通知用户登录 ──
            self.task_queue.put(("log", "请在浏览器中登录 B站，完成后点确认"))
            self.task_queue.put(("cookie_prompt", None))

        except Exception as e:
            self.task_queue.put(("log", f"Cookie 获取失败: {e}"))

    def _dp_cookie_prompt_dialog(self):
        """登录等待对话框"""
        self._cookie_dialog = Toplevel(self.root)
        self._cookie_dialog.title("登录 B站")
        self._cookie_dialog.geometry("400x220")
        self._cookie_dialog.resizable(False, False)
        self._cookie_dialog.configure(bg=Color.card)

        inner = Frame(self._cookie_dialog, bg=Color.card)
        inner.pack(fill=BOTH, expand=True, padx=28, pady=24)

        Label(inner, text="请登录 B站", font=_fonts.get("head"),
              bg=Color.card, fg=Color.title).pack(anchor=W, pady=(0, 12))

        Label(inner, text="浏览器窗口已打开 B站登录页。\n登录完成后，点击下方按钮读取 Cookie。",
              font=_fonts.get("body"), bg=Color.card, fg=Color.body,
              wraplength=340, justify=LEFT).pack(anchor=W, pady=(0, 20))

        btn = Frame(inner, bg=Color.card)
        btn.pack(fill=X)
        ttk.Button(btn, text="已登录，读取 Cookie",
                   command=self._dp_read_cookie).pack(side=LEFT, padx=(0, 8))
        ttk.Button(btn, text="取消", style="Second.TButton",
                   command=self._dp_cancel).pack(side=LEFT)

    def _dp_read_cookie(self):
        """CDP 读取全部 Cookie（含 HttpOnly）"""
        import json as _json
        self._cookie_dialog.destroy()
        self._log("读取 Cookie...")
        try:
            result = self._dp_page.run_cdp('Network.getAllCookies')
            cookies = result if isinstance(result, (list, dict)) else _json.loads(result)
            all_c = cookies.get('cookies', cookies) if isinstance(cookies, dict) else cookies
            bili = [c for c in all_c if 'bilibili' in c.get('domain', '')]

            needed = {'SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid', 'buvid3', 'buvid4'}
            pairs = {}
            for c in bili:
                n = c.get('name', '')
                if n in needed:
                    pairs[n] = c.get('value', '')

            if 'SESSDATA' in pairs:
                cookie_str = '; '.join(f'{k}={v}' for k, v in pairs.items())
                self.task_queue.put(("cookie_done", cookie_str))
                self.task_queue.put(("log", f"Cookie 已读取 ({len(cookie_str)} 字符)"))
            else:
                self.task_queue.put(("log", "未检测到登录，请确保已在浏览器中登录 B站"))

            self._dp_page.quit()
        except Exception as e:
            self.task_queue.put(("log", f"读取 Cookie 失败: {e}"))

    def _dp_cancel(self):
        self._cookie_dialog.destroy()
        try:
            self._dp_page.quit()
        except Exception:
            pass
        self._log("已取消")

    def _load_api_key(self):
        try:
            if _os.path.exists(self._api_key_path):
                with open(self._api_key_path, encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def _save_api_key(self, key):
        try:
            with open(self._api_key_path, "w", encoding="utf-8") as f:
                f.write(key)
        except Exception:
            pass

    def _save_and_verify_key(self):
        key = self.api_key_entry.get().strip()
        if not key:
            self._log("Key 不能为空")
            return
        self._save_api_key(key)
        self._log("Key 已保存")
        threading.Thread(target=self._verify_key_worker, args=(key,), daemon=True).start()

    def _verify_key_worker(self, key):
        try:
            req = Request("https://api.deepseek.com/v1/models",
                          headers={"Authorization": f"Bearer {key}"})
            with urlopen(req, timeout=10) as r:
                json.loads(r.read())
            self.task_queue.put(("key_ok", None))
        except Exception as e:
            self.task_queue.put(("key_error", str(e)))

    # ─── 爬取 ──────────────────────────────────────

    def _start_fetch(self):
        mode = self.mode_var.get()
        u = self.url_entry.get().strip()
        if not u:
            self._log("请输入链接或ID")
            return

        cookie = self.cookie_entry.get().strip()
        sort = int(self.sort_var.get()[0])
        mp = self.max_pages_var.get().strip()
        max_pages = int(mp) if mp.isdigit() else None
        fetch_sub = self.sub_var.get()

        if mode == "动态评论":
            dynamic_id = BilibiliAPI.parse_dynamic_id(u)
            if not dynamic_id:
                self._log("无法识别动态ID")
                return
            worker_target = self._fetch_dynamic_worker
            worker_args = (dynamic_id, sort, max_pages, cookie, fetch_sub)
            self.status_label.config(text="获取动态信息...")
        else:
            aid, bvid = BilibiliAPI.parse_video_id(u)
            if not aid and not bvid:
                self._log("无法识别视频号")
                return
            worker_target = self._fetch_worker
            worker_args = (aid, bvid, sort, max_pages, cookie, fetch_sub)
            self.status_label.config(text="获取视频信息...")

        if self._stop_event is not None:
            self._stop_event.set()
        if self._fetch_thread and self._fetch_thread.is_alive():
            self._log("等待上一轮结束...")
            self._fetch_thread.join(timeout=5)

        self._stop_event = threading.Event()
        self._fetch_start_time = time.time()
        self._set_running(True)
        self.progress_bar.set(0)
        self.count_label.config(text="")

        self._fetch_thread = threading.Thread(
            target=worker_target,
            args=(self._stop_event,) + worker_args,
            daemon=True,
        )
        self._fetch_thread.start()

    def _fetch_worker(self, se, aid, bvid, sort, max_pages, cookie, fetch_sub):
        try:
            api = BilibiliAPI(cookie=cookie)
            self.task_queue.put(("status", "获取视频信息..."))
            info = api.get_video_info(aid=aid, bvid=bvid)
            self.task_queue.put(("video_info", info))

            def cb(pg, total, cnt):
                pct = min(99, (cnt / total * 100)) if total else 0
                self.task_queue.put(("progress", pct))
                self.task_queue.put(("status", f"已爬 {cnt}/{total}"))
                self.task_queue.put(("count", cnt))

            comments = api.fetch_comments(oid=info["aid"], sort=sort,
                                          max_pages=max_pages, cb=cb,
                                          stop_check=se.is_set)

            if fetch_sub and comments and not se.is_set():
                for idx, c in enumerate(comments):
                    if se.is_set():
                        break
                    self.task_queue.put(("status", f"子评论 {idx+1}/{len(comments)}"))
                    if c.get("reply_count", 0) > 0:
                        comments.extend(
                            api.fetch_sub_replies(oid=info["aid"], root_rpid=c["rpid"],
                                                  stop_check=se.is_set)
                        )
                    self.task_queue.put(("count", len(comments)))

            self.task_queue.put(("done", (comments, time.time() - self._fetch_start_time)))
        except Exception as e:
            self.task_queue.put(("error", (str(e), time.time() - self._fetch_start_time)))

    def _fetch_dynamic_worker(self, se, dynamic_id, sort, max_pages, cookie, fetch_sub):
        """动态评论区爬取 Worker"""
        try:
            api = BilibiliAPI(cookie=cookie)
            self.task_queue.put(("status", "获取动态信息..."))
            oid, resource_type = api.get_dynamic_rid(dynamic_id)
            self.task_queue.put(("dynamic_info", {
                "title": f"动态 {dynamic_id}",
                "reply_count": 0,
                "bvid": f"动态 {dynamic_id}",
            }))

            def cb(pg, total, cnt):
                pct = min(99, (cnt / total * 100)) if total else 0
                self.task_queue.put(("progress", pct))
                self.task_queue.put(("status", f"已爬 {cnt}/{total}"))
                self.task_queue.put(("count", cnt))

            comments = api.fetch_comments(oid=oid, sort=sort,
                                          max_pages=max_pages, cb=cb,
                                          stop_check=se.is_set,
                                          resource_type=resource_type)

            if fetch_sub and comments and not se.is_set():
                for idx, c in enumerate(comments):
                    if se.is_set():
                        break
                    self.task_queue.put(("status", f"子评论 {idx+1}/{len(comments)}"))
                    if c.get("reply_count", 0) > 0:
                        comments.extend(
                            api.fetch_sub_replies(oid=oid, root_rpid=c["rpid"],
                                                  stop_check=se.is_set,
                                                  resource_type=resource_type)
                        )
                    self.task_queue.put(("count", len(comments)))

            self.task_queue.put(("done", (comments, time.time() - self._fetch_start_time)))
        except Exception as e:
            self.task_queue.put(("error", (str(e), time.time() - self._fetch_start_time)))

    def _stop_fetch(self):
        if self._stop_event is not None:
            self._stop_event.set()
        self._set_running(False)
        self.status_label.config(text="已停止")
        self._log("已停止")

    # ─── 视频解析 Worker ───────────────────────────

    def _start_video_parse(self):
        u = self.url_entry.get().strip()
        if not u:
            self._log("请输入视频链接或ID")
            return
        aid, bvid = BilibiliAPI.parse_video_id(u)
        if not aid and not bvid:
            self._log("无法识别视频号")
            return
        self._notebook.select(1)
        self._log("解析视频信息...")
        self._v_parse_btn.configure(state=DISABLED)
        cookie = self.cookie_entry.get().strip()
        threading.Thread(target=self._video_parse_worker,
                         args=(cookie, aid, bvid), daemon=True).start()

    def _video_parse_worker(self, cookie, aid, bvid):
        try:
            api = BilibiliAPI(cookie=cookie)
            data = api.get_video_detail_summary(aid=aid, bvid=bvid)
            self.task_queue.put(("video_detail_done", data))
        except Exception as e:
            self.task_queue.put(("video_detail_error", str(e)))

    def _start_get_download(self):
        sel = self._v_page_combo.get()
        if not sel:
            self._log("请先选择分P")
            return
        aid = None; bvid = None; cid = None
        if self.video_detail:
            aid = self.video_detail.get("aid")
            bvid = self.video_detail.get("bvid")
            m = re.match(r'P(\d+)', sel)
            if m:
                page_num = int(m.group(1))
                for p in (self.video_detail.get("pages") or []):
                    if p.get("page") == page_num:
                        cid = p.get("cid")
                        break
        if not cid:
            self._log("无法获取分P CID")
            return
        self._log("获取下载链接...")
        self._v_download_btn.configure(state=DISABLED)
        cookie = self.cookie_entry.get().strip()
        threading.Thread(target=self._download_url_worker,
                         args=(cookie, cid, aid, bvid), daemon=True).start()

    def _download_url_worker(self, cookie, cid, aid, bvid):
        try:
            api = BilibiliAPI(cookie=cookie)
            data = api.get_download_urls(cid=cid, aid=aid, bvid=bvid)
            self.task_queue.put(("download_urls_done", data))
        except Exception as e:
            self.task_queue.put(("download_urls_error", str(e)))

    # ─── 视频下载方法 ────────────────────────────

    @staticmethod
    def _format_bytes(size):
        if size == 0: return "0 B"
        units = ["B", "KB", "MB", "GB"]
        i = 0; fsize = float(size)
        while fsize >= 1024 and i < len(units) - 1:
            fsize /= 1024; i += 1
        return f"{fsize:.1f} {units[i]}"

    def _check_ffmpeg(self):
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available
        local_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg.exe")
        if _os.path.exists(local_path):
            self._ffmpeg_available = local_path
        else:
            self._ffmpeg_available = shutil.which('ffmpeg')
        if not self._ffmpeg_available:
            self._log("[下载] 未检测到 FFmpeg，DASH 格式将无法合并音视频")
        else:
            self._log(f"[下载] 检测到 FFmpeg: {self._ffmpeg_available}")
        return self._ffmpeg_available

    def _start_download(self):
        if self._downloading:
            self._log("[下载] 已有下载任务正在进行")
            return
        page_sel = self._v_page_combo.get()
        quality_sel = self._v_quality_combo.get()
        if not page_sel or not quality_sel:
            self._log("[下载] 请先选择分 P 和清晰度")
            return
        if not self._download_streams:
            self._log("[下载] 请先获取下载链接")
            return

        # 找到选中的 stream 和同质量备选
        selected_stream = None; target_quality = None
        for s in self._download_streams:
            desc = s.get("description", s.get("type", "未知"))
            q = s.get("quality", "")
            label = f"{desc} ({q})" if q else desc
            if label == quality_sel:
                selected_stream = s; target_quality = q; break
        if not selected_stream:
            self._log("[下载] 未找到对应的流数据")
            return

        # 收集同清晰度备选流，Head 检测 URL 可用性
        if target_quality:
            candidates = [selected_stream]
            for s in self._download_streams:
                if s.get("quality") == target_quality and s.get("type") == "dash_video" and s is not selected_stream:
                    candidates.append(s)
            if len(candidates) > 1:
                h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}
                for c in candidates:
                    url = c.get("url", "")
                    if not url: continue
                    try:
                        r = requests.head(url, headers=h, timeout=5, allow_redirects=True)
                        if r.status_code == 200:
                            if c is not selected_stream:
                                self._log(f"[下载] 当前流不可用，切换到: {c.get('description', '?')}")
                            selected_stream = c
                            break
                    except Exception: continue
                else:
                    self._log("[下载] 该清晰度所有流均不可访问")
                    return

        # 判断 DASH
        is_dash = False; dash_audio_stream = None
        stream_type = selected_stream.get("type", "")
        if stream_type in ("dash_video",):
            is_dash = True
            for s in self._download_streams:
                if s.get("type") == "dash_audio":
                    dash_audio_stream = s; break
            if not dash_audio_stream:
                self._log("[下载] DASH 视频需要音频流，但未找到")
                return
            if not self._check_ffmpeg():
                ret = messagebox.askyesno("FFmpeg 缺失",
                    "该视频为 DASH 格式（分离音视频），\n需要 FFmpeg 来合并。\n\n是否只下载视频画面（不含音频）？")
                if not ret: return
                self._log("[下载] 仅下载视频流（无音频）")
                is_dash = False; dash_audio_stream = None

        # 文件名
        title = (self.video_detail or {}).get("title", "video")
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        default_ext = ".mp4" if is_dash else (".flv" if stream_type == "flv" else ".mp4")
        quality_name = quality_sel.split("(")[0].strip()
        page_part = page_sel.split(" - ")[0].strip() if " - " in page_sel else "P1"
        initial_name = f"{safe_title}_{page_part}_{quality_name}{default_ext}"

        path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            initialfile=initial_name,
            filetypes=[("视频文件", "*.mp4;*.flv"), ("MP4", "*.mp4"), ("FLV", "*.flv"), ("所有文件", "*.*")]
        )
        if not path: return
        parent_dir = _os.path.dirname(path)
        if parent_dir and not _os.access(parent_dir, _os.W_OK):
            self._log(f"[下载] 目录不可写: {parent_dir}"); return

        self._downloading = True
        self._download_cancel_event.clear()
        self._dl_start_btn.configure(state=DISABLED)
        self._dl_cancel_btn.configure(state=NORMAL)
        self._dl_progress.set(0)
        self._dl_status_label.config(text="准备下载...")
        self._dl_log_label.config(text="")
        self._download_thread = threading.Thread(
            target=self._download_master_worker,
            args=(selected_stream, dash_audio_stream, path, is_dash), daemon=True)
        self._download_thread.start()
        self._log(f"[下载] 开始下载至: {path}")

    def _stream_download(self, stream_info, output_path, start_pct, end_pct):
        url = stream_info.get("url", "")
        if not url: raise ValueError("Stream URL 为空")
        total_size = stream_info.get("size", 0) or 0
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}
        resume_pos = _os.path.getsize(output_path) if _os.path.exists(output_path) else 0
        max_retries = 3; last_error = None
        for attempt in range(max_retries):
            if self._download_cancel_event.is_set(): return
            try:
                rh = headers.copy()
                if resume_pos > 0: rh['Range'] = f'bytes={resume_pos}-'
                resp = requests.get(url, headers=rh, stream=True, timeout=(10, 30))
                if resp.status_code == 403 and attempt < max_retries - 1:
                    self.task_queue.put(("download_status", f"遇到 403，重试 ({attempt+1}/{max_retries})"))
                    time.sleep(2 * (attempt + 1)); continue
                resp.raise_for_status()
                mode = 'ab' if (resume_pos > 0 and 'Content-Range' in resp.headers) else 'wb'
                downloaded = resume_pos if mode == 'ab' else 0
                with open(output_path, mode) as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if self._download_cancel_event.is_set(): return
                        if chunk:
                            f.write(chunk); downloaded += len(chunk)
                            if total_size > 0:
                                pct = start_pct + (end_pct - start_pct) * min(downloaded / total_size, 1.0)
                                self.task_queue.put(("download_progress", pct))
                                self.task_queue.put(("download_bytes", (downloaded, total_size)))
                return
            except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.task_queue.put(("download_status", f"网络错误，重试 ({attempt+1}/{max_retries})"))
                    time.sleep(3 * (attempt + 1))
                else:
                    raise RuntimeError(f"下载失败，已重试 {max_retries} 次: {e}")
        if last_error: raise RuntimeError(f"下载失败: {last_error}")

    def _merge_with_ffmpeg(self, video_path, audio_path, output_path):
        import subprocess, tempfile
        if not _os.path.exists(video_path): raise FileNotFoundError(f"视频流不存在: {video_path}")
        if not _os.path.exists(audio_path): raise FileNotFoundError(f"音频流不存在: {audio_path}")
        ffmpeg_path = self._ffmpeg_available or shutil.which('ffmpeg')
        if not ffmpeg_path: raise RuntimeError("FFmpeg 未找到")
        cmd = [ffmpeg_path, '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'copy', '-y', output_path]
        self.task_queue.put(("download_status", "正在合并音视频..."))
        # 用临时文件接 stderr，避免管道满导致死锁
        err_path = output_path + ".fferr"
        try:
            with open(err_path, 'w') as err_f:
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_f,
                                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                while process.poll() is None:
                    if self._download_cancel_event.is_set():
                        process.terminate()
                        try: process.wait(timeout=5)
                        except subprocess.TimeoutExpired: process.kill()
                        raise RuntimeError("合并被取消")
                    time.sleep(0.5)
            if process.returncode != 0:
                with open(err_path, encoding='utf-8', errors='ignore') as f:
                    err_text = f.read()[:300]
                raise RuntimeError(f"FFmpeg 合并失败 (code={process.returncode}): {err_text}")
        finally:
            try:
                if _os.path.exists(err_path): _os.unlink(err_path)
            except Exception: pass

    def _download_master_worker(self, video_stream, audio_stream, output_path, is_dash):
        import subprocess; temp_files = []
        try:
            if is_dash and video_stream and audio_stream:
                video_temp = output_path + ".video.tmp"
                audio_temp = output_path + ".audio.tmp"
                temp_files = [video_temp, audio_temp]
                self.task_queue.put(("download_status", "正在下载视频流 (0%)"))
                self._stream_download(video_stream, video_temp, 0, 40)
                if self._download_cancel_event.is_set(): self.task_queue.put(("download_cancelled", None)); return
                self.task_queue.put(("download_status", "正在下载音频流 (40%)"))
                self._stream_download(audio_stream, audio_temp, 40, 75)
                if self._download_cancel_event.is_set(): self.task_queue.put(("download_cancelled", None)); return
                self._merge_with_ffmpeg(video_temp, audio_temp, output_path)
                self.task_queue.put(("download_status", "清理临时文件 (95%)"))
                for tf in temp_files:
                    try:
                        if _os.path.exists(tf): _os.unlink(tf)
                    except Exception: pass
            else:
                self._stream_download(video_stream, output_path, 0, 95)
            if self._download_cancel_event.is_set(): self.task_queue.put(("download_cancelled", None)); return
            self.task_queue.put(("download_done", output_path))
        except Exception as e:
            self.task_queue.put(("download_error", str(e)))
            for tf in temp_files:
                try:
                    if _os.path.exists(tf): _os.unlink(tf)
                except Exception: pass
            try:
                if _os.path.exists(output_path): _os.unlink(output_path)
            except Exception: pass

    def _cancel_download(self):
        if not self._downloading: return
        self._download_cancel_event.set()
        self._dl_cancel_btn.configure(state=DISABLED)
        self._dl_status_label.config(text="正在取消...")
        self._log("[下载] 正在取消下载...")

    # ─── AI 分析 ──────────────────────────────────

    def _run_ai_analysis(self, comments, title):
        key = self._load_api_key()
        if not key:
            self.task_queue.put(("ai_done", "未配置 API Key"))
            return
        self.task_queue.put(("ai_status", "分析中..."))
        self._log("AI 分析中...")

        try:
            text = "\n".join(f"{i+1}. [{c['user']}] +{c['likes']} | {c['content']}"
                            for i, c in enumerate(comments))
            prompt = f"""你是专业舆情分析师。分析以下B站视频评论。

视频: {title}
评论数: {len(comments)}

{text}

结构化分析（中文）:
1. 情感倾向（正面/负面/中性占比）
2. 高频关键词 & 热门话题
3. 代表性评论（选3-5条）
4. 舆情总结"""

            body = json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [
                    {"role": "system", "content": "专业舆情分析师。中文输出。"},
                    {"role": "user", "content": prompt},
                ],
            }).encode()
            req = Request(
                "https://api.deepseek.com/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            )
            with urlopen(req, timeout=120) as r:
                result = json.loads(r.read())
                self.task_queue.put(("ai_done", result["choices"][0]["message"]["content"]))
        except Exception as e:
            self.task_queue.put(("ai_done", f"错误: {e}"))

    # ─── 轮询 ──────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                t, p = self.task_queue.get_nowait()
                if t == "status":
                    self.status_label.config(text=p)
                elif t == "video_info":
                    self.video_info = p
                    self.vid_title.config(text=p["title"])
                    self.vid_stat.config(text=f"{p['reply_count']} 条评论  {p['bvid']}")
                elif t == "dynamic_info":
                    self.video_info = p
                    self.vid_title.config(text=p["title"])
                    self.vid_stat.config(text=p.get("bvid", ""))
                elif t == "progress":
                    self.progress_bar.set(p)
                elif t == "count":
                    self.count_label.config(text=f"已爬取 {p} 条")
                elif t == "ai_status":
                    self.ai_status.config(text=p)
                elif t == "done":
                    comments, elapsed = p
                    try:
                        self.comments = comments
                        self._set_running(False)
                        self.progress_bar.set(100)
                        m, s = divmod(elapsed, 60)
                        dur = f"{int(m)}分{s:.1f}秒" if m else f"{s:.1f}秒"
                        self.status_label.config(text=f"完成 {len(comments)} 条  {dur}")
                        self._log(f"完成 {len(comments)} 条  {dur}")
                        title = self.video_info["title"] if self.video_info else ""
                        threading.Thread(target=self._run_ai_analysis,
                                         args=(comments, title), daemon=True).start()
                    finally:
                        self._fetch_thread = None
                elif t == "key_ok":
                    self._log("API Key 验证成功")
                elif t == "key_error":
                    self._log(f"API Key 验证失败: {p}")
                elif t == "ai_done":
                    self.analysis.configure(state=NORMAL)
                    self.analysis.delete("1.0", END)
                    self.analysis.configure(bg=Color.card, fg=Color.body)
                    self.analysis.insert("1.0", p)
                    self.analysis.configure(state=DISABLED)
                    self.ai_status.config(text="完成")
                    self._log("AI 分析完成")
                    self.status_label.config(text="AI 分析完成")
                elif t == "log":
                    self._log(p)
                elif t == "cookie_prompt":
                    self._dp_cookie_prompt_dialog()
                elif t == "cookie_done":
                    self.cookie_entry.delete(0, END)
                    self.cookie_entry.insert(0, p)
                    _save_cookie(p)
                    self._log(f"Cookie 已保存 ({len(p)} 字符)")
                elif t == "video_detail_done":
                    data = p
                    self.video_detail = data
                    self._v_parse_btn.configure(state=NORMAL)
                    self._v_title_label.config(text=data.get("title", ""))
                    self._v_desc_text.configure(state=NORMAL)
                    self._v_desc_text.delete("1.0", END)
                    self._v_desc_text.insert("1.0", data.get("desc", ""))
                    self._v_desc_text.configure(state=DISABLED)
                    self._v_cover_label.config(text=data.get("pic", ""))
                    owner = data.get("owner", {})
                    up_info = owner.get("name", "")
                    if owner.get("follower"):
                        up_info += f"  ({owner['follower']:,} 粉丝)"
                    self._v_up_label.config(text=up_info)
                    st = data.get("stat", {})
                    self._v_stat_label.config(
                        text=f"播放 {st.get('view', 0):,}  弹幕 {st.get('danmaku', 0):,}  评论 {st.get('reply', 0):,}  点赞 {st.get('like', 0):,}")
                    tags = data.get("tags", [])
                    self._v_tag_label.config(text=", ".join(tags) if tags else "无")
                    for row in self._v_page_tree.get_children():
                        self._v_page_tree.delete(row)
                    pages = data.get("pages", [])
                    page_options = []
                    for p_ in pages:
                        self._v_page_tree.insert("", END, values=(
                            p_.get("cid"), p_.get("page"), p_.get("part"), p_.get("duration")))
                        page_options.append(f"P{p_.get('page')} - {p_.get('part', '')}")
                    self._v_page_combo["values"] = page_options
                    if page_options:
                        self._v_page_combo.current(0)
                    self._v_download_btn.configure(state=NORMAL)
                    self._v_parse_btn.configure(state=NORMAL)
                    self._log(f"视频解析完成: {data.get('title', '')}")
                elif t == "video_detail_error":
                    self._v_parse_btn.configure(state=NORMAL)
                    self._log(f"视频解析失败: {p}")
                    messagebox.showerror("解析失败", p)
                elif t == "download_urls_done":
                    data = p
                    self._v_download_btn.configure(state=NORMAL)
                    error = data.get("error")
                    if error:
                        self._log(f"获取下载链接失败: {error}")
                        return
                    self._download_streams = data.get("streams", [])
                    quality_options = []
                    seen = set()
                    for s in self._download_streams:
                        desc = s.get("description", s.get("type", "未知"))
                        q = s.get("quality", "")
                        label = f"{desc} ({q})" if q else desc
                        if label not in seen:
                            seen.add(label)
                            quality_options.append(label)
                    self._v_quality_combo["values"] = quality_options
                    if quality_options:
                        self._v_quality_combo.current(0)
                        self._on_quality_select()
                    if data.get("is_dash"):
                        self._log(f"获取到 DASH 格式下载链接（{len(quality_options)} 种清晰度）")
                    else:
                        self._log(f"获取到下载链接（{len(quality_options)} 种）")
                elif t == "download_urls_error":
                    self._v_download_btn.configure(state=NORMAL)
                    self._log(f"获取下载链接失败: {p}")
                    messagebox.showerror("获取失败", p)
                # ── 下载消息 ──
                elif t == "download_progress":
                    self._dl_progress.set(p)
                elif t == "download_status":
                    self._dl_status_label.config(text=p)
                elif t == "download_bytes":
                    downloaded, total = p
                    dl_str = self._format_bytes(downloaded)
                    total_str = self._format_bytes(total) if total else "?"
                    self._dl_log_label.config(text=f"已下载: {dl_str} / {total_str}")
                elif t == "download_done":
                    path = p; self._downloading = False
                    self._dl_start_btn.configure(state=NORMAL)
                    self._dl_cancel_btn.configure(state=DISABLED)
                    self._dl_progress.set(100)
                    self._dl_status_label.config(text="下载完成")
                    self._log(f"[下载] 完成: {path}")
                elif t == "download_error":
                    err_msg = p; self._downloading = False
                    self._dl_start_btn.configure(state=NORMAL)
                    self._dl_cancel_btn.configure(state=DISABLED)
                    self._dl_progress.set(0)
                    self._dl_status_label.config(text="下载失败")
                    self._log(f"[下载] 失败: {err_msg}")
                    messagebox.showerror("下载失败", err_msg)
                elif t == "download_cancelled":
                    self._downloading = False
                    self._dl_start_btn.configure(state=NORMAL)
                    self._dl_cancel_btn.configure(state=DISABLED)
                    self._dl_progress.set(0)
                    self._dl_status_label.config(text="已取消")
                    self._log("[下载] 已取消")
                elif t == "error":
                    msg, elapsed = p
                    self._fetch_thread = None
                    self._set_running(False)
                    self._log(f"错误: {msg}")
        except queue.Empty:
            pass
        except Exception as ex:
            self._log(f"内部错误: {ex}")
        self.root.after(80, self._poll_queue)

    # ─── 导出 ──────────────────────────────────────

    def _export(self, fmt):
        if not self.comments:
            self._log("无数据")
            return
        exts = {"csv": ".csv", "json": ".json", "txt": ".txt", "excel": ".xlsx"}
        path = filedialog.asksaveasfilename(
            defaultextension=exts[fmt],
            initialfile=f"comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}{exts[fmt]}",
        )
        if not path:
            return
        try:
            {"csv": Exporter.csv, "json": Exporter.json,
             "txt": Exporter.txt, "excel": Exporter.excel}[fmt](self.comments, path)
            self._log(f"导出 {len(self.comments)} 条")
        except Exception as e:
            self._log(f"导出失败: {e}")

    def _on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    root = Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass
    app = EmberApp(root)
    root.mainloop()
