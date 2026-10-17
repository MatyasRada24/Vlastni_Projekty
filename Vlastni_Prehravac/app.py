"""Pulse Player — local media library, Qt and FFmpeg."""
from __future__ import annotations
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')
from media_runtime import prepare_media_runtime
prepare_media_runtime()

import mutagen
from PySide6.QtCore import Qt, QUrl, QSize, QRectF, QTimer, QEvent, Signal, Slot, QObject, QRunnable, QThreadPool, QMimeData
from PySide6.QtGui import QIcon, QPixmap, QDrag, QKeySequence, QShortcut, QPainter, QPainterPath, QColor, QPen, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QSplitter, QStackedWidget, QScrollArea,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QFileDialog,
    QInputDialog, QMessageBox, QMenu, QComboBox, QListView, QSlider, QDialog,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout, QSizePolicy, QTabBar,
    QStylePainter, QStyleOptionComboBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QMediaFormat, QMediaMetaData
from pulse_core import ALL_EXTS, VIDEO_EXTS, Playlist, LibraryStore, PlaybackQueue, canonical, discover_files
from player_widgets import (make_icon, ClickSlider, VideoViewer,
    FullscreenView, BG, BG_SURFACE, BG_CARD, BG_ELEVATED, BG_HOVER, ACCENT,
    ACCENT_GLOW, INK_ON_ACCENT, TEXT, TEXT_SEC, TEXT_MUT, BORDER, QSS)

MEDIA_FILTER = 'Média (' + ' '.join('*' + e for e in sorted(ALL_EXTS)) + ');;Všechny soubory (*)'
ASSET_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets'
STYLE = QSS + f'''
QWidget {{ background: transparent; }}
QMainWindow, QDialog {{ background: {BG}; }}
QLabel {{ background: transparent; border: none; }}
QWidget#sidebar {{ background: {BG}; }}
QWidget#librarySurface {{ background: {BG_SURFACE}; border-radius: 18px; }}
QFrame#outputCard {{ background: {BG_SURFACE}; border-radius: 14px; }}
QWidget#playlistContainer, QWidget#playlistViewport, QScrollArea#playlistScroll {{ background: transparent; }}
QWidget#barSection, QSlider {{ background: transparent; }}
QPushButton {{ padding: 9px 12px; color: {TEXT_SEC}; font-weight: 600; }}
QPushButton:hover {{ background: {BG_HOVER}; color: {TEXT}; }}
QPushButton:pressed {{ background: #353d47; }}
QPushButton:checked {{ background: #253021; color: {ACCENT}; }}
QPushButton#primary {{ background: {ACCENT}; color: {INK_ON_ACCENT}; border-radius: 10px; }}
QPushButton#primary:hover {{ background: {ACCENT_GLOW}; }}
QPushButton#primary:pressed {{ background: #add65f; }}
QPushButton#primary:disabled {{ background: {BG_ELEVATED}; color: {TEXT_MUT}; }}
QPushButton:disabled {{ color: #535b68; }}
QPushButton:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#addMedia {{ background: {BG_ELEVATED}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 10px; }}
QPushButton#addMedia:hover {{ background: {BG_HOVER}; border-color: {TEXT_MUT}; }}
QLineEdit {{ background: {BG}; border: 1px solid {BORDER}; padding: 8px 12px; border-radius: 10px; }}
QTabBar {{ background: {BG}; border-radius: 10px; }}
QTabBar::tab {{ color: {TEXT_SEC}; padding: 9px 18px; margin: 3px; border-radius: 7px; }}
QTabBar::tab:selected {{ background: {BG_ELEVATED}; color: {TEXT}; }}
QTabBar::tab:hover {{ color: {ACCENT}; }}
QTableWidget {{ background: transparent; border: none; gridline-color: transparent;
    selection-background-color: #2b3727; selection-color: {TEXT}; }}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: #2b3727; }}
QTableWidget::item:hover {{ background: #242e2d; }}
QHeaderView::section {{ background: {BG_SURFACE}; color: {TEXT_MUT}; border: none;
    border-bottom: 1px solid {BORDER}; padding: 12px 10px; font-size: 11px; font-weight: 400; }}
QTableCornerButton::section {{ background: {BG_SURFACE}; border: none; }}
QComboBox {{ background: {BG_ELEVATED}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 9px 40px 9px 12px; color: {TEXT}; min-height: 20px; }}
QComboBox:hover {{ border-color: #454e5f; background: {BG_HOVER}; }}
QComboBox:focus, QComboBox:on {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;
    width: 34px; border: none; background: transparent; }}
QComboBox::down-arrow {{ image: url("{(ASSET_DIR / 'chevron-down.svg').as_posix()}");
    width: 16px; height: 16px; }}
QComboBox::down-arrow:on {{ image: url("{(ASSET_DIR / 'chevron-up.svg').as_posix()}"); }}
QComboBox QAbstractItemView {{ background: {BG_CARD}; color: {TEXT};
    border: 1px solid #454e5f; border-radius: 8px; padding: 4px;
    selection-background-color: #2b3727; selection-color: {ACCENT}; outline: none; }}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px 10px; border-radius: 5px; }}
QMenu {{ background: {BG_CARD}; border: 1px solid {BORDER}; padding: 6px; }}
QMenu::item {{ padding: 8px 22px; }}
QMenu::item:selected {{ background: {BG_HOVER}; border-radius: 5px; }}
QSplitter::handle {{ background: transparent; width: 12px; }}
QSlider::handle:horizontal {{ background: {TEXT}; width: 10px; height: 10px;
    border-radius: 5px; margin: -3px 0; }}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; width: 10px; height: 10px;
    border-radius: 5px; margin: -3px 0; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; }}
'''

class ElidedLabel(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.setFont(self.font())
        painter.drawText(self.contentsRect(), Qt.AlignLeft | Qt.AlignVCenter,
                         self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self.contentsRect().width()))


def label(text, size=13, color=TEXT_SEC, bold=False, elide=False):
    widget = ElidedLabel(text) if elide else QLabel(text)
    widget.setTextFormat(Qt.PlainText)
    widget.setStyleSheet(f'font-size:{size}px; color:{color}; font-weight:{700 if bold else 400};')
    return widget

def button(text, callback, icon=None, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.PointingHandCursor)
    if icon:
        widget.setIcon(make_icon(icon, INK_ON_ACCENT if primary else TEXT_SEC, QSize(18, 18)))
    if primary:
        widget.setObjectName('primary')
    widget.clicked.connect(callback)
    return widget

def duration_text(seconds):
    if not seconds:
        return '—'
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02d}:{seconds:02d}' if hours else f'{minutes}:{seconds:02d}'


