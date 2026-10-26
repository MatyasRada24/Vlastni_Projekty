import robotsParser from 'robots-parser';

const allowedHosts = new Set(['www.bazos.cz', 'pc.bazos.cz', 'mobil.bazos.cz', 'aukro.cz', 'www.mironet.cz', 'www.k24.cz', 'www.apple.com']);
const agent = 'DealScout';
const cache = new Map();
let cacheBytes = 0;
const maxCacheBytes = 32 * 1024 * 1024;
const robots = new Map();
const queues = new Map();
const lastRequest = new Map();

export class SourceError extends Error {
  constructor(message, code = 'error') { super(message); this.code = code; }
}

function validateUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || !allowedHosts.has(url.hostname) || url.port || url.username || url.password) {
    throw new SourceError('Zdroj odkazuje mimo povolený web.');
  }
  return url;
}

async function paced(origin, fn, signal) {
  const previous = queues.get(origin) ?? Promise.resolve();
  const next = previous.catch(() => {}).then(async () => {
    signal?.throwIfAborted();
    const wait = Math.max(0, 1200 - (Date.now() - (lastRequest.get(origin) ?? 0)));
    if (wait) await new Promise(resolve => setTimeout(resolve, wait));
    signal?.throwIfAborted();
    lastRequest.set(origin, Date.now());
    return fn();
  });
  queues.set(origin, next.then(() => {}, () => {}));
  return next;
}

async function raw(url, signal) {
  return paced(url.origin, async () => {
    const response = await fetch(url, {
      redirect: 'manual', signal: AbortSignal.any([signal ?? new AbortController().signal, AbortSignal.timeout(18000)]),
      headers: { 'User-Agent': `${agent}/0.1 (personal marketplace search)`, 'Accept-Language': 'cs,en;q=0.8', Accept: 'text/html,text/plain' },
    });
    if ([301,302,303,307,308].includes(response.status)) {
      await response.body?.cancel();
      return { redirect: new URL(response.headers.get('location'), url).href };
    }
    if (!response.ok) {
      await response.body?.cancel();
      if ([403,429].includes(response.status)) throw new SourceError(`Web odmítl automatický přístup (HTTP ${response.status}). Zkus jej později nebo otevři ručně.`, 'blocked');
      if (response.status === 404) throw new SourceError('Stránka na zdroji neexistuje (HTTP 404).', 'not_found');
      throw new SourceError(`Zdroj vrátil HTTP ${response.status}.`);
    }
    const chunks = []; let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length;
      if (size > 8000000) throw new SourceError('Stránka přesáhla limit 8 MB.');
      chunks.push(chunk);
    }
    return { text: Buffer.concat(chunks).toString('utf8') };
  }, signal);
}

async function checkRobots(url, signal) {
  let policy = robots.get(url.origin);
  if (!policy || policy.expires < Date.now()) {
    try {
      const robotsUrl = new URL('/robots.txt', url);
      const result = await raw(robotsUrl, signal);
      if (result.redirect) throw new SourceError('Nelze ověřit robots.txt po přesměrování.');
      policy = { parser: robotsParser(robotsUrl.href, result.text), expires: Date.now() + 3600000 };
    } catch (e) {
      if (e.code !== 'not_found') throw e;
      policy = { parser: robotsParser(new URL('/robots.txt', url).href, ''), expires: Date.now() + 300000 };
    }
    robots.set(url.origin, policy);
  }
  if (policy.parser.isAllowed(url.href, agent) === false) throw new SourceError('Web nepovoluje automatické procházení této adresy v robots.txt.', 'blocked');
}

export async function getPage(value, signal, hops = 0) {
  const url = validateUrl(value);
  signal?.throwIfAborted();
  await checkRobots(url, signal);
  const cached = cache.get(url.href);
  if (cached && cached.expires > Date.now()) return { ...cached.value, cached: true };
  if (hops > 3) throw new SourceError('Příliš mnoho přesměrování.');
  const result = await raw(url, signal);
  if (result.redirect && /\/(?:altcha|captcha|challenge)\b/i.test(new URL(result.redirect, url).pathname)) throw new SourceError('Web vyžaduje ověření proti robotům. Agent ochranu neobchází.', 'blocked');
  if (result.redirect) return getPage(result.redirect, signal, hops + 1);
  if (/verify you are human|captcha challenge|access denied|just a moment\.\.\./i.test(result.text.slice(0,12000))) {
    throw new SourceError('Web vyžaduje ruční ověření. Agent ochranu neobchází.', 'blocked');
  }
  const valueResult = { html: result.text, url: url.href };
  for (const [key, entry] of cache) {
    if (entry.expires <= Date.now() || key === url.href) { cacheBytes -= entry.bytes; cache.delete(key); }
  }
  const bytes = Buffer.byteLength(result.text,'utf8');
  while (cache.size && (cache.size >= 180 || cacheBytes + bytes > maxCacheBytes)) {
    const key = cache.keys().next().value;
    cacheBytes -= cache.get(key).bytes; cache.delete(key);
  }
  cache.set(url.href, { value: valueResult, bytes, expires: Date.now() + 300000 });
  cacheBytes += bytes;
  return valueResult;
}
