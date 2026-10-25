"""Verify Playwright and its driver inside the delivered EXE."""
import json
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from tests.render_smoke import Site
from tests.test_engine import temporary_directory


def run():
    exe = Path('dist/Kontrola_SEO_1.0.exe').resolve()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with temporary_directory() as folder:
            output = Path(folder) / 'packaged-report.json'
            subprocess.run([str(exe), '--audit-url', f'http://127.0.0.1:{server.server_port}/',
                            '--render-js', '--limit', '4', '--output', str(output)],
                           timeout=60, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            data = json.loads(output.read_text(encoding='utf-8'))
            assert data['rendering']
            assert data['pages'][0]['title'] == 'Rendered title'
            assert data['pages'][0]['analysis_mode'] == 'rendered'
            assert data['pages'][0]['headings'] == [[1, 'Rendered heading']]
            assert '/js-link' in data['pages'][0]['source_links']
            assert any(p['location'].endswith('/js-link') for p in data['pages'])
            assert '/blocked' not in Site.paths
        print('Packaged EXE passed: bundled browser driver, JavaScript audit, discovered links and JSON export')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    run()
