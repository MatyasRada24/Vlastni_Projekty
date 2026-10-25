"""Illustrative repair recipes and evidence from narrowly scoped rechecks."""
from datetime import datetime
from html import escape

from .engine import audit_local


# Examples are instructions for a human, never automatic edits to the user's site.
RECIPES = {
    'Titulek stránky': ('Titulek pomáhá rozpoznat téma stránky ve výsledcích hledání.',
        '<title>Oprava notebooků v Brně | Ukázkový servis</title>',
        'Ponechte jeden neprázdný title v head. Text přizpůsobte skutečnému obsahu stránky.'),
    'Meta description': ('Popis shrnuje obsah pro návštěvníka; Google může zobrazit vlastní úryvek.',
        '<meta name="description" content="Opravy notebooků v Brně. Zjistěte postup diagnostiky, možnosti opravy a kontakt na servis.">',
        'Ponechte jeden popis. Nepřidávejte služby ani výhody, které stránka nenabízí.'),
    'Hlavní nadpis H1': ('Jasný hlavní nadpis usnadňuje orientaci v tématu stránky.',
        '<h1>Oprava notebooků v Brně</h1>',
        'Ověřte viditelný hlavní nadpis. Více H1 samo o sobě neznamená penalizaci.'),
    'Hierarchie nadpisů': ('Logická struktura nadpisů pomáhá čtenářům i asistivním technologiím.',
        '<h1>Opravy notebooků</h1>\n<h2>Postup opravy</h2>\n<h3>Diagnostika</h3>',
        'Úroveň nadpisu volte podle struktury, velikost písma nastavte pomocí CSS.'),
    'Alternativní texty obrázků': ('Chybějící alt neposkytuje textovou alternativu významového obrázku.',
        '<img src="servis.jpg" alt="Technik vyměňuje klávesnici notebooku">\n<!-- Pouze dekorace: -->\n<img src="dekorace.svg" alt="">',
        'Popis musí odpovídat konkrétnímu obrázku. Dekorativní obrázky ponechte s prázdným alt.'),
    'Prázdné alternativní texty': ('Prázdný alt může být správný u dekorace; záleží na významu obrázku.',
        '<!-- Významový obrázek -->\n<img src="produkt.jpg" alt="Modrý batoh s přední kapsou">\n<!-- Dekorativní obrázek -->\n<img src="pozadi.svg" alt="">',
        'Nedoplňujte alt plošně. Záměrně prázdný alt u dekorace označte jako Záměrné.'),
    'Pokyny k indexaci': ('Noindex brání zařazení stránky do hledání, pokud jej robot může načíst.',
        'Veřejná stránka určená do hledání:\nOdstraňte nechtěné noindex z meta robots/googlebot i X-Robots-Tag.\n\nStránka záměrně mimo hledání:\n<meta name="robots" content="noindex">',
        'Nejprve rozhodněte, zda má být stránka indexována. Robots.txt neslouží jako náhrada noindex. Absence noindex nepotvrzuje indexaci.'),
    'Kanonická adresa': ('Canonical označuje preferovanou variantu při existenci duplicitních URL.',
        '<link rel="canonical" href="https://example.com/sluzby/">',
        'Adresu nahraďte skutečnou preferovanou verzí stejného obsahu. Ověřte její dostupnost a indexovatelnost. Canonical není povinný u každé stránky.'),
    'canonical.target': ('Nefunkční nebo neindexovatelný cíl narušuje odkaz na preferovanou verzi.',
        '<link rel="canonical" href="https://example.com/sluzby/">\nCíl: HTTP 200, HTML, bez noindex, bez dalšího přesměrování.',
        'Ověřte obsah cíle a přístup Googlebotu. Použijte konečnou preferovanou adresu; externí cíle ověřte ručně.'),
    'canonical.noindex': ('Kombinace noindex a canonical na jinou stránku vyžaduje jasný publikační záměr.',
        'Duplicitní veřejná varianta:\n<link rel="canonical" href="https://example.com/preferovana/">\n\nSamostatné vyloučení z hledání:\n<meta name="robots" content="noindex">',
        'Vyberte postup podle skutečného obsahu a cíle. Noindex nepoužívejte jen jako nástroj pro výběr canonical.'),
    'Jazyk dokumentu': ('Deklarovaný jazyk pomáhá zejména čtečkám obrazovky.',
        '<html lang="cs">', 'Použijte jazyk skutečného obsahu; anglická stránka má například lang="en".'),
    'Mobilní viewport': ('Chybějící viewport může ztížit zobrazení na mobilu.',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        'Vložte do head a ověřte rozložení na mobilu. Samotná značka nepotvrzuje responzivní design.'),
    'Textový obsah': ('Bez dostupného textu nelze dobře posoudit téma stránky.',
        '<main>\n  <h1>Opravy notebooků</h1>\n  <p>Popište nabízenou službu a postup objednání.</p>\n</main>',
        'Pokud text vytváří JavaScript, ověřte vykreslený web. Nepřidávejte výplňový text jen kvůli počtu slov.'),
    'Strukturovaná data JSON-LD': ('Chybný JSON znemožňuje spolehlivé zpracování daného bloku.',
        '<script type="application/ld+json">\n{"@context":"https://schema.org","@type":"WebPage","name":"Kontakt"}\n</script>',
        'Příklad ukazuje platnou syntaxi, nikoli doporučené schéma pro každý web. Ověřte správný typ a obsah v Rich Results Test.'),
    'HTTP odpověď': ('Chybový HTTP stav omezuje dostupnost obsahu pro uživatele i roboty.',
        'Obnovená stránka: HTTP 200 + původní relevantní obsah.\nTrvale přesunutá stránka: HTTP 301 → relevantní náhrada → HTTP 200.',
        'Nevracejte 200 jen místo chybového kódu bez obsahu. Záměrně odstraněná stránka může mít 404/410; odstraňte odkazy na ni.'),
    'link.broken': ('Interní odkaz vede na nedostupnou stránku nebo vadné přesměrování.',
        '<!-- Původně: href="/neexistuje/" -->\n<a href="/sluzby/">Naše služby</a>',
        'Cíl musí obsahově odpovídat odkazu. Opravte href ve zdrojové stránce, obnovte cíl nebo odkaz odstraňte.'),
    'redirect.chain': ('Zbytečné mezikroky přesměrování komplikují cestu k cíli.',
        'Před: /stare → /docasne → /nove\nPo: /stare → /nove (HTTP 200)',
        'Změňte pravidlo přesměrování a interní odkazy směrujte rovnou na konečnou URL.'),
    'redirect.loop': ('Smyčka přesměrování nedovolí načíst konečný obsah.',
        'Před: /a → /b → /a\nPo: /a → /b; /b vrací HTTP 200.',
        'Zkontrolujte pravidla aplikace, serveru a přechod HTTP/HTTPS či www. Odstraňte návrat do smyčky.'),
    'redirect.invalid': ('Bez platného cíle nelze přesměrování následovat.',
        'HTTP/1.1 301 Moved Permanently\nLocation: https://example.com/nova-stranka/',
        'Nastavte platnou hlavičku Location s relevantním cílem. Konkrétní konfigurace závisí na serveru.'),
    'redirect.limit': ('Příliš dlouhou cestu aplikace nedokončila; dostupnost cíle není prokázaná.',
        'Před: dlouhý řetězec přesměrování\nPo: původní URL → konečná URL (HTTP 200)',
        'Najděte konečný relevantní cíl a zkraťte řetězec v pravidlech serveru i odkazech.'),
    'HTTPS': ('Nešifrované HTTP neposkytuje ochranu přenosu jako HTTPS.',
        'http://example.com/sluzby/ → https://example.com/sluzby/',
        'Nasaďte platný certifikát, ověřte HTTPS verzi a teprve potom nastavte přesměrování a aktualizujte odkazy.'),
    'Průchod Googlebot podle robots.txt': ('Blokace Googlebotu může zabránit načtení obsahu, pokud je nezáměrná.',
        'Pokud má být /verejne/ procházeno, odstraňte blokující pravidlo pro tuto cestu.\nSoukromé nebo záměrně blokované části ponechte podle záměru.',
        'Prověřte skupinu User-agent a pravidla konkrétní URL. Robots.txt není zabezpečení soukromých dat.'),
    'sitemap.indexability': ('Sitemap obsahuje URL, která neodpovídá dostupné preferované verzi.',
        '<url>\n  <loc>https://example.com/preferovana/</loc>\n</url>',
        'Do sitemapy dejte konečné preferované URL určené k indexaci. Po změně spusťte celý audit včetně sitemap.'),
    'Duplicitní titulek': ('Stejný titulek na různých stránkách ztěžuje jejich rozlišení.',
        'Stránka A: <title>Opravy notebooků | Servis</title>\nStránka B: <title>Výměna baterie | Servis</title>',
        'Odlište titulky podle obsahu. Skutečně duplicitní varianty řešte vhodnou kanonizací. Potom zopakujte úplný audit.'),
    'Duplicitní meta popis': ('Stejný popis neodlišuje nabídku jednotlivých stránek.',
        'Stránka A: Popis diagnostiky a oprav notebooků.\nStránka B: Popis výměny baterie a jejího objednání.',
        'Napište vlastní shrnutí každé odlišné stránky. Po opravě porovnejte celý kontrolovaný rozsah.'),
}


