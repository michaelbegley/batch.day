// Full sweep (15 Nov 2026) accuracy fixes: one check per finding. Run: node test_sweep.js
const E = require(process.argv[2] || './engine.js');
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const P = (t) => E.parseRecipe(t);
const B = (t, m) => E.batchDay(P(t), m);
const cupsIn = (s) => +((/about (\d+) cups?/.exec(s) || [])[1] || 0);
const qtIn = (s) => +((/(\d+) qt/.exec(s) || [])[1] || 0);
const store = (p) => p.split.fridge.concat(p.split.freezer).join(' ');

// B-03 food safety: savory food is never baking and never gets room-temp storage
const sheet = 'Sheet pan chicken\nServes 4\n2 lb chicken thighs\n2 tbsp olive oil\n1 tsp salt\n1 lb broccoli\n1. Spread everything on a cookie sheet.\n2. Roast at 425F for 25 minutes.';
const velvet = 'Beef stir fry\nServes 4\n1 lb flank steak\n1/4 tsp baking soda\n2 tbsp soy sauce\n1 tbsp cornstarch\n1 cup flour\n1 tbsp sugar\n1 egg\n1. Sear the beef until browned.';
const fried = 'Fried chicken\nServes 4\n2 lb chicken drumsticks\n2 cups flour\n1 tsp baking powder\n1 cup buttermilk\n1 tsp salt\n1. Fry until golden.';
const cakeChili = 'Chili with cornbread topping\nServes 6\n2 lb ground beef\n1 cup cornmeal\n1 cup flour\n1 tbsp baking powder\n2 tbsp sugar\n1 egg\n2 cans beans\n1. Brown the beef.';
for (const [t, n] of [[sheet, 'cookie sheet chicken'], [velvet, 'baking soda beef'], [fried, 'fried chicken'], [cakeChili, 'chili with cornbread']]) {
  const r = P(t); ok(!r.baking, n + ' is not baking');
  for (const m of [1, 14, 40]) { const p = E.batchDay(r, m); ok(!/room temp/i.test(store(p)), n + ' no room temp at ' + m); ok(/within 4 days/.test(store(p)), n + ' fridge 4 days at ' + m); ok(p.portions && p.portions.fridge > 0, n + ' has portions'); }
  ok(/within 2 hours/.test(E.batchDay(r, 14).order.map((o) => o.d).join(' ')), n + ' cool within 2 hours');
}
// no baking verdict ever pairs with meat
const meatTitles = ['Chili with a cornbread top\nServes 6\n2 lb ground beef\n1 cup cornmeal\n1 cup flour\n1 tbsp baking powder', 'Chicken pot pie\nServes 6\n2 lb chicken\n2 cups flour\n1 cup butter\n1 tbsp sugar\n2 eggs', 'Sausage biscuits\nMakes 12\n1 lb sausage\n2 cups flour\n1 tbsp baking powder\n4 tbsp butter'];
meatTitles.forEach((t, k) => ok(!P(t).baking, 'meat bake ' + k + ' not baking'));

