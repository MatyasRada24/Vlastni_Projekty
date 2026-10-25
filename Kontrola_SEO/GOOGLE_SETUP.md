# Rychlost a Google — verze 0.8.0

## Průvodce připojením

Otevřete **Rychlost a Google → Připojení služeb** a vyberte **Search Console** nebo **PageSpeed**. Přepínače 1–3 umožňují vrátit se k libovolnému kroku. Výběr OAuth JSON vás posune k přihlášení; uložení API klíče k ověření.

- **Search Console:** příprava OAuth klienta → přihlášení účtu → **Ověřit Search Console**. Úspěch potvrzuje dostupnost seznamu webů, nikoli automaticky data konkrétního webu. Pro ně pokračujte na **Přejít na data webu**.
- **PageSpeed:** zapnutí API → uložení klíče → zadání veřejné URL a **Ověřit PageSpeed**. Proběhne skutečné mobilní měření (až 90 sekund, čerpá kvótu). Tento test funguje bez auditu a neukládá se do historie. Pro uložené měření použijte kartu Rychlost webu u otevřeného URL auditu.
- Ověření obou služeb je nezávislé. Uložený klíč není totéž co úspěšná odpověď API. Po restartu aplikace se aktuální dostupnost znovu ověřuje; přihlašovací údaje zůstávají uložené.

## Vykreslení JavaScriptu

U zadání URL zaškrtněte **Včetně JavaScriptu**. Aplikace najde nainstalovaný Edge, Chrome nebo Brave a spustí izolovaný prohlížeč bez vašeho přihlášení, cookies a historie. HTML nejprve stáhne s respektováním robots.txt. Stejný dokument předá prohlížeči, který načte i skripty a další zdroje, případně z externích domén.

Analyzuje DOM po DOMContentLoaded a dalších dvou sekundách; navigace má limit 25 sekund. Dynamicky vzniklé odkazy vstoupí do stejného crawl limitu. Režim nekliká, nescrolluje a nepřihlašuje se. Není simulací Googlebotu. Klientské přesměrování mimo původní URL zastaví a doporučí samostatnou kontrolu cíle.

Pokud vykreslení selže, nález je **Neověřeno**, report je částečný a ostatní kontroly stránky vycházejí ze zdrojového HTML. Historie nepovažuje změnu režimu za potvrzenou opravu. Lokální HTML a ZIP se nadále analyzují bez spuštění skriptů.

## PageSpeed Insights

Pro rychlé otevření měření bez nastavení klíče použijte **PageSpeed v prohlížeči**. Výsledek z webové služby se automaticky nepřenáší do aplikace. Pro měření a uložení k auditu použijte **Změřit a uložit**.

Když se měření ihned zastaví, přečtěte hlášení nad kartou. Při **HTTP 429** Google odmítl požadavek kvůli kvótě; nejde o dokončené měření. Tlačítko **Nastavit PageSpeed klíč** otevře příslušné pole. Pokud již klíč máte, ověřte kvótu jeho projektu nebo měření zopakujte později.


Po uložení URL auditu otevřete **Rychlost a Google → Rychlost webu**, vyberte stránku a **Mobil** nebo **Počítač**. Měření odešle URL Googlu, trvá až 90 sekund a uloží výsledek k otevřenému auditu.

- **Laboratoř (Lighthouse):** skóre výkonu, FCP, LCP, Speed Index, TBT, CLS a doporučení. Jde o jednu simulovanou návštěvu. TBT není INP a skóre výkonu není SEO skóre.
- **Skuteční návštěvníci (CrUX):** dostupné percentily a kategorie odděleně pro URL a celý původ (origin). Chybějící data nejsou úspěšný test. Google může přestat vracet CrUX v PageSpeed; aplikace v takovém případě zobrazí nedostupnost. Samostatné CrUX API zatím není připojené.

Při HTTP 429 nebo omezení kvóty zadejte vlastní klíč na kartě **Připojení služeb**. V Google Cloud zapněte **PageSpeed Insights API**, vytvořte API klíč a omezte jej na toto API. Klíč nepatří do zdrojového kódu ani reportu. Měření lze zkusit bez klíče, dostupnost ale závisí na kvótě Googlu. Živý test bez klíče v tomto prostředí vrátil HTTP 429.

## Připojení Google Search Console