def media_tile(size, cover=None, icon='music'):
    """A reusable rounded cover, with a neutral placeholder for untagged files."""
    screen = QApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1
    pixels = round(size*ratio)
    pix = QPixmap(pixels, pixels)
    pix.setDevicePixelRatio(ratio)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), size*.16, size*.16)
    painter.setClipPath(clip)
    painter.fillRect(pix.rect(), QColor('#293632'))
    if cover is not None and not cover.isNull():
        scaled = cover.scaled(pixels, pixels, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(ratio)
        painter.drawPixmap(round((size-scaled.width()/ratio)/2), round((size-scaled.height()/ratio)/2), scaled)
    else:
        edge = round(size*.46)
        make_icon(icon, ACCENT if icon == 'wave' else '#94b0a1', QSize(edge, edge)).paint(
            painter, (size-edge)//2, (size-edge)//2, edge, edge)
    painter.end()
    return pix

class MediaComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setView(QListView())
        # Style the popup frame too, so Windows does not leave a white border
        # around the dark list. Keep native selection and keyboard behavior.
        popup = self.view().window()
        popup.setObjectName('mediaComboPopup')
        popup.setStyleSheet(f'QFrame#mediaComboPopup {{ background: {BG_CARD}; border: none; }}')

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        painter.drawComplexControl(QStyle.CC_ComboBox, option)
        field = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField, self)
        option.currentText = self.fontMetrics().elidedText(option.currentText, Qt.ElideRight, field.width()-4)
        painter.drawControl(QStyle.CE_ComboBoxLabel, option)

    def showPopup(self):
        super().showPopup()
        # The popup receives the window stylesheet on first display. Recompute
        # cached row positions after polishing so padded items do not overlap.
        self.view().doItemsLayout()

class TaskSignals(QObject):
    done = Signal(object, object)

    @Slot(object, object)
    def deliver(self, result, error):
        self.callback(result, error)

class Task(QRunnable):
    def __init__(self, function, signals):
        super().__init__()
        self.function, self.signals = function, signals

    def run(self):
        try:
            self.signals.done.emit(self.function(), None)
        except Exception as error:
            self.signals.done.emit(None, str(error))

def metadata(path):
    result = {}
    try:
        audio = mutagen.File(path)
        if audio is None:
            return result
        info = audio.info
        result.update(duration=getattr(info, 'length', 0), sample_rate=getattr(info, 'sample_rate', 0),
                      bits=getattr(info, 'bits_per_sample', 0), bitrate=getattr(info, 'bitrate', 0),
                      channels=getattr(info, 'channels', 0))
        if Path(path).suffix.lower() in {'.mp3', '.aac', '.opus', '.ogg', '.ac3', '.eac3', '.wma'} or (
                Path(path).suffix.lower() in {'.m4a', '.mp4'} and getattr(info, 'codec', '') != 'alac'):
            result['bits'] = 0  # Lossy streams do not have a meaningful PCM bit depth.
        easy = mutagen.File(path, easy=True)
        for key in ('title', 'artist', 'album'):
            value = easy.get(key) if easy is not None else None
            if value:
                result[key] = str(value[0])
        tags = audio.tags or {}
        if hasattr(audio, 'pictures') and audio.pictures:
            result['cover'] = audio.pictures[0].data
        elif 'covr' in tags:
            result['cover'] = bytes(tags['covr'][0])
        else:
            for tag in tags.values():
                if getattr(tag, 'FrameID', '') == 'APIC':
                    result['cover'] = tag.data
                    break
    except Exception:
        pass  # Metadata failure does not imply playback failure.
    return result

class RecordArtwork(QWidget):
    def __init__(self):
        super().__init__()
        self.cover = QPixmap()
        self.setMinimumSize(180, 180)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        painter.drawPixmap((self.width()-side)//2, (self.height()-side)//2,
                           media_tile(side, self.cover, 'wave'))

class MediaItemDelegate(QStyledItemDelegate):
    """Keep native selection/focus while separating track titles from metadata."""
    def paint(self, painter, option, index):
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        text = index.data(Qt.DisplayRole) or ''
        styled.text = ''
        style = styled.widget.style() if styled.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, styled, painter, styled.widget)
        painter.save()
        painter.setClipRect(option.rect)
        rect = option.rect.adjusted(10, 0, -10, 0)
        foreground = index.data(Qt.ForegroundRole)
        color = foreground.color() if foreground else QColor(TEXT_SEC)
        painter.setPen(color)
        font = QFont(option.font)
        font.setPixelSize(12)
        if index.column() == 1:
            thumb = index.data(Qt.UserRole + 1)
            if isinstance(thumb, QPixmap):
                painter.drawPixmap(rect.left(), rect.center().y()-20, thumb)
            rect.adjust(52, 0, 0, 0)
            title, _, artist = text.partition('\n')
            font.setPixelSize(13)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            title_rect = rect.adjusted(0, 13, 0, 0)
            title_rect.setHeight(21)
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter,
                             QFontMetrics(font).elidedText(title, Qt.ElideRight, rect.width()))
            font.setPixelSize(11)
            font.setWeight(QFont.Normal)
            painter.setFont(font)
            painter.setPen(QColor('#db9999') if color.name() == '#db9999' else QColor(TEXT_MUT))
            artist_rect = rect.adjusted(0, 35, 0, 0)
            artist_rect.setHeight(19)
            painter.drawText(artist_rect, Qt.AlignLeft | Qt.AlignVCenter,
                             QFontMetrics(font).elidedText(artist, Qt.ElideRight, rect.width()))
        elif index.column() == 0 and text == '▶':
            make_icon('play', color.name(), QSize(16, 16)).paint(
                painter, option.rect.center().x()-8, option.rect.center().y()-8, 16, 16)
        else:
            painter.setFont(font)
            align = Qt.AlignCenter if index.column() in (0, 2) else Qt.AlignRight | Qt.AlignVCenter if index.column() == 4 else Qt.AlignLeft | Qt.AlignVCenter
            painter.drawText(rect, align, QFontMetrics(font).elidedText(text, Qt.ElideRight, rect.width()))
        painter.restore()


class MediaTable(QTableWidget):
    def __init__(self, owner):
        super().__init__(0, 5)
        self.owner = owner
        self.setHorizontalHeaderLabels(['#', 'Název / interpret', 'Formát', 'Kvalita zdroje', 'Délka'])
        self.setItemDelegate(MediaItemDelegate(self))
        self.setMouseTracking(True)
        for col in (1, 3):
            self.horizontalHeaderItem(col).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.horizontalHeaderItem(4).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(68)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(owner.track_menu)
        self.itemDoubleClicked.connect(lambda item: owner.play_selected())
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col, width in ((0, 34), (2, 68), (3, 148), (4, 62)):
            self.setColumnWidth(col, width)
        self.setMinimumWidth(420)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep the title readable in a compact window; source details remain
        # visible in the player pane and in each track's tooltip.
        self.setColumnHidden(3, self.viewport().width() < 650)

    def selected_paths(self):
        return [self.item(index.row(), 0).data(Qt.UserRole) for index in self.selectionModel().selectedRows()]

    def startDrag(self, actions):
        paths = self.selected_paths()
        if paths:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)

    def dragEnterEvent(self, event):
        self.owner.accept_drag(event)

    def dragMoveEvent(self, event):
        self.owner.accept_drag(event)

    def dropEvent(self, event):
        if event.source() is self and self.owner.cur_view:
            self.owner.reorder_selected(self.indexAt(event.position().toPoint()).row())
            event.acceptProposedAction()
        else:
            self.owner.dropEvent(event)

