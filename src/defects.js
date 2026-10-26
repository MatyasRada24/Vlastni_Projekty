import { normalize } from './schema.js';

// Ids are shared with the client: repair-cost settings are keyed by defect id.
export const defectTypes = [
  ['power','Nezapne se',/\b(?:nezapn\w*|nezapina|nejde zapnout|nelze zapnout|nejde spustit|nenabehne|nenabiha|nespusti|nereaguje|mrtv\w*|no power|wont turn on|won't turn on|does not power|dead)\b/],
  ['display','Displej / obraz',/\b(?:(?:praskl\w*|rozbit\w*|poskozen\w*|nesviti\w*|vadn\w*|nefunkcni)\s+(?:lcd|displej\w*|display|obrazovk\w*|panel\w*)|(?:lcd|displej\w*|display|obrazovk\w*)\s+(?:je\s+|mel\s+|ma\s+)?(?:praskl\w*|prasklin\w*|rozbit\w*|nesviti|nefunguje|vadn\w*|poskozen\w*)|obraz\w*(?:\s+\w+){0,2}\s+(?:zustava\s+)?(?:cern\w*|sed\w*)|(?:cern|sed)\w* obrazovk\w*|bez obrazu|nejde obraz|black screen|cracked screen|broken screen|no display)\b/],
  ['bios','BIOS / firmware',/\b(?:(?:po\s+)?aktualizac\w* bios\w*|bios\w*\s+(?:je\s+)?(?:potreba|nutne|treba)\s+(?:\w+\s+)?(?:preprogram\w*|vymen\w*|veminit|nahrat|prehrat|flash\w*)|(?:vadn\w*|poskozen\w*|odpalen\w*) bios\w*|preflash\w*|bios (?:corrupt\w*|chip))\b/],
  ['liquid','Polití',/\b(?:polit\w*|zalit\w*|po polit\w*|water damage\w*|liquid damage\w*|spill\w*)\b/],
  ['motherboard','Základní deska',/\b(?:(?:vadn\w*|odpalen\w*|spalen\w*|nefunkcni|poskozen\w*)\s+(?:zakladni\s+desk\w*|deska|desk\w*|mainboard\w*|motherboard)|(?:zakladni\s+desk\w*|mainboard|motherboard)\s+(?:je\s+)?(?:vadn\w*|odpalen\w*|spalen\w*|nefunguje|kaput)|zkrat\w*|dead motherboard|bad motherboard)\b/],
  ['gpu','Grafika / výkon / přehřívání',/\b(?:artefakt\w*|prehriv\w*|vypina se|reballing|gpu (?:je\s+)?(?:vadn\w*|odpalen\w*)|(?:hrozne |hodne |strasne )?sek(?:a|alo|ani|ne)\b|overheat\w*|artifacts?)\b/],
  ['charging','Nabíjení / napájení',/\b(?:nenabij\w*|nenabiji|nabijeci konektor|konektor napajeni|dc jack|power jack|not charging)\b/],
  ['keyboard','Klávesnice / touchpad',/\b(?:(?:klavesnic\w*|touchpad\w*|klaves\w*)\s+(?:nefunguj\w*|nejde|vadn\w*|chybi)|nefunkcni (?:klavesnic\w*|touchpad)|chybi klaves\w*|keyboard (?:not working|broken))\b/],
  ['chassis','Panty / šasi',/\b(?:panty?|pant\w*|sasi|kryt\w*|vik\w*)\s+(?:je\s+)?(?:praskl\w*|rozbit\w*|ulomen\w*|poskozen\w*|vylomen\w*)|(?:praskl\w*|rozbit\w*|ulomen\w*)\s+(?:panty?|pant\w*|sasi|kryt\w*|vik\w*)|broken hinges?\b/],
  ['battery','Baterie',/\b(?:baterie\s+(?:je\s+)?(?:nafouk\w*|mrtv\w*|nedrzi|vadn\w*|odumrel\w*)|nafouk\w* bateri\w*|bez baterie|swollen battery|battery (?:dead|swollen))\b/],
  ['untested','Netestováno / stav neznámý',/\b(?:netestovan\w*|neotestovan\w*|nezkousel\w*|neznam (?:jeho )?(?:stav|funkcnost)|stav neznam\w*|nalezov\w* stav|untested|not tested)\b/],
];

// "block" risks usually leave the laptop usable only for parts; "warn" adds cost or uncertainty.
const riskTypes = [
  ['bios','Zámek BIOSu / heslo','block',/\b(?:bios\w*\s+(?:je\s+)?(?:heslo|zamcen\w*|zablokovan\w*|locked)|heslo (?:do|na|v) bios\w*|zamcen\w* bios\w*|supervisor password|bios (?:password|lock\w*))\b/],
  ['icloud','iCloud / aktivační zámek','block',/\b(?:icloud\s+(?:zamek|lock\w*|zamcen\w*|zablokovan\w*|neodhlasen\w*|prihlasen\w*)|aktivacni zamek|activation lock|zamcen\w* (?:na )?icloud|mdm\s+(?:zamek|lock|profil\w*))\b/],
  ['locked','Zablokované / blokace','block',/\b(?:computrace|absolute persistence|blacklist\w*|kradeny|kradenu|ztraceny rezim|stolen)\b/],
  ['parts','Chybí díly','warn',/\b(?:bez (?:disk\w*|ssd|hdd|ram|pameti|klavesnice|displeje|lcd|baterie|zakladni desky)|bez\s*:\s*[•\s]*(?:baterie|adapter\w*|hdd|ssd|ram|disk\w*)|(?:ram|hdd|ssd|disk)\s+bez\b|chybi (?:disk|ssd|hdd|ram|pamet|klavesnice|displej|baterie|kryt|sroub\w*)|(?:neni|nema)(?: v nem)? (?:disk|ssd|hdd|ram|spodni kryt)|nema spodni kryt|ssd\s+(?:\w+\s+){0,3}vyjmut\w*|no (?:ssd|hdd|ram|storage|battery))\b/],
  ['charger','Bez nabíječky','warn',/\b(?:bez (?:nabijecky|adapteru|zdroje|nabijeky)|(?:napajeci )?adapter (?:neni|nebude) soucasti|nemam (?:k nemu )?nabijecku|no charger|no (?:power )?adapter)\b/],
  ['repair','Předchozí pokus o opravu','warn',/\b(?:neuspesn\w* oprav\w*|po (?:neuspesne )?oprav\w*|rozebran\w*|rozdelan\w*|nekompletni|chybi sroub\w*|byl v servis\w*)\b/],
];
// Sellers often state the absence of a risk: "bez hesla v BIOSu", "odhlášený z iCloudu".
const negations = /\b(?:bez hesla|neni (?:zamcen\w*|zablokovan\w*|blokovan\w*)|nema (?:heslo|zamek|blokaci)|odhlasen\w*(?: (?:z|od))? icloud\w*|odhlaseny|neblokovan\w*|bez blokace|bez zamku|no (?:bios )?password|not locked|icloud (?:je )?odhlasen\w*|vcetne nabijecky|s nabijeckou|nabijecka (?:je )?soucasti)\b/;

export function classifyListing(item) {
  const text = normalize(`${item.title}. ${item.description}. ${item.condition}`)
    .replace(/(?:neni|nejsou|nebyl\w*|not|never)\s+(?:nijak\s+)?(?:poskozen\w*|rozbit\w*|vadn\w*|nefunkcn\w*|praskl\w*|polit\w*|broken|damaged)/g, ' ');
  const defects = defectTypes.filter(([, , re]) => re.test(text)).map(([id,label]) => ({id,label}));
  const riskText = text.replace(new RegExp(negations.source, 'g'), ' ');
  const risks = riskTypes.filter(([, , , re]) => re.test(riskText)).map(([id,label,level]) => ({id,label,level}));
  return { defects, risks };
}
