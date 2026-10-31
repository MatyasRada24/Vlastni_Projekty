import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.js';

test('Remembers listings between runs: new, price drops and hidden listings persist on disk', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lovec-store-'));
  const first = createStore(dir);
  const [a] = await first.annotate([{ id:'bazos:1', title:'Legion', url:'https://pc.bazos.cz/inzerat/1/', priceCzk:6000 }], '2026-10-01T10:00:00.000Z');
  assert.equal(a.history.isNew, true);
  await first.setHidden('bazos:2', true, 'Překupník');

  const second = createStore(dir);
  const [b] = await second.annotate([{ id:'bazos:1', title:'Legion', url:'https://pc.bazos.cz/inzerat/1/', priceCzk:5200 }], '2026-10-05T10:00:00.000Z');
  assert.deepEqual(b.history, { isNew:false, firstSeen:'2026-10-01T10:00:00.000Z', previousPrice:6000, priceChange:-800 });
  assert.ok((await second.hidden())['bazos:2']);
  await second.setHidden('bazos:2', false);
  assert.deepEqual(JSON.parse(await readFile(join(dir, 'store.json'), 'utf8')).hidden, {});
});

test('Verified new prices are reused for 12 hours, so a repeated search skips the network lookup', async () => {
  const { enrichValuations } = await import('../src/valuation.js');
  const store = createStore(await mkdtemp(join(tmpdir(), 'lovec-price-')));
  const specs = { brand:'LENOVO', model:'LOQ 15IRH8', cpu:'I5-12450H', gpu:'RTX 4050', sku:null, ramGb:16, storageGb:512, storageType:'SSD' };
  let calls = 0;
  const lookupNewPrice = async () => { calls++; return { status:'matched', reference:{ priceCzk:20000, match:'configuration' }, offers:[], reports:[] }; };
  const run = () => { const job = { filters:{ priceLookupLimit:5, targetProfit:0 }, items:[{ priceCzk:4000, specs }] }; return enrichValuations(job, new AbortController().signal, { lookupNewPrice, priceCache:store }).then(() => job); };
  await run();
  const second = await run();
  assert.equal(calls, 1);
  assert.equal(second.items[0].valuation.cached, true);
  assert.equal(second.items[0].valuation.calculation.grossProfit, 11000);
  assert.equal(await store.getPrice('x', Date.now()), null);
  // "Not found" at reachable shops is cached even when another shop blocks bots; a plain failure is not.
  let notFound = 0;
  const other = { ...specs, model:'LOQ 15APH8' };
  const missing = async () => { notFound++; return { status:'unavailable', offers:[], reports:[{ status:'unavailable', blocked:true },{ status:'not_found' }] }; };
  const failing = async () => { notFound++; return { status:'unavailable', offers:[], reports:[{ status:'unavailable', blocked:false }] }; };
  for (const lookup of [missing, missing]) await enrichValuations({ filters:{ priceLookupLimit:5 }, items:[{ priceCzk:1, specs:other }] }, new AbortController().signal, { lookupNewPrice:lookup, priceCache:store });
  assert.equal(notFound, 1);
  const third = { ...specs, model:'LOQ 16IRH8' };
  for (const lookup of [failing, failing]) await enrichValuations({ filters:{ priceLookupLimit:5 }, items:[{ priceCzk:1, specs:third }] }, new AbortController().signal, { lookupNewPrice:lookup, priceCache:store });
  assert.equal(notFound, 3);
  await store.setPrice('old', { status:'matched' }, Date.now() - 13 * 3600000);
  assert.equal(await store.getPrice('old'), null);
});
