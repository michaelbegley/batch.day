# Phase 1b checks (14 Nov): share picture, freezer labels, store links (Instacart row off, Amazon gear line on).
# Nothing leaves the machine: the AI reader, analytics, ads, the CDN, /api and every store are blocked or mocked.
import asyncio, json, io, base64, datetime, pypdf
from PIL import Image
from playwright.async_api import async_playwright
U='http://localhost:8765/'
R=[]
def log(name,ok,note=''):
    R.append((name,'ok' if ok else 'FAIL',str(note))); open('breakit/r7.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',name,'|',str(note)[:300])
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective+' '+e.blockedURI));
window.__ev=[];window.va=function(a,b){window.__ev.push(b)};
window.__printed=0;window.print=()=>{window.__printed++};
window.__open=[];window.__loc=[];window.open=function(){window.__open.push([...arguments]);return {opener:1,location:{replace:(u)=>window.__loc.push(u)}}};"""
STUB="window.__BD_AFF={instacart:'https://example.com/instacart-stub?x=1',amazonTag:'stub-20'};"
FSHARE="window.__files=[];window.__mode='ok';navigator.canShare=(d)=>window.__mode!=='cant'&&!!(d&&d.files);navigator.share=async(d)=>{if(window.__mode==='abort'){const e=new Error('x');e.name='AbortError';throw e}window.__files.push({n:d.files.length,name:d.files[0].name,type:d.files[0].type,size:d.files[0].size,keys:Object.keys(d)})};"
AMZ='As an Amazon Associate I earn from qualifying purchases.'
PNG="()=>{const i=document.getElementById('picImg'),c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);return c.toDataURL('image/png').split(',')[1]}"
EV="(n)=>window.__ev.filter(e=>e.name===n).map(e=>e.data)"
REHEAT="Turkey chili\nServes 4\n1 lb ground turkey\n1 can beans\n2 cups broth\n1. Brown the turkey.\n2. Simmer 30 minutes. To reheat, microwave 2.5 minutes and stir. Serve hot."
PREHEAT="Baked ziti\nServes 4\n1 lb pasta\n2 cups sauce\n1. Preheat the oven to 375.\n2. Bake 30 minutes."
LONGRH="Bean stew\nServes 4\n2 cans beans\n2 cups broth\n1. Simmer 30 minutes.\n2. To reheat this one you should really take your time and warm it slowly in a pot over a low flame while stirring now and then so nothing catches on the bottom of it."
HTMLT='<b>Mac</b> & "cheese"\nServes 4\n1 lb pasta\n2 cups cheese\n1. Boil.\n2. Mix.'
calls=[]
async def fresh(b,init='',mobile=True,api=None,**kw):
    ctx=await b.new_context(viewport={'width':390,'height':844} if mobile else {'width':1280,'height':900},is_mobile=mobile,has_touch=mobile,permissions=['clipboard-read','clipboard-write'],accept_downloads=True,**kw); errs=[]
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**','**/*.amazon.com/**','**/*.instacart.com/**','**/example.com/**'): await ctx.route(pat,lambda r:r.abort())
    async def apih(r):
        calls.append({'method':r.request.method,'body':r.request.post_data})
        if api is None or api=='down': await r.abort()
        else: await r.fulfill(status=api[0],content_type='application/json',body=json.dumps(api[1]))
    await ctx.route('**/api/**',apih)
    await ctx.add_init_script(INIT+init); pg=await ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    pg.on('dialog',lambda d:errs.append('dialog'))
    await pg.goto(U); await pg.wait_for_timeout(300)
    return ctx,pg,errs
async def sample(pg):
    await pg.click('#sample'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(700)
async def paste(pg,t):
    await pg.goto(U); await pg.wait_for_timeout(200); await pg.click('#pasteToggle'); await pg.fill('#paste',t); await pg.click('#usePaste'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(500)
async def tab(pg,t): await pg.click(f'[data-tab={t}]'); await pg.wait_for_timeout(250)
async def meals(pg,n): await pg.fill('#want',str(n)); await pg.evaluate("document.getElementById('want').blur()"); await pg.wait_for_timeout(350)  # blur sends the box's own change event
async def openpic(pg):
    await pg.click('#dShare'); await pg.wait_for_timeout(150); await pg.click('[data-pic]'); await pg.wait_for_selector('#picGo:not([disabled])'); await pg.wait_for_timeout(150)
async def png(pg): return Image.open(io.BytesIO(base64.b64decode(await pg.evaluate(PNG)))).convert('RGB')
def near(a,b,t=6): return all(abs(x-y)<=t for x,y in zip(a,b))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # ---------- store links: as shipped (Instacart off, Amazon on) ----------
        ctx,pg,errs=await fresh(b)
        log('links: none on the home page',await pg.locator('.aff').count()==0)
        await sample(pg)
        log('links: no Instacart row while its URL is empty',await pg.locator('#affShop').count()==0 and 'Instacart' not in await pg.inner_text('#sheet'))
        await tab(pg,'store'); g=pg.locator('#affGear')
        href=await g.get_attribute('href') if await g.count() else ''
        log('gear: one Freezer containers link on the Store tab',await g.count()==1 and await pg.locator('.aff').count()==1 and (await g.locator('span').inner_text()).strip()=='Freezer containers')
        log('gear: Amazon search with the tag',href=='https://www.amazon.com/s?k=freezer+meal+prep+containers&tag=batchrecipes-20',href)
        log('gear: sponsored, noopener, new tab',await g.get_attribute('rel')=='sponsored noopener' and await g.get_attribute('target')=='_blank')
        log('gear: Amazon disclosure, word for word',(await g.locator('small').inner_text()).strip()==AMZ,await g.locator('small').inner_text())
        bx=await g.bounding_box(); log('gear: tap target 44 or more',bx['height']>=44 and bx['width']>=44,bx)
        log('gear: visible only on the Store tab',await g.is_visible())
        await tab(pg,'shop'); log('gear: not shown on the Shop tab',not await g.is_visible())
        await tab(pg,'store'); await g.evaluate("a=>a.addEventListener('click',e=>e.preventDefault())"); await g.click(); await pg.wait_for_timeout(100)
        log('gear: click is counted',await pg.evaluate(EV,'Shop link')==[{'src':'direct','to':'amazon'}],await pg.evaluate(EV,'Shop link'))
        await pg.click('#dCook'); await pg.wait_for_timeout(500)
        cov=await pg.evaluate("(()=>{const a=document.querySelector('#affGear').getBoundingClientRect();const e=document.elementFromPoint(Math.min(innerWidth-1,Math.max(0,a.left+a.width/2)),Math.min(innerHeight-1,Math.max(0,a.top+a.height/2)));return {inCook:!!document.querySelector('#cook .aff'),top:e?!!e.closest('#cook'):null}})()")
        log('links: none in cook mode',not cov['inCook'] and cov['top'] is not False,cov)
        await pg.click('#cClose'); await pg.wait_for_timeout(400)
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300)
        log('links: none in Just scale',await pg.locator('.aff').count()==0)
        await pg.click('#mode [data-m=batch]'); await pg.wait_for_timeout(300)
        await pg.emulate_media(media='print'); log('links: not printed',await pg.evaluate("[...document.querySelectorAll('.affrow')].every(e=>getComputedStyle(e).display==='none')")); await pg.emulate_media(media='screen')
        log('links: no errors',not errs,errs); await ctx.close()
        # bakes: nothing portioned, no gear
        ctx,pg,errs=await fresh(b); await paste(pg,"Banana bread\nServes 8\n2 cups flour\n1 cup sugar\n2 eggs\n1 tsp baking soda\n3 bananas\n1. Mix.\n2. Bake 60 minutes.")
        await pg.click('#mode [data-m=batch]'); await pg.wait_for_timeout(300)
        log('gear: not on a plan without portions (a bake)',await pg.locator('#affGear').count()==0,await pg.inner_text('#sMeta')); await ctx.close()
        # privacy page
        ctx,pg,errs=await fresh(b); await pg.goto(U+'privacy.html'); tx=await pg.inner_text('main')
        log('privacy: affiliate section with the Amazon line','Affiliate links' in tx and AMZ in tx and 'may earn a commission' in tx and "store's own site" in tx)
        log('privacy: no em or en dashes in the new section',not any(c in tx[tx.index('Affiliate links'):tx.index('California')] for c in '—–')); await ctx.close()
        # ---------- store links: stub values ----------
        ctx,pg,errs=await fresh(b,STUB); await sample(pg)
        a=pg.locator('#affShop')
        log('shop: one row under the list',await a.count()==1 and await pg.evaluate("(()=>{const a=document.querySelector('#affShop').closest('.affrow'),c=a.closest('.card');return a===[...c.children].filter(e=>e.offsetParent).pop()&&!!c.querySelector('.checks')})()"))
        log('shop: words',(await a.locator('span').inner_text()).strip()=='Shop on Instacart' and (await a.locator('small').inner_text()).strip()=='We may earn from purchases')
        log('shop: sponsored, noopener, new tab, real href',await a.get_attribute('rel')=='sponsored noopener' and await a.get_attribute('target')=='_blank' and await a.get_attribute('href')=='https://example.com/instacart-stub?x=1')
        bx=await a.bounding_box(); log('shop: tap target 44 or more',bx['height']>=44,bx)
        # tick one, make one a staple: neither is on the copied list
        names=await pg.locator('.checks:not(.pan) .tx').all_inner_texts()
        await pg.locator('.checks:not(.pan) input').nth(0).check(); await pg.click('#stEdit'); await pg.locator('.checks:not(.pan) .stp').nth(1).click(); await pg.wait_for_timeout(200); await pg.click('#stEdit')
        want=[n.strip() for k,n in enumerate(names) if k not in (0,1)]
        await pg.locator('#affShop').click(); await pg.wait_for_timeout(300)
        clip=(await pg.evaluate('navigator.clipboard.readText()')).split('\n')
        norm=lambda s:' '.join(s.replace('check amount','').replace('for serving','').split())
        log('shop: clipboard has what is left to buy (no ticked item, no staple)',[norm(x) for x in clip]==[norm(x) for x in want],f'{len(clip)} of {len(names)}: {clip[:3]}')
        log('shop: toast says List copied',(await pg.inner_text('#toast')).strip()=='List copied',await pg.inner_text('#toast'))
        op=await pg.evaluate('window.__open'); log('shop: store opened in a new tab with the tracking URL',op==[['https://example.com/instacart-stub?x=1','_blank','noopener']],op)
        log('shop: no call to the API while it is off',not calls,calls)
        log('shop: click is counted',await pg.evaluate(EV,'Shop link')==[{'src':'direct','to':'instacart'}])
        await tab(pg,'store'); log('gear: stub tag in the link',await pg.get_attribute('#affGear','href')=='https://www.amazon.com/s?k=freezer+meal+prep+containers&tag=stub-20')
        log('links: at most one of each',await pg.locator('#affShop').count()==1 and await pg.locator('#affGear').count()==1 and await pg.locator('.aff').count()==2)
        for w in (320,195):
            await pg.set_viewport_size({'width':w,'height':800}); await pg.wait_for_timeout(200); ok=[]
            for t in ('shop','store'):
                await tab(pg,t); ok.append(await pg.evaluate("document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('.aff')].filter(e=>e.offsetParent).every(e=>{const r=e.getBoundingClientRect(),c=e.closest('.card').getBoundingClientRect();return r.left>=c.left&&r.right<=c.right})"))
            log(f'links: fit at {w}px',all(ok),ok)
        log('links (stub): no errors',not errs,errs); await ctx.close()
        # the override is for local tests only, and bad values are refused
        ctx,pg,errs=await fresh(b,STUB); html=open('site/index.html').read()
        await ctx.route('http://bd-not-local.test/**',lambda r:r.fulfill(status=200,content_type='text/html',body=html))
        await pg.goto('http://bd-not-local.test/'); await pg.wait_for_timeout(300); await sample(pg); await tab(pg,'store')
        log('override ignored off localhost',await pg.locator('#affShop').count()==0 and 'tag=batchrecipes-20' in (await pg.get_attribute('#affGear','href') or ''),await pg.evaluate('location.hostname')); await ctx.close()
        for nm,bad in (('script URL',"{instacart:'javascript:alert(1)',amazonTag:'a b&c=d'}"),('http URL and markup',"{instacart:'http://example.com/',amazonTag:'<i>'}"),('not strings',"{instacart:7,amazonTag:{}}")):
            ctx,pg,errs=await fresh(b,f"window.__BD_AFF={bad};"); await sample(pg); await tab(pg,'store')
            log(f'bad values refused ({nm})',await pg.locator('.aff').count()==0 and not errs,errs); await ctx.close()
        # the API path: built, off by default
        for nm,api,exp in (('cart link from the API',(200,{'url':'https://example.com/cart/abc'}),'https://example.com/cart/abc'),('503 off',(503,{'off':True}),'https://example.com/instacart-stub?x=1'),('network down','down','https://example.com/instacart-stub?x=1'),('answer is not an https link',(200,{'url':'javascript:alert(1)'}),'https://example.com/instacart-stub?x=1')):
            calls.clear(); ctx,pg,errs=await fresh(b,STUB+"window.__BD_AFF.instacartApi=true;",api=api); await sample(pg)
            await pg.locator('.checks:not(.pan) input').nth(0).check(); n=await pg.locator('.checks:not(.pan) input').count()
            await pg.click('#affShop'); await pg.wait_for_timeout(500)
            body=json.loads(calls[0]['body']) if calls and calls[0]['body'] else {}
            okb=calls and calls[0]['method']=='POST' and body.get('title')=='Brothy chicken and rice' and len(body.get('items',[]))==n-1 and all(set(i)=={'name','text'} for i in body['items'])
            op=await pg.evaluate('window.__open'); loc=await pg.evaluate('window.__loc'); clip=await pg.evaluate('navigator.clipboard.readText()')
            log(f'API: {nm}',bool(okb) and op==[['','_blank']] and loc==[exp] and len(clip.split('\n'))==n-1 and not errs,{'open':op,'loc':loc,'body':str(body)[:120],'errs':errs}); await ctx.close()
        # ---------- share picture ----------
        ctx,pg,errs=await fresh(b,mobile=False); await sample(pg)
        await pg.click('#dShare'); await pg.wait_for_timeout(200)
        rows=[x.strip() for x in await pg.locator('#menu .mrow:not(.hidden)').all_inner_texts()]
        log('picture: Share picture row in the Share sheet','Share picture' in rows,rows)
        await pg.click('[data-pic]'); await pg.wait_for_selector('#picGo:not([disabled])'); await pg.wait_for_timeout(450)
        log('picture: preview opens, Share sheet closes',await pg.is_visible('#pic') and not await pg.is_visible('#menu') and await pg.get_attribute('#pic','aria-modal')=='true')
        im=await png(pg); geo=json.loads(await pg.get_attribute('#picImg','data-geo'))
        log('picture: story is the default, 1080x1920',im.size==(1080,1920) and await pg.get_attribute('#picSize [data-s=story]','aria-pressed')=='true',im.size)
        log('picture: alt text has the dish and the count',await pg.get_attribute('#picImg','alt')=='Brothy chicken and rice, 14 meals',await pg.get_attribute('#picImg','alt'))
        px=im.load(); cols={c for x in range(0,1080,4) for y in range(0,1920,4) for c in [px[x,y]]}
        log('picture: light look (grey ground, white card, ink, accent)',near(px[4,4],(245,245,247)) and near(px[540,300],(255,255,255)) and any(near(c,(194,65,12),10) for c in cols) and any(near(c,(29,29,31),10) for c in cols))
        s=geo['slot']; blank=all(near(px[x,y],(255,255,255),2) for x in range(s['x'],s['x']+s['w'],6) for y in range(s['y'],s['y']+s['h'],4))
        log('picture: the cost per meal place is kept and empty',blank and s['h']>=40 and s['y']>geo['bottom'] and s['y']+s['h']<geo['word'][0],s)
        def rows_used(im,x0,x1,y0,y1):
            p=im.load(); ys=[y for y in range(y0,y1) if any(not near(p[x,y],(255,255,255),8) for x in range(x0,x1,3))]; return (ys[0],ys[-1]) if ys else None
        c=geo['card']; ink=rows_used(im,geo['side'],1080-geo['side'],c[1]+8,geo['word'][0]-8)
        log('picture: block centred between the card top and the word mark',abs((ink[0]-geo['free'][0])-(geo['free'][1]-ink[1]))<=14,{'above':ink[0]-geo['free'][0],'below':geo['free'][1]-ink[1]})
        await pg.click('#picSize [data-s=pin]'); await pg.wait_for_selector('#picGo:not([disabled])'); await pg.wait_for_timeout(200); im2=await png(pg)
        log('picture: Pinterest size 1000x1500',im2.size==(1000,1500) and await pg.get_attribute('#picSize [data-s=pin]','aria-pressed')=='true',im2.size)
        log('picture: desktop button says Save picture',(await pg.inner_text('#picGo')).strip()=='Save picture')
        async with pg.expect_download() as dl: await pg.click('#picGo')
        d=await dl.value; f=await d.path(); dim=Image.open(f).size
        log('picture: downloads a PNG named for the dish and size',d.suggested_filename=='batch-recipes-brothy-chicken-and-rice-pin.png' and dim==(1000,1500),(d.suggested_filename,dim))
        await pg.wait_for_timeout(400)
        log('picture: event {size, how}',await pg.evaluate(EV,'Share picture')==[{'src':'direct','size':'pin','how':'download'}],await pg.evaluate(EV,'Share picture'))
        log('picture: closes after saving, focus back on Share',not await pg.is_visible('#pic') and await pg.evaluate("document.activeElement.id")=='dShare')
        # keyboard
        await openpic(pg); f0=await pg.evaluate("document.activeElement.closest('#pic')!==null")
        seen=set()
        for _ in range(8): await pg.keyboard.press('Tab'); seen.add(await pg.evaluate("document.activeElement.closest('#pic')!==null"))
        log('picture: focus starts inside and Tab stays inside',f0 and seen=={True})
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
        log('picture: Escape closes',not await pg.is_visible('#pic') and await pg.evaluate("document.activeElement.id")=='dShare')
        await openpic(pg); await pg.mouse.click(5,5); await pg.wait_for_timeout(400); log('picture: a click outside closes',not await pg.is_visible('#pic'))
        # counts
        await meals(pg,1); await openpic(pg); a1=await pg.get_attribute('#picImg','alt'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(350)
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300); await meals(pg,6); await openpic(pg); a2=await pg.get_attribute('#picImg','alt'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(350)
        log('picture: 1 meal, and servings in Just scale',a1.endswith(', 1 meal') and a2.endswith(', 6 servings'),(a1,a2))
        log('picture: no errors',not errs,errs); await ctx.close()
        # hard titles
        for nm,t in (('very long, no spaces','A'*220),('long with spaces',' '.join(['Slow cooker chicken tortilla soup']*6)),('right to left','שקשוקה עם חצילים וטחינה'),('emoji and markup','<img src=x onerror=alert(1)> 🍲 "soup"')):
            ctx,pg,errs=await fresh(b,mobile=False); await paste(pg,t+"\nServes 4\n1 lb chicken\n2 cups rice\n1. Cook 20 minutes."); await meals(pg,999); await openpic(pg)
            im=await png(pg); geo=json.loads(await pg.get_attribute('#picImg','data-geo')); px=im.load(); c=geo['card']
            edge=all(near(px[x,y],(255,255,255),3) for y in range(c[1]+70,c[1]+c[3]-70,5) for x in (c[0]+40,c[0]+c[2]-40))
            log(f'picture: {nm} title stays inside the card',im.size==(1080,1920) and geo['lines']<=3 and edge and geo['top']>=geo['free'][0] and geo['bottom']<=geo['free'][1] and not errs,{'lines':geo['lines'],'top':geo['top'],'bottom':geo['bottom'],'free':geo['free'],'errs':errs}); await ctx.close()
        # phone: the share sheet gets one PNG file and nothing else
        ctx,pg,errs=await fresh(b,FSHARE,color_scheme='dark'); await sample(pg); await openpic(pg)
        log('picture: phone button says Share',(await pg.inner_text('#picGo')).strip()=='Share')
        im=await png(pg); log('picture: light look in dark mode too',near(im.load()[4,4],(245,245,247)) and near(im.load()[540,300],(255,255,255)))
        fit=await pg.evaluate("(()=>{const b=document.querySelector('#pic .mbox').getBoundingClientRect(),i=document.getElementById('picImg').getBoundingClientRect();return {in:b.top>=0&&b.bottom<=innerHeight&&b.left>=0&&b.right<=innerWidth,ratio:Math.round(i.width/i.height*1000),ow:document.documentElement.scrollWidth<=innerWidth}})()")
        log('picture: preview fits the phone, not stretched',fit['in'] and fit['ow'] and abs(fit['ratio']-562)<=4,fit)
        await pg.evaluate("window.__mode='abort'"); await pg.tap('#picGo'); await pg.wait_for_timeout(300)
        log('picture: backing out of the share sheet keeps the preview, no event',await pg.is_visible('#pic') and await pg.evaluate(EV,'Share picture')==[])
        await pg.evaluate("window.__mode='ok'"); await pg.tap('#picGo'); await pg.wait_for_timeout(400)
        fl=await pg.evaluate('window.__files')
        log('picture: shares one PNG file, files only',len(fl)==1 and fl[0]['n']==1 and fl[0]['type']=='image/png' and fl[0]['name']=='batch-recipes-brothy-chicken-and-rice-story.png' and fl[0]['keys']==['files'] and fl[0]['size']>5000,fl)
        log('picture: event how share',await pg.evaluate(EV,'Share picture')==[{'src':'direct','size':'story','how':'share'}],await pg.evaluate(EV,'Share picture'))
        await pg.evaluate("window.__mode='cant'"); await openpic(pg)
        async with pg.expect_download() as dl: await pg.tap('#picGo')
        log('picture: phone that cannot share a file downloads it',(await dl.value).suggested_filename.endswith('-story.png'))
        await pg.wait_for_timeout(400); await openpic(pg); await pg.go_back(); await pg.wait_for_timeout(500)
        log('picture: Back closes the preview',not await pg.is_visible('#pic'))
        log('picture (phone): no errors',not errs,errs); await ctx.close()
        ctx,pg,errs=await fresh(b); await sample(pg); bad=[]
        for w,h in ((320,568),(195,422),(844,390)):
            await pg.set_viewport_size({'width':w,'height':h}); await pg.wait_for_timeout(200); await openpic(pg)
            r=await pg.evaluate("(()=>{const m=document.querySelector('#pic .mbox'),b=m.getBoundingClientRect(),g=document.getElementById('picGo').getBoundingClientRect();return {in:b.top>=0&&b.bottom<=innerHeight+1&&b.left>=0&&b.right<=innerWidth,ow:document.documentElement.scrollWidth<=innerWidth,reach:m.scrollHeight<=m.clientHeight+1||getComputedStyle(m).overflowY==='auto',btn:g.height>=44}})()")
            if not all(r.values()): bad.append((w,h,r))
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(350)
        log('picture: sheet fits or scrolls at 320, 195 and on its side',not bad,bad); await ctx.close()
        ctx,pg,errs=await fresh(b,reduced_motion='reduce'); await sample(pg); await openpic(pg); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        log('picture: reduced motion opens and closes',not await pg.is_visible('#pic') and not errs,errs); await ctx.close()
        # ---------- freezer labels ----------
        ctx,pg,errs=await fresh(b,mobile=False); await sample(pg); await tab(pg,'store')
        today=datetime.date.today(); us=today.strftime('%b ')+str(today.day)+today.strftime(', %Y')
        lt=' '.join((await pg.inner_text('#lblPrev .lbl')).split())
        log('labels: card on the Store tab with a label preview',await pg.is_visible('.labels') and await pg.is_visible('#lblPrint') and await pg.is_visible('#lblImg'))
        log('labels: dish, 1 of 14, cooked today, use by left to write in',lt==f'Brothy chicken and rice Cooked {us} Use by 1 of 14',lt)  # with the QR (breakit9) the count sits under the code
        st=await pg.evaluate("(()=>{const r=[...document.querySelectorAll('#lblPrev .lbl .lt>div')];return {rows:r.length,useLine:r[2].lastElementChild.tagName==='I'&&r[2].lastElementChild.previousElementSibling.textContent==='Use by',third:r[3].children.length===1&&r[3].firstElementChild.tagName==='I'&&!r[3].textContent.trim()}})()")
        log('labels: use by is a blank line, and so is the reheat row (the sample has none)',st=={'rows':4,'useLine':True,'third':True},st)
        log('labels: no storage time anywhere on the label',not any(w in lt.lower() for w in ('month','week','days','best','within')))
        log('labels: date box holds today',await pg.input_value('#lblDate')==today.isoformat())
        await pg.fill('#lblDate','2026-12-03'); await pg.wait_for_timeout(150); l2=' '.join((await pg.inner_text('#lblPrev .lbl')).split())
        log('labels: cooked date can be changed','Cooked Dec 3, 2026 Use by' in l2,l2)
        await meals(pg,31); l3=' '.join((await pg.inner_text('#lblPrev .lbl')).split())
        log('labels: follows the meal count, keeps the date','1 of 31' in l3 and 'Dec 3, 2026' in l3 and await pg.input_value('#lblDate')=='2026-12-03',l3)
        await pg.fill('#lblDate',''); await pg.wait_for_timeout(150)
        log('labels: no date leaves a line to write on',await pg.evaluate("(()=>{const r=document.querySelectorAll('#lblPrev .lbl .lt>div')[1];return r.firstElementChild.textContent==='Cooked'&&r.children[1].tagName==='I'&&r.querySelectorAll('i').length===1})()"))
        await pg.fill('#lblDate','2026-12-03'); await meals(pg,14)
        # print
        await pg.click('#lblPrint'); await pg.wait_for_timeout(300)
        log('labels: Print labels calls print once',await pg.evaluate('window.__printed')==1)
        log('labels: event how print',await pg.evaluate(EV,'Labels')==[{'src':'direct','how':'print'}],await pg.evaluate(EV,'Labels'))
        await pg.emulate_media(media='print')
        G="""(()=>{const R=(n)=>Math.round(n*100)/100,ls=[...document.querySelectorAll('#labels .lbl')],r=ls.map(e=>e.getBoundingClientRect()),sh=[...document.querySelectorAll('.lsheet')];
          const vis=[...document.body.children].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.id||e.tagName);
          return {n:ls.length,sheets:sh.map(s=>s.children.length),vis,w:[...new Set(r.map(x=>R(x.width)))],h:[...new Set(r.map(x=>R(x.height)))],lefts:[...new Set(r.map(x=>R(x.left)))],top:R(r[0].top-sh[0].getBoundingClientRect().top),rowStep:r.length>3?R(r[3].top-r[0].top):null,sheetW:R(sh[0].getBoundingClientRect().width),
           page:[...document.querySelectorAll('style')].some(s=>/@page\\{size:8\\.5in 11in;margin:0\\}/.test(s.textContent)),nums:ls.map(e=>(e.querySelector('.lq span')||e.querySelector('span')).textContent),border:getComputedStyle(ls[0]).borderTopWidth,shadow:getComputedStyle(ls[0]).boxShadow}})()"""
        g=await pg.evaluate(G)
        log('labels: only the labels print',g['vis']==['labels'],g['vis'])
        log('labels: one per meal, numbered 1 of 14 to 14 of 14',g['n']==14 and g['sheets']==[14] and g['nums']==[f'{k} of 14' for k in range(1,15)],g['nums'][:3])
        log('labels: Avery 5160 label size 2.625 x 1 in',g['w']==[252] and g['h']==[96],(g['w'],g['h']))
        log('labels: 0.1875 in side margin, 0.125 in between columns',g['lefts']==[18,282,546] and g['sheetW']==816 and 816-(546+252)==18,(g['lefts'],g['sheetW']))
        log('labels: 0.5 in top margin, rows 1 in apart with no gap',g['top']==48 and g['rowStep']==96,(g['top'],g['rowStep']))
        log('labels: page rule letter with no margin, no label border or shadow',g['page'] and g['border']=='0px' and g['shadow']=='none',(g['page'],g['border'],g['shadow']))
        pdf=pypdf.PdfReader(io.BytesIO(await pg.pdf(prefer_css_page_size=True,print_background=True))); mb=pdf.pages[0].mediabox; txt=pdf.pages[0].extract_text()
        log('labels: PDF is one US letter page with the labels and nothing else',len(pdf.pages)==1 and (float(mb.width),float(mb.height))==(612.0,792.0) and txt.count('Brothy chicken and rice')==14 and txt.count('Use by')==14 and 'Grocery' not in txt and 'Where it goes' not in txt and 'Start cooking' not in txt,(len(pdf.pages),str(mb),txt[:300]))
        await pg.emulate_media(media='screen')
        log('labels: nothing shows on screen while printing',await pg.evaluate("getComputedStyle(document.getElementById('labels')).display")=='none' and await pg.is_visible('.labels'))
        await pg.evaluate("dispatchEvent(new Event('afterprint'))")
        log('labels: cleaned up after printing',await pg.evaluate("!document.body.classList.contains('plabels')&&!document.querySelector('#labels .lbl')&&![...document.querySelectorAll('style')].some(s=>/@page/.test(s.textContent))"))
        # recipe print after a label print that never reported back
        await pg.click('#lblPrint'); await pg.wait_for_timeout(200); await pg.click('#dShare'); await pg.wait_for_timeout(150); await pg.click('[data-print]'); await pg.wait_for_timeout(300)
        await pg.emulate_media(media='print'); vis=await pg.evaluate("({lab:document.body.classList.contains('plabels'),main:getComputedStyle(document.getElementById('main')).display,card:getComputedStyle(document.querySelector('.labels')).display})"); await pg.emulate_media(media='screen')
        log('labels: printing the recipe afterwards prints the recipe, without the labels card',not vis['lab'] and vis['main']!='none' and vis['card']=='none',vis)
        for n,exp in ((30,[30]),(31,[30,1]),(61,[30,30,1])):
            await meals(pg,n); await pg.click('#lblPrint'); await pg.wait_for_timeout(250); await pg.emulate_media(media='print'); g=await pg.evaluate(G)
            pdf=pypdf.PdfReader(io.BytesIO(await pg.pdf(prefer_css_page_size=True))); await pg.emulate_media(media='screen'); await pg.evaluate("dispatchEvent(new Event('afterprint'))")
            log(f'labels: {n} meals fill {len(exp)} sheet(s) of 30',g['sheets']==exp and len(pdf.pages)==len(exp) and g['nums'][-1]==f'{n} of {n}',(g['sheets'],len(pdf.pages)))
        # image
        await meals(pg,14); dls=[]; pg.on('download',lambda d:dls.append(d))
        await pg.click('#lblImg'); await pg.wait_for_timeout(1200)
        ims=[(d.suggested_filename,Image.open(await d.path()).convert('RGB')) for d in dls]
        log('labels: Save as image gives one PNG strip, a 788 x 300 row per label',len(ims)==1 and ims[0][0]=='freezer-labels-brothy-chicken-and-rice.png' and ims[0][1].size==(788,4200),[(n,i.size) for n,i in ims])
        if ims:
            im=ims[0][1]; px=im.load(); rows=[sum(1 for x in range(0,788,2) if sum(px[x,y])<200) for y in range(4200)]
            per=[sum(rows[r*300+6:r*300+294]) for r in range(14)]; edge=all(sum(px[x,y])>600 for y in range(0,4200,7) for x in (8,779))
            log('labels: every row of the strip is drawn, white edges kept clear',min(per)>1500 and edge,per[:4])
        log('labels: event how download',(await pg.evaluate(EV,'Labels'))[-1]=={'src':'direct','how':'download'},(await pg.evaluate(EV,'Labels'))[-1])
        dls.clear(); await meals(pg,31); await pg.click('#lblImg'); await pg.wait_for_timeout(2000)
        sz=sorted([(d.suggested_filename,Image.open(await d.path()).size) for d in dls])
        log('labels: 31 meals come as two strips (30 rows, then 1)',sz==[('freezer-labels-brothy-chicken-and-rice-1.png',(788,9000)),('freezer-labels-brothy-chicken-and-rice-2.png',(788,300))],sz)
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300)
        log('labels: not in Just scale',await pg.locator('.labels').count()==0)
        log('labels: no errors',not errs,errs); await ctx.close()
        # reheat line: only from the recipe's own words
        for nm,rec,exp in (('recipe has one',REHEAT,'To reheat, microwave 2.5 minutes and stir.'),('preheat is not reheat',PREHEAT,''),('too long for a label: left blank',LONGRH,'')):
            ctx,pg,errs=await fresh(b,mobile=False); await paste(pg,rec)
            if await pg.get_attribute('#mode [data-m=batch]','aria-pressed')!='true': await pg.click('#mode [data-m=batch]'); await pg.wait_for_timeout(300)
            await tab(pg,'store'); r=await pg.evaluate("(()=>{const d=document.querySelectorAll('#lblPrev .lbl .lt>div')[3];return {t:d.textContent.trim(),blank:!!d.querySelector('i')}})()")
            log(f'labels: reheat line, {nm}',r['t']==exp and r['blank']==(exp==''),r); await ctx.close()
        ctx,pg,errs=await fresh(b,mobile=False); await paste(pg,HTMLT); await tab(pg,'store')
        r=await pg.evaluate("({t:document.querySelector('#lblPrev b').textContent,tags:document.querySelectorAll('#lblPrev b *').length})")
        await pg.click('#lblPrint'); await pg.wait_for_timeout(200); n=await pg.evaluate("document.querySelectorAll('#labels b *').length")
        log('labels: a title with markup prints as plain text',r['t']=='<b>Mac</b> & "cheese"' and r['tags']==0 and n==0 and not errs,(r,errs)); await ctx.close()
        # phone
        ctx,pg,errs=await fresh(b,FSHARE); await sample(pg); await tab(pg,'store')
        r=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),c=q('.labels'),l=q('#lblPrev .lbl'),d=q('#lblDate'),p=q('#lblPrint'),i=q('#lblImg');return {lbl:[Math.round(l.width),Math.round(l.height)],inside:l.left>=c.left&&l.right<=c.right,date:d.height,print:p.height,img:i.height,ow:document.documentElement.scrollWidth<=innerWidth,fs:parseFloat(getComputedStyle(document.getElementById('lblDate')).fontSize)}})()")
        log('labels (phone): label at full size, targets 44 or more, date text 16px',r['lbl']==[252,96] and r['inside'] and r['date']>=44 and r['print']>=44 and r['img']>=44 and r['ow'] and r['fs']>=16,r)
        await pg.tap('#lblImg'); await pg.wait_for_timeout(800); fl=await pg.evaluate('window.__files')
        log('labels (phone): the strip goes to the share sheet as a PNG',len(fl)==1 and fl[0]['type']=='image/png' and fl[0]['name']=='freezer-labels-brothy-chicken-and-rice.png' and fl[0]['keys']==['files'],fl)
        log('labels (phone): event how share',(await pg.evaluate(EV,'Labels'))==[{'src':'direct','how':'share'}])
        bad=[]
        for w in (320,195):
            await pg.set_viewport_size({'width':w,'height':700}); await pg.wait_for_timeout(250)
            if not await pg.evaluate("document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('.labels *')].filter(e=>e.offsetParent).every(e=>{const r=e.getBoundingClientRect(),c=document.querySelector('.labels').getBoundingClientRect();return r.left>=c.left-1&&r.right<=c.right+1})"): bad.append(w)
        log('labels (phone): card fits at 320 and 195',not bad,bad)
        log('labels (phone): no errors',not errs,errs); await ctx.close()
        await b.close()
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)-len(bad)} of {len(R)} ok')
asyncio.run(main())
