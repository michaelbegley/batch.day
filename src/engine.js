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
  ];
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
    for (const [u, re] of UNITS) {
      const ci = new RegExp(re.source.replace('|T)', ')').replace('|t)', ')'), 'i');
      const um = rest.match(ci) || rest.match(re);
      if (um) { unit = u; rest = rest.slice(um[0].length).trim(); break; }
    }
    // "(8 oz) package" style: ignore; keep name
    let name = rest.replace(/^of\s+/i, '').trim();
    let note = '';
    const cm = name.match(/^(.*?)(,\s*|\s+\()(.*)$/);
    if (cm && cm[1].length > 2) { note = (cm[3] || '').replace(/\)$/, ''); name = cm[1]; }
    const toTaste = /to taste/i.test(line);
    const optional = /optional/i.test(line);
    if (qty === 0 && !qtyHi) qty = null;
    let odd = sci || neg;
    if (qty != null && unit && WT_OZ[unit] && qty * WT_OZ[unit] > 50 * 16) odd = true;
    if (qty != null && !unit && qty > 500) odd = true;
    if (qty != null && unit && VOL_TSP[unit] && qty * VOL_TSP[unit] > 48 * 40) odd = true;
    return { raw: line, qty, qtyHi, unit, name: name.trim(), note: note.trim(), toTaste, optional, flag, odd };
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
    if (/\b(broth|stock|coconut milk)\b/.test(s)) return 'liquid';
    if (/\b(cheese|sour cream|yogurt|eggs?)\b/.test(s)) return 'dairy';
    if (/garlic powder|onion powder/.test(s)) return 'spice';
    if (/ginger paste|garlic paste/.test(s)) return 'aromatic';
    if (/curry paste|tomato paste|chili paste|miso paste/.test(s)) return 'spice';
    if (/oil/.test(s) && /chili oil|chili crisp/.test(s)) return 'finisher';
    for (const [c, re] of CLASSES) if (re.test(s)) return c;
    return 'other';
  }

  function isBaking(ings, text) {
    const s = ings.map((i) => i.name).join(' ').toLowerCase() + ' ' + (text || '').toLowerCase();
    return /baking (powder|soda)|yeast/.test(s) || (/flour/.test(s) && /sugar/.test(s) && /egg/.test(s)) || /preheat oven.*(cake|muffin|cookie|bread)|\b(cake|muffins?|cookies?|brownies?|cupcakes?)\b/.test(s);
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
      const ym = line.match(/\b(serves|servings?|makes|yield[s]?)\s*:?\s*(\d+)(?:\s*(?:-|to)\s*(\d+))?/i);
      if (ym) { r.yield = ym[3] ? (+ym[2] + +ym[3]) / 2 : +ym[2]; r.yieldText = line; continue; }
      if (/^(instructions|directions|method|steps|preparation)\s*:?$/i.test(line)) { mode = 'step'; pushStep(); continue; }
      if (/^(ingredients)\s*:?$/i.test(line)) { mode = 'ing'; continue; }
      const sn = stepNumber(raw.trim());
      if (sn) { mode = 'step'; pushStep(); stepBuf = { n: sn.n, text: sn.rest.replace(/(?:\s+#[\w-]+)+\s*$/u, '') }; continue; }
      if (mode === 'step') {
        if (stepBuf) stepBuf.text += ' ' + line; else stepBuf = { n: r.steps.length + 1, text: line };
        if (/[.!]$/.test(line) && !/^\d/.test(line)) { /* keep merging until next number */ }
        continue;
      }
      // header? ends with a colon, or a known section word, or a short unbulleted line that isn't a food
      const bulleted = /^\s*(?:\[[^\]]{0,3}\]|\|[ _|\]]*\|?|[☐☑✓✔•●◦▪\-–*·°©®¢«»]|[eE]\s)/u.test(raw);
      const VOCAB = /^(chicken|beef|pork|meat|protein|aromatics|broth|soup|sauce|marinade|dressing|rice|noodles|grains?|veggies|vegetables|toppings?|garnish(es)?|to serve|for serving|optional.*|cake|frosting|icing|filling|crust|dough|batter|glaze|base|seasoning|spice mix|salad|cream cheese topping|chocolate cornflakes|for the .*)$/i;
      const isHeader = !QTY_RE.test(line) && !/\d/.test(line) && line.length < 40 && (
        (/:$/.test(line)) || VOCAB.test(line.replace(/:$/, '')) ||
        (!bulleted && line.split(' ').length <= 3 && /^[A-Z]/.test(line) && classify({ name: line, note: '' }, '') === 'other'));
      if (isHeader) {
        if (!r.title && /recipe/i.test(line)) { r.title = line.replace(/\s*recipe.*$/i, '').trim(); continue; }
        section = line.replace(/:$/, '');
        if (!r.sections.includes(section)) r.sections.push(section);
        continue;
      }
      if (/recipe/i.test(line) && !QTY_RE.test(line) && !r.title) { r.title = line.replace(/\s*recipe.*$/i, '').replace(/[^\w\s'&-]/g, '').trim(); continue; }
      const prev = r.ingredients[r.ingredients.length - 1];
      if (prev && !QTY_RE.test(line) && (/^[a-z(]/.test(line) || /^[A-Za-z ]{1,20}\)$/.test(line))) { prev.note = (prev.note + ' ' + line).trim(); continue; }
      const ing = parseIngredient(line);
      // drop lines that are clearly not ingredients
      if (!ing.qty && !ing.toTaste && !/^(salt|pepper|neutral|green onion|baby|fresh|optional|red chili|parish|cilantro|chili|black pepper)/i.test(ing.name) && line.split(' ').length > 7) { r.notes.push(line); continue; }
      if (!section && !r.ingredients.length && ing.qty == null && !ing.toTaste) { r.notes.push(line); continue; }
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
    r.baking = isBaking(r.ingredients, text);
    if (!r.yield) {
      const prot = r.ingredients.filter((i) => i.cls === 'protein' && i.qty && (i.unit === 'lb' || i.unit === 'oz' || i.unit === 'g' || i.unit === 'kg'));
      if (prot.length) {
        const oz = prot.reduce((s, i) => s + mid(i) * WT_OZ[i.unit], 0);
        r.yield = Math.max(1, Math.round(oz / 6));
        r.yieldGuessed = true;
        r.flags.push({ type: 'yield', line: '', msg: `No servings listed. Guessing ${r.yield} from the protein; change it if you know.` });
      } else { r.yield = 4; r.yieldGuessed = true; r.flags.push({ type: 'yield', line: '', msg: 'No servings listed. Guessing 4; change it if you know.' }); }
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
  function factorFor(cls, f, baking) {
    if (f <= 2 || baking) return f;
    if (cls === 'salt') return f * 0.7;
    if (cls === 'spice') return f * 0.75;
    if (cls === 'oil') return f * 0.6;
    return f;
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
  function fmtVol(tsp) {
    if (tsp < 3 * 0.95) return [niceFrac(tsp, .25), 'tsp'];
    if (tsp < 12 * 0.95) return [niceFrac(tsp / 3, .5), 'tbsp'];
    return [niceFrac(tsp / 48, .25), 'cup'];
  }
  function fmtWt(oz) {
    if (oz >= 16) return [Math.round(oz / 16 * 4) / 4, 'lb'];
    return [Math.round(oz * 2) / 2, 'oz'];
  }
  function show(n, u) {
    const plural = { cup: 'cups', clove: 'cloves', can: 'cans', slice: 'slices', stalk: 'stalks', bunch: 'bunches', package: 'packages', pinch: 'pinches' };
    const label = n > 1 && plural[u] ? plural[u] : u;
    return u ? `${fmtNum(n)} ${label}` : fmtNum(n);
  }

  function scaleIngredient(ing, f, baking) {
    const out = Object.assign({}, ing);
    if (ing.qty == null) { out.scaled = ing.toTaste ? 'to taste' : (['finisher', 'salt', 'oil'].includes(ing.cls) || Math.abs(f - 1) < .05 ? '' : `${Math.round(f * 10) / 10}× usual`); return out; }
    const q = mid(ing) * factorFor(ing.cls, f, baking);
    out.adjusted = f > 2 && !baking && ['salt', 'spice', 'oil'].includes(ing.cls);
    let n = q, u = ing.unit;
    if (u && VOL_TSP[u] && !['ml', 'l'].includes(u)) [n, u] = fmtVol(q * VOL_TSP[u]);
    else if (u && WT_OZ[u] && !['g', 'kg'].includes(u)) [n, u] = fmtWt(q * WT_OZ[u]);
    else if (!u || ['clove', 'can', 'slice', 'stalk', 'bunch', 'package'].includes(u)) n = /egg/i.test(ing.name) || u ? Math.max(1, Math.round(q)) : niceFrac(q, .5);
    else n = Math.round(q * 10) / 10;
    if (u === 'pinch') { n = Math.max(1, Math.round(q)); }
    out.qtyScaled = q;
    out.scaled = show(n, u);
    return out;
  }

  // ---------- Batch Day plan ----------
  function cupsOf(i, f) { // rough volume in cups after scaling
    if (i.qty == null) return 0;
    const q = mid(i) * f;
    if (i.unit && VOL_TSP[i.unit]) return q * VOL_TSP[i.unit] / 48;
    if (i.unit && WT_OZ[i.unit]) return q * WT_OZ[i.unit] / 8; // ~1 cup per 8 oz
    return 0;
  }

  const POTS = [3, 4, 6, 8, 12, 16, 20]; // quarts
  function potFor(cups, fill) { const q = cups / 4 / fill; return POTS.find((p) => p >= q) || null; }

  function batchDay(recipe, meals, opts) {
    opts = opts || {};
    const f = meals / recipe.yield;
    const baking = recipe.baking;
    const items = recipe.ingredients.map((i) => scaleIngredient(i, f, baking));
    const plan = { factor: f, meals, baking, items, pots: [], order: [], split: { freezer: [], fridge: [], fresh: [] }, grocery: [], notes: [], rice: null };

    if (baking) {
      const batches = Math.ceil(f / 2);
      plan.notes.push(f > 2
        ? `Baking doesn't scale well past 2x. Make ${batches} batches of ${fmtNum(f / batches)}x instead of one giant one.`
        : 'Baking: measure carefully. Same oven temperature; check doneness a few minutes early.');
    }

    const by = (c) => items.filter((i) => i.cls === c);
    const protein = by('protein'), liquid = by('liquid'), grain = by('grain'), veg = by('veg'), fin = by('finisher');

    // rice/grain with no amount: 1/3 cup dry per meal (rough estimate)
    grain.forEach((g) => {
      if (g.qty == null && /rice|quinoa|orzo|couscous/i.test(g.name)) {
        const dry = meals / 3;
        g.scaled = `${fmtNum(niceFrac(dry, .5))} cups dry (about ⅓ cup per meal — estimate)`;
        g.estimated = true;
        plan.rice = dry;
      } else if (g.qty != null && /rice/i.test(g.name)) plan.rice = cupsOf(g, f);
    });

    // pots
    const soupCups = liquid.reduce((s, i) => s + cupsOf(i, f), 0) + protein.reduce((s, i) => s + cupsOf(i, f), 0) * 0.9 + veg.reduce((s, i) => s + cupsOf(i, f), 0);
    if (!baking && soupCups > 0) {
      const q = potFor(soupCups, 0.75);
      plan.pots.push(q ? `Main pot: ${q} qt or bigger (about ${Math.round(soupCups)} cups of food, kept under ¾ full)` : `Main pot: about ${Math.round(soupCups)} cups of food — split across two big pots`);
    }
    if (plan.rice) {
      const q = potFor(plan.rice, 1 / 3);
      plan.pots.push(q ? `Rice pot: ${q} qt (dry rice under ⅓ full — it triples)` : 'Rice: cook in two pots or batches');
    }
    const lbs = protein.reduce((s, i) => s + (i.qty != null && i.unit && WT_OZ[i.unit] ? mid(i) * f * WT_OZ[i.unit] / 16 : 0), 0);
    if (lbs > 0 && /sear|brown|pan-?fry|golden/i.test(recipe.steps.map((s) => s.text).join(' '))) {
      const batches = Math.max(1, Math.ceil(lbs / 1.5));
      plan.pots.push(`Searing: ${batches} batch${batches > 1 ? 'es' : ''} in a 12-inch pan (about 1½ lb each). Don't crowd it, or it steams.`);
    }

    // order of operations
    const stepsTxt = recipe.steps.map((s) => s.text.toLowerCase()).join(' ');
    if (!baking) {
      if (plan.rice) plan.order.push({ t: 'Start the rice first', d: 'It runs on its own while you do everything else.', min: 25 });
      if (protein.length) plan.order.push({ t: `Season the ${protein[0].name.replace(/boneless|skinless/gi, '').trim()}`, d: 'Season all of it at once in a big bowl.', min: 5 });
      if (/sear|brown|pan-?fry|golden/.test(stepsTxt)) plan.order.push({ t: 'Sear in batches', d: 'Set each batch aside; it finishes cooking later.', min: Math.max(1, Math.ceil(lbs / 1.5)) * 6 });
      if (by('aromatic').length) plan.order.push({ t: 'Aromatics in the big pot', d: 'Same pot, scrape up the browned bits.', min: 4 });
      if (/paste|bloom/.test(stepsTxt)) plan.order.push({ t: 'Bloom the paste', d: 'About a minute, until it smells great.', min: 2 });
      if (liquid.length) plan.order.push({ t: 'Liquids in, bring to a simmer', d: 'A big pot takes a lot longer to simmer. Taste now, but hold back on salt.', min: 15 });
      if (protein.length && liquid.length) plan.order.push({ t: 'Protein back in until cooked through', d: 'Judge by doneness, not the clock (165°F for chicken).', min: 15 });
      if (veg.some((v) => /bok choy|spinach|kale|greens/i.test(v.name))) plan.order.push({ t: 'Skip the tender greens for now', d: 'Add them when you reheat each portion so they stay bright.', min: 0 });
      plan.order.push({ t: 'Taste and adjust', d: 'Now add the rest of the salt and spice if it needs it.', min: 3 });
      plan.order.push({ t: 'Cool, then portion', d: 'Shallow containers, into the fridge within 2 hours.', min: 20 });
    } else {
      plan.order.push({ t: 'Mix and bake in batches', d: 'Follow the recipe steps for each batch.', min: 0 });
    }
    plan.totalMin = plan.order.reduce((s, o) => s + o.min, 0);

    // what goes in at each step, with batch amounts
    if (!baking) {
      const used = new Set();
      const sc = plan.items;
      const take = (fn) => sc.filter((i) => !used.has(i) && fn(i)).map((i) => { used.add(i); return { amt: i.scaled || '', name: i.name }; });
      const pSec = protein.length ? protein[0].section : null;
      const isTender = (i) => /bok choy|spinach|kale|greens/i.test(i.name);
      const hasSec = (re) => sc.some((i) => re.test(i.section || ''));
      plan.order.forEach((o) => {
        let u = [];
        if (/^Start the rice/.test(o.t)) u = take((i) => i.cls === 'grain');
        else if (/^Season the/.test(o.t)) u = take((i) => i.cls !== 'oil' && i.cls !== 'finisher' && (pSec ? i.section === pSec : (i.cls === 'protein' || i.cls === 'salt')));
        else if (/^Sear/.test(o.t)) u = take((i) => i.cls === 'oil');
        else if (/^Aromatics/.test(o.t)) u = take((i) => i.cls !== 'finisher' && (hasSec(/aromatic/i) ? /aromatic/i.test(i.section || '') : i.cls === 'aromatic' || i.cls === 'spice'));
        else if (/^Bloom/.test(o.t)) u = take((i) => /paste/i.test(i.name));
        else if (/^Liquids/.test(o.t)) { const ls = liquid.length ? liquid[0].section : null; u = take((i) => i.cls === 'liquid' || (ls && i.section === ls && i.cls !== 'finisher' && !isTender(i))); }
        if (u.length) o.use = u;
      });
    }

    // split
    const fridgeMeals = Math.min(meals, opts.fridgeMeals || 4);
    if (!baking) {
      plan.split.fridge.push(`${fridgeMeals} meals for this week (eat within 4 days)`);
      if (meals > fridgeMeals) plan.split.freezer.push(`${meals - fridgeMeals} meals: protein and broth together, rice in its own bag`);
      fin.concat(veg.filter((v) => /bok choy|spinach|kale|greens/i.test(v.name))).forEach((i) => plan.split.fresh.push(i.name));
    } else {
      plan.split.fridge.push('Keep covered at room temp 2 days or fridge 5 days');
      plan.split.freezer.push('Most bakes freeze well wrapped tight (frost after thawing)');
    }

    // grocery: everything with an amount, finishers per bowl
    items.forEach((i) => {
      if (i.cls === 'finisher' && i.qty == null) plan.grocery.push({ name: i.name, amt: 'for serving' });
      else if (i.qty != null || i.estimated) plan.grocery.push({ name: i.name, amt: i.scaled });
      else if (!i.toTaste) plan.grocery.push({ name: i.name, amt: '' });
    });
    return plan;
  }

  function scaleAll(recipe, target) {
    const f = target / recipe.yield;
    return { factor: f, items: recipe.ingredients.map((i) => scaleIngredient(i, f, recipe.baking)) };
  }

  const api = { parseRecipe, parseIngredient, stitch, scaleAll, batchDay, fmtNum };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.BatchEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
