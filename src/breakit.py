import asyncio, json
from playwright.async_api import async_playwright
U='http://localhost:8765/'
R=[]
def log(group,name,ok,note=''):
    R.append((group,name,'ok' if ok else 'FAIL',note)); open('breakit/r1.json','w').write(json.dumps(R))
VIEW="['v-add','v-sheet'].find(i=>!document.getElementById(i).classList.contains('hidden'))"
async def fresh(b,**kw):
    ctx=await b.new_context(**kw); pg=await ctx.new_page(); errs=[]
    await pg.add_init_script("document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective+' '+e.blockedURI))")
    await pg.route('**/pagead2.googlesyndication.com/**',lambda r:r.abort())
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'jsdelivr' not in m.text and 'Failed to load resource' not in m.text else None)
    pg.on('dialog',lambda d:(errs.append('DIALOG: '+d.message),asyncio.ensure_future(d.dismiss())))
    return ctx,pg,errs
async def paste(pg,text):
    await pg.goto(U); await pg.wait_for_timeout(300)
    await pg.click('#pasteToggle'); await pg.fill('#paste',text); await pg.wait_for_timeout(150)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ph=dict(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True)
        # A. inputs
        cases={'empty':'','spaces':'     \n   ','one char':'x','5000 chars':'a'*5000,'long word':'b'*200,
          'script':'<script>alert(1)</script>\n<b>bold</b> <img src=x onerror=alert(2)>\n2 cups rice\nCook it.',
          'unicode':'Pollo 🍗 al ajillo\nمرحبا\n鸡肉 500 g\n2 dientes de ajo\n1. Cocinar.',
          'quotes':"O'Brien's \"best\" chili '; --\n1 lb beef\n1. Brown the beef.",
          'huge numbers':'Big pot\nServes 4\n999999999 lbs chicken\n1e309 cups rice\n-5 tsp salt\n0 eggs\n1. Cook.',
          'only steps':'1. Boil water.\n2. Add pasta.\n3. Drain.',
          'only ingredients':'2 lb chicken thighs\n1 cup rice\n1 tsp salt'}
        for name,text in cases.items():
            ctx,pg,errs=await fresh(b,**ph)
            await paste(pg,text)
            dis=await pg.locator('#usePaste').is_disabled()
            if dis: log('A input',name,True,'Use button stays disabled'); await ctx.close(); continue
            await pg.click('#usePaste'); await pg.wait_for_timeout(600)
            v=await pg.evaluate(VIEW)
            note='view='+v
            if v=='v-sheet':
                v2=v
                body=await pg.inner_text('#v-sheet')
                bad=[w for w in ['NaN','undefined','Infinity','null','[object'] if w in body]
                note+=f' -> {v2}; bad={bad}'
                if name=='huge numbers': note+=' | '+body[:300].replace('\n',' / ')
                ov=await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
                if ov: bad.append('hscroll')
                await pg.screenshot(path=f'breakit/A-{name.replace(" ","_")}.png',full_page=True)
                log('A input',name,not bad and not errs,note+' errs='+str(errs[:2]))
            else: log('A input',name,not errs,note+' toast='+repr(await pg.inner_text('#toast'))+' errs='+str(errs[:2]))
            await ctx.close()
        # steppers extremes
        ctx,pg,errs=await fresh(b,**ph)
        await pg.goto(U); await pg.click('#sample'); await pg.wait_for_timeout(400)
        for y,w in [('0','0'),('-3','-10'),('abc','xyz'),('99999','99999'),('1.5','2.5'),('','')]:
            await pg.fill('#yield',y); await pg.fill('#want',w); await pg.keyboard.press('Tab'); await pg.wait_for_timeout(400)
            body=await pg.inner_text('#v-sheet'); bad=[x for x in ['NaN','undefined','Infinity'] if x in body]
            head=body[:160].replace('\n',' / ')
            log('A steppers',f'yield={y!r} want={w!r}',not bad and not errs,head+(' bad='+str(bad) if bad else ''))
            await pg.screenshot(path=f'breakit/A-step-{y or "blank"}-{w or "blank"}.png')
        # stepper minus floor
        await pg.fill('#want','1'); 
        for _ in range(5): await pg.click('[data-t=want][data-d="-1"]')
        log('A steppers','minus below 1',await pg.input_value('#want')=='1','want='+await pg.input_value('#want'))
        await pg.fill('#want','998')
        for _ in range(5): await pg.click('[data-t=want][data-d="1"]')
        log('A steppers','plus above 999',await pg.input_value('#want')=='999','want='+await pg.input_value('#want'))
        await ctx.close()
        # B. repeats/timing
        ctx,pg,errs=await fresh(b,**ph)
        await pg.goto(U); await pg.click('#sample'); await pg.wait_for_timeout(300)
        n0=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')||'[]').length")
        for _ in range(12): await pg.click('[data-t=want][data-d="1"]')
        await pg.click('[data-m=scale]'); await pg.click('[data-m=batch]'); await pg.wait_for_timeout(300)
        n=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')||'[]').length")
        log('B repeats','sample alone is not saved; 12 stepper taps save one batch',n0==0 and n==1 and not errs,f'saved before={n0} after={n}')
        await pg.go_back(); await pg.wait_for_timeout(300)
        v=await pg.evaluate(VIEW)
        log('B repeats','Back from the recipe',v=='v-add' and not errs,'view='+v+' url='+pg.url)
        await pg.go_forward(); await pg.wait_for_timeout(400)
        v=await pg.evaluate(VIEW)
        log('B repeats','Forward',v=='v-sheet' and not errs,'view='+v)
        # reload on sheet
        await pg.reload(); await pg.wait_for_timeout(600)
        v=await pg.evaluate(VIEW)
        log('B repeats','reload while on sheet',not errs,'view after reload='+v)
        # cook mode spam
        COOK_OPEN="(()=>{const c=document.getElementById('cook').classList;return !c.contains('hidden')&&!c.contains('out')})()"
        await pg.goto(U); await pg.wait_for_timeout(300)
        await pg.click('#sample'); await pg.wait_for_timeout(800)
        await pg.click('#dCook'); await pg.wait_for_timeout(300)
        for _ in range(30):
            # 14 Nov: cook mode now fades out for 250 ms (class "out") before it is hidden, so "open" means not hidden and not fading out
            if not await pg.evaluate(COOK_OPEN): break
            await pg.click('#cNext')
        open_=await pg.evaluate(COOK_OPEN); await pg.wait_for_timeout(300)  # let the fade finish
        log('B repeats','Next x30 in cook mode',not errs,'cook still open='+str(open_)+' body overflow='+await pg.evaluate("document.body.style.overflow"))
        await pg.click('#dCook') if not open_ else None
        await pg.wait_for_timeout(300)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(450)  # 14 Nov: was 300; the close fade takes 250 ms before "hidden" is set
        esc_closed=await pg.evaluate("document.getElementById('cook').classList.contains('hidden')")
        log('D keyboard','Escape closes cook mode',esc_closed,'')
        if not esc_closed: await pg.click('#cClose')
        await pg.go_back(); await pg.wait_for_timeout(300)
        log('B repeats','Back after cook mode',not errs,'view='+await pg.evaluate(VIEW)+' cookHidden='+str(await pg.evaluate("document.getElementById('cook').classList.contains('hidden')")))
        await ctx.close()
        # offline: plan a batch offline
        ctx,pg,errs=await fresh(b,**ph); await pg.goto(U); await ctx.set_offline(True)
        await pg.click('#sample'); await pg.wait_for_timeout(800)
        log('B timing','offline after load: sample → sheet',not errs,'sheet shown='+str(await pg.is_visible('#v-sheet')))
        await ctx.close()
        # E. data: corrupted storage
        for k,val in [('bd-batches','not json'),('bd-batches','{"a":1}'),('bd-batches','[null,1,"x",{"id":5}]'),('bd-theme','purple'),('bd-tip','true')]:
            ctx,pg,errs=await fresh(b,**ph); await pg.goto(U)
            await pg.evaluate(f"localStorage.setItem({json.dumps(k)},{json.dumps(val)})"); await pg.reload(); await pg.wait_for_timeout(500)
            ok=await pg.is_visible('#choose')
            await pg.click('#sample'); await pg.wait_for_timeout(800)
            ok2=await pg.is_visible('#v-sheet')
            log('E storage',f'{k}={val}',ok and ok2 and not errs,'home ok='+str(ok)+' plan ok='+str(ok2)+' errs='+str(errs[:2]))
            await ctx.close()
        # 50+ saved
        ctx,pg,errs=await fresh(b,**ph); await pg.goto(U)
        await pg.evaluate("localStorage.setItem('bd-batches',JSON.stringify(Array.from({length:60},(_,i)=>({id:'i'+i,title:'Recipe '+i+' '+'x'.repeat(i%3?5:120),text:'1 lb chicken\\n1. Cook.',y:4,w:14,m:'batch',at:Date.now()-i*1e7}))))")
        await pg.reload(); await pg.wait_for_timeout(500)
        cnt=await pg.locator('#savedList li').count(); ov=await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
        await pg.screenshot(path='breakit/E-60-saved.png',full_page=True)
        log('E data','60 saved batches, long titles',not ov and not errs,f'rows shown={cnt} hscroll={ov}')
        await ctx.close()
        # F. share links
        for h in ['#r=','#r=zzzz','#r=p!!!','#r='+'z'+'A'*20000,'#r=p'+'eyJ0Ijo1fQ','#r=peyJ0IjoiPGltZyBzcmM9eCBvbmVycm9yPWFsZXJ0KDEpPiIsInkiOjQsInciOjE0fQ','#foo','#sheet','#check']:
            ctx,pg,errs=await fresh(b,**ph); await pg.goto(U+h); await pg.wait_for_timeout(900)
            toast=await pg.inner_text('#toast') if await pg.locator('#toast').count() else ''
            v=await pg.evaluate(VIEW)
            dlg=[e for e in errs if 'DIALOG' in e]
            log('F links',f'open {h[:40]}',not errs,f'view={v} toast={toast[:60]!r}'+(' DIALOG RAN' if dlg else ''))
            await ctx.close()
        # roundtrip share of unicode/script recipe
        ctx,pg,errs=await fresh(b,**ph); await ctx.grant_permissions(['clipboard-read','clipboard-write'])
        await paste(pg,cases['script']); await pg.click('#usePaste'); await pg.wait_for_timeout(700)
        await pg.click('#dShare'); await pg.click('#menu [data-link]'); await pg.wait_for_timeout(500); link=await pg.evaluate('navigator.clipboard.readText()')
        pg2=await ctx.new_page(); e2=[]; pg2.on('dialog',lambda d:(e2.append('DIALOG'),asyncio.ensure_future(d.dismiss())))
        await pg2.goto(link); await pg2.wait_for_timeout(1000)
        log('F links','share link round-trip (script text)',not e2 and await pg2.is_visible('#v-sheet'),f'len={len(link)}')
        await ctx.close()
        # C. widths & themes on sheet + cook
        for w in [320,390,600,601,720,721,768,1024,1280,1440,1920,2560]:
            for sch in ['light','dark']:
                ctx,pg,errs=await fresh(b,viewport={'width':w,'height':800},color_scheme=sch)
                await pg.goto(U); await pg.wait_for_timeout(200)
                ov1=await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
                await pg.click('#sample'); await pg.wait_for_timeout(800)
                ov2=await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
                # any element overflowing its parent horizontally
                clip=await pg.evaluate("""[...document.querySelectorAll('#v-sheet *')].filter(e=>e.offsetParent&&e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflowX==='visible'&&e.children.length===0).slice(0,3).map(e=>e.tagName+'.'+e.className+':'+e.textContent.slice(0,30))""")
                ov2=ov2 or await pg.evaluate("(async()=>{let o=false;for(const t of ['cook','store','recipe']){document.querySelector('[data-tab='+t+']').click();await new Promise(r=>setTimeout(r,60));o=o||document.documentElement.scrollWidth>innerWidth}document.querySelector('[data-m=scale]').click();await new Promise(r=>setTimeout(r,60));o=o||document.documentElement.scrollWidth>innerWidth;document.querySelector('[data-m=batch]').click();return o})()")
                await pg.click('#dShare'); await pg.wait_for_timeout(150); await pg.keyboard.press('Escape')
                await pg.click('#dCook'); await pg.wait_for_timeout(300)
                ov3=await pg.evaluate("document.documentElement.scrollWidth>innerWidth")
                if sch=='light' and w in (320,1920): await pg.screenshot(path=f'breakit/C-cook-{w}.png')
                log('C screens',f'{w}px {sch}',not(ov1 or ov2 or ov3) and not clip and not errs,f'hscroll home/sheet/cook={ov1}/{ov2}/{ov3} clipped={clip}')
                await ctx.close()
        # zoom 200% at 390 -> 195 css px
        ctx,pg,errs=await fresh(b,viewport={'width':195,'height':422}); await pg.goto(U); await pg.click('#sample'); await pg.wait_for_timeout(800)
        ov=await pg.evaluate("document.documentElement.scrollWidth>innerWidth"); await pg.screenshot(path='breakit/C-zoom200.png',full_page=True)
        log('C screens','200% zoom on a phone (195px)',not ov,f'hscroll={ov}'); await ctx.close()
        # D. keyboard & names
        ctx,pg,errs=await fresh(b,viewport={'width':1280,'height':800}); await pg.goto(U)
        seen=[]
        for _ in range(25):
            await pg.keyboard.press('Tab')
            seen.append(await pg.evaluate("(()=>{const e=document.activeElement;const cs=getComputedStyle(e);return e.tagName+'#'+e.id+'|'+(e.getAttribute('aria-label')||e.textContent.trim().slice(0,20))+'|ring:'+(cs.outlineStyle!=='none'||cs.boxShadow!=='none')})()"))
        noname=await pg.evaluate("[...document.querySelectorAll('button,input,a,textarea')].filter(e=>e.offsetParent&&!(e.getAttribute('aria-label')||e.textContent.trim()||e.getAttribute('placeholder')||e.labels&&e.labels.length)).map(e=>e.outerHTML.slice(0,80))")
        noring=[s for s in seen if s.endswith('ring:False')]
        log('D keyboard','Tab order on home',not noring,'; '.join(seen[:12]))
        log('D keyboard','controls without a name',not noname,str(noname[:4]))
        await ctx.close()
        # F 404
        ctx,pg,errs=await fresh(b); r=await pg.goto(U+'does-not-exist'); log('F links','/does-not-exist',True,f'status={r.status} (local server; checked live separately)'); await ctx.close()
        await b.close()
asyncio.run(main())
