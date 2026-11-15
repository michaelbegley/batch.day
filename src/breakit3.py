# Checks for the fixes made after the round-2 stress test. Readers are mocked; the live reader is never called.
import asyncio, json, base64, zlib
from playwright.async_api import async_playwright
U='http://localhost:8765/'
SHOTS=[f'/home/claude/test-shots/chicken{i}.jpg' for i in (1,2,3,4)]
TXT=open('/tmp/sample.txt').read()
R=[]
def log(name,ok,note=''):
    R.append((name,'ok' if ok else 'FAIL',str(note))); open('breakit/r3.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',name,'|',str(note)[:300])
VIEW="['v-add','v-sheet'].find(i=>!document.getElementById(i).classList.contains('hidden'))"
STATE="document.getElementById('reading').classList.contains('hidden')?'pick':document.getElementById('reading').dataset.state"
EV="window.__ev.filter(e=>e.name!=='Visit').map(e=>{const d=Object.assign({},e.data);delete d.src;const v=Object.values(d);return e.name+(v.length?':'+v.join('/'):'')})"  # Visit and src (added 14 Nov) are checked separately
N="JSON.parse(localStorage.getItem('bd-batches')||'[]').length"
FOC="(()=>{const e=document.activeElement;return e.id||e.className||e.tagName})()"
TESS="window.Tesseract={createWorker:async(l,n,o)=>({recognize:async()=>{await new Promise(r=>setTimeout(r,60));return{data:{text:window.__tt}}},terminate:async()=>{}})};"
def link(o,pre='z'):
    raw=json.dumps(o).encode()
    if pre=='z': c=zlib.compressobj(9,zlib.DEFLATED,-15); raw=c.compress(raw)+c.flush()
    return '#r='+pre+base64.urlsafe_b64encode(raw).decode().rstrip('=')
async def fresh(b,reader='ok',delay=0,tess=True,w=390,h=844,tt=None):
    ctx=await b.new_context(viewport={'width':w,'height':h}); pg=await ctx.new_page(); errs=[]; calls=[]
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    await ctx.add_init_script("document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective));window.__ev=[];window.va=function(a,b){window.__ev.push(b)};"+f"window.__tt={json.dumps(TXT if tt is None else tt)};"+(TESS if tess else ''))
    async def read(route):
        calls.append(len(json.loads(route.request.post_data)['images']))
        if delay: await asyncio.sleep(delay)
        try:
            if reader=='ok': await route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'text':TXT}))
            else: await route.abort()
        except Exception: pass
    await ctx.route('**/*.hf.space/**',read); await ctx.route('**/cdn.jsdelivr.net/**',lambda r:r.abort()); await ctx.route('**/pagead2.googlesyndication.com/**',lambda r:r.abort()); await ctx.route('**/*.umami.is/**',lambda r:r.abort())
    await pg.goto(U); await pg.wait_for_timeout(300)
    return ctx,pg,errs,calls
async def sheet(pg,t=6000):
    try: await pg.wait_for_selector('#v-sheet:not(.hidden)',timeout=t); await pg.wait_for_timeout(250); return True
    except Exception: return False
