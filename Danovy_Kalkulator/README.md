# TaxCalc 3.0 · Česko / Německo · 2026

Přepracovaná desktopová kalkulačka čisté zaměstnanecké mzdy v Pythonu a PySide6.

## Spuštění ve Windows

Nainstalovaný Python 3.10 nebo novější, 64bit. Otevřete **Spustit.cmd**. Při prvním spuštění vytvoří lokální `.venv` a nainstaluje PySide6; potřebuje internet. Další výpočty jsou offline. Alternativně v adresáři projektu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Ponechte soubory projektu pohromadě. Samotný `app.py` už nestačí: výpočetní jádro, PAP a ukládání jsou oddělené moduly.

## Použití

1. Vyberte zemi a zadejte měsíční hrubou mzdu.
2. Nastavte uplatňované slevy a pojistné údaje. Výsledek se přepočítává průběžně.
3. „Porovnat scénář“ uloží aktuální netto v paměti. Po změně mzdy uvidíte rozdíl ve stejné měně.
4. „Uložit výsledek“ exportuje JSON (znovu načitatelný scénář) nebo CSV (přehled pro tabulkový editor). Načtené výsledky se vždy přepočítají ze vstupů.
5. „Podrobný výpočet“ ukáže mezikroky a základní odvody zaměstnavatele; „Metodika a zdroje“ otevře audit přímo v aplikaci.

České a německé vstupy zůstávají při přepínání zemí oddělené. Program automaticky neukládá osobní údaje; soubory vytváří pouze na vyžádání. Exporty verze 2.2 nelze bez převodu načíst.

## Rozsah

Rok **2026**, běžný pracovní poměr za celý měsíc, jediný zaměstnavatel. Německé netto pouze pro standardní zákonné pojištění a mzdy nad 2 000 €. Třídy I–V, faktor IV, Sasko, děti a standardní církevní daň. Nepodporované případy a přesný rozsah ověření jsou v [AUDIT.md](AUDIT.md). Volba země sama neřeší přeshraniční daňovou povinnost.

Opakovaná kontrola opravila bavorské zaokrouhlení církevní daně, doplnila komorové příspěvky v Brémách a Sársku a sjednotila validaci českého kumulovaného základu. Prošlo 40 testů včetně UI a čerstvé porovnání 504 daňových výstupů s BMF. Církevní daň mimo Bavorsko a centové rozdělení dobrovolné GKV zůstávají orientační; přesné meze jsou uvedeny v auditu a u výsledku.

Původní moduly OSVČ, DPH a MwSt byly z mzdové aplikace odstraněny. Jejich původní výpočty nejsou považovány za ověřené.

## Ověření a vývoj

```powershell
python -m unittest discover -s tests -v
```

Výpočetní a datové testy potřebují jen standardní knihovnu; pro UI testy nainstalujte PySide6. UI testy bez něj vypíšou „skipped“, nikoli úspěšné ověření rozhraní. Referenční odpovědi BMF jsou přibalené a testy fungují bez internetu.

- `payroll.py`: validace, CZ výpočet a DE pojistné, rozhraní pro PAP.
- `pap2026.py`: generovaný oficiální postup BMF; neprovádět ruční úpravy.
- `decimal_math.py`: desetinná aritmetika kompatibilní s použitými operacemi BigDecimal.
- `storage.py`: validovaný import, JSON/CSV export.
- `tools/generate_pap.py`: obnoví generovaný Python ze zachovaného XML.
- `tools/fetch_bmf_cases.cjs`: výslovné obnovení syntetických referenčních případů proti testovací službě BMF (Node.js 18+, internet; nikdy uživatelské mzdy).
- `tests/`: regresní testy výpočtů, ukládání i ovládání.

Výchozí příklady: ČR 50 000 Kč hrubého, podepsané prohlášení, bez dětí → **39 270 Kč čistého**. DE 4 000 €, třída I, bezdětný od 23 let, Berlín, Zusatzbeitrag 2,9 %, bez církevní daně → **2 605,50 € čistého**.

## Původ a závislosti

PAP XML pochází od Bundesministerium der Finanzen, zdroj a kontrolní součet jsou v hlavičce `pap2026.py`. Přepis ani aplikace nejsou oficiálním produktem BMF. PySide6/Qt je samostatná závislost pod licencemi dodavatele; tento zdrojový balík její binární soubory neobsahuje. `pyinstaller` není nutný ke spuštění a byl z běžných závislostí odstraněn.
