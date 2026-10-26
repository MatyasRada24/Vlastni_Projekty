import { normalize } from './schema.js';
import { hasTerm, groupMatches, productGroups } from './vocabulary.js';
import { extractHardware, hardwareMatches } from './hardware.js';
import { classifyListing } from './defects.js';

const defectTerms = ['nefunkcni','nefunkcnost','nezapina','nejde zapnout','nenabiha','nejde obraz','bez obrazu','rozbity','rozbita','rozbite','poskozeny','poskozena','poskozene','vadny','vadna','vadne','na opravu','na dily','nefunkc','broken','faulty','not working','for parts','spares or repair','does not power','cracked screen','praskly displej','praskla obrazovka','netestovan','untested'];

export function damageEvidence(item) {
  const text = normalize(`${item.title}. ${item.description}. ${item.condition}`);
  // Negated phrases must not turn healthy listings into damaged ones.
  const withoutNegations = text.replace(/(?:neni|nejsou|nebyl|not|never)\s+(?:nijak\s+)?(?:poskozen\w*|rozbit\w*|vadn\w*|nefunkcn\w*|broken|faulty|damaged|defective)/g, '').replace(/bez\s+(?:vad\w*|poskozeni|zavad\w*|poruch\w*)/g, '');
  const hits = defectTerms.filter(term => withoutNegations.includes(term));
  const patterns = [
    [/\b(?:nefunguje|nefunkcnost|nebezi|nezapne|nezapina|nenabehne|nenabiji|nenabijí)\b/, 'nefunguje / nespouští se'],
    [/\b(?:zavada|zavady|porucha|poruchou|defekt|defektni)\b/, 'zmínka o závadě'],
    [/\b(?:praskl\w*|rozbit\w*|poskozen\w*)\b/, 'poškození / prasklina'],
    [/\b(?:polity|polita|polite|zality|zalita|po polit[ií]|water damaged|liquid damage)\b/, 'polití / kapalina'],
    [/\b(?:spares|defective|does not work|wont turn on|won't turn on|no power|dead motherboard|black screen)\b/, 'nefunkční / díly'],
  ];
  for (const [pattern, label] of patterns) if (pattern.test(withoutNegations)) hits.push(label);
  if (String(item.conditionId) === '7000') hits.push('eBay: stav na díly / nefunkční');
  return [...new Set(hits)];
}

function isAccessory(item, plan) {
  const title = normalize(item.title);
  // Avoid accessories that mention a target model only as compatibility information.
  return plan.category === 'laptops' && /^(?:originalni |original |nova |novy |nove |nahradni |oem |pouzita )*(?:nabijeck|adapter|bateri|klavesnic|displej|panty|kryt|obal|pouzdro|dock|charger|keyboard|battery|lcd|screen|motherboard|zakladni desk)/.test(title);
}

export function productMatches(item, plan, filters) {
  const text = `${item.title} ${item.description} ${item.condition}`;
  if (!plan.termGroups.every(group => groupMatches(item, group, plan.category))) return false;
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
  const needsValuation = plan.category === 'laptops' && filters.lookupNewPrices && !specs.sku && ['model','cpu','gpu','ramGb','storageGb'].some(key => specs[key] == null);
  return !!needsSpecs || !!needsValuation || !productMatches(item, plan, filters) || (plan.damaged && !damageEvidence(item).length);
}

function passesFilters(item, filters) {
  if (!filters.includeAuctions && (item.saleType === 'auction' || item.saleType === 'unknown')) return false;
  if (filters.location && !normalize(item.location).includes(normalize(filters.location))) return false;
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
