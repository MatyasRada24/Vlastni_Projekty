import { categories } from './schema.js';
import { getPage, SourceError } from './http.js';
import { parseBazos, parseAukro, parseEbay, extractDescription } from './parsers.js';
import { detailCandidate, productMatches, damageEvidence } from './matching.js';
import { groupMatches } from './vocabulary.js';

export const sourceNames = { bazos: 'Bazoš', aukro: 'Aukro', ebay: 'eBay' };

export function searchUrl(source, plan, page = 1) {
  const category = categories[plan.category];
  if (source === 'bazos') return `${category.bazos}${page > 1 ? `${(page - 1) * 20}/` : ''}`;
  if (source === 'aukro') {
    const url = new URL(category.aukro || 'https://aukro.cz/vysledky-vyhledavani');
    if (!category.aukro) url.searchParams.set('text', plan.queryCs);
    if (page > 1) url.searchParams.set('page', String(page));
    return url.href;
  }
  const url = new URL('https://www.ebay.com/sch/i.html');
  url.searchParams.set('_nkw', plan.queryEn);
  if (category.ebay) url.searchParams.set('_sacat', category.ebay);
  if (plan.damaged) url.searchParams.set('LH_ItemCondition', '7000');
  return url.href;
}

let tokenCache;
async function ebayToken(env, signal, fetchFn) {
  if (env.EBAY_ACCESS_TOKEN) return env.EBAY_ACCESS_TOKEN;
  if (!env.EBAY_CLIENT_ID || !env.EBAY_CLIENT_SECRET) throw new SourceError('Pro eBay doplň produkční EBAY_CLIENT_ID a EBAY_CLIENT_SECRET do .env (nebo EBAY_ACCESS_TOKEN).', 'not_configured');
  if (tokenCache && tokenCache.expires > Date.now()) return tokenCache.token;
  const response = await fetchFn('https://api.ebay.com/identity/v1/oauth2/token', {
    method: 'POST', signal: AbortSignal.any([signal, AbortSignal.timeout(18000)]),
    headers: { Authorization: `Basic ${Buffer.from(`${env.EBAY_CLIENT_ID}:${env.EBAY_CLIENT_SECRET}`).toString('base64')}`, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'client_credentials', scope: 'https://api.ebay.com/oauth/api_scope' }).toString(),
  });
  if (!response.ok) {
    const code = await response.json().then(body => body?.error, () => null);
    // eBay distinguishes a disabled/wrong keyset from a keyset that is valid but lacks OAuth.
    throw new SourceError(code === 'unauthorized_client'
      ? 'eBay klíče přijal, ale keyset nemá povolený OAuth (HTTP 401 unauthorized_client). V developer portálu u keysetu klikni na „Enable OAuth“; změna se může projevit až po několika minutách.'
      : response.status === 401
        ? 'eBay odmítl klíče (HTTP 401). Produkční keyset bývá neaktivní, dokud v developer portálu nenastavíš „Marketplace account deletion“ (výjimka „I do not persist eBay data“). Ověř také, že Cert ID patří ke stejnému keysetu.'
        : `eBay nepřijal přihlašovací údaje (HTTP ${response.status}). Zkontroluj produkční klíče.`, 'error');
  }
  const data = await response.json();
  if (!data.access_token) throw new SourceError('eBay nevrátil přístupový token.');
  tokenCache = { token: data.access_token, expires: Date.now() + Math.max(0, Number(data.expires_in) - 120) * 1000 };
  return tokenCache.token;
}

