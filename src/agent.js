import { createPlan } from './planner.js';
import { collectSource } from './sources.js';
import { evaluate } from './matching.js';
import { enrichValuations } from './valuation.js';
import { store } from './store.js';

export async function runAgent(job, dependencies = {}) {
  const signal = job.controller.signal;
  try {
    job.phase = 'Sestavuji vyhledávací plán';
    job.plan = await (dependencies.createPlan ?? createPlan)(job.filters, { signal });
    signal.throwIfAborted();
    job.phase = 'Procházím vybrané zdroje';
    const bySource = new Map();
    const evaluated = new Map();
    const updateResults = () => {
      const unique = new Map([...bySource.values()].flat().map(item => [item.id,item]));
      job.items = [...unique.values()].map(item => {
        // Previously scanned records are immutable except for detail enrichment. Avoid re-matching thousands on every tick.
        const cached = evaluated.get(item.id);
        if (cached?.item === item && cached.description === item.description && cached.detailRead === item.detailRead) return cached.result;
        const result = evaluate(item,job.plan,job.filters);
        evaluated.set(item.id,{item,description:item.description,detailRead:item.detailRead,result});
        return result;
      }).filter(Boolean).sort((a,b) => b.score - a.score || (a.priceCzk ?? Infinity) - (b.priceCzk ?? Infinity));
      job.scanned = unique.size;
    };
    const sourceResults = await Promise.all(job.filters.sources.map(source =>
      (dependencies.collectSource ?? collectSource)(source, job.plan, job.filters, (report, items) => {
        job.sources[source] = report;
        if (items) { bySource.set(source,items); updateResults(); }
      }, signal)
    ));
    const unique = new Map(sourceResults.flatMap(x => x.items).map(item => [item.id, item]));
    job.items = [...unique.values()].map(item => evaluate(item, job.plan, job.filters)).filter(Boolean).sort((a,b) => b.score - a.score || (a.priceCzk ?? Infinity) - (b.priceCzk ?? Infinity));
    job.scanned = unique.size;
    if (!signal.aborted && job.filters.lookupNewPrices && job.plan.category === 'laptops') await enrichValuations(job,signal,{...dependencies,marketListings:[...unique.values()]});
    if (dependencies.store !== null) await (dependencies.store ?? store).annotate(job.items).catch(() => {});
    job.status = signal.aborted ? 'cancelled' : 'done';
    job.phase = signal.aborted ? 'Zastaveno — dostupné výsledky zachovány' : 'Vyhledávání dokončeno';
  } catch (error) {
    job.status = signal.aborted ? 'cancelled' : 'error';
    job.phase = signal.aborted ? 'Vyhledávání zastaveno' : 'Vyhledávání se nepodařilo dokončit';
  } finally {
    for (const item of job.items ?? []) if (item.valuation?.status === 'pending') item.valuation = {status:'cancelled',message:'Ověření ceny nebylo dokončeno.'};
    job.finishedAt = new Date().toISOString();
  }
}
