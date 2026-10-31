import { normalize, memo } from './schema.js';

export const productGroups = {
  laptops: ['notebook', 'laptop', 'macbook', 'thinkpad', 'ideapad', 'probook', 'elitebook', 'latitude', 'zenbook', 'vivobook', 'legion', 'predator', 'nitro', 'alienware', 'victus', 'omen', 'pavilion', 'inspiron', 'vostro', 'aspire', 'swift', 'travelmate', 'lifebook', 'satellite', 'yoga', 'chromebook', 'expertbook', 'precision', 'tuf', 'rog', 'katana', 'sword', 'cyborg', 'stealth', 'raider', 'aorus', 'gigabyte aero'],
  desktops: ['pocitac', 'pc', 'desktop', 'sestava', 'computer', 'tower', 'all in one', 'imac', 'mac mini', 'mini pc'],
  ram: ['ram', 'pamet', 'ddr3', 'ddr4', 'ddr5', 'dimm', 'sodimm', 'so dimm', 'memory'],
  cpu: ['procesor', 'cpu', 'processor', 'ryzen', 'intel core', 'core i3', 'core i5', 'core i7', 'core i9', 'xeon', 'pentium', 'celeron', 'athlon'],
  gpu: ['grafick', 'graphics', 'gpu', 'geforce', 'radeon', 'rtx', 'gtx', 'quadro', 'arc a', 'arc b'],
  ssd: ['ssd', 'nvme', 'm 2'],
  psu: ['zdroj', 'psu', 'power supply'],
  mb: ['zakladni desk', 'motherboard', 'mainboard', 'deska'],
  phones: ['telefon', 'phone', 'iphone', 'smartphone', 'mobil', 'galaxy', 'pixel', 'redmi', 'poco', 'oneplus', 'xiaomi', 'motorola', 'moto g', 'nokia', 'honor', 'huawei', 'oppo', 'realme', 'vivo', 'xperia', 'nothing phone', 'fairphone', 'cat s'],
};
export const gamingTerms = ['herni', 'gaming', 'rtx', 'gtx', 'geforce', 'radeon rx', 'legion', 'rog', 'tuf', 'predator', 'nitro', 'alienware', 'victus', 'omen', 'katana', 'sword', 'cyborg', 'stealth', 'raider', 'aorus'];
const gamingFamilies = ['loq', 'zephyrus', 'clevo', 'uniwill', 'msi gf', 'msi gl', 'msi gp', 'msi ge', 'msi gs', 'msi gt', 'msi bravo', 'msi pulse', 'dell g3', 'dell g5', 'dell g15'];
productGroups.laptops.push(...gamingFamilies);
gamingTerms.push(...gamingFamilies);

// Same model written as RTX3060, RTX-3060 or RTX 3060. Token boundaries avoid ROG matching "program".
const matchTextOf = memo(value => normalize(value).replace(/([a-z])(\d)/g, '$1 $2').replace(/(\d)([a-z])/g, '$1 $2').replace(/[^a-z0-9]+/g, ' ').trim());
export const matchText = value => matchTextOf(String(value ?? ''));
// Padded haystack and its word list are reused for every term checked against the same listing.
const padded = memo(text => ` ${matchText(text)} `);
const words = memo(text => matchText(text).split(' '));
const stems = new Set(['notebook','laptop','grafick','telefon','herni','pocitac','procesor','pamet','zdroj','zakladni desk','deska']);
export function hasTerm(text, term) {
  const needle = matchText(term);
  if (!needle) return false;
  if (stems.has(needle)) return words(String(text ?? '')).some(word => word.startsWith(needle));
  return padded(String(text ?? '')).includes(` ${needle} `);
}

export function expandGroup(group, category) {
  const normalized = group.map(normalize);
  // Enrich generic product/gaming groups without broadening an explicit model or brand requirement.
  const generic = { laptops:['notebook','laptop','notebooky','laptops'], desktops:['pocitac','pc','desktop'], gpu:['grafick','graficka karta','graphics card','gpu'], phones:['telefon','mobilni telefon','phone','smartphone'] }[category] ?? [];
  if (normalized.some(t => generic.includes(t))) return [...new Set([...group, ...(productGroups[category] ?? [])])];
  if (category === 'laptops' && normalized.some(t => ['herni','gaming','herni notebook','gaming laptop'].includes(t))) return [...new Set([...group, ...gamingTerms])];
  return group;
}

export function groupMatches(item, group, category) {
  const text = `${item.title} ${item.description} ${item.condition}`;
  return expandGroup(group, category).some(term => hasTerm(text, term));
}
