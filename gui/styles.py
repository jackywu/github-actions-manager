"""Catppuccin inspired light and dark QSS stylesheets."""

def get_stylesheet(theme: str = "light") -> str:
    """Return the QSS string for the specified theme."""
    is_dark = (theme == "dark")

    # ---- Colors: Catppuccin Mocha (dark) vs Latte (light) ----
    bg_base = "#1e1e2e" if is_dark else "#eff1f5"
    bg_mantle = "#181825" if is_dark else "#e6e9ef"
    bg_crust = "#11111b" if is_dark else "#dce0e8"

    surf0 = "#313244" if is_dark else "#ccd0da"
    surf1 = "#45475a" if is_dark else "#bcc0cc"
    surf2 = "#585b70" if is_dark else "#acb0be"

    text_main = "#cdd6f4" if is_dark else "#4c4f69"
    text_sub = "#a6adc8" if is_dark else "#6c6f85"
    text_muted = "#6c7086" if is_dark else "#9ca0b0"

    primary = "#cba6f7" if is_dark else "#7287fd"
    primary_hover = "#d4b9f8" if is_dark else "#8aa2fd"
    primary_press = "#b89af5" if is_dark else "#5c74fc"

    danger = "#f38ba8" if is_dark else "#d20f39"
    danger_hover = "#f5a3b8" if is_dark else "#e82950"
    danger_press = "#e07090" if is_dark else "#ba0b30"

    success = "#a6e3a1" if is_dark else "#40a02b"
    success_hover = "#b8e9b4" if is_dark else "#50b83c"

    blue = "#89b4fa" if is_dark else "#1e66f5"

    # Status badge colors
    # For dark mode, we use dark backgrounds with bright text.
    # For light mode, we use pale backgrounds with dark text.
    st_success_bg = "#1c4a2c" if is_dark else "#e2f5e0"
    st_success_fg = "#a6e3a1" if is_dark else "#2e7a1f"

    st_failure_bg = "#4a1c2c" if is_dark else "#fce6eb"
    st_failure_fg = "#f38ba8" if is_dark else "#a80b2d"

    st_cancelled_bg = "#2a2a3e" if is_dark else "#e5e7ed"
    st_cancelled_fg = "#6c7086" if is_dark else "#5c5f77"

    st_skipped_bg = "#3a3a20" if is_dark else "#fdf6e3"
    st_skipped_fg = "#f9e2af" if is_dark else "#b58900"

    st_inprogress_bg = "#1a2a4a" if is_dark else "#e1ebfb"
    st_inprogress_fg = "#89b4fa" if is_dark else "#1451d6"

    return f"""
/* =========================================================
   Global
   ========================================================= */
* {{
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {text_main};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {bg_base};
}}

QWidget {{
    background-color: {bg_base};
}}

/* =========================================================
   Splitter
   ========================================================= */
QSplitter::handle {{
    background-color: {surf0};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}

/* =========================================================
   Line Edit
   ========================================================= */
QLineEdit {{
    background-color: {surf0};
    border: 1px solid {surf1};
    border-radius: 7px;
    padding: 6px 10px;
    color: {text_main};
    selection-background-color: {primary};
    selection-color: {bg_base};
}}
QLineEdit:focus {{
    border-color: {primary};
}}
QLineEdit:disabled {{
    color: {surf2};
    background-color: {bg_mantle};
}}

/* =========================================================
   Push Button
   ========================================================= */
QPushButton {{
    background-color: {surf0};
    border: 1px solid {surf1};
    border-radius: 7px;
    padding: 6px 16px;
    color: {text_main};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {surf1};
    border-color: {surf2};
}}
QPushButton:pressed {{
    background-color: {bg_mantle};
}}
QPushButton:disabled {{
    color: {surf2};
    border-color: {surf0};
    background-color: {bg_mantle};
}}

QPushButton#btn_primary {{
    background-color: {primary};
    color: {bg_base};
    border: none;
    font-weight: 600;
}}
QPushButton#btn_primary:hover {{
    background-color: {primary_hover};
}}
QPushButton#btn_primary:pressed {{
    background-color: {primary_press};
}}

QPushButton#btn_danger {{
    background-color: {danger};
    color: {bg_base};
    border: none;
    font-weight: 600;
}}
QPushButton#btn_danger:hover {{
    background-color: {danger_hover};
}}
QPushButton#btn_danger:pressed {{
    background-color: {danger_press};
}}
QPushButton#btn_danger:disabled {{
    background-color: {surf2};
    color: {bg_base};
}}

QPushButton#btn_monitor_on {{
    background-color: {success};
    color: {bg_base};
    border: none;
    font-weight: 600;
}}
QPushButton#btn_monitor_on:hover {{
    background-color: {success_hover};
}}

QPushButton#btn_monitor_off {{
    background-color: {surf0};
    color: {success};
    border: 1px solid {success};
    font-weight: 600;
}}
QPushButton#btn_monitor_off:hover {{
    background-color: {surf1};
}}

/* =========================================================
   List Widget  (Repo list)
   ========================================================= */
QListWidget {{
    background-color: transparent;
    border: none;
    outline: 0;
}}
QListWidget::item {{
    padding: 9px 12px;
    border-radius: 7px;
    margin: 1px 6px;
    color: {text_main};
}}
QListWidget::item:hover {{
    background-color: {surf0};
}}
QListWidget::item:selected {{
    background-color: {surf1};
    color: {primary};
}}

/* =========================================================
   Table Widget
   ========================================================= */
QTableWidget {{
    background-color: {bg_mantle};
    gridline-color: {bg_base};
    border: none;
    selection-background-color: {surf0};
    selection-color: {text_main};
    alternate-background-color: {bg_base};
}}
QTableWidget::item {{
    padding: 5px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {surf0};
}}

QHeaderView {{
    background-color: {bg_crust};
}}
QHeaderView::section {{
    background-color: {bg_crust};
    color: {text_sub};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {surf0};
    border-right: 1px solid {surf0};
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* =========================================================
   ComboBox
   ========================================================= */
QComboBox {{
    background-color: {surf0};
    border: 1px solid {surf1};
    border-radius: 7px;
    padding: 6px 10px;
    color: {text_main};
    min-width: 160px;
}}
QComboBox:hover {{
    border-color: {surf2};
}}
QComboBox:focus {{
    border-color: {primary};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {surf0};
    border: 1px solid {surf1};
    border-radius: 7px;
    selection-background-color: {surf1};
    selection-color: {text_main};
    padding: 4px;
}}

/* =========================================================
   SpinBox
   ========================================================= */
QSpinBox {{
    background-color: {surf0};
    border: 1px solid {surf1};
    border-radius: 7px;
    padding: 6px 10px;
    color: {text_main};
}}
QSpinBox:focus {{
    border-color: {primary};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 16px;
}}

/* =========================================================
   Scroll Bars
   ========================================================= */
QScrollBar:vertical {{
    background: {bg_mantle};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {surf1};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {surf2}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: {bg_mantle};
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {surf1};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {surf2}; }}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}

/* =========================================================
   Progress Bar
   ========================================================= */
QProgressBar {{
    background-color: {surf0};
    border-radius: 4px;
    border: none;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {primary};
    border-radius: 4px;
}}

/* =========================================================
   Text Edit (activity log)
   ========================================================= */
QTextEdit {{
    background-color: {bg_crust};
    border: none;
    color: {text_sub};
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
}}

/* =========================================================
   Status Bar
   ========================================================= */
QStatusBar {{
    background-color: {bg_crust};
    color: {text_muted};
    font-size: 12px;
    border-top: 1px solid {surf0};
}}
QStatusBar::item {{ border: none; }}

/* =========================================================
   Menu & Menu Bar
   ========================================================= */
QMenuBar {{
    background-color: {bg_mantle};
    color: {text_main};
    border-bottom: 1px solid {surf0};
    padding: 2px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 5px;
}}
QMenuBar::item:selected {{
    background-color: {surf0};
}}
QMenu {{
    background-color: {bg_mantle};
    border: 1px solid {surf1};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: {surf1};
}}
QMenu::separator {{
    height: 1px;
    background: {surf1};
    margin: 4px 10px;
}}

/* =========================================================
   Tooltip
   ========================================================= */
QToolTip {{
    background-color: {surf0};
    border: 1px solid {surf1};
    color: {text_main};
    padding: 5px 9px;
    border-radius: 6px;
}}

/* =========================================================
   Dialog
   ========================================================= */
QDialog {{
    background-color: {bg_base};
}}

/* =========================================================
   Label helpers (set via setObjectName)
   ========================================================= */
QLabel#panel_title {{
    font-size: 15px;
    font-weight: 700;
    color: {text_main};
    letter-spacing: 0.3px;
}}
QLabel#section_label {{
    font-size: 11px;
    font-weight: 600;
    color: {text_muted};
    letter-spacing: 1px;
}}
QLabel#user_chip {{
    background-color: {surf0};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    color: {primary};
}}

/* =========================================================
   Dynamic Status Badges (set via setProperty("status", ...))
   ========================================================= */
QLabel[status="success"] {{
    background-color: {st_success_bg};
    color: {st_success_fg};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="failure"] {{
    background-color: {st_failure_bg};
    color: {st_failure_fg};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="cancelled"] {{
    background-color: {st_cancelled_bg};
    color: {st_cancelled_fg};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="skipped"] {{
    background-color: {st_skipped_bg};
    color: {st_skipped_fg};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="in_progress"] {{
    background-color: {st_inprogress_bg};
    color: {st_inprogress_fg};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="queued"] {{
    background-color: {st_cancelled_bg};
    color: {text_sub};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel[status="waiting"] {{
    background-color: {st_cancelled_bg};
    color: {text_sub};
    border-radius: 5px;
    padding: 2px 8px;
    font-weight: 600;
}}

QLabel[color="muted"] {{ color: {text_muted}; }}
QLabel[color="sub"] {{ color: {text_sub}; }}
QLabel[color="primary"] {{ color: {primary}; font-weight: 600; }}
QLabel[color="success"] {{ color: {success}; }}
QLabel[color="danger"] {{ color: {danger}; }}

/* Layout widgets backgrounds */
QWidget#header_widget, QWidget#search_container, QWidget#page_bar, QWidget#toolbar {{
    background-color: {bg_mantle};
}}
QFrame#activity_frame {{
    background-color: {bg_crust};
    border-top: 1px solid {surf0};
}}
QWidget#act_header {{
    background-color: {bg_crust};
}}
"""

STATUS_ICONS: dict[str, str] = {
    "success":     "✅",
    "failure":     "❌",
    "cancelled":   "⊗",
    "skipped":     "⚠",
    "in_progress": "🔄",
    "queued":      "⏳",
    "waiting":     "⏳",
}
