#!/usr/bin/env python3
"""
Pulse Music Player v3.0
Desktop application — Python + PySide6 (Qt)
Modern UI · Playlists · DaVinci-style video viewer
Supports: MP3, MP4/M4A, WAV, OGG, FLAC
"""

import sys
import os
import io
import json
import uuid
import random
import threading
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import Qt, QUrl, QSize, QTimer, QRectF, QSizeF, QEvent, Signal, QObject
from PySide6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QBrush, QColor, QFont,
    QPen, QPainterPath, QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QSlider, QStackedWidget, QFileDialog, QMessageBox, QFrame,
    QGraphicsView, QGraphicsScene, QScrollArea, QSizePolicy,
    QDialog, QDialogButtonBox, QInputDialog
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

from PIL import Image, ImageDraw
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

# ─── Constants ───────────────────────────────────────────────────
APP_NAME        = "Pulse Music Player"
SETTINGS_FILE   = os.path.join(os.path.expanduser("~"), ".pulse_settings.json")
PLAYLISTS_DIR   = os.path.join(os.path.expanduser("~"), "Documents", "Pulse_Playlists")
AUDIO_EXTS      = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".opus", ".wma"}
VIDEO_EXTS      = {".mp4", ".m4a"}
ALL_EXTS        = AUDIO_EXTS | VIDEO_EXTS

# ── Color Palette (Component Hi-Fi -- graphite & copper VU-glow) ──
BG            = "#111416"
BG_SURFACE    = "#191d20"
BG_CARD       = "#202629"
BG_ELEVATED   = "#282f33"
BG_HOVER      = "#323c40"
ACCENT        = "#bbef92"
ACCENT_HV     = "#d0f8b3"
ACCENT_GLOW   = "#d0f8b3"
INK_ON_ACCENT = "#17200d"   # Dark ink text/icons set against copper fills
DANGER        = "#c1443a"
TEXT          = "#f1f4f2"
TEXT_SEC      = "#aab6b5"
TEXT_MUT      = "#849390"
BORDER        = "#303937"
BORDER_HV     = "#454e5f"

def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ─── Master Stylesheet ────────────────────────────────────────────
QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: transparent; width: 5px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BG_ELEVATED}; border-radius: 2px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QListWidget {{
    background-color: transparent; border: none; outline: none;
}}
QListWidget::item {{
    background-color: transparent; border-radius: 8px; margin: 1px 4px; padding: 0px;
}}
QListWidget::item:hover {{ background-color: {BG_HOVER}; }}
QListWidget::item:selected {{ background-color: {_rgba(ACCENT, 0.18)}; }}
QSlider::groove:horizontal {{
    height: 4px; background: {BG_ELEVATED}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_GLOW});
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #ffffff; width: 0px; height: 0px;
    border-radius: 0px; margin-top: -4px; margin-bottom: -4px;
}}
QSlider::handle:horizontal:hover {{
    background: white; width: 14px; height: 14px;
    border-radius: 7px; margin-top: -5px; margin-bottom: -5px;
}}
QLineEdit {{
    background-color: {BG_ELEVATED}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 7px 12px; color: {TEXT}; font-size: 13px;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; background-color: {BG_CARD}; }}