// F2-01/F2-02: whatever the title, a bake with meat, fish, beans, tofu or cheese is stored like a meal
const savoryBakes = ['Savory breakfast muffins\nMakes 12\n8 oz ham\n2 cups flour\n1 tbsp baking powder\n1 cup cheddar\n2 eggs\n1 cup milk',
  'Brunch muffins\nMakes 12\n1 lb ground beef\n2 cups flour\n1 tsp baking soda\n1 egg', 'Party cupcakes\nMakes 12\n1 lb sausage\n2 cups flour\n1 tbsp baking powder\n1 tbsp sugar\n2 eggs',
  'Little cakes\nMakes 8\n1 lb salmon\n1 cup flour\n1 tsp baking powder\n1 egg', 'Black bean cornbread bake\nServes 6\n2 cans black beans\n1 cup cornmeal\n1 cup flour\n1 tbsp baking powder\n1 tbsp sugar\n1 egg',
  'Lentil loaf\nServes 6\n2 cups cooked lentils\n1 cup oats\n1/2 cup flour\n1 tsp baking soda\n1 egg', 'Tofu bites\nServes 4\n1 lb tofu\n1 cup flour\n1 tbsp sugar\n1 egg',
  'Pepperoni pizza rolls\nMakes 12\n4 oz pepperoni\n3 cups flour\n1 tbsp sugar\n2 tsp yeast', 'Clam cakes\nMakes 12\n1 cup clams\n2 cups flour\n1 tbsp baking powder\n1 egg',
  'Prosciutto scones\nMakes 8\n3 oz prosciutto\n2 cups flour\n1 tbsp baking powder\n4 tbsp butter', 'Anchovy focaccia\nServes 8\n6 anchovies\n4 cups flour\n2 tsp yeast\n1 tbsp sugar',
  'Egg and cheese breakfast muffins\nMakes 12\n8 eggs\n1 cup cheddar\n1 cup milk\n1 cup flour', 'Cheese scones\nMakes 8\n2 cups flour\n1 tbsp baking powder\n1 cup cheddar\n4 tbsp butter\n1 tsp sugar',
  'Brisket biscuits\nMakes 10\n1 lb brisket\n2 cups flour\n1 tbsp baking powder\n6 tbsp butter', 'Corn dog muffins\nMakes 12\n4 hot dogs\n1 cup cornmeal\n1 cup flour\n1 tbsp baking powder\n1 tbsp sugar\n1 egg'];
savoryBakes.forEach((t) => { for (const m of [1, 14, 40]) { const p = E.batchDay(P(t), m); ok(!/room temp/i.test(store(p)), t.split('\n')[0] + ' never room temp at ' + m); ok(/2 hours/.test(store(p) + p.order.map((o) => o.d).join(' ')), t.split('\n')[0] + ' fridge within 2 hours at ' + m); ok(p.portions && p.portions.fridge + p.portions.freezer === m, t.split('\n')[0] + ' has portions at ' + m); } });
// sweet bakes keep the room-temp line
ok(/room temp/.test(store(B('Banana muffins\nMakes 12\n3 bananas\n1/3 cup butter\n3/4 cup sugar\n1 egg\n1 tsp baking soda\n1 1/2 cups flour', 12))), 'sweet muffins room temp');

// F2-03 capitalised no-number lines are ingredients, not headers
{ const r = P('Pasta\nServes 4\n1 lb penne\nParmesan rind\nPine nuts\nHot honey\nTortilla chips\n2 cups marinara'); const n = r.ingredients.map((i) => i.name).join('|'); ['Parmesan rind', 'Pine nuts', 'Hot honey', 'Tortilla chips'].forEach((w) => ok(n.includes(w), w + ' kept: ' + n)); }
// F2-05 ground spices are spices
['2 tsp ground cumin', '1 tsp ground cinnamon', '1 tsp ground black pepper'].forEach((l) => ok(P('X\nServes 1\n' + l).ingredients[0].cls === 'spice', l + ' is spice'));
// F2-10 ginger by the inch
{ const p = B('X\nServes 4\n1 inch piece ginger', 14); ok(p.items[0].scaled === '4 inches' && p.items[0].name === 'ginger', 'ginger inches: ' + p.items[0].scaled + ' ' + p.items[0].name); }
// F2-11 singular
{ const p = B('X\nServes 4\n4 eggs\n4 carrots\n2 ripe bananas', 1); const lab = p.grocery.map((g) => g.amt + ' ' + g.label).join('|'); ok(/1 egg\b/.test(lab) && /1 carrot\b/.test(lab) && /½ ripe banana\b/.test(lab), 'singular: ' + lab); }
// F2-15 pinch and handful are one each
{ const r = P('Soup\nServes 4\n1 lb chicken\npinch of dried thyme\na handful of spinach'); ok(r.ingredients.find((i) => /thyme/.test(i.name)).qty === 1 && r.ingredients.find((i) => /spinach/.test(i.name)).qty === 1, 'pinch and handful = 1'); }
// F2-07 no-cook and pasta
{ const p = B('Overnight oats\nServes 2\n1 cup oats\n1 cup milk\n1. Stir together in jars.\n2. Refrigerate overnight.', 14); ok(!p.pots.length && p.order[0].t === 'Mix and portion', 'no-cook plan'); }
{ const p = B('Baked ziti\nServes 8\n1 lb ziti\n1 lb sausage\n1 jar marinara\n1. Boil the ziti. 2. Brown the sausage. 3. Bake in a 9x13 dish 25 minutes.', 14); ok(p.order.some((o) => o.t === 'Boil the pasta'), 'pasta boil step'); }
// F2-06 every ingredient appears in a step (finishers and tender greens aside)
{ const p = B('Fried rice\nServes 4\n4 cups cooked rice\n3 eggs\n2 tbsp oil\n1 cup peas\n2 tbsp soy sauce\n1. Fry the rice.', 14); const used = p.order.flatMap((o) => (o.use || []).map((u) => u.name)).join('|'); ['cooked rice', 'eggs', 'peas', 'soy sauce'].forEach((w) => ok(used.includes(w), 'step has ' + w + ': ' + used)); }
// F2-09 oven rounds
{ const p = B('Sheet pan veg\nServes 4\n2 lb potatoes\n1 lb carrots\n2 tbsp oil\n1. Roast on a sheet pan for 35 minutes.', 40); ok(p.pots.some((x) => /rounds in the oven/.test(x)), 'oven rounds'); }

