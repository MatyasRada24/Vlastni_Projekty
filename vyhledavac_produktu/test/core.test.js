import test from 'node:test';
import assert from 'node:assert/strict';
import { searchSchema, parsePrice, safeUrl } from '../src/schema.js';
import { rulePlan, createPlan } from '../src/planner.js';
import { damageEvidence, evaluate, rejectionReason } from '../src/matching.js';
import { parseBazos, parseAukro, parseEbay, extractDescription } from '../src/parsers.js';
import { collectSource, searchUrl } from '../src/sources.js';
import { runAgent } from '../src/agent.js';
import { createServer } from '../server.js';

const filters = (overrides = {}) => searchSchema.parse({ prompt: 'Rozbitý herní notebook', sources: ['bazos','aukro','ebay'], ...overrides });
const listing = (overrides = {}) => ({ id:'bazos:1', source:'bazos', title:'Lenovo Legion RTX 3060 – nefunkční', description:'Nejde zapnout.', price:3500, currency:'CZK', shipping:null, condition:'', saleType:'classified', location:'Brno', detailRead:false, ...overrides });
const bazosHtml = `<div class="inzeraty"><h2 class="nadpis"><a href="/inzerat/123/lenovo.php">Lenovo Legion RTX 3060 nefunkční</a></h2><div class="popis">Nejde zapnout.</div><div class="inzeratycena">3 500 Kč</div><div class="inzeratylok">Brno</div><img class="obrazek" src="https://www.bazos.cz/img/123.jpg"></div>`;

