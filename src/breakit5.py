# Add to list: share sheet gets only the untouched items, one per line; hidden without a share sheet; fits a 320 phone.
import asyncio,json,sys
sys.path.insert(0,'.')
from breakit4 import fresh,sample
from playwright.async_api import async_playwright
R=[]
def log(n,ok,note=''):
    R.append((n,'ok' if ok else 'FAIL',str(note)));open('breakit/r5.json','w').write(json.dumps(R,indent=1));print('ok  ' if ok else 'FAIL',n,'|',str(note)[:300])
SHARE="window.__shared=[];navigator.share=async(d)=>{window.__shared.push(d)};"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    ctx,pg,errs=await fresh(b); await pg.add_init_script(SHARE); await pg.reload(); await pg.wait_for_timeout(300); await sample(pg)
    vis=await pg.is_visible('[data-addlist]'); log('button shows with a share sheet',vis)
    items=await pg.locator('.checks .tx').all_inner_texts(); n=len(items)
    await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200)
    sh=await pg.evaluate('window.__shared'); t=sh[0]['text'] if sh else ''
    lines=t.split('\n'); log('sends every item, one per line',len(lines)==n and all(l.strip() for l in lines),f'{len(lines)} of {n}: {lines[:3]}')
    log('no title or link in it',not sh[0].get('title') and 'http' not in t)
    await pg.locator('.checks input').nth(0).check(); await pg.locator('.checks input').nth(1).check(); await pg.wait_for_timeout(200)
    await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200)
    t2=(await pg.evaluate('window.__shared'))[-1]['text'].split('\n'); log('ticked items left out',len(t2)==n-2,f'{len(t2)} of {n}')
    for i in range(n): await pg.locator('.checks input').nth(i).check()
    await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200)
    t3=(await pg.evaluate('window.__shared'))[-1]['text'].split('\n'); log('all ticked sends the whole list',len(t3)==n)
    log('picker stays hidden (no shortcut yet)',not await pg.is_visible('#gpick'))
    for w in (320,390):
      await pg.set_viewport_size({'width':w,'height':800}); await pg.wait_for_timeout(200)
      r=await pg.evaluate("(()=>{const h=document.querySelector('[data-panel=shop] h3'),a=h.querySelector('.acts').getBoundingClientRect(),hb=h.getBoundingClientRect(),c=h.querySelector('[data-copy]').getBoundingClientRect(),l=h.querySelector('[data-addlist]').getBoundingClientRect();return {one:Math.abs(a.top-hb.top)<30&&hb.height<60,inside:a.right<=hb.right+1,gap:l.right<=c.left,ow:document.documentElement.scrollWidth<=innerWidth}})()")
      log(f'header fits at {w}',all(r.values()),r)
    log('no errors',not errs,errs); await ctx.close()
    ctx,pg,errs=await fresh(b); await pg.add_init_script("delete Navigator.prototype.share;"); await pg.reload(); await pg.wait_for_timeout(300); await sample(pg)
    log('hidden without a share sheet (desktop)',not await pg.is_visible('[data-addlist]') and await pg.is_visible('[data-copy]'))
    await ctx.close(); await b.close()
asyncio.run(main())