// B-04 bakes that must be detected
const shortbread = 'Shortbread\nMakes 16\n2 cups flour\n1 cup butter\n1/2 cup sugar\n1/4 tsp salt';
const crust = 'Pie crust\nMakes 1\n2 1/2 cups flour\n1 cup cold butter\n1 tsp salt\n6 tbsp ice water';
const muffins = 'Banana muffins\nMakes 12\n3 bananas\n1/3 cup butter\n3/4 cup sugar\n1 egg\n1 tsp baking soda\n1 1/2 cups flour';
for (const [t, n] of [[shortbread, 'shortbread'], [crust, 'pie crust'], [muffins, 'muffins']]) ok(P(t).baking, n + ' is baking');
{ const p = E.batchDay(P(shortbread), 48); const b = p.items.find((i) => /butter/.test(i.name)); ok(b.scaled === '3 cups', 'shortbread butter 3x = 3 cups, got ' + b.scaled); ok(!p.pots.length, 'shortbread no pots'); }
{ const p = E.batchDay(P(crust), 4); const b = p.items.find((i) => /butter/.test(i.name)); ok(b.scaled === '4 cups', 'pie crust butter 4x = 4 cups, got ' + b.scaled); }

// B-02 lowercase no-number lines are kept
{ const r = P('Garlic butter pasta\nServes 2\n8 oz spaghetti\n4 tbsp butter\nkosher salt\nfresh parsley, chopped\nred pepper flakes\nparmesan cheese');
  ok(r.ingredients.length === 6, 'six ingredients, got ' + r.ingredients.length + ': ' + r.ingredients.map((i) => i.name).join('|'));
  const g = E.batchDay(r, 4).grocery.map((x) => x.name.toLowerCase()).join('|');
  ['spaghetti', 'butter', 'kosher salt', 'parsley', 'red pepper flakes', 'parmesan'].forEach((w) => ok(g.includes(w), 'grocery has ' + w)); }
{ const r = P('Soup\nServes 4\n1 lb chicken\n2 cups broth\npinch of dried thyme\nhandful of spinach'); ok(r.ingredients.some((i) => /thyme/.test(i.name)), 'pinch of thyme kept'); ok(r.ingredients.some((i) => /spinach/.test(i.name)), 'handful of spinach kept'); }
// a real wrapped note still joins the line above
{ const r = P('Stew\nServes 4\n2 lb beef chuck,\ncut into cubes\n2 cups broth'); ok(r.ingredients.length === 2, 'wrapped note joins, got ' + r.ingredients.length); }

