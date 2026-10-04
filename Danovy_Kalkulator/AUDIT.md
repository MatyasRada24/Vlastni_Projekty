# TaxCalc 3 — metodika a kontrola pro rok 2026

Ověřeno k 2. 10. 2026. Jde o technickou kontrolu implementace proti uvedeným oficiálním pravidlům a referenčním výpočtům, nikoli o osvědčení úřadu či individuální daňové stanovisko.

## Výsledek opakované kontroly 2. 10. 2026

České parametry a měsíční postup odpovídají níže uvedeným pravidlům Finanční správy, ČSSZ a VZP pro podporovaný rozsah. Německé daňové jádro souhlasí s čerstvými odpověďmi BMF: **42 scénářů × 12 výstupů = 504 shod, žádný rozdíl**. Stažené XML se od přibaleného liší pouze konci řádků; opětovné generování `pap2026.py` vytvořilo totožný soubor. Protokol je v `work/bmf-live-verification.json`, opakování umožňuje `node work/verify_bmf.cjs` (internet, pouze syntetická data).

Kontrola našla a opravila následující nedostatky:

- **Chybějící příspěvky zaměstnaneckým komorám:** Bremen 0,11 % hrubé mzdy a Saarland 0,15 % nejvýše z 8 450 €. U mzdy 4 000 € bez církevní daně a při ostatních výchozích vstupech je po opravě netto 2 601,10 € v Brémách a 2 599,50 € v Sársku. Příspěvek se zobrazuje zvlášť a zahrnuje se i do ročního modelu, grafu a exportu.
- **Bavorské zaokrouhlování církevní daně:** nově na centy dolů podle § 9 odst. 2 AVKirchStG. Například z Maßstabsteuer 293,08 € je daň 23,44 €, dříve chybně 23,45 €.
- **Nesoulad české validace:** předchozí základ sociálního pojištění nad 10 milionů Kč byl platný pro měsíční výpočet, ale roční model jej odmítl a rozhraní skrylo i měsíční výsledek. Obě části nyní přijímají stejný rozsah do 120 milionů Kč; při nenulovém předchozím základu se roční model nadále nezobrazuje.
- **Věkové popisky PV:** příplatek za bezdětnost začíná až měsícem po 23. narozeninách; dítě se pro slevu započítává ještě po celý měsíc svých 25. narozenin. Rozhraní nyní tyto podmínky uvádí přímo.

Po změnách prošlo **40 testů bez vynechání**, včetně testů PySide6, importu/exportu, referenčních výpočtů a převodu vstupů aplikace do PAP. Příkaz: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.

**Co zůstává orientační:** centové zaokrouhlení církevní daně mimo Bavorsko nebylo pro každou zemi samostatně doloženo; používá se half-up a aplikace to při zapnuté církevní dani uvádí. U dobrovolné GKV může samostatně předepsané pojistné a příspěvek zaměstnavatele dát jiné centové zaokrouhlení než model zaměstnaneckých podílů. Ověření BMF se týká daně a jejích základů, nikoli celého netto. Z toho důvodu nelze tvrdit, že každá nabízená německá kombinace odpovídá výplatní pásce na cent.

## Co aplikace počítá

Pravidelnou **měsíční výplatu zaměstnance** za celý měsíc. Hrubá mzda je současně zdanitelný příjem a základ pojistného; bez nepeněžních benefitů, cestovních náhrad a dalších příjmů s odlišným daňovým režimem. Země se vybírá podle použitého mzdového režimu. Aplikace nerozhoduje, ve které zemi má člověk platit daně.

Česká varianta předpokládá běžný pracovní poměr s příjmem alespoň 4 500 Kč, účast na českém sociálním a zdravotním pojištění a jediného zaměstnavatele. Německá varianta předpokládá běžného zaměstnance bez Altersentlastungsbetrag (k 1. 1. 2026 ještě nedovršených 64 let), zákonné zdravotní pojištění s nárokem na Krankengeld, RV/AV a jedinou práci s pravidelnou mzdou **nad 2 000 €**. U zdravotního pojištění nad hranicí povinné účasti předpokládá pokračování v zákonné GKV a zobrazuje ekonomické netto po obou stranách příspěvku, bez dalších pojištěných příjmů.

Nepodporuje DPP/DPČ, zaměstnání malého rozsahu, Mini/Midijob, Werkstudent, učňovské nebo krátkodobé zvláštní režimy, souběh zaměstnání, německou třídu VI, soukromé pojištění, důchodce, zvláštní profesní sazby, neúplný měsíc, nemoc, jednorázové odměny a 13. plat, daňové vyrovnání, exekuce a jiné srážky kromě níže uvedených komorových příspěvků. Ani konečnou povinnost přeshraničního pracovníka, smlouvu o zamezení dvojímu zdanění, rezidentství, zahraniční home office či příslušnost k pojištění podle A1. U komorových příspěvků nepodporuje výjimky z členství (např. statutární orgány, některé vedoucí zaměstnance v Sársku a další případy dle předpisů komor).

