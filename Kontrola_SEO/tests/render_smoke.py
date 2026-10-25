"""Real browser integration against an isolated local fixture (no live websites)."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from seo_checker.engine import audit_url


class Site(BaseHTTPRequestHandler):
    paths = []
    def log_message(self, *args):
        pass
    def do_GET(self):
        self.paths.append(self.path)
        mime = 'text/html; charset=utf-8'
        code = 200
        if self.path == '/robots.txt':
            mime = 'text/plain'
            text = 'User-agent: *\nDisallow: /blocked'
        elif self.path == '/sitemap.xml':
            code, text = 404, ''
        elif self.path == '/redirect':
            text = '<script>location.href="/blocked"</script>'
        elif self.path == '/private-fetch':
            text = '<title>Private test</title><script>fetch("/private-secret").catch(()=>{}); new WebSocket("ws://" + location.host + "/private-ws");</script>'
        elif self.path == '/':
            text = '''<html><head><title>Before</title></head><body><script>
            setTimeout(() => {document.title='Rendered title'; document.body.insertAdjacentHTML('beforeend',
                '<h1>Rendered heading</h1><a href="/js-link">JS link</a><a href="/blocked">Blocked</a>');}, 200);
            </script></body></html>'''
        else:
            text = '<title>Linked page</title><h1>Linked</h1>'
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.end_headers()
        self.wfile.write(text.encode())


def run():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        raw = audit_url(url, limit=4)
        assert raw.pages[0].title == 'Before'
        rendered = audit_url(url, limit=4, rendering=True)
        assert rendered.rendering
        assert rendered.pages[0].title == 'Rendered title'
        assert rendered.pages[0].analysis_mode == 'rendered'
        assert any(p.location.endswith('/js-link') for p in rendered.pages)
        assert '/blocked' not in Site.paths, Site.paths
        redirect = audit_url(url + 'redirect', limit=1, rendering=True)
        assert redirect.pages[0].analysis_mode == 'render_failed'
        assert not redirect.complete
        assert '/blocked' not in Site.paths
        private = audit_url(url + 'private-fetch', limit=1, rendering=True)
        assert private.pages[0].analysis_mode == 'render_failed'
        assert '/private-secret' not in Site.paths
        assert '/private-ws' not in Site.paths
        print('Real browser passed: JS title/headings/links, robots, blocked client navigation, failure evidence, isolated contexts')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    run()
