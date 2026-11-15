// Guide pages: one question each, answered with numbers from engine.js. Run by build.py (node guides.js prints JSON).
// Every number on a page comes out of the page's own calc(), which runs here at build time and again in the browser.
// No storage or keep times anywhere in this file.
const fs = require('fs'), path = require('path');
const E = require('./engine.js');
const SITE = 'https://batch.recipes/', UPDATED = '2026-11-14';
const tpl = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8');
const SAMPLE = (/const SAMPLE=`([\s\S]*?)`;/.exec(tpl) || [])[1];
if (!SAMPLE) throw new Error('sample recipe not found in template.html');

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const text = (h) => h.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/\s+/g, ' ').trim();

// shared by every calc, in the page and here
const PRE = `var P=E.parseRecipe,X=function(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})},FX=function(f){return (Math.round(f*10)/10).toString().replace(/\\.0$/,'')},N=function(n,w){return n+' '+w+(n==1?'':'s')};
var EX=[['1 lb','chicken thighs'],['2 cups','chicken broth'],['1 cup','rice'],['2 cloves','garlic'],['1 tsp','salt'],['2 tsp','chili powder'],['2 tbsp','olive oil']];
function TB(y,want,head){var s=E.scaleAll(P('Example\\nServes '+y+'\\n'+EX.map(function(r){return r[0]+' '+r[1]}).join('\\n')),want);
return '<table class="tbl"><tr><th>Ingredient</th><th>Recipe</th><th>'+head+'</th></tr>'+s.items.map(function(i,k){return '<tr><td>'+X(i.name)+(i.adjusted?' <small>eased back</small>':'')+'</td><td class="num">'+EX[k][0]+'</td><td class="num"><b>'+X(i.scaled)+'</b></td></tr>'}).join('')+'</table>'}
`;

// the stepper wiring (browser only)
const RUN = `var v={},last={};
function el(i){return document.getElementById(i)}
function show(c){var e=el(c.id),b=e.parentNode.querySelectorAll('button');if(c.h)e.textContent=E.fmtNum(v[c.id]);else e.value=v[c.id];b[0].classList.toggle('end',v[c.id]<=c.min);b[1].classList.toggle('end',v[c.id]>=c.max)}
function draw(an){var o=calc(v);Object.keys(o).forEach(function(k){var e=document.querySelector('[data-o="'+k+'"]');if(!e||last[k]===o[k])return;var first=!(k in last);last[k]=o[k];if(first&&!an)return;e.innerHTML=o[k];if(an){e.classList.remove('chg');void e.offsetWidth;e.classList.add('chg')}})}
C.forEach(function(c){v[c.id]=c.val;var e=el(c.id),st=c.h?.5:1,t=0,r=0,held=false;
function nudge(d){var k=d>0?'nr':'nl';e.classList.remove('nr','nl');void e.offsetWidth;e.classList.add(k)}
function bump(d){var n=v[c.id]+d*st;if(n<c.min||n>c.max){nudge(d);return}v[c.id]=n;show(c);draw(1)}
function stop(){clearTimeout(t);clearInterval(r)}
[].forEach.call(e.parentNode.querySelectorAll('button'),function(b){var d=+b.getAttribute('data-d');
b.addEventListener('pointerdown',function(ev){if(ev.button)return;held=false;stop();t=setTimeout(function(){held=true;r=setInterval(function(){bump(d)},110)},400)});
['pointerup','pointerleave','pointercancel','blur'].forEach(function(n){b.addEventListener(n,stop)});
b.addEventListener('contextmenu',function(ev){ev.preventDefault()});
b.addEventListener('click',function(){if(held){held=false;return}bump(d)})});
if(!c.h){e.addEventListener('input',function(){if(/^\\d+$/.test(e.value)){var n=+e.value;if(n>=c.min&&n<=c.max){v[c.id]=n;var b=e.parentNode.querySelectorAll('button');b[0].classList.toggle('end',n<=c.min);b[1].classList.toggle('end',n>=c.max);draw(1)}}});
e.addEventListener('change',function(){var s=e.value.trim(),n=/^-?\\d+$/.test(s)?+s:v[c.id];v[c.id]=Math.min(c.max,Math.max(c.min,n));show(c);draw(1)});
e.addEventListener('keydown',function(ev){if(ev.key==='Enter')e.blur()})}
show(c)});
draw(0);document.addEventListener('touchstart',function(){},{passive:true});`;

