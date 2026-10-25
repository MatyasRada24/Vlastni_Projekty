from __future__ import annotations

import json
import re
import zipfile
from copy import deepcopy
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from threading import Event
from urllib.parse import urlsplit, urlunsplit

MAX_BYTES = 5 * 1024 * 1024
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
AGENT = "KontrolaSEO/0.4"
STATUSES = ("Chyba", "Doporučení", "Správně", "Neověřeno")
LIMITATION = (
    "Audit vyhodnocuje stažené HTML a nespouští JavaScript. Neověřuje skutečné "
    "zařazení do Googlu, pozice, zpětné odkazy ani Core Web Vitals. "
    "Výsledky jsou technické podklady, nikoli záruka pořadí ve vyhledávání."
)


@dataclass
class Finding:
    status: str
    name: str
    detail: str
    advice: str = ""
    code: str = ""
    target: str = ""

    @property
    def rule(self):
        return self.code or self.name

    @property
    def check_key(self):
        return self.rule + "\n" + self.target


@dataclass
class Page:
    location: str
    title: str = ""
    description: str = ""
    words: int = 0
    findings: list[Finding] = field(default_factory=list)
    checked_rules: list[str] = field(default_factory=list)
    inbound: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    links_complete: bool = True
    canonical: str = ""
    noindex: bool = False
    html_checked: bool = False
    http_status: int | None = None
    redirects: list[str] = field(default_factory=list)
    sitemap_sources: list[str] = field(default_factory=list)
    analysis_mode: str = "source"
    headings: list | None = None
    source_links: list[str] | None = None
    declared_canonicals: list[str] | None = None
    source_links_complete: bool = True

    def add(self, status, name, detail, advice="", code="", target=""):
        finding = Finding(status, name, detail, advice, code, target)
        self.findings.append(finding)
        if status != "Neověřeno" and finding.check_key not in self.checked_rules:
            self.checked_rules.append(finding.check_key)


