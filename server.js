import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { searchSchema, categories } from './src/schema.js';
import { runAgent } from './src/agent.js';
import { priceRetailers } from './src/valuation.js';
import { cnbRates } from './src/rates.js';
import { store } from './src/store.js';
import { createWatcher, watchSchema } from './src/watch.js';

const jobs = new Map();
const staticFiles = { '/': ['index.html','text/html'], '/app.js': ['app.js','text/javascript'], '/pricing.js':['pricing.js','text/javascript'], '/style.css': ['style.css','text/css'], '/favicon.svg':['favicon.svg','image/svg+xml'], '/fonts/fonts.css':['fonts/fonts.css','text/css'] };
for (const family of ['geist','geist-mono','bricolage-grotesque']) for (const subset of ['latin','latin-ext']) {
  const file = `fonts/${family}-${subset}-wght-normal.woff2`;
  staticFiles[`/${file}`] = [file,'font/woff2'];
}
// Matching runs on the server with the full text; the card shows two lines, so polls carry only the start
// of each description instead of up to 14 000 characters per listing.
const publicJob = ({ controller, ...job }) => ({ ...job, items: (job.items ?? []).map(item => item.description?.length > 600 ? { ...item, description: `${item.description.slice(0, 600)}…` } : item) });
const watcher = createWatcher({ store, runAgent, jobs });

async function readBody(req) {
  if (!req.headers['content-type']?.startsWith('application/json')) throw Object.assign(new Error('Očekáván JSON.'), { status: 415 });
  let length = 0, chunks = [];
  for await (const chunk of req) {
    length += chunk.length;
    if (length > 16000) throw Object.assign(new Error('Požadavek je příliš velký.'), { status: 413 });
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw Object.assign(new Error('Neplatný JSON.'), { status: 400 }); }
}

export function createServer() {
  return http.createServer(async (req, res) => {
    const send = (status, data) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(data)); };
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://*.bazos.cz https://*.aukro.cz https://*.ebayimg.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
    try {
      const port = res.socket.localPort;
      const origins = [`http://127.0.0.1:${port}`, `http://localhost:${port}`];
      if (!origins.some(origin => new URL(origin).host === req.headers.host)) return send(403, { error: 'Nepovolený host.' });
      if (req.headers.origin && !origins.includes(req.headers.origin)) return send(403, { error: 'Nepovolený původ požadavku.' });
      const path = new URL(req.url, origins[0]).pathname;
      if (req.method === 'GET' && path === '/api/config') return send(200, {
        searchVersion: 4, limits: { pages: 100, detailLimit: 500, priceLookupLimit: 200 },
        priceSources:Object.values(priceRetailers).map(({id,name}) => ({id,name})),
        aiConfigured: Boolean(process.env.OPENAI_API_KEY), ebayConfigured: Boolean(process.env.EBAY_ACCESS_TOKEN || (process.env.EBAY_CLIENT_ID && process.env.EBAY_CLIENT_SECRET)),
        categories: Object.entries(categories).map(([id, { label }]) => ({ id, label })),
      });
      if (path === '/api/watch' && req.method === 'GET') return send(200, await watcher.status());
      if (path === '/api/watch' && req.method === 'POST') {
        const parsed = watchSchema.safeParse(await readBody(req));
        if (!parsed.success) return send(400, { error: 'Zkontroluj nastavení hlídání.', details: parsed.error.issues.map(x => x.message).join(' ') });
        return send(200, await watcher.configure(parsed.data));
      }
      if (path === '/api/watch/seen' && req.method === 'POST') { await readBody(req); return send(200, await watcher.markSeen()); }
      if (path === '/api/watch/clear' && req.method === 'POST') { await readBody(req); return send(200, await watcher.clear()); }
      if (path === '/api/hidden') {
        if (req.method === 'GET') return send(200, await store.hidden());
        if (req.method === 'POST') {
          const body = await readBody(req);
          if (typeof body?.id !== 'string' || !/^(?:bazos|aukro|ebay):\S{1,300}$/.test(body.id) || typeof body.hidden !== 'boolean') return send(400, { error: 'Neplatná nabídka.' });
          return send(200, await store.setHidden(body.id, body.hidden, typeof body.title === 'string' ? body.title : ''));
        }
      }
      if (req.method === 'GET' && path === '/api/rates') {
        try { return send(200, await cnbRates()); }
        catch { return send(502, { error: 'Kurzy ČNB se nepodařilo načíst. Použij ruční kurzy.' }); }
      }
      if (req.method === 'POST' && path === '/api/search') {
        const parsed = searchSchema.safeParse(await readBody(req));
        if (!parsed.success) return send(400, { error: 'Zkontroluj filtry.', details: parsed.error.issues.map(x => x.message).join(' ') });
        const busy = [...jobs.values()].find(j => j.status === 'running');
        if (busy) return send(409, { error: busy.watch ? 'Právě běží hlídání uloženého hledání. Zkus to za pár minut.' : 'Jiné vyhledávání právě běží. Vyčkej na dokončení.' });
        while (jobs.size >= 20) jobs.delete(jobs.keys().next().value);
        const job = { id: randomUUID(), status: 'running', phase: 'Připravuji hledání', createdAt: new Date().toISOString(), filters: parsed.data, plan: null, sources: {}, items: [], scanned: 0, controller: new AbortController() };
        jobs.set(job.id, job);
        void runAgent(job);
        return send(202, publicJob(job));
      }
      const match = path.match(/^\/api\/search\/([a-f0-9-]+)(\/cancel)?$/);
      if (match) {
        const job = jobs.get(match[1]);
        if (!job) return send(404, { error: 'Vyhledávání neexistuje nebo už vypršelo.' });
        if (req.method === 'POST' && match[2]) { await readBody(req); job.controller.abort(); return send(200, { status: 'cancelling' }); }
        if (req.method === 'GET' && !match[2]) return send(200, publicJob(job));
      }
      if (req.method === 'GET' && staticFiles[path]) {
        const [file, type] = staticFiles[path];
        const body = await readFile(new URL(`./public/${file}`, import.meta.url));
        res.writeHead(200, { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'no-cache' }); res.end(body); return;
      }
      send(404, { error: 'Nenalezeno.' });
    } catch (error) { send(error.status || 500, { error: error.status ? error.message : 'Neočekávaná chyba serveru.' }); }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3210);
  createServer().listen(port, '127.0.0.1', () => console.log(`Lovec nabídek běží na http://127.0.0.1:${port}`));
  void watcher.init();
}
