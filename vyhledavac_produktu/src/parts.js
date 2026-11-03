import { normalize, memo } from './schema.js';
import { extractHardware, statedVram } from './hardware.js';

// Component parameters read from a listing. Each value comes from the title when it names it, otherwise
// from the description; several different values in the deciding text leave the parameter unknown.
const one = values => { const list = [...new Set(values.filter(v => v != null && v !== ''))]; return list.length === 1 ? list[0] : list.length ? undefined : null; };
const pick = (texts, read) => { for (const text of texts) { const value = one(read(text)); if (value !== null) return value ?? null; } return null; };
const all = (text, re, map = m => m[1]) => [...text.matchAll(re)].map(map);
const sizeGb = (n, unit) => Math.round(Number(n.replace(',', '.')) * (/^t/.test(unit) ? 1000 : 1));
const count = text => Number(text.replace(/[\s.]/g, ''));
// "3 500" and "3.500" are thousands; a longer run of digits and spaces is several numbers.
const number = String.raw`(\d{1,2}[\s.]\d{3}|\d{1,5})`;

const memType = text => all(text, /\b(?:(?<!lp)ddr\s*([2-5])l?|pc([2-5])l?-\d{4,5})\b/g, m => `ddr${m[1] ?? m[2]}`);

export const sockets = ['AM3','AM4','AM5','FM2','LGA775','LGA1150','LGA1151','LGA1155','LGA1156','LGA1200','LGA1700','LGA1851','LGA2011','LGA2066','TR4','STRX4'];
const socketText = text => all(text, /\b(?:socket\s*)?(am[345]|fm2|tr4|strx4)\+?(?![a-z0-9])|\b(?:lga|socket|patice)\s*-?\s*(775|115[0156]|1200|1700|1851|2011|2066)\b|\bs(1150|1151|1155|1200|1700|1851)\b/g,
  m => m[1] ? m[1].toUpperCase() : `LGA${m[2] ?? m[3]}`);
// Desktop chips name their socket through the generation; notebook chips (U, H, P suffix) are soldered.
function socketOfCpu(cpu) {
  if (!cpu) return null;
  let m = cpu.match(/^I[3579]-(\d{4,5})([A-Z]*)$/);
  if (m) {
    if (/[UHPY]/.test(m[2])) return null;
    const gen = m[1].length === 5 ? +m[1].slice(0, 2) : +m[1][0];
    return gen >= 12 ? 'LGA1700' : gen >= 10 ? 'LGA1200' : gen >= 6 ? 'LGA1151' : gen >= 4 ? 'LGA1150' : gen >= 2 ? 'LGA1155' : null;
  }
  if (/^CORE ULTRA [3579] 2\d\d[KF]*$/.test(cpu)) return 'LGA1851';
  m = cpu.match(/^RYZEN [3579] (?:PRO )?(\d{4})([A-Z]*)$/);
  if (m && !/[UH]/.test(m[2])) return +m[1][0] >= 7 ? 'AM5' : 'AM4';
  return null;
}
const chipsets = [['AM4',/\b[abx](?:3[257]0|4[57]0|5[2457]0)\b/], ['AM5',/\b(?:a620|b650e?|x670e?|b850|x870e?)\b/], ['LGA1851',/\b(?:z890|b860|h810)\b/],
  ['LGA1700',/\b(?:h610|b660|h670|z690|b760|h770|z790)\b/], ['LGA1200',/\b(?:h410|b460|h470|z490|h510|b560|h570|z590)\b/],
  ['LGA1151',/\b(?:h110|b150|h170|z170|b250|h270|z270|h310|b360|b365|h370|z370|z390)\b/], ['LGA1150',/\b(?:h81|b85|h87|z87|h97|z97)\b/], ['LGA1155',/\b(?:h61|b75|h77|z77|z68|p67|h67)\b/]];

const efficiencyRank = ['white','bronze','silver','gold','platinum','titanium'];
export const efficiencies = efficiencyRank;