@dataclass
class Report:
    source: str
    mode: str
    pages: list[Page] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    notes: list[str] = field(default_factory=lambda: [LIMITATION])
    complete: bool = True
    limit: int = 100
    discovered: int = 0
    schema_version: int = 4
    rendering: bool = False

    def counts(self):
        counts = Counter(f.status for p in self.pages for f in p.findings)
        return {status: counts[status] for status in STATUSES}

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = deepcopy(data)
        values = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "pages"}
        report = cls(**values)
        for raw in data.get("pages", []):
            page = Page(**{k: v for k, v in raw.items() if k in Page.__dataclass_fields__ and k != "findings"})
            page.findings = [Finding(**{k: v for k, v in f.items() if k in Finding.__dataclass_fields__}) for f in raw.get("findings", [])]
            report.pages.append(page)
        return report


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self.descriptions = []
        self.headings = []
        self.images = []
        self.links = []
        self.canonicals = []
        self.robots = []
        self.lang = ""
        self.viewport = ""
        self.base = ""
        self.json_ld = []
        self.text = []
        self._title = None
        self._heading = None
        self._json = None
        self._hidden = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang") or ""
        if tag == "title":
            self._title = []
        if re.fullmatch(r"h[1-6]", tag):
            self._heading = (int(tag[1]), [])
        if tag == "meta":
            name = (attrs.get("name") or "").lower()
            content = attrs.get("content") or ""
            if name == "description":
                self.descriptions.append(content.strip())
            if name in ("robots", "googlebot"):
                self.robots.append(content.lower())
            if name == "viewport":
                self.viewport = content.lower()
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonicals.append(attrs.get("href") or "")
        if tag == "img":
            self.images.append(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "base" and not self.base:
            self.base = attrs.get("href") or ""
        if tag in ("script", "style", "noscript", "template", "head"):
            self._hidden.append(tag)
        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._json = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "title" and self._title is not None:
            self.titles.append(" ".join("".join(self._title).split()))
            self._title = None
        if re.fullmatch(r"h[1-6]", tag) and self._heading:
            level, parts = self._heading
            self.headings.append((level, " ".join("".join(parts).split())))
            self._heading = None
        if tag == "script" and self._json is not None:
            self.json_ld.append("".join(self._json))
            self._json = None
        if tag in self._hidden:
            index = len(self._hidden) - 1 - self._hidden[::-1].index(tag)
            del self._hidden[index:]

    def handle_data(self, data):
        if self._title is not None:
            self._title.append(data)
        if self._heading:
            self._heading[1].append(data)
        if self._json is not None:
            self._json.append(data)
        if not self._hidden:
            self.text.append(data)


def decode_html(data: bytes, charset: str | None = None) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    match = re.search(br"charset\s*=\s*[\"']?\s*([a-zA-Z0-9_-]+)", data[:4096], re.I)
    encoding = charset or (match.group(1).decode("ascii") if match else "utf-8")
    try:
        return data.decode(encoding, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Zadejte URL adresu webu.")
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Zadejte platnou HTTP nebo HTTPS adresu bez přihlašovacích údajů.")
    try:
        parts.port
        host = parts.hostname.encode("idna").decode("ascii")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Adresa obsahuje neplatnou doménu nebo port.") from exc
    if ":" in host:
        host = f"[{host}]"
    netloc = host + (f":{parts.port}" if parts.port else "")
    from urllib.parse import quote
    return urlunsplit((parts.scheme.lower(), netloc, quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~"),
                       quote(parts.query, safe="%=&?/:@!$'()*+,;~-._"), ""))


def analyze_html(html: str, location: str, online=False, headers=None) -> tuple[Page, Document]:
    doc = Document()
    doc.feed(html)
    doc.close()
    page = Page(location, doc.titles[0] if doc.titles else "", doc.descriptions[0] if doc.descriptions else "")
    page.html_checked = True
    page.headings = [list(heading) for heading in doc.headings]
    page.source_links = list(dict.fromkeys(doc.links[:10000]))
    page.source_links_complete = len(doc.links) <= 10000
    page.declared_canonicals = doc.canonicals
    page.words = len(re.findall(r"\b\w+\b", " ".join(doc.text)))
    add = page.add
    if not page.title:
        add("Chyba", "Titulek stránky", "Chybí neprázdný prvek <title>.", "Doplňte stručný a konkrétní titulek vystihující tuto stránku.")
    elif len(doc.titles) > 1:
        add("Chyba", "Titulek stránky", f"Stránka má {len(doc.titles)} prvků <title>.", "Ponechte jeden výstižný titulek.")
    else:
        add("Správně", "Titulek stránky", page.title + f" ({len(page.title)} znaků). Délka sama o sobě neurčuje kvalitu titulku.")
    if not page.description:
        add("Doporučení", "Meta description", "Chybí neprázdný meta popis.", "Napište přirozené shrnutí obsahu. Vyhledávač může použít i vlastní úryvek stránky.")
    elif len(doc.descriptions) > 1:
        add("Doporučení", "Meta description", "Stránka má více meta popisů.", "Ponechte jediný relevantní popis.")
    else:
        add("Správně", "Meta description", page.description + f" ({len(page.description)} znaků).")
    h1s = [text for level, text in doc.headings if level == 1 and text]
    if not h1s:
        add("Doporučení", "Hlavní nadpis H1", "Nenalezen neprázdný hlavní nadpis H1.", "Přidejte jasný hlavní nadpis, který návštěvníkovi vysvětlí obsah stránky.")
    elif len(h1s) > 1:
        add("Doporučení", "Hlavní nadpis H1", f"Nalezeno {len(h1s)} nadpisů H1. Více H1 samo o sobě není penalizace.", "Zkontrolujte, že je hlavní téma a hierarchie nadpisů jasná.")
    else:
        add("Správně", "Hlavní nadpis H1", h1s[0])
    jumps = any(b[0] > a[0] + 1 for a, b in zip(doc.headings, doc.headings[1:]))
    add("Doporučení" if jumps else "Správně" if doc.headings else "Neověřeno", "Hierarchie nadpisů",
        "Úrovně nadpisů přeskakují (například H2 → H4)." if jumps else "Nadpisy nepřeskakují úrovně." if doc.headings else "Nenalezeny nadpisy.",
        "Uspořádejte nadpisy podle logické struktury obsahu." if jumps else "")
    missing = [img.get("src", "bez src") for img in doc.images if "alt" not in img]
    empty = sum(not (img.get("alt") or "").strip() for img in doc.images if "alt" in img)
    if missing:
        add("Doporučení", "Alternativní texty obrázků", f"Bez atributu alt: {len(missing)} z {len(doc.images)}. " + "; ".join(missing[:8]), "Významové obrázky stručně popište. Dekorativním nastavte alt=\"\".")
    elif doc.images:
        add("Správně", "Alternativní texty obrázků", f"Všech {len(doc.images)} obrázků má atribut alt. Kvalita popisu vyžaduje ruční posouzení.")
    else:
        add("Neověřeno", "Alternativní texty obrázků", "Ve zdrojovém HTML nejsou prvky img.")
    if empty:
        add("Doporučení", "Prázdné alternativní texty", f"Počet prázdných alt: {empty}.", "Ověřte, že jde pouze o dekorativní obrázky; u nich je prázdný alt správně.")
    tokens = set(re.findall(r"[a-z]+", ",".join(doc.robots) + "," + (headers or {}).get("X-Robots-Tag", "").lower()))
    if tokens & {"noindex", "none"}:
        page.noindex = True
        add("Doporučení", "Pokyny k indexaci", "Nalezen noindex/none v HTML nebo HTTP hlavičce; může být určen i konkrétnímu robotovi.", "Pokud má být stránka ve vyhledávání, prověřte a případně odstraňte blokující pokyn. U neveřejných stránek může být záměrný.")
    else:
        add("Správně", "Pokyny k indexaci", "V kontrolovaných meta značkách" + (" a HTTP hlavičce" if online else "") + " není noindex. Nejde o potvrzení skutečné indexace.")
    if not online:
        add("Neověřeno", "Nastavení živého webu", "Z lokálních souborů nelze ověřit HTTPS, HTTP stav, X-Robots-Tag, živé robots.txt ani sitemapu.", "Pro tyto kontroly spusťte audit URL nasazeného webu.")
    if len(doc.canonicals) > 1:
        add("Chyba", "Kanonická adresa", "Nalezeno více canonical odkazů.", "Ponechte jednu jednoznačnou kanonickou URL.")
    elif doc.canonicals and doc.canonicals[0].strip():
        canonical = doc.canonicals[0].strip()
        try:
            valid = urlsplit(canonical).scheme in ("http", "https") and bool(urlsplit(canonical).hostname)
        except ValueError:
            valid = False
        add("Správně" if valid else "Doporučení", "Kanonická adresa", canonical + ". Cílová adresa ani její vhodnost nejsou ověřeny.", "Preferujte úplnou absolutní URL preferované verze stránky." if not valid else "")
    else:
        add("Doporučení", "Kanonická adresa", "Nenalezen neprázdný rel=canonical; nemusí být nutný pro každou stránku.", "Pokud existují duplicitní varianty URL, uveďte preferovanou adresu.")
    add("Správně" if doc.lang.strip() else "Doporučení", "Jazyk dokumentu", f"Atribut lang: {doc.lang}" if doc.lang.strip() else "Chybí atribut lang na prvku html.", "Vyplňte jazyk pro přístupnost, například <html lang=\"cs\">." if not doc.lang.strip() else "")
    viewport_ok = bool(re.search(r"width\s*=\s*device-width", doc.viewport))
    add("Správně" if viewport_ok else "Doporučení", "Mobilní viewport", "Nalezen width=device-width; vzhled na mobilu není tímto ověřen." if viewport_ok else "Chybí viewport s width=device-width.", "Přidejte meta viewport a ručně ověřte mobilní zobrazení." if not viewport_ok else "")
    if page.words:
        add("Správně", "Textový obsah", f"Ve zdrojovém HTML nalezeno přibližně {page.words} slov. Počet slov není hodnocením kvality ani pevnou podmínkou SEO.")
    else:
        add("Doporučení", "Textový obsah", "Ve zdrojovém HTML není viditelný text; obsah může vznikat JavaScriptem.", "Ověřte vykreslenou stránku a dostupnost obsahu pro vyhledávače.")
    invalid = []
    for index, value in enumerate(doc.json_ld, 1):
        try:
            json.loads(value, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (ValueError, RecursionError):
            invalid.append(str(index))
    add("Chyba" if invalid else "Správně" if doc.json_ld else "Neověřeno", "Strukturovaná data JSON-LD",
        "Neplatná syntaxe JSON v blocích: " + ", ".join(invalid) if invalid else f"Syntaxe {len(doc.json_ld)} JSON-LD bloků je platná. Schéma a způsobilost pro rozšířené výsledky nebyly ověřeny." if doc.json_ld else "JSON-LD nenalezeno. Jiné formáty strukturovaných dat se nekontrolují.",
        "Opravte JSON a ověřte schéma v Google Rich Results Test." if invalid else "")
    page.checked_rules.append("Prázdné alternativní texty\n")
    return page, doc


def duplicates(report: Report):
    for attr, label in (("title", "titulek"), ("description", "meta popis")):
        values = Counter(getattr(p, attr).strip().casefold() for p in report.pages if getattr(p, attr).strip() and len(p.redirects) <= 1)
        for page in report.pages:
            if page.html_checked:
                page.checked_rules.append(f"Duplicitní {label}\n")
            value = getattr(page, attr).strip().casefold()
            if value and values[value] > 1 and len(page.redirects) <= 1:
                page.add("Doporučení", f"Duplicitní {label}", f"Stejný {label} má {values[value]} kontrolovaných stránek.", "Odlište stránky titulkem a popisem podle jejich skutečného obsahu.")


def audit_local(path: str, limit=30, cancel=None, progress=None, selected=None, resume=None, checkpoint=None, activity=None) -> Report:
    cancel = cancel or Event()
    progress = progress or (lambda _: None)
    source = Path(path).expanduser().resolve()
    report = Report(str(source), "Soubory")
    if not source.exists():
        raise ValueError("Vybraný soubor nebo složka neexistuje.")
    limit = max(1, min(int(limit), 1000))
    report.limit = limit
    activity = activity or (lambda _: None)
    manifest = []
    processed = set()
    def save_checkpoint():
        if checkpoint and selected is None:
            checkpoint({'version': 1, 'mode': 'Soubory', 'source': str(source), 'limit': limit,
                        'rendering': False, 'manifest': manifest, 'report': report.to_dict()})

    def prepare(signatures):
        nonlocal report, manifest, processed
        manifest = signatures
        if resume:
            if (selected is not None or resume.get('version') != 1 or resume.get('mode') != 'Soubory'
                    or resume.get('source') != str(source) or resume.get('manifest') != manifest):
                raise ValueError('Zdrojové soubory se od přerušení změnily. Spusťte novou kontrolu.')
            report = Report.from_dict(resume['report'])
            if len(report.pages) > limit:
                raise ValueError('Limit musí být alespoň počet již zpracovaných souborů.')
            report.limit = limit
            report.notes.append('Obnoveno ' + datetime.now().astimezone().isoformat(timespec='seconds') + '. Zdrojové soubory mají stejné velikosti a časové značky / CRC archivu.')
        processed = {p.location for p in report.pages}
        save_checkpoint()
    if selected is not None:
        selected = set(selected)
        if not selected or len(selected) > limit:
            raise ValueError('Vyberte 1 až 1000 HTML souborů pro ověření.')
        report.complete = False
        report.notes.append('Cílené ověření vybraných souborů. Odstranění duplicit vyžaduje nový úplný audit.')

    def append(name, data):
        activity({'completed': len(report.pages), 'waiting': max(0, len(entries)-len(report.pages)), 'current': name, 'limit': limit})
        progress(f"Kontroluji {name}")
        page, _ = analyze_html(decode_html(data), name)
        report.pages.append(page)
        save_checkpoint()
        activity({'completed': len(report.pages), 'waiting': max(0, len(entries)-len(report.pages)), 'current': '', 'limit': limit})

    if source.suffix.lower() == ".zip" and source.is_file():
        with zipfile.ZipFile(source) as archive:
            entries = sorted((i for i in archive.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in (".html", ".htm")), key=lambda i: i.filename)
            if selected is not None:
                entries = [i for i in entries if i.filename in selected]
            prepare([[i.filename, i.file_size, i.CRC] for i in entries])
            total = 0
            for info in entries[:limit]:
                if cancel.is_set():
                    break
                if info.file_size > MAX_BYTES or total + info.file_size > MAX_ARCHIVE_BYTES:
                    raise ValueError("HTML v archivu překračuje limit 5 MB na soubor nebo 50 MB celkem.")
                if info.filename in processed:
                    total += info.file_size
                    continue
                with archive.open(info) as stream:
                    data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("HTML v archivu překračuje limit 5 MB.")
                total += len(data)
                append(info.filename, data)
    else:
        if source.is_dir():
            entries = sorted(p for p in source.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower() in (".html", ".htm"))
        else:
            if source.suffix.lower() not in (".html", ".htm"):
                raise ValueError("Vyberte soubor HTML, HTM, ZIP nebo složku s HTML soubory.")
            entries = [source]
        if selected is not None:
            entries = [entry for entry in entries if str(entry) in selected]
        prepare([[str(entry), entry.stat().st_size, entry.stat().st_mtime_ns] for entry in entries])
        total = 0
        for entry in entries[:limit]:
            if cancel.is_set():
                break
            if str(entry) in processed:
                total += entry.stat().st_size
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError('HTML překračuje limit 50 MB celkem.')
                continue
            with entry.open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
            total += len(data)
            if len(data) > MAX_BYTES or total > MAX_ARCHIVE_BYTES:
                raise ValueError("HTML překračuje limit 5 MB na soubor nebo 50 MB celkem.")
            append(str(entry), data)
    if len(entries) > limit:
        report.complete = False
        report.notes.append(f"Dosažen limit {limit} HTML souborů; část souborů nebyla zkontrolována.")
    if cancel.is_set():
        report.complete = False
        report.notes.append("Kontrola byla zastavena; výsledky jsou částečné.")
    if selected is not None and not cancel.is_set():
        for missing in sorted(selected - {page.location for page in report.pages}):
            page = Page(missing)
            page.add('Neověřeno', 'Soubor není dostupný', 'Soubor v původním zdroji nyní chybí. Odstranění souboru není potvrzení opravy původního nálezu.', code='fetch')
            report.pages.append(page)
    if not report.pages and not cancel.is_set():
        raise ValueError("Nebyly nalezeny žádné soubory HTML nebo HTM. Zdrojový kód PHP/React nejprve nasaďte a zadejte jeho URL.")
    duplicates(report)
    report.discovered = len(selected) if selected is not None else len(entries)
    return report


def audit_url(value: str, limit=100, cancel=None, progress=None, rendering=False, resume=None, checkpoint=None, activity=None) -> Report:
    from .crawler import crawl
    return crawl(value, limit=limit, cancel=cancel, progress=progress, rendering=rendering,
                 resume=resume, checkpoint=checkpoint, activity=activity)
