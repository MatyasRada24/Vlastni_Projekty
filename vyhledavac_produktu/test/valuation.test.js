import test from 'node:test';
import assert from 'node:assert/strict';
import { extractHardware, hardwareMatches, compareHardware } from '../src/hardware.js';
import { calculateProfit, parseNewProduct, parseRetailLinks, lookupNewPrice, enrichValuations } from '../src/valuation.js';
import { searchSchema } from '../src/schema.js';
import { evaluate, detailCandidate } from '../src/matching.js';
import { rulePlan } from '../src/planner.js';
import { runAgent } from '../src/agent.js';

const url = 'https://www.mironet.cz/lenovo-loq+dp123456/';
const title = 'Lenovo LOQ 15IRH8 / Notebook / Intel Core i5-12450H / 16GB / 512GB SSD / RTX 4050 6GB';
const laptop = {title,description:'Nefunkční',id:'bazos:1',source:'bazos',price:4000,currency:'CZK',shipping:null,saleType:'classified',condition:'',location:'Brno'};
const product = (extra={}) => ({'@type':'Product',name:title,mpn:'82XV00ABCK',offers:{'@type':'Offer',url,price:20000,priceCurrency:'CZK',availability:'https://schema.org/InStock',...extra}});
const html = (p=product(),state='Nové') => `<html><body><h1>Lenovo LOQ</h1><span>Stav zboží: ${state}</span><script type="application/ld+json">${JSON.stringify(p)}</script></body></html>`;
const filters = extra => searchSchema.parse({prompt:'Rozbitý herní notebook',sources:['bazos'],...extra});

test('Extracts model, CPU, GPU, RAM and disk without treating VRAM as RAM', () => {
  const s=extractHardware(laptop);
  assert.equal(s.model,'LOQ 15IRH8'); assert.equal(s.cpu,'I5-12450H'); assert.equal(s.gpu,'RTX 4050'); assert.equal(s.ramGb,16); assert.equal(s.storageGb,512); assert.equal(s.storageType,'SSD');
  assert.equal(extractHardware({title:'RTX 4050 6GB'}).ramGb,null);
  assert.equal(extractHardware({title:'ASUS TUF FA507NV-LP111'}).sku,'FA507NV-LP111');
  assert.equal(extractHardware({title:'ASUS ROG Strix G18 G815LW-NEBULA046'}).sku,'G815LW-NEBULA046');
  assert.equal(extractHardware({title:'SSD 1 TB'}).storageGb,1000);
  assert.equal(extractHardware({title:'HP Zbook Intel Core Ultra 7 265HX, 512GB SSD m2'}).cpu,'CORE ULTRA 7 265HX');
  assert.equal(extractHardware({title:'Lenovo IdeaPad Slim 3 16IRH10'}).model,'IDEAPAD SLIM 3 16IRH10');
});

test('Reads labelled fields and marketplace parameters, including Aukro ranges', () => {
  const aukro=extractHardware({title:'ASUS TUF Gaming A15 FA507NV-LP111',description:'Stav zboží: Nefunkční / na díly; Značka: Asus; Model grafické karty: RTX 4060; Procesor: AMD Ryzen 7 7735HS; Velikost operační paměti: 16 – 31 GB; Kapacita disku: 500 GB až 749 GB; Typ pevného disku: SSD'});
  assert.equal(aukro.gpu,'RTX 4060'); assert.equal(aukro.cpu,'RYZEN 7 7735HS'); assert.equal(aukro.ramGb,null); assert.equal(aukro.storageGb,null); assert.equal(aukro.storageType,'SSD');
  const s=extractHardware({title:'Herní notebook Acer NITRO V15',description:'Procesor: 13th Gen Intel(R) Core(TM) i5-13420H Operační paměť: 16gb DDR5 Grafická karta: NVIDIA GeForce RTX 4050 6gb Úložiště: 1000 GB (1TB)'});
  assert.deepEqual([s.cpu,s.gpu,s.ramGb,s.storageGb],['I5-13420H','RTX 4050',16,1000]);
  const p=extractHardware({title:'Lenovo P16s G.4 64GB RAM',description:'Paměť : 2x 32GB SO-DIMM DDR5 • Maximální paměť : až 96GB (2x 48GB) • Úložiště : 1TB SSD M.2 • Podpora úložiště : jeden disk, až 2TB'});
  assert.deepEqual([p.model,p.ramGb,p.storageGb,p.storageType],['THINKPAD P16S GEN 4',64,1000,'SSD']);
});