const MEALS = { id: 'meals', label: 'Meals', val: 14, min: 1, max: 999, dn: 'Fewer meals', up: 'More meals' };
const SERVES = { id: 'serves', label: 'Recipe serves', val: 4, min: 1, max: 99, dn: 'Fewer servings', up: 'More servings' };
const A = (s) => (/^(8|11|18)\b/.test(s) ? 'an ' : 'a ') + s, Cap = (s) => s[0].toUpperCase() + s.slice(1);
const N = (n, w) => n + ' ' + w + (n == 1 ? '' : 's');
const L = (slug, t) => `<a href="${slug}">${t}</a>`;

const pages = [
  {
    slug: 'how-much-rice-for-meal-prep',
    sum: (c) => `${c({ meals: 14 }).cups} of dry rice for 14 meals.`,
    h1: 'How much rice do I need for meal prep?',
    controls: [MEALS],
    calc: `function calc(v){var p=E.batchDay(P('Bowl\\nServes 1\\n- white rice, for serving'),v.meals),n=p.items[0].scaled.split(' cups')[0],m=/Rice pot: (\\d+) qt/.exec(p.pots.join(' ')),c=n+(n==='1'||n==='½'?' cup':' cups');
return{big:c,cups:c,pot:m?m[1]+' qt pot':'',sub:'Dry rice for '+N(v.meals,'meal')+'. '+(m?'Cook it in a '+m[1]+' qt pot.':'Cook it in '+((/in (\\d+) pots/.exec(p.pots.join(' '))||[])[1]||'2')+' pots or rounds.')}}`,
    answer: (c) => { const a = c({ meals: 14 }); return `For 14 meals, cook ${a.cups} of dry rice in ${A(a.pot)}. batch.recipes plans about ⅓ cup of dry rice a meal, which cooks up to about 1 cup.`; },
    desc: (c) => `For 14 meals, cook ${c({ meals: 14 }).cups} of dry rice. Set your meals to get the cups and the pot size.`,
    how: () => ['About ⅓ cup of dry rice a meal. It\'s an estimate, used when a recipe only says "rice".', 'The total is rounded to the nearest half cup.', 'Dry rice about triples as it cooks, so ⅓ cup dry is about 1 cup cooked.', 'The pot is sized so the dry rice fills no more than a quarter of it. Cooked, it fills about three-quarters.', 'If your recipe gives a rice amount, batch.recipes scales that amount.'],
    faq: (c) => [
      ['How much rice for 5, 7, 10 or 21 meals?', [5, 7, 10, 21].map((m) => `${m} meals: ${c({ meals: m }).cups}.`).join(' ') + ' All dry.'],
      ['Is that dry or cooked rice?', 'Dry. It cooks up to about three times as much.'],
      ['What size pot do I need?', `${Cap(A(c({ meals: 14 }).pot))} for 14 meals. See ${L('how-much-rice-fits-in-a-pot', 'How much dry rice can I cook in one pot?')}`],
    ],
    more: ['how-much-rice-fits-in-a-pot', 'how-much-chicken-for-meal-prep', 'how-to-scale-a-recipe-for-meal-prep'],
  },
  {
    slug: 'how-much-chicken-for-meal-prep',
    sum: (c) => `${c({ meals: 14, serves: 4, lb: 1.5 }).big} for 14 meals, from 1½ lb for 4 servings.`,
    h1: 'How much chicken do I need for meal prep?',
    controls: [MEALS, SERVES, { id: 'lb', label: 'Chicken in the recipe (lb)', val: 1.5, min: 0.5, max: 20, h: 1, dn: 'Less chicken', up: 'More chicken' }],
    calc: `function calc(v){var r=P('Chicken\\nServes '+v.serves+'\\n'+v.lb+' lb chicken thighs\\n1. Sear the chicken until golden.'),p=E.batchDay(r,v.meals),one=E.scaleAll(r,1).items[0].scaled,m=/Searing: (\\d+) batch/.exec(p.pots.join(' ')),b=m?N(+m[1],'batch').replace(/batchs/,'batches'):'';
return{big:p.items[0].scaled,each:one,batches:b,sub:(/^0 /.test(one)?'':one+' a meal. ')+(b?'Sear it in '+b+' in a 12-inch pan.':'')}}`,
    answer: (c) => { const a = c({ meals: 14, serves: 4, lb: 1.5 }); return `Divide the chicken in your recipe by its servings, then multiply by your meals. A recipe with 1½ lb of chicken thighs for 4 servings needs ${a.big} for 14 meals, or ${a.each} a meal.`; },
    desc: (c) => `A recipe with 1½ lb of chicken for 4 servings needs ${c({ meals: 14, serves: 4, lb: 1.5 }).big} for 14 meals. Set your own recipe and meals.`,
    how: () => ['Meat scales straight up: the recipe amount, times your meals, divided by its servings.', 'There\'s no fixed portion. It uses your recipe\'s own.', 'A pound or more is rounded to the nearest quarter pound.', 'For searing, it plans about 1½ lb a batch in a 12-inch pan.'],
    faq: (c) => [
      ['How many pounds of chicken for 14 meals?', 'It depends on the recipe. For a recipe that serves 4: ' + [1, 1.5, 2].map((lb) => `${E.fmtNum(lb)} lb in the recipe makes ${c({ meals: 14, serves: 4, lb }).big}`).join(', ') + '.'],
      ['Does it work for chicken breast, beef or pork?', 'Yes. All meat scales the same way.'],
      ['How many batches to sear it?', `${c({ meals: 14, serves: 4, lb: 1.5 }).batches} for ${c({ meals: 14, serves: 4, lb: 1.5 }).big}. See ${L('how-much-meat-to-brown-at-once', 'How much meat can I brown at once?')}`],
    ],
    more: ['how-much-meat-to-brown-at-once', 'how-much-rice-for-meal-prep', 'how-to-scale-a-recipe-for-meal-prep'],
  },
  {
    slug: 'how-to-scale-a-recipe-for-meal-prep',
    sum: (c, x) => `Meals over servings. Past double, go easier on salt, spices and oil.`,
    h1: 'How do I scale a recipe for meal prep?',
    controls: [MEALS, SERVES],
    calc: `function calc(v){var f=v.meals/v.serves;return{big:FX(f)+'×',sub:'the recipe, for '+N(v.meals,'meal')+'.',tbl:TB(v.serves,v.meals,'Batch')}}`,
    answer: (c, x) => `Divide the meals you want by the servings the recipe makes, and multiply each ingredient by that. Past double, add the salt, spices and oil more slowly: the amount above double goes in at ${x.pct.salt}% for salt, ${x.pct.spice}% for spices and ${x.pct.oil}% for oil. Taste at the end. For 14 meals from a recipe that serves 4, that's ${c({ meals: 14, serves: 4 }).big}: 1 lb of chicken becomes ${x.at(3.5, 'chicken thighs')} and 1 tsp of salt becomes ${x.at(3.5, 'salt')}.`,
    desc: (c, x) => `Multiply by meals over servings. Past double, the extra salt goes in at ${x.pct.salt}%, spices at ${x.pct.spice}% and oil at ${x.pct.oil}%. Try it with your numbers.`,
    how: (c, x) => ['Meat, vegetables, grains, broth and garlic scale straight up.', 'Up to double, so do salt, spices and oil.', `Past double, the amount above double goes in at ${x.pct.salt}% for salt, ${x.pct.spice}% for spices and ${x.pct.oil}% for oil. Taste at the end and add more.`, 'Lime, herbs and other fresh finishers are kept for serving.', 'Amounts are rounded to spoons and cups you can measure.'],
    faq: () => [
      ['Why don\'t salt and spices scale all the way?', 'So a big batch isn\'t over-seasoned. Taste at the end and add more if it needs it.'],
      ['What about lime juice and fresh herbs?', 'Keep them out of the pot. Add them to each bowl when you eat.'],
      ['Does this work for baking?', `Baking isn't eased back, and past double it's made in more than one batch. See ${L('can-you-double-a-baking-recipe', 'Can you double or triple a baking recipe?')}`],
    ],
    more: ['how-to-double-a-recipe', 'how-to-triple-a-recipe', 'what-size-pot-for-a-double-batch'],
  },
  {
    slug: 'what-size-pot-for-a-double-batch',
    sum: (c) => `${Cap(A(c({ qt: 2, x: 2 }).big))} for a doubled 2 quart soup.`,
    h1: 'What size pot do I need to double a soup or chili recipe?',
    controls: [{ id: 'qt', label: 'One batch makes (quarts)', val: 2, min: 1, max: 20, dn: 'Fewer quarts', up: 'More quarts' }, { id: 'x', label: 'Times the recipe', val: 2, min: 1, max: 10, dn: 'Fewer times', up: 'More times' }],
    calc: `function calc(v){var p=E.batchDay(P('Soup\\nServes 1\\n'+v.qt*4+' cups broth'),v.x).pots[0]||'',m=/(\\d+) qt or bigger/.exec(p),c=(/about (\\d+) cups/.exec(p)||[])[1];
var k=(/Use (\\d+) big pots/.exec(p)||[])[1]||'2';return{big:m?m[1]+' qt pot':k+' big pots',pot:m?m[1]+' qt':'',sub:m?'About '+c+' cups, kept under ¾ full.':'About '+c+' cups. Split it across '+k+' big pots.'}}`,
    answer: (c) => `Use a pot the full batch fills no more than three-quarters. A soup or chili that makes 2 quarts needs ${A(c({ qt: 2, x: 2 }).big)} doubled and ${A(c({ qt: 2, x: 3 }).big)} tripled.`,
    desc: (c) => `A soup that makes 2 quarts needs ${A(c({ qt: 2, x: 2 }).big)} doubled and ${A(c({ qt: 2, x: 3 }).big)} tripled. Set your own batch.`,
    table: (c) => ({ cap: 'Pot sizes', head: ['One batch makes', 'Doubled', 'Tripled'], rows: [1, 2, 3, 4, 6].map((q) => [N(q, 'quart'), c({ qt: q, x: 2 }).big, c({ qt: q, x: 3 }).big]) }),
    how: (c, x) => ['The pot has to hold the whole batch at three-quarters full or less.', '4 cups is 1 quart.', `It picks the next size up from ${x.pots.slice(0, -1).join(', ')} and ${x.pots.slice(-1)[0]} quarts.`, `Past a ${x.pots.slice(-1)[0]} qt pot, split the batch across more pots, or cook it in rounds.`],
    faq: (c) => [
      ['What size pot for a triple batch of chili?', `If one batch makes 2 quarts, ${A(c({ qt: 2, x: 3 }).big)}. If it makes 3 quarts, ${A(c({ qt: 3, x: 3 }).big)}.`],
      ['How do I know how much my recipe makes?', 'Add up everything that goes in the pot: broth, cans, meat, vegetables and pasta. batch.recipes does it from the ingredient list. It counts 8 oz of meat or vegetables as about 1 cup, a 15 oz can as about 2 cups and a whole onion as about 1 cup.'],
      ['Does the cooking time change?', 'A bigger pot takes longer to come to a simmer. Go by doneness, not the clock.'],
    ],
    more: ['how-to-double-a-recipe', 'how-to-triple-a-recipe', 'how-much-rice-fits-in-a-pot'],
  },
  {
    slug: 'how-much-rice-fits-in-a-pot',
    sum: (c, x) => `Up to ${N(x.fit[3], 'cup')} in a 3 qt pot.`,
    h1: 'How much dry rice can I cook in one pot?',
    controls: [{ id: 'cups', label: 'Dry rice (cups)', val: 4, min: 1, max: 99, dn: 'Fewer cups', up: 'More cups' }],
    calc: `function calc(v){var p=E.batchDay(P('Rice\\nServes 1\\n1 cup white rice'),v.cups).pots.join(' '),m=/Rice pot: (\\d+) qt/.exec(p),s=N(v.cups,'cup')+' of dry rice is about '+N(v.cups*3,'meal')+'.';
var k=(/in (\\d+) pots/.exec(p)||[])[1]||'2';return{big:m?m[1]+' qt pot':k+' pots',qt:m?+m[1]:0,sub:m?s:s+' Cook it in '+k+' pots or rounds.'}}`,
    answer: (c, x) => `Fill the pot no more than a quarter with dry rice. It about triples as it cooks, so cooked rice fills about three-quarters. That's up to ${N(x.fit[3], 'cup')} of dry rice in a 3 qt pot, ${N(x.fit[4], 'cup')} in a 4 qt pot and ${N(x.fit[6], 'cup')} in a 6 qt pot.`,
    desc: (c, x) => `Up to ${N(x.fit[3], 'cup')} of dry rice in a 3 qt pot, ${x.fit[4]} in a 4 qt and ${x.fit[6]} in a 6 qt. Dry rice should fill no more than a quarter of the pot.`,
    table: (c, x) => ({ cap: 'Dry rice by pot size', head: ['Pot', 'Dry rice, at most', 'Meals'], rows: x.pots.map((q) => [q + ' qt', N(x.fit[q], 'cup'), 'About ' + x.fit[q] * 3]) }),
    how: (c, x) => [`A quart is 4 cups, so a 3 qt pot holds 12 cups. A quarter of that is ${N(x.fit[3], 'cup')} of dry rice.`, 'Amounts are whole cups, rounded down.', 'Meals are counted at about ⅓ cup of dry rice each.', `Past ${N(x.fit[x.pots.slice(-1)[0]], 'cup')} of dry rice, cook it in more pots or in rounds.`],
    faq: (c, x) => [
      ['How much rice can I cook in a 6 quart pot?', `Up to ${N(x.fit[6], 'cup')} of dry rice. That's about ${x.fit[6] * 3} meals.`],
      ['Why only a quarter full?', 'Rice about triples as it cooks, so a quarter dry is three-quarters cooked. That leaves room to boil without spilling over.'],
      ['How much rice do I need?', `About ⅓ cup of dry rice a meal. See ${L('how-much-rice-for-meal-prep', 'How much rice do I need for meal prep?')}`],
    ],
    more: ['how-much-rice-for-meal-prep', 'what-size-pot-for-a-double-batch', 'how-to-scale-a-recipe-for-meal-prep'],
  },
  {
    slug: 'how-to-double-a-recipe',
    sum: () => 'Everything times 2. Then check the pot.',
    h1: 'How do I double a recipe?',
    controls: [SERVES],
    calc: `function calc(v){return{big:N(v.serves*2,'serving'),sub:'2× the recipe.',tbl:TB(v.serves,v.serves*2,'Doubled')}}`,
    answer: () => 'Multiply every ingredient by 2, salt and spices included. Then check the pot: the doubled batch should fill it no more than three-quarters. Keep lime, herbs and other fresh finishers out of the pot and add them when you eat.',
    desc: () => 'Multiply every ingredient by 2, salt and spices included. Then check the pot size and sear meat in batches. Common amounts, doubled.',
    table: (c, x) => ({ cap: 'Common amounts, doubled', head: ['Recipe', 'Doubled'], rows: x.common(2) }),
    how: () => ['At double, everything scales straight up. Nothing is eased back until you go past double.', 'Sear meat in batches of about 1½ lb in a 12-inch pan.', 'A bigger pot takes longer to come to a simmer. Go by doneness, not the clock.', 'Baking doubles too. Measure carefully and check it a few minutes early.'],
    faq: (c, x) => [
      ['Do I double the salt and spices?', `Yes, at double. Past double they're eased back. See ${L('how-to-triple-a-recipe', 'How do I triple a recipe?')}`],
      ['What is ¾ cup doubled?', `${x.water('¾ cup', 2)}.`],
      ['Do I double the cooking time?', 'No. A bigger pot takes longer to come to a simmer. Go by doneness, not the clock.'],
      ['What size pot do I need?', `One the doubled batch fills no more than three-quarters. See ${L('what-size-pot-for-a-double-batch', 'What size pot do I need to double a soup or chili recipe?')}`],
    ],
    more: ['how-to-triple-a-recipe', 'what-size-pot-for-a-double-batch', 'can-you-double-a-baking-recipe'],
  },
  {
    slug: 'how-to-triple-a-recipe',
    sum: (c, x) => `Salt at ${x.mult(3, 'salt')}×, spices at ${x.mult(3, 'chili powder')}×, oil at ${x.mult(3, 'olive oil')}×.`,
    h1: 'How do I triple a recipe?',
    controls: [SERVES],
    calc: `function calc(v){return{big:N(v.serves*3,'serving'),sub:'3× the recipe.',tbl:TB(v.serves,v.serves*3,'Tripled')}}`,
    answer: (c, x) => `Multiply the meat, vegetables, grains and broth by 3. Start the salt at ${x.mult(3, 'salt')}×, the spices at ${x.mult(3, 'chili powder')}× and the oil at ${x.mult(3, 'olive oil')}×, then taste at the end and add more. Baking is different: make ${x.bake(3)}.`,
    desc: (c, x) => `Triple the meat, vegetables, grains and broth. Start the salt at ${x.mult(3, 'salt')}×, the spices at ${x.mult(3, 'chili powder')}× and the oil at ${x.mult(3, 'olive oil')}×, then taste.`,
    table: (c, x) => ({ cap: 'Common amounts, tripled', note: 'For ingredients that scale straight up.', head: ['Recipe', 'Tripled'], rows: x.common(3) }),
    how: (c, x) => [`Past double, the amount above double goes in at ${x.pct.salt}% for salt, ${x.pct.spice}% for spices and ${x.pct.oil}% for oil.`, 'Everything else scales straight up.', 'Lime, herbs and other fresh finishers are kept for serving.', 'Sear meat in batches of about 1½ lb in a 12-inch pan.'],
    faq: (c, x) => [
      ['Do I triple the salt?', `No. Start at ${x.mult(3, 'salt')}× and add more at the end. 1 tsp becomes ${x.at(3, 'salt')}.`],
      ['What is ½ cup tripled?', `${x.water('½ cup', 3)}.`],
      ['What size pot for a triple batch?', `One the batch fills no more than three-quarters. See ${L('what-size-pot-for-a-double-batch', 'What size pot do I need to double a soup or chili recipe?')}`],
    ],
    more: ['how-to-double-a-recipe', 'how-to-scale-a-recipe-for-meal-prep', 'can-you-double-a-baking-recipe'],
  },
  {
    slug: 'can-you-double-a-baking-recipe',
    sum: () => 'Double is fine. Past that, make more batches.',
    h1: 'Can you double or triple a baking recipe?',
    controls: [{ id: 'makes', label: 'Recipe makes', val: 12, min: 1, max: 999, dn: 'Fewer', up: 'More' }, { id: 'want', label: 'You want', val: 36, min: 1, max: 999, dn: 'Fewer', up: 'More' }],
    calc: `function calc(v){var p=E.batchDay(P('Muffins\\nServes '+v.makes+'\\n2 cups flour\\n2 tsp baking powder\\n1 cup sugar\\n2 eggs'),v.want),m=/Make (\\d+) batches of (\\S+)x/.exec(p.notes.join(' '));
return m?{big:m[1]+' batches',each:m[2]+'×',sub:'Each one '+m[2]+'× the recipe.'}:{big:'1 batch',each:FX(p.factor)+'×',sub:FX(p.factor)+'× the recipe. Measure carefully.'}}`,
    answer: (c, x) => `Doubling is fine: every ingredient doubles, baking powder and salt included. Past double, make more than one batch. To triple, make ${x.bake(3)}.`,
    desc: (c, x) => `Doubling is fine. Past double, make more than one batch: to triple, make ${x.bake(3)}. Set what the recipe makes and what you want.`,
    how: () => ['Bakes aren\'t eased back. Salt and leavening scale straight up.', 'Up to 2×, it\'s one batch. Measure carefully.', 'Past 2×, it\'s split into equal batches of 2× or less.', 'Same oven temperature. Check doneness a few minutes early.'],
    faq: (c, x) => [
      ['How do I make 4 or 5 times a cookie recipe?', `4 times: ${x.bake(4)}. 5 times: ${x.bake(5)}.`],
      ['Do I change the oven temperature?', 'No. Same temperature. Check doneness a few minutes early.'],
      ['What counts as baking?', 'Anything with baking powder, baking soda or yeast, or with flour, sugar and eggs together. Cakes, muffins, cookies and brownies.'],
    ],
    more: ['how-to-double-a-recipe', 'how-to-triple-a-recipe', 'how-to-scale-a-recipe-for-meal-prep'],
  },
  {
    slug: 'tiktok-recipe-to-grocery-list',
    sum: () => 'From screenshots, in store order.',
    h1: 'How do I turn a TikTok recipe into a grocery list?',
    controls: [MEALS],
    consts: `var S=${JSON.stringify(SAMPLE)};`,
    calc: `function calc(v){var g=E.shopList(E.batchDay(P(S),v.meals).grocery,[]).groups,n=0,h='';g.forEach(function(s){h+='<p class="aisle">'+X(s.name)+'</p><ul class="buy">'+s.items.map(function(i){n++;return '<li>'+(i.amt==='for serving'?X(i.name)+' <span class="muted">for serving</span>':(i.amt?'<b class="num">'+X(i.amt)+'</b> ':'')+X(i.name))+'</li>'}).join('')+'</ul>'});
return{big:N(n,'item'),sub:'The sample recipe, for '+N(v.meals,'meal')+'.',tbl:h}}`,
    answer: (c) => `Screenshot the recipe, add the screenshots to batch.recipes and set how many meals you want. It reads the ingredients and gives you a grocery list in store order. The sample recipe below comes to ${c({ meals: 14 }).big} for 14 meals.`,
    desc: () => 'Screenshot the recipe, add the screenshots to batch.recipes and set your meals. You get a grocery list in store order. Free, no account.',
    howTitle: 'Steps', ordered: true,
    how: () => ['Pause the video on the ingredients, or open the caption, and take screenshots. Up to 6.', 'On batch.recipes, tap Choose screenshots. An AI model reads the ingredients and steps.', 'Set your meals. Every amount updates.', 'Open Shop. Tick items as you go, or send the list to Reminders, Notes, Google Keep or any list app.'],
    faq: () => [
      ['Does it work with Instagram Reels and food blogs?', 'Yes. Any screenshot that shows the recipe.'],
      ['What if the recipe is only in the caption?', 'Copy the caption and use Paste text.'],
      ['Is it free?', 'Yes. No account.'],
    ],
    more: ['how-to-scale-a-recipe-for-meal-prep', 'how-much-rice-for-meal-prep', 'how-much-chicken-for-meal-prep'],
  },
  {
    slug: 'how-much-meat-to-brown-at-once',
    sum: (c) => `About ${c({ lb: 5 }).each} lb in a 12-inch pan.`,
    h1: 'How much meat can I brown at once?',
    controls: [{ id: 'lb', label: 'Meat (lb)', val: 5, min: 1, max: 99, dn: 'Fewer pounds', up: 'More pounds' }],
    calc: `function calc(v){var p=E.batchDay(P('Chicken\\nServes 1\\n'+v.lb+' lb chicken thighs\\n1. Sear the chicken until golden.'),1),n=+(/Searing: (\\d+) batch/.exec(p.pots.join(' '))||[0,0])[1],each=(/up to (\\S+) lb a batch/.exec(p.pots.join(' '))||[])[1],min=(p.order.filter(function(o){return /^Sear/.test(o.t)})[0]||{}).min;
return{big:n+(n==1?' batch':' batches'),each:each,min:min,per:min/n,sub:'About '+N(min,'minute')+' of searing in a 12-inch pan.'}}`,
    answer: (c) => { const a = c({ lb: 5 }); return `About ${a.each} lb at a time in a 12-inch pan. More than that crowds the pan and the meat steams. 5 lb takes ${a.big}.`; },
    desc: (c) => { const a = c({ lb: 5 }); return `About ${a.each} lb at a time in a 12-inch pan, so 5 lb takes ${a.big}. Set your pounds to get the batches and the time.`; },
    how: (c) => { const a = c({ lb: 5 }); return [`Pounds divided by ${a.each}, rounded up, is the number of batches.`, `It plans about ${a.per} minutes a batch.`, 'Set each batch aside while you sear the next.', 'Don\'t crowd the pan, or the meat steams.']; },
    faq: (c) => [
      ['How many batches for 3 lb of ground beef?', `${c({ lb: 3 }).big}.`],
      ['How long does it take to brown 5 lb?', `About ${c({ lb: 5 }).min} minutes, at ${c({ lb: 5 }).per} minutes a batch.`],
      ['How much meat do I need?', `Scale what your recipe uses. See ${L('how-much-chicken-for-meal-prep', 'How much chicken do I need for meal prep?')}`],
    ],
    more: ['how-much-chicken-for-meal-prep', 'how-to-double-a-recipe', 'what-size-pot-for-a-double-batch'],
  },
];

