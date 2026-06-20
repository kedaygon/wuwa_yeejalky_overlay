import tkinter as tk
from tkinter import scrolledtext, messagebox
import re, json, os, sys
from typing import Optional
from wuwa_updater import check_and_update, CURRENT_VER


def get_resource(filename):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

def _ssl_context():
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_appdata_dir():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "ddaljalky")
    os.makedirs(path, exist_ok=True)
    return path

def get_data_file():
    import urllib.request, shutil
    appdata_json = os.path.join(get_appdata_dir(), "wuwa_chars.json")
    if not os.path.exists(appdata_json):
        bundled = get_resource("wuwa_chars.json")
        if os.path.exists(bundled):
            shutil.copy(bundled, appdata_json)
        else:
            try:
                api_url = "https://api.github.com/repos/kedaygon/wuwa_yeejalky_overlay/releases/latest"
                req = urllib.request.Request(api_url, headers={"User-Agent": "ddaljalky-overlay"})
                with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as r:
                    release = json.loads(r.read().decode("utf-8"))
                dl_url = None
                for asset in release.get("assets", []):
                    if asset["name"] == "wuwa_chars.json":
                        dl_url = asset["browser_download_url"]
                        break
                if dl_url:
                    req2 = urllib.request.Request(dl_url, headers={"User-Agent": "ddaljalky-overlay"})
                    with urllib.request.urlopen(req2, timeout=10, context=_ssl_context()) as r2:
                        with open(appdata_json, "wb") as f:
                            f.write(r2.read())
            except Exception as e:
                print(f"[초기 데이터 다운로드 실패] {e}")


    return appdata_json

DATA_FILE = get_data_file()
ICON_FILE  = get_resource("00085-3009505209.ico")

def _cleanup_ocr_zips():
    import glob
    pattern = os.path.join(get_appdata_dir(), "ocr_debug_*.zip")
    for p in glob.glob(pattern):
        try:
            os.remove(p)
        except Exception:
            pass

_cleanup_ocr_zips()

THEMES = {
    "default": {
        "bg":        "#1a1208",
        "hd":        "#2d1f08",
        "gold_lt":   "#e8b84b",
        "gold_dim":  "#7a5a1a",
        "orange":    "#d4631a",
        "text":      "#f0e6cc",
        "dim":       "#a09070",
        "red":       "#c8412a",
        "tbl":       "#231608",
        "tbl2":      "#2a1e0c",
        "tbl_hd":    "#3d2a0e",
        "border":    "#5a3e18",
        "white":     "#f8f0e0",
        "green":     "#4caf50",
        "cycle_bg":  "#1e1a10",
        "cycle_txt": "#d4c49a",
    },
    "dark": {
        "bg":        "#121212",
        "hd":        "#2c2c2c",
        "gold_lt":   "#bb86fc",
        "gold_dim":  "#333333",
        "orange":    "#03dac6",
        "text":      "#ffffff",
        "dim":       "#757575",
        "red":       "#cf6679",
        "tbl":       "#121212",
        "tbl2":      "#1a1a1a",
        "tbl_hd":    "#272727",
        "border":    "#383838",
        "white":     "#e8e0ff",
        "green":     "#4caf50",
        "cycle_bg":  "#1a1a1a",
        "cycle_txt": "#b3b3b3",
    },
}

def load_settings() -> dict:
    try:
        path = os.path.join(get_appdata_dir(), "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"theme": "default"}

def save_settings(settings: dict):
    try:
        path = os.path.join(get_appdata_dir(), "settings.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if "last_version" in existing and "last_version" not in settings:
                    settings["last_version"] = existing["last_version"]
            except Exception:
                pass
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except Exception:
        pass

_settings = load_settings()
C = THEMES.get(_settings.get("theme", "default"), THEMES["default"])

try:
    import ctypes
    _dpi = ctypes.windll.user32.GetDpiForSystem()
    UI_SCALE = _dpi / 96.0
except Exception:
    UI_SCALE = 1.0

def fsc(n):
    return int(round(n * UI_SCALE))


_last_log_time = {}

def log_error(context, exc, extra=None):
    import traceback, datetime, platform
    try:
        now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        key = f"{context}:{type(exc).__name__}:{str(exc)[:80]}"
        if _last_log_time.get(key, 0) > datetime.datetime.now().timestamp() - 30:
            return
        _last_log_time[key] = datetime.datetime.now().timestamp()

        log_path = os.path.join(get_appdata_dir(), "error.log")
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines)//2:])

        mon_info = ""
        try:
            import ctypes, ctypes.wintypes
            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [("cbSize",ctypes.c_ulong),("rcMonitor",ctypes.wintypes.RECT),
                            ("rcWork",ctypes.wintypes.RECT),("dwFlags",ctypes.c_ulong),
                            ("szDevice",ctypes.c_wchar*32)]
            monitors = []
            def _mon_cb(hmon, hdc, lprect, lparam):
                mi = MONITORINFOEX(); mi.cbSize = ctypes.sizeof(MONITORINFOEX)
                ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
                r = mi.rcMonitor
                dpi_x = ctypes.c_uint(); dpi_y = ctypes.c_uint()
                try: ctypes.windll.shcore.GetDpiForMonitor(hmon,0,ctypes.byref(dpi_x),ctypes.byref(dpi_y))
                except: dpi_x.value = 96
                w = r.right-r.left; h = r.bottom-r.top
                scale = round(dpi_x.value/96*100)
                primary = "(주)" if mi.dwFlags & 1 else "(서브)"
                monitors.append(f"{w}x{h} {scale}% {primary}")
                return True
            MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_ulong,ctypes.c_ulong,
                                                  ctypes.POINTER(ctypes.wintypes.RECT),ctypes.c_ulong)
            ctypes.windll.user32.EnumDisplayMonitors(None,None,MONITORENUMPROC(_mon_cb),0)
            mon_info = " | ".join(monitors)
        except Exception:
            mon_info = "모니터 정보 수집 실패"

        roi = _settings.get("roi")
        roi_str = str(roi) if roi else "미설정"
        settings_str = json.dumps({k:v for k,v in _settings.items() if k not in ("favorites",)}, ensure_ascii=False)

        lines = [
            "=" * 60,
            f"[{now}] {context}",
            f"버전: v{CURRENT_VER} | Python: {sys.version.split()[0]} | OS: {platform.system()} {platform.version()}",
            f"모니터: {mon_info}",
            f"ROI: {roi_str}",
            f"Settings: {settings_str}",
        ]
        if extra:
            for k, v in extra.items():
                v_str = str(v)[:500] if v is not None else "None"
                lines.append(f"{k}: {v_str}")
        lines.append("-" * 60)
        lines.append(traceback.format_exc().strip())
        lines.append("=" * 60)
        lines.append("")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass

def _place_beside_card(win, w, h, card, offset=0):
    win.withdraw()
    try:
        cx = card.winfo_x()
        cy = card.winfo_y()
        x = cx - w - 8
        y = cy + offset * (h + 8)
        if x < 0:
            x = cx + card.W + 8
    except Exception:
        x = 0; y = 0
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.attributes("-alpha", 1.0)

