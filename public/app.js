import {calculateProfit, validateManualPrice, withManualPrice} from './pricing.js';
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
const effectiveItem = item => withManualPrice(item,manualPrices[item.id],item.valuation?.calculation?.targetProfit ?? job?.filters?.targetProfit ?? 0);
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
  return { prompt: $('#prompt').value.trim(), sources: [...document.querySelectorAll('[name=source]:checked')].map(x => x.value), category: $('#category').value, condition: $('#condition').value, minPrice: price('#min-price'), maxPrice: price('#max-price'), includeTerms: terms('#include'), excludeTerms: terms('#exclude'), location: $('#location').value.trim(), pages: Number($('#pages').value), detailLimit: Number($('#detail-limit').value), includeAuctions: $('#auctions').checked, includeUnknownPrice: $('#unknown-price').checked, useAI: $('#use-ai').checked, usdRate: Number($('#usd-rate').value), eurRate: Number($('#eur-rate').value), gbpRate: Number($('#gbp-rate').value), model:$('#model').value.trim(), cpu:$('#cpu').value.trim(), gpu:$('#gpu').value.trim(), minRamGb:price('#min-ram'), minStorageGb:price('#min-storage'), includeUnknownSpecs:$('#unknown-specs').checked, lookupNewPrices:$('#lookup-prices').checked, priceLookupLimit:Number($('#price-lookup-limit').value), targetProfit:Number($('#target-profit').value), priceSources:[...document.querySelectorAll('[name=price-source]:checked')].map(x => x.value) };
}
function restoreFilters(data) {
  const fields = { prompt:'prompt', category:'category', condition:'condition', minPrice:'min-price', maxPrice:'max-price', location:'location', pages:'pages', detailLimit:'detail-limit', usdRate:'usd-rate', eurRate:'eur-rate', gbpRate:'gbp-rate' };
  $('#detail-limit').value = data.detailLimit ?? 60;
  for (const [key,id,fallback] of [['model','model',''],['cpu','cpu',''],['gpu','gpu',''],['minRamGb','min-ram',''],['minStorageGb','min-storage',''],['targetProfit','target-profit',0],['priceLookupLimit','price-lookup-limit',30]]) $(`#${id}`).value = data[key] ?? fallback;
  $('#unknown-specs').checked = data.includeUnknownSpecs ?? false;
  $('#lookup-prices').checked = data.lookupNewPrices ?? true;
  document.querySelectorAll('[name=price-source]').forEach(input => {input.checked = (data.priceSources ?? ['mironet','k24']).includes(input.value);});
  for (const [key,id] of Object.entries(fields)) if (data[key] !== undefined) $(`#${id}`).value = data[key] ?? '';
  for (const [key,id] of Object.entries({ includeAuctions:'auctions', includeUnknownPrice:'unknown-price', useAI:'use-ai' })) if (typeof data[key] === 'boolean') $(`#${id}`).checked = data[key];
  $('#include').value = (data.includeTerms ?? []).join(', '); $('#exclude').value = (data.excludeTerms ?? []).join(', ');
  if (data.sources) document.querySelectorAll('[name=source]').forEach(x => { x.checked = data.sources.includes(x.value); });
}
function visibleItems() {
  const items = (savedView ? favorites : job?.items ?? []).filter(item => currentSource === 'all' || item.source === currentSource).map(effectiveItem);
  const sort = $('#sort').value;
  const endTime = item => Date.parse(item.endAt) > Date.now() ? Date.parse(item.endAt) : Infinity;
  if (sort === 'ending') return [...items].sort((a,b) => endTime(a) - endTime(b) || b.score - a.score);
  return [...items].sort((a,b) => sort === 'profit' ? (b.valuation?.calculation?.grossProfit ?? -Infinity) - (a.valuation?.calculation?.grossProfit ?? -Infinity) : sort === 'price' ? (a.priceCzk ?? Infinity) - (b.priceCzk ?? Infinity) : sort === 'price-desc' ? (b.priceCzk ?? -Infinity) - (a.priceCzk ?? -Infinity) : b.score - a.score);
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

function hardwareHtml(item) {
  if (!item.specs) return '';
  const specs = item.specs;
  return `<dl class="specs">${[['Model',specs.model || specs.sku],['CPU',specs.cpu],['GPU',specs.gpu],['RAM',specs.ramGb == null ? null : `${specs.ramGb} GB`],['Disk',specs.storageGb == null ? null : `${specs.storageGb} GB ${specs.storageType ?? ''}`]].map(([label,value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value ?? 'Neznámé')}</dd></div>`).join('')}</dl>${specs.ambiguous?.length ? '<p class="price-note">Některé údaje v popisu si odporují nebo uvádějí více variant; zůstávají neznámé.</p>' : ''}`;
}

function manualFormHtml(item) {
  if (!editingPrices.has(item.id)) return '';
  const draft = priceDrafts.get(item.id) ?? manualPrices[item.id] ?? {};
  return `<form class="manual-form" data-manual-form="${escapeHtml(item.id)}"><h5>Vlastní cena nového kusu</h5><p>Zadej cenu s DPH a odkaz na stejnou konfiguraci. Odkaz slouží jako tvůj podklad; aplikace ho automaticky neověřuje.</p><div class="manual-fields"><label>Cena nového · Kč<input name="newPrice" type="number" min="0.01" max="10000000" step="0.01" required value="${escapeHtml(draft.priceCzk ?? '')}" placeholder="Např. 20000"></label><label>Odkaz na nový kus<input name="referenceUrl" type="url" required maxlength="2000" placeholder="https://obchod.cz/notebook" value="${escapeHtml(draft.url ?? '')}"></label><label>Poznámka k ceně <span class="muted">volitelné</span><input name="priceNote" maxlength="180" placeholder="Např. přesné označení modelu nebo datum nabídky" value="${escapeHtml(draft.note ?? '')}"></label></div><label class="check-label"><input name="confirmedNew" type="checkbox" required ${draft.confirmed ? 'checked' : ''}> Ověřil/a jsem, že cena patří novému kusu se shodnou konfigurací.</label><output class="manual-preview" aria-live="polite">${Number(draft.priceCzk) > 0 && item.priceCzk != null ? `Hrubý rozdíl: ${money(calculateProfit(Number(draft.priceCzk),item.priceCzk).grossProfit)} Kč` : 'Po zadání ceny se zobrazí hrubý rozdíl.'}</output><p class="manual-error" role="alert">${escapeHtml(priceErrors.get(item.id) ?? '')}</p><div class="manual-buttons"><button type="submit" class="primary">Použít vlastní cenu</button><button type="button" class="quiet-button" data-manual-close="${escapeHtml(item.id)}">Zrušit</button></div></form>`;
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
  if (!reference || !calc) return `<div class="valuation"><div class="valuation-top"><div><span class="valuation-kicker">Cenový podklad</span><h4>Cena nového zatím není ověřená</h4></div><span class="valuation-unknown">— Kč</span></div><p class="price-note">${escapeHtml(value?.message ?? (job?.status === 'running' ? 'Cenové porovnání proběhne po dokončení sběru nabídek.' : 'Můžeš doplnit vlastní ověřenou cenu nového kusu.'))}</p>${linksHtml}${comparisonHtml(value)}${actions}${manualFormHtml(item)}</div>`;
  return `<div class="valuation"><div class="valuation-top"><div><span class="valuation-kicker">Hrubý rozdíl před opravou</span><h4>${manual ? 'Výpočet podle tvého podkladu' : `Nový kus · ${escapeHtml(reference.source)}`}</h4><span class="price-note">${manual ? 'Cena a shoda potvrzená tebou' : matchNotes[reference.match] ?? matchNotes.configuration}</span>${!manual && value.range?.count > 1 && value.range.max > value.range.min ? `<span class="price-note">Rozpětí ${value.range.count} nabídek: ${money(value.range.min)} – ${money(value.range.max)} Kč</span>` : ''}</div><div class="valuation-total"><b class="${calc.grossProfit < 0 ? 'negative' : ''}">${calc.grossProfit == null ? '— Kč' : `${money(calc.grossProfit)} Kč`}</b><br><span class="provenance ${manual || reference.match === 'partial' ? 'manual' : ''}">${manual ? 'Tvoje cena' : reference.match === 'partial' ? 'Orientační cena' : 'Ověřeno v obchodě'}</span></div></div><div class="valuation-math"><div><span>Cena nového</span><strong>${money(reference.priceCzk)} Kč</strong></div><div><span>Odhad prodeje · 75 %</span><strong>${money(calc.resaleEstimate)} Kč</strong></div><div><span>Max. nákup pro rozdíl ${money(calc.targetProfit)} Kč</span><strong>${money(calc.maxPurchasePrice)} Kč</strong></div><span class="calculation">${money(reference.priceCzk)} × 0,75 − ${item.priceCzk == null ? '?' : money(item.priceCzk)} = ${calc.grossProfit == null ? '?' : money(calc.grossProfit)} Kč</span></div><a href="${escapeHtml(reference.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(reference.source)} · ${escapeHtml(reference.title)} ↗</a><p class="price-note">${manual ? 'Zadáno tebou' : 'Nový, dostupný · ověřeno'} ${escapeHtml(new Date(reference.checkedAt ?? reference.enteredAt).toLocaleString('cs-CZ'))}. Bez opravy, dopravy a poplatků.${item.saleType === 'auction' ? ' Počítáno z aktuálního příhozu.' : ''}</p>${linksHtml}${comparisonHtml(value)}${actions}${manualFormHtml(item)}</div>`;
}
function renderItems() {
  const items = visibleItems();
  const priced = items.filter(item => item.valuation?.calculation?.grossProfit != null);
  $('#stat-found').innerHTML = `${items.length} <small>nabídek</small>`;
  $('#stat-priced').innerHTML = `${priced.length} <small>oceněných</small>`;
  $('#stat-profit').textContent = priced.length ? `${money(Math.max(...priced.map(item => item.valuation.calculation.grossProfit)))} Kč` : '—';
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
    $('#results').innerHTML = `<div class="empty"><span class="empty-symbol">⌕</span><h3>${title}</h3><p>${description}</p></div>`;
    return;
  }
  const shown = items.slice(0,displayedLimit);
  const key = JSON.stringify([shown, favorites.map(x=>x.id),[...editingPrices],[...priceErrors]]);
  if (key === lastResultsKey) return;
  lastResultsKey = key;
  const expanded = new Set([...$('#results').querySelectorAll('article details[open]')].map(detail=>`${detail.closest('article').dataset.id}:${detail.className}`));
  $('#results').innerHTML = shown.map(item => {
    const saved = favorites.some(x => x.id === item.id);
    const saleType = { auction:'Aukce · aktuální příhoz', fixed:'Kup teď', classified:'Inzerát', unknown:'Typ prodeje neověřen' }[item.saleType];
    return `<article class="listing" data-id="${escapeHtml(item.id)}">
      ${item.image ? `<img class="listing-image" loading="lazy" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}" referrerpolicy="no-referrer">` : '<div class="listing-image image-placeholder">Bez fotografie</div>'}
      <div><div class="listing-meta"><span class="source-tag">${escapeHtml(names[item.source])}</span><span>·</span><span>${escapeHtml(item.location || 'Lokalita neuvedena')}</span><span>·</span><span>Textová shoda ${item.score}/100</span></div><h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h3><p class="listing-desc">${escapeHtml(item.description || 'Ve výpisu není podrobný popis.')}</p>${hardwareHtml(item)}<div class="reasons">${item.reasons.map(r => `<span class="reason">${escapeHtml(r)}</span>`).join('')}</div><details><summary>Co ještě ověřit (${item.warnings.length})</summary><ul>${item.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>${item.endAt ? `<p>Konec: ${escapeHtml(new Date(item.endAt).toLocaleString('cs-CZ'))}</p>` : ''}</details></div>
      <div class="listing-price"><span class="price">${item.priceCzk === null ? 'Cena neznámá' : `${item.currency !== 'CZK' ? '≈ ' : ''}${money(item.priceCzk)} Kč`}</span>${item.currency !== 'CZK' && item.price !== null ? `<span class="original-price">${money(item.price)} ${escapeHtml(item.currency)}</span>` : ''}<span class="price-note">${escapeHtml(saleType)}</span>${endHtml(item.endAt)}<span class="price-note">${item.shippingCzk === null ? 'Doprava nezjištěna' : `Doprava od ${money(item.shippingCzk)} Kč`}</span><a class="primary" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Otevřít nabídku <span>↗</span></a><button class="bookmark ${saved ? 'saved' : ''}" data-save="${escapeHtml(item.id)}">${saved ? '★ Uloženo' : '☆ Uložit'}</button></div>
      ${valuationHtml(item)}
    </article>`;
  }).join('');
  $('#results').querySelectorAll('article details').forEach(detail => { if (expanded.has(`${detail.closest('article').dataset.id}:${detail.className}`)) detail.open = true; });
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
    $('#plan-content').innerHTML = `<strong>${p.mode === 'ai' ? 'AI plán' : 'Lokální pravidla'} · ${escapeHtml(config.categories?.find(c => c.id === p.category)?.label || p.category)}</strong><p>${escapeHtml(p.explanation)}</p><p>Česky: ${escapeHtml(p.queryCs)} · eBay: ${escapeHtml(p.queryEn)}<br>Stav: ${p.damaged ? 'Hledat zmínku o poškození / netestovaném stavu' : 'Jakýkoliv'}</p><p>Skupiny výrazů (v každé stačí jeden): ${p.termGroups.map(g => `[${g.map(escapeHtml).join(' / ')}]`).join(' + ')}<br>Vyloučeno: ${escapeHtml(p.excludeTerms.join(', ') || 'nic')}</p>${p.warning ? `<p class="notice">${escapeHtml(p.warning)}</p>` : ''}`;
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
$('#sort').addEventListener('change', renderItems);
$('#results').addEventListener('click', event => {
  const example = event.target.closest('[data-prompt]');
  if (example) { $('#prompt').value = example.dataset.prompt; $('#prompt').focus(); return; }
  const open = event.target.closest('[data-manual-open]');
  if (open) {
    const id=open.dataset.manualOpen;editingPrices.add(id);priceErrors.delete(id);
    if (!priceDrafts.has(id)) priceDrafts.set(id,{...manualPrices[id]});
    renderItems();document.querySelector(`[data-manual-form="${CSS.escape(id)}"] input`).focus();return;
  }
  const close = event.target.closest('[data-manual-close]');
  if (close) {editingPrices.delete(close.dataset.manualClose);priceDrafts.delete(close.dataset.manualClose);priceErrors.delete(close.dataset.manualClose);renderItems();return;}
  const remove = event.target.closest('[data-manual-remove]');
  if (remove) {
    const id=remove.dataset.manualRemove, next={...manualPrices};delete next[id];
    if (!writeLocal('lovec-manual-prices',next)) return;
    manualPrices=next;editingPrices.delete(id);priceDrafts.delete(id);priceErrors.delete(id);renderItems();toast('Vlastní cena odstraněna. Používá se dostupný automatický podklad.');return;
  }
  const button = event.target.closest('[data-save]'); if (!button) return;
  const id = button.dataset.save;
  if (favorites.some(x => x.id === id)) favorites = favorites.filter(x => x.id !== id);
  else { const item = job?.items.find(x => x.id === id); if (item) favorites.push({ ...item, savedAt: new Date().toISOString() }); }
  writeLocal('lovec-favorites', favorites); renderItems();
});
function readManualForm(form) {
  return {priceCzk:form.elements.newPrice.valueAsNumber,url:form.elements.referenceUrl.value.trim(),note:form.elements.priceNote.value.trim(),confirmed:form.elements.confirmedNew.checked};
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
    const entry=validateManualPrice(readManualForm(form));
    const next={...manualPrices,[id]:entry};
    if (!writeLocal('lovec-manual-prices',next)) return;
    manualPrices=next;editingPrices.delete(id);priceDrafts.delete(id);priceErrors.delete(id);renderItems();toast('Tvoje cena je uložená. Výpočet, řazení i export ji používají.');
  } catch(error) {priceErrors.set(id,error.message);form.querySelector('.manual-error').textContent=error.message;}
});
$('#nav-search').addEventListener('click', () => { savedView = false; renderItems(); });
$('#nav-saved').addEventListener('click', () => { savedView = true; renderItems(); });
$('#settings-button').addEventListener('click', () => $('#settings').showModal());
$('#help-button').addEventListener('click', () => $('#help').showModal());
$('#settings').addEventListener('close', () => { if ($('#settings').returnValue === 'save') { writeLocal('lovec-rates', { usdRate: Number($('#usd-rate').value), eurRate: Number($('#eur-rate').value), gbpRate: Number($('#gbp-rate').value) }); toast('Kurzy se použijí při příštím hledání.'); } });
function renderSearches() { $('#saved-searches').innerHTML = '<option value="">Vyber uložené…</option>' + searches.map((s,i) => `<option value="${i}">${escapeHtml(s.prompt)}</option>`).join(''); }
$('#save-search').addEventListener('click', () => { const data = filters(); if (!data.prompt) return; searches = [data, ...searches.filter(s => JSON.stringify(s) !== JSON.stringify(data))].slice(0,20); writeLocal('lovec-searches', searches); renderSearches(); toast('Hledání uloženo v prohlížeči.'); });
$('#saved-searches').addEventListener('change', event => { if (event.target.value !== '') restoreFilters(searches[Number(event.target.value)]); });
$('#delete-search').addEventListener('click', () => { const index = $('#saved-searches').value; if (index === '') return; searches.splice(Number(index),1); writeLocal('lovec-searches', searches); renderSearches(); toast('Uložené hledání smazáno.'); });
$('#export').addEventListener('click', () => {
  const cell = value => { let s = String(value ?? ''); if (/^[=+\-@\t\r]/.test(s)) s = "'" + s; return `"${s.replace(/"/g,'""')}"`; };
  const rows = [['Zdroj','Název','Cena','Měna','Cena CZK orientační','Typ prodeje','Lokalita','Odkaz','Model','CPU','GPU','RAM GB','Disk GB','Cena nového CZK','Odhad prodeje CZK','Hrubý rozdíl CZK','Maximální nákup CZK','Zdroj ceny nového','Shoda ceny nového','Ověřeno nebo zadáno','Původ ceny','Všechny cenové podklady','Upozornění','Konec nabídky'], ...visibleItems().map(x => [names[x.source],x.title,x.price,x.currency,x.priceCzk,x.saleType,x.location,x.url,x.specs?.model,x.specs?.cpu,x.specs?.gpu,x.specs?.ramGb,x.specs?.storageGb,x.valuation?.reference?.priceCzk,x.valuation?.calculation?.resaleEstimate,x.valuation?.calculation?.grossProfit,x.valuation?.calculation?.maxPurchasePrice,x.valuation?.reference?.url,x.valuation?.reference?.match,x.valuation?.reference?.checkedAt ?? x.valuation?.reference?.enteredAt,x.valuation?.status === 'manual' ? 'Ručně zadaná' : 'Automatická',(x.valuation?.offers ?? []).map(o => `${o.source}: ${o.priceCzk} CZK (${o.url})`).join(' | '),x.warnings.join(' '),x.endAt ? new Date(x.endAt).toLocaleString('cs-CZ') : ''])];
  const blob = new Blob(['\uFEFF' + rows.map(row => row.map(cell).join(';')).join('\r\n')], { type:'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'lovec-nabidek.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});

