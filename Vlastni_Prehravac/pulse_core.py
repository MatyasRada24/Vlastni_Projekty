"""Local library storage and playback order, independent of the GUI."""
from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path

AUDIO_EXTS = {'.mp3', '.m4a', '.m4b', '.aac', '.flac', '.wav', '.wave', '.ogg',
              '.oga', '.opus', '.wma', '.aif', '.aiff', '.alac', '.ape', '.ac3',
              '.a52', '.eac3', '.dts', '.mka', '.mp2', '.au', '.amr', '.wv'}
VIDEO_EXTS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.wmv', '.m4v', '.mpeg',
              '.mpg', '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.3gp', '.flv'}
ALL_EXTS = AUDIO_EXTS | VIDEO_EXTS


def canonical(path):
    return os.path.normcase(os.path.abspath(os.path.normpath(str(path))))


def unique_paths(paths):
    result, seen = [], set()
    for path in paths:
        if not isinstance(path, str) or not path:
            continue
        key = canonical(path)
        if key not in seen:
            result.append(os.path.abspath(path))
            seen.add(key)
    return result


def discover_files(paths):
    """Expand folders in a stable order; don't traverse directory symlinks."""
    result = []
    for value in unique_paths(paths):
        path = Path(value)
        if path.is_dir():
            for root, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.') and
                                 not os.path.islink(os.path.join(root, d)))
                result.extend(str(Path(root) / name) for name in sorted(files)
                              if Path(name).suffix.lower() in ALL_EXTS)
        elif path.is_file() and path.suffix.lower() in ALL_EXTS:
            result.append(str(path))
    return unique_paths(result)


def atomic_json(path, data):
    """Replace only after the complete new document has reached disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


@dataclass
class Playlist:
    name: str
    paths: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


class LibraryStore:
    def __init__(self, directory=None):
        root = os.environ.get('PULSE_DATA_DIR') or os.path.join(
            os.environ.get('LOCALAPPDATA', str(Path.home())), 'Pulse Player')
        self.directory = Path(directory or root)
        self.path = self.directory / 'library.json'
        self.warnings = []
        self.writable = True

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict) or data.get('version') != 1:
                    raise ValueError('Neznámý formát knihovny')
                if not isinstance(data.get('paths'), list) or not isinstance(data.get('playlists'), list):
                    raise ValueError('Neplatná knihovna')
                playlists = []
                ids = set()
                for pl in data['playlists']:
                    if not isinstance(pl, dict) or not isinstance(pl.get('name'), str) or not isinstance(pl.get('paths'), list):
                        raise ValueError('Neplatný playlist')
                    pid = pl.get('id')
                    if not isinstance(pid, str) or not pid or pid in ids:
                        pid = uuid.uuid4().hex
                    ids.add(pid)
                    playlists.append(Playlist(pl['name'], unique_paths(pl['paths']), pid))
                settings = data.get('settings', {})
                return unique_paths(data['paths']), playlists, settings if isinstance(settings, dict) else {}
            except (OSError, ValueError, TypeError) as error:
                # Never overwrite a damaged original with an empty library.
                self.writable = False
                self.warnings.append(f'Knihovnu nelze načíst: {error}. Původní soubor zůstává zachovaný: {self.path}')
                return [], [], {}
        return self._legacy()

    def _legacy(self):
        paths, playlists, settings = [], [], {}
        if os.environ.get('PULSE_DATA_DIR'):
            return paths, playlists, settings
        old = Path.home() / '.pulse_settings.json'
        if old.exists():
            try:
                data = json.loads(old.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    paths = unique_paths(data.get('paths', []))
                    settings = data
            except (OSError, ValueError, TypeError) as error:
                self.warnings.append(f'Staré nastavení se nepodařilo převést: {error}')
        for file in sorted((Path.home() / 'Documents' / 'Pulse_Playlists').glob('*.json')):
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                pl = Playlist(str(data.get('name') or file.stem), unique_paths(data.get('paths', [])))
                playlists.append(pl)
                paths.extend(pl.paths)
            except (OSError, ValueError, TypeError, AttributeError) as error:
                self.warnings.append(f'Playlist {file.name} nelze převést: {error}')
        return unique_paths(paths), playlists, settings

    def save(self, paths, playlists, settings):
        if not self.writable:
            raise OSError('Ukládání je pozastavené, aby nebyla přepsána poškozená knihovna.')
        atomic_json(self.path, {
            'version': 1, 'paths': unique_paths(paths),
            'playlists': [{'id': p.id, 'name': p.name, 'paths': unique_paths(p.paths)} for p in playlists],
            'settings': settings,
        })


class PlaybackQueue:
    """The active queue stays independent of the browsed library/playlist."""
    def __init__(self):
        self.paths = []
        self.position = -1
        self.shuffle = False
        self.repeat = 'none'
        self.original = []

    @property
    def current(self):
        return self.paths[self.position] if 0 <= self.position < len(self.paths) else None

    def start(self, paths, selected):
        self.original = list(dict.fromkeys(paths))
        self.paths = list(self.original)
        if self.shuffle:
            self.paths.remove(selected)
            random.shuffle(self.paths)
            self.paths.insert(0, selected)
        self.position = self.paths.index(selected)

    def set_shuffle(self, enabled):
        current = self.current
        self.shuffle = enabled
        self.paths = list(self.original)
        if enabled:
            random.shuffle(self.paths)
        if current in self.paths:
            self.paths.remove(current)
            if enabled:
                self.paths.insert(0, current)
            else:
                self.paths = list(self.original)
            self.position = self.paths.index(current)

    def advance(self, step=1, automatic=False):
        if not self.paths:
            return None
        if automatic and self.repeat == 'one':
            return self.current
        nxt = self.position + step
        if nxt >= len(self.paths) or nxt < 0:
            if self.repeat == 'all':
                nxt %= len(self.paths)
            else:
                return None
        self.position = nxt
        return self.current

    def remove(self, path):
        if path not in self.paths:
            return
        index = self.paths.index(path)
        self.paths.remove(path)
        self.original.remove(path)
        if index <= self.position:
            self.position -= 1
