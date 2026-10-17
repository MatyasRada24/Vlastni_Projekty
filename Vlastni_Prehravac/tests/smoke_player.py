"""Real decoder + UI integration smoke test. Uses isolated data and silent fixtures.
Run: .venv/Scripts/python tests/smoke_player.py
Requires the development-only imageio-ffmpeg package.
"""
import os
import sys
import subprocess
import time
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['PULSE_DATA_DIR'] = str(ROOT / 'qa' / 'smoke-data')
from PySide6.QtCore import Qt, QUrl, QMimeData, QPoint, QPointF, QTimer
from PySide6.QtGui import QFontDatabase, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtMultimedia import QMediaPlayer, QAudioBufferOutput
from PySide6.QtTest import QTest
from app import PulseApp, PlaylistButton
from pulse_core import LibraryStore, Playlist, VIDEO_EXTS
import imageio_ffmpeg


def wait_for(predicate, timeout=6000):
    end = time.monotonic() + timeout/1000
    while time.monotonic() < end:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(.02)  # Release the GIL so Python metadata workers can run.
    return False


def main():
    fixtures = ROOT / 'qa' / 'media'
    fixtures.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    samples = [
        ('Wave.wav', ['-c:a', 'pcm_s24le', '-ar', '96000']),
        ('MP3.mp3', ['-c:a', 'libmp3lame', '-b:a', '320k']),
        ('Lossless.flac', ['-c:a', 'flac']),
        ('AAC.m4a', ['-c:a', 'aac']),
        ('ALAC.m4a', ['-c:a', 'alac']),
        ('Opus.opus', ['-c:a', 'libopus']),
        ('Vorbis.ogg', ['-c:a', 'libvorbis']),
        ('Dolby.ac3', ['-c:a', 'ac3']),
    ]
    for name, options in samples:
        path = fixtures / name
        if not path.exists():
            subprocess.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
                            '-t', '2', *options, str(path)], check=True)
    for name, codec in [('H264.mp4', 'libx264'), ('HEVC.mkv', 'libx265'), ('VP9.webm', 'libvpx-vp9')]:
        path = fixtures / name
        if not path.exists():
            subprocess.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=12',
                            '-t', '2', '-c:v', codec, '-pix_fmt', 'yuv420p', str(path)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    app = QApplication([])
    for font in ['segoeui.ttf', 'segoeuib.ttf']:
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    store = LibraryStore(ROOT / 'qa' / 'smoke-data')
    store.save([], [], {})
    window = PulseApp(store)
    errors = []
    old_hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: (errors.append(str(value)), old_hook(kind, value, tb))
    window.show()
    app.processEvents()
    window.grab().save(str(ROOT / 'qa' / 'empty.png'))

    # External file manager drop with duplicates, a nested folder and Unicode paths.
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(fixtures)), QUrl.fromLocalFile(str(fixtures/'MP3.mp3'))])
    enter = QDragEnterEvent(QPoint(300, 200), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(window, enter)
    assert enter.isAccepted()
    drop = QDropEvent(QPointF(300, 200), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(window, drop)
    assert wait_for(lambda: len(window.paths) == 11 and not window.jobs), (window.paths, window.notice.text())
    assert len(set(window.paths)) == 11
    assert window.meta[str(fixtures/'Wave.wav')]['sample_rate'] == 96000

    pl = Playlist('Večerní poslech')
    window.playlists.append(pl)
    window.refresh_playlists()
    target = next(w for w in window.playlist_container.findChildren(PlaylistButton) if w.playlist is pl)
    enter = QDragEnterEvent(QPoint(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, enter)
    drop = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, drop)
    assert wait_for(lambda: len(pl.paths) == 11 and not window.jobs)
    window.switch_view(pl)
    window.table.selectRow(0)
    first = pl.paths[0]
    window.reorder_selected(-1)
    assert pl.paths[-1] == first
    window.search_input.setText('Lossless')
    assert len(window.filtered) == 1
    window.search_input.clear()
    # Visible media tabs filter the current playlist, including keyboard access.
    QTest.mouseClick(window.filter_combo, Qt.LeftButton, pos=window.filter_combo.tabRect(2).center())
    assert window.filtered and all(Path(p).suffix in VIDEO_EXTS for p in window.filtered)
    QTest.keyClick(window.filter_combo, Qt.Key_Left)
    assert window.filter_combo.currentIndex() == 1
    assert window.filtered and all(Path(p).suffix not in VIDEO_EXTS for p in window.filtered)
    QTest.keyClick(window.filter_combo, Qt.Key_Left)
    assert len(window.filtered) == 11
    assert not window.result_label.isVisible()
    # Header import uses the existing import flow and preserves deduplication.
    with patch('app.QFileDialog.getOpenFileNames', return_value=([str(fixtures/'MP3.mp3')], '')) as picker:
        QTest.mouseClick(window.import_button, Qt.LeftButton)
        picker.assert_called_once()
    assert wait_for(lambda: not window.jobs)
    assert len(window.paths) == len(pl.paths) == 11
    window.vol_slider.setValue(63)
    window._mute_toggle()
    assert window.audio_output.isMuted() and window.volume == .63
    window._mute_toggle()
    assert not window.audio_output.isMuted() and window.volume == .63

    buffers, frames, player_errors = [], [], []
    buffer_output = QAudioBufferOutput(window)
    window.media_player.setAudioBufferOutput(buffer_output)
    buffer_output.audioBufferReceived.connect(lambda b: buffers.append(b.frameCount()) if b.isValid() else None)
    window.video_widget.video_item.videoSink().videoFrameChanged.connect(lambda f: frames.append(f.size()) if f.isValid() else None)
    window.media_player.errorOccurred.connect(lambda e, text: player_errors.append(text))
    result = {}
    for path in sorted(fixtures.iterdir()):
        buffers.clear()
        frames.clear()
        player_errors.clear()
        window.queue.start([str(path)], str(path))
        window.play_path(str(path))
        video = path.suffix in ('.mp4', '.mkv', '.webm')
        ok = wait_for(lambda: bool(frames if video else buffers) or bool(player_errors))
        result[path.name] = 'PASS' if ok and (frames if video else buffers) else f'FAIL: {player_errors}'
        print(path.name, result[path.name], flush=True)
        if path.suffix == '.mp4' and result[path.name] == 'PASS':
            window.enter_fullscreen()
            app.processEvents()
            assert window.fs_view is not None
            window.fs_view.close()
            assert window.fs_view is None
        window.media_player.stop()

    # View navigation must not replace the active queue.
    window.switch_view(pl)
    window.play_all()
    queue_before = list(window.queue.paths)
    window.switch_view(None)
    assert window.queue.paths == queue_before
    window.media_player.stop()
    window.search_input.setText('MP3')
    window.table.selectRow(0)
    window.play_selected()
    assert wait_for(lambda: window.media_player.duration() > 0)
    window.media_player.pause()
    window.table.setFocus()
    QTest.keyClick(window.table, Qt.Key_Space)
    assert wait_for(lambda: window.is_playing)
    QTest.keyClick(window.table, Qt.Key_Space)
    assert wait_for(lambda: not window.is_playing)
    QTest.mouseClick(window.prog_slider, Qt.LeftButton, pos=QPoint(window.prog_slider.width()//2, 4))
    assert wait_for(lambda: window.media_player.position() >= 700)
    window.search_input.clear()
    window.switch_view(pl)
    app.processEvents()
    window.grab().save(str(ROOT / 'qa' / 'library.png'))
    window.resize(1100, 740)
    app.processEvents()
    window.grab().save(str(ROOT / 'qa' / 'compact.png'))
    QTimer.singleShot(150, lambda: next(w for w in app.topLevelWidgets() if isinstance(w, QDialog)).accept())
    window.show_audio_info()
    # End-of-media advances through the original queue, then stops.
    first, second = str(fixtures/'MP3.mp3'), str(fixtures/'Lossless.flac')
    window.queue.start([first, second], first)
    window.play_path(first)
    assert wait_for(lambda: window.current_path == second)
    assert wait_for(lambda: window.media_player.mediaStatus() == QMediaPlayer.EndOfMedia)
    assert window.queue.current == second
    broken = ROOT / 'qa' / 'broken.mp3'
    broken.write_bytes(b'this is not an audio file')
    window.play_path(str(broken))
    assert wait_for(lambda: window.media_player.error() != QMediaPlayer.NoError)
    assert window.notice.isVisible()
    assert window.save()
    before = list(pl.paths)
    window.close()
    reopened = PulseApp(LibraryStore(ROOT / 'qa' / 'smoke-data'))
    assert reopened.playlists[0].paths == before
    assert reopened.volume == .63
    reopened.close()
    assert not errors, errors
    assert all(r == 'PASS' for r in result.values()), result
    print('UI, drop, deduplication, playlist order, search, volume, seek, fullscreen, persistence: PASS', flush=True)


if __name__ == '__main__':
    main()
