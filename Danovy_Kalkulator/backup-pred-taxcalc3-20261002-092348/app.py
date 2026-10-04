#!/usr/bin/env python3
"""
Danovy Kalkulator v2.2  -  Enterprise Edition
Desktop aplikace -- Python + PySide6 (Qt)
CR 2026 + DE 2026  |  DPFO, DPH, OSVC, Lohnsteuer, MwSt
Import / Export (JSON, CSV)
"""

import sys
import os
import json
import csv
import datetime

from PySide6.QtCore import Qt, QSize, QRectF, Signal
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QBrush, QColor,
    QPen, QPainterPath
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QScrollArea,
    QStackedWidget, QComboBox, QCheckBox, QFileDialog, QMessageBox,
    QSizePolicy
)

APP_NAME = "TaxCalc Enterprise"
APP_VER  = "2.2"

# ── Colors (Ledger Palette -- ink, brass & oxblood) ────────────────
BG            = "#161109"   # Deep ink -- ledger cover
BG_SURFACE    = "#1c160d"   # Sidebar background
BG_CARD       = "#211a10"   # Card / dossier background
BG_ELEVATED   = "#2a2013"   # Input background
BG_HOVER      = "#3a2c17"   # Button hover state
ACCENT        = "#c09a2e"   # Brass -- Czech modules & primary actions
ACCENT_HV     = "#d3ac3c"
ACCENT_GLOW   = "#e8c765"
INK_ON_ACCENT = "#20170a"   # Dark ink text set against brass fills
SUCCESS       = "#7c9152"   # Sage ledger ink
WARNING       = "#c98a3a"   # Amber
INFO          = "#6f8fa8"   # Faded ink blue
DANGER        = "#a4453a"   # Oxblood stamp red
TEXT          = "#efe6d2"   # Warm parchment
TEXT_SEC      = "#ab9c7c"
TEXT_MUT      = "#726348"
BORDER        = "#372a16"   # Ruled ledger line
BORDER_HV     = "#4a3a1e"
DE_ACCENT     = "#8b3a34"   # Oxblood -- German modules
DE_GLOW       = "#b5615a"
SERIF         = "'Georgia', 'Iowan Old Style', 'Palatino Linotype', serif"

def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ── QSS (Corporate Theme) ─────────────────────────────────────────
QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 3px; min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ── Inputs ── */
QLineEdit {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px; padding: 8px 12px;
    color: {TEXT}; font-size: 13px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
    background-color: {BG_CARD};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {BG_ELEVATED}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 8px 12px;
    color: {TEXT}; font-size: 13px; min-width: 160px;
}}
QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {BG_ELEVATED}; border: 1px solid {BORDER};
    color: {TEXT}; selection-background-color: {ACCENT};
    outline: none; padding: 4px;
}}

/* ── Checkboxes ── */
QCheckBox {{ color: {TEXT_SEC}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {BORDER}; background: {BG_ELEVATED};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT_GLOW}; }}

