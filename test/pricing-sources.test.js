import test from 'node:test';
import assert from 'node:assert/strict';
import {lookupNewPrice,parseNewProduct,parseRetailLinks,newPriceSearchUrl} from '../src/valuation.js';
import {SourceError} from '../src/http.js';
import {validateManualPrice,withManualPrice} from '../public/pricing.js';
import {searchSchema} from '../src/schema.js';

const urls={mironet:'https://www.mironet.cz/lenovo-loq+dp123456/',k24:'https://www.k24.cz/product/123456/Lenovo_LOQ.html'};
const productHtml=(source,price,extra={})=>`<body><h1>Lenovo LOQ</h1><span>Stav zboží: Nové</span><script type="application/ld+json">${JSON.stringify({'@type':'BreadcrumbList',itemListElement:[{item:{name:'Notebooky'}}]})}</script><script type="application/ld+json">${JSON.stringify({'@type':'Product',name:'Lenovo LOQ 15IRH8',mpn:'82XV00ABCK',offers:{'@type':'Offer',url:urls[source],price,priceCurrency:'CZK',itemCondition:'https://schema.org/NewCondition',availability:'https://schema.org/InStock',...extra}})}</script></body>`;
const searchHtml=source=>source === 'mironet' ? `<div class="nazev"><a href="${urls[source]}">Notebook Lenovo LOQ</a></div>` : `<div id="products-list"><div class="product-entry2"><div class="pe2-head"><a href="${urls[source]}">Notebook Lenovo LOQ</a></div></div></div><aside><a href="https://www.k24.cz/product/999999/Recommendation.html">Recommendation</a></aside>`;
const fetchPrices=async url=>{const source=url.includes('k24.cz')?'k24':'mironet';return {url,html:url===urls[source]?productHtml(source,source==='k24'?18000:20000):searchHtml(source)};};

test('Compares both stores and chooses the lowest equally strong verified price',async()=>{
  const result=await lookupNewPrice({sku:'82XV00ABCK'},new AbortController().signal,{getPage:fetchPrices});
  assert.equal(result.status,'matched');assert.equal(result.reference.source,'K24');assert.equal(result.reference.priceCzk,18000);
  assert.equal(result.offers.length,2);assert.equal(result.reports.length,2);assert.deepEqual(result.range,{min:18000,max:20000,count:2});
});

test('A blocked store does not suppress the other and stays blocked for the current run',async()=>{
  const blockedSources=new Set();let mironetCalls=0,k24Calls=0;
  const getPage=async url=>{if(url.includes('mironet')){mironetCalls++;throw new SourceError('Blocked','blocked');}k24Calls++;return fetchPrices(url);};
  for(let i=0;i<2;i++){
    const result=await lookupNewPrice({sku:'82XV00ABCK'},new AbortController().signal,{getPage,blockedSources});
    assert.equal(result.status,'matched');assert.equal(result.reference.source,'K24');assert.equal(result.reports[0].status,'unavailable');assert.equal(result.blocked,false);
  }
  assert.equal(mironetCalls,1);assert.equal(k24Calls,4);
});

test('K24 accepts explicit new product data but rejects used, expired or unrelated URLs',()=>{
  assert.equal(parseNewProduct(productHtml('k24',18000),urls.k24).source,'K24');
  for(const extra of [{itemCondition:'https://schema.org/UsedCondition'},{priceValidUntil:'2020-01-01'},{url:'https://evil.example/product/123456/Lenovo_LOQ.html'}])assert.equal(parseNewProduct(productHtml('k24',18000,extra),urls.k24),null);
  assert.deepEqual(parseRetailLinks(searchHtml('k24'),newPriceSearchUrl({sku:'82XV00ABCK'},'k24')),[urls.k24]);
});

test('Net estimate subtracts repair per defect, shipping, fees and import costs', async ()=>{
  const { calculateNet, mergeCosts } = await import('../public/pricing.js');
  const costs = mergeCosts({ repair:{ display:2000, power:1000 }, risk:{ charger:300 }, shipping:150, feePercent:5 });
  const item = { priceCzk:4000, shippingCzk:null, defects:[{id:'display'},{id:'power'}], risks:[{id:'charger',level:'warn'}] };
  const net = calculateNet(15000, item, costs, 2000, 500);
  assert.equal(net.repair, 3300); assert.equal(net.shipping, 150); assert.equal(net.shippingEstimated, true); assert.equal(net.fee, 200);
  assert.equal(net.netProfit, 15000 - 4000 - 200 - 150 - 3300 - 500);
  assert.equal(net.maxPurchasePrice, Math.round((15000 - 150 - 3300 - 500 - 2000) / 1.05 * 100) / 100);
  assert.equal(calculateNet(15000, {...item, priceCzk:null}, costs).netProfit, null);
  assert.equal(calculateNet(null, item, costs), null);
  assert.equal(mergeCosts({ repair:{ display:-5 } }).repair.display, 1800);
});

