"""Load the pinned FFmpeg runtime before Qt selects a multimedia backend."""
import ctypes
import os
import sys
from pathlib import Path

DLL_NAMES = ('avutil-59.dll', 'swresample-5.dll', 'swscale-8.dll',
             'avcodec-61.dll', 'avformat-61.dll')
_libraries = []
_directory = None


def prepare_media_runtime():
    global _directory
    if sys.platform != 'win32' or _libraries:
        return
    # Qt 6.11 can open a hardware AV1 decoder on an unsupported GPU and then
    # emit no frames instead of retrying dav1d. Use software decoding by default
    # for deterministic playback; rendering still uses Qt's normal video path.
    os.environ.setdefault('QT_FFMPEG_DECODING_HW_DEVICE_TYPES', ',')
    root = (Path(sys._MEIPASS) / 'PySide6' if getattr(sys, 'frozen', False)
            else Path(__file__).resolve().parent / 'vendor' / 'ffmpeg')
    missing = [name for name in DLL_NAMES if not (root / name).is_file()]
    if missing:
        raise RuntimeError('Chybí knihovny přehrávače. Spusťte tools/setup_ffmpeg.py: ' + ', '.join(missing))
    _directory = os.add_dll_directory(str(root))
    # Explicit absolute paths avoid loading Qt's reduced build or an unrelated
    # FFmpeg installation via PATH. Keep handles alive for the process lifetime.
    for name in DLL_NAMES:
        _libraries.append(ctypes.CDLL(str(root / name)))
    codec = _libraries[3]
    codec.avcodec_find_decoder_by_name.argtypes = [ctypes.c_char_p]
    codec.avcodec_find_decoder_by_name.restype = ctypes.c_void_p
    if not codec.avcodec_find_decoder_by_name(b'libdav1d'):
        raise RuntimeError('Knihovny přehrávače neobsahují požadovaný dekodér AV1 (dav1d).')
