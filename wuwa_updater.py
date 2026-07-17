import tkinter as tk
from tkinter import ttk
import threading, urllib.request, json, os, sys, subprocess, shutil

REPO        = "kedaygon/wuwa_yeejalky_overlay"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/version.txt"
API_URL     = f"https://api.github.com/repos/{REPO}/releases/latest"

def _load_current_ver():
    try:
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "version.txt"), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1.00"

CURRENT_VER = _load_current_ver()

THEMES = {
    "default": {
        "bg":      "#1a1208",
        "hd":      "#2d1f08",
        "gold_lt": "#e8b84b",
        "gold_dim":"#7a5a1a",
        "text":    "#f0e6cc",
        "dim":     "#a09070",
        "border":  "#5a3e18",
        "tbl_hd":  "#3d2a0e",
        "tbl":     "#231608",
        "white":   "#f8f0e0",
        "green":   "#4caf50",
    },
    "dark": {
        "bg":      "#121212",
        "hd":      "#2c2c2c",
        "gold_lt": "#bb86fc",
        "gold_dim":"#333333",
        "text":    "#ffffff",
        "dim":     "#757575",
        "border":  "#383838",
        "tbl_hd":  "#272727",
        "tbl":     "#121212",
        "white":   "#e8e0ff",
        "green":   "#4caf50",
    },
}

def _load_settings_theme():
    try:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(appdata, "ddaljalky", "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("theme", "default")
    except Exception:
        pass
    return "default"

C = THEMES.get(_load_settings_theme(), THEMES["default"])

def _get_appdata_dir():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "ddaljalky")
    os.makedirs(path, exist_ok=True)
    return path

