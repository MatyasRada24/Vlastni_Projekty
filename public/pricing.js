const round = value => Math.round((value + Number.EPSILON) * 100) / 100;

export function calculateProfit(newPriceCzk, purchasePriceCzk, targetProfit = 0) {
  if (!Number.isFinite(newPriceCzk) || newPriceCzk <= 0) return null;
  return {
    resaleEstimate: round(newPriceCzk * 0.75),
    grossProfit: Number.isFinite(purchasePriceCzk) && purchasePriceCzk >= 0 ? round(newPriceCzk * 0.75 - purchasePriceCzk) : null,
    maxPurchasePrice: round(newPriceCzk * 0.75 - targetProfit), targetProfit,
  };
}

// Rough Czech repair estimates (parts + own work); the user adjusts them in settings.
export const defaultCosts = {
  repair: { power:1500, display:1800, bios:800, liquid:2000, motherboard:3000, gpu:2500, charging:600, keyboard:900, chassis:800, battery:1000, untested:1500, unknown:1500 },
  risk: { parts:800, charger:400, repair:500 },
  shipping: 120, feePercent: 0, sellFeePercent: 0,
};
export const costLabels = {
  power:'Nezapne se', display:'Displej / obraz', bios:'BIOS / firmware', liquid:'Polití', motherboard:'Základní deska', gpu:'Grafika / přehřívání', charging:'Nabíjení',
  keyboard:'Klávesnice / touchpad', chassis:'Panty / šasi', battery:'Baterie', untested:'Netestováno', unknown:'Závada neuvedena',
  parts:'Chybějící díly', charger:'Chybějící nabíječka', repair:'Po pokusu o opravu',
};

export function mergeCosts(saved) {
  const costs = structuredClone(defaultCosts);
  if (!saved || typeof saved !== 'object') return costs;
  for (const group of ['repair','risk']) for (const key of Object.keys(costs[group])) if (Number.isFinite(saved[group]?.[key]) && saved[group][key] >= 0) costs[group][key] = saved[group][key];
  for (const key of ['shipping','feePercent','sellFeePercent']) if (Number.isFinite(saved[key]) && saved[key] >= 0) costs[key] = saved[key];
  return costs;
}

// Net estimate = resale − purchase − shipping − repair − buyer fees − import costs − selling fee.
// Several defects add up; an unknown purchase price keeps the result unknown.
export function calculateNet(resale, item, costs = defaultCosts, targetProfit = 0, importCzk = 0) {
  if (!Number.isFinite(resale) || resale <= 0) return null;
  const lines = [];
  for (const d of item.defects ?? []) if (costs.repair[d.id] != null) lines.push({ label: costLabels[d.id] ?? d.label, czk: costs.repair[d.id] });
  for (const r of item.risks ?? []) if (costs.risk[r.id] != null) lines.push({ label: costLabels[r.id] ?? r.label, czk: costs.risk[r.id] });
  const repair = lines.reduce((sum, l) => sum + l.czk, 0);
  const shipping = Number.isFinite(item.shippingCzk) ? item.shippingCzk : costs.shipping;
  const sellFee = resale * costs.sellFeePercent / 100;
  const fixed = shipping + repair + importCzk + sellFee;
  const purchase = Number.isFinite(item.priceCzk) && item.priceCzk >= 0 ? item.priceCzk : null;
  const fee = purchase == null ? 0 : purchase * costs.feePercent / 100;
  return {
    netProfit: purchase == null ? null : round(resale - purchase - fee - fixed),
    maxPurchasePrice: round((resale - fixed - targetProfit) / (1 + costs.feePercent / 100)),
    repair: round(repair), repairLines: lines, shipping: round(shipping), shippingEstimated: !Number.isFinite(item.shippingCzk),
    fee: round(fee), sellFee: round(sellFee), importCzk: round(importCzk), targetProfit,
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
