import json
import shutil
import threading
import unittest
import uuid
import zipfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from seo_checker.engine import analyze_html, audit_local, audit_url, decode_html, normalize_url
from seo_checker.export import save_report


@contextmanager
def temporary_directory():
    # mkdir's default permissions also work in a restricted Windows sandbox.
    workspace = Path(__file__).resolve().parents[1]
    directory = workspace / (".test-" + uuid.uuid4().hex)
    directory.mkdir()
    try:
        yield str(directory)
    finally:
        resolved = directory.resolve()
        if resolved.parent == workspace and resolved.name.startswith(".test-"):
            shutil.rmtree(resolved)


GOOD = '''<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>Testovací stránka</title><meta name="description" content="Popis stránky.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.com/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Hlavní <em>nadpis</em></h1><h2>Obsah</h2><p>Ukázkový obsah.</p>
<img src="photo.jpg" alt="Popis fotografie"></body></html>'''


def findings(page, name):
    return [f for f in page.findings if f.name == name]


class AnalysisTests(unittest.TestCase):
    def test_good_html(self):
        page, doc = analyze_html(GOOD, "test.html")
        self.assertFalse(any(f.status == "Chyba" for f in page.findings))
        self.assertEqual(page.title, "Testovací stránka")
        self.assertEqual(doc.headings[0], (1, "Hlavní nadpis"))
        self.assertEqual(page.words, 5)
        self.assertEqual(findings(page, "Nastavení živého webu")[0].status, "Neověřeno")

    def test_missing_and_broken_markup(self):
        page, _ = analyze_html('<html><body><h1>Téma</h1><h3>Skok</h3><img src="x"><script type="application/ld+json">{broken}</script></body>', "bad.html")
        self.assertEqual(findings(page, "Titulek stránky")[0].status, "Chyba")
        self.assertEqual(findings(page, "Hierarchie nadpisů")[0].status, "Doporučení")
        self.assertEqual(findings(page, "Alternativní texty obrázků")[0].status, "Doporučení")
        self.assertEqual(findings(page, "Strukturovaná data JSON-LD")[0].status, "Chyba")

    def test_empty_decorative_alt_is_not_missing(self):
        page, _ = analyze_html('<img src="x" alt="">', "a.html")
        self.assertEqual(findings(page, "Alternativní texty obrázků")[0].status, "Správně")

    def test_noindex_sources(self):
        for markup, headers in [('<meta name="robots" content="NOINDEX">', {}), ('<meta name="googlebot" content="none">', {}), ("", {"X-Robots-Tag": "noindex"})]:
            page, _ = analyze_html(markup, "https://example.com", True, headers)
            self.assertEqual(findings(page, "Pokyny k indexaci")[0].status, "Doporučení")

    def test_decoding(self):
        self.assertIn("Příliš", decode_html('<meta charset="windows-1250">Příliš'.encode("cp1250")))
        self.assertEqual(decode_html("český".encode("utf-8-sig")), "český")

    def test_urls(self):
        self.assertEqual(normalize_url("example.com#top"), "https://example.com/")
        self.assertIn("%C4%8D", normalize_url("https://example.com/č"))
        for value in ("", "ftp://example.com", "https://user:pass@example.com", "https://example.com:bad"):
            with self.assertRaises(ValueError):
                normalize_url(value)


