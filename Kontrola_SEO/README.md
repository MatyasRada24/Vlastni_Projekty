# Kontrola SEO pro Windows

Desktopová aplikace v češtině s plánem oprav, historií auditů, vykreslením JavaScriptu, PageSpeed a propojením s Google Search Console. Vysvětluje nálezy jako **Chyba**, **Doporučení**, **Správně** nebo **Neověřeno**.

## Spuštění

Otevřete `dist\Kontrola_SEO_1.0.exe` nebo dvakrát klikněte na `Spustit_Kontrola_SEO.bat`. Samostatný EXE nepotřebuje instalaci Pythonu. Pro volitelné vykreslování potřebuje nainstalovaný Edge, Chrome nebo Brave. Není digitálně podepsaný. Pokud sestavený EXE není k dispozici, dávkový soubor použije nainstalovaný Python s Tkinterem.

Verze 1.0 přidává pět navazujících funkcí:

- **Priority podle Search Console:** v Plánu oprav se v rámci stejné technické priority P1–P3 řadí podle uložených prokliků, pak zobrazení a počtu dotčených stránek. Data je nutné načíst a uložit u otevřeného auditu. Shody jsou přesné URL, konečné přesměrování nebo canonical; stejný řádek se ve skupině nezapočítá vícekrát. Uvedeno je období i služba. Bez odpovídajících řádků se zobrazuje Bez dat, nikoli nulová návštěvnost. Nejde o odhad přínosu opravy. Pořadí a metriky se přenášejí také do exportu.
- **Vývoj webu:** v Projektech a historii tlačítko Vývoj webu zobrazí graf chyb a doporučení, otevřených nálezů nebo skóre Lighthouse. Zobrazuje posledních 30 auditů nebo až 30 měření vybrané URL a zařízení z posledních 200 projektových měření. Rozdílný rozsah, částečný audit či jiný režim přeruší spojnici; pokles nálezů sám neprokazuje opravu. Historické stavy práce se ukládají od této verze, u starších auditů chybí. Ruční změna stavu aktualizuje záznam daného auditu, nikoli ostatních auditů. Graf uvádí čas této aktualizace. Rychlost je laboratorní skóre; jiná verze Lighthouse nebo prostředí přeruší spojnici.
- **Stránka před a po:** dostupné v Detailu stránky (předchozí audit) a v Historii (zvolená dvojice auditů). Porovnává titulek, meta popis, H1, canonical, pokyny k indexaci a HTTP. Prázdné údaje se odlišují od nezměřených; srovnává se přesná URL a odpovídající režim analýzy. Hodnoty lze číst celé ve dvou spodních panelech. Změna není automaticky zlepšení.
- **Obnova rozpracované kontroly:** po každé dokončené stránce se do místní databáze transakčně ukládá průběžný stav, fronta URL a podklady. Po zastavení nebo zavření aplikace použijte Pokračovat v kontrole u vstupu. Již zpracované stránky se znovu nestahují; obnovený audit může obsahovat údaje z různých časů, což uvádí v omezeních. Robots.txt se při nových požadavcích ověřuje znovu. HTML ani přihlašovací tokeny se do rozpracovaného auditu neukládají. Existuje jeden rozpracovaný audit; před nahrazením novou kontrolou se aplikace zeptá. Při dosažení limitu lze zvolit vyšší celkový limit, nejvýše 1000. U souborů se kontroluje seznam, velikost a čas změny, u ZIP také CRC; při změně zdroje je nutná nová kontrola. Dokončené audity zůstávají v historii odděleně. CLI a cílené ověření oprav obnovu nepoužívají. Během běhu se zobrazují dokončené/čekající stránky a právě zpracovávaná adresa.
- **Diagnostika:** chyby rozlišují kvótu, přihlášení, oprávnění, vypnuté API, síť, časový limit, úložiště a neočekávanou chybu aplikace. Kopírovat diagnostiku je v hlášení služeb a po chybě auditu. Kopírují se pouze povolená technická pole (verze, čas, akce, kategorie, typ a HTTP), žádné původní chybové texty, adresy, cesty, klíče ani tokeny.

Verze 0.9.1 obsahuje aktualizovaný vzhled ze zdrojových souborů: tmavou boční navigaci, sjednocenou indigo paletu a upravené panely i ovládací prvky. Spouštěcí soubor otevírá tuto novou sestavenou verzi.

Verze 0.9.0 zpřesňuje **Plán oprav**. U každé skupiny zobrazuje důvod priority a ilustrační příklad opravy, který je nutné přizpůsobit webu. Příklady se přidávají i do exportovaného plánu. Priorita celé skupiny vychází z jejího nejzávažnějšího nálezu; není odhadem růstu návštěvnosti.

