# Phase 1 checks (14 Nov): store sections, staples ("Always have" + Check your pantry), backup and restore.
# Phone viewport with touch unless said. Nothing leaves the machine: the AI reader, analytics, ads and the CDN are blocked.
import asyncio, json, subprocess, re, datetime
from playwright.async_api import async_playwright
U='http://localhost:8765/'
R=[]
def log(name,ok,note=''):
    R.append((name,'ok' if ok else 'FAIL',str(note))); open('breakit/r6.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',name,'|',str(note)[:300])
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective));
window.__ev=[];window.va=function(a,b){window.__ev.push(b)};"""
SHARE="window.__shared=[];navigator.share=async(d)=>{window.__shared.push(d)};"
FSHARE="window.__files=[];window.__mode='ok';navigator.canShare=(d)=>window.__mode!=='cant'&&!!(d&&d.files);navigator.share=async(d)=>{if(window.__mode==='abort'){const e=new Error('x');e.name='AbortError';throw e}window.__files.push(d.files?{name:d.files[0].name,type:d.files[0].type,text:await d.files[0].text(),keys:Object.keys(d)}:d)};"
PERSIST="window.__persist=0;try{Object.defineProperty(navigator,'storage',{value:{persist:()=>{window.__persist++;return Promise.resolve(false)}},configurable:true})}catch(e){}"
REC2="Weeknight stir fry\nServes 4\n1 lb chicken breast\n2 tbsp Soy Sauce\n1 tbsp neutral oil\n2 bell peppers\n1 cup jasmine rice\n1 tsp salt\n1. Cook the rice.\n2. Stir fry the rest."
def batch(i,at,text=None,title=None,k=None): return {'id':'b%d'%i,'title':title or 'Batch %d'%i,'text':text or ('Batch %d\nServes 4\n1 lb chicken %d\n1 cup rice\n1. Cook.'%(i,i)),'y':4,'w':14,'m':'batch','at':at,'k':k or []}
def bfile(o,name='batch-recipes-backup-2026-11-14.json'): return {'name':name,'mimeType':'application/json','buffer':(o if isinstance(o,str) else json.dumps(o)).encode()}
def bk(batches,**st): return {'app':'batch.recipes','v':1,'at':'2026-11-14T12:00:00.000Z','batches':batches,'settings':{'theme':st.get('theme'),'staples':st.get('staples',[])}}
async def fresh(b,init='',mobile=True,**kw):
    ctx=await b.new_context(viewport={'width':390,'height':844} if mobile else {'width':1280,'height':900},is_mobile=mobile,has_touch=mobile,permissions=['clipboard-read','clipboard-write'],accept_downloads=True,**kw); errs=[]
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**'): await ctx.route(pat,lambda r:r.abort())
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
async def toast(pg): return (await pg.inner_text('#toast')).strip()
async def ev(pg,name): return [e['data'] for e in await pg.evaluate('window.__ev') if e and e.get('name')==name]
async def stored(pg): return json.loads(await pg.evaluate("localStorage.getItem('bd-batches')||'[]'"))
async def seed(pg,arr,**ls):
    await pg.evaluate("([a,o])=>{localStorage.setItem('bd-batches',JSON.stringify(a));for(const k in o)localStorage.setItem(k,o[k])}",[arr,ls]); await pg.goto(U); await pg.wait_for_timeout(300)
SHOP="(()=>{const c=document.querySelector('[data-panel=shop] .card');return {labels:[...c.querySelectorAll('.aisle')].map(e=>e.textContent),rows:[...c.querySelectorAll('.checks:not(.pan) .tx')].map(e=>e.innerText.trim()),pan:[...c.querySelectorAll('.pan .tx')].map(e=>e.innerText.trim()),ptog:(c.querySelector('#ptog')||{}).innerText||'',open:c.querySelector('#ptog')?c.querySelector('#ptog').getAttribute('aria-expanded'):null,stp:[...c.querySelectorAll('.stp')].filter(e=>e.offsetParent).length,count:document.getElementById('gcount').textContent}})()"
NOW=1794000000000
async def main():
    # --- the pure functions, in node
    out=subprocess.run(['node','test_aisle.js'],capture_output=True,text=True)
    try:
        for n,ok,note in json.loads(out.stdout): log('unit: '+n,ok=='ok',note)
    except Exception as e: log('unit: node test_aisle.js runs',False,out.stderr[:300])
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # --- 3 aisle order
        ctx,pg,errs=await fresh(b,SHARE); await pg.reload(); await pg.wait_for_timeout(300); await sample(pg)
        s=await pg.evaluate(SHOP)
        log('aisle: sample shows its sections in store order',s['labels']==['Produce','Meat & seafood','Canned & jarred','Dry goods & grains','Spices & oils'],s['labels'])
        log('aisle: all 17 items still listed, chicken under Meat, broth under Canned',len(s['rows'])==17 and s['rows'][5].endswith('boneless chicken thighs') and '7 cups chicken bone broth' in s['rows'][6:12],s['rows'][:7])
        log('aisle: no staples yet, so no pantry group and no "Always have" buttons',s['ptog']=='' and s['stp']==0 and await pg.evaluate("localStorage.getItem('bd-staples')") is None)
        await pg.click('[data-copy]'); await pg.wait_for_timeout(200); clip=await pg.evaluate('navigator.clipboard.readText()')
        blocks=clip.split('\n\n'); heads=[x.split('\n')[0] for x in blocks]; flat=[l for x in blocks for l in x.split('\n')[1:]]
        log('aisle: Copy has the section names, items under each, same order as the screen',heads==s['labels'] and len(flat)==17 and flat[0]=='Green onion whites' and flat[5]=='6¼ lb boneless chicken thighs',heads)
        await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200); sent=(await pg.evaluate('window.__shared'))[-1]['text'].split('\n')
        log('aisle: Add to list has no section names and follows the same order',len(sent)==17 and not any(x in sent for x in s['labels']) and sent[0]=='Green onion whites' and sent[5]=='6¼ lb boneless chicken thighs' and sent[-1]=='Chili oil',sent[:6])
        await pg.tap('.checks label >> nth=5'); await pg.wait_for_timeout(300); c1=await pg.inner_text('#gcount'); k=(await stored(pg))[0]['k']
        await pg.reload(); await pg.wait_for_timeout(500); on=await pg.evaluate("[...document.querySelectorAll('.checks input')].map((e,i)=>e.checked?i:-1).filter(i=>i>=0)")
        log('aisle: a tick is counted, saved by item and comes back in the same place',c1=='1 of 17' and k==['boneless chicken thighs'] and on==[5],f'{c1} {k} {on}')
        await pg.evaluate("document.querySelector('#menu [data-share]').click()"); await pg.wait_for_timeout(300); txt=(await pg.evaluate('window.__shared'))[-1]['text']
        shop=txt.split('Shopping\n')[1].split('\n\n')[0].split('\n')
        log('aisle: the shared recipe text lists the shopping in the same order',shop[0]=='- Green onion whites' and shop[5]=='- 6¼ lb boneless chicken thighs' and len(shop)==17,shop[:3])
        ms=[]
        for txt_,want in ((REC2,['Produce','Meat & seafood','Canned & jarred','Dry goods & grains','Spices & oils']),("Chili\nServes 6\n2 lb ground beef\n1 yellow onion\n2 cans kidney beans\n1 can crushed tomatoes\n2 tbsp chili powder\n1 cup shredded cheddar\n1 bag frozen corn\n6 corn tortillas\n1. Brown the beef.\n2. Simmer 40 minutes.",['Produce','Meat & seafood','Dairy & eggs','Bakery','Canned & jarred','Spices & oils','Frozen'])):
            await paste(pg,txt_); ms.append(((await pg.evaluate(SHOP))['labels'],want))
        log('aisle: two more recipes group right (stir fry, chili with dairy, bakery, frozen)',all(a==w for a,w in ms),[a for a,w in ms])
        log('aisle: no errors',not errs,errs); await ctx.close()

        # --- 2 staples
        ctx,pg,errs=await fresh(b,SHARE); await pg.reload(); await pg.wait_for_timeout(300); await sample(pg)
        saved0=len(await stored(pg))
        await pg.tap('#stEdit'); await pg.wait_for_timeout(200); s=await pg.evaluate(SHOP)
        log('staples: "Mark staples" shows an "Always have" button on every row and turns into "Done"',s['stp']==17 and (await pg.inner_text('#stEdit'))=='Done',s['stp'])
        small=await pg.evaluate("[...document.querySelectorAll('.stp,#stEdit')].filter(e=>e.offsetParent).map(e=>e.getBoundingClientRect()).filter(r=>r.height<44||r.width<44).length")
        log('staples: every "Always have" and the Done link are 44px or more',small==0,small)
        await pg.tap('.stp[aria-label="Always have soy sauce"]'); await pg.wait_for_timeout(250); s=await pg.evaluate(SHOP); st=json.loads(await pg.evaluate("localStorage.getItem('bd-staples')"))
        foc=await pg.evaluate("document.activeElement.getAttribute('aria-label')")
        log('staples: marking soy sauce moves it to "Check your pantry (1)", collapsed',s['ptog'].strip()=='Check your pantry (1)' and s['open']=='false' and len(s['rows'])==16 and not any('soy sauce' in r for r in s['rows']) and not await pg.is_visible('#pan'),s['ptog'])
        log('staples: stored as a normalised name in bd-staples',st==['soy sauce'],st)
        log('staples: focus stays in the list, on the next row',foc=='Always have jasmine rice',foc)
        log('staples: marking one on the sample does not save the sample as a batch',len(await stored(pg))==saved0,saved0)
        await pg.tap('.stp[aria-label="Always have Salt & black pepper"]'); await pg.tap('.stp[aria-label="Always have ginger paste"] >> nth=0'); await pg.wait_for_timeout(250)
        s=await pg.evaluate(SHOP); st=json.loads(await pg.evaluate("localStorage.getItem('bd-staples')"))
        log('staples: an item that is on the list twice moves both rows; names are folded',s['ptog'].strip()=='Check your pantry (4)' and len(s['rows'])==13 and st==['soy sauce','salt black pepper','ginger paste'],f"{s['ptog']} {st}")
        await pg.tap('#stEdit'); await pg.wait_for_timeout(150); s=await pg.evaluate(SHOP)
        log('staples: Done hides the buttons on the main list',s['stp']==0 and (await pg.inner_text('#stEdit'))=='Mark staples',s['stp'])
        await pg.tap('.checks label >> nth=0'); await pg.wait_for_timeout(300); c=await pg.inner_text('#gcount')
        log('staples: the count leaves staples out ("1 of 13")',c=='1 of 13',c)
        await pg.tap('#ptog'); await pg.wait_for_timeout(350); s=await pg.evaluate(SHOP)
        log('staples: the group opens and lists them in store order, each with a pressed "Always have"',s['open']=='true' and s['pan']==['1 tbsp ginger paste','2 tbsp ginger paste','1½ tbsp soy sauce','Salt & black pepper'] and s['stp']==4 and await pg.evaluate("[...document.querySelectorAll('.pan .stp')].every(e=>e.getAttribute('aria-pressed')==='true')"),s['pan'])
        hh=await pg.evaluate("(()=>{const r=document.getElementById('ptog').getBoundingClientRect();return [Math.round(r.height),r.width>=44]})()")
        log('staples: the pantry row is a 48px tap target',hh==[48,True],hh)
        await pg.tap('.pan label >> nth=2'); await pg.wait_for_timeout(300); c2=await pg.inner_text('#gcount'); k=(await stored(pg))[0]['k']
        log('staples: a staple can still be ticked; the tick is saved and the count does not move',c2=='1 of 13' and 'soy sauce' in k,f'{c2} {k}')
        clip=''; await pg.click('[data-copy]'); await pg.wait_for_timeout(200); clip=await pg.evaluate('navigator.clipboard.readText()'); last=clip.split('\n\n')[-1].split('\n')
        log('staples: Copy puts them last under "Check your pantry"',last==['Check your pantry','1 tbsp ginger paste','2 tbsp ginger paste','1½ tbsp soy sauce','Salt & black pepper'] and clip.count('soy sauce')==1,last)
        await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200); sent=(await pg.evaluate('window.__shared'))[-1]['text'].split('\n')
        log('staples: Add to list leaves staples (and ticked items) out',len(sent)==12 and not any('soy' in x or 'ginger paste' in x or 'Salt' in x for x in sent) and 'Check your pantry' not in sent,len(sent))
        for _ in range(2): await pg.click('[data-t=want][data-d="1"]')
        await pg.wait_for_timeout(300); s=await pg.evaluate(SHOP)
        log('staples: the group stays open and ticked through a stepper change',s['open']=='true' and len(s['pan'])==4 and await pg.evaluate("document.querySelectorAll('.pan input:checked').length")==1,s['pan'])
        await pg.tap('.pan .stp[aria-label="Always have soy sauce"]'); await pg.wait_for_timeout(250); s=await pg.evaluate(SHOP); st=json.loads(await pg.evaluate("localStorage.getItem('bd-staples')"))
        log('staples: unmarking from the group sends it back to its section, tick kept',s['ptog'].strip()=='Check your pantry (3)' and any('soy sauce' in r for r in s['rows']) and 'soy sauce' not in st and await pg.evaluate("document.querySelector('.checks:not(.pan) input[data-k=\"soy sauce\"]').checked"),s['ptog'])
        await pg.tap('.pan .stp >> nth=0'); await pg.wait_for_timeout(200); await pg.tap('.pan .stp >> nth=0'); await pg.wait_for_timeout(250); s=await pg.evaluate(SHOP)
        log('staples: the group goes away when the last one is unmarked; focus lands on "Mark staples"',s['ptog']=='' and len(s['rows'])==17 and await pg.evaluate("document.activeElement.id")=='stEdit',s['ptog'])
        await pg.tap('#stEdit'); await pg.tap('.stp[aria-label="Always have soy sauce"]'); await pg.tap('.stp[aria-label="Always have Neutral oil"]'); await pg.wait_for_timeout(200)
        await paste(pg,REC2); s=await pg.evaluate(SHOP)
        log('staples: remembered for the next recipe, whatever the capitals ("Soy Sauce", "neutral oil")',s['ptog'].strip()=='Check your pantry (2)' and s['stp']==0 and len(s['rows'])==4,f"{s['ptog']} {s['rows']}")
        await pg.evaluate("localStorage.setItem('bd-staples','{not json')"); await pg.reload(); await pg.wait_for_timeout(500); s=await pg.evaluate(SHOP)
        log('staples: a corrupt bd-staples is read as empty, no error',s['ptog']=='' and len(s['rows'])==6 and not errs,errs)
        # all staples: the list still sends something
        await pg.tap('#stEdit')
        for _ in range(6): await pg.tap('.checks:not(.pan) .stp >> nth=0'); await pg.wait_for_timeout(120)
        s=await pg.evaluate(SHOP); await pg.tap('[data-addlist]'); await pg.wait_for_timeout(200); sent=(await pg.evaluate('window.__shared'))[-1]['text'].split('\n')
        log('staples: with everything marked the card is just the pantry group, and Add to list sends it',s['labels']==[] and s['ptog'].strip()=='Check your pantry (6)' and s['count']=='' and len(sent)==6,f"{s['ptog']} {len(sent)}")
        for w in (320,195):
            await pg.set_viewport_size({'width':w,'height':800}); await pg.wait_for_timeout(250)
            if await pg.get_attribute('#ptog','aria-expanded')=='false': await pg.tap('#ptog')
            r=await pg.evaluate("(()=>{const c=document.querySelector('[data-panel=shop] .card').getBoundingClientRect();return {ow:document.documentElement.scrollWidth<=innerWidth,inside:[...document.querySelectorAll('.pan .stp,#ptog,#stEdit')].every(e=>{const r=e.getBoundingClientRect();return r.left>=c.left-1&&r.right<=c.right+1&&r.height>=44})}})()")
            log(f'staples: fits at {w}px, nothing outside the card',all(r.values()),r)
        log('staples: no errors',not errs,errs); await ctx.close()
        ctx,pg,errs=await fresh(b,reduced_motion='reduce'); await sample(pg); await pg.tap('#stEdit'); await pg.tap('.stp >> nth=0'); await pg.wait_for_timeout(300); await pg.tap('#ptog'); await pg.wait_for_timeout(300)
        tr=await pg.evaluate("[getComputedStyle(document.querySelector('#ptog svg')).transitionProperty,getComputedStyle(document.getElementById('pcount')).animationName]")
        log('staples: reduced motion: the chevron does not turn, the count does not slide',tr[0]=='opacity' and tr[1] in ('none','fadeIn') and not errs,tr); await ctx.close()

        # --- 1 backup and restore
        ctx,pg,errs=await fresh(b,mobile=False)
        log('backup: with no batches the card is hidden and the footer offers "Restore backup"',not await pg.is_visible('#mine') and await pg.is_visible('#bkFoot') and (await pg.inner_text('#bkFoot'))=='Restore backup')
        await pg.evaluate("localStorage.setItem('bd-theme','dark');localStorage.setItem('bd-staples',JSON.stringify(['soy sauce','olive oil']));localStorage.setItem('bd-hap','0');localStorage.setItem('bd-tip','1');sessionStorage.setItem('bd-src','tiktok')")
        junk={'id':'bad','text':''}
        await seed(pg,[batch(1,NOW,k=['rice']),batch(2,NOW-1000),junk])
        await pg.wait_for_timeout(300)
        vis=await pg.evaluate("['#bkUp','#bkIn'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [document.querySelector(s).innerText,r.height>=44&&r.width>=44]})")
        log('backup: My batches has quiet "Back up" and "Restore" links, 44px; the footer one is gone',vis==[['Back up',True],['Restore',True]] and not await pg.is_visible('#bkFoot'),vis)
        async with pg.expect_download() as d: await pg.click('#bkUp')
        dl=await d.value; data=json.load(open(await dl.path())); today=datetime.date.today().isoformat()
        log('backup: desktop downloads batch-recipes-backup-YYYY-MM-DD.json',bool(re.fullmatch(r'batch-recipes-backup-\d{4}-\d\d-\d\d\.json',dl.suggested_filename)) and today in dl.suggested_filename,dl.suggested_filename)
        log('backup: the file is {app, v, at, batches, freezer, settings} and nothing else',list(data)==['app','v','at','batches','freezer','settings'] and data['app']=='batch.recipes' and data['v']==1 and bool(re.match(r'\d{4}-\d\d-\d\dT[\d:.]+Z$',data['at'])) and list(data['settings'])==['theme','staples'],list(data))
        log('backup: batches carry their ticks; settings carry theme and staples; unreadable entries and other keys stay out',[x['id'] for x in data['batches']]==['b1','b2'] and data['batches'][0]['k']==['rice'] and sorted(data['batches'][0])==['at','id','k','m','text','title','w','y'] and data['settings']=={'theme':'dark','staples':['soy sauce','olive oil']} and 'tiktok' not in json.dumps(data) and 'hap' not in json.dumps(data),data['settings'])
        e=await ev(pg,'Backup'); log('backup: toast "Backup saved", event Backup {how: download}',(await toast(pg))=='Backup saved' and len(e)==1 and e[0]['how']=='download',e)
        log('backup: no errors, no CSP block on the download',not errs,errs); await ctx.close()
        # phone: share sheet with a File
        ctx,pg,errs=await fresh(b,FSHARE); await seed(pg,[batch(1,NOW)])
        await pg.tap('#bkUp'); await pg.wait_for_timeout(300); f=await pg.evaluate('window.__files'); e=await ev(pg,'Backup')
        log('backup: on a phone that can share files it goes to the share sheet as one .json File',len(f)==1 and bool(re.fullmatch(r'batch-recipes-backup-\d{4}-\d\d-\d\d\.json',f[0]['name'])) and f[0]['type']=='application/json' and f[0]['keys']==['files'] and json.loads(f[0]['text'])['batches'][0]['id']=='b1' and e[-1]['how']=='share',f[0]['name'] if f else f)
        await pg.evaluate("window.__mode='abort';localStorage.removeItem('bd-bk');document.getElementById('toast').classList.remove('on')"); await pg.tap('#bkUp'); await pg.wait_for_timeout(300)
        log('backup: closing the share sheet does nothing (no toast, no event, not marked as backed up)',len(await ev(pg,'Backup'))==1 and await pg.evaluate("localStorage.getItem('bd-bk')") is None and not await pg.evaluate("document.getElementById('toast').classList.contains('on')"))
        await pg.evaluate("window.__mode='cant'")
        async with pg.expect_download() as d: await pg.tap('#bkUp')
        e=await ev(pg,'Backup'); log('backup: a phone that will not share files (Android Chrome and .json) downloads instead',(await d.value).suggested_filename.endswith('.json') and e[-1]['how']=='download',e[-1])
        log('backup: no errors (phone)',not errs,errs); await ctx.close()
        # restore into an empty browser
        ctx,pg,errs=await fresh(b)
        acc=await pg.get_attribute('#bfile','accept')
        await pg.set_input_files('#bfile',bfile(bk([batch(1,NOW,k=['rice']),batch(2,NOW-5000,title='<img src=x onerror=alert(1)>'),batch(3,NOW-9000)],theme='dark',staples=['Soy Sauce','olive oil']))); await pg.wait_for_timeout(400)
        rows=await pg.locator('#savedList .open b').all_inner_texts(); e=await ev(pg,'Restore'); st=await stored(pg)
        log('restore: the picker takes .json; a good file fills My batches, newest first',acc=='.json,application/json' and rows==['Batch 1','<img src=x onerror=alert(1)>','Batch 3'] and await pg.is_visible('#mine') and not await pg.is_visible('#bkFoot'),rows)
        log('restore: toast "Restored 3 batches", event Restore {ok: yes, n: 3}, focus on the heading',(await toast(pg))=='Restored 3 batches' and e==[{**e[0],'ok':'yes','n':3}] and await pg.evaluate('document.activeElement.id')=='mineH',e)
        log('restore: ticks, theme and staples come with it (staple names folded)',st[0]['k']==['rice'] and await pg.evaluate("document.documentElement.dataset.theme")=='dark' and await pg.get_attribute('#theme','aria-checked')=='true' and json.loads(await pg.evaluate("localStorage.getItem('bd-staples')"))==['soy sauce','olive oil'])
        log('restore: a title made of markup shows as text; no dialog',await pg.locator('#savedList img').count()==0 and 'dialog' not in errs)
        # merge
        await pg.goto(U); await pg.wait_for_timeout(300); await pg.evaluate("localStorage.setItem('bd-theme','light');document.documentElement.dataset.theme='light'")
        f2=bk([batch(1,NOW+1000,k=['rice','chicken 1'],title='Batch 1 newer'),batch(2,NOW-99999,title='Batch 2 older'),batch(9,NOW+50)],theme='dark',staples=['olive oil','salt'])
        await pg.set_input_files('#bfile',bfile(f2)); await pg.wait_for_timeout(400); rows=await pg.locator('#savedList .open b').all_inner_texts(); st=await stored(pg); e=await ev(pg,'Restore')
        log('restore: merge by id keeps the newer copy either way, adds the new one, deletes nothing',rows==['Batch 1 newer','Batch 9','<img src=x onerror=alert(1)>','Batch 3'] and st[0]['k']==['rice','chicken 1'] and (await toast(pg))=='Restored 2 batches' and e[-1]['n']==2,rows)
        log('restore: staples are added to, and a theme already chosen here is kept',json.loads(await pg.evaluate("localStorage.getItem('bd-staples')"))==['soy sauce','olive oil','salt'] and await pg.evaluate("localStorage.getItem('bd-theme')")=='light')
        await pg.set_input_files('#bfile',bfile(f2)); await pg.wait_for_timeout(400)
        log('restore: the same file again changes nothing ("Nothing new in that file")',(await toast(pg))=='Nothing new in that file' and await pg.locator('#savedList li').count()==4 and (await ev(pg,'Restore'))[-1]=={**e[-1],'ok':'yes','n':0},await toast(pg))
        same=batch(77,NOW+9999,text=st[3]['text'],title='Same text, new id')
        await pg.set_input_files('#bfile',bfile(bk([same]))); await pg.wait_for_timeout(400); st2=await stored(pg)
        log('restore: the very same recipe under another id is not listed twice',len(st2)==4 and st2[0]['title']=='Same text, new id' and st2[0]['id']=='b3',[x['id'] for x in st2])
        await pg.click('#savedList .open >> nth=1'); await pg.wait_for_timeout(500); t=await pg.inner_text('#sTitle')
        log('restore: a restored batch opens',t=='Batch 1' and await pg.locator('.checks input').count()==2 and await pg.locator('.checks input:checked').count()==2,t)
        await pg.goto(U); await pg.wait_for_timeout(300)
        # bad files: one plain line, nothing changes
        before=await pg.evaluate("localStorage.getItem('bd-batches')+localStorage.getItem('bd-staples')+localStorage.getItem('bd-theme')")
        good=batch(50,NOW)
        bads=[('not JSON','{oops'),('a JSON list',[good]),('another app',{**bk([good]),'app':'other'}),('no app',{'v':1,'batches':[good]}),('a later version',{**bk([good]),'v':2}),('version as text',{**bk([good]),'v':'1'}),('batches not a list',{**bk([]),'batches':{'0':good}}),
              ('one batch with no text',bk([good,{**batch(51,NOW),'text':'  '}])),('one batch with no id',bk([{k:v for k,v in good.items() if k!='id'}])),('a batch with a bad date',bk([{**good,'at':'soon'}])),('a batch with zero meals',bk([{**good,'w':0}])),('a title that is not text',bk([{**good,'title':{'a':1}}])),
              ('staples that are not text',bk([good],staples=[1,2])),('a theme we do not have',bk([good],theme='pink')),('settings as a list',{**bk([good]),'settings':[]}),('null','null'),('an empty file','')]
        outb=[]
        for n,o in bads:
            await pg.evaluate("document.getElementById('toast').textContent=''"); await pg.set_input_files('#bfile',bfile(o)); await pg.wait_for_timeout(250); t=await toast(pg)
            if t!="That file isn't a batch.recipes backup" or '\n' in t: outb.append((n,t))
        after=await pg.evaluate("localStorage.getItem('bd-batches')+localStorage.getItem('bd-staples')+localStorage.getItem('bd-theme')"); e=await ev(pg,'Restore')
        log(f'restore: {len(bads)} kinds of bad file each get one plain line and change nothing',not outb and after==before and await pg.locator('#savedList li').count()==4,outb)
        log('restore: each bad file is counted as Restore {ok: no, n: 0}',len([x for x in e if x['ok']=='no' and x['n']==0])==len(bads),len(e))
        big=bk([batch(60,NOW,text='1 cup rice\n'+'x'*2100000)])
        await pg.set_input_files('#bfile',bfile(big)); await pg.wait_for_timeout(400)
        log('restore: a file over 2 MB is refused ("That file is too big")',(await toast(pg))=='That file is too big' and await pg.evaluate("localStorage.getItem('bd-batches')+localStorage.getItem('bd-staples')+localStorage.getItem('bd-theme')")==before,await toast(pg))
        proto='{"app":"batch.recipes","v":1,"batches":[{"id":"p1","text":"1 cup rice","w":4,"at":%d,"__proto__":{"polluted":1},"evil":"<script>"}],"settings":{"__proto__":{"polluted":1}},"extra":{"a":1}}'%(NOW+5)
        await pg.set_input_files('#bfile',bfile(proto)); await pg.wait_for_timeout(400); st=[x for x in await stored(pg) if x['id']=='p1']
        log('restore: extra keys in a file are dropped, not stored',(await toast(pg))=='Restored 1 batch' and sorted(st[0])==['at','id','k','m','text','w'] and await pg.evaluate("({}).polluted===undefined"),sorted(st[0]))
        log('restore: no errors',not [x for x in errs if x!='dialog'] and 'dialog' not in errs,errs); await ctx.close()
        # cap
        ctx,pg,errs=await fresh(b); await seed(pg,[batch(i,NOW-i*1000) for i in range(198)])
        await pg.set_input_files('#bfile',bfile(bk([batch(1000+i,NOW+100-i) for i in range(5)]+[batch(3,NOW+7,title='Batch 3 newer')]))); await pg.wait_for_timeout(500); st=await stored(pg); e=await ev(pg,'Restore')
        log('restore: at the 200 cap it adds what fits (newest first), still updates, and says so',len(st)==200 and (await toast(pg))=='My batches is full. Added 2 of 5.' and [x['id'] for x in st[:3]]==['b1000','b1001','b3'] and st[2]['title']=='Batch 3 newer' and e[-1]['n']==3 and all(any(x['id']=='b%d'%i for x in st) for i in range(198)),await toast(pg))
        await seed(pg,[batch(i,NOW-i*1000) for i in range(260)])
        await pg.set_input_files('#bfile',bfile(bk([batch(2000,NOW+1)]))); await pg.wait_for_timeout(500)
        log('restore: a list already over the cap is left whole',len(await stored(pg))==260 and (await toast(pg))=='My batches is full. Added 0 of 1.',await toast(pg))
        log('restore: no errors at the cap',not errs,errs); await ctx.close()
        # nudge + persist
        ctx,pg,errs=await fresh(b,PERSIST); await pg.reload(); await pg.wait_for_timeout(300)
        await sample(pg); p0=await pg.evaluate('window.__persist')
        await pg.tap('.checks label >> nth=0'); await pg.wait_for_timeout(300); p1=await pg.evaluate('window.__persist'); await pg.tap('.checks label >> nth=1'); await pg.wait_for_timeout(200)
        await paste(pg,REC2); p2=await pg.evaluate('window.__persist')
        log('persist: asked for once, after the first batch is saved, never again',p0==0 and p1==1 and p2==0 and await pg.evaluate("localStorage.getItem('bd-ps')")=='1',f'{p0} {p1} {p2}')
        await pg.goto(U); await pg.wait_for_timeout(300); n2=await pg.is_visible('#bkNudge')
        await paste(pg,"Lentil soup\nServes 4\n1 cup lentils\n2 carrots\n4 cups broth\n1. Simmer everything 30 minutes."); await pg.goto(U); await pg.wait_for_timeout(300)
        n3=await pg.is_visible('#bkNudge'); t=(await pg.inner_text('#bkNudge')).replace('\n',' ')
        log('nudge: nothing at two batches, a small card at three',not n2 and n3 and t.startswith("Back up your batches. They're only on this device.") and 'Back up' in t and 'Not now' in t,t)
        sm=await pg.evaluate("['#bkYes','#bkNo'].every(s=>{const r=document.querySelector(s).getBoundingClientRect();return r.height>=44&&r.width>=44})"); log('nudge: both buttons are 44px',sm)
        await pg.tap('#bkNo'); await pg.wait_for_timeout(150); g1=await pg.is_visible('#bkNudge'); await pg.reload(); await pg.wait_for_timeout(300)
        log('nudge: "Not now" puts it away for good (bd-bkn)',not g1 and not await pg.is_visible('#bkNudge') and await pg.evaluate("localStorage.getItem('bd-bkn')")=='1' and await pg.is_visible('#bkUp'))
        await pg.evaluate("localStorage.removeItem('bd-bkn')"); await pg.reload(); await pg.wait_for_timeout(300); back=await pg.is_visible('#bkNudge')
        async with pg.expect_download() as d: await pg.tap('#bkYes')
        await d.value; await pg.wait_for_timeout(200); g2=await pg.is_visible('#bkNudge'); await pg.reload(); await pg.wait_for_timeout(300)
        log('nudge: "Back up" on the card makes the backup and the card does not come back',back and not g2 and not await pg.is_visible('#bkNudge') and bool(await pg.evaluate("localStorage.getItem('bd-bk')")))
        log('nudge: no errors',not errs,errs); await ctx.close()
        ctx,pg,errs=await fresh(b,user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'); await seed(pg,[batch(i,NOW-i) for i in range(3)])
        log('nudge: on iPhone it waits while the Home Screen tip is showing, then takes its place',await pg.is_visible('#tip') and not await pg.is_visible('#bkNudge'))
        await pg.tap('#tipX'); await pg.reload(); await pg.wait_for_timeout(300); log('nudge: shows once that tip is put away',await pg.is_visible('#bkNudge') and not await pg.is_visible('#tip') and not errs,errs); await ctx.close()
        # no sideways scroll on the home card
        ctx,pg,errs=await fresh(b); await seed(pg,[batch(i,NOW-i) for i in range(3)])
        outw=[]
        for w in (195,320,390,1440):
            await pg.set_viewport_size({'width':w,'height':800}); await pg.wait_for_timeout(200)
            if not await pg.evaluate("document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('#bkNudge,#bkRow,#bkRow button,#bkNudge button')].every(e=>{const r=e.getBoundingClientRect(),c=document.getElementById('mine').getBoundingClientRect();return r.left>=c.left&&r.right<=c.right})"): outw.append(w)
        log('backup: the card fits from 195 to 1440px',not outw,outw); await ctx.close()
        await b.close()
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)-len(bad)} of {len(R)} ok')
asyncio.run(main())
