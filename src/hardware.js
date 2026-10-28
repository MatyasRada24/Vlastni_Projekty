import { normalize, memo } from './schema.js';

const canonical = value => normalize(value).replace(/[^a-z0-9]/g, '');
const tidy = value => value.replace(/\s+/g, ' ').trim().toUpperCase();
const keys = ['brand','model','cpu','gpu','sku','ramGb','storageGb','storageType'];
const textKeys = new Set(['model','cpu','gpu','sku']);

// Pattern + formatter pairs; formatters give one spelling per part so duplicates collapse.
const cpuPatterns = [
  [/\b(?:intel\s+)?(?:core\s+)?(?:ultra\s*(x?)|u(?=[3579]))([3579])\s*[- ]?\s*(\d{3})([a-z]{0,2})\b/g, m => `CORE ULTRA ${m[1] ? 'X' : ''}${m[2]} ${m[3]}${m[4]}`],
  [/\b(?:intel\s+)?core\s+([3579])\s+(\d{3})([a-z]{0,2})\b/g, m => `CORE ${m[1]} ${m[2]}${m[3]}`],
  [/\b(?:intel\s+)?(?:core\s+)?i([3579])\s*[- ]?\s*(\d{4,5}(?:[a-z]{1,2}\d?)?|\d{3}[a-z]{1,2})\b(?!\s*(?:gb|ghz|mhz))/g, m => `I${m[1]}-${m[2]}`],
  [/\b(?:amd\s+)?ryzen\s+(ai\s+)?([3579])\s+(pro\s+|hx\s+)?(\d{3,4}[a-z]{0,3})\b/g, m => `RYZEN ${m[1] ? 'AI ' : ''}${m[2]} ${m[3] ?? ''}${m[4]}`],
  [/\bsnapdragon\s+x\s*(elite|plus)?(?:\s+(x1[ep])\s*-?\s*(\d{2})\s*-?\s*(\d{3}))?/g, m => `SNAPDRAGON X ${m[1] ?? ''} ${m[2] ? `${m[2]}-${m[3]}-${m[4]}` : ''}`],
  [/\b(?:intel\s+)?(celeron|pentium)\s+(silver\s+|gold\s+)?([a-z]?\d{4}[a-z]?)\b/g, m => `${m[1]} ${m[2] ?? ''}${m[3]}`],
  [/\b(?:amd\s+)?athlon\s+(silver\s+|gold\s+)?(\d{4}[a-z]?)\b/g, m => `ATHLON ${m[1] ?? ''}${m[2]}`],
];
const appleCpu = [/\b(?:apple\s+)?m([1-9])(?:\s*(pro|max|ultra))?\b/g, m => `M${m[1]}${m[2] ? ` ${m[2]}` : ''}`];
const gpuPatterns = [
  [/\b(?:geforce\s+)?(rtx|gtx|mx)\s*-?\s*(\d{3,4})\s*(ti|super)?\b/g, m => `${m[1]} ${m[2]}${m[3] ? ` ${m[3]}` : ''}`],
  [/\brtx\s+a(\d{3,4})\b/g, m => `RTX A${m[1]}`],
  [/\brtx\s+(pro\s+)?(\d{3,4})\s+(ada|blackwell)\b/g, m => `RTX ${m[1] ?? ''}${m[2]} ${m[3]}`],
  [/\b(?:nvidia|quadro)\s+(?:quadro\s+)?([tpa])(\d{3,4})\b/g, m => `${m[1]}${m[2]}`],
  [/\b(?:amd\s+)?radeon\s+(pro\s+)?(rx\s*)?(\d{3,4})\s*(m|s|xt)?\b/g, m => `RADEON ${m[1] ?? ''}${m[2] ? 'RX ' : ''}${m[3]}${m[4] ?? ''}`],
  [/\brx\s*(\d{4})\s*(m|s|xt)?\b/g, m => `RADEON RX ${m[1]}${m[2] ?? ''}`],
  [/\b(?:radeon\s+)?(?:rx\s+)?vega\s*(\d{1,2})\b/g, m => `RADEON VEGA ${m[1]}`],
  [/\bradeon\s+graphics\b/g, () => 'RADEON GRAPHICS'],
  [/\biris\s+(xe|plus)\b/g, m => `IRIS ${m[1]}`],
  [/\buhd\s*(?:graphics\s*)?(\d{3})\b/g, m => `UHD ${m[1]}`],
  [/\b(?:intel\s+)?uhd\s+graphics\b(?!\s*\d)/g, () => 'UHD GRAPHICS'],
  [/\barc\s+([ab]\d{3}m?)\b/g, m => `ARC ${m[1]}`],
  [/\barc\s+graphics\b/g, () => 'ARC GRAPHICS'],
];
const discreteGpu = /^(?:RTX|GTX|MX|[TPA]\d|RADEON (?:PRO|RX)|ARC A\d{3}M)/;
// "G10" means a generation only in business lines; ROG Strix G18 or Dell G15 are model names.
const generation = value => /^(?:THINKPAD|THINKBOOK|X1|ELITEBOOK|PROBOOK|ZBOOK)\b/.test(value) ? value.replace(/\b(?:GEN\.?\s*|G)(\d{1,2})\b/g, 'GEN $1') : value;
const modelPatterns = [
  /\b(?:thinkpad|ideapad|legion|loq|yoga|thinkbook)\s+(?:slim\s+|pro\s+|gaming\s+)?(?:[3579]\s+)?(?:[a-z]?\d{2}[a-z]{2,6}\d{1,3}[a-z]?|[txelpz]\d{1,3}(?:s|p)?(?:\s+(?:extreme|carbon|yoga|nano))?(?:\s+(?:gen\.?|g)\s*\d{1,2})?)\b/g,
  /\b(?:thinkpad\s+)?x1\s+(?:carbon|yoga|extreme|nano)(?:\s+(?:gen\.?|g)\s*\d{1,2})?\b/g,
  /\blenovo\s+(?:thinkpad\s+)?[txelpz]\d{2,3}[sp]?(?:\s+(?:gen\.?|g\.?)\s*\d{1,2})?\b/g,
  /\bdell\s+(?:latitude\s+)?e\d{4}\b/g,
  /\b(?:loq|ideapad|legion|yoga|thinkbook|vivobook|zenbook|tuf\s+gaming)\s+(?:(?:essential|slim|pro|gaming|go|flex|plus|duo|s)\s+){0,2}(?:[3579]\s+)?1[3-8]\b/g,
  /\bhp\s+[23][45]\d\s+g\d{1,2}\b/g,
  /\b(?:[fg][ax]\d{3}[a-z]{0,3}|[ag]\d{3}[a-z]{1,4}|[fxkm]\d{3,4}[a-z]{1,3}|u[xm]\d{3,4}[a-z]{0,3})(?:-[a-z0-9]{3,12})?\b/g,
  /\b(?:anv?|ph|pt|phn|sf|sfg|al|ag|a[1-9])\d{2,3}-\d{2,3}(?:-[a-z0-9]{3,8})?\b/g,
  /\b(?:victus|omen|pavilion|envy|spectre)\s+(?:x360\s+)?(?:laptop\s*-?\s*)?(?:\d{2}-[a-z]{1,3}\d{3,5}[a-z]{0,2}|\d{2})\b/g,
  /\b(?:elitebook|probook|zbook)\s+(?:(?:firefly|fury|power|studio|create|ultra)\s+)?(?:x360\s+)?\d{2,4}(?:\s+g\d{1,2})?\b/g,
  /\b(?:latitude|lattitude|precision|inspiron|vostro|xps)\s+(?:\d{2}\s+)?(?:plus\s+|pro\s+)?\d{4}\b/g,
  /\bxps\s+1[3-7]\b/g,
  /\b(?:alienware\s+[mx]?\d{2}(?:\s+r\d{1,2})?|dell\s+g(?:3|5|7|15|16)(?:\s+\d{4})?)\b/g,
  /\b(?:nitro|helios|aspire|swift|travelmate|extensa)\s+(?:v\s*)?(?:neo\s+)?\d{1,2}\b/g,
  /\baspire\s+one\s+[a-z]?\d{3}\b/g,
  /\b(?:zephyrus|zephirus|strix|flow|tuf\s+gaming)\s+(?:scar\s+)?[a-z]\d{2}\b/g,
  /\b(?:katana|sword|cyborg|raider|stealth|pulse|bravo|vector|titan|crosshair|thin|modern|prestige|summit|creator|alpha|delta|gf|gl|gp|ge|gs|gt)\s*a?\d{2}(?:\s+hx)?(?:\s+[a-z0-9]{3,10}(?:-[a-z0-9]{3,8})?)?\b/g,
  /\bmacbook\s+(?:air|pro)\s+(?:13|14|15|16)(?:\s+m[1-9](?:\s+(?:pro|max))?)?\b/g,
  /\bmacbook\s+(?:air|pro)\b/g,
  /\b(?:razer\s+blade\s+1[4-8]|aorus\s+[a-z]?\d{2}|matebook\s+(?:d\s*)?1[3-6]|galaxy\s+book\s*\d(?:\s+(?:pro|ultra|360))?)\b/g,
];
const skuPatterns = [
  /\b(?:8[0-9a-z]{9}|(?:[fg][axu]\d{3}[a-z]{1,3}|[ag]\d{3}[a-z]{1,4}|[fxkm]\d{3,4}[a-z]{1,3})-[a-z0-9]{3,12}|(?:anv?|ph|phn)\d{2,3}-\d{2,3}-[a-z0-9]{3,8})\b/g,
  /\b1[3-7]-[a-z]{1,3}\d{3,5}[a-z]{2}\b/g,
  /\b[a-z]\d{1,2}[a-z]{3,5}-\d{3,4}[a-z]{2,4}\b/g,
  /\b\d[a-z0-9]{4}(?:ea|es|ec|av|ua|ut|ez)\b(?=[^a-z0-9]|$)/g,
];
const brands = /\b(lenovo|asus|acer|msi|dell|hp|apple|gigabyte|razer|fujitsu|toshiba|samsung|huawei|honor|microsoft|medion|xiaomi)\b/g;
const families = [
  ['LENOVO',/\b(?:thinkpad|legion|ideapad|yoga|loq|thinkbook)\b/], ['HP',/\b(?:omen|victus|pavilion|elitebook|probook|zbook|envy|spectre)\b/],
  ['ASUS',/\b(?:zenbook|vivobook|rog|tuf|expertbook|zephyrus|strix)\b/], ['ACER',/\b(?:nitro|predator|aspire|swift|travelmate|extensa)\b/],
  ['DELL',/\b(?:latitude|inspiron|xps|precision|vostro|alienware)\b/], ['APPLE',/\bmacbook\b/], ['MSI',/\b(?:katana|vector|raider|stealth|titan|cyborg|crosshair)\b/],
];