Od verze 0.7.2 lze připojit účet, načíst weby a zobrazit stránky i dotazy bez otevřeného auditu. Samostatné zobrazení data neukládá. Chcete-li data uložit a spojit s nálezy, nejprve spusťte nebo otevřete URL audit a pak otevřete Rychlost a Google. Ukládání měření PageSpeed nadále vyžaduje URL audit; samotný test připojení v průvodci jej nevyžaduje.

Pokud aplikace hlásí, že **Google Search Console API není zapnuté**, přihlášení může být již uložené. Klikněte na **Zapnout Search Console API**, v Google Cloud vyberte stejný projekt, ze kterého pochází OAuth JSON, a zvolte **Enable / Povolit**. Po aktivaci chvíli počkejte a v aplikaci klikněte na **Načíst weby**. Není nutné vytvářet nový OAuth klient ani PageSpeed klíč. Vypnuté API se nyní rozlišuje od nedostatečných oprávnění a vypršeného přihlášení.

Potřebujete vlastní OAuth klient a Google účet s přístupem k danému webu. Klient ani přístup k vašemu účtu nejsou v aplikaci předvyplněné.

1. V [Google Cloud](https://console.cloud.google.com/apis/credentials) vytvořte nebo vyberte projekt a zapněte **Google Search Console API**.
2. Nastavte OAuth consent screen / Google Auth Platform: název aplikace, audience a kontaktní údaje. V testovacím režimu přidejte svůj Google účet mezi testovací uživatele. Při veřejné distribuci mohou platit další požadavky Googlu na ověření aplikace.
3. Vytvořte OAuth client ID typu **Desktop app** a stáhněte JSON. Nepoužívejte Web application ani service account.
4. V aplikaci otevřete **Rychlost a Google → Připojení služeb → Vybrat OAuth JSON…**, poté **Přihlásit Google účet**. Souhlas dokončete ve výchozím prohlížeči. Návrat probíhá na dočasném lokálním portu `127.0.0.1`, s kontrolou state a PKCE.
5. Na kartě **Search Console** vyberte dostupný web, období `RRRR-MM-DD` a **Načíst data**. Podporované jsou URL-prefix i doménové služby. Vybraná služba musí obsahovat zdroj otevřeného URL auditu.
6. Vyberte stránku a načtěte její vyhledávací dotazy. Pod tabulkou uvidíte související nálezy z auditu. Párování používá přesnou URL, konečnou adresu přesměrování nebo canonical; neslučuje automaticky HTTP/HTTPS ani varianty www.

Tabulka ukazuje prokliky, zobrazení, CTR a průměrnou pozici. Řadí stránky podle zobrazení. Filtr **Příležitosti** vybere alespoň 100 zobrazení a CTR pod 2 %. Je to pracovní filtr, nikoli obecná hranice správného SEO. Posuďte také pozici, dotazy a záměr vyhledávání.

Načítají se dokončená data pro webové vyhledávání, do 50 000 řádků stránek a do 1 000 dotazů vybrané stránky. API negarantuje všechny řádky, anonymizované dotazy mohou chybět. Data stránek se nesčítají z dotazů. Období Search Console používá Pacific Time, nikoli českou půlnoc. Prázdný výsledek znamená, že API pro výběr nevrátilo data; neprokazuje nulovou návštěvnost.

## Uložení a odpojení

Přístup je pouze ke čtení (`webmasters.readonly`). Tokeny, OAuth nastavení a PageSpeed klíč jsou v `google-secrets.dat` vedle databáze, šifrované Windows DPAPI pro váš účet. Obnova tokenu je automatická. **Odpojit na tomto PC** smaže místní tokeny; úplné odvolání oprávnění lze provést v Google účtu. Přenos šifrovaného souboru na jiný počítač či účet nemusí fungovat; přihlaste se tam znovu.

Měření se ukládají samostatně s vlastním časem a obdobím. Původní audit se nepřepisuje. Po otevření auditu z historie se zobrazí poslední uložené měření dané URL/zařízení a poslední načtení Search Console. HTML i JSON export je zahrnují. Export neobsahuje tokeny ani klíče, ale může obsahovat vaše neveřejná data o výkonu a vyhledávacích dotazech.

## Ověření a metodika

Testy ověřují skutečné vykreslení lokálního webu, ovládání rozhraní, ukládání měření, DPAPI a lokální OAuth callback se state/PKCE. Data úspěšných odpovědí Google API jsou při automatických testech řízené testovací vzorky. Přihlášení k živému soukromému účtu musí dokončit uživatel.

- [PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started)
- [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [OAuth pro desktopové aplikace](https://developers.google.com/identity/protocols/oauth2/native-app)
- [JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
