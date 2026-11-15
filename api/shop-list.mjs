// "Shop this list": sends a grocery list to Instacart (Developer Platform) and returns the page link.
// Off until INSTACART_KEY is set in Vercel. Stores nothing; logs no list contents.
const ORIGINS = new Set(['https://batch.recipes', 'https://www.batch.recipes']);
const BASE = process.env.INSTACART_BASE || 'https://connect.instacart.com';
const hits = new Map(); // best-effort per-instance limit: 20 lists per IP per hour
const clean = (s, n) => String(s ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n);
const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

export async function POST(request) {
  const key = process.env.INSTACART_KEY;
  if (!key) return json(503, { off: true });
  const origin = request.headers.get('origin');
  if (!ORIGINS.has(origin)) return json(403, { error: 'origin' });
  const ip = (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() || 'x';
  const now = Date.now(), h = (hits.get(ip) || []).filter((t) => now - t < 3600e3);
  if (h.length >= 20) return json(429, { error: 'limit' });
  h.push(now); hits.set(ip, h);
  let body;
  try { body = await request.json(); } catch { return json(400, { error: 'body' }); }
  const items = Array.isArray(body?.items) ? body.items.slice(0, 80) : [];
  const line_items = items.map((i) => ({ name: clean(i?.name, 80), display_text: clean(i?.text || i?.name, 120) })).filter((i) => i.name);
  if (!line_items.length) return json(400, { error: 'empty' });
  const payload = {
    title: clean(body?.title, 80) || 'Grocery list',
    link_type: 'shopping_list',
    expires_in: 30,
    line_items,
    landing_page_configuration: { partner_linkback_url: 'https://batch.recipes/' },
  };
  try {
    const r = await fetch(BASE + '/idp/v1/products/products_link', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + key, Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(12000),
    });
    if (!r.ok) { console.log('instacart status', r.status); return json(502, { error: 'upstream' }); }
    const d = await r.json();
    const url = String(d?.products_link_url || '');
    if (!/^https:\/\/[a-z0-9.-]*instacart\.com\//i.test(url)) return json(502, { error: 'link' });
    return json(200, { url });
  } catch (e) {
    console.log('instacart error', e?.name);
    return json(504, { error: 'timeout' });
  }
}