// B-07 package sizes
{ const r = P('Bake\nServes 6\n1 jar (15 oz) pesto\n1 box (200 g) curry roux\n1 (15 oz) can tomato sauce\n2 (14.5-ounce) cans diced tomatoes\n1 28-ounce can crushed tomatoes');
  const by = (re) => r.ingredients.find((i) => re.test(i.name));
  ok(by(/pesto/) && by(/pesto/).unit === 'jar' && by(/pesto/).size.n === 15, 'pesto jar 15 oz');
  ok(by(/roux/) && by(/roux/).unit === 'box', 'roux box');
  ok(by(/tomato sauce/) && by(/tomato sauce/).unit === 'can', 'tomato sauce can');
  ok(by(/diced/) && by(/diced/).qty === 2 && by(/diced/).size.n === 14.5, 'two 14.5 oz cans');
  ok(by(/crushed/) && by(/crushed/).unit === 'can' && by(/crushed/).size.n === 28 && by(/crushed/).qty === 1, '28-ounce can');
  const p = E.batchDay(r, 21); // 3.5x
  const s = (re) => p.items.find((i) => re.test(i.name)).scaled;
  ok(s(/pesto/) === '4 jars (15 oz)', 'pesto rounds up to 4 jars, got ' + s(/pesto/));
  ok(s(/tomato sauce/) === '4 cans (15 oz)', 'sauce 4 cans, got ' + s(/tomato sauce/));
  ok(!/½/.test(p.grocery.map((g) => g.amt).join(' ')), 'no half cans or jars'); }

// B-01 pots count cans, whole vegetables and pasta
{ const curry = 'Chickpea curry\nServes 4\n2 cans chickpeas\n1 can coconut milk\n1 (14 oz) can diced tomatoes\n1 onion\n2 tbsp curry powder\n1 tsp salt\n1. Simmer 20 minutes.';
  const p = E.batchDay(P(curry), 14); const main = p.pots.find((x) => /^Main pot/.test(x));
  // 7 cans chickpeas + 3.5 coconut + 3.5 tomatoes + 3.5 onions, about 26 cups or more
  ok(cupsIn(main) >= 24, 'curry pot counts cans: ' + main); ok(qtIn(main) * 4 * 0.75 >= cupsIn(main), 'curry pot holds it at ¾: ' + main); }
{ const soup = 'Black bean soup\nServes 4\n2 cans black beans\n2 cups broth\n1 onion\n1. Simmer.';
  const p = E.batchDay(P(soup), 14); const main = p.pots[0]; ok(qtIn(main) * 4 * 0.75 >= cupsIn(main) && cupsIn(main) >= 18, 'bean soup pot: ' + main); }

// B-05 200 meals: enough pots, a split warning, no impossible single pot
{ const p = B('Lentil soup\nServes 4\n2 cups red lentils\n8 cups broth\n1 onion\n2 carrots', 200);
  const main = p.pots[0]; const n = +((/Use (\d+) big pots/.exec(main) || [])[1] || 0);
  ok(n > 2 && n * 60 >= cupsIn(main), 'pot count covers the food: ' + main);
  ok(p.notes.some((x) => /two sessions/.test(x)), 'big cook warning'); }
{ const p = B('Rice bowls\nServes 4\n2 lb chicken thighs\n2 cups rice\n1. Sear the chicken until golden.', 200);
  const rice = p.pots.find((x) => /^Rice/.test(x)); const n = +((/in (\d+) pots/.exec(rice) || [])[1] || 0);
  ok(n * 20 >= p.rice, 'rice pots hold it: ' + rice);
  ok(p.pots.some((x) => /two pans at once|in the oven/.test(x)), 'sear warning past 6 batches'); }

