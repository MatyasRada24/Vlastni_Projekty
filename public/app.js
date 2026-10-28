import {calculateProfit, calculateNet, importCost, mergeCosts, costLabels, validateManualPrice, withManualPrice} from './pricing.js';
const $ = selector => document.querySelector(selector);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, x => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[x]));
const money = value => new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 2 }).format(value);
const names = { bazos: 'Bazoš', aukro: 'Aukro', ebay: 'eBay' };
function readLocal(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function writeLocal(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { toast('Prohlížeč nedovolil uložení dat.'); return false; } }
let favorites = readLocal('lovec-favorites', []), searches = readLocal('lovec-searches', []);
if (!Array.isArray(favorites)) favorites = [];
if (!Array.isArray(searches)) searches = [];
let job = null, currentSource = 'all', savedView = false, config = {}, polling = null, toastTimer;
let manualPrices = readLocal('lovec-manual-prices', {});
if (!manualPrices || typeof manualPrices !== 'object' || Array.isArray(manualPrices)) manualPrices = {};
const editingPrices = new Set(), priceDrafts = new Map(), priceErrors = new Map();
let costs = mergeCosts(readLocal('lovec-costs', null));
// A price entered once applies to every listing with the same model, CPU and GPU.
const configKey = specs => specs?.model && specs?.cpu && specs?.gpu ? `cfg:${[specs.model,specs.cpu,specs.gpu].map(v => String(v).toLowerCase().replace(/[^a-z0-9]/g,'')).join('|')}` : null;
const manualFor = item => manualPrices[item.id] ?? (configKey(item.specs) ? manualPrices[configKey(item.specs)] : undefined);
const findItem = id => (job?.items ?? []).find(x => x.id === id) ?? favorites.find(x => x.id === id);
const effectiveItem = item => {
  const target = item.valuation?.calculation?.targetProfit ?? job?.filters?.targetProfit ?? 0;
  const priced = withManualPrice(item,manualFor(item),target);
  return {...priced, manualShared: !manualPrices[item.id] && Boolean(manualFor(item)), net: calculateNet(priced.valuation?.calculation?.resaleEstimate, priced, costs, target, importCost(priced, costs))};
};
const bestProfit = item => item.net?.netProfit ?? item.valuation?.calculation?.grossProfit;
const initialEmptyState = $('#results').innerHTML;
let displayedLimit = 100, lastResultsKey = '';
const moreButton = document.createElement('button');
moreButton.className = 'secondary'; moreButton.hidden = true;
$('#results').insertAdjacentElement('afterend', moreButton);
moreButton.addEventListener('click', () => { displayedLimit += 100; renderItems(); });

function toast(text) { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3500); }
function showError(text) { $('#error').textContent = text; $('#error').hidden = !text; }
async function api(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json' } });
  const data = await response.json();
  if (!response.ok) throw new Error([data.error, data.details].filter(Boolean).join(' '));
  return data;
}
const terms = id => $(id).value.split(',').map(x => x.trim()).filter(Boolean);
const price = id => $(id).value.trim() === '' ? null : Number($(id).value);
function filters() {
  return { prompt: $('#prompt').value.trim(), sources: [...document.querySelectorAll('[name=source]:checked')].map(x => x.value), category: searchCategory(), condition: $('#condition').value, minPrice: price('#min-price'), maxPrice: price('#max-price'), includeTerms: terms('#include'), excludeTerms: terms('#exclude'), location: $('#location').value.trim(), region: $('#region').value, pages: Number($('#pages').value), detailLimit: Number($('#detail-limit').value), includeAuctions: $('#auctions').checked, includeUnknownPrice: $('#unknown-price').checked, usdRate: Number($('#usd-rate').value), eurRate: Number($('#eur-rate').value), gbpRate: Number($('#gbp-rate').value), brand:$('#brand').value, cpu:$('#cpu').value.trim(), gpu:$('#gpu').value.trim(), minRamGb:price('#min-ram'), minStorageGb:price('#min-storage'), minVramGb:price('#min-vram'), includeUnknownSpecs:$('#unknown-specs').checked, lookupNewPrices:$('#lookup-prices').checked, priceLookupLimit:Number($('#price-lookup-limit').value), targetProfit:Number($('#target-profit').value), priceSources:[...document.querySelectorAll('[name=price-source]:checked')].map(x => x.value) };
}
// Components are one choice in the form; the server searches each kind as its own category.
const componentKinds = ['ram','cpu','gpu','ssd','psu','mb'];
const brandOptions = {
  laptops: [['LENOVO','Lenovo'],['HP','HP'],['DELL','Dell'],['ASUS','Asus'],['ACER','Acer'],['MSI','MSI'],['APPLE','Apple'],['GIGABYTE','Gigabyte'],['RAZER','Razer'],['SAMSUNG','Samsung'],['HUAWEI','Huawei'],['MICROSOFT','Microsoft'],['FUJITSU','Fujitsu'],['TOSHIBA','Toshiba'],['MEDION','Medion'],['XIAOMI','Xiaomi']],
  phones: [['APPLE','Apple'],['SAMSUNG','Samsung'],['XIAOMI','Xiaomi'],['GOOGLE','Google'],['HUAWEI','Huawei'],['HONOR','Honor'],['MOTOROLA','Motorola'],['NOKIA','Nokia'],['ONEPLUS','OnePlus'],['OPPO','Oppo'],['REALME','Realme'],['VIVO','Vivo'],['SONY','Sony'],['NOTHING','Nothing'],['FAIRPHONE','Fairphone']],
};
const parameterTexts = {
  laptops: ['Parametry notebooku a ocenění', 'Výrobce, RAM, SSD, VRAM a cenové zdroje'],
  desktops: ['Parametry počítače', 'RAM, procesor, grafika a SSD'],
  phones: ['Parametry telefonu', 'Výrobce, RAM a úložiště'],
};
const searchCategory = () => $('#category').value === 'components' ? $('#component').value : $('#category').value;
// Every search is a category plus an optional model; each category remembers its own model text.
const modelExamples = { laptops:'Např. Lenovo Legion 5', desktops:'Např. Dell OptiPlex 7070', phones:'Např. Pixel 9 nebo iPhone 13', ram:'Např. DDR4 3200', cpu:'Např. Ryzen 7 5800X3D', gpu:'Např. RTX 4080', ssd:'Např. Samsung 970 EVO', psu:'Např. Corsair RM750x', mb:'Např. B550' };
const categoryLabel = id => componentKinds.includes(id) ? `Komponenty · ${$('#component').querySelector(`option[value="${id}"]`)?.textContent ?? id}` : $('#category').querySelector(`option[value="${id}"]`)?.textContent ?? id;
const searchName = f => `${categoryLabel(f.category)}${f.prompt ? ` · ${f.prompt}` : ''}`;
let promptCategory = null;
const promptMemory = {};
function applyPromptMode() {
  const category = searchCategory();
  if (promptCategory !== null && category !== promptCategory) { promptMemory[promptCategory] = $('#prompt').value; $('#prompt').value = promptMemory[category] ?? ''; }
  promptCategory = category;
  $('#prompt').placeholder = `${modelExamples[category]}. Bez modelu se projde celá kategorie.`;
}
function applyCategory(brand = $('#brand').value) {
  applyPromptMode();
  const category = $('#category').value;
  document.querySelectorAll('[data-for]').forEach(el => { el.hidden = !el.dataset.for.split(' ').includes(category); });
  // Components are filtered by kind and price only, so their parameter section disappears.
  $('#parameters').hidden = category === 'components';
  const [title, hint] = parameterTexts[category] ?? parameterTexts.laptops;
  $('#parameters-title').textContent = title; $('#parameters-hint').textContent = hint;
  $('#storage-label').textContent = category === 'phones' ? 'Úložiště alespoň · GB' : 'SSD alespoň · GB';
  $('#brand').innerHTML = `<option value="">Všichni výrobci</option>${(brandOptions[category] ?? []).map(([value,label]) => `<option value="${value}">${label}</option>`).join('')}`;
  $('#brand').value = (brandOptions[category] ?? []).some(([value]) => value === brand) ? brand : '';
}
function restoreFilters(data) {
  const fields = { prompt:'prompt', condition:'condition', minPrice:'min-price', maxPrice:'max-price', location:'location', region:'region', pages:'pages', detailLimit:'detail-limit', usdRate:'usd-rate', eurRate:'eur-rate', gbpRate:'gbp-rate' };
  // Searches saved before the category rework used auto, all, graphics or consoles.
  const category = data.category === 'graphics' ? 'gpu' : data.category;
  if (componentKinds.includes(category)) { $('#category').value = 'components'; $('#component').value = category; }
  else $('#category').value = ['laptops','desktops','phones'].includes(category) ? category : 'laptops';
  applyCategory(data.brand ?? '');
  $('#detail-limit').value = data.detailLimit ?? 60;
  for (const [key,id,fallback] of [['cpu','cpu',''],['gpu','gpu',''],['minRamGb','min-ram',''],['minStorageGb','min-storage',''],['minVramGb','min-vram',''],['targetProfit','target-profit',0],['priceLookupLimit','price-lookup-limit',30]]) $(`#${id}`).value = data[key] ?? fallback;
  $('#unknown-specs').checked = data.includeUnknownSpecs ?? false;
  $('#lookup-prices').checked = data.lookupNewPrices ?? true;
  document.querySelectorAll('[name=price-source]').forEach(input => {input.checked = (data.priceSources ?? ['mironet','k24']).includes(input.value);});
  for (const [key,id] of Object.entries(fields)) if (data[key] !== undefined) $(`#${id}`).value = data[key] ?? '';
  // "Podle zadání" no longer exists; older searches were almost always for pieces to repair.
  if (data.condition === 'auto' || data.condition === undefined) $('#condition').value = 'damaged';
  for (const [key,id] of Object.entries({ includeAuctions:'auctions', includeUnknownPrice:'unknown-price' })) if (typeof data[key] === 'boolean') $(`#${id}`).checked = data[key];
  $('#include').value = (data.includeTerms ?? []).join(', '); $('#exclude').value = (data.excludeTerms ?? []).join(', ');
  if (data.sources) document.querySelectorAll('[name=source]').forEach(x => { x.checked = data.sources.includes(x.value); });
}
function visibleItems() {
  const defect = $('#defect-filter').value, hideRisky = $('#hide-risky').checked, showHidden = $('#show-hidden').checked, onlyNew = $('#only-new').checked;
  const items = (savedView ? favorites : job?.items ?? []).filter(item => currentSource === 'all' || item.source === currentSource)
    .filter(item => savedView || showHidden || !hiddenListings[item.id])
    .filter(item => !onlyNew || item.history?.isNew || item.history?.priceChange < 0)
    .filter(item => !defect || (item.defects ?? []).some(d => d.id === defect))
    .filter(item => !hideRisky || !(item.risks ?? []).some(r => r.level === 'block'))
    .map(effectiveItem);
  const sort = $('#sort').value;
  const endTime = item => Date.parse(item.endAt) > Date.now() ? Date.parse(item.endAt) : Infinity;
  if (sort === 'ending') return [...items].sort((a,b) => endTime(a) - endTime(b) || b.score - a.score);
  return [...items].sort((a,b) => sort === 'profit' ? (bestProfit(b) ?? -Infinity) - (bestProfit(a) ?? -Infinity) : sort === 'price' ? (a.priceCzk ?? Infinity) - (b.priceCzk ?? Infinity) : sort === 'price-desc' ? (b.priceCzk ?? -Infinity) - (a.priceCzk ?? -Infinity) : b.score - a.score);
}

