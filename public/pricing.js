const round = value => Math.round((value + Number.EPSILON) * 100) / 100;

export function calculateProfit(newPriceCzk, purchasePriceCzk, targetProfit = 0) {
  if (!Number.isFinite(newPriceCzk) || newPriceCzk <= 0) return null;
  return {
    resaleEstimate: round(newPriceCzk * 0.75),
    grossProfit: Number.isFinite(purchasePriceCzk) && purchasePriceCzk >= 0 ? round(newPriceCzk * 0.75 - purchasePriceCzk) : null,
    maxPurchasePrice: round(newPriceCzk * 0.75 - targetProfit), targetProfit,
  };
}

export function validateManualPrice(value) {
  if (!value || !Number.isFinite(value.priceCzk) || value.priceCzk <= 0 || value.priceCzk > 10000000) throw new Error('Zadej cenu nového kusu větší než 0 Kč, nejvýše 10 000 000 Kč.');
  let url;
  try { url = new URL(value.url); } catch { throw new Error('Přidej platný odkaz na zdroj ceny.'); }
  if (url.protocol !== 'https:' || url.username || url.password || !url.hostname.includes('.') || value.url.length > 2000) throw new Error('Použij úplný HTTPS odkaz na produkt, bez přihlašovacích údajů.');
  if (value.confirmed !== true) throw new Error('Potvrď, že jde o nový kus se shodnou konfigurací.');
  return {priceCzk:round(value.priceCzk),url:url.href,note:String(value.note ?? '').trim().slice(0,180),confirmed:true,enteredAt: typeof value.enteredAt === 'string' && Number.isFinite(Date.parse(value.enteredAt)) ? value.enteredAt : new Date().toISOString()};
}

export function withManualPrice(item, manual, targetProfit = 0) {
  if (!manual) return item;
  try {
    const entry = validateManualPrice(manual);
    return {...item,valuation:{...item.valuation,status:'manual',reference:{priceCzk:entry.priceCzk,url:entry.url,title:entry.note || 'Cena zadaná uživatelem',source:new URL(entry.url).hostname,match:'manual',enteredAt:entry.enteredAt},calculation:calculateProfit(entry.priceCzk,item.priceCzk,targetProfit)}};
  } catch { return item; }
}
