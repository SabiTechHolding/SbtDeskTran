"""
Reusable widget components for SbtDeskTran.
"""
import tkinter as tk
from tkinter import ttk
from diff_engine import compute_line_diff, compute_inline_diff, get_diff_stats


def themed_scrollbar(parent, theme: dict, orient: str = "vertical", **kwargs) -> ttk.Scrollbar:
    """
    Create a ttk.Scrollbar styled to match the current theme.
    Uses ttk so thumb/trough colors are respected on Windows.
    """
    # Must use standard style names that map to existing ttk layouts
    if orient == "vertical":
        style_name = "Themed.Vertical.TScrollbar"
        base = "Vertical.TScrollbar"
    else:
        style_name = "Themed.Horizontal.TScrollbar"
        base = "Horizontal.TScrollbar"

    t = theme
    style = ttk.Style()
    # Clone layout from base style then override colors
    try:
        layout = style.layout(base)
        style.layout(style_name, layout)
    except Exception:
        pass  # layout already registered or not needed

    style.configure(style_name,
        troughcolor=t.get("bg2", "#141414"),
        background=t.get("scrollbar", "#383838"),
        arrowcolor=t.get("fg2", "#909090"),
        borderwidth=0,
        bd=0,
        relief="flat",
    )
    style.map(style_name,
        background=[
            ("active",  t.get("scrollbar_hover", "#484848")),
            ("!active", t.get("scrollbar",       "#383838")),
        ]
    )
    return ttk.Scrollbar(parent, orient=orient, style=style_name, **kwargs)


def _cjk_font(base_font: tuple) -> tuple:
    """
    Return a font tuple that renders CJK characters.
    Tries fonts with good CJK coverage available on Windows.
    Falls back to base_font if none found.
    """
    import tkinter.font as tkfont
    cjk_candidates = [
        "MS Gothic",        # Japanese — ships with Windows
        "Yu Gothic",        # Japanese — Windows 8.1+
        "Meiryo",           # Japanese — Windows Vista+
        "BIZ UDGothic",     # Japanese — Windows 10+
        "MS Mincho",        # Japanese
        "SimSun",           # Chinese
        "Malgun Gothic",    # Korean
        "Noto Sans CJK JP", # cross-platform
    ]
    try:
        families = set(tkfont.families())
        for name in cjk_candidates:
            if name in families:
                return (name, base_font[1]) + base_font[2:]
    except Exception:
        pass
    return base_font


# ──────────────────────────────────────────────
# Flat Button
# ──────────────────────────────────────────────
class FlatButton(tk.Label):
    """Flat styled button using a Label for full color control."""

    def __init__(self, parent, text, command=None, theme=None,
                 width=None, icon=None, toggle=False, **kwargs):
        self.theme = theme or {}
        self.command = command
        self.toggle = toggle
        self._toggled = False
        display = f"{icon} {text}" if icon else text
        super().__init__(
            parent,
            text=display,
            bg=self.theme.get("btn_bg", "#313244"),
            fg=self.theme.get("btn_fg", "#cdd6f4"),
            cursor="hand2",
            padx=10, pady=4,
            font=self.theme.get("font_ui", ("Segoe UI", 9)),
            relief="flat",
            bd=0,
            **kwargs,
        )
        if width:
            self.config(width=width)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        if not self._toggled:
            self.config(bg=self.theme.get("btn_hover", "#45475a"))

    def _on_leave(self, _):
        if not self._toggled:
            self.config(bg=self.theme.get("btn_bg", "#313244"))

    def _on_click(self, _):
        if self.toggle:
            self._toggled = not self._toggled
            if self._toggled:
                self.config(
                    bg=self.theme.get("accent", "#89b4fa"),
                    fg=self.theme.get("bg", "#1e1e2e"),
                )
            else:
                self.config(
                    bg=self.theme.get("btn_bg", "#313244"),
                    fg=self.theme.get("btn_fg", "#cdd6f4"),
                )
        if self.command:
            self.command()

    def set_toggled(self, state: bool):
        self._toggled = state
        if state:
            self.config(
                bg=self.theme.get("accent", "#89b4fa"),
                fg=self.theme.get("bg", "#1e1e2e"),
            )
        else:
            self.config(
                bg=self.theme.get("btn_bg", "#313244"),
                fg=self.theme.get("btn_fg", "#cdd6f4"),
            )

    def update_theme(self, theme):
        self.theme = theme
        self.set_toggled(self._toggled)


