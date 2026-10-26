import assert from 'node:assert/strict';
import { getPage } from '../src/http.js';
import { parseBazos, parseAukro } from '../src/parsers.js';

for (const [source, url, parser] of [
  ['Bazoš','https://pc.bazos.cz/notebook/',parseBazos],
  ['Aukro','https://aukro.cz/notebooky-netbooky',parseAukro],
]) {
  try {
    const page = await getPage(url,new AbortController().signal);
    const result = parser(page.html,page.url);
    assert.ok(result.recognized,`${source}: nerozpoznaná struktura`);
    assert.ok(result.items.length > 0,`${source}: žádné nabídky pro ověření`);
    assert.ok(result.items.some(x => x.price !== null),`${source}: chybějí ceny`);
    console.log(`${source}: OK, ${result.items.length} nabídek, ${result.items.filter(x=>x.price !== null).length} s cenou.`);
  } catch(error) { console.error(`${source}: ${error.message}`); process.exitCode=1; }
}
console.log('eBay a OpenAI: živé volání vyžaduje vlastní klíče; tento test je nepoužívá.');