def _load_last_version():
    try:
        path = os.path.join(_get_appdata_dir(), "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "last_version" in data:
                    return data["last_version"]
    except Exception:
        pass
    # last_version 없으면 현재 버전으로 초기화 저장
    _save_last_version(CURRENT_VER)
    return CURRENT_VER

def _save_last_version(ver):
    try:
        path = os.path.join(_get_appdata_dir(), "settings.json")
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["last_version"] = ver
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def _ssl_context():
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_resource(filename):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

def fetch_text(url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ddaljalky-overlay"})
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            return r.read().decode("utf-8").strip()
    except Exception:
        return None

def fetch_json(url, timeout=5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ddaljalky-overlay"})
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def download_file(url, dest, progress_cb=None):
    req = urllib.request.Request(url, headers={"User-Agent": "ddaljalky-overlay"})
    with urllib.request.urlopen(req, context=_ssl_context()) as r:
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded / total)

def get_asset_url(release_data, filename):
    for asset in release_data.get("assets", []):
        if asset["name"] == filename:
            return asset["browser_download_url"]
    return None

class UpdateDialog(tk.Toplevel):
    def __init__(self, master, latest_ver, has_exe, has_json, on_confirm, release_body=""):
        super().__init__(master)
        self.title("업데이트 알림")
        self.configure(bg=C["bg"])
        self.attributes("-topmost", True)
        self.resizable(False, False)
        try:
            icon = get_resource("app.ico")
            if os.path.exists(icon):
                self.iconbitmap(icon)
        except Exception:
            pass
        self._on_confirm = on_confirm
        self._has_exe  = has_exe
        self._has_json = has_json
        self._json_only = has_json and not has_exe

        # 헤더
        tk.Label(self, text="⚡  업데이트 알림",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(body, text=f"새 버전이 있습니다!",
                 font=("맑은 고딕", 10, "bold"), fg=C["gold_lt"], bg=C["bg"],
                 anchor="w").pack(fill="x")
        tk.Label(body, text=f"현재: {CURRENT_VER}  →  최신: {latest_ver}",
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["bg"],
                 anchor="w").pack(fill="x", pady=(2, 8))

        if release_body:
            tk.Label(body, text=release_body,
                     font=("맑은 고딕", 9), fg=C["dim"], bg=C["bg"],
                     anchor="w", justify="left", wraplength=320).pack(fill="x")

        # 진행바 (숨김 상태로 준비)
        self._prog_frame = tk.Frame(self, bg=C["bg"])
        self._prog_var = tk.DoubleVar()
        self._prog_label = tk.Label(self._prog_frame, text="",
                                    font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"])
        self._prog_label.pack(fill="x", padx=16)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Gold.Horizontal.TProgressbar",
                        troughcolor=C["tbl_hd"], background=C["gold_lt"], borderwidth=0)
        self._prog_bar = ttk.Progressbar(self._prog_frame, variable=self._prog_var,
                                          maximum=1.0, style="Gold.Horizontal.TProgressbar")
        self._prog_bar.pack(fill="x", padx=16, pady=(0, 8))

        # 버튼
        bf = tk.Frame(self, bg=C["bg"])
        bf.pack(fill="x", padx=16, pady=(0, 12))
        self._confirm_btn = tk.Button(bf, text="업데이트",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=self._start_update)
        self._confirm_btn.pack(side="left", ipadx=12, ipady=4, padx=(0, 8))
        tk.Button(bf, text="나중에",
                  font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl_hd"],
                  relief="flat", command=self.destroy).pack(side="left", ipadx=12, ipady=4)

        self.update_idletasks()
        self.geometry(f"360x{self.winfo_reqheight()}")

    def _start_update(self):
        self._confirm_btn.configure(state="disabled")
        self._prog_frame.pack(fill="x", before=self._confirm_btn.master)
        threading.Thread(target=self._do_update, daemon=True).start()

    def _set_progress(self, val, label=""):
        self._prog_var.set(val)
        if label: self._prog_label.configure(text=label)

    def _do_update(self):
        try:
            self._on_confirm(self._set_progress)
            # 업데이트 완료 - 창 닫기 버튼만 표시
            self.after(0, self._show_done)
        except Exception as e:
            self.after(0, lambda: self._prog_label.configure(
                text=f"오류: {e}", fg="#ff6b6b"))

    def _show_done(self):
        for w in self.winfo_children():
            w.destroy()
        tk.Label(self, text="⚡  업데이트 완료",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(body, text="✅  업데이트가 완료되었습니다!",
                 font=("맑은 고딕", 10, "bold"), fg=C["gold_lt"], bg=C["bg"],
                 anchor="w").pack(fill="x")
        if self._json_only:
            done_text = "데이터가 업데이트 되었습니다.\n재시작 후 새 데이터가 적용됩니다."
            close_cmd = self.destroy
        else:
            done_text = "업데이트 완료 후 정리까지 5~10초 정도 소요되므로\n이후 프로그램을 다시 실행해주세요."
            close_cmd = lambda: os._exit(0)
        tk.Label(body, text=done_text,
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["bg"],
                 anchor="w", pady=6, justify="left").pack(fill="x")
        tk.Button(self, text="닫기",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=close_cmd).pack(pady=(0, 12), ipadx=16, ipady=4)


def check_and_update(master):
    def _check():
        latest_ver = fetch_text(VERSION_URL)
        last_ver = _load_last_version()
        if not latest_ver or latest_ver == last_ver:
            return

        release = fetch_json(API_URL)
        if not release:
            return

        exe_url      = get_asset_url(release, "ddaljalky.exe")
        json_url     = get_asset_url(release, "wuwa_chars.json")
        has_exe  = bool(exe_url)
        has_json = bool(json_url)
        release_body = (release.get("body") or "").strip()

        if not has_exe and not has_json:
            return

        def on_confirm(progress_cb):
            base = get_base_dir()
            appdata_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ddaljalky")
            os.makedirs(appdata_dir, exist_ok=True)

            data_jobs = []
            if json_url:     data_jobs.append((json_url,     os.path.join(appdata_dir, "wuwa_chars.json"),    "캐릭터 데이터 다운로드 중..."))

            data_ratio = 0.4 if has_exe else 1.0
            for i, (url, dest, label) in enumerate(data_jobs):
                seg_start = data_ratio * i / len(data_jobs)
                seg_end   = data_ratio * (i + 1) / len(data_jobs)
                download_file(url, dest,
                              lambda p, s=seg_start, e=seg_end, lb=label:
                              progress_cb(s + p * (e - s), lb))

            _save_last_version(latest_ver)
            progress_cb(data_ratio, "데이터 완료!")

            if has_exe and exe_url:
                progress_cb(0.4, "프로그램 다운로드 중...")
                exe_path = sys.executable if getattr(sys, "frozen", False) else None
                if exe_path:
                    tmp_path = exe_path + ".new"
                    download_file(exe_url, tmp_path,
                                  lambda p: progress_cb(0.4 + p * 0.6, "프로그램 다운로드 중..."))
                    progress_cb(1.0, "완료! 프로그램을 다시 실행해주세요")
                    # bat으로 exe 교체 (재실행은 유저가 직접)
                    bat = os.path.join(base, "_update.bat")
                    old_path = exe_path + ".old"
                    bat_lines = "\r\n".join([
                        "@echo off",
                        f'cd /d "{base}"',
                        "timeout /t 5 /nobreak >nul",
                        f'move /y "{exe_path}" "{old_path}"',
                        f'move /y "{tmp_path}" "{exe_path}"',
                        "timeout /t 5 /nobreak >nul",
                        f'if exist "{old_path}" del /f /q "{old_path}"',
                        "del %~f0",
                    ])
                    with open(bat, "w", encoding="cp949") as f:
                        f.write(bat_lines)
                    subprocess.Popen(
                        ["cmd", "/c", bat],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        close_fds=True
                    )

        master.after(0, lambda: UpdateDialog(master, latest_ver, has_exe, has_json, on_confirm, release_body))

    threading.Thread(target=_check, daemon=True).start()
