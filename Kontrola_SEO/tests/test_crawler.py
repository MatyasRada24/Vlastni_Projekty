import gzip
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from seo_checker.engine import audit_url
from seo_checker.planning import compare_reports
from seo_checker.crawler import crawl_selected


class DeepServer(BaseHTTPRequestHandler):
    paths = []
    fixed = False

    def do_GET(self):
        self.paths.append(self.path)
        base = f"http://127.0.0.1:{self.server.server_port}"
        status, mime, text = 200, "text/html; charset=utf-8", ""
        redirects = {"/chain": "/middle", "/middle": "/final", "/loop": "/loop2", "/loop2": "/loop", "/redirect-blocked": "/blocked", "/external": "https://outside.invalid/"}
        if self.path in redirects:
            self.send_response(302)
            self.send_header("Location", redirects[self.path])
            self.end_headers()
            return
        if self.path == "/robots.txt":
            mime, text = "text/plain", f"User-agent: *\nDisallow: /blocked\nSitemap: {base}/sitemap-index.xml\n"
        elif self.path == "/sitemap-index.xml":
            mime = "application/xml"
            text = f'<sitemapindex><sitemap><loc>{base}/nested.xml.gz</loc></sitemap><sitemap><loc>{base}/sitemap-index.xml</loc></sitemap></sitemapindex>'
        elif self.path == "/nested.xml.gz":
            mime = "application/gzip"
            text = gzip.compress(f'<urlset><url><loc>{base}/only-map</loc></url><url><loc>{base}/noindex</loc></url></urlset>'.encode())
        else:
            canonical = "/noindex" if self.path == "/canonical-src" else "/blocked" if self.path == "/canon-blocked" else self.path
            body = ""
            if self.path == "/":
                body = ''.join(f'<a href="{url}">Link</a>' for url in ["/broken", "/chain", "/loop", "/canonical-src", "/canon-blocked", "/redirect-blocked", "/external", "/query?a=1"])
            if self.path == "/broken" and not self.fixed:
                status = 404
            noindex = '<meta name="robots" content="noindex">' if self.path == "/noindex" else ""
            text = f'<html lang="cs"><head><title>{self.path}</title><meta name="description" content="{self.path}"><link rel="canonical" href="{base}{canonical}">{noindex}</head><body><h1>Page</h1>{body}</body></html>'
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(text if isinstance(text, bytes) else text.encode())

    def log_message(self, *args):
        pass


class DeepCrawlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DeepServer)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        DeepServer.paths.clear()
        DeepServer.fixed = False

    def test_nested_sitemap_links_canonical_redirects_and_provenance(self):
        report = audit_url(self.base, limit=40)
        pages = {p.location.removeprefix(self.base): p for p in report.pages}
        self.assertIn("/only-map", pages)
        self.assertIn(self.base + "/nested.xml.gz", pages["/only-map"].sitemap_sources)
        self.assertEqual(DeepServer.paths.count("/sitemap-index.xml"), 1)
        self.assertEqual(pages["/broken"].inbound, [self.base + "/"])
        broken = next(f for f in pages["/"].findings if f.rule == "link.broken" and f.target.endswith("/broken"))
        self.assertEqual(broken.status, "Chyba")
        self.assertEqual(len(pages["/chain"].redirects), 3)
        self.assertTrue(any(f.rule == "redirect.chain" and f.status == "Doporučení" for f in pages["/chain"].findings))
        self.assertTrue(any(f.rule == "redirect.loop" for f in pages["/loop"].findings))
        self.assertTrue(any(f.rule == "canonical.target" and f.status == "Chyba" for f in pages["/canonical-src"].findings))
        self.assertTrue(any(f.rule == "sitemap.indexability" for f in pages["/noindex"].findings))
        self.assertNotIn("/blocked", DeepServer.paths)
        self.assertTrue(any(f.rule == "canonical.target" and f.status == "Neověřeno" for f in pages["/canon-blocked"].findings))
        self.assertTrue(any(f.status == "Neověřeno" for f in pages["/redirect-blocked"].findings))
        self.assertFalse(any(f.status == "Chyba" for f in pages["/external"].findings))

    def test_limit_and_cancel_never_claim_unvisited_issues_fixed(self):
        old = audit_url(self.base, limit=40)
        new = audit_url(self.base, limit=1)
        self.assertFalse(new.complete)
        self.assertGreater(new.discovered, len(new.pages))
        delta = compare_reports(old, new)
        self.assertFalse(any(f.rule == "link.broken" for p, f in delta["Odstraněné"]))
        event = threading.Event()
        event.set()
        cancelled = audit_url(self.base, cancel=event)
        self.assertFalse(cancelled.complete)
        self.assertFalse(cancelled.pages)

    def test_fixed_target_resolves_http_and_source_link(self):
        old = audit_url(self.base, limit=40)
        DeepServer.fixed = True
        new = audit_url(self.base, limit=40)
        removed = compare_reports(old, new)["Odstraněné"]
        self.assertTrue(any(f.rule == "link.broken" and f.target.endswith("/broken") for p, f in removed))
        self.assertTrue(any(f.rule == "HTTP odpověď" and p.location.endswith("/broken") for p, f in removed))

    def test_targeted_recheck_dependencies_and_no_sitemap_crawl(self):
        report = crawl_selected(self.base, [self.base + '/canonical-src'])
        self.assertEqual([p.location for p in report.pages], [self.base + '/canonical-src'])
        self.assertIn('/noindex', DeepServer.paths)
        self.assertNotIn('/sitemap-index.xml', DeepServer.paths)
        self.assertNotIn('/', DeepServer.paths)
        self.assertFalse(report.complete)
        self.assertTrue(any(f.rule == 'canonical.target' and f.status == 'Chyba' for f in report.pages[0].findings))
        old = crawl_selected(self.base, [self.base + '/'])
        DeepServer.fixed = True
        new = crawl_selected(self.base, [self.base + '/'])
        self.assertTrue(any(f.rule == 'link.broken' and f.target.endswith('/broken')
                            for _, f in compare_reports(old, new)['Odstraněné']))
        self.assertNotIn('/blocked', DeepServer.paths)
        self.assertNotIn('/only-map', DeepServer.paths)
