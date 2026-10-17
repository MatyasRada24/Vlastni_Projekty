# FFmpeg runtime for Pulse Player

Pinned BtbN LGPL shared build: FFmpeg 7.1.3-42-g39ee683e8f, Windows x64.
The archive and individual library SHA-256 hashes are in manifest.json. The
archive hash was checked against the publisher's checksums.sha256.

- Binary release and checksums: https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-02-28-12-59
- Build recipes and dependency sources: https://github.com/BtbN/FFmpeg-Builds
- FFmpeg source revision: https://github.com/FFmpeg/FFmpeg/tree/39ee683e8f
- FFmpeg licensing: https://ffmpeg.org/legal.html
- dav1d software AV1 decoder: https://code.videolan.org/videolan/dav1d

These unmodified shared libraries replace Qt's reduced FFmpeg build, which
lacks a software AV1 decoder. FFmpeg is distributed under LGPL; see LICENSE.txt.
Additional third-party components retain their respective upstream licenses.
Libraries are dynamically loaded and can be replaced with ABI-compatible ones.
The application requires avcodec 61, avformat 61, avutil 59, swresample 5,
swscale 8 and an available libdav1d decoder.

Qt 6.11.2 does not reliably fall back after an unsupported hardware AV1 decoder
has opened. Pulse defaults to software video decoding (no transcoding). This
can increase CPU consumption for high-resolution video. The private Qt setting
is documented at https://doc.qt.io/qt-6/advanced-ffmpeg-configuration.html and
must be retested when updating Qt. No changes are made to Windows settings.
