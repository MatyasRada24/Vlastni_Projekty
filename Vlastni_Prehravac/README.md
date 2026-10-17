# Pulse Player

Desktopový přehrávač hudby a videa pro Windows. Nové tmavé rozhraní se zeleným akcentem, knihovna vlevo od přehrávače a samostatné lokální playlisty.

## Spuštění

Otevřete **`dist/Pulse Music Player.exe`** nebo `start.bat`. Nové EXE obsahuje Python, Qt i FFmpeg, takže nepotřebuje instalaci Pythonu ani VLC. Původní aplikace je zálohovaná v `backups/`.

## Ovládání

- **Přidat soubory** v záhlaví otevře výběr médií. Přepínače **Vše / Hudba / Video** a hledání filtrují otevřenou knihovnu nebo playlist.
- Přetáhněte soubory nebo celé složky do okna. Přidají se do právě otevřené knihovny či playlistu. Složky se procházejí včetně podsložek, duplicity se nepřidávají.
- Playlist založíte tlačítkem **+** vedle nadpisu **Moje playlisty**. Média lze přetáhnout přímo na jeho jméno, nebo označit v tabulce a zvolit **Do playlistu**. Více položek vyberete pomocí Ctrl / Shift.
- Pořadí v playlistu měníte přetažením řádků, případně přes pravé tlačítko → Posunout nahoru / dolů. Pravé tlačítko na playlist nabídne přejmenování a smazání.
- Dvojklik přehraje skladbu nebo video. **Přehrát vše** používá právě zobrazené výsledky. Přehrávací fronta zůstává stejná i při procházení jiné knihovny či playlistu; další dvojklik nebo Přehrát vše vytvoří novou frontu.
- Chybějící soubory zůstávají v playlistech. Přes pravé tlačítko → **Najít soubor** lze opravit jejich umístění.
- Odebrání z knihovny odstraní také odkazy z playlistů. Odebrání z playlistu ponechá soubor v knihovně. Žádná z těchto akcí nemaže skutečné soubory z disku.
- Zvukový výstup vyberete v pravém panelu. Video lze otevřít přes celou obrazovku; Esc zavře fullscreen. Kolečko myši nad videem mění přiblížení.
- Obaly se načítají z metadat souborů. V užším okně se sloupec kvality schová; parametry přehrávané nahrávky zůstávají v pravém panelu. Informace o zvuku a kodecích otevře ikona **ⓘ** u zvukového výstupu.

| Klávesa | Akce |
| --- | --- |
| Mezerník | Přehrát / pozastavit |
| ← / → | Posun o 5 sekund, pokud šipky nepoužívá aktivní ovládací prvek |
| Ctrl+← / Ctrl+→ | Předchozí / následující |
| M | Ztlumit / obnovit původní hlasitost |
| F | Video přes celou obrazovku |
| Ctrl+O | Přidat soubory |
| Ctrl+Shift+O | Přidat složku |
| Ctrl+N | Nový playlist |
| Ctrl+F | Hledání |

## Lokální data

Knihovna, playlisty, jejich pořadí, hlasitost a výstupní zařízení se ukládají automaticky do **`%LOCALAPPDATA%/Pulse Player/library.json`**. Ukládání používá atomickou výměnu souboru. Poškozená knihovna se nepřepisuje prázdnými daty; aplikace oznámí problém.

Při prvním spuštění se převezmou stará data z `~/.pulse_settings.json` a `~/Documents/Pulse_Playlists/`. Originály zůstanou zachovány. Playlisty obsahují cesty k souborům, nikoliv kopie médií. Přesunutí či odpojení disku proto může vyžadovat opětovné připojení nebo nalezení souboru.

## Kodeky a kvalita zvuku

Přehrávání používá Qt a přibalený FFmpeg 7.1 s dekodérem dav1d pro AV1. Import přijímá běžné audio/video kontejnery včetně MP3, MP4, M4A, FLAC, WAV, OGG, Opus, MKV, WebM, MOV a AVI. Přípona sama nezaručuje podporu všech profilů kodeku uvnitř souboru. Chráněné DRM soubory nejsou podporovány.

Video se standardně dekóduje softwarově: Qt 6.11 na některých GPU neobnoví přehrávání po selhání hardwarového AV1. Soubory se nepřevádějí. U vysokého rozlišení může být vyšší zatížení CPU. Verze, kontrolní součty a licence knihoven jsou v `vendor/ffmpeg/`; EXE obsahuje jejich kopii.

Na tomto počítači bylo dekódování ověřeno skutečnými audio buffery / video snímky pro:

- MP3, AAC, ALAC, FLAC, Opus, Vorbis, AC3 a PCM WAV **24 bit / 96 kHz**;
- H.264 v MP4, HEVC v MKV a VP9 ve WebM.
- AV1 v MP4 (8 i 10 bit), MKV a WebM, včetně posouvání, pauzy a celé obrazovky.

Kontrola po opravě AV1: 51 z 52 kombinací v `tests/format_matrix.py` prošlo. APE zůstává omezením: referenční minutový soubor se v Qt přehrává příliš pomalu. Podrobnosti jsou v `qa/format-report.md`.

Přehrávač nepřekódovává soubory, nepoužívá automatické efekty ani digitální zesílení nad 100 %. Zobrazuje dostupné parametry zdroje a umožňuje volbu zvukového zařízení. Konečný výstup ovlivňuje směšovač Windows a hardware. Nejde o exkluzivní WASAPI ani garantovaný bit-perfect režim a aplikace neobnovuje informace ztracené kompresí. Parametry zařízení v dialogu jsou jeho preferovaný formát, nikoliv měření aktuálního výstupu.

## Vývoj a sestavení

Ověřeno na Pythonu 3.14 a PySide6 6.11.2. `build.bat` vytvoří lokální prostředí, nainstaluje připnuté závislosti, spustí jednotkové testy a sestaví EXE podle `Pulse Music Player.spec`.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe tools\setup_ffmpeg.py
.venv\Scripts\python.exe app.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m PyInstaller --noconfirm "Pulse Music Player.spec"
```

Integrační test si vytváří vlastní tiché mediální ukázky a izolovanou knihovnu v `qa/`; nedotýká se uživatelských playlistů:

```powershell
.venv\Scripts\python.exe -m pip install imageio-ffmpeg==0.6.0
.venv\Scripts\python.exe tests\smoke_player.py
```

`pulse_core.py` obsahuje ukládání a přehrávací frontu, `app.py` rozhraní a obsluhu médií, `player_widgets.py` kreslené ikony a video/fullscreen prvky. FFmpeg DLL a Qt multimediální pluginy jsou součástí sestavení. Dokumentace backendu: https://doc.qt.io/qt-6/qtmultimedia-index.html
