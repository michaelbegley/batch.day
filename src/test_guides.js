// What every guide page must show, worked out here from engine.js and the written rules, not from guides.js.
// Prints {cases, static}. cases: per page, stepper settings and the text the calculator must show (breakit10.py sets them in a browser).
// static: checks on the built files in site/ (the answer paragraph, the tables, the engine copy). Run: node test_guides.js
const E = require('./engine.js'), fs = require('fs');
const POTS = [3, 4, 6, 8, 12, 16, 20];
const S = [], cases = {};
const log = (n, ok, note) => S.push([n, ok ? 'ok' : 'FAIL', String(note == null ? '' : note)]);
const N = (n, w) => n + ' ' + w + (n === 1 ? '' : 's');
const FX = (f) => String(Math.round(f * 10) / 10);
const P = E.parseRecipe;
const agree = [];
const same = (what, rule, engine) => { if (!String(engine).includes(String(rule))) agree.push(`${what}: rule says ${rule}, engine says ${engine}`); };

// rice with no amount: a third of a cup dry per meal, to the nearest half cup, pot a quarter full at most (cooked, it triples to three-quarters)
function rice(m) {
  const dry = m / 3, n = E.fmtNum(Math.max(.5, Math.round(dry * 2) / 2)), pot = POTS.find((p) => p >= dry / 4 / (1 / 4)), k = Math.ceil(dry / 20); // written the way the engine divides, so 80 meals (26⅔ cups, a hair over a third of 20 qt in floating point) lands where the engine puts it
  const e = E.batchDay(P('Dinner\nServes 1\n- jasmine rice, to serve'), m);
  same('rice ' + m, n + ' cups dry (about ⅓ cup per meal', e.items[0].scaled); same('rice pot ' + m, pot ? 'Rice pot: ' + pot + ' qt' : `Cook it in ${k} pots or rounds`, e.pots.join(' '));
  return { set: { meals: m }, big: n + (n === '1' || n === '½' ? ' cup' : ' cups'), sub: [N(m, 'meal'), pot ? `${pot} qt pot` : `${k} pots or rounds`] };
}
function wt(oz) { return oz >= 16 ? E.fmtNum(Math.round(oz / 16 * 4) / 4) + ' lb' : E.fmtNum(Math.max(.5, Math.round(oz * 2) / 2)) + ' oz'; } // never "0 oz"
function chicken(m, s, lb) {
  const big = wt(lb * 16 * m / s), each = wt(lb * 16 / s), b = Math.max(1, Math.ceil(lb * m / s / 1.5));
  same(`chicken ${m}/${s}/${lb}`, big, E.scaleAll(P('A\nServes ' + s + '\n' + lb + ' lb chicken breast'), m).items[0].scaled);
  same(`sear ${m}/${s}/${lb}`, `Searing: ${b} batch`, E.batchDay(P('A\nServes ' + s + '\n' + lb + ' lb pork shoulder\n1. Brown the pork.'), m).pots.join(' '));
  return { set: { meals: m, serves: s, lb }, big, sub: (each.startsWith('0 ') ? [] : [each + ' a meal']).concat([b === 1 ? '1 batch ' : b + ' batches ']) };
}
// the example recipe, one ingredient at a time
const EX = [['1 lb', 'chicken thighs', 1], ['2 cups', 'chicken broth', 1], ['1 cup', 'rice', 1], ['2 cloves', 'garlic', 1], ['1 tsp', 'salt', .7], ['2 tsp', 'chili powder', .75], ['2 tbsp', 'olive oil', .6]];
function rows(serves, want) {
  const f = want / serves;
  return EX.map(([amt, name, ease]) => {
    const i = E.scaleAll(P('A\nServes ' + serves + '\n' + amt + ' ' + name), want).items[0], k = f > 2 ? (2 + ease * (f - 2)) / f : 1;
    if (Math.abs(i.qtyScaled - parseFloat(amt) * f * k) > 1e-9) agree.push(`${name} at ${f}x: engine ${i.qtyScaled}, rule ${parseFloat(amt) * f * k}`);
    return [name + (f > 2 && ease < 1 ? ' eased back' : ''), amt, i.scaled];
  });
}
function pot(qt, x) {
  const cups = qt * 4 * x, p = POTS.find((q) => q >= cups / 4 / .75), k = Math.ceil(cups / 60);
  same(`pot ${qt}x${x}`, p ? `Main pot: ${p} qt` : `Use ${k} big pots`, E.batchDay(P('Chili\nServes 2\n' + qt * 4 + ' cups beef broth'), 2 * x).pots[0]);
  return { set: { qt, x }, big: p ? `${p} qt pot` : `${k} big pots`, sub: [`About ${cups} cups`, p ? 'under ¾ full' : `${k} big pots`] };
}
function ricepot(c) {
  const p = POTS.find((q) => q >= c), k = Math.ceil(c / 20);
  same('rice pot for ' + c, p ? `Rice pot: ${p} qt` : `Cook it in ${k} pots or rounds`, E.batchDay(P('R\nServes 2\n1 cup basmati rice'), 2 * c).pots.join(' '));
  return { set: { cups: c }, big: p ? `${p} qt pot` : `${k} pots`, sub: [N(c, 'cup') + ' of dry rice', 'about ' + N(c * 3, 'meal')].concat(p ? [] : [`${k} pots or rounds`]) };
}
function bake(makes, want) {
  const f = want / makes, n = Math.ceil(f / 2), each = E.fmtNum(f / n);
  const note = E.batchDay(P('Cookies\nServes ' + makes + '\n2 cups flour\n1 tsp baking soda\n1 cup sugar\n1 egg'), want).notes.join(' ');
  if (f > 2) same(`bake ${makes}->${want}`, `Make ${n} batches of ${each}x`, note); else same(`bake ${makes}->${want}`, 'Baking: measure carefully', note);
  return f > 2 ? { set: { makes, want }, big: `${n} batches`, sub: [`${each}× the recipe`] } : { set: { makes, want }, big: '1 batch', sub: [`${FX(f)}× the recipe`, 'Measure carefully'] };
}
const tpl = fs.readFileSync('template.html', 'utf8'), SAMPLE = /const SAMPLE=`([\s\S]*?)`;/.exec(tpl)[1];
function shop(m) {
  const g = E.batchDay(P(SAMPLE), m).grocery, order = E.aisles(g);
  const list = []; order.forEach((s) => { list.push('#' + s.name); s.items.forEach((i) => list.push(i.amt === 'for serving' ? `${i.name} for serving` : `${i.amt ? i.amt + ' ' : ''}${i.name}`)); });
  return { set: { meals: m }, big: N(g.length, 'item'), sub: [N(m, 'meal')], list };
}
function sear(lb) {
  const n = Math.max(1, Math.ceil(lb / 1.5));
  const p = E.batchDay(P('B\nServes 1\n' + lb + ' lb ground beef\n1. Brown the beef.'), 1);
  same('sear ' + lb, `Searing: ${n} batch`, p.pots.join(' ')); same('sear minutes ' + lb, 'Sear in batches:' + n * 6, p.order.map((o) => o.t + ':' + o.min).join('|'));
  return { set: { lb }, big: n === 1 ? '1 batch' : `${n} batches`, sub: [`About ${N(n * 6, 'minute')}`, '12-inch pan'] };
}
const M = [1, 2, 13, 14, 15, 27, 99, 999];
cases['how-much-rice-for-meal-prep'] = M.concat([3, 5, 7, 10, 21, 80, 81]).map(rice);
cases['how-much-chicken-for-meal-prep'] = M.map((m) => chicken(m, 4, 1.5)).concat([chicken(14, 1, 1.5), chicken(14, 99, 1.5), chicken(14, 4, .5), chicken(14, 4, 2), chicken(1, 99, .5)]);
cases['how-to-scale-a-recipe-for-meal-prep'] = M.map((m) => ({ set: { meals: m, serves: 4 }, big: FX(m / 4) + '×', sub: [N(m, 'meal')], rows: rows(4, m) })).concat([[8, 4], [9, 4], [14, 1], [14, 99], [6, 3], [7, 3]].map(([m, s]) => ({ set: { meals: m, serves: s }, big: FX(m / s) + '×', sub: [N(m, 'meal')], rows: rows(s, m) })));
cases['what-size-pot-for-a-double-batch'] = [[2, 2], [2, 3], [1, 1], [14, 1], [20, 1], [20, 10], [1, 10], [3, 2], [5, 3], [5, 4], [4, 4]].map(([q, n]) => pot(q, n));
cases['how-much-rice-fits-in-a-pot'] = [1, 4, 5, 6, 8, 9, 14, 26, 27, 99].map(ricepot);
cases['how-to-double-a-recipe'] = [1, 4, 5, 14, 99].map((s) => ({ set: { serves: s }, big: N(s * 2, 'serving'), sub: ['2× the recipe'], rows: rows(s, s * 2) }));
cases['how-to-triple-a-recipe'] = [1, 4, 5, 14, 99].map((s) => ({ set: { serves: s }, big: N(s * 3, 'serving'), sub: ['3× the recipe'], rows: rows(s, s * 3) }));
cases['can-you-double-a-baking-recipe'] = [[12, 36], [12, 12], [12, 24], [12, 25], [12, 48], [12, 60], [12, 1], [1, 14], [1, 99], [99, 14], [14, 99], [12, 999]].map(([a, b]) => bake(a, b));
cases['tiktok-recipe-to-grocery-list'] = M.map(shop);
cases['how-much-meat-to-brown-at-once'] = [1, 2, 3, 4, 5, 14, 99].map(sear);
log('the written rules and engine.js agree on every case', !agree.length, agree.slice(0, 6).join('; '));