const labels = [
  ['gpu','model graficke karty|graficka karta|graficky cip|graficky procesor|graficky adapter|grafika|gpu|vga'],
  ['cpu','model procesoru|typ procesoru|procesor|cpu|cip'],
  ['ram','velikost operacni pameti|operacni pamet|pamet ram|ram pamet|pamet|ram|memory'],
  ['storageType','typ pevneho disku|typ disku|typ uloziste'],
  ['storage','kapacita disku|kapacita ssd|kapacita uloziste|ssd\\/hdd disk|pevny disk|ssd disk|uloziste|disk|ssd\\s?\\d?|hdd|slot\\s?1'],
  ['sku','p\\/n|part number|kod vyrobce|produktove cislo|mpn'],
  ['model','model notebooku|modelova rada|typove oznaceni|model'],
  ['brand','znacka|vyrobce'],
].flatMap(([key,list]) => list.split('|').map(label => [key,label])).sort((a,b) => b[1].length - a[1].length);
const labelRe = new RegExp(`(?:^|[^a-z0-9])(${labels.map(([,l]) => l).join('|')})\\s*[:=]\\s*`, 'g');
const labelTests = labels.map(([key,l]) => [key,new RegExp(`^(?:${l})$`)]);
const labelKey = label => labelTests.find(([,re]) => re.test(label))[0];
const range = /\d+(?:[.,]\d+)?\s*(?:gb|tb)?\s*(?:–|-|az)\s*\d+(?:[.,]\d+)?\s*(?:gb|tb)|\ba (?:vice|mene|vyse)\b|\b(?:mene|vice) nez\b/;