// ---- build-time facts, all read off the engine ----
const calcOf = (p) => new Function('E', PRE + (p.consts || '') + p.calc + ';return calc')(E);
const EXR = (f) => E.scaleAll(E.parseRecipe('Example\nServes 1\n1 lb chicken thighs\n2 cups chicken broth\n1 cup rice\n2 cloves garlic\n1 tsp salt\n2 tsp chili powder\n2 tbsp olive oil'), f).items;
const ratio = (f, name) => { const i = EXR(f).find((k) => k.name === name); return i.qtyScaled / i.qty; };
const x = {
  // past double, the share of each extra batch's salt, spice and oil that goes in (measured from 3x to 4x)
  pct: { salt: Math.round((ratio(4, 'salt') - ratio(3, 'salt')) * 100), spice: Math.round((ratio(4, 'chili powder') - ratio(3, 'chili powder')) * 100), oil: Math.round((ratio(4, 'olive oil') - ratio(3, 'olive oil')) * 100) },
  mult: (f, name) => String(Math.round(ratio(f, name) * 100) / 100),
  at: (f, name) => EXR(f).find((k) => k.name === name).scaled,
  water: (amt, f) => E.scaleAll(E.parseRecipe('W\nServes 1\n' + amt + ' water'), f).items[0].scaled,
  bake: (f) => { const c = calcOf(pages.find((p) => p.slug === 'can-you-double-a-baking-recipe'))({ makes: 12, want: 12 * f }); return `${c.big} of ${c.each} each`; },
};
// a row only goes in a "common amounts" table when the engine's rounded answer is exact
const TSP = { tsp: 1, tbsp: 3, cup: 48, cups: 48 }, FR = { '⅛': .125, '¼': .25, '⅓': 1 / 3, '½': .5, '⅔': 2 / 3, '¾': .75 };
const toTsp = (s) => { const m = /^(\d+)?([⅛¼⅓½⅔¾])? (\w+)$/.exec(s); return ((+m[1] || 0) + (FR[m[2]] || 0)) * TSP[m[3]]; };
x.common = (f) => ['¼ tsp', '½ tsp', '1 tsp', '1 tbsp', '¼ cup', '⅓ cup', '½ cup', '¾ cup', '1 cup'].map((a) => [a, x.water(a, f)]).filter(([a, b]) => Math.abs(toTsp(b) - toTsp(a) * f) < 1e-6);
{ // pot sizes the engine picks from, and the most whole cups of dry rice each takes
  const rice = calcOf(pages.find((p) => p.slug === 'how-much-rice-fits-in-a-pot')); x.fit = {};
  for (let cups = 1; cups <= 99; cups++) { const q = rice({ cups }).qt; if (q) x.fit[q] = cups; }
  const pot = calcOf(pages.find((p) => p.slug === 'what-size-pot-for-a-double-batch')), seen = new Set();
  for (let qt = 1; qt <= 20; qt++) for (let n = 1; n <= 10; n++) { const m = /(\d+) qt/.exec(pot({ qt, x: n }).big); if (m) seen.add(+m[1]); }
  x.pots = [...seen].sort((a, b) => a - b);
}

