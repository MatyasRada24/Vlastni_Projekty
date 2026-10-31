import test from 'node:test';
import assert from 'node:assert/strict';
import { searchSchema } from '../src/schema.js';
import { rulePlan } from '../src/planner.js';
import { evaluate, detailCandidate, damageEvidence } from '../src/matching.js';
import { collectSource } from '../src/sources.js';
import { runAgent } from '../src/agent.js';
import { SourceError } from '../src/http.js';

const filters = (extra={}) => searchSchema.parse({prompt:'Rozbitý herní notebook',sources:['bazos'],pages:1,...extra});
const item = (extra={}) => ({id:'bazos:1',source:'bazos',title:'HP Victus',description:'Nefunguje',price:2000,currency:'CZK',saleType:'classified',shipping:null,location:'Brno',condition:'',...extra});
const html = (id, title='HP Victus', description='') => `<div class="inzeraty"><h2><a href="/inzerat/${id}/pc.php">${title}</a></h2><div class="popis">${description}</div><div class="inzeratycena">2000 Kč</div><div class="inzeratylok">Brno</div></div>`;
const detail = description => `<div class="popisdetail">${description}</div>`;

test('Recognizes additional gaming families without notebook or RTX in title', () => {
  for (const title of ['HP Victus','HP Omen','MSI GF63','MSI Katana 15','Lenovo LOQ','Asus ROG Zephyrus','Uniwill GM5']) assert.ok(evaluate(item({title}),rulePlan('rozbitý herní notebook'),filters()),title);
});
test('Model punctuation and joined digits match, but ROG does not match program', () => {
  const p=rulePlan('notebook RTX 3060');
  for (const title of ['notebook RTX3060','notebook RTX-3060','notebook RTX 3060']) assert.ok(evaluate(item({title}),p,filters()));
  assert.equal(evaluate(item({title:'notebook s programem'}),rulePlan('herní notebook'),filters()),null);
  assert.equal(evaluate(item({title:'notebook RTX 30600'}),p,filters()),null);
});
test('Generic AI-like term groups expand without loosening explicit brand filters', () => {
  const p={...rulePlan('herní notebook Lenovo'),termGroups:[['laptop'],['gaming'],['Lenovo']]};
  assert.ok(evaluate(item({title:'Lenovo LOQ'}),p,filters()));
  assert.equal(evaluate(item({title:'HP Victus'}),p,filters()),null);
});
test('Negated defects stay excluded and real defect vocabulary expands', () => {
  assert.equal(damageEvidence(item({description:'Bez závady. Není poškozený. Not defective.'})).length,0);
  for (const description of ['Nenabíjí','Nefunguje','Prasklina displeje','Zalitý','No power','Porucha desky']) assert.ok(damageEvidence(item({description})).length,description);
});
test('Symptom in query does not become a mandatory title keyword', () => {
  for (const prompt of ['Notebook nefunguje','Notebook nejde zapnout']) {
    const p=rulePlan(prompt);assert.equal(p.damaged,true);assert.ok(evaluate(item({title:'Notebook',description:'Na díly'}),p,filters()));
  }
});
test('Detail reads recover gaming specification and defect hidden outside snippet', async () => {
  const f=filters({includeTerms:['RTX3060']}); const p=rulePlan(f.prompt);
  const result=await collectSource('bazos',p,f,()=>{},new AbortController().signal,{getPage:async url=>({url,html:url.includes('/inzerat/') ? detail('RTX-3060, nejde zapnout.') : html(1,'Notebook Acer')})});
  assert.equal(result.report.details,1);assert.ok(result.items[0].detailRead);assert.ok(evaluate(result.items[0],p,f));
});
test('Detail budget is spent on unknown defects instead of already matching ads', async () => {
  const f=filters({detailLimit:1,lookupNewPrices:false}), p=rulePlan(f.prompt);const visited=[];
  const result=await collectSource('bazos',p,f,()=>{},new AbortController().signal,{getPage:async url=>{
    visited.push(url); return {url,html:url.includes('/inzerat/') ? detail('Nefunguje') : html(1,'HP Victus','Nefunkční')+html(2,'HP Omen')+html(3,'Lenovo Legion')};
  }});
  assert.match(visited[1],/inzerat\/2\//);assert.equal(result.report.details,1);assert.equal(result.report.detailCandidates,2);
  assert.ok(result.report.warnings.some(x=>x.includes('Limit popisů')));
  assert.equal(result.items.filter(x=>evaluate(x,p,f)).length,2);
});
test('User price/location/exclusions still prevent unnecessary detail reads', () => {
  const f=filters({maxPrice:3000,location:'Brno'}), p={...rulePlan(f.prompt),excludeTerms:['politý']};
  assert.equal(detailCandidate(item({price:9000}),p,f),false);
  assert.equal(detailCandidate(item({location:'Praha'}),p,f),false);
  assert.equal(detailCandidate(item({description:'Politý'}),p,f),false);
});
test('Proceeds beyond page ten and stops at configured page budget', async () => {
  let count=0;const f=filters({pages:12,detailLimit:0});
  const result=await collectSource('bazos',rulePlan(f.prompt),f,()=>{},new AbortController().signal,{getPage:async url=>({url,html:html(++count)})});
  assert.equal(result.report.pages,12);assert.equal(result.items.length,12);
});
test('Overlapping pages do not stop crawling unless the complete ID set repeats', async () => {
  const pages=[html(1)+html(2),html(2)+html(3),html(1)+html(3),html(4)];let i=0;
  const f=filters({pages:4,detailLimit:0});
  const result=await collectSource('bazos',rulePlan(f.prompt),f,()=>{},new AbortController().signal,{getPage:async url=>({url,html:pages[i++]})});
  assert.equal(i,4);assert.equal(result.items.length,4);
});
test('eBay exploratory query shares budget and keeps independent offsets', async () => {
  const calls=[];const f=filters({pages:8}),p=rulePlan(f.prompt);
  const result=await collectSource('ebay',p,f,()=>{},new AbortController().signal,{env:{EBAY_ACCESS_TOKEN:'test'},fetchFn:async url=>{
    calls.push(new URL(url));return new Response(JSON.stringify({next:'more',itemSummaries:[{itemId:String(calls.length),title:'HP Victus nefunguje',itemWebUrl:`https://www.ebay.com/itm/${calls.length}`,price:{value:'50',currency:'USD'},buyingOptions:['FIXED_PRICE']}]}));
  }});
  assert.equal(calls.length,8);assert.equal(result.report.discoveryPages,2);
  assert.equal(calls[3].searchParams.has('q'),false);assert.equal(calls[3].searchParams.get('offset'),'0');assert.equal(calls[7].searchParams.get('offset'),'50');
  assert.equal(calls[3].searchParams.get('filter').includes('conditionIds'),false);
  assert.equal(calls[4].searchParams.get('offset'),'150');assert.equal(calls[0].searchParams.get('fieldgroups'),'EXTENDED');
});
test('Already found listings stream out before details and survive cancellation', async () => {
  const f=filters(), p=rulePlan(f.prompt), controller=new AbortController();let streamed=false;
  const result=await collectSource('bazos',p,f,(report,items)=>{if(report.pages===1){streamed=items.length===2;controller.abort();}},controller.signal,{getPage:async url=>({url,html:html(1,'HP Victus','Nefunkční')+html(2,'HP Omen')})});
  assert.equal(streamed,true);assert.equal(result.report.status,'cancelled');assert.equal(result.items.length,2);
});
test('A detail access block preserves results and marks source partial', async () => {
  const f=filters();const result=await collectSource('bazos',rulePlan(f.prompt),f,()=>{},new AbortController().signal,{getPage:async url=>{if(url.includes('/inzerat/'))throw new SourceError('Blocked','blocked');return {url,html:html(1)};}});
  assert.equal(result.report.status,'partial');assert.equal(result.items.length,1);
});
test('Agent exposes matches before a source finishes', async () => {
  const f=filters(); const job={filters:f,sources:{},items:[],controller:new AbortController()};let observed=false;
  await runAgent(job,{createPlan:async()=>rulePlan(f.prompt),collectSource:async(source,plan,filter,progress)=>{
    progress({source,scanned:1},[item()]);observed=job.items.length===1;return {items:[item()],report:{}};
  }});assert.equal(observed,true);assert.equal(job.items.length,1);
});