class PlaylistButton(QPushButton):
    def __init__(self, playlist, owner):
        super().__init__()
        self.playlist, self.owner = playlist, owner
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(make_icon('playlist', TEXT_SEC, QSize(16, 16)))
        self.setStyleSheet('text-align:left; padding:12px 10px;')
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)
        self.clicked.connect(lambda: owner.switch_view(playlist))
        name = playlist.name if len(playlist.name) <= 21 else playlist.name[:20] + '…'
        self.setText(f'  {name}   {len(playlist.paths)}')
        self.setToolTip(playlist.name + '\nPřetáhněte sem soubory. Pravé tlačítko: přejmenovat / smazat.')
        self.setChecked(owner.cur_view is playlist)

    def menu(self, pos):
        menu = QMenu(self)
        menu.addAction('Přejmenovat', lambda: self.owner.rename_playlist(self.playlist))
        menu.addAction('Smazat playlist', lambda: self.owner.delete_playlist(self.playlist))
        menu.exec(self.mapToGlobal(pos))

    def dragEnterEvent(self, event):
        self.owner.accept_drag(event)

    def dragMoveEvent(self, event):
        self.owner.accept_drag(event)

    def dropEvent(self, event):
        self.owner.import_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()], self.playlist)
        event.acceptProposedAction()