const readers = {
  ssd: {
    // "M.2" alone does not say NVMe or SATA; a 2.5" drive or a bare "SATA" is a SATA disk.
    interface: text => {
      const m2 = /\bm\.?\s?2\b|\b2280\b/.test(text), nvme = /\b(?:nvme|pci-?e|pcie)\b/.test(text), sata = /\bsata\b/.test(text);
      return [nvme ? 'nvme' : m2 && sata ? 'm2sata' : m2 ? 'm2' : sata || /\b2[.,]5\s*(?:"|''|palc|inch|in\b)/.test(text) ? 'sata' : null];
    },
    capacityGb: text => all(text, /\b(\d+(?:[.,]\d+)?)\s*(gb|tb)\b(?!\s*\/\s*s)/g, m => sizeGb(m[1], m[2])).filter(gb => gb >= 32),
    // Read speed is the first and higher of "3500/3000 MB/s"; SATA "6 Gb/s" is the link, not the drive.
    readMbs: text => {
      const labelled = all(text, new RegExp(String.raw`\b(?:cteni|read\w*)\s*(?:rychlost\w*\s*)?(?:az|up to|do)?\s*[:=-]?\s*${number}\s*mb\s*\/?\s*s`, 'g'), m => count(m[1]));
      const speeds = all(text, new RegExp(String.raw`\b${number}\s*(?:\/\s*${number}\s*)?mb\s*\/?\s*s\b`, 'g'), m => count(m[1])).filter(n => n >= 50);
      return labelled.length ? labelled : speeds.length ? [Math.max(...speeds)] : [];
    },
    tbw: text => [...all(text, new RegExp(String.raw`\b${number}\s*tbw\b`, 'g'), m => count(m[1])), ...all(text, new RegExp(String.raw`\btbw\s*[:=-]?\s*${number}\b`, 'g'), m => count(m[1]))],
    healthPct: text => [...all(text, /\b(?:zdravi|health|zivotnost|kondice|stav|smart)\s*(?:disku\s*)?[:=-]?\s*(\d{1,3})\s*%/g, m => +m[1]), ...all(text, /\b(\d{1,3})\s*%\s*(?:zdravi|health|zivotnost)/g, m => +m[1])].filter(n => n <= 100),
  },
  gpu: {
    chip: text => [...new Set([/\b(?:nvidia|geforce|rtx|gtx|quadro|gt\s?\d{3,4})\b/.test(text) && 'nvidia', /\b(?:radeon|rx\s?\d{3,4}|amd)\b/.test(text) && 'amd', /\b(?:intel\s+)?arc\s+a\d{3}\b/.test(text) && 'intel'].filter(Boolean))],
  },
  cpu: {
    chip: text => [...new Set([/\b(?:intel|core\s+i[3579]|i[3579]-?\s?\d{4,5}|celeron|pentium|xeon|core\s+ultra)\b/.test(text) && 'intel', /\b(?:amd|ryzen|athlon|threadripper|epyc|fx-?\d{4})\b/.test(text) && 'amd'].filter(Boolean))],
    socket: socketText,
    cores: text => all(text, /\b(\d{1,2})\s*(?:-|\s)?(?:jader|jadra|jadrovy|jadrov\w*|cores?|c\s*\/\s*\d{1,2}\s*t)/g, m => +m[1]).filter(n => n >= 1 && n <= 64),
  },
  ram: {
    memType,
    form: text => { const so = /\b(?:so-?\s?dimm|sodimm|notebook\w*|laptop\w*|ntb)\b/.test(text); const dimm = /\b(?:u?dimm|desktop\w*|stolni)\b/.test(text.replace(/so-?\s?dimm/g, '')); return so && dimm ? ['sodimm','dimm'] : [so ? 'sodimm' : dimm ? 'dimm' : null]; },
    // "32GB (2x16GB)" is one 32 GB kit; "2x 8 GB" alone is 16 GB.
    capacityGb: text => { const kits = all(text, /\b([1-8])\s*x\s*(\d{1,3})\s*gb\b/g, m => m[1] * m[2]); return kits.length ? kits : all(text, /\b(\d{1,3})\s*gb\b/g, m => +m[1]).filter(n => n >= 1 && n <= 512); },
    mhz: text => [...all(text, /\b(\d{3,4})\s*(?:mhz|mt\s*\/\s*s)\b/g, m => +m[1]), ...all(text, /\bddr[2-5]l?\s*-\s*(\d{3,4})\b/g, m => +m[1]), ...all(text, /\bpc[2-5]l?-(\d{4,5})\b/g, m => Math.round(m[1] / 8 / 100) * 100)].filter(n => n >= 400 && n <= 12000),
  },
  psu: {
    watts: text => all(text, /\b(\d{3,4})\s*w(?:att\w*)?\b/g, m => +m[1]).filter(n => n >= 150 && n <= 2500),
    efficiency: text => { const levels = all(text, /\b(titanium|platin\w*|gold|silver|bronze)\b/g, m => /^platin/.test(m[1]) ? 'platinum' : m[1]); return levels.length ? levels : [/\b80\s*(?:\+|plus)/.test(text) ? 'white' : null]; },
    modular: text => [/\b(?:nemodul\w*|non-?\s?modular)\b/.test(text) ? 'none' : /\b(?:plne|full(?:y)?|zcela)\s*-?\s*modul\w*/.test(text) ? 'full' : /\b(?:semi|polo|castecne)\s*-?\s*modul\w*/.test(text) ? 'semi' : /\bmodul(?:arni|ar)\b/.test(text) ? 'modular' : null],
  },
  mb: {
    socket: text => { const named = socketText(text); return named.length ? named : chipsets.filter(([, re]) => re.test(text)).map(([s]) => s); },
    memType,
    form: text => [/\be-?\s?atx\b/.test(text) ? 'eatx' : /\b(?:micro\s*-?\s*atx|m-?atx|matx|uatx|µatx)\b/.test(text) ? 'matx' : /\b(?:mini\s*-?\s*itx|m-?itx|itx)\b/.test(text) ? 'itx' : /\batx\b/.test(text) ? 'atx' : null],
  },
};

// Aukro parameters give buckets ("Výkon zdroje: 550 - 649 W", "Kapacita: 500 - 999 GB"), not the part's value.
const ranges = /\b\d+(?:[.,]\d+)?\s*(?:-|–|az)\s*\d+(?:[.,]\d+)?\s*(?:w|gb|tb|mhz|mb\s*\/\s*s|tbw|%)(?![a-z])/g;
// PSU model numbers carry the wattage: "Seasonic B12 BC-550", "Corsair RM750x", "EVGA 650 GM".
const psuWatts = new Set([300,350,400,430,450,500,520,550,600,620,650,700,750,800,850,900,1000,1050,1200,1300,1500,1600]);
const modelWatts = text => all(text, /(?:^|[^a-z0-9])[a-z]{0,4}-?(\d{3,4})[a-z]{0,3}(?![a-z0-9])/g, m => +m[1]).filter(n => psuWatts.has(n));

const extractCached = memo(key => {
  const [kind, rawTitle, rawDescription] = key.split('\u0000');
  const texts = [normalize(rawTitle), normalize(rawDescription)].map(text => text.replace(ranges, ' '));
  const specs = { kind };
  for (const [name, read] of Object.entries(readers[kind])) specs[name] = pick(texts, read);
  if (kind === 'psu' && !specs.watts) specs.watts = pick([texts[0]], modelWatts);
  if (kind === 'gpu') {
    const vram = statedVram({ title: rawTitle, description: rawDescription });
    // A card title such as "Sapphire RX 580 8GB" states the memory with no other size around it.
    specs.vramGb = vram !== undefined ? vram : pick([texts[0]], text => all(text, /\b(\d{1,2})\s*gb\b/g, m => +m[1]).filter(n => [1,2,3,4,6,8,10,11,12,16,20,24,32,48].includes(n)));
  }
  if (kind === 'cpu' && !specs.socket) specs.socket = socketOfCpu(extractHardware({ title: rawTitle, description: rawDescription }).cpu);
  return specs;
}, 10000);

export const partKinds = Object.keys(readers);
export const extractPart = (item, kind) => readers[kind] ? { ...extractCached(`${kind}\u0000${item.title ?? ''}\u0000${item.description ?? ''}`) } : null;

// Each check: [filter value is set, specs value, does it pass]. Unknown values follow "Pustit i neznámé".
const checks = {
  ssd: (s, f) => [
    [f.interface, s.interface, () => f.interface === 'm2' ? ['m2','nvme','m2sata'].includes(s.interface) : s.interface === 'm2' ? undefined : s.interface === f.interface],
    [f.minCapacityGb, s.capacityGb, () => s.capacityGb >= f.minCapacityGb], [f.minReadMbs, s.readMbs, () => s.readMbs >= f.minReadMbs],
    [f.minTbw, s.tbw, () => s.tbw >= f.minTbw], [f.minHealth, s.healthPct, () => s.healthPct >= f.minHealth],
  ],
  gpu: (s, f) => [[f.chip, s.chip, () => s.chip === f.chip], [f.minVramGb, s.vramGb, () => s.vramGb >= f.minVramGb]],
  cpu: (s, f) => [[f.chip, s.chip, () => s.chip === f.chip], [f.socket, s.socket, () => s.socket === f.socket], [f.minCores, s.cores, () => s.cores >= f.minCores]],
  ram: (s, f) => [[f.memType, s.memType, () => s.memType === f.memType], [f.ramForm, s.form, () => s.form === f.ramForm], [f.minCapacityGb, s.capacityGb, () => s.capacityGb >= f.minCapacityGb], [f.minMhz, s.mhz, () => s.mhz >= f.minMhz]],
  psu: (s, f) => [
    [f.minWatts, s.watts, () => s.watts >= f.minWatts],
    [f.efficiency, s.efficiency, () => efficiencyRank.indexOf(s.efficiency) >= efficiencyRank.indexOf(f.efficiency)],
    // "Modulární" without full or semi passes the semi-modular minimum but stays unknown for full.
    [f.modular, s.modular, () => s.modular === 'none' ? false : f.modular === 'full' ? (s.modular === 'modular' ? undefined : s.modular === 'full') : true],
  ],
  mb: (s, f) => [[f.socket, s.socket, () => s.socket === f.socket], [f.memType, s.memType, () => s.memType === f.memType], [f.boardForm, s.form, () => s.form === f.boardForm]],
};

export function partMatches(specs, part, kind, includeUnknown) {
  if (!checks[kind] || !specs || !part) return true;
  for (const [wanted, value, passes] of checks[kind](specs, part)) {
    if (wanted == null || wanted === '') continue;
    const result = value == null ? undefined : passes();
    if (result === false || (result === undefined && !includeUnknown)) return false;
  }
  return true;
}