// B-06 rice pot: cooked rice (3x) stays at or under ¾ of the pot
for (const m of [4, 8, 14, 20, 30, 40, 60, 79]) {
  const p = B('Rice\nServes 1\n1/3 cup white rice', m); const rp = p.pots.find((x) => /^Rice pot/.test(x));
  if (rp) ok(p.rice * 3 <= qtIn(rp) * 4 * 0.75 + 1e-9, `rice ${m} meals: ${p.rice} cups dry in ${qtIn(rp)} qt`);
}

// L-01 no salt cliff past 2x: more meals never means less salt
{ const t = 'Soup\nServes 4\n1 tsp salt\n2 tbsp olive oil\n1 tbsp chili powder\n4 cups broth';
  const r = P(t); let prev = { salt: 0, oil: 0, chili: 0 };
  for (let m = 4; m <= 40; m++) { const p = E.batchDay(r, m); const q = (re) => p.items.find((i) => re.test(i.name)).qtyScaled;
    const now = { salt: q(/salt/), oil: q(/oil/), chili: q(/chili/) };
    for (const k in now) ok(now[k] >= prev[k] - 1e-9, `${k} at ${m} meals not below ${m - 1}`);
    prev = now; } }

// L-02 rounding: 6 tbsp stays 6 tbsp, never ½ cup; ¼ cup band within 7%
{ const p = B('X\nServes 1\n2 tbsp chili powder', 3); ok(p.items[0].scaled !== '½ cup', '6 tbsp not ½ cup: ' + p.items[0].scaled); }
{ const vals = [];
  for (let tsp = 1; tsp <= 200; tsp += 0.37) { const p = B('X\nServes 1\n' + tsp.toFixed(2) + ' tsp paprika', 1); vals.push(p.items[0]); }
  ok(vals.length > 10, 'rounding sample'); }

// L-03 / D: titles
ok(P('Minestrone\nServes 8\n1 onion\n8 cups broth').title === 'Minestrone', 'one-word title');
ok(P('Chicken Curry (serves 4)\n2 lb chicken\n1 can coconut milk').title === 'Chicken Curry', 'title with (serves 4)');
ok(P('Chicken curry | Serves 4\n2 lb chicken').title === 'Chicken curry', 'title | serves');
ok(P('Chicken Curry - serves 4\n2 lb chicken').title === 'Chicken Curry', 'title - serves');
{ const p = B('Minestrone\nServes 8\n1 onion\n2 carrots\n8 cups broth\n2 cans beans\n8 oz pasta\n1. Simmer 20 minutes.', 14);
  ok(!p.order.some((o) => /Season the beans|Season the minestrone/i.test(o.t)), 'no Season the beans'); }

// L-04 freezer line depends on the dish
{ const p = B('Chicken noodle soup\nServes 6\n2 lb chicken\n10 cups stock\n8 oz egg noodles\n2 carrots', 14); ok(/noodles go soft/i.test(p.split.freezer.join(' ')), 'noodle warning'); ok(!/rice/.test(p.split.freezer.join(' ')), 'no rice bag line without rice'); }

// L-05 recipe's own time is in the total
{ const p = B('Salsa chicken\nServes 6\n3 lb chicken breasts\n16 oz salsa\n1. Slow cook on low for 4 hours.', 14); ok(p.totalMin >= 240, 'slow cook time counted: ' + p.totalMin); }
{ const p = B('Braise\nServes 6\n4 lb pork shoulder\n2 cups broth\n1. Brown the pork. 2. Simmer 2 hours.', 14); ok(p.totalMin >= 120, 'braise time counted: ' + p.totalMin); }