class PulseApp(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.setWindowTitle('Pulse Player')
        self.resize(1440, 900)
        self.setMinimumSize(1100, 740)
        self.setStyleSheet(STYLE)
        self.setAcceptDrops(True)
        asset = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets' / 'icon.ico'
        self.setWindowIcon(QIcon(str(asset)))
        self.store = store or LibraryStore()
        self.paths, self.playlists, self.settings = self.store.load()
        self.paths = list(dict.fromkeys(self.paths + [p for pl in self.playlists for p in pl.paths]))
        self.meta = {}
        self.placeholder_thumbs = {kind: media_tile(40, icon=kind) for kind in ('music', 'video')}
        self.cur_view = self.current_path = None
        self.filtered = []
        self.queue = PlaybackQueue()
        self.queue.shuffle = bool(self.settings.get('is_shuffle', False))
        repeat = self.settings.get('repeat_mode', 'none')
        self.queue.repeat = repeat if repeat in ('none', 'all', 'one') else 'none'
        try:
            self.volume = max(0, min(1, float(self.settings.get('volume', .8))))
        except (ValueError, TypeError):
            self.volume = .8
        self.is_playing = self.seeking = self.closing = False
        self.fs_view = None
        self.jobs = set()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render_tracks)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save)
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(self.volume)
        self.media_devices = QMediaDevices(self)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.playback_changed)
        self.media_player.mediaStatusChanged.connect(self.media_status)
        self.media_player.errorOccurred.connect(self.playback_error)
        self.media_player.hasVideoChanged.connect(self.video_changed)
        self.media_player.metaDataChanged.connect(self.media_metadata_changed)
        self.media_devices.audioOutputsChanged.connect(self.refresh_outputs)
        self.build_ui()
        self.refresh_outputs()
        self.refresh_playlists()
        self.render_tracks()
        self.sync_modes()
        self.install_shortcuts()
        QApplication.instance().installEventFilter(self)
        self.load_metadata(self.paths)
        if self.store.warnings:
            QTimer.singleShot(0, lambda: self.notify('\n'.join(self.store.warnings), True))

    @property
    def is_shuffle(self):
        return self.queue.shuffle

    @property
    def repeat_mode(self):
        return self.queue.repeat

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        root.addLayout(body, 1)
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(204)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(8, 14, 16, 12)
        sb.setSpacing(10)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(media_tile(34, icon='wave'))
        mark.setFixedSize(34, 34)
        brand.addWidget(mark)
        brand.addWidget(label('pulse', 27, TEXT, True))
        brand.addStretch()
        sb.addLayout(brand)
        sb.addSpacing(32)
        self.library_button = button('  Knihovna', lambda: self.switch_view(None), 'music')
        self.library_button.setCheckable(True)
        self.library_button.setChecked(True)
        self.library_button.setStyleSheet('text-align:left; padding:12px 10px;')
        sb.addWidget(self.library_button)
        folder_button = button('  Přidat složku', self.scan_folder, 'plus')
        folder_button.setStyleSheet('text-align:left; padding:12px 10px;')
        sb.addSpacing(20)
        pl_header = QHBoxLayout()
        pl_header.addWidget(label('Moje playlisty', 11, TEXT_MUT))
        pl_header.addStretch()
        plus = button('', self.create_playlist)
        plus.setIcon(make_icon('plus', TEXT_SEC, QSize(28, 28)))
        plus.setIconSize(QSize(28, 28))
        plus.setToolTip('Vytvořit playlist')
        plus.setAccessibleName('Vytvořit playlist')
        plus.setFixedSize(40, 40)
        plus.setStyleSheet('padding:0;')
        pl_header.addWidget(plus)
        sb.addLayout(pl_header)
        scroll = QScrollArea()
        scroll.setObjectName('playlistScroll')
        scroll.viewport().setObjectName('playlistViewport')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.playlist_container = QWidget()
        self.playlist_container.setObjectName('playlistContainer')
        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(0, 0, 0, 0)
        self.playlist_layout.setSpacing(4)
        self.playlist_layout.addStretch()
        scroll.setWidget(self.playlist_container)
        sb.addWidget(scroll, 1)
        sb.addWidget(folder_button)
        body.addWidget(sidebar)
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(12)
        split.setChildrenCollapsible(False)
        body.addWidget(split, 1)
        library = QWidget()
        library.setObjectName('librarySurface')
        lib = QVBoxLayout(library)
        lib.setContentsMargins(26, 26, 26, 14)
        lib.setSpacing(20)
        header = QHBoxLayout()
        header.setSpacing(12)
        heading = QVBoxLayout()
        heading.setSpacing(6)
        self.view_title = label('Knihovna', 28, TEXT, True, elide=True)
        self.view_title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.view_title.setToolTip('Knihovna')
        heading.addWidget(self.view_title)
        self.lbl_stats = label('', 12)
        heading.addWidget(self.lbl_stats)
        header.addLayout(heading, 1)
        self.import_button = button('Přidat soubory', self.add_files, 'plus')
        self.import_button.setObjectName('addMedia')
        self.import_button.setFixedHeight(42)
        self.import_button.setToolTip('Vybrat soubory (Ctrl+O)')
        header.addWidget(self.import_button)
        lib.addLayout(header)
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Hledat v knihovně…')
        self.search_input.addAction(make_icon('search', TEXT_MUT, QSize(20,20)), QLineEdit.LeadingPosition)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(42)
        self.search_input.textChanged.connect(self.render_tracks)
        toolbar.addWidget(self.search_input, 1)
        self.filter_combo = QTabBar()
        self.filter_combo.setAccessibleName('Typ médií')
        self.filter_combo.setCursor(Qt.PointingHandCursor)
        self.filter_combo.setDrawBase(False)
        self.filter_combo.setExpanding(False)
        self.filter_combo.setFixedHeight(42)
        for name in ('Vše', 'Hudba', 'Video'):
            self.filter_combo.addTab(name)
        self.filter_combo.currentChanged.connect(self.render_tracks)
        toolbar.addWidget(self.filter_combo)
        lib.addLayout(toolbar)
        actions = QHBoxLayout()
        self.play_all_button = button('Přehrát vše', self.play_all, 'play', True)
        actions.addWidget(self.play_all_button)
        self.add_playlist_button = button('Do playlistu', self.add_selection_to_playlist, 'plus')
        actions.addWidget(self.add_playlist_button)
        actions.addStretch()
        self.result_label = label('', 11)
        actions.addWidget(self.result_label)
        lib.addLayout(actions)
        self.table = MediaTable(self)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        lib.addWidget(self.table, 1)
        self.empty_label = label('', 14)
        self.empty_label.setTextFormat(Qt.RichText)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        lib.addWidget(self.empty_label, 1)
        split.addWidget(library)
        inspector = QWidget()
        inspector.setMinimumWidth(264)
        inspector.setMaximumWidth(336)
        ins = QVBoxLayout(inspector)
        ins.setContentsMargins(12, 18, 12, 12)
        ins.setSpacing(16)
        self.now_badge = label('Přehrávač', 13, TEXT_SEC, True)
        ins.addWidget(self.now_badge)
        self.media_stack = QStackedWidget()
        self.media_stack.setFixedHeight(256)
        self.artwork = RecordArtwork()
        self.media_stack.addWidget(self.artwork)
        self.video_widget = VideoViewer(self)
        self.media_stack.addWidget(self.video_widget)
        self.media_player.setVideoOutput(self.video_widget.video_item)
        ins.addWidget(self.media_stack)
        self.now_title = label('Zatím nic nehraje', 21, TEXT, True)
        self.now_title.setWordWrap(True)
        ins.addWidget(self.now_title)
        self.now_artist = label('', 12)
        self.now_artist.setWordWrap(True)
        ins.addWidget(self.now_artist)
        self.source_label = label('', 11, ACCENT)
        self.source_label.setWordWrap(True)
        ins.addWidget(self.source_label)
        ins.addStretch(1)
        output_card = QFrame()
        output_card.setObjectName('outputCard')
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(14, 12, 14, 16)
        output_layout.setSpacing(12)
        output_heading = QHBoxLayout()
        output_heading.addWidget(label('Zvukový výstup', 12, TEXT_SEC))
        output_heading.addStretch()
        info_button = self.icon_button('info', 'Informace o zvuku a kodecích', self.show_audio_info)
        info_button.setFixedSize(26, 26)
        output_heading.addWidget(info_button)
        output_layout.addLayout(output_heading)
        self.output_combo = MediaComboBox()
        self.output_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.output_combo.setMinimumContentsLength(12)
        self.output_combo.currentIndexChanged.connect(self.choose_output)
        output_layout.addWidget(self.output_combo)
        self.output_info = label('', 11)
        self.output_info.setWordWrap(True)
        self.output_info.hide()
        output_layout.addWidget(self.output_info)
        ins.addWidget(output_card)
        split.addWidget(inspector)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        split.setSizes([800, 300])
        self.notice = label('', 11)
        self.notice.setWordWrap(True)
        self.notice.setContentsMargins(24, 6, 24, 6)
        self.notice.hide()
        root.addWidget(self.notice)
        root.addSpacing(12)
        self.build_player_bar(root)

    def build_player_bar(self, root):
        bar = QFrame()
        bar.setObjectName('playerBar')
        bar.setStyleSheet(f'QFrame#playerBar {{ background:{BG_SURFACE}; border-radius:16px; }}')
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)
        progress = QHBoxLayout()
        self.lbl_cur_time, self.lbl_tot_time = label('0:00', 11), label('0:00', 11)
        for time_label in (self.lbl_cur_time, self.lbl_tot_time):
            time_label.setFixedWidth(36)
            time_label.setAlignment(Qt.AlignCenter)
        self.prog_slider = ClickSlider(Qt.Horizontal)
        self.prog_slider.setRange(0, 1000)
        self.prog_slider.sliderPressed.connect(lambda: setattr(self, 'seeking', True))
        self.prog_slider.sliderMoved.connect(self.preview_seek)
        self.prog_slider.sliderReleased.connect(self.seek_released)
        progress.addWidget(self.lbl_cur_time)
        progress.addWidget(self.prog_slider, 1)
        progress.addWidget(self.lbl_tot_time)
        row = QGridLayout()
        row.setColumnStretch(0, 1)
        row.setColumnStretch(1, 2)
        row.setColumnStretch(2, 1)
        row.setHorizontalSpacing(20)
        track = QWidget()
        track.setObjectName('barSection')
        track.setMinimumWidth(0)
        track.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        track_row = QHBoxLayout(track)
        track_row.setContentsMargins(0, 0, 0, 0)
        track_row.setSpacing(12)
        self.bar_thumb = QLabel()
        self.bar_thumb.setPixmap(media_tile(44))
        self.bar_thumb.setFixedSize(44, 44)
        track_row.addWidget(self.bar_thumb)
        names = QVBoxLayout()
        self.lbl_title = label('Zatím nic nehraje', 13, TEXT, True, elide=True)
        self.lbl_title.setMinimumWidth(0)
        self.lbl_title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.lbl_artist = label('Vyberte skladbu nebo video', 11, elide=True)
        self.lbl_artist.setMinimumWidth(0)
        self.lbl_artist.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        names.setSpacing(3)
        names.addWidget(self.lbl_title)
        names.addWidget(self.lbl_artist)
        track_row.addLayout(names, 1)
        row.addWidget(track, 0, 0)
        transport = QHBoxLayout()
        transport.setSpacing(12)
        transport.addStretch()
        self.btn_shuf = self.icon_button('shuffle', 'Náhodné pořadí', self.toggle_shuffle)
        transport.addWidget(self.btn_shuf)
        transport.addWidget(self.icon_button('prev', 'Předchozí (Ctrl+←)', self.prev_track))
        self.btn_play = self.icon_button('play', 'Přehrát / pozastavit (mezerník)', self.toggle_play, True)
        transport.addWidget(self.btn_play)
        transport.addWidget(self.icon_button('next', 'Následující (Ctrl+→)', self.next_track))
        self.btn_rep = self.icon_button('repeat', 'Opakování', self.cycle_repeat)
        transport.addWidget(self.btn_rep)
        transport.addStretch()
        playback = QWidget()
        playback.setObjectName('barSection')
        playback.setMinimumWidth(360)
        playback.setMaximumWidth(580)
        playback_layout = QVBoxLayout(playback)
        playback_layout.setContentsMargins(0, 0, 0, 0)
        playback_layout.setSpacing(6)
        playback_layout.addLayout(transport)
        playback_layout.addLayout(progress)
        row.addWidget(playback, 0, 1)
        output = QHBoxLayout()
        output.setSpacing(10)
        output.addStretch(1)
        self.btn_fs = self.icon_button('fullscreen', 'Celá obrazovka (F)', self.enter_fullscreen)
        self.btn_fs.setEnabled(False)
        output.addWidget(self.btn_fs)
        self.btn_mute = self.icon_button('volume', 'Ztlumit (M)', self._mute_toggle)
        output.addWidget(self.btn_mute)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(round(self.volume*100))
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        output.addWidget(self.vol_slider)
        self.lbl_vol = label(f'{round(self.volume*100)}%', 11)
        self.lbl_vol.setFixedWidth(34)
        output.addWidget(self.lbl_vol)
        row.addLayout(output, 0, 2)
        layout.addLayout(row)
        root.addWidget(bar)

    def icon_button(self, icon, tip, callback, primary=False):
        widget = button('', callback, icon, primary)
        widget.setFixedSize(52 if primary else 36, 52 if primary else 36)
        icon_size = QSize(26 if primary else 19, 26 if primary else 19)
        widget.setIcon(make_icon(icon, INK_ON_ACCENT if primary else TEXT_SEC, icon_size))
        widget.setIconSize(icon_size)
        widget.setToolTip(tip)
        widget.setAccessibleName(tip)
        widget.setStyleSheet('padding:0; border-radius:26px;' if primary else 'padding:0; border-radius:18px;')
        return widget

    def install_shortcuts(self):
        for key, callback in [('Ctrl+O', self.add_files), ('Ctrl+Shift+O', self.scan_folder),
                              ('Ctrl+N', self.create_playlist), ('Ctrl+F', self.search_input.setFocus),
                              ('Ctrl+Right', self.next_track), ('Ctrl+Left', self.prev_track)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

    def keyPressEvent(self, event):
        if isinstance(QApplication.focusWidget(), QLineEdit):
            return super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key_Space:
            self.toggle_play()
        elif key == Qt.Key_F:
            self.enter_fullscreen()
        elif key == Qt.Key_M:
            self._mute_toggle()
        elif key in (Qt.Key_Left, Qt.Key_Right):
            offset = 5000 if key == Qt.Key_Right else -5000
            self.media_player.setPosition(max(0, self.media_player.position()+offset))
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.play_selected()
        else:
            return super().keyPressEvent(event)
        event.accept()

    def eventFilter(self, watched, event):
        # Table views and focused buttons otherwise consume Space before the window.
        if (event.type() == QEvent.KeyPress and isinstance(watched, QWidget)
                and watched.window() in (self, self.fs_view)
                and not isinstance(watched, (QLineEdit, QComboBox, QTabBar))
                and event.modifiers() == Qt.NoModifier
                and event.key() in (Qt.Key_Space, Qt.Key_M, Qt.Key_F)):
            if not event.isAutoRepeat():
                self.keyPressEvent(event)
            return True
        return super().eventFilter(watched, event)

    def notify(self, message, error=False):
        self.notice.setText(message)
        self.notice.setStyleSheet(f'color:{"#ffaaaa" if error else ACCENT}; background:{BG_CARD};')
        self.notice.show()

    def run_task(self, function, callback):
        signals = TaskSignals(self)
        self.jobs.add(signals)
        def done(result, error):
            self.jobs.discard(signals)
            signals.deleteLater()
            if not self.closing:
                callback(result, error)
        signals.callback = done
        signals.done.connect(signals.deliver, Qt.QueuedConnection)
        self.pool.start(Task(function, signals))

    def accept_drag(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        self.accept_drag(event)

    def dragMoveEvent(self, event):
        self.accept_drag(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.import_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()], self.cur_view)
            event.acceptProposedAction()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Přidat média', '', MEDIA_FILTER)
        if paths:
            self.import_paths(paths, self.cur_view)

    def scan_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Přidat složku včetně podsložek')
        if folder:
            self.import_paths([folder], self.cur_view)

    def import_paths(self, paths, target=None):
        self.notify('Načítám soubory…')
        def complete(found, error):
            if error:
                self.notify(f'Soubory se nepodařilo načíst: {error}', True)
            elif target is not None and target not in self.playlists:
                self.notify('Cílový playlist už neexistuje. Přidání bylo zrušeno.', True)
            elif not found:
                self.notify('Nebyly nalezeny podporované mediální soubory.', True)
            else:
                self.add_paths(found, target)
        self.run_task(lambda: discover_files(paths), complete)

    def add_paths(self, paths, target=None):
        existing = {canonical(p): p for p in self.paths}
        fresh, resolved = [], []
        for path in paths:
            key = canonical(path)
            if key not in existing:
                existing[key] = path
                self.paths.append(path)
                fresh.append(path)
            resolved.append(existing[key])
        before = len(target.paths) if target else len(self.paths)-len(fresh)
        if target:
            target.paths = list(dict.fromkeys(target.paths + resolved))
        added = len(target.paths)-before if target else len(fresh)
        saved = self.save()
        self.refresh_playlists()
        self.render_tracks()
        self.load_metadata(fresh)
        if saved:
            destination = target.name if target else 'Knihovna'
            self.notify(f'{destination} · přidáno {added} souborů.' + (' Duplicity byly přeskočeny.' if added < len(paths) else ''))

    def load_metadata(self, paths):
        for start in range(0, len(paths), 50):
            batch = paths[start:start+50]
            def complete(result, error):
                if result:
                    for path, value in result:
                        if value.get('cover') and path in self.paths:
                            cover = QPixmap()
                            if cover.loadFromData(value['cover']):
                                value['_thumbnail'] = media_tile(40, cover)
                    self.meta.update({p: value for p, value in result if p in self.paths})
                    self.render_timer.start(120)
                    if self.current_path:
                        self.update_now_playing()
            self.run_task(lambda batch=batch: [(p, metadata(p)) for p in batch], complete)

    def track_info(self, path):
        base = Path(path).stem
        artist, title = base.split(' - ', 1) if ' - ' in base else ('Neznámý interpret', base)
        return {'title': title, 'artist': artist, 'album': '', **self.meta.get(path, {})}

    def quality_text(self, path):
        info = self.meta.get(path, {})
        parts = []
        if info.get('bits'):
            parts.append(f'{info["bits"]} bit')
        if info.get('sample_rate'):
            parts.append(f'{info["sample_rate"]/1000:g} kHz')
        if not info.get('bits') and info.get('bitrate'):
            parts.append(f'{round(info["bitrate"]/1000)} kb/s')
        return ' / '.join(parts) or '—'

    def view_paths(self):
        return list(self.cur_view.paths if self.cur_view else self.paths)

    def render_tracks(self):
        selected = set(self.table.selected_paths())
        scroll = self.table.verticalScrollBar().value()
        query = self.search_input.text().strip().casefold()
        kind = self.filter_combo.currentIndex()
        self.filtered = []
        for path in self.view_paths():
            info = self.track_info(path)
            video = Path(path).suffix.lower() in VIDEO_EXTS
            if kind == 1 and video or kind == 2 and not video:
                continue
            if query and query not in ' '.join([info['title'], info['artist'], info['album'], Path(path).name]).casefold():
                continue
            self.filtered.append(path)
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.filtered))
        for row, path in enumerate(self.filtered):
            info = self.track_info(path)
            exists = Path(path).is_file()
            title = info['title'] + '\n' + (info['artist'] if exists else 'Soubor není dostupný · pravé tlačítko → Najít soubor')
            values = ['▶' if path == self.current_path else str(row+1), title,
                      Path(path).suffix[1:].upper(), self.quality_text(path), duration_text(info.get('duration'))]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, path)
                if col == 1:
                    media_kind = 'video' if Path(path).suffix.lower() in VIDEO_EXTS else 'music'
                    item.setData(Qt.UserRole + 1, info.get('_thumbnail', self.placeholder_thumbs[media_kind]))
                item.setToolTip(path if col != 3 else 'Parametry zdrojové nahrávky: ' + self.quality_text(path))
                item.setForeground(QColor(ACCENT if path == self.current_path else TEXT if col == 1 else TEXT_SEC))
                if not exists:
                    item.setForeground(QColor('#db9999'))
                self.table.setItem(row, col, item)
                if path in selected:
                    item.setSelected(True)
        self.table.verticalScrollBar().setValue(scroll)
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)
        count = len(self.view_paths())
        seconds = sum(self.meta.get(p, {}).get('duration', 0) for p in self.view_paths())
        self.lbl_stats.setText(f'{count} médií  ·  {duration_text(seconds)}' if count else '')
        self.lbl_stats.setVisible(count > 0)
        self.result_label.setText(f'{len(self.filtered)} položek')
        self.result_label.setVisible(bool(query or kind))
        self.table.setVisible(bool(self.filtered))
        self.empty_label.setVisible(not self.filtered)
        empty_title = 'Žádné výsledky' if count else 'Vaše knihovna je zatím prázdná'
        empty_hint = 'Zkuste jiný název nebo filtr.' if count else 'Přetáhněte sem hudbu či video<br>nebo zvolte Přidat soubory.'
        self.empty_label.setText(f'<span style="font-size:20px; font-weight:600; color:{TEXT}">{empty_title}</span>'
                                 f'<br><br><span style="color:{TEXT_SEC}">{empty_hint}</span>')
        self.play_all_button.setEnabled(bool(self.filtered))
        self.selection_changed()

    def selection_changed(self):
        self.add_playlist_button.setEnabled(bool(self.table.selected_paths()))

    def refresh_playlists(self):
        while self.playlist_layout.count() > 1:
            item = self.playlist_layout.takeAt(0)
            item.widget().hide()
            item.widget().deleteLater()
        for index, pl in enumerate(self.playlists):
            self.playlist_layout.insertWidget(index, PlaylistButton(pl, self))
        self.library_button.setChecked(self.cur_view is None)

    def switch_view(self, playlist):
        self.cur_view = playlist
        self.view_title.setText(playlist.name if playlist else 'Knihovna')
        self.view_title.setToolTip(playlist.name if playlist else 'Knihovna')
        self.search_input.setPlaceholderText('Hledat v playlistu…' if playlist else 'Hledat v knihovně…')
        self.search_input.clear()
        self.refresh_playlists()
        self.render_tracks()

    def create_playlist(self):
        name, ok = QInputDialog.getText(self, 'Nový playlist', 'Jak se bude playlist jmenovat?')
        if ok and name.strip():
            pl = Playlist(name.strip()[:120])
            self.playlists.append(pl)
            self.save()
            self.switch_view(pl)
            return pl
        return None

    def rename_playlist(self, playlist):
        name, ok = QInputDialog.getText(self, 'Přejmenovat playlist', 'Název:', text=playlist.name)
        if ok and name.strip():
            playlist.name = name.strip()[:120]
            self.save()
            self.refresh_playlists()
            if self.cur_view is playlist:
                self.view_title.setText(playlist.name)

    def delete_playlist(self, playlist):
        if QMessageBox.question(self, 'Smazat playlist', f'Smazat playlist „{playlist.name}“?\nMediální soubory zůstanou na disku.',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.playlists.remove(playlist)
        if self.cur_view is playlist:
            self.switch_view(None)
        self.refresh_playlists()
        self.save()

    def playlist_menu(self, paths, menu):
        for pl in self.playlists:
            menu.addAction(pl.name, lambda pl=pl: self.add_paths(paths, pl))
        menu.addSeparator()
        def new_playlist():
            pl = self.create_playlist()
            if pl:
                self.add_paths(paths, pl)
        menu.addAction('+ Nový playlist', new_playlist)

    def add_selection_to_playlist(self):
        paths = self.table.selected_paths()
        if paths:
            menu = QMenu(self)
            self.playlist_menu(paths, menu)
            menu.exec(self.add_playlist_button.mapToGlobal(self.add_playlist_button.rect().bottomLeft()))

    def track_menu(self, pos):
        paths = self.table.selected_paths()
        if not paths:
            return
        menu = QMenu(self)
        menu.addAction('Přehrát', self.play_selected)
        self.playlist_menu(paths, menu.addMenu('Přidat do playlistu'))
        if self.cur_view:
            menu.addAction('Posunout nahoru', lambda: self.move_selection(-1))
            menu.addAction('Posunout dolů', lambda: self.move_selection(1))
        if len(paths) == 1 and not Path(paths[0]).is_file():
            menu.addAction('Najít soubor…', lambda: self.relocate(paths[0]))
        menu.addSeparator()
        menu.addAction('Odebrat z playlistu' if self.cur_view else 'Odebrat z knihovny', self.remove_selection)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def remove_selection(self):
        paths = set(self.table.selected_paths())
        if self.cur_view:
            self.cur_view.paths = [p for p in self.cur_view.paths if p not in paths]
        else:
            self.paths = [p for p in self.paths if p not in paths]
            for pl in self.playlists:
                pl.paths = [p for p in pl.paths if p not in paths]
            for path in paths:
                self.queue.remove(path)
            if self.current_path in paths:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
                self.current_path = None
                self.update_now_playing()
        self.save()
        self.refresh_playlists()
        self.render_tracks()

    def reorder_selected(self, row):
        if not self.cur_view:
            return
        selected = self.table.selected_paths()
        target = self.filtered[row] if 0 <= row < len(self.filtered) else None
        if target in selected:
            return
        remaining = [p for p in self.cur_view.paths if p not in selected]
        index = remaining.index(target) if target in remaining else len(remaining)
        self.cur_view.paths = remaining[:index] + selected + remaining[index:]
        self.save()
        self.render_tracks()

    def move_selection(self, direction):
        if not self.cur_view:
            return
        paths = self.cur_view.paths
        selected = set(self.table.selected_paths())
        indices = range(len(paths)) if direction < 0 else range(len(paths)-1, -1, -1)
        for i in indices:
            j = i + direction
            if paths[i] in selected and 0 <= j < len(paths) and paths[j] not in selected:
                paths[i], paths[j] = paths[j], paths[i]
        self.save()
        self.render_tracks()

    def relocate(self, missing):
        path, _ = QFileDialog.getOpenFileName(self, 'Najít přesunutý soubor', '', MEDIA_FILTER)
        if not path:
            return
        existing = next((p for p in self.paths if canonical(p) == canonical(path)), path)
        self.paths = list(dict.fromkeys(existing if p == missing else p for p in self.paths))
        for pl in self.playlists:
            pl.paths = list(dict.fromkeys(existing if p == missing else p for p in pl.paths))
        current = self.queue.current
        self.queue.paths = list(dict.fromkeys(existing if p == missing else p for p in self.queue.paths))
        self.queue.original = list(dict.fromkeys(existing if p == missing else p for p in self.queue.original))
        current = existing if current == missing else current
        self.queue.position = self.queue.paths.index(current) if current in self.queue.paths else -1
        if self.current_path == missing:
            self.media_player.stop()
            self.current_path = None
            self.update_now_playing()
        self.save()
        self.load_metadata([existing])
        self.refresh_playlists()
        self.render_tracks()

    def play_all(self):
        paths = [p for p in self.filtered if Path(p).is_file()]
        if paths:
            self.queue.start(paths, paths[0])
            self.play_path(paths[0])
        else:
            self.notify('Soubory nejsou dostupné. Připojte disk nebo použijte „Najít soubor“.', True)

    def play_selected(self):
        selected = self.table.selected_paths()
        if not selected:
            return
        path = selected[0]
        if not Path(path).is_file():
            self.notify('Soubor nebyl nalezen. Pravým tlačítkem můžete vybrat „Najít soubor“.', True)
            return
        self.queue.start([p for p in self.filtered if Path(p).is_file()], path)
        self.play_path(path)

    def play_path(self, path):
        if not Path(path).is_file():
            self.notify(f'Soubor není dostupný: {path}', True)
            self.media_player.stop()
            return
        self.media_player.stop()
        self.current_path = path
        self.media_stack.setCurrentIndex(0)
        self.btn_fs.setEnabled(False)
        self.notice.hide()
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.update_now_playing()
        self.render_tracks()
        self.media_player.play()

    def update_now_playing(self):
        path = self.current_path
        if not path:
            self.lbl_title.setText('Zatím nic nehraje')
            self.lbl_artist.setText('Vyberte médium z knihovny')
            self.now_title.setText('Zatím nic nehraje')
            self.now_artist.setText('')
            self.source_label.setText('')
            self.artwork.cover = QPixmap()
            self.artwork.update()
            self.bar_thumb.setPixmap(media_tile(44))
            self.media_stack.setCurrentIndex(0)
            return
        info = self.track_info(path)
        self.lbl_title.setText(info['title'])
        self.lbl_title.setToolTip(info['title'])
        self.lbl_artist.setText(info['artist'])
        self.now_title.setText(info['title'])
        self.now_artist.setText(info['artist'])
        self.source_label.setText(Path(path).suffix[1:].upper() + '  ·  ' + self.quality_text(path))
        pix = QPixmap()
        if info.get('cover'):
            pix.loadFromData(info['cover'])
        self.artwork.cover = pix
        self.artwork.update()
        self.bar_thumb.setPixmap(media_tile(44, pix, 'video' if Path(path).suffix.lower() in VIDEO_EXTS else 'music'))

    def toggle_play(self):
        if not self.current_path:
            self.play_all()
        elif self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def next_track(self, automatic=False):
        path = self.queue.advance(automatic=automatic)
        if path:
            self.play_path(path)
        elif automatic:
            self.media_player.stop()

    def prev_track(self):
        if self.media_player.position() > 3000:
            self.media_player.setPosition(0)
        else:
            path = self.queue.advance(-1)
            if path:
                self.play_path(path)
            elif self.current_path:
                self.media_player.setPosition(0)

    def playback_changed(self, state):
        self.is_playing = state == QMediaPlayer.PlayingState
        self.btn_play.setIcon(make_icon('pause' if self.is_playing else 'play', INK_ON_ACCENT, QSize(26, 26)))
        self.now_badge.setText('Právě hraje' if self.is_playing else 'Pozastaveno' if state == QMediaPlayer.PausedState else 'Přehrávač')
        if self.fs_view:
            self.fs_view.controls.sync()

    def media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            ended_path = self.current_path
            QTimer.singleShot(0, lambda: self.next_track(automatic=True)
                if not self.closing and self.current_path == ended_path
                and self.media_player.mediaStatus() == QMediaPlayer.EndOfMedia else None)

    def playback_error(self, error, message):
        if error != QMediaPlayer.NoError:
            self.notify(f'Médium nelze přehrát. Soubor může být poškozený nebo jeho kodek není dostupný. {message}', True)

    def video_changed(self, has_video):
        self.media_stack.setCurrentIndex(1 if has_video else 0)
        self.btn_fs.setEnabled(has_video)
        if has_video:
            self.video_widget.fit_video()
        elif self.fs_view:
            self.fs_view.close()

    def media_metadata_changed(self):
        if not self.current_path:
            return
        data = self.media_player.metaData()
        info = self.meta.setdefault(self.current_path, {})
        for key, field in ((QMediaMetaData.Title, 'title'), (QMediaMetaData.AlbumTitle, 'album')):
            value = data.stringValue(key)
            if value:
                info[field] = value
        self.update_now_playing()
        self.render_timer.start(120)

    def toggle_shuffle(self):
        self.queue.set_shuffle(not self.queue.shuffle)
        self.sync_modes()
        self.save_timer.start(250)

    def cycle_repeat(self):
        modes = ['none', 'all', 'one']
        self.queue.repeat = modes[(modes.index(self.queue.repeat)+1) % 3]
        self.sync_modes()
        self.save_timer.start(250)

    def sync_modes(self):
        self.btn_shuf.setIcon(make_icon('shuffle', ACCENT if self.is_shuffle else TEXT_SEC, QSize(19, 19)))
        self.btn_shuf.setToolTip('Náhodné pořadí: ' + ('zapnuto' if self.is_shuffle else 'vypnuto'))
        self.btn_rep.setIcon(make_icon('repeat', ACCENT if self.repeat_mode != 'none' else TEXT_SEC, QSize(19, 19)))
        self.btn_rep.setText('1' if self.repeat_mode == 'one' else '')
        self.btn_rep.setToolTip('Opakování: ' + {'none': 'vypnuto', 'all': 'celá fronta', 'one': 'jedna skladba'}[self.repeat_mode])
        if self.fs_view:
            self.fs_view.controls.sync()

    def preview_seek(self, value):
        seconds = value / 1000 * self.media_player.duration() / 1000
        self.lbl_cur_time.setText(duration_text(seconds) if seconds else '0:00')

    def seek_released(self):
        self.seeking = False
        self.media_player.setPosition(round(self.prog_slider.value()/1000*self.media_player.duration()))

    def update_position(self, position):
        total = self.media_player.duration()
        if not self.seeking:
            self.prog_slider.setValue(round(position/total*1000) if total else 0)
            self.lbl_cur_time.setText(duration_text(position/1000) if position else '0:00')
        if self.fs_view:
            self.fs_view.controls.update_progress(position, total)

    def update_duration(self, duration):
        self.lbl_tot_time.setText(duration_text(duration/1000) if duration else '0:00')
        self.prog_slider.setEnabled(duration > 0)
        if self.current_path and duration:
            self.meta.setdefault(self.current_path, {})['duration'] = duration / 1000
            self.render_timer.start(120)

    def _on_vol_changed(self, value):
        self.volume = value / 100
        self.audio_output.setVolume(self.volume)
        if value > 0:
            self.audio_output.setMuted(False)
        self.sync_volume()
        self.save_timer.start(400)

    def _mute_toggle(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())
        self.sync_volume()

    def sync_volume(self):
        muted = self.audio_output.isMuted()
        self.lbl_vol.setText('0%' if muted else f'{round(self.volume*100)}%')
        self.btn_mute.setIcon(make_icon('mute' if muted or not self.volume else 'volume', TEXT_SEC, QSize(19, 19)))
        if self.fs_view:
            self.fs_view.controls.sync()

    def refresh_outputs(self):
        self.output_combo.blockSignals(True)
        self.output_combo.clear()
        self.output_combo.addItem('Výchozí zařízení', None)
        wanted = self.settings.get('output_device', '')
        selected = 0
        self.devices = QMediaDevices.audioOutputs()
        for index, device in enumerate(self.devices, 1):
            identifier = bytes(device.id()).hex()
            self.output_combo.addItem(device.description(), identifier)
            if identifier == wanted:
                selected = index
        self.output_combo.setCurrentIndex(selected)
        self.output_combo.blockSignals(False)
        self.choose_output(selected)
        if wanted and selected == 0:
            self.notify('Uložený zvukový výstup není připojen. Používám výchozí zařízení systému.')

    def choose_output(self, index):
        if index < 0:
            return
        device = self.devices[index-1] if index > 0 else QMediaDevices.defaultAudioOutput()
        self.audio_output.setDevice(device)
        self.settings['output_device'] = self.output_combo.itemData(index) or ''
        self.output_combo.setToolTip(device.description())
        self.output_info.setText('Není připojené žádné zvukové zařízení.' if device.isNull() else '')
        self.output_info.setVisible(device.isNull())
        self.save_timer.start(400)

    def show_audio_info(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Zvuk a kodeky')
        dialog.resize(580, 470)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)
        layout.addWidget(label('Věrně původní nahrávce', 23, TEXT, True))
        device = self.audio_output.device()
        preferred = device.preferredFormat()
        text = ('Přehrávání používá FFmpeg v Qt. Nahrávka se při importu nepřevádí, '
                'nepřekódovává ani neupravuje ekvalizérem. Hlasitost je omezena na 100 %, '
                'aby aplikace nepřidávala digitální zesílení.\n\n'
                'Kvalitu určuje zdroj, nastavení zvuku Windows a váš DAC / zvuková karta. '
                'Ztracené detaily MP3 nelze obnovit. Tento režim nezaručuje bit-perfect '
                'ani exkluzivní WASAPI výstup.\n\n'
                f'Výstup: {device.description() or "žádný"}\n'
                f'Preferovaný formát zařízení: {preferred.sampleRate()/1000:g} kHz, '
                f'{preferred.channelCount()} kanálů (není měřením právě odesílaného zvuku).\n\n')
        codecs = QMediaFormat().supportedAudioCodecs(QMediaFormat.ConversionMode.Decode)
        text += 'Zvukové kodeky hlášené enginem: ' + ', '.join(QMediaFormat.audioCodecDescription(c) for c in codecs) + '.\n\n'
        text += 'Podpora konkrétního profilu závisí na sestavení dekodéru. Soubory chráněné DRM nejsou podporovány.'
        content = label(text, 12)
        content.setWordWrap(True)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addWidget(button('Hotovo', dialog.accept, primary=True))
        dialog.exec()

    def enter_fullscreen(self):
        if self.media_player.hasVideo() and self.fs_view is None:
            self.fs_view = FullscreenView(self.video_widget.scene, self, self)
            self.fs_view.setAttribute(Qt.WA_DeleteOnClose)
            self.fs_view.show()

    def fullscreen_view_closed(self):
        self.fs_view = None
        self.video_widget.fit_video()

    def save(self):
        self.settings.update(volume=self.volume, is_shuffle=self.is_shuffle, repeat_mode=self.repeat_mode)
        try:
            self.store.save(self.paths, self.playlists, self.settings)
            return True
        except OSError as error:
            self.notify(f'Změny se nepodařilo uložit: {error}', True)
            return False

    def closeEvent(self, event):
        self.save_timer.stop()
        if not self.save():
            answer = QMessageBox.question(self, 'Neuložené změny', 'Knihovnu nelze uložit. Zavřít i bez uložení změn?',
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self.closing = True
        QApplication.instance().removeEventFilter(self)
        self.render_timer.stop()
        self.media_player.stop()
        if self.fs_view:
            self.fs_view.close()
        self.pool.clear()
        self.pool.waitForDone()
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        # Keep the native Windows frame (snap, resize and system menu), while
        # matching its title bar to the application on supported Windows builds.
        if sys.platform == 'win32' and QApplication.platformName() == 'windows':
            import ctypes
            from ctypes import wintypes
            try:
                set_attribute = ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
                set_attribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
                set_attribute.restype = ctypes.c_long
                dark = ctypes.c_int(1)
                set_attribute(int(self.winId()), 20, ctypes.byref(dark), ctypes.sizeof(dark))
            except (OSError, AttributeError):
                pass  # Older Windows versions keep their standard title bar.


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('Pulse Player')
    app.setOrganizationName('Pulse')
    window = PulseApp()
    window.show()
    if len(sys.argv) > 1:
        window.import_paths(sys.argv[1:])
    sys.exit(app.exec())