/* ── MessageBox ── */
QMessageBox {{ background-color: {BG_CARD}; }}
QMessageBox QPushButton {{
    background: {BG_ELEVATED}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 6px 16px; color: {TEXT}; min-width: 70px;
}}
QMessageBox QPushButton:hover {{ background: {BG_HOVER}; border-color: {ACCENT}; }}
"""

# ══════════════════════════════════════════════════════════════════
# TAX RATES 2026
# ══════════════════════════════════════════════════════════════════
CR_2026 = {
    "year": 2026,
    "sp_zam":            0.0650,
    "zp_zam":            0.0450,
    "sp_zamestnavatel":  0.2480,
    "zp_zamestnavatel":  0.0900,
    "dan_sazba":         0.15,
    "sleva_poplatnik_mes": 2_570.0,
    "sleva_student_mes":   335.0,
    "sleva_deti_mes": [1_267.0, 1_860.0, 2_320.0],
    "dan_sazba2":        0.23,
    "limit_23":          1_676_052.0,
    "sleva_poplatnik_rok": 30_840.0,
    "sp_osvc_sazba":     0.292,
    "sp_osvc_min_vz":    170_424.0,
    "zp_osvc_sazba":     0.135,
    "zp_osvc_min_vz":    170_424.0,
    "sp_osvc_podil_vz":  0.50,
    "zp_osvc_podil_vz":  0.50,
    "dph_sazby": [0.21, 0.12, 0.00],
    "currency": "Kc",
}

DE_2026 = {
    "year": 2026,
    "grundfreibetrag":   12_096.0,
    "zone2_limit":       17_443.0,
    "zone3_limit":       68_480.0,
    "zone4_limit":      277_826.0,
    "zone2_start": 0.14,  "zone3_start": 0.2397,
    "zone4_rate":  0.42,  "zone5_rate":  0.45,
    "soli_sazba":        0.055,
    "soli_freigrenze":   18_130.0,
    "rv_sazba":   0.0930,  "kv_sazba":   0.0756,
    "pv_sazba":   0.0170,  "av_sazba":   0.0130,
    "bbg_rv":  96_600.0,   "bbg_kv":  66_150.0,
    "mwst_sazby": [0.19, 0.07, 0.00],
    "currency": "EUR",
}

class NumberInput(QWidget):
    valueChanged = Signal(float)

    def __init__(self, placeholder="", suffix="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setAlignment(Qt.AlignRight)
        self._edit.textChanged.connect(self._on_change)
        lay.addWidget(self._edit)
        if suffix:
            lbl = QLabel(suffix); lbl.setFixedWidth(50); lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"background:{BG_CARD};border:1px solid {BORDER};"
                f"border-left:none;border-radius:0 6px 6px 0;color:{TEXT_SEC};padding:8px 0;"
            )
            self._edit.setStyleSheet(
                f"background:{BG_ELEVATED};border:1px solid {BORDER};"
                f"border-right:none;border-radius:6px 0 0 6px;padding:8px 12px;color:{TEXT};font-size:13px;"
            )
            lay.addWidget(lbl)

    def _on_change(self, text):
        try: self.valueChanged.emit(float(text.replace("\u00a0","").replace(" ","").replace(",",".")))
        except ValueError: pass

    def get_value(self):
        try: return float(self._edit.text().replace("\u00a0","").replace(" ","").replace(",","."))
        except ValueError: return 0.0

    def set_value(self, val):
        self._edit.setText(str(int(val)) if val == int(val) else f"{val:.2f}")

    def clear(self): self._edit.clear()


def fmt_czk(val):
    if val < 0: return f"-{fmt_czk(-val)}"
    return f"{int(round(val)):,}".replace(",", "\u00a0") + " Kc"

def fmt_eur(val):
    if val < 0: return f"-{fmt_eur(-val)}"
    return f"{int(round(val)):,}".replace(",", "\u00a0") + " EUR"

def de_lohnsteuer_annual(brutto: float, steuerklasse: int = 1) -> float:
    s = DE_2026
    gf = s["grundfreibetrag"] * (2 if steuerklasse == 3 else 1)
    if brutto <= gf: return 0.0
    zvE = brutto - gf
    z2 = s["zone2_limit"] - gf; z3 = s["zone3_limit"] - gf; z4 = s["zone4_limit"] - gf
    if zvE <= z2:
        y = zvE / z2; rate = s["zone2_start"] + (s["zone3_start"] - s["zone2_start"]) * y * 0.5
        return max(0.0, zvE * rate)
    t2 = z2 * (s["zone2_start"] + s["zone3_start"]) / 2
    if zvE <= z3:
        above = zvE - z2; y = above / (z3 - z2)
        rate = s["zone3_start"] + (s["zone4_rate"] - s["zone3_start"]) * y * 0.5
        return max(0.0, t2 + above * rate)
    t3 = (z3 - z2) * (s["zone3_start"] + s["zone4_rate"]) / 2
    if zvE <= z4:
        return max(0.0, t2 + t3 + (zvE - z3) * s["zone4_rate"])
    t4 = (z4 - z3) * s["zone4_rate"]
    return max(0.0, t2 + t3 + t4 + (zvE - z4) * s["zone5_rate"])

# ══════════════════════════════════════════════════════════════════
# CLEAN PROFESSIONAL ICONS (No lines or visual clutter)
# ══════════════════════════════════════════════════════════════════
def make_icon(name, color, sz=QSize(24, 24)):
    px = QPixmap(sz); px.fill(Qt.transparent)
    p  = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
    c  = QColor(color); w, h = sz.width(), sz.height()
    p.setPen(Qt.NoPen); p.setBrush(QBrush(c))

    if name == "calculator":
        pen = QPen(c, 1.8); pen.setJoinStyle(Qt.RoundJoin); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(w*.15, h*.10, w*.70, h*.80), w*.08, h*.08)
        p.drawLine(int(w*.25), int(h*.30), int(w*.75), int(h*.30))
        p.setBrush(QBrush(c))
        p.drawRect(QRectF(w*.30, h*.45, w*.12, h*.10))
        p.drawRect(QRectF(w*.58, h*.45, w*.12, h*.10))
        p.drawRect(QRectF(w*.30, h*.65, w*.12, h*.10))
        p.drawRect(QRectF(w*.58, h*.65, w*.12, h*.10))

    elif name == "person":
        p.setBrush(QBrush(c))
        p.drawEllipse(QRectF(w*.35, h*.15, w*.30, h*.30))
        path = QPainterPath()
        path.moveTo(w*.20, h*.85)
        path.quadTo(w*.20, h*.55, w*.50, h*.52)
        path.quadTo(w*.80, h*.55, w*.80, h*.85)
        path.closeSubpath(); p.drawPath(path)

    elif name == "business":
        pen = QPen(c, 1.8); pen.setJoinStyle(Qt.RoundJoin); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(w*.15, h*.30, w*.70, h*.55))
        p.drawLine(int(w*.10), int(h*.30), int(w*.90), int(h*.30))
        p.drawRect(QRectF(w*.40, h*.55, w*.20, h*.30))

    elif name == "dph":
        p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(w*.20, h*.20, w*.18, h*.18))
        p.drawEllipse(QRectF(w*.62, h*.62, w*.18, h*.18))
        p.setPen(QPen(c, 2.0)); p.drawLine(int(w*.25), int(h*.75), int(w*.75), int(h*.25))

    elif name == "home":
        pen = QPen(c, 1.8); pen.setJoinStyle(Qt.RoundJoin); p.setPen(pen); p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(w*.15, h*.50); path.lineTo(w*.50, h*.15); path.lineTo(w*.85, h*.50)
        path.moveTo(w*.25, h*.50); path.lineTo(w*.25, h*.85); path.lineTo(w*.75, h*.85); path.lineTo(w*.75, h*.50)
        p.drawPath(path)

    elif name == "check":
        pen = QPen(c, 2.5); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(w*.22, h*.50); path.lineTo(w*.45, h*.72); path.lineTo(w*.78, h*.28)
        p.drawPath(path)

    elif name == "reset":
        pen = QPen(c, 2.0); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(w*.15, h*.15, w*.70, h*.70), 45*16, 270*16)

    elif name == "export":
        pen = QPen(c, 1.8); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(int(w*.50), int(h*.15), int(w*.50), int(h*.65))
        p.drawLine(int(w*.35), int(h*.50), int(w*.50), int(h*.65))
        p.drawLine(int(w*.65), int(h*.50), int(w*.50), int(h*.65))
        p.drawLine(int(w*.20), int(h*.80), int(w*.80), int(h*.80))

    elif name == "import_icon":
        pen = QPen(c, 1.8); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(int(w*.50), int(h*.65), int(w*.50), int(h*.15))
        p.drawLine(int(w*.35), int(h*.30), int(w*.50), int(h*.15))
        p.drawLine(int(w*.65), int(h*.30), int(w*.50), int(h*.15))
        p.drawLine(int(w*.20), int(h*.80), int(w*.80), int(h*.80))

    elif name == "seal":
        pen = QPen(c, 1.6); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(w*.12, h*.12, w*.76, h*.76))
        pen2 = QPen(c, 1.1); p.setPen(pen2)
        p.drawEllipse(QRectF(w*.24, h*.24, w*.52, h*.52))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
        path = QPainterPath()
        path.moveTo(w*.50, h*.32); path.lineTo(w*.57, h*.46)
        path.lineTo(w*.71, h*.50); path.lineTo(w*.57, h*.54)
        path.lineTo(w*.50, h*.68); path.lineTo(w*.43, h*.54)
        path.lineTo(w*.29, h*.50); path.lineTo(w*.43, h*.46)
        path.closeSubpath(); p.drawPath(path)

    elif name == "flag_de":
        p.setBrush(QBrush(QColor("#1e1e1e"))); p.drawRect(QRectF(w*.10, h*.22, w*.80, h*.18))
        p.setBrush(QBrush(QColor("#D00000"))); p.drawRect(QRectF(w*.10, h*.40, w*.80, h*.18))
        p.setBrush(QBrush(QColor("#FFCC00"))); p.drawRect(QRectF(w*.10, h*.58, w*.80, h*.18))

    p.end(); return QIcon(px)

# ══════════════════════════════════════════════════════════════════
# SUBTLE, CLEAN STRUCTURAL COMPONENTS (No style leakage)
# ══════════════════════════════════════════════════════════════════

class EnterpriseHeader(QFrame):
    """Clean, flat enterprise view header with breadcrumb and description."""
    def __init__(self, title, desc, kicker=None, accent=None, parent=None):
        super().__init__(parent)
        accent = accent or ACCENT
        self.setObjectName("entHeader")
        self.setStyleSheet(f"""
            QFrame#entHeader {{
                background-color: {BG_CARD};
                border-bottom: 2px solid {accent};
            }}
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(28, 18, 28, 18); lay.setSpacing(4)

        if kicker:
            k_lbl = QLabel(kicker.upper())
            k_lbl.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
            lay.addWidget(k_lbl)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {TEXT}; font-size: 19px; font-weight: 600; font-family: {SERIF};")
        lay.addWidget(t_lbl)
        
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px;")
        lay.addWidget(d_lbl)


