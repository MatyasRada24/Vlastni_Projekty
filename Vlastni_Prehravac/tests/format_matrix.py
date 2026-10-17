"""Import and decode every advertised extension using the real Pulse UI/backend.

Development-only: imageio-ffmpeg. Fixtures are synthetic except the separately
downloaded APE sample from https://samples.ffmpeg.org/A-codecs/lossless/luckynight.ape.
No user library is opened. Results are written under qa/format-*.
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['PULSE_DATA_DIR'] = str(ROOT / 'qa' / 'format-data')
import imageio_ffmpeg
from PySide6.QtCore import Qt, QUrl, QMimeData, QPoint, QPointF
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioBufferOutput
from app import PulseApp, PlaylistButton
from pulse_core import ALL_EXTS, Playlist, LibraryStore

MEDIA = ROOT / 'qa' / 'format-media'
CASES = []


def audio(ext, codec, mux, extra=(), name=None):
    CASES.append(dict(name=name or codec, ext=ext, audio=codec, video=None,
                      mux=mux, extra=list(extra)))


def video(ext, codec='libx264', acodec='aac', mux='mp4', extra=(), name=None):
    CASES.append(dict(name=name or codec, ext=ext, audio=acodec, video=codec,
                      mux=mux, extra=list(extra)))


for ext, codec, mux in [
    ('mp3','libmp3lame','mp3'), ('m4a','aac','ipod'), ('m4b','aac','ipod'),
    ('aac','aac','adts'), ('flac','flac','flac'), ('wav','pcm_s24le','wav'),
    ('wave','pcm_s16le','wav'), ('ogg','libvorbis','ogg'), ('oga','libvorbis','ogg'),
    ('opus','libopus','opus'), ('wma','wmav2','asf'), ('aif','pcm_s16be','aiff'),
    ('aiff','pcm_s24be','aiff'), ('alac','alac','ipod'), ('ac3','ac3','ac3'),
    ('a52','ac3','ac3'), ('eac3','eac3','eac3'), ('mka','flac','matroska'),
    ('mp2','mp2','mp2'), ('au','pcm_s16be','au'), ('wv','wavpack','wv')]:
    audio(ext,codec,mux)
audio('dts','dca','dts', ['-strict','-2'])
audio('amr','libopencore_amrnb','amr', ['-ar','8000','-ac','1','-b:a','12.2k'])
CASES.append(dict(name='monkeys-audio',ext='ape',audio='ape',video=None,mux='ape',external=True))
for ext in ('mp4','mov','m4v'):
    video(ext)
video('mkv',mux='matroska')
video('webm','libvpx-vp9','libopus','webm')
video('avi','mpeg4','libmp3lame','avi')
video('wmv','wmv2','wmav2','asf')
for ext in ('mpeg','mpg'):
    video(ext,'mpeg2video','mp2','mpeg')
for ext in ('ts','mts','m2ts'):
    video(ext,'libx264','ac3','mpegts')
video('vob','mpeg2video','ac3','vob')
video('ogv','libtheora','libvorbis','ogg')
video('3gp','h263','libopencore_amrnb','3gp',['-ar','8000','-ac','1','-b:a','12.2k'])
video('flv','flv','libmp3lame','flv')
# Additional common codecs/profiles in shared containers.
audio('m4a','alac','ipod')
audio('amr','libvo_amrwbenc','amr',['-ar','16000','-ac','1','-b:a','23.85k'])
audio('wav','pcm_f32le','wav',name='float32')
audio('flac','flac','flac',['-ar','96000','-sample_fmt','s32'],name='24bit-96k')
audio('ogg','libopus','ogg')
video('mkv','libx265','aac','matroska', ['-preset','ultrafast'],name='hevc')
video('mp4','libx265','aac','mp4',['-preset','ultrafast','-tag:v','hvc1'],name='hevc')
video('mkv','libx265','aac','matroska',['-preset','ultrafast','-pix_fmt','yuv420p10le'],name='hevc10')
video('webm','libvpx','libvorbis','webm',name='vp8')
video('mp4','libaom-av1','aac','mp4',['-cpu-used','8'],name='av1')
video('avi','mjpeg','pcm_s16le','avi',['-pix_fmt','yuvj420p'],name='mjpeg')
video('mov','prores_ks','pcm_s16le','mov',['-pix_fmt','yuv422p10le'],name='prores')
assert {'.'+c['ext'] for c in CASES} == ALL_EXTS


def wait_for(predicate, timeout):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(.01)
    return False


def drop(target, path):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    enter = QDragEnterEvent(QPoint(10,10),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
    QApplication.sendEvent(target,enter)
    event = QDropEvent(QPointF(10,10),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
    QApplication.sendEvent(target,event)
    return enter.isAccepted() and event.isAccepted()


def main():
    MEDIA.mkdir(parents=True,exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    selected = [c for c in CASES if len(sys.argv)==1 or c['ext'] in sys.argv[1:]]
    results = []
    if len(sys.argv)>1 and (ROOT/'qa'/'format-results.json').exists():
        previous = json.loads((ROOT/'qa'/'format-results.json').read_text(encoding='utf-8'))
        results = [r for r in previous['results'] if r['ext'] not in sys.argv[1:]]
    for case in selected:
        case['path'] = str(MEDIA / (case['name']+'.'+case['ext']))
        path = Path(case['path'])
        if case.get('external'):
            case['fixture_ok'] = path.exists()
            continue
        command = [ffmpeg,'-hide_banner','-loglevel','error','-y']
        if case['video']:
            command += ['-f','lavfi','-i','testsrc2=size=176x144:rate=25']
        command += ['-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','1.2']
        if case['video']:
            command += ['-c:v',case['video'],'-pix_fmt','yuv420p','-threads','2']
        command += ['-c:a',case['audio'],'-ac','2',*case['extra'],'-f',case['mux'],str(path)]
        process = subprocess.run(command,capture_output=True,text=True,timeout=90)
        case['fixture_ok'] = process.returncode == 0
        if process.returncode:
            case['generation_error'] = process.stderr[-2000:]
        print('FIXTURE',path.name,'OK' if case['fixture_ok'] else 'FAILED',flush=True)

    app = QApplication([])
    store = LibraryStore(ROOT / 'qa' / 'format-data')
    store.save([],[],{})
    window = PulseApp(store)
    window.setAttribute(Qt.WA_DontShowOnScreen)
    window.show()
    window.audio_output.setMuted(True)
    app.processEvents()
    exceptions = []
    sys.excepthook = lambda kind,value,tb: exceptions.append(str(value))
    accepted = drop(window,MEDIA)
    assert wait_for(lambda: not window.jobs,20)
    playlist = Playlist('Test všech formátů')
    window.playlists.append(playlist)
    window.refresh_playlists()
    target = next(b for b in window.playlist_container.findChildren(PlaylistButton) if b.playlist is playlist)
    playlist_drop = drop(target,MEDIA)
    assert wait_for(lambda: not window.jobs,20)
    output = QAudioBufferOutput(window)
    window.media_player.setAudioBufferOutput(output)
    audio_frames,video_frames,errors = [],[],[]
    output.audioBufferReceived.connect(lambda b: audio_frames.append(b.frameCount()) if b.isValid() else None)
    window.video_widget.video_item.videoSink().videoFrameChanged.connect(lambda f: video_frames.append(f.size().toTuple()) if f.isValid() else None)
    window.media_player.errorOccurred.connect(lambda e,s: errors.append(s))
    for case in selected:
        result = {k:v for k,v in case.items() if k not in ('extra',)}
        result['platform'] = QApplication.platformName()
        result['import'] = accepted and case['path'] in window.paths
        result['playlist'] = playlist_drop and case['path'] in playlist.paths
        if not case['fixture_ok']:
            result['status'] = 'UNTESTED'
        else:
            window.media_player.stop()
            app.processEvents()
            audio_frames.clear(); video_frames.clear(); errors.clear()
            window.queue.start([case['path']],case['path'])
            window.play_path(case['path'])
            finished = wait_for(lambda: errors or window.media_player.mediaStatus()==QMediaPlayer.EndOfMedia, 90 if case.get('external') else 12)
            result.update(audio_frames=sum(audio_frames), video_frames=len(video_frames),
                          duration_ms=window.media_player.duration(),errors=list(errors),
                          reached_end=window.media_player.mediaStatus()==QMediaPlayer.EndOfMedia)
            result['status'] = 'PASS' if (result['import'] and result['playlist'] and audio_frames
                and (video_frames or not case['video']) and finished and result['reached_end'] and not errors) else 'FAIL'
        results.append(result)
        print('PLAY',Path(case['path']).name,result['status'],result.get('errors',[]),flush=True)
        (ROOT/'qa'/'format-results.json').write_text(json.dumps(dict(results=results,exceptions=exceptions),ensure_ascii=False,indent=2),encoding='utf-8')
    window.close()
    lines = ['# Ověření formátů Pulse Player','',
        'Datum kontroly: 16. 10. 2026. Pokryto všech 40 přípon uvedených v aplikaci a 52 konkrétních kombinací kontejneru/kodeku.','',
        'Test skutečného importu přetažením do knihovny i playlistu a dekódování až do konce souboru. Zvuk je ztlumený; kontrolují se dekódované audio buffery a u videa také snímky. Uživatelská knihovna se nepoužívá.','',
        'Syntetické vzorky mají 1,2 s. APE je celý vzorek [FFmpeg](https://samples.ffmpeg.org/A-codecs/lossless/luckynight.ape). ALAC s příponou .alac je uložen v kontejneru MP4. Výsledek platí pro uvedené kombinace, nikoli všechny možné kodeky/profily, poškozené nebo DRM soubory.','',
        '| Soubor | Kontejner | Video / zvuk | Import / playlist | Audio snímky | Video snímky | Do konce | Výsledek |',
        '|---|---|---|---|---:|---:|---|---|']
    for r in results:
        lines.append(f"| {Path(r['path']).name} | {r['mux']} | {r['video'] or '—'} / {r['audio']} | {r['import']} / {r['playlist']} | {r.get('audio_frames',0)} | {r.get('video_frames',0)} | {r.get('reached_end',False)} | {r['status']} |")
        if r.get('errors') or r.get('generation_error'):
            lines.append('\nChyba: '+str(r.get('errors') or r.get('generation_error'))+'\n')
    (ROOT/'qa'/'format-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('SUMMARY', {status:sum(r['status']==status for r in results) for status in ('PASS','FAIL','UNTESTED')}, 'exceptions:',exceptions,flush=True)
    raise SystemExit(0 if not exceptions and all(r['status']=='PASS' for r in results) else 1)


if __name__ == '__main__':
    main()
