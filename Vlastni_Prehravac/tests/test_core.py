import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pulse_core import LibraryStore, Playlist, PlaybackQueue, atomic_json, discover_files, canonical


class StorageTests(unittest.TestCase):
    def test_restart_retains_order_unicode_missing_files_and_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LibraryStore(folder)
            paths = [str(Path(folder) / 'žlutá.mp3'), str(Path(folder) / 'absent.mp4')]
            playlists = [Playlist('Večerní poslech', paths[::-1])]
            store.save(paths, playlists, {'volume': .67, 'repeat_mode': 'all'})
            loaded, pls, settings = LibraryStore(folder).load()
            self.assertEqual(loaded, paths)
            self.assertEqual(pls[0], playlists[0])
            self.assertEqual(settings['volume'], .67)

    def test_corrupt_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LibraryStore(folder)
            store.path.write_text('{broken', encoding='utf-8')
            self.assertEqual(store.load(), ([], [], {}))
            with self.assertRaises(OSError):
                store.save([], [], {})
            self.assertEqual(store.path.read_text(), '{broken')

    def test_failed_atomic_replace_preserves_previous_library(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'library.json'
            atomic_json(path, {'before': 1})
            with patch('pulse_core.os.replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    atomic_json(path, {'after': 2})
            self.assertEqual(json.loads(path.read_text()), {'before': 1})
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])

    def test_folder_import_filters_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'nested').mkdir()
            for name in ('audio.MP3', 'clip.mp4', 'readme.txt', 'nested/lossless.flac'):
                (root / name).touch()
            found = discover_files([folder, str(root / 'audio.MP3'), folder])
            self.assertEqual(len(found), 3)
            self.assertEqual(len(set(map(canonical, found))), 3)

    def test_legacy_migration_leaves_originals_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            old = home / '.pulse_settings.json'
            old.write_text(json.dumps({'paths': [str(home/'one.mp3')], 'volume': .6}))
            pl_dir = home / 'Documents' / 'Pulse_Playlists'
            pl_dir.mkdir(parents=True)
            (pl_dir/'old.json').write_text(json.dumps({'name': 'Old', 'paths': [str(home/'two.mp3')]}))
            with patch('pulse_core.Path.home', return_value=home), patch.dict(os.environ, {}, clear=True):
                store = LibraryStore(home / 'new')
                paths, playlists, settings = store.load()
                store.save(paths, playlists, settings)
            self.assertEqual(len(paths), 2)
            self.assertEqual(playlists[0].name, 'Old')
            self.assertTrue(old.exists())
            self.assertTrue((pl_dir/'old.json').exists())


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.queue = PlaybackQueue()

    def test_queue_is_snapshot_not_browsed_playlist(self):
        paths = ['a', 'b', 'c']
        self.queue.start(paths, 'a')
        paths.clear()
        self.assertEqual(self.queue.advance(), 'b')

    def test_repeat_one_only_repeats_automatically(self):
        self.queue.start(['a', 'b'], 'a')
        self.queue.repeat = 'one'
        self.assertEqual(self.queue.advance(automatic=True), 'a')
        self.assertEqual(self.queue.advance(), 'b')

    def test_shuffle_visits_each_track_once_then_stops(self):
        self.queue.shuffle = True
        self.queue.start(['a', 'b', 'c', 'd'], 'c')
        visited = [self.queue.current]
        while (value := self.queue.advance()) is not None:
            visited.append(value)
        self.assertEqual(visited[0], 'c')
        self.assertEqual(sorted(visited), ['a', 'b', 'c', 'd'])

    def test_repeat_all_wraps_and_shuffle_toggle_preserves_current(self):
        self.queue.start(['a', 'b', 'c'], 'c')
        self.queue.repeat = 'all'
        self.assertEqual(self.queue.advance(), 'a')
        self.queue.set_shuffle(True)
        self.assertEqual(self.queue.current, 'a')
        self.queue.set_shuffle(False)
        self.assertEqual(self.queue.advance(), 'b')

    def test_removing_prior_track_does_not_skip_next(self):
        self.queue.start(['a', 'b', 'c'], 'b')
        self.queue.remove('a')
        self.assertEqual(self.queue.current, 'b')
        self.assertEqual(self.queue.advance(), 'c')


if __name__ == '__main__':
    unittest.main()