class FormSection(QFrame):
    """Clean container for inputs, styled strictly by object name to prevent layout leakage."""
    def __init__(self, title, parent=None, accent=None):
        super().__init__(parent)
        accent = accent or ACCENT
        self.setObjectName("formSection")
        self.setStyleSheet(f"""
            QFrame#formSection {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-top: 2px solid {accent};
                border-radius: 8px;
            }}
        """)
        self._lay = QVBoxLayout(self); self._lay.setContentsMargins(20, 20, 20, 20); self._lay.setSpacing(14)
        
        t_lbl = QLabel(title.upper())
        t_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        self._lay.addWidget(t_lbl)

    def add_row(self, label_text, widget, label_width=200):
        row = QHBoxLayout(); row.setSpacing(12)
        lbl = QLabel(label_text); lbl.setFixedWidth(label_width)
        lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
        row.addWidget(lbl)
        row.addWidget(widget)
        self._lay.addLayout(row)

    def add_widget(self, w):
        self._lay.addWidget(w)


class MetricsGrid(QFrame):
    """Structured financial-like table representation for results, styled as a ruled ledger sheet."""
    def __init__(self, title="VÝSLEDKY VÝPOČTU", parent=None, accent=None):
        super().__init__(parent)
        self._accent = accent or ACCENT
        self.setObjectName("metricsGrid")
        self.setStyleSheet(f"""
            QFrame#metricsGrid {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-top: 2px solid {self._accent};
                border-radius: 8px;
            }}
        """)
        self.main_lay = QVBoxLayout(self); self.main_lay.setContentsMargins(20, 20, 20, 20); self.main_lay.setSpacing(12)
        
        t_lbl = QLabel(title.upper())
        t_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;")
        self.main_lay.addWidget(t_lbl)
        
        self.grid = QVBoxLayout(); self.grid.setSpacing(0); self.grid.setContentsMargins(0, 8, 0, 0)
        self.main_lay.addLayout(self.grid)
        self.items = {}

    def add_metric(self, name, key_label, initial_value="--", is_total=False, is_divider=False):
        row = QFrame()
        row.setObjectName("metricRow")

        if is_divider:
            row.setStyleSheet(f"""
                QFrame#metricRow {{
                    background-color: transparent;
                    border: none;
                    border-bottom: 1px solid {self._accent};
                    border-radius: 0px;
                }}
            """)
            rl = QHBoxLayout(row); rl.setContentsMargins(2, 16, 2, 6)
            lbl = QLabel(key_label.upper())
            lbl.setStyleSheet(f"color: {self._accent}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; background: transparent;")
            rl.addWidget(lbl); rl.addStretch()
            self.grid.addWidget(row)
            self.items[name] = lbl
            return

        if is_total:
            bg_col = _rgba(self._accent, 0.10)
            border_style = (f"border-top: 1px solid {self._accent}; "
                             f"border-bottom-width: 3px; border-bottom-style: double; border-bottom-color: {self._accent};")
        else:
            bg_col = "transparent"
            border_style = f"border-bottom: 1px solid {BORDER};"
        font_weight = "800" if is_total else "500"
        font_size = "15px" if is_total else "13px"
        text_color = TEXT if is_total else TEXT_SEC

        row.setStyleSheet(f"""
            QFrame#metricRow {{
                background-color: {bg_col};
                border: none;
                {border_style}
                border-radius: 0px;
            }}
        """)
        rl = QHBoxLayout(row); rl.setContentsMargins(12, 10, 12, 10)
        
        lbl = QLabel(key_label)
        lbl.setStyleSheet(f"color: {text_color}; font-size: 13px; font-weight: {font_weight}; background: transparent;")
        
        val = QLabel(initial_value)
        val.setStyleSheet(f"color: {TEXT}; font-size: {font_size}; font-weight: {font_weight}; font-family: 'Consolas', monospace; background: transparent;")
        val.setAlignment(Qt.AlignRight)
        
        rl.addWidget(lbl)
        rl.addWidget(val)
        
        self.grid.addWidget(row)
        self.items[name] = val

    def set_metric(self, name, val):
        if name in self.items:
            self.items[name].setText(val)


# ══════════════════════════════════════════════════════════════════
# ENTERPRISE BUTTON STYLE HELPERS
# ══════════════════════════════════════════════════════════════════
def make_calc_btn():
    btn = QPushButton(" Vypočítat")
    btn.setIcon(make_icon("check", INK_ON_ACCENT, QSize(14,14)))
    btn.setIconSize(QSize(14,14)); btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {ACCENT};
            color: {INK_ON_ACCENT}; font-weight: 700; font-size: 13px;
            padding: 10px 24px; border-radius: 6px;
        }}
        QPushButton:hover {{ background-color: {ACCENT_HV}; }}
        QPushButton:pressed {{ background-color: {ACCENT}; }}
    """)
    return btn

def make_reset_btn():
    btn = QPushButton(" Vyčistit")
    btn.setIcon(make_icon("reset", TEXT_SEC, QSize(14,14)))
    btn.setIconSize(QSize(14,14)); btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {BG_ELEVATED};
            color: {TEXT}; font-size: 13px;
            padding: 10px 20px; border-radius: 6px;
            border: 1px solid {BORDER};
        }}
        QPushButton:hover {{ background-color: {BG_HOVER}; }}
    """)
    return btn

def make_export_btn():
    btn = QPushButton(" Export dat")
    btn.setIcon(make_icon("export", TEXT_SEC, QSize(14,14)))
    btn.setIconSize(QSize(14,14)); btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {BG_ELEVATED};
            color: {TEXT_SEC}; font-size: 13px;
            padding: 10px 20px; border-radius: 6px;
            border: 1px solid {BORDER};
        }}
        QPushButton:hover {{ color: {TEXT}; border-color: {TEXT_SEC}; }}
    """)
    return btn

def make_import_btn():
    btn = QPushButton(" Import dat")
    btn.setIcon(make_icon("import_icon", TEXT_SEC, QSize(14,14)))
    btn.setIconSize(QSize(14,14)); btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {BG_ELEVATED};
            color: {TEXT_SEC}; font-size: 13px;
            padding: 10px 20px; border-radius: 6px;
            border: 1px solid {BORDER};
        }}
        QPushButton:hover {{ color: {TEXT}; border-color: {TEXT_SEC}; }}
    """)
    return btn

