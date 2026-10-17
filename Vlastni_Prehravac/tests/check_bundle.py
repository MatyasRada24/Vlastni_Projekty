"""Check bundled runtime and startup; uses a separate test library."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parents[1]
executable = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / 'dist' / 'Pulse Music Player.exe'
archive = CArchiveReader(str(executable))
names = list(archive.toc)
manifest = json.loads((root/'vendor'/'ffmpeg'/'manifest.json').read_text(encoding='utf-8'))
for name, digest in manifest['files'].items():
    entries = [n for n in names if n.replace('\\','/').split('/')[-1] == name]
    assert entries, name
    for entry in entries:
        assert hashlib.sha256(archive.extract(entry)).hexdigest() == digest, entry
assert any(n.replace('\\','/').endswith('licenses/ffmpeg/LICENSE.txt') for n in names)
print('Pinned AV1-capable FFmpeg runtime and license in EXE: PASS', flush=True)
for part in ('avcodec-', 'avformat-', 'avutil-', 'swresample-', 'swscale-',
             'ffmpegmediaplugin.dll', 'qwindows.dll'):
    assert any(part in name for name in names), f'Missing packaged runtime: {part}'
print('Qt platform, multimedia plugin and FFmpeg DLLs: PASS', flush=True)

data = root / 'qa' / f'bundle-{time.time_ns()}'
env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PULSE_DATA_DIR=str(data))
proc = subprocess.Popen([str(executable), str(root/'qa'/'media'/'MP3.mp3')], env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW)
try:
    deadline = time.monotonic() + 35
    result = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f'Packaged application exited unexpectedly: {proc.returncode}')
        path = data / 'library.json'
        if path.exists():
            result = json.loads(path.read_text(encoding='utf-8'))
            if len(result['paths']) == 1:
                break
        time.sleep(.25)
    assert result and len(result['paths']) == 1, 'Startup/import did not finish'
    print('Packaged EXE startup, CLI import, asynchronous processing and disk save: PASS', flush=True)
finally:
    # Terminate only the process tree launched by this test (onefile parent + child).
    if proc.poll() is None:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        proc.wait(timeout=10)