QPushButton {{ border: none; border-radius: 8px; padding: 6px; background: transparent; }}
QToolTip {{
    background-color: {BG_ELEVATED}; color: {TEXT}; border: 1px solid {BORDER_HV};
    border-radius: 8px; padding: 5px 10px; font-size: 12px;
}}
"""


# ─── Vector Icons ─────────────────────────────────────────────────
def make_icon(name: str, color: str, sz: QSize = QSize(24, 24)) -> QIcon:
    screen = QApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1
    px = QPixmap(round(sz.width()*ratio), round(sz.height()*ratio))
    px.setDevicePixelRatio(ratio)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    w, h = sz.width(), sz.height()

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(c))

    if name == "play":
        path = QPainterPath()
        path.moveTo(w*.33, h*.20); path.lineTo(w*.80, h*.50); path.lineTo(w*.33, h*.80)
        path.closeSubpath(); p.drawPath(path)

    elif name == "pause":
        p.drawRoundedRect(w*.28, h*.21, w*.14, h*.58, 3, 3)
        p.drawRoundedRect(w*.56, h*.21, w*.14, h*.58, 3, 3)

    elif name == "prev":
        path = QPainterPath()
        path.moveTo(w*.72, h*.20); path.lineTo(w*.37, h*.50); path.lineTo(w*.72, h*.80)
        path.closeSubpath(); p.drawPath(path)
        p.drawRoundedRect(w*.20, h*.20, w*.10, h*.60, 2, 2)

    elif name == "next":
        path = QPainterPath()
        path.moveTo(w*.28, h*.20); path.lineTo(w*.63, h*.50); path.lineTo(w*.28, h*.80)
        path.closeSubpath(); p.drawPath(path)
        p.drawRoundedRect(w*.70, h*.20, w*.10, h*.60, 2, 2)

    elif name == "shuffle":
        pen = QPen(c, 2.2); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        def line(ax,ay,bx,by): p.drawLine(int(w*ax),int(h*ay),int(w*bx),int(h*by))
        path1 = QPainterPath()
        path1.moveTo(w*.18,h*.25); path1.lineTo(w*.42,h*.25)
        path1.lineTo(w*.58,h*.75); path1.lineTo(w*.82,h*.75); p.drawPath(path1)
        h1 = QPainterPath()
        h1.moveTo(w*.70,h*.63); h1.lineTo(w*.82,h*.75); h1.lineTo(w*.70,h*.87); p.drawPath(h1)
        p2 = QPainterPath()
        p2.moveTo(w*.18,h*.75); p2.lineTo(w*.42,h*.75)
        p2.lineTo(w*.47,h*.65); p.drawPath(p2)
        p3 = QPainterPath()
        p3.moveTo(w*.53,h*.35); p3.lineTo(w*.58,h*.25)
        p3.lineTo(w*.82,h*.25); p.drawPath(p3)
        h2 = QPainterPath()
        h2.moveTo(w*.70,h*.13); h2.lineTo(w*.82,h*.25); h2.lineTo(w*.70,h*.37); p.drawPath(h2)

    elif name == "repeat":
        pen = QPen(c, 2.2); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(w*.18, h*.20, w*.64, h*.60), 40*16, 280*16)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
        head = QPainterPath()
        head.moveTo(w*.56,h*.06); head.lineTo(w*.80,h*.20); head.lineTo(w*.50,h*.34)
        head.closeSubpath(); p.drawPath(head)

    elif name == "volume":
        path = QPainterPath()
        path.moveTo(w*.14,h*.37); path.lineTo(w*.30,h*.37); path.lineTo(w*.50,h*.18)
        path.lineTo(w*.50,h*.82); path.lineTo(w*.30,h*.63); path.lineTo(w*.14,h*.63)
        path.closeSubpath(); p.drawPath(path)
        pen = QPen(c, 1.8); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(w*.30,h*.32,w*.36,h*.36), -50*16, 100*16)
        p.drawArc(QRectF(w*.18,h*.18,w*.64,h*.64), -50*16, 100*16)

    elif name == "mute":
        path = QPainterPath()
        path.moveTo(w*.14,h*.37); path.lineTo(w*.30,h*.37); path.lineTo(w*.50,h*.18)
        path.lineTo(w*.50,h*.82); path.lineTo(w*.30,h*.63); path.lineTo(w*.14,h*.63)
        path.closeSubpath(); p.drawPath(path)
        pen = QPen(c, 2.0); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(int(w*.65),int(h*.35), int(w*.85),int(h*.65))
        p.drawLine(int(w*.85),int(h*.35), int(w*.65),int(h*.65))

    elif name == "fullscreen":
        pen = QPen(c, 2.2); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        for x1,y1,x2,y2 in [(.22,.34,.22,.22), (.22,.22,.34,.22),
                              (.78,.34,.78,.22), (.78,.22,.66,.22),
                              (.22,.66,.22,.78), (.22,.78,.34,.78),
                              (.78,.66,.78,.78), (.78,.78,.66,.78)]:
            p.drawLine(int(w*x1),int(h*y1),int(w*x2),int(h*y2))

    elif name == "plus":
        pen = QPen(c, 2.5); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawLine(int(w*.50),int(h*.20), int(w*.50),int(h*.80))
        p.drawLine(int(w*.20),int(h*.50), int(w*.80),int(h*.50))

    elif name == "close":
        pen = QPen(c, 2.0); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
        p.drawLine(int(w*.28),int(h*.28), int(w*.72),int(h*.72))
        p.drawLine(int(w*.72),int(h*.28), int(w*.28),int(h*.72))

    elif name == "playlist":
        pen = QPen(c, 2.0); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.setBrush(Qt.NoBrush)
        for y in [.28, .50, .72]:
            p.drawLine(int(w*.20),int(h*y), int(w*.80),int(h*y))

    elif name == "folder":
        pen = QPen(c, 2.0); pen.setJoinStyle(Qt.RoundJoin); pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(w*.12,h*.72); path.lineTo(w*.12,h*.42)
        path.lineTo(w*.40,h*.42); path.lineTo(w*.48,h*.28)
        path.lineTo(w*.88,h*.28); path.lineTo(w*.88,h*.72); path.closeSubpath()
        p.drawPath(path)

    elif name in ("music", "wave", "video", "search", "info"):
        pen = QPen(c, max(1.5, w*.075))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        if name == "wave":
            for x, length in ((.22,.28),(.40,.64),(.60,.90),(.78,.44)):
                p.drawLine(int(w*x), int(h*(.5-length/2)), int(w*x), int(h*(.5+length/2)))
        elif name == "music":
            path = QPainterPath()
            path.moveTo(w*.4,h*.72); path.lineTo(w*.4,h*.28)
            path.lineTo(w*.78,h*.19); path.lineTo(w*.78,h*.62)
            p.drawPath(path)
            p.setBrush(c)
            p.drawEllipse(QRectF(w*.19,h*.64,w*.21,h*.16))
            p.drawEllipse(QRectF(w*.57,h*.54,w*.21,h*.16))
        elif name == "video":
            p.drawRoundedRect(QRectF(w*.12,h*.22,w*.76,h*.56), w*.08,w*.08)
            path = QPainterPath()
            path.moveTo(w*.42,h*.38); path.lineTo(w*.63,h*.50); path.lineTo(w*.42,h*.62)
            path.closeSubpath(); p.fillPath(path,c)
        elif name == "search":
            p.drawEllipse(QRectF(w*.16,h*.13,w*.49,h*.49))
            p.drawLine(int(w*.61),int(h*.60),int(w*.84),int(h*.83))
        else:
            p.drawEllipse(QRectF(w*.14,h*.14,w*.72,h*.72))
            p.drawLine(int(w*.50),int(h*.47),int(w*.50),int(h*.69))
            p.drawPoint(int(w*.50),int(h*.32))

    elif name == "edit":
        pen = QPen(c, 1.8); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(w*.60,h*.22); path.lineTo(w*.78,h*.40)
        path.lineTo(w*.35,h*.80); path.lineTo(w*.18,h*.82)
        path.lineTo(w*.20,h*.65); path.closeSubpath()
        p.drawPath(path)

    p.end()
    return QIcon(px)


# ─── Vinyl Disc Rendering (signature visual motif) ────────────────
def _pil_to_qpixmap(img: "Image.Image") -> QPixmap:
    buf = io.BytesIO(); img.save(buf, "PNG")
    return QPixmap.fromImage(QImage.fromData(buf.getvalue()))


def render_mini_vinyl(size: int) -> QPixmap:
    """Small flat placeholder disc used for list-row / bar thumbnails without cover art."""
    px = QPixmap(size, size); px.fill(Qt.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
    cx = cy = size / 2.0
    r = size / 2.0 - 1
    grad = QRadialGradient(cx, cy, r)
    grad.setColorAt(0.0, QColor(BG_ELEVATED)); grad.setColorAt(1.0, QColor("#0c0a08"))
    p.setBrush(QBrush(grad)); p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
    pen = QPen(QColor(0, 0, 0, 90), max(1.0, size * 0.02)); p.setPen(pen); p.setBrush(Qt.NoBrush)
    for frac in (0.42, 0.58, 0.74, 0.90):
        rr = r * frac
        p.drawEllipse(QRectF(cx - rr, cy - rr, rr * 2, rr * 2))
    lr = r * 0.34
    p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor(ACCENT)))
    p.drawEllipse(QRectF(cx - lr, cy - lr, lr * 2, lr * 2))
    sr = max(1.0, r * 0.08)
    p.setBrush(QBrush(QColor(INK_ON_ACCENT)))
    p.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))
    p.end()
    return px


def circular_cover(size: int, cover_img: "Image.Image") -> "Image.Image":
    """Crop real cover art into a circular puck with a thin copper rim."""
    img = cover_img.convert("RGBA")
    s = min(img.size)
    img = img.crop(((img.width - s)//2, (img.height - s)//2,
                     (img.width + s)//2, (img.height + s)//2)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    img.putalpha(mask)
    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse([0, 0, size - 1, size - 1], outline=(0xc9, 0x79, 0x3c, 200),
                                 width=max(1, int(size * 0.045)))
    return Image.alpha_composite(img, rim)


def build_disc_base(size: int, cover_img: Optional["Image.Image"] = None) -> "Image.Image":
    """Compose a full 'picture-disc' vinyl record at angle 0: cover art (or placeholder glow),
    groove rings, center label ring with a rotation-visible notch, and a spindle hole."""
    cx = cy = size / 2.0
    r = size / 2.0 - 1
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    if cover_img is not None:
        img = cover_img.convert("RGBA")
        s = min(img.size)
        img = img.crop(((img.width - s)//2, (img.height - s)//2,
                         (img.width + s)//2, (img.height + s)//2)).resize((size, size), Image.LANCZOS)
        disc.paste(img, (0, 0))
    else:
        d = ImageDraw.Draw(disc)
        rad = int(r)
        for rr in range(rad, 0, -2):
            t = (1 - rr / rad) ** 2
            col = (int(0x20 + (0xc9 - 0x20) * t * 0.6),
                   int(0x1c + (0x79 - 0x1c) * t * 0.6),
                   int(0x16 + (0x3c - 0x16) * t * 0.6), 255)
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    disc.putalpha(mask)

    groove = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(groove)
    n_rings = 20
    for i in range(n_rings):
        frac = 0.30 + (0.985 - 0.30) * (i / (n_rings - 1))
        rr = r * frac
        alpha = 50 if i % 2 == 0 else 28
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(0, 0, 0, alpha),
                   width=max(1, int(size * 0.006)))
    disc = Image.alpha_composite(disc, groove)

    label = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(label)
    lr = r * 0.30
    if cover_img is None:
        ld.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill=(0x1c, 0x16, 0x10, 255))
    ld.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], outline=(0xc9, 0x79, 0x3c, 235),
               width=max(2, int(size * 0.012)))
    notch_r = max(2, size * 0.012)
    nx = cx + lr * 0.55
    ld.ellipse([nx - notch_r, cy - notch_r, nx + notch_r, cy + notch_r], fill=(0xc9, 0x79, 0x3c, 255))
    disc = Image.alpha_composite(disc, label)

    sr = max(2, r * 0.035)
    sd = ImageDraw.Draw(disc)
    sd.ellipse([cx - sr, cy - sr, cx + sr, cy + sr], fill=(0x0c, 0x0a, 0x08, 255))

    rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse([1, 1, size - 2, size - 2], outline=(255, 255, 255, 18), width=2)
    disc = Image.alpha_composite(disc, rim)
    return disc


def rotate_disc(base: "Image.Image", angle_deg: float) -> "Image.Image":
    if not angle_deg:
        return base
    c = (base.width / 2.0, base.height / 2.0)
    return base.rotate(-angle_deg, resample=Image.BICUBIC, center=c)


# ─── Click-to-seek Slider ─────────────────────────────────────────
class ClickSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSliderDown(True)
            self._move(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def _move(self, event):
        ratio = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
        self.setValue(round(self.minimum() + (self.maximum() - self.minimum()) * ratio))
        self.sliderMoved.emit(self.value())

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self._move(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSliderDown():
            self._move(event)
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ─── Video Viewer ─────────────────────────────────────────────────
class VideoViewer(QGraphicsView):
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene.addItem(self.video_item)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#000000")))
        self.setStyleSheet("border: none; background-color: #000000;")
        self._zoom = 1.0

    def wheelEvent(self, event):
        f = 1.15 if event.angleDelta().y() > 0 else 0.85
        nz = self._zoom * f
        if 0.4 <= nz <= 15.0:
            self._zoom = nz
            self.scale(f, f)

    def mouseDoubleClickEvent(self, event):
        self.main_app.enter_fullscreen()

    def fit_video(self):
        self.resetTransform(); self._zoom = 1.0
        sz = self.viewport().size()
        self.scene.setSceneRect(0, 0, sz.width(), sz.height())
        self.video_item.setSize(QSizeF(sz.width(), sz.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event); self.fit_video()


# ─── Fullscreen Control Overlay ───────────────────────────────────
class FullscreenControls(QWidget):
    def __init__(self, fs_window, main_app):
        super().__init__(fs_window)
        self.fs_window = fs_window
        self.main_app = main_app
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            FullscreenControls {{
                background-color: rgba(20,18,16,225);
                border: 1px solid {BORDER_HV};
                border-radius: 18px;
            }}
            QLabel {{ background:transparent; border:none; color:{TEXT}; }}
            QPushButton {{ background:transparent; border:none; border-radius:8px; }}
            QPushButton:hover {{ background-color:rgba(255,255,255,15); }}
            QSlider::groove:horizontal {{ height:3px; background:rgba(255,255,255,20); border-radius:2px; }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_GLOW});
                border-radius:2px;
            }}
            QSlider::handle:horizontal {{ background:white; width:0; height:0; margin:-4px 0; }}
            QSlider::handle:horizontal:hover {{ background:white; width:12px; height:12px; border-radius:6px; margin:-5px 0; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 14, 24, 14)
        lay.setSpacing(10)

        # Timeline
        pr = QHBoxLayout(); pr.setSpacing(12)
        self.lbl_cur = QLabel("0:00")
        self.lbl_cur.setFixedWidth(36)
        self.lbl_cur.setStyleSheet(f"font-family:'Consolas'; font-size:11px; color:{ACCENT_GLOW}; letter-spacing:0.5px;")
        pr.addWidget(self.lbl_cur)
        self.prog = ClickSlider(Qt.Horizontal)
        self.prog.setRange(0, 1000)
        self.prog.sliderPressed.connect(lambda: setattr(self.main_app, "seeking", True))
        self.prog.sliderReleased.connect(self._seek_released)
        self.prog.sliderMoved.connect(self._slider_moved)
        pr.addWidget(self.prog)
        self.lbl_tot = QLabel("0:00")
        self.lbl_tot.setFixedWidth(36)
        self.lbl_tot.setStyleSheet(f"font-family:'Consolas'; font-size:11px; color:{ACCENT_GLOW}; letter-spacing:0.5px;")
        pr.addWidget(self.lbl_tot)
        lay.addLayout(pr)

        # Buttons
        br = QHBoxLayout(); br.setSpacing(8); br.addStretch()

        def btn(ico, col, sz=22, tip=""):
            b = QPushButton()
            b.setIcon(make_icon(ico, col, QSize(sz, sz))); b.setIconSize(QSize(sz, sz))
            b.setFixedSize(42, 42); b.setCursor(Qt.PointingHandCursor)
            if tip: b.setToolTip(tip)
            return b

        sc = ACCENT_GLOW if self.main_app.is_shuffle else TEXT_SEC
        self.btn_shuf = btn("shuffle", sc, 22, "Shuffle")
        self.btn_shuf.clicked.connect(lambda: (self.main_app.toggle_shuffle(), self.sync()))
        br.addWidget(self.btn_shuf)

        self.btn_prev = btn("prev", TEXT, 26, "Předchozí")
        self.btn_prev.clicked.connect(self.main_app.prev_track)
        br.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        pi = "pause" if self.main_app.is_playing else "play"
        self.btn_play.setIcon(make_icon(pi, INK_ON_ACCENT, QSize(34, 34)))
        self.btn_play.setIconSize(QSize(34, 34))
        self.btn_play.setFixedSize(56, 56)
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.setStyleSheet(f"""
            QPushButton {{ background:qradialgradient(cx:.5,cy:.5,radius:.8,stop:0 {ACCENT_HV},stop:1 {ACCENT}); border-radius:28px; }}
            QPushButton:hover {{ background:qradialgradient(cx:.5,cy:.5,radius:.8,stop:0 {ACCENT_GLOW},stop:1 {ACCENT_HV}); }}
        """)
        self.btn_play.clicked.connect(lambda: (self.main_app.toggle_play(), self.sync()))
        self.btn_play.setToolTip("Play / Pause")
        br.addWidget(self.btn_play)

        self.btn_next = btn("next", TEXT, 26, "Následující")
        self.btn_next.clicked.connect(self.main_app.next_track)
        br.addWidget(self.btn_next)

        rc = ACCENT_GLOW if self.main_app.repeat_mode != "none" else TEXT_SEC
        self.btn_rep = btn("repeat", rc, 22, "Opakovat")
        self.btn_rep.clicked.connect(lambda: (self.main_app.cycle_repeat(), self.sync()))
        br.addWidget(self.btn_rep)

        self.btn_fs = btn("fullscreen", ACCENT_GLOW, 22, "Ukončit (Esc)")
        self.btn_fs.clicked.connect(self.fs_window.close)
        br.addWidget(self.btn_fs)

        br.addStretch()
        lay.addLayout(br)

        # Volume
        vr = QHBoxLayout(); vr.setSpacing(8); vr.addStretch()
        is_muted = self.main_app.audio_output.isMuted()
        self.btn_mute = QPushButton()
        self.btn_mute.setFixedSize(30, 30)
        self.btn_mute.setIcon(make_icon("mute" if is_muted else "volume",
                                        TEXT_MUT if is_muted else TEXT_SEC, QSize(18, 18)))
        self.btn_mute.setIconSize(QSize(18, 18))
        self.btn_mute.clicked.connect(lambda: (self.main_app._mute_toggle(), self.sync()))
        self.btn_mute.setToolTip("Ztlumit")
        vr.addWidget(self.btn_mute)
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(int(self.main_app.volume * 100))
        self.vol.setFixedWidth(110)
        self.vol.valueChanged.connect(lambda v: self.main_app.vol_slider.setValue(v))
        vr.addWidget(self.vol)
        self.lbl_vol = QLabel(f"{int(self.main_app.volume*100)}%")
        self.lbl_vol.setStyleSheet(f"font-family:'Consolas'; font-size:11px; color:{TEXT_SEC};")
        vr.addWidget(self.lbl_vol)
        vr.addStretch()
        lay.addLayout(vr)

    def _seek_released(self):
        self.main_app.seeking = False
        dur = self.main_app.media_player.duration()
        self.main_app.media_player.setPosition(int((self.prog.value()/1000.0) * dur))

    def _slider_moved(self, val):
        dur = self.main_app.media_player.duration()
        pos = int((val / 1000.0) * dur); s = int(pos / 1000)
        m, s = divmod(s, 60); self.lbl_cur.setText(f"{m}:{s:02d}")

    def update_progress(self, pos, dur):
        if not self.prog.isSliderDown():
            self.prog.setValue(int((pos/dur)*1000) if dur > 0 else 0)
        s = int(pos/1000); m, s = divmod(s, 60); self.lbl_cur.setText(f"{m}:{s:02d}")
        ts = int(dur/1000); tm, ts = divmod(ts, 60); self.lbl_tot.setText(f"{tm}:{ts:02d}")

    def sync(self):
        pi = "pause" if self.main_app.is_playing else "play"
        self.btn_play.setIcon(make_icon(pi, INK_ON_ACCENT, QSize(34, 34)))
        sc = ACCENT_GLOW if self.main_app.is_shuffle else TEXT_SEC
        self.btn_shuf.setIcon(make_icon("shuffle", sc, QSize(22, 22)))
        rc = ACCENT_GLOW if self.main_app.repeat_mode != "none" else TEXT_SEC
        self.btn_rep.setIcon(make_icon("repeat", rc, QSize(22, 22)))
        is_muted = self.main_app.audio_output.isMuted()
        self.btn_mute.setIcon(make_icon("mute" if is_muted else "volume",
                                        TEXT_MUT if is_muted else TEXT_SEC, QSize(18, 18)))
        self.vol.setValue(int(self.main_app.volume * 100))
        self.lbl_vol.setText(f"{int(self.main_app.volume*100)}%")


# ─── Fullscreen Window ────────────────────────────────────────────
class FullscreenView(QWidget):
    def __init__(self, scene, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background: black;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        self.view = QGraphicsView(scene, self)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setBackgroundBrush(QBrush(QColor("black")))
        self.view.setStyleSheet("border:none;")
        lay.addWidget(self.view)
        self.controls = FullscreenControls(self, main_app)
        self.setMouseTracking(True)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        self.view.viewport().installEventFilter(self)
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(3000)
        self.hide_timer.timeout.connect(self._hide_controls)
        self.hide_timer.start()
        self._zoom = 1.0
        self.showFullScreen()

    def eventFilter(self, w, e):
        if w == self.view.viewport() and e.type() == QEvent.MouseMove:
            self._show_controls()
        return super().eventFilter(w, e)

    def mouseMoveEvent(self, e):
        self._show_controls(); super().mouseMoveEvent(e)

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 0.85
        nz = self._zoom * f
        if 0.4 <= nz <= 15.0:
            self._zoom = nz; self.view.scale(f, f)

    def mouseDoubleClickEvent(self, e): self.close()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_F): self.close()
        else: self.main_app.keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cw = min(700, self.width() - 80)
        ch = 195
        self.controls.setGeometry((self.width()-cw)//2, self.height()-ch-36, cw, ch)
        QTimer.singleShot(50, self._fit)

    def _fit(self):
        if self.view.scene() is None:
            return
        self.view.resetTransform(); self._zoom = 1.0
        items = self.view.scene().items()
        if items: self.view.fitInView(items[0], Qt.KeepAspectRatio)

    def _show_controls(self):
        self.controls.show()
        self.view.viewport().setCursor(Qt.OpenHandCursor)
        self.hide_timer.start()

    def _hide_controls(self):
        if not self.controls.underMouse():
            self.controls.hide()
            self.view.viewport().setCursor(Qt.BlankCursor)

    def closeEvent(self, e):
        self.hide_timer.stop(); self.view.setScene(None)
        self.main_app.fullscreen_view_closed(); super().closeEvent(e)