class LocalTests(unittest.TestCase):
    def test_folder_zip_duplicates_and_limit(self):
        with temporary_directory() as folder:
            root = Path(folder)
            (root / "one.html").write_text(GOOD, encoding="utf-8")
            (root / "two.HTML").write_text(GOOD, encoding="utf-8")
            report = audit_local(folder)
            self.assertEqual(len(report.pages), 2)
            self.assertTrue(findings(report.pages[0], "Duplicitní titulek"))
            limited = audit_local(folder, limit=1)
            self.assertEqual(len(limited.pages), 1)
            self.assertIn("limit", limited.notes[-1])
            archive_path = root / "web.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../../never-extracted.html", GOOD)
                archive.writestr("nested/page.html", GOOD)
                archive.writestr("server.php", "<?php echo 1; ?>")
            self.assertEqual(len(audit_local(str(archive_path)).pages), 2)
            self.assertFalse((root.parent / "never-extracted.html").exists())

    def test_empty_and_unsupported(self):
        with temporary_directory() as folder:
            with self.assertRaises(ValueError):
                audit_local(folder)
            path = Path(folder) / "app.php"
            path.write_text("hello")
            with self.assertRaises(ValueError):
                audit_local(str(path))

    def test_cancel(self):
        with temporary_directory() as folder:
            event = threading.Event()
            event.set()
            report = audit_local(folder, cancel=event)
            self.assertFalse(report.pages)
            self.assertIn("zastavena", report.notes[-1])

    def test_report_escapes_untrusted_html(self):
        with temporary_directory() as folder:
            root = Path(folder)
            source = root / "page.html"
            source.write_text('<title>&lt;script&gt;alert(1)&lt;/script&gt;</title>', encoding="utf-8")
            report = audit_local(str(source))
            save_report(report, str(root / "report.html"))
            exported = (root / "report.html").read_text(encoding="utf-8")
            self.assertNotIn("<script>", exported)
            self.assertIn("&lt;script&gt;", exported)
            save_report(report, str(root / "report.json"))
            self.assertEqual(json.loads((root / "report.json").read_text(encoding="utf-8"))["pages"][0]["title"], "<script>alert(1)</script>")


class Server(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.requests.append(self.path)
        code, mime, content = 200, "text/html; charset=utf-8", GOOD
        if self.path == "/robots.txt":
            mime, content = "text/plain", "User-agent: *\nDisallow: /blocked\n"
        elif self.path == "/sitemap.xml":
            mime, content = "application/xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
        elif self.path == "/":
            content += '<a href="/second">Second</a><a href="/blocked">Block</a><a href="/missing">Missing</a><a href="/second#x">Fragment</a><a href="https://example.org/">External</a><a href="/query?q=1">Query</a>'
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/second")
            self.end_headers()
            return
        elif self.path == "/missing":
            code, content = 404, "Missing"
        elif self.path == "/pdf":
            mime, content = "application/pdf", "%PDF"
        self.send_response(code)
        self.send_header("Content-Type", mime)
        if self.path == "/second":
            self.send_header("X-Robots-Tag", "noindex")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def log_message(self, *args):
        pass


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Server)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Server.requests.clear()

    def test_crawl_robots_http_and_duplicates(self):
        report = audit_url(self.url, limit=10)
        self.assertEqual(len(report.pages), 5)
        self.assertNotIn("/blocked", Server.requests)
        self.assertEqual(Server.requests.count("/second"), 1)
        self.assertIn("/query?q=1", Server.requests)
        self.assertTrue(findings(report.pages[0], "Duplicitní titulek"))
        missing = next(p for p in report.pages if p.location.endswith("/missing"))
        self.assertEqual(findings(missing, "HTTP odpověď")[0].status, "Chyba")
        second = next(p for p in report.pages if p.location.endswith("/second"))
        self.assertEqual(findings(second, "Pokyny k indexaci")[0].status, "Doporučení")
        self.assertEqual(findings(report.pages[0], "Sitemap XML")[0].status, "Správně")

    def test_limit_and_redirect(self):
        report = audit_url(self.url, limit=1)
        self.assertEqual(len(report.pages), 1)
        self.assertNotIn("/second", Server.requests)
        self.assertTrue(any("limit" in note for note in report.notes))
        report = audit_url(self.url + "/redirect", limit=1)
        self.assertTrue(report.pages[0].location.endswith("/redirect"))
        self.assertTrue(report.pages[0].redirects[-1].endswith("/second"))
        self.assertTrue(findings(report.pages[0], "Přesměrování"))

    def test_non_html(self):
        report = audit_url(self.url + "/pdf", limit=1)
        self.assertEqual(findings(report.pages[0], "Typ dokumentu")[0].status, "Neověřeno")


if __name__ == "__main__":
    unittest.main()