test('Recognizes current CPU, GPU and model naming in titles', () => {
  const cases = [
    ['DELL XPS 16 | Ultra X7 358H | 32GB','cpu','CORE ULTRA X7 358H'],['Legion Pro 5 16IAX10H,U9 275HX,32GB,SSD1TB,RTX5070Ti','cpu','CORE ULTRA 9 275HX'],
    ['Alienware 15 Intel Core 5 210H','cpu','CORE 5 210H'],['Thinkpad Z13 Ryzen 7 PRO 6850U','cpu','RYZEN 7 PRO 6850U'],
    ['HP ZBook Firefly 16 G10 RTX A500 + Intel Iris Xe','gpu','RTX A500'],['Dell Precision 5690 RTX 1000 Ada','gpu','RTX 1000 ADA'],
    ['Thinkpad X1 i7 10750H, GTX1650Ti 4GB, NVIDIA GeForce GTX 1650 Ti','gpu','GTX 1650 TI'],['HP ZBook Firefly 16 G10','model','ZBOOK FIREFLY 16 GEN 10'],
    ['MSI Vector 16 HX AI','model','VECTOR 16 HX'],['ASUS ROG Strix G18','model','STRIX G18'],['Dell XPS 13 9310','model','XPS 13 9310'],
  ];
  for (const [title,key,value] of cases) assert.equal(extractHardware({title})[key],value,title);
  const t=extractHardware({title:'MacBook Air M4 13" 16/256 GB černý'});
  assert.deepEqual([t.brand,t.cpu,t.ramGb,t.storageGb,t.storageType],['APPLE','M4',16,256,'SSD']);
  const h=extractHardware({title:'Herní Omen 16, RTX 4070, 32gb, 1TB',description:'HP exceluje stejně jako Acer, Lenovo, Dell či Asus.'});
  assert.deepEqual([h.brand,h.ramGb,h.storageGb],['HP',32,1000]);
});

test('Upgrade options, VRAM and trade-in wishes are not read as the laptop hardware', () => {
  const s=extractHardware({title:'Dell XPS 13 9310 i7-1185G7, 16GB, 512',description:'Paměť 16GB LPDDR4x. Grafická karta Nvidia RTX 4060 s vlastní 8GB pamětí. Tento notebook mám i v konfiguraci s 32GB RAM nebo SSD 1TB za cenu 9990,-'});
  assert.equal(s.ramGb,16);
  assert.equal(extractHardware({title:'Victus',description:'RTX 4070 s vlastní 8GB pamětí, paměti RAM DDR5 16GB (mohu navýšit)'}).ramGb,16);
  assert.equal(extractHardware({title:'MacBook Air M4',description:'Výměna: zajímá mě herní PC s RTX 4060 a 32 GB RAM.'}).gpu,null);
  assert.equal(extractHardware({title:'Lenovo P15s SSD 16GB RAM'}).storageGb,null);
  assert.equal(extractHardware({title:'Lenovo P14s (Ryzen 7, 24/32/48GB RAM)'}).ramGb,null);
  assert.equal(extractHardware({title:'MSI Vector',description:'SSD: 1000GB NVMe + slot na další HDD'}).storageType,'SSD');
});

test('Conflicting specs stay unknown; no hardware is inferred from a family name', () => {
  const s=extractHardware({title:'HP Victus',description:'8 GB RAM nebo 16 GB RAM. RTX 3050 nebo RTX 3060.'});
  assert.equal(s.ramGb,null);assert.equal(s.gpu,null);assert.equal(s.cpu,null);assert.ok(s.ambiguous.includes('ramGb'));
});

test('Hardware filters exclude unknowns by default and known mismatches even when unknowns are allowed', () => {
  const s=extractHardware(laptop);
  assert.ok(hardwareMatches(s,filters({cpu:'i5',gpu:'RTX4050',minRamGb:16,minStorageGb:512})));
  assert.equal(hardwareMatches(s,filters({minRamGb:32,includeUnknownSpecs:true})),false);
  const unknown=extractHardware({title:'Lenovo notebook'});
  assert.equal(hardwareMatches(unknown,filters({gpu:'RTX4050'})),false);
  assert.ok(hardwareMatches(unknown,filters({gpu:'RTX4050',includeUnknownSpecs:true})));
});

test('Detail reads can recover required hardware on an otherwise matching ad', () => {
  const f=filters({minRamGb:16,lookupNewPrices:false}),p=rulePlan(f.prompt);
  const i={...laptop,title:'Lenovo LOQ nefunkční',description:''};
  assert.equal(evaluate(i,p,f),null);assert.ok(detailCandidate(i,p,f));
  assert.ok(evaluate({...i,description:'16 GB RAM'},p,f));
  assert.ok(detailCandidate(i,p,filters({lookupNewPrices:true})));
});

test('Profit follows the requested formula, including zero, loss and unknown purchase price', () => {
  assert.deepEqual(calculateProfit(20000,4000,3000),{resaleEstimate:15000,grossProfit:11000,maxPurchasePrice:12000,targetProfit:3000});
  assert.equal(calculateProfit(20000,16000).grossProfit,-1000);
  assert.equal(calculateProfit(20000,0).grossProfit,15000);
  assert.equal(calculateProfit(20000,null).grossProfit,null);
  assert.equal(calculateProfit(null,1000),null);
  assert.equal(calculateProfit(100,0,100).maxPurchasePrice,-25);
});

