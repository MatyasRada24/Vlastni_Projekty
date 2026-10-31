# Lovec nabídek

Lokální aplikace v češtině pro hledání produktů na Bazoši, Aukru a eBay. Vybereš kategorii (notebooky, stolní PC, komponenty, telefony), případně model, například **Legion 5** nebo **RTX 4080**, nastavíš filtry a agent projde zvolený počet stránek. Zobrazuje skutečně načtené nabídky, odkazy, důvody textové shody a stav každého zdroje. Žádná demonstrační data se nevydávají za živé výsledky.

## Spuštění ve Windows

Vyžaduje Node.js 22.9+ (ověřeno na Node.js 24).

```powershell
npm.cmd install
Copy-Item .env.example .env
npm.cmd start
```

Otevři **http://127.0.0.1:3210**. Bez klíčů fungují Bazoš a Aukro. Server je přístupný pouze na tomto počítači. Pro rychlé spuštění po instalaci lze použít `spustit.cmd`.

### Kategorie, model a filtry

Hledání je vždy kategorie a nepovinný model. Bez modelu se projde celá kategorie; s modelem musí inzerát obsahovat každou jeho část („RTX 4080“ odpovídá i „RTX4080 SUPER“, ne „RTX 4070 Ti, vyměním za 4080“). Model se zároveň hledá textem na Aukru a eBay; Bazoš vyhledávání zakazuje, takže prochází kategorii (u telefonů sekci značky). Stav (na opravu / jakýkoliv), cena a parametry kategorie se nastavují jen ve filtrech, nic se nevyvozuje z volného textu.

### eBay

