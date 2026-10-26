import { normalize } from './schema.js';

export const regions = {
  praha:'Praha', stredocesky:'Středočeský', jihocesky:'Jihočeský', plzensky:'Plzeňský', karlovarsky:'Karlovarský', ustecky:'Ústecký', liberecky:'Liberecký',
  kralovehradecky:'Královéhradecký', pardubicky:'Pardubický', vysocina:'Vysočina', jihomoravsky:'Jihomoravský', olomoucky:'Olomoucký', zlinsky:'Zlínský', moravskoslezsky:'Moravskoslezský',
};

// Czech postcodes follow postal districts, which mostly but not exactly match regions.
// Three-digit exceptions refine the two-digit default.
const byPrefix3 = {
  393:'vysocina',394:'vysocina',395:'vysocina',396:'vysocina',
  506:'kralovehradecky',507:'kralovehradecky',508:'kralovehradecky',509:'kralovehradecky',512:'liberecky',513:'liberecky',514:'liberecky',
  569:'pardubicky',570:'pardubicky',571:'pardubicky',572:'pardubicky',
  674:'vysocina',675:'vysocina',676:'vysocina',
  686:'zlinsky',687:'zlinsky',688:'zlinsky',
  750:'olomoucky',751:'olomoucky',752:'olomoucky',753:'olomoucky',754:'zlinsky',755:'zlinsky',756:'zlinsky',757:'zlinsky',
  792:'moravskoslezsky',793:'moravskoslezsky',794:'moravskoslezsky',795:'moravskoslezsky',
};
const byPrefix2 = {
  10:'praha',11:'praha',12:'praha',13:'praha',14:'praha',15:'praha',16:'praha',17:'praha',18:'praha',19:'praha',
  25:'stredocesky',26:'stredocesky',27:'stredocesky',28:'stredocesky',29:'stredocesky',
  30:'plzensky',31:'plzensky',32:'plzensky',33:'plzensky',34:'plzensky',35:'karlovarsky',36:'karlovarsky',
  37:'jihocesky',38:'jihocesky',39:'jihocesky',40:'ustecky',41:'ustecky',43:'ustecky',44:'ustecky',46:'liberecky',47:'liberecky',
  50:'kralovehradecky',51:'kralovehradecky',53:'pardubicky',54:'kralovehradecky',55:'kralovehradecky',56:'pardubicky',57:'pardubicky',
  58:'vysocina',59:'vysocina',60:'jihomoravsky',61:'jihomoravsky',62:'jihomoravsky',63:'jihomoravsky',64:'jihomoravsky',66:'jihomoravsky',67:'jihomoravsky',68:'jihomoravsky',69:'jihomoravsky',
  70:'moravskoslezsky',71:'moravskoslezsky',72:'moravskoslezsky',73:'moravskoslezsky',74:'moravskoslezsky',76:'zlinsky',77:'olomoucky',78:'olomoucky',79:'olomoucky',
};
const cities = [
  ['praha','praha'],['brno','jihomoravsky'],['ostrava','moravskoslezsky'],['plzen','plzensky'],['liberec','liberecky'],['olomouc','olomoucky'],
  ['ceske budejovice','jihocesky'],['hradec kralove','kralovehradecky'],['usti nad labem','ustecky'],['pardubice','pardubicky'],['zlin','zlinsky'],
  ['jihlava','vysocina'],['karlovy vary','karlovarsky'],['kladno','stredocesky'],['opava','moravskoslezsky'],['havirov','moravskoslezsky'],['most','ustecky'],
];

export function regionOf(location) {
  const text = normalize(location);
  const psc = text.match(/\b(\d{3})\s?\d{2}\b/);
  if (psc) return byPrefix3[psc[1]] ?? byPrefix2[psc[1].slice(0,2)] ?? null;
  return cities.find(([name]) => new RegExp(`(?:^|[^a-z])${name}(?:[^a-z]|$)`).test(text))?.[1] ?? null;
}