test('Reference requires exact manufacturer SKU or complete matching configuration', () => {
  const s=extractHardware(laptop), p=parseNewProduct(html(),url);
  assert.equal(compareHardware(s,p.specs),'configuration');
  assert.equal(compareHardware({...s,gpu:'RTX 4060'},p.specs),null);
  assert.equal(compareHardware({...s,ramGb:null},p.specs),'partial');
  assert.equal(compareHardware({sku:'82XV00ABCK'},p.specs),'sku');
  assert.equal(compareHardware({...s,sku:'82XV00ZZCK'},p.specs),null);
  assert.equal(compareHardware({...s,sku:'82XV00ABCK',gpu:'RTX 4060'},p.specs),null);
  assert.equal(compareHardware({model:s.model,cpu:s.cpu,gpu:s.gpu,ramGb:null},{...p.specs,sku:null}),'partial');
  assert.equal(compareHardware({model:s.model,cpu:s.cpu,gpu:s.gpu,ramGb:32},{...p.specs,sku:null}),null);
});

test('Retail price rejects used, expired, unavailable and unrelated offers', () => {
  assert.equal(parseNewProduct(html(),url).priceCzk,20000);
  for(const extra of [{availability:'https://schema.org/OutOfStock'},{priceCurrency:'EUR'},{price:0},{priceValidUntil:'2020-01-01'},{itemCondition:'https://schema.org/UsedCondition'},{url:'https://evil.example/'}]) assert.equal(parseNewProduct(html(product(extra)),url),null);
  assert.equal(parseNewProduct(html(product(),'Použité'),url),null);
  assert.equal(parseNewProduct(html([product(),product()]),url),null);
  assert.equal(parseNewProduct(html({...product(),name:'Adaptér pro Lenovo LOQ'}),url),null);
});

test('Search only accepts observed retailer product links and deduplicates', () => {
  assert.deepEqual(parseRetailLinks(`<div class="nazev"><a href="${url}">one</a><a href="${url}">two</a><a href="https://evil.example/x+dp123/">bad</a></div><a href="/recommendation+dp999/">recommendation</a>`,'https://www.mironet.cz'),[url]);
});

test('Lookup verifies a real product page before accepting a new price', async () => {
  const calls=[];
  const result=await lookupNewPrice(extractHardware(laptop),new AbortController().signal,{priceSources:['mironet'],getPage:async u=>{calls.push(u);return {url:u,html:u.includes('showSearch')?`<div class="nazev"><a href="${url}">LOQ</a></div>`:html()};}});
  assert.equal(calls.length,2);assert.equal(result.status,'matched');assert.equal(result.reference.match,'configuration');assert.equal(result.reference.priceCzk,20000);
});

test('One lookup is reused for duplicate configurations but each purchase price is calculated independently', async () => {
  const specs=extractHardware(laptop);let calls=0;
  const job={filters:filters({priceLookupLimit:1}),items:[{specs,priceCzk:4000},{specs,priceCzk:6000},{specs:{...specs,model:'LOQ 15ARP9'},priceCzk:3000}]};
  await enrichValuations(job,new AbortController().signal,{lookupNewPrice:async()=>{calls++;return {status:'matched',reference:parseNewProduct(html(),url)};}});
  assert.equal(calls,1);assert.equal(job.items[0].valuation.calculation.grossProfit,11000);assert.equal(job.items[1].valuation.calculation.grossProfit,9000);assert.equal(job.items[2].valuation.status,'limit');
});

test('Unique SKU searches may redirect directly to a product', async () => {
  const result=await lookupNewPrice({sku:'82XV00ABCK'},new AbortController().signal,{getPage:async()=>({url,html:html()})});
  assert.equal(result.status,'matched');assert.equal(result.reference.match,'sku');
});

test('Insufficient identity spends no requests and a blocked retailer stops further lookups', async () => {
  let calls=0;
  const result=await lookupNewPrice({model:'LOQ 15IRH8'},new AbortController().signal,{getPage:async()=>{calls++;throw new Error('must not request');}});
  assert.equal(result.status,'insufficient');assert.equal(calls,0);
  const job={filters:filters(),items:[{specs:{sku:'82XV00ABCK'}},{specs:{sku:'82XV00ZZCK'}}]};
  await enrichValuations(job,new AbortController().signal,{lookupNewPrice:async()=>{calls++;return {status:'unavailable',blocked:true,message:'Blocked'};}});
  assert.equal(calls,1);assert.equal(job.items[1].valuation.status,'unavailable');
});

test('Agent retains results and closes pending valuation states when cancelled', async () => {
  const controller=new AbortController(),job={controller,filters:filters(),sources:{},items:[]};
  await runAgent(job,{createPlan:async()=>rulePlan(job.filters.prompt),collectSource:async()=>({items:[laptop]}),lookupNewPrice:async()=>{controller.abort();controller.signal.throwIfAborted();}});
  assert.equal(job.status,'cancelled');assert.equal(job.items.length,1);assert.equal(job.items[0].valuation.status,'cancelled');
});

test('New filter ranges are validated and valuation defaults on', () => {
  assert.equal(filters().lookupNewPrices,true);
  for(const f of [{priceLookupLimit:201},{minRamGb:0},{minStorageGb:-1},{targetProfit:-1}]) assert.throws(()=>filters(f));
});
