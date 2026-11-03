import test from 'node:test';
import assert from 'node:assert/strict';
import { extractPart, partMatches } from '../src/parts.js';
import { searchSchema } from '../src/schema.js';
import { evaluate } from '../src/matching.js';

const part = (title, kind, description = '') => extractPart({ title, description }, kind);

test('SSD listings give interface, capacity, read speed, endurance and health', () => {
  assert.deepEqual(part('Samsung 970 EVO Plus 1TB M.2 NVMe, čtení 3500 MB/s, 600 TBW', 'ssd'), { kind:'ssd', interface:'nvme', capacityGb:1000, readMbs:3500, tbw:600, healthPct:null });
  assert.equal(part('Crucial MX500 500GB SATA 2,5"', 'ssd').interface, 'sata');
  assert.equal(part('WD Blue M.2 SATA 1TB', 'ssd').interface, 'm2sata');
  assert.equal(part('Kingston M.2 512GB', 'ssd').interface, 'm2');
  assert.equal(part('SSD 256GB', 'ssd', 'Rychlost 3 500/3 000 MB/s, zdraví 97 %').readMbs, 3500);
  assert.equal(part('SSD 256GB', 'ssd', 'Zdraví disku: 97 %').healthPct, 97);
  assert.equal(part('SanDisk X400 512GB 2,5" SATA III – SMART 99 % – od 1 Kč', 'ssd').healthPct, 99);
  assert.equal(part('Samsung 860 EVO 500GB SSD – SATA – stav 97 % od 1 Kč', 'ssd').healthPct, 97);
  assert.equal(part('SSD 240GB SATA III 6Gb/s', 'ssd').capacityGb, 240, 'the link speed is no capacity');
});

test('GPU, CPU, RAM, PSU and motherboard parameters', () => {
  assert.deepEqual(part('Sapphire Radeon RX 580 8GB na opravu', 'gpu'), { kind:'gpu', chip:'amd', vramGb:8 });
  assert.equal(part('MSI GeForce RTX 3060 Ventus 12 GB GDDR6', 'gpu').vramGb, 12);
  assert.equal(part('Intel Core i5-12400F', 'cpu').socket, 'LGA1700', 'socket from the generation');
  assert.equal(part('AMD Ryzen 5 5600X 6 jader', 'cpu').socket, 'AM4');
  assert.equal(part('AMD Ryzen 7 7800X3D', 'cpu').cores, null);
  assert.equal(part('AMD Ryzen 5 5600X 6 jader', 'cpu').cores, 6);
  assert.equal(part('Procesor Intel Xeon E5-2680 v4 LGA 2011', 'cpu').socket, 'LGA2011');
  assert.equal(part('Intel Core i7-8550U', 'cpu').socket, null, 'notebook chips are soldered');
  assert.deepEqual(part('Kingston Fury 32GB (2x16GB) DDR4 3200MHz', 'ram'), { kind:'ram', memType:'ddr4', form:null, capacityGb:32, mhz:3200 });
  assert.deepEqual(part('RAM do notebooku SO-DIMM 8GB PC4-25600', 'ram'), { kind:'ram', memType:'ddr4', form:'sodimm', capacityGb:8, mhz:3200 });
  assert.deepEqual(part('Zdroj Seasonic Focus GX 750W 80+ Gold plně modulární', 'psu'), { kind:'psu', watts:750, efficiency:'gold', modular:'full' });
  assert.equal(part('PC zdroj Seasonic B12 BC-550 Bronze', 'psu', 'Výkon zdroje: 550 - 649 W; Účinnost: 81 - 82 %').watts, 550, 'an Aukro range is no value');
  assert.equal(part('PC zdroj EVGA 650 GM Gold', 'psu').watts, 650);
  assert.equal(part('Corsair RM750x', 'psu').watts, 750);
  assert.equal(part('Zdroj 500W nemodulární 80 Plus', 'psu').efficiency, 'white');
  assert.equal(part('Zdroj 500W nemodulární 80 Plus', 'psu').modular, 'none');
  assert.deepEqual(part('MSI B550 Tomahawk', 'mb'), { kind:'mb', socket:'AM4', memType:null, form:null });
  assert.deepEqual(part('ASUS Prime B660M-A D4 mATX DDR4 LGA1700', 'mb'), { kind:'mb', socket:'LGA1700', memType:'ddr4', form:'matx' });
});

test('Component filters check only their own kind, with unknown values following the switch', () => {
  const f = searchSchema.parse({ sources:['bazos'], category:'ssd', part:{ interface:'nvme', minReadMbs:3000 } });
  assert.equal(f.part.minTbw, null);
  const nvme = part('Samsung 980 1TB M.2 NVMe 3500 MB/s', 'ssd'), m2 = part('Kingston M.2 1TB', 'ssd');
  assert.ok(partMatches(nvme, f.part, 'ssd', false));
  assert.equal(partMatches(m2, f.part, 'ssd', false), false);
  assert.ok(partMatches(m2, f.part, 'ssd', true), 'plain M.2 may be NVMe');
  assert.ok(partMatches(m2, { ...f.part, interface:'m2', minReadMbs:null }, 'ssd', false));
  assert.equal(partMatches(part('Crucial MX500 SATA 2,5" 560 MB/s', 'ssd'), f.part, 'ssd', true), false);
  assert.ok(partMatches(nvme, { socket:'AM4' }, 'ssd', false), 'a CPU socket is no SSD filter');
  const psu = { minWatts:650, efficiency:'bronze', modular:'full' };
  assert.equal(partMatches(part('Zdroj 750W 80+ Gold modulární', 'psu'), psu, 'psu', false), false, '"modulární" may be semi-modular');
  assert.ok(partMatches(part('Zdroj 750W 80+ Gold modulární', 'psu'), { ...psu, modular:'semi' }, 'psu', false));
  assert.equal(partMatches(part('Zdroj 550W 80+ Gold', 'psu'), { minWatts:650 }, 'psu', true), false);
});

test('A component search applies its parameters to listings and shows them as specs', () => {
  const filters = searchSchema.parse({ sources:['bazos'], category:'ram', condition:'any', maxPrice:null, part:{ memType:'ddr4', minCapacityGb:16 } });
  const plan = { category:'ram', termGroups:[], excludeTerms:[], damaged:false };
  const item = (title, id) => ({ id, title, description:'', condition:'', category:'ram', price:500, currency:'CZK', location:'', saleType:'fixed', shipping:null });
  const hit = evaluate(item('Corsair Vengeance 2x8GB DDR4 3200', 'a'), plan, filters);
  assert.equal(hit.specs.capacityGb, 16);
  assert.equal(evaluate(item('Corsair 16GB DDR5 6000', 'b'), plan, filters), null);
  assert.equal(evaluate(item('Corsair 8GB DDR4', 'c'), plan, filters), null);
});
