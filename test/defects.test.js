import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyListing } from '../src/defects.js';

const ids = (title, description = '') => { const c = classifyListing({title, description, condition:''}); return { defects:c.defects.map(d => d.id), risks:c.risks.map(r => r.id) }; };

test('Classifies common defects from real listing wording', () => {
  assert.deepEqual(ids('Acer Nitro 5','Jednoho dne se vypnul a už se nezapnul. Byl v servise, kde mi bylo řečeno, že je vadná základní deska.').defects, ['power','motherboard']);
  assert.deepEqual(ids('Legion 5','Po aktualizaci BIOSu se zapne, obraz však zůstává černý.').defects, ['display','bios']);
  assert.deepEqual(ids('Macbook Pro A1278','Po zapnutí je jen šedá obrazovka.').defects, ['display']);
  assert.deepEqual(ids('Notebook po polití','Polita klávesnice.').defects, ['liquid']);
  assert.deepEqual(ids('Legion','Když si chtěl něco zahrát, tak se to hrozně sekalo.').defects, ['gpu']);
  assert.deepEqual(ids('Samsung i7','Nezkoušel jsem ho zapnout, neznám jeho stav.').defects, ['untested']);
});

test('Flags locks and missing parts, but respects sellers ruling them out', () => {
  assert.deepEqual(ids('ThinkPad T480','Heslo v BIOSu, nevím ho.').risks, ['bios']);
  assert.deepEqual(ids('MacBook Air','Zamčený na iCloud, na díly.').risks, ['icloud']);
  assert.deepEqual(ids('ThinkPad','Bez hesla v BIOSu, odhlášený z iCloudu.').risks, []);
  assert.deepEqual(ids('HP Compaq CQ58','BEZ: • BATERIE • ADAPTÉRU • HDD').risks, ['parts']);
  assert.deepEqual(ids('Dell Latitude 5480','RAM bez • HDD bez • Napájecí adaptér NENÍ součástí této aukce').risks, ['parts','charger']);
  assert.deepEqual(ids('Dell','Displej není poškozený, vše funguje.').defects, []);
});
