import { normalize, categories } from './schema.js';
import { productGroups, gamingTerms as gaming } from './vocabulary.js';


export function rulePlan(prompt, forcedCategory = null) {
  const text = normalize(prompt);
  // The form always names the category; the fallback only serves older callers and tests.
  const category = forcedCategory ?? (/telefon|phone|iphone|galaxy|pixel/.test(text) ? 'phones' : /stolni|pocitac|desktop|sestava/.test(text) ? 'desktops' : 'laptops');
  const damaged = /rozbit|nefunkc|nefung|nezap|nenab|netestovan|poskozen|na opravu|na dily|vadn|broken|for parts|faulty|untested|nejde zapnout/.test(text);
  const wantsGaming = /herni|gaming/.test(text);
  const termGroups = [[...productGroups[category]]];
  if (wantsGaming && category === 'laptops') termGroups.push(gaming);
  // Free text is treated as terms, never as executable instructions. Complex constraints need explicit filters or AI.
  const residual = text.replace(/na (?:opravu|dily)|nejde zapnout|stolni pc/g, '').split(/[^a-z0-9]+/).filter(w => (w.length > 1 || /^\d$/.test(w)) && !/^(hledam|najdi|chci|prosim|koupit|rozbit.*|nefunkc.*|nefung.*|nezap.*|nenab.*|netestovan.*|untested|poskozen.*|vadn.*|herni|gaming|notebook.*|laptop.*|grafick.*|kart.*|konzol.*|mobil.*|telefon.*|phone|pc|pocitac.*|stolni|desktop|sestava|komponent.*|pamet.*|procesor.*|zdroj.*|zakladni|desk.*|ram|cpu|gpu|ssd|psu|mb|broken|faulty|for|parts|do|od|kc|czk|korun|max|cena|levny|levne|levnou|levna|levneho|opravu|dily)$/.test(w));
  const withoutBudget = text.replace(/\b(?:do|od|max)\s+[\d\s.,]+\s*(?:kc|czk|korun)?/g, '');
  // The model is typed on purpose, so its words stay even when they also name other goods
  // ("ASUS ROG Strix B550-F" is a motherboard although ROG also names notebooks).
  const remaining = residual.filter(w => withoutBudget.split(/[^a-z0-9]+/).includes(w))
    // "Pixel 9" or "RTX 3060" is one model name: a lone "9" would also match the code "G9S9B" of a Pixel 6.
    .reduce((list, word) => {
      const previous = list.at(-1);
      if (previous && /^\d/.test(word) && !/\d/.test(previous) && Object.values(productGroups).some(group => group.includes(previous))) list[list.length - 1] = `${previous} ${word}`;
      else list.push(word);
      return list;
    }, []);
  for (const word of remaining.slice(0, 8)) termGroups.push([word]);
  const cs = { laptops: 'notebook', desktops: 'počítač', ram: 'paměť RAM', cpu: 'procesor', gpu: 'grafická karta', ssd: 'SSD', psu: 'zdroj', mb: 'základní deska', phones: 'telefon' }[category];
  const en = { laptops: 'laptop', desktops: 'desktop computer', ram: 'memory', cpu: 'processor', gpu: 'graphics card', ssd: 'ssd', psu: 'power supply', mb: 'motherboard', phones: 'phone' }[category];
  return { category, keywords: remaining.slice(0, 8), queryCs: [cs, ...remaining].join(' ').slice(0,160), queryEn: [wantsGaming && category === 'laptops' ? 'gaming' : '', en, ...remaining].filter(Boolean).join(' ').slice(0,160), termGroups, excludeTerms: [], damaged, explanation:'Lokální pravidla: synonyma produktu, herní výbava a zmínky o poškození. Cenu, lokalitu a další přesné požadavky nastav ve filtrech.' };
}

// Every search is the chosen category plus an optional model ("Legion 5", "Pixel 9", "RTX 4080").
// Condition, price and parameters come from the filters only, never from guessing at free text.
export async function createPlan(filters) {
  const plan = rulePlan(filters.prompt, filters.category);
  const model = plan.keywords.join(' ');
  plan.explanation = `${categories[filters.category].label}${model ? ` · model „${model}“: inzerát musí obsahovat každou část modelu` : ': všechny nabídky v kategorii'}. Stav, cenu a parametry určují filtry.`;
  // Keywords are what the marketplaces search for: model words plus required terms.
  // Without them Bazoš and Aukro only browse the newest listings of the whole category.
  const own = plan.keywords;
  // A chosen manufacturer narrows the search itself (Bazoš brand section, Aukro and eBay text), not just the filter.
  const brand = filters.brand && ['laptops','phones'].includes(plan.category) ? [filters.brand.toLowerCase()] : [];
  const keywords = [...new Set([...brand, ...own, ...filters.includeTerms].map(x => x.trim()).filter(Boolean))];
  plan.keywords = keywords.filter(word => !keywords.some(other => other !== word && normalize(other).split(/\s+/).includes(normalize(word))));
  const append = (query, term) => normalize(query).includes(normalize(term)) ? query : `${query} ${term}`.slice(0, 160);
  for (const term of filters.includeTerms) { plan.queryCs = append(plan.queryCs, term); plan.queryEn = append(plan.queryEn, term); }
  // "auto" is kept only for searches saved before the model field: damage words in their old description.
  if (filters.condition !== 'auto') plan.damaged = filters.condition === 'damaged';
  plan.excludeTerms = [...new Set([...plan.excludeTerms, ...filters.excludeTerms])];
  return { ...plan, warning: null };
}
