// Audit only: public BMF requests contain synthetic fixtures, never user data.
const fs = require('fs');
const crypto = require('crypto');
const root = require('path').join(__dirname, '..');
const endpoint = 'https://www.bmf-steuerrechner.de/interface/2026Version1.xhtml?code=LSt2026ext&';
async function get(url) {
  const response = await fetch(url, {signal: AbortSignal.timeout(30000)});
  if (!response.ok) throw Error(`HTTP ${response.status}`);
  return response.text();
}
(async () => {
  const xml = await get('https://www.bmf-steuerrechner.de/javax.faces.resource/daten/xmls/Lohnsteuer2026.xml.xhtml');
  fs.writeFileSync(`${root}/work/bmf-live-2026.xml`, xml);
  const local = fs.readFileSync(`${root}/vendor/Lohnsteuer2026.xml`, 'utf8');
  const normalized = text => text.replace(/\r\n/g, '\n').replace(/^\uFEFF/, '');
  const fixtures = JSON.parse(fs.readFileSync(`${root}/tests/bmf_cases.json`, 'utf8'));
  const report = {checked_at: new Date().toISOString(), source: endpoint,
    remote_xml_sha256: crypto.createHash('sha256').update(xml).digest('hex'),
    xml_equal_after_line_endings: normalized(xml) === normalized(local), cases: []};
  for (const c of fixtures.cases) {
    const response = await get(endpoint + new URLSearchParams(c.input));
    if (response.includes('status="error"')) throw Error(response);
    const outputs = Object.fromEntries([...response.matchAll(/<ausgabe name="([^"]+)" value="([^"]+)"/g)].map(m=>[m[1],m[2]]));
    if (Object.keys(outputs).length !== 12) throw Error('Missing BMF outputs');
    const differences = Object.entries(c.expected).filter(([k,v])=>v !== outputs[k]);
    report.cases.push({input:c.input, expected:outputs, differences});
  }
  fs.writeFileSync(`${root}/work/bmf-live-verification.json`, JSON.stringify(report,null,2));
  console.log(JSON.stringify({xml_equal_after_line_endings:report.xml_equal_after_line_endings,
    cases:report.cases.length, mismatches:report.cases.filter(c=>c.differences.length).length}));
})().catch(e=>{console.error(e);process.exitCode=1});
