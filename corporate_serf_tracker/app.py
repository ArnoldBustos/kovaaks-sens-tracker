import threading
import os
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .analysis import calc_median, estimate_best_cm, estimate_worst_cm, recommend_next_cm
from .constants import ACCENT, ACCENT2, BG, BG2, BG3, BORDER, CM_OPTIONS, DEFAULT_STATS_PATH, GOLD, MAX_SELECTED, MUTED, TEXT, TEXT2, WARN, WORST_BG, WORST_COL
from .formatting import fmt_score, fmt_ts, get_effective_cm
from .parsing import load_folder
from .storage import load_data, save_data

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kovaaks Sensitivity Performance Tracker")
        self.geometry("1400x820")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.storage = load_data()
        self.all_scenarios: dict = {}
        self.selected: list[str] = []
        self.folder_path: str = ""
        self.show_all_cm = tk.BooleanVar(value=False)
        self._table_collapsed = {}
        self._plays_collapsed = {}
        self._chart_collapsed = {}
        self.last_8_only = tk.BooleanVar(value=False)
        self._active_tab_name: str = ""
        self.chart_scale = tk.DoubleVar(value=1.0)
        self.chart_height = tk.DoubleVar(value=1.0)
        self._scenario_tooltip = None
        self._scenario_tooltip_after_id = None
        self._hovered_scenario_index = None

        # ── NEW: cm range filter (global, affects display + next-cm rec) ───
        self.cm_range_min = tk.StringVar(value="")
        self.cm_range_max = tk.StringVar(value="")

        # ── NEW: per-scenario hidden cms {scenario_name: set of float} ─────
        self._hidden_cms: dict[str, set] = defaultdict(set)

        self._build_styles()
        self._build_ui()

        # ── NEW: auto-load default KovaaK's stats path on startup ──────────
        if os.path.exists(DEFAULT_STATS_PATH):
            self.folder_path = DEFAULT_STATS_PATH
            self.after(150, self._load_folder)

    # ── Styles ────────────────────────────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 9))

        style.configure("Treeview",
            background=BG2, foreground=TEXT, fieldbackground=BG2,
            borderwidth=0, rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
            background=BG3, foreground=TEXT2, relief="flat",
            font=("Segoe UI", 8, "bold"))
        style.map("Treeview",
            background=[("selected", "#1f3044")],
            foreground=[("selected", ACCENT)])
        style.map("Treeview.Heading", background=[("active", BG3)])

        style.configure("Vertical.TScrollbar",
            background=BG3, troughcolor=BG, arrowcolor=TEXT2,
            borderwidth=0, relief="flat")
        style.configure("Horizontal.TScrollbar",
            background=BG3, troughcolor=BG, arrowcolor=TEXT2,
            borderwidth=0, relief="flat")

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        style.configure("TNotebook.Tab",
            background=BG2, foreground=TEXT2,
            padding=[12, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
            background=[("selected", BG3)],
            foreground=[("selected", ACCENT)])

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=BG2)

        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=TEXT2, font=("Segoe UI", 8))
        style.configure("Accent.TLabel", background=BG2, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        style.configure("Gold.TLabel", background=BG2, foreground=GOLD, font=("Consolas", 12, "bold"))
        style.configure("Green.TLabel", background=BG2, foreground=ACCENT2, font=("Consolas", 11, "bold"))
        style.configure("StatLabel.TLabel", background=BG2, foreground=TEXT2, font=("Segoe UI", 8))
        style.configure("Heading.TLabel", background=BG, foreground=TEXT2, font=("Segoe UI", 8, "bold"))

        style.configure("TButton",
            background=BG3, foreground=TEXT, relief="flat",
            font=("Segoe UI", 9), padding=[8, 4])
        style.map("TButton",
            background=[("active", BORDER)], foreground=[("active", ACCENT)])
        style.configure("Accent.TButton",
            background="#1a3a5c", foreground=ACCENT, relief="flat",
            font=("Segoe UI", 9, "bold"), padding=[10, 5])
        style.map("Accent.TButton",
            background=[("active", "#1f4878")])

        style.configure("TEntry",
            fieldbackground=BG3, foreground=TEXT, insertcolor=TEXT,
            borderwidth=1, relief="solid") 
        style.map("TEntry", fieldbackground=[("focus", BG3)])

        style.configure("TCombobox",
            fieldbackground=BG3, foreground=TEXT, background=BG3,
            arrowcolor=TEXT2, borderwidth=1)
        style.map("TCombobox", fieldbackground=[("readonly", BG3)])

        style.configure("TSeparator", background=BORDER)

        style.configure("TLabelframe", background=BG2, foreground=TEXT2, bordercolor=BORDER)
        style.configure("TLabelframe.Label", background=BG2, foreground=TEXT2, font=("Segoe UI", 8))

        style.configure("Score.Horizontal.TProgressbar",
            troughcolor=BG3, background=ACCENT2, borderwidth=0, thickness=4)
        style.configure("Best.Horizontal.TProgressbar",
            troughcolor=BG3, background=GOLD, borderwidth=0, thickness=4)

    # ── UI Layout ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        topbar = tk.Frame(self, bg="#0a0a0a", height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Kovaaks Sensitivity Performance Tracker",
            font=("Consolas", 14, "bold"), bg=BG2, fg=ACCENT).pack(side="left", padx=18, pady=12)
        tk.Label(topbar, text="Inspired by the Corporate Serf method!",
            font=("Segoe UI", 9), bg=BG2, fg=TEXT2).pack(side="left", pady=12)

        self.folder_label = tk.Label(topbar, text="Auto-loading default path...",
            font=("Consolas", 8), bg=BG2, fg=TEXT2, wraplength=350)
        self.folder_label.pack(side="right", padx=12)

        ttk.Button(topbar, text="↺ Refresh", style="TButton",
            command=self._refresh).pack(side="right", pady=10)
        ttk.Button(topbar, text="📂 Select Stats Folder", style="Accent.TButton",
            command=self._select_folder).pack(side="right", padx=6, pady=10)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self.main_pane = tk.PanedWindow(
            body,
            orient="horizontal",
            bg=BG,
            sashwidth=6,
            sashrelief="flat",
            bd=0,
            opaqueresize=False
        )
        self.main_pane.pack(fill="both", expand=True)

        sidebar = tk.Frame(self.main_pane, bg=BG2, width=320)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        self.main_frame = tk.Frame(self.main_pane, bg=BG)
        self.main_frame.pack_propagate(False)

        self.main_pane.add(sidebar, minsize=220)
        self.main_pane.add(self.main_frame, minsize=500)

        self.after(50, lambda: self.main_pane.sash_place(0, 320, 0))

        self._show_empty()

    def _build_sidebar(self, parent):
        hdr = tk.Frame(parent, bg=BG2)
        hdr.pack(fill="x", padx=10, pady=(10,4))

        tk.Label(hdr, text="SCENARIOS", font=("Segoe UI", 8, "bold"),
            bg=BG2, fg=TEXT2).pack(anchor="w")

        sf = tk.Frame(hdr, bg=BG2)
        sf.pack(fill="x", pady=4)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_scenarios())
        self.search_entry = tk.Entry(sf, textvariable=self.search_var,
            bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat",
            font=("Segoe UI", 9), bd=1)
        self.search_entry.pack(fill="x", ipady=4)
        self.search_entry.insert(0, "Search scenarios...")
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)

        self.sel_label = tk.Label(hdr, text="0 / 5 selected",
            font=("Consolas", 8), bg=BG2, fg=ACCENT2)
        self.sel_label.pack(anchor="e")

        self.count_label = tk.Label(hdr, text="0 scenarios",
            font=("Segoe UI", 8), bg=BG2, fg=TEXT2)
        self.count_label.pack(anchor="w")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        lf = tk.Frame(parent, bg=BG2)
        lf.pack(fill="both", expand=True)

        self.scenario_lb = tk.Listbox(lf,
            bg=BG2, fg=TEXT, selectbackground="#1f3044", selectforeground=ACCENT2,
            relief="flat", bd=0, activestyle="none",
            font=("Segoe UI", 9), highlightthickness=0, exportselection=False)
        self.scenario_lb.pack(fill="both", expand=True, side="left")
        self.scenario_lb.bind("<ButtonRelease-1>", self._on_scenario_click)
        self.scenario_lb.bind("<Motion>", self._on_scenario_hover)
        self.scenario_lb.bind("<Leave>", self._hide_scenario_tooltip)

        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.scenario_lb.yview)
        vsb.pack(side="right", fill="y")
        self.scenario_lb.configure(yscrollcommand=vsb.set)

        self._scenario_names: list[str] = []

    def _on_scenario_hover(self, event):
        idx = self.scenario_lb.nearest(event.y)
        if idx < 0 or idx >= len(self._scenario_names):
            self._cancel_scenario_tooltip()
            self._hide_scenario_tooltip()
            return

        bbox = self.scenario_lb.bbox(idx)
        if not bbox:
            self._cancel_scenario_tooltip()
            self._hide_scenario_tooltip()
            return

        row_y, row_height = bbox[1], bbox[3]
        if event.y < row_y or event.y > row_y + row_height:
            self._cancel_scenario_tooltip()
            self._hide_scenario_tooltip()
            return

        if self._hovered_scenario_index == idx and self._scenario_tooltip is not None:
            pointer_x = self.scenario_lb.winfo_rootx() + event.x + 18
            pointer_y = self.scenario_lb.winfo_rooty() + event.y + 12
            self._scenario_tooltip.geometry(f"+{pointer_x}+{pointer_y}")
            return

        self._hovered_scenario_index = idx
        self._cancel_scenario_tooltip()

        pointer_x = self.scenario_lb.winfo_rootx() + event.x + 18
        pointer_y = self.scenario_lb.winfo_rooty() + event.y + 12

        self._scenario_tooltip_after_id = self.after(
            250,
            lambda: self._show_scenario_tooltip(idx, pointer_x, pointer_y)
        )
    
    def _show_scenario_tooltip(self, idx, pointer_x, pointer_y):
        if idx < 0 or idx >= len(self._scenario_names):
            return

        scenario_name = self._scenario_names[idx]
        plays = len(self.all_scenarios.get(scenario_name, []))
        tooltip_text = f"{scenario_name} ({plays})"

        if self._scenario_tooltip is None:
            self._scenario_tooltip = tk.Toplevel(self)
            self._scenario_tooltip.overrideredirect(True)
            self._scenario_tooltip.attributes("-topmost", True)

            self._scenario_tooltip_label = tk.Label(
                self._scenario_tooltip,
                text=tooltip_text,
                font=("Segoe UI", 8),
                bg=BG3,
                fg=TEXT,
                relief="solid",
                bd=1,
                padx=8,
                pady=4,
                justify="left"
            )
            self._scenario_tooltip_label.pack()
        else:
            self._scenario_tooltip_label.config(text=tooltip_text)

        self._scenario_tooltip.geometry(f"+{pointer_x}+{pointer_y}")

    def _cancel_scenario_tooltip(self):
        if self._scenario_tooltip_after_id is not None:
            self.after_cancel(self._scenario_tooltip_after_id)
            self._scenario_tooltip_after_id = None

    def _hide_scenario_tooltip(self, event=None):
        self._cancel_scenario_tooltip()
        self._hovered_scenario_index = None
        if self._scenario_tooltip is not None:
            self._scenario_tooltip.destroy()
            self._scenario_tooltip = None

    def _search_focus_in(self, e):
        if self.search_entry.get() == "Search scenarios...":
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=TEXT)

    def _search_focus_out(self, e):
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search scenarios...")
            self.search_entry.config(fg=MUTED)

    # ── Folder ops ────────────────────────────────────────────────────────────
    def _select_folder(self):
        init = DEFAULT_STATS_PATH if os.path.exists(DEFAULT_STATS_PATH) else "/"
        folder = filedialog.askdirectory(title="Select KovaaK's Stats Folder",
            initialdir=init)
        if folder:
            self.folder_path = folder
            self._load_folder()

    def _refresh(self):
        if self.folder_path:
            self._load_folder(preserve_state=True)
        else:
            self._select_folder()

    def _load_folder(self, preserve_state=False):
        self.folder_label.config(text="Loading...", fg=TEXT2)
        self.update_idletasks()
        prev_selected = list(self.selected)
        prev_tab = self._active_tab_name
        self.all_scenarios = load_folder(self.folder_path)
        count = len(self.all_scenarios)
        short = Path(self.folder_path).name
        self.folder_label.config(
            text=f"✓ {short}  ({count} scenarios)", fg=ACCENT2)
        if preserve_state:
            self.selected = [n for n in prev_selected if n in self.all_scenarios]
            self.sel_label.config(text=f"{len(self.selected)} / 5 selected")
        cur_q = self.search_var.get()
        if cur_q == "Search scenarios...":
            cur_q = ""
        self._populate_scenario_list(cur_q)
        self._refresh_main(restore_tab=prev_tab if preserve_state else "")
        self._show_toast(f"Loaded {count} scenarios")

    def _populate_scenario_list(self, query=""):
        self.scenario_lb.delete(0, "end")
        names = sorted(self.all_scenarios.keys())
        if query and query != "Search scenarios...":
            names = [n for n in names if query.lower() in n.lower()]
        self._scenario_names = names
        self.count_label.config(text=f"{len(names)} scenarios")
        for name in names:
            plays = len(self.all_scenarios[name])
            self.scenario_lb.insert("end", f"  {name}  ({plays})")
            if name in self.selected:
                idx = self._scenario_names.index(name)
                self.scenario_lb.itemconfig(idx, fg=ACCENT2)

    def _filter_scenarios(self):
        if not hasattr(self, "scenario_lb"):
            return
        q = self.search_var.get()
        if q == "Search scenarios...":
            q = ""
        self._populate_scenario_list(q)

    def _on_scenario_click(self, event):
        sel = self.scenario_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._scenario_names):
            return
        name = self._scenario_names[idx]
        if name in self.selected:
            self.selected.remove(name)
            self.scenario_lb.itemconfig(idx, fg=TEXT)
        else:
            if len(self.selected) >= MAX_SELECTED:
                self._show_toast("Max 5 scenarios. Remove one first.")
                return
            self.selected.append(name)
            self.scenario_lb.itemconfig(idx, fg=ACCENT2)
        self.sel_label.config(text=f"{len(self.selected)} / 5 selected")
        self._refresh_main()

    # ── Main area ─────────────────────────────────────────────────────────────
    def _show_empty(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        f = tk.Frame(self.main_frame, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")
        tk.Label(f, text="◈", font=("Segoe UI", 48), bg=BG, fg=MUTED).pack()
        tk.Label(f, text="NO SCENARIOS SELECTED", font=("Consolas", 14, "bold"),
            bg=BG, fg=TEXT2).pack(pady=8)
        tk.Label(f, text="Load your stats folder and select up to 5 scenarios\nfrom the sidebar to begin charting your Kovaaks Sensitivity stats.",
            font=("Segoe UI", 9), bg=BG, fg=MUTED, justify="center").pack()

    def _refresh_main(self, restore_tab=""):
        for w in self.main_frame.winfo_children():
            w.destroy()
        if not self.selected:
            self._show_empty()
            return
        nb = ttk.Notebook(self.main_frame)
        nb.pack(fill="both", expand=True, padx=0, pady=0)
        for name in self.selected:
            frame = ttk.Frame(nb)
            nb.add(frame, text=f"  {name[:28]}{chr(8230) if len(name)>28 else ''}  ")
            self._build_scenario_tab(frame, name)
        def _on_tab_change(e):
            try:
                idx = nb.index(nb.select())
                self._active_tab_name = self.selected[idx]
            except Exception:
                pass
        nb.bind("<<NotebookTabChanged>>", _on_tab_change)
        target = restore_tab or self._active_tab_name
        if target and target in self.selected:
            nb.select(self.selected.index(target))
            self._active_tab_name = target
        elif self.selected:
            self._active_tab_name = self.selected[0]

    def _build_scenario_tab(self, parent, name):
        plays = self.all_scenarios.get(name, [])
        assignments = self.storage["assignments"].get(name, {})
        ranks = self.storage["ranks"].get(name, {})

        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_frame_resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_frame_resize)

        def _on_mousewheel(e):
            canvas.yview_scroll(-1 * (e.delta // 120), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_stats_bar(inner, name, plays, assignments)
        self._build_chart_section(inner, name, plays, assignments)
        self._build_sens_table(inner, name, plays, assignments, ranks)
        self._build_tag_section(inner, name, plays, assignments)
    
    def _build_tag_section(self, parent, name, plays, assignments):
        outer = tk.Frame(parent, bg=BG2, bd=1, relief="solid")
        outer.pack(fill="x", padx=16, pady=6)

        is_collapsed = self._plays_collapsed.get(name, True)

        hdr_bar = tk.Frame(outer, bg=BG3, cursor="hand2")
        hdr_bar.pack(fill="x")
        arrow = "▶" if is_collapsed else "▼"
        hdr_lbl = tk.Label(hdr_bar, text=f"  {arrow}  TAG PLAY SENSITIVITIES",
            font=("Consolas", 9, "bold"), bg=BG3, fg=TEXT2, anchor="w", pady=6)
        hdr_lbl.pack(side="left", padx=4)
        hdr_hint = tk.Label(hdr_bar, text="click to collapse",
            font=("Segoe UI", 7), bg=BG3, fg=MUTED, anchor="e")
        hdr_hint.pack(side="right", padx=8)

        frame = tk.Frame(outer, bg=BG2)
        if not is_collapsed:
            frame.pack(fill="x")

        def _toggle_plays(e=None):
            self._plays_collapsed[name] = not self._plays_collapsed.get(name, False)
            if self._plays_collapsed[name]:
                frame.pack_forget()
                hdr_lbl.config(text="  ▶  TAG PLAY SENSITIVITIES")
            else:
                frame.pack(fill="x")
                hdr_lbl.config(text="  ▼  TAG PLAY SENSITIVITIES")

        hdr_bar.bind("<Button-1>", _toggle_plays)
        hdr_lbl.bind("<Button-1>", _toggle_plays)
        hdr_hint.bind("<Button-1>", _toggle_plays)

        info = tk.Frame(frame, bg=BG2)
        info.pack(fill="x", padx=10, pady=6)
        auto_count = sum(1 for p in plays if p.get("cm360") is not None)
        manual_count = sum(1 for p in plays if p["filename"] in assignments)
        unresolved = sum(1 for p in plays if get_effective_cm(p, assignments) is None)
        tk.Label(info, text=f"✓ {auto_count} auto-detected  +  {manual_count} manual override  |  {unresolved} unresolved",
            font=("Consolas", 8), bg=BG2, fg=ACCENT2).pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────
    def _get_active_range(self):
        """
        Parse cm_range_min / cm_range_max StringVars.
        Returns (lo: float|None, hi: float|None).
        None means no bound.
        """
        lo, hi = None, None
        try:
            v = self.cm_range_min.get().strip()
            if v:
                lo = float(v)
        except ValueError:
            pass
        try:
            v = self.cm_range_max.get().strip()
            if v:
                hi = float(v)
        except ValueError:
            pass
        return lo, hi

    def _cm_in_range(self, cm: float) -> bool:
        lo, hi = self._get_active_range()
        if lo is not None and cm < lo:
            return False
        if hi is not None and cm > hi:
            return False
        return True

    # ─────────────────────────────────────────────────────────────────────────
    def _build_stats_bar(self, parent, name, plays, assignments):
        bar = tk.Frame(parent, bg=BG2, pady=10)
        bar.pack(fill="x", padx=16, pady=(12, 0))
        tk.Frame(bar, bg=ACCENT, height=2).pack(fill="x")

        title_row = tk.Frame(bar, bg=BG2)
        title_row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(title_row, text=name, font=("Consolas", 10, "bold"),
            bg=BG2, fg=ACCENT, anchor="w").pack(side="left")
        close_btn = tk.Button(title_row, text="✕  close",
            font=("Segoe UI", 8), bg=BG3, fg=WARN,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            activebackground=BG3, activeforeground="#ff4444",
            command=lambda n=name: self._remove_scenario(n))
        close_btn.pack(side="right")

        inner = tk.Frame(bar, bg=BG2)
        inner.pack(fill="x", padx=14, pady=8)

        # respects range filter + hidden cms
        hidden = self._hidden_cms.get(name, set())

        def _play_visible(p):
            cm = get_effective_cm(p, assignments)
            if cm is None:
                return False
            return self._cm_in_range(cm) and cm not in hidden

        filtered_plays = [p for p in plays if _play_visible(p)]
        all_scores = [p["score"] for p in filtered_plays if p["score"] > 0]
        best = max(all_scores) if all_scores else None
        best_play = next((p for p in filtered_plays if p["score"] == best), None) if best else None
        cm_of_best = get_effective_cm(best_play, assignments) if best_play else None
        best_crosshair_name = best_play.get("crosshair_name") if best_play else None
        best_crosshair_scale = best_play.get("crosshair_scale") if best_play else None
        median = calc_median(all_scores)

        # Build cm→best map respecting range filter + hidden cms
        byCm_all = defaultdict(list)
        for p in plays:
            cm = get_effective_cm(p, assignments)
            if cm is not None:
                byCm_all[cm].append(p["score"])

        def _is_visible_cm(cm):
            return self._cm_in_range(cm) and cm not in hidden

        cm_bests_filtered = {
            cm: max(scores)
            for cm, scores in byCm_all.items()
            if _is_visible_cm(cm)
        }

        est_cm, est_method = estimate_best_cm(cm_bests_filtered)
        worst_cm, worst_method = estimate_worst_cm(cm_bests_filtered)

        # Worst cm best score
        worst_score = None
        if worst_cm is not None:
            # Find the actual cm key closest to worst_cm
            closest = min(cm_bests_filtered.keys(), key=lambda c: abs(c - worst_cm), default=None)
            if closest is not None:
                worst_score = cm_bests_filtered[closest]

        best_crosshair_label = "—"
        if best_crosshair_name:
          if best_crosshair_scale is not None:
            best_crosshair_label = f"{best_crosshair_name}  ({best_crosshair_scale})"
          else:
            best_crosshair_label = best_crosshair_name

        stats = [
          ("OVERALL BEST", fmt_score(best), GOLD),
          ("CM FOR BEST", f"{cm_of_best} cm" if cm_of_best else "—", ACCENT),
          ("BEST CROSSHAIR", best_crosshair_label, ACCENT),
          ("MEDIAN", fmt_score(median), TEXT),
          ("TOTAL PLAYS", str(len(plays)), TEXT),
          ("EST. BEST CM", "Need more data", ACCENT2),
        ]
        if est_cm is not None:
            stats[5] = ("EST. BEST CM", f"~{est_cm} cm  ({est_method})", ACCENT2)

        for label, val, col in stats:
            cell = tk.Frame(inner, bg=BG3, padx=12, pady=8)
            cell.pack(side="left", padx=4, fill="y")
            tk.Label(cell, text=label, font=("Segoe UI", 7, "bold"),
                bg=BG3, fg=TEXT2).pack(anchor="w")
            tk.Label(cell, text=val, font=("Consolas", 12, "bold"),
                bg=BG3, fg=col).pack(anchor="w", pady=(2, 0))

        # ── EXPERIMENTAL: worst cm stat ─────────────────────────────────────
        worst_cell = tk.Frame(
            inner,
            bg=WORST_BG,
            padx=12,
            pady=8,
            highlightbackground=WORST_COL,
            highlightthickness=1
        )
        worst_cell.pack(side="left", padx=4, fill="y")

        tk.Label(
            worst_cell,
            text="⚗ WORST CM",
            font=("Segoe UI", 7, "bold"),
            bg=WORST_BG,
            fg=WORST_COL
        ).pack(anchor="w")

        if worst_cm is not None:
            worst_method_label = worst_method if worst_method else "estimate"
            worst_val = f"~{worst_cm:.4g} cm\n({worst_method_label})"
        else:
            worst_val = "Need more\ndata"

        worst_score_str = f"best: {fmt_score(worst_score)}" if worst_score is not None else ""

        tk.Label(
            worst_cell,
            text=worst_val,
            font=("Consolas", 10, "bold"),
            bg=WORST_BG,
            fg=WORST_COL,
            justify="left",
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        if worst_score_str:
            tk.Label(
                worst_cell,
                text=worst_score_str,
                font=("Consolas", 8),
                bg=WORST_BG,
                fg=TEXT2,
                justify="left",
                anchor="w"
            ).pack(anchor="w", pady=(2, 0))

        # ── EXPERIMENTAL: next cm recommendation ───────────────────────────
        rec_cm, rec_reason = recommend_next_cm(cm_bests_filtered, est_cm, list(cm_bests_filtered.keys()))

        # Show range-filter note if active
        lo, hi = self._get_active_range()
        range_note = ""
        if lo is not None or hi is not None:
            lo_s = f"{lo:.4g}" if lo is not None else "—"
            hi_s = f"{hi:.4g}" if hi is not None else "—"
            range_note = f"  [range filter: {lo_s}–{hi_s} cm active]"

        hidden_note = ""
        if hidden:
            hidden_note = f"  [{len(hidden)} cm(s) hidden]"

        rec_bar = tk.Frame(bar, bg="#0f1f0f", padx=14, pady=6)
        rec_bar.pack(fill="x")
        rec_left = tk.Frame(rec_bar, bg="#0f1f0f")
        rec_left.pack(side="left")
        tk.Label(rec_left, text="⚗ EXPERIMENTAL — NEXT CM TO TEST",
            font=("Segoe UI", 7, "bold"), bg="#0f1f0f", fg="#4a8c4a").pack(anchor="w")
        tk.Label(rec_left,
            text=f"→  {rec_cm:.4g} cm/360   ({rec_reason}){range_note}{hidden_note}",
            font=("Consolas", 11, "bold"), bg="#0f1f0f", fg=ACCENT2).pack(anchor="w", pady=(2,0))
        tk.Label(rec_bar,
            text="fills the biggest gap in your data to sharpen the curve fit",
            font=("Segoe UI", 7), bg="#0f1f0f", fg="#4a8c4a").pack(side="right", padx=8)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_sens_table(self, parent, name, plays, assignments, ranks):
        outer = tk.Frame(parent, bg=BG2, bd=1, relief="solid")
        outer.pack(fill="x", padx=16, pady=10)

        is_collapsed = self._table_collapsed.get(name, False)

        hdr_bar = tk.Frame(outer, bg=BG3, cursor="hand2")
        hdr_bar.pack(fill="x")
        arrow = "▶" if is_collapsed else "▼"
        hdr_lbl = tk.Label(hdr_bar, text=f"  {arrow}  SENSITIVITY CHART",
            font=("Consolas", 9, "bold"), bg=BG3, fg=ACCENT, anchor="w", pady=6)
        hdr_lbl.pack(side="left", padx=4)
        hdr_hint = tk.Label(hdr_bar, text="click to collapse",
            font=("Segoe UI", 7), bg=BG3, fg=MUTED, anchor="e")
        hdr_hint.pack(side="right", padx=8)

        frame = tk.Frame(outer, bg=BG2)
        if not is_collapsed:
            frame.pack(fill="x")

        def _toggle_table(e=None):
            self._table_collapsed[name] = not self._table_collapsed.get(name, False)
            if self._table_collapsed[name]:
                frame.pack_forget()
                hdr_lbl.config(text="  ▶  SENSITIVITY CHART")
            else:
                frame.pack(fill="x")
                hdr_lbl.config(text="  ▼  SENSITIVITY CHART")

        hdr_bar.bind("<Button-1>", _toggle_table)
        hdr_lbl.bind("<Button-1>", _toggle_table)
        hdr_hint.bind("<Button-1>", _toggle_table)

        # ── Toggle bar ──────────────────────────────────────────────────────
        tog_row = tk.Frame(frame, bg=BG2)
        tog_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(tog_row, text="Show non-standard cm/360 rows:",
            font=("Segoe UI", 8), bg=BG2, fg=TEXT2).pack(side="left")

        def _toggle_refresh():
            self._refresh_main()

        tog_btn = tk.Checkbutton(tog_row, text="ON",
            variable=self.show_all_cm, command=_toggle_refresh,
            bg=BG2, fg=ACCENT2, selectcolor=BG3, activebackground=BG2,
            activeforeground=ACCENT2, font=("Consolas", 8, "bold"),
            relief="flat", bd=0, cursor="hand2")
        tog_btn.pack(side="left", padx=6)

        tk.Label(tog_row,
            text="(off = plays at non-standard sens shown as ? and excluded from chart)",
            font=("Segoe UI", 7), bg=BG2, fg=MUTED).pack(side="left", padx=4)

        # Last-8 toggle
        l8_row = tk.Frame(frame, bg=BG2)
        l8_row.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(l8_row, text="Only count last 8 runs per sensitivity:",
            font=("Segoe UI", 8), bg=BG2, fg=TEXT2).pack(side="left")
        tk.Checkbutton(l8_row, text="ON",
            variable=self.last_8_only, command=lambda: self._refresh_main(),
            bg=BG2, fg=ACCENT2, selectcolor=BG3, activebackground=BG2,
            activeforeground=ACCENT2, font=("Consolas", 8, "bold"),
            relief="flat", bd=0, cursor="hand2").pack(side="left", padx=6)
        tk.Label(l8_row, text="(uses 8 most recent plays per cm for best/median)",
            font=("Segoe UI", 7), bg=BG2, fg=MUTED).pack(side="left", padx=4)

        # ── NEW: CM Range Filter row ─────────────────────────────────────────
        range_row = tk.Frame(frame, bg="#0a1a2a")
        range_row.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(range_row, text="⧉ CM RANGE FILTER:",
            font=("Segoe UI", 8, "bold"), bg="#0a1a2a", fg=ACCENT).pack(side="left", padx=(6, 4))
        tk.Label(range_row, text="min",
            font=("Segoe UI", 8), bg="#0a1a2a", fg=TEXT2).pack(side="left")

        min_entry = tk.Entry(range_row, textvariable=self.cm_range_min,
            bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=1,
            font=("Consolas", 9), width=6)
        min_entry.pack(side="left", padx=(2, 6), ipady=2)

        tk.Label(range_row, text="max",
            font=("Segoe UI", 8), bg="#0a1a2a", fg=TEXT2).pack(side="left")

        max_entry = tk.Entry(range_row, textvariable=self.cm_range_max,
            bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=1,
            font=("Consolas", 9), width=6)
        max_entry.pack(side="left", padx=(2, 8), ipady=2)

        def _apply_range(*_):
            self._refresh_main()

        ttk.Button(range_row, text="Apply", style="TButton",
            command=_apply_range).pack(side="left", padx=2)

        def _clear_range():
            self.cm_range_min.set("")
            self.cm_range_max.set("")
            self._refresh_main()

        ttk.Button(range_row, text="Clear", style="TButton",
            command=_clear_range).pack(side="left", padx=2)

        lo, hi = self._get_active_range()
        range_status = "inactive"
        range_col = MUTED
        if lo is not None or hi is not None:
            lo_s = f"{lo:.4g}" if lo is not None else "any"
            hi_s = f"{hi:.4g}" if hi is not None else "any"
            range_status = f"active: {lo_s} – {hi_s} cm  (also limits next-cm recommendation)"
            range_col = ACCENT2
        tk.Label(range_row, text=range_status,
            font=("Segoe UI", 7), bg="#0a1a2a", fg=range_col).pack(side="left", padx=8)

        # ── Group plays by exact cm ─────────────────────────────────────────
        byCm = defaultdict(list)
        for p in plays:
            cm = get_effective_cm(p, assignments)
            if cm is not None:
                byCm[cm].append(p["score"])
        if self.last_8_only.get():
            byCm = defaultdict(list, {cm: scores[-8:] for cm, scores in byCm.items()})

        show_all = self.show_all_cm.get()
        hidden = self._hidden_cms.get(name, set())

        standard_cms = [float(c) for c in CM_OPTIONS]
        nonstandard_cms = sorted(cm for cm in byCm if cm not in standard_cms)
        unknown_scores = [p["score"] for p in plays if get_effective_cm(p, assignments) is None]

        if show_all:
            display_cms_raw = sorted(set(standard_cms) | set(nonstandard_cms))
        else:
            display_cms_raw = standard_cms

        # Apply range filter + hidden filter
        display_cms = [cm for cm in display_cms_raw
                       if self._cm_in_range(cm) and cm not in hidden]

        all_displayed_scores = [s for cm in display_cms for s in byCm.get(cm, [])]
        max_score = max(all_displayed_scores) if all_displayed_scores else 1

        best_cm = None
        best_cm_score = -1
        for cm in display_cms:
            scores = byCm.get(cm, [])
            if scores:
                b = max(scores)
                if b > best_cm_score:
                    best_cm_score = b
                    best_cm = cm

        cm_bests_visible = {cm: max(scores) for cm, scores in byCm.items()
                            if cm in display_cms and byCm.get(cm)}
        est_cm, est_method = estimate_best_cm(cm_bests_visible)

        # ── NEW: worst cm for table highlighting ────────────────────────────
        worst_cm_table, _ = estimate_worst_cm(cm_bests_visible)
        worst_cm_key = None
        if worst_cm_table is not None and cm_bests_visible:
            worst_cm_key = min(cm_bests_visible.keys(),
                               key=lambda c: abs(c - worst_cm_table), default=None)

        rank_entries = {}

        # Table header
        header = tk.Frame(frame, bg=BG3)
        header.pack(fill="x")
        for txt, w, anchor in [
            ("CM/360", 9, "w"), ("Best Score", 10, "e"),
            ("Bar", 17, "w"), ("Median", 10, "e"),
            ("Plays", 5, "e"), ("Peak Rank", 14, "w"),
        ]:
            tk.Label(header, text=txt, font=("Segoe UI", 8, "bold"),
                bg=BG3, fg=TEXT2, width=w, anchor=anchor,
                pady=5).pack(side="left", padx=(8 if anchor=="w" and txt=="CM/360" else 2, 2))
        # Extra column header for hide button
        tk.Label(header, text="", bg=BG3, width=4).pack(side="left")
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x")

        def _make_row(cm_key, label_text, scores, is_question=False):
            nonlocal rank_entries
            b = max(scores) if scores else None
            med = calc_median(scores) if scores else None
            is_best = (cm_key == best_cm and b is not None and not is_question)
            is_est = (est_cm is not None and not is_question and
                      b is not None and isinstance(cm_key, float) and abs(cm_key - est_cm) < 1.0)
            # ── NEW: worst highlighting ─────────────────────────────────────
            is_worst = (worst_cm_key is not None and not is_question and
                        isinstance(cm_key, float) and cm_key == worst_cm_key and
                        not is_best)

            if is_question:
                row_bg = "#2a1a00"; cm_col = WARN
            elif is_best:
                row_bg = "#1a2840"; cm_col = GOLD
            elif is_worst:
                row_bg = WORST_BG; cm_col = WORST_COL
            elif is_est:
                row_bg = "#1a2a1a"; cm_col = ACCENT2
            else:
                row_bg = BG2; cm_col = ACCENT

            row = tk.Frame(frame, bg=row_bg)
            row.pack(fill="x")
            tk.Frame(row, bg=BORDER, height=1).pack(fill="x")
            inner = tk.Frame(row, bg=row_bg)
            inner.pack(fill="x")

            worst_marker = "  ☠" if is_worst else ""
            suffix = ("  ★" if is_best else ("  ~" if is_est else worst_marker))
            tk.Label(inner, text=label_text + suffix,
                font=("Consolas", 9, "bold" if (is_best or is_worst) else "normal"),
                bg=row_bg, fg=cm_col, width=9, anchor="w").pack(side="left", padx=(8,4), pady=4)

            sc_col = GOLD if is_best else (WORST_COL if is_worst else (WARN if is_question else (ACCENT2 if b else MUTED)))
            tk.Label(inner, text=fmt_score(b),
                font=("Consolas", 10, "bold" if (is_best or is_worst) else "normal"),
                bg=row_bg, fg=sc_col, width=10, anchor="e").pack(side="left", padx=4)

            bar_frame = tk.Frame(inner, bg=row_bg, width=140)
            bar_frame.pack(side="left", padx=4)
            bar_frame.pack_propagate(False)
            if b and not is_question:
                pct = max(2, int((b / max_score) * 130))
                bar_bg = tk.Frame(bar_frame, bg=BG3, height=8, width=130)
                bar_bg.pack(pady=9)
                bar_bg.pack_propagate(False)
                bar_color = GOLD if is_best else (WORST_COL if is_worst else ACCENT2)
                bar_fill = tk.Frame(bar_bg, bg=bar_color, height=8, width=pct)
                bar_fill.place(x=0, y=0)

            tk.Label(inner, text=fmt_score(med),
                font=("Consolas", 9), bg=row_bg, fg=TEXT2, width=10, anchor="e").pack(side="left", padx=4)

            tk.Label(inner, text=str(len(scores)) if scores else "—",
                font=("Consolas", 9), bg=row_bg, fg=TEXT2, width=5, anchor="e").pack(side="left", padx=4)

            if not is_question:
                rank_val = ranks.get(str(cm_key), "")
                rv = tk.StringVar(value=rank_val)
                rank_entry = tk.Entry(inner, textvariable=rv,
                    bg=BG3, fg=TEXT2 if not rank_val else TEXT,
                    insertbackground=TEXT, relief="flat", bd=1,
                    font=("Segoe UI", 8), width=14)
                rank_entry.pack(side="left", padx=6, pady=4)
                rank_entries[cm_key] = rv

                # ── NEW: hide button ────────────────────────────────────────
                if not is_question and isinstance(cm_key, float):
                    hide_btn = tk.Button(inner, text="✕",
                        font=("Segoe UI", 7), bg=row_bg, fg=MUTED,
                        relief="flat", bd=0, padx=4, pady=2, cursor="hand2",
                        activebackground=row_bg, activeforeground=WARN,
                        command=lambda c=cm_key, n=name: self._hide_cm(n, c))
                    hide_btn.pack(side="left", padx=2)
            else:
                tk.Label(inner, text=f"{len(nonstandard_cms)} unique non-standard sens",
                    font=("Segoe UI", 7), bg=row_bg, fg=WARN).pack(side="left", padx=6)

        for cm in display_cms:
            label = f"{cm:.4g} cm"
            _make_row(cm, label, byCm.get(cm, []))

        if not show_all and nonstandard_cms:
            # Only show ? row for non-standard cms that aren't range-filtered out
            visible_nonstandard = [cm for cm in nonstandard_cms
                                   if self._cm_in_range(cm) and cm not in hidden]
            if visible_nonstandard:
                all_nonstandard_scores = [s for cm in visible_nonstandard for s in byCm.get(cm, [])]
                _make_row("?", "? cm", all_nonstandard_scores, is_question=True)

        def save_ranks(*_):
            if name not in self.storage["ranks"]:
                self.storage["ranks"][name] = {}
            for cm_key, var in rank_entries.items():
                val = var.get().strip()
                sk = str(cm_key)
                if val:
                    self.storage["ranks"][name][sk] = val
                elif sk in self.storage["ranks"].get(name, {}):
                    del self.storage["ranks"][name][sk]
            save_data(self.storage)

        for var in rank_entries.values():
            var.trace_add("write", save_ranks)

        # ── NEW: hidden cm listing + unhide section ──────────────────────────
        if hidden:
            hidden_frame = tk.Frame(frame, bg="#1a1a2a")
            hidden_frame.pack(fill="x", padx=8, pady=(4, 2))
            tk.Label(hidden_frame,
                text=f"  HIDDEN FROM CHART (temporary — resets on restart):",
                font=("Segoe UI", 7, "bold"), bg="#1a1a2a", fg=MUTED).pack(side="left", padx=4)
            for hcm in sorted(hidden):
                chip = tk.Frame(hidden_frame, bg=BG3)
                chip.pack(side="left", padx=2, pady=3)
                tk.Label(chip, text=f" {hcm:.4g} cm ",
                    font=("Consolas", 8), bg=BG3, fg=TEXT2).pack(side="left")
                tk.Button(chip, text="↩",
                    font=("Segoe UI", 7), bg=BG3, fg=ACCENT2,
                    relief="flat", bd=0, padx=2, cursor="hand2",
                    activebackground=BG3, activeforeground=ACCENT,
                    command=lambda c=hcm, n=name: self._unhide_cm(n, c)).pack(side="left")

            def _unhide_all():
                self._hidden_cms[name].clear()
                self._refresh_main()

            tk.Button(hidden_frame, text="↩ restore all",
                font=("Segoe UI", 7), bg="#1a1a2a", fg=ACCENT2,
                relief="flat", bd=0, padx=6, cursor="hand2",
                activebackground="#1a1a2a", activeforeground=ACCENT,
                command=_unhide_all).pack(side="left", padx=8)

        # Legend
        leg = tk.Frame(frame, bg=BG2)
        leg.pack(fill="x", padx=8, pady=(4, 8))
        nonstandard_note = (f"  |  {len(nonstandard_cms)} non-standard cm values hidden (toggle to show)"
                            if nonstandard_cms and not show_all else "")
        range_note = ""
        lo, hi = self._get_active_range()
        if lo is not None or hi is not None:
            range_note = f"  |  range filter active"
        hidden_note = f"  |  {len(hidden)} cm(s) hidden (✕ to hide, ↩ to restore)" if hidden else "  |  click ✕ on a row to temporarily hide it"
        tk.Label(leg,
            text=f"★ = best cm  |  ~ = est. best  |  ☠ = worst cm{nonstandard_note}{range_note}{hidden_note}",
            font=("Segoe UI", 7), bg=BG2, fg=MUTED).pack(anchor="w")

    # ── NEW: hide/unhide cm helpers ───────────────────────────────────────────
    def _hide_cm(self, name: str, cm: float):
        self._hidden_cms[name].add(cm)
        self._refresh_main()
        self._show_toast(f"Hidden {cm:.4g} cm from chart (temporary)")

    def _unhide_cm(self, name: str, cm: float):
        self._hidden_cms[name].discard(cm)
        self._refresh_main()
        self._show_toast(f"Restored {cm:.4g} cm to chart")

    # ─────────────────────────────────────────────────────────────────────────

    def _build_chart_section(self, parent, name, plays, assignments):
        outer = tk.Frame(parent, bg=BG2, bd=1, relief="solid")
        outer.pack(fill="x", padx=16, pady=6)

        is_collapsed = self._chart_collapsed.get(name, True)

        hdr_bar = tk.Frame(outer, bg=BG3, cursor="hand2")
        hdr_bar.pack(fill="x")

        arrow = "▶" if is_collapsed else "▼"
        hdr_lbl = tk.Label(
            hdr_bar,
            text=f"  {arrow}  CM/360 SCORE CHART",
            font=("Consolas", 9, "bold"),
            bg=BG3,
            fg=ACCENT,
            anchor="w",
            pady=6
        )
        hdr_lbl.pack(side="left", padx=4)

        hdr_hint = tk.Label(
            hdr_bar,
            text="click to collapse",
            font=("Segoe UI", 7),
            bg=BG3,
            fg=MUTED,
            anchor="e"
        )
        hdr_hint.pack(side="right", padx=8)

        chart_frame = tk.Frame(outer, bg=BG2)
        if not is_collapsed:
            chart_frame.pack(fill="x")

        controls_row = tk.Frame(chart_frame, bg=BG2)
        controls_row.pack(fill="x", padx=12, pady=(8, 2))

        tk.Label(
            controls_row,
            text="Chart size:",
            font=("Segoe UI", 8),
            bg=BG2,
            fg=TEXT2
        ).pack(side="left")

        def _set_chart_scale(next_scale):
            clamped_scale = max(0.85, min(1.8, next_scale))
            self.chart_scale.set(clamped_scale)
            self._refresh_main(restore_tab=name)

        def _set_chart_height(next_height):
            clamped_height = max(0.90, min(1.8, next_height))
            self.chart_height.set(clamped_height)
            self._refresh_main(restore_tab=name)

        tk.Button(
            controls_row,
            text="− Width",
            font=("Segoe UI", 8),
            bg=BG3,
            fg=TEXT2,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: _set_chart_scale(self.chart_scale.get() - 0.10)
        ).pack(side="left", padx=(8, 2))

        tk.Button(
            controls_row,
            text="+ Width",
            font=("Segoe UI", 8),
            bg=BG3,
            fg=TEXT2,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: _set_chart_scale(self.chart_scale.get() + 0.10)
        ).pack(side="left", padx=2)

        tk.Button(
            controls_row,
            text="− Height",
            font=("Segoe UI", 8),
            bg=BG3,
            fg=TEXT2,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: _set_chart_height(self.chart_height.get() - 0.10)
        ).pack(side="left", padx=(10, 2))

        tk.Button(
            controls_row,
            text="+ Height",
            font=("Segoe UI", 8),
            bg=BG3,
            fg=TEXT2,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: _set_chart_height(self.chart_height.get() + 0.10)
        ).pack(side="left", padx=2)

        tk.Button(
            controls_row,
            text="Reset",
            font=("Segoe UI", 8),
            bg=BG3,
            fg=ACCENT,
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._reset_chart_size(name)
        ).pack(side="left", padx=(10, 2))

        tk.Label(
            controls_row,
            text=f"width {self.chart_scale.get():.2f}x   height {self.chart_height.get():.2f}x",
            font=("Consolas", 8),
            bg=BG2,
            fg=MUTED
        ).pack(side="left", padx=10)

        def _toggle(event=None):
            self._chart_collapsed[name] = not self._chart_collapsed.get(name, False)
            if self._chart_collapsed[name]:
                chart_frame.pack_forget()
                hdr_lbl.config(text="  ▶  CM/360 SCORE CHART")
            else:
                chart_frame.pack(fill="x")
                hdr_lbl.config(text="  ▼  CM/360 SCORE CHART")

        hdr_bar.bind("<Button-1>", _toggle)
        hdr_lbl.bind("<Button-1>", _toggle)
        hdr_hint.bind("<Button-1>", _toggle)

        hidden = self._hidden_cms.get(name, set())
        by_cm = defaultdict(list)
        for play in plays:
            cm_value = get_effective_cm(play, assignments)
            if cm_value is not None:
                by_cm[cm_value].append(play["score"])

        if self.last_8_only.get():
            by_cm = defaultdict(list, {
                cm_value: scores[-8:]
                for cm_value, scores in by_cm.items()
            })

        visible_cms = sorted(
            cm_value for cm_value in by_cm
            if self._cm_in_range(cm_value) and cm_value not in hidden
        )

        if not visible_cms:
            tk.Label(
                chart_frame,
                text="No data to chart with current filters.",
                font=("Segoe UI", 9),
                bg=BG2,
                fg=MUTED
            ).pack(pady=20)
            return

        figure = self._create_score_chart_figure(
            visible_cms=visible_cms,
            by_cm=by_cm
        )

        canvas_widget = FigureCanvasTkAgg(figure, master=chart_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="x", padx=16, pady=(4, 8))

        chart_frame.bind("<Destroy>", lambda event: plt.close(figure))

    def _create_score_chart_figure(self, visible_cms, by_cm):
        best_scores = [max(by_cm[cm_value]) for cm_value in visible_cms]
        cm_bests = dict(zip(visible_cms, best_scores))

        est_cm, est_method = estimate_best_cm(cm_bests)
        worst_cm, worst_method = estimate_worst_cm(cm_bests)

        est_cm_key = None
        if est_cm is not None:
            est_cm_key = min(cm_bests.keys(), key=lambda cm_value: abs(cm_value - est_cm))

        worst_cm_key = None
        if worst_cm is not None:
            worst_cm_key = min(cm_bests.keys(), key=lambda cm_value: abs(cm_value - worst_cm))

        bar_count = len(visible_cms)

        base_width = max(5.4, min(7.8, 4.8 + (bar_count * 0.18)))
        base_height = 4.9

        figure_width = base_width * self.chart_scale.get()
        figure_height = base_height * self.chart_height.get()

        figure, axis = plt.subplots(figsize=(figure_width, figure_height), dpi=100)
        figure.patch.set_facecolor(BG2)
        axis.set_facecolor(BG2)

        x_positions = list(range(len(visible_cms)))

        bar_colors = []
        for cm_value in visible_cms:
            if est_cm_key is not None and cm_value == est_cm_key:
                bar_colors.append(GOLD)
            elif worst_cm_key is not None and cm_value == worst_cm_key:
                bar_colors.append(WORST_COL)
            else:
                bar_colors.append(ACCENT)

        bars = axis.bar(
            x_positions,
            best_scores,
            color=bar_colors,
            width=0.78,
            zorder=2,
            linewidth=0
        )

        max_score = max(best_scores)
        min_score = min(best_scores)

        label_offset = max_score * 0.016
        for bar_rect, score in zip(bars, best_scores):
            axis.text(
                bar_rect.get_x() + (bar_rect.get_width() / 2),
                bar_rect.get_height() + label_offset,
                str(int(score)),
                ha="center",
                va="bottom",
                color=TEXT2,
                fontsize=8,
                fontfamily="Consolas"
            )

        if est_cm_key is not None:
            est_index = visible_cms.index(est_cm_key)
            axis.axvline(
                est_index,
                color=GOLD,
                linewidth=1.5,
                linestyle="--",
                zorder=3,
                alpha=0.85
            )
            axis.text(
                est_index + 0.22,
                max_score * 0.985,
                f"est. best\n~{est_cm:.4g} cm",
                color=GOLD,
                fontsize=8,
                va="top",
                ha="left",
                fontfamily="Consolas",
                bbox=dict(
                    boxstyle="round,pad=0.22",
                    facecolor=BG2,
                    edgecolor="none",
                    alpha=0.92
                ),
                zorder=4
            )

        if worst_cm_key is not None and worst_cm_key != est_cm_key:
            worst_index = visible_cms.index(worst_cm_key)
            axis.axvline(
                worst_index,
                color=WORST_COL,
                linewidth=1.5,
                linestyle=":",
                zorder=3,
                alpha=0.85
            )

            worst_label_x = worst_index + 0.38
            worst_label_align = "left"

            if worst_index >= len(visible_cms) - 2:
                worst_label_x = worst_index - 0.38
                worst_label_align = "right"

            axis.text(
                worst_label_x,
                max_score * 0.86,
                f"worst\n~{worst_cm:.4g} cm",
                color=WORST_COL,
                fontsize=8,
                va="top",
                ha=worst_label_align,
                fontfamily="Consolas",
                bbox=dict(
                    boxstyle="round,pad=0.22",
                    facecolor=BG2,
                    edgecolor="none",
                    alpha=0.92
                ),
                zorder=4
            )

        axis.set_xticks(x_positions)
        axis.set_xticklabels(
            [f"{cm_value:.4g}" for cm_value in visible_cms],
            color=TEXT2,
            fontsize=8,
            fontfamily="Consolas"
        )

        axis.set_ylabel("Best Score", color=TEXT2, fontsize=9)
        axis.set_xlabel("cm / 360", color=TEXT2, fontsize=9)
        axis.tick_params(colors=TEXT2, length=3, labelsize=8)
        axis.tick_params(axis="y", colors=TEXT2)

        for spine in axis.spines.values():
            spine.set_color(BG3)

        axis.set_ylim(
            bottom=max(0, min_score * 0.90),
            top=max_score * 1.20
        )

        axis.margins(x=0.08)

        axis.grid(axis="y", color=BG3, linewidth=0.8, zorder=0)
        axis.set_axisbelow(True)

        legend_handles = [
            mpatches.Patch(
                color=GOLD,
                label=f"Est. best  (~{est_cm:.4g} cm  {est_method})" if est_cm is not None else "Est. best"
            ),
            mpatches.Patch(
                color=WORST_COL,
                label=f"Worst  (~{worst_cm:.4g} cm  {worst_method})" if worst_cm is not None else "Worst"
            ),
            mpatches.Patch(
                color=ACCENT,
                label="Other tested cm"
            ),
        ]

        axis.legend(
            handles=legend_handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=3,
            facecolor=BG3,
            edgecolor=BG3,
            labelcolor=TEXT2,
            fontsize=8,
            framealpha=1.0,
            borderpad=0.6,
            handlelength=1.6,
            handletextpad=0.5,
            columnspacing=1.4
        )

        figure.tight_layout(pad=1.2, rect=(0, 0.06, 1, 1))
        return figure
    def _assign_play(self, name, filename, cm_var):
        val = cm_var.get().strip()
        if not self.storage["assignments"].get(name):
            self.storage["assignments"][name] = {}
        if val:
            self.storage["assignments"][name][filename] = int(val)
        elif filename in self.storage["assignments"].get(name, {}):
            del self.storage["assignments"][name][filename]
        save_data(self.storage)
        self._refresh_main()
        self._show_toast(f"Saved — rebuild in progress")

    def _quick_tag(self, name, cm):
        plays = self.all_scenarios.get(name, [])
        assignments = self.storage["assignments"].get(name, {})
        unassigned = next(
            (p for p in reversed(plays)
             if get_effective_cm(p, assignments) is None), None)
        if not unassigned:
            self._show_toast("All plays have a cm/360 assigned!")
            return
        if name not in self.storage["assignments"]:
            self.storage["assignments"][name] = {}
        self.storage["assignments"][name][unassigned["filename"]] = cm
        save_data(self.storage)
        self._refresh_main()
        self._show_toast(f"Tagged {fmt_ts(unassigned['ts'])} → {cm} cm/360")

    def _remove_scenario(self, name):
        if name in self.selected:
            self.selected.remove(name)
        self.sel_label.config(text=f"{len(self.selected)} / 5 selected")
        self._populate_scenario_list(self.search_var.get())
        self._refresh_main()
    
    def _reset_chart_size(self, restore_tab_name=""):
        self.chart_scale.set(1.0)
        self.chart_height.set(1.0)
        self._refresh_main(restore_tab=restore_tab_name)

    # ── Toast notification ────────────────────────────────────────────────────
    def _show_toast(self, msg):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=BG2)
        tk.Label(toast, text=f"  {msg}  ",
            font=("Consolas", 9), bg=BG2, fg=ACCENT2,
            padx=10, pady=6).pack()
        self.update_idletasks()
        w = self.winfo_x() + self.winfo_width() - 320
        h = self.winfo_y() + self.winfo_height() - 60
        toast.geometry(f"+{w}+{h}")
        toast.after(2000, toast.destroy)


# ─────────────────────────────────────────────────────────────────────────────

