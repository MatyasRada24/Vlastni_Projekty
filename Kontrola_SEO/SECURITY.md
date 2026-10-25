# Bezpečnost a vydání 1.0

## Hranice ochrany

Google tokeny a API klíč jsou uložené přes Windows DPAPI pro aktuálního uživatele. To nechrání před malwarem běžícím pod stejným účtem. Historie auditů a exporty nejsou šifrované; mohou obsahovat URL, parametry adres, místní cesty a neveřejná data Search Console. Před sdílením je zkontrolujte.

OAuth používá PKCE, náhodný state a callback pouze na loopbacku. Aplikace požaduje Search Console pouze ke čtení. Google dostává URL při měření PageSpeed a požadavky Search Console při jejich použití. Google připojení si každý uživatel nastavuje vlastní; osobní OAuth JSON ani API klíč nejsou součástí vydání.

Crawler ověřuje všechny DNS adresy cíle a připojuje se k ověřené IP bez druhého DNS překladu. TLS ověřuje certifikát původního hostname. Veřejné domény nesmějí mířit na neveřejné IP. Ruční zadání místní IP nebo localhost je výslovným výběrem místního cíle; dovoluje audit pouze stejného hostname. Firemní proxy a intranetové DNS názvy tento transport zatím nepodporuje.

JavaScript běží v Chromium sandboxu a novém profilu bez osobních cookies. Vedlejší HTTP požadavky procházejí kontrolovaným transportem bez povolení místní sítě, cookies či přihlášení. Povolené jsou jen GET požadavky; WebSockety a service workers jsou blokované. WebRTC má zakázaný přímý UDP provoz. Limity: 100 vedlejších požadavků, 5 MB na odpověď, přibližně 50 MB celkem a časové omezení. Nejde o plnou síťovou izolaci operačního systému. Pro vysoce nedůvěryhodné weby použijte virtuální stroj. Aktualizujte Edge/Chrome i Windows. Weby vyžadující POST, lokální zdroje nebo přihlášení mohou mít neúplné vykreslení, které aplikace označí jako neověřené.

## Publikování

Nahrávejte obsah zdrojového ZIP, nikoli celou pracovní složku. Spusťte `python -m tools.prepare_release` po sestavení. Skript vybírá jen schválené zdrojové soubory a dokumentaci, hledá některé běžné formáty klíčů a vytvoří kontrolní součty. Nenahrazuje kompletní secret scanner. Buildy, OAuth soubory, tokeny, databáze a exporty jsou vyloučené. `.gitignore` neodstraňuje soubory z existující historie Gitu. Zde zatím není inicializovaný repozitář.

Před prvním commitem zkontrolujte `git diff --cached` a seznam připravených souborů. Pokud už byly skutečné tokeny nebo API klíče zveřejněny, odvolejte je u poskytovatele; pouhé smazání souboru nestačí. Před dalším vydáním opakujte audit závislostí a testy. EXE není digitálně podepsané; SHA256 potvrzuje shodu souboru, nikoli identitu autora. Před zveřejněním zvolte licenci projektu.

Bezpečnostní chyby hlaste soukromě přes GitHub Private vulnerability reporting, pokud jej vlastník repozitáře zapne. Do veřejných issues nevkládejte klíče, tokeny ani soukromé reporty.

## Ověření vydání 25. 10. 2026

59 jednotkových testů prošlo. Audit pip-audit nad konkrétními verzemi nenašel známé zranitelnosti: playwright 1.64.0, pyee 14.0.0, greenlet 3.5.6, pyinstaller 6.22.3, pyinstaller-hooks-contrib 2026.8, altgraph 0.17.5, packaging 26.3, pefile 2024.8.26 a pywin32-ctypes 0.2.3. Toto tvrzení platí k datu kontroly a nevztahuje se na Windows, Python ani samostatně instalovaný prohlížeč. Nejde o penetrační test nebo záruku absence chyb.