// ---- the built pages ----
const page = (s) => fs.readFileSync('site/' + s + '.html', 'utf8');
const txt = (h) => h.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
const lead = (s) => txt(/<p class="lead">([\s\S]*?)<\/p>/.exec(page(s))[1]);
const has = (s, list) => { const l = lead(s), miss = list.filter((w) => !l.includes(w)); log(`${s}: the answer paragraph has ${list.join(', ')}`, !miss.length, miss.length ? `missing ${miss.join(', ')} in: ${l}` : ''); };
const mult = (name, ease) => String(Math.round((2 + ease) * 100) / 100) + '×';
has('how-much-rice-for-meal-prep', ['For 14 meals', rice(14).big, rice(14).sub[1], '⅓ cup']);
has('how-much-chicken-for-meal-prep', ['1½ lb', '4 servings', chicken(14, 4, 1.5).big + ' for 14 meals', wt(1.5 * 16 / 4) + ' a meal']);
has('how-to-scale-a-recipe-for-meal-prep', ['70% for salt', '75% for spices', '60% for oil', "that's 3.5×", 'becomes ' + rows(4, 14)[0][2], 'becomes ' + rows(4, 14)[4][2]]);
has('what-size-pot-for-a-double-batch', ['three-quarters', '2 quarts', `a ${pot(2, 2).big} doubled`, `an ${pot(2, 3).big} tripled`]);
const fit = (q) => Math.floor(q * 4 / 4 + 1e-9);
has('how-much-rice-fits-in-a-pot', ['a quarter', `${fit(3)} cups of dry rice in a 3 qt pot`, `${fit(4)} cups in a 4 qt pot`, `${fit(6)} cups in a 6 qt pot`]);
has('how-to-double-a-recipe', ['by 2', 'three-quarters']);
has('how-to-triple-a-recipe', ['by 3', 'salt at ' + mult('salt', .7), 'spices at ' + mult('spice', .75), 'oil at ' + mult('oil', .6), `${bake(1, 3).big} of ${bake(1, 3).sub[0].split(' ')[0]} each`]);
has('can-you-double-a-baking-recipe', [`${bake(1, 3).big} of ${bake(1, 3).sub[0].split(' ')[0]} each`]);
has('tiktok-recipe-to-grocery-list', [shop(14).big + ' for 14 meals', 'store order']);
has('how-much-meat-to-brown-at-once', ['1½ lb', '12-inch pan', '5 lb takes ' + sear(5).big]);

