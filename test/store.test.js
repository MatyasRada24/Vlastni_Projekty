import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.js';

test('Remembers listings between runs: new, price drops and hidden listings persist on disk', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lovec-store-'));
  const first = createStore(dir);
  const [a] = await first.annotate([{ id:'bazos:1', title:'Legion', url:'https://pc.bazos.cz/inzerat/1/', priceCzk:6000 }], '2026-10-01T10:00:00.000Z');
  assert.equal(a.history.isNew, true);
  await first.setHidden('bazos:2', true, 'Překupník');

  const second = createStore(dir);
  const [b] = await second.annotate([{ id:'bazos:1', title:'Legion', url:'https://pc.bazos.cz/inzerat/1/', priceCzk:5200 }], '2026-10-05T10:00:00.000Z');
  assert.deepEqual(b.history, { isNew:false, firstSeen:'2026-10-01T10:00:00.000Z', previousPrice:6000, priceChange:-800 });
  assert.ok((await second.hidden())['bazos:2']);
  await second.setHidden('bazos:2', false);
  assert.deepEqual(JSON.parse(await readFile(join(dir, 'store.json'), 'utf8')).hidden, {});
});