**Roční model** je součet 12 měsíčních výplat od ledna při neměnné mzdě a podmínkách. Český model postupně uplatní roční strop sociálního pojištění; při zadaném předchozím základu se nezobrazuje. Není to roční zúčtování daně. Nezahrnuje odpočty darů, úroků, penzijních produktů ani roční slevu na manžela/manželku. Kindergeld se do německé mzdy nepřičítá.

## Česko

### Záloha na daň

Základ zálohy zaokrouhlujeme nahoru na stokoruny. Sazba 15 % platí do 146 901 Kč měsíčně, 23 % nad tuto hranici; součet daně zaokrouhlujeme nahoru na celé koruny. Podepsané prohlášení umožňuje základní slevu 2 570 Kč a případné další nároky. Invalidita I/II: 210 Kč; III: 420 Kč; průkaz ZTP/P poplatníka: 1 345 Kč měsíčně. Nerezidentovi se měsíčně uplatní jen základní sleva.

Děti: 1 267 / 1 860 / 2 320 Kč; poslední částka platí i na každé další dítě. Pořadí je za domácnost, nikoli pořadí v této aplikaci. ZTP/P se zadává jednotlivě u dítěte a zdvojnásobí pouze jeho zvýhodnění. Nejprve se uplatní osobní slevy, potom zvýhodnění proti zbývající dani. Nevyužitá osobní sleva bonus nevytváří. Bonus na děti se vyplatí při příjmu alespoň 11 200 Kč a bonusu alespoň 50 Kč.