// static tables
const table = (s, cap) => { const h = page(s), a = h.indexOf('<h2>' + cap + '</h2>'); if (a < 0) return null; const t = /<table class="tbl">([\s\S]*?)<\/table>/.exec(h.slice(a))[1]; return [...t.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/g)].map((c) => txt(c[1]))).slice(1); };
{ const t = table('what-size-pot-for-a-double-batch', 'Pot sizes') || [], bad = t.filter((r) => { const q = parseInt(r[0]); return r[1] !== pot(q, 2).big || r[2] !== pot(q, 3).big; }); log('pot page: every row of the table is the ¾-full rule', t.length >= 4 && !bad.length, JSON.stringify(bad.length ? bad : t)); }
{ const t = table('how-much-rice-fits-in-a-pot', 'Dry rice by pot size') || [], bad = t.filter((r) => { const q = parseInt(r[0]), c = fit(q); return r[1] !== N(c, 'cup') || r[2] !== 'About ' + c * 3 || ricepot(c).big !== q + ' qt pot' || ricepot(c + 1).big === q + ' qt pot'; }); log('rice pot page: every pot size, with the most whole cups that fit and no more', t.map((r) => parseInt(r[0])).join() === POTS.join() && !bad.length, JSON.stringify(bad.length ? bad : t)); }
const FRAC = { '⅛': .125, '¼': .25, '⅓': 1 / 3, '½': .5, '⅔': 2 / 3, '¾': .75 }, TSP = { tsp: 1, tbsp: 3, cup: 48, cups: 48 };
const tsp = (s) => { const m = /^(\d+)?([⅛¼⅓½⅔¾])? (\w+)$/.exec(s); return ((+m[1] || 0) + (FRAC[m[2]] || 0)) * TSP[m[3]]; };
for (const [s, cap, f] of [['how-to-double-a-recipe', 'Common amounts, doubled', 2], ['how-to-triple-a-recipe', 'Common amounts, tripled', 3]]) {
  const t = table(s, cap) || [], bad = t.filter((r) => Math.abs(tsp(r[1]) - tsp(r[0]) * f) > 1e-6 || E.scaleAll(P('W\nServes 1\n' + r[0] + ' milk'), f).items[0].scaled !== r[1]);
  log(`${s}: "${cap}" rows are exact (${t.length} rows) and are what the engine gives`, t.length >= 6 && !bad.length, JSON.stringify(bad.length ? bad : t));
}
log('site/engine.js is engine.js, byte for byte', fs.readFileSync('site/engine.js', 'utf8') === fs.readFileSync('engine.js', 'utf8'));
process.stdout.write(JSON.stringify({ cases, static: S }));
if (S.some((r) => r[1] === 'FAIL')) process.exitCode = 1;