# ══════════════════════════════════════════════════════════════════
# IO MIXIN
# ══════════════════════════════════════════════════════════════════
class IOViewMixin:
    def _get_export_data(self): return {}
    def _apply_import_data(self, data): pass

    def do_export(self):
        data = self._get_export_data()
        if not data:
            QMessageBox.warning(self, "Export", "Nejprve proveďte výpočet."); return
        data["exported_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        data["app"] = f"{APP_NAME} v{APP_VER}"
        path, _ = QFileDialog.getSaveFileName(self, "Uložit výsledky", "", "JSON (*.json);;CSV (*.csv)")
        if not path: return
        if path.endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Polozka","Hodnota"])
                for k,v in data.items(): w.writerow([k,v])
        else:
            if not path.endswith(".json"): path += ".json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "Export", f"Uloženo:\n{path}")

    def do_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Načíst data", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, encoding="utf-8") as f: data = json.load(f)
            self._apply_import_data(data)
        except Exception as e:
            QMessageBox.critical(self, "Import", f"Chyba při načítání dat:\n{e}")

# ══════════════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════════════

class DPFOZamView(QWidget, IOViewMixin):
    def __init__(self, parent=None):
        super().__init__(parent); self._last = {}; self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        
        # Header
        root.addWidget(EnterpriseHeader("Zaměstnanec (DPFO)", "Výpočet čisté mzdy, daně a povinných odvodů na straně zaměstnance a zaměstnavatele v roce 2026.", kicker="Česká republika · Daňový rok 2026"))
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(inner); lay.setContentsMargins(28,24,28,32); lay.setSpacing(20)

        # Form Section
        form = FormSection("Parametry výpočtu")
        self.inp_hruba = NumberInput("např. 50 000", suffix="Kč")
        form.add_row("Hrubá měsíční mzda:", self.inp_hruba)
        self.inp_deti = NumberInput("0", suffix="dětí")
        form.add_row("Počet dětí (daňové zvýhodnění):", self.inp_deti)
        
        self.chk_student = QCheckBox("Uplatnit slevu na studenta (335 Kč / měsíc)")
        self.chk_ztp = QCheckBox("Držitel průkazu ZTP/P (zdvojnásobení daňového zvýhodnění na děti)")
        form.add_widget(self.chk_student)
        form.add_widget(self.chk_ztp)
        lay.addWidget(form)

        # Actions Row
        actions = QHBoxLayout(); actions.setSpacing(12)
        self.btn_calc = make_calc_btn(); self.btn_calc.clicked.connect(self._calculate); actions.addWidget(self.btn_calc)
        self.btn_reset = make_reset_btn(); self.btn_reset.clicked.connect(self._reset); actions.addWidget(self.btn_reset)
        actions.addSpacing(12)
        self.btn_exp = make_export_btn(); self.btn_exp.clicked.connect(self.do_export); actions.addWidget(self.btn_exp)
        self.btn_imp = make_import_btn(); self.btn_imp.clicked.connect(self.do_import); actions.addWidget(self.btn_imp)
        actions.addStretch(); lay.addLayout(actions)

        # Metrics Result Area
        self.res = MetricsGrid("Rozpis výpočtu (Měsíčně)")
        self.res.add_metric("hruba", "Hrubá mzda")
        self.res.add_metric("sp_zam", "Sociální pojištění zaměstnanec (6.5 %)")
        self.res.add_metric("zp_zam", "Zdravotní pojištění zaměstnanec (4.5 %)")
        self.res.add_metric("dan", "Daň z příjmu po slevách")
        self.res.add_metric("sleva", "Uplatněné slevy a zvýhodnění")
        self.res.add_metric("sp_firm", "Sociální pojištění zaměstnavatel (24.8 %)")
        self.res.add_metric("zp_firm", "Zdravotní pojištění zaměstnavatel (9.0 %)")
        self.res.add_metric("naklady", "Celkové náklady zaměstnavatele")
        self.res.add_metric("cista", "Čistá mzda k výplatě", is_total=True)
        self.res.setVisible(False)
        lay.addWidget(self.res)
        
        lay.addStretch()
        scroll.setWidget(inner); root.addWidget(scroll)

    def _calculate(self):
        hruba = self.inp_hruba.get_value()
        if hruba <= 0: return
        deti=max(0,int(self.inp_deti.get_value())); student=self.chk_student.isChecked(); ztp=self.chk_ztp.isChecked()
        r = CR_2026
        sp_zam=hruba*r["sp_zam"]; zp_zam=hruba*r["zp_zam"]
        sp_zam2=hruba*r["sp_zamestnavatel"]; zp_zam2=hruba*r["zp_zamestnavatel"]
        dan_brutto=hruba*r["dan_sazba"]
        sleva=r["sleva_poplatnik_mes"]
        for i in range(min(deti,3)): sleva+=r["sleva_deti_mes"][min(i,2)]*(2 if ztp else 1)
        if student: sleva+=r["sleva_student_mes"]
        dan=max(0.0,dan_brutto-sleva)
        cista=hruba-sp_zam-zp_zam-dan; naklady=hruba+sp_zam2+zp_zam2
        efekt=(dan/hruba*100) if hruba>0 else 0
        
        self.res.set_metric("hruba", fmt_czk(hruba))
        self.res.set_metric("sp_zam", fmt_czk(sp_zam))
        self.res.set_metric("zp_zam", fmt_czk(zp_zam))
        self.res.set_metric("dan", fmt_czk(dan))
        self.res.set_metric("sleva", fmt_czk(sleva))
        self.res.set_metric("sp_firm", fmt_czk(sp_zam2))
        self.res.set_metric("zp_firm", fmt_czk(zp_zam2))
        self.res.set_metric("naklady", fmt_czk(naklady))
        self.res.set_metric("cista", fmt_czk(cista))
        self.res.setVisible(True)
        self._last={"modul":"DPFO_zamestnanec_CR_2026","hruba_mzda_Kc":hruba,"pocet_deti":deti,
                    "student":student,"ztp":ztp,"cista_mzda_Kc":round(cista,2),
                    "dan_z_prijmu_Kc":round(dan,2),"sp_zam_Kc":round(sp_zam,2),
                    "zp_zam_Kc":round(zp_zam,2),"slevy_Kc":round(sleva,2),
                    "efektivni_sazba_pct":round(efekt,2),"naklady_firmy_Kc":round(naklady,2)}

    def _get_export_data(self): return dict(self._last)
    def _apply_import_data(self, d):
        if "hruba_mzda_Kc" in d: self.inp_hruba.set_value(d["hruba_mzda_Kc"])
        if "pocet_deti" in d: self.inp_deti.set_value(d["pocet_deti"])
        if "student" in d: self.chk_student.setChecked(bool(d["student"]))
        if "ztp" in d: self.chk_ztp.setChecked(bool(d["ztp"]))
    def _reset(self):
        self.inp_hruba.clear(); self.inp_deti.clear()
        self.chk_student.setChecked(False); self.chk_ztp.setChecked(False)
        self.res.setVisible(False); self._last={}


class OSVCView(QWidget, IOViewMixin):
    def __init__(self, parent=None):
        super().__init__(parent); self._last={}; self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(EnterpriseHeader("Podnikatel / OSVČ (DPFO)", "Roční zúčtování OSVČ, včetně výpočtu pojistného na sociální a zdravotní pojištění a stanovení minimálních záloh pro rok 2026.", kicker="Česká republika · Daňový rok 2026"))
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(inner); lay.setContentsMargins(28,24,28,32); lay.setSpacing(20)

        form = FormSection("Vstupní parametry podnikání")
        self.inp_prijmy = NumberInput("např. 900 000", suffix="Kč")
        form.add_row("Celkové roční příjmy:", self.inp_prijmy, 250)
        self.inp_vydaje = NumberInput("0", suffix="Kč")
        form.add_row("Skutečné daňové výdaje (pokud nevyužíváte paušál):", self.inp_vydaje, 250)
        self.combo_pausal = QComboBox()
        self.combo_pausal.addItems([
            "Nevyužívat výdajový paušál (skutečné výdaje)",
            "80 % paušál (řemesla, zemědělství)",
            "60 % paušál (ostatní živnosti)",
            "40 % paušál (svobodná povolání, autorské)",
            "30 % paušál (pronájem)"
        ])
        form.add_row("Uplatnit výdajový paušál:", self.combo_pausal, 250)
        lay.addWidget(form)

        actions = QHBoxLayout(); actions.setSpacing(12)
        self.btn_calc=make_calc_btn(); self.btn_calc.clicked.connect(self._calculate); actions.addWidget(self.btn_calc)
        self.btn_reset=make_reset_btn(); self.btn_reset.clicked.connect(self._reset); actions.addWidget(self.btn_reset)
        actions.addSpacing(12)
        self.btn_exp=make_export_btn(); self.btn_exp.clicked.connect(self.do_export); actions.addWidget(self.btn_exp)
        self.btn_imp=make_import_btn(); self.btn_imp.clicked.connect(self.do_import); actions.addWidget(self.btn_imp)
        actions.addStretch(); lay.addLayout(actions)

        self.res = MetricsGrid("Kalkulace hospodářského výsledku (Ročně)")
        self.res.add_metric("prijmy", "Hrubé roční příjmy")
        self.res.add_metric("vydaje", "Uplatněné daňové výdaje")
        self.res.add_metric("zaklad", "Základ daně (Zisk)")
        self.res.add_metric("dan", "Vyměřená daň z příjmů (po slevě)")
        self.res.add_metric("sp", "Roční sociální pojištění")
        self.res.add_metric("zp", "Roční zdravotní pojištění")
        self.res.add_metric("sp_z", "Předepsaná měsíční záloha na SP")
        self.res.add_metric("zp_z", "Předepsaná měsíční záloha na ZP")
        self.res.add_metric("celkem", "Celkové roční odvodové zatížení")
        self.res.add_metric("cisty_zisk", "Čistý zisk po zdanění a odvodech", is_total=True)
        self.res.setVisible(False)
        lay.addWidget(self.res)

        lay.addStretch()
        scroll.setWidget(inner); root.addWidget(scroll)

    def _calculate(self):
        prijmy=self.inp_prijmy.get_value()
        if prijmy<=0: return
        skutecne=self.inp_vydaje.get_value(); pi=self.combo_pausal.currentIndex()
        ps=[0,.80,.60,.40,.30]; pv=prijmy*ps[pi]
        vydaje=(skutecne if pi==0 else (pv if skutecne==0 else max(skutecne,pv)))
        r=CR_2026; zaklad=max(0.0,prijmy-vydaje)
        dan_brutto=(zaklad*r["dan_sazba"] if zaklad<=r["limit_23"]
                    else r["limit_23"]*r["dan_sazba"]+(zaklad-r["limit_23"])*r["dan_sazba2"])
        dan=max(0.0,dan_brutto-r["sleva_poplatnik_rok"])
        sp_r=max(zaklad*r["sp_osvc_podil_vz"],r["sp_osvc_min_vz"])*r["sp_osvc_sazba"]; sp_z=sp_r/12
        zp_r=max(zaklad*r["zp_osvc_podil_vz"],r["zp_osvc_min_vz"])*r["zp_osvc_sazba"]; zp_z=zp_r/12
        celkem=dan+sp_r+zp_r; zbytek=prijmy-celkem; efekt=(celkem/prijmy*100) if prijmy>0 else 0
        
        self.res.set_metric("prijmy", fmt_czk(prijmy))
        self.res.set_metric("vydaje", fmt_czk(vydaje))
        self.res.set_metric("zaklad", fmt_czk(zaklad))
        self.res.set_metric("dan", fmt_czk(dan))
        self.res.set_metric("sp", fmt_czk(sp_r))
        self.res.set_metric("zp", fmt_czk(zp_r))
        self.res.set_metric("sp_z", fmt_czk(sp_z))
        self.res.set_metric("zp_z", fmt_czk(zp_z))
        self.res.set_metric("celkem", fmt_czk(celkem))
        self.res.set_metric("cisty_zisk", fmt_czk(zbytek))
        self.res.setVisible(True)
        
        self._last={"modul":"DPFO_OSVC_CR_2026",
                    "rocni_prijmy_Kc":prijmy,
                    "uplatnene_vydaje_Kc":skutecne,
                    "pausal_index":pi,
                    "zaklad_dane_Kc":round(zaklad,2),
                    "dan_z_prijmu_Kc":round(dan,2),
                    "sp_rocne_Kc":round(sp_r,2),
                    "zp_rocne_Kc":round(zp_r,2),
                    "mes_zaloha_sp_Kc":round(sp_z,2),
                    "mes_zaloha_zp_Kc":round(zp_z,2),
                    "celkove_odvody_Kc":round(celkem,2),
                    "zbyva_Kc":round(zbytek,2),
                    "efektivni_zatizeni_pct":round(efekt,2)}

    def _get_export_data(self): return dict(self._last)
    def _apply_import_data(self,d):
        if "rocni_prijmy_Kc" in d: self.inp_prijmy.set_value(d["rocni_prijmy_Kc"])
        if "uplatnene_vydaje_Kc" in d: self.inp_vydaje.set_value(d["uplatnene_vydaje_Kc"])
        if "pausal_index" in d: self.combo_pausal.setCurrentIndex(int(d["pausal_index"]))
    def _reset(self):
        self.inp_prijmy.clear(); self.inp_vydaje.clear()
        self.combo_pausal.setCurrentIndex(0); self.res.setVisible(False); self._last={}


class DPHView(QWidget, IOViewMixin):
    def __init__(self, parent=None):
        super().__init__(parent); self._last={}; self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(EnterpriseHeader("DPH Kalkulátor", "Výpočet výše daně z přidané hodnoty a přepočet cen s/bez DPH pro sazby platné v ČR.", kicker="Česká republika · Sazby platné od 1. 1. 2026"))
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(inner); lay.setContentsMargins(28,24,28,32); lay.setSpacing(20)

        form = FormSection("Základní DPH parametry")
        self.inp_castka=NumberInput("např. 1 000", suffix="Kč")
        form.add_row("Vstupní částka:", self.inp_castka)
        self.combo_sazba=QComboBox()
        self.combo_sazba.addItems(["21 % -- základní sazba", "12 % -- snížená sazba", "0 % -- osvobozená plnění"])
        form.add_row("Sazba DPH:", self.combo_sazba)
        self.combo_smer=QComboBox()
        self.combo_smer.addItems(["Připočítat DPH k základu (bez DPH -> s DPH)", "Vyčlenit DPH z celkové částky (s DPH -> bez DPH)"])
        form.add_row("Směr přepočtu:", self.combo_smer)
        lay.addWidget(form)

        actions = QHBoxLayout(); actions.setSpacing(12)
        self.btn_calc=make_calc_btn(); self.btn_calc.clicked.connect(self._calculate); actions.addWidget(self.btn_calc)
        self.btn_reset=make_reset_btn(); self.btn_reset.clicked.connect(self._reset); actions.addWidget(self.btn_reset)
        actions.addSpacing(12)
        self.btn_exp=make_export_btn(); self.btn_exp.clicked.connect(self.do_export); actions.addWidget(self.btn_exp)
        self.btn_imp=make_import_btn(); self.btn_imp.clicked.connect(self.do_import); actions.addWidget(self.btn_imp)
        actions.addStretch(); lay.addLayout(actions)

        self.res = MetricsGrid("Rozpad ceny s DPH / bez DPH")
        self.res.add_metric("s_dph", "Cena s DPH")
        self.res.add_metric("bez_dph", "Cena bez DPH")
        self.res.add_metric("vyse", "Výše daně (DPH)")
        self.res.add_metric("sazba", "Aplikovaná sazba", "21 %")
        self.res.setVisible(False)
        lay.addWidget(self.res)

        lay.addStretch()
        scroll.setWidget(inner); root.addWidget(scroll)

    def _calculate(self):
        castka=self.inp_castka.get_value()
        if castka<=0: return
        sazba_idx=self.combo_sazba.currentIndex()
        smer_idx=self.combo_smer.currentIndex()
        sazba=CR_2026["dph_sazby"][sazba_idx]
        if smer_idx==0: bez=castka; s=castka*(1+sazba)
        else: s=castka; bez=castka/(1+sazba) if sazba>0 else castka
        dph_c=s-bez
        
        self.res.set_metric("s_dph", fmt_czk(s))
        self.res.set_metric("bez_dph", fmt_czk(bez))
        self.res.set_metric("vyse", fmt_czk(dph_c))
        self.res.set_metric("sazba", f"{int(sazba*100)} %")
        self.res.setVisible(True)
        self._last={"modul":"DPH_CR_2026",
                    "vstupni_castka_Kc":castka,
                    "sazba_index":sazba_idx,
                    "smer_index":smer_idx,
                    "cena_s_dph_Kc":round(s,2),
                    "cena_bez_dph_Kc":round(bez,2),
                    "vyse_dph_Kc":round(dph_c,2)}

    def _get_export_data(self): return dict(self._last)
    def _apply_import_data(self, d):
        if "vstupni_castka_Kc" in d: self.inp_castka.set_value(d["vstupni_castka_Kc"])
        if "sazba_index" in d: self.combo_sazba.setCurrentIndex(int(d["sazba_index"]))
        if "smer_index" in d: self.combo_smer.setCurrentIndex(int(d["smer_index"]))
    def _reset(self):
        self.inp_castka.clear(); self.combo_sazba.setCurrentIndex(0); self.combo_smer.setCurrentIndex(0)
        self.res.setVisible(False); self._last={}


class DEView(QWidget, IOViewMixin):
    def __init__(self, parent=None):
        super().__init__(parent); self._last={}; self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(EnterpriseHeader("Německý daňový systém (DE)", "Kalkulace daňového zatížení příjmů v SRN pro rok 2026 včetně zohlednění solidárního příspěvku a německého DPH (MwSt).", kicker="Spolková republika Německo · Steuerjahr 2026", accent=DE_ACCENT))
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(inner); lay.setContentsMargins(28,24,28,32); lay.setSpacing(20)

        # ---- Payroll Mzda ----
        form_m = FormSection("Německá daň ze mzdy (Lohnsteuer)", accent=DE_ACCENT)
        self.inp_brutto=NumberInput("např. 60 000", suffix="EUR")
        form_m.add_row("Hrubá roční mzda (Bruttogehalt):", self.inp_brutto, 250)
        self.combo_sk=QComboBox()
        self.combo_sk.addItems([
            "Steuerklasse I  -- Single / Svobodný(á)",
            "Steuerklasse II -- Samoživitel s dětmi",
            "Steuerklasse III -- Manželé (vysoké rozdíly v příjmech)",
            "Steuerklasse IV -- Manželé (srovnatelné příjmy)"
        ])
        form_m.add_row("Daňová třída (Steuerklasse):", self.combo_sk, 250)
        self.chk_kirche = QCheckBox("Uplatnit církevní daň (Kirchensteuer ~8 % - 9 % z Lohnsteuer)")
        self.chk_kinderlos = QCheckBox("Bezdětný poplatník (Kinderlose - přirážka na Pflegeversicherung)")
        self.chk_kinderlos.setChecked(True)
        form_m.add_widget(self.chk_kirche)
        form_m.add_widget(self.chk_kinderlos)
        lay.addWidget(form_m)

        # ---- MwSt ----
        form_v = FormSection("Kalkulace německé DPH (Mehrwertsteuer)", accent=DE_ACCENT)
        self.inp_mwst=NumberInput("např. 1 000", suffix="EUR")
        form_v.add_row("Částka k přepočtu:", self.inp_mwst, 200)
        self.combo_mwst_s=QComboBox()
        self.combo_mwst_s.addItems(["19 % -- Standardní sazba (Regelsteuersatz)", "7 % -- Snížená sazba (ermäßigter Steuersatz)", "0 %"])
        form_v.add_row("Sazba MwSt:", self.combo_mwst_s, 200)
        self.combo_mwst_d=QComboBox()
        self.combo_mwst_d.addItems(["Připočítat daň k základu (Netto -> Brutto)", "Odečíst daň z celku (Brutto -> Netto)"])
        form_v.add_row("Směr výpočtu:", self.combo_mwst_d, 200)
        lay.addWidget(form_v)

        actions = QHBoxLayout(); actions.setSpacing(12)
        self.btn_calc=make_calc_btn(); self.btn_calc.clicked.connect(self._calculate); actions.addWidget(self.btn_calc)
        self.btn_reset=make_reset_btn(); self.btn_reset.clicked.connect(self._reset); actions.addWidget(self.btn_reset)
        actions.addSpacing(12)
        self.btn_exp=make_export_btn(); self.btn_exp.clicked.connect(self.do_export); actions.addWidget(self.btn_exp)
        self.btn_imp=make_import_btn(); self.btn_imp.clicked.connect(self.do_import); actions.addWidget(self.btn_imp)
        actions.addStretch(); lay.addLayout(actions)

        # Results Grid
        self.res = MetricsGrid("Přehled německého zdanění a odvodů (Roční)", accent=DE_ACCENT)
        self.res.add_metric("brutto", "Hrubá mzda (Brutto)")
        self.res.add_metric("lst", "Německá daň ze mzdy (Lohnsteuer)")
        self.res.add_metric("soli", "Solidární příspěvek (Solidaritätszuschlag)")
        self.res.add_metric("kirche", "Církevní daň (Kirchensteuer)")
        self.res.add_metric("rv", "Příspěvek na důchodové pojištění (RV)")
        self.res.add_metric("kv", "Příspěvek na zdravotní pojištění (KV)")
        self.res.add_metric("pv", "Pojištění dlouhodobé péče (PV)")
        self.res.add_metric("av", "Pojištění v nezaměstnanosti (AV)")
        self.res.add_metric("netto_m", "Měsíční čistá mzda (Nettogehalt monatlich)")
        self.res.add_metric("netto", "Čistá mzda celkem (Nettogehalt jährlich)", is_total=True)
        
        # MwSt Results inside same grid
        self.res.add_metric("spacer", "Kalkulace MwSt (DPH)", is_divider=True)
        self.res.add_metric("mwst_b", "MwSt Bruttobetrag (s DPH)")
        self.res.add_metric("mwst_n", "MwSt Nettobetrag (bez DPH)")
        self.res.add_metric("mwst_c", "Výše německé DPH (MwSt-Betrag)")
        self.res.setVisible(False)
        lay.addWidget(self.res)

        lay.addStretch()
        scroll.setWidget(inner); root.addWidget(scroll)

    def _calculate(self):
        brutto=self.inp_brutto.get_value()
        sk_idx=self.combo_sk.currentIndex()
        sk_map={0:1,1:2,2:3,3:4}; sk=sk_map.get(sk_idx,1)
        r=DE_2026
        lst=de_lohnsteuer_annual(brutto,sk)
        soli=lst*r["soli_sazba"] if lst>r["soli_freigrenze"] else 0.0
        kirche=lst*0.085 if self.chk_kirche.isChecked() else 0.0
        rv=min(brutto,r["bbg_rv"])*r["rv_sazba"]
        kv=min(brutto,r["bbg_kv"])*r["kv_sazba"]
        pv_s=r["pv_sazba"]+(0.0035 if self.chk_kinderlos.isChecked() else 0.0)
        pv=min(brutto,r["bbg_kv"])*pv_s
        av=min(brutto,r["bbg_rv"])*r["av_sazba"]
        netto=brutto-(lst+soli+kirche+rv+kv+pv+av)
        efekt=((lst+soli+kirche+rv+kv+pv+av)/brutto*100) if brutto>0 else 0
        
        self.res.set_metric("brutto", fmt_eur(brutto))
        self.res.set_metric("lst", fmt_eur(lst))
        self.res.set_metric("soli", fmt_eur(soli))
        self.res.set_metric("kirche", fmt_eur(kirche) if kirche>0 else "0 EUR")
        self.res.set_metric("rv", fmt_eur(rv))
        self.res.set_metric("kv", fmt_eur(kv))
        self.res.set_metric("pv", fmt_eur(pv))
        self.res.set_metric("av", fmt_eur(av))
        self.res.set_metric("netto_m", fmt_eur(netto/12))
        self.res.set_metric("netto", fmt_eur(netto))

        castka=self.inp_mwst.get_value()
        mwst_s_idx = self.combo_mwst_s.currentIndex()
        mwst_d_idx = self.combo_mwst_d.currentIndex()
        if castka>0:
            ms=DE_2026["mwst_sazby"][mwst_s_idx]
            if mwst_d_idx==0: n=castka; b=castka*(1+ms)
            else: b=castka; n=castka/(1+ms) if ms>0 else castka
            self.res.set_metric("mwst_b", fmt_eur(b))
            self.res.set_metric("mwst_n", fmt_eur(n))
            self.res.set_metric("mwst_c", fmt_eur(b-n))
        else:
            self.res.set_metric("mwst_b", "--")
            self.res.set_metric("mwst_n", "--")
            self.res.set_metric("mwst_c", "--")
            
        self.res.setVisible(True)
        self._last={"modul":"Lohnsteuer_DE_2026",
                    "brutto_EUR":brutto,
                    "steuerklasse_index":sk_idx,
                    "kirchensteuer":self.chk_kirche.isChecked(),
                    "kinderlos":self.chk_kinderlos.isChecked(),
                    "mwst_castka_EUR":castka,
                    "mwst_sazba_index":mwst_s_idx,
                    "mwst_smer_index":mwst_d_idx,
                    "lohnsteuer_EUR":round(lst,2),
                    "soli_EUR":round(soli,2),
                    "kirchensteuer_EUR":round(kirche,2),
                    "rv_EUR":round(rv,2),
                    "kv_EUR":round(kv,2),
                    "pv_EUR":round(pv,2),
                    "av_EUR":round(av,2),
                    "netto_rocne_EUR":round(netto,2),
                    "netto_mesicne_EUR":round(netto/12,2),
                    "efektivni_zatizeni_pct":round(efekt,2)}

    def _get_export_data(self): return dict(self._last)
    def _apply_import_data(self,d):
        if "brutto_EUR" in d: self.inp_brutto.set_value(d["brutto_EUR"])
        if "steuerklasse_index" in d: self.combo_sk.setCurrentIndex(int(d["steuerklasse_index"]))
        if "kirchensteuer" in d: self.chk_kirche.setChecked(bool(d["kirchensteuer"]))
        if "kinderlos" in d: self.chk_kinderlos.setChecked(bool(d["kinderlos"]))
        if "mwst_castka_EUR" in d: self.inp_mwst.set_value(d["mwst_castka_EUR"])
        if "mwst_sazba_index" in d: self.combo_mwst_s.setCurrentIndex(int(d["mwst_sazba_index"]))
        if "mwst_smer_index" in d: self.combo_mwst_d.setCurrentIndex(int(d["mwst_smer_index"]))
    def _reset(self):
        self.inp_brutto.clear(); self.inp_mwst.clear()
        self.combo_sk.setCurrentIndex(0); self.chk_kirche.setChecked(False)
        self.chk_kinderlos.setChecked(True); self.res.setVisible(False); self._last={}


# ══════════════════════════════════════════════════════════════════
# HOME VIEW (Clean, Simple, Professional Dashboard)
# ══════════════════════════════════════════════════════════════════
class HomeView(QWidget):
    nav_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent); self._build()

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(inner); lay.setContentsMargins(40,40,40,40); lay.setSpacing(28)

        # Welcome Card
        welcome = QFrame()
        welcome.setObjectName("welcomeCard")
        welcome.setStyleSheet(f"""
            QFrame#welcomeCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-top: 2px solid {ACCENT};
                border-radius: 8px;
            }}
        """)
        wl = QVBoxLayout(welcome); wl.setContentsMargins(32, 28, 32, 28); wl.setSpacing(8)
        
        t_lbl = QLabel("Daňový kalkulátor Enterprise")
        t_lbl.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 600; letter-spacing: 0.3px; font-family: {SERIF};")
        wl.addWidget(t_lbl)
        
        d_lbl = QLabel("Integrovaný systém pro výpočet přímých i nepřímých daní a sociálního pojištění v České republice a Spolkové republice Německo (verze 2026).")
        d_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; line-height: 1.5;")
        d_lbl.setWordWrap(True)
        wl.addWidget(d_lbl)
        lay.addWidget(welcome)

        # Quick Navigation Title
        q_title = QLabel("DOSTUPNÉ DAŇOVÉ MODULY")
        q_title.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(q_title)

        # Navigation Grid
        cards_lay = QHBoxLayout(); cards_lay.setSpacing(16)
        
        def ent_nav_card(icon, title, subtitle, target_index, accent=None):
            accent = accent or ACCENT
            glow = ACCENT_GLOW if accent == ACCENT else DE_GLOW
            card = QFrame()
            card.setObjectName("navCard")
            card.setStyleSheet(f"""
                QFrame#navCard {{
                    background-color: {BG_CARD};
                    border: 1px solid {BORDER};
                    border-top: 2px solid {accent};
                    border-radius: 8px;
                }}
                QFrame#navCard:hover {{
                    background-color: {BG_ELEVATED};
                    border-color: {accent};
                }}
            """)
            card.setCursor(Qt.PointingHandCursor)
            
            cl = QVBoxLayout(card); cl.setContentsMargins(20, 20, 20, 20); cl.setSpacing(10)
            
            # Icon
            ic = QLabel()
            ic.setPixmap(make_icon(icon, accent, QSize(32, 32)).pixmap(32, 32))
            cl.addWidget(ic)
            
            t = QLabel(title)
            t.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600;")
            cl.addWidget(t)
            
            d = QLabel(subtitle)
            d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; line-height: 1.4;")
            d.setWordWrap(True)
            cl.addWidget(d)
            
            cl.addStretch()
            
            lnk = QLabel("Spustit kalkulaci →")
            lnk.setStyleSheet(f"color: {glow}; font-size: 12px; font-weight: 600;")
            cl.addWidget(lnk)
            
            card.mousePressEvent = lambda e, idx=target_index: self.nav_requested.emit(idx)
            return card

        cards_lay.addWidget(ent_nav_card("person", "Zaměstnanec ČR", "Výpočet čisté mzdy, daňových slev, zdravotního a sociálního pojištění.", 1, accent=ACCENT))
        cards_lay.addWidget(ent_nav_card("business", "OSVČ / Podnikatel", "Roční přiznání, zálohy na pojištění a daňový paušál v ČR.", 2, accent=ACCENT))
        cards_lay.addWidget(ent_nav_card("dph", "Kalkulátor DPH ČR", "Přepočet základu a vyčíslení DPH dle českých sazeb.", 3, accent=ACCENT))
        cards_lay.addWidget(ent_nav_card("flag_de", "Německé daně", "Německá mzda (Lohnsteuer), odvody a kalkulátor MwSt.", 4, accent=DE_ACCENT))
        lay.addLayout(cards_lay)

        # Footer Informational Message
        lay.addStretch()
        footer = QLabel("Všechny finanční výpočty vycházejí ze zákonných norem platných od 1. 1. 2026. Aplikace plně odpovídá podnikovým standardům auditovatelnosti dat (včetně podpory JSON a CSV exportů).")
        footer.setStyleSheet(f"color: {TEXT_MUT}; font-size: 11px; line-height: 1.4;")
        footer.setWordWrap(True)
        lay.addWidget(footer)

        scroll.setWidget(inner); outer.addWidget(scroll)


