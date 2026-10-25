"""Bounded same-site crawler with explicit redirects, sitemap discovery and evidence."""
from __future__ import annotations

import gzip
from http.client import HTTPException
import io
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import Event
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .engine import AGENT, MAX_BYTES, Page, Report, analyze_html, decode_html, duplicates, normalize_url
from .network import open_url, local_target


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Result:
    url: str
    status: int | None = None
    data: bytes = b""
    headers: object = field(default_factory=dict)
    chain: list[str] = field(default_factory=list)
    error: str = ""
    kind: str = ""


def origin(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class Crawler:
    def __init__(self, value, limit, cancel, progress, renderer=None, resume=None, checkpoint=None, activity=None):
        self.start = normalize_url(value)
        self.limit = max(1, min(int(limit), 1000))
        self.cancel = cancel or Event()
        self.progress = progress or (lambda _: None)
        self.report = Report(self.start, "URL", limit=self.limit)
        self.renderer = renderer
        self.report.rendering = renderer is not None
        if renderer:
            self.report.notes = ['Audit analyzuje DOM po spuštění JavaScriptu v izolovaném desktopovém prohlížeči. Čekání: DOMContentLoaded + 2 s, navigace nejvýše 25 s. Neprovádí přihlášení, klikání ani scrollování; nejde o simulaci Googlebotu. Rychlost se měří samostatně přes PageSpeed.']
        self.report.notes.append("Kontrolují se interní URL, sitemapy a cíle canonical do zadaného limitu. Externí cíle se nestahují. Přesměrování: nejvýše 10 kroků; sitemapy: nejvýše 20 souborů / 10 000 URL.")
        self.opener = build_opener(NoRedirect())
        self.policies = {}
        self.last_request = {}
        self.results = {}
        self.pages = {}
        self.inbound = defaultdict(set)
        self.sitemap_urls = defaultdict(set)
        self.queue = deque()
        self.queued = set()
        self.sitemap_notes = []
        self.sitemaps_complete = False
        self.root = origin(self.start)
        self.checkpoint_callback = checkpoint
        self.activity = activity or (lambda _: None)
        if resume:
            self.restore(resume)
            self.report.notes.append('Kontrola obnovena ' + datetime.now().astimezone().isoformat(timespec='seconds') +
                                     '. Již zpracované stránky pocházejí z předchozí části kontroly; web se mezitím mohl změnit.')

    def snapshot(self):
        return {'version': 1, 'mode': 'URL', 'source': self.start, 'limit': self.limit,
                'rendering': self.renderer is not None, 'report': self.report.to_dict(),
                'queue': list(self.queue), 'queued': sorted(self.queued), 'root': self.root,
                'inbound': {k: sorted(v) for k, v in self.inbound.items()},
                'sitemap_urls': {k: sorted(v) for k, v in self.sitemap_urls.items()},
                'sitemap_notes': self.sitemap_notes, 'sitemaps_complete': self.sitemaps_complete,
                'results': {url: {'url': r.url, 'status': r.status, 'chain': r.chain, 'error': r.error, 'kind': r.kind}
                            for url, r in self.results.items()}}

    def restore(self, data):
        if (data.get('version') != 1 or data.get('source') != self.start or data.get('mode') != 'URL'
                or bool(data.get('rendering')) != (self.renderer is not None)):
            raise ValueError('Rozpracovaná kontrola má jiný zdroj nebo režim. Spusťte novou kontrolu.')
        report = Report.from_dict(data['report'])
        if len(report.pages) > self.limit or len(data['queued']) > 10000:
            raise ValueError('Limit musí být alespoň počet již zpracovaných stránek.')
        if any(not self.in_site(url) for url in data['queued']):
            raise ValueError('Rozpracovaná kontrola obsahuje URL mimo zadaný web.')
        self.report = report
        self.report.limit = self.limit
        self.pages = {p.location: p for p in report.pages}
        self.results = {url: Result(**row) for url, row in data['results'].items()}
        self.queue, self.queued = deque(data['queue']), set(data['queued'])
        self.root = data['root']
        self.inbound = defaultdict(set, {k: set(v) for k, v in data['inbound'].items()})
        self.sitemap_urls = defaultdict(set, {k: set(v) for k, v in data['sitemap_urls'].items()})
        self.sitemap_notes = list(data['sitemap_notes'])
        self.sitemaps_complete = data['sitemaps_complete']

    def checkpoint(self):
        if self.checkpoint_callback:
            self.checkpoint_callback(self.snapshot())
        self.activity({'completed': len(self.report.pages), 'waiting': len(self.queue), 'current': '', 'limit': self.limit})

    def in_site(self, url):
        a, b = urlsplit(self.start), urlsplit(url)
        host_a = (a.hostname or "").removeprefix("www.")
        host_b = (b.hostname or "").removeprefix("www.")
        port_a, port_b = a.port or (443 if a.scheme == "https" else 80), b.port or (443 if b.scheme == "https" else 80)
        return b.scheme in ("http", "https") and host_a == host_b and (port_a == port_b or {port_a, port_b} <= {80, 443})

    def policy(self, url):
        base = origin(url)
        if base not in self.policies:
            result = self.request(base + "/robots.txt", robots=False)
            parser = RobotFileParser()
            if result.status in (404, 410):
                parser.parse([])
                note = "robots.txt není dostupný (404/410); jeho absence není SEO chyba."
            elif result.status == 200 and not result.error and "html" not in result.headers.get("Content-Type", "").lower():
                parser.parse(decode_html(result.data).splitlines())
                note = "Pravidla robots.txt byla načtena."
            else:
                parser = None
                note = "robots.txt nelze spolehlivě načíst; procházení tohoto původu je zastaveno. " + result.error
            self.policies[base] = (parser, note)
        return self.policies[base]

    def request(self, url, robots=True):
        chain = []
        current = url
        for _ in range(11):
            if self.cancel.is_set():
                return Result(current, chain=chain, error="Kontrola byla zastavena.", kind="cancelled")
            if current in chain:
                return Result(current, chain=chain + [current], error="Přesměrování tvoří smyčku.", kind="redirect.loop")
            chain.append(current)
            if not self.in_site(current):
                return Result(current, chain=chain, error="Cíl je mimo kontrolovaný web.", kind="external")
            if robots:
                parser, note = self.policy(current)
                if parser is None or not parser.can_fetch("KontrolaSEO", current):
                    return Result(current, chain=chain, error=note if parser is None else "Procházení zakazuje robots.txt pro KontrolaSEO.", kind="robots")
                delay = parser.crawl_delay("KontrolaSEO") or 0.15
                if delay > 30:
                    return Result(current, chain=chain, error="Crawl-delay překračuje 30 sekund.", kind="robots")
                remaining = self.last_request.get(origin(current), 0) + delay - time.monotonic()
                if remaining > 0 and self.cancel.wait(remaining):
                    return Result(current, chain=chain, error="Kontrola byla zastavena.", kind="cancelled")
            try:
                request = Request(current, headers={"User-Agent": AGENT, "Accept-Encoding": "identity"})
                try:
                    response = open_url(current, headers=dict(request.header_items()), timeout=12,
                                        allowed_local=local_target(self.start))
                except HTTPError as exc:
                    response = exc
                self.last_request[origin(current)] = time.monotonic()
                with response:
                    if response.code in (301, 302, 303, 307, 308):
                        location = response.headers.get("Location")
                        if not location:
                            return Result(current, response.code, chain=chain, error="Přesměrování nemá hlavičku Location.", kind="redirect.invalid")
                        current = normalize_url(urljoin(current, location))
                        continue
                    mime = response.headers.get_content_type()
                    readable = mime.startswith("text/") or "xml" in mime or "gzip" in mime or current.endswith(".gz")
                    data = response.read(MAX_BYTES + 1) if readable else b""
                    if len(data) > MAX_BYTES:
                        return Result(current, response.code, chain=chain, error="Odpověď překračuje limit 5 MB.", kind="size")
                    return Result(current, response.code, data, response.headers, chain)
            except (OSError, URLError, ValueError, HTTPException) as exc:
                return Result(current, chain=chain, error=str(exc), kind="network")
        return Result(current, chain=chain, error="Přesměrování překročilo 10 kroků.", kind="redirect.limit")

    def enqueue(self, url, source="", sitemap=""):
        try:
            url = normalize_url(url)
            if not self.in_site(url):
                return
        except ValueError:
            return
        if url not in self.queued and len(self.queued) >= 10000:
            self.report.complete = False
            return
        if source:
            self.inbound[url].add(source)
        if sitemap:
            self.sitemap_urls[url].add(sitemap)
        if url not in self.queued:
            self.queued.add(url)
            self.queue.append(url)

    def read_sitemaps(self):
        parser, _ = self.policy(self.root + "/")
        if not parser or self.cancel.is_set():
            return
        todo = deque(parser.site_maps() or [self.root + "/sitemap.xml"])
        visited = set()
        failed = False
        valid_count = 0
        while todo and len(visited) < 20 and not self.cancel.is_set():
            raw = todo.popleft()
            try:
                url = normalize_url(urljoin(self.root + "/", raw))
            except ValueError:
                continue
            if url in visited:
                continue
            visited.add(url)
            self.progress(f"Načítám sitemapu: {url}")
            result = self.request(url)
            if result.error or result.status != 200:
                failed = True
                self.sitemap_notes.append(("Neověřeno", f"{url}: {result.error or 'HTTP ' + str(result.status)}"))
                continue
            try:
                data = result.data
                if data.startswith(b"\x1f\x8b"):
                    with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
                        data = compressed.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES or b"<!DOCTYPE" in data.upper():
                    raise ValueError("Nepodporované nebo příliš velké XML.")
                tree = ET.fromstring(data)
                kind = tree.tag.rsplit("}", 1)[-1]
                if kind not in ("urlset", "sitemapindex"):
                    raise ValueError("XML není sitemap ani sitemap index.")
                valid_count += 1
                count = 0
                for entry in tree:
                    if self.cancel.is_set() or count >= 10000:
                        break
                    loc = next((child.text for child in entry if child.tag.rsplit("}", 1)[-1] == "loc"), None)
                    if not loc:
                        continue
                    count += 1
                    target = urljoin(result.url, loc.strip())
                    if kind == "sitemapindex":
                        if len(todo) < 10000:
                            todo.append(target)
                    else:
                        self.enqueue(target, sitemap=url)
                self.sitemap_notes.append(("Správně", f"{url}: načteno {count} položek ({kind})."))
                if len(tree) > count and count >= 10000:
                    failed = True
                    self.report.complete = False
                    self.report.notes.append(f"Sitemap {url}: zpracováno pouze prvních 10 000 položek.")
            except (ET.ParseError, ValueError, OSError, EOFError) as exc:
                failed = True
                self.sitemap_notes.append(("Neověřeno", f"{url}: {exc}"))
        if todo:
            self.report.complete = False
            self.report.notes.append("Dosažen limit 20 sitemap; část sitemap nebyla zpracována.")
        self.sitemaps_complete = valid_count > 0 and not failed and not todo and not self.cancel.is_set()
        if failed and valid_count:
            self.report.complete = False

    def visit(self, url):
        self.activity({'completed': len(self.report.pages), 'waiting': len(self.queue), 'current': url, 'limit': self.limit})
        self.progress(f"Kontroluji {len(self.report.pages) + 1}/{self.limit}: {url}")
        result = self.request(url)
        self.results[url] = result
        if result.error:
            page = Page(url, redirects=result.chain, http_status=result.status)
            status = "Chyba" if result.kind.startswith("redirect.") else "Neověřeno"
            page.add(status, "Přesměrování" if status == "Chyba" else "Stažení stránky", result.error + "\n" + " → ".join(result.chain),
                     "Prověřte pravidla přesměrování." if status == "Chyba" else "Ověřte dostupnost a pravidla procházení.", code=result.kind if status == "Chyba" else "fetch")
            self.report.complete = False
        elif result.status >= 400:
            page = Page(url, http_status=result.status)
            page.add("Chyba", "HTTP odpověď", f"HTTP {result.status}: {result.url}", "Opravte dostupnost cíle a interní odkazy na něj.")
        elif result.headers.get_content_type() not in ("text/html", "application/xhtml+xml"):
            page = Page(url, http_status=result.status)
            page.add("Správně", "HTTP odpověď", f"HTTP {result.status}.")
            page.add("Neověřeno", "Typ dokumentu", f"Cíl má typ {result.headers.get_content_type()}, nikoli HTML.")
        else:
            html = decode_html(result.data, result.headers.get_content_charset())
            render_error = ''
            if self.renderer:
                self.progress(f'Vykresluji JavaScript: {url}')
                try:
                    html = self.renderer.render(result, self.cancel)
                except Exception as exc:
                    render_error = str(exc)
                    self.report.complete = False
            page, doc = analyze_html(html, url, True, result.headers)
            if self.renderer:
                page.analysis_mode = 'render_failed' if render_error else 'rendered'
                page.add('Neověřeno' if render_error else 'Správně', 'Vykreslení JavaScriptu',
                         render_error + ' Ostatní nálezy vycházejí pouze ze zdrojového HTML.' if render_error else 'Analyzován DOM po DOMContentLoaded a dalších 2 sekundách; desktopový prohlížeč.',
                         code='rendering')
            page.http_status = result.status
            page.add("Správně", "HTTP odpověď", f"HTTP {result.status}; konečná adresa: {result.url}.")
            page.add("Správně" if urlsplit(result.url).scheme == "https" else "Doporučení", "HTTPS", "Stránka používá HTTPS." if result.url.startswith("https:") else "Stránka používá HTTP.", "Nasaďte platné HTTPS." if result.url.startswith("http:") else "")
            parser, note = self.policy(result.url)
            page.add("Správně" if parser else "Neověřeno", "robots.txt", note)
            google_allowed = parser.can_fetch("Googlebot", result.url) if parser else None
            page.add("Správně" if google_allowed else "Doporučení" if parser else "Neověřeno", "Průchod Googlebot podle robots.txt", "Procházení je povoleno." if google_allowed else "Procházení není povoleno nebo nebylo ověřeno.", "Prověřte pravidla robots.txt, pokud má být stránka procházena." if not google_allowed else "")
            base = urljoin(result.url, doc.base) if doc.base else result.url
            if len(doc.links) > 10000:
                page.links_complete = False
                self.report.complete = False
                self.report.notes.append(f"{url}: zpracováno pouze prvních 10 000 odkazů.")
            for link in doc.links[:10000]:
                try:
                    target = normalize_url(urljoin(base, link))
                except ValueError:
                    continue
                if self.in_site(target):
                    if target not in page.links:
                        page.links.append(target)
                    self.enqueue(target, source=url)
            if len(doc.canonicals) == 1 and doc.canonicals[0].strip():
                try:
                    page.canonical = normalize_url(urljoin(base, doc.canonicals[0].strip()))
                    self.enqueue(page.canonical)
                except ValueError:
                    page.add("Chyba", "Cíl canonical", "Canonical obsahuje neplatnou URL.", "Doplňte platnou adresu preferované stránky.", code="canonical.target")
            page.checked_rules.append("canonical.noindex\n")
            if page.noindex and page.canonical and page.canonical != result.url:
                page.add("Doporučení", "Noindex a canonical na jinou stránku", f"Noindex je současně s canonical → {page.canonical}.", "Ujasněte záměr: vyloučení stránky, nebo sloučení duplicit přes canonical.", code="canonical.noindex")
            # No robots success can turn an untested canonical into a verified one.
            for f in page.findings:
                if f.name == "Kanonická adresa" and page.canonical:
                    f.detail = page.canonical + ". Dostupnost cíle je uvedena v kontrole Cíl canonical."
        page.redirects = result.chain
        if not result.error:
            page.checked_rules.extend(["redirect.chain\n", "redirect.loop\n", "redirect.invalid\n", "redirect.limit\n"])
        if len(result.chain) > 1 and not result.error:
            page.add("Doporučení" if len(result.chain) > 2 else "Správně", "Přesměrování", " → ".join(result.chain),
                     "Zkraťte řetězec a interní odkazy veďte přímo na konečnou adresu." if len(result.chain) > 2 else "", code="redirect.chain")
        self.pages[url] = page
        self.report.pages.append(page)
        result.data = b""  # Responses are not retained in memory after parsing.
        if url == self.start and not result.error:
            self.root = origin(result.url)
        return page

    def cross_checks(self):
        for page in self.report.pages:
            page.inbound = sorted(self.inbound[page.location])
            page.sitemap_sources = sorted(self.sitemap_urls[page.location])
            for target in page.links:
                result = self.results.get(target)
                if result and not result.error:
                    page.checked_rules.append("link.broken\n" + target)
                    if result.status >= 400:
                        page.add("Chyba", "Nefunkční interní odkaz", f"Odkaz z {page.location} vede na {target} (HTTP {result.status}).", "Opravte href na této stránce nebo obnovte cílovou stránku.", code="link.broken", target=target)
                elif result and result.kind.startswith("redirect."):
                    page.add("Chyba", "Nefunkční interní odkaz", f"{target}: {result.error}", "Opravte přesměrování cílové URL nebo změňte odkaz.", code="link.broken", target=target)
            unchecked = [url for url in page.links if url not in self.results or (self.results[url].error and not self.results[url].kind.startswith("redirect."))]
            if unchecked:
                page.add("Neověřeno", "Dostupnost interních odkazů", f"Neověřených cílů: {len(unchecked)}.\n" + "\n".join(unchecked), "Zvyšte limit nebo opravte přístupnost cílových stránek.")
            elif page.html_checked and page.links_complete:
                broken = sum(f.rule == "link.broken" for f in page.findings)
                if not broken:
                    page.add("Správně", "Dostupnost interních odkazů", f"Zkontrolováno interních cílů: {len(page.links)}; bez nalezených chyb HTTP nebo přesměrování.")
            if page.html_checked and self.sitemaps_complete:
                page.checked_rules.append("sitemap.indexability\n")
            if page.sitemap_sources:
                result = self.results[page.location]
                if page.noindex or (page.canonical and page.canonical != result.url) or (page.http_status and page.http_status >= 400) or len(result.chain) > 1 or result.kind == "robots":
                    page.add("Doporučení", "Konflikt URL v sitemapě", "URL uvedená v sitemapě je neindexovatelná, přesměrovaná, blokovaná nebo má canonical na jinou URL.\n" + "\n".join(page.sitemap_sources), "Do sitemapy zařaďte dostupné preferované URL určené k indexaci.", code="sitemap.indexability")
            if page.canonical:
                target = page.canonical
                result = self.results.get(target)
                target_page = self.pages.get(target)
                if not self.in_site(target):
                    page.add("Neověřeno", "Cíl canonical", f"Externí cíl nebyl stažen: {target}", "Externí canonical může být záměrný; ověřte jej ručně.", code="canonical.target", target=target)
                elif result is None or result.error:
                    page.add("Neověřeno", "Cíl canonical", f"Cíl {target} nebyl ověřen: " + (result.error if result else "limit kontroly"), code="canonical.target", target=target)
                elif result.status >= 400 or not target_page.html_checked or target_page.noindex:
                    page.add("Chyba", "Cíl canonical", f"{target}: HTTP {result.status}, HTML={target_page.html_checked}, noindex={target_page.noindex}.", "Nasměrujte canonical na dostupnou indexovatelnou HTML stránku.", code="canonical.target", target=target)
                elif len(result.chain) > 1 or (target_page.canonical and target_page.canonical != result.url):
                    page.add("Doporučení", "Cíl canonical", f"{target} přesměrovává nebo odkazuje dalším canonical jinam.", "Použijte přímo konečnou preferovanou URL a odstraňte cykly canonical.", code="canonical.target", target=target)
                else:
                    parser, _ = self.policy(result.url) if not self.cancel.is_set() else self.policies.get(origin(result.url), (None, ""))
                    allowed = parser and parser.can_fetch("Googlebot", result.url)
                    page.add("Správně" if allowed else "Doporučení", "Cíl canonical", f"{target}: dostupné HTML bez noindex; " + ("Googlebot má podle robots.txt povolený přístup." if allowed else "prověřte přístup Googlebotu."), code="canonical.target", target=target)

    def run(self):
        self.enqueue(self.start)
        self.checkpoint()
        while self.queue and len(self.report.pages) < self.limit and not self.cancel.is_set():
            before = self.snapshot()
            url = self.queue.popleft()
            self.visit(url)
            if url == self.start:
                self.read_sitemaps()
            if self.cancel.is_set():
                self.restore(before)
                break
            self.checkpoint()
        self.report.discovered = len(self.queued)
        if self.queue:
            self.report.complete = False
            self.report.notes.append(f"Dosažen limit {self.limit} URL nebo přerušena kontrola; objeveno {self.report.discovered} URL. Nejde o úplný audit.")
        if self.cancel.is_set():
            self.report.complete = False
            self.report.notes.append("Kontrola byla zastavena; výsledky jsou částečné.")
        self.cross_checks()
        if self.report.pages:
            for status, detail in self.sitemap_notes:
                self.report.pages[0].add(status, "Sitemap XML", detail)
            if not self.sitemap_notes:
                self.report.pages[0].add("Neověřeno", "Sitemap XML", "Sitemapy nebyly ověřeny.")
        duplicates(self.report)
        return self.report

    def run_selected(self, locations):
        """Revisit explicit pages and one level of link/canonical dependencies only."""
        locations = list(dict.fromkeys(normalize_url(url) for url in locations))
        if not locations or len(locations) > self.limit:
            raise ValueError('Vyberte 1 až 1000 stránek pro ověření.')
        if any(not self.in_site(url) for url in locations):
            raise ValueError('Dotčené stránky musí patřit ke kontrolovanému webu.')
        self.report.notes = self.report.notes[:1] + [
            'Cílené ověření vybraných stránek, nikoli nový audit celého webu. '
            'Ověřují se také jejich přímé interní odkazy a canonical, celkem nejvýše 1000 URL. '
            'Robots.txt se respektuje; sitemapy ani další úrovně odkazů se neprocházejí. '
            'Odstranění duplicit a konfliktů v sitemapě vyžaduje nový úplný audit.'
        ]
        for url in locations:
            if self.cancel.is_set():
                break
            self.visit(url)
        primary = list(self.report.pages)
        dependencies = dict.fromkeys(target for page in primary
                                     for target in [*page.links, page.canonical] if target)
        for url in dependencies:
            if self.cancel.is_set() or len(self.results) >= self.limit:
                break
            if url not in self.results and self.in_site(url):
                self.visit(url)
        # Dependency evidence stays available to cross_checks, but is not presented
        # as additional requested pages or recursively crawled.
        self.report.pages = primary
        self.report.discovered = len(locations)
        self.report.complete = False
        self.cross_checks()
        duplicates(self.report)
        return self.report


def crawl(value, limit=100, cancel=None, progress=None, rendering=False, resume=None, checkpoint=None, activity=None):
    options = dict(resume=resume, checkpoint=checkpoint, activity=activity)
    if rendering:
        from .rendering import Renderer
        with Renderer() as renderer:
            return Crawler(value, limit, cancel, progress, renderer=renderer, **options).run()
    return Crawler(value, limit, cancel, progress, **options).run()


def crawl_selected(value, locations, cancel=None, progress=None, rendering=False):
    if rendering:
        from .rendering import Renderer
        with Renderer() as renderer:
            return Crawler(value, 1000, cancel, progress, renderer=renderer).run_selected(locations)
    return Crawler(value, 1000, cancel, progress).run_selected(locations)
