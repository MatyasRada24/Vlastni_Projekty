// Only synthetic test data is sent. The BMF API is for verification, never runtime payroll.
// Run explicitly: node tools/fetch_bmf_cases.cjs
const fs = require('fs');
const path = require('path');
const endpoint = 'https://www.bmf-steuerrechner.de/interface/2026Version1.xhtml?code=LSt2026ext&';
(async () => {
  const cases = [];
  const common = {LZZ:2, KVZ:'2.9', PVZ:1};
  for (const STKL of [1,2,3,4,5,6]) {
    for (const RE4 of [200001,400000,581250,845000,1500000,3000000]) {
      cases.push({...common, STKL, RE4});
    }
  }
  cases.push(
    {...common, STKL:4, RE4:555555, af:1, f:'0.823', R:1, ZKF:'1.5', PVS:1, PVZ:0, PVA:2},
    {...common, STKL:1, RE4:612345, KVZ:'2.69', R:1, ZKF:'0.5', PVZ:0, PVA:4},
    {...common, STKL:2, RE4:350000, PVZ:0, ZKF:1, LZZFREIB:20000},
    {...common, STKL:3, RE4:1000000, R:1, ZKF:2, PVZ:0},
    {...common, STKL:1, RE4:581251, R:1, PVS:1},
    {...common, STKL:1, RE4:300012, PVZ:0, KVZ:0},
  );
  const output = [];
  for (const input of cases) {
    const url = endpoint + new URLSearchParams(input);
    const response = await fetch(url);
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    const xml = await response.text();
    if (!xml.includes('status="ok"') || xml.includes('status="error"')) throw Error(xml);
    const expected = {};
    for (const m of xml.matchAll(/<ausgabe name="([^"]+)" value="([^"]+)"/g)) expected[m[1]]=m[2];
    if (!('LSTLZZ' in expected)) throw Error('Invalid BMF response');
    output.push({input, expected, xml});
    console.log(`${output.length}/${cases.length} STKL=${input.STKL} RE4=${input.RE4} LST=${expected.LSTLZZ}`);
  }
  fs.writeFileSync(path.join(__dirname,'../tests/bmf_cases.json'),JSON.stringify({
    source:endpoint, verified:'2026-10-02', cases:output
  },null,2));
})();
