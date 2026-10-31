const url = 'https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt';
let cache = null;

export function parseCnb(text) {
  const [header, , ...rows] = text.trim().split(/\r?\n/);
  const date = header.match(/^(\d{2})\.(\d{2})\.(\d{4})/);
  const rates = {};
  for (const row of rows) {
    const [, , amount, code, rate] = row.split('|');
    const value = Number(String(rate).replace(',', '.')) / Number(amount);
    if (['USD','EUR','GBP'].includes(code) && Number.isFinite(value) && value > 0) rates[code] = Math.round(value * 1000) / 1000;
  }
  if (!date || Object.keys(rates).length !== 3) throw new Error('Neočekávaný formát kurzovního lístku ČNB.');
  return { date: `${date[3]}-${date[2]}-${date[1]}`, rates };
}

// The ČNB publishes one list per business day; six hours of caching keeps requests minimal.
export async function cnbRates({ fetchFn = fetch, now = Date.now() } = {}) {
  if (cache && cache.expires > now) return cache.value;
  const response = await fetchFn(url, { signal: AbortSignal.timeout(10000), headers: { 'User-Agent': 'DealScout/0.1 (personal marketplace search)' } });
  if (!response.ok) throw new Error(`ČNB vrátila HTTP ${response.status}.`);
  const value = parseCnb(await response.text());
  cache = { value, expires: now + 6 * 3600000 };
  return value;
}