function prepare(value) {
  return normalize(value).replace(/[™®©]|\((?:r|tm)\)/g, '').replace(/_/g, ' ')
    // Upgrade options, alternative configurations and trade-in wishes are not this laptop's hardware.
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\([^)]*(?:max|rozsir|priplat|moznost|lze|volny)[^)]*\)/g, ' ')
    .replace(/(?:\bmax\w*(?:\s+(?:velikost|kapacita|pamet\w*|ram))?|\bumi|(?:mohu\s+)?rozsir\w*(?:\s+[a-z]+){0,4}?\s+na|upgrade na)\s*[:=]?\s*(?:az\s*)?\d+(?:[.,]\d+)?\s*(?:gb|tb)(?:\s*(?:\/|,|nebo|a)\s*\d+(?:[.,]\d+)?\s*(?:gb|tb))*/g, ' ')
    .replace(/(?<!\d\s*(?:gb|tb)?\s*)\b(?:az|up to)\s*\d+(?:[.,]\d+)?\s*(?:gb|tb)\b/g, ' ')
    .replace(/(?:v konfiguraci s|verze|varianta)\s[^.!]{0,60}?(?:za cenu|,-|kc)/g, ' ')
    .replace(/(?:vymen\w* za|vymena\s*:?|zajima me)[^.!]{0,160}/g, ' ');
}

