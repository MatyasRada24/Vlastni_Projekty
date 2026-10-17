# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys
import json
import hashlib
import PySide6

# Multimedia hooks collect Qt plugins; list FFmpeg runtime DLLs explicitly.
qt_dir = Path(PySide6.__file__).parent
runtime_dir = Path(SPECPATH) / 'vendor' / 'ffmpeg'
manifest = json.loads((runtime_dir / 'manifest.json').read_text(encoding='utf-8'))
for name, digest in manifest['files'].items():
    path = runtime_dir / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Missing or modified FFmpeg runtime; run tools/setup_ffmpeg.py: ' + name)
# Build hosts may inject tools such as Poppler into PATH. Their icuuc.dll is
# incompatible with the Windows system ICU used by Qt. Limit DLL discovery to
# this Python/Qt environment and Windows, rather than unrelated tool runtimes.
windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
os.environ['PATH'] = os.pathsep.join(map(str, [
    runtime_dir, qt_dir, qt_dir.parent / 'shiboken6', Path(sys.executable).parent,
    Path(sys.base_prefix), windows / 'System32', windows,
]))
ffmpeg_dlls = [(str(runtime_dir / name), 'PySide6') for name in manifest['files'] if name.endswith('.dll')]

a = Analysis(['app.py'], pathex=[], binaries=ffmpeg_dlls,
    datas=[('assets', 'assets'), (str(runtime_dir / 'LICENSE.txt'), 'licenses/ffmpeg'),
           (str(runtime_dir / 'NOTICE.md'), 'licenses/ffmpeg'),
           (str(runtime_dir / 'manifest.json'), 'licenses/ffmpeg')], hiddenimports=[], hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=['tkinter', 'customtkinter'], noarchive=False, optimize=0)
# Qt's hook also discovers the reduced FFmpeg build in site-packages. Replace
# every occurrence, including dependency-discovered duplicates, with our pin.
a.binaries = [(dest, str(runtime_dir / Path(dest).name), kind)
              if Path(dest).name in manifest['files'] else (dest, source, kind)
              for dest, source, kind in a.binaries]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='Pulse Music Player', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=['assets/icon.ico'])