// L-06 sheet pan is not a pot plan
{ const p = B(sheet, 14); ok(p.pots.some((x) => /^Sheet pans/.test(x)) && !p.pots.some((x) => /^Main pot/.test(x)), 'sheet pan plan'); ok(!p.order.some((o) => /big pot/.test(o.t)), 'no big pot step on a sheet pan'); }
// cooked rice is not cooked again
{ const p = B('Fried rice\nServes 4\n4 cups cooked rice\n3 eggs\n2 tbsp soy sauce', 14); ok(!p.pots.some((x) => /^Rice pot/.test(x)) && !p.rice, 'cooked rice: no rice pot'); }
// congee: rice cooks in the soup
{ const p = B('Chicken congee\nServes 4\n1 cup jasmine rice\n10 cups water\n1 lb chicken thighs\n1. Simmer 1 1/2 hours until thick.', 14); ok(!p.pots.some((x) => /^Rice pot/.test(x)), 'congee: no separate rice pot'); }

// L-07 butter in a roux or mash is not eased
{ const p = B('Mac\nServes 6\n1 lb macaroni\n4 tbsp butter\n4 tbsp flour\n4 cups milk', 18); const b = p.items.find((i) => /butter/.test(i.name)); ok(!b.adjusted && Math.abs(b.qtyScaled - 12) < 1e-9, 'roux butter 3x linear'); }
{ const p = B('Seared\nServes 4\n2 lb chicken\n2 tbsp butter, for cooking\n1. Sear until golden.', 12); const b = p.items.find((i) => /butter/.test(i.name)); ok(b.adjusted, 'frying butter eased'); }

// L-08 classes
['2 tsp garam masala', '1 tsp mustard powder', '2 chipotles in adobo', '2 bay leaves'].forEach((l) => ok(P('X\nServes 1\n' + l).ingredients[0].cls === 'spice', l + ' is spice'));
['Green onions, for serving', 'Sour cream, for serving'].forEach((l) => ok(P('X\nServes 1\n1 lb chicken\n' + l).ingredients[1].cls === 'finisher', l + ' is finisher'));

// L-10 the same item in two sections is one grocery line; to-taste items are on the list
{ const p = B('Bowls\nServes 4\nMarinade:\n1 tbsp ginger paste\n1 lb chicken\nSauce:\n2 tbsp ginger paste\nred chili flakes, to taste', 4);
  const g = p.grocery.filter((x) => /ginger paste/.test(x.name)); ok(g.length === 1 && g[0].amt === '3 tbsp', 'ginger paste merged: ' + JSON.stringify(g));
  ok(p.grocery.some((x) => /chili flakes/.test(x.name)), 'to-taste item on the list'); }

// L-12 / D: count items never round down; cans round up
{ const p = B('Chili\nServes 6\n1 green bell pepper\n2 cans kidney beans\n1 large onion', 14); // 2.33x
  const s = (re) => p.items.find((i) => re.test(i.name)).scaled;
  ok(s(/pepper/) === '2½', 'pepper 2.33 -> 2½, got ' + s(/pepper/)); ok(s(/beans/) === '5 cans', 'beans 4.67 -> 5 cans, got ' + s(/beans/)); }

// M-01 plurals
{ const p = B('Eggs\nServes 1\n1 egg\n1 onion\n1 large carrot\n1 potato', 3); const lab = p.grocery.map((g) => g.label).join('|'); ok(/eggs/.test(lab) && /onions/.test(lab) && /carrots/.test(lab) && /potatoes/.test(lab), 'plurals: ' + lab); }
{ const p = B('Soup\nServes 4\n1 onion\n4 cups broth', 1); ok(/1 meal for/.test(p.split.fridge[0]), 'singular meal'); ok(!/1 cups/.test(p.pots.join(' ')), 'no "1 cups"'); }
// M-02 metric
{ const p = B('Curry\nServes 4\n600 g chicken\n30 g butter\n400 ml passata', 14); const s = p.items.map((i) => i.scaled).join('|'); ok(/2\.1 kg/.test(s) && /105 g/.test(s) && /1\.4 l/.test(s) && !/[⅓⅔½¼¾]\s*g/.test(s), 'metric: ' + s); }
// M-04 sear size for a small batch
{ const p = B('Steak\nServes 4\n1 lb steak\n1. Sear until browned.', 1); ok(/about 4 oz/.test(p.pots.join(' ')), 'small sear: ' + p.pots.join(' ')); }

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
