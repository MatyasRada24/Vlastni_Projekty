import html
import json
from dataclasses import asdict
from pathlib import Path

from .engine import Report, STATUSES
from .planning import build_plan
from .repairs import repair_example
from .reporting import audit_summary, page_sections, problem_line
from .theme import readable
from .evolution import search_snapshot, traffic_text

SECTIONS = {'summary': 'Shrnutí a tři další kroky', 'plan': 'Prioritní plán oprav',
            'comparison': 'Změny od předchozí kontroly', 'pages': 'Podrobnosti jednotlivých stránek',
            'measurements': 'Měření PageSpeed a Search Console'}
PRESETS = {'Pro klienta': {'summary', 'plan', 'comparison'},
           'Pro vývojáře': {'summary', 'plan', 'comparison', 'pages'},
           'Kompletní report': set(SECTIONS)}


def save_report(report: Report, path: str, states=None, comparison=None, measurements=None, sections=None, title="Kontrola SEO"):
    selected = set(SECTIONS) if sections is None else set(sections)
    if not selected or selected - SECTIONS.keys():
        raise ValueError('Vyberte alespoň jednu platnou část reportu.')
    target = Path(path)
    summary = audit_summary(report, states, search_snapshot(measurements))
    tasks = build_plan(report, states, search_snapshot(measurements))
    if target.suffix.lower() == ".json":
        data = report.to_dict()
        data['export'] = {'title': title, 'sections': sorted(selected)}
        data['scope_summary'] = {key: value for key, value in summary.items() if key != 'next_steps'}
        if 'summary' in selected:
            data['summary'] = summary
        if 'pages' not in selected:
            data.pop('pages', None)
        if 'measurements' in selected:
            data['measurements'] = measurements or []
        data["repair_plan"] = [{"name": task.name, "priority": task.priority, "reason": task.reason,
                                "effort": task.effort, "pages": task.pages, "work_states": task.state_summary, "traffic": task.traffic,
                                "example": repair_example(task.code), "example_note": "Ilustrační příklad; přizpůsobte skutečnému webu.",
                                "advice": list(dict.fromkeys(f.advice for p, f in task.occurrences if f.advice))} for task in tasks]
        data["comparison"] = {name: [{"page": p.location, "finding": asdict(f)} for p, f in values]
                              for name, values in (comparison or {}).items()}
        if 'plan' not in selected:
            data.pop('repair_plan', None)
        if 'comparison' not in selected:
            data.pop('comparison', None)
        data['comparison_available'] = comparison is not None if 'comparison' in selected else None
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    esc = lambda value: html.escape(str(value), quote=True)
    counts = "".join(f'<div class="stat"><strong>{count}</strong>{esc(status)}</div>' for status, count in report.counts().items())
    pages = []
    for page in report.pages if 'pages' in selected else []:
        rows = "".join(
            f'<tr><td class="status s{STATUSES.index(f.status)}">{esc(f.status)}</td>'
            f'<td><b>{esc(f.name)}</b><p>{esc(readable(f.detail))}</p>'
            f'{"<p class=advice>" + esc(f.advice) + "</p>" if f.advice else ""}</td></tr>'
            for f in sorted(page.findings, key=lambda f: STATUSES.index(f.status))
        )
        evidence = "".join(f'<p class="url">Odkazuje sem: {esc(source)}</p>' for source in page.inbound)
        evidence += "".join(f'<p class="url">Sitemap: {esc(source)}</p>' for source in page.sitemap_sources)
        properties = ''.join(f'<h3>{esc(name)}</h3><pre>{esc(value)}</pre>' for name, value in page_sections(page, report.mode).items())
        pages.append(f'<section><h2>{esc(page.title or "Stránka bez titulku")}</h2><p class="url">{esc(page.location)}</p>{evidence}{properties}<h3>Všechny nálezy stránky</h3><table><thead><tr><th>Stav</th><th>Kontrola a doporučení</th></tr></thead><tbody>{rows}</tbody></table></section>')
    document = '''<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Kontrola SEO — report</title><style>
body{font:16px/1.6 'Segoe UI',sans-serif;background:#eef2f3;color:#203238;margin:0;padding:40px 24px}
main{max-width:1100px;margin:auto}h1{font-size:36px;margin-bottom:4px}h2{font-size:22px;margin-bottom:4px}
.stats{display:flex;gap:16px;flex-wrap:wrap;margin:28px 0}.stat{background:white;padding:16px 24px;border:1px solid #d5dfe2;min-width:130px;border-radius:8px}
.stat strong{display:block;font-size:32px}.url{color:#52647d;overflow-wrap:anywhere}section{margin:28px 0;background:white;border:1px solid #d5dfe2;padding:24px;border-radius:8px}
table{border-collapse:collapse;width:100%;table-layout:fixed}th:first-child,td:first-child{width:130px}th{text-align:left;background:#f4f7f8}td,th{padding:14px;vertical-align:top;border-bottom:1px solid #e2e7ee;overflow-wrap:anywhere}p{margin:6px 0}
.status{font-weight:600}.s0{color:#b42318}.s1{color:#875600}.s2{color:#147448}.s3{color:#59687d}.advice{color:#167568}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.scope{padding:18px;background:#e4f2ee;border-left:4px solid #167568}.scope.partial{background:#fff2de;border-color:#92651c}h3{margin-bottom:6px}a{color:#167568}footer{font-size:14px;color:#52647d}
@media(max-width:600px){body{padding:16px}section{padding:12px}th:first-child,td:first-child{width:80px}td,th{padding:8px}}
@media print{body{padding:0;background:white}section{border:0;padding:0}details{display:block}details>summary{font-weight:bold}details>pre{display:block}thead{display:table-header-group}h2,h3{break-after:avoid}tr{break-inside:avoid}}
</style></head><body><main>'''
    document += f'<h1>{esc(title)}</h1><p class="url">{esc(report.source)}</p><p>{esc(report.created)} · {esc(report.mode)} · Počet stránek: {len(report.pages)}</p><div class="stats">{counts}</div>'
    document += f'<div class="scope {"" if report.complete else "partial"}"><b>{esc(summary["scope"])}</b><p>{esc(problem_line(summary))} · Neověřené kontroly: {summary["uncertain"]}.</p><p>Zpracováno {summary["visited"]} z {summary["discovered"]} objevených URL/souborů; HTML prověřeno u {summary["html_checked"]}. Nezpracováno: {summary["not_visited"]}. Limit: {report.limit}.</p><p>Problémy = chyby a doporučení. Dokončený rozsah neznamená kontrolu celého webu. Počty nahoře označují nálezy, nikoli stránky.</p></div>'
    if 'summary' in selected:
        document += '<section><h2>Doporučené další kroky</h2><ol>'
        for step in summary['next_steps']:
            rank = f"P{step['priority']} · " if step['priority'] else ''
            count = f" · Dotčené stránky: {len(step['pages'])}" if step['pages'] else ''
            document += f'<li><h3>{rank}{esc(step["name"])}{count}</h3><p>{esc(step["advice"])}</p></li>'
        document += '</ol><h3>Co zůstalo neověřené</h3>'
        document += '<ul>' + ''.join(f'<li>{esc(name)}: {count} kontrol</li>' for name, count in summary['uncertain_reasons'].items()) + '</ul>' if summary['uncertain_reasons'] else '<p>Žádné jednotlivé kontroly nejsou označené Neověřeno.</p>'
        document += '<p>Důvody nezpracovaných adres a hranice kontroly jsou uvedené v části Rozsah a omezení.</p></section>' 
    if 'plan' in selected:
        document += '<section><h2>Plán oprav</h2><p>Priority jsou technické odhady. Ruční stav práce není potvrzením odstranění chyby.</p>'
        for task in tasks:
            document += f'<h3>P{task.priority} · {esc(task.name)} · Dotčené stránky: {len(task.pages)}</h3><p>{esc(task.reason)}</p><p>Náročnost (odhad): {esc(task.effort)} · {esc(task.state_summary)}</p>'
            document += '<details><summary>Příklad opravy — přizpůsobte webu</summary><pre>' + esc(repair_example(task.code)) + '</pre></details>'
            document += '<p>' + esc(traffic_text(task.traffic)) + '</p>'
            for advice in dict.fromkeys(f.advice for p, f in task.occurrences if f.advice):
                document += '<p class="advice">Doporučený krok: ' + esc(advice) + '</p>'
            document += '<ul>' + ''.join(f'<li>{esc(url)}</li>' for url in task.pages) + '</ul>'
        document += '</section>'
    if 'comparison' in selected and comparison is None:
        document += '<section><h2>Porovnání s předchozí kontrolou</h2><p>Není k dispozici předchozí kontrola stejného projektu. Změny nelze vyhodnotit.</p></section>'
    if 'comparison' in selected and comparison is not None:
        document += '<section><h2>Porovnání s předchozí kontrolou</h2><p>Neověřené nálezy nejsou automaticky považovány za opravené.</p>'
        for name, occurrences in comparison.items():
            document += f'<h3>{esc(name)} ({len(occurrences)})</h3><ul>'
            document += ''.join(f'<li>{esc(f.name)} — {esc(p.location)}{": " + esc(f.target) if f.target else ""}</li>' for p, f in occurrences) + '</ul>'
        document += '</section>'
    if 'measurements' in selected:
        document += '<section><h2>Rychlost a Search Console</h2><p>Samostatná měření s vlastním časem a obdobím. Laboratorní data nejsou data skutečných návštěvníků.</p>'
        if not measurements:
            document += '<p>K této kontrole nejsou uložená měření.</p>'
        for item in measurements or []:
            document += f'<details><summary>{esc(item["kind"])} · uloženo {esc(item["saved"])}</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{esc(json.dumps(item["data"], ensure_ascii=False, indent=2))}</pre></details>'
        document += '</section>'
    document += "".join(pages) + "<footer><h2>Rozsah a omezení</h2>" + "".join(f"<p>{esc(note)}</p>" for note in report.notes)
    document += '<p>Metodika: <a href="https://developers.google.com/search/docs/fundamentals/seo-starter-guide">Google SEO Starter Guide</a>. Kontroly se vztahují pouze na uvedený vzorek stránek.</p></footer></main></body></html>'
    target.write_text(document, encoding="utf-8")
