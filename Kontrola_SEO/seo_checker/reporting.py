"""Shared, conservative descriptions for the desktop and exported reports."""
from collections import Counter
from urllib.parse import urlsplit

from .planning import build_plan, issues
from .theme import readable


def browser_url(value):
    try:
        parts = urlsplit(value)
        return parts.scheme in ('http', 'https') and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError:
        return False


def audit_summary(report, states=None, search=None):
    problems = list(issues(report).values())
    uncertain = [(p, f) for p in report.pages for f in p.findings if f.status == 'Neověřeno']
    visited = len(report.pages)
    discovered = max(visited, report.discovered)
    reasons = Counter(f.name for p, f in uncertain)
    steps = []
    for task in build_plan(report, states, search)[:3]:
        advice = next((f.advice for p, f in task.occurrences if f.advice), task.reason)
        steps.append({'name': task.name, 'priority': task.priority, 'pages': task.pages,
                      'advice': advice, 'reason': task.reason})
    if not steps:
        steps.append({'name': 'Ověřte zbývající rozsah' if uncertain or not report.complete else 'Sledujte změny při další kontrole',
                      'priority': None, 'pages': [],
                      'advice': 'Projděte neověřené kontroly a omezení níže.' if uncertain or not report.complete else 'Uložte report a po změnách webu zopakujte kontrolu.',
                      'reason': 'Žádné chyby ani doporučení v kontrolovaném vzorku.'})
    return {'problems': len(problems), 'affected_pages': len({p.location for p, f in problems}),
            'visited': visited, 'html_checked': sum(p.html_checked for p in report.pages),
            'discovered': discovered, 'not_visited': max(0, discovered-visited),
            'uncertain': len(uncertain), 'uncertain_pages': len({p.location for p, f in uncertain}),
            'uncertain_reasons': dict(reasons), 'complete': report.complete,
            'scope': 'Dokončený zadaný rozsah' if report.complete else 'Částečná kontrola',
            'next_steps': steps}


def problem_line(summary):
    count = summary['problems']
    noun = 'problém' if count == 1 else 'problémy' if 2 <= count <= 4 else 'problémů'
    pages = summary['affected_pages']
    return f"{count} {noun} na {pages} " + ('stránce' if pages == 1 else 'stránkách')


def summary_text(report, states=None, search=None):
    s = audit_summary(report, states, search)
    lines = [problem_line(s),
             'Problémy = chyby a doporučení. Neověřené kontroly se počítají zvlášť.', '',
             s['scope'], f"Zpracováno: {s['visited']} z {s['discovered']} objevených URL/souborů. HTML prověřeno u {s['html_checked']}.",
             f"Nezpracováno: {s['not_visited']}. Limit kontroly: {report.limit}.",
             f"Neověřené kontroly: {s['uncertain']}. Dotčené stránky: {s['uncertain_pages']}.",
             'Dokončený rozsah neznamená prověření všech stránek webu ani všech SEO vlastností.', '',
             'Doporučené další kroky']
    for i, step in enumerate(s['next_steps'], 1):
        rank = f"P{step['priority']} · " if step['priority'] else ''
        lines += [f"{i}. {rank}{step['name']}" + (f" · Dotčené stránky: {len(step['pages'])}" if step['pages'] else ''), step['advice'], '']
    lines += ['Proč něco zůstalo neověřené']
    lines += [f'{name}: {count} kontrol (podrobnosti v nálezech stránky).' for name, count in s['uncertain_reasons'].items()]
    if not s['uncertain_reasons']:
        lines.append('Žádné jednotlivé kontroly nejsou označené Neověřeno.')
    if s['not_visited']:
        lines.append('Část objevených adres nebyla zpracována. Důvod a hranice kontroly jsou uvedené níže.')
    lines += ['', 'Rozsah a omezení'] + report.notes
    return '\n'.join(lines)


def indexability(page, mode):
    if not page.html_checked:
        return 'Nelze posoudit: HTML nebylo prověřeno. Viz dostupnost a nálezy.'
    if page.noindex:
        return 'Nalezen zákaz indexování (noindex/none); ověřte, zda je záměrný.'
    if mode != 'URL':
        return 'V HTML není noindex. Dostupnost a pravidla serveru se u místních souborů neověřují.'
    robots = next((f for f in page.findings if f.name == 'Průchod Googlebot podle robots.txt'), None)
    if not robots or robots.status != 'Správně':
        return 'V HTML není noindex; přístup Googlebotu je blokovaný nebo neověřený. Viz nálezy.'
    return 'Bez nalezeného noindex; procházení Googlebotem povoleno. Canonical a další nálezy posuďte níže. Skutečná indexace není ověřena.'


def page_sections(page, mode):
    missing = 'Tento údaj nebyl uložen. Spusťte novou kontrolu.'
    absent = 'Nenalezeno v prověřeném HTML.' if page.html_checked else 'HTML nebylo prověřeno.'
    canonical = '\n'.join(page.declared_canonicals) if page.declared_canonicals is not None else page.canonical or missing
    overview = '\n\n'.join([
        page.location,
        'Titulek\n' + (page.title or absent),
        'Meta popis\n' + (page.description or absent),
        'Canonical v HTML\n' + (canonical or absent),
        'Vyhodnocený cíl canonical\n' + (page.canonical or 'Není k dispozici; viz deklarace a nálezy.'),
        'Indexovatelnost\n' + indexability(page, mode),
        'HTTP\n' + (str(page.http_status) if page.http_status is not None else 'Neověřeno / místní soubor'),
        'Přesměrování\n' + (' → '.join(page.redirects) or 'Není zaznamenáno.'),
        'Režim analýzy\n' + {'source': 'Zdrojové HTML', 'rendered': 'DOM po vykreslení JavaScriptu', 'render_failed': 'Vykreslení selhalo; použito zdrojové HTML'}.get(page.analysis_mode, page.analysis_mode),
    ])
    headings = missing if page.headings is None else '\n'.join(f"H{level}  {'  ' * (level-1)}{text or '(prázdný nadpis)'}" for level, text in page.headings) or 'V HTML nejsou nadpisy H1–H6.'
    raw_links = missing if page.source_links is None else '\n'.join(page.source_links) or 'V HTML nejsou odkazy <a href>.'
    links = 'Odkazy z HTML (původní hodnoty href; relativní adresy nejsou doplněné)\n' + raw_links
    if not page.source_links_complete:
        links += '\nUloženo pouze prvních 10 000 odkazů.'
    links += '\n\nInterní cíle zařazené do kontroly (nemusely být všechny staženy)\n' + ('\n'.join(page.links) or 'Nejsou zaznamenány.')
    links += '\n\nOdkazuje sem z kontrolovaného webu\n' + ('\n'.join(page.inbound) or 'Nejsou zaznamenány.')
    links += '\n\nSitemapy\n' + ('\n'.join(page.sitemap_sources) or 'Nejsou zaznamenány.')
    return {'Přehled': readable(overview), 'Nadpisy': headings, 'Odkazy': links}