try {
  config = await api('/api/config');
  $('#category').insertAdjacentHTML('beforeend', config.categories.map(c => `<option value="${c.id}">${escapeHtml(c.label)}</option>`).join(''));
  $('#ai-label').textContent = config.aiConfigured ? 'Použít AI plán' : 'AI plán · klíč nenastaven';
  $('#ebay-hint').textContent = config.ebayConfigured ? '' : 'vyžaduje klíč';
  $('#connection-status').innerHTML = `Bazoš a Aukro: veřejné stránky<br>AI plánování: <strong>${config.aiConfigured ? 'klíč nastaven (platnost se ověří při hledání)' : 'nenastaveno · fungují lokální pravidla'}</strong><br>eBay: <strong>${config.ebayConfigured ? 'klíče nastaveny (přístup se ověří při hledání)' : 'chybí API klíče'}</strong>`;
  const previous = readLocal('lovec-last-filters', null); if (previous) restoreFilters(previous.detailLimit === undefined ? { ...previous, pages: Math.max(20,previous.pages || 0), detailLimit:60 } : previous);
  const rates = readLocal('lovec-rates', null); if (rates) for (const [key,id] of Object.entries({usdRate:'usd-rate',eurRate:'eur-rate',gbpRate:'gbp-rate'})) if (rates[key]) $(`#${id}`).value = rates[key];
  renderSearches(); $('#saved-count').textContent = favorites.length;
  const activeId = readLocal('lovec-active-job', null);
  if (activeId) { try { job = await api(`/api/search/${activeId}`); renderJob(); if (job.status === 'running') poll(); } catch { localStorage.removeItem('lovec-active-job'); } }
} catch (error) { showError(`Server není dostupný: ${error.message}`); }