test('Czech and international price formats, unknown price remains null', () => {
  assert.equal(parsePrice('12 500 Kč'),12500); assert.equal(parsePrice('1 299,50 Kč'),1299.5);
  assert.equal(parsePrice('$1,299.99'),1299.99); assert.equal(parsePrice('Dohodou'),null); assert.equal(parsePrice(null),null); assert.equal(parsePrice(''),null); assert.equal(parsePrice('0 Kč'),0);
});
test('Reject inverted budgets, oversized scans and invalid sources', () => {
  assert.throws(() => filters({ minPrice:100,maxPrice:50 })); assert.throws(() => filters({ pages:101 })); assert.throws(() => filters({ sources:['http://localhost'] }));
  assert.equal(filters({pages:100,detailLimit:500}).pages,100);
  assert.throws(() => filters({detailLimit:501}));
  assert.equal(filters().pages,20); assert.equal(filters().detailLimit,60);
});
test('Rule plan understands damaged gaming laptops without requiring literal notebook', () => {
  const plan = rulePlan('Rozbitý herní notebook'); assert.equal(plan.category,'laptops'); assert.equal(plan.damaged,true);
  assert.ok(evaluate(listing(),plan,filters())); assert.equal(evaluate(listing({title:'ThinkPad T480 nefunkční'}),plan,filters()),null);
});
test('Known brand and model remain required in rule-based plans', () => {
  const plan = rulePlan('Rozbitý notebook Lenovo Legion');
  assert.ok(evaluate(listing(),plan,filters())); assert.equal(evaluate(listing({title:'HP Omen RTX nefunkční'}),plan,filters()),null);
});
test('Condition comes from the filter; the model only narrows the category', async () => {
  assert.equal((await createPlan(filters({ condition:'any' }))).damaged, false);
  const legion = await createPlan(filters({ prompt:'Legion 5', condition:'damaged' }));
  assert.equal(legion.damaged, true); assert.deepEqual(legion.keywords, ['legion 5']);
  const all = await createPlan(filters({ prompt:'', condition:'any' }));
  assert.deepEqual(all.keywords, []); assert.equal(all.queryCs, 'notebook');
  // Every category accepts an empty model.
  for (const category of ['laptops','desktops','phones','gpu']) assert.equal(searchSchema.parse({ prompt:'', sources:['bazos'], category }).prompt, '');
});
test('Healthy listings with negated damage are excluded', () => {
  assert.equal(damageEvidence(listing({title:'Notebook Lenovo Legion',description:'Není poškozený. Bez vad. Not broken.'})).length,0);
});
test('Budget, currency conversion and unknown price are handled independently', () => {
  const plan = rulePlan('rozbitý herní notebook');
  assert.equal(evaluate(listing({price:300,currency:'USD'}),plan,filters({maxPrice:6000,usdRate:23})),null);
  assert.equal(evaluate(listing({price:null}),plan,filters()),null);
  assert.equal(evaluate(listing({price:null}),plan,filters({includeUnknownPrice:true})).priceCzk,null);
  assert.equal(evaluate(listing({price:100,currency:'EUR'}),plan,filters({eurRate:25})).priceCzk,2500);
});
test('Excluded phrases, required terms and location obey explicit filters', async () => {
  const f = filters({ excludeTerms:['politý'],includeTerms:['RTX'],location:'Brno' }); const p = await createPlan(f,{env:{}});
  assert.ok(evaluate(listing(),p,f)); assert.equal(evaluate(listing({description:'Politý, nejde zapnout'}),p,f),null); assert.equal(evaluate(listing({location:'Praha'}),p,f),null);
});
test('A hand-picked category rebuilds the search terms and keeps only that kind of goods', async () => {
  for (const [category, cs] of [['phones','telefon'],['gpu','grafická karta'],['desktops','počítač'],['psu','zdroj']]) {
    const plan = await createPlan(searchSchema.parse({ prompt:'Rozbitý herní notebook', sources:['bazos'], category, useAI:false }), { env:{} });
    assert.equal(plan.category, category); assert.equal(plan.queryCs, cs); assert.equal(plan.damaged, true);
    assert.ok(!plan.termGroups.flat().includes('notebook'));
  }
  // Searches saved before the rework keep working.
  assert.equal(searchSchema.parse({ prompt:'x1', sources:['bazos'], category:'graphics' }).category, 'gpu');
  assert.equal(searchSchema.parse({ prompt:'x1', sources:['bazos'], category:'auto' }).category, 'laptops');
  const f = searchSchema.parse({ prompt:'telefon', sources:['bazos'], category:'phones', condition:'any', maxPrice:null });
  const p = await createPlan(f, { env:{} });
  const phone = title => ({ id:'bazos:9', source:'bazos', category:'phones', title, description:'', price:1500, currency:'CZK', shipping:null, location:'Brno', condition:'', saleType:'classified' });
  assert.ok(evaluate(phone('Motorola Moto G54 128GB'), p, f));
  assert.equal(evaluate(phone('Kryt na iPhone 13 Pro'), p, f), null);
  assert.equal(evaluate(phone('KOUPÍM iPHONE A SAMSUNG – NA DÍLY'), p, f), null);
  // Bazoš puts disks and HDDs together, cases and PSUs together: the listing has to name the kind.
  const ssd = await createPlan(searchSchema.parse({ prompt:'ssd', sources:['bazos'], category:'ssd', condition:'any' }), { env:{} });
  const part = (title, category) => ({ ...phone(title), category });
  assert.ok(evaluate(part('Samsung 970 EVO Plus 1TB NVMe', 'ssd'), ssd, f));
  assert.equal(evaluate(part('WD Blue 2TB 3,5"', 'ssd'), ssd, f), null);
  const psu = await createPlan(searchSchema.parse({ prompt:'zdroj', sources:['bazos'], category:'psu', condition:'any' }), { env:{} });
  assert.ok(evaluate(part('Zdroj Corsair RM750x', 'psu'), psu, f));
  assert.equal(evaluate(part('Skříň Fractal Design Define 7', 'psu'), psu, f), null);
  assert.equal(searchUrl('bazos', ssd), 'https://pc.bazos.cz/hdd/');
  assert.ok(!searchUrl('ebay', ssd).includes('_nkw=ssd'), 'a component category needs no generic keyword');
});
test('Components search the chosen kind; an optional model narrows it', async () => {
  const gpu = title => ({ id:'bazos:5', source:'bazos', category:'gpu', title, description:'', price:9000, currency:'CZK', shipping:null, location:'Brno', condition:'', saleType:'classified' });
  const all = searchSchema.parse({ prompt:'', sources:['bazos','aukro','ebay'], category:'gpu', maxPrice:null });
  const plan = await createPlan(all, { env:{ OPENAI_API_KEY:'x' }, fetchFn: async () => { throw new Error('AI must not be asked'); } });
  assert.equal(plan.damaged, false); assert.deepEqual(plan.keywords, []); assert.equal(plan.warning, null);
  assert.ok(evaluate(gpu('Gigabyte Radeon RX 6600 8GB'), plan, all));
  assert.equal(searchUrl('aukro', plan), 'https://aukro.cz/pc-graficke-karty');
  const f = searchSchema.parse({ prompt:'RTX 4080', sources:['bazos','aukro','ebay'], category:'gpu', maxPrice:null });
  const model = await createPlan(f, { env:{} });
  assert.deepEqual(model.keywords, ['rtx 4080']);
  assert.equal(searchUrl('aukro', model), 'https://aukro.cz/pc-graficke-karty?text=rtx+4080');
  assert.ok(evaluate(gpu('MSI GeForce RTX4080 Gaming X Trio 16G'), model, f));
  assert.ok(evaluate(gpu('Gigabyte RTX 4080 SUPER Windforce'), model, f));
  assert.equal(evaluate(gpu('ASUS RTX 4070 Ti, vyměním za 4080'), model, f), null);
  // Aukro's text search also returns whole computers with that GPU.
  assert.equal(evaluate(gpu('MSI Vector 16 HX A14VHG i7-14700HX 16GB 1TB SSD RTX 4080'), model, f), null);
  assert.equal(evaluate(gpu('[nové] Herní PC: Core i7/ 32GB/ RTX 4080/ SSD 2TB'), model, f), null);
  assert.ok(evaluate(gpu('RTX 4080 16GB GDDR6X Founders Edition'), model, f));
  assert.equal(evaluate(gpu('Colorful iGame RTX 4080 Ultra W OC GPU Heatsink 7 Heatpipe 3Fan'), model, f), null);
  assert.equal(evaluate(gpu('NEW 3x8 8 to 12+4 Graphics Power Cable Connector for NVIDI RTX 4080'), model, f), null);
  // A model may contain words that name other categories.
  const board = await createPlan(searchSchema.parse({ prompt:'ASUS ROG Strix B550-F', sources:['bazos'], category:'mb' }), { env:{} });
  assert.ok(board.keywords.includes('rog'));
});
test('Required terms are searched for, not just filtered', async () => {
  const f = searchSchema.parse({ prompt:'Rozbitý herní notebook', sources:['bazos','aukro','ebay'], category:'phones', includeTerms:['Google pixel 10a'], condition:'any', maxPrice:null });
  const plan = await createPlan(f, { env:{} });
  assert.equal(plan.category, 'phones'); assert.deepEqual(plan.keywords, ['Google pixel 10a']);
  assert.equal(searchUrl('bazos', plan, 2), 'https://mobil.bazos.cz/google/20/');
  assert.equal(searchUrl('aukro', plan), 'https://aukro.cz/mobilni-telefony?text=Google+pixel+10a');
  assert.ok(searchUrl('ebay', plan).includes('_nkw=Google+pixel+10a'));
  const phone = title => ({ id:'aukro:1', source:'aukro', category:'phones', title, description:'', price:9000, currency:'CZK', shipping:null, location:'Praha', condition:'', saleType:'classified' });
  assert.ok(evaluate(phone('Google Pixel 10a 128 GB Lavender nový'), plan, f));
  assert.equal(evaluate(phone('Průhledné pouzdro 3mk Clear pro Google Pixel 10A'), plan, f), null);
  assert.equal(evaluate(phone('Tech-Protect FlexAir Hybrid MagSafe pouzdro na Google Pixel 10A'), plan, f), null);
  assert.deepEqual(damageEvidence({ title:'Google Pixel 10a', description:'Prodám nepoškozený/jako nový Pixel 10a', condition:'' }), []);
  // "Pixel 9" is one model name, so the model code G9S9B of a Pixel 6 does not count as a 9.
  const f9 = searchSchema.parse({ prompt:'Google Pixel 9', sources:['ebay'], category:'phones', maxPrice:null, minVramGb:8, cpu:'i7' });
  const nine = await createPlan(f9, { env:{} });
  assert.deepEqual(nine.keywords, ['google', 'pixel 9']);
  assert.ok(evaluate(phone('Google Pixel 9a 128GB Iris'), nine, f9), 'notebook and PC filters must not apply to phones');
  assert.equal(evaluate(phone('Google Pixel 6 G9S9B 128 GB Black'), nine, f9), null);
  assert.match(rejectionReason(phone('Google Pixel 9 Pro'), nine, { ...f9, maxPrice:6000 }), /^Dražší než limit 6\s000 Kč$/);
  assert.equal(rejectionReason(phone('Google Pixel 9 Pro'), plan, f), 'Chybí povinný výraz „Google pixel 10a“');
  // A notebook prompt may name its GPU; brand-less browsing is unchanged.
  const rtx = await createPlan(searchSchema.parse({ prompt:'Rozbitý notebook Legion RTX 3060', sources:['bazos'], category:'laptops' }), { env:{} });
  assert.deepEqual(rtx.keywords, ['legion', 'rtx 3060']);
  assert.equal(searchUrl('bazos', await createPlan(searchSchema.parse({ prompt:'telefon', sources:['bazos'], category:'phones' }), { env:{} })), 'https://mobil.bazos.cz/');
});

