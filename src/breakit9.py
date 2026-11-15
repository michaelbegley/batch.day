# My freezer, "I cooked this", QR on freezer labels, #b= links, backup of the freezer, and the lost-tap fix
# (type a number in Meals or Recipe serves, then tap a button straight away). Nothing leaves the machine.
# QR checks: module-for-module against python-qrcode, then scanned with zxing-cpp and OpenCV from the screen, the print layout and the image strip.
import asyncio, json, io, subprocess, datetime, re
import numpy as np, cv2
from PIL import Image
from playwright.async_api import async_playwright
try: import zxingcpp
except Exception: zxingcpp=None
try:
    import qrcode
    from qrcode.util import QRData, MODE_8BIT_BYTE
    from qrcode.constants import ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
except Exception: qrcode=None
U='http://localhost:8765/'
AND='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36'
R=[]
def log(n,ok,note=''):
    R.append((n,'ok' if ok else 'FAIL',str(note))); open('breakit/r9.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',n,'|',str(note)[:300])
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective));
window.__ev=[];window.umami={track:(n,d)=>window.__ev.push([n,d])};window.__printed=0;window.print=()=>{window.__printed++};"""
TODAY=datetime.date.today().isoformat()
SOUP=lambda i:f'Soup {i}\nServes 4\n1 cup lentils\n2 carrots\n1. Simmer 30 minutes.'
BATCH=lambda n:[{'id':f'b{i}','title':f'Soup {i}','text':SOUP(i),'y':4,'w':14,'m':'batch','at':1763000000000+i,'k':[]} for i in range(n)]
def FZ(id,bid,title,date,fz,fr,fz0=None,fr0=None,at=1763000000000,**kw):
    d={'id':id,'bid':bid,'title':title,'date':date,'fz':fz,'fr':fr,'fz0':fz if fz0 is None else fz0,'fr0':fr if fr0 is None else fr0,'at':at}; d.update(kw); return d
def seed(batches=None,fz=None,extra=''):
    s=''
    if batches is not None: s+=f"localStorage.setItem('bd-batches',{json.dumps(json.dumps(batches))});"
    if fz is not None: s+=f"localStorage.setItem('bd-freezer',{json.dumps(json.dumps(fz))});"
    return "if(!sessionStorage.getItem('__s')){sessionStorage.setItem('__s','1');"+s+extra+"}"
async def fresh(b,w=390,h=844,mob=True,pre='',go=U,**kw):
    if mob and 'user_agent' not in kw: kw['user_agent']=AND
    ctx=await b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,accept_downloads=True,**kw); errs=[]
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**'): await ctx.route(pat,lambda r:r.abort())
    await ctx.add_init_script(INIT+pre); pg=await ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    pg.on('dialog',lambda d:(errs.append('DIALOG: '+d.message),asyncio.ensure_future(d.dismiss())))
    await pg.goto(go); await pg.wait_for_timeout(350)
    return ctx,pg,errs
EV="(n)=>window.__ev.filter(e=>e[0]===n).map(e=>e[1])"
LSJ="(k)=>{try{return JSON.parse(localStorage.getItem(k))}catch(e){return null}}"
VIS="(s)=>{const e=document.querySelector(s);return !!e&&!e.closest('.hidden')&&e.getClientRects().length>0}"
PRESSED="(t)=>document.querySelector('[data-tab='+t+']').getAttribute('aria-pressed')"
async def sample(pg): await pg.click('#sample'); await pg.wait_for_timeout(700)
async def tab(pg,t): await pg.click(f'[data-tab={t}]'); await pg.wait_for_timeout(250)
async def typed(pg,sel,val,mob):
    # put the cursor in the box and type, as a person does; the box is not blurred here
    if mob: await pg.tap(sel)
    else: await pg.click(sel)
    await pg.keyboard.press('Control+A'); await pg.keyboard.type(str(val))
def scan(png):
    # every QR in a picture: [(text, width in px)], read with zxing-cpp, or OpenCV when zxing is missing
    img=cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_GRAYSCALE)
    if zxingcpp:
        return [(r.text,abs(r.position.top_right.x-r.position.top_left.x)) for r in zxingcpp.read_barcodes(img)]
    ok,texts,pts,_=cv2.QRCodeDetector().detectAndDecodeMulti(img)
    return [(t,float(abs(p[1][0]-p[0][0]))) for t,p in zip(texts,pts)] if ok else []
def scan_cv(png):
    img=cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_GRAYSCALE); t,_,_=cv2.QRCodeDetector().detectAndDecode(img); return t
FZROWS="""(()=>({hidden:document.getElementById('fz').classList.contains('hidden'),sum:document.getElementById('fzSum').textContent,
 labels:[...document.querySelectorAll('#fzList .aisle')].map(e=>e.textContent),
 rows:[...document.querySelectorAll('#fzList li')].map(li=>({grp:(()=>{let p=li.parentNode.previousElementSibling;return p&&p.classList.contains('aisle')?p.textContent:''})(),t:li.querySelector('b').textContent,s:li.querySelector('.open span').textContent,btn:li.querySelector('.ate').textContent,name:li.querySelector('.ate').getAttribute('aria-label')}))}))()"""
async def main():
    # ---------- unit: the split as numbers, and the QR encoder ----------
    out=subprocess.run(['node','-e',"const E=require('./engine.js');const r=E.parseRecipe('Soup\\nServes 4\\n1 cup lentils\\n2 carrots\\n1. Simmer 30 minutes.');console.log(JSON.stringify([14,4,3,1,30].map(n=>E.batchDay(r,n).portions)))"],capture_output=True,text=True)
    try: po=json.loads(out.stdout)
    except Exception: po=out.stderr[:200]
    log('unit: batchDay gives the split as numbers (4 to the fridge, the rest to the freezer)',po==[{'fridge':4,'freezer':10},{'fridge':4,'freezer':0},{'fridge':3,'freezer':0},{'fridge':1,'freezer':0},{'fridge':4,'freezer':26}],po)
    gen="""const Q=require('./qr.js');const T=['https://batch.recipes/#b=mhz1abcd','A','hello world, this is a longer line of text for version four or five!!','https://batch.recipes/#b='+'x'.repeat(70),'ünï¢ødé ✓ 冷凍'];const o=[];
