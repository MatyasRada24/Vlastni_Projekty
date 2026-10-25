"""Comparable page values, explicit traffic evidence and audit trend data."""
import math


def search_snapshot(measurements):
    return next((item['data'] for item in reversed(measurements or [])
                 if item['kind'] == 'search-console' and not item['data'].get('page')), None)


def traffic_evidence(report, pages, snapshot):
    from .google_services import property_contains
    if not snapshot or report.mode != 'URL' or not property_contains(snapshot.get('property', ''), report.source):
        return None
    aliases = {url for page in pages for url in
               (page.location, page.canonical, page.redirects[-1] if page.redirects else '') if url}
    rows = {}
    for row in snapshot.get('rows', []):
        keys = row.get('keys', [])
        if len(keys) != 1 or keys[0] not in aliases:
            continue
        if any(not isinstance(row.get(k), (int, float)) or not math.isfinite(row[k]) or row[k] < 0
               for k in ('clicks', 'impressions')):
            continue
        rows.setdefault(keys[0], row)
    return {'clicks': sum(row['clicks'] for row in rows.values()),
            'impressions': sum(row['impressions'] for row in rows.values()),
            'matched': len(rows), 'urls': sorted(rows), 'property': snapshot.get('property', ''),
            'start': snapshot.get('start', ''), 'end': snapshot.get('end', ''),
            'created': snapshot.get('created', ''), 'truncated': bool(snapshot.get('truncated'))}


def traffic_text(evidence):
    if evidence is None:
        return 'Návštěvnost není k dispozici. U tohoto auditu načtěte data v Rychlost a Google → Search Console.'
    scope = f"Search Console · {evidence['start']} až {evidence['end']} · {evidence['property']}"
    if not evidence['matched']:
        return scope + '\nŽádné odpovídající řádky. Chybějící data neznamenají nulovou návštěvnost.'
    return (scope + f"\n{evidence['clicks']:,.0f} prokliků · {evidence['impressions']:,.0f} zobrazení · "
            f"{evidence['matched']} odpovídajících URL.\n"
            'V rámci stejné technické priority řadíme podle prokliků, potom zobrazení. '
            'Shoda je přesná URL, konečné přesměrování nebo canonical; návštěvnost není přičítána každé variantě zvlášť. '
            'API nemusí vrátit všechny stránky; nejde o odhad přínosu opravy.' +
            (' Výsledek dosáhl limitu řádků.' if evidence['truncated'] else ''))


def page_values(page):
    if page is None:
        return {key: None for key in ('Titulek', 'Meta popis', 'H1', 'Canonical v HTML', 'Cíl canonical', 'Pokyny k indexaci', 'HTTP')}
    html = page.html_checked and page.analysis_mode != 'render_failed'
    index = next((f.detail for f in page.findings if f.rule == 'Pokyny k indexaci' and f.status != 'Neověřeno'), None)
    return {'Titulek': page.title if html else None, 'Meta popis': page.description if html else None,
            'H1': '\n'.join(text for level, text in page.headings if level == 1) if html and page.headings is not None else None,
            'Canonical v HTML': '\n'.join(page.declared_canonicals) if html and page.declared_canonicals is not None else None,
            'Cíl canonical': page.canonical if html else None, 'Pokyny k indexaci': index if html else None,
            'HTTP': str(page.http_status) if page.http_status is not None else None}


def page_changes(previous, current, url):
    before = next((p for p in previous.pages if p.location == url), None) if previous else None
    after = next((p for p in current.pages if p.location == url), None)
    a, b = page_values(before), page_values(after)
    comparable = before and after and before.analysis_mode == after.analysis_mode
    return [{'field': key, 'before': a[key], 'after': b[key],
             'state': 'Neověřeno' if a[key] is None or b[key] is None or (key != 'HTTP' and not comparable)
             else 'Beze změny' if a[key] == b[key] else 'Změněno'} for key in a]


def trend_rows(store, project_id):
    from .planning import comparison_scope, issues
    result, previous = [], None
    for item in reversed(store.audits(project_id)[:30]):
        _, report = store.load(item['id'])
        state = store.audit_states(item['id'])
        counts = report.counts()
        warnings = comparison_scope(previous, report)['warnings'] if previous else []
        result.append({'id': item['id'], 'created': report.created, 'errors': counts['Chyba'],
                       'warnings': counts['Doporučení'], 'pages': len(report.pages), 'complete': report.complete,
                       'open': sum(state['states'].get(key, 'Otevřené') == 'Otevřené' for key in issues(report)) if state else None,
                       'state_updated': state['updated'] if state else None,
                       'comparable': bool(previous) and not warnings, 'scope_warnings': warnings})
        previous = report
    return result