test('Region filter uses the postcode district, with city names as fallback', async () => {
  const { regionOf } = await import('../src/regions.js');
  assert.equal(regionOf('Brno 602 00'), 'jihomoravsky');
  assert.equal(regionOf('Zličín 15521'), 'praha');
  assert.equal(regionOf('Třebíč 674 01'), 'vysocina');
  assert.equal(regionOf('Uherské Hradiště 686 01'), 'zlinsky');
  assert.equal(regionOf('Ostrava'), 'moravskoslezsky');
  assert.equal(regionOf('Austin, US'), null);
});

test('Auction and unknown sale types cannot pass fixed-only filter', () => {
  for (const saleType of ['auction','unknown']) assert.equal(evaluate(listing({saleType}),rulePlan('notebook'),filters({includeAuctions:false})),null);
});
test('Laptop accessories mentioning gaming models are excluded', () => {
  assert.equal(evaluate(listing({title:'Náhradní baterie Lenovo Legion RTX nefunkční'}),rulePlan('rozbitý herní notebook'),filters()),null);
});
test('Bazos parses independent listings without collecting contact details', () => {
  const parsed = parseBazos(bazosHtml,'https://pc.bazos.cz/notebook/'); assert.equal(parsed.items.length,1); assert.equal(parsed.items[0].price,3500); assert.equal(parsed.items[0].id,'bazos:123'); assert.equal(parsed.items[0].saleType,'classified');
  assert.equal(parseBazos('<html>unexpected website</html>','https://pc.bazos.cz/notebook/').recognized,false);
});
test('Aukro reads main results only, current bid, location and shipping', () => {
  const row = {itemId:456,itemName:'Lenovo Legion nefunkční',seoUrl:'lenovo',price:{amount:500,currency:'CZK'},priceWithShipping:{amount:569,currency:'CZK'},auction:true,itemState:'ACTIVE',location:'Praha',attributes:[{attributeName:'Stav zboží',attributeValue:'Poškozené'}]};
  const state = {aukCache:{'POST /offers/searchItemsCommon':{b:{content:[row]}}}};
  const html = `<script id="ng-state" type="application/json">${JSON.stringify(state)}</script>`;
  const result = parseAukro(html,'https://aukro.cz/notebooky-netbooky'); assert.equal(result.items.length,1); assert.equal(result.items[0].saleType,'auction'); assert.equal(result.items[0].shipping,69); assert.equal(result.items[0].condition,'Poškozené');
});
test('Aukro fallback offers from other categories are dropped', async () => {
  const row = (itemId, itemName, path) => ({ itemId, itemName, seoUrl:`x${itemId}`, price:{amount:300,currency:'CZK'}, auction:false, itemState:'ACTIVE', categoryPath:path.map(seoUrl => ({ seoUrl })) });
  const state = { aukCache:{ 'POST /offers/searchItemsCommon':{ b:{ content:[
    row(1, 'Pouzdro pro Google Pixel 10A', ['mobily-a-gps','obaly-pouzdra-kapsy-pro-mobily-a-gps']),
    row(2, 'MSI RTX 3060 Ventus', ['pocitace-a-hry','pc-komponenty','pc-graficke-karty']),
  ] } } } };
  const html = `<script id="ng-state" type="application/json">${JSON.stringify(state)}</script>`;
  const f = searchSchema.parse({ prompt:'', sources:['aukro'], category:'gpu', pages:1, detailLimit:0, maxPrice:null });
  const plan = await createPlan(f, { env:{} });
  const result = await collectSource('aukro', plan, f, () => {}, new AbortController().signal, { getPage: async url => ({ html, url }) });
  assert.deepEqual(result.items.map(x => x.title), ['MSI RTX 3060 Ventus']);
});
test('Aukro JSON-LD fallback keeps sale type unknown', () => {
  const html = `<script type="application/ld+json">${JSON.stringify({mainEntity:{itemListElement:[{'@type':'Product',name:'Notebook',url:'https://aukro.cz/notebook-123',offers:{price:100,priceCurrency:'CZK'}}]}})}</script>`;
  assert.equal(parseAukro(html,'https://aukro.cz').items[0].saleType,'unknown');
});
test('Aukro detects valid empty results separately from parser errors', () => {
  assert.equal(parseAukro('<html>CAPTCHA</html>','https://aukro.cz').recognized,false);
  assert.equal(parseAukro('<script id="ng-state">{"aukCache":{"/offers/searchItemsCommon":{"b":{"content":[]}}}}</script>','https://aukro.cz').recognized,true);
});
test('Detail parsers read description, not surrounding navigation', () => {
  assert.equal(extractDescription('<nav>nabídky</nav><div class="popisdetail">Nejde zapnout.</div>','bazos'),'Nejde zapnout.');
  assert.equal(extractDescription('<script type="application/ld+json">{"@type":"Product","description":"<p>Broken screen</p>"}</script>','aukro'),'Broken screen');
  assert.equal(extractDescription('<div class="popisdetail">RAM: 16 GB<br>SSD: 512 GB</div>','bazos'),'RAM: 16 GB • SSD: 512 GB');
});
test('Aukro detail uses the full description and item parameters, not the shortened JSON-LD', () => {
  const state = {aukCache:{'GET/backend-web/api/offers/7138845760/offerDetail':{b:{descriptionInHtml:'<html><body><div>Nefunkční<br>- CPU Intel Core i5-10300h</div></body></html>',attributes:[{attributeName:'Model grafické karty',attributeValue:'RTX 4060'}]}}}};
  const html = `<script id="ng-state" type="application/json">${JSON.stringify(state)}</script><script type="application/ld+json">{"@type":"Product","description":"Nefunkční…"}</script>`;
  assert.equal(extractDescription(html,'aukro'),'Nefunkční • - CPU Intel Core i5-10300h • Model grafické karty: RTX 4060');
});
test('eBay uses bid price for auction-only and condition IDs as damage evidence', () => {
  const row = {itemId:'v1|123',title:'Lenovo Legion laptop',itemWebUrl:'https://www.ebay.com/itm/123',conditionId:'7000',price:{value:'500',currency:'USD'},currentBidPrice:{value:'55',currency:'USD'},buyingOptions:['AUCTION']};
  const item = parseEbay({itemSummaries:[row]})[0]; assert.equal(item.price,55); assert.equal(item.saleType,'auction'); assert.ok(damageEvidence(item).length);
  assert.equal(parseEbay({itemSummaries:[{...row,itemEndDate:'2020-01-01'}]}).length,0);
});
test('External and executable listing links are rejected', () => {
  assert.equal(safeUrl(undefined,'https://aukro.cz',['aukro.cz']),null);
  assert.equal(safeUrl('','https://aukro.cz',['aukro.cz']),null);
  assert.equal(safeUrl('javascript:alert(1)','https://aukro.cz',['aukro.cz']),null); assert.equal(safeUrl('https://evil.test/','https://aukro.cz',['aukro.cz']),null); assert.equal(safeUrl('https://aukro.cz@evil.test/','https://aukro.cz',['aukro.cz']),null);
});
test('Phones read brand, RAM and storage; notebooks read VRAM; each category filters only its own parameters', async () => {
  const { extractPhone, extractHardware, hardwareMatches } = await import('../src/hardware.js');
  const phone = (title, description = '') => extractPhone({ title, description });
  assert.deepEqual({ ...phone('Samsung Galaxy S23 8/256GB') }, { kind:'phone', brand:'SAMSUNG', ramGb:8, storageGb:256 });
  assert.deepEqual({ ...phone('iPhone 13 128GB, stav 10/10') }, { kind:'phone', brand:'APPLE', ramGb:null, storageGb:128 });
  assert.deepEqual({ ...phone('Redmi Note 13 Pro', 'RAM: 12 GB, úložiště 512 GB') }, { kind:'phone', brand:'XIAOMI', ramGb:12, storageGb:512 });
  assert.equal(phone('Google Pixel 9 - 12/256 porcelain').ramGb, 12);
  assert.equal(extractHardware({ title:'Lenovo Legion 5, RTX 3060, 16GB RAM', description:'' }).vramGb, 6);
  assert.equal(extractHardware({ title:'Asus TUF RTX 4060 8GB, 16GB RAM, 1TB SSD', description:'' }).vramGb, 8);
  assert.equal(extractHardware({ title:'HP ProBook 450 G8 i5 Iris Xe', description:'' }).vramGb, 0);
  assert.equal(extractHardware({ title:'Dell G15 RTX 3050', description:'' }).vramGb, null);
  const laptop = extractHardware({ title:'Lenovo Legion 5 RTX 3060 16GB RAM 512GB SSD', description:'' });
  const f = searchSchema.parse({ prompt:'notebook', sources:['bazos'], brand:'LENOVO', minRamGb:16, minStorageGb:512, minVramGb:6, cpu:'ryzen 9' });
  assert.ok(hardwareMatches(laptop, f, 'laptops'), 'CPU is not a notebook filter');
  assert.equal(hardwareMatches(laptop, { ...f, minVramGb:8 }, 'laptops'), false);
  assert.equal(hardwareMatches(laptop, { ...f, brand:'HP' }, 'laptops'), false);
  assert.equal(hardwareMatches(laptop, f, 'desktops'), false, 'CPU is a PC filter');
  assert.ok(hardwareMatches(null, f, 'gpu'));
  const google = await createPlan(searchSchema.parse({ prompt:'telefon', sources:['bazos'], category:'phones', brand:'GOOGLE' }), { env:{} });
  assert.equal(searchUrl('bazos', google), 'https://mobil.bazos.cz/google/');
  assert.equal(searchUrl('aukro', google), 'https://aukro.cz/mobilni-telefony?text=google');
});
test('Model number is retained in the plan', () => {
  const plan = rulePlan('Nefunkční Galaxy 5', 'phones');
  assert.ok(plan.termGroups.some(group => group.includes('galaxy 5')));
  assert.ok(plan.queryEn.includes('5'));
});
test('Bazos uses category pagination, not disallowed search parameters', () => {
  assert.equal(searchUrl('bazos',rulePlan('notebook'),3),'https://pc.bazos.cz/notebook/40/');
});
test('Source failure preserves listings already collected and reports partial status', async () => {
  let calls = 0; const result = await collectSource('bazos',rulePlan('notebook'),filters({condition:'any'}),()=>{},new AbortController().signal,{getPage:async () => { if (++calls > 1) throw new Error('offline'); return {html:bazosHtml,url:'https://pc.bazos.cz/notebook/'}; }});
  assert.equal(result.items.length,1); assert.equal(result.report.status,'partial'); assert.equal(result.report.pages,1);
});
test('Missing eBay credentials are distinct from zero search results', async () => {
  const result = await collectSource('ebay',rulePlan('notebook'),filters(),()=>{},new AbortController().signal,{env:{}}); assert.equal(result.report.status,'not_configured'); assert.equal(result.report.scanned,0);
});
test('eBay adapter applies category, damage, auction and pagination filters', async () => {
  const requests = [];
  const result = await collectSource('ebay',rulePlan('rozbitý notebook'),filters({pages:3}),()=>{},new AbortController().signal,{
    env:{EBAY_ACCESS_TOKEN:'test-token'},
    fetchFn:async (url,options) => {
      requests.push(new URL(url));
      assert.equal(options.headers['X-EBAY-C-MARKETPLACE-ID'],'EBAY_US');
      assert.equal(options.headers.Authorization,'Bearer test-token');
      return new Response(JSON.stringify({itemSummaries:[{itemId:String(requests.length),title:'ThinkPad na díly',itemWebUrl:`https://www.ebay.com/itm/${requests.length}`,conditionId:'7000',price:{value:'50',currency:'USD'},buyingOptions:['FIXED_PRICE']}],...(requests.length === 1 ? {next:'next-page'} : {})}));
    },
  });
  assert.equal(requests.length,2);assert.equal(requests[1].searchParams.get('offset'),'50');
  assert.equal(requests[0].searchParams.get('category_ids'),'175672');
  assert.match(requests[0].searchParams.get('filter'),/conditionIds:\{7000\}/);
  assert.match(requests[0].searchParams.get('filter'),/FIXED_PRICE\|AUCTION/);
  assert.equal(result.report.status,'done');assert.equal(result.items.length,2);
});
test('Deduplicates repeated pages and stops pagination', async () => {
  let calls=0;const result = await collectSource('bazos',rulePlan('notebook'),filters({pages:10,lookupNewPrices:false}),()=>{},new AbortController().signal,{getPage:async () => {calls++;return {html:bazosHtml,url:'https://pc.bazos.cz/notebook/'};}});
  assert.equal(calls,2);assert.equal(result.items.length,1);
});
test('Agent combines source results and applies filters once', async () => {
  const job = {filters:filters({sources:['bazos']}),sources:{},controller:new AbortController()};
  await runAgent(job,{createPlan:async () => rulePlan('rozbitý herní notebook'),collectSource:async () => ({items:[listing(),listing()],report:{}})});
  assert.equal(job.status,'done');assert.equal(job.items.length,1);assert.equal(job.scanned,1);
});
test('Cancelled job terminates before source access', async () => {
  const job = {filters:filters(),sources:{},controller:new AbortController()};job.controller.abort();
  await runAgent(job,{createPlan:async () => rulePlan('notebook'),collectSource:async () => {throw new Error('must not run')}});assert.equal(job.status,'cancelled');
});
test('HTTP API protects origin, validates requests and never exposes env keys', async t => {
  const server = createServer();await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const config = await (await fetch(`${base}/api/config`)).json();assert.equal('OPENAI_API_KEY' in config,false);
  assert.equal((await fetch(`${base}/api/config`,{headers:{Origin:'https://evil.test'}})).status,403);
  assert.equal((await fetch(`${base}/api/search`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{"prompt":"x"}'})).status,400);
  assert.equal((await fetch(`${base}/.env`)).status,404);
  assert.equal((await fetch(base)).status,200);
});
