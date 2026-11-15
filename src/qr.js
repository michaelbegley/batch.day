/* QR codes for the freezer labels. Byte mode, versions 1 to 6 (21 to 41 modules), error correction M, Q or H.
   Written for this page; no dependencies, nothing loaded. make(text) returns null when the text is too long for version 6. */
(function (root) {
  'use strict';

  // per version 1..6: [error-correction codewords per block, blocks, data codewords per block (, more blocks, their data codewords)]
  const EC = {
    M: [[10, 1, 16], [16, 1, 28], [26, 1, 44], [18, 2, 32], [24, 2, 43], [16, 4, 27]],
    Q: [[13, 1, 13], [22, 1, 22], [18, 2, 17], [26, 2, 24], [18, 2, 15, 2, 16], [24, 4, 19]],
    H: [[17, 1, 9], [28, 1, 16], [22, 2, 13], [16, 4, 9], [22, 2, 11, 2, 12], [28, 4, 15]],
  };
  const LEVEL_BITS = { M: 0, Q: 3, H: 2 };
  const MAXV = 6;

  // GF(256) over x^8 + x^4 + x^3 + x^2 + 1
  const EXP = new Uint8Array(512), LOG = new Uint8Array(256);
  for (let i = 0, x = 1; i < 255; i++) { EXP[i] = x; LOG[x] = i; x <<= 1; if (x & 256) x ^= 0x11d; }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  const mul = (a, b) => (a && b ? EXP[LOG[a] + LOG[b]] : 0);

  // n Reed-Solomon codewords for one block of data
  function rs(data, n) {
    let g = [1];
    for (let i = 0; i < n; i++) { const ng = new Array(g.length + 1).fill(0); for (let j = 0; j < g.length; j++) { ng[j] ^= g[j]; ng[j + 1] ^= mul(g[j], EXP[i]); } g = ng; }
    const r = new Array(n).fill(0);
    for (const d of data) { const f = d ^ r.shift(); r.push(0); for (let j = 0; j < n; j++) r[j] ^= mul(g[j + 1], f); }
    return r;
  }

  function utf8(s) {
    if (typeof TextEncoder !== 'undefined') return Array.from(new TextEncoder().encode(String(s)));
    const e = unescape(encodeURIComponent(String(s))), out = [];
    for (let i = 0; i < e.length; i++) out.push(e.charCodeAt(i));
    return out;
  }
  const dataWords = (spec) => spec[1] * spec[2] + (spec[3] || 0) * (spec[4] || 0);
  // bytes of text a version holds at a level: 4 bits of mode and 8 of length come off the top
  const room = (v, level) => dataWords(EC[level][v - 1]) - 2;

  // the smallest version that holds the text at M, then the strongest correction that still fits in that size
  function choose(n, opts) {
    const o = opts || {};
    if (o.version || o.level) {
      const level = o.level || 'M';
      if (!EC[level]) return null;
      for (let v = o.version || 1; v <= (o.version || MAXV); v++) if (n <= room(v, level)) return { v, level };
      return null;
    }
    for (let v = 1; v <= MAXV; v++) if (n <= room(v, 'M')) return { v, level: n <= room(v, 'H') ? 'H' : n <= room(v, 'Q') ? 'Q' : 'M' };
    return null;
  }

  function codewords(bytes, v, level) {
    const spec = EC[level][v - 1], cap = dataWords(spec), bits = [];
    const put = (val, len) => { for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
    put(4, 4); put(bytes.length, 8); bytes.forEach((b) => put(b, 8));
    put(0, Math.min(4, cap * 8 - bits.length));
    while (bits.length % 8) bits.push(0);
    const data = [];
    for (let i = 0; i < bits.length; i += 8) data.push(parseInt(bits.slice(i, i + 8).join(''), 2));
    for (let p = 0; data.length < cap; p ^= 1) data.push(p ? 0x11 : 0xec);
    // blocks, each with its own correction, then woven together a codeword at a time
    const blocks = []; let at = 0;
    for (let k = 1; k < spec.length; k += 2) for (let b = 0; b < spec[k]; b++) { const d = data.slice(at, at + spec[k + 1]); at += spec[k + 1]; blocks.push({ d, e: rs(d, spec[0]) }); }
    const out = [], longest = Math.max.apply(null, blocks.map((b) => b.d.length));
    for (let i = 0; i < longest; i++) blocks.forEach((b) => { if (i < b.d.length) out.push(b.d[i]); });
    for (let i = 0; i < spec[0]; i++) blocks.forEach((b) => out.push(b.e[i]));
    return out;
  }

  const MASKS = [
    (x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x, y) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => (x * y) % 2 + (x * y) % 3 === 0,
    (x, y) => ((x * y) % 2 + (x * y) % 3) % 2 === 0, (x, y) => ((x + y) % 2 + (x * y) % 3) % 2 === 0,
  ];

  function frame(v) {
    const n = 17 + 4 * v, m = [], f = [];
    for (let y = 0; y < n; y++) { m.push(new Uint8Array(n)); f.push(new Uint8Array(n)); }
    const set = (x, y, on) => { if (x >= 0 && y >= 0 && x < n && y < n) { m[y][x] = on ? 1 : 0; f[y][x] = 1; } };
    // three finders with their light border
    [[3, 3], [n - 4, 3], [3, n - 4]].forEach((c) => { for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const d = Math.max(Math.abs(dx), Math.abs(dy)); set(c[0] + dx, c[1] + dy, d !== 2 && d !== 4); } });
    // timing lines
    for (let i = 8; i < n - 8; i++) { set(i, 6, i % 2 === 0); set(6, i, i % 2 === 0); }
    // one alignment mark, from version 2 up
    if (v > 1) { const c = n - 7; for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(c + dx, c + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1); }
    // keep the format strips free; they are written last
    for (let i = 0; i < 9; i++) { if (!f[8][i]) set(i, 8, 0); if (!f[i][8]) set(8, i, 0); }
    for (let i = 0; i < 8; i++) { set(n - 1 - i, 8, 0); set(8, n - 1 - i, 0); }
    set(8, n - 8, 1);
    return { n, m, f };
  }

  function format(q, level, mask) {
    const n = q.n, data = (LEVEL_BITS[level] << 3) | mask; let rem = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412, bit = (i) => (bits >>> i) & 1;
    for (let i = 0; i <= 5; i++) q.m[i][8] = bit(i);
    q.m[7][8] = bit(6); q.m[8][8] = bit(7); q.m[8][7] = bit(8);
    for (let i = 9; i < 15; i++) q.m[8][14 - i] = bit(i);
    for (let i = 0; i < 8; i++) q.m[8][n - 1 - i] = bit(i);
    for (let i = 8; i < 15; i++) q.m[n - 15 + i][8] = bit(i);
    q.m[n - 8][8] = 1;
  }

  // the standard's four penalties; the mask with the lowest total is the easiest to scan
  function penalty(q) {
    const n = q.n, m = q.m; let p = 0, dark = 0;
    const line = (get) => {
      let run = 1, s = '' + get(0);
      for (let i = 1; i < n; i++) { const c = get(i); s += c; if (c === get(i - 1)) run++; else { if (run >= 5) p += run - 2; run = 1; } }
      if (run >= 5) p += run - 2;
      for (let i = s.indexOf('1011101'); i >= 0; i = s.indexOf('1011101', i + 1)) {
        const before = s.slice(Math.max(0, i - 4), i), after = s.slice(i + 7, i + 11);
        if ((!/1/.test(before) && (before.length === 4 || i < 4)) || (!/1/.test(after) && (after.length === 4 || i + 11 > n))) p += 40;
      }
    };
    for (let y = 0; y < n; y++) { line((i) => m[y][i]); line((i) => m[i][y]); }
    for (let y = 0; y < n - 1; y++) for (let x = 0; x < n - 1; x++) { const c = m[y][x]; if (c === m[y][x + 1] && c === m[y + 1][x] && c === m[y + 1][x + 1]) p += 3; }
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) dark += m[y][x];
    p += Math.floor(Math.abs(dark * 20 - n * n * 10) / (n * n)) * 10;
    return p;
  }

  function make(text, opts) {
    const bytes = utf8(text), pick = choose(bytes.length, opts);
    if (!bytes.length || !pick) return null;
    const cw = codewords(bytes, pick.v, pick.level), base = frame(pick.v), n = base.n;
    // data runs up and down in two-module columns from the right, skipping the timing column
    let i = 0;
    for (let right = n - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let k = 0; k < n; k++) for (let j = 0; j < 2; j++) {
        const x = right - j, y = ((right + 1) & 2) === 0 ? n - 1 - k : k;
        if (!base.f[y][x] && i < cw.length * 8) { base.m[y][x] = (cw[i >>> 3] >>> (7 - (i & 7))) & 1; i++; }
      }
    }
    const forced = opts && opts.mask != null ? +opts.mask : -1;
    let best = null;
    for (let k = 0; k < 8; k++) {
      if (forced >= 0 && k !== forced) continue;
      const q = { n, m: base.m.map((r) => Uint8Array.from(r)) };
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (!base.f[y][x] && MASKS[k](x, y)) q.m[y][x] ^= 1;
      format(q, pick.level, k);
      const p = penalty(q);
      if (!best || p < best.p) best = { p, k, q };
    }
    const m = best.q.m;
    return { size: n, version: pick.v, level: pick.level, mask: best.k, dark: (x, y) => m[y][x] === 1, rows: m.map((r) => Array.from(r).join('')) };
  }

  // one SVG path of the dark modules, a unit per module: runs along each row
  function path(q) {
    let d = '';
    for (let y = 0; y < q.size; y++) for (let x = 0; x < q.size; x++) {
      if (!q.dark(x, y)) continue;
      let w = 1; while (x + w < q.size && q.dark(x + w, y)) w++;
      d += `M${x} ${y}h${w}v1h-${w}z`; x += w;
    }
    return d;
  }

  const api = { make, path, room, MAXV };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.BatchQR = api;
})(typeof window !== 'undefined' ? window : globalThis);