const collect = (text, patterns) => patterns.flatMap(([re, format]) => [...text.matchAll(re)].map(m => tidy(format(m))));
const sizeGb = (n, unit) => Number(n.replace(',', '.')) * (/^t/.test(unit) ? 1000 : 1);
// The first named type belongs to the stated size: "SSD 1TB + slot na další HDD" is an SSD.
const storageTypeOf = text => ({hdd:'HDD',emmc:'EMMC'})[text.match(/\b(ssd|nvme|m\.?2|hdd|emmc)\b/)?.[1]] ?? (/\b(?:ssd|nvme|m\.?2)\b/.test(text) ? 'SSD' : null);
// VRAM after a GPU name ("RTX 4060 8GB GDDR6") must never be read as RAM or disk.
const withoutGpuMemory = text => text
  .replace(/\b(?:rtx|gtx|mx|rx|radeon(?:\s+pro)?|quadro|arc)[\s-]*(?:[a-z]?[\s-]*\d{3,4}[\s-]*(?:ti|super|xt|m|ada)?[\s-]*)?\d{1,2}\s*gb(?!\s*(?:(?:lp)?ddr|ram|operacni|ssd|hdd|nvme|emmc))(?:\s*g?ddr\d\w*)?/g, ' ')
  .replace(/\b\d{1,2}\s*gb\s*(?:g?ddr\d\w*\s*)?(?:vram|gddr\d\w*)/g, ' ')
  .replace(/\b(?:vlastni|dedikovan\w*|graficke|video)\s+\d{1,2}\s*gb(?:\s*g?ddr\d\w*)?(?:\s*pamet\w*)?/g, ' ')
  .replace(/\b\d{1,2}\s*gb\s*(?:g?ddr\d\w*\s*)?(?:vlastni|graficke|video)\s*pamet\w*/g, ' ');

