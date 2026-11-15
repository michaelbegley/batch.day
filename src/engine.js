/* Batch Day engine: parse, stitch, scale, plan. No dependencies. */
(function (root) {
  'use strict';

  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  // ---------- text cleanup ----------
  const FRAC = { '¼': .25, '½': .5, '¾': .75, '⅓': 1 / 3, '⅔': 2 / 3, '⅛': .125, '⅜': .375, '⅝': .625, '⅞': .875, '⅙': 1 / 6, '⅚': 5 / 6 };

  function cleanLine(s) {
    return s
      .replace(/[\u2012-\u2015\u2212]/g, '-')
      .replace(/(?:\s+#[\w-]+)+\s*$/u, '')                              // trailing TikTok hashtags
      .replace(/^\s*(?:[\[|][ _|\]]{0,3}|[☐☑✓✔])\s*/u, '')          // checkboxes (incl. OCR forms)
      .replace(/^\s*(?:[•●◦▪\-–*·°©®¢«»eE]{1,3})\s+(?=\S)/u, '')            // bullets (incl. OCR forms)
      .replace(/(\d)\s?%(?=[\s-])/g, '$1½').replace(/(^|\s)%(?=\s)/g, '$1½')  // OCR: ½ read as %
      .replace(/(^|\s)[¥]?Y[2z](?=\s)/g, '$1½')
      .replace(/\btosp\b/g, 'tbsp').replace(/(\d\s*)Ibs?\b/g, '$1lbs').replace(/(\d\s*)0z\b/g, '$1oz').replace(/\s#\w+/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // keycap step numbers like "1️⃣"
  function stepNumber(s) {
    const m = s.match(/^\s*(\d{1,2})\uFE0F?\u20E3\s*/) || s.match(/^\s*(\d{1,2})[.)]\s+(?=[A-Za-z])/) ||
      s.match(/^\s*[‘’“”'"]?\s*(\d{1,2})\]?\s+(?=(?!(?:cups?|tsp|tbsp|teaspoons?|tablespoons?|oz|ounces?|lbs?|pounds?|large|medium|small|cloves?|cans?|grams?|g|ml)\b)[A-Z][a-z])/);
    return m ? { n: +m[1], rest: s.slice(m[0].length).trim() } : null;
  }

  // ---------- quantities ----------
  const NUM = String.raw`(?:\d+\s+\d+\/\d+|\d+\s*[¼½¾⅓⅔⅛⅜⅝⅞⅙⅚]|\d+\/\d+|\d*\.\d+|\d+|[¼½¾⅓⅔⅛⅜⅝⅞⅙⅚])`;
  const QTY_RE = new RegExp(String.raw`^(${NUM})(?:\s*(?:-|to)\s*(${NUM}))?`);

  function numVal(t) {
    t = t.trim();
    let m;
    if ((m = t.match(/^(\d+)\s+(\d+)\/(\d+)$/))) return +m[1] + m[2] / m[3];
    if ((m = t.match(/^(\d+)\s*([¼½¾⅓⅔⅛⅜⅝⅞⅙⅚])$/))) return +m[1] + FRAC[m[2]];
    if ((m = t.match(/^(\d+)\/(\d+)$/))) return m[1] / m[2];
    if (FRAC[t] !== undefined) return FRAC[t];
    return parseFloat(t);
  }

  const UNITS = [
    ['tbsp', /^(tablespoons?|tbsps?|tbs|tbl|T)\b\.?/],
    ['tsp', /^(teaspoons?|tsps?|t)\b\.?/],
    ['cup', /^(cups?|c)\b\.?/],
    ['fl oz', /^(fl\.?\s*oz|fluid ounces?)\b\.?/],
    ['oz', /^(ounces?|oz)\b\.?/],
    ['lb', /^(pounds?|lbs?)\b\.?/],
    ['g', /^(grams?|g)\b\.?/],
    ['kg', /^(kilograms?|kgs?)\b\.?/],
    ['ml', /^(millilit(er|re)s?|ml)\b\.?/],
    ['l', /^(lit(er|re)s?|l)\b\.?/],
    ['clove', /^(cloves?)\b/],
    ['can', /^(cans?)\b/],
    ['pinch', /^(pinch(es)?)\b/],
    ['bunch', /^(bunch(es)?)\b/],
    ['stalk', /^(stalks?)\b/],
    ['slice', /^(slices?)\b/],
    ['package', /^(packages?|pkgs?|packs?)\b/],
    ['jar', /^(jars?)\b/],
    ['box', /^(box(es)?)\b/],
    ['bag', /^(bags?)\b/],
    ['bottle', /^(bottles?)\b/],
    ['carton', /^(cartons?)\b/],
    ['container', /^(containers?|tubs?)\b/],
    ['handful', /^(handfuls?)\b/],
    ['inch', /^(inch(es)?|in\.)(\s*(piece|knob|chunk)s?)?(\s+of)?(?=\s)/],
    ['head', /^(heads?)\b/],
    ['sprig', /^(sprigs?)\b/],
  ];
  // things you buy whole: round up to what the store sells
  const PACK = ['can', 'jar', 'box', 'bag', 'bottle', 'package', 'carton', 'container'];
  // "(15 oz)", "(14.5-ounce)", "(200 g)" right before or after a package word
  const SIZE_RE = /^\(\s*(\d+(?:\.\d+)?)\s*-?\s*(oz|ounces?|ounce|g|grams?|ml|lbs?|pounds?|fl\.?\s*oz)\.?\s*\)\s*/i;
  function sizeOf(n, u) {
    u = u.toLowerCase();
    if (/^g/.test(u)) return { n, u: 'g', oz: n * 0.035274 };
    if (/^ml/.test(u)) return { n, u: 'ml', oz: n / 29.57 };
    if (/^(lb|pound)/.test(u)) return { n, u: 'lb', oz: n * 16 };
    return { n, u: 'oz', oz: n };
  }
  // volume in tsp, weight in oz
  const VOL_TSP = { tsp: 1, tbsp: 3, cup: 48, 'fl oz': 6, ml: 0.2029, l: 202.9 };
  const WT_OZ = { oz: 1, lb: 16, g: 0.035274, kg: 35.274 };

  // OCR suspicion: "%"/"Y2"/"$" where a number should be
  function suspicious(raw) {
    return /(^|\s)(\d*%|Y2|\$)(\s|$)/.test(raw) || /^\d{2}\/\d\b/.test(raw.trim()) || /^\.\d/.test(raw.trim());
  }

  function parseIngredient(raw) {
    const line = cleanLine(raw);
    const flag = suspicious(raw) || (/[%¥]|Y2/.test(raw) && /½/.test(line)) || /^\s*\$/.test(raw);
    let fixed = line.replace(/^(\d)([1-3])\/([2-4])\b/, (m, a, b, c) => (+b < +c ? `${a} ${b}/${c}` : m));
    let rest = fixed, qty = null, qtyHi = null, unit = null;
    const sci = /^\d+(\.\d+)?e[+-]?\d+/i.test(rest);
    const neg = /^[-−–]\s*\d/.test(rest);
    const m = sci || neg ? null : rest.match(QTY_RE);
    if (m) {
      qty = numVal(m[1]);
      qtyHi = m[2] ? numVal(m[2]) : null;
      rest = rest.slice(m[0].length).trim();
    }
    // package sizes: "1 (15 oz) can beans", "2 (14.5-ounce) cans", "1 jar (15 oz) pesto", "1 28-ounce can tomatoes"
    let size = null, sm;
    if (qty != null && (sm = rest.match(SIZE_RE))) { size = sizeOf(+sm[1], sm[2]); rest = rest.slice(sm[0].length).trim(); }
    else if (qty != null && (sm = rest.match(/^(\d+(?:\.\d+)?)\s*-?\s*(ounces?|ounce|oz|g|grams?)\.?\s+(?=(cans?|jars?|box(es)?|bags?|bottles?|packages?|pkgs?|cartons?|containers?|tubs?)\b)/i))) { size = sizeOf(+sm[1], sm[2]); rest = rest.slice(sm[0].length).trim(); }
    else if (qty != null && (sm = rest.match(/^-?\s*(ounces?|ounce|oz)\.?\s+(?=(cans?|jars?|box(es)?|bags?|bottles?|packages?|pkgs?)\b)/i))) { size = sizeOf(qty, 'oz'); qty = 1; qtyHi = null; rest = rest.slice(sm[0].length).trim(); }
    if (qty == null) rest = rest.replace(/^(a|an)\s+(?=(pinch|handful|bunch|head|sprig)\b)/i, '');
    for (const [u, re] of UNITS) {
      const ci = new RegExp(re.source.replace('|T)', ')').replace('|t)', ')'), 'i');
      const um = rest.match(ci) || rest.match(re);
      if (um) { unit = u; rest = rest.slice(um[0].length).trim(); break; }
    }
    if (!size && unit && PACK.includes(unit) && (sm = rest.match(SIZE_RE))) { size = sizeOf(+sm[1], sm[2]); rest = rest.slice(sm[0].length).trim(); }
    // "pinch of thyme", "a handful of spinach": one
    if (qty == null && unit && ['pinch', 'handful', 'bunch', 'head', 'sprig'].includes(unit)) qty = 1;
    // a size with no package word: "1 (15 oz) tomato sauce" is a can
    if (size && !unit) unit = 'can';
    let name = rest.replace(/^of\s+/i, '').trim();
    let note = '';
    const cm = name.match(/^(.*?)(,\s*|\s+\()(.*)$/);
    if (cm && cm[1].length > 2) { note = (cm[3] || '').replace(/\)$/, ''); name = cm[1]; }
    const toTaste = /to taste/i.test(line);
    name = name.replace(/,?\s*\bto taste\b/i, '').trim() || name;
    const optional = /optional/i.test(line);
    if (qty === 0 && !qtyHi) qty = null;
    let odd = sci || neg;
    if (qty != null && unit && WT_OZ[unit] && qty * WT_OZ[unit] > 50 * 16) odd = true;
    if (qty != null && !unit && qty > 500) odd = true;
    if (qty != null && unit && VOL_TSP[unit] && qty * VOL_TSP[unit] > 48 * 40) odd = true;
    const out = { raw: line, qty, qtyHi, unit, name: name.trim(), note: note.trim(), toTaste, optional, flag, odd };
    if (size) out.size = size;
    return out;
  }

  // ---------- classify ----------
  const CLASSES = [
    ['salt', /\bsalt\b(?!ed)/i],
    ['finisher', /\b(lime|lemon|vinegar|cilantro|parsley|basil|mint|dill|chives|green onion tops|scallion tops|chili oil|chili crisp|hot sauce|sesame seeds|fresh herbs|sour cream topping)\b/i],
    ['baking', /\b(flour|baking powder|baking soda|yeast|cornmeal|cocoa|powdered sugar|granulated sugar|brown sugar|sugar|vanilla|espresso powder|chocolate|cornflakes|sprinkles)\b/i],
    ['protein', /\b(chicken|thighs?|breasts?|beef|steak|pork|turkey|sausage|bacon|tofu|tempeh|shrimp|salmon|fish|cod|lamb|ground|beans?|lentils?|chickpeas?)\b/i],
    ['grain', /\b(rice|pasta|noodles?|quinoa|orzo|couscous|barley|oats|farro|spaghetti|penne)\b/i],
    ['liquid', /\b(broth|stock|water|coconut milk|milk|cream|wine|tomato sauce|crushed tomatoes|passata)\b/i],
    ['oil', /\b(oil|butter|ghee)\b/i],
    ['aromatic', /\b(garlic|ginger|shallots?|onions?|green onion whites|scallion whites|leeks?|celery|lemongrass)\b/i],
    ['spice', /\b(pepper|paprika|cumin|chili|chile|curry|cayenne|oregano|thyme|rosemary|cinnamon|nutmeg|turmeric|garlic powder|onion powder|flakes|seasoning|soy sauce|fish sauce|gochujang|miso|paste)\b/i],
    ['veg', /\b(bok choy|spinach|kale|broccoli|carrots?|peppers?|zucchini|mushrooms?|cabbage|peas|corn|potato(es)?|sweet potato(es)?|squash|tomato(es)?|greens|cauliflower|green beans)\b/i],
    ['dairy', /\b(cheese|cream cheese|sour cream|yogurt|eggs?)\b/i],
  ];
  function classify(ing, section) {
    const s = (ing.name + ' ' + ing.note).toLowerCase();
    const sec = (section || '').toLowerCase();
    if (/finish|garnish|topping|to serve|serving/.test(sec) && !/cream cheese topping/.test(sec)) return 'finisher';
    if (/\b(for (serving|garnish|topping)|to serve|to garnish)\b/.test(s + ' ' + (ing.raw || '').toLowerCase()) && !/\b(rice|quinoa|couscous|noodles?|pasta|tortillas?|bread|naan)\b/.test(s)) return 'finisher';
    if (/\bground (cumin|cinnamon|black pepper|white pepper|pepper|turmeric|ginger|nutmeg|paprika|cayenne|mustard|coriander|cloves|allspice|cardamom|fennel|chil(i|e)s?)\b/.test(s)) return 'spice';
    if (/\b(garam masala|mustard powder|dry mustard|chipotles?|adobo|bay lea(f|ves)|coriander|cardamom|allspice|five[- ]spice|za.?atar|sumac|cloves, ground|ground cloves|smoked paprika|italian seasoning|herbes)\b/.test(s)) return 'spice';
    if (/\b(broth|stock|coconut milk)\b/.test(s)) return 'liquid';
    if (/\b(cheese|sour cream|yogurt|eggs?)\b/.test(s)) return 'dairy';
    if (/garlic powder|onion powder/.test(s)) return 'spice';
    if (/ginger paste|garlic paste/.test(s)) return 'aromatic';
    if (/curry paste|tomato paste|chili paste|miso paste/.test(s)) return 'spice';
    if (/oil/.test(s) && /chili oil|chili crisp/.test(s)) return 'finisher';
    for (const [c, re] of CLASSES) if (re.test(s)) return c;
    return 'other';
  }

  // Baking is decided from the title and the ingredients only, never from the steps ("a cookie sheet" is not a cookie).
  // Food safety: a recipe with meat or fish is never baking, so it never gets room-temp storage.
  const BAKE_TITLE = /\b(cakes?|muffins?|cookies?|brownies?|blondies?|cupcakes?|shortbread|pie crusts?|pastry|pastries|scones?|biscuits?|cornbread|banana bread|quick bread|loaf cake|bread|rolls|buns|pancakes?|waffles?|crumble|cobbler|bars|tart|galette)\b/;
  const MEAT = /\b(chicken|beef|steak|pork|turkey|sausages?|bacon|ham|lamb|veal|duck|goose|venison|bison|shrimp|prawns?|salmon|fish|cod|tilapia|halibut|trout|tuna|crab|lobster|clams?|mussels|scallops|oysters|squid|calamari|anchov(y|ies)|sardines|kielbasa|chorizo|pepperoni|salami|prosciutto|pancetta|brisket|hot ?dogs?|franks|frankfurters|bratwurst|meatballs?|jerky|ground (meat|beef|pork|turkey|chicken|lamb))\b/;
  // savory proteins that make a bake a meal: never room temp
  const PERISH = /\b(beans?|lentils?|tofu|tempeh|chickpeas?|refried|cheese|cheddar|mozzarella|parmesan|ricotta|feta|cream cheese|cottage|custard|whipped cream|heavy cream|sour cream|pumpkin puree|cream filling)\b/;
  const isMeat = (n) => MEAT.test(String(n).toLowerCase()) && !/\b(broth|stock|bouillon|soup|base|seasoning|flavou?r|powder|gravy)\b/i.test(n);
  const SAFE = new RegExp('^(?:' + [
    '(all[- ]purpose |bread |cake |self[- ]rising |whole wheat |white |almond |oat )?flour', 'cornmeal', 'cornstarch', 'oats?', 'rolled oats', 'quick oats',
    '((granulated|white|brown|light brown|dark brown|powdered|confectioners.?|cane|coconut|caster|turbinado|raw) )?sugar', 'honey', 'maple syrup', 'molasses', '(light |dark )?corn syrup', 'golden syrup',
    '(unsalted |salted |softened |melted |cold )*butter', '(vegetable |canola |neutral |coconut |olive )?oil', 'shortening',
    '(large )?eggs?', '(large )?egg (yolks?|whites?)',
    '(whole |2% |skim |low[- ]fat )?milk', 'buttermilk', 'water', '(warm )?water',
    'baking (powder|soda)', '(active dry |instant )?yeast', '(kosher |sea |table )?salt', '(pure )?vanilla( extract)?', '(almond|lemon|orange) extract',
    '(ground )?(cinnamon|nutmeg|ginger|allspice|cloves|cardamom)', 'pumpkin pie spice', 'espresso powder', 'instant coffee',
    '((semi|bitter)[- ]?sweet |milk |dark |white )?chocolate( chips| chunks)?', '(unsweetened |dutch[- ]process )?cocoa( powder)?', 'sprinkles',
    '(chopped |toasted )?(walnuts|pecans|almonds|hazelnuts|peanuts|macadamia nuts|nuts)', 'peanut butter', '(raisins|dried cranberries|dried cherries|dates|currants)',
    '(ripe |mashed |overripe )*bananas?', 'apples?', 'applesauce', '(fresh |frozen )?(blueberries|raspberries|strawberries|berries|cranberries)', '(shredded |grated )?(carrots?|zucchini)',
    '(lemon|orange|lime) (zest|juice)', 'zest of (a |one )?(lemon|orange|lime)', '(shredded |sweetened )?coconut', '(jam|jelly|preserves)', 'poppy seeds', 'chia seeds', 'flax( seeds| meal)?'
  ].join('|') + ')$');
  function shelfStable(ings, title) {
    if (/\b(pies?|custards?|flan|puddings?|cheesecakes?|tarts?|bars|quiche|tres leches|cream|frosting|icing|filling|eclairs?|cannoli|tiramisu|trifle)\b/i.test(title)) return false;
    if (!ings.every((i) => SAFE.test(String(i.name).toLowerCase().replace(/[,(].*$/, '').replace(/\s+/g, ' ').trim()))) return false;
    if (!ings.some((i) => /\b(sugar|honey|maple|molasses|syrup|chocolate)\b/i.test(i.name))) return false; // no sweetener: biscuits, savory muffins go in the fridge
    // more egg and milk than flour is a custard, not a cake
    const cups = (i) => (i.qty == null ? 0 : i.unit && VOL_TSP[i.unit] ? mid(i) * VOL_TSP[i.unit] / 48 : !i.unit && /\beggs?\b|yolks?|whites?/i.test(i.name) ? mid(i) * 0.25 : 0);
    const wet = ings.filter((i) => /\b(eggs?|yolks?|whites?|milk|buttermilk)\b/i.test(i.name)).reduce((a, i) => a + cups(i), 0);
    const dry = ings.filter((i) => /\b(flour|cornmeal|oats)\b/i.test(i.name)).reduce((a, i) => a + cups(i), 0);
    return wet <= dry;
  }
  function isBaking(ings, title) {
    const names = ings.map((i) => i.name).join(' ').toLowerCase();
    const t = (title || '').toLowerCase();
    const meat = ings.some((i) => isMeat(i.name)) || isMeat(t);
    // more meat than flour by weight (chili with a cornbread top, sausage and biscuits): a meal, not a bake
    const oz = (i) => (i.qty == null ? 0 : i.unit && WT_OZ[i.unit] ? mid(i) * WT_OZ[i.unit] : i.unit && VOL_TSP[i.unit] ? mid(i) * VOL_TSP[i.unit] / 48 * 4.5 : 0);
    const meatOz = ings.filter((i) => isMeat(i.name)).reduce((a, i) => a + oz(i), 0), flourOz = ings.filter((i) => /\b(flour|cornmeal)\b/i.test(i.name)).reduce((a, i) => a + oz(i), 0);
    if (meatOz >= 12 && meatOz > flourOz) return false;
    const flour = /\b(flour|cornmeal)\b/.test(names.replace(/flour tortillas?/g, ''));
    const leaven = /baking (powder|soda)|\byeast\b/.test(names);
    const sweet = /\bsugar\b|\bhoney\b|\bmaple syrup\b|\bchocolate\b/.test(names);
    const rich = /\b(eggs?|butter)\b/.test(names);
    if (BAKE_TITLE.test(t) && (flour || /\b(oats|sugar)\b/.test(names))) return true; // muffins, scones, cornbread: a bake, even with ham in it (stored as a meal, see batchDay)
    if (meat) return false; // breaded or fried meat (flour, baking powder) is a meal, not a bake
    if (flour && leaven) return true;
    if (flour && sweet && rich) return true;
    return false;
  }

  // ---------- parse a whole recipe ----------
  function parseRecipe(text) {
    const lines = text.split(/\r?\n/).map((l) => l.replace(/\s+$/, ''));
    const r = { title: '', yield: null, yieldText: '', sections: [], ingredients: [], steps: [], notes: [], flags: [] };
    let mode = 'ing', section = '', stepBuf = null;
    const pushStep = () => { if (stepBuf) { r.steps.push(stepBuf); stepBuf = null; } };
    for (let raw of lines) {
      const line = cleanLine(raw);
      if (!line) continue;
      if (/^(less|more|search\b|add comment|comment recipe|#)/i.test(line)) continue;
      if (/^(jump to recipe|print recipe|pin recipe|save recipe|rate (this )?recipe|share( this)?( recipe)?|skip to (content|recipe)|go to recipe|watch (the )?video|leave a review)\b/i.test(line) && line.length < 40) continue; // web page buttons pasted with the recipe
      const ym = line.match(/\b(serves|servings?|makes|yield[s]?)\s*:?\s*(\d+)(?:\s*(?:-|to)\s*(\d+))?/i);
      if (ym) {
        r.yield = ym[3] ? (+ym[2] + +ym[3]) / 2 : +ym[2]; r.yieldText = line;
        // "Chicken curry (serves 4)": keep the part before the yield as the title
        if (!r.title && !r.ingredients.length) {
          const before = line.slice(0, ym.index).replace(/[(\[|,:·•\-–—\s]+$/u, '').replace(/[^\p{L}\p{M}\p{N}\s'&-]/gu, '').trim();
          if (before.length > 2 && !QTY_RE.test(before)) r.title = before.replace(/\s*recipe.*$/i, '').trim() || before;
        }
        continue;
      }
      if (/^(instructions|directions|method|steps|preparation)\s*:?$/i.test(line)) { mode = 'step'; pushStep(); continue; }
      if (/^(ingredients)\s*:?$/i.test(line)) { mode = 'ing'; continue; }
      const sn = stepNumber(raw.trim());
      if (sn) { mode = 'step'; pushStep(); stepBuf = { n: sn.n, text: sn.rest.replace(/(?:\s+#[\w-]+)+\s*$/u, '') }; continue; }
      if (mode === 'step') {
        if (stepBuf) stepBuf.text += ' ' + line; else stepBuf = { n: r.steps.length + 1, text: line };
        if (/[.!]$/.test(line) && !/^\d/.test(line)) { /* keep merging until next number */ }
        continue;
      }
      // the first line before any ingredient or section, with no amount, is the title ("Chicken tortilla soup", "Minestrone")
      if (!r.title && !r.ingredients.length && !r.sections.length && !QTY_RE.test(line) && !/:$/.test(line) && line.length < 80 && line.split(' ').length <= 10 &&
        !/^(ingredients|instructions|directions|method)\b/i.test(line) && !/^(for the|to serve|for serving|garnish)/i.test(line)) {
        r.title = line.replace(/\s+recipe\b.*$/i, '').replace(/^[^\p{L}\p{N}<"'(]+/u, '').trim() || line; continue;
      }
      // header? ends with a colon, or a known section word, or a short unbulleted line that isn't a food
      const bulleted = /^\s*(?:\[[^\]]{0,3}\]|\|[ _|\]]*\|?|[☐☑✓✔•●◦▪\-–*·°©®¢«»]|[eE]\s)/u.test(raw);
      const VOCAB = /^(chicken|beef|pork|meat|protein|aromatics|broth|soup|sauce|marinade|dressing|rice|noodles|grains?|veggies|vegetables|toppings?|garnish(es)?|to serve|for serving|optional.*|cake|frosting|icing|filling|crust|dough|batter|glaze|base|seasoning|spice mix|salad|cream cheese topping|chocolate cornflakes|for the .*)$/i;
      const isHeader = !QTY_RE.test(line) && !/\d/.test(line) && line.length < 40 && (
        (/:$/.test(line)) || VOCAB.test(line.replace(/:$/, '')) ||
        (!bulleted && line.split(' ').length <= 3 && /^[A-Z]/.test(line) && classify({ name: line, note: '' }, '') === 'other' && aisleOf(line) === 8 &&
          !/\b(nuts|seeds|honey|chips|rind|crackers|croutons|bread|buns|syrup|jam|salsa|pesto|olives|pickles|capers|mayo|ketchup|mustard|sriracha|tahini|cheese|parmesan|cream|butter|milk|yogurt|herbs?)\b/i.test(line)));
      if (isHeader) {
        if (!r.title && /recipe/i.test(line)) { r.title = line.replace(/\s*recipe.*$/i, '').trim(); continue; }
        // the first short line before anything else is the title, not a section ("Minestrone", "Baked ziti")
        if (!r.title && !r.ingredients.length && !r.sections.length && !/:$/.test(line) && !VOCAB.test(line)) { r.title = line; continue; }
        section = line.replace(/:$/, '');
        if (!r.sections.includes(section)) r.sections.push(section);
        continue;
      }
      if (/recipe/i.test(line) && !QTY_RE.test(line) && !r.title) { r.title = line.replace(/\s*recipe.*$/i, '').replace(/[^\p{L}\p{M}\p{N}\s'&-]/gu, '').trim(); continue; }
      const prev = r.ingredients[r.ingredients.length - 1];
      // a lowercase line with no number is a wrapped note only when it reads like one; "kosher salt" or "fresh parsley, chopped" is its own ingredient
      if (prev && !QTY_RE.test(line) && (/^[a-z(]/.test(line) || /^[A-Za-z ]{1,20}\)$/.test(line))) {
        const cont = /^\(|^[A-Za-z ]{1,20}\)$/.test(line) || /[,(]$/.test(prev.raw) || (prev.raw.split('(').length > prev.raw.split(')').length) ||
          /^(or|and|plus|such as|divided|about|roughly|cut|chopped|minced|diced|sliced|peeled|seeded|trimmed|finely|thinly|coarsely|roughly|room temp|softened|melted|at room|if |for the|drained|rinsed|packed|heaping|optional|see note)\b/.test(line);
        const foodish = classify({ name: line, note: '' }, '') !== 'other' || /\b(salt|pepper|parsley|cheese|parmesan|flakes|thyme|spinach|herbs?|sauce|oil|sugar|seeds|nuts|onions?|scallions?|cilantro|basil|lemon|lime)\b/i.test(line);
        if (cont || !foodish) { prev.note = (prev.note + ' ' + line).trim(); continue; }
      }
      const ing = parseIngredient(line);
      // drop lines that are clearly not ingredients
      if (!ing.qty && !ing.toTaste && !/^(salt|pepper|neutral|green onion|baby|fresh|optional|red chili|parish|cilantro|chili|black pepper)/i.test(ing.name) && line.split(' ').length > 7) { r.notes.push(line); continue; }
      if (!section && !r.ingredients.length && ing.qty == null && !ing.toTaste && !(r.title && classify(ing, '') !== 'other')) { r.notes.push(line); continue; }
      ing.section = section;
      ing.cls = classify(ing, section);
      if (ing.cls === 'liquid' && ing.unit === 'oz') ing.unit = 'fl oz';
      const key = norm(ing.name);
      if (key && r.ingredients.some((x) => norm(x.name) === key && x.section === section)) continue;
      if (ing.flag) r.flags.push({ type: 'amount', line: ing.raw, msg: 'Amount may have been misread' });
      if (ing.qtyHi) r.flags.push({ type: 'range', line: ing.raw, msg: 'Range: using the middle' });
      if (!ing.qty && !ing.toTaste && ing.cls !== 'finisher' && !ing.optional && !['salt', 'oil'].includes(ing.cls) && !/pepper|for cooking|for frying/i.test(ing.raw)) r.flags.push({ type: 'noamount', line: ing.raw, msg: 'No amount given' });
      r.ingredients.push(ing);
    }
    pushStep();
    r.steps.sort((a, b) => a.n - b.n);
    // de-dup steps by number
    const best = {};
    r.steps.forEach((st) => { if (!best[st.n] || st.text.length > best[st.n].text.length) best[st.n] = st; });
    r.steps = Object.values(best).sort((a, b) => a.n - b.n);
    const lastStep = r.steps[r.steps.length - 1];
    if (lastStep && !/[.!)]$/.test(lastStep.text.trim())) r.flags.push({ type: 'cutoff', line: lastStep.text.slice(-40), msg: 'Steps look cut off' });
    r.baking = isBaking(r.ingredients, r.title || (lines.find((l) => l.trim()) || ''));
    // a bake with meat, fish, beans, cheese or cream (or no sugar at all) is stored like a meal, never at room temp
    // Room temp only for a plain sweet bake where every ingredient is on a short safe list (an allow list, so an
    // ingredient we don't know, like "ground chuck" or "pumpkin", always means the fridge). Pies, custards, bars and puddings: fridge.
    // Two kinds of bake that never sit out: a savory bake (meat, fish, beans, tofu, or no sweetener at all) is a meal and
    // gets Batch day; a sweet bake with cream cheese, cream, custard and the like (fridgeBake) stays a bake but is kept in the fridge.
    { const n = r.ingredients.map((i) => i.name).join(' ').toLowerCase();
      r.savoryBake = r.baking && (r.ingredients.some((i) => isMeat(i.name)) || /\b(beans?|lentils?|tofu|tempeh|chickpeas?|refried)\b/.test(n) ||
        !r.ingredients.some((i) => /\b(sugar|honey|maple|molasses|syrup|chocolate)\b/i.test(i.name)));
      r.fridgeBake = r.baking && !r.savoryBake && !shelfStable(r.ingredients, r.title || ''); }
    if (!r.yield) {
      const prot = r.ingredients.filter((i) => i.cls === 'protein' && i.qty && (i.unit === 'lb' || i.unit === 'oz' || i.unit === 'g' || i.unit === 'kg'));
      if (prot.length) {
        const oz = prot.reduce((s, i) => s + mid(i) * WT_OZ[i.unit], 0);
        r.yield = Math.max(1, Math.round(oz / 6));
        r.yieldGuessed = true;
        r.flags.push({ type: 'yield', line: '', msg: `No servings listed. Guessing ${r.yield} from the protein; change it if you know.` });
      } else { const g = r.baking ? 12 : 4; r.yield = g; r.yieldGuessed = true; r.flags.push({ type: 'yield', line: '', msg: `No servings listed. Guessing ${g}; change it if you know.` }); }
    }
    return r;
  }

  const mid = (i) => (i.qtyHi ? (i.qty + i.qtyHi) / 2 : i.qty);

  // ---------- stitch several screenshots ----------
  function overlap(a, b) { // lines at end of a that match start of b
    const A = a.split('\n').map(norm).filter(Boolean), B = b.split('\n').map(norm).filter(Boolean);
    let best = 0;
    for (let k = Math.min(A.length, B.length); k >= 2; k--) {
      let ok = 0;
      for (let i = 0; i < k; i++) if (A[A.length - k + i] === B[i]) ok++;
      if (ok >= Math.max(2, Math.ceil(k * 0.6))) { best = k; break; }
    }
    // weaker signal: shared line anywhere
    const shared = A.filter((l) => l.length > 12 && B.includes(l)).length;
    return { tail: best, shared };
  }
  function stitch(texts) {
    const n = texts.length;
    if (n <= 1) return [{ order: [0], text: texts[0] || '' }];
    const W = [...Array(n)].map(() => Array(n).fill(0));
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) { const o = overlap(texts[i], texts[j]); W[i][j] = o.tail * 10 + o.shared; }
    // components by shared lines
    const parent = [...Array(n).keys()];
    const find = (x) => (parent[x] === x ? x : (parent[x] = find(parent[x])));
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (W[i][j] > 0) parent[find(i)] = find(j);
    const groups = {};
    for (let i = 0; i < n; i++) (groups[find(i)] = groups[find(i)] || []).push(i);
    const out = [];
    for (const g of Object.values(groups)) {
      // greedy chain: start = node with least incoming weight
      const inW = (j) => g.reduce((s, i) => s + (i === j ? 0 : W[i][j]), 0);
      let cur = g.slice().sort((a, b) => inW(a) - inW(b))[0];
      const order = [cur], left = new Set(g.filter((x) => x !== cur));
      while (left.size) {
        let nx = null, bw = -1;
        for (const j of left) if (W[cur][j] > bw) { bw = W[cur][j]; nx = j; }
        order.push(nx); left.delete(nx); cur = nx;
      }
      // texts with step numbers go after the ingredient-only ones, in step order
      const minStep = (i) => { let m = Infinity; texts[i].split('\n').forEach((l) => { const sn = stepNumber(l); if (sn) m = Math.min(m, sn.n); }); return m; };
      const chainPos = new Map(order.map((x, k) => [x, k]));
      const key = (i) => (minStep(i) === Infinity ? -1 : minStep(i));
      order.sort((a, b) => (key(a) - key(b)) || (chainPos.get(a) - chainPos.get(b)));
      // merge, dropping duplicate lines (keep first time we see a line)
      const seen = new Set(), lines = [];
      for (const idx of order) for (const l of texts[idx].split('\n')) {
        const k = norm(l);
        if (k && k.length > 3 && seen.has(k)) continue;
        if (k) seen.add(k);
        lines.push(l);
      }
      out.push({ order, text: lines.join('\n') });
    }
    return out;
  }

  // ---------- scaling ----------
  // past 2x, ease only the part above 2x, so there's no cliff (9 meals never gets less salt than 8)
  const EASE = { salt: 0.7, spice: 0.75, oil: 0.6 };
  function eases(ing) {
    if (!EASE[ing.cls]) return false;
    // butter and ghee in a roux, mash or sauce are an ingredient, not frying fat
    if (ing.cls === 'oil' && /butter|ghee/i.test(ing.name) && !/for (cooking|frying|the pan|greasing|searing)/i.test(ing.raw || '')) return false;
    return true;
  }
  function factorFor(cls, f, baking, ing) {
    if (f <= 2 || baking || !EASE[cls] || (ing && !eases(ing))) return f;
    return 2 + EASE[cls] * (f - 2);
  }

  function niceFrac(x, step) {
    const r = Math.round(x / step) * step;
    return r <= 0 ? step : r;
  }
  function fmtNum(x) {
    const whole = Math.floor(x + 1e-9), frac = x - whole;
    const map = [[0, ''], [.125, '⅛'], [.25, '¼'], [1 / 3, '⅓'], [.5, '½'], [2 / 3, '⅔'], [.75, '¾'], [1, '']];
    let best = map[0], d = 9;
    for (const m of map) if (Math.abs(frac - m[0]) < d) { d = Math.abs(frac - m[0]); best = m; }
    const w = best[0] === 1 ? whole + 1 : whole;
    if (!w && !best[1]) return '0';
    return (w ? w : '') + best[1];
  }
  // turn a volume (tsp) into a friendly measure
  // cups to the nearest quarter or third, whichever is closer
  function cupFrac(c) {
    const q = Math.round(c * 4) / 4, t = Math.round(c * 3) / 3;
    const r = Math.abs(t - c) < Math.abs(q - c) - 1e-9 ? t : q;
    return r <= 0 ? .25 : r;
  }
  function fmtVol(tsp) {
    if (tsp < 3 * 0.95) return [niceFrac(tsp, .25), 'tsp'];
    if (tsp < 12 * 0.93) { const t = niceFrac(tsp / 3, .5); return Math.abs(t * 3 - tsp) / tsp > 0.06 ? [niceFrac(tsp, .25), 'tsp'] : [t, 'tbsp']; } // 4 tsp stays 4 tsp, not 1½ tbsp
    if (tsp < 24 * 0.95) {
      // between ¼ and ½ cup: a cup measure only when it's close, otherwise tablespoons
      const c = cupFrac(tsp / 48);
      if (Math.abs(c * 48 - tsp) / tsp <= 0.07) return [c, 'cup'];
      return [niceFrac(tsp / 3, .5), 'tbsp'];
    }
    return [cupFrac(tsp / 48), 'cup'];
  }
  function fmtWt(oz) {
    if (oz >= 16) return [Math.ceil(oz / 16 * 4 - 0.15) / 4, 'lb']; // up to the quarter pound, so you're not short
    return [Math.max(.5, Math.round(oz * 2) / 2), 'oz'];
  }
  function fmtMetric(q, u) {
    if (u === 'g' || u === 'kg') { const g = q * (u === 'kg' ? 1000 : 1); return g >= 1000 ? [Math.round(g / 100) / 10, 'kg'] : [Math.max(5, Math.round(g / 5) * 5), 'g']; }
    const ml = q * (u === 'l' ? 1000 : 1); return ml >= 1000 ? [Math.round(ml / 100) / 10, 'l'] : [Math.max(5, Math.round(ml / 5) * 5), 'ml'];
  }
  const PLURAL = { cup: 'cups', clove: 'cloves', can: 'cans', slice: 'slices', stalk: 'stalks', bunch: 'bunches', package: 'packages', pinch: 'pinches', jar: 'jars', box: 'boxes', carton: 'cartons', container: 'containers', bag: 'bags', bottle: 'bottles', handful: 'handfuls', head: 'heads', sprig: 'sprigs', inch: 'inches' };
  function show(n, u) {
    const label = n > 1 && PLURAL[u] ? PLURAL[u] : u;
    const num = ['g', 'kg', 'ml', 'l'].includes(u) ? String(n) : fmtNum(n);
    return u ? `${num} ${label}` : num;
  }
  // "2 onion" -> "2 onions": the plural of a counted item's first word or last word
  function plural(name, n) {
    if (!name) return name;
    const pl = (w) => (/(s|sh|ch|x)$/i.test(w) ? w : /[^aeiou]y$/i.test(w) ? w.slice(0, -1) + 'ies' : /(potato|tomato)$/i.test(w) ? w + 'es' : /leaf$/i.test(w) ? w.slice(0, -1) + 'ves' : w + 's');
    const m = name.match(/^(.*?\b)(eggs?|onions?|carrots?|potato(?:es)?|tomato(?:es)?|peppers?|jalape[nñ]os?|limes?|lemons?|zucchinis?|shallots?|avocados?|bananas?|apples?|tortillas?|cucumbers?|leeks?|chiles?|chilies?|bay leaf|bay leaves|chipotles?|thighs?|breasts?|fillets?|sausages?|cloves?|parsnips?|turnips?|beets?|whole chickens?|chickens?|lemons?|oranges?|peaches|peach|pears?|zucchini|eggplants?|squash(?:es)?|heads? of garlic)(\b.*)$/i);
    if (!m || m[3].trim()) return name;
    const w = m[2];
    if (!(n > 1)) { // one, or less: singular
      const sg = /ves$/i.test(w) ? w.replace(/ves$/i, 'f') : /(potato|tomato)es$/i.test(w) ? w.slice(0, -2) : /(sh|ch)es$/i.test(w) ? w.slice(0, -2) : /[^s]s$/i.test(w) ? w.slice(0, -1) : w;
      return m[1] + sg + m[3];
    }
    if (/s$|ves$|zucchini$/i.test(w)) return name;
    return m[1] + pl(w) + m[3];
  }

  const upTo = (q, step, tol) => Math.max(step, Math.ceil(q / step - tol) * step);
  function scaleIngredient(ing, f, baking) {
    const out = Object.assign({}, ing);
    if (ing.qty == null) { out.scaled = ing.toTaste ? 'to taste' : (!['spice', 'aromatic', 'veg', 'protein'].includes(ing.cls) || Math.abs(f - 1) < .05 || /\b(rind|bay|stick|pod)\b/i.test(ing.name) ? '' : `${Math.round(f * 10) / 10}× usual`); return out; }
    const q = mid(ing) * factorFor(ing.cls, f, baking, ing);
    out.adjusted = f > 2 && !baking && EASE[ing.cls] && eases(ing);
    let n = q, u = ing.unit;
    if (u && VOL_TSP[u] && !['ml', 'l'].includes(u)) [n, u] = fmtVol(q * VOL_TSP[u]);
    else if (u && WT_OZ[u] && !['g', 'kg'].includes(u)) [n, u] = fmtWt(q * WT_OZ[u]);
    else if (['g', 'kg', 'ml', 'l'].includes(u)) [n, u] = fmtMetric(q, u);
    else if (u && PACK.includes(u)) n = upTo(q, 1, 0.1); // cans and jars: whole ones, rounded up
    else if (u === 'pinch') n = Math.max(1, Math.round(q));
    else if (u) n = upTo(q, 1, 0.15); // cloves, stalks, bunches, heads, sprigs
    else if (/\beggs?\b/i.test(ing.name)) n = Math.max(1, Math.round(q));
    else n = upTo(q, .5, 0.1); // whole produce: round up to the half, so you're never short
    out.qtyScaled = q;
    out.scaled = show(n, u) + (ing.size && u && PACK.includes(u) ? ` (${ing.size.n} ${ing.size.u})` : '');
    out.label = u && u !== 'inch' ? ing.name : plural(ing.name, n);
    return out;
  }

  // ---------- Batch Day plan ----------
  // rough cups for things counted, not measured
  const EACH_CUPS = [[/whole chickens?/, 6], [/parsnip|turnip|beet|rutabaga/, .75], [/sweet potato|butternut|squash|eggplant|cabbage|cauliflower|broccoli/, 2], [/potato/, 1], [/onion/, 1], [/bell pepper|\bpeppers?$/, 1], [/zucchini/, 1.5], [/tomato/, .75], [/carrot/, .5], [/celery/, .5], [/apple/, 1], [/jalape|chile|chili|shallot|lime|lemon|garlic|egg|chipotle|bay/, 0]];
  const isRiceName = (n) => /\brice\b/i.test(n) && !/cooked rice|leftover rice|day.old|rice vinegar|rice noodles?|rice wine|rice paper|rice flour|cauliflower rice/i.test(n);
  const NOODLE = /\b(pasta|noodles?|macaroni|spaghetti|penne|orzo|ziti|rigatoni|lasagna|linguine|fettuccine|shells|elbows|egg noodles)\b/i;
  function cupsOf(i, f) { // rough volume in the pot, in cups, after scaling
    if (i.qty == null) return 0;
    const q = mid(i) * f;
    const swell = (i.cls === 'grain' || NOODLE.test(i.name)) && !/cooked|leftover/i.test(i.name) ? 2 : 1; // dry pasta and grains about double
    if (i.size && i.unit) return q * i.size.oz / 8 * swell;
    if (i.unit === 'can') return q * 1.875;
    if (i.unit && PACK.includes(i.unit)) return q * 2 * swell;
    if (i.unit && VOL_TSP[i.unit]) return q * VOL_TSP[i.unit] / 48 * swell;
    if (i.unit && WT_OZ[i.unit]) return q * WT_OZ[i.unit] / (swell > 1 ? 2 : 8) * (swell > 1 ? 1 : 1); // 8 oz is about a cup; 8 oz dry pasta cooks to about 4 cups
    const n = (i.name || '').toLowerCase();
    if (i.unit === 'stalk') return q * .5;
    if (['bunch', 'handful'].includes(i.unit)) return q * (i.unit === 'bunch' ? 1 : .5);
    if (!i.unit || i.unit === 'head') { const e = EACH_CUPS.find(([re]) => re.test(n)); return q * (e ? e[1] : (['veg', 'aromatic'].includes(i.cls) ? .75 : 0)); }
    return 0;
  }

  const POTS = [3, 4, 6, 8, 12, 16, 20]; // quarts
  function potFor(cups, fill) { const q = cups / 4 / fill; return POTS.find((p) => p >= q) || null; }
  const BIG = POTS[POTS.length - 1];
  const RICE_FILL = 1 / 4; // dry rice at most a quarter of the pot, so cooked rice (it triples) stays under ¾
  const S = (n, w, pl) => `${fmtNum(n)} ${n === 1 ? w : pl || w + 's'}`;
  // the longest time the recipe itself says (simmer 2 hours, slow cook 4 hours, roast 30 minutes)
  function ownMinutes(text) {
    let best = 0, m;
    const re = /(\d+(?:\.\d+)?)\s*([½¼¾])?(?:\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*([½¼¾])?)?\s*(hours?|hrs?|minutes?|mins?)\b/gi;
    while ((m = re.exec(text))) {
      const v = (m[3] ? +m[3] + (FRAC[m[4]] || 0) : +m[1] + (FRAC[m[2]] || 0));
      best = Math.max(best, /^h/i.test(m[5]) ? v * 60 : v);
    }
    return Math.min(best, 24 * 60);
  }
  function fmtDur(min) { if (min < 60) return `${Math.round(min)} minutes`; const h = Math.round(min / 30) / 2; return `${fmtNum(h)} hour${h === 1 ? '' : 's'}`; }

  function batchDay(recipe, meals, opts) {
    opts = opts || {};
    const f = meals / recipe.yield;
    const baking = recipe.baking;
    const items = recipe.ingredients.map((i) => scaleIngredient(i, f, baking));
    const plan = { factor: f, meals, baking, items, pots: [], order: [], split: { freezer: [], fridge: [], fresh: [] }, grocery: [], notes: [], rice: null };

    if (baking) {
      const batches = Math.ceil(f / 2);
      plan.notes.push(f > 2
        ? `Baking doesn't scale well past 2x. Make ${batches} batches of ${(() => { const e = f / batches, n = fmtNum(e), back = numVal(n.replace(/^(\d)([¼½¾⅓⅔⅛])/, '$1 $2').replace(/ (.)$/, (m, c) => ' ' + c)); return Math.abs((isNaN(back) ? e : back) - e) > 0.02 ? String(Math.round(e * 100) / 100) : n; })()}x instead of one giant one.`
        : 'Baking: measure carefully. Same oven temperature; check doneness a few minutes early.' + (Math.abs(f - Math.round(f)) > 0.1 && Math.abs(f - 0.5) > 0.05 ? ' Pick a pan that keeps the batter about as deep as the recipe\'s, or the time changes.' : ''));
    }

    // a bake with meat, fish, beans, cheese or cream in it is stored like a meal: fridge within 2 hours, eat within 4 days
    const savoryBake = baking && !!recipe.savoryBake;
    plan.savoryBake = savoryBake;
    const by = (c) => items.filter((i) => i.cls === c);
    const protein = by('protein'), liquid = by('liquid'), grain = by('grain'), veg = by('veg'), fin = by('finisher');
    const meat = items.filter((i) => ['protein', 'other'].includes(i.cls) && isMeat(i.name));
    const stepsTxt = recipe.steps.map((s) => s.text.toLowerCase()).join(' ');
    const sheet = /sheet pan|baking sheet|sheet-pan|cookie sheet|roasting pan|rimmed pan/.test(stepsTxt);
    const dish = /baking dish|casserole|9\s*[x×]\s*13|13\s*[x×]\s*9|8\s*[x×]\s*8|pie dish|gratin dish/.test(stepsTxt);
    const liquidCups = liquid.reduce((s, i) => s + cupsOf(i, f), 0);

    // rice: its own pot, unless it cooks in the soup (congee) or in the oven (casserole)
    let riceDry = 0;
    grain.forEach((g) => {
      if (!isRiceName(g.name) && !(g.qty == null && /quinoa|orzo|couscous/i.test(g.name))) return;
      if (g.qty == null) {
        const dry = meals / 3;
        g.scaled = `${fmtNum(niceFrac(dry, .5))} cups dry (about ⅓ cup per meal, an estimate)`;
        g.estimated = true;
        riceDry += dry;
      } else riceDry += cupsOf(g, f) / 2;
    });
    const riceInPot = riceDry > 0 && ((liquidCups >= riceDry * 4 && /simmer|congee|porridge|soup|stew|jook/.test(stepsTxt + ' ' + (recipe.title || '').toLowerCase())) ||
      (dish && /oven|bake/.test(stepsTxt) && !/cooked rice|serve (it )?over|rice cooker|cook the rice/.test(stepsTxt)));
    if (riceDry && !riceInPot) plan.rice = riceDry;

    // pots: everything that goes in the pot, cans, whole vegetables and pasta included
    const potItems = items.filter((i) => !['finisher', 'salt', 'spice', 'oil', 'baking'].includes(i.cls) && !/bok choy|spinach|kale|greens/i.test(i.name) && !(plan.rice && isRiceName(i.name)) && !(i.cls === 'grain' && /cooked/i.test(i.name) === false && sheet));
    const potCups = potItems.reduce((s, i) => s + cupsOf(i, f) * (isMeat(i.name) && i.unit && WT_OZ[i.unit] ? 0.9 : 1), 0) + (riceInPot ? riceDry : 0); // in congee or a casserole the liquid is soaked up, so only the dry rice adds
    let bigJob = false;
    // no heat anywhere in the steps and no raw meat: overnight oats, salads, dressings
    const nocook = !baking && recipe.steps.length > 0 && !meat.length && !/\b(cook|simmer|boil|bak|roast|sear|fr(y|ied)|saut|heat|oven|stove|grill|microwave|broil|toast|brown|melt|pressure|instant pot|slow)/.test(stepsTxt);
    plan.nocook = nocook;
    // pasta that boils on its own (not cooked in the soup)
    const pasta = items.filter((i) => NOODLE.test(i.name) && i.qty != null && !/cooked|leftover/i.test(i.name));
    const pastaCups = pasta.reduce((s, i) => s + cupsOf(i, f), 0);
    const boilPasta = !nocook && pasta.length && !(liquidCups >= pastaCups * 2 && /soup|stew|simmer|broth/.test(stepsTxt + ' ' + (recipe.title || '').toLowerCase()));
    if (nocook) { /* no pots */ }
    else if (!baking && sheet && !liquid.length) {
      const pans = Math.max(1, Math.ceil(potCups / 6));
      plan.pans = pans;
      plan.pots.push(`Sheet pans: ${pans} (one layer, about 6 cups of food each). Crowded pans steam instead of roast.`);
      if (pans > 2) plan.pots.push(`An oven fits about 2 sheet pans at once, so that's ${Math.ceil(pans / 2)} rounds in the oven.`);
    } else if (!baking && potCups >= 1) {
      const q = potFor(potCups, 0.75);
      if (q) plan.pots.push(`Main pot: ${q} qt or bigger (about ${S(Math.max(1, Math.round(potCups)), 'cup')} of food, kept under ¾ full)`);
      else {
        const n = Math.ceil(potCups / (BIG * 4 * 0.75));
        bigJob = true;
        plan.pots.push(`Main pot: about ${Math.round(potCups)} cups of food, more than one pot holds. Use ${n} big pots (${BIG} qt), or cook it in ${n} rounds.`);
      }
      if (dish) { const d = Math.max(1, Math.ceil(potCups / 12)); plan.dishes = d; plan.pots.push(`Baking dishes: ${d} (9×13, about 12 cups each)`); if (d > 4) plan.pots.push(`An oven fits about 4 baking dishes at once, so that's ${Math.ceil(d / 4)} rounds in the oven.`); }
    }
    if (plan.rice) {
      const q = potFor(plan.rice, RICE_FILL);
      if (q) plan.pots.push(`Rice pot: ${q} qt (dry rice no more than ¼ full; it triples)`);
      else {
        const per = BIG * 4 * RICE_FILL, n = Math.ceil(plan.rice / per);
        bigJob = true;
        plan.pots.push(`Rice: about ${Math.round(plan.rice)} cups dry, more than one pot holds. Cook it in ${n} pots or rounds of up to ${per} cups.`);
      }
    }
    const lbs = meat.reduce((s, i) => s + (i.qty != null && i.unit && WT_OZ[i.unit] ? mid(i) * f * WT_OZ[i.unit] / 16 : 0), 0);
    const sears = lbs > 0 && /sear|brown|pan-?fry|golden/.test(stepsTxt);
    const searBatches = sears ? Math.max(1, Math.ceil(lbs / 1.5)) : 0;
    if (sears) {
      const each = searBatches === 1 ? lbs : 1.5;
      const eachTxt = each >= 1 ? `${fmtNum(Math.round(each * 4) / 4)} lb` : `${Math.max(1, Math.round(each * 16))} oz`;
      plan.pots.push(`Searing: ${searBatches} batch${searBatches > 1 ? 'es' : ''} in a 12-inch pan (about ${eachTxt}${searBatches > 1 ? ' each' : ''}).`);
      if (searBatches > 6) plan.pots.push(`That's a lot of batches for one pan. Run two pans at once, or brown it in the oven: one layer on sheet pans at 450°F until browned.`);
    }

    // order of operations
    const own = ownMinutes(stepsTxt);
    if (nocook) {
      plan.order.push({ t: 'Mix and portion', d: 'No cooking. Into the fridge right away.', min: 10 });
    } else if (!baking) {
      if (plan.rice) plan.order.push({ t: 'Start the rice first', d: 'It cooks while you do the rest.', min: 25 });
      if (meat.length) plan.order.push({ t: `Season the ${meat[0].name.replace(/boneless|skinless/gi, '').replace(/\s+/g, ' ').trim()}`, d: 'All of it at once, in a big bowl.', min: 5 });
      else if (sheet) plan.order.push({ t: 'Season everything', d: 'Toss it all in a big bowl with the oil and seasoning.', min: 5 });
      if (boilPasta) plan.order.push({ t: 'Boil the pasta', d: 'Big pot, salted water. If it bakes after, pull it a minute early.', min: 15 });
      if (sears) plan.order.push({ t: 'Sear in batches', d: 'Set each batch aside.', min: searBatches * 6 });
      let covered = 0;
      if (sheet && !liquid.length) {
        const m = (own || 30) * Math.ceil(plan.pans / 2); covered += m;
        plan.order.push({ t: 'Roast on sheet pans', d: `One layer${plan.pans > 1 ? `, ${plan.pans} pans` : ''}. With more than one pan, swap racks halfway and give it a little longer.`, min: m });
      } else {
        if (by('aromatic').length) plan.order.push({ t: 'Aromatics in the big pot', d: 'Same pot. Scrape up the browned bits.', min: 4 });
        if (/paste|bloom/.test(stepsTxt)) plan.order.push({ t: 'Bloom the paste', d: 'About a minute, until it smells great.', min: 2 });
        if (liquid.length) {
          const m = potCups < 24 ? 15 : potCups < 60 ? 25 : 40; covered += m;
          plan.order.push({ t: 'Liquids in, bring to a simmer', d: 'A big pot takes longer. Taste, but hold back on salt.', min: m });
        }
        if (meat.length && liquid.length) { covered += 15; plan.order.push({ t: 'Protein back in until cooked through', d: 'Judge by doneness, not the clock (165°F for chicken).', min: 15 }); }
        if (dish) { const m = (own || 30) * Math.ceil((plan.dishes || 1) / 4); covered = Math.max(covered, m); plan.order.push({ t: 'Into the oven', d: `${plan.dishes > 1 ? `${plan.dishes} baking dishes, swap racks halfway. ` : ''}Bake as the recipe says; check the middle is hot.`, min: m }); }
      }
      if (own - covered >= 10) plan.order.push({ t: 'Let it cook', d: `The recipe's own time is about ${fmtDur(own)}. Mostly hands off.`, min: own - covered });
      if (veg.some((v) => /bok choy|spinach|kale|greens/i.test(v.name))) plan.order.push({ t: 'Skip the tender greens for now', d: 'Add them when you reheat each portion so they stay bright.', min: 0 });
      plan.order.push({ t: 'Taste and adjust', d: 'Now add the rest of the salt and spice if it needs it.', min: 3 });
      plan.order.push({ t: 'Cool, then portion', d: 'Shallow containers, into the fridge within 2 hours.', min: 20 });
    } else {
      plan.order.push({ t: 'Mix and bake in batches', d: 'Follow the recipe steps for each batch.', min: 0 });
      if (savoryBake) plan.order.push({ t: 'Cool, then portion', d: 'Into the fridge within 2 hours.', min: 20 });
    }
    plan.totalMin = plan.order.reduce((s, o) => s + o.min, 0);
    const handsOn = plan.order.filter((o) => !/^(Let it cook|Roast on sheet pans|Into the oven|Start the rice)/.test(o.t)).reduce((s, o) => s + o.min, 0);
    if (!baking && (bigJob || searBatches > 10 || handsOn > 240)) plan.notes.push('This is a very big cook for one day. Think about splitting it into two sessions.');

    // what goes in at each step, with batch amounts
    if (!baking && !nocook) {
      const used = new Set();
      const sc = plan.items;
      const take = (fn) => sc.filter((i) => !used.has(i) && fn(i)).map((i) => { used.add(i); return { amt: i.scaled || '', name: i.label || i.name }; });
      const pSec = meat.length ? meat[0].section : null;
      const isTender = (i) => /bok choy|spinach|kale|greens/i.test(i.name);
      const hasSec = (re) => sc.some((i) => re.test(i.section || ''));
      // the title's section is no section at all
      const realSec = (x) => x && norm(x) !== norm(recipe.title || '');
      plan.order.forEach((o) => {
        let u = [];
        if (/^Start the rice/.test(o.t)) u = take((i) => i.cls === 'grain' && isRiceName(i.name));
        else if (/^Season the/.test(o.t)) u = take((i) => i.cls !== 'oil' && i.cls !== 'finisher' && (realSec(pSec) ? i.section === pSec && !['liquid', 'grain', 'veg'].includes(i.cls) : (isMeat(i.name) || i.cls === 'salt')));
        else if (/^Season everything/.test(o.t)) u = take((i) => i.cls !== 'finisher');
        else if (/^Sear/.test(o.t)) u = take((i) => i.cls === 'oil');
        else if (/^Aromatics/.test(o.t)) u = take((i) => i.cls !== 'finisher' && (hasSec(/aromatic/i) ? /aromatic/i.test(i.section || '') : i.cls === 'aromatic' || i.cls === 'spice' || (i.cls === 'oil' && !sears)));
        else if (/^Bloom/.test(o.t)) u = take((i) => /paste/i.test(i.name));
        else if (/^Liquids/.test(o.t)) { const ls = liquid.length ? liquid[0].section : null; u = take((i) => i.cls === 'liquid' || (realSec(ls) && i.section === ls && i.cls !== 'finisher' && !isTender(i)) || (!realSec(ls) && ['protein', 'veg', 'grain', 'other'].includes(i.cls) && !isMeat(i.name) && !isTender(i) && !(plan.rice && isRiceName(i.name)))); }
        else if (/^Boil the pasta/.test(o.t)) u = take((i) => NOODLE.test(i.name) && !/cooked|leftover/i.test(i.name));
        else if (/^Protein back/.test(o.t)) u = take((i) => isMeat(i.name));
        if (u.length) o.use = u;
      });
      // anything not placed yet goes in with the last cooking step, so every ingredient shows up somewhere
      const rest = take((i) => i.cls !== 'finisher' && !isTender(i));
      if (rest.length) {
        const k = plan.order.map((o) => /^(Skip the tender|Taste and adjust|Cool, then portion|Start the rice)/.test(o.t)).lastIndexOf(false);
        if (k >= 0) plan.order[k].use = (plan.order[k].use || []).concat(rest);
        else {
          const at = plan.order.findIndex((o) => /^(Skip the tender|Taste and adjust)/.test(o.t));
          plan.order.splice(at < 0 ? plan.order.length : at, 0, { t: 'Cook as the recipe says', d: 'In batches if the pan is crowded.', min: Math.max(15, own), use: rest });
          plan.totalMin = plan.order.reduce((s, o) => s + o.min, 0);
        }
      }
    }

    // split
    const fridgeMeals = Math.min(meals, opts.fridgeMeals || 4);
    if (!baking) {
      const fz = meals - fridgeMeals;
      const noodles = items.some((i) => NOODLE.test(i.name));
      if (nocook) {
        plan.split.fridge.push(`${S(meals, 'meal')}: eat within 4 days.` + (meals > 4 ? ` It doesn't freeze well, so make only what you'll eat by then.` : ''));
      } else plan.split.fridge.push(`${S(fridgeMeals, 'meal')} for this week: into the fridge within 2 hours, eat within 4 days`);
      if (fz > 0 && !nocook) {
        let line = `${S(fz, 'meal')}: ` + (liquid.length ? (meat.length ? 'protein and broth together' : 'in freezer containers, leave a little room at the top') : 'in freezer containers');
        if (plan.rice) line += ', rice in its own bag';
        line += '.';
        if (noodles && liquid.length) line += ' Pasta and noodles go soft in the freezer: if you can, cook them fresh when you reheat.';
        if (fz > 40) line += ' Check you have the freezer room first.';
        plan.split.freezer.push(line);
      }
      fin.concat(veg.filter((v) => /bok choy|spinach|kale|greens/i.test(v.name))).forEach((i) => plan.split.fresh.push(i.name));
    } else {
      if (recipe.fridgeBake) {
        plan.split.fridge.push('Keep it in the fridge (it has cream, cheese, custard or fruit filling). Into the fridge within 2 hours of cooling, eat within 4 days.');
        plan.split.freezer.push('Most bakes freeze well wrapped tight (frost after thawing)');
      } else if (!savoryBake) {
        plan.split.fridge.push('Keep covered at room temp up to 2 days. Anything with cream, cream cheese or custard goes in the fridge.');
        plan.split.freezer.push('Most bakes freeze well wrapped tight (frost after thawing)');
      } else {
        plan.split.fridge.push(`${S(fridgeMeals, 'meal')} for this week: into the fridge within 2 hours, eat within 4 days`);
        if (meals > fridgeMeals) plan.split.freezer.push(`${S(meals - fridgeMeals, 'meal')}: wrap tight and freeze.`);
      }
    }
    // the same split as numbers, for My freezer
    plan.portions = nocook ? { fridge: meals, freezer: 0 } : baking && !savoryBake ? null : { fridge: fridgeMeals, freezer: meals - fridgeMeals };

    // grocery: everything with an amount, finishers per bowl; the same item twice (ginger paste in the marinade and the sauce) becomes one line
    const kindOf = (i) => (i.qty == null ? null : i.unit && VOL_TSP[i.unit] && !['ml', 'l'].includes(i.unit) ? 'vol' : i.unit && WT_OZ[i.unit] && !['g', 'kg'].includes(i.unit) ? 'wt' : ['g', 'kg'].includes(i.unit) ? 'g' : ['ml', 'l'].includes(i.unit) ? 'ml' : 'u:' + (i.unit || '') + (i.size ? i.size.n + i.size.u : ''));
    const base = (i) => { const q = i.qtyScaled; const k = kindOf(i); return k === 'vol' ? q * VOL_TSP[i.unit] : k === 'wt' ? q * WT_OZ[i.unit] : i.unit === 'kg' || i.unit === 'l' ? q * 1000 : q; };
    const baseUnit = { vol: 'tsp', wt: 'oz', g: 'g', ml: 'ml' };
    const groups = new Map();
    items.forEach((i) => {
      const k = norm(i.name) + '|' + kindOf(i);
      if (i.qty != null && groups.has(k)) groups.get(k).push(i); else if (i.qty != null) groups.set(k, [i]); else groups.set(k + '|' + groups.size, [i]);
    });
    groups.forEach((g) => {
      const i = g[0];
      let amt = i.scaled, label = i.label || i.name;
      if (g.length > 1) {
        const k = kindOf(i), sum = g.reduce((s, x) => s + base(x), 0);
        const syn = Object.assign({}, i, { qty: sum, qtyHi: null, unit: baseUnit[k] || i.unit });
        const sc = scaleIngredient(syn, 1, true);
        amt = sc.scaled; label = sc.label || i.name;
      }
      if (i.cls === 'finisher' && i.qty == null) plan.grocery.push({ name: i.name, amt: 'for serving' });
      else if (i.qty != null || i.estimated) plan.grocery.push({ name: i.name, label, amt });
      else plan.grocery.push({ name: i.name, amt: i.toTaste ? 'to taste' : '' });
    });
    return plan;
  }

  function scaleAll(recipe, target) {
    const f = target / recipe.yield;
    return { factor: f, items: recipe.ingredients.map((i) => scaleIngredient(i, f, recipe.baking)) };
  }


  /* ---------- the shop: store sections and staples (pure, no storage) ---------- */
  // US grocery sections in walking order
  const AISLES = ['Produce', 'Meat & seafood', 'Dairy & eggs', 'Bakery', 'Canned & jarred', 'Dry goods & grains', 'Spices & oils', 'Frozen', 'Other'];
  const HERB = 'basil|parsley|cilantro|rosemary|thyme|dill|mint|sage|chives|oregano|tarragon|marjoram';
  // first match wins, so the order matters: "garlic powder" is a spice before "garlic" is produce, "chicken broth" is a can before "chicken" is meat
  const AISLE_RULES = [
    [7, /\bfrozen\b|ice cream|\bpopsicles?\b|tater tots|\bwaffles\b/],
    [0, new RegExp('\\bfresh\\s+(' + HERB + '|herbs?|ginger|garlic|turmeric)\\b|cauliflower rice|butternut|butter lettuce|\\bcloves?( of)? garlic|garlic cloves?|\\b(lemon|lime)s?\\b|spaghetti squash|\\bgreen beans?\\b|\\bbean sprouts?\\b|sweet potato|\\bcorn on the cob\\b|\\bbell peppers?\\b|\\b(red|green|yellow|orange) peppers?$')],
    [5, /baking (powder|soda)|(powdered|brown|white|granulated|cane|coconut) sugar|\bcocoa\b|corn ?starch|bread ?crumbs|\bpanko\b|bread flour|egg noodles|rice noodles|cream of wheat|peanut butter (chips|cups)|\b(tortilla|pita|bagel|corn) chips\b/],
    [6, /cream of tartar|\b(garlic|onion|chili|chile|chilli|curry|mustard|ginger|five[- ]spice) powder\b|\bbouillon powder\b/],
    [4, /\b(broth|stock|bouillon|sauce|paste|salsa|canned|cans?|jarred|jars?|soup|puree|purée)\b|coconut (milk|cream|aminos)|(condensed|evaporated) milk|\b(diced|crushed|stewed|whole peeled|fire[- ]roasted|sun[- ]dried) tomatoes\b|\b(peanut|almond|cashew|nut|apple) butter\b|\b(apple|orange|pineapple|tomato|cranberry|grape) juice\b/],
    [6, new RegExp('\\boils?\\b|vinegar|\\bsalt\\b|\\b(black|white|cayenne|ground|cracked|lemon|red) pepper\\b|peppercorns?|\\bpepper$|(chili|chile|chilli|pepper) flakes|seasoning|\\bspice|\\b(dried|ground)\\s+(' + HERB + '|ginger|mustard|coriander|cloves|garlic|onion|chiles?|chilies)\\b|\\b(cumin|paprika|cinnamon|nutmeg|turmeric|cardamom|allspice|saffron|oregano|cayenne|garam masala|bay lea(f|ves)|vanilla|extract|msg|za.?atar|sumac|fennel seeds?|mustard seeds?|caraway|curry leaves|taco mix|cooking spray|shortening|lard|ghee)\\b|\\b(whole|ground) cloves\\b')],
    [4, /\b(black|kidney|pinto|cannellini|garbanzo|white|navy|refried|baked|butter|lima) beans\b|chickpeas|\b(jam|jelly|honey|syrup|molasses|ketchup|mustard|mayo|mayonnaise|pickles?|relish|olives|capers|tuna|sardines|anchovies|tahini|sriracha|worcestershire|pesto|marinara|hummus|dressing|applesauce|mirin|rice wine|cooking wine|sauerkraut|kimchi|artichoke hearts|chipotles?|adobo|pimentos?|gochujang|miso|harissa|sambal)\b/],
    [3, /\b(bread|buns?|rolls|tortillas?|pitas?|naan|bagels?|baguette|croissants?|english muffins?|flatbreads?|pizza dough|pie crust|ciabatta|sourdough|brioche|wraps)\b/],
    [5, /\b(rice|pasta|spaghetti|penne|macaroni|linguine|fettuccine|rigatoni|lasagna|orzo|noodles|ramen|couscous|quinoa|oats|oatmeal|flour|sugar|cornmeal|polenta|grits|yeast|lentils|split peas|barley|farro|bulgur|cereal|granola|crackers|chips|almonds|walnuts|pecans|cashews|peanuts|pistachios|pine nuts|nuts|sesame seeds|chia seeds|flaxseed|sunflower seeds|pumpkin seeds|raisins|dried (cranberries|apricots|fruit|beans)|chocolate|marshmallows|gelatin|sprinkles|pretzels|popcorn|beans|tapioca)\b/],
    [1, /\b(chicken|beef|pork|turkey|lamb|veal|duck|bacon|sausages?|ham|steaks?|brisket|ribs|chuck|sirloin|tenderloin|thighs|breasts?|drumsticks|wings|meatballs|chorizo|pepperoni|salami|prosciutto|pancetta|hot dogs|ground meat|mince|salmon|shrimp|prawns|fish|cod|tilapia|halibut|trout|crab|lobster|scallops|clams|mussels|oysters|squid|calamari|kielbasa|bratwurst|roast)\b/],
    [2, /\b(milk|cream|butter|buttermilk|cheese|cheddar|mozzarella|parmesan|parmigiano|feta|ricotta|gouda|swiss|provolone|monterey jack|pepper jack|queso|paneer|halloumi|mascarpone|yogurt|yoghurt|kefir|eggs?|egg whites|egg yolks|half[- ](and|&)[- ]half|creamer|margarine|whipped topping)\b/],
    [0, new RegExp('\\b(onions?|scallions?|shallots?|leeks?|garlic|ginger|potato(es)?|carrots?|celery|tomato(es)?|peppers?|jalape[nñ]os?|serranos?|poblanos?|habaneros?|chil(i|e|ie|li)s?|cucumbers?|zucchini|squash|pumpkin|eggplant|broccoli|broccolini|cauliflower|cabbage|bok choy|kale|spinach|lettuce|romaine|arugula|greens|chard|mushrooms?|corn|peas|snap peas|snow peas|asparagus|beets?|radish(es)?|turnips?|parsnips?|fennel|okra|sprouts|avocados?|apples?|bananas?|oranges?|grapes|berries|strawberries|blueberries|raspberries|blackberries|cranberries|mango(es)?|pineapple|peach(es)?|pears?|plums?|cherries|melon|watermelon|cantaloupe|grapefruit|kiwi|pomegranate|dates|figs|coconut|lemongrass|tofu|tempeh|edamame|herbs?|' + HERB + '|microgreens|plantains?|yams?|jicama|tomatillos?|rhubarb|artichokes?|endive|radicchio|watercress|fresh)\\b')]
  ];
  // which section an item is in: an index into AISLES
  function aisleOf(name) {
    const n = String(name == null ? '' : name).toLowerCase().replace(/[’']/g, '').replace(/\([^)]*\)/g, ' ').replace(/\s+/g, ' ').trim();
    if (!n) return 8;
    for (let k = 0; k < AISLE_RULES.length; k++) if (AISLE_RULES[k][1].test(n)) return AISLE_RULES[k][0];
    return 8;
  }
  // grocery items grouped by section, in store order; items keep their order inside a section; empty sections are left out
  function aisles(items) {
    const g = AISLES.map((name) => ({ name, items: [] }));
    (items || []).forEach((i) => g[aisleOf(i.name)].items.push(i));
    return g.filter((x) => x.items.length);
  }
  // one spelling for a staple: "Olive Oil", "olive oil " and "olive oils" are the same thing
  function stapleKey(name) {
    return String(name == null ? '' : name).toLowerCase().replace(/[’']/g, '').replace(/[^a-z0-9À-￿]+/g, ' ').trim()
      .split(' ').map((w) => (w.length > 3 ? w.replace(/ies$/, 'y').replace(/oes$/, 'o').replace(/([^s])s$/, '$1') : w)).join(' ').slice(0, 60);
  }
  // the shop as the cook sees it: sections of what to buy, then the staples to check at home. staples = a Set or array of stapleKey names
  function shopList(grocery, staples) {
    const st = staples instanceof Set ? staples : new Set(staples || []);
    const buy = [], pan = [];
    (grocery || []).forEach((g) => (st.has(stapleKey(g.name)) ? pan : buy).push(g));
    const flat = (a) => aisles(a).reduce((o, s) => o.concat(s.items), []);
    return { groups: aisles(buy), buy: flat(buy), pantry: flat(pan) };
  }

  const api = { parseRecipe, parseIngredient, stitch, scaleAll, batchDay, fmtNum, AISLES, aisleOf, aisles, stapleKey, shopList };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.BatchEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
