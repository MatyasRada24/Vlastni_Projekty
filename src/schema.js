import { z } from 'zod';

export const categories = {
  laptops: { label: 'Notebooky', bazos: 'https://pc.bazos.cz/notebook/', aukro: 'https://aukro.cz/notebooky-netbooky', ebay: '175672' },
  desktops: { label: 'Stolní PC', bazos: 'https://pc.bazos.cz/pc/', aukro: 'https://aukro.cz/stolni-pocitace', ebay: '179' },
  // Components are one category in the form; each kind has its own marketplace sections.
  // "strict": the section mixes kinds (Bazoš disks with HDDs, PSUs with cases), so the listing must name the kind.
  ram: { label: 'RAM', group: 'components', bazos: 'https://pc.bazos.cz/pamet/', aukro: 'https://aukro.cz/pc-pameti', ebay: '170083' },
  cpu: { label: 'CPU', group: 'components', bazos: 'https://pc.bazos.cz/procesor/', aukro: 'https://aukro.cz/procesory', ebay: '164' },
  gpu: { label: 'GPU', group: 'components', bazos: 'https://pc.bazos.cz/graficka/', aukro: 'https://aukro.cz/pc-graficke-karty', ebay: '27386' },
  ssd: { label: 'SSD', group: 'components', strict: true, bazos: 'https://pc.bazos.cz/hdd/', aukro: 'https://aukro.cz/pc-interni-disky', ebay: '175669' },
  psu: { label: 'PSU', group: 'components', strict: true, bazos: 'https://pc.bazos.cz/case/', aukro: 'https://aukro.cz/zdroje-k-pc', ebay: '42017' },
  mb: { label: 'MB', group: 'components', bazos: 'https://pc.bazos.cz/motherboard/', aukro: 'https://aukro.cz/zakladni-desky', ebay: '1244' },
  phones: { label: 'Telefony', bazos: 'https://mobil.bazos.cz/', bazosBrands: { apple:['apple','iphone'], google:['google','pixel'], huawei:['huawei','honor'], motorola:['motorola','moto g'], nokia:['nokia'], realme:['realme'], samsung:['samsung','galaxy'], ericsson:['sony','xperia'], xiaomi:['xiaomi','redmi','poco'], mobily:['oneplus','oppo','vivo','nothing phone','fairphone'] }, aukro: 'https://aukro.cz/mobilni-telefony', ebay: '9355' },
};
// Searches saved before the category rework used auto, all, graphics or consoles.
const categoryOf = value => Object.hasOwn(categories, value) ? value : value === 'graphics' ? 'gpu' : 'laptops';

const words = z.array(z.string().trim().min(1).max(80)).max(20);
export const planSchema = z.object({
  category: z.enum(Object.keys(categories)),
  queryCs: z.string().trim().min(1).max(160),
  queryEn: z.string().trim().min(1).max(160),
  termGroups: z.array(z.array(z.string().trim().min(1).max(80)).min(1).max(80)).max(12),
  excludeTerms: words,
  damaged: z.boolean(),
  explanation: z.string().max(800),
  keywords: z.array(z.string().trim().min(1).max(80)).max(12).optional(),
}).strict();

export const searchSchema = z.object({
  prompt: z.string().trim().min(2).max(600),
  sources: z.array(z.enum(['bazos', 'aukro', 'ebay'])).min(1).max(3).transform(v => [...new Set(v)]),
  category: z.preprocess(categoryOf, z.enum(Object.keys(categories))),
  condition: z.enum(['auto', 'damaged', 'any']).default('auto'),
  minPrice: z.number().min(0).max(10000000).nullable().default(null),
  maxPrice: z.number().min(0).max(10000000).nullable().default(null),
  includeTerms: words.default([]),
  excludeTerms: words.default([]),
  location: z.string().trim().max(100).default(''),
  region: z.enum(['', 'praha','stredocesky','jihocesky','plzensky','karlovarsky','ustecky','liberecky','kralovehradecky','pardubicky','vysocina','jihomoravsky','olomoucky','zlinsky','moravskoslezsky']).default(''),
  brand: z.string().trim().max(40).default(''),
  cpu: z.string().trim().max(80).default(''),
  gpu: z.string().trim().max(80).default(''),
  minRamGb: z.number().int().min(1).max(256).nullable().default(null),
  minStorageGb: z.number().int().min(1).max(32000).nullable().default(null),
  minVramGb: z.number().int().min(1).max(48).nullable().default(null),
  includeUnknownSpecs: z.boolean().default(false),
  lookupNewPrices: z.boolean().default(true),
  priceSources: z.array(z.enum(['mironet','k24'])).min(1).max(2).transform(v => [...new Set(v)]).default(['mironet','k24']),
  priceLookupLimit: z.number().int().min(1).max(200).default(30),
  targetProfit: z.number().min(0).max(10000000).default(0),
  pages: z.number().int().min(1).max(100).default(20),
  detailLimit: z.number().int().min(0).max(500).default(60),
  includeAuctions: z.boolean().default(true),
  includeUnknownPrice: z.boolean().default(false),
  useAI: z.boolean().default(true),
  usdRate: z.number().min(1).max(1000).default(23),
  eurRate: z.number().min(1).max(1000).default(25),
  gbpRate: z.number().min(1).max(1000).default(30),
}).refine(v => v.minPrice === null || v.maxPrice === null || v.minPrice <= v.maxPrice, { message: 'Cena od nesmí být vyšší než cena do.' });

// The same listing texts are normalized many times per run (each search term, filter and detector),
// so pure text functions keep a bounded cache keyed by the input string.
export function memo(fn, max = 20000) {
  const cache = new Map();
  return key => {
    let value = cache.get(key);
    if (value === undefined) {
      if (cache.size >= max) cache.clear();
      value = fn(key);
      cache.set(key, value);
    }
    return value;
  };
}

const normalizeText = memo(text => text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().replace(/\s+/g, ' ').trim());
export const normalize = value => normalizeText(String(value ?? ''));
export const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();

export function safeUrl(value, base, hosts) {
  if (typeof value !== 'string' || !value.trim()) return null;
  try {
    const url = new URL(value, base);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    if (hosts && !hosts.some(h => url.hostname === h || url.hostname.endsWith(`.${h}`))) return null;
    return url.href;
  } catch { return null; }
}

export function parsePrice(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) && value >= 0 ? value : null;
  const match = clean(value).match(/\d[\d\s.,]*/);
  if (!match) return null;
  let digits = match[0].replace(/\s/g, '').replace(/,$/, '');
  if (/[,\.]\d{1,2}$/.test(digits)) {
    const split = Math.max(digits.lastIndexOf(','), digits.lastIndexOf('.'));
    digits = digits.slice(0, split).replace(/[.,]/g, '') + '.' + digits.slice(split + 1);
  } else digits = digits.replace(/[.,]/g, '');
  const price = Number(digits);
  return Number.isFinite(price) && price >= 0 ? price : null;
}