function freeText(text, { title = false, apple = false } = {}) {
  const out = Object.fromEntries(keys.map(k => [k,[]]));
  out.brand = [...text.matchAll(brands)].map(m => m[1].toUpperCase())
    .filter((b,i,all) => b !== 'SAMSUNG' || new Set(all).size === 1); // SSD/RAM vendor, rarely the laptop brand when another brand is named
  // A title like "Herní Omen 16, RTX 4070" names the brand through its product line.
  if (title && !out.brand.length) out.brand = families.filter(([,re]) => re.test(text)).map(([b]) => b);
  // The chip belongs to the CPU field: "MacBook Air 13 M2" is model "MACBOOK AIR 13" with CPU "M2".
  out.model = modelPatterns.flatMap(re => [...text.matchAll(re)].map(m => generation(tidy(m[0].replace(/^(macbook\s+(?:air|pro)\s+\d{2})\s+m[1-9].*$/, '$1')
    .replace(/^lattitude/, 'latitude').replace(/\blaptop\s*-?\s*/, '').replace(/\bg\.\s*(\d)/, 'g$1')
    .replace(/^lenovo\s+(?:thinkpad\s+)?/, 'thinkpad ').replace(/^dell\s+(?:latitude\s+)?/, 'latitude ')))));
  out.cpu = collect(text, cpuPatterns);
  if (apple) out.cpu.push(...collect(text, [appleCpu]));
  out.gpu = collect(text, gpuPatterns);
  out.sku = skuPatterns.flatMap(re => [...text.matchAll(re)].map(m => tidy(m[0])));
  const memory = withoutGpuMemory(text);
  out.ramGb.push(
    ...[...memory.matchAll(/\b(?:ram|operacni pamet|pamet|memory)\s*[:=-]?\s*(?:\d\s*x\s*)?(\d{1,3})\s*gb\b/g)].map(m => +m[1]),
    ...[...memory.matchAll(/\b(\d{1,3})\s*gb\s*(?:(?:so-?dimm|sjednocene)\s*)?(?:ram|(?:lp)?ddr\d|operacni|pamet)/g)].map(m => +m[1]),
    ...[...memory.matchAll(/\bram\s+(?:lp)?ddr\d\w*\s+(\d{1,3})\s*gb\b/g)].map(m => +m[1]),
    ...[...memory.matchAll(/(?:\/|,)\s*(\d{1,3})\s*gb\s*(?:\/|,)\s*\d+(?:[.,]\d+)?\s*(?:gb|tb)\s*ssd\b/g)].map(m => +m[1]),
  );
  const disks = [
    ...[...memory.matchAll(/\b(\d+(?:[.,]\d+)?)\s*(gb|tb|t)\s*\(?\s*(?:(?:m\.?2|pcie(?:\s*gen\s*\d)?|gen\s*\d|sata|flash|2280|disk|\d\.\d)\s*)*(ssd|hdd|nvme|emmc|m\.?2)\b/g)].map(m => ({gb:sizeGb(m[1],m[2]),type:storageTypeOf(m[3])})),
    ...[...memory.matchAll(/\b(ssd|hdd|nvme|emmc)\s*(?:disk|flash|m\.?2)?\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*(gb|tb)\b(?!\s*(?:ram|(?:lp)?ddr|operacni|pamet))/g)].map(m => ({gb:sizeGb(m[2],m[3]),type:storageTypeOf(m[1])})),
  ];
  if (title) {
    // "24/32/48GB RAM" lists offered variants, not this laptop's memory.
    for (const m of memory.matchAll(/\b(\d{1,2})\s*\/\s*(\d{1,2})((?:\s*\/\s*\d{1,2})*)\s*gb\b/g)) out.ramGb.push(+m[1], +m[2], ...(m[3].match(/\d+/g) ?? []).map(Number));
    // Listing titles commonly read "i7, 16GB, 512GB" or "16/256 GB" without the words RAM/SSD.
    for (const m of memory.matchAll(/\b(\d{1,2})\s*(?:gb)?\s*\/\s*(\d{3,4}|[124])\s*(gb|tb)\b/g)) { out.ramGb.push(+m[1]); disks.push({gb:sizeGb(m[2],m[3]),type:null}); }
    for (const m of memory.matchAll(/\b(\d+(?:[.,]\d+)?)\s*(gb|tb)\b(?!\s*(?:ddr|gddr|vram))/g)) {
      const gb = sizeGb(m[1], m[2]);
      if (m[2] === 'gb' && [4,8,12,16,18,20,24,32,36,40,48,64,96].includes(gb)) out.ramGb.push(gb);
      else if (gb >= 120) disks.push({gb,type:null});
    }
  }
  out.storageGb = disks.map(d => d.gb);
  out.storageType = disks.map(d => d.type).filter(Boolean);
  out.ramGb = out.ramGb.filter(n => n > 0 && n <= 256);
  return out;
}

// "Procesor: …", "RAM: …" and Aukro parameters ("Model grafické karty: RTX 4060") name the field explicitly.
function labelled(text, apple) {
  const out = Object.fromEntries(keys.map(k => [k,[]]));
  const hits = [...text.matchAll(labelRe)];
  hits.forEach((hit, i) => {
    const start = hit.index + hit[0].length;
    const end = Math.min(hits[i + 1]?.index ?? text.length, start + 90);
    const value = text.slice(start, end).split(/[•*|;\n]| - /)[0];
    const key = labelKey(hit[1]);
    if (key === 'cpu') out.cpu.push(...collect(value, apple ? [...cpuPatterns, appleCpu] : cpuPatterns));
    else if (key === 'gpu') out.gpu.push(...collect(value, gpuPatterns));
    else if (key === 'ram' && !range.test(value)) {
      const m = value.match(/\b(?:([1-4])\s*x\s*)?(\d{1,3})\s*gb\b/), gb = m ? (+m[1] || 1) * +m[2] : null; // "2x 32GB" is 64 GB
      if (gb && gb <= 256) out.ramGb.push(gb);
    }
    else if (key === 'storage' && !range.test(value)) {
      const m = value.match(/\b(\d+(?:[.,]\d+)?)\s*(gb|tb|t)\b/);
      if (m) { out.storageGb.push(sizeGb(m[1], m[2])); const type = storageTypeOf(`${hit[1]} ${value}`); if (type) out.storageType.push(type); }
    }
    else if (key === 'storageType') { const type = storageTypeOf(value); if (type) out.storageType.push(type); }
    else if (key === 'sku') out.sku.push(...value.split(/[\s,]+/).filter(t => /^[a-z0-9#-]{5,20}$/.test(t) && /\d/.test(t) && /[a-z]/.test(t)).slice(0,1).map(tidy));
    else if (key === 'model') { const f = freeText(value); out.model.push(...f.model); out.sku.push(...f.sku); }
    else if (key === 'brand') out.brand.push(...[...value.matchAll(brands)].slice(0,1).map(m => m[1].toUpperCase()));
  });
  return out;
}

function distinct(key, values) {
  let list = [...new Map(values.map(v => [textKeys.has(key) || key === 'brand' || key === 'storageType' ? canonical(v) : v, v])).values()];
  if (textKeys.has(key)) list = list.filter(v => !list.some(o => o !== v && canonical(o).includes(canonical(v))));
  if (key === 'gpu' && list.some(v => discreteGpu.test(v))) list = list.filter(v => discreteGpu.test(v));
  return list;
}

// Sources are ranked: named fields, then the listing title, then the free description.
// A stronger source wins; conflicting values within the deciding source stay unknown.
const extractCached = memo(key => { const [title, description] = key.split('\u0000'); return extract(title, description); }, 10000);
// Callers may adjust the result (e.g. a retailer part number), so each call gets its own copy.
export function extractHardware(item) {
  const result = extractCached(`${item.title ?? ''}\u0000${item.description ?? ''}`);
  return { ...result, ambiguous: [...result.ambiguous] };
}

function extract(rawTitle, rawDescription) {
  const title = prepare(rawTitle), description = prepare(rawDescription);
  const apple = /\b(?:apple|macbook)\b/.test(`${title} ${description}`);
  const tiers = [labelled(`${title}. ${description}`, apple), freeText(title, {title:true, apple}), freeText(description, {apple})];
  const result = {}, ambiguous = [];
  for (const key of keys) {
    result[key] = null;
    for (const tier of tiers) {
      let values = distinct(key, tier[key]);
      // A product code ("ANV16-42-R1M5") is kept as the SKU; the series name is the readable model.
      if (key === 'model' && values.length > 1) {
        const skus = new Set(tier.sku.map(canonical)), named = values.filter(v => !skus.has(canonical(v)));
        if (named.length) values = named;
      }
      if (values.length === 1) { result[key] = values[0]; break; }
      if (values.length > 1) { ambiguous.push(key); break; }
    }
    // A weaker source may add detail to the same part: "THINKPAD X1 CARBON" → "THINKPAD X1 CARBON GEN 10".
    if (result[key] && textKeys.has(key)) {
      const richer = distinct(key, tiers.flatMap(t => t[key]).filter(v => canonical(v).includes(canonical(result[key]))));
      if (richer.length === 1) result[key] = richer[0];
    }
  }
  if (!result.brand && !ambiguous.includes('brand')) {
    const family = families.filter(([,re]) => re.test(`${title} ${description}`)).map(([b]) => b);
    if (new Set(family).size === 1) result.brand = family[0];
  }
  // Every MacBook since 2016 ships with an SSD; older HDD models state it explicitly.
  if (result.brand === 'APPLE' && result.storageGb != null && !result.storageType && !ambiguous.includes('storageType')) result.storageType = 'SSD';
  result.vramGb = vramOf(title, description, result);
  result.ambiguous = ambiguous;
  return result;
}

// Notebook GPUs ship with one VRAM size; chips sold with several sizes (RTX 3050, 3080, GTX 1050) stay unknown.
const laptopVram = { 'GTX 1050 TI':4, 'GTX 1060':6, 'GTX 1070':8, 'GTX 1080':8, 'GTX 1650':4, 'GTX 1650 TI':4, 'GTX 1660 TI':6, 'RTX 2050':4, 'RTX 2060':6, 'RTX 2070':8, 'RTX 2070 SUPER':8, 'RTX 2080':8, 'RTX 2080 SUPER':8, 'RTX 3050 TI':4, 'RTX 3060':6, 'RTX 3070':8, 'RTX 3070 TI':8, 'RTX 3080 TI':16, 'RTX 4050':6, 'RTX 4060':8, 'RTX 4070':8, 'RTX 4080':12, 'RTX 4090':16, 'RTX 5050':8, 'RTX 5060':8, 'RTX 5070':8, 'RTX 5070 TI':12, 'RTX 5080':16, 'RTX 5090':24 };
const vramPatterns = [
  /\b(?:rtx|gtx|rx|radeon(?:\s+pro)?|quadro|arc)[\s-]*(?:[a-z]?[\s-]*\d{3,4}[\s-]*(?:ti|super|xt|m|ada)?[\s-]*)?(\d{1,2})\s*gb\b(?!\s*(?:(?:lp)?ddr|ram|operacni|ssd|hdd|nvme|emmc))/g,
  /\b(\d{1,2})\s*gb\s*(?:g?ddr\d\w*\s*)?(?:vram|gddr\d\w*)/g,
  /\bvram\s*[:=-]?\s*(\d{1,2})\s*gb\b/g,
  /\b(?:vlastni|dedikovan\w*|graficke|video)\s+(?:pamet\w*\s*[:=-]?\s*)?(\d{1,2})\s*gb\b/g,
];
function vramOf(title, description, specs) {
  for (const text of [title, description]) {
    const sizes = [...new Set(vramPatterns.flatMap(re => [...text.matchAll(re)].map(m => +m[1])).filter(n => n >= 1 && n <= 48))];
    if (sizes.length === 1) return sizes[0];
    if (sizes.length > 1) return null;
  }
  if (!specs.gpu) return integratedChip(specs) ? 0 : null;
  if (/^MX/.test(specs.gpu)) return 2;
  // Integrated graphics (Iris Xe, Radeon Graphics, UHD) share system memory.
  return discreteGpu.test(specs.gpu) ? laptopVram[specs.gpu] ?? null : 0;
}

export const phoneBrands = [['APPLE',/\b(?:apple|iphone)\b/], ['SAMSUNG',/\b(?:samsung|galaxy)\b/], ['XIAOMI',/\b(?:xiaomi|redmi|poco)\b/], ['GOOGLE',/\b(?:google|pixel)\b/], ['HUAWEI',/\bhuawei\b/], ['HONOR',/\bhonor\b/], ['MOTOROLA',/\b(?:motorola|moto [a-z]\d*)\b/], ['NOKIA',/\bnokia\b/], ['ONEPLUS',/\bone ?plus\b/], ['OPPO',/\boppo\b/], ['REALME',/\brealme\b/], ['VIVO',/\bvivo\b/], ['SONY',/\b(?:sony|xperia)\b/], ['NOTHING',/\bnothing phone\b/], ['FAIRPHONE',/\bfairphone\b/]];
const phoneStorage = new Set([16, 32, 64, 128, 256, 512, 1000]);
function phoneParts(text) {
  const brand = [...new Set(phoneBrands.filter(([, re]) => re.test(text)).map(([b]) => b))];
  const ram = [], storage = [];
  // "8/256 GB", "12+512": memory first, then storage. "Stav 10/10" has no storage size and is skipped.
  for (const m of text.matchAll(/\b(\d{1,2})\s*(?:gb)?\s*[/+]\s*(\d{2,3}|1)\s*(gb|tb)?\b/g)) {
    const gb = sizeGb(m[2], m[3] ?? (m[2] === '1' ? 'tb' : 'gb'));
    if (+m[1] <= 24 && phoneStorage.has(gb)) { ram.push(+m[1]); storage.push(gb); }
  }
  ram.push(...[...text.matchAll(/\b(\d{1,2})\s*gb\s*(?:lp)?(?:ram|operacni)/g)].map(m => +m[1]), ...[...text.matchAll(/\b(?:ram|operacni pamet)\s*[:=-]?\s*(\d{1,2})\s*gb\b/g)].map(m => +m[1]));
  storage.push(...[...text.matchAll(/\b(?:uloziste|interni pamet|kapacita|storage)\s*[:=-]?\s*(\d{2,4}|1|2)\s*(gb|tb)\b/g)].map(m => sizeGb(m[1], m[2])));
  // A lone "128 GB" on a phone is storage; 8 or 16 GB alone could be either and stays unknown.
  for (const m of text.matchAll(/\b(\d{2,4}|1|2)\s*(gb|tb)\b(?!\s*(?:lp)?(?:ram|ddr|operacni))/g)) { const gb = sizeGb(m[1], m[2]); if (gb >= 32 && phoneStorage.has(gb)) storage.push(gb); }
  return { brand, ram: [...new Set(ram.filter(n => n >= 1 && n <= 24))], storage: [...new Set(storage)] };
}
const phoneCached = memo(key => {
  const [title, description] = key.split('\u0000').map(prepare);
  const tiers = [phoneParts(title), phoneParts(description)];
  // Title first; several values in the deciding text leave the field unknown.
  const pick = key => { for (const tier of tiers) { if (tier[key].length === 1) return tier[key][0]; if (tier[key].length > 1) return null; } return null; };
  return { kind: 'phone', brand: pick('brand'), ramGb: pick('ram'), storageGb: pick('storage') };
}, 10000);
export const extractPhone = item => ({ ...phoneCached(`${item.title ?? ''}\u0000${item.description ?? ''}`) });

// Parameters the form offers per category. Components are filtered by kind (the category) and price only.
const filterKeys = { laptops: ['brand','ramGb','storageGb','vramGb'], desktops: ['cpu','gpu','ramGb','storageGb'], phones: ['brand','ramGb','storageGb'] };
export const specsFor = (item, category) => category === 'phones' ? extractPhone(item) : category === 'laptops' || category === 'desktops' ? extractHardware(item) : null;

export function hardwareMatches(specs, filters, category) {
  const active = new Set(category ? filterKeys[category] ?? [] : ['brand','cpu','gpu','ramGb','storageGb','vramGb']);
  if (!active.size || !specs) return true;
  const unknown = () => filters.includeUnknownSpecs;
  if (active.has('brand') && filters.brand) {
    if (!specs.brand) { if (!unknown()) return false; }
    else if (canonical(specs.brand) !== canonical(filters.brand)) return false;
  }
  for (const key of ['cpu','gpu']) if (active.has(key) && filters[key]) {
    if (!specs[key]) { if (!unknown()) return false; }
    else if (!canonical(specs[key]).includes(canonical(filters[key]))) return false;
  }
  for (const [key,min] of [['ramGb',filters.minRamGb],['storageGb',filters.minStorageGb],['vramGb',filters.minVramGb]]) if (active.has(key) && min != null) {
    if (specs[key] == null) { if (!unknown()) return false; }
    else if (specs[key] < min) return false;
  }
  return true;
}

// Apple silicon has the GPU inside the chip, so "M3" already identifies the graphics.
export const integratedChip = specs => specs?.brand === 'APPLE' && /^M[1-9]/.test(specs?.cpu ?? '') && specs?.gpu == null;

export function compareHardware(wanted, found) {
  if (integratedChip(wanted) && integratedChip(found)) {
    wanted = { ...wanted, gpu: wanted.cpu }; found = { ...found, gpu: found.cpu };
  }
  const keys = ['brand','cpu','gpu','ramGb','storageGb','storageType'];
  if (keys.some(key => wanted[key] != null && found[key] != null && canonical(wanted[key]) !== canonical(found[key]))) return null;
  if (wanted.sku && found.sku && canonical(wanted.sku) === canonical(found.sku)) return 'sku';
  if (wanted.sku && found.sku && canonical(wanted.sku) !== canonical(found.sku)) return null;
  if (!wanted.model || !found.model || canonical(wanted.model) !== canonical(found.model)) return null;
  if (['brand','cpu','gpu','ramGb','storageGb','storageType'].every(key => wanted[key] != null && found[key] != null && canonical(wanted[key]) === canonical(found[key]))) return 'configuration';
  // Same model, CPU and GPU with no known conflict: an indicative price, RAM/disk may differ.
  if (['cpu','gpu'].every(key => wanted[key] != null && found[key] != null)) return 'partial';
  return null;
}
