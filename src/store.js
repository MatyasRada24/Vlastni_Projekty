import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const maxListings = 20000;

// Local JSON memory between runs: when a listing was first seen, its price history and hidden listings.
// Stored in data/ (git-ignored). Only listing ids, titles, URLs and prices; no seller contacts.
export function createStore(dir = fileURLToPath(new URL('../data/', import.meta.url))) {
  const file = join(dir, 'store.json');
  let state = null, saving = Promise.resolve();
  const load = async () => {
    if (state) return state;
    try { state = JSON.parse(await readFile(file, 'utf8')); } catch { state = {}; }
    state.listings ??= {}; state.hidden ??= {}; state.watch ??= null;
    return state;
  };
  const save = () => {
    saving = saving.then(async () => {
      await mkdir(dir, { recursive: true });
      const tmp = `${file}.tmp`;
      await writeFile(tmp, JSON.stringify(state));
      await rename(tmp, file);
    }).catch(() => {});
    return saving;
  };
  return {
    load, save,
    async annotate(items, now = new Date().toISOString()) {
      const s = await load();
      for (const item of items) {
        const rec = s.listings[item.id];
        const price = item.priceCzk ?? null;
        if (!rec) {
          s.listings[item.id] = { title:item.title, url:item.url, firstSeen:now, lastSeen:now, prices:[[now, price]] };
          item.history = { isNew:true, firstSeen:now, previousPrice:null, priceChange:null };
          continue;
        }
        const last = rec.prices.at(-1)?.[1] ?? null;
        if (price !== last) rec.prices.push([now, price]);
        rec.prices = rec.prices.slice(-20);
        rec.lastSeen = now; rec.title = item.title;
        const previous = [...rec.prices].reverse().find(([, p]) => p !== price)?.[1] ?? null;
        item.history = { isNew:false, firstSeen:rec.firstSeen, previousPrice:previous, priceChange: previous != null && price != null ? price - previous : null };
      }
      const ids = Object.keys(s.listings);
      if (ids.length > maxListings) ids.sort((a,b) => s.listings[a].lastSeen.localeCompare(s.listings[b].lastSeen)).slice(0, ids.length - maxListings).forEach(id => delete s.listings[id]);
      await save();
      return items;
    },
    async hidden() { return (await load()).hidden; },
    async setHidden(id, hidden, title = '') {
      const s = await load();
      if (hidden) s.hidden[id] = { title:String(title).slice(0,200), at:new Date().toISOString() }; else delete s.hidden[id];
      await save();
      return s.hidden;
    },
    async watch() { return (await load()).watch; },
    async setWatch(value) { (await load()).watch = value; await save(); return value; },
  };
}

// Test runs never touch the user's real data/ folder.
export const store = createStore(process.env.NODE_TEST_CONTEXT ? join(tmpdir(), `lovec-test-${process.pid}`) : undefined);
