import test from 'node:test';
import assert from 'node:assert/strict';
import { searchSchema, parsePrice, safeUrl } from '../src/schema.js';
import { rulePlan, createPlan } from '../src/planner.js';
import { damageEvidence, evaluate } from '../src/matching.js';
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
test('Explicit condition filter overrides prompt', async () => {
  const plan = await createPlan(filters({ condition:'any' }),{env:{}}); assert.equal(plan.damaged,false); assert.equal(plan.mode,'rules'); assert.ok(plan.warning);
});
test('AI plan is schema validated and fallback is clearly labelled', async () => {
  const plan = await createPlan(filters(),{env:{OPENAI_API_KEY:'test'},fetchFn:async () => new Response(JSON.stringify({output:[{content:[{type:'output_text',text:'{"unexpected":true}'}]}]}),{status:200})});
  assert.equal(plan.mode,'rules'); assert.ok(plan.warning);
});
test('AI API uses structured plan and does not send provider listings', async () => {
  let body;
  const plan = await createPlan(filters(),{env:{OPENAI_API_KEY:'test'},fetchFn:async (url,options) => { assert.equal(url,'https://api.openai.com/v1/responses'); body=JSON.parse(options.body); return new Response(JSON.stringify({output:[{content:[{type:'output_text',text:JSON.stringify(rulePlan('rozbitý notebook'))}]}]})); }});
  assert.equal(plan.mode,'ai'); assert.equal(body.store,false); assert.equal(body.text.format.type,'json_schema'); assert.equal(body.input,'Rozbitý herní notebook');
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
test('Console generation number is retained in the plan', () => {
  const plan = rulePlan('Nefunkční PlayStation 5');
  assert.ok(plan.termGroups.some(group => group.includes('5')));
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