Používá [oficiální Browse API](https://developer.ebay.com/api-docs/buy/static/api-browse.html), marketplace `EBAY_US`, kategorii a anglický dotaz. Pro poškozené zboží používá `conditionIds:{7000}`. Aukce zobrazuje jako aktuální příhoz; u nabídky s možností Buy It Now používá pevnou cenu.

Potřebuje produkční `EBAY_CLIENT_ID` a `EBAY_CLIENT_SECRET` s přístupem k Browse API. Server získá application token přes [OAuth client credentials](https://developer.ebay.com/develop/guides/sell/authorization) a drží jej v paměti do expirace. Alternativou je dočasný `EBAY_ACCESS_TOKEN`. Pouhé vyplnění klíčů nepotvrzuje oprávnění účtu: přístup se ověří při hledání. Bez klíčů je zdroj označen „nenakonfigurován“, nikoli jako zdroj bez nabídek. Scraping webového eBay se nepoužívá.

## Jak probíhá hledání

1. **Plán**: zvolená kategorie, model a filtry. V plánu je vidět každá skupina výrazů (OR uvnitř skupiny, AND mezi skupinami).
2. **Sběr**: 1–100 stránek na web, výchozí rozsah 20. Bazoš má obvykle 20 položek na stránku; eBay se dotazuje po 50. Počet položek Aukra se řídí stránkou webu. Zdrojové nabídky se deduplikují podle ID. Při přesně opakované sadě ID se daný průchod zastaví; pouhý překryv s dřívějšími stránkami další procházení nezastavuje. Vyšší limity prodlužují běh, nikoli rychlost požadavků.
3. **Popisy**: nastavitelných 0–500 detailů z každého českého webu (výchozí hodnota 60). Agent dává přednost nabídkám, u kterých ve výpisu chybí závada nebo požadovaná vlastnost; finální filtry uplatní po načtení detailu. Nabídky mimo cenu či lokalitu ani zjevné příslušenství zbytečně nedočítá. Neprohlédnuté a chybějící popisy jsou označené. eBay v této verzi používá jen souhrn dostupný přes API.
4. **Filtry**: cena zboží bez dopravy, poškození nebo netestovaný stav, povinné/vyloučené výrazy, text lokality, aukce. Text se porovnává bez diakritiky; zápisy RTX3060, RTX-3060 a RTX 3060 jsou ekvivalentní. Slovník zahrnuje další řady notebooků. Krátké názvy jako ROG se hledají po slovech, aby neodpovídaly třeba slovu program. Lokalita je podřetězec, nikoli okruh v km. Neznámá cena je standardně vyloučena; lze ji výslovně povolit i při nastaveném rozpočtu. Neznámý typ prodeje se při zákazu aukcí vyloučí.
5. **Výsledky**: přibývají už při načítání stránek a popisů. Při zastavení zůstávají získané výsledky. Rozhraní vykresluje nabídky po 100 s tlačítkem pro další; CSV zahrnuje celý aktuálně filtrovaný výsledek. Skóre vyjadřuje pouze textovou shodu, ne výhodnost nákupu. Doprava, příhoz, ruční kurz a neověřený stav mají vlastní upozornění. Oblíbené nabídky, uložené filtry a CSV jsou dostupné v rozhraní.

### Zdroje a omezení pokrytí

- **Bazoš**: prochází veřejné kategorie, nikoli adresy hledání zakázané v [robots.txt](https://pc.bazos.cz/robots.txt). Kategorie notebooky, stolní PC, komponenty (RAM, CPU, GPU, SSD, zdroje, základní desky) a telefony jsou mapované přímo; telefony podle zvolené nebo zadané značky. Nabídky filtruje lokálně. TOPované inzeráty ovlivňují pokrytí prvních stránek; aplikace neslibuje kompletní ani chronologický přehled trhu.
- **Aukro**: prochází kategorii zvoleného zboží; model nebo značku v ní hledá textem. Čte data hlavního výpisu vložená v HTML, nikoli doporučovací karusely. Při změně struktury má zálohu v JSON-LD, kde typ prodeje zůstává „neověřen“. [robots.txt](https://aukro.cz/robots.txt) se ověřuje za běhu.
- **eBay**: výše uvedené produkční API, omezené získaným oprávněním. Při rozsahu alespoň 4 stránek střídá cílené hledání s širším průchodem kategorie (každá čtvrtá stránka, případně po vyčerpání cíleného dotazu). Oba průchody sdílejí celkový limit, mají vlastní stránkování a společnou deduplikaci. Širší průchod nevyžaduje klíčová slova ani štítek poškození; rozhodují místní filtry. EXTENDED vrací dostupný krátký popis a město. Dostupnost dopravy do ČR, clo a konečná cena vyžadují ověření na eBay. Zvolená lokalita se porovnává pouze s vráceným textem lokality.
- Automatický přístup k HTML má odstup alespoň 1,2 s mezi požadavky na stejný web, mezipaměť 5 minut a kontrolu robots.txt. Na HTTP 403/429 nebo CAPTCHA se zastaví; ochrany neobchází.
- Neúspěšný zdroj, změna parseru a skutečně prázdný výsledek jsou odlišné stavy. Při částečné chybě se zachovají již načtené nabídky.
- Pravidla poškození jsou heuristická a mohou mít falešné shody nebo něco přehlédnout. Výraz „netestovaný“ je kandidát k prověření. Popis závady není diagnóza. Fotografie se neanalyzují AI.
- Kurzy v nastavení jsou **ruční orientační hodnoty**, nikoli živý kurzovní lístek. Cenový filtr nepřičítá dopravu, clo, daně ani poplatky. Přepočet měn jiných než CZK/USD/EUR/GBP není podporován.
- Vyhledávání se spouští ručně. Žádné automatické nákupy, kontaktování prodejců ani plánované prohledávání na pozadí.

## Parametry notebooku a hrubý rozdíl

Z názvu a dostupného popisu se lokálně rozpoznávají značka, řada/model, vybraná výrobní označení, CPU, GPU, RAM a disk. Přednost mají pojmenovaná pole („Procesor:“, „RAM:“, parametry Aukra), potom název inzerátu a nakonec volný text popisu; rozpor uvnitř rozhodujícího zdroje nechá údaj neznámý. Nabídky rozšíření („lze rozšířit na 32 GB“), paměť grafické karty a přání při výměně se ignorují. U Aukra se čte celý popis i tabulka parametrů z detailu; intervalové parametry („16 – 31 GB“) se za přesnou hodnotu nepovažují. Rozpoznávání je konzervativní a nepokrývá všechna označení. Neznámé či rozporné údaje zůstávají prázdné; VRAM se nepovažuje za RAM. Více různých disků se nesčítá bez jistoty konfigurace. Kapacita 1 TB se pro filtr převádí na 1000 GB. Model, CPU a GPU lze filtrovat textem, RAM a disk minimální kapacitou. Chybějící vybraný parametr nabídku vyloučí, pokud výslovně nezapneš zahrnutí neznámých parametrů. Známá neshoda neprojde ani pak. Nedostatečné výpisy se mohou doplnit z detailů v nastaveném limitu.

Po sběru nabídek se pro kategorii notebooků automaticky ověřují nové kusy na **Mironetu**. Vyhledává se výrobní označení, případně značka a model; z jednoho hledání se prověří nejvýše 8 produktových stránek. Vyhledání ceny lze vypnout a limit odlišných konfigurací nastavit od 1 do 200 (výchozí 30). Stejné konfigurace sdílejí dotaz v rámci běhu. Používají se stejné limity rychlosti, robots.txt, kontrola přesměrování a pětiminutová mezipaměť jako u ostatních HTML zdrojů. Vyhledávaný model se odesílá Mironetu; neodesílají se kontakty prodávajících.

Cena se přijme pouze u produktu označeného jako nový a dostupný, s cenou CZK z jeho vlastních strukturovaných dat. Vyžaduje se stejné výrobní označení bez známých rozporů, nebo shodná značka, model, CPU, GPU, RAM, kapacita a typ disku. Druhá varianta má slabší jistotu: displej, OS, klávesnice a ostatní výbava mohou být odlišné. Pokud u inzerátu chybí RAM nebo disk, použije se jako třetí, „orientační“ úroveň shoda modelu, CPU a GPU bez známého rozporu; karta ji tak označí a ukáže rozpětí nalezených cen. Odkazy z vyhledávání obchodu se řadí podle shody názvu s modelem, CPU a GPU. Ověřovací stránka proti robotům (např. ALTCHA) se hlásí jako odmítnutý přístup, ne jako nenalezená cena. Na kartě je zdrojový odkaz, typ shody a čas ověření. Jde o dostupnou cenu u jednoho prodejce, nikoli kompletní průzkum ani původní zaváděcí cenu. Starší model nemusí být jako nový v prodeji; v takovém případě se zisk nehádá. Chyba zdroje a dosažení limitu jsou viditelně odlišeny od nedohledané shody.

- **Odhad prodejní ceny = cena nového × 0,75.**
- **Hrubý rozdíl = cena nového × 0,75 − nákupní cena rozbitého kusu.**
- **Maximální nákup = cena nového × 0,75 − požadovaný hrubý rozdíl.**

Například nový kus za 20 000 Kč a rozbitý za 4 000 Kč dávají hrubý rozdíl 11 000 Kč. Při požadovaném rozdílu 3 000 Kč je maximální nákup 12 000 Kč. Výpočet zachovává záporné výsledky a neznámou nákupní cenu. **Oprava, práce, doprava, clo a poplatky se podle zadaného vzorce neodečítají. Nejde o čistý zisk ani garantovanou prodejní cenu.** U aukce se používá aktuální příhoz. Požadovaný rozdíl mění doporučené maximum nákupu, neskrývá nabídky. Výsledky lze podle hrubého rozdílu seřadit a parametry i cenové podklady jsou součástí CSV.

## Čistý odhad, závady a hlídání

- **Závady a rizika** (`src/defects.js`): z textu inzerátu se určí typ závady (nezapne se, displej, BIOS, polití, deska, grafika, nabíjení, klávesnice, panty, baterie, netestováno) a rizika. Rizika „zámek BIOSu“, „iCloud“ a „blokace“ znamenají, že kus může být jen na díly; „chybí díly“, „bez nabíječky“ a „po pokusu o opravu“ jsou varování. Věty jako „bez hesla v BIOSu“ nebo „odhlášený z iCloudu“ se berou jako vyloučení rizika. Výsledky jde filtrovat podle typu závady a zamčené kusy skrýt.
- **Čistý odhad** = odhad prodeje − nákup − doprava (u inzerátu bez údaje odhad) − oprava podle typu závady − poplatky − dovozní náklady. Více závad se sčítá. Částky jsou odhad, ne diagnóza, a upravíš je v dialogu „Připojení a náklady“ (ukládají se v prohlížeči).
- **eBay mimo EU**: notebooky mají v EU nulové clo, přičítá se ale DPH 21 % z ceny a dopravy a poplatek dopravce za proclení. Měny se přepočítávají denním kurzem ČNB (`/api/rates`, mezipaměť 6 h); v nastavení lze přepnout na vlastní kurzy.
- **Bazarová prodejní cena**: z inzerátů prohlédnutých v témže hledání (funkční, pevná cena v Kč) se počítá medián stejného modelu, CPU a GPU, potom stejného CPU a GPU, u Apple modelu a čipu. Odhad prodeje je 90 % mediánu. Úroveň „jen stejná dedikovaná grafika“ je hrubá a použije se jen tam, kde chybí cena nového.
- **Paměť mezi běhy** (`data/store.json`, mimo git): kdy byl inzerát poprvé viděn a historie jeho ceny. Karty ukazují „Nové“, „Zlevněno o…“, filtr „Jen nové a zlevněné“. Nabídky lze skrýt; skryté se ukládají tamtéž.
- **MacBooky**: čip Apple (M1–M5) slouží zároveň jako grafika. Cena nového se bere z oficiálního českého Apple Store (nejlevnější konfigurace stejné velikosti a čipu, označeno jako orientační). Apple prodává jen aktuální generaci; starší čipy nový nekoupíš a hodnotí se bazarovou cenou podle modelu a čipu. K24 MacBooky neprodává, nabízí jen příslušenství, které se jako cena notebooku nepřijímá.
- **Vlastní cena nového** může platit pro všechny nabídky se stejným modelem, CPU a GPU.
- **Kraj**: filtr podle kraje určeného z PSČ (podle poštovních okrsků, přibližně) nebo názvu krajského města.
- **Hlídání**: uložené hledání se spouští v intervalu 30 min až 24 h, jen když běží server a souběžně neběží ruční hledání. Upozorní na nové nebo zlevněné kusy nad zvolený hrubý rozdíl; upozornění prohlížeče se zobrazí, dokud je stránka otevřená.

## Uložení a soukromí

Posledních 20 běhů je v paměti procesu; restart je odstraní. Historie nabídek, skryté nabídky a nastavení hlídání jsou v `data/store.json`; smazáním souboru se vynulují. Oblíbené nabídky, poslední filtry a až 20 uložených hledání jsou v `localStorage` aktuálního prohlížeče. Nejde o trvale synchronizovanou databázi. Uložená nabídka může později zmizet nebo změnit cenu. Klíče jsou jen v `.env`, který je v `.gitignore`. Fotografie se načítají přímo z původních zdrojů.

## Ověření

```powershell
npm.cmd test
npm.cmd run test:live
```

Jednotkové a integrační testy ověřují parsování, měny, aukce, filtry, plán z kategorie a modelu, deduplikaci, chyby zdrojů, zrušení a bezpečnost lokálního HTTP serveru. `test:live` provede jeden skutečný výpis Bazoše a Aukra; nepoužívá klíče ani placená API. Živé eBay volání je možné ověřit až s vlastními klíči.

### Soubory

- `server.js`: lokální HTTP API, běhy, zastavení a statická aplikace.
- `src/planner.js`: plán hledání z kategorie, modelu a filtrů.
- `src/sources.js`, `src/http.js`, `src/parsers.js`: adaptéry, řízené stahování a parsování.
- `src/matching.js`: filtry, důvody shody, upozornění.
- `public/`: samostatné webové rozhraní bez sestavovacího kroku.

Pokud web změní HTML nebo pravidla přístupu, upravuje se jeho adaptér a testy. Aplikace při nerozpoznané struktuře nevydává chybu parseru za nulový počet nabídek.
