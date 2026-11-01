import { z } from 'zod';
import { getPage, SourceError } from './http.js';
import { parseAukro, parseEbay } from './parsers.js';
import { ebayToken } from './sources.js';

const maxSellers = 30;
const maxOffers = 300;
const staleMs = 30 * 60000;
const intervalMs = 60 * 60000;
const logins = { aukro: /^[\p{L}\d._-]{2,64}$/u, ebay: /^[\w.*-]{2,64}$/ };
// Bazoš lists a seller's other ads only through hodnoceni.php / idphone= / idmail=, all disallowed in its robots.txt.
export const bazosSellerMessage = 'Bazoš nedovoluje automatické procházení inzerátů jednoho prodejce (robots.txt). Sledovat lze prodejce z Aukra a eBay.';

export const sellerInputSchema = z.object({ source: z.enum(['aukro','ebay']).optional(), input: z.string().trim().min(2).max(300) }).strict();

// Accepts a seller page URL (aukro.cz/uzivatel/x, ebay.com/usr/x, an eBay link with _ssn=x) or a bare login with a chosen web.
export function parseSeller(input, source) {
  const text = input.trim();
  let found;
  if (/^(?:https?:\/\/|www\.|[\w.-]*(?:aukro\.cz|bazos\.cz|ebay\.[a-z.]+)(?:\/|$))/i.test(text)) {
    let url;
    try { url = new URL(/^https?:\/\//i.test(text) ? text : `https://${text}`); } catch { throw new SourceError('Odkaz na prodejce není platný.'); }
    const host = url.hostname.replace(/^www\./, '');
    if (host === 'bazos.cz' || host.endsWith('.bazos.cz')) throw new SourceError(bazosSellerMessage);
    if (host === 'aukro.cz') found = { source:'aukro', login:url.pathname.match(/^\/uzivatel\/([^/]+)/)?.[1] };
    else if (/^ebay\.[a-z.]+$/.test(host)) found = { source:'ebay', login:url.pathname.match(/^\/usr\/([^/]+)/)?.[1] ?? url.searchParams.get('_ssn') ?? url.pathname.match(/^\/sch\/([^/]+)\/m\.html/)?.[1] };
    else throw new SourceError('Podporované jsou odkazy na prodejce z Aukra a eBay.');
    if (!found.login) throw new SourceError(found.source === 'aukro' ? 'V odkazu chybí prodejce. Použij adresu ve tvaru aukro.cz/uzivatel/jmeno.' : 'V odkazu chybí prodejce. Použij adresu ve tvaru ebay.com/usr/jmeno.');
    try { found.login = decodeURIComponent(found.login); } catch { throw new SourceError('Odkaz na prodejce není platný.'); }
  } else {
    if (!source) throw new SourceError('Vyber web prodejce, nebo vlož odkaz na jeho stránku.');
    found = { source, login:text.replace(/^@/, '') };
  }
  if (!logins[found.source].test(found.login)) throw new SourceError('Jméno prodejce obsahuje nepovolené znaky.');
  return { ...found, id:`${found.source}:${found.login.toLowerCase()}` };
}

export const sellerUrl = seller => seller.source === 'aukro' ? `https://aukro.cz/uzivatel/${encodeURIComponent(seller.login)}/nabidky` : `https://www.ebay.com/usr/${encodeURIComponent(seller.login)}`;

export async function fetchSellerOffers(seller, { signal = new AbortController().signal, getPage:pageFn = getPage, fetchFn = fetch, env = process.env } = {}) {
  const items = new Map();
  let total = null;
  if (seller.source === 'aukro') {
    for (let page = 1; page <= Math.ceil(maxOffers / 60); page++) {
      const url = new URL(sellerUrl(seller));
      if (page > 1) url.searchParams.set('page', String(page));
      let result;
      try { result = await pageFn(url.href, signal); }
      catch (error) { throw error.code === 'not_found' ? new SourceError('Prodejce na Aukru neexistuje. Zkontroluj jméno.', 'not_found') : error; }
      const parsed = parseAukro(result.html, result.url);
      if (!parsed.recognized) throw new SourceError('Stránku prodejce se nepodařilo rozpoznat. Zkontroluj jméno prodejce.', 'parser_error');
      const before = items.size;
      for (const item of parsed.items) items.set(item.id, item);
      if (items.size === before || parsed.items.length < 60) break;
    }
  } else {
    const token = await ebayToken(env, signal, fetchFn);
    for (let offset = 0; offset < maxOffers; offset += 100) {
      const url = new URL('https://api.ebay.com/buy/browse/v1/item_summary/search');
      // The seller filter needs a category; 0 is the eBay root, so every category the seller sells in.
      url.searchParams.set('category_ids', '0');
      url.searchParams.set('filter', `sellers:{${seller.login}},buyingOptions:{FIXED_PRICE|AUCTION}`);
      url.searchParams.set('limit', '100'); url.searchParams.set('offset', String(offset));
      const response = await fetchFn(url, {
        signal: AbortSignal.any([signal, AbortSignal.timeout(18000)]),
        // Unlike the search, no Czech delivery context: it hides every offer the seller does not ship to CZ.
        headers: { Authorization: `Bearer ${token}`, 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US' },
      });
      if (!response.ok) throw new SourceError(`eBay Browse API vrátilo HTTP ${response.status}.`, response.status === 429 ? 'blocked' : 'error');
      const data = await response.json();
      total = Number.isFinite(data.total) ? data.total : total;
      for (const item of parseEbay(data)) items.set(item.id, item);
      if (!data.next) break;
    }
  }
  return { items:[...items.values()].slice(0, maxOffers), total };
}

// Followed sellers live in the local store with their last known offers. An offer first seen after the
// user last opened the list is new; a lower price than the previous check is a price drop.
export function createSellerWatch({ store, fetchOffers = fetchSellerOffers, isBusy = () => false, now = () => Date.now(), setTimer = setInterval, clearTimer = clearInterval }) {
  let queue = Promise.resolve(), pending = 0, timer = null;
  const sellers = async () => { const state = await store.load(); state.sellers ??= []; return state.sellers; };
  const refreshOne = async seller => {
    const at = new Date(now()).toISOString();
    try {
      const { items, total } = await fetchOffers(seller);
      const known = new Map((seller.offers ?? []).map(offer => [offer.id, offer]));
      seller.offers = items.map(item => {
        const previous = known.get(item.id);
        const dropped = previous && item.price != null && previous.price != null && item.price < previous.price;
        return { id:item.id, title:item.title, url:item.url, price:item.price, currency:item.currency, image:item.image, saleType:item.saleType, endAt:item.endAt, location:item.location, condition:item.condition,
          firstSeen:previous?.firstSeen ?? at,
          previousPrice:dropped ? previous.price : item.price === previous?.price ? previous?.previousPrice ?? null : null,
          droppedAt:dropped ? at : item.price === previous?.price ? previous?.droppedAt ?? null : null };
      });
      seller.total = total ?? items.length; seller.error = null;
      seller.seenAt ??= at;
    } catch (error) {
      seller.error = error instanceof SourceError ? error.message : error?.name === 'TimeoutError' ? 'Web neodpověděl do 18 s.' : 'Nabídky se nepodařilo načíst.';
    }
    seller.checkedAt = at;
  };
  const refresh = ids => {
    pending++;
    queue = queue.then(async () => {
      for (const seller of await sellers()) if (!ids || ids.includes(seller.id)) { await refreshOne(seller); await store.save(); }
    }).catch(() => {}).finally(() => { pending--; });
    return queue;
  };
  const staleIds = async () => (await sellers()).filter(s => !s.checkedAt || now() - Date.parse(s.checkedAt) >= staleMs).map(s => s.id);
  const api = {
    async status() {
      const list = await sellers();
      const offers = list.flatMap(seller => (seller.offers ?? []).map(offer => ({ ...offer, sellerId:seller.id, seller:seller.login, source:seller.source,
        isNew: Boolean(seller.seenAt && offer.firstSeen > seller.seenAt), isCheaper: Boolean(seller.seenAt && offer.droppedAt && offer.droppedAt > seller.seenAt) })));
      return {
        sellers: list.map(({ offers:items, ...seller }) => ({ ...seller, url:sellerUrl(seller), count:items?.length ?? 0, newCount:offers.filter(o => o.sellerId === seller.id && (o.isNew || o.isCheaper)).length })),
        offers, newCount: offers.filter(o => o.isNew || o.isCheaper).length, refreshing: pending > 0,
      };
    },
    async add(input, source) {
      const parsed = parseSeller(input, source), list = await sellers();
      if (list.some(s => s.id === parsed.id)) throw new SourceError('Tohoto prodejce už sleduješ.');
      if (list.length >= maxSellers) throw new SourceError(`Sledovat lze nejvýše ${maxSellers} prodejců.`);
      list.push({ id:parsed.id, source:parsed.source, login:parsed.login, addedAt:new Date(now()).toISOString(), checkedAt:null, error:null, total:null, seenAt:null, offers:[] });
      await store.save();
      await refresh([parsed.id]);
      return api.status();
    },
    async remove(id) {
      const state = await store.load();
      state.sellers = (state.sellers ?? []).filter(s => s.id !== id);
      await store.save();
      return api.status();
    },
    async markSeen() {
      const at = new Date(now()).toISOString();
      for (const seller of await sellers()) if (seller.checkedAt && !seller.error) seller.seenAt = at;
      await store.save();
      return api.status();
    },
    refresh,
    // Opening the list or the hourly timer reloads only sellers older than 30 minutes, never beside a running search.
    async autoRefresh() { const ids = await staleIds(); if (ids.length && !pending && !isBusy()) void refresh(ids); },
    init() { timer = setTimer(() => { void api.autoRefresh(); }, intervalMs); timer.unref?.(); void api.autoRefresh(); },
    stop() { if (timer) clearTimer(timer); timer = null; },
  };
  return api;
}
