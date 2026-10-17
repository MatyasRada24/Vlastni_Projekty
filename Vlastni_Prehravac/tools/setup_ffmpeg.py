"""Fetch the pinned LGPL FFmpeg build, verify it and install only required DLLs."""
import hashlib
import io
import json
from pathlib import Path
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1] / 'vendor' / 'ffmpeg'


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    def valid(name, digest):
        path = ROOT / name
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
    if all(valid(n, h) for n, h in manifest['files'].items()):
        print('Pinned FFmpeg runtime: verified')
        return
    with urllib.request.urlopen(manifest['url'], timeout=120) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != manifest['sha256']:
        raise RuntimeError('FFmpeg archive checksum mismatch')
    with ZipFile(io.BytesIO(archive)) as bundle:
        payloads = {}
        for name, digest in manifest['files'].items():
            entries = [n for n in bundle.namelist() if n.endswith('/bin/' + name)]
            if len(entries) != 1:
                raise RuntimeError('Missing or ambiguous DLL: ' + name)
            data = bundle.read(entries[0])
            if hashlib.sha256(data).hexdigest() != digest:
                raise RuntimeError('FFmpeg DLL checksum mismatch: ' + name)
            payloads[name] = data
        for name, data in payloads.items():
            temporary = ROOT / (name + '.tmp')
            temporary.write_bytes(data)
            temporary.replace(ROOT / name)
    print('Pinned FFmpeg runtime: installed and verified')


if __name__ == '__main__':
    main()
