# Full sweep fixes (15 Nov): checks for what changed after the sweep reports B, D and E.
# Run from the build folder after build.py: python3 breakit12.py  (starts its own servers; nothing live is called).
# The AI reader is mocked; Umami, AdSense, jsDelivr, Amazon, Instacart and every other outside host are blocked.
# https://batch.recipes is served from site/ by request interception, because the Vercel loader only starts on that host.
import asyncio, json, os, sys, re, base64, datetime, threading, http.server, functools, shutil, subprocess, tempfile, io
from playwright.async_api import async_playwright
from PIL import Image, ImageChops
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.join(HERE,'site')
PORT=8773; U=f'http://localhost:{PORT}/'; LIVE='https://batch.recipes/'
SHOT='/home/claude/test-shots/chicken1.jpg'
BLOCK=['**/cloud.umami.is/**','**/gateway.umami.is/**','**/pagead2.googlesyndication.com/**','**/*.doubleclick.net/**','**/cdn.jsdelivr.net/**','**/*amazon.com/**','**/*instacart.com/**','**/*impact.com/**']
CHILI='Beef chili\nServes 6\n2 lb ground beef\n1 large yellow onion\n2 cans (15 oz) kidney beans\n1 can crushed tomatoes\n2 tbsp chili powder\n1 tsp salt\n1. Brown the beef.\n2. Add the rest and simmer 30 minutes.'
SOUP='Lentil soup\nServes 4\n1 cup lentils\n2 carrots\n4 cups vegetable broth\n1. Simmer 30 minutes.'
GUIDE='how-to-double-a-recipe'
PAGES=['guides',GUIDE,'about','privacy','no-such-page/deeper']
R=[]; ERRS=[]
def log(n,ok,note=''):
    R.append([n,'ok' if ok else 'FAIL',str(note)[:600]]); print(('ok   ' if ok else 'FAIL ')+n+('' if ok else '  '+str(note)[:600]),flush=True)

def path_file(p):
    p=p.split('?')[0].split('#')[0]
    f=os.path.join(ROOT,p.lstrip('/'))
    if p.endswith('/'): f=os.path.join(f,'index.html')
    if os.path.isfile(f): return f,200
    if os.path.isfile(f+'.html'): return f+'.html',200
    return os.path.join(ROOT,'404.html'),404
TYPES={'.html':'text/html; charset=utf-8','.js':'text/javascript','.png':'image/png','.svg':'image/svg+xml','.xml':'application/xml','.txt':'text/plain','.webmanifest':'application/manifest+json','.ico':'image/x-icon'}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        f,st=path_file(self.path); d=open(f,'rb').read()
        self.send_response(st); self.send_header('Content-Type',TYPES.get(os.path.splitext(f)[1],'application/octet-stream')); self.send_header('Content-Length',str(len(d))); self.end_headers(); self.wfile.write(d)

INIT="""window.va=function(a,b){if(a==='event')try{window.bdRec(b.name,JSON.stringify(b.data||{}))}catch(e){}};
document.addEventListener('securitypolicyviolation',function(e){try{window.bdCsp(location.pathname+' '+e.violatedDirective+' '+e.blockedURI)}catch(x){}});
document.addEventListener('DOMContentLoaded',function(){window.__themeAtDcl=document.documentElement.dataset.theme||''});"""
VERCEL_STUB="fetch('/_vercel/insights/view',{method:'POST',body:'{}'}).catch(function(){});window.__vercelRan=1;"

async def new(b,w=1280,h=900,mob=False,scheme='light',live=False,reader_text=None):
    """a fresh browser profile. Returns ctx, events (list of [name,data]), requests seen at /_vercel"""
    ctx=await b.new_context(viewport={'width':w,'height':h},has_touch=mob,is_mobile=mob,color_scheme=scheme)
    ev=[]; seen=[]
    await ctx.expose_binding('bdRec',lambda s,name,data: ev.append([name,json.loads(data)]))
    await ctx.expose_binding('bdCsp',lambda s,t: ERRS.append('CSP '+t))
    await ctx.add_init_script(INIT)
    for pat in BLOCK: await ctx.route(pat,lambda r:r.abort())
    async def reader(route):
        if route.request.method=='OPTIONS': await route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type','Access-Control-Allow-Methods':'POST'}); return
        if reader_text is None: await route.abort(); return
        await route.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body=json.dumps({'text':reader_text}))
    await ctx.route('**/*.hf.space/**',reader)
    async def vercel(route):
        u=route.request.url; seen.append(u.split('/_vercel/')[1])
        if u.endswith('/script.js'): await route.fulfill(status=200,content_type='text/javascript',body=VERCEL_STUB)
        else: await route.fulfill(status=200,content_type='text/plain',body='OK')
    await ctx.route('**/_vercel/**',vercel)
    async def live_site(route):
        u=route.request.url
        if '/_vercel/' in u: await vercel(route); return
        f,st=path_file(u[len(LIVE)-1:]); await route.fulfill(status=st,content_type=TYPES.get(os.path.splitext(f)[1],'application/octet-stream'),body=open(f,'rb').read())
    if live: await ctx.route(LIVE+'**',live_site)
    else: await ctx.route(LIVE+'**',lambda r:r.abort())
    ctx._ev=ev; ctx._seen=seen
    return ctx
async def tab(ctx,url=None,**kw):
    pg=await ctx.new_page()
    pg.on('pageerror',lambda e: ERRS.append('PAGEERROR '+str(e)[:200]))
    pg.on('console',lambda m: ERRS.append('CONSOLE '+m.text[:200]) if m.type=='error' and 'Failed to load resource' not in m.text and 'net::ERR' not in m.text else None)
    if url is not None: await pg.goto(url,**kw); await pg.wait_for_timeout(350)
    return pg
def names(ev): return [e[0] for e in ev]
def of(ev,n): return [e[1] for e in ev if e[0]==n]
LS="(k)=>JSON.parse(localStorage.getItem(k)||'null')"
async def paste(pg,text):
    if not await pg.is_visible('#paste'): await pg.click('#pasteToggle')
    await pg.fill('#paste',text); await pg.wait_for_timeout(550); await pg.click('#usePaste'); await pg.wait_for_timeout(450)
async def sample(pg):
    await pg.click('#sample'); await pg.wait_for_timeout(450)
async def panel(pg,t):
    await pg.click(f'#tabs [data-tab={t}]'); await pg.wait_for_timeout(250)
async def to_end(pg):
    """cook mode, stepped to its last screen"""
    await pg.click('#dCook'); await pg.wait_for_timeout(400)
    for _ in range(40):
        if await pg.inner_text('#cNext') not in ('Next','Finish'): break
        await pg.click('#cNext'); await pg.wait_for_timeout(70)
    await pg.wait_for_timeout(600)  # past the double-tap hold
async def pic_ready(pg):
    for _ in range(80):  # polled: the page's CSP does not allow wait_for_function's eval
        if not await pg.is_disabled('#picGo'): return
        await pg.wait_for_timeout(100)
def link_for(text,y=4,w=14,m='batch'):
    raw=json.dumps({'v':1,'t':text,'y':y,'w':w,'m':m}).encode()
    return '#r=p'+base64.urlsafe_b64encode(raw).decode().rstrip('=')
def day(n): return (datetime.date.today()-datetime.timedelta(days=n)).isoformat()
def FZ(id,title,date,fz,fr,fz0=None,fr0=None): return {'id':id,'bid':None,'title':title,'date':date,'fz':fz,'fr':fr,'fz0':fz if fz0 is None else fz0,'fr0':fr if fr0 is None else fr0,'at':1763000000000}