// Aukro and eBay report an end time; Bazoš classifieds run until the seller removes them.
function endState(endAt, now = Date.now()) {
  const left = Date.parse(endAt) - now;
  if (!Number.isFinite(left)) return null;
  if (left <= 0) return { text:'Skončeno', level:'over' };
  const minutes = Math.floor(left / 60000), hours = Math.floor(minutes / 60), days = Math.floor(hours / 24);
  const text = days >= 1 ? `Končí za ${days} d ${hours % 24} h` : hours >= 1 ? `Končí za ${hours} h ${minutes % 60} min` : `Končí za ${Math.max(1, minutes)} min`;
  return { text, level: hours < 1 ? 'urgent' : hours < 24 ? 'soon' : 'later' };
}
function endHtml(endAt) {
  const state = endAt && endState(endAt);
  if (!state) return '';
  const date = new Date(endAt).toLocaleString('cs-CZ', { weekday:'short', day:'numeric', month:'numeric', hour:'2-digit', minute:'2-digit' });
  return `<span class="ends" data-end="${escapeHtml(endAt)}" data-level="${state.level}"><b>${escapeHtml(state.text)}</b><small>${escapeHtml(date)}</small></span>`;
}
setInterval(() => document.querySelectorAll('.ends[data-end]').forEach(el => {
  const state = endState(el.dataset.end);
  if (state) { el.dataset.level = state.level; el.querySelector('b').textContent = state.text; }
}), 30000);

let hiddenListings = {};
function historyHtml(item) {
  const h = item.history;
  if (!h) return '';
  if (h.priceChange < 0) return `<span class="history-tag down" title="Dříve ${money(h.previousPrice)} Kč">Zlevněno o ${money(-h.priceChange)} Kč</span>`;
  if (h.priceChange > 0) return `<span class="history-tag" title="Dříve ${money(h.previousPrice)} Kč">Zdraženo o ${money(h.priceChange)} Kč</span>`;
  if (h.isNew) return '<span class="history-tag new">Nové</span>';
  return `<span title="Poprvé viděno">od ${escapeHtml(new Date(h.firstSeen).toLocaleDateString('cs-CZ'))}</span>`;
}