Vyberte skupinu nebo jednotlivý nález v poli **Výběr nálezů pro stav i ověření** a klikněte na **Ověřit stránky**. Karta **Výsledek ověření** zobrazí Opraveno, Přetrvává nebo Neověřeno, čas a podklady. U URL se znovu načtou vybrané stránky a jejich přímé interní odkazy/canonical, maximálně 1000 zpracovaných URL; robots.txt a původní režim JavaScriptu se respektují. Neprocházejí se sitemapy ani další úrovně odkazů. U lokálních zdrojů se znovu přečtou vybrané HTML soubory nebo položky ZIP.

Ověření se ukládají samostatně k původnímu auditu, zobrazí se i po restartu a nemění původní nálezy ani ruční stavy práce. Při zastavení nebo zavření plánu se rozpracovaný výsledek neuloží. Chybějící stránka, neporovnatelný režim nebo nedokončená kontrola nejsou potvrzením opravy. Odstranění duplicit a konfliktů sitemap vyžaduje úplný audit. Ověření původního nálezu neznamená, že celá stránka je bez dalších problémů. Podrobné záznamy cílených ověření zůstávají v aplikaci; export obsahuje původní audit a příklady, ne tyto nové záznamy.

Příklady pro [titulky](https://developers.google.com/search/docs/appearance/title-link), [canonical](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) a [noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing) vycházejí z dokumentace Google Search Central.

Verze 0.8.0 přidává průvodce **Připojení služeb**: pro Search Console a PageSpeed zvlášť projdete přípravu, přihlášení nebo uložení klíče a skutečné ověření. Test PageSpeed funguje i bez auditu, odešle zadanou URL Googlu a neukládá se do historie. Uložený klíč ani token není sám o sobě potvrzením dostupnosti služby. Chyba jedné služby nemění stav druhé.

V **Projektech a historii** vyberete aktuální a předchozí audit. Uvidíte počty chyb a doporučení před a po kontrole, společné URL a upozornění na odlišný nebo částečný rozsah, rozdílné vykreslení či dokončené kontroly. Kliknutím na souhrny filtrujete nové, ověřeně odstraněné a další nálezy. Tlačítko **Rozsah** vypíše i přidané a vynechané adresy. Pokles počtu nálezů při menším rozsahu se nepovažuje za opravu.

Verze 0.7.5 přepracovává kartu PageSpeed: prázdný stav vede k prvnímu auditu URL, formulář jasně označuje stránku a zařízení, výsledky oddělují hlavní metriky, podrobnosti a doporučení Lighthouse.

Verze 0.7.4 přepracovává Projekty a historii: přehled kontrol ukazuje více řádků, změny se porovnávají v hlavní tabulce a detail vybrané změny je vedle ní. Souhrn počtů rozděluje nové, přetrvávající, odstraněné, neověřené a poprvé kontrolované nálezy.

Verze 0.7.3 sjednocuje horní navigaci do kompaktního přepínače sekcí. Aktivní část je zvýrazněná a po zavření jejího okna se aplikace vrátí na Přehled.

Verze 0.7.2 umožňuje načíst stránky i dotazy Search Console samostatně, bez otevřeného SEO auditu. V tomto režimu se data zobrazují do zavření okna a neukládají se k auditu ani nespojují s nálezy. Při otevřeném URL auditu se dál ukládají a párují jako dosud. Chybné zadání nebo chybějící audit pro PageSpeed nezmění úspěšně ověřený stav připojení.

Verze 0.7.1 zobrazuje na všech kartách Rychlost a Google stav účtu, přístupu k Search Console a PageSpeed. **Ověřit připojení** načte dostupné weby a ukáže čas úspěšného ověření. Uložené přihlášení a historické měření se při novém otevření označí jako neověřené pro aktuální spojení. Probíhající operace ukazuje činnost, uplynulé sekundy, průběh a konečný úspěch, chybu nebo zastavení.

Verze 0.7 používá schválený grafický redesign: horní navigaci s aktivní záložkou, kompaktní zadání, společný pás stavů a přehlednější tabulku s ikonami. Detail se zobrazí po výběru nálezu a lze jej zavřít. Obsahuje postup opravy, případně příklad meta popisu, otevření stránky a kopírování úplné URL. V tabulce se adresy stejného webu zobrazují jako kratší cesty; vyhledávání a akce používají úplné adresy. Rozsah kontroly je dostupný přes **Zobrazit rozsah**, připojení služeb přes **Nastavení**.

Verze 0.6.3 si pamatuje poslední zadanou URL, cestu k souborům, zvolený režim, limit stránek a volbu JavaScriptu. Zadání se průběžně ukládá místně a obnoví při příštím spuštění, i když jste kontrolu ještě nespustili.

Verze 0.6.2 rozlišuje vypnuté Search Console API, chybějící oprávnění a vypršené přihlášení. Při vypnutém API nabízí přímý odkaz do Google Cloud a zachová uložené přihlášení.

Verze 0.6.1 opravuje nenápadné selhání měření: chyby Google se zobrazí nad kartou s konkrétním dalším krokem. PageSpeed bez API klíče může Google okamžitě odmítnout kvůli kvótě (HTTP 429). Tlačítko **PageSpeed v prohlížeči** otevře vybranou URL ve webové službě; tento výsledek se neukládá do historie aplikace. **Změřit a uložit** nadále používá API. Search Console předem kontroluje připojení účtu a při prázdném výběru nabídne načtení dostupných webů. Účet ani klíč se nevytvářejí automaticky.

Verze 0.6 přidává **Detail stránky**, **Shrnutí auditu** a **volitelný obsah exportu**.

- Klikněte na adresu v tabulce výsledků nebo na **Stránky**. Detail nabízí přehled SEO údajů, nadpisy H1–H6, odkazy a všechny nálezy vybrané stránky. Tlačítko **Otevřít v prohlížeči** je dostupné pro HTTP/HTTPS adresy z URL auditu. Lokální soubory se tímto tlačítkem nespouštějí.
- Nadpisy a původní hodnoty odkazů se ukládají od verze 0.6. Starší historie zůstává čitelná a u chybějících údajů nabídne novou kontrolu. Detail nikdy sám znovu nestahuje web. Ukládá se nejvýše prvních 10 000 odkazů z HTML; případné zkrácení je označeno.
- **Shrnutí auditu** odděluje chyby a doporučení od neověřených kontrol, počítá postižené stránky a ukazuje až tři prioritní další kroky. Rozlišuje zpracované adresy, skutečně prověřené HTML a nezpracovaný objevený rozsah. Dokončený rozsah není potvrzení kontroly celého webu ani skutečné indexace.
- **Exportovat report** otevře volbu názvu, formátu HTML/JSON a částí reportu. **Pro klienta** zahrne shrnutí, plán oprav a změny; **Pro vývojáře** navíc stránky s důkazy. Měření Google lze přidat samostatně. Rozsah a omezení kontroly jsou vždy přiložené. Bez předchozího auditu report výslovně uvádí, že změny nelze porovnat. HTML lze vytisknout do PDF v prohlížeči. JSON obsahuje jen zvolené části; příkazová řádka nadále exportuje kompletní data.

Verze 0.5 sjednocuje vzhled všech oken, přidává klikatelné souhrny pro rychlé filtrování, hledání ve výsledcích (Ctrl+F), zrušení filtrů a kopírování adresy nálezu. Plán oprav zobrazuje detail a změnu stavu vedle seznamu. Historie odděluje výběr projektu, kontroly a srovnání. Tlačítko **Zpět na přehled** nebo Escape zavře vedlejší okno.

U URL je volba **Včetně JavaScriptu** a nabídka **Rychlost a Google** s kartami **Rychlost webu**, **Search Console** a **Připojení služeb**. [Podrobný návod k vykreslení, PageSpeed a nastavení Google účtu](GOOGLE_SETUP.md). Search Console potřebuje vlastní OAuth klient typu Desktop app a přihlášení; PageSpeed může kvůli kvótě vyžadovat vlastní API klíč.

Verze 0.2.1 opravuje rozmazání při zvětšení obrazovky ve Windows. EXE deklaruje Per-Monitor V2 DPI awareness; text, rozměry panelů, odsazení, řádky tabulky a kreslené ikony se vykreslují podle DPI monitoru. Při změně DPI se rozhraní obnoví se zachováním výsledků, filtrů a probíhající kontroly. Starší EXE tuto opravu neobsahují.

Verze 0.2 přináší světlé rozhraní se zeleným akcentem, kompaktní zadání zdroje, přehled stavů, detail nálezu vedle výsledků a chybová hlášení přímo v okně. Auditovací jádro zůstává stejné.

1. Zvolte **Webová adresa**, nebo **Soubory webu** (HTML, ZIP nebo složka).
2. Zadejte URL či vyberte soubory a nastavte limit 1–1000 URL (výchozí hodnota 100).
3. Klikněte na **Spustit kontrolu**.
4. Kliknutím na nález zobrazíte vysvětlení a doporučenou opravu. Filtry omezí výsledky podle stránky a stavu.
5. **Exportovat report** umožní vybrat obsah a uložit jej do HTML nebo JSON. HTML lze otevřít v prohlížeči a vytisknout do PDF.

Pro první vyzkoušení použijte `priklady\ukazkovy-web.html`. Obsahuje záměrně chybějící popis a alternativní text obrázku.

## Co aplikace kontroluje

- Titulky, meta popisy, H1 a návaznost úrovní nadpisů.
- Přítomnost atributů alt, jazyka dokumentu a mobilního viewportu.
- Meta pokyny robots/googlebot, canonical a syntaxi JSON-LD.
- Přítomnost textového obsahu a duplicitní titulky či popisy mezi kontrolovanými stránkami.
- U URL navíc stav HTTP, HTTPS, hlavičku X-Robots-Tag a základní pravidla robots.txt.
- Interní odkazy včetně parametrů, jejich chybové cíle a zdrojové stránky odkazů.
- Řetězce a smyčky přesměrování; robots.txt se respektuje i na jednotlivých cílech přesměrování.
- Dostupnost interních cílů canonical, jejich noindex, další canonical a přístup Googlebotu.
- URL objevené ze sitemap, vnořených sitemap indexů a gzip sitemap; konflikty mezi sitemapou, noindex, canonical, HTTP stavem a přesměrováním.

Výsledky nejsou umělé univerzální SEO skóre: například počet slov ani přesná délka titulku nejsou pevnou podmínkou dobrého SEO. Doporučení vyžadují posouzení účelu stránky. Záměrný noindex může být správné nastavení.

## Plán oprav a historie (verze 0.3)

Po kontrole otevřete tlačítko **Plán oprav** v horní liště. Stejné nálezy jsou seskupené s počtem dotčených stránek, zdůvodněnou prioritou P1–P3 a orientační náročností. Detail obsahuje konkrétní stránky, nálezy, doporučení a dostupné zdroje odkazů. Opakování na více stránkách je podnět ke kontrole šablony, nikoli důkaz společné příčiny.

Vyberte celou skupinu nebo jednotlivý nález a uložte stav **Otevřené**, **Vyřešené** nebo **Záměrné**. Vyřešené je ruční označení. Pokud další audit stejný problém znovu najde, automaticky jej otevře; záměrné rozhodnutí zachová. Stavy měníte pouze u nejnovějšího auditu projektu. Nemění samotná naměřená data.

**Projekty a historie** uchovávají každou dokončenou i částečnou kontrolu. Projekt se vytvoří automaticky podle hostitele a portu URL, nebo podle absolutní cesty k místním souborům. Opakovaná kontrola stejného zdroje patří do stejného projektu. Projekt lze přejmenovat. Otevření starého auditu nic znovu nestahuje a nevytváří další záznam.

Vyberte kontrolu a v poli **Porovnat s** zvolte některou starší kontrolu stejného projektu. Změny jsou rozdělené na:

- **Nové:** nálezy na dříve srovnatelně zkontrolovaných stránkách.
- **Přetrvávající:** tentýž typ problému na téže stránce a cíli.
- **Odstraněné:** odstranění lze potvrdit novým měřením; například nefunkční odkaz už neexistuje nebo jeho cíl odpovídá úspěšně.
- **Neověřené:** dřívější nález nelze ověřit, například kvůli limitu, nedostupné stránce či odlišnému rozsahu.
- **Poprvé kontrolované:** nález z nové stránky nebo kontroly bez srovnatelného předchozího výsledku.

Porovnání je technické; nedokazuje změnu návštěvnosti. U duplicit se odstranění potvrzuje pouze při dostatečně srovnatelném dokončeném rozsahu. HTML/JSON export obsahuje plán oprav a při exportu uloženého auditu také srovnání s bezprostředně předchozí kontrolou projektu. Ruční stavy v exportu odpovídají aktuálnímu stavu práce.

### Uložení dat

Databáze je v `%LOCALAPPDATA%\KontrolaSEO\projects.sqlite3`. Zůstává zachovaná mezi spuštěními a verzemi EXE. Pro zálohu zavřete aplikaci a zkopírujte tento soubor. Proměnná prostředí `SEO_CHECKER_DATA_DIR` umožňuje zvolit jinou datovou složku; testy používají vlastní dočasnou databázi. Reporty a měření se uchovávají lokálně. PageSpeed a Search Console komunikují s Googlem po spuštění příslušné akce. Vykreslování stahuje i zdroje stránky včetně externích skriptů a dat. Přihlašovací údaje jsou šifrované v samostatném souboru `google-secrets.dat`.

## Rozsah a omezení

- JavaScript se spouští pouze ve volitelném URL režimu. React/Vue/PHP zdrojový projekt není hotová HTML stránka; použijte URL nasazeného webu nebo exportované HTML. Lokální soubory se analyzují bez spuštění skriptů.
- Technický audit neověřuje skutečnou indexaci, zpětné odkazy, kvalitu obsahu ani mobilní vzhled. Rychlost, dostupná data návštěvníků a výkon ve vyhledávání jsou v samostatných přehledech PageSpeed a Search Console. Čas stažení HTML není výkon celé stránky.
- Prochází objevené URL stejného webu včetně parametrů do zadaného limitu. Povoluje přechod HTTP/HTTPS a variantu www téhož hostitele na standardních portech. Externí odkazy ani externí canonical cíle nestahuje. Obrázkové src nejsou samostatně kontrolovány. URL neobjevené v odkazech ani sitemapách nemohou být prověřeny.
- robots.txt vyhodnocuje standardní knihovna Pythonu; neimplementuje veškerá rozšíření jednotlivých vyhledávačů. Při nedostupných pravidlech procházení zastaví. Stav Googlebot se uvádí zvlášť od pravidel pro KontrolaSEO.
- Načte sitemapy uvedené v robots.txt, případně `/sitemap.xml`. Podporuje XML urlset, sitemapindex a gzip, maximálně 20 sitemap a 10 000 objevených URL, nejvýše 10 000 odkazů na jednu HTML stránku. Přesměrování sleduje do 10 kroků. Nadlimitní nebo nedostupné cíle označí jako neověřené.
- Načtené HTML, XML a rozbalená sitemap mají limit 5 MB. Síťové požadavky používají odstup alespoň 0,15 sekundy mezi dokončením předchozího požadavku a dalším požadavkem na stejný původ, případně delší crawl-delay. Crawl-delay nad 30 sekund procházení zastaví.
- JSON-LD kontroluje syntakticky; neověřuje slovník schema.org ani nárok na rozšířené výsledky. Canonical kontroluje v HTML, nikoli v HTTP Link hlavičce.
- Lokální soubory se nikam neodesílají. ZIP se čte přímo bez rozbalování. Limit je 5 MB na HTML a 50 MB načteného HTML celkem, nejvýše 1000 souborů.
- Zastavení počká na probíhající požadavek (HTTP timeout 12 s, navigace prohlížeče 25 s); hotové výsledky zachová jako částečný report. Zavření aplikace skryje okno, zastaví kontrolu a počká na úklid prohlížeče. Samostatné Google API požadavky mají timeout 30 s, PageSpeed 90 s.
- Projekty a auditní snímky se ukládají automaticky do lokální SQLite databáze. Při chybě ukládání aplikace výslovně oznámí, že výsledek není uložen; v takovém případě použijte export.

## Vývoj

Python s Tkinterem a závislostmi z `requirements.txt` (Playwright). Ověřeno na Pythonu 3.14. Playwright je zabalený v EXE; prohlížeč samotný se používá z instalace Edge/Chrome/Brave.

```powershell
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
python -m tests.gui_smoke
python -m tests.dpi_smoke
python -m tests.workspace_smoke
python -m tests.insights_smoke
python -m tests.google_recovery_smoke
python -m tests.redesign_smoke
python -m tests.report_ui_smoke
python -m tests.render_smoke
```

Sestavení pro Windows (PyInstaller je pouze sestavovací závislost):

```powershell
python -m pip install pyinstaller
.\build_windows.ps1
```

Sestavovací skript vždy přidává `windows.manifest`; nevynechávejte jej, jinak Windows může znovu použít rozmazávající bitmapové zvětšení. Pro spuštění ze zdrojů se DPI nastavuje před vytvořením prvního okna Tk. `python -m tests.packaged_smoke` ověří vykreslování v hotovém EXE nad lokálním testovacím webem.

Volitelný audit bez okna: `dist\Kontrola_SEO_1.0.exe --audit-url https://example.com/ --render-js --limit 10 --output report.json`. Zapisuje pouze export a nepřidává projekt do historie.

## Podklady pro metodiku

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google: robots meta tag a X-Robots-Tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)
- [Google: JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)

Tato aplikace není služba Googlu a nepředpovídá pořadí výsledků vyhledávání.

## Bezpečnost vydání

Před publikací a používáním vykreslování si přečtěte [SECURITY.md](SECURITY.md). Zdrojový balíček bez osobních dat vytvoří `python -m tools.prepare_release`.