for(const t of T){const a=Q.make(t);o.push({t,auto:1,v:a.version,level:a.level,mask:a.mask,rows:a.rows});for(const level of ['M','Q','H'])for(let mask=0;mask<8;mask++){const q=Q.make(t,{level,mask});if(q)o.push({t,level,mask,v:q.version,rows:q.rows})}}
console.log(JSON.stringify({o,long:Q.make('y'.repeat(200)),empty:Q.make(''),url:(()=>{const q=Q.make('https://batch.recipes/#b=mhz1abcd');return [q.version,q.level,q.size]})(),path:Q.path(Q.make('A')).length>100}))"""
    out=subprocess.run(['node','-e',gen],capture_output=True,text=True)
    try: g=json.loads(out.stdout)
    except Exception: g=None; log('unit: node qr.js runs',False,out.stderr[:300])
    if g:
        log('unit: QR for a batch link is version 3 (29 modules), level M','url' in g and g['url']==[3,'M',29],g['url'])
        log('unit: QR too long for version 6, or empty, gives nothing (the label then has no code)',g['long'] is None and g['empty'] is None and g['path'])
        if qrcode:
            L={'M':ERROR_CORRECT_M,'Q':ERROR_CORRECT_Q,'H':ERROR_CORRECT_H}; bad=[]; n=0; pairs=set()
            for c in g['o']:
                q=qrcode.QRCode(version=c['v'],error_correction=L[c['level']],border=0,mask_pattern=c['mask']); q.add_data(QRData(c['t'].encode('utf8'),mode=MODE_8BIT_BYTE,check_data=False)); q.make(fit=False)
                n+=1; pairs.add((c['v'],c['level']))
                if [''.join('1' if x else '0' for x in r) for r in q.modules]!=c['rows']: bad.append((c['t'][:12],c['level'],c['mask']))
            log(f'unit: QR matches python-qrcode module for module ({n} codes, versions 1 to 6, levels M Q H, all 8 masks)',not bad and n>=100 and len(pairs)>=10,bad[:3] or sorted(pairs))
        else: log('unit: QR matches python-qrcode (module not installed, skipped)',True,'pip install qrcode to run')
        dec=[]
        for c in g['o']:
            if not c.get('auto'): continue
            m=np.array([[255*(1-int(ch)) for ch in r] for r in c['rows']],dtype=np.uint8); img=cv2.copyMakeBorder(cv2.resize(m,None,fx=8,fy=8,interpolation=cv2.INTER_NEAREST),32,32,32,32,cv2.BORDER_CONSTANT,value=255)
            ok,buf=cv2.imencode('.png',img); z=scan(buf.tobytes()); dec.append((bool(z) and z[0][0]==c['t'],scan_cv(buf.tobytes())==c['t']))
        log('unit: every auto-picked QR scans back to its text (zxing-cpp and OpenCV)',all(a and b for a,b in dec),dec)
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # ---------- 1. the tap after typing a number ----------
        for nm,mob in (('mouse',False),('touch',True)):
            hit=(lambda pg,s:pg.tap(s)) if mob else (lambda pg,s:pg.click(s))
            kw=dict(w=390,h=844,mob=True) if mob else dict(w=1280,h=900,mob=False)
            ctx,pg,errs=await fresh(b,**kw); await sample(pg)
            await typed(pg,'#want',20,mob); await hit(pg,'[data-tab=cook]'); await pg.wait_for_timeout(120)
            r={'tab':await pg.evaluate(PRESSED,'cook'),'want':await pg.input_value('#want'),'meta':await pg.inner_text('#sMeta')}
            log(f'tap ({nm}): type 20 in Meals, tap the Cook tab: the tab opens and the page is for 20',r['tab']=='true' and r['want']=='20' and r['meta'].startswith('5×'),r)
            await typed(pg,'#want',8,mob); await hit(pg,'[data-tab=shop]'); await pg.wait_for_timeout(120)
            log(f'tap ({nm}): and again back to Shop',await pg.evaluate(PRESSED,'shop')=='true' and (await pg.inner_text('#sMeta')).startswith('2×'),await pg.inner_text('#sMeta'))
            AMT="[...document.querySelectorAll('.checks b[data-a]')].find(e=>e.textContent.trim()).textContent"; before=await pg.evaluate(AMT)
            await typed(pg,'#want',28,mob); await hit(pg,'.checks li:first-child label'); await pg.wait_for_timeout(150)
            r=await pg.evaluate("({ck:document.querySelector('.checks li:first-child input').checked,amt:[...document.querySelectorAll('.checks b[data-a]')].find(e=>e.textContent.trim()).textContent,cnt:document.getElementById('gcount').textContent,saved:JSON.parse(localStorage.getItem('bd-batches'))[0]})")
            log(f'tap ({nm}): type 28, tap a grocery row: it is ticked, amounts are for 28, both saved',r['ck'] and r['amt']!=before and r['cnt'].startswith('1 of') and r['saved']['w']==28 and len(r['saved']['k'])==1,(before,r['amt'],r['cnt'],r['saved']['w']))
            await typed(pg,'#want',14,mob); await hit(pg,'#dCook'); await pg.wait_for_timeout(450)
            r={'cook':await pg.evaluate(VIS,'#cook'),'want':await pg.evaluate("document.getElementById('want').value"),'ev':len(await pg.evaluate(EV,'Cook mode'))}
            await pg.click('#cClose'); await pg.wait_for_timeout(450)
            log(f'tap ({nm}): type 14, tap Start cooking: cook mode opens for 14',r['cook'] and r['want']=='14' and r['ev']==1 and (await pg.inner_text('#sMeta')).startswith('3.5×'),(r,await pg.inner_text('#sMeta')))
            await typed(pg,'#want',20,mob); await hit(pg,'.step button[data-t=want][data-d="1"]'); await pg.wait_for_timeout(150)
            log(f'tap ({nm}): type 20, tap +: 21',await pg.input_value('#want')=='21' and (await pg.inner_text('#sMeta')).startswith('5.3×'),(await pg.input_value('#want'),await pg.inner_text('#sMeta')))
            await typed(pg,'#yield',2,mob); await hit(pg,'[data-tab=store]'); await pg.wait_for_timeout(150)
            log(f'tap ({nm}): type in Recipe serves, tap the Store tab',await pg.evaluate(PRESSED,'store')=='true' and (await pg.inner_text('#sMeta')).startswith('10.5×') and await pg.evaluate("document.getElementById('yieldNote').classList.contains('hidden')"),await pg.inner_text('#sMeta'))
            await typed(pg,'#want',33,mob); await hit(pg,'#lblPrint'); await pg.wait_for_timeout(250)
            r=await pg.evaluate("({printed:window.__printed,n:document.querySelectorAll('#labels .lbl').length,last:[...document.querySelectorAll('#labels .lq span')].pop().textContent})"); await pg.evaluate("dispatchEvent(new Event('afterprint'))")
            log(f'tap ({nm}): type 33, tap Print labels: 33 labels',r=={'printed':1,'n':33,'last':'33 of 33'},r)
            await typed(pg,'#want',12,mob); await hit(pg,'#didGo'); await pg.wait_for_timeout(200)
            fz=await pg.evaluate(LSJ,'bd-freezer')
            log(f'tap ({nm}): type 12, tap I cooked this: 12 portions recorded',len(fz)==1 and fz[0]['fz']+fz[0]['fr']==12 and await pg.evaluate(EV,'Cooked')==[{'src':'direct','portions':12}],fz)
            await typed(pg,'#want',6,mob); await hit(pg,'#mode [data-m=scale]'); await pg.wait_for_timeout(250)
            log(f'tap ({nm}): type, tap Just scale: the mode changes',await pg.get_attribute('#mode [data-m=scale]','aria-pressed')=='true')
            await hit(pg,'#mode [data-m=batch]'); await pg.wait_for_timeout(250)
            await typed(pg,'#want',9,mob); await hit(pg,'#dShare'); await pg.wait_for_timeout(350)
            log(f'tap ({nm}): type, tap Share: the sheet opens and stays open',await pg.evaluate(VIS,'#menu') and (await pg.inner_text('#sMeta')).startswith('4.5×'),await pg.inner_text('#sMeta')); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            # the page still redraws at once without a tap
            await typed(pg,'#want',16,mob); await pg.keyboard.press('Enter'); t1=await pg.inner_text('#sMeta')
            await typed(pg,'#want',18,mob); await pg.keyboard.press('Tab'); t2=await pg.inner_text('#sMeta')
            log(f'tap ({nm}): Enter and Tab still redraw straight away',t1.startswith('8×') and t2.startswith('9×'),(t1,t2))
            # a press that never becomes a click (finger slides off): the page is still drawn
            await typed(pg,'#want',24,mob)
            await pg.evaluate("(()=>{const t=document.querySelector('[data-tab=recipe]');t.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));document.getElementById('want').blur();t.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))})()")
            m0=await pg.inner_text('#sMeta'); await pg.wait_for_timeout(600); m1=await pg.inner_text('#sMeta')
            log(f'tap ({nm}): a press with no click still ends in a redraw (within 0.6 s)',m1.startswith('12×'),(m0,m1))
            await typed(pg,'#want',14,mob); await hit(pg,'[data-tab=shop]'); await pg.wait_for_timeout(120)
            chg=await pg.evaluate("document.querySelectorAll('#sheet [data-panel=shop] .chg').length")
            log(f'tap ({nm}): changed amounts still show it after the late redraw',chg>0,chg)
            log(f'tap ({nm}): no errors',not errs,errs); await ctx.close()
        # ---------- 2. I cooked this, on the Store tab ----------
        ctx,pg,errs=await fresh(b); await sample(pg)
        log('cooked: nothing saved by looking at the sample',await pg.evaluate(LSJ,'bd-batches') is None and await pg.evaluate(LSJ,'bd-freezer') is None)
        await tab(pg,'store')
        r=await pg.evaluate("(()=>{const c=document.querySelector('.didc');return {h:c.querySelector('h3').textContent,p:c.querySelector('.didp').textContent,date:document.getElementById('ckDate').value,btn:document.getElementById('didGo').textContent,see:!!document.getElementById('didSee'),after:c.previousElementSibling.classList.contains('labels'),all:c.innerText}})()")
        log('cooked: card on the Store tab after the labels, split from the plan, date is today',r['h']=='My freezer' and r['p']=='10 meals for the freezer, 4 for the fridge.' and r['date']==TODAY and r['btn']=='I cooked this' and not r['see'] and r['after'],r)
        log('cooked: no storage or use-by time in the card',not re.search(r'use by|month|week|days|within|best|keeps|good for',r['all'],re.I),r['all'])
        await pg.tap('#didGo'); await pg.wait_for_timeout(250)
        fz=await pg.evaluate(LSJ,'bd-freezer'); bt=await pg.evaluate(LSJ,'bd-batches'); e=fz[0] if fz else {}
        log('cooked: one entry {id, bid, title, date, fz, fr, fz0, fr0, at}',len(fz)==1 and sorted(e)==['at','bid','date','fr','fr0','fz','fz0','id','title'] and e['title']=='Brothy chicken and rice' and e['date']==TODAY and (e['fz'],e['fr'],e['fz0'],e['fr0'])==(10,4,10,4),e)
        log('cooked: the sample is now a saved batch and the entry points at it',len(bt)==1 and e.get('bid')==bt[0]['id'],(e.get('bid'),bt and bt[0]['id']))
        log('cooked: event Cooked {portions: 14}',await pg.evaluate(EV,'Cooked')==[{'src':'direct','portions':14}],await pg.evaluate(EV,'Cooked'))
        t=await pg.evaluate("({t:document.querySelector('#toast span').textContent,undo:!!document.querySelector('#toast button'),on:document.getElementById('toast').classList.contains('on'),see:!!document.getElementById('didSee'),foc:document.activeElement.id})")
        log('cooked: toast "Added to My freezer" with Undo, See My freezer link shows, focus stays on the button',t=={'t':'Added to My freezer','undo':True,'on':True,'see':True,'foc':'didGo'},t)
        await pg.tap('#didGo'); await pg.wait_for_timeout(200)
        ask=await pg.evaluate("({txt:(document.querySelector('#didBox .tip')||{}).innerText||'',n:JSON.parse(localStorage.getItem('bd-freezer')).length,foc:document.activeElement.id,go:!!document.getElementById('didGo')})")
        log('cooked: the same batch on the same day asks first, adds nothing yet',ask['n']==1 and 'Already added for' in ask['txt'] and 'Add it again?' in ask['txt'] and ask['foc']=='didAgain' and not ask['go'] and not errs,ask)
        await pg.screenshot(path='breakit/9-ask.png')
        await pg.tap('#didNo'); await pg.wait_for_timeout(150)
        log('cooked: Cancel adds nothing and brings the button back',len(await pg.evaluate(LSJ,'bd-freezer'))==1 and await pg.evaluate("document.activeElement.id")=='didGo')
        await pg.tap('#didGo'); await pg.wait_for_timeout(150); await pg.tap('#didAgain'); await pg.wait_for_timeout(200)
        fz=await pg.evaluate(LSJ,'bd-freezer')
        log('cooked: Add again adds a second entry with its own id',len(fz)==2 and fz[0]['id']!=fz[1]['id'] and len(await pg.evaluate(EV,'Cooked'))==2,[x['id'] for x in fz])
        await pg.tap('#toast button'); await pg.wait_for_timeout(200)
        log('cooked: Undo takes that one back out',len(await pg.evaluate(LSJ,'bd-freezer'))==1)
        await pg.fill('#ckDate','2026-10-31'); await pg.wait_for_timeout(150)
        r=await pg.evaluate("({lbl:document.getElementById('lblDate').value,prev:document.querySelector('#lblPrev .lbl').innerText})")
        log('cooked: the date is the labels\' Cooked date, both boxes move together',r['lbl']=='2026-10-31' and 'Oct 31, 2026' in r['prev'],r)
        await pg.tap('#didGo'); await pg.wait_for_timeout(200); fz=await pg.evaluate(LSJ,'bd-freezer')
        log('cooked: another day does not ask, and keeps the chosen date',len(fz)==2 and fz[1]['date']=='2026-10-31',[x['date'] for x in fz])
        await pg.fill('#lblDate',TODAY); await pg.wait_for_timeout(150)
        log('cooked: changing the labels date moves this one too',await pg.input_value('#ckDate')==TODAY)
        await pg.tap('.step button[data-t=want][data-d="-1"]'); await pg.wait_for_timeout(200)
        log('cooked: the split follows the Meals number',await pg.inner_text('.didp')=='9 meals for the freezer, 4 for the fridge.',await pg.inner_text('.didp'))
        await pg.fill('#want','3'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        log('cooked: 3 meals all go to the fridge',await pg.inner_text('.didp')=='3 meals for the fridge.',await pg.inner_text('.didp'))
        await pg.fill('#want','14'); await pg.keyboard.press('Enter')
        bx=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect();return {go:q('#didGo').height,see:q('#didSee').height,date:q('#ckDate').height,fs:parseFloat(getComputedStyle(document.getElementById('ckDate')).fontSize),ow:document.documentElement.scrollWidth<=innerWidth}})()")
        log('cooked: targets 44 or more, date text 16px (no zoom on iPhone), no sideways scroll',bx['go']>=44 and bx['see']>=44 and bx['date']>=44 and bx['fs']>=16 and bx['ow'],bx)
        await pg.tap('#didSee'); await pg.wait_for_timeout(500)
        r=await pg.evaluate("(()=>{const f=document.getElementById('fz').getBoundingClientRect();return {home:!document.getElementById('v-add').classList.contains('hidden'),foc:document.activeElement.id,seen:f.top>=0&&f.top<innerHeight}})()")
        log('cooked: See My freezer goes to the home card and puts focus on its heading',r=={'home':True,'foc':'fzH','seen':True},r)
        await pg.go_back(); await pg.wait_for_timeout(400)
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300)
        log('cooked: not in Just scale',await pg.locator('.didc').count()==0 and await pg.locator('#didGo').count()==0)
        log('cooked: no errors',not errs,errs); await ctx.close()
        # ---------- 3. I cooked this, at the end of cook mode ----------
        ctx,pg,errs=await fresh(b); await sample(pg); await pg.tap('#dCook'); await pg.wait_for_timeout(400)
        for _ in range(40):
            if await pg.inner_text('#cNext')=='Close': break
            await pg.tap('#cNext'); await pg.wait_for_timeout(60)
        await pg.wait_for_timeout(400)
        r=await pg.evaluate("({btn:(document.getElementById('cDid')||{}).textContent,h:document.getElementById('cDid').getBoundingClientRect().height,p:document.querySelector('#cBody p').textContent})")
        log('cook mode: the last screen has a quiet I cooked this',r['btn']=='I cooked this' and r['h']>=44 and 'Label the bags' in r['p'],r)
        await pg.screenshot(path='breakit/9-cook-done.png')
        await pg.tap('#cDid'); await pg.wait_for_timeout(250)
        fz=await pg.evaluate(LSJ,'bd-freezer')
        r=await pg.evaluate("({t:document.getElementById('cDidBox').innerText.trim(),btn:!!document.getElementById('cDid'),foc:document.activeElement.id,status:document.querySelector('#cDidBox [role=status]')!==null})")
        log('cook mode: tap records it and says In My freezer',len(fz)==1 and (fz[0]['fz'],fz[0]['fr'])==(10,4) and r=={'t':'In My freezer','btn':False,'foc':'cNext','status':True} and len(await pg.evaluate(EV,'Cooked'))==1,r)
        await pg.tap('#cBack'); await pg.wait_for_timeout(200); await pg.tap('#cNext'); await pg.wait_for_timeout(300); await pg.tap('#cDid'); await pg.wait_for_timeout(200)
        r=await pg.evaluate("({t:document.getElementById('cDidBox').innerText,n:JSON.parse(localStorage.getItem('bd-freezer')).length,foc:document.activeElement.id})")
        log('cook mode: a second time the same day asks first',r['n']==1 and 'Already added today. Add it again?' in r['t'] and r['foc']=='cDidAgain',r)
        await pg.keyboard.press('Tab'); f1=await pg.evaluate("document.activeElement.id"); await pg.keyboard.press('Tab'); await pg.keyboard.press('Tab'); await pg.keyboard.press('Tab'); await pg.keyboard.press('Tab'); f2=await pg.evaluate("!!document.activeElement.closest('#cook')")
        log('cook mode: Tab reaches Cancel and stays inside cook mode',f1=='cDidNo' and f2,(f1,f2))
        await pg.tap('#cDidNo'); await pg.wait_for_timeout(150)
        log('cook mode: Cancel adds nothing',len(await pg.evaluate(LSJ,'bd-freezer'))==1 and await pg.locator('#cDid').count()==1)
        await pg.tap('#cDid'); await pg.wait_for_timeout(100); await pg.tap('#cDidAgain'); await pg.wait_for_timeout(200)
        log('cook mode: Add again adds',len(await pg.evaluate(LSJ,'bd-freezer'))==2)
        await pg.tap('#cNext'); await pg.wait_for_timeout(450); await tab(pg,'store')
        log('cook mode: back on the page the Store card knows',await pg.locator('#didSee').count()==1)
        await pg.click('#mode [data-m=scale]'); await pg.wait_for_timeout(300); await pg.tap('#dCook'); await pg.wait_for_timeout(300)
        for _ in range(40):
            if await pg.inner_text('#cNext')=='Close': break
            await pg.tap('#cNext'); await pg.wait_for_timeout(60)
        log('cook mode: not offered in Just scale',await pg.locator('#cDid').count()==0 and await pg.locator('#cDidBox').count()==0)
        log('cook mode: no errors',not errs,errs); await ctx.close()
        # ---------- 4. the home card ----------
        ctx,pg,errs=await fresh(b)
        log('home: no card when the freezer is empty',not await pg.evaluate(VIS,'#fz') and await pg.evaluate("document.getElementById('fzList').children.length")==0); await ctx.close()
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(1),[]))
        log('home: no card for an empty list either',not await pg.evaluate(VIS,'#fz')); await ctx.close()
        F=[FZ('e2','b1','Soup 1','2026-11-10',10,4,at=1763000000002),FZ('e1','b0','Soup 0','2026-11-02',9,0,10,4,at=1763000000001),FZ('e3','gone','Chili <b>big</b>','2025-12-30',1,2,10,4,at=1763000000003),
           {'id':'bad','title':'x'},FZ('e4','b0','Old all gone','2026-10-01',0,0,10,4,zx=1,rx=1)]
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(2),F))
        s=await pg.evaluate(FZROWS)
        log('home: card shows with a total line',not s['hidden'] and s['sum']=='20 meals in the freezer',s['sum'])
        log('home: fridge group first, then the freezer, each oldest first',s['labels']==['In the fridge','In the freezer'] and [(x['grp'],x['t']) for x in s['rows']]==[('In the fridge','Chili <b>big</b>'),('In the fridge','Soup 0'),('In the fridge','Soup 1'),('In the freezer','Chili <b>big</b>'),('In the freezer','Soup 0'),('In the freezer','Soup 1')],[(x['grp'],x['t']) for x in s['rows']])
        log('home: rows say what is left and when it was cooked (year only when it is not this year)',[x['s'] for x in s['rows']]==['2 left · Cooked Dec 30, 2025','None left · Cooked Nov 2','4 left · Cooked Nov 10','1 left · Cooked Dec 30, 2025','9 left · Cooked Nov 2','10 left · Cooked Nov 10'],[x['s'] for x in s['rows']])
        log('home: Ate one on rows with some left, Remove at 0, each named for a screen reader',[x['btn'] for x in s['rows']]==['Ate one','Remove','Ate one','Ate one','Ate one','Ate one'] and s['rows'][0]['name']=='Ate one, Chili <b>big</b>' and s['rows'][1]['name']=='Remove, Soup 0',[x['name'] for x in s['rows']][:2])
        log('home: a title is text, never markup',await pg.evaluate("document.querySelectorAll('#fzList b *').length")==0)
        txt=await pg.inner_text('#fz')
        log('home: no storage or use-by time anywhere in the card',not re.search(r'use by|month|week|days|within|best|keeps|good for|expire',txt,re.I),txt[:200])
        pos=await pg.evaluate("(()=>{const f=document.getElementById('fz'),p=f.previousElementSibling,n=f.nextElementSibling,q=(e)=>e.getBoundingClientRect();return {prev:p.className,next:n.className,above:Math.round(q(f).top-q(p).bottom),below:Math.round(q(n).top-q(f).bottom),inView:q(f).top<innerHeight,ow:document.documentElement.scrollWidth<=innerWidth,small:[...f.querySelectorAll('button')].filter(b=>q(b).height<44||q(b).width<44).length}})()")
        log('home: card sits between the paste links and the three icons, 24 above and below, peeking on the first screen',pos['prev']=='links' and pos['next']=='flow' and pos['above']==24 and pos['below']==24 and pos['inView'],pos)
        log('home: every button 44 or more, no sideways scroll',pos['small']==0 and pos['ow'],pos)
        await pg.screenshot(path='breakit/9-home.png',full_page=True)
        # ate one
        await pg.tap('#fzList [data-ate="e2"][data-p="z"]'); await pg.wait_for_timeout(250)
        s=await pg.evaluate(FZROWS); st=await pg.evaluate(LSJ,'bd-freezer'); e2=[x for x in st if x.get('id')=='e2'][0]
        t=await pg.evaluate("({t:document.querySelector('#toast span').textContent,undo:!!document.querySelector('#toast button'),foc:[document.activeElement.dataset.ate,document.activeElement.dataset.p]})")
        log('ate one: counts down on the row, in the total and in storage',s['rows'][5]['s'].startswith('9 left') and s['sum']=='19 meals in the freezer' and e2['fz']==9 and e2['fz0']==10 and e2['at']>1763000000002,(s['rows'][5]['s'],s['sum'],e2))
        log('ate one: short toast with Undo, focus stays on the same button',t=={'t':'Ate one. 9 left','undo':True,'foc':['e2','z']},t)
        log('ate one: event',await pg.evaluate(EV,'Ate one')==[{'src':'direct'}],await pg.evaluate(EV,'Ate one'))
        log('ate one: unreadable entries are left in storage untouched',{'id':'bad','title':'x'} in st and len(st)==5,len(st))
        await pg.tap('#toast button'); await pg.wait_for_timeout(250); s=await pg.evaluate(FZROWS)
        log('ate one: Undo puts it back',s['rows'][5]['s'].startswith('10 left') and s['sum']=='20 meals in the freezer' and [x for x in await pg.evaluate(LSJ,'bd-freezer') if x.get('id')=='e2'][0]['fz']==10,s['sum'])
        await pg.tap('#fzList [data-ate="e2"][data-p="z"]'); await pg.wait_for_timeout(100)
        gone=await pg.evaluate("new Promise(r=>{const t0=performance.now(),el=document.getElementById('toast');const f=()=>{if(!el.classList.contains('on'))r(performance.now()-t0);else if(performance.now()-t0>7000)r(-1);else setTimeout(f,100)};f()})")
        log('ate one: the toast goes by itself in about 4 s',3000<gone<4600,gone)
        await pg.tap('#fzList [data-ate="e3"][data-p="z"]'); await pg.wait_for_timeout(250); s=await pg.evaluate(FZROWS)
        t=await pg.evaluate("({t:document.querySelector('#toast span').textContent,foc:[document.activeElement.dataset.frm,document.activeElement.dataset.p]})")
        log('ate the last one: the row says None left and offers Remove, focus moves to it',s['rows'][3]['s'].startswith('None left') and s['rows'][3]['btn']=='Remove' and t=={'t':'Ate one. None left','foc':['e3','z']},(s['rows'][3],t))
        await pg.tap('#toast button'); await pg.wait_for_timeout(200); s=await pg.evaluate(FZROWS)
        log('ate the last one: Undo brings Ate one back',s['rows'][3]['btn']=='Ate one' and s['rows'][3]['s'].startswith('1 left'))
        # remove
        await pg.tap('#fzList [data-frm="e1"][data-p="r"]'); await pg.wait_for_timeout(250); s=await pg.evaluate(FZROWS); st=await pg.evaluate(LSJ,'bd-freezer')
        log('remove: the fridge row goes, its freezer row stays',[(x['grp'],x['t']) for x in s['rows']].count(('In the fridge','Soup 0'))==0 and ('In the freezer','Soup 0') in [(x['grp'],x['t']) for x in s['rows']] and [x for x in st if x.get('id')=='e1'][0].get('rx')==1,[(x['grp'],x['t']) for x in s['rows']])
        t=await pg.evaluate("({t:document.querySelector('#toast span').textContent,undo:!!document.querySelector('#toast button')})")
        log('remove: toast with Undo',t=={'t':'Removed Soup 0','undo':True},t)
        await pg.tap('#toast button'); await pg.wait_for_timeout(200); s=await pg.evaluate(FZROWS)
        log('remove: Undo brings the row back',('In the fridge','Soup 0') in [(x['grp'],x['t']) for x in s['rows']])
        # open
        await pg.tap('#fzList [data-fo="e2"]'); await pg.wait_for_timeout(600)
        log('open: a row opens its batch',await pg.inner_text('#sTitle')=='Soup 1' and await pg.evaluate(VIS,'#v-sheet') and await pg.evaluate(EV,'Freezer open')==[{'src':'direct','from':'card','ok':'yes'}],await pg.evaluate(EV,'Freezer open'))
        await pg.go_back(); await pg.wait_for_timeout(400)
        await pg.tap('#fzList [data-fo="e3"]'); await pg.wait_for_timeout(300)
        t=await pg.evaluate("({t:document.querySelector('#toast span').textContent,on:document.getElementById('toast').classList.contains('on'),home:!document.getElementById('v-add').classList.contains('hidden')})")
        log('open: a batch that is no longer saved says so plainly',t=={'t':"This batch isn't saved on this phone",'on':True,'home':True} and (await pg.evaluate(EV,'Freezer open'))[-1]=={'src':'direct','from':'card','ok':'no'},t)
        log('home: no errors',not errs,errs); await ctx.close()
        # the card empties and hides
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(1),[FZ('e1','b0','Soup 0','2026-11-02',1,0,1,1)]))
        s=await pg.evaluate(FZROWS)
        log('home: singular, and the fridge row at 0 offers Remove',s['sum']=='1 meal in the freezer' and [x['btn'] for x in s['rows']]==['Remove','Ate one'],s)
        await pg.tap('#fzList [data-ate]'); await pg.wait_for_timeout(200); s=await pg.evaluate(FZROWS)
        log('home: nothing left anywhere says Nothing left, card still there until removed',s['sum']=='Nothing left' and not s['hidden'] and [x['btn'] for x in s['rows']]==['Remove','Remove'],s['sum'])
        await pg.tap('#fzList [data-frm][data-p="r"]'); await pg.wait_for_timeout(200); await pg.tap('#fzList [data-frm][data-p="z"]'); await pg.wait_for_timeout(250)
        r=await pg.evaluate("({hidden:document.getElementById('fz').classList.contains('hidden'),st:JSON.parse(localStorage.getItem('bd-freezer')),foc:document.activeElement.id})")
        log('home: both rows removed: the entry is gone, the card hides, focus goes to Choose screenshots',r=={'hidden':True,'st':[],'foc':'choose'},r)
        await pg.tap('#toast button'); await pg.wait_for_timeout(200)
        log('home: Undo brings the card back',not await pg.evaluate("document.getElementById('fz').classList.contains('hidden')") and len(await pg.evaluate(LSJ,'bd-freezer'))==1)
        log('home: no errors (2)',not errs,errs); await ctx.close()
        # keyboard, small phones, 200% zoom, dark, reduced motion
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(BATCH(2),F))
        await pg.focus('#fzList [data-fo="e3"]'); await pg.keyboard.press('Tab'); a=await pg.evaluate("[document.activeElement.dataset.ate,getComputedStyle(document.activeElement).outlineStyle]"); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        s=await pg.evaluate(FZROWS)
        log('keyboard: Tab from a row to its Ate one with a focus ring, Enter eats one',a==['e3','solid'] and s['rows'][0]['s'].startswith('1 left'),(a,s['rows'][0]['s']))
        await pg.click('#fzList [data-fo="e3"]'); await pg.wait_for_timeout(200); tt=await pg.evaluate("document.querySelector('#toast span').textContent")
        log('desktop: the missing-batch line says device, not phone',tt=="This batch isn't saved on this device",tt)
        await ctx.close()
        for w,h in ((320,568),(195,422)):
            for sch in ('light','dark'):
                ctx,pg,errs=await fresh(b,w=w,h=h,pre=seed(BATCH(2),F+[FZ('e9','b1','A very long dish name that keeps going and going for a while yes','2026-11-12',100,4)]),color_scheme=sch)
                r=await pg.evaluate("(()=>{const f=document.getElementById('fz'),q=(e)=>e.getBoundingClientRect();return {ow:document.documentElement.scrollWidth<=innerWidth,small:[...f.querySelectorAll('button')].filter(b=>q(b).height<43.9).length,which:[...f.querySelectorAll('button')].filter(b=>q(b).height<43.9).map(b=>[b.className,b.textContent,q(b).height,q(b).width]),out:[...f.querySelectorAll('button,b,span,p,h3,h4')].filter(e=>q(e).right>q(f).right+0.5||q(e).left<q(f).left-0.5).length}})()")
                await sample(pg); await tab(pg,'store'); r2=await pg.evaluate("document.documentElement.scrollWidth<=innerWidth")
                log(f'{w}px {sch}: freezer card and Store tab fit, buttons 44 high, nothing pokes out',r['ow'] and r['small']==0 and r['out']==0 and r2 and not errs,(r,r2,errs)); await ctx.close()
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(2),F),reduced_motion='reduce')
        await pg.tap('#fzList [data-ate="e2"][data-p="z"]'); await pg.wait_for_timeout(300); await sample(pg); await tab(pg,'store'); await pg.tap('#didGo'); await pg.wait_for_timeout(300)
        log('reduced motion: ate one and I cooked this work, no errors',len([x for x in await pg.evaluate(LSJ,'bd-freezer') if x.get('id')])==6 and not errs,errs); await ctx.close()
        # ---------- 5. backup and restore ----------
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(BATCH(2),F))
        async with pg.expect_download() as di: await pg.click('#bkUp')
        data=json.loads(open(await (await di.value).path()).read())
        log('backup: the file carries the freezer (the readable entries)',[x['id'] for x in data['freezer']]==['e2','e1','e3','e4'] and data['freezer'][0]==FZ('e2','b1','Soup 1','2026-11-10',10,4,at=1763000000002) and data['freezer'][3].get('zx')==1,[x['id'] for x in data['freezer']]); await ctx.close()
        async def restore(pg,obj):
            await pg.set_input_files('#bfile',files=[{'name':'b.json','mimeType':'application/json','buffer':json.dumps(obj).encode() if not isinstance(obj,bytes) else obj}]); await pg.wait_for_timeout(350)
            return await pg.evaluate("document.querySelector('#toast span').textContent")
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False)
        t=await restore(pg,data); s=await pg.evaluate(FZROWS)
        log('restore: on an empty device the batches and the freezer come back',t=='Restored 2 batches' and s['sum']=='20 meals in the freezer' and len(await pg.evaluate(LSJ,'bd-freezer'))==4 and not s['hidden'],(t,s['sum']))
        await pg.click('#fzList [data-fo="e2"]'); await pg.wait_for_timeout(500)
        log('restore: a restored row opens its restored batch',await pg.inner_text('#sTitle')=='Soup 1'); await ctx.close()
        # merge by id: newer copy wins, older is ignored, nothing here is removed
        here=[FZ('e2','b1','Soup 1','2026-11-10',3,0,10,4,at=1763000009999),FZ('e1','b0','Soup 0','2026-11-02',9,4,10,4,at=1700000000000),FZ('mine','b0','Only here','2026-11-13',5,4)]
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(BATCH(2),here))
        t=await restore(pg,data); st={x['id']:x for x in await pg.evaluate(LSJ,'bd-freezer')}
        log('restore: merged by entry id. Newer here is kept, older here is updated, new ones added, nothing removed',sorted(st)==['e1','e2','e3','e4','mine'] and st['e2']['fz']==3 and st['e1']['fr']==0 and st['e1']['at']==1763000000001 and st['mine']['fz']==5 and t=='Restored',(t,{k:(v['fz'],v['fr']) for k,v in st.items()}))
        t=await restore(pg,data)
        log('restore: the same file again changes nothing',t=='Nothing new in that file' and len(await pg.evaluate(LSJ,'bd-freezer'))==5,t)
        bad=dict(data); bad['freezer']=data['freezer']+[{'id':'x','title':'T','date':'soon','fz':1,'fr':0,'fz0':1,'fr0':0,'at':1}]
        t=await restore(pg,bad)
        log('restore: one bad freezer entry and the whole file is refused',t=="That file isn't a batch.recipes backup" and len(await pg.evaluate(LSJ,'bd-freezer'))==5,t)
        bad2=dict(data); bad2['freezer']=[FZ('neg','b0','T','2026-11-01',5,0,2,0)]
        log('restore: more left than was cooked is refused too',await restore(pg,bad2)=="That file isn't a batch.recipes backup")
        old={k:v for k,v in data.items() if k!='freezer'}
        t=await restore(pg,old)
        log('restore: a backup from before the freezer still restores',t=='Nothing new in that file' and not errs,(t,errs)); await ctx.close()
        # the same recipe is here under another id: the freezer row follows it
        mine=[dict(BATCH(1)[0],id='local7')]
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(mine,[]))
        await restore(pg,{'app':'batch.recipes','v':1,'at':'2026-11-14T00:00:00.000Z','batches':BATCH(1),'freezer':[FZ('e1','b0','Soup 0','2026-11-02',9,4)],'settings':{'theme':None,'staples':[]}})
        st=await pg.evaluate(LSJ,'bd-freezer'); await pg.click('#fzList [data-fo="e1"]'); await pg.wait_for_timeout(500)
        log('restore: a row whose batch is already here under another id points at that one, and opens it',st[0]['bid']=='local7' and len(await pg.evaluate(LSJ,'bd-batches'))==1 and await pg.inner_text('#sTitle')=='Soup 0',st[0]['bid'])
        log('restore: no errors',not errs,errs); await ctx.close()
        # ---------- 6. labels with a QR ----------
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,device_scale_factor=4); await sample(pg); await tab(pg,'store')
        g=await pg.evaluate("""(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),l=q('#lblPrev .lbl'),s=q('#lblPrev .lq svg'),t=q('#lblPrev .lt'),n=q('#lblPrev .lq span'),b=document.querySelector('#lblPrev b'),R=(x)=>Math.round(x*100)/100,rows=[...document.querySelectorAll('#lblPrev .lt>div')].map(e=>e.getBoundingClientRect());
          return {lbl:[R(l.width),R(l.height)],qr:[R(s.width),R(s.height)],top:R(s.top-l.top),right:R(l.right-s.right),textLeft:R(t.left-l.left),gap:R(s.left-t.right),below:R(n.top-s.bottom),countBottom:R(l.bottom-n.bottom),countMid:R((n.left+n.right)/2-(s.left+s.right)/2),
            rowGaps:rows.slice(1).map((r,i)=>R(r.top-rows[i].bottom)),firstTop:R(rows[0].top-l.top),lastBottom:R(l.bottom-rows[3].bottom),titleFits:b.scrollWidth<=b.clientWidth,pt:b.style.fontSize,count:document.querySelector('#lblPrev .lq span').textContent,saved:localStorage.getItem('bd-batches')}})()""")
        log('label: QR is 0.62 in square (59.52 px) on the 1 in label',g['lbl']==[252,96] and g['qr']==[59.52,59.52],(g['lbl'],g['qr']))
        log('label: QR sits on the label\'s own padding (0.08 in top, 0.14 in right), text 0.14 in from the left, 0.1 in between',abs(g['top']-7.68)<.1 and abs(g['right']-13.44)<.1 and abs(g['textLeft']-13.44)<.1 and abs(g['gap']-9.6)<.1,g)
        log('label: "1 of 14" stays, centred under the code, on the bottom padding, clear of the code',g['count']=='1 of 14' and abs(g['countMid'])<.6 and abs(g['countBottom']-7.68)<.6 and g['below']>=8,(g['count'],g['countMid'],g['countBottom'],g['below']))
        log('label: four rows of words spaced evenly, first and last on the padding',max(g['rowGaps'])-min(g['rowGaps'])<=.5 and min(g['rowGaps'])>=2 and abs(g['firstTop']-7.68)<.6 and abs(g['lastBottom']-7.68)<.6,(g['rowGaps'],g['firstTop'],g['lastBottom']))
        log('label: the dish shrinks to fit beside the code, not cut',g['titleFits'] and g['pt'] in ('11pt','10.5pt','10pt','9.5pt','9pt'),g['pt'])
        log('label: looking at the sample still saves nothing',g['saved'] is None)
        sc=scan(await pg.locator('#lblPrev .lbl').screenshot())
        log('label: the code on screen scans as https://batch.recipes/#b=<id>',len(sc)==1 and re.fullmatch(r'https://batch\.recipes/#b=[a-z0-9]+',sc[0][0]) is not None,sc)
        cvt=scan_cv(await pg.locator('#lblPrev .lbl').screenshot())
        log('label: OpenCV reads the same',bool(sc) and cvt==sc[0][0],cvt)
        url=sc[0][0] if sc else ''; bid=url.split('#b=')[-1]
        # print: all 14, each scans, and the id is the one the batch is saved under
        await pg.click('#lblPrint'); await pg.wait_for_timeout(300); await pg.emulate_media(media='print')
        saved=await pg.evaluate(LSJ,'bd-batches'); shot=await pg.locator('.lsheet').first.screenshot(); await pg.evaluate("0"); sc=scan(shot)
        open('freezer-shots/labels-print-qr-desktop.png','wb').write(shot)
        log('label: printing saves the batch under the id the code carries',len(saved)==1 and saved[0]['id']==bid,(bid,saved and saved[0]['id']))
        log('label: all 14 printed labels scan to that link',len(sc)==14 and {t for t,_ in sc}=={url},(len(sc),{t for t,_ in sc}))
        log('label: printed code is at least 0.6 in across',bool(sc) and min(w for _,w in sc)/4/96>=.6,[round(w/4/96,3) for _,w in sc][:3])
        pg9=await pg.evaluate("(()=>{const ls=[...document.querySelectorAll('#labels .lbl')];return {n:ls.length,nums:ls.map(e=>e.querySelector('.lq span').textContent),w:[...new Set(ls.map(e=>Math.round(e.getBoundingClientRect().width*100)/100))],h:[...new Set(ls.map(e=>Math.round(e.getBoundingClientRect().height*100)/100))],over:ls.filter(e=>e.scrollHeight>e.clientHeight+1||e.scrollWidth>e.clientWidth+1).length}})()")
        log('label: print keeps 1 of 14 to 14 of 14 at 2.625 x 1 in, nothing overflows',pg9['n']==14 and pg9['nums']==[f'{k} of 14' for k in range(1,15)] and pg9['w']==[252] and pg9['h']==[96] and pg9['over']==0,pg9)
        await pg.emulate_media(media='screen'); await pg.evaluate("dispatchEvent(new Event('afterprint'))")
        # image strip
        dls=[]; pg.on('download',lambda d:dls.append(d)); await pg.click('#lblImg'); await pg.wait_for_timeout(1200)
        png=open(await dls[0].path(),'rb').read() if dls else b''; im=Image.open(io.BytesIO(png)) if png else None
        open('freezer-shots/labels-strip-qr.png','wb').write(png)
        sc=scan(png) if png else []
        log('label: the image strip is 788 x 300 a label, and all 14 codes scan to the link',bool(im) and im.size==(788,4200) and len(sc)==14 and {t for t,_ in sc}=={url},(im and im.size,len(sc)))
        log('label: code in the strip is 0.62 in at 300 dpi (186 px)',bool(sc) and all(abs(w-186)<=8 for _,w in sc),[round(w) for _,w in sc][:3])
        if im:
            a=np.array(im.convert('L').crop((0,0,788,300)))<128; ys,xs=np.where(a[:,560:]); qx0,qx1,qy0=560+xs.min(),560+xs.max(),ys.min()
            left=np.where(a[:,:560].any(axis=0))[0]
            log('label: strip layout matches the print (code 0.08 in from the top, 0.14 in from the right, words 0.14 in from the left)',abs(qy0-24)<=2 and abs(787-qx1-42)<=3 and abs(left.min()-42)<=4,(int(qy0),int(787-qx1),int(left.min())))
        # reheat line and no date, with the code
        await ctx.close()
        RH='Lentil soup\nServes 4\n2 cups lentils\n1 onion\n6 cups broth\n1. Simmer 40 minutes.\n2. To reheat, microwave 2.5 minutes and stir. Add a splash of water if it has gone thick.'
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,device_scale_factor=4); await pg.click('#pasteToggle'); await pg.fill('#paste',RH); await pg.click('#usePaste'); await pg.wait_for_timeout(700); await tab(pg,'store'); await pg.fill('#lblDate',''); await pg.wait_for_timeout(150)
        r=await pg.evaluate("(()=>{const l=document.querySelector('#lblPrev .lbl'),rows=[...l.querySelectorAll('.lt>div')];return {over:l.scrollHeight>l.clientHeight+1,rh:rows[3].textContent,cooked:rows[1].querySelectorAll('i').length,inside:rows[3].getBoundingClientRect().bottom<=l.getBoundingClientRect().bottom-7}})()")
        sc=scan(await pg.locator('#lblPrev .lbl').screenshot())
        log('label: reheat line and a blank Cooked line fit beside the code, and it still scans',not r['over'] and r['rh']=='To reheat, microwave 2.5 minutes and stir.' and r['cooked']==1 and r['inside'] and len(sc)==1,r)
        await pg.locator('#lblPrev').screenshot(path='freezer-shots/label-reheat-nodate.png'); await ctx.close()
        # a batch whose id is too long for a small code: the old label, no code
        longb=[dict(BATCH(1)[0],id='L'*120)]
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(longb,[])); await pg.click('#savedList .open'); await pg.wait_for_timeout(600); await tab(pg,'store')
        r=await pg.evaluate("({svg:document.querySelectorAll('#lblPrev svg').length,rows:document.querySelectorAll('#lblPrev .lbl>div').length,t:document.querySelector('#lblPrev .lbl').innerText.replace(/\\s+/g,' ').trim()})")
        log('label: an id too long for the code prints the plain label',r['svg']==0 and r['rows']==3 and r['t'].startswith('Soup 0 1 of 14 Cooked') and not errs,r); await ctx.close()
        # the id holds still: the same text pasted again keeps its id
        ctx,pg,errs=await fresh(b,w=1280,h=900,mob=False,pre=seed(BATCH(2),[FZ('e1','b1','Soup 1','2026-11-02',9,4)]))
        await pg.click('#pasteToggle'); await pg.fill('#paste',SOUP(1)); await pg.click('#usePaste'); await pg.wait_for_timeout(700)
        ids=[x['id'] for x in await pg.evaluate(LSJ,'bd-batches')]
        log('ids: pasting a saved recipe again keeps its id, so old labels and freezer rows still open it',sorted(ids)==['b0','b1'],ids); await ctx.close()
        # ---------- 7. #b= links ----------
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(3),[]),go=U+'#b=b1')
        r=await pg.evaluate("({t:document.getElementById('sTitle').textContent,sheet:!document.getElementById('v-sheet').classList.contains('hidden'),hash:location.hash,ev:window.__ev.filter(e=>e[0]==='Freezer open').map(e=>e[1])})")
        log('link: #b=<id> opens that batch',r['t']=='Soup 1' and r['sheet'] and r['ev']==[{'src':'direct','from':'label','ok':'yes'}],r)
        await pg.go_back(); await pg.wait_for_timeout(400)
        log('link: Back goes to the home page',await pg.evaluate(VIS,'#home'))
        await pg.evaluate("location.hash='#b=b2'"); await pg.wait_for_timeout(600)
        log('link: scanning another label while the page is open opens that one',await pg.inner_text('#sTitle')=='Soup 2' and '#b=' not in await pg.evaluate('location.hash'),await pg.evaluate('location.hash')); await ctx.close()
        for nm,kw,word in (('phone',dict(),'phone'),('desktop',dict(w=1280,h=900,mob=False),'device')):
            ctx,pg,errs=await fresh(b,pre=seed(BATCH(1),[]),go=U+'#b=nope',**kw)
            r=await pg.evaluate("({vis:!document.getElementById('noB').classList.contains('hidden'),t:document.getElementById('noB').innerText.trim(),role:document.getElementById('noB').getAttribute('role'),home:!document.getElementById('v-add').classList.contains('hidden'),hash:location.hash,above:document.getElementById('noB').getBoundingClientRect().bottom<=document.getElementById('dropcard').getBoundingClientRect().top,ev:window.__ev.filter(e=>e[0]==='Freezer open').map(e=>e[1])})")
            log(f'link ({nm}): a batch that is not on this {word} says so plainly, on the page, and stays',r['vis'] and r['t']==f"This batch isn't saved on this {word}." and r['role']=='status' and r['home'] and r['hash']=='' and r['above'] and r['ev']==[{'src':'direct','from':'label','ok':'no'}],r)
            await pg.wait_for_timeout(3200); still=await pg.evaluate(VIS,'#noB')
            if nm=='phone': await pg.screenshot(path='breakit/9-not-here.png')
            await sample(pg); await pg.go_back(); await pg.wait_for_timeout(400)
            log(f'link ({nm}): still there after 3 s, gone once a recipe has been opened',still and not await pg.evaluate(VIS,'#noB') and not errs,errs); await ctx.close()
        ctx,pg,errs=await fresh(b,go=U+'#b=nope')
        log('link: a first visit from a label gets the plain line, not the tour offer',await pg.evaluate(VIS,'#noB') and not await pg.evaluate(VIS,'#tourOffer')); await ctx.close()
        for h in ('#b=','#b=%E0%A4%A','#b=<img src=x onerror=alert(1)>','#b='+'z'*5000):
            ctx,pg,errs=await fresh(b,pre=seed(BATCH(1),[]),go=U+h)
            log(f'link: odd link {h[:24]!r} is handled',await pg.evaluate(VIS,'#noB') and await pg.evaluate("document.querySelectorAll('#noB img').length")==0 and not errs,errs); await ctx.close()
        ctx,pg,errs=await fresh(b,pre=seed(BATCH(1),[]),go=U+'#r=AAAA')
        log('link: shared recipe links (#r=) still go their own way',not await pg.evaluate(VIS,'#noB') and await pg.evaluate("document.querySelector('#toast span').textContent")=="That link didn't open"); await ctx.close()
        # ---------- 8. the page itself ----------
        html=open('site/index.html').read()
        log('build: impact-site-verification tag and AFF are still there','<meta name="impact-site-verification" value="44a0832b-93ba-4379-b2a0-530627c39acf">' in html and "const AFF={instacart:'',amazonTag:'batchrecipes-20'}" in html)
        log('build: QR encoder is inline, no new script or host',html.count('<script')==6 and 'BatchQR' in html and len(re.findall(r"'sha256-",html))==4,html.count('<script'))
        ui=re.sub(r'<svg.*?</svg>','',html[html.index('<main'):html.index('<script>\n/* Batch Day engine')],flags=re.S)
        log('copy: no em dash in the page\'s words','—' not in ui)
        await b.close()
    bad=[r for r in R if r[1]=='FAIL']; print(f'\n{len(R)-len(bad)} of {len(R)} ok')
asyncio.run(main())