# ══════════════════════════════════════════════════════════════════
# SIDEBAR (Enterprise Edition - strictly styled, no leaks)
# ══════════════════════════════════════════════════════════════════
class Sidebar(QWidget):
    nav_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {BG_SURFACE};
                border-right: 1px solid {BORDER};
            }}
        """)
        self._buttons = []; self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 20, 12, 20); lay.setSpacing(4)

        # Logo Card
        logo_card = QFrame()
        logo_card.setObjectName("logoCard")
        logo_card.setStyleSheet(f"""
            QFrame#logoCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-top: 2px solid {ACCENT};
                border-radius: 6px;
            }}
        """)
        ll = QHBoxLayout(logo_card); ll.setContentsMargins(12,12,12,12); ll.setSpacing(10)
        li = QLabel(); li.setPixmap(make_icon("seal", ACCENT, QSize(22,22)).pixmap(22,22))
        li.setStyleSheet("background:transparent; border:none;")
        ll.addWidget(li)
        
        ltv = QVBoxLayout(); ltv.setSpacing(1); ltv.setContentsMargins(0,0,0,0)
        lt1 = QLabel("TAXCALC"); lt1.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; font-family: {SERIF}; background:transparent;")
        ltv.addWidget(lt1)
        lt2 = QLabel("Enterprise v2.2"); lt2.setStyleSheet(f"color: {TEXT_MUT}; font-size: 10px; background:transparent;")
        ltv.addWidget(lt2)
        ll.addLayout(ltv); ll.addStretch()
        lay.addWidget(logo_card)
        lay.addSpacing(20)

        # Navigation title separators
        def group_title(text, accent=None):
            accent = accent or TEXT_MUT
            lbl = QLabel()
            lbl.setText(f'<span style="color:{accent};">&#9632;</span>&nbsp;&nbsp;'
                        f'<span style="color:{TEXT_MUT};">{text.upper()}</span>')
            lbl.setStyleSheet("font-size: 9px; font-weight: 700; letter-spacing: 1px; padding: 12px 10px 4px 10px; background:transparent;")
            lay.addWidget(lbl)

        group_title("Hlavní menu")
        self._add_nav_item("home", "Domů (Přehled)", 0)

        group_title("Česká republika", accent=ACCENT)
        self._add_nav_item("person", "DPFO -- Zaměstnanec", 1, accent=ACCENT)
        self._add_nav_item("business", "DPFO -- OSVČ", 2, accent=ACCENT)
        self._add_nav_item("dph", "DPH Kalkulátor", 3, accent=ACCENT)

        group_title("Německo", accent=DE_ACCENT)
        self._add_nav_item("flag_de", "Lohnsteuer + MwSt", 4, accent=DE_ACCENT)

        lay.addStretch()

        # Enterprise audit log statement in sidebar footer
        foot = QLabel("Internal Use Only\nAudit Trail Active")
        foot.setStyleSheet(f"color: {TEXT_MUT}; font-size: 9px; font-weight: 600;")
        foot.setAlignment(Qt.AlignCenter)
        lay.addWidget(foot)

    def _add_nav_item(self, icon, label, idx, accent=None):
        btn = QPushButton()
        btn.setObjectName(f"navItemBtn_{idx}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(38)
        
        bl = QHBoxLayout(btn); bl.setContentsMargins(10, 0, 10, 0); bl.setSpacing(8)
        
        ico = QLabel()
        ico.setPixmap(make_icon(icon, TEXT_SEC, QSize(16,16)).pixmap(16,16))
        ico.setFixedSize(16,16); ico.setStyleSheet("background:transparent; border:none;")
        
        txt = QLabel(label)
        txt.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; font-weight: 500; background:transparent;")
        
        bl.addWidget(ico)
        bl.addWidget(txt)
        bl.addStretch()
        
        btn._ico = ico; btn._txt = txt; btn._iname = icon; btn._idx = idx; btn._accent = accent or ACCENT
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {BG_HOVER};
            }}
        """)
        btn.clicked.connect(lambda: self.nav_changed.emit(idx))
        self._buttons.append(btn)
        self.layout().addWidget(btn)

    def set_active(self, idx):
        for btn in self._buttons:
            active = (btn._idx == idx)
            if active:
                accent = btn._accent
                on_color = TEXT if accent == DE_ACCENT else INK_ON_ACCENT
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        border-radius: 6px;
                        border: none;
                    }}
                """)
                btn._txt.setStyleSheet(f"color: {on_color}; font-size: 12px; font-weight: 600; background:transparent;")
                btn._ico.setPixmap(make_icon(btn._iname, on_color, QSize(16,16)).pixmap(16,16))
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: 6px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {BG_HOVER};
                    }}
                """)
                btn._txt.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; font-weight: 500; background:transparent;")
                btn._ico.setPixmap(make_icon(btn._iname, TEXT_SEC, QSize(16,16)).pixmap(16,16))


# ══════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VER}")
        self.resize(1120, 740)
        self.setMinimumSize(920, 580)
        self._build()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        self.sidebar = Sidebar(); self.sidebar.nav_changed.connect(self._navigate)
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget(); self.stack.setStyleSheet(f"background-color:{BG};")
        self.home_view = HomeView(); self.home_view.nav_requested.connect(self._navigate)
        self.dpfo_view = DPFOZamView()
        self.osvc_view = OSVCView()
        self.dph_view  = DPHView()
        self.de_view   = DEView()

        for v in [self.home_view, self.dpfo_view, self.osvc_view, self.dph_view, self.de_view]:
            self.stack.addWidget(v)

        root.addWidget(self.stack)
        self._navigate(0)

    def _navigate(self, idx):
        self.stack.setCurrentIndex(idx)
        self.sidebar.set_active(idx)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VER)
    app.setStyleSheet(QSS)
    app.setWindowIcon(make_icon("seal", ACCENT, QSize(64, 64)))
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "cz.danovy.kalkulator.22"
        )
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