function issuesHtml(item) {
  const defects = item.defects ?? [], risks = item.risks ?? [];
  if (!defects.length && !risks.length) return '';
  return `<div class="issues">${risks.map(r => `<span class="risk" data-level="${escapeHtml(r.level)}">${r.level === 'block' ? '⛔' : '⚠'} ${escapeHtml(r.label)}</span>`).join('')}${defects.map(d => `<span class="defect">${escapeHtml(d.label)}</span>`).join('')}</div>`;
}

function hardwareHtml(item) {
  if (!item.specs) return '';
  const specs = item.specs, gb = value => value == null ? null : `${value} GB`;
  const rows = specs.kind === 'phone' ? [['Výrobce',specs.brand],['RAM',gb(specs.ramGb)],['Úložiště',gb(specs.storageGb)]]
    : item.category === 'desktops' ? [['CPU',specs.cpu],['GPU',specs.gpu],['RAM',gb(specs.ramGb)],['Disk',specs.storageGb == null ? null : `${specs.storageGb} GB ${specs.storageType ?? ''}`]]
    : [['Model',specs.model || specs.sku],['CPU',specs.cpu],['GPU',specs.gpu],['VRAM',gb(specs.vramGb)],['RAM',gb(specs.ramGb)],['Disk',specs.storageGb == null ? null : `${specs.storageGb} GB ${specs.storageType ?? ''}`]];
  return `<dl class="specs">${rows.map(([label,value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value ?? 'Neznámé')}</dd></div>`).join('')}</dl>${specs.ambiguous?.length ? '<p class="price-note">Některé údaje v popisu si odporují nebo uvádějí více variant; zůstávají neznámé.</p>' : ''}`;
}

function manualFormHtml(item) {
  if (!editingPrices.has(item.id)) return '';
  const draft = priceDrafts.get(item.id) ?? manualFor(item) ?? {};
  const shared = configKey(item.specs) ? `<label class="check-label"><input name="sharedConfig" type="checkbox" ${draft.shared !== false ? 'checked' : ''}> Použít pro všechny nabídky ${escapeHtml(item.specs.model)} · ${escapeHtml(item.specs.cpu)} · ${escapeHtml(item.specs.gpu)}</label>` : '';
  return `<form class="manual-form" data-manual-form="${escapeHtml(item.id)}"><h5>Vlastní cena nového kusu</h5><p>Zadej cenu s DPH a odkaz na stejnou konfiguraci. Odkaz slouží jako tvůj podklad; aplikace ho automaticky neověřuje.</p><div class="manual-fields"><label>Cena nového · Kč<input name="newPrice" type="number" min="0.01" max="10000000" step="0.01" required value="${escapeHtml(draft.priceCzk ?? '')}" placeholder="Např. 20000"></label><label>Odkaz na nový kus<input name="referenceUrl" type="url" required maxlength="2000" placeholder="https://obchod.cz/notebook" value="${escapeHtml(draft.url ?? '')}"></label><label>Poznámka k ceně <span class="muted">volitelné</span><input name="priceNote" maxlength="180" placeholder="Např. přesné označení modelu nebo datum nabídky" value="${escapeHtml(draft.note ?? '')}"></label></div>${shared}<label class="check-label"><input name="confirmedNew" type="checkbox" required ${draft.confirmed ? 'checked' : ''}> Ověřil/a jsem, že cena patří novému kusu se shodnou konfigurací.</label><output class="manual-preview" aria-live="polite">${Number(draft.priceCzk) > 0 && item.priceCzk != null ? `Hrubý rozdíl: ${money(calculateProfit(Number(draft.priceCzk),item.priceCzk).grossProfit)} Kč` : 'Po zadání ceny se zobrazí hrubý rozdíl.'}</output><p class="manual-error" role="alert">${escapeHtml(priceErrors.get(item.id) ?? '')}</p><div class="manual-buttons"><button type="submit" class="primary">Použít vlastní cenu</button><button type="button" class="quiet-button" data-manual-close="${escapeHtml(item.id)}">Zrušit</button></div></form>`;
}

const matchLabels = { sku:'Výrobní označení', configuration:'Konfigurace', partial:'Model, CPU a GPU' };
const matchNotes = { sku:'Shodné výrobní označení', configuration:'Shoda modelu, CPU, GPU, RAM a disku', partial:'Orientační: shoda modelu, CPU a GPU. RAM a disk se mohou lišit.' };
function comparisonHtml(value) {
  const offers = value?.offers ?? [], reports = value?.reports ?? [];
  if (!offers.length && !reports.length) return '';
  return `<details class="price-details"><summary>Porovnat cenové podklady · ${offers.length} ${offers.length === 1 ? 'nabídka' : 'nabídek'}</summary>${offers.length ? `<div class="price-table-wrap"><table class="price-table"><thead><tr><th scope="col">Obchod / podklad</th><th scope="col">Cena nového</th><th scope="col">Shoda</th></tr></thead><tbody>${offers.map(offer => `<tr class="${offer.url === value.reference?.url && value.status !== 'manual' ? 'chosen' : ''}"><td><a href="${escapeHtml(offer.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(offer.source)} ↗</a><br><span class="price-note">${escapeHtml(offer.title)}</span></td><td>${money(offer.priceCzk)} Kč${offer.url === value.reference?.url && value.status !== 'manual' ? '<br><span class="price-note">Použito ve výpočtu</span>' : ''}</td><td>${matchLabels[offer.match] ?? 'Konfigurace'}<br><span class="price-note">${escapeHtml(new Date(offer.checkedAt).toLocaleString('cs-CZ'))}</span></td></tr>`).join('')}</tbody></table></div>` : ''}<div class="retailer-reports">${reports.map(report => `<div class="retailer-report" data-status="${escapeHtml(report.status)}"><strong>${escapeHtml(report.name)} · ${{matched:'shoda nalezena',not_found:'bez potvrzené shody',unavailable:'nepodařilo se ověřit'}[report.status] ?? 'čeká'}</strong>${escapeHtml(report.message ?? '')}${report.checked != null ? ` · ${report.checked} ověřených stránek` : ''}</div>`).join('')}</div><p class="price-note">Přednost má výrobní označení. Ze stejně silných shod vybíráme nejnižší cenu. Ostatní výbavu a aktuální nabídku ověř na webu obchodu.</p></details>`;
}

