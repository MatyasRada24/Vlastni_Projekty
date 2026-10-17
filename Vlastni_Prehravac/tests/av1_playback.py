"""AV1 audio/video, 8/10-bit, seek/pause/fullscreen regression test."""
import os
import sys
import time
import json
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app import PulseApp
from pulse_core import LibraryStore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QAudioBufferOutput, QMediaPlayer
import imageio_ffmpeg

def wait_for(predicate, seconds=12):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(.01)
    return False

def main():
    folder = ROOT / 'qa' / 'av1-regression-media'
    folder.mkdir(exist_ok=True)
    cases = [('mp4','yuv420p','aac'),('mp4','yuv420p10le','aac'),
             ('mkv','yuv420p10le','aac'),('webm','yuv420p','libopus')]
    paths = []
    for ext, pixels, audio in cases:
        path = folder / f'av1-{pixels}.{ext}'
        if not path.exists():
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y',
                '-f','lavfi','-i','testsrc2=size=640x360:rate=25','-f','lavfi','-i',
                'sine=frequency=440:sample_rate=48000','-t','3','-c:v','libaom-av1',
                '-cpu-used','8','-crf','40','-threads','2','-pix_fmt',pixels,'-c:a',audio,
                str(path)],check=True,timeout=90)
        paths.append(path)
    app = QApplication([])
    window = PulseApp(LibraryStore(ROOT/'qa'/'av1-playback-data'))
    window.setAttribute(Qt.WA_DontShowOnScreen)
    window.show()
    window.audio_output.setMuted(True)
    audio_output = QAudioBufferOutput(window)
    window.media_player.setAudioBufferOutput(audio_output)
    buffers, images, errors = [], [], []
    audio_output.audioBufferReceived.connect(lambda b: buffers.append(b.frameCount()) if b.isValid() else None)
    window.video_widget.video_item.videoSink().videoFrameChanged.connect(
        lambda f: images.append(not f.toImage().isNull()) if f.isValid() else None)
    window.media_player.errorOccurred.connect(lambda e,t: errors.append(t))
    result = []
    for path in paths:
        buffers.clear(); images.clear(); errors.clear()
        window.queue.start([str(path)],str(path))
        window.play_path(str(path))
        assert wait_for(lambda: buffers and images), (path,errors)
        assert all(images), path
        window.media_player.pause()
        assert wait_for(lambda: not window.is_playing)
        count = len(images)
        window.media_player.setPosition(1500)
        window.media_player.play()
        assert wait_for(lambda: len(images)>count and window.media_player.position()>=1500)
        window.enter_fullscreen()
        app.processEvents()
        assert window.fs_view is not None
        window.fs_view.close()
        assert wait_for(lambda: window.media_player.mediaStatus()==QMediaPlayer.EndOfMedia)
        assert not errors, errors
        result.append(dict(file=path.name,audio_frames=sum(buffers),video_frames=len(images),
                           decoded_images=all(images),seek=True,fullscreen=True,status='PASS'))
        print(path.name,'PASS',flush=True)
    window.close()
    (ROOT/'qa'/'av1-playback-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__ == '__main__':
    main()
