# Break test round 3 (report: breakit-batch.recipes-20261115.md). Every finding is run twice:
# on the build that was live when it was reported (OLD, a copy of site/ at 6049b1c) it must show the break,
# on this build (site/) it must pass. Nothing leaves the machine.
#   python3 breakit11.py            both builds
#   python3 breakit11.py new        this build only
# OLD defaults to /tmp/r3-base; set BD_OLD to another copy of the old site folder.
import asyncio, json, os, sys, io, time, threading, http.server, functools, datetime, re
from playwright.async_api import async_playwright
NEW_ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'site'); OLD_ROOT=os.environ.get('BD_OLD','/tmp/r3-base')
PN,PO=8771,8772; UN=f'http://127.0.0.1:{PN}/'; UO=f'http://127.0.0.1:{PO}/'
IOS='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
AND='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36'
DEV={'ios':dict(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,user_agent=IOS),
     'android':dict(viewport={'width':412,'height':915},is_mobile=True,has_touch=True,user_agent=AND),
     'desk':dict(viewport={'width':1440,'height':900})}
TODAY=datetime.date.today(); TISO=TODAY.isoformat()
R=[]
os.makedirs('breakit',exist_ok=True)
def log(n,ok,note=''):
    R.append((n,'ok' if ok else 'FAIL',str(note))); open('breakit/r11.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',n,'|',str(note)[:300],flush=True)

def serve(root,port):  # the way Vercel serves it: /about is about.html, anything unknown is 404.html with status 404
    class H(http.server.SimpleHTTPRequestHandler):
        def send_head(self):
            path=self.path.split('?')[0].split('#')[0]; p=self.translate_path(path)
            if not os.path.exists(p) and os.path.exists(p+'.html'): self.path=path+'.html'
            elif not os.path.exists(p) or (os.path.isdir(p) and not os.path.exists(os.path.join(p,'index.html'))):
                body=open(os.path.join(root,'404.html'),'rb').read(); self.send_response(404); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers()
                return io.BytesIO(body)
            return super().send_head()
        def log_message(self,*a): pass
    s=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(H,directory=root)); threading.Thread(target=s.serve_forever,daemon=True).start(); return s

INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective+' '+e.blockedURI));
window.__ev=[];window.umami={track:(n,d)=>window.__ev.push([n,d])};window.__printed=0;window.print=()=>{window.__printed++};
window.__shared=[];navigator.share=async(d)=>{window.__shared.push({text:d&&d.text,files:d&&d.files?[...d.files].map(f=>f.name):null})};navigator.canShare=()=>true;"""
ERRS=[]
async def ctxp(b,dev='ios',scheme='light',reduce=False):
    kw=dict(DEV[dev]); kw['color_scheme']=scheme
    if reduce: kw['reduced_motion']='reduce'
    ctx=await b.new_context(accept_downloads=True,**kw)
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/_vercel/**','**/pagead2.googlesyndication.com/**','**/*.doubleclick.net/**','**/cdn.jsdelivr.net/**','**/*amazon.com/**'): await ctx.route(pat,lambda r:r.abort())
    await ctx.add_init_script(INIT); return ctx
async def page(ctx,U,path='',wait=350):
    pg=await ctx.new_page()
    pg.on('pageerror',lambda e:ERRS.append((U,'pageerror: '+str(e)[:160])))
    pg.on('console',lambda m: ERRS.append((U,'console: '+m.text[:160])) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    await pg.goto(U+path); await pg.wait_for_timeout(wait); return pg
async def seeded(b,U,js,dev='ios',**kw):
    ctx=await ctxp(b,dev,**kw); pg=await page(ctx,U)
    await pg.evaluate("localStorage.setItem('bd-seen','1');localStorage.setItem('bd-tip','1');localStorage.setItem('bd-bkn','1');localStorage.setItem('bd-tour','skip');"+js)
    await pg.reload(); await pg.wait_for_timeout(350); return ctx,pg
async def sample(pg): await pg.click('#sample'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(600)
async def paste(pg,text):
    if not await pg.is_visible('#paste'): await pg.click('#pasteToggle')
    await pg.fill('#paste',text); await pg.click('#usePaste'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(500)
async def tab(pg,t): await pg.click(f'#tabs [data-tab={t}]'); await pg.wait_for_timeout(300)
async def mid(loc):
    await loc.scroll_into_view_if_needed(); await loc.page.wait_for_timeout(150); bb=await loc.bounding_box(); return bb['x']+bb['width']/2,bb['y']+bb['height']/2
async def hit(pg,dev,x,y):
    if dev=='desk': await pg.mouse.click(x,y)
    else: await pg.touchscreen.tap(x,y)
async def taps(pg,dev,x,y,n,gap):
    for _ in range(n): await hit(pg,dev,x,y); await pg.wait_for_timeout(gap)
LS="(k)=>{try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}}"
SOUPS="localStorage.setItem('bd-batches',JSON.stringify([0,1,2,3].map(i=>({id:'s'+i,title:'Soup '+i,text:'Soup '+i+'\\nServes 4\\n1 lb beef\\n1. Cook.',w:14,m:'batch',at:1763000000000-i,k:[]}))));"
STEWS="localStorage.setItem('bd-freezer',JSON.stringify([0,1,2].map(i=>({id:'e'+i,bid:null,title:'Stew '+i,date:'2026-11-0'+(i+1),fz:0,fr:0,fz0:3,fr0:0,at:1}))));"
CAP="localStorage.setItem('bd-batches',JSON.stringify([...Array(200)].map((_,i)=>({id:'c'+i,title:'Cap '+i,text:'Cap '+i+'\\nServes 4\\n1 lb beef\\n1. Cook.',w:14,m:'batch',at:1763000000000+i,k:[]}))));"
CHILI='Chili\nServes 4\n2 lb beef\n1 onion\n1 tsp salt\n2 cans beans\n1. Brown the beef 10 minutes.\n2. Simmer 30 minutes.\n3. Portion into containers.'

C=[]  # (id, what it shows, fn, old build must fail)
def check(id,what,old_fails=True):
    def d(f): C.append((id,what,f,old_fails)); return f
    return d

# ---------- B-01
@check('B-01a','second quick tap on a saved batch x removes one batch only (100/300/600 ms; iPhone, Android, desktop)')
async def _(b,U):
    bad=[]
    for dev in ('ios','android','desk'):
        for gap in (100,300,600):
            ctx,pg=await seeded(b,U,SOUPS,dev); x,y=await mid(pg.locator('#savedList .rm').first); await taps(pg,dev,x,y,2,gap)
            left=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).map(x=>x.title)")
            if left!=['Soup 1','Soup 2','Soup 3']: bad.append(f'{dev} {gap}ms left={left}')
            await ctx.close()
    return not bad,bad or 'one removed in all 9 runs'
@check('B-01b','two removals a second apart, then one Undo: both batches come back, in their old places')
async def _(b,U):
    out=[]
    for dev,kw in (('ios',{}),('desk',{}),('android',{'reduce':True}),('ios',{'scheme':'dark'})):
        ctx,pg=await seeded(b,U,SOUPS,dev,**kw); x,y=await mid(pg.locator('#savedList .rm').first); await taps(pg,dev,x,y,2,1100)
        mid_=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).map(x=>x.title)"); t=await pg.inner_text('#toast')
        await pg.click('#toast button'); await pg.wait_for_timeout(300)
        after=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).map(x=>x.title)"); rows=await pg.locator('#savedList .open').count()
        out.append((dev,mid_==['Soup 2','Soup 3'] and after==['Soup 0','Soup 1','Soup 2','Soup 3'] and rows==4 and 'Removed 2 batches' in t,f'{mid_} toast={t!r} after={after}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'both back, toast "Removed 2 batches"'
@check('B-01c','My freezer: double tap Remove on a None left row takes one row; Undo brings it back')
async def _(b,U):
    out=[]
    for dev in ('ios','android','desk'):
        ctx,pg=await seeded(b,U,STEWS,dev); x,y=await mid(pg.locator('#fzList [data-frm]').first); await taps(pg,dev,x,y,2,150); await pg.wait_for_timeout(200)
        left=await pg.evaluate("JSON.parse(localStorage.getItem('bd-freezer')).map(x=>x.title)")
        await pg.click('#toast button'); await pg.wait_for_timeout(300); back=await pg.evaluate("JSON.parse(localStorage.getItem('bd-freezer')).map(x=>x.title).sort()")
        out.append((dev,left==['Stew 1','Stew 2'] and back==['Stew 0','Stew 1','Stew 2'],f'left={left} back={back}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'one removed, Undo restores'
@check('B-01d','My freezer: two Removes a second apart, one Undo restores both')
async def _(b,U):
    ctx,pg=await seeded(b,U,STEWS,'ios'); x,y=await mid(pg.locator('#fzList [data-frm]').first); await taps(pg,'ios',x,y,2,1100)
    left=await pg.evaluate("JSON.parse(localStorage.getItem('bd-freezer')).map(x=>x.title)"); t=await pg.inner_text('#toast')
    await pg.click('#toast button'); await pg.wait_for_timeout(300); back=await pg.evaluate("JSON.parse(localStorage.getItem('bd-freezer')).map(x=>x.title).sort()"); await ctx.close()
    return left==['Stew 2'] and back==['Stew 0','Stew 1','Stew 2'],f'left={left} toast={t!r} back={back}'
@check('B-01e','Shop: double tap Always have marks one staple (80/200/400 ms; iPhone, Android, desktop)')
async def _(b,U):
    bad=[]
    for dev in ('ios','android','desk'):
        for gap in (80,200,400):
            ctx=await ctxp(b,dev); pg=await page(ctx,U); await sample(pg); await pg.click('#stEdit'); await pg.wait_for_timeout(300)
            x,y=await mid(pg.locator('#sheet .checks:not(.pan) .stp').nth(1)); await taps(pg,dev,x,y,2,gap); await pg.wait_for_timeout(300)
            st=await pg.evaluate(LS,'bd-staples')
            if not st or len(st)!=1: bad.append(f'{dev} {gap}ms {st}')
            await ctx.close()
    return not bad,bad or 'one staple in all 9 runs'
@check('B-01f','Shop: marking staples one at a time still works (a second apart), and un-marking')
async def _(b,U):
    ctx=await ctxp(b,'android'); pg=await page(ctx,U); await sample(pg); await pg.click('#stEdit'); await pg.wait_for_timeout(300)
    for _ in range(3): x,y=await mid(pg.locator('#sheet .checks:not(.pan) .stp').nth(1)); await hit(pg,'android',x,y); await pg.wait_for_timeout(950)
    n3=len(await pg.evaluate(LS,'bd-staples')); await pg.click('#ptog'); await pg.wait_for_timeout(950)
    x,y=await mid(pg.locator('#pan .stp').first); await hit(pg,'android',x,y); await pg.wait_for_timeout(400); n2=len(await pg.evaluate(LS,'bd-staples')); await ctx.close()
    return n3==3 and n2==2,f'{n3} then {n2}'
C[-1]=(C[-1][0],C[-1][1],C[-1][2],False)  # worked before too
@check('B-01g','My freezer: double tap Ate one on the last meal eats it and does not also remove the row')
async def _(b,U):
    out=[]
    for dev in ('ios','desk'):
        ctx,pg=await seeded(b,U,"localStorage.setItem('bd-freezer',JSON.stringify([{id:'e1',bid:null,title:'Stew',date:'2026-11-01',fz:1,fr:0,fz0:3,fr0:0,at:1},{id:'e2',bid:null,title:'Curry',date:'2026-11-02',fz:2,fr:0,fz0:2,fr0:0,at:1}]));",dev)
        x,y=await mid(pg.locator('#fzList [data-ate]').first); await taps(pg,dev,x,y,2,200); await pg.wait_for_timeout(200)
        f=await pg.evaluate(LS,'bd-freezer'); e=[v for v in f if v['id']=='e1']
        out.append((dev,len(f)==2 and e and e[0]['fz']==0 and not e[0].get('zx'),json.dumps(f)[:200])); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'row stays as None left'
@check('B-01h','double tap on a saved batch opens it and nothing else: no tick, no other tab, no changed number (the second tap is not passed to the recipe page)')
async def _(b,U):
    out=[]; ST="({view:!document.getElementById('v-sheet').classList.contains('hidden'),ticks:document.querySelectorAll('#sheet .checks input:checked').length,tab:(document.querySelector('#tabs [aria-pressed=true]')||{dataset:{}}).dataset.tab,mode:(document.querySelector('#mode [aria-pressed=true]')||{dataset:{}}).dataset.m,w:document.getElementById('want').value,y:document.getElementById('yield').value,menu:!document.getElementById('menu').classList.contains('hidden'),cook:!document.getElementById('cook').classList.contains('hidden'),title:document.getElementById('sTitle').textContent})"
    want={'view':True,'ticks':0,'tab':'shop','mode':'batch','w':'14','y':'4','menu':False,'cook':False}
    for dev in ('ios','android','desk'):
        for row in (0,1,2,3):
            for gap in (120,300):
                ctx,pg=await seeded(b,U,SOUPS,dev); x,y=await mid(pg.locator('#savedList .open').nth(row)); await taps(pg,dev,x,y,2,gap); await pg.wait_for_timeout(400)
                r=await pg.evaluate(ST); t_=r.pop('title')
                if r!=want or t_!=f'Soup {row}': out.append(f'{dev} row {row} {gap}ms: {t_} {r}')
                await ctx.close()
    return not out,out[:4] or '24 runs: opened, nothing else changed'
@check('B-01i','still two taps: the same button twice (Meals +, Ate one), and a tick then untick',False)
async def _(b,U):
    ctx=await ctxp(b,'ios'); pg=await page(ctx,U); await sample(pg)
    x,y=await mid(pg.locator('[data-t=want][data-d="1"]')); await taps(pg,'ios',x,y,3,120); w=await pg.input_value('#want')
    x,y=await mid(pg.locator('#sheet .checks label').first); await taps(pg,'ios',x,y,2,150); t2=await pg.locator('#sheet .checks input:checked').count()
    await hit(pg,'ios',x,y); await pg.wait_for_timeout(200); t3=await pg.locator('#sheet .checks input:checked').count(); await ctx.close()
    return w=='17' and t2==0 and t3==1,f'meals {w}, ticks {t2} then {t3}'

# ---------- B-02
@check('B-02a','I cooked this with My batches full: nothing is added, the "My batches is full" note shows with a way to make room')
async def _(b,U):
    out=[]
    for dev in ('desk','ios','android'):
        ctx,pg=await seeded(b,U,CAP,dev); await paste(pg,CHILI); await tab(pg,'store')
        await pg.click('#didGo'); await pg.wait_for_timeout(300)
        if await pg.is_visible('#didGo'): await pg.click('#didGo'); await pg.wait_for_timeout(300)
        f=await pg.evaluate(LS,'bd-freezer') or []; note=await pg.evaluate("(()=>{const e=document.getElementById('didFull');return e?e.innerText.replace(/\\s+/g,' ').trim():''})()")
        ok=len(f)==0 and note.startswith('My batches is full. Remove a few to save this one.') and 'My batches' in note[40:]
        if ok:
            await pg.click('#didMine'); await pg.wait_for_timeout(400); ok=await pg.evaluate("document.activeElement.id==='mineH'&&!document.getElementById('v-add').classList.contains('hidden')")
        out.append((dev,ok,f'entries={len(f)} note={note!r}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'no entry, note with My batches link, link lands on My batches'
@check('B-02b','after room is made the batch saves, the entry is tied to it, and a second tap the same day asks first')
async def _(b,U):
    ctx,pg=await seeded(b,U,CAP,'desk'); await paste(pg,CHILI); await tab(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(300)
    if await pg.locator('#didMine').count(): await pg.click('#didMine')
    else: await pg.click('#fullGo')
    await pg.wait_for_timeout(400); await pg.locator('#savedList .rm').first.click(); await pg.wait_for_timeout(300)
    await pg.go_back(); await pg.wait_for_timeout(500)
    gone=await pg.locator('#didFull').count()==0; await tab(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(300)
    f=await pg.evaluate(LS,'bd-freezer') or []; bs=await pg.evaluate(LS,'bd-batches'); chili=[x for x in bs if x['title']=='Chili']
    tied=[e for e in f if chili and e['bid']==chili[0]['id']]
    await pg.click('#didGo'); await pg.wait_for_timeout(300); ask=await pg.locator('#didAgain').count()==1; f2=await pg.evaluate(LS,'bd-freezer') or []
    await pg.goto(U); await pg.wait_for_timeout(400); await pg.click('#fzList [data-fo]'); await pg.wait_for_timeout(500); opens=await pg.is_visible('#v-sheet') and await pg.inner_text('#sTitle')=='Chili'; await ctx.close()
    return gone and len(chili)==1 and len(tied)==1 and len(f2)==len(f) and ask and opens,f'note gone={gone} saved={len(chili)} tied={len(tied)} of {len(f)}; second tap: entries={len(f2)} asks={ask}; opens from My freezer={opens}'
@check('B-02c','cook mode\'s "I cooked this" pill when full: same note, nothing added, My batches link leaves cook mode')
async def _(b,U):
    ctx,pg=await seeded(b,U,CAP,'android'); await paste(pg,CHILI); await pg.click('#dCook'); await pg.wait_for_timeout(300)
    for _ in range(12):
        if await pg.locator('#cDid,#cDone').count(): break
        await pg.click('#cNext'); await pg.wait_for_timeout(120)
    await pg.wait_for_timeout(600); await pg.click('#cDid' if await pg.locator('#cDid').count() else '#cNext'); await pg.wait_for_timeout(300); f=await pg.evaluate(LS,'bd-freezer') or []; txt=(await pg.inner_text('#cDidBox')).replace('\n',' ')  # since 15 Nov "I cooked this" is the big button (#cNext); the old build has the pill (#cDid)
    ok=len(f)==0 and 'My batches is full. Remove a few to save this one.' in txt and await pg.locator('#cDidMine').count()==1
    st=''
    await pg.wait_for_timeout(500)
    if ok: await pg.click('#cDidMine'); await pg.wait_for_timeout(700); st=await pg.evaluate("[document.activeElement.id,document.getElementById('cook').className,document.getElementById('v-add').className,location.hash]"); ok=st[0]=='mineH' and 'hidden' in st[1] and 'hidden' not in st[2]
    await ctx.close(); return ok,f'entries={len(f)} text={txt!r} after the link: {st}'

# ---------- L-01
async def tour_dbl(b,U,dev,step,mode):
    ctx=await ctxp(b,dev); pg=await page(ctx,U); await pg.click('#tourYes'); await pg.wait_for_timeout(600)
    for _ in range(step-1): await pg.click('#tNext'); await pg.wait_for_timeout(700)
    bb=await pg.locator('#tNext').bounding_box(); x,y=bb['x']+bb['width']/2,bb['y']+bb['height']/2
    if mode=='dbl': await pg.mouse.dblclick(x,y)
    else: await taps(pg,dev,x,y,2,mode)
    await pg.wait_for_timeout(500)
    r=await pg.evaluate("({on:!document.getElementById('tour').classList.contains('hidden'),at:document.getElementById('tDots').getAttribute('aria-label'),flag:localStorage.getItem('bd-tour'),ev:window.__ev.filter(e=>e[0]==='Tour'&&e[1].end).length})"); await ctx.close()
    steps=(step+1,) if mode=='dbl' or mode<350 else (step+1,step+2)  # past a third of a second a tap is a second Next, if Next is still under the finger (iPhone, step 1)
    return r['on'] and r['at'] in [f'{s} of 5' for s in steps] and not r['flag'] and r['ev']==0,r
@check('L-01a','double tap on the tour\'s Next never ends the tour, and within a third of a second it is one step (steps 1 and 3; dblclick, 100 to 1000 ms; iPhone, Android, desktop)')
async def _(b,U):
    bad=[];n=0
    for step in (1,3):
        for dev in ('ios','android','desk'):
            for mode in ('dbl',100,250,400,600,1000) if step==1 else ('dbl',150,600,1000):
                if mode=='dbl' and dev!='desk': continue
                n+=1; ok,r=await tour_dbl(b,U,dev,step,mode)
                if not ok: bad.append(f'step {step} {dev} {mode}: {r}')
    return not bad,bad[:6] or f'{n} runs, all on the next step'
@check('L-01b','double tap on Show me starts the tour and leaves it on step 1',False)
async def _(b,U):
    out=[]
    for dev in ('ios','desk'):
        for gap in (150,600):
            ctx=await ctxp(b,dev); pg=await page(ctx,U); x,y=await mid(pg.locator('#tourYes')); await taps(pg,dev,x,y,2,gap); await pg.wait_for_timeout(300)
            r=await pg.evaluate("({on:!document.getElementById('tour').classList.contains('hidden'),at:document.getElementById('tDots').getAttribute('aria-label'),flag:localStorage.getItem('bd-tour')})")
            out.append((dev,gap,r['on'] and r['at']=='1 of 5' and not r['flag'],r)); await ctx.close()
    return all(o[2] for o in out),[o for o in out if not o[2]] or 'tour on, step 1'
@check('L-01c','a real tap off the bubble still ends the tour at once (and Escape, Skip tour); the tap is not passed to the page',False)
async def _(b,U):
    out=[]
    for dev in ('ios','desk'):
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await pg.click('#tourYes'); await pg.wait_for_timeout(300)
        vp=pg.viewport_size; await hit(pg,dev,vp['width']/2,vp['height']-30); await pg.wait_for_timeout(300)
        r=await pg.evaluate("({on:!document.getElementById('tour').classList.contains('hidden'),flag:localStorage.getItem('bd-tour'),view:!document.getElementById('v-add').classList.contains('hidden')})")
        out.append((dev,'outside',(not r['on']) and r['flag']=='skip' and r['view'],r)); await ctx.close()
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await pg.click('#tourYes'); await pg.wait_for_timeout(650); await pg.click('#tNext'); await pg.wait_for_timeout(200); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        out.append((dev,'escape',await pg.evaluate("document.getElementById('tour').classList.contains('hidden')&&localStorage.getItem('bd-tour')==='skip'"),'')); await ctx.close()
    ctx=await ctxp(b,'android'); pg=await page(ctx,U); await pg.click('#tourYes'); await pg.wait_for_timeout(650)
    for _ in range(5): await pg.click('#tNext'); await pg.wait_for_timeout(650)
    out.append(('android','five Nexts finish it',await pg.evaluate("localStorage.getItem('bd-tour')")=='done','')); await ctx.close()
    return all(o[2] for o in out),[o for o in out if not o[2]] or 'outside, Escape and Done all work'

# ---------- L-02 / M-08
LBL="document.querySelector('#lblPrev .lbl').innerText.replace(/\\s+/g,' ')"
@check('L-02a','typing 11 14 26 in Cooked and leaving the box gives 2026, never 1926 (label, My freezer row)')
async def _(b,U):
    out=[]
    for box in ('#ckDate','#lblDate'):
        ctx=await ctxp(b,'desk'); pg=await page(ctx,U); await sample(pg); await tab(pg,'store'); await pg.focus(box)
        seen=[]
        for k in ('11','14','26'): await pg.keyboard.type(k); await pg.wait_for_timeout(100); seen.append(await pg.evaluate(LBL))
        await pg.keyboard.press('Tab'); await pg.wait_for_timeout(300)
        lbl=await pg.evaluate(LBL)  # Tab can stay inside the date box (its calendar button); the tap on the button is what leaves it
        await pg.click('#didGo'); await pg.wait_for_timeout(400); f=await pg.evaluate(LS,'bd-freezer') or [{}]; v=[await pg.input_value('#ckDate'),await pg.input_value('#lblDate')]
        await pg.goto(U); await pg.wait_for_timeout(400); row=(await pg.inner_text('#fzList')).replace('\n',' ') if await pg.locator('#fzList li').count() else ''
        ok=v==['2026-11-14','2026-11-14'] and 'Nov 14, 2026' in lbl and f[0].get('date')=='2026-11-14' and '1926' not in ' '.join(seen)+lbl+row and 'Nov 14' in row
        out.append((box,ok,f'value={v} label={lbl!r} entry={f[0].get("date")} row={row!r}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'both boxes 2026-11-14, label Nov 14, 2026'
@check('L-02b','a year far off (9999, 0026 set directly, 1990) is not taken: the last good date stays on the label and in My freezer; the box shows it again on leaving')
async def _(b,U):
    out=[]
    for dev in ('desk','android'):
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await sample(pg); await tab(pg,'store'); good=f'{TODAY.year}-01-05'; await pg.fill('#lblDate',good); await pg.wait_for_timeout(150); base=await pg.evaluate(LBL)
        for v in ('9999-12-31','0026-11-14','1990-06-01',f'{TODAY.year+2}-01-01',f'{TODAY.year-3}-12-31'):
            await pg.fill('#lblDate',v); await pg.wait_for_timeout(150); l1=await pg.evaluate(LBL)
            await pg.evaluate("document.activeElement.blur()"); await pg.wait_for_timeout(150); val=await pg.input_value('#lblDate'); ck=await pg.input_value('#ckDate')
            exp=good if v!='0026-11-14' else ('2026-11-14' if abs(2026-TODAY.year)<=1 or TODAY.year-2<=2026<=TODAY.year+1 else good)
            if not(l1==base and val==exp and ck==exp): out.append(f'{dev} {v}: label={l1!r} box={val} other={ck}')
            await pg.fill('#lblDate',good); await pg.wait_for_timeout(100)
        for v in (f'{TODAY.year-2}-01-01',f'{TODAY.year+1}-12-31'):  # the ends of the range are fine
            await pg.fill('#lblDate',v); await pg.wait_for_timeout(120)
            if await pg.input_value('#ckDate')!=v: out.append(f'{dev} {v} should be taken')
        await pg.fill('#lblDate','9999-12-31'); await pg.click('#didGo'); await pg.wait_for_timeout(400); f=await pg.evaluate(LS,'bd-freezer') or [{}]
        if f[0].get('date')!=f'{TODAY.year+1}-12-31': out.append(f'{dev} entry date {f[0].get("date")}')
        await ctx.close()
    return not out,out[:5] or 'refused, last good date kept'
@check('M-08','Cooked date cleared: the label and My freezer both use today, and the box shows today again')
async def _(b,U):
    out=[]
    for dev in ('desk','ios','android'):
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await sample(pg); await tab(pg,'store'); await pg.fill('#lblDate',f'{TODAY.year}-01-05'); await pg.wait_for_timeout(100)
        await pg.fill('#lblDate',''); await pg.wait_for_timeout(200); lbl=await pg.evaluate(LBL); us=TODAY.strftime('%b ')+str(TODAY.day)+', '+str(TODAY.year)
        await pg.click('#didGo'); await pg.wait_for_timeout(400); f=await pg.evaluate(LS,'bd-freezer') or [{}]; v=[await pg.input_value('#lblDate'),await pg.input_value('#ckDate')]
        out.append((dev,f'Cooked {us}' in lbl and f[0].get('date')==TISO and v==[TISO,TISO],f'label={lbl!r} entry={f[0].get("date")} boxes={v}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'label, entry and both boxes say today'

# ---------- L-03
GEO="(()=>{const q=(s)=>{const r=document.querySelector(s).getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)};const t=document.querySelector('#tabs [data-tab=shop]');return {bub:q('#tBub'),ring:q('#tRing'),next:q('#tNext'),tab:t?q('#tabs [data-tab=shop]'):null,dock:Math.round(document.getElementById('dock').getBoundingClientRect().top),bar:Math.round(document.querySelector('.bar').getBoundingClientRect().bottom),W:innerWidth,H:innerHeight,at:document.getElementById('tDots').getAttribute('aria-label')}})()"
def tour_ok(g,ring_on=None):
    bx,rg,nx=g['bub'],g['ring'],g['next']; lim=g['dock'] if g['at'] in('2 of 5','3 of 5') else g['H']
    ok=bx[0]>=0 and bx[2]<=g['W'] and bx[1]>=g['bar'] and bx[3]<=g['H'] and nx[1]>=bx[1] and nx[3]<=g['H'] and rg[1]>=g['bar']-4 and rg[3]<=lim+4
    if ring_on and g.get(ring_on): t=g[ring_on]; ok=ok and abs(rg[0]-(t[0]-4))<=1 and abs(rg[1]-(t[1]-4))<=1
    return ok
@check('L-03','turning the phone on tour step 3: the ring stays on the Shop tab, on screen, and the whole bubble with Next is on screen (Android and iPhone, both ways)')
async def _(b,U):
    out=[]
    for dev,(w,h) in (('android',(412,915)),('ios',(390,844))):
        for start in ('portrait','landscape'):
            ctx=await ctxp(b,dev); pg=await page(ctx,U)
            if start=='landscape': await pg.set_viewport_size({'width':h,'height':w}); await pg.wait_for_timeout(300)
            await pg.click('#tourYes'); await pg.wait_for_timeout(500)
            for _ in range(2): await pg.click('#tNext'); await pg.wait_for_timeout(700)
            await pg.set_viewport_size({'width':h,'height':w} if start=='portrait' else {'width':w,'height':h}); await pg.wait_for_timeout(800); g=await pg.evaluate(GEO)
            ok=g['at']=='3 of 5' and tour_ok(g,'tab'); out.append((dev,start,'turn',ok,g))
            await pg.set_viewport_size({'width':w,'height':h} if start=='portrait' else {'width':h,'height':w}); await pg.wait_for_timeout(800); g=await pg.evaluate(GEO)
            out.append((dev,start,'turn back',g['at']=='3 of 5' and tour_ok(g,'tab'),g))
            await pg.click('#tNext'); await pg.wait_for_timeout(700); g=await pg.evaluate(GEO); out.append((dev,start,'step 4 after',g['at']=='4 of 5' and tour_ok(g),g)); await ctx.close()
    bad=[o for o in out if not o[3]]
    return not bad,[(o[0],o[1],o[2],{k:o[4][k] for k in('bub','ring','tab','H')}) for o in bad][:3] or f'{len(out)} positions on screen'
@check('L-03b','every tour step, turned to landscape and back, keeps ring and bubble on screen (short window 740 x 360 too)',False)
async def _(b,U):
    bad=[]
    for dev,(w,h) in (('android',(412,915)),('ios',(360,740))):
        for step in (1,2,3,4,5):
            ctx=await ctxp(b,dev); pg=await page(ctx,U); await pg.set_viewport_size({'width':w,'height':h}); await pg.click('#tourYes'); await pg.wait_for_timeout(500)
            for _ in range(step-1): await pg.click('#tNext'); await pg.wait_for_timeout(600)
            await pg.set_viewport_size({'width':h,'height':w}); await pg.wait_for_timeout(800); g=await pg.evaluate(GEO)
            if not(g['at']==f'{step} of 5' and tour_ok(g)): bad.append((dev,step,g['bub'],g['ring'],g['H']))
            await ctx.close()
    return not bad,bad[:4] or '10 positions on screen'

# ---------- L-04
@check('L-04','a made-up address shows "Page not found" with links home and to Guides, stays put, and its links work from any depth')
async def _(b,U):
    out=[]
    for dev,scheme in (('ios','light'),('android','dark'),('desk','light')):
        for path in ('guide-that-does-not-exist','how-to-double-a-recip','a/b/c'):
            ctx=await ctxp(b,dev,scheme); pg=await ctx.new_page(); r=await pg.goto(U+path); await pg.wait_for_timeout(900)
            h1=await pg.inner_text('h1') if await pg.locator('h1').count() else ''; here=pg.url==U+path
            links=await pg.evaluate("[...document.querySelectorAll('main a')].map(a=>[a.textContent.trim(),a.href])")
            ok=r.status==404 and here and h1=='Page not found' and [U,U+'guides']==[l[1] for l in links] and await pg.evaluate("!document.querySelector('meta[http-equiv=refresh]')&&document.documentElement.scrollWidth<=document.documentElement.clientWidth&&document.querySelector('meta[name=robots]').content==='noindex'")
            if ok:
                await pg.click('main a >> nth=1'); await pg.wait_for_timeout(400); ok=pg.url==U+'guides' and await pg.inner_text('h1')=='Guides'
                await pg.go_back(); await pg.wait_for_timeout(300); await pg.click('main a >> nth=0'); await pg.wait_for_timeout(500); ok=ok and pg.url.rstrip('/')==U.rstrip('/') and await pg.is_visible('#choose')
            out.append((dev,path,ok,f'status={r.status} url={pg.url} h1={h1!r} links={links}')); await ctx.close()
    bad=[o for o in out if not o[2]]
    return not bad,bad[:2] or '9 runs: 404 status, message, both links work'
@check('L-04b','real pages still open at their clean addresses, and the 404 page is not in the sitemap',False)
async def _(b,U):
    root=NEW_ROOT if U==UN else OLD_ROOT; ctx=await ctxp(b,'desk'); pg=await ctx.new_page(); bad=[]
    for p in ('','guides','about','privacy','how-to-double-a-recipe','sitemap.xml','robots.txt'):
        r=await pg.goto(U+p)
        if r.status!=200: bad.append((p,r.status))
    await ctx.close(); sm=open(os.path.join(root,'sitemap.xml')).read()
    return not bad and '404' not in sm,bad or 'all 200'

# ---------- minors
def bk(batches,freezer=None):
    o={'app':'batch.recipes','v':1,'at':'2026-11-14T00:00:00Z','batches':batches,'settings':{'theme':None,'staples':[]}}
    if freezer is not None: o['freezer']=freezer
    return json.dumps(o)
def B(id,text=None,w=14,at=1763000000000,**k):
    d={'id':id,'title':'Chili','text':text or CHILI+' '+id,'w':w,'m':'batch','at':at,'k':[]}; d.update(k); return d
FZ1=lambda date:[{'id':'e1','bid':'f1','title':'Chili','date':date,'fz':3,'fr':0,'fz0':3,'fr0':0,'at':1}]
BAD={'meals 1e9':bk([B('w1',w=1e9)]),'meals 0.5':bk([B('w2',w=0.5)]),'saved at 9e15':bk([B('t1',at=9e15)]),'freezer date 31 Feb':bk([B('f1')],FZ1('2026-02-31')),
     'meals 1000':bk([B('w3',w=1000)]),'serves 1e9':bk([B('y1',y=1e9)]),'serves 2.5':bk([B('y2',y=2.5)]),'freezer date 29 Feb 2026':bk([B('f1')],FZ1('2026-02-29')),'freezer month 13':bk([B('f1')],FZ1('2026-13-01'))}
@check('M-01','hand-edited backups with impossible values are refused whole, with the one-line message; nothing is added')
async def _(b,U):
    bad=[]
    for name,txt in BAD.items():
        ctx,pg=await seeded(b,U,'','desk'); await pg.set_input_files('#bfile',{'name':'b.json','mimeType':'application/json','buffer':txt.encode()}); await pg.wait_for_timeout(350)
        t=await pg.inner_text('#toast'); n=len(await pg.evaluate(LS,'bd-batches') or []); f=len(await pg.evaluate(LS,'bd-freezer') or []); home=(await pg.inner_text('#home')).replace('\n',' ')
        if not(t=="That file isn't a batch.recipes backup" and n==0 and f==0 and 'Invalid Date' not in home): bad.append(f'{name}: toast={t!r} batches={n} freezer={f}')
        await ctx.close()
    return not bad,bad[:4] or f'{len(BAD)} files refused'
@check('M-01b','good backups still restore: whole numbers 1 and 999, a leap day, an older file with no freezer or serves',False)
async def _(b,U):
    ctx,pg=await seeded(b,U,'','desk'); txt=bk([B('g1',w=1),B('g2',w=999,y=999),B('g3',w='14'),B('f1')],FZ1('2024-02-29'))
    await pg.set_input_files('#bfile',{'name':'b.json','mimeType':'application/json','buffer':txt.encode()}); await pg.wait_for_timeout(350)
    t=await pg.inner_text('#toast'); n=len(await pg.evaluate(LS,'bd-batches') or []); f=len(await pg.evaluate(LS,'bd-freezer') or [])
    o=json.loads(bk([B('h1')])); del o['settings']
    await pg.set_input_files('#bfile',{'name':'b.json','mimeType':'application/json','buffer':json.dumps(o).encode()}); await pg.wait_for_timeout(350); n2=len(await pg.evaluate(LS,'bd-batches') or []); await ctx.close()
    return t=='Restored 4 batches' and n==4 and f==1 and n2==5,f'toast={t!r} batches={n} then {n2}, freezer={f}'
@check('M-02','Recipe serves 999 with 12 meals shows a real factor (0.012×), not 0×')
async def _(b,U):
    out=[]
    for dev in ('android','ios','desk'):
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await sample(pg); await pg.fill('#want','12'); await pg.keyboard.press('Enter'); await pg.fill('#yield','99999'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        m=await pg.inner_text('#sMeta'); await pg.click('[data-m=scale]'); await pg.wait_for_timeout(300); await pg.fill('#want','1'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200); m2=await pg.inner_text('#sMeta')
        await pg.fill('#yield','4'); await pg.keyboard.press('Enter'); await pg.fill('#want','6'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200); m3=await pg.inner_text('#sMeta')
        await pg.fill('#want','8'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200); m4=await pg.inner_text('#sMeta')
        out.append((dev,m.startswith('0.012× the recipe') and m2=='0.001× the recipe' and m3=='1.5× the recipe' and m4=='2× the recipe',[m,m2,m3,m4])); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or '0.012×, 0.001×; 1.5× and 2× unchanged'
@check('M-03a','two tabs: a batch removed in one tab is closed in the other and does not come back when that tab changes something')
async def _(b,U):
    ctx,pg=await seeded(b,U,SOUPS,'desk'); pg2=await page(ctx,U); await pg2.locator('#savedList .open').first.click(); await pg2.wait_for_timeout(500)
    await pg.reload(); await pg.wait_for_timeout(300); await pg.locator('#savedList .rm').first.click(); await pg.wait_for_timeout(500)
    home=await pg2.evaluate("!document.getElementById('v-add').classList.contains('hidden')"); t=await pg2.inner_text('#toast')
    if not home: await pg2.click('[data-t=want][data-d="1"]'); await pg2.wait_for_timeout(300)
    left=await pg2.evaluate("JSON.parse(localStorage.getItem('bd-batches')).map(x=>x.title)"); rows=await pg2.locator('#savedList .open').count()
    await pg2.go_forward(); await pg2.wait_for_timeout(300); left2=await pg2.evaluate("JSON.parse(localStorage.getItem('bd-batches')).length"); await ctx.close()
    return left==['Soup 1','Soup 2','Soup 3'] and home and rows==3 and left2==3 and 'Removed Soup 0' in t,f'other tab on home={home} toast={t!r} stored={left} rows shown={rows}'
@check('M-03b','two tabs: lists follow each other (a new batch, a freezer row, a staple, the theme); a different batch open in the other tab is left alone',False)
async def _(b,U):
    ctx,pg=await seeded(b,U,SOUPS,'desk'); pg2=await page(ctx,U); await pg2.locator('#savedList .open').nth(2).click(); await pg2.wait_for_timeout(400)
    await pg.reload(); await pg.wait_for_timeout(300); await pg.click('#savedList .rm[data-rm=s0]'); await pg.wait_for_timeout(400); still=await pg2.is_visible('#v-sheet') and await pg2.inner_text('#sTitle')=='Soup 2'
    await pg2.click('[data-t=want][data-d="1"]'); await pg2.wait_for_timeout(300); n=await pg.locator('#savedList .open').count(); first=await pg.inner_text('#savedList .open >> nth=0')
    await tab(pg2,'store'); await pg2.click('#didGo'); await pg2.wait_for_timeout(400); fz=await pg.is_visible('#fz') and 'Soup 2' in await pg.inner_text('#fzList')
    await pg.click('#theme'); await pg.wait_for_timeout(200); th=await pg2.evaluate("document.documentElement.dataset.theme"); await ctx.close()
    return still and n==3 and 'Soup 2' in first and '15 meals' in first and fz and th=='dark',f'open batch kept={still} rows={n} first={first!r} freezer shown={fz} theme={th}'
@check('M-04','three quick taps on Ate one, then Undo: all three come back')
async def _(b,U):
    out=[]
    for dev in ('ios','android','desk'):
        ctx,pg=await seeded(b,U,"localStorage.setItem('bd-freezer',JSON.stringify([{id:'e1',bid:null,title:'Stew',date:'2026-11-01',fz:10,fr:0,fz0:10,fr0:0,at:1}]));",dev)
        x,y=await mid(pg.locator('#fzList [data-ate]').first); await taps(pg,dev,x,y,3,120); await pg.wait_for_timeout(200); a=(await pg.evaluate(LS,'bd-freezer'))[0]['fz']; t=(await pg.inner_text('#toast')).replace('\n',' ')
        await pg.click('#toast button'); await pg.wait_for_timeout(300); c=(await pg.evaluate(LS,'bd-freezer'))[0]['fz']; out.append((dev,a==7 and c==10 and t.startswith('Ate 3. 7 left'),f'10 -> {a} -> {c} toast={t!r}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or '10 -> 7 -> 10, toast "Ate 3. 7 left"'
@check('M-05','double tap Add to list opens one share sheet (also while a slow sheet is still open); a later tap opens it again')
async def _(b,U):
    out=[]
    for dev in ('ios','android'):
        ctx=await ctxp(b,dev); pg=await page(ctx,U); await sample(pg); await pg.locator('[data-addlist]').dblclick(); await pg.wait_for_timeout(500); n1=await pg.evaluate('window.__shared.length'); ev=await pg.evaluate("window.__ev.filter(e=>e[0]==='Add to list').length")
        await pg.wait_for_timeout(1000); await pg.click('[data-addlist]'); await pg.wait_for_timeout(300); n2=await pg.evaluate('window.__shared.length')
        await pg.evaluate("window.__shared=[];window.__go=null;navigator.share=(d)=>new Promise((ok)=>{window.__shared.push(1);window.__go=ok});0")  # a sheet that stays open
        await pg.wait_for_timeout(1100); await pg.click('[data-addlist]'); await pg.wait_for_timeout(1300); await pg.click('[data-addlist]'); await pg.wait_for_timeout(200); n3=await pg.evaluate('window.__shared.length')
        toast=await pg.evaluate("document.getElementById('toast').classList.contains('on')")
        out.append((dev,n1==1 and ev==1 and n2==2 and n3==1 and not toast,f'double tap: {n1} share, {ev} event; later tap: {n2}; while open: {n3}; stray toast={toast}')); await ctx.close()
    return all(o[1] for o in out),[o for o in out if not o[1]] or 'one sheet each time'
@check('M-06','Save as image at 999 meals asks first ("34 images"), Cancel does nothing, Save sends 34 files in one go; 90 meals does not ask')
async def _(b,U):
    ctx=await ctxp(b,'android'); pg=await page(ctx,U); await sample(pg); await tab(pg,'store'); await pg.fill('#want','999'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)
    await pg.click('#lblImg'); await pg.wait_for_timeout(1500); n0=await pg.evaluate('window.__shared.length'); ask=(await pg.inner_text('#lblFoot')).replace('\n',' ') if await pg.locator('#lblFoot').count() else ''
    ok=n0==0 and "That's 34 images, 30 labels each." in ask and 'Save 34 images' in ask and 'Cancel' in ask
    if ok:
        await pg.click('#lblNo'); await pg.wait_for_timeout(300); ok=await pg.is_visible('#lblImg') and await pg.evaluate('window.__shared.length')==0 and await pg.evaluate("document.activeElement.id")=='lblImg'
        await pg.click('#lblImg'); await pg.wait_for_timeout(200); await pg.click('#lblAll')
        for _ in range(120):
            if await pg.evaluate('window.__shared.length'): break
            await pg.wait_for_timeout(500)
        sh=await pg.evaluate('window.__shared'); ok=ok and len(sh)==1 and len(sh[0]['files'])==34 and sh[0]['files'][33]=='freezer-labels-brothy-chicken-and-rice-34.png'
        await pg.fill('#want','90'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1200); await pg.click('#lblImg'); await pg.wait_for_timeout(2500); sh=await pg.evaluate('window.__shared')
        ok=ok and len(sh)==2 and len(sh[1]['files'])==3 and await pg.locator('#lblAll').count()==0
    await ctx.close(); return ok,f'before answering: {n0} sent; card says {ask!r}'
@check('M-06b','Save as image on a computer: 999 meals asks, then 34 downloads; 14 meals is one file at once')
async def _(b,U):
    ctx=await ctxp(b,'desk'); pg=await page(ctx,U); await pg.evaluate("delete Navigator.prototype.share"); await sample(pg); await tab(pg,'store'); got=[]; pg.on('download',lambda d:got.append(d.suggested_filename))
    await pg.click('#lblImg'); await pg.wait_for_timeout(1500); one=list(got)
    await pg.fill('#want','999'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400); got.clear(); await pg.click('#lblImg'); await pg.wait_for_timeout(1500); held=len(got); asks=await pg.locator('#lblAll').count()==1
    if asks:
        await pg.click('#lblAll')
        for _ in range(160):
            if len(got)>=34: break
            await pg.wait_for_timeout(500)
    await ctx.close(); return one==['freezer-labels-brothy-chicken-and-rice.png'] and held==0 and asks and len(got)==34,f'14 meals: {one}; 999: {held} before the answer, asked={asks}, {len(got)} after'
@check('M-07','home, About and Privacy have a canonical link; the guides keep theirs')
async def _(b,U):
    root=NEW_ROOT if U==UN else OLD_ROOT; out={}
    for f,want in (('index.html','https://batch.recipes/'),('about.html','https://batch.recipes/about'),('privacy.html','https://batch.recipes/privacy'),('guides.html','https://batch.recipes/guides'),('how-to-double-a-recipe.html','https://batch.recipes/how-to-double-a-recipe')):
        m=re.findall(r'<link rel="canonical" href="([^"]+)">',open(os.path.join(root,f)).read()); out[f]=m==[want]
    return all(out.values()),out
@check('PRINT','printing never saves a sample that was only looked at (Print in the Share sheet and Print labels agree); Save as image, cooking and Copy link still save it')
async def _(b,U):
    out={}
    for how in ('labels','sheet','image','cooked','link'):
        ctx=await ctxp(b,'desk'); await ctx.grant_permissions(['clipboard-read','clipboard-write']); pg=await page(ctx,U); await sample(pg)
        if how=='labels': await tab(pg,'store'); await pg.click('#lblPrint')
        elif how=='sheet': await pg.click('#dShare'); await pg.wait_for_timeout(400); await pg.click('#menu [data-print]')
        elif how=='image': await tab(pg,'store'); await pg.click('#lblImg')
        elif how=='cooked': await tab(pg,'store'); await pg.click('#didGo')
        else: await pg.click('#dShare'); await pg.wait_for_timeout(400); await pg.click('#menu [data-link]')
        await pg.wait_for_timeout(700); out[how]=(len(await pg.evaluate(LS,'bd-batches') or []),await pg.evaluate('window.__printed')); await ctx.close()
    # the code on labels printed from the unsaved sample still opens the sample, on this phone or any other
    ctx=await ctxp(b,'android'); pg=await page(ctx,U); await sample(pg); await tab(pg,'store'); await pg.click('#lblPrint'); await pg.wait_for_timeout(400)
    out['unsaved after print']=len(await pg.evaluate(LS,'bd-batches') or []); await ctx.close()
    for name in ('sample','zzzz'):
        ctx=await ctxp(b,'ios'); pg=await page(ctx,U,'#b='+name,600)
        out['label '+name]=(await pg.is_visible('#v-sheet') and await pg.inner_text('#sTitle')=='Brothy chicken and rice',await pg.is_visible('#noB'),len(await pg.evaluate(LS,'bd-batches') or [])); await ctx.close()
    return out['labels']==(0,1) and out['sheet']==(0,1) and out['image'][0]==1 and out['cooked'][0]==1 and out['link'][0]==1 and out['label sample']==(True,False,0) and out['label zzzz']==(False,True,0),out

# ---------- the new bits look right
@check('LOOK','new notes sit on the 8 px scale, nothing scrolls sideways (320 to 1440, light and dark), and the 404 page is even',False)
async def _(b,U):
    bad=[]
    for (dev,w,h,scheme) in (('android',320,640,'light'),('ios',390,844,'dark'),('android',412,915,'light'),('desk',1440,900,'dark')):
        ctx,pg=await seeded(b,U,CAP,dev,scheme=scheme); await pg.set_viewport_size({'width':w,'height':h}); await paste(pg,CHILI); await tab(pg,'store'); await pg.click('#didGo'); await pg.wait_for_timeout(300)
        g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),a=q('#didFull'),go=q('#didGo'),d=q('.didc .set'),l=q('#didMine');return {top:Math.round(a.top-d.bottom),gap:Math.round(go.top-a.bottom),link:Math.round(l.height),sw:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()")
        if g!={'top':8,'gap':8,'link':44,'sw':0}: bad.append(('full note',w,g))
        await pg.fill('#want','999'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400); await pg.click('#lblImg'); await pg.wait_for_timeout(300)
        g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),t=q('#lblFoot .tip'),h=q('.labels .hint'),c=q('.labels'),a=q('#lblAll'),n=q('#lblNo'),cs=getComputedStyle(document.querySelector('.labels'));return {top:Math.round(t.top-h.bottom),bot:Math.round(c.bottom-parseFloat(cs.paddingBottom)-parseFloat(cs.borderBottomWidth)-t.bottom),btn:[Math.round(a.height),Math.round(n.height)],sw:document.documentElement.scrollWidth-document.documentElement.clientWidth}})()")
        if not(g['top']==8 and g['bot']==0 and min(g['btn'])>=44 and g['sw']==0): bad.append(('labels ask',w,g))
        await ctx.close()
        ctx=await ctxp(b,dev,scheme); pg=await ctx.new_page(); await pg.set_viewport_size({'width':w,'height':h}); await pg.goto(U+'nope'); await pg.wait_for_timeout(300)
        g=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),h=q('h1'),l=q('.lead'),b=q('.cta .btn'),n=q('.nf a'),m=q('main'),cs=getComputedStyle(document.body);return {a:Math.round(l.top-h.bottom),b:Math.round(b.top-l.bottom),c:Math.round(n.top-b.bottom),btn:Math.round(b.height),link:Math.round(n.height),mid:Math.abs(Math.round((n.left+n.right)/2-(m.left+m.right)/2)),sw:document.documentElement.scrollWidth-document.documentElement.clientWidth,bg:cs.backgroundColor}})()")
        if not(g['a']==16 and g['b']==32 and g['c']==8 and g['btn']==56 and g['link']==44 and g['mid']<=1 and g['sw']==0 and g['bg']==('rgb(0, 0, 0)' if scheme=='dark' else 'rgb(255, 255, 255)')): bad.append(('404',w,g))
        await ctx.close()
    return not bad,bad[:4] or 'full note 8/8, labels ask 8, 404 page 16/32/8'
@check('GHOST','a removed row keeps its place, hidden from screen readers and with nothing to tap, then folds and goes; with reduced motion it just goes',False)
async def _(b,U):
    out=[]
    for sel,seedjs,box in (('#savedList .rm',SOUPS,'#savedList'),('#fzList [data-frm]',STEWS,'#fzList')):
        for red in (False,True):
            ctx,pg=await seeded(b,U,seedjs,'ios',reduce=red); x,y=await mid(pg.locator(sel).first); y0=await pg.evaluate(f"document.querySelectorAll('{box} li')[1].getBoundingClientRect().top")
            await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(250)
            g=await pg.evaluate(f"(()=>{{const g=document.querySelector('{box} li.gone'),n=document.querySelectorAll('{box} li:not(.gone)')[0];return g?{{hid:g.getAttribute('aria-hidden'),ctl:g.querySelectorAll('button,a,input').length,pe:getComputedStyle(g).pointerEvents,y:n.getBoundingClientRect().top,foc:document.activeElement.className}}:null}})()")
            await pg.wait_for_timeout(900); left=await pg.locator(f'{box} li.gone').count(); y2=await pg.evaluate(f"document.querySelectorAll('{box} li')[0].getBoundingClientRect().top")
            out.append((box,red,bool(g) and g['hid']=='true' and g['ctl']==0 and g['pe']=='none' and abs(g['y']-y0)<=1 and left==0 and y2<y0-20,f'{g} left={left} y {y0}->{y2}')); await ctx.close()
    return all(o[2] for o in out),[o for o in out if not o[2]] or 'held, then gone, in both lists'

async def run_all(b,U,only=None):
    out={}
    for id,what,fn,_ in C:
        if only and not any(id.startswith(o) for o in only): continue
        t0=time.time()
        try: out[id]=await asyncio.wait_for(fn(b,U),300)
        except Exception as e: out[id]=(False,'crashed: '+repr(e)[:260])
        print(f'   .. {"new" if U==UN else "old"} {id} {time.time()-t0:.0f}s',file=sys.stderr,flush=True)
    return out
async def main():
    args=[a for a in sys.argv[1:]]; new_only='new' in args; only=[a for a in args if a!='new'] or None
    serve(NEW_ROOT,PN)
    if not new_only: serve(OLD_ROOT,PO)
    async with async_playwright() as p:
        b=await p.chromium.launch()
        new,old=await asyncio.gather(run_all(b,UN,only),run_all(b,UO,only) if not new_only else asyncio.sleep(0,{}))
        await b.close()
    for id,what,fn,old_fails in C:
        if id not in new: continue
        log(f'{id} {what}',new[id][0],new[id][1])
        if new_only or id not in old: continue
        if old_fails is True: log(f'{id} old build shows the break',not old[id][0],old[id][1])
        elif old_fails is None: print('note',id,'on the old build:','passes' if old[id][0] else 'breaks','|',str(old[id][1])[:300])
    e=[x for x in ERRS if x[0]==UN]; log('no console errors or CSP violations on this build in any run',not e,e[:3])
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)-len(bad)} of {len(R)} ok'); sys.exit(1 if bad else 0)
asyncio.run(main())
