import tkinter as tk
from tkinter import scrolledtext
import re, json, os, sys
from typing import Optional
from wuwa_updater import check_and_update, CURRENT_VER


def get_resource(filename):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

def get_appdata_dir():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(appdata, "ddaljalky")
    os.makedirs(path, exist_ok=True)
    return path

def get_data_file():
    import urllib.request, shutil
    appdata_json = os.path.join(get_appdata_dir(), "wuwa_chars.json")
    if not os.path.exists(appdata_json):
        # 1. 번들 json 시도
        bundled = get_resource("wuwa_chars.json")
        if os.path.exists(bundled):
            shutil.copy(bundled, appdata_json)
        else:
            # 2. 번들 없으면 GitHub API로 최신 릴리즈 json 다운로드
            try:
                api_url = "https://api.github.com/repos/kedaygon/wuwa_yeejalky_overlay/releases/latest"
                req = urllib.request.Request(api_url, headers={"User-Agent": "ddaljalky-overlay"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    release = json.loads(r.read().decode("utf-8"))
                dl_url = None
                for asset in release.get("assets", []):
                    if asset["name"] == "wuwa_chars.json":
                        dl_url = asset["browser_download_url"]
                        break
                if dl_url:
                    req2 = urllib.request.Request(dl_url, headers={"User-Agent": "ddaljalky-overlay"})
                    with urllib.request.urlopen(req2, timeout=10) as r2:
                        with open(appdata_json, "wb") as f:
                            f.write(r2.read())
            except Exception as e:
                print(f"[초기 데이터 다운로드 실패] {e}")
    return appdata_json

DATA_FILE = get_data_file()
ICON_FILE  = get_resource("00085-3009505209.ico")

C = {
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
    "cycle_bg":  "#1e1a10",
    "cycle_txt": "#d4c49a",
}

ELEM_COLOR = {
    "기류": "#82e0aa", "빙결": "#74c7ec", "글로시": "#da77f2",
    "용융": "#ff9b5e", "치유": "#f9e17a", "전도":   "#d4aaff",
    "인멸": "#ff8080", "암흑": "#9b8ec4", "회절":   "#ffe066",
    "광학": "#a8d8ea",
}


# ── 데이터 로드/저장 ─────────────────────────────────────────────────

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


# ── 카드 팝업 ────────────────────────────────────────────────────────

class CharCard(tk.Toplevel):
    W = 480

    def __init__(self, master, char: dict):
        super().__init__(master)
        self.char = char
        self._master = master
        self._dx = 0
        self._dy = 0

        # 창 기본 설정
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg=C["border"])

        # 콘텐츠 먼저 빌드
        self._build()

        # update_idletasks() 후 화면 크기 읽기 → geometry 안전하게 설정
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        x = max(0, sw - self.W - 16)
        self.geometry(f"{self.W}x{self.winfo_reqheight()}+{x}+40")

        # 드래그
        self.bind("<ButtonPress-1>", self._drag_start)
        self.bind("<B1-Motion>",     self._drag_move)
        # 닫기
        self.bind("<Escape>",    lambda e: self.destroy())
        self.bind("<Button-3>",  lambda e: self.destroy())

        # 페이드인
        self._fade(0.0)

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.winfo_x() + e.x - self._dx
        y = self.winfo_y() + e.y - self._dy
        self.geometry(f"+{x}+{y}")

    def _fade(self, a):
        if a < 0.93:
            self.attributes("-alpha", a)
            self.after(14, lambda: self._fade(min(a + 0.08, 0.93)))
        else:
            self.attributes("-alpha", 0.93)

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
        tk.Frame(p, bg=C["bg"], height=8).pack()

    def _div(self, p):
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x")

    # ── 이름 / 스킬 ─────────────────────────────────────────────────
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

    # ── 포지션 / 사이클 / 노드 ──────────────────────────────────────
    def _pos_cycle_node(self, p):
        row = tk.Frame(p, bg=C["tbl"])
        row.pack(fill="x")

        # 포지션
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

        # 사이클
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

        tk.Frame(cyc, bg=C["border"], height=1).pack(fill="x")

        cyc_txt = self.char.get("cycle", "").strip()
        if cyc_txt:
            tk.Label(cyc, text=cyc_txt,
                     font=("맑은 고딕", 9), fg=C["cycle_txt"], bg=C["cycle_bg"],
                     padx=8, pady=6, anchor="nw", justify="left",
                     wraplength=148).pack(fill="both", expand=True)
        else:
            tk.Label(cyc, text="✎ 편집 버튼으로 입력",
                     font=("맑은 고딕", 8), fg=C["dim"], bg=C["cycle_bg"],
                     pady=14).pack(fill="both", expand=True)

        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y")

        # 노드 옵션
        nd = tk.Frame(row, bg=C["tbl"])
        nd.pack(side="left", fill="both", expand=True)
        tk.Label(nd, text="노드 옵션",
                 font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 pady=4).pack(fill="x")
        tk.Frame(nd, bg=C["border"], height=1).pack(fill="x")
        tk.Label(nd, text=self.char.get("node_option") or "—",
                 font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl"],
                 pady=6, wraplength=120).pack(fill="both", expand=True)

    def _edit_cycle(self):
        win = tk.Toplevel(self)
        win.title(f"{self.char['name']} 사이클 편집")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        win.geometry("360x240")
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
        txt.insert("1.0", self.char.get("cycle", ""))

        def do_save():
            self.char["cycle"] = txt.get("1.0", "end").strip()
            chars = load_chars()
            if self.char["name"] in chars:
                chars[self.char["name"]]["cycle"] = self.char["cycle"]
                save_chars(chars)
            win.destroy()
            self.destroy()
            CharCard(self._master, self.char)

        bf = tk.Frame(win, bg=C["bg"])
        bf.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(bf, text="저장",
                  font=("맑은 고딕", 9, "bold"), fg=C["bg"], bg=C["gold_lt"],
                  relief="flat", command=do_save).pack(side="left", ipadx=10, ipady=3, padx=(0, 6))
        tk.Button(bf, text="취소",
                  font=("맑은 고딕", 9), fg=C["text"], bg=C["tbl_hd"],
                  relief="flat", command=win.destroy).pack(side="left", ipadx=10, ipady=3)

    # ── 추천 무기 ────────────────────────────────────────────────────
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

    # ── 에코 세트 ────────────────────────────────────────────────────
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

        # 헤더
        for col, txt in enumerate(["에코\n주옵", "코스트", "메인 에코", "3코스트", "1코스트"]):
            tk.Label(outer, text=txt,
                     font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                     pady=4, padx=4, anchor="center").grid(
                row=0, column=col, sticky="nsew",
                padx=(0, 1) if col < 4 else 0)

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=1, column=0, columnspan=5, sticky="ew")

        # 데이터 행
        for bi, build in enumerate(builds):
            r = bi * 2 + 2
            bg = C["tbl"] if bi % 2 == 0 else C["tbl2"]

            # 에코주옵 라벨 (모든 빌드 행 병합 → rowspan)
            if bi == 0:
                tk.Label(outer, text="에코\n주옵",
                         font=("맑은 고딕", 8), fg=C["white"], bg=C["gold_dim"],
                         pady=6).grid(
                    row=2, column=0, rowspan=len(builds) * 2 - 1,
                    sticky="nsew", padx=(0, 1))

            # 코스트
            tk.Label(outer, text=build.get("tag", ""),
                     font=("맑은 고딕", 9, "bold"), fg=C["gold_lt"], bg=bg,
                     pady=6, padx=4).grid(
                row=r, column=1, sticky="nsew", padx=(0, 1))

            # 메인 에코
            tk.Label(outer, text=build.get("main", ""),
                     font=("맑은 고딕", 9), fg=C["text"], bg=bg,
                     pady=6, padx=6, anchor="center").grid(
                row=r, column=2, sticky="nsew", padx=(0, 1))

            # 3코1코 2×2: subs 리스트를 "/" 기준으로 좌/우 분리
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

            # 행 구분선 (마지막 행 제외)
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

        # 헤더
        for col, txt in enumerate(["크확\n크피", "코스트", "크확", "크피"]):
            tk.Label(outer, text=txt,
                     font=("맑은 고딕", 8, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                     pady=4, padx=4, anchor="center").grid(
                row=0, column=col, sticky="nsew",
                padx=(0, 1) if col < 3 else 0)

        tk.Frame(outer, bg=C["border"], height=1).grid(
            row=1, column=0, columnspan=4, sticky="ew")

        # 데이터 행
        for ci, cs in enumerate(crits):
            r = ci * 2 + 2
            bg = C["tbl"] if ci % 2 == 0 else C["tbl2"]

            # 크확크피 라벨 병합
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

    # ── 참고사항 ─────────────────────────────────────────────────────
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


# ── 메인 패널 ────────────────────────────────────────────────────────

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

        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=C["tbl_hd"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚡  명조 이잘키 오버레이",
                 font=("맑은 고딕", 11, "bold"), fg=C["gold_lt"], bg=C["tbl_hd"],
                 padx=12, pady=8).pack(side="left")
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        sf = tk.Frame(self.root, bg=C["bg"], pady=12, padx=12)
        sf.pack(fill="x")

        self._sv = tk.StringVar()
        self._entry = tk.Entry(
            sf, textvariable=self._sv,
            font=("맑은 고딕", 12),
            bg=C["tbl_hd"], fg=C["text"],
            insertbackground=C["gold_lt"],
            relief="flat", bd=0)
        self._entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self._entry.bind("<Return>", lambda e: self._do_search())
        self._entry.focus_set()

        tk.Button(
            sf, text="검색",
            font=("맑은 고딕", 9, "bold"),
            fg=C["bg"], bg=C["gold_lt"],
            activebackground=C["gold_dim"], activeforeground=C["white"],
            relief="flat", bd=0, padx=10, pady=4,
            command=self._do_search
        ).pack(side="left")

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        # 투명도 슬라이더
        sf2 = tk.Frame(self.root, bg=C["bg"])
        sf2.pack(fill="x", padx=12, pady=(6,0))
        tk.Label(sf2, text="가이드 투명도",
                 font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"]).pack(side="left")
        self._alpha_var = tk.DoubleVar(value=0.93)
        alpha_slider = tk.Scale(
            sf2, from_=0.3, to=1.0, resolution=0.01,
            orient="horizontal", variable=self._alpha_var,
            bg=C["bg"], fg=C["dim"], troughcolor=C["tbl_hd"],
            highlightthickness=0, bd=0, showvalue=False,
            command=self._set_popup_alpha
        )
        alpha_slider.pack(side="left", fill="x", expand=True, padx=8)

        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x")

        bottom = tk.Frame(self.root, bg=C["bg"])
        bottom.pack(fill="x", padx=12, pady=8)

        tk.Label(bottom,
            text="※ 방랑자는 속성만 or 이름붙여서 (예:기류, 기류방랑자)\nCitation:쿠로발냄새킁카킁카[명조챈], 닝냉뇽(유튜브)",
            font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"],
            anchor="w", justify="left").pack(side="left")

        tk.Label(bottom,
            text="made by 소리나",
            font=("맑은 고딕", 8), fg=C["dim"], bg=C["bg"],
            anchor="e").pack(side="right")

    def _set_popup_alpha(self, val):
        if self._popup:
            try:
                self._popup.attributes("-alpha", float(val))
            except Exception:
                pass

    def _do_search(self):
        q = self._sv.get().strip()
        if not q:
            return
        self._sv.set("")
        found = None
        for k, v in self.chars.items():
            if q in k or k in q:
                found = v
                break
        self._close_popup()
        if found:
            self._popup = CharCard(self.root, found)

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


if __name__ == "__main__":
    MainPanel().run()
