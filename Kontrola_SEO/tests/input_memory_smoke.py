"""Exercise remembered input across independent application processes."""
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

from seo_checker.app import Application
from seo_checker.storage import Store
from tests.test_engine import temporary_directory


def phase(database, number):
    root = tk.Tk()
    root.withdraw()
    app = Application(root, database=database)
    try:
        if number == 'write':
            assert app.url.get() == '' and app.limit.get() == '100'
            app.url.set('https://example.test/článek?a=1&b=2')
            app.path.set('C:/Weby/Můj web/index.html')
            app.mode.set('Soubory')
            app.limit.set('250')
            app.rendering.set(True)
            deadline = time.monotonic() + .8
            while time.monotonic() < deadline:
                root.update()
                time.sleep(.02)
            with_check = Store(database)
            assert with_check.get_setting('audit_inputs')['limit'] == '250'
            with_check.close()
        elif number == 'reopen':
            assert app.url.get() == 'https://example.test/článek?a=1&b=2'
            assert app.path.get() == 'C:/Weby/Můj web/index.html'
            assert app.mode.get() == 'Soubory' and app.files_frame.winfo_manager() == 'pack'
            assert app.url_frame.winfo_manager() == ''
            assert app.limit.get() == '250' and app.rendering.get()
            assert not app.running and app.report is None
            app.mode.set('URL')
            app.url.set('')
            app.rendering.set(False)
            # Close before the debounce timer: the explicit clearing must persist.
        else:
            assert app.url.get() == '' and app.mode.get() == 'URL'
            assert not app.rendering.get()
            assert app.limit.get() == '250'
            assert app.store.projects() == []
    finally:
        app.close()


if __name__ == '__main__':
    if len(sys.argv) == 3:
        phase(sys.argv[1], sys.argv[2])
    else:
        with temporary_directory() as folder:
            database = str(Path(folder) / 'settings.sqlite3')
            for step in ('write', 'reopen', 'cleared'):
                subprocess.run([sys.executable, '-m', 'tests.input_memory_smoke', database, step], check=True, timeout=20)
        print('Remembered inputs passed: autosave, restart, local-file mode, close flush, cleared values, no automatic audit')