def _place_on_cursor_monitor(win, w, h):
    win.withdraw()
    try:
        import ctypes, ctypes.wintypes
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize",    ctypes.c_ulong),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork",    ctypes.wintypes.RECT),
                ("dwFlags",   ctypes.c_ulong),
            ]
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        hmon = ctypes.windll.user32.MonitorFromPoint(pt, 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        dpi_x = ctypes.c_uint(); dpi_y = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        scale = dpi_x.value / 96.0
        hmon_primary = ctypes.windll.user32.MonitorFromPoint(ctypes.wintypes.POINT(0, 0), 1)
        dpi_px = ctypes.c_uint(); dpi_py = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(hmon_primary, 0, ctypes.byref(dpi_px), ctypes.byref(dpi_py))
        primary_scale = dpi_px.value / 96.0
        cx = int((mi.rcWork.left + mi.rcWork.right) / 2 / primary_scale)
        cy = int((mi.rcWork.top  + mi.rcWork.bottom) / 2 / primary_scale)
        x = cx - w // 2
        y = cy - h // 2
    except Exception:
        x = win.winfo_screenwidth() // 2 - w // 2
        y = win.winfo_screenheight() // 2 - h // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.attributes("-alpha", 1.0)

ELEM_COLOR = {
    "응결": "#5bc8f5",
    "용융": "#e8522a",
    "전도": "#9b6abf",
    "기류": "#6abf69",
    "회절": "#d4a017",
    "인멸": "#c45faa",
}



def load_chars() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[JSON 오류] {e}")
            print(f"[경로] {DATA_FILE}")
    else:
        print(f"[파일 없음] {DATA_FILE}")
    return {}


def save_chars(chars: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)



class CharCard(tk.Toplevel):
    W = 480

    def __init__(self, master, char: dict, on_reopen=None, on_move=None, init_pos=None,
                 on_fav_toggle=None, on_fav_check=None, main_panel=None):
        super().__init__(master)
        self.char = char
        self._master = master
        self._main_panel = main_panel
        self._on_reopen = on_reopen
        self._on_move = on_move
        self._init_pos = init_pos
        self._on_fav_toggle = on_fav_toggle
        self._on_fav_check = on_fav_check
        self._dx = 0
        self._dy = 0
        self._sub_popup_count = 0

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg=C["border"])

        self._build()

        self.update_idletasks()
        try:
            import ctypes, ctypes.wintypes
            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize",    ctypes.c_ulong),
                    ("rcMonitor", ctypes.wintypes.RECT),
                    ("rcWork",    ctypes.wintypes.RECT),
                    ("dwFlags",   ctypes.c_ulong),
                ]
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            hmon_cursor = ctypes.windll.user32.MonitorFromPoint(pt, 2)
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            ctypes.windll.user32.GetMonitorInfoW(hmon_cursor, ctypes.byref(mi))
            dpi_x = ctypes.c_uint(); dpi_y = ctypes.c_uint()
            ctypes.windll.shcore.GetDpiForMonitor(
                hmon_cursor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
            scale = dpi_x.value / 96.0
            mon_right = int(mi.rcWork.right  / scale)
            mon_top   = int(mi.rcWork.top    / scale)
            hmon_primary = ctypes.windll.user32.MonitorFromPoint(
                ctypes.wintypes.POINT(0, 0), 1)
            dpi_px = ctypes.c_uint(); dpi_py = ctypes.c_uint()
            ctypes.windll.shcore.GetDpiForMonitor(
                hmon_primary, 0, ctypes.byref(dpi_px), ctypes.byref(dpi_py))
            primary_scale = dpi_px.value / 96.0
            phys_right  = mi.rcWork.right
            phys_top    = mi.rcWork.top
            popup_w_phys = int(self.W * scale)
            default_x = int((phys_right  - popup_w_phys - 16) / primary_scale)
            default_y = max(int(phys_top / primary_scale) + 40, 40)
            if self._init_pos:
                px, py = self._init_pos
                px_phys = int(px * primary_scale)
                py_phys = int(py * primary_scale)
                pt2 = ctypes.wintypes.POINT(px_phys, py_phys)
                hmon_popup = ctypes.windll.user32.MonitorFromPoint(pt2, 2)
                if hmon_popup == hmon_cursor:
                    x, y = px, py
                else:
                    x, y = default_x, default_y
            else:
                x, y = default_x, default_y
        except Exception:
            if self._init_pos:
                x, y = self._init_pos
            else:
                sw = self.winfo_screenwidth()
                x = max(0, sw - self.W - 16)
                y = 40
        self.geometry(f"{self.W}x{self.winfo_reqheight()}+{x}+{y}")

        self.bind("<ButtonPress-1>", self._drag_start)
        self.bind("<B1-Motion>",     self._drag_move)
        self.bind("<Escape>",    lambda e: self.destroy())
        self.bind("<Button-3>",  lambda e: self.destroy())

        self._target_alpha = 0.93
        self._fade(0.0)

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.winfo_x() + e.x - self._dx
        y = self.winfo_y() + e.y - self._dy
        self.geometry(f"+{x}+{y}")
        if self._on_move:
            self._on_move(x, y)
        self._reposition_toast()

    def _fade(self, a):
        t = self._target_alpha
        if a < t:
            self.attributes("-alpha", a)
            self.after(14, lambda: self._fade(min(a + 0.08, t)))
        else:
            self.attributes("-alpha", t)

    def _build(self):
        wrap = tk.Frame(self, bg=C["border"], padx=2, pady=2)
        wrap.pack(fill="both", expand=True)

        self._sb = tk.Scrollbar(wrap, orient="vertical")
        canvas = tk.Canvas(wrap, bg=C["bg"], highlightthickness=0,
                           yscrollcommand=self._on_scroll)
        canvas.pack(side="left", fill="both", expand=True)
        self._sb.configure(command=canvas.yview)
        self._canvas = canvas
        self._wrap   = wrap

        inner = tk.Frame(canvas, bg=C["bg"])
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            self._update_scrollbar()

        def on_canvas_configure(e):
            canvas.itemconfig(win_id, width=e.width)
            self._update_scrollbar()

        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._render(inner)

        self.update_idletasks()
        sh  = self.winfo_screenheight()
        h   = min(inner.winfo_reqheight(), sh - 80)
        canvas.configure(height=h)
        self._update_scrollbar()

    def show_toast(self, msg):
        if hasattr(self, "_toast") and self._toast:
            try:
                self._toast.destroy()
            except Exception:
                pass
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.92)
        toast.configure(bg=C["hd"])
        tk.Label(toast, text=msg,
                 font=("맑은 고딕", 9), fg=C["gold_lt"], bg=C["hd"],
                 padx=14, pady=8).pack()
        toast.update_idletasks()
        self._toast = toast
        self._reposition_toast()
        self.after(2500, self._destroy_toast)

    def _reposition_toast(self):
        if not hasattr(self, "_toast") or not self._toast:
            return
        try:
            tw = self._toast.winfo_reqwidth()
            th = self._toast.winfo_reqheight()
            cx = self.winfo_rootx()
            cy = self.winfo_rooty()
            cw = self.winfo_width()
            x = cx + (cw - tw) // 2
            y = cy - th - 4
            self._toast.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _destroy_toast(self):
        if hasattr(self, "_toast") and self._toast:
            try:
                self._toast.destroy()
            except Exception:
                pass
            self._toast = None

    def _toggle_fav(self):
        if self._on_fav_toggle:
            result = self._on_fav_toggle(self.char["name"])
            if result == "full":
                return
            is_fav = self._on_fav_check and self._on_fav_check(self.char["name"])
            pin_color = C["gold_lt"] if is_fav else C["dim"]
            try:
                self._pin_btn.configure(fg=pin_color)
            except Exception:
                pass

    def _on_scroll(self, *args):
        self._sb.set(*args)

    def _update_scrollbar(self):
        self.update_idletasks()
        top, bot = self._sb.get()
        if top <= 0.0 and bot >= 1.0:
            self._sb.pack_forget()
        else:
            if not self._sb.winfo_ismapped():
                self._sb.pack(in_=self._wrap, side="right", fill="y")
                self._sb.lift()

    def _render(self, p):
        self._name_row(p);        self._div(p)
        self._pos_cycle_node(p);  self._div(p)
        self._weapon_row(p);      self._div(p)
        self._echo_set_row(p);    self._div(p)
        self._echo_table(p);      self._div(p)
        self._crit_table(p);      self._div(p)
        self._stat_row(p)
        if self.char.get("notes"):
            self._div(p)
            self._notes_row(p)
        self._div(p)
        self._echo_score_btn(p)
        tk.Frame(p, bg=C["bg"], height=8).pack()

    def _div(self, p):
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x")

    def _name_row(self, p):
        row = tk.Frame(p, bg=C["hd"])
        row.pack(fill="x")

        ec = ELEM_COLOR.get(self.char.get("element", ""), C["gold_dim"])
        badge = tk.Frame(row, bg=ec)
        badge.pack(side="left", fill="y")
        tk.Label(badge, text=self.char["name"],
                 font=("맑은 고딕", 13, "bold"), fg=C["bg"], bg=ec,
                 padx=14, pady=10).pack(fill="both", expand=True)

        sf = tk.Frame(row, bg=C["hd"])
        sf.pack(side="left", fill="both", expand=True)
        tk.Label(sf, text="스킬",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=8, pady=4, anchor="center").pack(fill="x")
        tk.Frame(sf, bg=C["border"], height=1).pack(fill="x")
        tk.Label(sf, text=self.char.get("skill_priority") or "—",
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["hd"],
                 padx=8, pady=6, anchor="w",
                 wraplength=310, justify="left").pack(fill="both", expand=True)

        close = tk.Label(row, text="✕",
                         font=("맑은 고딕", 11), fg=C["dim"], bg=C["hd"],
                         padx=10, cursor="hand2")
        close.pack(side="right", anchor="n", pady=4)
        close.bind("<Button-1>", lambda e: self.destroy())

        if self._on_fav_toggle:
            is_fav = self._on_fav_check and self._on_fav_check(self.char["name"])
            pin_color = C["gold_lt"] if is_fav else C["dim"]
            self._pin_btn = tk.Label(row, text="★",
                                     font=("맑은 고딕", 11), fg=pin_color, bg=C["hd"],
                                     padx=6, cursor="hand2")
            self._pin_btn.pack(side="right", anchor="n", pady=4)
            self._pin_btn.bind("<Button-1>", lambda e: self._toggle_fav())

    def _pos_cycle_node(self, p):
        row = tk.Frame(p, bg=C["tbl"])
        row.pack(fill="x")

        pos = tk.Frame(row, bg=C["tbl"])
        pos.pack(side="left", fill="both", expand=True)
        tk.Label(pos, text="포지션",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 pady=4).pack(fill="x")
        tk.Frame(pos, bg=C["border"], height=1).pack(fill="x")
        tk.Label(pos, text=self.char.get("position") or "—",
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl"],
                 pady=6, wraplength=120, justify="center").pack(fill="both", expand=True)

        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y")

        cyc = tk.Frame(row, bg=C["cycle_bg"])
        cyc.pack(side="left", fill="both", expand=True)

        cyc_hd = tk.Frame(cyc, bg=C["tbl_hd"])
        cyc_hd.pack(fill="x")
        tk.Label(cyc_hd, text="사이클",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 pady=4).pack(side="left", padx=8)
        ebtn = tk.Label(cyc_hd, text="✎ 편집",
                        font=("맑은 고딕", 8), fg=C["dim"], bg=C["tbl_hd"],
                        padx=6, cursor="hand2")
        ebtn.pack(side="right")
        ebtn.bind("<Button-1>", lambda e: self._edit_cycle())

        video_url = self.char.get("video_url", "")
        if video_url:
            import webbrowser
            vbtn = tk.Label(cyc_hd, text="▶ 기본기",
                            font=("맑은 고딕", 8), fg=C["gold_lt"], bg=C["tbl_hd"],
                            padx=6, cursor="hand2")
            vbtn.pack(side="right")
            vbtn.bind("<Button-1>", lambda e, u=video_url: webbrowser.open(u))

        if self.char.get("teams"):
            tbtn = tk.Label(cyc_hd, text="👥 파티",
                            font=("맑은 고딕", 8), fg=C["gold_lt"], bg=C["tbl_hd"],
                            padx=6, cursor="hand2")
            tbtn.pack(side="right")
            tbtn.bind("<Button-1>", lambda e: self._open_teams())

        tk.Frame(cyc, bg=C["border"], height=1).pack(fill="x")

        cyc_txt = _settings.get("cycles", {}).get(self.char["name"], "").strip()
        self.char["cycle"] = cyc_txt  # 메모리 동기화
        self._cycle_overlay = None
        self._cycle_font_size = [13]

        if cyc_txt:
            def _update_overlay_size():
                if self._cycle_overlay and self._cycle_overlay.winfo_exists():
                    self._cycle_overlay.update_idletasks()
                    w = self._cycle_overlay.winfo_reqwidth()
                    h = self._cycle_overlay.winfo_reqheight()
                    ox = self._cycle_overlay.winfo_x()
                    oy = self._cycle_overlay.winfo_y()
                    self._cycle_overlay.geometry(f"{w}x{h}+{ox}+{oy}")
            def _font_up(e=None):
                self._cycle_font_size[0] = min(self._cycle_font_size[0] + 1, 28)
                if self._cycle_overlay and self._cycle_overlay.winfo_exists():
                    for w in self._cycle_overlay.winfo_children():
                        try: w.configure(font=("맑은 고딕", self._cycle_font_size[0], "bold"))
                        except: pass
                    _update_overlay_size()
            def _font_dn(e=None):
                self._cycle_font_size[0] = max(self._cycle_font_size[0] - 1, 8)
                if self._cycle_overlay and self._cycle_overlay.winfo_exists():
                    for w in self._cycle_overlay.winfo_children():
                        try: w.configure(font=("맑은 고딕", self._cycle_font_size[0], "bold"))
                        except: pass
                    _update_overlay_size()
            pbtn = tk.Label(cyc_hd, text="+",
                            font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                            padx=4, cursor="hand2")
            pbtn.pack(side="right")
            pbtn.bind("<Button-1>", _font_up)
            mbtn = tk.Label(cyc_hd, text="-",
                            font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                            padx=4, cursor="hand2")
            mbtn.pack(side="right")
            mbtn.bind("<Button-1>", _font_dn)
        if cyc_txt:
            def _toggle_cycle_overlay(e=None):
                if self._cycle_overlay and self._cycle_overlay.winfo_exists():
                    self._cycle_overlay.destroy()
                    self._cycle_overlay = None
                    return
                ov = tk.Toplevel()
                ov.overrideredirect(True)
                ov.attributes("-topmost", True)
                ov.attributes("-alpha", 0.92)
                ov.configure(bg="#0a0a0a")
                self._cycle_overlay = ov
                lbl = tk.Label(ov, text=cyc_txt,
                               font=("맑은 고딕", self._cycle_font_size[0], "bold"),
                               fg=C["cycle_txt"], bg="#0a0a0a",
                               padx=20, pady=16, justify="left", anchor="nw")
                lbl.pack(fill="both", expand=True)
                ov.update_idletasks()
                try:
                    import ctypes, ctypes.wintypes
                    class MI(ctypes.Structure):
                        _fields_ = [("cbSize",ctypes.c_ulong),("rcMonitor",ctypes.wintypes.RECT),("rcWork",ctypes.wintypes.RECT),("dwFlags",ctypes.c_ulong)]
                    pt = ctypes.wintypes.POINT()
                    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                    hmon = ctypes.windll.user32.MonitorFromPoint(pt, 2)
                    mi = MI(); mi.cbSize = ctypes.sizeof(MI)
                    ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
                    dpi_x = ctypes.c_uint(); dpi_y = ctypes.c_uint()
                    ctypes.windll.shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                    hmon_p = ctypes.windll.user32.MonitorFromPoint(ctypes.wintypes.POINT(0,0),1)
                    dpi_px = ctypes.c_uint(); dpi_py = ctypes.c_uint()
                    ctypes.windll.shcore.GetDpiForMonitor(hmon_p, 0, ctypes.byref(dpi_px), ctypes.byref(dpi_py))
                    ps = dpi_px.value / 96.0
                    cx = int((mi.rcWork.left + mi.rcWork.right) / 2 / ps)
                    cy = int((mi.rcWork.top  + mi.rcWork.bottom) / 2 / ps)
                    ow = ov.winfo_reqwidth(); oh = ov.winfo_reqheight()
                    ov.geometry(f"{ow}x{oh}+{cx - ow//2}+{cy - oh//2}")
                except Exception:
                    ov.geometry(f"+100+100")
                dx = [0]; dy = [0]
                def drag_start(e): dx[0]=e.x; dy[0]=e.y
                def drag_move(e):
                    ov.geometry(f"+{ov.winfo_x()+e.x-dx[0]}+{ov.winfo_y()+e.y-dy[0]}")
                lbl.bind("<ButtonPress-1>", drag_start)
                lbl.bind("<B1-Motion>", drag_move)
                lbl.bind("<Button-3>", lambda e: _toggle_cycle_overlay())
                ov.bind("<Escape>", lambda e: _toggle_cycle_overlay())
            cyc_lbl = tk.Label(cyc, text=cyc_txt,
                     font=("맑은 고딕", 9), fg=C["cycle_txt"], bg=C["cycle_bg"],
                     padx=8, pady=6, anchor="nw", justify="left",
                     wraplength=148, cursor="hand2")
            cyc_lbl.pack(fill="both", expand=True)
            cyc_lbl.bind("<Button-1>", _toggle_cycle_overlay)
        else:
            tk.Label(cyc, text="✎ 편집 버튼으로 입력",
                     font=("맑은 고딕", 8), fg=C["dim"], bg=C["cycle_bg"],
                     pady=14).pack(fill="both", expand=True)

        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y")

        nd = tk.Frame(row, bg=C["tbl"])
        nd.pack(side="left", fill="both", expand=True)
        tk.Label(nd, text="노드 옵션",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 pady=4).pack(fill="x")
        tk.Frame(nd, bg=C["border"], height=1).pack(fill="x")
        tk.Label(nd, text=self.char.get("node_option") or "—",
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl"],
                 pady=6, wraplength=120).pack(fill="both", expand=True)

    def _open_teams(self):
        teams = self.char.get("teams", [])
        if not teams:
            return

        win = tk.Toplevel(self)
        win.attributes("-alpha", 0.0)
        win.withdraw()
        win.title(f"{self.char['name']} 추천 파티")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        try:
            if os.path.exists(ICON_FILE):
                win.iconbitmap(ICON_FILE)
        except Exception:
            pass

        tk.Label(win, text=f"👥  {self.char['name']} 추천 파티",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        for i, team in enumerate(teams):
            tf = tk.Frame(win, bg=C["tbl"] if i % 2 == 0 else C["tbl2"])
            tf.pack(fill="x", padx=0)

            ordinals = ["1st", "2nd", "3rd", "4th"]
            team_label = f"추천파티 {ordinals[i] if i < len(ordinals) else str(i+1)}"
            tk.Label(tf, text=team_label,
                     font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=tf["bg"],
                     padx=12, pady=6, anchor="w").pack(fill="x")

            mf = tk.Frame(tf, bg=tf["bg"])
            mf.pack(fill="x", padx=12, pady=(0, 8))

            ec = ELEM_COLOR.get(self.char.get("element", ""), C["gold_dim"])
            self_badge = tk.Label(mf, text=self.char["name"],
                                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=ec,
                                  padx=8, pady=4, cursor="hand2")
            self_badge.pack(side="left", padx=(0, 4))

            tk.Label(mf, text="＋", font=("맑은 고딕", 9), fg=C["dim"], bg=tf["bg"]).pack(side="left")

            chars = self._main_panel.chars if self._main_panel else {}
            for mem in team["members"]:
                mem_char = chars.get(mem, {})
                ec2 = ELEM_COLOR.get(mem_char.get("element", ""), C["gold_dim"])
                btn = tk.Label(mf, text=mem,
                               font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=ec2,
                               padx=8, pady=4, cursor="hand2")
                btn.pack(side="left", padx=4)

                def on_click(e, name=mem, w=win):
                    w.destroy()
                    if self._main_panel:
                        found = self._main_panel.chars.get(name)
                        if found:
                            self._main_panel._close_popup()
                            self._main_panel._make_popup(found)
                btn.bind("<Button-1>", on_click)

            if i < len(teams) - 1:
                tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")
        tk.Button(win, text="닫기",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=win.destroy).pack(pady=8, ipadx=16, ipady=4)

        win.update_idletasks()
        _oc = self._sub_popup_count; self._sub_popup_count += 1
        win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, '_sub_popup_count', max(0, self._sub_popup_count-1)), win.destroy()))
        _place_beside_card(win, 380, win.winfo_reqheight(), self, _oc)

    def _edit_cycle(self):
        win = tk.Toplevel(self)
        win.attributes("-alpha", 0.0)
        win.withdraw()
        win.title(f"{self.char['name']} 사이클 편집")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        _oc = self._sub_popup_count; self._sub_popup_count += 1
        win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, '_sub_popup_count', max(0, self._sub_popup_count-1)), win.destroy()))
        _place_beside_card(win, 360, 240, self, _oc)
        try:
            if os.path.exists(ICON_FILE):
                win.iconbitmap(ICON_FILE)
        except Exception:
            pass

        tk.Label(win, text=f"  {self.char['name']}  사이클",
                 font=("맑은 고딕", 10, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=10, pady=6).pack(fill="x")
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        txt = scrolledtext.ScrolledText(
            win, font=("맑은 고딕", 9),
            bg=C["tbl_hd"], fg=C["text"],
            insertbackground=C["gold_lt"],
            relief="flat", bd=0, height=8)
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        _saved_cycle = _settings.get("cycles", {}).get(self.char["name"], "")
        txt.insert("1.0", _saved_cycle)

        def do_save():
            new_cycle = txt.get("1.0", "end").strip()
            self.char["cycle"] = new_cycle
            if "cycles" not in _settings:
                _settings["cycles"] = {}
            _settings["cycles"][self.char["name"]] = new_cycle
            save_settings(_settings)
            win.destroy()
            self.destroy()
            if self._on_reopen:
                self._on_reopen(self.char)

        bf = tk.Frame(win, bg=C["bg"])
        bf.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(bf, text="저장",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=do_save).pack(side="left", ipadx=10, ipady=3, padx=(0, 6))
        tk.Button(bf, text="취소",
                  font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl_hd"],
                  relief="flat", command=win.destroy).pack(side="left", ipadx=10, ipady=3)

    def _weapon_row(self, p):
        tk.Label(p, text="추천 무기",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=10, pady=5, anchor="w").pack(fill="x")
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x")

        wf = tk.Frame(p, bg=C["tbl"], pady=6, padx=10)
        wf.pack(fill="x")

        weapons = self.char.get("weapons", [])
        if weapons:
            for i, w in enumerate(weapons):
                color = C["orange"] if i == 0 else C["gold_lt"] if i == 1 else C["dim"]
                tag_m = re.search(r"\[.+?\]", w)
                tag   = tag_m.group(0) if tag_m else ""
                name  = w.replace(tag, "").strip()
                r = tk.Frame(wf, bg=C["tbl"])
                r.pack(anchor="w", pady=1)
                tk.Label(r, text=name,
                         font=("맑은 고딕", 10, "bold"), fg=color, bg=C["tbl"]).pack(side="left")
                if tag:
                    tk.Label(r, text=tag,
                             font=("맑은 고딕", 8), fg=C["red"], bg=C["tbl"]).pack(side="left", padx=4)
        else:
            tk.Label(wf, text="—", font=("맑은 고딕", 9), fg=C["dim"], bg=C["tbl"]).pack(anchor="w")

    def _echo_set_row(self, p):
        tk.Label(p, text="에코 세트",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=10, pady=5, anchor="w").pack(fill="x")
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x")

        for line in (self.char.get("echo_set") or "—").splitlines():
            tk.Label(p, text=line,
                     font=("맑은 고딕", 9), fg=C["orange"], bg=C["tbl"],
                     padx=10, pady=3, anchor="w",
                     wraplength=self.W - 24, justify="left").pack(fill="x")
        tk.Frame(p, bg=C["tbl"], height=4).pack()

    def _echo_table(self, p):
        builds = self.char.get("echo_builds", [])
        if not builds:
            return

        outer = tk.Frame(p, bg=C["border"])
        outer.pack(fill="x")

        outer.columnconfigure(0, minsize=56)
        outer.columnconfigure(1, minsize=64)
        outer.columnconfigure(2, weight=2)
        outer.columnconfigure(3, weight=1)
        outer.columnconfigure(4, weight=1)

        for col, txt in enumerate(["에코\n주옵", "코스트", "메인 에코", "3코스트", "1코스트"]):
            tk.Label(outer, text=txt,
                     font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                     pady=4, padx=4, anchor="center").grid(
                row=0, column=col, sticky="nsew",
                padx=(0, 1) if col < 4 else 0)

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=1, column=0, columnspan=5, sticky="ew")

        for bi, build in enumerate(builds):
            r = bi * 2 + 2
            bg = C["tbl"] if bi % 2 == 0 else C["tbl2"]

            if bi == 0:
                tk.Label(outer, text="에코\n주옵",
                         font=("맑은 고딕", 8), fg=C["white"], bg=C["gold_dim"],
                         pady=6).grid(
                    row=2, column=0, rowspan=len(builds) * 2 - 1,
                    sticky="nsew", padx=(0, 1))

            tk.Label(outer, text=build.get("tag", ""),
                     font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=bg,
                     pady=6, padx=4).grid(
                row=r, column=1, sticky="nsew", padx=(0, 1))

            tk.Label(outer, text=build.get("main", ""),
                     font=("맑은 고딕", 9), fg=C["text"], bg=bg,
                     pady=6, padx=6, anchor="center").grid(
                row=r, column=2, sticky="nsew", padx=(0, 1))

            subs = build.get("subs", [])
            left_parts  = []
            right_parts = []
            for s in subs:
                if "/" in s:
                    l, _, rv = s.partition("/")
                    left_parts.append(l.strip())
                    right_parts.append(rv.strip())
                else:
                    left_parts.append(s.strip())

            tk.Label(outer, text="\n".join(left_parts),
                     font=("맑은 고딕", 8), fg=C["dim"], bg=bg,
                     pady=6, padx=4, anchor="w", justify="left").grid(
                row=r, column=3, sticky="nsew", padx=(0, 1))

            tk.Label(outer, text="\n".join(right_parts),
                     font=("맑은 고딕", 8), fg=C["dim"], bg=bg,
                     pady=6, padx=4, anchor="w", justify="left").grid(
                row=r, column=4, sticky="nsew")

            if bi < len(builds) - 1:
                tk.Frame(outer, bg=C["border"], height=1).grid(
                    row=r + 1, column=1, columnspan=4, sticky="ew")

    def _crit_table(self, p):
        crits = self.char.get("crit_stats", [])
        if not crits:
            return

        outer = tk.Frame(p, bg=C["border"])
        outer.pack(fill="x")

        outer.columnconfigure(0, minsize=56)
        outer.columnconfigure(1, minsize=64)
        outer.columnconfigure(2, weight=1)
        outer.columnconfigure(3, weight=1)

        for col, txt in enumerate(["크확\n크피", "코스트", "크확", "크피"]):
            tk.Label(outer, text=txt,
                     font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                     pady=4, padx=4, anchor="center").grid(
                row=0, column=col, sticky="nsew",
                padx=(0, 1) if col < 3 else 0)

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=1, column=0, columnspan=4, sticky="ew")

        for ci, cs in enumerate(crits):
            r = ci * 2 + 2
            bg = C["tbl"] if ci % 2 == 0 else C["tbl2"]

            if ci == 0:
                tk.Label(outer, text="크확\n크피",
                         font=("맑은 고딕", 8), fg=C["white"], bg=C["gold_dim"],
                         pady=6, padx=4).grid(
                    row=2, column=0, rowspan=len(crits) * 2 - 1,
                    sticky="nsew", padx=(0, 1))

            tk.Label(outer, text=cs.get("tag", ""),
                     font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=bg,
                     pady=6, padx=4).grid(
                row=r, column=1, sticky="nsew", padx=(0, 1))

            tk.Label(outer, text=cs.get("cr", ""),
                     font=("맑은 고딕", 9), fg=C["text"], bg=bg,
                     pady=6, padx=4, anchor="center").grid(
                row=r, column=2, sticky="nsew", padx=(0, 1))

            tk.Label(outer, text=cs.get("cd", ""),
                     font=("맑은 고딕", 9), fg=C["text"], bg=bg,
                     pady=6, padx=4, anchor="center").grid(
                row=r, column=3, sticky="nsew")

            if ci < len(crits) - 1:
                tk.Frame(outer, bg=C["border"], height=1).grid(
                    row=r + 1, column=1, columnspan=3, sticky="ew")

    def _stat_row(self, p):
        stats     = self.char.get("res_stats", {})
        energy    = self.char.get("energy_cost", "")
        mid_label = stats.get("중간_label", "공격력")
        labels    = ["공명 효율", mid_label, "에너지 소모"]
        values    = [
            stats.get("공명효율", "—"),
            stats.get("중간값",   "—"),
            stats.get("에너지소모", energy or "—"),
        ]

        outer = tk.Frame(p, bg=C["tbl_hd"])
        outer.pack(fill="x")
        for col in range(3):
            outer.columnconfigure(col, weight=1)

        for col, lbl in enumerate(labels):
            tk.Label(outer, text=lbl,
                     font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                     pady=4, anchor="center").grid(
                row=0, column=col, sticky="nsew",
                padx=(0, 1) if col < 2 else 0)

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew")

        for col, val in enumerate(values):
            tk.Label(outer, text=(val or "—").strip(),
                     font=("맑은 고딕", 11, "bold"), fg=C["text"], bg=C["tbl"],
                     pady=9, anchor="center").grid(
                row=2, column=col, sticky="nsew",
                padx=(0, 1) if col < 2 else 0)

    def _echo_score_btn(self, p):
        btn = tk.Label(p, text="📊 에코 점수 계산",
                       font=("맑은 고딕", fsc(9)), fg=C["bg"], bg=C["gold_lt"],
                       padx=8, pady=4, cursor="hand2", anchor="center")
        btn.pack(fill="x", padx=8, pady=(4,8))
        btn.bind("<Button-1>", lambda e: self._open_echo_score())

    def _open_echo_score(self):
        char = self.char
        char_type = char.get("type", "attack")
        dmg_contrib = char.get("dmg_contribution", {})

        WEIGHTS_DEFAULT = {
            "크리티컬%": 3.2, "크리티컬 피해%": 1.5, "공명효율%": 1.5,
            "공격력%": 1.4, "공격력": 0.14,
            "방어력%": 0.0, "방어력": 0.0, "HP%": 0.0, "HP": 0.0,
        }
        WEIGHTS_TYPE = {
            "fuluoluo": {**WEIGHTS_DEFAULT, "크리티컬%": 3.6, "크리티컬 피해%": 1.7,
                         "공명효율%": 0.0, "공격력%": 1.6, "공격력": 0.16},
            "attack":   {**WEIGHTS_DEFAULT},
            "defense":  {**WEIGHTS_DEFAULT, "공격력%": 0.0, "공격력": 0.0,
                         "방어력%": 1.1, "방어력": 0.14},
            "hp":       {**WEIGHTS_DEFAULT, "공격력%": 0.0, "공격력": 0.0,
                         "HP%": 1.4, "HP": 0.017},
        }
        weights = WEIGHTS_TYPE.get(char_type, WEIGHTS_DEFAULT)

        OPTION_VALUES = {
            "크리티컬%":      [6.3,6.9,7.5,8.1,8.7,9.3,9.9,10.5],
            "크리티컬 피해%":  [12.6,13.8,15,16.2,17.4,18.6,19.8,21],
            "공격력%":        [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "공명효율%":      [6.8,7.6,8.4,9.2,10,10.8,11.6,12.4],
            "공명해방 피해 보너스%": [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "강공격 피해 보너스%":  [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "공명스킬 피해 보너스%": [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "일반공격 피해 보너스%": [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "방어력%": [8.1,9,10,10.9,11.8,12.8,13.8,14.7],
            "HP%":    [6.4,7.1,7.9,8.6,9.4,10.1,10.9,11.6],
            "공격력": [30,40,50,60],
            "HP":     [320,360,390,430,470,510,540,580],
            "방어력": [40,50,60,70],
        }

        DMG_BONUS_OPTIONS = {
            "공명해방 피해 보너스%",
            "강공격 피해 보너스%",
            "공명스킬 피해 보너스%",
            "일반공격 피해 보너스%",
        }
        DMG_KEY_MAP = {
            "공명해방 피해 보너스%": "공명해방",
            "강공격 피해 보너스%":   "강공격",
            "공명스킬 피해 보너스%": "공명스킬",
            "일반공격 피해 보너스%": "일반공격",
        }

        def calc_echo_score(options):
            import math as _math
            c = sum(dmg_contrib.get(v, 0) for v in DMG_KEY_MAP.values())
            t = max(0, 1 - c)
            e = 1 + 0.001 * (0 if t == 0 else _math.ceil(t / 0.01))
            score = 0.0
            for opt in options:
                option = opt.get("option", "")
                value = opt.get("value")
                if not option or value is None:
                    continue
                if option in DMG_BONUS_OPTIONS:
                    n = value * dmg_contrib.get(DMG_KEY_MAP[option], 0) * 1.4
                elif option in weights:
                    n = value * weights[option]
                else:
                    n = 0.0
                g = n if option == "공명효율%" else n * e
                score = round(score + g, 2)
            return score

        def calc_total(echo_scores, total_reso, max_reso):
            c = sum(echo_scores)
            if weights.get("공명효율%", 0) == 0:
                return round(c / 5 * 100) / 100, 0
            excess = max(0, total_reso - max_reso)
            c -= 1.5 * excess
            return round(c / 5 * 100) / 100, round(excess * 100) / 100

        win = tk.Toplevel(self)
        win.withdraw()
        win.title(f"{char['name']} 에코 점수")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        try:
            if os.path.exists(ICON_FILE):
                win.iconbitmap(ICON_FILE)
        except Exception:
            pass

        tk.Label(win, text=f"⚡ {char['name']} 에코 점수 계산",
                 font=("맑은 고딕", fsc(10), "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        NUM_ECHO = 5
        NUM_OPTS = 5
        all_options = [[{"option": "", "value": None} for _ in range(NUM_OPTS)]
                        for _ in range(NUM_ECHO)]
        echo_scores = [tk.StringVar(value="—") for _ in range(NUM_ECHO)]
        selected_echo = tk.IntVar(value=0)

        opt_labels = list(OPTION_VALUES.keys())

        _ocr_captures = []
        _ocr_active = [False]
        _popup_open = [False]

        top_frame = tk.Frame(win, bg=C["bg"])
        top_frame.pack(fill="x", padx=12, pady=(8,4))
        tk.Label(top_frame, text="최대 공명효율",
                 font=("맑은 고딕", fsc(8)), fg=C["dim"], bg=C["bg"]).pack(side="left")
        max_reso_var = tk.StringVar(value="62")
        max_reso_entry = tk.Entry(top_frame, textvariable=max_reso_var, width=5,
                                   font=("맑은 고딕", fsc(9)), bg=C["tbl"], fg=C["text"],
                                   insertbackground=C["text"], relief="flat",
                                   highlightthickness=1, highlightbackground=C["border"])
        max_reso_entry.pack(side="left", padx=(6,0))

        tab_frame = tk.Frame(win, bg=C["tbl_hd"])
        tab_frame.pack(fill="x")
        tab_btns = []
        ROMAN = ["Ⅰ","Ⅱ","Ⅲ","Ⅳ","Ⅴ"]

        def select_echo(idx):
            selected_echo.set(idx)
            for i, btn in enumerate(tab_btns):
                btn.configure(bg=C["gold_lt"] if i == idx else C["tbl_hd"],
                               fg=C["bg"] if i == idx else C["dim"])
            refresh_options()

        for i in range(NUM_ECHO):
            btn = tk.Label(tab_frame, text=f"에코{ROMAN[i]}",
                           font=("맑은 고딕", fsc(8)), fg=C["dim"], bg=C["tbl_hd"],
                           padx=8, pady=4, cursor="hand2")
            btn.pack(side="left", expand=True, fill="x")
            btn.bind("<Button-1>", lambda e, idx=i: select_echo(idx))
            tab_btns.append(btn)

        opts_frame = tk.Frame(win, bg=C["bg"])
        opts_frame.pack(fill="x", padx=12, pady=8)
        opt_rows = []
        for j in range(NUM_OPTS):
            row = tk.Frame(opts_frame, bg=C["bg"])
            row.pack(fill="x", pady=1)
            var_opt = tk.StringVar(value="")
            var_val = tk.StringVar(value="")
            cb_opt = tk.OptionMenu(row, var_opt, *[""] + opt_labels)
            cb_opt.configure(font=("맑은 고딕", fsc(8)), bg=C["tbl"], fg=C["text"],
                              activebackground=C["tbl_hd"], activeforeground=C["text"],
                              highlightthickness=0, relief="flat", width=18)
            cb_opt["menu"].configure(font=("맑은 고딕", fsc(8)), bg=C["tbl"], fg=C["text"])
            cb_opt.pack(side="left", padx=(0,4))
            cb_val = tk.OptionMenu(row, var_val, *[""])
            cb_val.configure(font=("맑은 고딕", fsc(8)), bg=C["tbl"], fg=C["text"],
                              activebackground=C["tbl_hd"], activeforeground=C["text"],
                              highlightthickness=0, relief="flat", width=8)
            cb_val["menu"].configure(font=("맑은 고딕", fsc(8)), bg=C["tbl"], fg=C["text"])
            cb_val.pack(side="left")
            opt_rows.append((var_opt, var_val, cb_val))

        def refresh_options():
            idx = selected_echo.get()
            for j, (var_opt, var_val, cb_val) in enumerate(opt_rows):
                opt = all_options[idx][j]["option"] or ""
                val = all_options[idx][j]["value"]
                var_opt.set(opt)
                update_val_menu(j, opt)
                def _fmt_val(v):
                    if isinstance(v, float) and v == int(v): return str(int(v))
                    return str(v)
                var_val.set(_fmt_val(val) if val is not None else "")

        def update_val_menu(j, opt_name):
            _, var_val, cb_val = opt_rows[j]
            menu = cb_val["menu"]
            menu.delete(0, "end")
            vals = OPTION_VALUES.get(opt_name, [])
            menu.add_command(label="", command=lambda: var_val.set(""))
            for v in vals:
                label = f"{v}%" if "%" in opt_name else str(v)
                menu.add_command(label=label, command=lambda v=v: var_val.set(str(v)))
            if not vals:
                var_val.set("")

        def on_opt_change(j, *args):
            idx = selected_echo.get()
            opt_name = opt_rows[j][0].get()
            all_options[idx][j]["option"] = opt_name
            all_options[idx][j]["value"] = None
            opt_rows[j][1].set("")
            update_val_menu(j, opt_name)

        def on_val_change(j, *args):
            idx = selected_echo.get()
            val_str = opt_rows[j][1].get()
            try:
                all_options[idx][j]["value"] = float(val_str) if val_str else None
            except ValueError:
                all_options[idx][j]["value"] = None
            win.after(50, _update_scores)

        for j, (var_opt, var_val, cb_val) in enumerate(opt_rows):
            var_opt.trace_add("write", lambda *a, j=j: on_opt_change(j))
            var_val.trace_add("write", lambda *a, j=j: on_val_change(j))

        ocr_status = tk.Label(win, text="",
                               font=("맑은 고딕", fsc(8)), fg=C["dim"], bg=C["bg"],
                               anchor="w", padx=12)
        ocr_status.pack(fill="x")

        def _find_crop_x(gray_arr, img_w):
            import numpy as _np
            col_d = (gray_arr > 200).sum(axis=0)
            thresh = gray_arr.shape[0] * 0.03
            search_w = int(img_w * 0.25)
            in_text = False; gap_found = False
            for x in range(search_w):
                if not in_text and col_d[x] > thresh:
                    in_text = True
                elif in_text and col_d[x] <= thresh:
                    gap_found = True
                elif gap_found and col_d[x] > thresh:
                    pad = max(8, int(img_w * 0.02))
                    return max(0, x - pad)
            return int(img_w * 0.08)

        def _process_row(row_gray):
            from PIL import Image as _Img, ImageFilter, ImageEnhance, ImageOps
            import numpy as _np
            rw, rh = row_gray.size
            resized = row_gray.resize((rw * 3, rh * 3), _Img.Resampling.BICUBIC)
            blurred = resized.filter(ImageFilter.GaussianBlur(radius=1.0))
            high_contrast = ImageEnhance.Contrast(blurred).enhance(3.5)
            arr = _np.array(high_contrast)
            hist, _ = _np.histogram(arr.flatten(), bins=256, range=(0,256))
            total = arr.size
            sum_total = _np.dot(_np.arange(256), hist)
            sum_bg, w_bg, max_var, threshold = 0, 0, 0, 130
            for t in range(256):
                w_bg += hist[t]
                if w_bg == 0: continue
                w_fg = total - w_bg
                if w_fg == 0: break
                sum_bg += t * hist[t]
                mean_bg = sum_bg / w_bg
                mean_fg = (sum_total - sum_bg) / w_fg
                var = w_bg * w_fg * (mean_bg - mean_fg) ** 2
                if var > max_var:
                    max_var = var
                    threshold = t
            binary = _Img.fromarray((arr > threshold).astype(_np.uint8) * 255)
            cleaned = binary.filter(ImageFilter.MinFilter(size=3))
            dilated  = cleaned.filter(ImageFilter.MaxFilter(size=3))
            return ImageOps.invert(dilated)

        def _preprocess(pil_image):
            import numpy as _np
            from PIL import ImageFilter, ImageEnhance, Image as _Img
            gray = pil_image.convert("L")
            w, h = gray.size
            arr = _np.array(gray)
            crop_x = _find_crop_x(arr, w)
            gray = gray.crop((crop_x, 0, w, h))
            gw, gh = gray.size

            resized = gray.resize((gw * 3, gh * 3), _Img.Resampling.BICUBIC)
            blurred = resized.filter(ImageFilter.GaussianBlur(radius=1.0))
            high_contrast = ImageEnhance.Contrast(blurred).enhance(3.5)
            arr2 = _np.array(high_contrast)

            median_val = _np.median(arr2)
            text_pixels = arr2[arr2 > median_val].flatten()
            if len(text_pixels) < 100:
                text_pixels = arr2.flatten()
            hist, _ = _np.histogram(text_pixels, bins=256, range=(0, 256))
            total = text_pixels.size
            sum_total = _np.dot(_np.arange(256), hist)
            sum_bg, w_bg, max_var, threshold = 0, 0, 0, 130
            for t in range(256):
                w_bg += hist[t]
                if w_bg == 0: continue
                w_fg = total - w_bg
                if w_fg == 0: break
                sum_bg += t * hist[t]
                mean_bg = sum_bg / w_bg
                mean_fg = (sum_total - sum_bg) / w_fg
                var = w_bg * w_fg * (mean_bg - mean_fg) ** 2
                if var > max_var:
                    max_var = var
                    threshold = t

            from PIL import ImageFilter as _IF, ImageOps
            binary = _Img.fromarray((arr2 > threshold).astype(_np.uint8) * 255)
            cleaned = binary.filter(_IF.MinFilter(size=3))
            dilated  = cleaned.filter(_IF.MaxFilter(size=3))
            return ImageOps.invert(dilated)

        def _split_rows(processed_img):
            import numpy as _np
            arr = _np.array(processed_img)
            row_density = (arr < 128).sum(axis=1)
            max_d = row_density.max() if row_density.max() > 0 else 1
            has_text = row_density > max_d * 0.05
            segments = []
            in_seg = False
            for i, v in enumerate(has_text):
                if v and not in_seg: start = i; in_seg = True
                elif not v and in_seg: segments.append((start, i)); in_seg = False
            if in_seg: segments.append((start, len(has_text)))
            w = processed_img.size[0]
            h_total = processed_img.size[1]
            rows = []
            for s, e in segments:
                pad = max(4, (e - s) // 4)
                y1 = max(0, s - pad)
                y2 = min(h_total, e + pad)
                rows.append(processed_img.crop((0, y1, w, y2)))
            return rows

        def _do_ocr(pil_image):
            import asyncio, io
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.graphics.imaging import BitmapDecoder
            from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

            async def _recognize_one(engine, row_img):
                buf = io.BytesIO()
                row_img.save(buf, format="PNG")
                buf_bytes = buf.getvalue()
                stream = InMemoryRandomAccessStream()
                writer = DataWriter(stream)
                writer.write_bytes(buf_bytes)
                await writer.store_async()
                await writer.flush_async()
                stream.seek(0)
                decoder = await BitmapDecoder.create_async(stream)
                bitmap = await decoder.get_software_bitmap_async()
                result = await engine.recognize_async(bitmap)
                return result.text.strip() if result else ""

            async def _run():
                ko_eng = None
                try:
                    from winrt.windows.globalization import Language
                    ko_lang = Language("ko")
                    if OcrEngine.is_language_supported(ko_lang):
                        ko_eng = OcrEngine.try_create_from_language(ko_lang)
                except Exception:
                    pass
                if not ko_eng:
                    ko_eng = OcrEngine.try_create_from_user_profile_languages()

                rows = _split_rows(pil_image)
                if not rows:
                    rows = [pil_image]

                import numpy as _np2
                import re as _re3
                line_texts = []
                for row_img in rows:
                    rw = row_img.size[0]
                    rarr = _np2.array(row_img)
                    col_d = (rarr < 128).sum(axis=0)
                    row_h = rarr.shape[0]
                    right_start = int(rw * 0.5)
                    val_x = rw
                    for x in range(right_start, rw):
                        if col_d[x] > row_h * 0.05:
                            val_x = x; break

                    full_text = await _recognize_one(ko_eng, row_img) if ko_eng else ""

                    if val_x < rw:
                        val_img = row_img.crop((val_x, 0, rw, row_img.size[1]))
                        val_text = await _recognize_one(ko_eng, val_img) if ko_eng else ""
                        val_num = _re3.search(r'[\d.%]+', val_text)
                        full_num = _re3.search(r'[\d.%]+', full_text)
                        if val_num and (not full_num or val_num.group() != full_num.group()):
                            label_part = _re3.sub(r'[\d.%]+.*$', '', full_text).strip()
                            combined = f"{label_part} {val_num.group()}".strip()
                            line_texts.append(combined)
                        else:
                            line_texts.append(full_text)
                    else:
                        line_texts.append(full_text)

                _do_ocr._last_rows = [f"[ko] {t}" for t in line_texts]
                return "\n".join(t for t in line_texts if t)

            return asyncio.run(_run())

        def _normalize(text):
            import re as _re
            LABEL_RESTORE = {
                "크리티컬피해": "크리티컬 피해",
                "공명해방피해보너스": "공명해방 피해 보너스",
                "공명스킬피해보너스": "공명스킬 피해 보너스",
                "강공격피해보너스": "강공격 피해 보너스",
                "일반공격피해보너스": "일반공격 피해 보너스",
            }
            lines_out = []
            for line in text.splitlines():
                line = line.strip()
                ns = line.replace("-","").replace("[","").replace("'","")
                ns = _re.sub(r'(\d+\.\d{1,2})96\b', r'\1%', ns)
                ns = ns.replace(" ", "")
                for w, r in OCR_CORRECTIONS.items():
                    ns = ns.replace(w, r)
                ns = _re.sub(r'[^가-힣\d.%]', '', ns)
                m = _re.search(r'([가-힣]+)([\d.%]+)', ns)
                if m:
                    label = LABEL_RESTORE.get(m.group(1), m.group(1))
                    lines_out.append(f"{label} {m.group(2)}")
                elif _re.search(r'[가-힣]', ns):
                    for w, r in LABEL_RESTORE.items():
                        ns = ns.replace(w, r)
                    lines_out.append(ns)
                elif _re.search(r'^[\d.%]+$', ns) and _re.search(r'\d', ns):
                    lines_out.append(ns)
            return '\n'.join(l for l in lines_out if l.strip())

        def _parse_echo_options(text):
            import re as _re

            LABEL_MAP = [
                ("크리티컬 피해",        "크리티컬 피해%",          True),
                ("크리티컬",             "크리티컬%",               True),
                ("공명해방 피해 보너스", "공명해방 피해 보너스%",   True),
                ("강공격 피해 보너스",   "강공격 피해 보너스%",     True),
                ("공명스킬 피해 보너스", "공명스킬 피해 보너스%",   True),
                ("일반공격 피해 보너스", "일반공격 피해 보너스%",   True),
                ("공명효율",             "공명효율%",               True),
                ("HP%",                  "HP%",                     True),
                ("방어력%",              "방어력%",                 True),
                ("공격력%",              "공격력%",                 True),
                ("HP",                   "HP",                      False),
                ("방어력",               "방어력",                  False),
                ("공격력",               "공격력",                  False),
            ]
            AMBIGUOUS_BASE = {"HP", "방어력", "공격력"}

            HP_INT_VALS  = {320,360,390,430,470,510,540,580}
            ATK_INT_VALS = {30,40,50,60}
            DEF_INT_VALS = {40,50,60,70}

            ALL_PCT_VALS = {}
            for opt_name, vals in OPTION_VALUES.items():
                if "%" in opt_name:
                    for v in vals:
                        ALL_PCT_VALS.setdefault(v, []).append(opt_name)

            def _snap_pct(v, opt_name):
                candidates = OPTION_VALUES.get(opt_name, [])
                if not candidates: return v
                closest = min(candidates, key=lambda c: abs(c - v))
                if abs(closest - v) <= 0.15:
                    return closest
                return v

            def _fix_val(v):
                if v == int(v):
                    iv = int(v); s = str(iv)
                    if len(s) >= 3 and s[-1] != '0':
                        c = round(iv / 10, 1)
                        if c <= 300: return c
                return v

            def _parse_line(line):
                import re as _re2
                if not _re2.search(r'[가-힣a-zA-Z]', line):
                    if '%' in line:
                        m = _re2.search(r'(\d+\.?\d*)\s*%', line)
                        if m:
                            val = _fix_val(float(m.group(1)))
                            val = _snap_pct(val, "HP%")
                            return {"option": "HP%", "value": val}
                    else:
                        m = _re2.search(r'(\d+)', line)
                        if m:
                            iv = int(m.group(1))
                            if iv in HP_INT_VALS:
                                return {"option": "HP", "value": iv}
                    return None

                matched_opt = None; is_pct = False
                for kw, opt, pct in LABEL_MAP:
                    if kw in line:
                        matched_opt = opt; is_pct = pct; break
                if not matched_opt:
                    return None
                if matched_opt.rstrip("%") in AMBIGUOUS_BASE:
                    is_pct = bool(_re2.search(r'\d+\.?\d*\s*%', line))
                    base = matched_opt.rstrip("%")
                    matched_opt = base + "%" if is_pct else base
                if is_pct:
                    m = _re2.search(r'(\d+\.?\d*)\s*%', line)
                    if m:
                        val = _fix_val(float(m.group(1)))
                        val = _snap_pct(val, matched_opt)
                        return {"option": matched_opt, "value": val}
                else:
                    m = _re2.search(r'(?<![.\d])(\d{2,5})(?![.\d%])', line)
                    if m:
                        iv = int(m.group(1))
                        if matched_opt == "HP" and iv in HP_INT_VALS: return {"option": "HP", "value": iv}
                        if matched_opt == "공격력" and iv in ATK_INT_VALS: return {"option": "공격력", "value": iv}
                        if matched_opt == "방어력" and iv in DEF_INT_VALS: return {"option": "방어력", "value": iv}
                        return {"option": matched_opt, "value": iv}
                return None

            text = _normalize(text)
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            result = []
            for line in lines:
                if len(result) >= 5: break
                parsed = _parse_line(line)
                if parsed:
                    result.append(parsed)

            return result[:5]

        btn_frame = tk.Frame(win, bg=C["bg"])
        btn_frame.pack(fill="x", padx=12, pady=(0,4))

        def start_ocr():
            try:
                if not win.winfo_exists(): return
            except Exception: return
            if not _settings.get("roi"):
                ocr_status.configure(text="🔲 영역 지정 후 사용해주세요", fg=C["red"])
                return
            _ocr_captures.clear()
            _ocr_active[0] = True
            ocr_status.configure(text=f"에코{ROMAN[selected_echo.get()]} 스탯창 열고 F9 캡처하세요", fg=C["gold_lt"])
            try:
                import keyboard as _kb
                for hk in ["f9","enter","esc"]:
                    try: _kb.remove_hotkey(hk)
                    except: pass

                target_echo = selected_echo.get()

                def on_f9():
                    if not _ocr_active[0]: return
                    if not win.winfo_exists(): return
                    if _popup_open[0]: return
                    nonlocal target_echo
                    target_echo = selected_echo.get()
                    idx = len(_ocr_captures) + 1
                    _last_ocr_text = ""
                    import threading
                    def _capture():
                        try:
                            import time, PIL.ImageGrab, PIL.Image
                            win.after(0, win.withdraw)
                            if self._main_panel:
                                win.after(0, self._main_panel.root.withdraw)
                            win.after(0, self.withdraw)
                            time.sleep(0.2)
                            roi = _settings.get("roi")
                            if roi:
                                import PIL.ImageGrab
                                _probe = PIL.ImageGrab.grab()
                                _sc = _probe.width / win.winfo_screenwidth()
                                x1,y1,x2,y2 = roi
                                img = _probe.crop((int(x1*_sc),int(y1*_sc),int(x2*_sc),int(y2*_sc)))
                            else:
                                img = PIL.ImageGrab.grab()
                            win.after(0, win.deiconify)
                            if self._main_panel:
                                win.after(0, self._main_panel.root.deiconify)
                            win.after(0, self.deiconify)
                            processed = _preprocess(img)
                            text = _do_ocr(processed)
                            print(f"[OCR 원문 {idx}번째]\n{text}\n")
                            try:
                                import datetime, zipfile, io
                                char_name = char.get("name", "unknown")
                                zip_path = os.path.join(get_appdata_dir(), f"ocr_debug_{char_name}.zip")
                                parsed_dbg = _parse_echo_options(text)
                                txt_buf = io.StringIO()
                                txt_buf.write(f"[{datetime.datetime.now()}] OCR {idx}번째\n\n")
                                txt_buf.write(f"원문:\n{text}\n\n")
                                txt_buf.write(f"파싱 결과:\n")
                                for _p in parsed_dbg:
                                    txt_buf.write(f"  {_p}\n")
                                try:
                                    txt_buf.write(f"\n--- 행별 OCR ---\n")
                                    for _ri, _rt in enumerate(getattr(_do_ocr, "_last_rows", [])):
                                        txt_buf.write(f"  행{_ri+1}: {_rt}\n")
                                except Exception: pass
                                raw_buf = io.BytesIO()
                                img.save(raw_buf, format="PNG")
                                proc_buf = io.BytesIO()
                                processed.save(proc_buf, format="PNG")
                                with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                                    zf.writestr(f"echo{idx}.txt",           txt_buf.getvalue())
                                    zf.writestr(f"echo{idx}_raw.png",       raw_buf.getvalue())
                                    zf.writestr(f"echo{idx}_processed.png", proc_buf.getvalue())
                            except Exception: pass
                            _ocr_captures.append(text)
                            parsed_now = _parse_echo_options(text)
                            new_opts = [{"option":"","value":None} for _ in range(NUM_OPTS)]
                            for _i, _p in enumerate(parsed_now[:NUM_OPTS]):
                                new_opts[_i] = _p
                            _echo_idx = target_echo
                            all_options[_echo_idx] = new_opts
                            count = sum(1 for o in new_opts if o["option"])
                            def _apply_and_update(ei=_echo_idx, no=new_opts, ct=count):
                                try:
                                    if not win.winfo_exists(): return
                                except Exception: return
                                if selected_echo.get() == ei:
                                    refresh_options()
                                ocr_status.configure(
                                    text=f"에코{ROMAN[ei]} 자동 입력 완료 ({ct}개) ✓",
                                    fg=C["green"])
                                _update_scores()
                            win.after(0, _apply_and_update)
                        except Exception as ex:
                            log_error("OCR 캡처 (계산기)", ex, {"캐릭터": char.get("name","?"), "캡처 인덱스": idx})
                            win.after(0, win.deiconify)
                            if self._main_panel:
                                win.after(0, self._main_panel.root.deiconify)
                            win.after(0, self.deiconify)
                            win.after(0, lambda e=ex: ocr_status.configure(text=f"캡처 오류: {e}", fg=C["red"]) if win.winfo_exists() else None)
                    threading.Thread(target=_capture, daemon=True).start()

                def on_enter():
                    _ocr_active[0] = False
                    for hk in ["f9","enter","esc"]:
                        try: _kb.remove_hotkey(hk)
                        except: pass
                    win.after(0, lambda: ocr_status.configure(
                        text="캡처 종료", fg=C["dim"]))

                def on_esc():
                    _ocr_active[0] = False
                    for hk in ["f9","enter","esc"]:
                        try: _kb.remove_hotkey(hk)
                        except: pass
                    try:
                        if win.winfo_exists():
                            win.after(0, lambda: ocr_status.configure(text="취소됨", fg=C["dim"]))
                    except Exception: pass

                _kb.add_hotkey("f9",    on_f9)
                _kb.add_hotkey("enter", on_enter)
                _kb.add_hotkey("esc",   on_esc)

            except ImportError as ex:
                log_error("keyboard 패키지 없음", ex, {"캐릭터": char.get("name","?")})
                ocr_status.configure(text="keyboard 패키지 없음", fg=C["red"])
            except Exception as ex:
                log_error("단축키 등록 실패", ex, {"캐릭터": char.get("name","?")})
                ocr_status.configure(text=f"단축키 등록 실패: {ex}", fg=C["red"])

        def start_roi():
            wins_to_hide = [win, self]
            if self._main_panel:
                wins_to_hide.append(self._main_panel.root)
            for w in wins_to_hide:
                try: w.withdraw()
                except: pass
            import time; time.sleep(0.15)
            overlay = tk.Toplevel()
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.25)
            overlay.attributes("-topmost", True)
            overlay.configure(bg="black")
            overlay.config(cursor="crosshair")
            canvas_roi = tk.Canvas(overlay, cursor="crosshair", bg="black", highlightthickness=0)
            canvas_roi.pack(fill="both", expand=True)
            state = {"sx":0,"sy":0,"rect":None}

            def on_press(e):
                state["sx"], state["sy"] = e.x, e.y
                state["rect"] = canvas_roi.create_rectangle(e.x, e.y, e.x, e.y, outline=C["gold_lt"], width=2, fill="")

            def on_drag(e):
                canvas_roi.coords(state["rect"], state["sx"], state["sy"], e.x, e.y)

            def on_release(e):
                x1 = min(state["sx"], e.x); y1 = min(state["sy"], e.y)
                x2 = max(state["sx"], e.x); y2 = max(state["sy"], e.y)
                overlay.destroy()
                if x2 - x1 > 10 and y2 - y1 > 10:
                    try:
                        import PIL.ImageGrab
                        _probe = PIL.ImageGrab.grab()
                        _sc = _probe.width / overlay.winfo_screenwidth()
                    except Exception:
                        _sc = 1.0
                    _settings["roi"] = [int(x1*_sc), int(y1*_sc), int(x2*_sc), int(y2*_sc)]
                    save_settings(_settings)
                    win.after(100, lambda: ocr_status.configure(text="✅ 영역 지정 완료", fg=C["green"]))
                    win.after(100, lambda: _roi_btn.configure(bg=C["gold_lt"]))
                for w in wins_to_hide:
                    try: w.deiconify()
                    except: pass

            canvas_roi.bind("<ButtonPress-1>", on_press)
            canvas_roi.bind("<B1-Motion>", on_drag)
            canvas_roi.bind("<ButtonRelease-1>", on_release)
            overlay.bind("<Escape>", lambda e: (overlay.destroy(), [w.deiconify() for w in wins_to_hide]))

        roi_saved = _settings.get("roi")
        roi_color = C["gold_lt"] if roi_saved else C["dim"]
        _roi_btn = tk.Button(btn_frame, text="🔲 영역 지정",
                  font=("맑은 고딕", fsc(8)), fg=C["bg"], bg=roi_color,
                  relief="flat", command=start_roi)
        _roi_btn.pack(side="right", ipadx=6, ipady=2, padx=(0,4))

        tk.Button(btn_frame, text="📷 캡처 시작",
                  font=("맑은 고딕", fsc(8), "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=start_ocr).pack(side="right", ipadx=8, ipady=2)

        tk.Frame(win, bg=C["border"], height=1).pack(fill="x", padx=0)

        result_frame = tk.Frame(win, bg=C["bg"])
        result_frame.pack(fill="x", padx=12, pady=8)

        echo_score_labels = []
        for i in range(NUM_ECHO):
            row = tk.Frame(result_frame, bg=C["bg"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"에코{ROMAN[i]}",
                     font=("맑은 고딕", fsc(8)), fg=C["dim"], bg=C["bg"], width=6, anchor="w").pack(side="left")
            lbl = tk.Label(row, textvariable=echo_scores[i],
                           font=("맑은 고딕", fsc(9), "bold"), fg=C["text"], bg=C["bg"], anchor="w")
            lbl.pack(side="left", padx=4)
            echo_score_labels.append(lbl)

        tk.Frame(result_frame, bg=C["border"], height=1).pack(fill="x", pady=4)

        total_label = tk.Label(result_frame, text="",
                               font=("맑은 고딕", fsc(11), "bold"), fg=C["gold_lt"], bg=C["bg"],
                               anchor="center")
        total_label.pack(fill="x")

        grade_label = tk.Label(result_frame, text="",
                               font=("맑은 고딕", fsc(9)), fg=C["dim"], bg=C["bg"], anchor="center")
        grade_label.pack(fill="x", pady=(0,4))

        bf = tk.Frame(win, bg=C["bg"])
        bf.pack(fill="x", padx=12, pady=(0,8))

        def _update_scores():
            """옵션 변경 시 즉시 에코별 점수 업데이트 (총점은 기입된 에코만)"""
            try:
                try:
                    max_reso = float(max_reso_var.get())
                except (ValueError, tk.TclError):
                    max_reso = 62.0

                total_reso = 0.0
                filled_scores = []
                for i in range(NUM_ECHO):
                    opts = all_options[i]
                    has_any = any(o.get("option") and o.get("value") is not None for o in opts)
                    if has_any:
                        s = calc_echo_score(opts)
                        echo_scores[i].set(f"{s:.2f}")
                        filled_scores.append(s)
                        for opt in opts:
                            if opt.get("option") == "공명효율%" and opt.get("value"):
                                total_reso += opt["value"]
                    else:
                        echo_scores[i].set("—")

                if not filled_scores:
                    total_label.configure(text="", fg=C["text"])
                    grade_label.configure(text="", fg=C["dim"])
                    return

                total, excess = calc_total(filled_scores, total_reso, max_reso)

                if total >= 75:   grade, color = "SS", "#ff4444"
                elif total >= 60: grade, color = "S",  C["gold_lt"]
                elif total >= 50: grade, color = "A",  "#4caf50"
                elif total >= 30: grade, color = "B",  "#2196f3"
                elif total >= 20: grade, color = "C",  C["dim"]
                else:             grade, color = "D",  C["dim"]

                n = len(filled_scores)
                total_label.configure(
                    text=f"총점: {total:.2f}  [{grade}]  ({n}/5 에코)",
                    fg=color)
                excess_text = f"공효 초과: {excess:.1f} → -{1.5*excess:.2f}점" if excess > 0 else ""
                grade_label.configure(text=excess_text, fg=C["red"] if excess > 0 else C["dim"])

            except Exception:
                pass

        def calc_score():
            _update_scores()

        def reset_all():
            _ocr_active[0] = False
            try:
                import keyboard as _kb2
                for hk in ["f9","enter","esc"]:
                    try: _kb2.remove_hotkey(hk)
                    except: pass
            except Exception: pass
            for i in range(NUM_ECHO):
                all_options[i] = [{"option":"","value":None} for _ in range(NUM_OPTS)]
                echo_scores[i].set("—")
            total_label.configure(text="")
            grade_label.configure(text="")
            ocr_status.configure(text="")
            _ocr_captures.clear()
            refresh_options()
            _update_scores()

        tk.Button(bf, text="점수 계산",
                  font=("맑은 고딕", fsc(9), "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=calc_score).pack(side="left", ipadx=12, ipady=4, padx=(0,8))
        tk.Button(bf, text="초기화",
                  font=("맑은 고딕", fsc(9)), fg=C["text"], bg=C["tbl_hd"],
                  relief="flat", command=reset_all).pack(side="left", ipadx=12, ipady=4, padx=(0,8))
        tk.Button(bf, text="닫기",
                  font=("맑은 고딕", fsc(9)), fg=C["text"], bg=C["tbl_hd"],
                  relief="flat", command=win.destroy).pack(side="left", ipadx=12, ipady=4)

        select_echo(0)
        win.update_idletasks()
        win.deiconify()
        _place_beside_card(win, 420, win.winfo_reqheight(), self)

    def _notes_row(self, p):
        tk.Label(p, text="참고사항",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=10, pady=4, anchor="w").pack(fill="x")
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x")
        for line in self.char.get("notes", "").splitlines():
            tk.Label(p, text=line,
                     font=("맑은 고딕", 9), fg=C["dim"], bg=C["tbl"],
                     padx=10, pady=2, anchor="w",
                     wraplength=self.W - 24, justify="left").pack(fill="x")
        tk.Frame(p, bg=C["tbl"], height=4).pack()



class MainPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"딸잘키  v{CURRENT_VER}")
        self.root.configure(bg=C["bg"])
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.geometry("480x170")
        if os.path.exists(ICON_FILE):
            try:
                self.root.iconbitmap(ICON_FILE)
            except Exception:
                pass
        self.chars: dict = load_chars()
        self._popup: Optional[CharCard] = None
        self._last_card_pos: Optional[tuple] = None
        self._dropdown = None
        self._dd_items: list = []
        self._dd_index: int = -1
        self._last_query: str = ""
        self._favorites: list = _settings.get("favorites", [])
        self._search_history: list = []
        self._compact: bool = False
        self._echo_score_saved: dict = {}

        self._build_ui()
        self.root.update_idletasks()
        self.root.geometry(f"480x{self.root.winfo_reqheight()}")
        self.root.bind("<Configure>", self._on_root_move)
        self._poll_entry()

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=C["tbl_hd"])
        hdr.pack(fill="x")
        hdr_lbl = tk.Label(hdr, text="⚡  명조 이잘키 오버레이",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8)
        hdr_lbl.pack(side="left")
        hdr_lbl.bind("<Button-3>", lambda e: self._toggle_compact())
        hdr.bind("<Button-1>", lambda e: self._close_dropdown())
        hdr_lbl.bind("<Button-1>", lambda e: self._close_dropdown())
        cur_theme = _settings.get("theme", "default")
        theme_label = "🌙 다크" if cur_theme == "default" else "☀ 디폴트"
        def toggle_theme():
            new_t = "dark" if _settings.get("theme", "default") == "default" else "default"
            _settings["theme"] = new_t
            save_settings(_settings)
            messagebox.showinfo("테마 변경", "다음 실행부터 적용됩니다.")
        tbtn = tk.Label(hdr, text=theme_label,
                        font=("맑은 고딕", 8), fg=C["dim"], bg=C["tbl_hd"],
                        padx=10, cursor="hand2")
        tbtn.pack(side="right")
        tbtn.bind("<Button-1>", lambda e: toggle_theme())

        self._fav_frame = tk.Frame(hdr, bg=C["tbl_hd"])
        self._fav_frame.pack(side="left", fill="x", expand=True, padx=4)
        self._refresh_fav_ui()

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        sf = tk.Frame(self.root, bg=C["bg"], pady=12, padx=12)
        sf.pack(fill="x")

        self._entry = tk.Entry(
            sf,
            font=("맑은 고딕", 12),
            bg=C["tbl_hd"], fg=C["text"],
            insertbackground=C["gold_lt"],
            relief="flat", bd=0)
        self._entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self._entry.bind("<Return>",    lambda e: self._do_search())
        self._entry.bind("<Down>",      lambda e: self._dd_move(1))
        self._entry.bind("<Up>",        lambda e: self._dd_move(-1))
        self._entry.bind("<Escape>",    lambda e: self._close_dropdown())
        self._entry.bind("<Key>",       lambda e: self.root.after(1, self._check_entry))
        self._entry.bind("<Button-1>", lambda e: self._on_focus_in())
        self._entry.bind("<FocusOut>", lambda e: self.root.after(150, self._close_dropdown))
        self._entry.focus_set()

        tk.Button(
            sf, text="검색",
            font=("맑은 고딕", 9, "bold"),
            fg=C["bg"], bg=C["gold_lt"],
            activebackground=C["gold_dim"], activeforeground=C["white"],
            relief="flat", bd=0, padx=10, pady=4,
            command=self._do_search
        ).pack(side="left")

        self._div_slider = tk.Frame(self.root, bg=C["border"], height=1)
        self._div_slider.pack(fill="x")

        self._sf2 = tk.Frame(self.root, bg=C["bg"])
        self._sf2.pack(fill="x", padx=12, pady=(6,0))
        tk.Label(self._sf2, text="가이드 투명도",
                 font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"]).pack(side="left")
        self._alpha_var = tk.IntVar(value=93)
        alpha_slider = tk.Scale(
            self._sf2, from_=0, to=100, resolution=1,
            orient="horizontal", variable=self._alpha_var,
            bg=C["bg"], fg=C["dim"], troughcolor=C["tbl_hd"],
            highlightthickness=0, bd=0, showvalue=False,
            command=self._set_popup_alpha
        )
        alpha_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._div_bottom = tk.Frame(self.root, bg=C["border"], height=1)
        self._div_bottom.pack(fill="x")

        self._bottom = tk.Frame(self.root, bg=C["bg"])
        self._bottom.pack(fill="x", padx=12, pady=8)

        tk.Label(self._bottom,
            text="※ 방랑자는 속성만 or 이름붙여서 (예:기류, 기류방랑자)\nCitation:쿠로발냄새킁카킁카[명조챈], 닝냉뇽(유튜브)\n[명조시뮬]",
            font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"],
            anchor="w", justify="left", wraplength=340).pack(side="left")

        tk.Label(self._bottom,
            text="made by 소리나",
            font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"],
            anchor="e").pack(side="right")

        help_btn = tk.Label(self._bottom, text="[어케씀?]",
                            font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["bg"],
                            cursor="hand2")
        help_btn.pack(side="right", padx=6)
        help_btn.bind("<Button-1>", lambda e: self._show_help())

    def _show_help(self):
        win = tk.Toplevel(self.root)
        win.title("사용법")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.resizable(False, False)
        try:
            if os.path.exists(ICON_FILE):
                win.iconbitmap(ICON_FILE)
        except Exception:
            pass

        tk.Label(win, text="⚡  딸잘키 사용법",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")

        from tkinter import scrolledtext
        txt = scrolledtext.ScrolledText(
            win, font=("맑은 고딕", 9),
            bg=C["tbl_hd"], fg=C["text"],
            relief="flat", bd=0,
            wrap="word", state="normal",
            width=44, height=24)
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        help_text = """
🔍 캐릭터 검색
검색창에 캐릭터 이름 입력 후 Enter 또는 검색 버튼 클릭
입력 중 매칭되는 캐릭터 목록이 드롭다운으로 표시됩니다
↑↓ 키로 이동, Enter로 선택 가능

📋 카드 팝업 보는 법
• 스킬 — 스킬 찍는 우선순위
• 포지션 — 파티에서 역할
• 사이클 — 교체 사이클 (직접 편집 가능)
• 노드 옵션 — 패시브 추가 스탯 항목
• 추천 무기 — 1순위부터 표기
• 에코 세트/빌드 — 추천 에코 구성
• 크확/크피 — 목표 크리티컬 수치
• 공명효율/공격력/에너지 — 목표 스탯

▶ 파티 버튼
추천파티 열람

▶ 기본기 버튼
카드 상단 [▶ 기본기] 클릭 시 유튜브 영상으로 이동

✎ 사이클 편집
카드 사이클 칸의 [✎ 편집] 버튼 클릭 후 입력 후 저장
메모칸 클릭으로 오버레이 팝업 가능
-/+ 버튼으로 크기 조절

★ 즐겨찾기
카드 팝업 우상단 ★ 클릭으로 최대 3명 등록
메인 패널 타이틀 옆에 표시, 클릭 시 바로 팝업
우클릭으로 삭제

📊 에코 점수 계산
카드 팝업 하단 [📊 에코 점수 계산] 클릭
영역지정 해서 에코 부옵(5칸) 잘 보이게 지정
최대 공효 (125%=25) 설정 한뒤 캡쳐시작 
에코 1번째부터 5번째까지 F9로 캡쳐하여 자동기입
인식 안된 수치나 오인식됐건 드롭다운으로 선택

🌙 테마 변경
메인 패널 우상단 [다크/디폴트] 버튼 클릭
다음 실행부터 적용됩니다

📦 컴팩트 모드
메인 패널 타이틀 텍스트 우클릭으로 토글
슬라이더/안내문구 숨겨서 공간 절약
"""
        txt.insert("1.0", help_text.strip())
        txt.configure(state="disabled")

        tk.Frame(win, bg=C["border"], height=1).pack(fill="x")
        tk.Button(win, text="닫기",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=win.destroy).pack(pady=8, ipadx=16, ipady=4)

        win.update_idletasks()
        _place_on_cursor_monitor(win, 380, win.winfo_reqheight())

    def _on_focus_in(self):
        q = self._entry.get().strip()
        if not q and self._search_history:
            self._show_dropdown(self._search_history, is_history=True)

    def _poll_entry(self):
        self._check_entry()
        self.root.after(100, self._poll_entry)

    def _check_entry(self):
        q = self._entry.get().strip()
        if q != self._last_query:
            self._last_query = q
            self._on_entry_change(q)

    def _toggle_compact(self):
        self._compact = not self._compact
        if self._compact:
            self._div_slider.pack_forget()
            self._sf2.pack_forget()
            self._div_bottom.pack_forget()
            self._bottom.pack_forget()
        else:
            self._div_slider.pack(fill="x")
            self._sf2.pack(fill="x", padx=12, pady=(6,0))
            self._div_bottom.pack(fill="x")
            self._bottom.pack(fill="x", padx=12, pady=8)
        self.root.update_idletasks()
        self.root.geometry(f"480x{self.root.winfo_reqheight()}")

    def _on_root_move(self, e):
        if self._dropdown and e.widget == self.root:
            x = self._entry.winfo_rootx()
            y = self._entry.winfo_rooty() + self._entry.winfo_height()
            w = self._entry.winfo_width()
            h = self._dropdown.winfo_height()
            self._dropdown.geometry(f"{w}x{h}+{x}+{y}")

    def _on_entry_change(self, q=""):
        self._close_dropdown()
        if not q:
            if self._search_history:
                self._show_dropdown(self._search_history, is_history=True)
            return
        matches = [k for k in self.chars if q in k or k in q]
        self._show_dropdown(matches)

    def _show_dropdown(self, matches, is_history=False):
        self._close_dropdown()
        self._dd_items = matches
        self._dd_index = -1

        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width()

        dd = tk.Toplevel(self.root)
        dd.overrideredirect(True)
        dd.attributes("-topmost", True)
        dd.geometry(f"{w}x1+{x}+{y}")
        dd.configure(bg=C["border"])

        inner = tk.Frame(dd, bg=C["hd"], padx=1, pady=1)
        inner.pack(fill="both", expand=True)

        if is_history and matches:
            tk.Label(inner, text="최근 검색",
                     font=("맑은 고딕", 8), fg=C["dim"], bg=C["tbl_hd"],
                     padx=10, pady=3, anchor="w").pack(fill="x")
            tk.Frame(inner, bg=C["border"], height=1).pack(fill="x")

        if matches:
            for i, name in enumerate(matches):
                lbl = tk.Label(inner, text=name,
                               font=("맑은 고딕", 10), fg=C["text"], bg=C["hd"],
                               padx=10, pady=5, anchor="w", cursor="hand2")
                lbl.pack(fill="x")
                lbl.bind("<Enter>",    lambda e, l=lbl: l.configure(bg=C["tbl_hd"], fg=C["gold_lt"]))
                lbl.bind("<Leave>",    lambda e, l=lbl: l.configure(bg=C["hd"], fg=C["text"]))
                lbl.bind("<Button-1>", lambda e, n=name: self._select_item(n))
        else:
            tk.Label(inner, text="검색 결과 없음",
                     font=("맑은 고딕", 9), fg=C["dim"], bg=C["hd"],
                     padx=10, pady=6, anchor="w").pack(fill="x")

        dd.update_idletasks()
        dd.geometry(f"{w}x{inner.winfo_reqheight()}+{x}+{y}")
        dd.lift()

        def _keep_on_top():
            try:
                if self._dropdown and self._dropdown.winfo_exists():
                    self._dropdown.lift()
                    self._dropdown.after(100, _keep_on_top)
            except Exception:
                pass
        dd.after(100, _keep_on_top)

        self._dropdown = dd

    def _close_dropdown(self):
        if self._dropdown:
            try:
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None
        self._dd_items = []
        self._dd_index = -1

    def _dd_move(self, direction):
        if not self._dd_items:
            return
        self._dd_index = (self._dd_index + direction) % len(self._dd_items)
        name = self._dd_items[self._dd_index]
        self._entry.delete(0, "end")
        self._entry.insert(0, name)
        self._last_query = name
        self._entry.icursor("end")
        if self._dropdown:
            try:
                inner = self._dropdown.winfo_children()[0]
                for i, child in enumerate(inner.winfo_children()):
                    if isinstance(child, tk.Label):
                        if i == self._dd_index:
                            child.configure(bg=C["tbl_hd"], fg=C["gold_lt"])
                        else:
                            child.configure(bg=C["hd"], fg=C["text"])
            except Exception:
                pass

    def _select_item(self, name):
        self._entry.delete(0, "end")
        self._entry.insert(0, name)
        self._last_query = name
        self._close_dropdown()
        self._do_search()

    def _refresh_fav_ui(self):
        for w in self._fav_frame.winfo_children():
            w.destroy()
        for i, name in enumerate(self._favorites):
            if i > 0:
                tk.Label(self._fav_frame, text="|",
                         font=("맑은 고딕", 8), fg=C["gold_dim"], bg=C["tbl_hd"],
                         padx=0).pack(side="left")
            btn = tk.Label(self._fav_frame, text=name,
                           font=("맑은 고딕", 8), fg=C["gold_lt"], bg=C["tbl_hd"],
                           padx=6, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, n=name: self._open_fav(n))
            btn.bind("<Button-3>", lambda e, n=name: self._remove_fav(n))

    def _open_fav(self, name):
        found = self.chars.get(name)
        if not found:
            return
        self._close_popup()
        self._make_popup(found)

    def _fav_toggle(self, name):
        if name in self._favorites:
            self._favorites.remove(name)
        else:
            if len(self._favorites) >= 3:
                self._show_toast("즐겨찾기가 가득 찼습니다 (최대 3명)\n(우클릭으로 삭제할 수 있습니다)")
                return "full"
            self._favorites.append(name)
        _settings["favorites"] = self._favorites
        save_settings(_settings)
        self._refresh_fav_ui()

    def _fav_check(self, name):
        return name in self._favorites

    def _remove_fav(self, name):
        if name in self._favorites:
            self._favorites.remove(name)
            _settings["favorites"] = self._favorites
            save_settings(_settings)
            self._refresh_fav_ui()

    def _show_toast(self, msg):
        if self._popup:
            try:
                self._popup.show_toast(msg)
            except Exception:
                pass

    def _make_popup(self, found):
        def on_move(x, y):
            self._last_card_pos = (x, y)
        def reopen(char):
            self._popup = CharCard(self.root, char, on_reopen=reopen,
                                   on_move=on_move, init_pos=self._last_card_pos,
                                   on_fav_toggle=self._fav_toggle,
                                   on_fav_check=self._fav_check,
                                   main_panel=self)
            try:
                self._popup._target_alpha = self._alpha_var.get() / 100.0
            except Exception:
                pass
        self._popup = CharCard(self.root, found, on_reopen=reopen,
                               on_move=on_move, init_pos=self._last_card_pos,
                               on_fav_toggle=self._fav_toggle,
                               on_fav_check=self._fav_check,
                               main_panel=self)
        try:
            self._popup._target_alpha = self._alpha_var.get() / 100.0
        except Exception:
            pass

    def _set_popup_alpha(self, val):
        alpha = int(float(val)) / 100.0
        if self._popup:
            try:
                self._popup._target_alpha = alpha
                self._popup.attributes("-alpha", alpha)
            except Exception:
                pass

    def _do_search(self):
        q = self._entry.get().strip()
        if not q:
            return
        self._close_dropdown()
        self._entry.delete(0, "end")
        self._last_query = ""
        found = None
        for k, v in self.chars.items():
            if q in k or k in q:
                found = v
                break
        self._close_popup()
        if found:
            name = found["name"]
            if name in self._search_history:
                self._search_history.remove(name)
            self._search_history.insert(0, name)
            self._search_history = self._search_history[:5]
            self._make_popup(found)

    def _close_popup(self):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    def run(self):
        check_and_update(self.root)
        self.root.mainloop()


OCR_CORRECTIONS = {
    "크리티결": "크리티컬", "크리티칼": "크리티컬", "크리티걸": "크리티컬",
    "크리EI결": "크리티컬", "크리EI컬": "크리티컬",
    "크리EW결": "크리티컬", "크리EW컬": "크리티컬",
    "크리T컬": "크리티컬",
    "k크리티컬": "크리티컬", "ck리티컬": "크리티컬",
    "고것려": "공격력", "고겨려": "공격력", "고겨궐": "공격력",
    "고겨력": "공격력", "공겨력": "공격력", "고격력": "공격력",
    "공겨궐": "공격력", "고것력": "공격력",
    "공곅력": "공격력", "공겪력": "공격력", "공겯력": "공격력",
    "공격r력": "공격력", "공격rr": "공격력",
    "공명효음": "공명효율", "공명효윰": "공명효율", "공명효윤": "공명효율",
    "공명효를": "공명효율", "공명효룰": "공명효율",
    "꿀명효음": "공명효율", "꿀명효율": "공명효율",
    "공명호율": "공명효율", "공명흐율": "공명효율",
    "공명H율": "공명효율", "공명H효율": "공명효율",
    "공명효r율": "공명효율",
    "피히보너스": "피해보너스", "피히r보너스": "피해보너스",
    "피6H": "피해", "피헤": "피해", "피H": "피해",
    "P해": "피해", "F해": "피해",
    "방어럭": "방어력", "방어렉": "방어력",
    "방어r력": "방어력", "방어 력": "방어력",
    "보니스": "보너스", "보나스": "보너스",
    "보너S": "보너스", "보너 스": "보너스", "B너스": "보너스",
    "강공 격": "강공격", "강공g격": "강공격", "강g격": "강공격",
    "일반 공격": "일반공격", "일반공 격": "일반공격", "일반공g격": "일반공격",
    "해B방": "해방", "H방": "해방",
    "크리티컬피해": "크리티컬피해",
    "크리티결피해": "크리티컬피해",
    "크리EI결피해": "크리티컬피해", "크리EI컬피해": "크리티컬피해",
    "크리EW결피해": "크리티컬피해", "크리EW컬피해": "크리티컬피해",
    "크리EI피해": "크리티컬피해", "크리EW피해": "크리티컬피해",
    "k크리티컬피해": "크리티컬피해", "k크리EI컬피해": "크리티컬피해",
    "k크리EW피해": "크리티컬피해",
    "크리티컬데미지": "크리티컬피해",
    "공명해방피해보너스": "공명해방피해보너스",
    "공명스킬피해보너스": "공명스킬피해보너스",
    "강공격피해보너스": "강공격피해보너스",
    "일반공격피해보너스": "일반공격피해보너스",
}

if __name__ == "__main__":
    MainPanel().run()