def recipe(code):
    return RECIPES.get(code, (
        'Priorita vychází ze závažnosti nalezeného technického problému.',
        'Najděte nastavení uvedené v nálezu, upravte je podle doporučení a změnu nasaďte.',
        'Ověřte dotčenou stránku; při neúplném výsledku proveďte nový audit.'))


def repair_example(code, page=None):
    if code == 'Titulek stránky' and page:
        heading = next((text for level, text in page.headings if level == 1 and text.strip()), '')
        if heading:
            return '<title>' + escape(heading, quote=True) + '</title>'
    return recipe(code)[1]


def repair_instructions(task, page=None):
    _, _, check = recipe(task.code)
    return (f'Proč priorita P{task.priority}\n{task.reason}\n\n'
            f'Příklad opravy (upravte podle webu)\n{repair_example(task.code, page)}\n\n'
            f'Postup a ověření\n{check}\n\n'
            'Příklad není automatická úprava webu ani záruka vyšší návštěvnosti.')


def verify_repairs(previous, occurrences, cancel=None, progress=None):
    from .crawler import crawl_selected
    from .planning import compare_reports, issue_key, issues
    locations = list(dict.fromkeys(page.location for page, _ in occurrences))
    if not locations or len(locations) > 1000:
        raise ValueError('Vyberte 1 až 1000 dotčených stránek.')
    if previous.mode == 'URL':
        current = crawl_selected(previous.source, locations, cancel=cancel,
                                 progress=progress, rendering=previous.rendering)
    else:
        current = audit_local(previous.source, limit=1000, selected=locations,
                              cancel=cancel, progress=progress)
    delta = compare_reports(previous, current)
    fixed = {issue_key(p, f) for p, f in delta['Odstraněné']}
    remaining = issues(current)
    pages = {page.location: page for page in current.pages}
    rows = []
    for page, finding in occurrences:
        key = issue_key(page, finding)
        actual = pages.get(page.location)
        comparable = actual and actual.analysis_mode == page.analysis_mode and actual.analysis_mode != 'render_failed'
        if cancel and cancel.is_set():
            status, detail = 'Neověřeno', 'Ověření bylo zastaveno.'
        elif not comparable:
            status, detail = 'Neověřeno', 'Stránka nebyla ověřena srovnatelným způsobem.'
        elif key in remaining:
            status, detail = 'Přetrvává', remaining[key][1].detail
        elif key in fixed:
            status, detail = 'Opraveno', 'Původní nález byl znovu ověřen a nebyl nalezen. Nejde o potvrzení bezchybnosti celé stránky.'
        else:
            status = 'Neověřeno'
            detail = ('Pro ověření tohoto nálezu spusťte úplný audit včetně původního rozsahu.'
                      if finding.rule.startswith('Duplicitní') or finding.rule == 'sitemap.indexability' else
                      'Chybí dokončená kontrola původního nálezu. Zkontrolujte dostupnost a rozsah ověření.')
        evidence = [f'{f.status} · {f.name}: {f.detail}' for f in actual.findings
                    if f.check_key == finding.check_key or f.status == 'Neověřeno'] if actual else []
        rows.append({'key': key, 'page': page.location, 'name': finding.name, 'rule': finding.rule,
                     'target': finding.target, 'status': status, 'detail': detail, 'evidence': evidence})
    return {'created': datetime.now().astimezone().isoformat(timespec='seconds'),
            'source': previous.source, 'mode': previous.mode, 'rendering': previous.rendering,
            'requested': locations, 'notes': current.notes, 'results': rows}