Pravidla a dva převzaté referenční příklady zálohy (45 810 Kč → 6 885 Kč; 165 615 Kč → 26 359 Kč, před slevami): [Finanční správa — zaměstnanci, obecné informace, § 38h, § 35ba–35d zákona č. 586/1992 Sb.](https://financnisprava.gov.cz/cs/dane/dane/dan-z-prijmu/zamestnanci-zamestnavatele/obecne-informace).

Sleva na studenta se neuplatňuje: [Finanční správa — zrušení od roku 2024](https://financnisprava.gov.cz/cs/financni-sprava/media-a-verejnost/tiskove-zpravy-gfr/tiskove-zpravy-2025/vyplnujete-danove-priznani-pozor-zmeny-od-2024).

### Pojištění

Zaměstnanec: sociální pojištění **7,1 %**, částka nahoru na celé koruny. Zadaný kumulovaný základ u stejného zaměstnavatele omezuje zbývající část ročního stropu **2 350 416 Kč**. Základní sazba zaměstnavatele je 24,8 %. Jeho náklad je v kalkulačce modelován pro jednoho zaměstnance; skutečný souhrnný odvod zaměstnavatele může mít jiné korunové zaokrouhlení.

Zdroje: [ČSSZ — sazby pojistného, zákon č. 589/1992 Sb.](https://www.cssz.gov.cz/web/cz/vyse-a-sazba), [ČSSZ — parametry 2026, včetně ročního stropu a zvláštních sazeb](https://www.cssz.gov.cz/-/prehled-nejdulezitejsich-udaju-pro-socialni-zabezpeceni-v-roce-2026).

Zdravotní pojištění: celkem 13,5 % nahoru na koruny; zaměstnanci 4,5 % nahoru, zaměstnavateli zbývající část. Při zapnutém minimu doplatí zaměstnanec rozdíl do celkových **3 024 Kč**. Minimum pro rok 2026 odpovídá mzdě **22 400 Kč**. Při výjimce z minima po celý měsíc se doplatek vypíná; neuvažujeme překážky na straně zaměstnavatele, kdy doplatek nese zaměstnavatel. Zdravotní pojištění nemá maximální základ.

Zdroj: [VZP — vyměřovací základ a výpočet pojistného, zákon č. 592/1992 Sb.](https://www.vzp.cz/platci/informace/zamestnavatel/vymerovaci-zaklad-a-vypocet-pojistneho), [VZP — povinnosti zaměstnavatele a rozdělení pojistného](https://www.vzp.cz/platci/informace/povinnosti-platcu-metodika/2-4-platce-pojistneho-zamestnavatel).

## Německo

### Lohnsteuer a Solidaritätszuschlag

Původní odhad byl nahrazen **oficiálním PAP BMF 2026**. XML je uloženo ve `vendor/Lohnsteuer2026.xml`; deterministický překladač `tools/generate_pap.py` vytváří `pap2026.py`. V hlavičce výsledného modulu je kontrolní SHA-256 zdroje. Datový typ Decimal a adaptér zachovávají operace i směry zaokrouhlování z PAP. Za běhu se XML nevyhodnocuje ani nic nestahuje.

Vstupy zahrnují třídy I–V, faktor třídy IV, měsíční Freibetrag z ELStAM, Kinderfreibetrag, Zusatzbeitrag, rodičovství a saské pojistné. PAP zahrnuje Vorsorgepauschale, tarif 2026 a přechodové pásmo Solidaritního příspěvku. Počet podílů Kinderfreibetrag není totéž co počet dětí pro pojištění péče.

Zdroj: [BMF — XML-Pseudocodes a vysvětlení metodiky](https://www.bmf-steuerrechner.de/interface/pseudocodes.xhtml), [oficiální XML 2026](https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2026.xml.xhtml), [§ 39b EStG](https://www.gesetze-im-internet.de/estg/__39b.html), [§ 4 SolzG](https://www.gesetze-im-internet.de/solzg_1995/__4.html).

**42 syntetických scénářů** bylo porovnáno s [testovací službou BMF](https://www.bmf-steuerrechner.de/interface/einganginterface.xhtml). Porovnávají se všechny vrácené výstupy PAP, nejen Lohnsteuer: 12 výstupů na případ. Uchované odpovědi a vstupy jsou v `tests/bmf_cases.json`. Testují se i třídy VI na úrovni PAP, přestože čistá mzda této třídy není v aplikaci nabízena kvůli souběhu zaměstnání. Služba BMF je využita pouze k testům se smyšlenými daty; běžné výpočty uživatele jsou offline.

### Pojistné a církevní daň

Zaměstnanecké podíly: RV 9,3 %, AV 1,3 %, KV 7,3 % + polovina individuálního Zusatzbeitrag. Průměrný Zusatzbeitrag 2,9 % pro 2026 je pouze výchozí hodnota, kterou je nutné přizpůsobit pojišťovně. Základní a doplňková část KV se počítají a zaokrouhlují samostatně.

PV: 1,8 % (Sasko 2,3 %), pro bezdětného od měsíce následujícího po 23. narozeninách příplatek 0,6 procentního bodu; od druhého do pátého zohledňovaného dítěte sleva po 0,25 bodu. Dítě se započítává do konce měsíce svých 25. narozenin. Rodičovství odstraňuje příplatek i po dosažení 25 let dětí. Výpočet používá jeden výsledný zaměstnanecký podíl PV. [Metodika GKV-Spitzenverband z 31. 3. 2025, oddíl 3.3](https://www.kbs.de/SharedDocs/Downloads/DE/VersicherungsrechtBeitraegeMeldungen/Downloads/Hinweise_Differenzierung_BeitragssaetzePV_Anzahl_Kinder_und_Empfehlungen_Nachweis_Elterneigenschaft.pdf?__blob=publicationFile) připouští i samostatné zaokrouhlení příplatku či slevy; centový rozdíl mezi těmito dvěma postupy tedy sám o sobě není chybou. Věkové hranice vysvětluje také [Deutsche Rentenversicherung — sazby pojistného](https://www.deutsche-rentenversicherung.de/DRV/DE/Experten/Arbeitgeber-und-Steuerberater/summa-summarum/Lexikon/_functions/lexikon?lv2=6a097da3ca84ce5471c172a3).

Stropy měsíčně: RV/AV **8 450 €**, KV/PV **5 812,50 €**. Pojištění se zaokrouhluje na centy metodou half-up.

Zdroje: [BMG — KV a Zusatzbeitrag](https://www.bundesgesundheitsministerium.de/beitraege), [BMG — financování pojištění péče](https://www.bundesgesundheitsministerium.de/themen/pflege/online-ratgeber-pflege/die-pflegeversicherung/finanzierung/), [vláda SRN — stropy 2026](https://www.bundesregierung.de/breg-de/aktuelles/beitragsgemessungsgrenzen-2386514), [BVV — zaokrouhlování a výpočet](https://www.gesetze-im-internet.de/beitrvv/BJNR113800006.html), [TK — samostatný výpočet KV a Zusatzbeitrag](https://www.tk.de/techniker/versicherung/gut-versichert-in-jeder-lebenslage/freiwillige-krankenversicherung-tk/beitragshoehe-arbeitnehmer-2006954).

Církevní daň: standardních 8 % v Bavorsku/Bádensku-Württembersku, 9 % v ostatních zemích z Maßstabsteuer vrácené PAP po zohlednění Kinderfreibetrag. Předpokládá se stejná země pracoviště a mzdové účtárny, běžná církevní příslušnost a plná srážka. Výsledek nezahrnuje církevní specifika, Mindestkirchensteuer, zvláštní Kirchgeld, dělení mezi vyznání manželů a Kappung; u těchto případů nejde o přesný model. Bavorsko: centy dolů podle [§ 9 odst. 2 AVKirchStG](https://www.gesetze-bayern.de/Content/Document/BayAVKirchStG-9). Ostatní země: orientační half-up, bez ověření všech místních pravidel zaokrouhlení.

Zdroje: [BMF — daňové druhy A–Z, Kirchensteuer](https://www.bundesfinanzministerium.de/Content/DE/Downloads/Broschueren_Bestellservice/steuern-von-a-z.pdf?__blob=publicationFile&v=8), [Bavorsko — informace k mzdovému zdanění a 8% sazbě](https://finanzamt.bayern.de/Informationen/Steuerinfos/Haeufig_gestellte_Fragen/Geringfuegige_Beschaeftigung/default.php?c=n&d=x&f=Landshut&t=t), [BMF — vliv Kinderfreibetrag](https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Service/Abgabenrechner/FAQ.html).

### Příspěvky zaměstnaneckým komorám

U běžných zaměstnanců nad 2 000 € aplikace odečítá podle země zaměstnání také povinný komorový příspěvek. Nejde o sociální pojištění ani církevní daň a nezávisí na náboženské příslušnosti. V Brémách činí pro rok 2026 **0,11 %** celé zdanitelné hrubé mzdy bez pojistného stropu; v Sársku **0,15 %** pojistného základu nejvýše **8 450 €**, tedy maximálně **12,67 € měsíčně**. V obou případech se zlomky centu odříznou. Výjimky z členství nejsou modelovány.

Zdroje: [Arbeitnehmerkammer Bremen — Beitragsmerkblatt 2026](https://www.arbeitnehmerkammer.de/fileadmin/Arbeitnehmer/Downloads/Infos_zur_Arbeitnehmerkammer/Beitragsmerkblatt-Arbeitnehmerkammer_2026.pdf), [Arbeitskammer Saarland — sazba, strop a zaokrouhlení pro 2026, str. 1–2](https://www.arbeitskammer.de/fileadmin/user_upload/---------------AK_Download_Datenbank-------------/Ueber_uns/Mitgliedsbeitraege/AK_Mitgliedsbeitrag_2026.pdf).

## Zjištění v původní verzi 2.2

| Oblast | Zjištění | Změna ve verzi 3 |
|---|---|---|
| CZ sociální pojištění | Sazba 6,5 % | 7,1 % a roční strop |
| CZ daň | Jen 15 % z nezaokrouhlené mzdy | Stokoruny, obě pásma, zaokrouhlení zálohy |
| CZ slevy | Automatická základní sleva a zrušená studentská sleva | Prohlášení, rezidentství, platné osobní slevy |
| CZ děti | Nejvýše tři děti; společné ZTP; žádný bonus | Každé dítě zvlášť, pořadí v domácnosti, bonus |
| CZ zdravotní | Bez minima a zaokrouhlení | Minimum, výjimka a korektní součet odvodů |
| DE daň | Přibližná lineární pásma; staré parametry | Oficiální PAP 2026 |
| DE Soli | Okamžitých 5,5 % nad chybnou hranicí | PAP včetně přechodového pásma |
| DE pojištění | Staré stropy, pevné KV/PV | Parametry 2026, pojišťovna, děti a Sasko |
| DE církevní daň | Jednotných 8,5 % z Lohnsteuer | Standardních 8/9 % z Maßstabsteuer |
| Import/export | Nevalidované vstupy a zastaralé výsledky | Validace, verze souboru, přepočet a ochrana před exportem neplatného stavu |
| Ostatní moduly | OSVČ mělo chybné základy a limity; DPH nepatří do výplaty | OSVČ/DPH/MwSt nejsou součástí této mzdové verze |

Původní moduly OSVČ a DPH nejsou po tomto přepracování právně validované. Původní soubory jsou zachovány v záloze; nepoužívejte je jako ověřenou daňovou kalkulačku.

## Meze ověření

Automatické testy ověřují oficiální české příklady, hranice pásem a bonusu, stropy a zaokrouhlování, rodinné situace, BMF referenční výsledky, import/export a rozhraní. BMF potvrzuje referenční **daňové výstupy**, nikoli české nebo německé netto jako celek. Sociální a zdravotní odvody mají samostatné testy podle výše uvedených pravidel. Nejde o test všech možných právních situací a všech mzdových programů.

Zobrazené náklady zaměstnavatele obsahují jen hrubou mzdu a základní pojistné. Nejsou úplným personálním nákladem: chybí úrazové pojištění, německé Umlagen a Insolvenzgeldumlage, případné profesní a zaměstnavatelské příspěvky či slevy. U neobvyklé situace nebo přeshraničních příjmů je třeba výpočet posoudit s mzdovou účtárnou.