async def main():
    srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
    async with async_playwright() as p:
        b=await p.chromium.launch()

        # ---------- 1. your own share link keeps the batch's ticks, staples and freezer rows (sweep E, B-1)
        ctx=await new(b); await ctx.grant_permissions(['clipboard-read','clipboard-write'],origin=U.rstrip('/'))
        pg=await tab(ctx,U); await paste(pg,CHILI)
        for _ in range(6): await pg.click('.step [data-t=want][data-d="1"]')
        await pg.wait_for_timeout(300)
        boxes=pg.locator('[data-panel=shop] .checks:not(.pan) input'); await boxes.nth(0).check(); await boxes.nth(1).check()
        await pg.click('#stEdit'); await pg.locator('[data-panel=shop] .checks:not(.pan) .stp').last.click(); await pg.wait_for_timeout(1000)
        await panel(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(300); await panel(pg,'shop')
        before=(await pg.evaluate(LS,'bd-batches'))[0]; st0=await pg.evaluate(LS,'bd-staples'); fz0=await pg.evaluate(LS,'bd-freezer')
        await pg.click('#dShare'); await pg.click('#menu [data-link]'); await pg.wait_for_timeout(400)
        link=await pg.evaluate('navigator.clipboard.readText()')
        log('share link: the test batch has 20 meals, 2 ticks, a staple and a freezer row',before['w']==20 and len(before['k'])==2 and len(st0)==1 and len(fz0)==1 and fz0[0]['bid']==before['id'] and '#r=' in link,(before['w'],before['k'],st0,link[:60]))
        pg2=await tab(ctx,link); await pg2.wait_for_timeout(300)
        after=(await pg2.evaluate(LS,'bd-batches')); ui=await pg2.evaluate("[...document.querySelectorAll('[data-panel=shop] input:checked')].map(i=>i.dataset.k)")
        log('share link opened in the browser that saved it: same batch, ticks still saved',len(after)==1 and after[0]['id']==before['id'] and sorted(after[0]['k'])==sorted(before['k']) and after[0]['w']==20,after)
        log('share link opened in the browser that saved it: the ticks show on the page',sorted(ui)==sorted(before['k']),ui)
        log('share link: staples and My freezer are untouched',await pg2.evaluate(LS,'bd-staples')==st0 and await pg2.evaluate(LS,'bd-freezer')==fz0)
        log('share link: the batch keeps its origin (paste), not "link"',after[0].get('f')=='paste',after[0].get('f'))
        pg3=await tab(ctx,U+'#b='+before['id']); await pg3.wait_for_timeout(300)
        ui3=await pg3.evaluate("[...document.querySelectorAll('[data-panel=shop] input:checked')].map(i=>i.dataset.k)")
        log('share link: reopened by its label code afterwards, both ticks are there',sorted(ui3)==sorted(before['k']) and await pg3.input_value('#want')=='20',ui3)
        # the same link with another number of meals: the link's meals, the saved ticks
        pg4=await tab(ctx,U+link_for(CHILI,6,8)); await pg4.wait_for_timeout(300); a4=(await pg4.evaluate(LS,'bd-batches'))
        log('a link to the same recipe with other meals: meals follow the link, ticks stay',len(a4)==1 and a4[0]['id']==before['id'] and a4[0]['w']==8 and sorted(a4[0]['k'])==sorted(before['k']),a4)
        await ctx.close()
        # someone else's link: saved as a link batch; ticking and opening the link again keeps the tick
        ctx=await new(b); pg=await tab(ctx,U+link_for(CHILI,6,10)); await pg.wait_for_timeout(300)
        await pg.locator('[data-panel=shop] .checks:not(.pan) input').nth(0).check(); await pg.wait_for_timeout(200)
        r1=(await pg.evaluate(LS,'bd-batches'))
        pg2=await tab(ctx,U+link_for(CHILI,6,10)); await pg2.wait_for_timeout(300); r2=(await pg2.evaluate(LS,'bd-batches'))
        log('a received link: saved with origin "link"; opened twice it is one batch and keeps its tick',len(r1)==1 and r1[0].get('f')=='link' and len(r2)==1 and r2[0]['id']==r1[0]['id'] and len(r2[0]['k'])==1 and r2[0].get('f')=='link',r2)
        await ctx.close()

        # ---------- 2. Returning visit only with a batch the cook made (sweep B, findings 2 and 8)
        async def next_session(ctx):
            n=len(ctx._ev); pg=await tab(ctx,U); await pg.wait_for_timeout(200); return names(ctx._ev[n:]),pg
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg); await pg.click('#dCook'); await pg.wait_for_timeout(300); await pg.click('#cClose'); await pg.wait_for_timeout(400)
        saved=await pg.evaluate(LS,'bd-batches'); ev,_=await next_session(ctx)
        log('sample only (cook mode opened, so it is saved): next session sends Visit, no Returning visit',len(saved)==1 and saved[0]['id']=='sample' and saved[0].get('f')=='sample' and ev==['Visit'],(saved and saved[0]['id'],ev)); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg); await panel(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(300); ev,_=await next_session(ctx)
        log('sample only (I cooked this): no Returning visit',ev==['Visit'],ev); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg); await pg.click('.step [data-t=want][data-d="1"]'); await pg.wait_for_timeout(300)
        saved=await pg.evaluate(LS,'bd-batches'); ev,_=await next_session(ctx)
        log('sample with the meals changed: saved, still not a Returning visit',len(saved)==1 and saved[0].get('f')=='sample' and ev==['Visit'],ev); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.click('#tourGo'); await pg.wait_for_timeout(300)
        for _ in range(5): await pg.click('#tNext'); await pg.wait_for_timeout(500)
        await pg.click('#dCook'); await pg.wait_for_timeout(300); await pg.click('#cClose'); await pg.wait_for_timeout(400)
        saved=await pg.evaluate(LS,'bd-batches'); plans=of(ctx._ev,'Plan'); ev,_=await next_session(ctx)
        log('tour only (then Start cooking): Plan says from tour, saved with origin tour, no Returning visit',len(saved)==1 and saved[0].get('f')=='tour' and [x.get('from') for x in plans]==['tour'] and ev==['Visit'],(saved and saved[0].get('f'),plans,ev)); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U+link_for(CHILI,6,10)); await pg.wait_for_timeout(300); first=names(ctx._ev); ev,pg2=await next_session(ctx)
        log('shared-link receiver: Open shared link, no Plan; next session no Returning visit',first==['Visit','Open shared link'] and ev==['Visit'],(first,ev))
        await paste(pg2,CHILI); r=(await pg2.evaluate(LS,'bd-batches')); ev,_=await next_session(ctx)
        log('the receiver then pastes the same recipe: it becomes theirs, and the next session is a Returning visit',len(r)==1 and r[0].get('f')=='paste' and ev==['Visit','Returning visit'],(r[0].get('f'),ev)); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await paste(pg,SOUP); same=names(ctx._ev); ev,pg2=await next_session(ctx)
        n=len(ctx._ev); await pg2.reload(); await pg2.wait_for_timeout(300); again=names(ctx._ev[n:])
        log('a pasted recipe: not in the session that made it, once in the next, not on reload','Returning visit' not in same and ev==['Visit','Returning visit'] and again==[],(same,ev,again)); await ctx.close()
        ctx=await new(b,reader_text=SOUP); pg=await tab(ctx,U); await pg.set_input_files('#file',SHOT); await pg.wait_for_selector('#v-sheet:not(.hidden)',timeout=15000); await pg.wait_for_timeout(300)
        r=(await pg.evaluate(LS,'bd-batches')); plans=of(ctx._ev,'Plan'); ev,_=await next_session(ctx)
        log('a recipe read from a screenshot (reader mocked): origin screenshots, Returning visit next session',len(r)==1 and r[0].get('f')=='screenshots' and plans and plans[0].get('from')=='screenshots' and ev==['Visit','Returning visit'],(r and r[0].get('f'),plans,ev))
        with_from=ctx;
        # 3 (part). Cook mode from screenshots
        pgs=ctx.pages[0]; n=len(ctx._ev); await pgs.click('#dCook'); await pgs.wait_for_timeout(300)
        log('Cook mode on a screenshot recipe carries from: screenshots',of(ctx._ev[n:],'Cook mode')==[{'src':'direct','from':'screenshots'}],of(ctx._ev[n:],'Cook mode')); await ctx.close()
        for nm,seed,want in [('a batch saved before 15 Nov (no origin) still counts',[{'id':'abc1','title':'Old','text':SOUP,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[]}],True),
                             ('an old saved sample (id sample, no origin) does not',[{'id':'sample','title':'S','text':SOUP,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[]}],False),
                             ('link and tour batches alone do not',[{'id':'l1','title':'L','text':SOUP,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[],'f':'link'},{'id':'t1','title':'T','text':CHILI,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[],'f':'tour'}],False),
                             ('one real batch among link and sample batches does',[{'id':'l1','title':'L','text':SOUP,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[],'f':'link'},{'id':'p1','title':'P','text':CHILI,'y':4,'w':14,'m':'batch','at':1762000000000,'k':[],'f':'screenshots'}],True)]:
            ctx=await new(b); await ctx.add_init_script("if(!localStorage.getItem('bd-batches'))localStorage.setItem('bd-batches',"+json.dumps(json.dumps(seed))+")")
            await tab(ctx,U); ev=names(ctx._ev)
            log('Returning visit: '+nm,ev==(['Visit','Returning visit'] if want else ['Visit']),ev); await ctx.close()
        # the origin rides in a backup
        ctx=await new(b); pg=await tab(ctx,U); await paste(pg,SOUP); await pg.click('#newRec'); await pg.wait_for_timeout(300)
        async with pg.expect_download() as dl: await pg.click('#bkUp')
        bk=json.load(open(await (await dl.value).path()))
        log('backup: each batch carries its origin',[x.get('f') for x in bk['batches']]==['paste'],[x.get('f') for x in bk['batches']]); await ctx.close()

        # ---------- 3. Cook mode and Cooked say where the recipe came from (sweep B, finding 3)
        async def cook_events(ctx,pg):
            n=len(ctx._ev); await panel(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(250)
            if await pg.locator('#didAgain').count(): await pg.click('#didAgain'); await pg.wait_for_timeout(250)
            await pg.click('#dCook'); await pg.wait_for_timeout(300); await pg.click('#cClose'); await pg.wait_for_timeout(400)
            e=ctx._ev[n:]; return [of(e,'Cook mode')[0].get('from') if of(e,'Cook mode') else None, of(e,'Cooked')[0].get('from') if of(e,'Cooked') else None, of(e,'Cooked')[0].get('portions') if of(e,'Cooked') else None]
        ctx=await new(b); pg=await tab(ctx,U); await paste(pg,CHILI); got=await cook_events(ctx,pg)
        log('events: a pasted recipe sends Cook mode and Cooked with from: paste (and Cooked keeps portions)',got==['paste','paste',14],got)
        await pg.click('#newRec'); await pg.wait_for_timeout(300); await pg.click('#savedList .open'); await pg.wait_for_timeout(400); got=await cook_events(ctx,pg)
        log('events: the same batch opened again from My batches: reopened',got[:2]==['reopened','reopened'],got); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg); got=await cook_events(ctx,pg)
        log('events: the sample: sample',got[:2]==['sample','sample'],got)
        await pg.click('#newRec'); await pg.wait_for_timeout(300); await pg.click('#savedList .open'); await pg.wait_for_timeout(400); got=await cook_events(ctx,pg)
        log('events: the saved sample opened again is still sample, so it can be filtered out',got[:2]==['sample','sample'],got); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.click('#tourGo'); await pg.wait_for_timeout(300)
        for _ in range(5): await pg.click('#tNext'); await pg.wait_for_timeout(500)
        got=await cook_events(ctx,pg); log('events: the tour: tour',got[:2]==['tour','tour'],got); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U+link_for(CHILI,6,14)); await pg.wait_for_timeout(300); got=await cook_events(ctx,pg)
        log('events: a shared link: shared',got[:2]==['shared','shared'],got)
        pg2=await tab(ctx,U); await pg2.click('#savedList .open'); await pg2.wait_for_timeout(400); got=await cook_events(ctx,pg2)
        log('events: a link batch opened again from My batches is still shared',got[:2]==['shared','shared'],got); await ctx.close()

        # ---------- 4. a visit that lands on a guide keeps its source (sweep B, finding 5)
        ctx=await new(b); pg=await tab(ctx,U+GUIDE,referer='https://www.google.com/')
        src=await pg.evaluate("sessionStorage.getItem('bd-src')"); await pg.click('.cta .btn'); await pg.wait_for_timeout(500)
        v=of(ctx._ev,'Visit'); await sample(pg); pl=of(ctx._ev,'Plan')
        log('Google to a guide to home: the guide records google.com and the home Visit and Plan carry it',src=='google.com' and v==[{'src':'google.com'}] and pl and pl[0].get('src')=='google.com' and pg.url.rstrip('/')==U.rstrip('/')+'/#sheet' or (src=='google.com' and v==[{'src':'google.com'}] and pl and pl[0].get('src')=='google.com'),(src,v,pl)); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U+'guides?utm_source=TikTok'); src=await pg.evaluate("sessionStorage.getItem('bd-src')"); await pg.click('.gl a'); await pg.wait_for_timeout(300); src2=await pg.evaluate("sessionStorage.getItem('bd-src')")
        await pg.click('.cta .btn'); await pg.wait_for_timeout(500)
        log('utm_source on a guide address is kept across guide pages and on to home',src=='tiktok' and src2=='tiktok' and of(ctx._ev,'Visit')==[{'src':'tiktok'}],(src,src2,of(ctx._ev,'Visit'))); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U+'about'); src=await pg.evaluate("sessionStorage.getItem('bd-src')")
        log('a guide page opened with no referrer records direct',src=='direct',src); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U,referer='https://www.reddit.com/r/mealprep'); await pg.click('footer a[href=guides]'); await pg.wait_for_timeout(300); src=await pg.evaluate("sessionStorage.getItem('bd-src')")
        log('home first (from Reddit), then a guide: the first source stays',src=='reddit.com' and of(ctx._ev,'Visit')==[{'src':'reddit.com'}],src); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U+GUIDE+'?utm_source=%3Cscript%3EX%20y',referer='https://evil.example/'); src=await pg.evaluate("sessionStorage.getItem('bd-src')")
        log('the source is cleaned the same way as on home (lower case, letters digits dot dash, 40 at most)',src=='scriptxy',src); await ctx.close()

        # ---------- 5. Vercel Web Analytics on every page, and the guide CTA as a Vercel event (sweep B, finding 6)
        ctx=await new(b,live=True); out={}
        for path in ['']+PAGES:
            n=len(ctx._seen); pg=await tab(ctx,LIVE+path); await pg.wait_for_timeout(250)
            out[path or 'home']=[await pg.locator('script[src="/_vercel/insights/script.js"]').count(),await pg.evaluate('window.__vercelRan||0'),ctx._seen[n:]]; await pg.close()
        log('on batch.recipes every page loads /_vercel/insights/script.js once and it can post to /_vercel/insights/view',all(v[0]==1 and v[1]==1 and v[2]==['insights/script.js','insights/view'] for v in out.values()),out)
        for slug in (GUIDE,'guides'):
            pg=await tab(ctx,LIVE+slug,referer='https://www.google.com/'); n=len(ctx._ev); a=pg.locator('[data-umami-event="Guide plan"]'); await a.click(); await pg.wait_for_timeout(500)
            gp=of(ctx._ev[n:],'Guide plan'); log(f'{slug}: the CTA sends Guide plan to Vercel with the guide and the source',gp==[{'guide':slug,'src':'google.com'}],ctx._ev[n:]); await pg.close()
        pg=await tab(ctx,LIVE+GUIDE); await pg.evaluate("document.addEventListener('click',e=>{if(e.target.closest('a'))e.preventDefault()})"); await pg.click('[data-umami-event="Guide plan"]')
        log('the CTA also gets the source as an Umami attribute (data-umami-event-src)',await pg.get_attribute('[data-umami-event="Guide plan"]','data-umami-event-src')=='google.com' or await pg.get_attribute('[data-umami-event="Guide plan"]','data-umami-event-src')=='direct',await pg.get_attribute('[data-umami-event="Guide plan"]','data-umami-event-src')); await ctx.close()
        ctx=await new(b); out={}
        for path in PAGES:
            pg=await tab(ctx,U+path); out[path]=[await pg.locator('script[src="/_vercel/insights/script.js"]').count(),len(ctx._seen)]; await pg.close()
        log('off batch.recipes (localhost) the Vercel script is not loaded, as on home',all(v==[0,0] for v in out.values()),out); await ctx.close()
        csp={}
        for path in ['index']+['guides',GUIDE,'about','privacy','404']:
            h=open(os.path.join(ROOT,path+'.html')).read(); m=re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"',h)
            csp[path]=bool(m) and "script-src 'self' 'sha256-" in m.group(1) and "connect-src 'self'" in m.group(1) and 'unsafe-inline' not in m.group(1).split('style-src')[0]
        log('every page carries a CSP whose inline scripts are allowed by hash (About, Privacy and 404 had none)',all(csp.values()),csp)

        # ---------- 6. fridge meals past 4 days are flagged on the home page (sweep D)
        seed=[FZ('new','Fresh soup',day(0),10,4),FZ('edge','Day four',day(4),0,3,10,4),FZ('old','Old curry',day(5),6,2,10,4),FZ('older','Week old',day(7),0,4,0,4),FZ('ate','All eaten',day(9),5,0,10,4),FZ('ice','Deep freeze',day(300),8,0,8,0)]
        ctx=await new(b,w=390,h=844,mob=True); await ctx.add_init_script("if(!localStorage.getItem('bd-freezer'))localStorage.setItem('bd-freezer',"+json.dumps(json.dumps(seed))+")")
        pg=await tab(ctx,U)
        ROWS="[...document.querySelectorAll('#fzList li')].map(li=>({t:li.querySelector('b').textContent,grp:li.parentNode.previousElementSibling?li.parentNode.previousElementSibling.textContent:'',old:(li.querySelector('.old')||{}).textContent||'',btn:li.querySelector('.ate').textContent,name:li.querySelector('.ate').getAttribute('aria-label'),s:li.querySelector('.open span').textContent}))"
        rows=await pg.evaluate(ROWS); fr={r['t']:r for r in rows if r['grp']=='In the fridge'}; fzr=[r for r in rows if r['grp']!='In the fridge']
        log('fridge: a row cooked 5 or 7 days ago says "Past 4 days. Toss it." and offers Remove',fr['Old curry']['old']=='Past 4 days. Toss it.' and fr['Old curry']['btn']=='Remove' and fr['Old curry']['name']=='Remove, Old curry' and fr['Week old']['old']=='Past 4 days. Toss it.' and fr['Week old']['btn']=='Remove',fr)
        log('fridge: today and day 4 are not flagged and keep Ate one',fr['Fresh soup']['old']=='' and fr['Fresh soup']['btn']=='Ate one' and fr['Day four']['old']=='' and fr['Day four']['btn']=='Ate one',fr)
        log('fridge: an old row with none left just says None left',fr['All eaten']['old']=='' and fr['All eaten']['btn']=='Remove' and fr['All eaten']['s'].startswith('None left'),fr['All eaten'])
        log('freezer rows are never flagged, however old',len(fzr)==5 and all(r['old']=='' for r in fzr) and any(r['t']=='Deep freeze' and r['btn']=='Ate one' for r in fzr),fzr)
        st=await pg.evaluate("(()=>{const o=document.querySelector('#fzList .old'),c=getComputedStyle(o),li=o.closest('li'),r=li.getBoundingClientRect();return {color:c.color,size:c.fontSize,weight:c.fontWeight,warn:getComputedStyle(document.documentElement).getPropertyValue('--warn').trim(),bg:getComputedStyle(li).backgroundColor,wide:document.documentElement.scrollWidth<=innerWidth,h:li.querySelector('.ate').getBoundingClientRect().height}})()")
        log('fridge flag: warning colour text, same small size, no coloured block, button 44 high, no sideways scroll',st['color']=='rgb(166, 82, 0)' and st['warn']=='#a65200' and st['size']=='13px' and st['bg']=='rgba(0, 0, 0, 0)' and st['wide'] and st['h']>=44,st)
        await pg.screenshot(path=os.path.join(HERE,'breakit','12-fridge.png'),full_page=True)
        await pg.tap('#fzList [data-frm="old"][data-p="r"]'); await pg.wait_for_timeout(300); f=await pg.evaluate(LS,'bd-freezer'); e=[x for x in f if x['id']=='old'][0]; t=(await pg.inner_text('#toast')).replace('\n',' ')
        log('fridge flag: Remove takes the fridge row away, keeps its freezer row, and can be undone',e.get('rx')==1 and e['fz']==6 and 'Removed Old curry' in t and 'Undo' in t,(e,t))
        await pg.tap('#toast button'); await pg.wait_for_timeout(300); e=[x for x in await pg.evaluate(LS,'bd-freezer') if x['id']=='old'][0]
        log('fridge flag: Undo brings it back, still flagged',not e.get('rx') and e['fr']==2 and (await pg.evaluate(ROWS))[2]['old']!='' or any(r['t']=='Old curry' and r['old'] for r in await pg.evaluate(ROWS)),e); await ctx.close()

        # ---------- 7. cook mode's last screen: "I cooked this" is the big button, Close the small one (sweep D)
        ctx=await new(b,w=390,h=844,mob=True); pg=await tab(ctx,U); await pg.tap('#sample'); await pg.wait_for_timeout(450); await pg.tap('#dCook'); await pg.wait_for_timeout(400)
        nxt=await pg.evaluate("(()=>{const r=document.getElementById('cNext').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        for _ in range(40):
            if await pg.inner_text('#cNext')=='Finish': break
            await pg.tap('#cNext'); await pg.wait_for_timeout(70)
        bx=await pg.locator('#cNext').bounding_box(); x,y=bx['x']+bx['width']/2,bx['y']+bx['height']/2
        await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(120); await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(250)   # a double tap on Finish
        s=await pg.evaluate("(()=>{const n=document.getElementById('cNext'),c=document.getElementById('cDone'),r=n.getBoundingClientRect(),g=(e)=>getComputedStyle(e).backgroundColor;return {next:n.textContent,rect:[r.left,r.top,r.width,r.height],nbg:g(n),close:c&&c.textContent,cbg:c&&g(c),ch:c&&c.getBoundingClientRect().height,h2:document.querySelector('#cBody h2').textContent,p:(document.querySelector('#cBody p')||{}).textContent,back:document.getElementById('cBack').disabled,fz:JSON.parse(localStorage.getItem('bd-freezer')||'[]').length,open:!document.getElementById('cook').classList.contains('hidden')}})()")
        log('last screen: the orange button where Next was says I cooked this',s['next']=='I cooked this' and s['rect']==nxt and s['nbg']=='rgb(194, 65, 12)',s)
        log('last screen: Close is the small grey one (44 high); Back still works',s['close']=='Close' and s['cbg']=='rgb(245, 245, 247)' and s['ch']>=44 and s['back'] is False,s)
        log('last screen: says Done once, keeps the label line',s['h2']=='Done.' and 'Label the bags' in (s['p'] or ''),(s['h2'],s['p']))
        log('last screen: a double tap on Finish does not log a cook or close',s['fz']==0 and s['open'],s)
        await pg.wait_for_timeout(500); await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(250)
        log('last screen: the right arrow key does not log a cook',len(await pg.evaluate(LS,'bd-freezer') or [])==0 and await pg.is_visible('#cook'))
        n=len(ctx._ev); await pg.tap('#cNext'); await pg.wait_for_timeout(300)
        s=await pg.evaluate("({next:document.getElementById('cNext').textContent,box:document.getElementById('cDidBox').innerText.trim(),done:!!document.getElementById('cDone'),foc:document.activeElement.id,fz:JSON.parse(localStorage.getItem('bd-freezer')||'[]').map(e=>[e.fz,e.fr]),toast:document.getElementById('toast').innerText.replace(/\\n/g,' ')})")
        log('I cooked this: one tap logs it, the button becomes Close, the screen says In My freezer, Undo is offered',s=={'next':'Close','box':'In My freezer','done':False,'foc':'cNext','fz':[[10,4]],'toast':'Added to My freezer Undo'} and names(ctx._ev[n:])==['Cooked'],(s,names(ctx._ev[n:])))
        await pg.tap('#toast button'); await pg.wait_for_timeout(300)
        s=await pg.evaluate("({next:document.getElementById('cNext').textContent,fz:JSON.parse(localStorage.getItem('bd-freezer')||'[]').length,done:!!document.getElementById('cDone')})")
        log('I cooked this: Undo takes it out again and the big button is back',s=={'next':'I cooked this','fz':0,'done':True},s)
        await pg.wait_for_timeout(500); await pg.tap('#cNext'); await pg.wait_for_timeout(700); await pg.tap('#cBack'); await pg.wait_for_timeout(200); await pg.tap('#cNext'); await pg.wait_for_timeout(700); await pg.tap('#cNext'); await pg.wait_for_timeout(300)
        s=await pg.evaluate("({next:document.getElementById('cNext').textContent,box:document.getElementById('cDidBox').innerText.replace(/\\n/g,' '),foc:document.activeElement.id,fz:JSON.parse(localStorage.getItem('bd-freezer')||'[]').length,again:getComputedStyle(document.getElementById('cDidAgain')).backgroundColor})")
        log('a second time the same day asks first; the big button is then Close and Add again is grey (one orange button)',s['next']=='Close' and 'Already added for' in s['box'] and 'Add again' in s['box'] and s['foc']=='cDidAgain' and s['fz']==1 and s['again']=='rgb(245, 245, 247)',s)
        await pg.wait_for_timeout(500); await pg.tap('#cNext'); await pg.wait_for_timeout(500)
        log('Close (big, after the question) closes cook mode and adds nothing',not await pg.is_visible('#cook') and len(await pg.evaluate(LS,'bd-freezer'))==1)
        await pg.evaluate("localStorage.removeItem('bd-freezer')"); await to_end(pg); await pg.tap('#cDone'); await pg.wait_for_timeout(500)
        log('the small Close closes cook mode without logging',not await pg.is_visible('#cook') and not await pg.evaluate(LS,'bd-freezer'))
        await to_end(pg); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        log('keyboard: Enter on the focused big button logs the cook',len(await pg.evaluate(LS,'bd-freezer') or [])==1 and await pg.inner_text('#cNext')=='Close')
        await pg.wait_for_timeout(500); await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(500)
        log('once logged, the right arrow closes as before',not await pg.is_visible('#cook'))
        await pg.tap('#mode [data-m=scale]'); await pg.wait_for_timeout(300); await to_end(pg)
        s=await pg.evaluate("({next:document.getElementById('cNext').textContent,box:!!document.getElementById('cDidBox'),h2:document.querySelector('#cBody h2').textContent,p:!!document.querySelector('#cBody p')})")
        log('Just scale: the last screen is Done with one Close, no freezer button and no label line',s=={'next':'Close','box':False,'h2':'Done.','p':False},s); await ctx.close()

        # ---------- 8. guides, Guides, About, Privacy and 404 follow the theme chosen on home (sweep D)
        for scheme,pick,bg in [('light','dark','rgb(0, 0, 0)'),('dark','light','rgb(255, 255, 255)')]:
            ctx=await new(b,scheme=scheme); pg=await tab(ctx,U); await pg.click('#theme'); await pg.wait_for_timeout(200); out={}
            for path in PAGES:
                await pg.goto(U+path); await pg.wait_for_timeout(200)
                out[path]=await pg.evaluate("[getComputedStyle(document.body).backgroundColor,window.__themeAtDcl,getComputedStyle(document.querySelector('.mark b')).color]")
            acc='rgb(255, 122, 61)' if pick=='dark' else 'rgb(194, 65, 12)'
            log(f'OS {scheme}, {pick} chosen on home: every other page is {pick}, set before the page is drawn',await pg.evaluate("localStorage.getItem('bd-theme')")==pick and all(v==[bg,pick,acc] for v in out.values()),out); await ctx.close()
        for scheme,bg in [('light','rgb(255, 255, 255)'),('dark','rgb(0, 0, 0)')]:
            ctx=await new(b,scheme=scheme); out={}
            for path in PAGES:
                pg=await tab(ctx,U+path); out[path]=await pg.evaluate("[getComputedStyle(document.body).backgroundColor,window.__themeAtDcl]"); await pg.close()
            log(f'no theme chosen, OS {scheme}: the pages follow the OS',all(v==[bg,''] for v in out.values()),out); await ctx.close()
        ctx=await new(b,scheme='light'); await ctx.add_init_script("try{localStorage.setItem('bd-theme','\"><b>x')}catch(e){}"); pg=await tab(ctx,U+'about')
        log('a junk saved theme is ignored',await pg.evaluate("[getComputedStyle(document.body).backgroundColor,document.documentElement.dataset.theme||'']")==['rgb(255, 255, 255)','']); await ctx.close()
        pos={}
        for path in ['guides',GUIDE,'about','privacy','404']:
            h=open(os.path.join(ROOT,path+'.html')).read(); pos[path]=0<h.find("localStorage.getItem('bd-theme')")<h.find('<style>')<h.find('<body')
        log('the theme script sits in the head, before the styles',all(pos.values()),pos)

        # ---------- 9. link previews say what the tool does (sweep D; sweep E, L-5)
        im=Image.open(os.path.join(ROOT,'og.png')).convert('RGB'); bb=ImageChops.difference(im,Image.new('RGB',im.size,(255,255,255))).getbbox(); m=[bb[0],im.size[0]-bb[2],bb[1],im.size[1]-bb[3]]
        log('og.png is 1200 x 630 and its content is centred (left/right and top/bottom within 1 px)',im.size==(1200,630) and abs(m[0]-m[1])<=1 and abs(m[2]-m[3])<=1 and min(m)>=48,m)
        og=open(os.path.join(HERE,'og.html')).read()
        log('og.html carries the line that says what it does','Recipe screenshot to grocery list' in og and 'cook order and freezer plan' in og and 'Cook once.' in og and '—' not in og)
        ctx=await new(b); out={}
        for path,title in [('about','About · batch.recipes'),('privacy','Privacy · batch.recipes')]:
            pg=await tab(ctx,U+path)
            out[path]=await pg.evaluate("""({og:Object.fromEntries([...document.querySelectorAll('meta[property^="og:"]')].map(m=>[m.getAttribute('property'),m.content])),tw:(document.querySelector('meta[name="twitter:card"]')||{}).content,c:[...document.querySelectorAll('link[rel=canonical]')].map(l=>l.href),d:document.querySelector('meta[name=description]').content})""")
            o=out[path]; out[path]=o['og'].get('og:title')==title and o['og'].get('og:image')==LIVE+'og.png' and o['og'].get('og:url')==LIVE+path and o['og'].get('og:description')==o['d'] and o['og'].get('og:site_name')=='batch.recipes' and o['tw']=='summary_large_image' and o['c']==[LIVE+path]
            await pg.close()
        log('About and Privacy have Open Graph tags, a large Twitter card and one canonical',all(out.values()),out)
        pg=await tab(ctx,U); await sample(pg); await pg.click('#dShare'); await pg.click('#menu [data-pic]'); await pic_ready(pg)
        for size in ('story','pin'):
            if size=='pin': await pg.click('#picSize [data-s=pin]'); await pg.wait_for_timeout(200); await pic_ready(pg)
            geo=json.loads(await pg.get_attribute('#picImg','data-geo'))
            raw=await pg.evaluate("(()=>{const i=document.getElementById('picImg'),c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);return c.toDataURL('image/png').split(',')[1]})()"); im=Image.open(io.BytesIO(base64.b64decode(raw))).convert('RGB')
            c=geo['card']; band=im.crop((c[0]+4,geo['say'][0]-2,c[0]+c[2]-4,geo['say'][1]+10)); bb=ImageChops.difference(band,Image.new('RGB',band.size,(255,255,255))).getbbox()
            l=bb[0]; r=band.size[0]-bb[2]
            log(f'share picture ({size}): a line under the word mark says what batch.recipes does, centred, inside the card',bool(bb) and abs(l-r)<=2 and l>=geo['side']-c[0]-4 and geo['say'][0]>geo['word'][1] and geo['say'][1]<=c[1]+c[3]-40 and geo['free'][1]<geo['word'][0] and geo['bottom']<=geo['free'][1],{'l':l,'r':r,'say':geo['say'],'word':geo['word'],'free':geo['free'],'bottom':geo['bottom']})
            if size=='story': im.save(os.path.join(HERE,'breakit','12-sharepic.png'))
        await ctx.close()
        t=open(os.path.join(HERE,'template.html')).read()
        log('the share picture line is plain words','const PIC_SAY=\'Batch plan from a recipe\'' in t)

        # ---------- 10. Privacy and About say what is true (sweep E, L-1 L-2; sweep B, 7 9 10; sweep D, 37)
        ctx=await new(b); pg=await tab(ctx,U+'privacy'); pv=await pg.inner_text('main'); pg2=await tab(ctx,U+'about'); ab=await pg2.inner_text('main'); await ctx.close()
        log('privacy: the reader keeps the IP address in memory until it restarts (not "up to a day")','in memory until it restarts' in pv and 'up to a day' not in pv and 'IP address and the times of your recent reads' in pv)
        log('privacy: Back up lists My freezer',re.search(r'Back up makes a file on your device with your batches, My freezer, your theme and your staples',pv) is not None)
        log('privacy: Amazon sets its own cookies after a click, and the Associates sentence is word for word','Amazon sets its own cookies to track the commission' in pv and 'As an Amazon Associate I earn from qualifying purchases.' in pv)
        log('privacy: names Hugging Face Inference Providers and the third-party provider, and that our reader saves nothing','Hugging Face Inference Providers' in pv and "third-party provider" in pv and "Our reader doesn't save the screenshots or the text" in pv)
        log('privacy: no promise of a privacy button or a Do not sell option on the site; consent comes through Google\'s messages where required','privacy button' not in pv and 'Do not sell or share my personal information' not in pv and "Google's consent message" in pv and "Google's privacy message" in pv and 'Global Privacy Control' in pv)
        log('privacy: the AdSense vendor and cookie wording is unchanged','Third-party vendors, including Google, use cookies to serve ads based on your earlier visits to this website or other websites.' in pv and "Google's advertising cookies let Google and its partners serve ads to you based on your visits to this site and other sites." in pv and 'aboutads.info' in pv)
        log('privacy and About agree on the fallback: read on your device','read on your device instead' in pv and 'read on your device instead' in ab and 'your phone reads them' not in ab and 'read in your browser instead' not in pv)
        log('privacy: dated 15 November 2026','Last updated 15 November 2026' in pv)

        # ---------- 11. sitemap lastmod is each page's own last change (sweep E, L-3)
        tmp=tempfile.mkdtemp(prefix='bd12-')
        try:
            for f in ['template.html','build.py','engine.js','guides.js','qr.js','reader.txt']: shutil.copy(os.path.join(HERE,f),tmp)
            shutil.copytree(os.path.join(HERE,'pages'),os.path.join(tmp,'pages')); os.mkdir(os.path.join(tmp,'site'))
            def build(day_):
                r=subprocess.run([sys.executable,'build.py'],cwd=tmp,env=dict(os.environ,BD_TODAY=day_),capture_output=True,text=True)
                if r.returncode: raise RuntimeError(r.stderr[-400:])
                return dict(re.findall(r'<loc>https://batch\.recipes/([^<]*)</loc><lastmod>([^<]+)</lastmod>',open(os.path.join(tmp,'site','sitemap.xml')).read()))
            a=build('2030-01-01'); b2=build('2030-01-02')
            open(os.path.join(tmp,'pages','about.body'),'a').write('<p>One more line.</p>\n'); c3=build('2030-01-03')
            log('sitemap: a first build dates every page that day (14 addresses)',len(a)==14 and set(a.values())=={'2030-01-01'},a)
            log('sitemap: building again with nothing changed keeps every date',b2==a,b2)
            log('sitemap: a change to About moves only About',c3.get('about')=='2030-01-03' and all(v=='2030-01-01' for k,v in c3.items() if k!='about'),c3)
            lm=json.load(open(os.path.join(tmp,'lastmod.json')))
            log('lastmod.json holds a hash and a date for each of the 14 pages',len(lm)==14 and all(re.fullmatch(r'[0-9a-f]{64}',v['hash']) and re.fullmatch(r'\d{4}-\d\d-\d\d',v['date']) for v in lm.values()),list(lm)[:3])
        except Exception as e: log('sitemap: build in a scratch folder',False,e)
        finally: shutil.rmtree(tmp,ignore_errors=True)
        sm=dict(re.findall(r'<loc>https://batch\.recipes/([^<]*)</loc><lastmod>([^<]+)</lastmod>',open(os.path.join(ROOT,'sitemap.xml')).read()))
        log('sitemap in site/: 14 addresses, each with a real date',len(sm)==14 and all(re.fullmatch(r'\d{4}-\d\d-\d\d',v) for v in sm.values()),sm)

        # ---------- 12. small things from sweep D
        ORANGE="[...document.querySelectorAll('button,a,[role=button]')].filter(e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return r.width>0&&r.height>0&&r.top<innerHeight&&c.visibility!=='hidden'&&(c.backgroundColor==='rgb(194, 65, 12)'||c.backgroundColor==='rgb(255, 122, 61)')}).map(e=>e.id||e.textContent.trim())"
        for w,h,mob in [(390,844,True),(1440,900,False)]:
            ctx=await new(b,w=w,h=h,mob=mob); pg=await tab(ctx,U)
            o=await pg.evaluate(ORANGE); smp=await pg.is_visible('#sample'); cls=await pg.get_attribute('#sample','class')
            log(f'first view at {w}: one filled orange button (Choose screenshots); See a sample plan is grey; no tour offer',o==['choose'] and smp and cls=='pillb soft' and await pg.inner_text('#sample')=='See a sample plan' and await pg.locator('#tourOffer').count()==0,(o,smp,cls))
            g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),y=q('#sample'),c=q('#choose');return {mid:Math.round((y.left+y.right)/2-(c.left+c.right)/2),yes:y.height,hero:getComputedStyle(document.querySelector('.hero')).paddingTop,ad:getComputedStyle(document.querySelector('.adlab')).marginBottom,adc:getComputedStyle(document.querySelector('.adlab')).color,ink2:getComputedStyle(document.querySelector('.sub')).color}})()")
            log(f'sample button at {w}: centred under Choose screenshots, 44 high',g['mid']==0 and g['yes']>=43.9,g)
            log(f'spacing at {w}: hero top padding {"64" if not mob else "40"} and the Advertisement label 8 under, in the secondary text colour',g['hero']==('40px' if mob else '64px') and g['ad']=='8px' and g['adc']==g['ink2'],g)
            if mob:
                await pg.set_viewport_size({'width':320,'height':700}); await pg.wait_for_timeout(200)
                g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),y=q('#sample'),c=q('#choose');return {b:Math.round((y.left+y.right)/2-(c.left+c.right)/2),wide:document.documentElement.scrollWidth<=innerWidth}})()")
                log('sample button at 320: centred, no sideways scroll',abs(g['b'])<=1 and g['wide'],g); await pg.set_viewport_size({'width':w,'height':h})
            await paste(pg,SOUP) if not mob else (await pg.tap('#pasteToggle'), await pg.fill('#paste',SOUP), await pg.tap('#usePaste'), await pg.wait_for_timeout(450))
            pad=await pg.evaluate("(()=>{const c=document.getElementById('ctl'),r=c.getBoundingClientRect(),seg=c.querySelector('.seg').getBoundingClientRect(),st=[...c.querySelectorAll('.step')].pop().getBoundingClientRect(),o=document.querySelector('#sheet .card'),oc=getComputedStyle(o),cc=getComputedStyle(c);return {top:Math.round(seg.top-r.top),left:Math.round(seg.left-r.left),right:Math.round(r.right-seg.right),bottom:Math.round(r.bottom-st.bottom),css:cc.padding,other:oc.padding}})()")
            log(f'controls card at {w}: the same padding on all four sides as the other cards',pad['css']==pad['other'] and pad['top']==pad['left']==pad['right']==pad['bottom'],pad)
            fresh_=await pg.evaluate("[...document.querySelectorAll('[data-panel=store] .split h4')].map(h=>h.textContent)")
            log(f'Store tab at {w}: no "Fresh at serving" box when there is nothing fresh',fresh_==['Freezer','Fridge'],fresh_)
            if not mob:
                await panel(pg,'store'); cols=await pg.evaluate("[...document.querySelectorAll('[data-panel=store] .split>div')].map(d=>Math.round(d.getBoundingClientRect().width))")
                log('Store tab on desktop: the two boxes share the row evenly',len(cols)==2 and abs(cols[0]-cols[1])<=1,cols); await panel(pg,'shop')
            await (pg.tap if mob else pg.click)('#newRec'); await pg.wait_for_timeout(300)
            x=await pg.evaluate("(()=>{const c=document.getElementById('mine').getBoundingClientRect(),t=document.querySelector('#savedList .open b').getBoundingClientRect(),g=document.querySelector('#savedList .rm svg').getBoundingClientRect(),b=document.querySelector('#savedList .rm').getBoundingClientRect();return {l:Math.round(t.left-c.left),r:Math.round(c.right-g.right),tap:[b.width,b.height],inCard:b.right<=c.right}})()")
            log(f'My batches at {w}: the X is as far from the right edge as the title is from the left; still a 44 px target inside the card',x['l']==x['r'] and x['tap']==[44,44] and x['inCard'],x)
            await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg)
        log('Store tab: the sample still shows Fresh at serving',await pg.evaluate("[...document.querySelectorAll('[data-panel=store] .split h4')].map(h=>h.textContent)")==['Freezer','Fridge','Fresh at serving'])
        await pg.click('#newRec'); await pg.wait_for_timeout(300); await paste(pg,'2 cups rice\n1 lb chicken thighs\n1. Cook the rice.')
        ttl=[await pg.inner_text('#sTitle'),(await pg.evaluate(LS,'bd-batches'))[0]['title']]
        log('a recipe with no title is called Recipe, not Your recipe',ttl==['Recipe','Recipe'],ttl)
        await pg.click('#newRec'); await pg.wait_for_timeout(300); await paste(pg,CHILI); row0=await pg.inner_text('#savedList li:first-child .open span')
        await panel(pg,'store'); await pg.fill('#ckDate',day(3)); await pg.wait_for_timeout(200); await pg.click('#didGo'); await pg.wait_for_timeout(300); await pg.click('#newRec'); await pg.wait_for_timeout(300)
        d3=datetime.date.today()-datetime.timedelta(days=3); want=f"14 meals · Cooked {d3.strftime('%b')} {d3.day}"
        row1=await pg.inner_text('#savedList li:first-child .open span'); rest=await pg.eval_on_selector_all('#savedList li .open span','e=>e.map(x=>x.textContent)')
        log('My batches: a batch that was cooked shows its cooked date; the others keep the saved date',not 'Cooked' in row0 and row1==want and all('Cooked' not in r for r in rest[1:]),(row0,row1,rest))
        await pg.click('#toast button') if await pg.locator('#toast.on button').count() else None
        await pg.tap('#fzList [data-ate]') if False else None
        await ctx.close()
        for w in (390,1440):
            ctx=await new(b,w=w,h=900,mob=w<500); pg=await tab(ctx,U+GUIDE)
            pad=await pg.evaluate("getComputedStyle(document.querySelector('.card')).padding"); wide=await pg.evaluate('document.documentElement.scrollWidth<=innerWidth')
            log(f'guide calculator card at {w}: padding {"32" if w>720 else "20"}, no sideways scroll',pad==('32px' if w>720 else '20px') and wide,pad); await ctx.close()
        g=open(os.path.join(ROOT,'guides.html')).read(); f4=open(os.path.join(ROOT,'404.html')).read()
        log('Guides index: the line under the heading is gone; the description for search stays','each with a calculator.</p>' not in g and 'name="description" content="Batch cooking questions, each with a calculator' in g)
        log('404: one plain line','It may have been mistyped' not in f4 and "That address isn't on batch.recipes." in f4.replace('&#x27;',"'"))

        # the engine's display names: label when there is one, name for keys
        WRAP="""(()=>{let be;Object.defineProperty(window,'BatchEngine',{configurable:true,get(){return be},set(v){be=v;const bd=v.batchDay,sa=v.scaleAll;
          v.batchDay=function(){const p=bd.apply(this,arguments);p.items.forEach(i=>{i.label='L:'+i.name});p.grocery.forEach(g=>{g.label='L:'+g.name});p.notes=(p.notes||[]).concat(['A very big cook. Split it over two days.']);p.pots=p.pots.concat(['Sheet pans: 2 half sheets']);return p};
          v.scaleAll=function(){const s=sa.apply(this,arguments);s.items.forEach(i=>{i.label='L:'+i.name});return s}}})})()"""
        ctx=await new(b); await ctx.add_init_script(WRAP); await ctx.grant_permissions(['clipboard-read','clipboard-write'],origin=U.rstrip('/')); pg=await tab(ctx,U); await paste(pg,CHILI)
        rows=await pg.evaluate("[...document.querySelectorAll('[data-panel=shop] .checks:not(.pan) .tx')].map(e=>e.innerText.trim())"); keys=await pg.evaluate("[...document.querySelectorAll('[data-panel=shop] .checks:not(.pan) input')].map(e=>e.dataset.k)")
        log('grocery list shows the engine\'s label; ticks are still keyed by name',len(rows)>3 and all(' L:' in r or r.startswith('L:') for r in rows) and not any(k.startswith('L:') for k in keys),(rows[:3],keys[:3]))
        await pg.locator('[data-panel=shop] .checks:not(.pan) input').nth(0).check(); k=(await pg.evaluate(LS,'bd-batches'))[0]['k']
        log('a tick is saved under the item\'s name',len(k)==1 and not k[0].startswith('L:'),k)
        await pg.click('[data-copy]'); await pg.wait_for_timeout(200); clip=await pg.evaluate('navigator.clipboard.readText()')
        log('Copy puts the labels on the clipboard',clip.count('L:')==len(rows),clip[:120])
        await pg.click('#stEdit'); nm=await pg.get_attribute('[data-panel=shop] .stp','aria-label'); await pg.locator('[data-panel=shop] .checks:not(.pan) .stp').first.click(); await pg.wait_for_timeout(1000); st=await pg.evaluate(LS,'bd-staples')
        log('Always have: named by the label for a screen reader, remembered by the name',nm.startswith('Always have L:') and len(st)==1 and not st[0].startswith('l:'),(nm,st))
        notes=await pg.evaluate("[...document.querySelectorAll('#sheet .note')].map(n=>[n.textContent,n.getBoundingClientRect().height>0])")
        log('Batch day shows the plan\'s notes above the tabs',notes==[['A very big cook. Split it over two days.',True]],notes)
        await panel(pg,'cook'); pots=await pg.evaluate("[...document.querySelectorAll('[data-panel=cook] .plain li')].map(n=>n.textContent)")
        log('new pot lines (Sheet pans) show under Pots and pans',pots[-1]=='Sheet pans: 2 half sheets',pots)
        await panel(pg,'recipe'); tbl=await pg.evaluate("[...document.querySelectorAll('[data-panel=recipe] .tbl tr td:nth-child(2)')].map(e=>e.firstChild.textContent)")
        log('Recipe tab shows labels',len(tbl)>3 and all(x.startswith('L:') for x in tbl),tbl[:3])
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300); tbl=await pg.evaluate("[...document.querySelectorAll('#sheet .tbl tr td:nth-child(2)')].map(e=>e.firstChild.textContent)")
        log('Just scale shows labels',len(tbl)>3 and all(x.startswith('L:') for x in tbl),tbl[:3]); await ctx.close()

        # ---------- 13. sweep C: focus clear of the dock, tap targets, headings, toast, old Safari links
        CLEAR="(()=>{const a=document.activeElement,r=a.getBoundingClientRect(),d=document.getElementById('dock').getBoundingClientRect(),t=document.getElementById('tabs').getBoundingClientRect();return {id:a.id||a.dataset.k||a.className,ok:r.bottom<=d.top+0.5&&r.top>=t.bottom-0.5&&r.top>=52,b:Math.round(r.bottom),dock:Math.round(d.top),top:Math.round(r.top),tabs:Math.round(t.bottom)}})()"
        for w,h in [(390,844),(820,1180),(1440,900)]:
            ctx=await new(b,w=w,h=h); pg=await tab(ctx,U); await sample(pg); await pg.focus('#tabs [data-tab=recipe]'); bad=[]; n=0
            for _ in range(40):
                await pg.keyboard.press('Tab'); await pg.wait_for_timeout(40); c=await pg.evaluate(CLEAR); n+=1
                if c['id'] in ('dShare','dCook'): break
                if not c['ok']: bad.append(c)
            log(f'keyboard at {w}x{h}: every focused control on the Shop tab is clear of the dock and the tabs ({n} stops)',not bad and n>10,bad[:3])
            await panel(pg,'store'); await pg.focus('#tabs [data-tab=recipe]'); bad=[]; n=0
            for _ in range(20):
                await pg.keyboard.press('Tab'); await pg.wait_for_timeout(40); c=await pg.evaluate(CLEAR); n+=1
                if c['id'] in ('dShare','dCook'): break
                if not c['ok']: bad.append(c)
            log(f'keyboard at {w}x{h}: the same on the Store tab (Print labels, Save as image, I cooked this)',not bad and n>=5,bad[:3])
            await pg.keyboard.press('Shift+Tab'); await pg.keyboard.press('Shift+Tab'); await pg.wait_for_timeout(60)
            for _ in range(30): await pg.keyboard.press('Shift+Tab')
            await pg.wait_for_timeout(100); c=await pg.evaluate("(()=>{const a=document.activeElement,r=a.getBoundingClientRect();return [a.id,r.top>=52]})()")
            log(f'keyboard at {w}x{h}: tabbing back up, focus is not under the top bar',c[1],c); await ctx.close()
        ctx=await new(b,w=390,h=844,mob=True); pg=await tab(ctx,U)
        SZ="(sel)=>[...document.querySelectorAll(sel)].filter(e=>e.getBoundingClientRect().width>0).map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})"
        sz={'theme':await pg.evaluate(SZ,'#theme'),'sample':await pg.evaluate(SZ,'#sample')}
        sw=await pg.evaluate("(()=>{const b=document.getElementById('theme'),k=b.querySelector('i').getBoundingClientRect(),r=b.getBoundingClientRect(),t=getComputedStyle(b,'::before');return {track:[t.width,t.height],knobMid:Math.round(k.top+k.height/2-r.top),bar:document.querySelector('.bar').getBoundingClientRect().height}})()")
        await pg.tap('#sample'); await pg.wait_for_timeout(450); sz['mode']=await pg.evaluate(SZ,'#mode button'); sz['tabs']=await pg.evaluate(SZ,'#tabs button')
        await pg.tap('#dShare'); await pg.tap('#menu [data-pic]'); await pic_ready(pg); sz['pic']=await pg.evaluate(SZ,'#picSize button'); alt=await pg.get_attribute('#picImg','alt')
        log('tap targets: theme switch, See a sample plan, Batch day / Just scale, the four tabs and Story / Pinterest are all at least 44 x 44',all(x[0]>=44 and x[1]>=44 for v in sz.values() for x in v) and all(len(v)>0 for v in sz.values()),sz)
        log('theme switch: the button is 52 x 44, the track inside it is still 52 x 32, knob centred, bar still 52 high',sz['theme']==[[52,44]] and sw['track']==['52px','32px'] and sw['knobMid']==22 and sw['bar']==52,sw)
        log('share picture preview has alt text naming the dish and the count',alt=='Brothy chicken and rice, 14 meals',alt)
        await pg.tap('#picX'); await pg.wait_for_timeout(400)
        hd=await pg.evaluate("[...document.querySelectorAll('h1,h2,h3,h4,h5')].filter(h=>h.getBoundingClientRect().height>0&&!h.closest('.hidden')).map(h=>+(h.getAttribute('aria-level')||h.tagName[1]))")
        skips=[(a,b_) for a,b_ in zip(hd,hd[1:]) if b_>a+1]
        log('recipe page headings: one level 1 (the dish), then levels with no gaps',hd.count(1)==1 and hd[0]==1 and not skips and len(hd)>4,hd)
        nm=await pg.evaluate("(()=>{const h=document.querySelector('[data-panel=shop] h3');return [h.getAttribute('aria-labelledby'),document.getElementById(h.getAttribute('aria-labelledby')).textContent]})()")
        log('the grocery heading is named "Grocery list" alone, not with its buttons',nm==['glName','Grocery list'],nm)
        await pg.tap('#tabs [data-tab=store]'); await pg.wait_for_timeout(250); await pg.tap('#didGo'); await pg.wait_for_timeout(250); t1='on' in (await pg.get_attribute('#toast','class'))
        await pg.tap('#newRec'); await pg.wait_for_timeout(350); t2='on' in (await pg.get_attribute('#toast','class'))
        hd=await pg.evaluate("[...document.querySelectorAll('h1,h2,h3,h4,h5')].filter(h=>h.getBoundingClientRect().height>0&&!h.closest('.hidden')).map(h=>+(h.getAttribute('aria-level')||h.tagName[1]))")
        skips=[(a,b_) for a,b_ in zip(hd,hd[1:]) if b_>a+1]
        log('the "Added to My freezer" toast does not follow to the home page',t1 and not t2,(t1,t2))
        log('home headings with My freezer and My batches showing: one level 1, no gaps',hd.count(1)==1 and hd[0]==1 and not skips and len(hd)>=5,hd); await ctx.close()
        ctx=await new(b); pg=await tab(ctx,U); await sample(pg); await pg.focus('#newRec'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(350)
        f1=await pg.evaluate('document.activeElement.id'); await paste(pg,SOUP); await pg.focus('#newRec'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(350); f2=await pg.evaluate('document.activeElement.id')
        log('New recipe by keyboard: focus lands on Choose screenshots (or the paste box when that is showing), not the page body',[f1,f2]==['choose','paste'],[f1,f2]); await ctx.close()
        ctx=await new(b); await ctx.grant_permissions(['clipboard-read','clipboard-write'],origin=U.rstrip('/')); pg=await tab(ctx,U); await paste(pg,SOUP); await pg.click('#dShare'); await pg.click('#menu [data-link]'); await pg.wait_for_timeout(400); link=await pg.evaluate('navigator.clipboard.readText()'); await ctx.close()
        ctx=await new(b); await ctx.add_init_script("delete window.DecompressionStream;delete window.CompressionStream;"); pg=await tab(ctx,link); await pg.wait_for_timeout(400)
        t=await pg.inner_text('#toast'); home=await pg.is_visible('#choose')
        log('a compressed share link on a browser without DecompressionStream (Safari before 16.4): a clear message, home still usable','#r=z' in link and t=='This link needs a newer browser. Update your phone, or ask for the recipe text.' and home,(link[:40],t))
        await paste(pg,SOUP); await pg.context.grant_permissions(['clipboard-read','clipboard-write'],origin=U.rstrip('/')); await pg.click('#dShare'); await pg.click('#menu [data-link]'); await pg.wait_for_timeout(400); l2=await pg.evaluate('navigator.clipboard.readText()')
        pg2=await tab(ctx,l2); await pg2.wait_for_timeout(300)
        log('that browser makes plain links, and opens them','#r=p' in l2 and await pg2.inner_text('#sTitle')=='Lentil soup',l2[:40]); await ctx.close()
        ctx=await new(b,w=320,h=256); pg=await tab(ctx,U); await pg.click('#tourGo'); await pg.wait_for_timeout(300); await pg.click('#tNext'); await pg.wait_for_timeout(700); await pg.click('#tNext'); await pg.wait_for_timeout(900)
        g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),t=q('#tabs [data-tab=shop]'),d=q('#dock'),r=q('#tRing'),bb=q('#tBub');return {step:document.getElementById('tDots').getAttribute('aria-label'),tab:[Math.round(t.top),Math.round(t.bottom)],dock:Math.round(d.top),ring:[Math.round(r.top),Math.round(r.bottom)],bub:[Math.round(bb.top),Math.round(bb.bottom)],H:innerHeight}})()")
        log('tour step 3 in a 320 x 256 window (400% zoom): the Shop tab and its ring are above the dock, the bubble is on screen and off the tab',g['step']=='3 of 5' and g['tab'][1]<=g['dock'] and g['ring'][1]<=g['dock']+4 and g['tab'][0]>=52 and g['bub'][0]>=0 and g['bub'][1]<=g['H'] and (g['bub'][0]>=g['tab'][1] or g['bub'][1]<=g['tab'][0]),g)
        await pg.screenshot(path=os.path.join(HERE,'breakit','12-tour3-320x256.png')); await ctx.close()
        ctx=await new(b,w=390,h=844,mob=True); pg=await tab(ctx,U); await pg.tap('#sample'); await pg.wait_for_timeout(60)
        early=await pg.evaluate("document.getElementById('lblPrev').children.length"); await pg.wait_for_timeout(500); late=await pg.evaluate("document.getElementById('lblPrev').children.length")
        await pg.tap('.step [data-t=want][data-d=\"1\"]'); await pg.tap('#tabs [data-tab=store]'); now=await pg.evaluate("[document.getElementById('lblPrev').children.length,document.querySelector('#lblPrev .lq span').textContent]")
        log('the label preview is drawn after the page (not inside the tap), and at once when the Store tab opens',early==0 and late==1 and now==[1,'1 of 15'],(early,late,now)); await ctx.close()

        # ---------- 14. a savory bake is stored like a meal, never at room temperature (food safety; needs the engine's savoryBake)
        HAM='Ham and cheese muffins\nMakes 12\n2 cups flour\n1 cup diced ham\n1 cup shredded cheddar\n2 eggs\n1 cup milk\n1 tbsp baking powder\n1. Mix.\n2. Bake at 375 for 20 minutes.'
        COOKIE='Sugar cookies\nMakes 24\n2 cups flour\n1 cup sugar\n1 cup butter\n1 egg\n1 tsp baking powder\n1 tsp vanilla\n1. Mix.\n2. Bake at 350 for 10 minutes.'
        ctx=await new(b); pg=await tab(ctx,U); await paste(pg,HAM)
        st=await pg.evaluate("({mode:document.querySelector('#mode [aria-pressed=true]').dataset.m,alerts:document.getElementById('alerts').innerText,tabs:!!document.getElementById('tabs')})")
        await panel(pg,'store'); store=await pg.inner_text('[data-panel=store]'); allt=await pg.evaluate("document.getElementById('v-sheet').textContent"); did=await pg.locator('#didGo').count(); lbl=await pg.locator('#lblPrint').count()
        log('savory bake (ham and cheese muffins): opens in Batch day, no "set to Just scale" note',st['mode']=='batch' and st['tabs'] and 'Just scale' not in st['alerts'],st)
        log('savory bake: the Store tab says fridge within 2 hours and 4 days, with labels and I cooked this; no room temperature anywhere','within 2 hours' in store and 'eat within 4 days' in store and did==1 and lbl==1 and not re.search(r'room.temp|counter|airtight',allt,re.I),store[:300])
        await pg.click('#didGo'); await pg.wait_for_timeout(300); fz=await pg.evaluate(LS,'bd-freezer')
        log('savory bake: I cooked this puts fridge and freezer portions in My freezer',len(fz)==1 and fz[0]['fr']>0 and fz[0]['fz']+fz[0]['fr']==14,fz)
        await pg.click('#dCook'); await pg.wait_for_timeout(300); steps=[]
        for _ in range(30):
            steps.append(await pg.inner_text('#cBody'))
            if await pg.inner_text('#cNext') not in ('Next','Finish'): break
            await pg.click('#cNext'); await pg.wait_for_timeout(60)
        log('savory bake: no cook step or end screen mentions room temperature',not re.search(r'room.temp|counter',' '.join(steps),re.I),steps[-2:])
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400); await pg.click('#newRec'); await pg.wait_for_timeout(300); await paste(pg,COOKIE)
        st=await pg.evaluate("({mode:document.querySelector('#mode [aria-pressed=true]').dataset.m,alerts:document.getElementById('alerts').innerText})")
        log('sweet bake (sugar cookies): still set to Just scale, with the note',st['mode']=='scale' and 'Baking: set to Just scale.' in st['alerts'],st); await ctx.close()

        # no em dash in anything a visitor reads
        ctx=await new(b); bad={}
        for path in ['']+PAGES:
            pg=await tab(ctx,U+path); t=await pg.evaluate("document.body.innerText+' '+[...document.querySelectorAll('[aria-label],[placeholder],[content]')].map(e=>(e.getAttribute('aria-label')||'')+(e.getAttribute('placeholder')||'')+(e.getAttribute('content')||'')).join(' ')")
            if '—' in t: bad[path]=t[max(0,t.find('—')-30):t.find('—')+30]
            await pg.close()
        js=re.findall(r"'[^'\n]*—[^'\n]*'|\"[^\"\n]*—[^\"\n]*\"|`[^`]*—[^`]*`",open(os.path.join(HERE,'template.html')).read())
        log('no em dash in any page text, label or app string',not bad and not js,(bad,js[:2])); await ctx.close()

        await b.close()
    log('no console errors, page errors or CSP violations in any run',not ERRS,ERRS[:5])
    os.makedirs(os.path.join(HERE,'breakit'),exist_ok=True); json.dump(R,open(os.path.join(HERE,'breakit','r12.json'),'w'),indent=1)
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)-len(bad)} of {len(R)} ok'); sys.exit(1 if bad else 0)
asyncio.run(main())