function stepper(c) {
  const mid = c.h ? `<output id="${c.id}" class="num">${E.fmtNum(c.val)}</output>` : `<input id="${c.id}" class="num" inputmode="numeric" autocomplete="off" value="${c.val}">`;
  return `<div class="set"><label for="${c.id}">${esc(c.label)}</label><div class="step"><button type="button" data-d="-1" aria-label="${c.dn}">−</button>${mid}<button type="button" data-d="1" aria-label="${c.up}">+</button></div></div>`;
}
function table(t) {
  return `<h2>${esc(t.cap)}</h2>${t.note ? `<p class="muted">${esc(t.note)}</p>` : ''}<table class="tbl"><tr>${t.head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr>${t.rows.map((r) => `<tr>${r.map((d, i) => `<td class="num">${i ? esc(d) : `<b>${esc(d)}</b>`}</td>`).join('')}</tr>`).join('')}</table>`;
}

const bySlug = Object.fromEntries(pages.map((p) => [p.slug, p]));
const out = { updated: UPDATED, pages: [] };
for (const p of pages) {
  const calc = calcOf(p), def = Object.fromEntries(p.controls.map((c) => [c.id, c.val])), d = calc(def);
  const answer = p.answer(calc, x), desc = p.desc(calc, x), how = p.how(calc, x), faq = p.faq(calc, x), tb = p.table ? p.table(calc, x) : null;
  const url = SITE + p.slug;
  const C = JSON.stringify(p.controls.map((c) => ({ id: c.id, val: c.val, min: c.min, max: c.max, h: c.h ? 1 : 0 })));
  const script = `(function(){var E=window.BatchEngine;if(!E)return;var C=${C};\n${PRE}${p.consts || ''}${p.calc}\n${RUN}})();`;
  const ld = { '@context': 'https://schema.org', '@graph': [
    { '@type': 'WebPage', '@id': url, url, name: p.h1, description: desc, inLanguage: 'en-US', dateModified: UPDATED, isPartOf: { '@type': 'WebSite', name: 'batch.recipes', url: SITE } },
    { '@type': 'FAQPage', '@id': url + '#faq', mainEntity: [[p.h1, answer]].concat(faq).map(([q, a]) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: text(a) } })) },
  ] };
  const body = `<article class="g">
<h1>${esc(p.h1)}</h1>
<p class="lead">${esc(answer)}</p>
<section class="card calc" aria-label="Calculator">
${p.controls.map(stepper).join('\n')}
<div class="res" aria-live="polite"><p class="big num" data-o="big">${d.big}</p><p class="sub" data-o="sub">${d.sub}</p></div>
${d.tbl ? `<div class="out" data-o="tbl">${d.tbl}</div>` : ''}
</section>
${tb ? table(tb) : ''}
<h2>${p.howTitle || 'How it works'}</h2>
<${p.ordered ? 'ol' : 'ul'}>${how.map((h) => `<li>${esc(h)}</li>`).join('')}</${p.ordered ? 'ol' : 'ul'}>
<h2>Questions</h2>
${faq.map(([q, a]) => `<h3>${esc(q)}</h3>\n<p>${a}</p>`).join('\n')}
<p class="cta"><a class="btn" href="./" data-umami-event="Guide plan" data-umami-event-guide="${p.slug}">Plan your own recipe</a></p>
<h2>More guides</h2>
<ul class="gl">${p.more.map((s) => `<li><a href="${s}">${esc(bySlug[s].h1)}</a></li>`).join('')}<li><a href="guides">All guides</a></li></ul>
</article>
<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, '\\u003c')}</script>
<script src="engine.js"></script>
<script>${script}</script>`;
  if (/—|–/.test(body.replace(/<script>[\s\S]*?<\/script>/g, ''))) throw new Error('dash in page text: ' + p.slug);
  out.pages.push({ slug: p.slug, h1: p.h1, title: p.h1, desc, answer, sum: p.sum(calc, x), body, url });
}
process.stdout.write(JSON.stringify(out));
