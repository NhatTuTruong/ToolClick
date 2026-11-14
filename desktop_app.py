"""
Cửa sổ ứng dụng ToolClick (tkinter) — không mở port / trình duyệt.

Chạy: python desktop_app.py
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from src.domain_filter import parse_domains_text
from src.google_region import locale_choice_labels, locale_label_for, parse_locale_choice
from src.job_runner import PROJECT_ROOT, JobSettings, launch_browser_window
from src.license_client import activate as license_activate
from src.license_client import machine_id as license_machine_id
from src.license_client import report_run as license_report_run
from src.license_client import verify_for_run
from src.proxy_config import parse_proxies_text
from src.ui_common import (
    ENV_PATH,
    env_bool,
    env_int,
    load_env_defaults,
    parse_keywords,
    save_env_from_settings,
)

# Palette (dark)
BG = "#0B1220"
SURFACE = "#151C2C"
NAVY = "#080E18"
NAVY_2 = "#1E293B"
TEXT = "#E8EEF8"
MUTED = "#8B97AB"
LINE = "#2A3348"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
DANGER = "#F87171"
DANGER_HOVER = "#EF4444"
OK = "#34D399"
WARN = "#FBBF24"
LOG_BG = "#070B14"
LOG_FG = "#E2E8F0"
FIELD = "#1A2234"
FONT_UI = ("Segoe UI", 10)
FONT_UI_SM = ("Segoe UI", 9)
FONT_UI_BD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_H = ("Segoe UI", 11, "bold")
FONT_MONO = ("Cascadia Mono", 9) if sys.platform == "win32" else ("Consolas", 9)


def _enable_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _plain_text(
    parent: tk.Misc,
    *,
    height: int,
    placeholder: str = "",
) -> tk.Text:
    wrap = tk.Frame(parent, bg=LINE, highlightthickness=0)
    inner = tk.Frame(wrap, bg=SURFACE)
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    txt = tk.Text(
        inner,
        height=height,
        wrap=tk.WORD,
        font=FONT_UI,
        bg=SURFACE,
        fg=TEXT,
        insertbackground=TEXT,
        relief=tk.FLAT,
        padx=10,
        pady=8,
        highlightthickness=0,
        bd=0,
        undo=True,
    )
    sb = ttk.Scrollbar(inner, orient=tk.VERTICAL, command=txt.yview)
    txt.configure(yscrollcommand=sb.set)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    if placeholder:
        txt.insert("1.0", placeholder)
        txt.tag_add("ph", "1.0", "end")
        txt.tag_config("ph", foreground="#64748B")

        def _clear_ph(_e: tk.Event | None = None) -> None:
            if "ph" in txt.tag_names("1.0"):
                txt.delete("1.0", tk.END)
                txt.tag_remove("ph", "1.0", tk.END)

        def _restore_ph(_e: tk.Event | None = None) -> None:
            if not txt.get("1.0", "end-1c").strip():
                txt.delete("1.0", tk.END)
                txt.insert("1.0", placeholder)
                txt.tag_add("ph", "1.0", "end")

        txt.bind("<FocusIn>", _clear_ph)
        txt.bind("<FocusOut>", _restore_ph)
    return txt


def _text_value(widget: tk.Text) -> str:
    if "ph" in widget.tag_names("1.0"):
        return ""
    return widget.get("1.0", "end-1c")


class ToolClickApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ToolClick")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.configure(bg=BG)

        self._defaults = load_env_defaults()
        self._log_q: queue.Queue[str | tuple[str, int]] = queue.Queue()
        self._proc: subprocess.Popen[str] | None = None
        self._running = False
        self._run_log_buf = ""
        self._last_stats_path: Path | None = None
        self._run_started_at: datetime | None = None
        self._run_elapsed_label = "—"
        self._pending_run_settings: JobSettings | None = None

        self._setup_style()
        self._build()
        self.after(80, self._drain_log)
        self.after(200, self._auto_activate_license)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=FONT_UI, background=BG, foreground=TEXT)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("Nav.TFrame", background=NAVY)
        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_UI)
        style.configure("Card.TLabel", background=SURFACE, foreground=TEXT, font=FONT_UI)
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=FONT_UI_SM)
        style.configure("Head.TLabel", background=SURFACE, foreground=TEXT, font=FONT_H)
        style.configure("Nav.TLabel", background=NAVY, foreground="#F8FAFC", font=FONT_TITLE)
        style.configure("NavSub.TLabel", background=NAVY, foreground="#94A3B8", font=FONT_UI_SM)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=FONT_UI_BD,
            padding=(18, 8),
            background=FIELD,
            foreground=MUTED,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", SURFACE)],
            foreground=[("selected", TEXT)],
        )
        style.configure("TLabelframe", background=SURFACE, bordercolor=LINE, relief="flat")
        style.configure(
            "TLabelframe.Label",
            background=SURFACE,
            foreground=TEXT,
            font=FONT_H,
        )
        style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=FONT_UI)
        style.map(
            "TCheckbutton",
            background=[("active", SURFACE)],
            foreground=[("active", TEXT)],
        )
        style.configure(
            "TEntry",
            fieldbackground=FIELD,
            foreground=TEXT,
            insertcolor=TEXT,
            padding=6,
            bordercolor=LINE,
        )
        style.configure(
            "TCombobox",
            padding=4,
            fieldbackground=FIELD,
            background=FIELD,
            foreground=TEXT,
            arrowcolor=TEXT,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", FIELD)],
            foreground=[("readonly", TEXT)],
            background=[("readonly", FIELD)],
        )
        style.configure(
            "TSpinbox",
            padding=4,
            fieldbackground=FIELD,
            foreground=TEXT,
            arrowcolor=TEXT,
            insertcolor=TEXT,
        )
        style.configure("TScrollbar", background=SURFACE, troughcolor=BG)
        style.configure(
            "Treeview",
            background=FIELD,
            fieldbackground=FIELD,
            foreground=TEXT,
            bordercolor=LINE,
        )
        style.configure(
            "Treeview.Heading",
            background=NAVY_2,
            foreground=TEXT,
            font=FONT_UI_BD,
        )
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#FFFFFF")])
        style.configure("TSeparator", background=LINE)

    def _build(self) -> None:
        header = tk.Frame(self, bg=NAVY)
        header.pack(fill=tk.X)
        self._badge = tk.Label(
            header,
            text="  Sẵn sàng  ",
            bg="#064E3B",
            fg="#A7F3D0",
            font=FONT_UI_SM,
            padx=10,
            pady=4,
        )
        self._badge.pack(side=tk.RIGHT, padx=20, pady=14)
        titles = tk.Frame(header, bg=NAVY)
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20, pady=12)
        row = tk.Frame(titles, bg=NAVY)
        row.pack(anchor=tk.W, fill=tk.X)
        tk.Label(row, text="ToolClick", bg=NAVY, fg="#F8FAFC", font=FONT_TITLE).pack(
            side=tk.LEFT
        )
        tk.Label(
            row,
            text="  ·  Thu thập & kiểm thử quảng cáo Google",
            bg=NAVY,
            fg="#94A3B8",
            font=FONT_UI,
        ).pack(side=tk.LEFT)

        body = ttk.Frame(self, style="TFrame")
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(12, 8))

        nb = ttk.Notebook(body)
        nb.pack(fill=tk.BOTH, expand=True)
        tab_run = ttk.Frame(nb, style="TFrame")
        tab_set = ttk.Frame(nb, style="TFrame")
        nb.add(tab_run, text="  Công việc  ")
        nb.add(tab_set, text="  Cài đặt  ")

        self._build_run_tab(tab_run)
        self._build_settings_tab(tab_set)

        foot = tk.Frame(self, bg=BG)
        foot.pack(fill=tk.X, padx=16, pady=(0, 10))
        self._status = tk.Label(
            foot, text="Sẵn sàng.", bg=BG, fg=MUTED, font=FONT_UI_SM, anchor=tk.W
        )
        self._status.pack(side=tk.LEFT)

    def _card(self, parent: tk.Misc) -> tk.Frame:
        outer = tk.Frame(parent, bg=LINE)
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        return outer, inner

    def _section_title(self, parent: tk.Misc, title: str, hint: str) -> None:
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill=tk.X, padx=14, pady=(12, 4))
        tk.Label(row, text=title, bg=SURFACE, fg=TEXT, font=FONT_H).pack(side=tk.LEFT)
        tk.Label(row, text=hint, bg=SURFACE, fg=MUTED, font=FONT_UI_SM).pack(
            side=tk.LEFT, padx=(8, 0)
        )

    def _build_run_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        top = ttk.Frame(parent, style="TFrame")
        top.grid(row=0, column=0, sticky="nsew", pady=(8, 8))
        top.columnconfigure(0, weight=3)
        top.columnconfigure(1, weight=2)
        top.columnconfigure(2, weight=2)
        top.columnconfigure(3, weight=0)

        kw_outer, kw_inner = self._card(top)
        kw_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._section_title(kw_inner, "Từ khóa", "mỗi dòng một từ")
        self.kw_text = _plain_text(
            kw_inner, height=8, placeholder="hosting\nmua laptop văn phòng"
        )
        self.kw_text.master.master.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        dm_col = ttk.Frame(top, style="TFrame")
        dm_col.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        dm_col.rowconfigure(0, weight=1)
        dm_col.rowconfigure(1, weight=1)
        dm_col.columnconfigure(0, weight=1)

        dm_outer, dm_inner = self._card(dm_col)
        dm_outer.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        self._section_title(dm_inner, "Domain click", "trống = mọi quảng cáo")
        self.domain_text = _plain_text(dm_inner, height=4, placeholder="bluehost.com")
        self.domain_text.master.master.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
        domains = self._defaults.get("ALLOWED_CLICK_DOMAINS", "").replace(",", "\n")
        if domains.strip():
            self._set_text(self.domain_text, domains.strip())

        skip_outer, skip_inner = self._card(dm_col)
        skip_outer.grid(row=1, column=0, sticky="nsew")
        self._section_title(skip_inner, "Domain không click", "dán vào = bỏ qua, không click")
        self.skip_domain_text = _plain_text(
            skip_inner, height=4, placeholder="example.com"
        )
        self.skip_domain_text.master.master.pack(
            fill=tk.BOTH, expand=True, padx=14, pady=(0, 10)
        )
        skip_domains = self._defaults.get("SKIP_CLICK_DOMAINS", "").replace(",", "\n")
        if skip_domains.strip():
            self._set_text(self.skip_domain_text, skip_domains.strip())

        px_outer, px_inner = self._card(top)
        px_outer.grid(row=0, column=2, sticky="nsew", padx=(0, 8))
        self._section_title(px_inner, "Proxy", "trống = không dùng")
        self.proxy_text = _plain_text(
            px_inner, height=8, placeholder="http://user:pass@host:8080"
        )
        self.proxy_text.master.master.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))
        proxies = (
            (self._defaults.get("PROXY_LIST") or "")
            .replace("|", "\n")
            .replace(",", "\n")
        )
        if proxies.strip():
            self._set_text(self.proxy_text, proxies.strip())

        actions = tk.Frame(top, bg=BG, width=168)
        actions.grid(row=0, column=3, sticky="ns")
        actions.grid_propagate(False)

        self.btn_run = tk.Button(
            actions,
            text="Chạy",
            command=self._on_run,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            font=FONT_UI_BD,
            relief=tk.FLAT,
            cursor="hand2",
            pady=8,
        )
        self.btn_run.pack(fill=tk.X, pady=(0, 8))
        self.btn_stop = tk.Button(
            actions,
            text="Dừng",
            command=self._on_stop,
            bg="#3F1D1D",
            fg=DANGER,
            activebackground="#7F1D1D",
            font=FONT_UI_BD,
            relief=tk.FLAT,
            cursor="hand2",
            pady=8,
            state=tk.DISABLED,
        )
        self.btn_stop.pack(fill=tk.X, pady=(0, 8))
        self._ghost_btn(actions, "Mở trình duyệt", self._on_open_browser).pack(
            fill=tk.X, pady=(0, 8)
        )
        self._ghost_btn(actions, "Lưu .env", self._on_save_env).pack(fill=tk.X, pady=(0, 8))
        self._ghost_btn(actions, "Xóa log", self._on_clear_log).pack(fill=tk.X)

        self._count_lbl = tk.Label(
            actions, text="", bg=BG, fg=MUTED, font=FONT_UI_SM, wraplength=150, justify=tk.LEFT
        )
        self._count_lbl.pack(anchor=tk.W, pady=(16, 0))

        self._build_results_block(parent)

        log_outer, log_inner = self._card(parent)
        log_outer.grid(row=2, column=0, sticky="nsew")
        head = tk.Frame(log_inner, bg=SURFACE)
        head.pack(fill=tk.X, padx=14, pady=(10, 6))
        tk.Label(head, text="Nhật ký chạy", bg=SURFACE, fg=TEXT, font=FONT_H).pack(
            side=tk.LEFT
        )
        tk.Label(
            head,
            text="Quảng cáo mở tab mới · tab SERP giữ nguyên",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
        ).pack(side=tk.RIGHT)

        log_wrap = tk.Frame(log_inner, bg=LOG_BG)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.log = tk.Text(
            log_wrap,
            wrap=tk.WORD,
            font=FONT_MONO,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief=tk.FLAT,
            padx=12,
            pady=10,
            state=tk.DISABLED,
            highlightthickness=0,
            bd=0,
        )
        log_sb = ttk.Scrollbar(log_wrap, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=log_sb.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.tag_config("cmd", foreground="#93C5FD")
        self.log.tag_config("warn", foreground="#FBBF24")
        self.log.tag_config("err", foreground="#F87171")
        self.log.tag_config("ok", foreground="#34D399")
        self.log.tag_config("muted", foreground="#64748B")
        self._append_log("Chưa chạy job.\n", "muted")

        for w in (self.kw_text, self.domain_text, self.skip_domain_text, self.proxy_text):
            w.bind("<KeyRelease>", lambda _e: self._refresh_counts())
        self._refresh_counts()

    def _build_results_block(self, parent: ttk.Frame) -> None:
        outer, inner = self._card(parent)
        outer.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        head = tk.Frame(inner, bg=SURFACE)
        head.pack(fill=tk.X, padx=14, pady=(10, 6))
        tk.Label(head, text="Kết quả lần chạy", bg=SURFACE, fg=TEXT, font=FONT_H).pack(
            side=tk.LEFT
        )
        self._result_meta = tk.Label(
            head, text="Chưa có lần chạy", bg=SURFACE, fg=MUTED, font=FONT_UI_SM
        )
        self._result_meta.pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(
            head,
            text="Mở thư mục output",
            command=self._open_output_dir,
            bg=SURFACE,
            fg=ACCENT,
            activebackground=FIELD,
            font=FONT_UI_SM,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
        ).pack(side=tk.RIGHT)

        metrics = tk.Frame(inner, bg=SURFACE)
        metrics.pack(fill=tk.X, padx=12, pady=(0, 8))
        self._metric_vars: dict[str, tk.Label] = {}
        tiles = (
            ("ads", "Quảng cáo tìm thấy"),
            ("click_ok", "Click ads OK"),
            ("keywords", "Từ khóa"),
            ("time", "Thời gian"),
        )
        for i, (key, title) in enumerate(tiles):
            cell = tk.Frame(metrics, bg=FIELD, highlightbackground=LINE, highlightthickness=1)
            cell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0 if i == 0 else 6, 0))
            val_font = FONT_H if key == "time" else ("Segoe UI", 16, "bold")
            val = tk.Label(
                cell,
                text="—",
                bg=FIELD,
                fg=TEXT,
                font=val_font,
                wraplength=220,
                justify=tk.CENTER,
            )
            val.pack(pady=(8, 0))
            tk.Label(cell, text=title, bg=FIELD, fg=MUTED, font=FONT_UI_SM).pack(
                pady=(0, 8)
            )
            self._metric_vars[key] = val

        table_wrap = tk.Frame(inner, bg=SURFACE)
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        cols = ("kw", "ads", "ok", "rounds", "time")
        self._result_tree = ttk.Treeview(
            table_wrap,
            columns=cols,
            show="headings",
            height=4,
            selectmode="browse",
        )
        headings = {
            "kw": "Từ khóa",
            "ads": "Ads tìm thấy",
            "ok": "Click OK",
            "rounds": "Vòng SERP",
            "time": "Thời gian",
        }
        widths = {"kw": 280, "ads": 110, "ok": 90, "rounds": 90, "time": 220}
        for c in cols:
            self._result_tree.heading(c, text=headings[c], anchor=tk.W)
            self._result_tree.column(c, width=widths[c], anchor=tk.W if c == "kw" else tk.CENTER)
        sb = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self._result_tree.yview)
        self._result_tree.configure(yscrollcommand=sb.set)
        self._result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._result_files = tk.Label(
            inner,
            text="File: —",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
            anchor=tk.W,
            wraplength=900,
            justify=tk.LEFT,
        )
        self._result_files.pack(fill=tk.X, padx=14, pady=(0, 10))

    def _ghost_btn(self, parent: tk.Misc, text: str, cmd) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=SURFACE,
            fg=TEXT,
            activebackground=FIELD,
            font=FONT_UI,
            relief=tk.FLAT,
            cursor="hand2",
            pady=7,
            highlightthickness=1,
            highlightbackground=LINE,
            bd=0,
        )

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.tag_remove("ph", "1.0", tk.END)

    def _build_settings_tab(self, parent: ttk.Frame) -> None:
        d = self._defaults
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        def _inner_cfg(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _canvas_cfg(e: tk.Event) -> None:
            canvas.itemconfigure(win_id, width=e.width)

        inner.bind("<Configure>", _inner_cfg)
        canvas.bind("<Configure>", _canvas_cfg)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        def _wheel(event: tk.Event) -> str | None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        canvas.bind("<MouseWheel>", _wheel)
        inner.bind("<MouseWheel>", _wheel)

        grid = tk.Frame(inner, bg=BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        grid.columnconfigure(0, weight=1, uniform="s")
        grid.columnconfigure(1, weight=1, uniform="s")

        # --- Browser ---
        c1o, c1 = self._card(grid)
        c1o.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self._section_title(c1, "Trình duyệt", "")
        form = tk.Frame(c1, bg=SURFACE)
        form.pack(fill=tk.X, padx=14, pady=(0, 14))
        self.var_headed = tk.BooleanVar(value=not env_bool(d.get("HEADLESS"), False))
        self._check(form, "Hiện cửa sổ Chrome khi chạy job", self.var_headed)
        self.var_channel = tk.StringVar(value=d.get("BROWSER_CHANNEL", "chrome"))
        if self.var_channel.get() not in ("chrome", "msedge", "auto", "chromium"):
            self.var_channel.set("chrome")
        self._labeled_combo(
            form, "Kênh trình duyệt", self.var_channel, ["chrome", "msedge", "auto", "chromium"]
        )
        self.var_persist = tk.BooleanVar(
            value=env_bool(d.get("USE_PERSISTENT_PROFILE"), True)
        )
        self._check(form, "Dùng profile Chrome cố định (cookie/login — ads gần trình duyệt thật hơn)", self.var_persist)
        self.var_user_data = tk.StringVar(value=d.get("USER_DATA_DIR", "browser-profile"))
        self._labeled_entry(form, "Thư mục profile", self.var_user_data)

        # --- Google ---
        c2o, c2 = self._card(grid)
        c2o.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self._section_title(c2, "Google & thời gian chờ", "")
        form2 = tk.Frame(c2, bg=SURFACE)
        form2.pack(fill=tk.X, padx=14, pady=(0, 14))
        self.var_locale = tk.StringVar(
            value=locale_label_for(d.get("GOOGLE_LOCALE", "vi-VN"))
        )
        self._labeled_combo(
            form2,
            "Ngôn ngữ / khu vực",
            self.var_locale,
            locale_choice_labels(),
            readonly=False,
            height=18,
        )
        tk.Label(
            form2,
            text="Chọn nhanh quốc gia hoặc gõ mã (vd. en-US, tr-TR).",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
        ).pack(anchor=tk.W, pady=(4, 0))
        self.var_search_delay = tk.IntVar(value=env_int(d.get("SEARCH_DELAY_MS"), 2500))
        self._labeled_spin(form2, "Nghỉ sau mỗi search (ms)", self.var_search_delay, 500, 30000, 100)
        self.var_captcha = tk.IntVar(value=env_int(d.get("CAPTCHA_WAIT_SEC"), 300))
        self._labeled_spin(form2, "Chờ CAPTCHA tối đa (giây)", self.var_captcha, 30, 900, 10)

        # --- Ads ---
        c3o, c3 = self._card(grid)
        c3o.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self._section_title(c3, "Click quảng cáo", "tab mới, SERP giữ nguyên")
        form3 = tk.Frame(c3, bg=SURFACE)
        form3.pack(fill=tk.X, padx=14, pady=(0, 14))
        tk.Label(
            form3,
            text="Chỉ dùng trên môi trường được phép kiểm thử.",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
        ).pack(anchor=tk.W, pady=(0, 8))
        self.var_enable_sponsored = tk.BooleanVar(
            value=env_bool(d.get("ENABLE_SPONSORED_CLICK_TEST"), True)
        )
        self._check(form3, "Bật click quảng cáo", self.var_enable_sponsored)
        self.var_max_sponsored = tk.IntVar(value=0)
        self._labeled_spin(form3, "Tối đa mỗi SERP (0 = hết)", self.var_max_sponsored, 0, 20, 1)
        self.var_sponsored_dwell = tk.IntVar(value=env_int(d.get("SPONSORED_DWELL_MS"), 1000))
        self._labeled_spin(form3, "Ở trang đích (ms)", self.var_sponsored_dwell, 500, 60000, 100)
        self.var_click_delay = tk.IntVar(value=env_int(d.get("SPONSORED_CLICK_DELAY_MS"), 300))
        self._labeled_spin(form3, "Nghỉ giữa các click (ms)", self.var_click_delay, 0, 10000, 50)
        self.var_serp_repeat_on = tk.BooleanVar(
            value=env_int(d.get("SERP_REPEAT_COUNT"), 1) > 1
        )
        self._check(form3, "Lặp SERP (vòng 2 trở lên)", self.var_serp_repeat_on)
        self.var_serp_repeat = tk.IntVar(value=max(1, env_int(d.get("SERP_REPEAT_COUNT"), 1)))
        self._labeled_spin(form3, "Số vòng SERP", self.var_serp_repeat, 1, 10, 1)
        self.var_dwell_override = tk.BooleanVar(value=False)
        self._check(form3, "Ghi đè thời gian ở trang đích", self.var_dwell_override)

        # --- Proxy + export ---
        c4o, c4 = self._card(grid)
        c4o.grid(row=1, column=1, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self._section_title(c4, "Proxy & xuất file", "")
        form4 = tk.Frame(c4, bg=SURFACE)
        form4.pack(fill=tk.X, padx=14, pady=(0, 14))
        rot = (d.get("PROXY_ROTATE_MODE") or "keyword").strip().lower()
        if rot in ("kw", "per_keyword"):
            rot = "keyword"
        if rot not in ("keyword", "serp"):
            rot = "keyword"
        self.var_rotate = tk.StringVar(value=rot)
        self._labeled_combo(form4, "Xoay proxy", self.var_rotate, ["keyword", "serp"])
        tk.Label(
            form4,
            text="keyword = một IP / từ khóa (ít CAPTCHA).  serp = đổi IP mỗi SERP.",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 8))
        self.var_proxy_persist = tk.BooleanVar(
            value=env_bool(d.get("PROXY_PERSIST_PROFILE"), True)
        )
        self._check(form4, "Profile Chrome riêng từng proxy", self.var_proxy_persist)
        self.var_warmup_all = tk.BooleanVar(value=env_bool(d.get("PROXY_WARMUP_ALL"), False))
        self._check(form4, "Làm nóng hết proxy khi mở trình duyệt", self.var_warmup_all)

        ttk.Separator(form4).pack(fill=tk.X, pady=10)
        self.var_output = tk.StringVar(value="output")
        self._labeled_entry(form4, "Thư mục kết quả", self.var_output)
        self.var_format = tk.StringVar(value="xlsx")
        tk.Label(
            form4,
            text="Xuất: sponsored_*.xlsx và sponsored_clicks_*.csv",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
        ).pack(anchor=tk.W, pady=(8, 4))
        self.var_debug = tk.BooleanVar(value=False)
        self._check(form4, "Gỡ lỗi: chụp màn hình khi 0 kết quả", self.var_debug)

        lic_o, lic = self._card(grid)
        lic_o.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self._section_title(lic, "Bản quyền", "mở app tự kích hoạt lại key đã lưu")
        form_lic = tk.Frame(lic, bg=SURFACE)
        form_lic.pack(fill=tk.X, padx=14, pady=(0, 14))
        self.var_license_url = tk.StringVar(
            value=d.get("LICENSE_SERVER_URL", "http://127.0.0.1:8000")
        )
        self._labeled_entry(form_lic, "Máy chủ license", self.var_license_url)
        self.var_license_key = tk.StringVar(value=d.get("LICENSE_KEY", ""))
        self._labeled_entry(form_lic, "Key bản quyền", self.var_license_key)
        self.var_license_secret = tk.StringVar(value=d.get("LICENSE_API_SECRET", ""))
        self._labeled_entry(form_lic, "API secret (nếu server bật)", self.var_license_secret)
        tk.Label(
            form_lic,
            text=f"Máy này: {license_machine_id()}",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 6))
        self._license_status = tk.Label(
            form_lic,
            text="Đang kiểm tra key đã lưu…",
            bg=SURFACE,
            fg=MUTED,
            font=FONT_UI_SM,
            wraplength=520,
            justify=tk.LEFT,
        )
        self._license_status.pack(anchor=tk.W, pady=(0, 8))
        tk.Button(
            form_lic,
            text="Kích hoạt key trên máy này",
            command=self._on_activate_license,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            font=FONT_UI_BD,
            relief=tk.FLAT,
            cursor="hand2",
            pady=7,
        ).pack(anchor=tk.W)

        save_bar = tk.Frame(inner, bg=BG)
        save_bar.pack(fill=tk.X, padx=4, pady=(4, 16))
        tk.Button(
            save_bar,
            text="Lưu cài đặt (.env)",
            command=self._on_save_env,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            font=FONT_UI_BD,
            relief=tk.FLAT,
            cursor="hand2",
            pady=8,
            padx=16,
        ).pack(side=tk.LEFT)
        tk.Label(
            save_bar,
            text="Ghi toàn bộ tab Cài đặt + từ khóa / domain / proxy vào file .env",
            bg=BG,
            fg=MUTED,
            font=FONT_UI_SM,
        ).pack(side=tk.LEFT, padx=12)

    def _check(self, parent: tk.Misc, text: str, var: tk.BooleanVar) -> None:
        ttk.Checkbutton(parent, text=text, variable=var).pack(anchor=tk.W, pady=3)

    def _labeled_entry(self, parent: tk.Misc, label: str, var: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=SURFACE, fg=MUTED, font=FONT_UI_SM).pack(
            anchor=tk.W, pady=(8, 2)
        )
        ttk.Entry(parent, textvariable=var).pack(fill=tk.X)

    def _labeled_combo(
        self,
        parent: tk.Misc,
        label: str,
        var: tk.StringVar,
        values: list[str],
        *,
        readonly: bool = True,
        height: int = 8,
    ) -> None:
        tk.Label(parent, text=label, bg=SURFACE, fg=MUTED, font=FONT_UI_SM).pack(
            anchor=tk.W, pady=(8, 2)
        )
        ttk.Combobox(
            parent,
            textvariable=var,
            values=values,
            state="readonly" if readonly else "normal",
            height=height,
        ).pack(fill=tk.X)

    def _labeled_spin(
        self,
        parent: tk.Misc,
        label: str,
        var: tk.IntVar,
        lo: int,
        hi: int,
        step: int,
    ) -> None:
        tk.Label(parent, text=label, bg=SURFACE, fg=MUTED, font=FONT_UI_SM).pack(
            anchor=tk.W, pady=(8, 2)
        )
        ttk.Spinbox(parent, from_=lo, to=hi, increment=step, textvariable=var).pack(fill=tk.X)

    def _set_badge(self, text: str, kind: str = "ok") -> None:
        colors = {
            "ok": ("#064E3B", "#A7F3D0"),
            "run": ("#1E3A8A", "#BFDBFE"),
            "warn": ("#78350F", "#FDE68A"),
            "err": ("#7F1D1D", "#FECACA"),
        }
        bg, fg = colors.get(kind, colors["ok"])
        self._badge.configure(text=f"  {text}  ", bg=bg, fg=fg)

    def _refresh_counts(self) -> None:
        k = len(parse_keywords(_text_value(self.kw_text)))
        d = len(parse_domains_text(_text_value(self.domain_text)))
        s = len(parse_domains_text(_text_value(self.skip_domain_text)))
        p = len(parse_proxies_text(_text_value(self.proxy_text)))
        self._count_lbl.configure(
            text=f"{k} từ khóa\n{d} domain click\n{s} không click\n{p} proxy"
        )

    def _collect_settings(self) -> JobSettings:
        keywords = parse_keywords(_text_value(self.kw_text))
        domains = parse_domains_text(_text_value(self.domain_text))
        skip_domains = parse_domains_text(_text_value(self.skip_domain_text))
        proxies = parse_proxies_text(_text_value(self.proxy_text))
        enable = bool(self.var_enable_sponsored.get())
        serp_repeat = 1
        if enable and self.var_serp_repeat_on.get():
            serp_repeat = int(self.var_serp_repeat.get())
        dwell_override = None
        if self.var_dwell_override.get():
            dwell_override = int(self.var_sponsored_dwell.get())
        organic_dwell = env_int(self._defaults.get("ORGANIC_DWELL_MS"), 2000)
        organic_delay = env_int(self._defaults.get("ORGANIC_CLICK_DELAY_MS"), 800)
        return JobSettings(
            keywords=keywords,
            headed=bool(self.var_headed.get()),
            output_dir=self.var_output.get().strip() or "output",
            export_format=self.var_format.get() or "both",
            debug=bool(self.var_debug.get()),
            click_organic=False,
            max_organic=5,
            organic_dwell_ms=None,
            click_sponsored_test=enable,
            max_sponsored=int(self.var_max_sponsored.get()),
            sponsored_dwell_ms=dwell_override,
            google_locale=parse_locale_choice(self.var_locale.get()),
            search_delay_ms=int(self.var_search_delay.get()),
            browser_channel=self.var_channel.get() or "chrome",
            use_persistent_profile=bool(self.var_persist.get()),
            user_data_dir=self.var_user_data.get().strip() or "browser-profile",
            captcha_wait_sec=int(self.var_captcha.get()),
            organic_click_delay_ms=organic_delay,
            enable_sponsored_click_test=enable,
            sponsored_dwell_ms_env=int(self.var_sponsored_dwell.get()),
            sponsored_click_delay_ms=int(self.var_click_delay.get()),
            organic_dwell_ms_env=organic_dwell,
            serp_repeat=serp_repeat if enable else None,
            allowed_domains=domains or None,
            skip_domains=skip_domains or None,
            proxy_list=proxies or None,
            proxy_rotate_mode=self.var_rotate.get() or "keyword",
            proxy_persist_profile=bool(self.var_proxy_persist.get()),
            proxy_warmup_all=bool(self.var_warmup_all.get()),
            license_server_url=self.var_license_url.get().strip() or "http://127.0.0.1:8000",
            license_key=self.var_license_key.get().strip(),
            license_api_secret=self.var_license_secret.get().strip(),
        )

    def _append_log(self, text: str, tag: str | None = None) -> None:
        self.log.configure(state=tk.NORMAL)
        if tag is None:
            low = text.lower()
            if text.startswith("$"):
                tag = "cmd"
            elif "⚠" in text or "canh bao" in low or "warning" in low:
                tag = "warn"
            elif "lỗi" in low or "error" in low or "traceback" in low:
                tag = "err"
            elif "kết thúc" in low or "xong" in low:
                tag = "ok"
            else:
                tag = ""
        if tag:
            self.log.insert(tk.END, text, tag)
        else:
            self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _drain_log(self) -> None:
        try:
            while True:
                item = self._log_q.get_nowait()
                if isinstance(item, tuple) and item[0] == "done":
                    self._running = False
                    self._proc = None
                    self.btn_run.configure(state=tk.NORMAL, bg=ACCENT)
                    self.btn_stop.configure(state=tk.DISABLED)
                    code = item[1]
                    if code == 0:
                        self._status.configure(text=f"Hoàn tất (exit {code}).")
                        self._set_badge("Xong", "ok")
                    else:
                        self._status.configure(text=f"Kết thúc với lỗi (exit {code}).")
                        self._set_badge("Lỗi", "err")
                    out = PROJECT_ROOT / (self.var_output.get().strip() or "output")
                    if out.is_dir() and code == 0:
                        self._append_log(f"\nXem file trong: {out}\n", "ok")
                    self._update_results_from_run(code)
                else:
                    chunk = str(item)
                    self._run_log_buf += chunk
                    self._append_log(chunk)
        except queue.Empty:
            pass
        self.after(80, self._drain_log)

    def _on_clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)
        self._append_log("Chưa chạy job.\n", "muted")

    def _on_save_env(self) -> None:
        try:
            save_env_from_settings(self._collect_settings())
            self._status.configure(text=f"Đã lưu {ENV_PATH}")
            messagebox.showinfo("ToolClick", f"Đã lưu cài đặt vào\n{ENV_PATH}")
        except Exception as e:
            messagebox.showerror("ToolClick", str(e))

    def _on_open_browser(self) -> None:
        try:
            launch_browser_window(self._collect_settings())
            self._status.configure(text="Đã mở Chrome (cửa sổ riêng).")
            self._set_badge("Chrome", "run")
        except Exception as e:
            messagebox.showerror("ToolClick", str(e))

    def _on_stop(self) -> None:
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            self._status.configure(text="Đang dừng…")
            self._set_badge("Dừng", "warn")

    def _license_status_text(self, data: dict) -> str:
        extra = (
            f"Máy {data.get('machines_active')}/{data.get('max_machines')}"
            f" · còn {data.get('remaining_today')} record/ngày"
        )
        exp = data.get("expires_at")
        if exp:
            extra += f" · hạn {exp}"
        return extra

    def _apply_license_result(self, data: dict, *, popup: bool, persist: bool) -> None:
        if data.get("ok"):
            extra = self._license_status_text(data)
            self._license_status.configure(text="Key đã kích hoạt. " + extra, fg=OK)
            self._set_badge("Key OK", "ok")
            self._status.configure(text="Key bản quyền đã kích hoạt trên máy này.")
            if persist:
                try:
                    save_env_from_settings(self._collect_settings())
                except Exception:
                    pass
            if popup:
                messagebox.showinfo("ToolClick", "Đã kích hoạt key trên máy này.\n" + extra)
            return
        err = str(data.get("error") or "Kích hoạt thất bại.")
        self._license_status.configure(text=err, fg=DANGER)
        self._set_badge("Key lỗi", "err")
        self._status.configure(text=err)
        if popup:
            messagebox.showerror("ToolClick", err)

    def _activate_license_async(self, *, popup: bool, persist: bool) -> None:
        key = self.var_license_key.get().strip()
        if not key:
            self._license_status.configure(
                text="Chưa có key — nhập rồi bấm kích hoạt (sẽ tự nhớ lần sau).",
                fg=MUTED,
            )
            return

        url = self.var_license_url.get().strip()
        secret = self.var_license_secret.get().strip()

        def worker() -> None:
            data = license_activate(key, server_url=url, api_secret=secret)
            self.after(
                0,
                lambda: self._apply_license_result(data, popup=popup, persist=persist),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _auto_activate_license(self) -> None:
        if not self.var_license_key.get().strip():
            self._license_status.configure(
                text="Chưa có key — nhập rồi bấm kích hoạt (sẽ tự nhớ lần sau).",
                fg=MUTED,
            )
            return
        self._license_status.configure(text="Đang kích hoạt lại key đã lưu…", fg=MUTED)
        self._status.configure(text="Đang kích hoạt lại key bản quyền…")
        self._activate_license_async(popup=False, persist=False)

    def _on_activate_license(self) -> None:
        self._activate_license_async(popup=True, persist=True)

    def _report_run_stats(
        self,
        settings: JobSettings,
        *,
        ads_found: int = 0,
        clicks_ok: int = 0,
    ) -> None:
        def worker() -> None:
            try:
                license_report_run(
                    settings.license_key,
                    keywords=settings.keywords,
                    click_domains=settings.allowed_domains or [],
                    skip_domains=settings.skip_domains or [],
                    serp_rounds=int(settings.serp_repeat or 1),
                    ads_found=ads_found,
                    clicks_ok=clicks_ok,
                    server_url=settings.license_server_url,
                    api_secret=settings.license_api_secret,
                )
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_run(self) -> None:
        if self._running:
            return
        settings = self._collect_settings()
        if not settings.keywords:
            messagebox.showwarning("ToolClick", "Nhập ít nhất một từ khóa.")
            return
        ok, lic_msg, _ = verify_for_run(
            settings.license_key,
            records_delta=max(1, len(settings.keywords)),
            server_url=settings.license_server_url,
            api_secret=settings.license_api_secret,
        )
        if not ok:
            messagebox.showerror("Bản quyền", lic_msg)
            self._license_status.configure(text=lic_msg, fg=DANGER)
            self._set_badge("Key lỗi", "err")
            return
        self._append_log(lic_msg + "\n", "ok")
        self._pending_run_settings = settings
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)
        self._run_log_buf = ""
        self._run_started_at = datetime.now()
        self._run_elapsed_label = "—"
        self._reset_results("Đang chạy…")
        self._running = True
        self.btn_run.configure(state=tk.DISABLED, bg="#93C5FD")
        self.btn_stop.configure(state=tk.NORMAL)
        self._status.configure(text="Đang chạy… Giải CAPTCHA trên Chrome nếu Google yêu cầu.")
        self._set_badge("Đang chạy", "run")

        def worker() -> None:
            argv = settings.build_argv()
            self._log_q.put("$ " + " ".join(argv) + "\n\n")
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                proc = subprocess.Popen(
                    argv,
                    cwd=str(PROJECT_ROOT),
                    env=settings.to_env(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                )
            except Exception as e:
                self._log_q.put(f"Lỗi khởi chạy: {e}\n")
                self._log_q.put(("done", 1))
                return
            self._proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                self._log_q.put(line)
            code = proc.wait()
            self._log_q.put(f"\n--- Kết thúc (exit code {code}) ---\n")
            self._log_q.put(("done", code))

        threading.Thread(target=worker, daemon=True).start()

    def _reset_results(self, meta: str) -> None:
        self._result_meta.configure(text=meta)
        for lbl in self._metric_vars.values():
            lbl.configure(text="—")
        for item in self._result_tree.get_children():
            self._result_tree.delete(item)
        self._result_files.configure(text="File: —")
        self._last_stats_path = None
        if meta == "Đang chạy…":
            self._run_elapsed_label = "—"

    def _extract_summary_json(self, text: str) -> dict | None:
        key = '"total_sponsored_found"'
        idx = text.rfind(key)
        if idx < 0:
            return None
        start = text.rfind("{", 0, idx)
        if start < 0:
            return None
        try:
            obj, _end = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            return None
        return obj if isinstance(obj, dict) else None

    def _stamp_from_log(self) -> str:
        for line in self._run_log_buf.splitlines():
            if "sponsored_" in line and line.endswith(".xlsx"):
                name = Path(line.split()[-1]).stem
                return name.replace("sponsored_", "", 1)
        return ""

    def _update_results_from_run(self, exit_code: int) -> None:
        outdir = PROJECT_ROOT / (self.var_output.get().strip() or "output")
        summary = self._extract_summary_json(self._run_log_buf)
        stamp = self._stamp_from_log()
        self._run_elapsed_label = self._format_run_time()
        self._metric_vars["time"].configure(text=self._run_elapsed_label)
        if not summary:
            if exit_code != 0:
                self._result_meta.configure(text="Lần chạy không có thống kê (lỗi hoặc bị dừng).")
            else:
                self._result_meta.configure(text="Không đọc được JSON thống kê.")
            self._flush_run_stats(0, 0)
            return

        ads = int(summary.get("total_sponsored_found") or 0)
        click_ok = int(summary.get("sponsored_clicks_ok") or 0)
        by_kw = summary.get("by_keyword") or {}
        self._metric_vars["ads"].configure(text=str(ads))
        self._metric_vars["click_ok"].configure(text=str(click_ok))
        self._metric_vars["keywords"].configure(text=str(len(by_kw) if isinstance(by_kw, dict) else 0))
        self._metric_vars["time"].configure(text=self._run_elapsed_label)

        if stamp:
            self._result_meta.configure(text=f"Lần chạy {stamp}")
        else:
            self._result_meta.configure(text="Lần chạy vừa xong")

        for item in self._result_tree.get_children():
            self._result_tree.delete(item)
        if isinstance(by_kw, dict):
            for kw, row in by_kw.items():
                rounds = row.get("serp_rounds") or []
                n_rounds = len(rounds) if isinstance(rounds, list) else 0
                self._result_tree.insert(
                    "",
                    tk.END,
                    values=(
                        kw,
                        row.get("sponsored_found", 0),
                        row.get("sponsored_clicks_ok", 0),
                        n_rounds or "—",
                        self._run_elapsed_label,
                    ),
                )

        names: list[str] = []
        if outdir.is_dir() and stamp:
            for p in sorted(outdir.glob(f"*{stamp}*")):
                if p.suffix.lower() in (".xlsx", ".csv") and p.name.startswith(
                    ("sponsored_", "sponsored_clicks_")
                ):
                    names.append(p.name)
        self._result_files.configure(
            text="File: " + (", ".join(names) if names else "—")
        )
        self._flush_run_stats(ads, click_ok)

    def _flush_run_stats(self, ads_found: int, clicks_ok: int) -> None:
        settings = self._pending_run_settings
        self._pending_run_settings = None
        if settings is None:
            return
        self._report_run_stats(settings, ads_found=ads_found, clicks_ok=clicks_ok)

    def _format_run_time(self) -> str:
        ended = datetime.now()
        clock = ended.strftime("%H:%M:%S")
        started = self._run_started_at
        if started is None:
            return clock
        sec = int(max(0, (ended - started).total_seconds()))
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        if h:
            dur = f"{h} giờ {m} phút {s} giây"
        elif m:
            dur = f"{m} phút {s} giây"
        else:
            dur = f"{s} giây"
        return f"{clock} ({dur})"

    def _open_output_dir(self) -> None:
        outdir = PROJECT_ROOT / (self.var_output.get().strip() or "output")
        outdir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(outdir))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(outdir)])
            else:
                subprocess.Popen(["xdg-open", str(outdir)])
        except Exception as e:
            messagebox.showerror("ToolClick", str(e))


def main() -> None:
    _enable_dpi()
    os.chdir(PROJECT_ROOT)
    app = ToolClickApp()
    app.mainloop()


if __name__ == "__main__":
    main()
