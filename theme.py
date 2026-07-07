"""
Theme definitions - Dark and Light themes.
"""

THEMES = {
    "dark": {
        "name": "dark",
        # Pure neutral dark — không ám màu xanh
        "bg": "#1a1a1a",
        "bg2": "#141414",
        "bg3": "#252525",
        "fg": "#e8e8e8",
        "fg2": "#909090",
        "accent": "#d4a843",       # vàng/amber — nổi bật trên nền tối
        "accent2": "#c0c0c0",      # xám sáng cho text dịch
        "success": "#6abf6a",
        "warning": "#c8963e",
        "error": "#d95f5f",
        "border": "#333333",
        "selection": "#3a3a3a",
        "btn_bg": "#2a2a2a",
        "btn_fg": "#d0d0d0",
        "btn_hover": "#363636",
        "btn_active": "#404040",

        # Diff colors
        "diff_add_bg":     "#0d2a0d",   # nền line thêm — xanh lá đậm
        "diff_add_inline": "#1a6b1a",   # inline word thêm — xanh lá sáng hẳn
        "diff_add_fg":     "#87d987",   # text trên nền add
        "diff_del_bg":     "#2a0d0d",   # nền line xóa — đỏ đậm
        "diff_del_inline": "#8b1a1a",   # inline word xóa — đỏ sáng hẳn
        "diff_del_fg":     "#f08080",   # text trên nền del
        "diff_equal_bg":   "#1a1a1a",   # nền dòng không đổi
        "diff_equal_fg":   "#c0c0c0",   # text không đổi — sáng hơn để dễ đọc
        "diff_header_bg":  "#141414",
        "diff_header_fg":  "#d4a843",
        "diff_line_num_bg":"#141414",
        "diff_line_num_fg":"#555555",

        "scrollbar": "#383838",
        "scrollbar_hover": "#484848",
        "combo_bg": "#252525",
        "combo_fg": "#d0d0d0",
        "status_bg": "#111111",
        "status_fg": "#707070",
        "separator": "#333333",
        "font_mono": ("Consolas", 10),
        "font_ui": ("Segoe UI", 9),
        "font_ui_bold": ("Segoe UI", 9, "bold"),
        "font_small": ("Segoe UI", 8),
    },
    "light": {
        "name": "light",
        "bg": "#ffffff",
        "bg2": "#f5f5f5",
        "bg3": "#e8e8e8",
        "fg": "#1e1e1e",
        "fg2": "#5a5a5a",
        "accent": "#0078d4",
        "accent2": "#0099bc",
        "success": "#107c10",
        "warning": "#b8860b",
        "error": "#c42b1c",
        "border": "#d1d1d1",
        "selection": "#cce8ff",
        "btn_bg": "#f0f0f0",
        "btn_fg": "#1e1e1e",
        "btn_hover": "#e0e0e0",
        "btn_active": "#d0d0d0",

        # Diff colors
        "diff_add_bg":     "#d4f7dc",   # nền line thêm — xanh lá nhạt
        "diff_add_inline": "#34a853",   # inline word thêm — xanh đậm, contrast cao
        "diff_add_fg":     "#1a4a2a",   # text trên nền add
        "diff_del_bg":     "#fce8e8",   # nền line xóa — đỏ nhạt
        "diff_del_inline": "#d93025",   # inline word xóa — đỏ đậm, contrast cao
        "diff_del_fg":     "#5c1010",   # text trên nền del
        "diff_equal_bg":   "#ffffff",   # nền dòng không đổi
        "diff_equal_fg":   "#3c3c3c",   # text không đổi
        "diff_header_bg":  "#f6f8fa",
        "diff_header_fg":  "#0078d4",
        "diff_line_num_bg":"#f6f8fa",
        "diff_line_num_fg":"#a0a0a0",

        "scrollbar": "#c0c0c0",
        "scrollbar_hover": "#a0a0a0",
        "combo_bg": "#ffffff",
        "combo_fg": "#1e1e1e",
        "status_bg": "#f0f0f0",
        "status_fg": "#5a5a5a",
        "separator": "#d1d1d1",
        "font_mono": ("Consolas", 10),
        "font_ui": ("Segoe UI", 9),
        "font_ui_bold": ("Segoe UI", 9, "bold"),
        "font_small": ("Segoe UI", 8),
    },
}