# ──────────────────────────────────────────────
# Diff Viewer Widget
# ──────────────────────────────────────────────
class DiffViewer(tk.Frame):
    """
    Side-by-side diff viewer with line-level and word-level highlighting.
    Inspired by GitHub / VSCode / Beyond Compare diff UI.
    """

    def __init__(self, parent, theme, word_wrap: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        self.theme = theme
        self._word_wrap = word_wrap
        self._build_ui()

    def _build_ui(self):
        t = self.theme
        wrap_mode = "char" if self._word_wrap else "none"
        self.config(bg=t["bg2"])

        # ── Stats header — hidden (stats shown in app statusbar) ────────────
        self.header = tk.Frame(self, bg=t["diff_header_bg"], height=0)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        self.stats_label = tk.Label(self.header, text="",
            bg=t["diff_header_bg"], fg=t["diff_header_fg"],
            font=t["font_ui"], anchor="w", padx=8)

        # ── Side-by-side panes: pure grid, equal columns ─────────────────────
        self.pane_frame = tk.Frame(self, bg=t["bg2"])
        self.pane_frame.pack(fill="both", expand=True)
        self.pane_frame.columnconfigure(0, weight=1, uniform="half")
        self.pane_frame.columnconfigure(1, weight=0, minsize=2)
        self.pane_frame.columnconfigure(2, weight=1, uniform="half")
        self.pane_frame.rowconfigure(0, weight=1)

        # ── Left pane ────────────────────────────────────────────────────────
        self.left_frame = tk.Frame(self.pane_frame, bg=t["bg2"])
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.rowconfigure(1, weight=1)
        self.left_frame.columnconfigure(0, weight=1)

        self.left_label = tk.Label(self.left_frame,
            text="  ◀  Diff left",
            bg=t["diff_header_bg"], fg=t["diff_del_fg"],
            font=t["font_ui_bold"], anchor="w", padx=4, pady=3)
        self.left_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.left_text = tk.Text(self.left_frame,
            bg=t["diff_equal_bg"], fg=t["diff_equal_fg"],
            font=_cjk_font(t["font_mono"]), wrap=wrap_mode,
            relief="flat", bd=0, state="disabled",
            selectbackground=t["selection"], cursor="arrow")
        self.left_scroll_y = themed_scrollbar(self.left_frame, t,
            command=self._sync_scroll_y)
        self.left_text.config(yscrollcommand=self._left_yscroll)
        self.left_text.grid(row=1, column=0, sticky="nsew")
        self.left_scroll_y.grid(row=1, column=1, sticky="ns")

        # Horizontal scrollbar for left — only when wrap=off
        if not self._word_wrap:
            self.left_scroll_x = themed_scrollbar(self.left_frame, t,
                orient="horizontal", command=self._sync_scroll_x_left)
            self.left_text.config(xscrollcommand=self._left_xscroll)
            self.left_scroll_x.grid(row=2, column=0, sticky="ew")
            self.left_frame.rowconfigure(2, weight=0)

        # Separator
        tk.Frame(self.pane_frame, bg=t["border"], width=2).grid(
            row=0, column=1, sticky="ns")

        # ── Right pane ───────────────────────────────────────────────────────
        self.right_frame = tk.Frame(self.pane_frame, bg=t["bg2"])
        self.right_frame.grid(row=0, column=2, sticky="nsew")
        self.right_frame.rowconfigure(1, weight=1)
        self.right_frame.columnconfigure(0, weight=1)

        self.right_label = tk.Label(self.right_frame,
            text="  ▶  Diff right",
            bg=t["diff_header_bg"], fg=t["diff_add_fg"],
            font=t["font_ui_bold"], anchor="w", padx=4, pady=3)
        self.right_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.right_text = tk.Text(self.right_frame,
            bg=t["diff_equal_bg"], fg=t["diff_equal_fg"],
            font=_cjk_font(t["font_mono"]), wrap=wrap_mode,
            relief="flat", bd=0, state="disabled",
            selectbackground=t["selection"], cursor="arrow")
        self.right_scroll_y = themed_scrollbar(self.right_frame, t,
            command=self._sync_scroll_y)
        self.right_text.config(yscrollcommand=self._right_yscroll)
        self.right_text.grid(row=1, column=0, sticky="nsew")
        self.right_scroll_y.grid(row=1, column=1, sticky="ns")

        if not self._word_wrap:
            self.right_scroll_x = themed_scrollbar(self.right_frame, t,
                orient="horizontal", command=self._sync_scroll_x_right)
            self.right_text.config(xscrollcommand=self._right_xscroll)
            self.right_scroll_x.grid(row=2, column=0, sticky="ew")
            self.right_frame.rowconfigure(2, weight=0)

        self._configure_tags(self.left_text)
        self._configure_tags(self.right_text)

    def _configure_tags(self, widget: tk.Text):
        t = self.theme
        mono_bold = (t["font_mono"][0], t["font_mono"][1], "bold")

        widget.tag_configure("equal",
            background=t["diff_equal_bg"],
            foreground=t["diff_equal_fg"])

        widget.tag_configure("delete_line",
            background=t["diff_del_bg"],
            foreground=t["diff_del_fg"])

        widget.tag_configure("insert_line",
            background=t["diff_add_bg"],
            foreground=t["diff_add_fg"])

        # Inline highlights: bold + high-contrast fg for maximum visibility
        widget.tag_configure("delete_inline",
            background=t["diff_del_inline"],
            foreground="#ffffff",
            font=mono_bold)

        widget.tag_configure("insert_inline",
            background=t["diff_add_inline"],
            foreground="#ffffff",
            font=mono_bold)

        widget.tag_configure("placeholder",
            background=t["diff_header_bg"],
            foreground=t["diff_line_num_fg"])

        widget.tag_configure("line_num",
            foreground=t["diff_line_num_fg"],
            font=(t["font_mono"][0], t["font_mono"][1] - 1))

    def _left_yscroll(self, *args):
        self.left_scroll_y.set(*args)
        self.right_text.yview_moveto(args[0])

    def _right_yscroll(self, *args):
        self.right_scroll_y.set(*args)
        self.left_text.yview_moveto(args[0])

    def _sync_scroll_y(self, *args):
        self.left_text.yview(*args)
        self.right_text.yview(*args)

    def _left_xscroll(self, *args):
        try:
            self.left_scroll_x.set(*args)
        except Exception:
            pass

    def _right_xscroll(self, *args):
        try:
            self.right_scroll_x.set(*args)
        except Exception:
            pass

    def _sync_scroll_x_left(self, *args):
        self.left_text.xview(*args)

    def _sync_scroll_x_right(self, *args):
        self.right_text.xview(*args)

    def render(self, old_text: str, new_text: str):
        """Render a diff between old_text and new_text."""
        chunks = compute_line_diff(old_text, new_text)
        stats = get_diff_stats(chunks)
        added = stats["added"]
        removed = stats["removed"]
        blocks = stats["changed_blocks"]
        self.stats_label.config(
            text=f"   +{added} added   −{removed} removed   "
                 f"{blocks} changed block{'s' if blocks != 1 else ''}"
        )

        for widget in (self.left_text, self.right_text):
            widget.config(state="normal")
            widget.delete("1.0", "end")

        old_lineno = 1
        new_lineno = 1

        for chunk in chunks:
            kind = chunk.kind

            if kind == "equal":
                for line in chunk.old_lines:
                    self._insert_line(self.left_text, old_lineno,
                                      line.rstrip("\n"), "equal")
                    self._insert_line(self.right_text, new_lineno,
                                      line.rstrip("\n"), "equal")
                    old_lineno += 1
                    new_lineno += 1

            elif kind == "delete":
                for line in chunk.old_lines:
                    self._insert_line(self.left_text, old_lineno,
                                      line.rstrip("\n"), "delete_line")
                    self._insert_placeholder(self.right_text)
                    old_lineno += 1

            elif kind == "insert":
                for line in chunk.new_lines:
                    self._insert_placeholder(self.left_text)
                    self._insert_line(self.right_text, new_lineno,
                                      line.rstrip("\n"), "insert_line")
                    new_lineno += 1

            elif kind == "replace":
                max_lines = max(len(chunk.old_lines), len(chunk.new_lines))
                for i in range(max_lines):
                    old_line = (chunk.old_lines[i]
                                if i < len(chunk.old_lines) else None)
                    new_line = (chunk.new_lines[i]
                                if i < len(chunk.new_lines) else None)

                    if old_line is not None and new_line is not None:
                        old_toks, new_toks = compute_inline_diff(old_line, new_line)
                        self._insert_inline_line(
                            self.left_text, old_lineno, old_toks, "delete")
                        self._insert_inline_line(
                            self.right_text, new_lineno, new_toks, "insert")
                        old_lineno += 1
                        new_lineno += 1
                    elif old_line is not None:
                        self._insert_line(self.left_text, old_lineno,
                                          old_line.rstrip("\n"), "delete_line")
                        self._insert_placeholder(self.right_text)
                        old_lineno += 1
                    else:
                        self._insert_placeholder(self.left_text)
                        self._insert_line(self.right_text, new_lineno,
                                          new_line.rstrip("\n"), "insert_line")
                        new_lineno += 1

        for widget in (self.left_text, self.right_text):
            widget.config(state="disabled")

    def clear(self):
        for widget in (self.left_text, self.right_text):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")
        self.stats_label.config(
            text="  No diff yet — translate some text first")

    def _insert_line(self, widget, lineno, text, tag):
        widget.insert("end", f" {lineno:>4} ", "line_num")
        widget.insert("end", " " + text + "\n", tag)

    def _insert_placeholder(self, widget):
        widget.insert("end", "       \n", "placeholder")

    def _insert_inline_line(self, widget, lineno, tokens, side):
        bg_tag = "delete_line" if side == "delete" else "insert_line"
        inline_tag = "delete_inline" if side == "delete" else "insert_inline"
        widget.insert("end", f" {lineno:>4} ", "line_num")
        widget.insert("end", " ", bg_tag)
        for token in tokens:
            if token.kind == "equal":
                widget.insert("end", token.text, bg_tag)
            else:
                widget.insert("end", token.text, inline_tag)
        widget.insert("end", "\n", bg_tag)

    def update_theme(self, theme):
        self.theme = theme
        t = theme
        self.config(bg=t["bg2"])
        self.header.config(bg=t["diff_header_bg"])
        self.stats_label.config(bg=t["diff_header_bg"], fg=t["diff_header_fg"])
        self.left_label.config(bg=t["diff_header_bg"], fg=t["diff_del_fg"])
        self.right_label.config(bg=t["diff_header_bg"], fg=t["diff_add_fg"])
        for sb in (self.left_scroll_y, self.right_scroll_y):
            sb.config(
                bg=t.get("scrollbar", "#383838"),
                troughcolor=t.get("bg2", "#141414"),
                activebackground=t.get("scrollbar_hover", "#484848"),
            )
        for widget in (self.left_text, self.right_text):
            widget.config(
                bg=t["diff_equal_bg"], fg=t["diff_equal_fg"],
                selectbackground=t["selection"],
            )
            self._configure_tags(widget)
