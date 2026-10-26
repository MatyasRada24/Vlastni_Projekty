import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createStore } from '../src/store.js';
import { createWatcher, watchSchema } from '../src/watch.js';

const filters = { prompt:'Rozbitý herní notebook', sources:['bazos'] };

test('Watch config is validated and the interval cannot be shorter than 30 minutes', () => {
  assert.equal(watchSchema.safeParse({ enabled:true, intervalMinutes:10, minProfit:null, filters }).success, false);
  assert.equal(watchSchema.safeParse({ enabled:true, intervalMinutes:60, minProfit:2000, filters:{ prompt:'x', sources:['bazos'] } }).success, false);
  assert.equal(watchSchema.parse({ enabled:true, intervalMinutes:60, minProfit:2000, filters }).filters.pages, 20);
});

test('Watcher alerts only on new or cheaper listings above the threshold, once, and skips during a manual search', async () => {
  const store = createStore(await mkdtemp(join(tmpdir(), 'lovec-watch-')));
  const timers = [], jobs = new Map();
  let run = 0;
  const runAgent = async job => {
    run++;
    job.items = [
      { id:'bazos:1', title:'Legion', url:'https://pc.bazos.cz/inzerat/1/', source:'bazos', priceCzk:4000, valuation:{ calculation:{ grossProfit:9000 } } },
      { id:'bazos:2', title:'IdeaPad', url:'https://pc.bazos.cz/inzerat/2/', source:'bazos', priceCzk:3000, valuation:{ calculation:{ grossProfit:500 } } },
    ];
    await store.annotate(job.items);
    job.status = 'done';
  };
  const watcher = createWatcher({ store, runAgent, jobs, setTimer:(fn, ms) => { timers.push(ms); return { unref(){} }; }, clearTimer:() => {} });
  await watcher.configure(watchSchema.parse({ enabled:true, intervalMinutes:60, minProfit:2000, filters }));
  assert.equal(timers.at(-1), 3600000);

  await watcher.tick();
  let status = await watcher.status();
  assert.deepEqual(status.alerts.map(a => [a.id, a.reason]), [['bazos:1','new']]);

  await watcher.tick();
  assert.equal((await watcher.status()).alerts.length, 1);

  jobs.set('manual', { status:'running' });
  await watcher.tick();
  assert.equal(run, 2);
  jobs.clear();

  status = await watcher.markSeen();
  assert.equal(status.alerts[0].seen, true);
  assert.equal((await watcher.clear()).alerts.length, 0);
});
