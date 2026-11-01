import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.js';
import { parseSeller, fetchSellerOffers, createSellerWatch } from '../src/sellers.js';
import { parseAukro } from '../src/parsers.js';

test('Seller input accepts Aukro and eBay links or a bare name, and refuses Bazoš', () => {
  assert.deepEqual(parseSeller('https://aukro.cz/uzivatel/demo_prodejce/nabidky'), { source:'aukro', login:'demo_prodejce', id:'aukro:demo_prodejce' });
  assert.deepEqual(parseSeller('aukro.cz/uzivatel/Demo_Prodejce'), { source:'aukro', login:'Demo_Prodejce', id:'aukro:demo_prodejce' });
  assert.equal(parseSeller('https://www.ebay.com/usr/demo-seller?_trksid=1').login, 'demo-seller');
  assert.equal(parseSeller('https://www.ebay.de/sch/i.html?_ssn=sample-shop&_sop=10').login, 'sample-shop');
  assert.deepEqual(parseSeller('@demo-seller', 'ebay'), { source:'ebay', login:'demo-seller', id:'ebay:demo-seller' });
  assert.throws(() => parseSeller('https://pc.bazos.cz/inzerat/1/x.php'), /Bazoš/);
  assert.throws(() => parseSeller('demo-seller'), /Vyber web/);
  assert.throws(() => parseSeller('a},sellers:{b', 'ebay'), /nepovolené/);
  assert.throws(() => parseSeller('https://www.ebay.com/str/someshop'), /chybí prodejce/);
});

const aukroPage = rows => `<script id="ng-state" type="application/json">${JSON.stringify({ aukCache: { 'POST/backend-web/api/offers/searchItemsCommon': { b: { content: rows } } } })}</script>`;
const row = (id, price) => ({ itemId:id, itemName:`Notebook ${id}`, seoUrl:`notebook-${id}`, price:{ amount:price, currency:'CZK' }, sellerLogin:'demo_prodejce', auction:false });

test('Aukro listings carry the seller login and a seller page is read with the normal parser', async () => {
  assert.equal(parseAukro(aukroPage([row(1, 100)]), 'https://aukro.cz/').items[0].seller, 'demo_prodejce');
  const urls = [];
  const result = await fetchSellerOffers({ source:'aukro', login:'demo_prodejce' }, { getPage: async url => { urls.push(url); return { html:aukroPage([row(1, 100), row(2, 200)]), url }; } });
  assert.deepEqual(urls, ['https://aukro.cz/uzivatel/demo_prodejce/nabidky']);
  assert.deepEqual(result.items.map(i => i.id), ['aukro:1', 'aukro:2']);
});

test('eBay seller offers use the root category with a seller filter', async () => {
  let requested;
  const fetchFn = async url => { requested = new URL(url); return { ok:true, json: async () => ({ total:1, itemSummaries:[{ itemId:'v1|9|0', title:'ThinkPad for parts', itemWebUrl:'https://www.ebay.com/itm/9', price:{ value:'50', currency:'USD' }, buyingOptions:['FIXED_PRICE'], seller:{ username:'demo-seller' } }] }) }; };
  const result = await fetchSellerOffers({ source:'ebay', login:'demo-seller' }, { fetchFn, env:{ EBAY_ACCESS_TOKEN:'t' } });
  assert.equal(requested.searchParams.get('category_ids'), '0');
  assert.match(requested.searchParams.get('filter'), /^sellers:\{demo-seller\},/);
  assert.equal(result.items[0].seller, 'demo-seller');
  assert.equal(result.total, 1);
});

test('Followed sellers mark offers that appeared or got cheaper after the list was last opened', async () => {
  const store = createStore(await mkdtemp(join(tmpdir(), 'lovec-sellers-')));
  let clock = Date.parse('2026-11-01T10:00:00Z'), offers = [{ id:'aukro:1', title:'A', url:'https://aukro.cz/a-1', price:1000, currency:'CZK' }];
  const watch = createSellerWatch({ store, now: () => clock, fetchOffers: async () => ({ items: offers.map(o => ({ ...o })), total: offers.length }) });

  let status = await watch.add('https://aukro.cz/uzivatel/demo_prodejce');
  assert.equal(status.sellers.length, 1);
  assert.equal(status.offers.length, 1);
  assert.equal(status.newCount, 0);
  await assert.rejects(watch.add('demo_prodejce', 'aukro'), /už sleduješ/);

  clock += 3600000;
  offers = [{ ...offers[0], price:800 }, { id:'aukro:2', title:'B', url:'https://aukro.cz/b-2', price:500, currency:'CZK' }];
  await watch.refresh();
  status = await watch.status();
  assert.deepEqual(status.offers.map(o => [o.id, o.isNew, o.isCheaper, o.previousPrice]), [['aukro:1', false, true, 1000], ['aukro:2', true, false, null]]);
  assert.equal(status.newCount, 2);

  clock += 60000;
  status = await watch.markSeen();
  assert.equal(status.newCount, 0);
  assert.equal((await watch.remove('aukro:demo_prodejce')).sellers.length, 0);
});

test('A failed check keeps the previous offers and reports the error', async () => {
  const store = createStore(await mkdtemp(join(tmpdir(), 'lovec-sellers-')));
  let fail = false;
  const watch = createSellerWatch({ store, fetchOffers: async () => { if (fail) throw new Error('down'); return { items:[{ id:'ebay:1', title:'X', url:'https://www.ebay.com/itm/1', price:5, currency:'USD' }], total:1 }; } });
  await watch.add('demo-seller', 'ebay');
  fail = true;
  await watch.refresh();
  const status = await watch.status();
  assert.equal(status.offers.length, 1);
  assert.equal(status.sellers[0].error, 'Nabídky se nepodařilo načíst.');
});