test('eBay imports from outside the EU add VAT and clearance; ČNB list is parsed per unit', async ()=>{
  const { importCost } = await import('../public/pricing.js');
  const { parseCnb } = await import('../src/rates.js');
  assert.equal(importCost({source:'ebay',country:'US',priceCzk:4000,shippingCzk:1000}), 5000 * 0.21 + 350);
  assert.equal(importCost({source:'ebay',country:'DE',priceCzk:4000,shippingCzk:1000}), 0);
  assert.equal(importCost({source:'bazos',country:null,priceCzk:4000}), 0);
  const cnb = parseCnb('26.10.2026 #206\nzemě|měna|množství|kód|kurz\nEMU|euro|1|EUR|24,365\nJaponsko|jen|100|JPY|14,5\nUSA|dolar|1|USD|21,782\nVelká Británie|libra|1|GBP|29,064');
  assert.deepEqual(cnb, { date:'2026-10-26', rates:{ EUR:24.365, USD:21.782, GBP:29.064 } });
  assert.throws(() => parseCnb('<html>chyba</html>'));
});

test('Used-market resale uses the median of working same-config listings and ignores broken, auctions and outliers', async ()=>{
  const { marketIndex, enrichValuations } = await import('../src/valuation.js');
  const ad = (price, extra = {}) => ({ title:'Lenovo Legion 5 15ACH6H Ryzen 7 5800H RTX 3060', description:'Plně funkční', price, currency:'CZK', saleType:'classified', source:'bazos', url:`https://pc.bazos.cz/inzerat/${price}/`, ...extra });
  const listings = [ad(14000), ad(15000), ad(16000), ad(900000), ad(3000, {description:'Nefunkční, nezapne se'}), ad(9000, {saleType:'auction'})];
  const lookup = marketIndex(listings);
  const specs = { model:'LEGION 5 15ACH6H', cpu:'RYZEN 7 5800H', gpu:'RTX 3060' };
  assert.deepEqual([lookup(specs).median, lookup(specs).count, lookup(specs).resale], [15000, 3, 13500]);
  assert.equal(marketIndex(listings.slice(0, 2))(specs), null);
  const job = { filters:{ targetProfit:0, priceLookupLimit:5 }, items:[{ priceCzk:5000, specs:{...specs, ramGb:null} }] };
  await enrichValuations(job, new AbortController().signal, { marketListings:listings, lookupNewPrice:async()=>({ status:'not_found', offers:[], reports:[] }) });
  assert.equal(job.items[0].valuation.calculation.resaleEstimate, 13500);
  assert.equal(job.items[0].valuation.calculation.grossProfit, 8500);
});

test('MacBooks: the chip stands in for the GPU and Apple Store prices the same size and chip', async ()=>{
  const { lookupNewPrice, parseAppleStore } = await import('../src/valuation.js');
  const { extractHardware } = await import('../src/hardware.js');
  const html = '"aosContainerPartNumber":"RO_MBA_M5_13_INCH_SILVER_GOO_2026","x":1,"priceKey":"13inch-silver-10-8"}'
    + ',"aosContainerPartNumber":"RO_MBA_M5_15_INCH_SILVER_BET_2026","priceKey":"15inch-silver-10-10"}'
    + ',"prices":{"13inch-silver-10-8":{"comparativeDisplayPrice":"Od <span class=\\"nowrap\\">34 990 Kč</span>","amount":34990.00},"15inch-silver-10-10":{"comparativeDisplayPrice":"x","amount":41990.00}}';
  assert.deepEqual(parseAppleStore(html,'https://www.apple.com/cz/shop/buy-mac/macbook-air').map(o => [o.specs.model,o.specs.cpu,o.priceCzk]), [['MACBOOK AIR 13','M5',34990],['MACBOOK AIR 15','M5',41990]]);
  const page = async url => ({ html, url });
  const air = extractHardware({ title:'MacBook Air 15 M5 16GB 512GB nefunkční' });
  assert.deepEqual([air.model, air.cpu, air.gpu], ['MACBOOK AIR 15','M5',null]);
  const found = await lookupNewPrice(air, new AbortController().signal, { getPage:page });
  assert.deepEqual([found.status, found.reference.priceCzk, found.reference.match], ['matched',41990,'partial']);
  const older = await lookupNewPrice(extractHardware({ title:'MacBook Air 13 M2 8GB 256GB' }), new AbortController().signal, { getPage:page });
  assert.equal(older.status, 'not_found');
});