async def paste(pg,text):
    await pg.click('#pasteToggle'); await pg.fill('#paste',text); await pg.click('#usePaste'); await pg.wait_for_timeout(500)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # B1 cap
        ctx,pg,errs,_=await fresh(b)
        await pg.evaluate("localStorage.setItem('bd-batches',JSON.stringify(Array.from({length:200},(_,i)=>({id:'i'+i,title:'Saved '+i,text:'1 lb chicken '+i+'\\n1. Cook.',y:4,w:14,m:'batch',at:Date.now()-i*1e6}))))"); await pg.reload(); await pg.wait_for_timeout(300)
        await pg.click('#sample'); await pg.click('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(300)
        n=await pg.evaluate(N); vis=await pg.is_visible('#fullNote'); txt=await pg.inner_text('#fullNote') if vis else ''
        log('B1 at 200 a new batch is not saved and nothing is dropped',n==200 and vis and await pg.is_hidden('#savedNote'),f'stored={n} note={txt!r}')
        await pg.click('#fullGo'); await pg.wait_for_timeout(500); foc=await pg.evaluate(FOC)
        await pg.click('#savedList .rm >> nth=0'); await pg.wait_for_timeout(200); await pg.go_back(); await pg.wait_for_timeout(400)
        n2=await pg.evaluate(N); log('B1 remove one, go back: it saves',await pg.evaluate(VIEW)=='v-sheet' and n2==200 and await pg.is_hidden('#fullNote') and await pg.is_visible('#savedNote') and not errs,f'focus after My batches={foc} stored={n2} errs={errs[:2]}'); await ctx.close()
        ctx,pg,errs,_=await fresh(b)
        await pg.evaluate("localStorage.setItem('bd-batches',JSON.stringify(Array.from({length:260},(_,i)=>({id:'i'+i,title:'Saved '+i,text:'1 lb chicken '+i+'\\n1. Cook.',y:4,w:14,m:'batch',at:Date.now()-i*1e6}))))"); await pg.reload(); await pg.wait_for_timeout(300)
        await pg.click('#savedList .open >> nth=250'); await pg.wait_for_timeout(300); await pg.click('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(200)
        log('B1 260 legacy batches: editing one keeps all 260',await pg.evaluate(N)==260 and await pg.is_hidden('#fullNote'),await pg.evaluate(N)); await ctx.close()
        # B2 bad files
        F='/home/claude/bk2/files/'
        ctx,pg,errs,calls=await fresh(b); await pg.set_input_files('#file',SHOTS[:3]+[F+'zero.jpg',F+'text.jpg']); ok=await sheet(pg)
        al=await pg.inner_text('#alerts'); ev=await pg.evaluate(EV)
        log('B2 3 good + 2 bad files: reads the 3',ok and calls==[3] and "2 files couldn't be opened" in al and 'AI read:3/ok' in ev and not errs,f'calls={calls} alert={al!r} ev={ev}'); await ctx.close()
        ctx,pg,errs,calls=await fresh(b); await pg.set_input_files('#file',[F+'zero.jpg',F+'photo.heic']); await pg.wait_for_timeout(800)
        ev=await pg.evaluate(EV); ti=await pg.inner_text('#rdTitle'); st=await pg.inner_text('#status'); tiles=await pg.locator('#thumbs .th').count()
        log('B2 only bad files: own message, AI not called or blamed',calls==[] and await pg.evaluate(STATE)=='fail' and ti=="Those files couldn't be opened" and ev==['AI read:2/badfile'] and tiles==0 and not errs,f'{ti!r} {st!r} ev={ev} tiles={tiles}')
        await pg.go_back(); await pg.wait_for_timeout(300); log('B2 Back from that state returns home',await pg.evaluate(STATE)=='pick' and await pg.is_visible('#choose') and 'localhost' in pg.url,pg.url); await ctx.close()
        # B3 ticks
        ctx,pg,errs,_=await fresh(b); await pg.click('#sample'); await pg.wait_for_timeout(300)
        await pg.click('.checks label:has(input[data-k="boneless chicken thighs"])'); await pg.click('.checks label:has(input[data-k="ginger paste"])'); await pg.wait_for_timeout(200); await pg.reload(); await pg.wait_for_timeout(500)
        t1=await pg.locator('.checks input:checked').count()
        for _ in range(3): await pg.click('[data-t=want][data-d="1"]')
        t2=await pg.locator('.checks input:checked').count(); await pg.click('#newRec'); await pg.click('#savedList .open >> nth=0'); await pg.wait_for_timeout(300)
        t3=await pg.locator('.checks input:checked').count()
        log('B3 ticks survive reload, stepper and reopen',t1==2 and t2==2 and t3==2 and not errs,f'{t1}/{t2}/{t3}')
        await pg.click('[data-tab=recipe]'); await pg.click('#edit summary'); v=await pg.input_value('#text'); await pg.fill('#text',v.replace('boneless chicken thighs','pork shoulder')); await pg.wait_for_timeout(600); await pg.click('#reparse'); await pg.wait_for_timeout(300); await pg.click('[data-tab=shop]')  # round 3: Update scrolls to where Edit the text was tapped; a tap there within half a second is taken as a stray, so wait as a person would
        log('B3 a tick goes when its item text changes',await pg.locator('.checks input:checked').count()==1,''); await ctx.close()
        # B4 links
        ctx,pg,errs,_=await fresh(b)
        bomb=link({'v':1,'t':'Big\nServes 4\n'+'\n'.join(f'{i} cups rice number {i}' for i in range(200000)),'y':4,'w':14,'m':'batch'})
        import time; t0=time.time(); await pg.goto(U+bomb); await pg.wait_for_timeout(1500)
        log('B4 deflate bomb link refused fast, nothing saved',await pg.evaluate(VIEW)=='v-add' and await pg.evaluate(N)==0 and "didn't open" in await pg.inner_text('#toast'),f'link={len(bomb)//1000} KB in {time.time()-t0:.1f}s toast={await pg.inner_text("#toast")!r}')
        for nm,o in [('21 KB text',{'v':1,'t':'A\nServes 4\n'+'1 cup rice\n'*2100,'y':4,'w':14}),('empty text',{'v':1,'t':'','y':4,'w':14}),('spaces',{'v':1,'t':'  \n ','y':4,'w':14})]:
            await pg.goto(U); await pg.goto(U+link(o)); await pg.wait_for_timeout(700)
            log('B4/M10 link with '+nm+' is refused',await pg.evaluate(VIEW)=='v-add' and await pg.evaluate(N)==0 and "didn't open" in await pg.inner_text('#toast'),'')
        await pg.goto(U); await pg.goto(U+link({'v':1,'t':TXT,'y':4,'w':10,'m':'batch'},'p')); await pg.wait_for_timeout(700)
        log('B4 normal legacy p link still opens',await pg.evaluate(VIEW)=='v-sheet' and await pg.input_value('#want')=='10' and not errs,''); await ctx.close()
        # L1
        ctx,pg,errs,_=await fresh(b); await pg.click('#sample'); await pg.wait_for_timeout(300)
        log('L1 copy textarea is hidden',await pg.evaluate("getComputedStyle(document.getElementById('glist')).display")=='none',''); 
        # L5 focus on recipe page, share trap, cook trap, live region
        f1=await pg.evaluate(FOC); await pg.click('#dShare'); seen=[]
        for _ in range(6): await pg.keyboard.press('Tab'); seen.append(await pg.evaluate("!!document.activeElement.closest('#menu')"))
        await pg.keyboard.press('Escape'); f2=await pg.evaluate(FOC)
        await pg.click('#dCook'); await pg.wait_for_timeout(200); seen2=[]
        for _ in range(8): await pg.keyboard.press('Tab'); seen2.append(await pg.evaluate("!!document.activeElement.closest('#cook')"))
        await pg.keyboard.press('ArrowRight'); live=await pg.inner_text('#cLive'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300); f3=await pg.evaluate(FOC)
        log('L5 focus: heading on build, Tab trapped in share and cook, back to buttons',f1=='sTitle' and all(seen) and f2=='dShare' and all(seen2) and f3=='dCook' and live.startswith('Step 2 of') and not errs,f'{f1} {seen} {f2} {seen2} {f3} live={live!r}'); await ctx.close()
        ctx,pg,errs,_=await fresh(b,delay=2); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(500)
        log('L5 focus moves to the reading heading',await pg.evaluate(FOC)=='rdTitle',await pg.evaluate(FOC))
        # L2 back during reading
        await pg.go_back(); await pg.wait_for_timeout(2600)
        log('L2 Back while reading cancels and stays on the site',pg.url.startswith(U) and await pg.evaluate(STATE)=='pick' and await pg.is_visible('#choose') and await pg.evaluate(VIEW)=='v-add' and 'Plan' not in str(await pg.evaluate(EV)) and not errs,f'{pg.url} ev={await pg.evaluate(EV)}')
        await pg.set_input_files('#file',SHOTS[:1]); ok=await sheet(pg); await pg.go_back(); await pg.wait_for_timeout(300); v=await pg.evaluate(VIEW); st=await pg.evaluate(STATE); await pg.go_back(); await pg.wait_for_timeout(300)
        log('L2 after a read, one Back goes home (no extra reading entry)',ok and v=='v-add' and st=='pick' and not pg.url.startswith(U),f'{v} {st} then {pg.url}'); await ctx.close()
        ctx,pg,errs,_=await fresh(b,delay=2); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(500); await pg.click('#rdCancel'); await pg.wait_for_timeout(400)
        await pg.go_back(); await pg.wait_for_timeout(300); log('L2 Cancel pops the reading entry',not pg.url.startswith(U),pg.url); await ctx.close()
        # L3 195 px
        ctx,pg,errs,_=await fresh(b,w=195,h=422); await pg.click('#sample'); await pg.wait_for_timeout(400); over={}
        OV="(()=>{const W=document.documentElement.clientWidth;const bad=[...document.querySelectorAll('body *')].filter(e=>{if(!e.offsetParent&&getComputedStyle(e).position!=='fixed')return false;if(e.closest('.sr'))return false;const r=e.getBoundingClientRect();return r.width>0&&(r.right>W+1||e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflowX==='visible'&&!e.children.length)}).slice(0,3).map(e=>e.tagName+'.'+e.className+'#'+e.id+':'+Math.round(e.getBoundingClientRect().right));return [document.documentElement.scrollWidth,bad]})()"
        over['home->shop']=await pg.evaluate(OV)
        for t in ['cook','store','recipe']:
            await pg.click(f'[data-tab={t}]'); await pg.wait_for_timeout(150); over[t]=await pg.evaluate(OV)
        await pg.click('#edit summary'); over['edit']=await pg.evaluate(OV); await pg.screenshot(path='breakit/195-recipe.png',full_page=True)
        await pg.click('[data-m=scale]'); await pg.wait_for_timeout(150); over['scale']=await pg.evaluate(OV); await pg.click('[data-m=batch]')
        await pg.click('#dShare'); await pg.wait_for_timeout(150); over['share']=await pg.evaluate(OV); await pg.keyboard.press('Escape')
        await pg.click('#dCook'); await pg.wait_for_timeout(300); over['cook mode']=await pg.evaluate(OV); nx=await pg.evaluate("(()=>{const r=document.getElementById('cNext').getBoundingClientRect();return [Math.round(r.right),document.getElementById('cNext').scrollWidth<=document.getElementById('cNext').clientWidth]})()"); await pg.screenshot(path='breakit/195-cook.png')
        await pg.click('#cNext'); await pg.wait_for_timeout(200); over['cook step 2']=await pg.evaluate(OV); await pg.keyboard.press('Escape')
        for pgn in ['privacy.html','about.html']:
            await pg.goto(U+pgn); over[pgn]=[await pg.evaluate('document.documentElement.scrollWidth'),[]]
        bad={k:v for k,v in over.items() if v[0]>195 or v[1]}
        log('L3 195 px: no sideways scroll or clipped text anywhere',not bad and nx[0]<=195 and nx[1],f'bad={bad} Next right edge={nx}'); await ctx.close()
        # L4 titles
        ctx,pg,errs,_=await fresh(b); out=[]
        for t in ['宫保鸡丁','دجاج بالأرز','Crème brûlée #fyp #food','🍗 Chicken 🔥 bowl','#fyp #viral']:
            await pg.goto(U); await paste(pg,t+'\nServes 4\n2 lbs chicken\n1 cup rice\n1. Cook it all.'); out.append(await pg.inner_text('#sTitle'))
        log('L4 titles keep other scripts, drop hashtags',out[0]=='宫保鸡丁' and out[1]=='دجاج بالأرز' and out[2]=='Crème brûlée' and out[4]=='Your recipe',out)
        saved=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).map(x=>x.title)"); log('L4 saved under the real title','宫保鸡丁' in saved,saved)
        # M3 cut off
        al=[]
        for last in ['1. Cook','1. Cook the rice and','1. Simmer until,','1. Stir in the']:
            await pg.goto(U); await paste(pg,'Rice\nServes 4\n2 cups rice\n'+last); al.append('cut off' in await pg.inner_text('#alerts'))
        log('M3 cut-off warning only for a real cut',al==[False,True,True,True],al)
        # M5 odd
        await pg.goto(U); await paste(pg,'Big pot\nServes 4\n99999999 lbs chicken\n1e9 cups rice\n-3 cups water\n2 tsp salt\n1. Cook.')
        a=await pg.inner_text('#alerts'); tags=await pg.locator('.checks .tag').count(); await pg.click('[data-tab=recipe]'); w=await pg.locator('.tbl small.w').count()
        log('M5 odd amounts: alert plus a mark on each row','look off' in a and tags>=2 and w>=2,f'alert={a!r} grocery marks={tags} amount marks={w}')
        # M6 steppers
        await pg.goto(U); await pg.click('#sample'); await pg.wait_for_timeout(300); res=[]
        for v in ['0','-5','0x10','abc','','1e3','7.6','٧','5000',' 9 ']:
            await pg.fill('#want',v); await pg.keyboard.press('Tab'); res.append(await pg.input_value('#want'))
        log('M6 steppers: 1 to 999, whole, last good value otherwise',res==['1','1','1','1','1','1','8','8','999','9'],res)
        # M14
        await pg.goto(U); await pg.click('#sample'); await pg.wait_for_timeout(300)
        for _ in range(3): await pg.click('[data-t=want][data-d="1"]')
        await pg.click('[data-m=scale]'); s1=await pg.input_value('#want'); await pg.click('[data-t=want][data-d="1"]'); await pg.click('[data-m=batch]'); s2=await pg.input_value('#want'); await pg.click('[data-m=scale]'); s3=await pg.input_value('#want')
        log('M14 Just scale starts at the recipe servings; each mode keeps its own number',[s1,s2,s3]==['4','17','5'],[s1,s2,s3]); await ctx.close()
        # M1 returning visit
        ctx,pg,errs,_=await fresh(b); await pg.click('#sample'); await pg.click('[data-t=want][data-d="1"]'); await pg.reload(); await pg.wait_for_timeout(300); a=await pg.evaluate(EV)
        pg2=await ctx.new_page(); await pg2.goto(U); await pg2.wait_for_timeout(300); c=await pg2.evaluate(EV); await pg2.reload(); await pg2.wait_for_timeout(300); d=await pg2.evaluate(EV)
        log('M1 Returning visit: not in the first session, once in a new tab, not on reload','Returning visit' not in a and c.count('Returning visit')==1 and 'Returning visit' not in d,f'{a} | {c} | {d}'); await ctx.close()
        # M2 outcomes
        ctx,pg,errs,_=await fresh(b,reader='down',tt=''); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(1500); ev=await pg.evaluate(EV)
        log('M2 device read that finds nothing is recorded as no','Device read:error/no' in ev,ev); await ctx.close()
        # M9 corrupt entries
        ctx,pg,errs,_=await fresh(b)
        await pg.evaluate("""localStorage.setItem('bd-batches',JSON.stringify([null,7,'x',{id:{a:1},text:'1 cup rice',w:14,at:1},{id:'a',text:'1 cup rice',title:'<b>T</b>',w:'abc',at:'never'},{id:'ok1',title:'Good one',text:'2 cups rice\\n1. Cook.',y:4,w:14,m:'batch',at:Date.now()}]))"""); await pg.reload(); await pg.wait_for_timeout(300)
        rows=await pg.inner_text('#savedList'); await pg.click('#sample'); await pg.click('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(200)
        log('M9 corrupt entries are not listed, and not deleted either','Good one' in rows and 'undefined' not in rows and 'Invalid' not in rows and await pg.locator('#savedList li').count()==2 and await pg.evaluate(N)==7 and not errs,rows.replace('\n',' / ')); await ctx.close()
        # M11 remove then Forward
        ctx,pg,errs,_=await fresh(b); await pg.click('#sample'); await pg.click('[data-t=want][data-d="1"]'); await pg.go_back(); await pg.wait_for_timeout(300)
        await pg.click('#savedList .rm'); await pg.wait_for_timeout(200); f=await pg.evaluate(FOC); await pg.go_forward(); await pg.wait_for_timeout(400)
        log('M11 removed batch does not come back with Forward',await pg.evaluate(VIEW)=='v-add' and await pg.evaluate(N)==0 and not errs,f'focus after remove={f}'); await ctx.close()
        # M13 offline, no device reader
        ctx,pg,errs,calls=await fresh(b,tess=False); await ctx.set_offline(True); await pg.set_input_files('#file',SHOTS[:2]); await pg.wait_for_timeout(1500)
        bt=await pg.inner_text('#rdAgain'); st=await pg.inner_text('#status'); await ctx.set_offline(False); await pg.click('#rdAgain'); ok=await sheet(pg)
        log('M13 offline fail: Try again is the main button and it works once back online',bt=='Try again' and "offline" in st and ok and calls==[2] and not errs,f'{bt!r} {st!r} calls={calls}'); await ctx.close()
        await b.close(); bad=[r for r in R if r[1]=='FAIL']; print(len(R),'checks,',len(bad),'failed')
asyncio.run(main())
