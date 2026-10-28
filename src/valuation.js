import { load } from 'cheerio';
import { getPage } from './http.js';
import { normalize, parsePrice, safeUrl } from './schema.js';
import { extractHardware, compareHardware, integratedChip } from './hardware.js';

export const priceRetailers = {
  mironet: {id:'mironet',name:'Mironet',host:'www.mironet.cz',path:query => `/ProductList/showSearch?EXPF=${encodeURIComponent(query)}`,productPath:/\+dp\d+\//},
  k24: {id:'k24',name:'K24',host:'www.k24.cz',path:query => `/search/category/1?query=${encodeURIComponent(query)}`,productPath:/^\/product\/\d+\/[^/]+\.html$/},
};
// Exact SKU or full configuration gives a firm price; model + CPU + GPU at least an indicative one.
const hasPriceIdentity = specs => Boolean(specs.sku || ['model','cpu','gpu'].every(key => specs[key] != null) || (integratedChip(specs) && specs.model));
const missingFields = specs => [['model','model'],['cpu', specs.brand === 'APPLE' ? 'čip (M1–M5)' : 'CPU'],...(specs.brand === 'APPLE' ? [] : [['gpu','GPU']])].filter(([key]) => specs[key] == null).map(([,label]) => label);
const insufficient = specs => ({status:'insufficient',message:`Pro dohledání ceny chybí ${missingFields(specs).join(', ') || 'výrobní označení'}. Doplň je ve vlastní ceně nebo hledej ručně.`,searchUrl:newPriceSearchUrl(specs)});
const matchRank = {sku:0,configuration:1,partial:2};
export { calculateProfit } from '../public/pricing.js';
import { calculateProfit, calculateFromResale } from '../public/pricing.js';
import { damageEvidence } from './matching.js';

export function newPriceSearchUrl(specs, source = 'mironet') {
  const query = specs.sku || [specs.brand,specs.model].filter(Boolean).join(' ');
  const retailer = priceRetailers[source];
  return query && retailer ? `https://${retailer.host}${retailer.path(query)}` : null;
}

// Product URLs carry the product name; spend the 8 detail reads on names sharing the model, CPU or GPU
// (a "Acer Nitro" search otherwise starts with Acer Nitro monitors).
export function rankLinks(links, specs) {
  const slug = url => decodeURIComponent(new URL(url).pathname).toLowerCase().replace(/[^a-z0-9]/g, '');
  const tokens = [specs.model, specs.cpu, specs.gpu, specs.sku].filter(Boolean).flatMap(v => String(v).toLowerCase().split(/[\s-]+/)).map(t => t.replace(/[^a-z0-9]/g, '')).filter(t => t.length > 1 && !['core','ultra','ryzen','rtx','gtx','gen'].includes(t));
  // Product URLs spell out the configuration ("…_Ryzen_5_150_16GB_512GB_RTX5050"); a known CPU, GPU, RAM
  // or disk that differs from the wanted laptop cannot match, so its page is not worth a request.
  const conflicts = url => {
    const found = extractHardware({ title: decodeURIComponent(new URL(url).pathname.split('/').pop()).replace(/\.html?$/, '').replace(/_/g, ' ') });
    return ['cpu','gpu','ramGb','storageGb'].some(key => specs[key] != null && found[key] != null && normalize(String(specs[key])).replace(/[^a-z0-9]/g,'') !== normalize(String(found[key])).replace(/[^a-z0-9]/g,''));
  };
  const scored = links.filter(url => !conflicts(url)).map((url, i) => ({url, i, score: tokens.filter(t => slug(url).includes(t)).length}));
  const relevant = scored.filter(x => x.score > 0);
  return (relevant.length ? relevant : scored).sort((a,b) => b.score - a.score || a.i - b.i).map(x => x.url);
}

export function parseRetailLinks(html, base) {
  const $ = load(html);
  const retailer = Object.values(priceRetailers).find(r => r.host === new URL(base).hostname);
  if (!retailer) return [];
  return [...new Set($(retailer.id === 'mironet' ? '.nazev a[href]' : '#products-list .product-entry2 .pe2-head a[href]').map((_,a) => safeUrl($(a).attr('href'),base,[retailer.host])).get().filter(url => url && new URL(url).hostname === retailer.host && retailer.productPath.test(new URL(url).pathname)))];
}

export function parseNewProduct(html, url, now = new Date()) {
  const retailer = Object.values(priceRetailers).find(r => r.host === new URL(url).hostname);
  if (!retailer) return null;
  const $ = load(html);
  const products = [];
  let laptopCategory = false;
  const visit = value => {
    if (Array.isArray(value)) value.forEach(visit);
    else if (value && typeof value === 'object') {
      if ([value['@type']].flat().includes('Product')) products.push(value);
      if (value['@type'] === 'BreadcrumbList') laptopCategory ||= /notebook|laptop/i.test(JSON.stringify(value.itemListElement ?? []));
      if (value['@graph']) visit(value['@graph']);
    }
  };
  $('script[type="application/ld+json"]').each((_,e) => { try { visit(JSON.parse($(e).text())); } catch {} });
  // Only the primary product can supply a price, never recommendations or accessory carousels.
  if (products.length !== 1) return null;
  const product = products[0];
  const offers = [product.offers].flat().filter(Boolean);
  if (offers.length !== 1 || offers[0]['@type'] !== 'Offer') return null;
  const offer = offers[0], price = parsePrice(offer.price);
  if (offer.priceCurrency !== 'CZK' || !price || !/\/(?:InStock|LimitedAvailability)$/.test(offer.availability ?? '')) return null;
  if (offer.priceValidUntil && String(offer.priceValidUntil).slice(0,10) < now.toISOString().slice(0,10)) return null;
  const offerUrl = safeUrl(offer.url,url,[retailer.host]);
  if (!offerUrl || new URL(offerUrl).hostname !== retailer.host || new URL(offerUrl).pathname !== new URL(url).pathname) return null;
  $('script,style,nav,footer').remove();
  const body = normalize($('body').text());
  const state = body.match(/stav zbozi\s*:\s*([a-z]+)/)?.[1];
  const text = `${product.name ?? ''} ${product.description ?? ''}`;
  if ((!/\b(?:notebook|laptop)\b/i.test(text) && !laptopCategory) || /repas|rozbalen|pouzit|predvade|poskozen/i.test(normalize(text))) return null;
  // Cases, skins and chargers "pro MacBook Air 13" are not the laptop itself.
  if (/\b(?:obal|pouzdr\w*|kryt|skin|shell|case|sleeve|folie|taska|batoh|nabijec\w*|adapter|baterie|klavesnice pro|pro (?:apple )?macbook|pro notebook)\b/.test(normalize(product.name ?? ''))) return null;
  if (offer.itemCondition && !/\/NewCondition$/.test(offer.itemCondition)) return null;
  if (state && state !== 'nove') return null;
  if (!/\/NewCondition$/.test(offer.itemCondition ?? '') && state !== 'nove') return null;
  const specs = extractHardware({title:product.name, description:product.description});
  // Retailer SKU is an internal ID; the manufacturer's part number is the useful identity.
  if (typeof product.mpn === 'string' && product.mpn.trim()) specs.sku = product.mpn.trim().toUpperCase();
  return { title:product.name, url:offerUrl, priceCzk:price, source:retailer.name, sourceId:retailer.id, checkedAt:now.toISOString(), condition:'new', specs };
}

async function lookupRetailer(specs, retailer, signal, dependencies) {
  const page = dependencies.getPage ?? getPage;
  const searchUrl = newPriceSearchUrl(specs,retailer.id);
  const report = {source:retailer.id,name:retailer.name,searchUrl,checked:0,offers:[]};
  if (dependencies.blockedSources?.has(retailer.id)) return {...report,status:'unavailable',blocked:true,message:'Zdroj v tomto běhu odmítl přístup. Další požadavky jsou zastavené.'};
  try {
    const search = await page(searchUrl,signal);
    if (new URL(search.url).hostname !== retailer.host) throw new Error('Unexpected retailer redirect');
    // A unique search result redirects straight to its product detail.
    const isDetail = retailer.productPath.test(new URL(search.url).pathname);
    const direct = isDetail ? parseNewProduct(search.html,search.url) : null;
    const directMatch = direct && compareHardware(specs,direct.specs);
    if (directMatch) return {...report,checked:1,status:'matched',offers:[{...direct,match:directMatch}]};
    const links = isDetail ? [] : rankLinks(parseRetailLinks(search.html,search.url),specs).slice(0,8);
    const matches = [];
    let failures = 0;
    for (const url of links) {
      signal?.throwIfAborted();
      try {
        const detail = await page(url,signal);
        if (new URL(detail.url).hostname !== retailer.host) throw new Error('Unexpected retailer redirect');
        report.checked++;
        const product = parseNewProduct(detail.html,detail.url);
        if (!product) continue;
        const match = compareHardware(specs,product.specs);
        if (match) matches.push({...product,match});
      } catch (error) {
        if (signal?.aborted) throw error;
        if (error.code === 'blocked') return {...report,status:'unavailable',blocked:true,message:error.message,offers:matches};
        failures++;
      }
    }
    return {...report,offers:matches,status:matches.length ? 'matched' : failures ? 'unavailable' : 'not_found',message:failures ? 'Část cenových stránek se nepodařilo ověřit.' : matches.length ? 'Dostupný nový kus se shodou.' : 'V prověřených nabídkách není potvrzená shoda nového dostupného kusu.'};
  } catch (error) {
    if (signal?.aborted) throw error;
    return {...report,status:'unavailable',blocked:error.code === 'blocked',message:error.code === 'blocked' ? error.message : 'Cenový zdroj se nepodařilo načíst.'};
  }
}

// Apple's Czech store embeds its configurations in the page: the container part number names the
// family and chip (RO_MBA_M5_13_INCH…), the price key the size and chip (14inch-silver-standard-m5pro-15-16).
// Only the current generation is sold, so older chips are reported as not found.
const appleFamily = specs => specs.brand === 'APPLE' && /^MACBOOK (AIR|PRO)\b/.exec(specs.model ?? '')?.[1];
export function parseAppleStore(html, url, now = new Date()) {
  const family = /macbook-pro/.test(url) ? 'PRO' : 'AIR';
  const best = new Map();
  for (const m of html.matchAll(/"aosContainerPartNumber":"RO_(MBA|MBP)_([A-Z0-9_]+?)_(\d{2})_?INCH[^"]*"[\s\S]*?"priceKey":"([\w-]+)"/g)) {
    const key = m[4], price = Number(html.match(new RegExp(`"${key}":\\{[^}]*?"amount":([\\d.]+)`))?.[1]);
    if (!Number.isFinite(price) || price <= 0) continue;
    const size = key.match(/^(\d{2})inch/)?.[1] ?? m[3];
    const chip = (key.match(/-(m\d(?:pro|max)?)-/)?.[1] ?? m[2].match(/^M\d(?:PRO|MAX)?/)?.[0] ?? '').toUpperCase().replace(/(M\d)(PRO|MAX)/, '$1 $2');
    if (!chip) continue;
    const id = `${size}|${chip}`;
    if (!best.has(id) || best.get(id).priceCzk > price) best.set(id, { title:`MacBook ${family === 'AIR' ? 'Air' : 'Pro'} ${size}" ${chip} · nejlevnější konfigurace`, url, priceCzk:price, source:'Apple Store', sourceId:'apple', checkedAt:now.toISOString(), condition:'new',
      specs:{ brand:'APPLE', model:`MACBOOK ${family} ${size}`, cpu:chip, gpu:null, sku:null, ramGb:null, storageGb:null, storageType:'SSD', ambiguous:[] } });
  }
  return [...best.values()];
}

async function lookupApple(specs, signal, dependencies) {
  const page = dependencies.getPage ?? getPage;
  const url = `https://www.apple.com/cz/shop/buy-mac/macbook-${appleFamily(specs).toLowerCase()}`;
  const report = { source:'apple', name:'Apple Store', searchUrl:url, checked:0, offers:[] };
  try {
    const result = await page(url, signal);
    report.checked = 1;
    // "MacBook Air M4" without a size compares against every size; the cheapest (13") wins.
    const offers = parseAppleStore(result.html, result.url).map(o => ({ ...o, match: compareHardware(/\d{2}$/.test(specs.model) ? specs : { ...specs, model:o.specs.model }, o.specs) })).filter(o => o.match);
    return { ...report, offers, status: offers.length ? 'matched' : 'not_found', message: offers.length ? 'Nejlevnější konfigurace se stejnou velikostí a čipem; RAM a úložiště se mohou lišit.' : 'Apple prodává jen aktuální generaci. Starší čip už nový nekoupíš; použij bazarovou cenu.' };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { ...report, status:'unavailable', blocked:error.code === 'blocked', message:'Apple Store se nepodařilo načíst.' };
  }
}

export async function lookupNewPrice(specs, signal, dependencies = {}) {
  if (appleFamily(specs) && hasPriceIdentity(specs)) {
    const report = await lookupApple(specs, signal, dependencies);
    const offers = [...report.offers].sort((a,b) => a.priceCzk - b.priceCzk), reference = offers[0];
    return { status: reference ? 'matched' : report.status, reference, offers, reports:[report], searchLinks:[{source:'apple',name:'Apple Store',url:report.searchUrl}], searchUrl:report.searchUrl,
      range: offers.length ? { min:offers[0].priceCzk, max:offers.at(-1).priceCzk, count:offers.length } : null, blocked: Boolean(report.blocked), message: reference ? 'Použita cena nejlevnější konfigurace v Apple Store.' : report.message };
  }
  const selected = (dependencies.priceSources ?? ['mironet','k24']).map(id => priceRetailers[id]).filter(Boolean);
  const searchLinks = selected.map(r => ({source:r.id,name:r.name,url:newPriceSearchUrl(specs,r.id)}));
  if (!hasPriceIdentity(specs)) return {...insufficient(specs),searchLinks};
  const settled = await Promise.allSettled(selected.map(r => lookupRetailer(specs,r,signal,dependencies)));
  signal?.throwIfAborted();
  const reports = settled.map((result,i) => result.status === 'fulfilled' ? result.value : {source:selected[i].id,name:selected[i].name,status:'unavailable',offers:[],message:'Zdroj se nepodařilo ověřit.'});
  for (const report of reports) if (report.blocked) dependencies.blockedSources?.add(report.source);
  const offers = [...new Map(reports.flatMap(r => r.offers).map(o => [o.url,o])).values()].sort((a,b) => matchRank[a.match] - matchRank[b.match] || a.priceCzk-b.priceCzk);
  const reference = offers[0];
  // Prefer exact manufacturer IDs; compare prices only within the strongest available match class.
  const comparable = offers.filter(o => o.match === reference?.match);
  return {status:reference ? 'matched' : reports.some(r => r.status === 'unavailable') ? 'unavailable' : 'not_found',reference,offers,reports,searchLinks,searchUrl:searchLinks[0]?.url,
    range:comparable.length ? {min:Math.min(...comparable.map(o => o.priceCzk)),max:Math.max(...comparable.map(o => o.priceCzk)),count:comparable.length} : null,
    blocked:reports.length > 0 && reports.every(r => r.blocked),message:reference ? 'Použita nejnižší ověřená cena z nejsilnější dostupné shody.' : 'Cenu nového kusu se nepodařilo potvrdit. Podrobnosti najdeš u jednotlivých obchodů.'};
}

const median = values => { const s = [...values].sort((a,b) => a-b), m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2; };
const part = v => normalize(v).replace(/[^a-z0-9]/g,'');
// Exact model first; the same CPU + GPU across brands is the fallback, since performance drives used prices.
const marketLevels = [
  ['model', 'shodný model, CPU a GPU', s => s.model && s.cpu && s.gpu ? [s.model,s.cpu,s.gpu].map(part).join('|') : null],
  ['hardware', 'stejné CPU a GPU (různé modely)', s => s.cpu && s.gpu ? [s.cpu,s.gpu].map(part).join('|') : null],
  ['apple', 'shodný model a čip Apple', s => s.brand === 'APPLE' && s.model && s.cpu ? [s.model,s.cpu].map(part).join('|') : null],
  // Coarse: price class of gaming laptops follows the dedicated GPU, but CPU and age still vary.
  ['gpu', 'jen stejná dedikovaná grafika (hrubý odhad)', s => s.gpu && /^(?:RTX|GTX|RADEON RX)/.test(s.gpu) ? part(s.gpu) : null, 5],
];
export const marketFactor = 0.9;

// Used-market reference from the listings already scanned in this run: working laptops, fixed price in CZK.
// Asking prices run high, so the resale estimate is 90 % of the median.
export function marketIndex(listings, minCount = 3) {
  const groups = marketLevels.map(() => new Map());
  for (const item of listings) {
    if (item.currency !== 'CZK' || !Number.isFinite(item.price) || item.price < 1000 || item.saleType === 'auction' || damageEvidence(item).length) continue;
    const specs = extractHardware(item);
    marketLevels.forEach(([, , key], i) => {
      const k = key(specs);
      if (!k) return;
      if (!groups[i].has(k)) groups[i].set(k, []);
      groups[i].get(k).push({ title:item.title, url:item.url, priceCzk:item.price, source:item.source });
    });
  }
  return specs => {
    for (const [i, [level, label, key, levelMin = minCount]] of marketLevels.entries()) {
      const all = groups[i].get(key(specs)) ?? [];
      if (all.length < Math.max(minCount, levelMin)) continue;
      const mid = median(all.map(x => x.priceCzk));
      const kept = all.filter(x => x.priceCzk >= mid * 0.4 && x.priceCzk <= mid * 2.5);
      if (kept.length < Math.max(minCount, levelMin)) continue;
      const value = median(kept.map(x => x.priceCzk));
      return { level, label, median: value, count: kept.length, resale: Math.round(value * marketFactor), listings: kept.sort((a,b) => a.priceCzk - b.priceCzk).slice(0, 8) };
    }
    return null;
  };
}

const priceKey = (specs, filters) => JSON.stringify([specs.brand, specs.model, specs.cpu, specs.gpu, specs.sku, specs.ramGb, specs.storageGb, specs.storageType, [...(filters.priceSources ?? ['mironet','k24'])].sort()]);

export async function enrichValuations(job, signal, dependencies = {}) {
  const market = marketIndex(dependencies.marketListings ?? []);
  const lookup = dependencies.lookupNewPrice ?? lookupNewPrice;
  const cache = new Map();
  const limit = job.filters.priceLookupLimit ?? 30;
  let blocked = null;
  const blockedSources = new Set();
  for (const item of job.items) item.valuation = {status:'pending',message:'Čeká na ověření ceny nového kusu.'};
  job.valuationProgress = {lookups:0,matched:0,limit};
  for (const item of job.items) {
    signal.throwIfAborted();
    const key = JSON.stringify(item.specs);
    let value = cache.get(key);
    if (!value) {
      if (!hasPriceIdentity(item.specs)) value = {...insufficient(item.specs),searchLinks:(job.filters.priceSources ?? ['mironet','k24']).map(id => ({source:id,name:priceRetailers[id].name,url:newPriceSearchUrl(item.specs,id)}))};
      else if ((value = await dependencies.priceCache?.getPrice(priceKey(item.specs, job.filters)))) value = {...value, cached:true};
      else if (blocked) value = {...blocked,searchUrl:newPriceSearchUrl(item.specs)};
      else if (job.valuationProgress.lookups >= limit) value = {status:'limit',message:'Dosažen nastavený limit dohledávání cen.',searchUrl:newPriceSearchUrl(item.specs)};
      else {
        job.valuationProgress.lookups++;
        job.phase = `Ověřuji cenu nového notebooku · ${job.valuationProgress.lookups}/${limit}`;
        value = await lookup(item.specs,signal,{priceSources:job.filters.priceSources,blockedSources});
        if (value.blocked) blocked = value;
        // Only definite answers are reused by later searches; failures are retried next time.
        if (['matched','not_found'].includes(value.status)) await dependencies.priceCache?.setPrice(priceKey(item.specs, job.filters), value);
      }
      cache.set(key,value);
    }
    item.valuation = {...value};
    const used = market(item.specs);
    if (used) item.valuation.market = used;
    // A real used-market median beats a fixed share of the new price; the new price stays as context.
    // The coarse GPU-only median is used only when no new price is available.
    if (used && (used.level !== 'gpu' || !value.reference)) item.valuation.calculation = calculateFromResale(used.resale,item.priceCzk,job.filters.targetProfit ?? 0,`Bazarová cena · medián ${used.count} nabídek × ${String(marketFactor).replace('.',',')}`);
    else if (value.reference) item.valuation.calculation = calculateProfit(value.reference.priceCzk,item.priceCzk,job.filters.targetProfit ?? 0);
    if (item.valuation.calculation) job.valuationProgress.matched++;
  }
}