test('Cached recognition returns independent copies and shop links with a different configuration are skipped', async ()=>{
  const { extractHardware } = await import('../src/hardware.js');
  const { classifyListing } = await import('../src/defects.js');
  const { rankLinks } = await import('../src/valuation.js');
  const first = extractHardware({ title:'Lenovo LOQ 15IRH8 i5-12450H RTX 4050 16GB 512GB SSD' });
  first.sku = 'CHANGED'; first.ambiguous.push('x');
  const second = extractHardware({ title:'Lenovo LOQ 15IRH8 i5-12450H RTX 4050 16GB 512GB SSD' });
  assert.equal(second.sku, null); assert.deepEqual(second.ambiguous, []);
  const c1 = classifyListing({ title:'Nezapne se', description:'', condition:'' }); c1.defects.push({ id:'x' });
  assert.equal(classifyListing({ title:'Nezapne se', description:'', condition:'' }).defects.length, 1);
  const links = ['https://www.k24.cz/product/1/Lenovo_LOQ_Essential_15_Ryzen_5_150_16GB_512GB_RTX5050.html','https://www.k24.cz/product/2/Lenovo_LOQ_Essential_15_Ryzen_5_150_32GB_512GB_RTX5050.html','https://www.k24.cz/product/3/Lenovo_LOQ_15IRX9_i5-13450HX_16GB_512GB_RTX4050.html'];
  assert.deepEqual(rankLinks(links, { model:'LOQ ESSENTIAL 15', cpu:'RYZEN 5 150', gpu:'RTX 5050', ramGb:16 }), [links[0]]);
  assert.deepEqual(rankLinks(links, { model:'LOQ ESSENTIAL 15', cpu:'RYZEN 5 150', gpu:'RTX 5050', ramGb:null }), [links[0], links[1]]);
});

test('Missing hardware does not trigger network requests but exposes both manual search links',async()=>{
  const value=await lookupNewPrice({model:'LOQ 15IRH8'},new AbortController().signal,{getPage:async()=>{throw new Error('must not fetch');}});
  assert.equal(value.status,'insufficient');assert.equal(value.searchLinks.length,2);
});

test('Cancellation propagates while stores are checked in parallel',async()=>{
  const controller=new AbortController();
  await assert.rejects(lookupNewPrice({sku:'82XV00ABCK'},controller.signal,{getPage:async()=>{controller.abort();controller.signal.throwIfAborted();}}));
});

test('Manual price requires a positive price, safe source link and explicit confirmation',()=>{
  const entry={priceCzk:20000,url:'https://example.com/notebook',confirmed:true};
  assert.equal(validateManualPrice(entry).priceCzk,20000);
  for(const patch of [{priceCzk:0},{priceCzk:NaN},{priceCzk:Infinity},{priceCzk:-1},{priceCzk:10000001},{url:'javascript:alert(1)'},{url:'https://user:password@example.com/'},{url:''},{confirmed:false}])assert.throws(()=>validateManualPrice({...entry,...patch}));
});

test('Manual calculation retains original automatic evidence and can be removed without mutating the item',()=>{
  const original={id:'bazos:1',priceCzk:4000,valuation:{status:'matched',reference:{priceCzk:25000},offers:[{source:'K24',priceCzk:25000}]}};
  const modified=withManualPrice(original,{priceCzk:20000,url:'https://example.com/notebook',confirmed:true},3000);
  assert.equal(modified.valuation.status,'manual');assert.equal(modified.valuation.calculation.grossProfit,11000);assert.equal(modified.valuation.calculation.maxPurchasePrice,12000);
  assert.equal(modified.valuation.offers[0].priceCzk,25000);assert.equal(original.valuation.reference.priceCzk,25000);
  assert.equal(withManualPrice(original,null),original);assert.equal(withManualPrice(original,{priceCzk:-1}),original);
});

test('Manual values preserve unknown purchase prices and losses',()=>{
  const entry={priceCzk:20000,url:'https://example.com/notebook',confirmed:true};
  assert.equal(withManualPrice({priceCzk:null},entry).valuation.calculation.grossProfit,null);
  assert.equal(withManualPrice({priceCzk:17000},entry).valuation.calculation.grossProfit,-2000);
});

test('Price source selection is explicit, deduplicated and validated',()=>{
  const base={prompt:'notebook',sources:['bazos']};
  assert.deepEqual(searchSchema.parse(base).priceSources,['mironet','k24']);
  assert.deepEqual(searchSchema.parse({...base,priceSources:['k24','k24']}).priceSources,['k24']);
  assert.throws(()=>searchSchema.parse({...base,priceSources:['evil']}));assert.throws(()=>searchSchema.parse({...base,priceSources:[]}));
});
