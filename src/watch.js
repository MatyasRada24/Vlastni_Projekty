import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { searchSchema } from './schema.js';

export const watchSchema = z.object({
  enabled: z.boolean(),
  intervalMinutes: z.number().int().min(30).max(1440),
  minProfit: z.number().min(-1000000).max(10000000).nullable(),
  filters: z.unknown().transform((value, ctx) => {
    const parsed = searchSchema.safeParse(value);
    if (!parsed.success) { ctx.addIssue({ code:'custom', message:'Hledání pro hlídání není platné.' }); return z.NEVER; }
    return parsed.data;
  }),
}).strict();

const maxAlerts = 100;

// Runs the saved search on a timer while the local server runs. Only listings that are new or cheaper
// since the previous run become alerts; the profit threshold uses the gross difference known to the server.
export function createWatcher({ store, runAgent, jobs, now = () => Date.now(), setTimer = setTimeout, clearTimer = clearTimeout }) {
  let timer = null, running = false, lastRun = null, nextRun = null, lastError = null;
  const schedule = async () => {
    if (timer) clearTimer(timer);
    timer = null; nextRun = null;
    const config = await store.watch();
    if (!config?.enabled) return;
    const wait = config.intervalMinutes * 60000;
    nextRun = new Date(now() + wait).toISOString();
    timer = setTimer(() => { void tick(); }, wait);
    timer.unref?.();
  };
  const tick = async () => {
    const config = await store.watch();
    if (!config?.enabled) return;
    // Never run beside a manual search: both would share the same per-site request pacing.
    if (running || [...jobs.values()].some(j => j.status === 'running')) { await schedule(); return; }
    running = true; lastError = null;
    const job = { id: randomUUID(), watch: true, status:'running', phase:'Hlídání', createdAt:new Date(now()).toISOString(), filters: config.filters, plan:null, sources:{}, items:[], scanned:0, controller:new AbortController() };
    jobs.set(job.id, job);
    try {
      await runAgent(job);
      const fresh = job.items.filter(item => item.history?.isNew || item.history?.priceChange < 0)
        .filter(item => config.minProfit == null || (item.valuation?.calculation?.grossProfit ?? -Infinity) >= config.minProfit);
      const state = await store.load();
      const known = new Set((state.watchAlerts ?? []).map(a => `${a.id}:${a.priceCzk}`));
      const alerts = fresh.filter(item => !known.has(`${item.id}:${item.priceCzk}`)).map(item => ({
        id:item.id, title:item.title, url:item.url, source:item.source, priceCzk:item.priceCzk, endAt:item.endAt ?? null,
        grossProfit:item.valuation?.calculation?.grossProfit ?? null, reason:item.history?.isNew ? 'new' : 'cheaper', previousPrice:item.history?.previousPrice ?? null,
        foundAt:new Date(now()).toISOString(), seen:false,
      }));
      state.watchAlerts = [...alerts, ...(state.watchAlerts ?? [])].slice(0, maxAlerts);
      await store.save();
      if (job.status === 'error') lastError = 'Hledání se nepodařilo dokončit.';
    } catch { lastError = 'Hlídání selhalo.'; }
    finally { running = false; lastRun = new Date(now()).toISOString(); jobs.delete(job.id); await schedule(); }
  };
  return {
    init: schedule,
    tick,
    async status() {
      const state = await store.load();
      return { config: state.watch ?? null, running, lastRun, nextRun, lastError, alerts: state.watchAlerts ?? [] };
    },
    async configure(value) { await store.setWatch(value); await schedule(); return this.status(); },
    async markSeen() { const state = await store.load(); for (const a of state.watchAlerts ?? []) a.seen = true; await store.save(); return this.status(); },
    async clear() { const state = await store.load(); state.watchAlerts = []; await store.save(); return this.status(); },
    stop() { if (timer) clearTimer(timer); timer = null; },
  };
}