function valuationHtml(item) {
  const value = item.valuation, reference = value?.reference, calc = value?.calculation;
  const manual = value?.status === 'manual';
  // Heureka and Alza block automated access, so they are only offered as links the user opens.
  const query = item.specs?.sku || [item.specs?.brand, item.specs?.model].filter(Boolean).join(' ');
  const links = [...(value?.searchLinks ?? (value?.searchUrl ? [{name:'Mironet',url:value.searchUrl}] : [])),
    ...(query ? [{name:'Heurece',url:`https://www.heureka.cz/?h%5Bfraze%5D=${encodeURIComponent(query)}`},{name:'Alze',url:`https://www.alza.cz/search.htm?exps=${encodeURIComponent(query)}`}] : [])];
  const linksHtml = links.length ? `<div class="retailer-links">${links.filter(link=>link.url).map(link=>`<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer">Hledat na ${escapeHtml(link.name)} ↗</a>`).join('')}</div>` : '';
  const actions = `<div class="valuation-actions"><button type="button" class="text-button" data-manual-open="${escapeHtml(item.id)}">${manual ? 'Upravit vlastní cenu' : '+ Zadat vlastní cenu nového'}</button>${manual ? `<button type="button" class="quiet-button" data-manual-remove="${escapeHtml(item.id)}">Odstranit vlastní cenu</button>` : ''}</div>`;
  const market = value?.market;
  const marketHtml = market ? `<details class="price-details"><summary>Bazarové nabídky funkčních kusů · ${market.count}</summary><div class="price-table-wrap"><table class="price-table"><thead><tr><th scope="col">Inzerát</th><th scope="col">Cena</th></tr></thead><tbody>${market.listings.map(l => `<tr><td><a href="${escapeHtml(l.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(names[l.source] ?? l.source)} ↗</a><br><span class="price-note">${escapeHtml(l.title)}</span></td><td>${money(l.priceCzk)} Kč</td></tr>`).join('')}</tbody></table></div><p class="price-note">Medián ${money(market.median)} Kč z inzerátů prohlédnutých v tomto hledání (${escapeHtml(market.label)}, bez zmínky o závadě, pevná cena v Kč). Odhad prodeje počítá s 90 % mediánu, protože inzerované ceny bývají vyšší než prodejní.</p></details>` : '';
  if (!calc) return `<div class="valuation"><div class="valuation-top"><div><span class="valuation-kicker">Cenový podklad</span><h4>Cena nového zatím není ověřená</h4></div><span class="valuation-unknown">— Kč</span></div><p class="price-note">${escapeHtml(value?.message ?? (job?.status === 'running' ? 'Cenové porovnání proběhne po dokončení sběru nabídek.' : 'Můžeš doplnit vlastní ověřenou cenu nového kusu.'))}</p>${linksHtml}${comparisonHtml(value)}${actions}${manualFormHtml(item)}</div>`;
  const net = item.net, headline = net?.netProfit ?? calc.grossProfit;
  const costParts = net ? [...net.repairLines.map(l => `${l.label} ${money(l.czk)}`), `doprava ${money(net.shipping)}${net.shippingEstimated ? ' (odhad)' : ''}`, net.fee ? `poplatek ${money(net.fee)}` : '', net.importCzk ? `dovoz ${money(net.importCzk)}` : '', net.sellFee ? `prodej ${money(net.sellFee)}` : ''].filter(Boolean) : [];
  const costTotal = net ? net.repair + net.shipping + net.fee + net.importCzk + net.sellFee : 0;
  const usesMarket = !manual && market && calc.resaleLabel;
  const title = manual ? 'Výpočet podle tvého podkladu' : usesMarket ? 'Prodej podle bazarového trhu' : `Nový kus · ${escapeHtml(reference.source)}`;
  const note = manual ? (item.manualShared ? 'Tvoje cena pro všechny nabídky se stejným modelem, CPU a GPU' : 'Cena a shoda potvrzená tebou') : usesMarket ? `${market.label[0].toUpperCase()}${market.label.slice(1)} · ${market.count} funkčních nabídek` : matchNotes[reference.match] ?? matchNotes.configuration;
  const provenance = manual ? ['manual','Tvoje cena'] : usesMarket ? (market.level === 'gpu' ? ['manual','Bazarový trh · hrubý'] : ['','Bazarový trh']) : reference.match === 'partial' ? ['manual','Orientační cena'] : ['','Ověřeno v obchodě'];
  const referenceHtml = reference ? `<a href="${escapeHtml(reference.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(reference.source)} · ${escapeHtml(reference.title)} ↗</a><p class="price-note">${manual ? 'Zadáno tebou' : `Nový, dostupný · ${reference.match === 'partial' ? 'orientační shoda' : 'ověřeno'}`} ${escapeHtml(new Date(reference.checkedAt ?? reference.enteredAt).toLocaleString('cs-CZ'))}.</p>` : '';
  return `<div class="valuation"><div class="valuation-top"><div><span class="valuation-kicker">${net ? 'Čistý odhad po opravě' : 'Hrubý rozdíl před opravou'}</span><h4>${title}</h4><span class="price-note">${escapeHtml(note)}</span>${!manual && !usesMarket && value.range?.count > 1 && value.range.max > value.range.min ? `<span class="price-note">Rozpětí ${value.range.count} nabídek: ${money(value.range.min)} – ${money(value.range.max)} Kč</span>` : ''}</div><div class="valuation-total"><b class="${headline < 0 ? 'negative' : ''}">${headline == null ? '— Kč' : `${money(headline)} Kč`}</b><br><span class="provenance ${provenance[0]}">${provenance[1]}</span></div></div><div class="valuation-math"><div><span>Cena nového</span><strong>${reference ? `${money(reference.priceCzk)} Kč` : '—'}</strong></div><div><span>${escapeHtml(calc.resaleLabel ?? 'Odhad prodeje · 75 % nového')}</span><strong>${money(calc.resaleEstimate)} Kč</strong></div><div><span>Náklady (oprava, doprava…)</span><strong>${money(costTotal)} Kč</strong></div><div><span>Hrubý rozdíl</span><strong>${calc.grossProfit == null ? '—' : `${money(calc.grossProfit)} Kč`}</strong></div><div><span>Max. nákup pro čistý zisk ${money(calc.targetProfit)} Kč</span><strong>${money(net?.maxPurchasePrice ?? calc.maxPurchasePrice)} Kč</strong></div><span class="calculation">${money(calc.resaleEstimate)} − ${item.priceCzk == null ? '?' : money(item.priceCzk)} − ${money(costTotal)} = ${headline == null ? '?' : money(headline)} Kč${costParts.length ? `<small>Náklady: ${escapeHtml(costParts.join(' · '))} Kč. Uprav v „Připojení a náklady“.</small>` : ''}</span></div>${referenceHtml}<p class="price-note">Náklady na opravu jsou odhad podle typu závady, ne diagnóza.${item.saleType === 'auction' ? ' Počítáno z aktuálního příhozu.' : ''}</p>${marketHtml}${linksHtml}${comparisonHtml(value)}${actions}${manualFormHtml(item)}</div>`;
}
function renderItems() {
  const items = visibleItems();
  const priced = items.filter(item => bestProfit(item) != null);
  $('#stat-found').innerHTML = `${items.length} <small>nabídek</small>`;
  $('#stat-priced').innerHTML = `${priced.length} <small>oceněných</small>`;
  $('#stat-profit').textContent = priced.length ? `${money(Math.max(...priced.map(bestProfit)))} Kč` : '—';
  moreButton.hidden = items.length <= displayedLimit;
  moreButton.textContent = `Zobrazit dalších ${Math.min(100,Math.max(0,items.length-displayedLimit))} · nyní ${Math.min(items.length,displayedLimit)} z ${items.length}`;
  $('#results-title').innerHTML = `${savedView ? 'Uložené nabídky' : 'Nalezené nabídky'} <span class="count">${items.length}</span>`;
  $('#saved-count').textContent = favorites.length;
  $('#export').disabled = !items.length;
  $('#nav-search').classList.toggle('active', !savedView); $('#nav-saved').classList.toggle('active', savedView);
  if (!items.length) {
    lastResultsKey = '';
    if (!job && !savedView) { $('#results').innerHTML = initialEmptyState; return; }
    const title = savedView ? 'Zatím tu není žádná uložená nabídka.' : job?.status === 'running' ? 'Agent právě prochází nabídky.' : 'V prohlédnutém vzorku není shoda.';
    const description = savedView ? 'U nabídky klikni na „Uložit“. Oblíbené zůstanou v tomto prohlížeči.' : job?.status === 'running' ? 'Nalezené nabídky se zobrazují průběžně. Procházení můžeš kdykoliv zastavit.' : 'Zkontroluj stav zdrojů a vyhledávací plán. Zkus více stránek, obecnější zadání nebo volnější filtry.';
    const reasons = !savedView && job?.rejections?.length ? `<ul class="rejections"><li class="rejections-title">Nejčastější důvody vyřazení</li>${job.rejections.map(r => `<li><span>${escapeHtml(r.reason)}</span><b>${r.count}×</b></li>`).join('')}</ul>` : '';
    $('#results').innerHTML = `<div class="empty"><span class="empty-symbol">⌕</span><h3>${title}</h3><p>${description}</p>${reasons}</div>`;
    return;
  }
  const shown = items.slice(0,displayedLimit);
  const key = JSON.stringify([shown, favorites.map(x=>x.id),[...editingPrices],[...priceErrors]]);
  if (key === lastResultsKey) return;
  lastResultsKey = key;
  patchResults(shown.map(item => {
    const saved = favorites.some(x => x.id === item.id);
    const saleType = { auction:'Aukce · aktuální příhoz', fixed:'Kup teď', classified:'Inzerát', unknown:'Typ prodeje neověřen' }[item.saleType];
    return `<article class="listing" data-id="${escapeHtml(item.id)}">
      ${item.image ? `<img class="listing-image" loading="lazy" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}" referrerpolicy="no-referrer">` : '<div class="listing-image image-placeholder">Bez fotografie</div>'}
      <div><div class="listing-meta"><span class="source-tag">${escapeHtml(names[item.source])}</span>${historyHtml(item)}<span>·</span><span>${escapeHtml(item.location || 'Lokalita neuvedena')}</span><span>·</span><span>Textová shoda ${item.score}/100</span></div><h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3><p class="listing-desc">${escapeHtml(item.description || 'Ve výpisu není podrobný popis.')}</p>${issuesHtml(item)}${hardwareHtml(item)}<div class="reasons">${item.reasons.map(r => `<span class="reason">${escapeHtml(r)}</span>`).join('')}</div><details><summary>Co ještě ověřit (${item.warnings.length})</summary><ul>${item.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>${item.endAt ? `<p>Konec: ${escapeHtml(new Date(item.endAt).toLocaleString('cs-CZ'))}</p>` : ''}</details></div>
      <div class="listing-price"><span class="price">${item.priceCzk === null ? 'Cena neznámá' : `${item.currency !== 'CZK' ? '≈ ' : ''}${money(item.priceCzk)} Kč`}</span>${item.currency !== 'CZK' && item.price !== null ? `<span class="original-price">${money(item.price)} ${escapeHtml(item.currency)}</span>` : ''}<span class="price-note">${escapeHtml(saleType)}</span>${endHtml(item.endAt)}<span class="price-note">${item.shippingCzk === null ? 'Doprava nezjištěna' : `Doprava od ${money(item.shippingCzk)} Kč`}</span><a class="primary" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Otevřít nabídku <span>↗</span></a><div class="card-actions"><button class="bookmark ${saved ? 'saved' : ''}" data-save="${escapeHtml(item.id)}">${saved ? '★ Uloženo' : '☆ Uložit'}</button><button class="bookmark" data-hide="${escapeHtml(item.id)}">${hiddenListings[item.id] ? 'Zrušit skrytí' : 'Skrýt'}</button></div></div>
      ${valuationHtml(item)}
    </article>`;
  }), shown.map(item => item.id));
}

// Only cards whose markup changed are rebuilt; unchanged cards keep their DOM, loaded photos and open sections.
const renderedCards = new Map();
function patchResults(htmls, ids) {
  const container = $('#results');
  [...container.children].forEach(el => { if (el.tagName !== 'ARTICLE') el.remove(); });
  const existing = new Map([...container.children].map(el => [el.dataset.id, el]));
  ids.forEach((id, index) => {
    let el = existing.get(id);
    if (!el || renderedCards.get(id) !== htmls[index]) {
      const template = document.createElement('template');
      template.innerHTML = htmls[index].trim();
      const fresh = template.content.firstElementChild;
      if (el) {
        const open = new Set([...el.querySelectorAll('details[open]')].map(d => d.className));
        fresh.querySelectorAll('details').forEach(d => { if (open.has(d.className)) d.open = true; });
        el.replaceWith(fresh);
      }
      el = fresh;
      renderedCards.set(id, htmls[index]);
    }
    if (container.children[index] !== el) container.insertBefore(el, container.children[index] ?? null);
    existing.delete(id);
  });
  existing.forEach((el, id) => { el.remove(); renderedCards.delete(id); });
}
function renderJob() {
  if (!job) return;
  let updatedFavorites = false;
  favorites = favorites.map(saved => {
    const current = job.items.find(item => item.id === saved.id);
    if (saved.valuation?.status === 'pending' && current?.valuation && current.valuation.status !== 'pending') {
      updatedFavorites = true;
      return {...current,savedAt:saved.savedAt};
    }
    return saved;
  });
  if (updatedFavorites) writeLocal('lovec-favorites',favorites);
  $('#activity').hidden = false;
  $('#phase').textContent = job.phase;
  const seconds = Math.round((new Date(job.finishedAt ?? Date.now()) - new Date(job.createdAt)) / 1000);
  $('#elapsed').textContent = `${seconds} s`;
  $('#source-status').innerHTML = job.filters.sources.map(source => {
    const state = job.sources[source];
    return `<div class="source-state" data-status="${escapeHtml(state?.status || 'waiting')}"><strong>${names[source]}${state?.status === 'done' ? ' · hotovo' : ''}</strong>${escapeHtml(state?.message || 'Čeká na plán…')}${state ? `<small>${state.scanned} nabídek · ${state.pages} stránek · ${state.details}/${state.detailCandidates ?? 0} popisů${state.discoveryPages ? ` · ${state.discoveryPages} širších stránek eBay` : ""}${state.cachedPages ? ` · ${state.cachedPages} stránek z mezipaměti` : ''}</small><small>${escapeHtml(state.warnings.join(' '))}</small><a href="${escapeHtml(state.url)}" target="_blank" rel="noopener noreferrer">Otevřít zdroj ↗</a>` : ''}</div>`;
  }).join('');
  $('#plan-box').hidden = !job.plan;
  if (job.plan) {
    const p = job.plan;
    $('#plan-content').innerHTML = `<strong>${escapeHtml(categoryLabel(p.category))}</strong><p>${escapeHtml(p.explanation)}</p><p>Česky: ${escapeHtml(p.queryCs)} · eBay: ${escapeHtml(p.queryEn)}<br>Stav: ${p.damaged ? 'Hledat zmínku o poškození / netestovaném stavu' : 'Jakýkoliv'}</p><p>Skupiny výrazů (v každé stačí jeden): ${p.termGroups.map(g => `[${g.map(escapeHtml).join(' / ')}]`).join(' + ')}<br>Vyloučeno: ${escapeHtml(p.excludeTerms.join(', ') || 'nic')}</p>${p.warning ? `<p class="notice">${escapeHtml(p.warning)}</p>` : ''}`;
  }
  const scanned = Object.values(job.sources).reduce((sum, x) => sum + x.scanned, 0);
  $('#scan-summary').textContent = `${scanned} prohlédnutých nabídek · ${new Date(job.createdAt).toLocaleTimeString('cs-CZ', { hour:'2-digit', minute:'2-digit' })}`;
  const running = job.status === 'running';
  $('#activity').dataset.running = String(running);
  $('#search-button').disabled = running; $('#cancel-button').hidden = !running;
  if (!running) clearTimeout(polling);
  renderItems();
}

async function poll() {
  try { job = await api(`/api/search/${job.id}`); renderJob(); if (job.status === 'running') polling = setTimeout(poll, 1200); }
  catch (error) { showError(`Nepodařilo se získat průběh: ${error.message}`); $('#search-button').disabled = false; }
}
$('#search-form').addEventListener('submit', async event => {
  event.preventDefault(); showError('');
  const data = filters(); displayedLimit = 100;
  if (!data.sources.length) return showError('Vyber alespoň jeden web.');
  if (data.lookupNewPrices && !data.priceSources.length) { document.querySelector('.advanced').open = true; return showError('Vyber alespoň jeden obchod pro cenu nového kusu.'); }
  if (!data.priceSources.length) data.priceSources = ['mironet','k24'];
  if (data.minPrice !== null && data.maxPrice !== null && data.minPrice > data.maxPrice) return showError('Cena od nesmí být vyšší než cena do.');
  $('#search-button').disabled = true; savedView = false; currentSource = 'all';
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('active', x.dataset.source === 'all'));
  try { job = await api('/api/search', { method:'POST', body: JSON.stringify(data) }); writeLocal('lovec-active-job', job.id); writeLocal('lovec-last-filters', data); renderJob(); polling = setTimeout(poll, 800); }
  catch (error) { showError(error.message); $('#search-button').disabled = false; }
});
$('#cancel-button').addEventListener('click', async () => { if (!job) return; try { await api(`/api/search/${job.id}/cancel`, { method:'POST', body:'{}' }); toast('Zastavuji vyhledávání…'); } catch(e) { showError(e.message); } });
$('#source-tabs').addEventListener('click', event => { const tab = event.target.closest('[data-source]'); if (!tab) return; currentSource = tab.dataset.source; document.querySelectorAll('.tab').forEach(x => x.classList.toggle('active', x === tab)); renderItems(); });
$('#category').addEventListener('change', () => applyCategory());
$('#component').addEventListener('change', applyPromptMode);
$('#sort').addEventListener('change', renderItems);
$('#defect-filter').addEventListener('change', renderItems);
$('#show-hidden').addEventListener('change', renderItems);
$('#only-new').addEventListener('change', renderItems);
$('#hide-risky').addEventListener('change', renderItems);
$('#results').addEventListener('click', event => {
  const example = event.target.closest('[data-prompt]');
  if (example) {
    const kind = example.dataset.category;
    if (componentKinds.includes(kind)) { $('#category').value = 'components'; $('#component').value = kind; } else $('#category').value = kind;
    applyCategory(); $('#prompt').value = example.dataset.prompt; $('#condition').value = 'damaged'; $('#prompt').focus(); return;
  }
  const open = event.target.closest('[data-manual-open]');
  if (open) {
    const id=open.dataset.manualOpen;editingPrices.add(id);priceErrors.delete(id);
    if (!priceDrafts.has(id)) { const item = findItem(id); priceDrafts.set(id,{...(item ? manualFor(item) : manualPrices[id]), shared: item ? !manualPrices[id] : false}); }
    renderItems();document.querySelector(`[data-manual-form="${CSS.escape(id)}"] input`).focus();return;
  }
  const close = event.target.closest('[data-manual-close]');
  if (close) {editingPrices.delete(close.dataset.manualClose);priceDrafts.delete(close.dataset.manualClose);priceErrors.delete(close.dataset.manualClose);renderItems();return;}
  const remove = event.target.closest('[data-manual-remove]');
  if (remove) {
    const id=remove.dataset.manualRemove, next={...manualPrices}, key=configKey(findItem(id)?.specs);delete next[id];if (key) delete next[key];
    if (!writeLocal('lovec-manual-prices',next)) return;
    manualPrices=next;editingPrices.delete(id);priceDrafts.delete(id);priceErrors.delete(id);renderItems();toast('Vlastní cena odstraněna. Používá se dostupný automatický podklad.');return;
  }
  const hide = event.target.closest('[data-hide]');
  if (hide) {
    const id = hide.dataset.hide, item = job?.items.find(x => x.id === id) ?? favorites.find(x => x.id === id);
    api('/api/hidden', { method:'POST', body: JSON.stringify({ id, hidden: !hiddenListings[id], title: item?.title ?? '' }) })
      .then(map => { const wasHidden = Boolean(hiddenListings[id]); hiddenListings = map; lastResultsKey = ''; renderItems(); toast(wasHidden ? 'Nabídka je znovu vidět.' : 'Nabídka skryta. Najdeš ji přes „Zobrazit skryté“.'); })
      .catch(error => showError(error.message));
    return;
  }
  const button = event.target.closest('[data-save]'); if (!button) return;
  const id = button.dataset.save;
  if (favorites.some(x => x.id === id)) favorites = favorites.filter(x => x.id !== id);
  else { const item = job?.items.find(x => x.id === id); if (item) favorites.push({ ...item, savedAt: new Date().toISOString() }); }
  writeLocal('lovec-favorites', favorites); renderItems();
});
function readManualForm(form) {
  return {priceCzk:form.elements.newPrice.valueAsNumber,url:form.elements.referenceUrl.value.trim(),note:form.elements.priceNote.value.trim(),confirmed:form.elements.confirmedNew.checked,shared:Boolean(form.elements.sharedConfig?.checked)};
}
$('#results').addEventListener('input', event => {
  const form=event.target.closest('[data-manual-form]');if (!form) return;
  const id=form.dataset.manualForm, draft=readManualForm(form);priceDrafts.set(id,draft);
  const item=(savedView ? favorites : job?.items ?? []).find(item=>item.id===id);
  const calc=calculateProfit(draft.priceCzk,item?.priceCzk);
  form.querySelector('.manual-preview').textContent=calc?.grossProfit != null ? `Hrubý rozdíl: ${money(calc.grossProfit)} Kč` : 'Pro výpočet potřebujeme cenu nového i nákupní cenu.';
});
$('#results').addEventListener('submit', event => {
  const form=event.target.closest('[data-manual-form]');if (!form) return;event.preventDefault();
  const id=form.dataset.manualForm;
  try {
    const draft=readManualForm(form), entry=validateManualPrice(draft), key=draft.shared ? configKey(findItem(id)?.specs) : null;
    const next={...manualPrices};
    if (key) { next[key]=entry; delete next[id]; } else next[id]=entry;
    if (!writeLocal('lovec-manual-prices',next)) return;
    manualPrices=next;editingPrices.delete(id);priceDrafts.delete(id);priceErrors.delete(id);renderItems();toast('Tvoje cena je uložená. Výpočet, řazení i export ji používají.');
  } catch(error) {priceErrors.set(id,error.message);form.querySelector('.manual-error').textContent=error.message;}
});
$('#nav-search').addEventListener('click', () => { savedView = false; renderItems(); });
$('#nav-saved').addEventListener('click', () => { savedView = true; renderItems(); });
async function applyCnbRates() {
  const manual = !$('#use-cnb').checked;
  document.querySelectorAll('.rate-grid input[id$=-rate]').forEach(input => { input.readOnly = !manual; });
  if (manual) { $('#cnb-note').textContent = 'Používáš vlastní kurzy. Daně, clo a poplatky v nich nejsou.'; return; }
  try {
    const cnb = await api('/api/rates');
    $('#usd-rate').value = cnb.rates.USD; $('#eur-rate').value = cnb.rates.EUR; $('#gbp-rate').value = cnb.rates.GBP;
    $('#cnb-note').textContent = `Kurz ČNB ze dne ${new Date(cnb.date).toLocaleDateString('cs-CZ')}. Použije se při dalším hledání.`;
  } catch { $('#cnb-note').textContent = 'Kurz ČNB se nepodařilo načíst, používají se uložené kurzy.'; }
}
$('#use-cnb').addEventListener('change', applyCnbRates);

function renderCosts(values) {
  $('#cost-grid').innerHTML = ['repair','risk'].flatMap(group => Object.entries(values[group]).map(([key,czk]) => `<label>${escapeHtml(costLabels[key] ?? key)}<input type="number" min="0" max="1000000" step="50" data-cost-group="${group}" data-cost-key="${key}" value="${czk}"></label>`)).join('');
  $('#cost-shipping').value = values.shipping; $('#cost-fee').value = values.feePercent; $('#cost-sell-fee').value = values.sellFeePercent;
  $('#cost-import-vat').value = values.importVatPercent; $('#cost-import-fee').value = values.importHandling;
}
function readCosts() {
  const saved = { repair:{}, risk:{}, shipping:Number($('#cost-shipping').value), feePercent:Number($('#cost-fee').value), sellFeePercent:Number($('#cost-sell-fee').value), importVatPercent:Number($('#cost-import-vat').value), importHandling:Number($('#cost-import-fee').value) };
  document.querySelectorAll('[data-cost-group]').forEach(input => { if (input.value !== '') saved[input.dataset.costGroup][input.dataset.costKey] = Number(input.value); });
  return mergeCosts(saved);
}
$('#settings-button').addEventListener('click', () => { renderCosts(costs); $('#settings').showModal(); });
$('#reset-costs').addEventListener('click', () => renderCosts(mergeCosts(null)));
$('#help-button').addEventListener('click', () => $('#help').showModal());

let watchState = null, notifiedAlerts = new Set();
const timeText = iso => iso ? new Date(iso).toLocaleString('cs-CZ', { day:'numeric', month:'numeric', hour:'2-digit', minute:'2-digit' }) : '—';
function renderWatch(state) {
  watchState = state;
  const unseen = state.alerts.filter(a => !a.seen);
  $('#watch-count').hidden = !unseen.length; $('#watch-count').textContent = unseen.length;
  const c = state.config;
  $('#watch-status').textContent = !c?.enabled ? 'Hlídání je vypnuté.' : state.running ? `Právě hledám: „${searchName(c.filters)}“…` : `Hlídám „${searchName(c.filters)}“ · ${c.intervalMinutes >= 60 ? `každé ${c.intervalMinutes / 60} h` : `každých ${c.intervalMinutes} min`} · poslední běh ${timeText(state.lastRun)} · další ${timeText(state.nextRun)}${state.lastError ? ` · ${state.lastError}` : ''}`;
  if (c) { $('#watch-interval').value = c.intervalMinutes; $('#watch-min-profit').value = c.minProfit ?? ''; }
  $('#watch-stop').disabled = !c?.enabled;
  $('#watch-alerts').innerHTML = state.alerts.length ? state.alerts.map(a => `<div class="watch-alert" data-seen="${a.seen}"><a href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(a.title)} ↗</a><strong>${a.priceCzk == null ? '—' : `${money(a.priceCzk)} Kč`}</strong><small>${escapeHtml(names[a.source] ?? a.source)} · ${a.reason === 'new' ? 'nová nabídka' : `zlevněno z ${money(a.previousPrice)} Kč`}${a.grossProfit != null ? ` · hrubý rozdíl ${money(a.grossProfit)} Kč` : ''} · ${timeText(a.foundAt)}</small></div>`).join('') : '<p class="subtle">Zatím žádná upozornění.</p>';
  // Browser notifications only for alerts this page has not announced yet.
  const fresh = unseen.filter(a => !notifiedAlerts.has(`${a.id}:${a.priceCzk}`));
  fresh.forEach(a => notifiedAlerts.add(`${a.id}:${a.priceCzk}`));
  if (fresh.length && document.visibilityState !== 'visible' && 'Notification' in window && Notification.permission === 'granted') {
    new Notification(`Lovec nabídek: ${fresh.length} ${fresh.length === 1 ? 'nová nabídka' : 'nových nabídek'}`, { body: fresh.slice(0,3).map(a => a.title).join('\n'), icon:'/favicon.svg' });
  }
}
async function refreshWatch() { try { renderWatch(await api('/api/watch')); } catch {} }
async function saveWatch(enabled) {
  const data = filters();
  if (enabled && 'Notification' in window && Notification.permission === 'default') { try { await Notification.requestPermission(); } catch {} }
  const minProfit = $('#watch-min-profit').value.trim() === '' ? null : Number($('#watch-min-profit').value);
  try {
    renderWatch(await api('/api/watch', { method:'POST', body: JSON.stringify({ enabled, intervalMinutes:Number($('#watch-interval').value), minProfit, filters: enabled ? data : (watchState?.config?.filters ?? data) }) }));
    toast(enabled ? 'Hlídání je zapnuté. První kontrola proběhne po uplynutí intervalu.' : 'Hlídání je vypnuté.');
  } catch (error) { $('#watch-status').textContent = error.message; }
}
$('#watch-button').addEventListener('click', async () => { await refreshWatch(); $('#watch').showModal(); if (watchState?.alerts.some(a => !a.seen)) { try { const state = await api('/api/watch/seen', { method:'POST', body:'{}' }); watchState = state; $('#watch-count').hidden = true; } catch {} } });
$('#watch-start').addEventListener('click', () => saveWatch(true));
$('#watch-stop').addEventListener('click', () => saveWatch(false));
$('#watch-clear').addEventListener('click', async () => { try { renderWatch(await api('/api/watch/clear', { method:'POST', body:'{}' })); } catch (error) { showError(error.message); } });
setInterval(refreshWatch, 60000);
$('#save-settings').addEventListener('click', () => { { writeLocal('lovec-rates', { useCnb: $('#use-cnb').checked, usdRate: Number($('#usd-rate').value), eurRate: Number($('#eur-rate').value), gbpRate: Number($('#gbp-rate').value) }); costs = readCosts(); writeLocal('lovec-costs', costs); lastResultsKey = ''; renderItems(); toast('Náklady jsou přepočítané. Kurzy se použijí při příštím hledání.'); } });
function renderSearches() { $('#saved-searches').innerHTML = '<option value="">Vyber uložené…</option>' + searches.map((s,i) => `<option value="${i}">${escapeHtml(searchName(s))}</option>`).join(''); }
$('#save-search').addEventListener('click', () => { const data = filters(); searches = [data, ...searches.filter(s => JSON.stringify(s) !== JSON.stringify(data))].slice(0,20); writeLocal('lovec-searches', searches); renderSearches(); toast('Hledání uloženo v prohlížeči.'); });
$('#saved-searches').addEventListener('change', event => { if (event.target.value !== '') restoreFilters(searches[Number(event.target.value)]); });
$('#delete-search').addEventListener('click', () => { const index = $('#saved-searches').value; if (index === '') return; searches.splice(Number(index),1); writeLocal('lovec-searches', searches); renderSearches(); toast('Uložené hledání smazáno.'); });
$('#export').addEventListener('click', () => {
  const cell = value => { let s = String(value ?? ''); if (/^[=+\-@\t\r]/.test(s)) s = "'" + s; return `"${s.replace(/"/g,'""')}"`; };
  const rows = [['Zdroj','Název','Cena','Měna','Cena CZK orientační','Typ prodeje','Lokalita','Odkaz','Model','CPU','GPU','RAM GB','Disk GB','Cena nového CZK','Odhad prodeje CZK','Hrubý rozdíl CZK','Maximální nákup CZK','Zdroj ceny nového','Shoda ceny nového','Ověřeno nebo zadáno','Původ ceny','Všechny cenové podklady','Upozornění','Konec nabídky','Závady','Rizika','Náklady na opravu CZK','Čistý odhad CZK','Max. nákup pro čistý zisk CZK'], ...visibleItems().map(x => [names[x.source],x.title,x.price,x.currency,x.priceCzk,x.saleType,x.location,x.url,x.specs?.model,x.specs?.cpu,x.specs?.gpu,x.specs?.ramGb,x.specs?.storageGb,x.valuation?.reference?.priceCzk,x.valuation?.calculation?.resaleEstimate,x.valuation?.calculation?.grossProfit,x.valuation?.calculation?.maxPurchasePrice,x.valuation?.reference?.url,x.valuation?.reference?.match,x.valuation?.reference?.checkedAt ?? x.valuation?.reference?.enteredAt,x.valuation?.status === 'manual' ? 'Ručně zadaná' : 'Automatická',(x.valuation?.offers ?? []).map(o => `${o.source}: ${o.priceCzk} CZK (${o.url})`).join(' | '),x.warnings.join(' '),x.endAt ? new Date(x.endAt).toLocaleString('cs-CZ') : '',(x.defects ?? []).map(d => d.label).join(', '),(x.risks ?? []).map(r => r.label).join(', '),x.net?.repair,x.net?.netProfit,x.net?.maxPurchasePrice])];
  const blob = new Blob(['\uFEFF' + rows.map(row => row.map(cell).join(';')).join('\r\n')], { type:'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'lovec-nabidek.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});

try {
  config = await api('/api/config');
  applyCategory();
  $('#ebay-hint').textContent = config.ebayConfigured ? '' : 'vyžaduje klíč';
  $('#connection-status').innerHTML = `Bazoš a Aukro: veřejné stránky<br>eBay: <strong>${config.ebayConfigured ? 'klíče nastaveny (přístup se ověří při hledání)' : 'chybí API klíče'}</strong>`;
  const previous = readLocal('lovec-last-filters', null); if (previous) restoreFilters(previous.detailLimit === undefined ? { ...previous, pages: Math.max(20,previous.pages || 0), detailLimit:60 } : previous);
  const rates = readLocal('lovec-rates', null); if (rates) for (const [key,id] of Object.entries({usdRate:'usd-rate',eurRate:'eur-rate',gbpRate:'gbp-rate'})) if (rates[key]) $(`#${id}`).value = rates[key];
  $('#use-cnb').checked = rates?.useCnb ?? true;
  try { hiddenListings = await api('/api/hidden'); } catch {}
  void refreshWatch();
  void applyCnbRates();
  renderSearches(); $('#saved-count').textContent = favorites.length;
  const activeId = readLocal('lovec-active-job', null);
  if (activeId) { try { job = await api(`/api/search/${activeId}`); renderJob(); if (job.status === 'running') poll(); } catch { localStorage.removeItem('lovec-active-job'); } }
} catch (error) { showError(`Server není dostupný: ${error.message}`); }
