import { normalize, memo } from './schema.js';
import { hasTerm, groupMatches, productGroups } from './vocabulary.js';
import { extractHardware, hardwareMatches } from './hardware.js';
import { classifyListing } from './defects.js';
import { regionOf } from './regions.js';

const defectTerms = ['nefunkcni','nefunkcnost','nezapina','nejde zapnout','nenabiha','nejde obraz','bez obrazu','rozbity','rozbita','rozbite','poskozeny','poskozena','poskozene','vadny','vadna','vadne','na opravu','na dily','nefunkc','broken','faulty','not working','for parts','spares or repair','does not power','cracked screen','praskly displej','praskla obrazovka','netestovan','untested'];

const textEvidence = memo(raw => {
  const text = normalize(raw);
  // Negated phrases must not turn healthy listings into damaged ones.
  const withoutNegations = text.replace(/(?:neni|nejsou|nebyl|not|never)\s+(?:nijak\s+)?(?:poskozen\w*|rozbit\w*|vadn\w*|nefunkcn\w*|broken|faulty|damaged|defective)/g, '').replace(/bez\s+(?:vad\w*|poskozeni|zavad\w*|poruch\w*)/g, '').replace(/\bne(?:poskozen|rozbit|vadn|poskraban)\w*/g, '');
  const hits = defectTerms.filter(term => withoutNegations.includes(term));
  const patterns = [
    [/\b(?:nefunguje|nefunkcnost|nebezi|nezapne|nezapina|nenabehne|nenabiji|nenabijí)\b/, 'nefunguje / nespouští se'],
    [/\b(?:zavada|zavady|porucha|poruchou|defekt|defektni)\b/, 'zmínka o závadě'],
    [/\b(?:praskl\w*|rozbit\w*|poskozen\w*)\b/, 'poškození / prasklina'],
    [/\b(?:polity|polita|polite|zality|zalita|po polit[ií]|water damaged|liquid damage)\b/, 'polití / kapalina'],
    [/\b(?:spares|defective|does not work|wont turn on|won't turn on|no power|dead motherboard|black screen)\b/, 'nefunkční / díly'],
  ];
  for (const [pattern, label] of patterns) if (pattern.test(withoutNegations)) hits.push(label);
  return hits;
}, 10000);

export function damageEvidence(item) {
  const hits = [...textEvidence(`${item.title}. ${item.description}. ${item.condition}`)];
  if (String(item.conditionId) === '7000') hits.push('eBay: stav na díly / nefunkční');
  return [...new Set(hits)];
}

// Accessories and spare parts name the device only as compatibility ("Kryt na iPhone 13", "Ovladač PS5").
const accessoryStart = '^(?:originalni |original |nova |novy |nove |nahradni |oem |pouzita |pouzity |sada |2x |\\d+x )*';
const accessories = {
  laptops: /(?:nabijeck|adapter|bateri|klavesnic|displej|panty|kryt|obal|pouzdro|dock|charger|keyboard|battery|lcd|screen|motherboard|zakladni desk)/,
  phones: /(?:kryt|obal|pouzdr|tvrzen|ochrann|sklo|folie|nabijeck|nabijec|adapter|kabel|drzak|bateri|displej|lcd|sluchatk|case|cover|charger|screen protector|powerbank|stojan|reproduktor)/,
  graphics: /(?:chladic|ventilator|backplate|riser|drzak|kabel|redukce|vodni blok|waterblock|bracket|zdroj)/,
  consoles: /(?:ovladac|ovladace|gamepad|joystick|controller|hra |hry |kabel|nabijec|nabijeck|stojan|obal|pouzdr|kryt|skin|polep|headset|sluchatk|volant|disk |hdd|ssd|chladic|ventilator)/,
};
function isAccessory(item, plan) {
  const pattern = accessories[plan.category];
  if (!pattern) return false;
  const title = normalize(item.title);
  if (new RegExp(accessoryStart + pattern.source).test(title)) return true;
  // "Průhledné pouzdro 3mk pro Google Pixel 10A": the accessory word precedes every product name and is "for" something.
  // "Prasklý displej Samsung Galaxy" (no "pro") or "Lenovo Legion, nová baterie, pro hráče" stay devices.
  const match = new RegExp(pattern.source + String.raw`\w*\b.*?\b(?:pro|for|kompatibiln\w*|na(?! dily| opravu))\b`).exec(title);
  return Boolean(match) && ![...(productGroups[plan.category] ?? []), ...brands].some(term => hasTerm(title.slice(0, match.index), term));
}
const brands = ['hp','dell','lenovo','asus','acer','msi','apple','toshiba','fujitsu','samsung','huawei','xiaomi','razer','xps','sony','google','microsoft','nvidia','amd','gigabyte','zotac','palit','sapphire','evga','pny','inno3d','gainward','asrock','powercolor'];

// "Koupím iPhone na díly" is a buyer's request, not an offer.
const wantedAd = /^(?:koupim|vykoupim|vykup|shanim|hledam|poptavam|poptavka|wanted|buying)\b/;

export function productMatches(item, plan, filters) {
  if (wantedAd.test(normalize(item.title))) return false;
  const text = `${item.title} ${item.description} ${item.condition}`;
  // A listing taken from the category itself (phone category page, eBay category) needs no generic
  // "telefon / phone" word; only the more specific groups such as a brand or model still apply.
  const generic = new Set(productGroups[plan.category] ?? []);
  const fromCategory = item.category === plan.category && plan.category !== 'all';
  if (!plan.termGroups.every(group => (fromCategory && group.every(term => generic.has(term))) || groupMatches(item, group, plan.category))) return false;
  if (!filters.includeTerms.every(term => hasTerm(text, term))) return false;
  if (plan.excludeTerms.some(term => hasTerm(text, term))) return false;
  if (isAccessory(item, plan)) return false;
  return true;
}

// A truncated snippet is not evidence that a required model/feature is absent.
// Known price/location/type exclusions remain hard filters; detail reads cannot change those fields.
export function detailCandidate(item, plan, filters) {
  if (item.detailRead || !passesFilters(item, filters) || isAccessory(item, plan)) return false;
  const text = `${item.title} ${item.description} ${item.condition}`;
  if (plan.excludeTerms.some(term => hasTerm(text, term))) return false;
  const categoryMatch = item.category === plan.category || (productGroups[plan.category] ?? []).some(term => hasTerm(text, term));
  if (!categoryMatch && !plan.termGroups.some(group => groupMatches(item, group, plan.category))) return false;
  // Spend reads on unconfirmed candidates first, instead of repeatedly inspecting already confirmed matches.
  const specs = extractHardware(item);
  const needsSpecs = (filters.model && !specs.model) || (filters.cpu && !specs.cpu) || (filters.gpu && !specs.gpu) || (filters.minRamGb != null && specs.ramGb === null) || (filters.minStorageGb != null && specs.storageGb === null);
  const needsValuation = plan.category === 'laptops' && filters.lookupNewPrices && !specs.sku && ['model','cpu','gpu','ramGb','storageGb'].some(key => specs[key] == null && !(key === 'gpu' && specs.brand === 'APPLE'));
  return !!needsSpecs || !!needsValuation || !productMatches(item, plan, filters) || (plan.damaged && !damageEvidence(item).length);
}

function passesFilters(item, filters) {
  if (!filters.includeAuctions && (item.saleType === 'auction' || item.saleType === 'unknown')) return false;
  if (filters.location && !normalize(item.location).includes(normalize(filters.location))) return false;
  if (filters.region && regionOf(item.location) !== filters.region) return false;
  const rates = { CZK: 1, USD: filters.usdRate, EUR: filters.eurRate, GBP: filters.gbpRate };
  const value = item.price !== null && rates[item.currency] ? Math.round(item.price * rates[item.currency]) : null;
  if (value === null && !filters.includeUnknownPrice) return false;
  if (value !== null && ((filters.minPrice !== null && value < filters.minPrice) || (filters.maxPrice !== null && value > filters.maxPrice))) return false;
  return true;
}

export function evaluate(item, plan, filters) {
  if (!productMatches(item, plan, filters)) return null;
  const specs = extractHardware(item);
  if (!hardwareMatches(specs, filters)) return null;
  const evidence = damageEvidence(item);
  if (plan.damaged && !evidence.length) return null;
  if (!filters.includeAuctions && (item.saleType === 'auction' || item.saleType === 'unknown')) return null;
  if (filters.location && !normalize(item.location).includes(normalize(filters.location))) return null;
  if (filters.region && regionOf(item.location) !== filters.region) return null;
  const rates = { CZK: 1, USD: filters.usdRate, EUR: filters.eurRate, GBP: filters.gbpRate };
  const rate = rates[item.currency];
  const priceCzk = item.price !== null && rate ? Math.round(item.price * rate) : null;
  if (priceCzk === null && !filters.includeUnknownPrice) return null;
  if (priceCzk !== null && ((filters.minPrice !== null && priceCzk < filters.minPrice) || (filters.maxPrice !== null && priceCzk > filters.maxPrice))) return null;
  const warnings = [];
  if (item.saleType === 'auction') warnings.push('Aktuální příhoz; konečná cena může vzrůst.');
  if (item.saleType === 'unknown') warnings.push('Typ prodeje se nepodařilo ověřit.');
  if (item.shipping === null) warnings.push('Cena dopravy není známá.');
  if (item.currency !== 'CZK') warnings.push('Přepočet používá kurz z nastavení (ČNB nebo ruční); dovozní DPH a proclení jsou jen odhad.');
  if (!item.detailRead) warnings.push('Shoda vychází z názvu a dostupného výpisu, ne z celého popisu.');
  if (evidence.some(x => /netest|untested/.test(x))) warnings.push('Netestované není potvrzení konkrétní závady.');
  if (evidence.length) warnings.push('Projev závady je tvrzení inzerátu, nikoli diagnóza.');
  const { defects, risks } = classifyListing(item);
  if (evidence.length && !defects.length) defects.push({ id:'unknown', label:'Závada neuvedena' });
  if (risks.some(r => r.level === 'block')) warnings.unshift('Možný zámek nebo blokace: kus může být použitelný jen na díly. Ověř u prodejce.');
  const reasons = ['Odpovídá hledaným výrazům'];
  if (evidence.length) reasons.push(`Zmínka o stavu: ${evidence.slice(0,3).join(', ')}`);
  if (filters.maxPrice !== null && priceCzk !== null) reasons.push('V nastaveném cenovém limitu (bez dopravy)');
  // Ranking is text relevance, never profitability or diagnostic confidence.
  const titleHits = plan.termGroups.filter(g => groupMatches({title:item.title},g,plan.category)).length;
  const score = Math.min(100, 50 + titleHits * 10 + Math.min(evidence.length,2) * 10 + (item.detailRead ? 5 : 0));
  return { ...item, specs, priceCzk, shippingCzk: item.shipping !== null && rate ? Math.round(item.shipping * rate) : null, score, evidence, defects, risks, reasons, warnings };
}
