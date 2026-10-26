import { load } from 'cheerio';
import { clean, parsePrice, safeUrl } from './schema.js';

function baseItem(source, id, title, url) {
  return { id: `${source}:${id}`, source, title: clean(title), url, description: '', price: null, currency: 'CZK', shipping: null, image: null, location: '', condition: '', saleType: 'unknown', endAt: null, detailRead: false };
}

export function parseBazos(html, pageUrl) {
  const $ = load(html), items = [];
  $('.inzeraty').each((_, element) => {
    const row = $(element), link = row.find('h2 a').first();
    const url = safeUrl(link.attr('href'), pageUrl, ['bazos.cz']);
    const id = url?.match(/\/inzerat\/(\d+)\//)?.[1];
    if (!id || !clean(link.text())) return;
    const item = baseItem('bazos', id, link.text(), url);
    item.description = clean(row.find('.popis').text());
    item.price = parsePrice(row.find('.inzeratycena').text());
    item.location = clean(row.find('.inzeratylok').text());
    item.image = safeUrl(row.find('img.obrazek').attr('src'), pageUrl, ['bazos.cz']);
    item.saleType = 'classified';
    items.push(item);
  });
  return { items, recognized: items.length > 0 || /Zobrazeno\s+0|Nebyly nalezeny|nebyl nalezen|inzerátů z\s*0/i.test($.text()) };
}

function jsonScripts($) {
  return $('script[type="application/ld+json"]').toArray().flatMap(el => {
    try { const json = JSON.parse($(el).text()); return Array.isArray(json) ? json : [json]; } catch { return []; }
  });
}

export function parseAukro(html, pageUrl, now = Date.now()) {
  const $ = load(html), items = [];
  // Only the main search response embedded in public HTML, never recommended-item carousels.
  let state;
  try { state = JSON.parse($('#ng-state').text()); } catch { state = null; }
  const responses = Object.entries(state?.aukCache ?? {}).filter(([key]) => key.includes('/offers/searchItemsCommon'));
  let recognized = false;
  for (const [, response] of responses) {
    const rows = response?.b?.content;
    if (!Array.isArray(rows)) continue;
    recognized = true;
    for (const row of rows) {
      if (row.itemState && row.itemState !== 'ACTIVE') continue;
      if (row.endingTime && Date.parse(row.endingTime) < now) continue;
      const url = safeUrl(`/${row.seoUrl}-${row.itemId}`, pageUrl, ['aukro.cz']);
      if (!url || !row.itemId || !row.itemName || !row.seoUrl) continue;
      const item = baseItem('aukro', row.itemId, row.itemName, url);
      item.price = parsePrice(row.price?.amount);
      item.currency = row.price?.currency || 'CZK';
      item.condition = clean(row.attributes?.find(a => a.attributeName === 'Stav zboží')?.attributeValue);
      item.description = (row.attributes ?? []).map(a => `${a.attributeName}: ${a.attributeValue}`).join('; ');
      item.image = safeUrl(row.titleImageUrl || row.titleImage?.url, pageUrl, ['aukro.cz']);
      item.location = clean(`${row.location ?? ''} ${row.postcode ?? ''}`);
      item.saleType = row.auction === true ? 'auction' : row.auction === false ? 'fixed' : 'unknown';
      item.endAt = row.endingTime || null;
      const withShipping = parsePrice(row.priceWithShipping?.amount);
      if (item.price !== null && withShipping !== null && row.priceWithShipping?.currency === item.currency) item.shipping = Math.max(0, withShipping - item.price);
      items.push(item);
    }
  }
  if (!recognized) {
    for (const doc of jsonScripts($)) {
      const list = doc.mainEntity?.itemListElement;
      if (!Array.isArray(list)) continue;
      recognized = true;
      for (const entry of list) {
        const product = entry.item || entry;
        if (product['@type'] !== 'Product') continue;
        const url = safeUrl(product.url, pageUrl, ['aukro.cz']);
        if (!url) continue;
        const item = baseItem('aukro', product.sku || url, product.name, url);
        const offer = Array.isArray(product.offers) ? product.offers[0] : product.offers;
        item.price = parsePrice(offer?.price);
        item.currency = offer?.priceCurrency || 'CZK';
        item.image = safeUrl(Array.isArray(product.image) ? product.image[0] : product.image, pageUrl, ['aukro.cz']);
        items.push(item);
      }
    }
  }
  return { items: [...new Map(items.map(x => [x.id, x])).values()], recognized };
}

// Keeps line structure as " • " so "RAM: 16 GB<br>SSD: 512 GB" stays two separate values.
function textWithBreaks(root) {
  root.find('br').replaceWith('\n');
  root.find('p,div,li,tr,h1,h2,h3,h4').each((_, el) => { root.find(el).append('\n'); });
  return root.text().split('\n').map(clean).filter(Boolean).join(' • ');
}

function aukroDetail($) {
  let state;
  try { state = JSON.parse($('#ng-state').text()); } catch { return null; }
  const detail = Object.entries(state?.aukCache ?? {}).find(([key]) => key.includes('/offerDetail'))?.[1]?.b;
  if (!detail) return null;
  // The JSON-LD description is cut after ~300 characters; specifications are usually further down.
  const html = detail.descriptionInHtml ? load(String(detail.descriptionInHtml)) : null;
  const text = html ? textWithBreaks(html('body')) : clean(detail.descriptionStripped);
  const attributes = (detail.attributes ?? []).map(a => `${clean(a.attributeName)}: ${clean(a.attributeValue)}`).join('; ');
  return [text, attributes].filter(Boolean).join(' • ') || null;
}

export function extractDescription(html, source) {
  const $ = load(html);
  if (source === 'bazos') return textWithBreaks($('.popisdetail')).slice(0,12000);
  const detail = aukroDetail($);
  if (detail) return detail.slice(0,12000);
  if ($('#user-field').length) return textWithBreaks($('#user-field')).slice(0,12000);
  for (const doc of jsonScripts($)) {
    const products = [doc, ...(doc['@graph'] ?? [])];
    const product = products.find(x => x['@type'] === 'Product');
    if (product?.description) return clean(load(String(product.description)).text()).slice(0,12000);
  }
  return clean($('[itemprop="description"]').text()).slice(0,12000);
}

export function parseEbay(data, now = Date.now()) {
  return (data.itemSummaries ?? []).filter(row => !row.itemEndDate || Date.parse(row.itemEndDate) >= now).flatMap(row => {
    const url = safeUrl(row.itemWebUrl, 'https://www.ebay.com', ['ebay.com']);
    if (!url || !row.itemId || !row.title) return [];
    const item = baseItem('ebay', row.itemId, row.title, url);
    const auctionOnly = row.buyingOptions?.includes('AUCTION') && !row.buyingOptions?.includes('FIXED_PRICE');
    const price = auctionOnly ? row.currentBidPrice : row.price;
    item.price = parsePrice(price?.value);
    item.currency = price?.currency || 'USD';
    item.saleType = auctionOnly ? 'auction' : row.buyingOptions?.includes('FIXED_PRICE') ? 'fixed' : 'unknown';
    item.condition = clean(row.condition);
    item.conditionId = row.conditionId;
    item.description = clean(row.shortDescription);
    item.image = safeUrl(row.image?.imageUrl, 'https://www.ebay.com', ['ebayimg.com']);
    item.location = clean([row.itemLocation?.city, row.itemLocation?.country].filter(Boolean).join(', '));
    item.endAt = row.itemEndDate ?? null;
    const costs = (row.shippingOptions ?? []).filter(o => o.shippingCost?.currency === item.currency).map(o => parsePrice(o.shippingCost.value)).filter(x => x !== null);
    item.shipping = costs.length ? Math.min(...costs) : null;
    return [item];
  });
}