export async function collectSource(source, plan, filters, progress, signal, dependencies = {}) {
  const pageFn = dependencies.getPage ?? getPage, fetchFn = dependencies.fetchFn ?? fetch, env = dependencies.env ?? process.env;
  const items = new Map();
  const report = { source, name: sourceNames[source], status: 'running', pages: 0, scanned: 0, details: 0, detailCandidates: 0, detailLimit: filters.detailLimit ?? 60, discoveryPages: 0, cachedPages: 0, warnings: [], url: searchUrl(source, plan), message: 'Načítám nabídky…' };
  const emit = () => progress({ ...report, warnings: [...report.warnings] }, [...items.values()]);
  emit();
  try {
    const token = source === 'ebay' ? await ebayToken(env, signal, fetchFn) : null;
    const seenPages = new Set();
    const streams = [{ offset: 0, done: false, broad: false }];
    // Every fourth API page explores the whole category, catching omitted keywords and misclassified condition.
    // Both streams share the user's total page budget; each has its own pagination and deduplication.
    if (source === 'ebay' && filters.pages >= 4 && categories[plan.category].ebay) streams.push({offset:0,done:false,broad:true});
    for (let page = 1; page <= filters.pages; page++) {
      signal.throwIfAborted();
      report.message = `Procházím stránku ${page} z ${filters.pages}`; emit();
      let parsed, exhausted = false, stream;
      if (source === 'ebay') {
        stream = (page % 4 === 0 ? streams[1] : streams[0]);
        if (!stream || stream.done) stream = streams.find(x => !x.done);
        if (!stream) break;
        const url = new URL('https://api.ebay.com/buy/browse/v1/item_summary/search');
        url.searchParams.set('fieldgroups', 'EXTENDED');
        if (!stream.broad) url.searchParams.set('q', plan.queryEn);
        url.searchParams.set('limit', '50'); url.searchParams.set('offset', String(stream.offset));
        if (categories[plan.category].ebay) url.searchParams.set('category_ids', categories[plan.category].ebay);
        const queryFilters = [filters.includeAuctions ? 'buyingOptions:{FIXED_PRICE|AUCTION}' : 'buyingOptions:{FIXED_PRICE}'];
        if (plan.damaged && !stream.broad) queryFilters.push('conditionIds:{7000}');
        url.searchParams.set('filter', queryFilters.join(','));
        const response = await fetchFn(url, {
          signal: AbortSignal.any([signal, AbortSignal.timeout(18000)]),
          headers: { Authorization: `Bearer ${token}`, 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US', 'X-EBAY-C-ENDUSERCTX': 'contextualLocation=country%3DCZ' },
        });
        if (!response.ok) {
          if (response.status === 401) tokenCache = null;
          throw new SourceError(`eBay Browse API vrátilo HTTP ${response.status}. Ověř platnost tokenu a oprávnění k produkčnímu API.`, response.status === 429 ? 'blocked' : 'error');
        }
        const data = await response.json();
        if (data.errors?.length) throw new SourceError('eBay odmítlo vyhledávací požadavek.');
        parsed = { items: parseEbay(data), recognized: true };
        stream.offset += 50;
        stream.done = !data.next;
        if (stream.broad) report.discoveryPages++;
        exhausted = streams.every(x => x.done);
      } else {
        const result = await pageFn(searchUrl(source, plan, page), signal);
        report.cachedPages += result.cached ? 1 : 0;
        parsed = source === 'bazos' ? parseBazos(result.html, result.url) : parseAukro(result.html, result.url);
        if (!parsed.recognized) throw new SourceError('Strukturu stránky se nepodařilo rozpoznat. Nejde o ověřený prázdný výsledek.', 'parser_error');
      }
      report.pages++;
      const signature = `${stream?.broad ?? false}:` + parsed.items.map(x => x.id).sort().join('|');
      const repeated = parsed.items.length > 0 && seenPages.has(signature);
      seenPages.add(signature);
      for (const item of parsed.items) {
        // Only infer category from a real category page/API category, never an unrestricted keyword result.
        if (source === 'bazos' || source === 'ebay' || categories[plan.category].aukro) item.category = plan.category;
        items.set(item.id, item);
      }
      report.scanned = items.size; emit();
      if (stream && (repeated || !parsed.items.length)) stream.done = true;
      if (exhausted || (stream ? streams.every(x => x.done) : (!parsed.items.length || repeated))) break;
    }
    if (source !== 'ebay') {
      const relevance = item => plan.termGroups.filter(group => groupMatches(item, group, plan.category)).length;
      const pending = [...items.values()].filter(item => detailCandidate(item, plan, filters));
      const needsCondition = item => plan.damaged && !damageEvidence(item).length;
      pending.sort((a,b) => Number(needsCondition(b)) - Number(needsCondition(a)) || Number(productMatches(b,plan,filters)) - Number(productMatches(a,plan,filters)) || relevance(b) - relevance(a));
      report.detailCandidates = pending.length;
      const candidates = pending.slice(0, report.detailLimit);
      if (pending.length > candidates.length) report.warnings.push(`Limit popisů: ${pending.length - candidates.length} dalších kandidátů zůstane bez přečteného detailu. Pro širší záběr zvyš počet popisů.`);
      for (const item of candidates) {
        signal.throwIfAborted();
        report.message = `Čtu popis ${report.details + 1} z ${candidates.length}`; emit();
        try {
          const result = await pageFn(item.url, signal);
          const description = extractDescription(result.html, source);
          if (description) { item.description = `${item.description} ${description}`.slice(0,14000); item.detailRead = true; }
          else if (!report.warnings.includes('U některých nabídek se nepodařilo načíst celý popis.')) report.warnings.push('U některých nabídek se nepodařilo načíst celý popis.');
          report.details++;
        } catch (error) {
          if (signal.aborted) throw error;
          if (!report.warnings.includes('Část podrobných popisů nebyla dostupná.')) report.warnings.push('Část podrobných popisů nebyla dostupná.');
          if (error.code === 'blocked') throw error;
        }
        emit();
      }
    }
    report.status = 'done';
    report.message = `Prohlédnuto ${report.scanned} nabídek na ${report.pages} stránkách.`;
  } catch (error) {
    report.status = signal.aborted ? 'cancelled' : items.size ? 'partial' : (error.code || 'error');
    report.message = signal.aborted ? 'Vyhledávání zastaveno.' : error instanceof SourceError ? error.message : 'Zdroj není dostupný nebo vypršel čas připojení. Zkus hledání později.';
  }
  report.warnings = [...new Set(report.warnings)];
  emit();
  return { items: [...items.values()], report };
}
