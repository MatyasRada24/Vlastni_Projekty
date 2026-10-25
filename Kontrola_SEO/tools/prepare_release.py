"""Create a source release from an allowlist, never by zipping the workspace."""
from pathlib import Path
import hashlib
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['main.py', 'requirements.txt', 'README.md', 'GOOGLE_SETUP.md', 'SECURITY.md',
         '.gitignore', 'build_windows.ps1', 'windows.manifest', 'Spustit_Kontrola_SEO.bat']
SECRET = re.compile(rb'AIza[0-9A-Za-z_-]{30,}|GOCSPX-[0-9A-Za-z_-]{15,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')

def run():
    from seo_checker import __version__
    files = [ROOT / name for name in NAMES]
    for directory in ['seo_checker', 'tests', 'tools']:
        files.extend(sorted((ROOT / directory).rglob('*.py')))
    for path in files:
        if path.is_symlink() or SECRET.search(path.read_bytes()):
            raise RuntimeError('Release blocked: inspect ' + str(path.relative_to(ROOT)))
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'Kontrola_SEO_{__version__}_source.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, path.relative_to(ROOT).as_posix())
    exe = output / f'Kontrola_SEO_{__version__}.exe'
    artifacts = [archive, exe] if exe.exists() else [archive]
    (output / 'SHA256SUMS.txt').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in artifacts), encoding='utf-8')
    print(f'Source release checked: {len(files)} files; credentials and private data excluded.')

if __name__ == '__main__':
    run()
