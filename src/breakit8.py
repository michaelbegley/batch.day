# First-visit tour: the offer card, the 5 bubbles, how it ends, what it stores and tracks, fit at 320 / 390 / desktop, keyboard, reduced motion,
# and that it keeps clear of the Home Screen tip, the backup nudge and the toast. Nothing leaves the machine.
import asyncio, json
from playwright.async_api import async_playwright
U='http://localhost:8765/'
R=[]
def log(n,ok,note=''):
    R.append((n,'ok' if ok else 'FAIL',str(note))); open('breakit/r8.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',n,'|',str(note)[:300])
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective));
window.__ev=[];window.umami={track:(n,d)=>window.__ev.push([n,d])};"""
IOS='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
AND='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36'
BATCH=lambda n:json.dumps([{'id':f'b{i}','title':f'Soup {i}','text':f'Soup {i}\nServes 4\n1 cup lentils\n2 carrots\n1. Simmer 30 minutes.','y':4,'w':14,'m':'batch','at':1763000000000+i,'k':[]} for i in range(n)])
async def fresh(b,w=390,h=844,mob=True,pre='',go=U,**kw):
    ctx=await b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob,**kw); errs=[]
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**'): await ctx.route(pat,lambda r:r.abort())
    await ctx.add_init_script(INIT+pre); pg=await ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    await pg.goto(go); await pg.wait_for_timeout(350)
    return ctx,pg,errs
VIS="(s)=>{const e=document.querySelector(s);return !!e&&!e.closest('.hidden')&&e.getClientRects().length>0}"
EV="(n)=>window.__ev.filter(e=>e[0]===n).map(e=>e[1])"
LS="(k)=>localStorage.getItem(k)"
FOC="(()=>{const e=document.activeElement;return e.id||e.className||e.tagName})()"
SAVED="(()=>{try{return JSON.parse(localStorage.getItem('bd-batches')||'[]').length}catch(e){return -1}})()"
TARGETS=['#choose','.step:has(#want)','#tabs [data-tab=shop]','#dCook','#dShare']
# everything about where the bubble sits, for the step on screen
GEO="""(sel)=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),t=q(sel),b=q('#tBub'),r=q('#tRing'),a=q('#tArr'),W=document.documentElement.clientWidth,H=innerHeight,bar=q('.bar').bottom,R=Math.round;
 const hit=!(b.right<=t.left||b.left>=t.right||b.bottom<=t.top||b.top>=t.bottom), acx=a.left+a.width/2;
 return {onScreen:b.left>=0&&b.right<=W&&b.top>=bar&&b.bottom<=H,margins:[R(b.left),R(W-b.right)],targetSeen:t.top>=bar&&t.bottom<=H&&t.left>=0&&t.right<=W,covers:hit,
  ring:[R(t.left-r.left),R(t.top-r.top),R(r.right-t.right),R(r.bottom-t.bottom)],gap:R(b.top>=t.bottom?b.top-t.bottom:t.top-b.bottom),side:b.top>=t.bottom?'below':'above',
  arrowOnTarget:acx>=t.left&&acx<=t.right,arrowInBubble:a.left>=b.left+8&&a.right<=b.right-8,noSide:document.documentElement.scrollWidth<=W,
  top:document.elementFromPoint(b.left+b.width/2,b.top+b.height/2).closest('#tBub')!==null,w:R(b.width)}}"""
async def walk(pg,tag,minm=16):
    """Show me, then all five steps; checks each bubble. Leaves the tour on step 5."""
    for n,sel in enumerate(TARGETS):
        if n: await pg.click('#tNext')
        await pg.wait_for_timeout(650)
        g=await pg.evaluate(GEO,sel); lab=await pg.get_attribute('#tDots','aria-label')
        ok=g['onScreen'] and g['targetSeen'] and not g['covers'] and g['ring']==[4,4,4,4] and 15<=g['gap']<=17 and g['arrowOnTarget'] and g['arrowInBubble'] and g['noSide'] and g['top'] and min(g['margins'])>=minm and lab==f'{n+1} of 5'
        log(f'{tag}: step {n+1} bubble on screen, beside its control, pointer on it',ok,{**g,'label':lab})
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()

    # ---- the first screen: one sample button, no tour offer (five-second test, 15 Nov)
    ctx,pg,errs=await fresh(b)
    r=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),s=q('#sample'),c=q('#choose');return {under:s.top>c.bottom,inCard:!!document.querySelector('#dropcard #sample'),text:document.querySelector('#sample').textContent,offer:!!document.querySelector('#tourOffer')}})()")
    log('first visit: one See a sample plan button under Choose screenshots, in the card; no tour offer',r=={'under':True,'inCard':True,'text':'See a sample plan','offer':False},r)
    await pg.wait_for_timeout(1500)
    log('never starts by itself: no bubble, nothing dimmed',not await pg.evaluate(VIS,'#tour') and not await pg.evaluate(VIS,'#tBub'))
    log('nothing stored or tracked until a tap',await pg.evaluate(LS,'bd-tour') is None and await pg.evaluate(EV,'Tour')==[])
    log('footer has Take the tour',await pg.evaluate(VIS,'#tourGo') and await pg.inner_text('#tourGo')=='Take the tour')
    await pg.tap('#sample'); await pg.wait_for_timeout(600)
    log('See a sample plan opens the finished sample plan, no tour',await pg.inner_text('#sTitle')=='Brothy chicken and rice' and not await pg.evaluate(VIS,'#tour') and [e.get('from') for e in await pg.evaluate(EV,'Plan')]==['sample'])
    log('no errors (first screen)',not errs,errs); await ctx.close()

    ctx,pg,errs=await fresh(b,pre="Storage.prototype.setItem=function(){throw new Error('no')};")
    log('storage blocked: footer link still there',await pg.evaluate(VIS,'#tourGo'))
    await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    log('storage blocked: tour still runs',await pg.evaluate(VIS,'#tBub') and await pg.inner_text('#sTitle')=='Brothy chicken and rice' and not errs,errs); await ctx.close()

    # ---- Show me: the whole walk on a phone
    ctx,pg,errs=await fresh(b,pre="navigator.share=async()=>{};")
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    log('Take the tour: event step 0 choice link; nothing stored yet',[(e.get('step'),e.get('choice')) for e in await pg.evaluate(EV,'Tour')]==[(0,'link')] and await pg.evaluate(LS,'bd-tour') is None)
    a=await pg.evaluate("(()=>{const b=document.querySelector('#tBub'),t=document.querySelector('#tText'),d=document.querySelector('#tDots');return {role:b.getAttribute('role'),label:b.getAttribute('aria-label'),desc:b.getAttribute('aria-describedby'),live:t.getAttribute('aria-live'),dots:d.getAttribute('role')+'|'+d.getAttribute('aria-label')+'|'+d.children.length+'|'+d.querySelectorAll('.on').length,tags:[...b.querySelectorAll('#tNext,#tSkip')].map(e=>e.tagName+':'+e.textContent),focus:document.activeElement.id,view:document.querySelector('#v-add').classList.contains('hidden')?'sheet':'add'}})()")
    log('step 1: a labelled dialog, live text, real buttons, focus on the bubble, still on home',a=={'role':'dialog','label':'Tour','desc':'tText','live':'polite','dots':'img|1 of 5|5|1','tags':['BUTTON:Skip tour','BUTTON:Next'],'focus':'tBub','view':'add'},a)
    log('step 1 copy',await pg.inner_text('#tText')=="Add screenshots. Here's a sample.",await pg.inner_text('#tText'))
    dim=await pg.evaluate("(()=>{const s=getComputedStyle(document.querySelector('#tRing')).boxShadow,m=s.match(/rgba\\(0, 0, 0, ([\\d.]+)\\)/);return m?+m[1]:-1})()")
    log('light dim only (under 20%), page still visible',0<dim<=.2,dim)
    await pg.tap('#tNext'); await pg.wait_for_timeout(700)
    plans=await pg.evaluate(EV,'Plan')
    log('Next loads the sample; Plan event is tagged from: tour, none as sample',await pg.inner_text('#sTitle')=='Brothy chicken and rice' and [e.get('from') for e in plans]==['tour'],plans)
    log('sample is not saved as a batch',await pg.evaluate(SAVED)==0 and not await pg.evaluate(VIS,'#savedNote'))
    log('focus stays in the bubble after the page changes',await pg.evaluate(FOC)=='tNext',await pg.evaluate(FOC))
    texts=[await pg.inner_text('#tText')]
    for n in (3,4,5):
        await pg.tap('#tNext'); await pg.wait_for_timeout(650); texts.append(await pg.inner_text('#tText'))
    want=['Set how many meals.','Your grocery list. Tick as you shop.','One step at a time. Screen stays on.','Save it or share it.']
    log('steps 2 to 5 copy',texts==want,texts)
    log('no em or en dash, no exclamation mark in any tour words',not any(c in ''.join(texts+["Quick tour","Tour is in the footer."]) for c in '—–!'))
    log('last step says Done; dots say 5 of 5',await pg.inner_text('#tNext')=='Done' and await pg.get_attribute('#tDots','aria-label')=='5 of 5')
    log('cook mode and the share sheet did not open under the tour',not await pg.evaluate(VIS,'#cook') and not await pg.evaluate(VIS,'#menu'))
    await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    ev=await pg.evaluate(EV,'Tour')
    log('Done: tour gone, bd-tour=done, event step 5 end done',not await pg.evaluate(VIS,'#tour') and await pg.evaluate(LS,'bd-tour')=='done' and (ev[-1].get('step'),ev[-1].get('end'))==(5,'done') and len(ev)==2,ev)
    log('Done: left on the sample plan, focus on its title, no toast',await pg.evaluate(VIS,'#v-sheet') and await pg.evaluate(FOC)=='sTitle' and 'on' not in (await pg.get_attribute('#toast','class') or ''))
    log('Done: still nothing saved',await pg.evaluate(SAVED)==0)
    await pg.tap('#dCook'); await pg.wait_for_timeout(500); cook=await pg.evaluate(VIS,'#cook'); await pg.tap('#cClose'); await pg.wait_for_timeout(600)
    log('after the tour the page works: Start cooking opens cook mode',cook)
    await pg.tap('#newRec'); await pg.wait_for_timeout(500)
    log('New recipe goes home; card does not come back; footer link is there',await pg.evaluate(VIS,'#choose') and not await pg.evaluate(VIS,'#tourOffer') and await pg.evaluate(VIS,'#tourGo'))
    await pg.reload(); await pg.wait_for_timeout(350)
    log('after Done the card never returns',not await pg.evaluate(VIS,'#tourOffer'))
    log('no errors (walk)',not errs,errs); await ctx.close()

    # ---- ways out
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300); ev=await pg.evaluate(EV,'Tour')
    log('Escape on step 3: ends, event step 3 end outside, stored skip',not await pg.evaluate(VIS,'#tour') and (ev[-1].get('step'),ev[-1].get('end'))==(3,'outside') and await pg.evaluate(LS,'bd-tour')=='skip',ev[-1])
    log('ended early on the plan: toast names the home page; focus on the title',await pg.inner_text('#toast')=="Tour is in the home page footer." and await pg.evaluate(FOC)=='sTitle',await pg.inner_text('#toast'))
    log('ended early: sample not saved; Back goes home',await pg.evaluate(SAVED)==0)
    await pg.go_back(); await pg.wait_for_timeout(400); log('Back after the tour lands on home',await pg.evaluate(VIS,'#choose')); await ctx.close()
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    await pg.touchscreen.tap(60,700); await pg.wait_for_timeout(300); ev=await pg.evaluate(EV,'Tour')
    log('tap outside on step 2: ends, end outside',not await pg.evaluate(VIS,'#tour') and (ev[-1].get('step'),ev[-1].get('end'))==(2,'outside'),ev[-1])
    log('the outside tap did not press what was under it',not await pg.evaluate(VIS,'#cook') and not await pg.evaluate(VIS,'#menu') and await pg.evaluate(SAVED)==0); await ctx.close()
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    b0=await pg.evaluate("window.__picked=0;document.querySelector('#file').addEventListener('click',()=>window.__picked++);0")
    box=await pg.locator('#choose').bounding_box(); await pg.touchscreen.tap(box['x']+20,box['y']+20); await pg.wait_for_timeout(300); ev=await pg.evaluate(EV,'Tour')
    log('tap on the ringed control on step 1: ends the tour, does not open the picker',not await pg.evaluate(VIS,'#tour') and (ev[-1].get('step'),ev[-1].get('end'))==(1,'outside') and await pg.evaluate('window.__picked')==0 and await pg.evaluate(FOC)=='tourGo',ev[-1])
    await ctx.close()
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    for _ in range(3): await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    await pg.tap('#tSkip'); await pg.wait_for_timeout(300); ev=await pg.evaluate(EV,'Tour')
    log('Skip tour on step 4: end skip, stored skip, toast',not await pg.evaluate(VIS,'#tour') and (ev[-1].get('step'),ev[-1].get('end'))==(4,'skip') and await pg.evaluate(LS,'bd-tour')=='skip' and 'on' in (await pg.get_attribute('#toast','class')),ev[-1])
    await ctx.close()
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    await pg.go_back(); await pg.wait_for_timeout(500); ev=await pg.evaluate(EV,'Tour')
    log('phone Back on step 2: tour ends and Back goes home',not await pg.evaluate(VIS,'#tour') and await pg.evaluate(VIS,'#choose') and (ev[-1].get('step'),ev[-1].get('end'))==(2,'outside') and not await pg.evaluate(VIS,'#tourOffer'),ev[-1])
    log('no errors (ways out)',not errs,errs); await ctx.close()
    # hammering
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    # round 3 (L-01): a burst of presses on Next is one Next, so 12 at once move one step and the tour goes on
    await pg.evaluate("for(let i=0;i<12;i++)document.querySelector('#tNext').click()"); await pg.wait_for_timeout(650); ev=await pg.evaluate(EV,'Tour')
    log('Next pressed 12 times at once: one step, tour still on',await pg.evaluate(VIS,'#tour') and await pg.get_attribute('#tDots','aria-label')=='2 of 5' and not [e for e in ev if e.get('end')] and len(await pg.evaluate(EV,'Plan'))==1 and await pg.evaluate(SAVED)==0 and not errs,[ev,errs])
    for _ in range(4): await pg.evaluate("document.querySelector('#tNext').click()"); await pg.wait_for_timeout(650)
    ev=await pg.evaluate(EV,'Tour')
    log('then four more, one at a time: one clean finish',not await pg.evaluate(VIS,'#tour') and len([e for e in ev if e.get('end')])==1 and ev[-1].get('end')=='done' and len(await pg.evaluate(EV,'Plan'))==1 and await pg.evaluate(SAVED)==0 and not errs,[ev,errs])
    await pg.evaluate("document.querySelector('#tSkip').click();document.querySelector('#tNext').click()"); await pg.wait_for_timeout(200)
    log('buttons of a finished tour do nothing',len(await pg.evaluate(EV,'Tour'))==len(ev) and not errs); await ctx.close()

    # ---- after the tour the sample behaves like the sample
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); [await pg.evaluate("document.querySelector('#tNext').click();new Promise(r=>setTimeout(r,650))") for _ in range(5)]
    await pg.tap('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(400)
    log('after the tour, changing the meals saves it (same rule as Try a sample)',await pg.evaluate(SAVED)==1 and await pg.inner_text('#want')=='' and await pg.input_value('#want')=='15'); await ctx.close()

    # ---- keyboard
    ctx,pg,errs=await fresh(b,1280,900,False)
    await pg.focus('#tourGo'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(650)
    seq=[]
    for k in ('Tab','Tab','Tab','Shift+Tab'): await pg.keyboard.press(k); seq.append(await pg.evaluate(FOC))
    log('keyboard: Tab stays between the two buttons',seq==['tSkip','tNext','tSkip','tNext'],seq)
    for _ in range(4): await pg.keyboard.press('Enter'); await pg.wait_for_timeout(650)
    log('keyboard: Enter walks to the last step',await pg.inner_text('#tNext')=='Done' and await pg.evaluate(FOC)=='tNext' and await pg.get_attribute('#tDots','aria-label')=='5 of 5')
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
    log('keyboard: Done by Enter',not await pg.evaluate(VIS,'#tour') and await pg.evaluate(LS,'bd-tour')=='done' and not errs,errs); await ctx.close()
    ctx,pg,errs=await fresh(b,1280,900,False,pre="delete Navigator.prototype.share;")
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.click('#tourGo'); await pg.wait_for_timeout(650); await pg.click('#tNext'); await pg.wait_for_timeout(650); await pg.click('#tNext'); await pg.wait_for_timeout(650)
    log('no share sheet: step 3 leaves the list app out',await pg.inner_text('#tText')=='Your grocery list. Tick as you shop.',await pg.inner_text('#tText')); await ctx.close()

    # ---- fit: every step at every size, light and dark, iPhone and Android
    for tag,w,h,mob,kw in (('iPhone 390',390,844,True,{'user_agent':IOS}),('Android 412',412,915,True,{'user_agent':AND}),('phone 320',320,568,True,{'user_agent':IOS}),('short 360x560',360,560,True,{'user_agent':AND}),('desktop 1440',1440,900,False,{}),('wide 2560',2560,1200,False,{})):
        for th in ('light','dark'):
            ctx,pg,errs=await fresh(b,w,h,mob,color_scheme=th,pre="navigator.share=async()=>{};",**kw)
            fo=await pg.evaluate("(()=>{const q=(s)=>document.querySelector(s).getBoundingClientRect(),o=q('#sample'),c=q('#pick');return {in:o.left>=c.left&&o.right<=c.right,h:o.height,noSide:document.documentElement.scrollWidth<=document.documentElement.clientWidth}})()")
            log(f'{tag} {th}: sample button fits, 44 px',fo['in'] and fo['h']>=43.9 and fo['noSide'],fo)
            await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.click('#tourGo'); await pg.wait_for_timeout(650)
            await walk(pg,f'{tag} {th}')
            sz=await pg.evaluate("[...document.querySelectorAll('#tNext,#tSkip')].map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})")
            c=await pg.evaluate("(()=>{const L=(c)=>{const m=c.match(/[\\d.]+/g).map(Number).slice(0,3).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*m[0]+.7152*m[1]+.0722*m[2]},b=getComputedStyle(document.querySelector('#tBub')),t=getComputedStyle(document.querySelector('#tText')),a=L(b.backgroundColor),x=L(t.color);return (Math.max(a,x)+.05)/(Math.min(a,x)+.05)})()")
            log(f'{tag} {th}: bubble buttons 44 px or more, text contrast AA',all(s[0]>=44 and s[1]>=44 for s in sz) and c>=4.5,[sz,round(c,2)])
            log(f'{tag} {th}: no errors',not errs,errs); await ctx.close()
    # rotation / resize while a bubble is up
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650); await pg.tap('#tNext'); await pg.wait_for_timeout(650)
    await pg.set_viewport_size({'width':844,'height':390}); await pg.wait_for_timeout(500); g=await pg.evaluate(GEO,TARGETS[2])
    log('turned sideways on step 3: bubble follows, still clear of its control',g['ring']==[4,4,4,4] and not g['covers'] and g['noSide'],g)
    await pg.set_viewport_size({'width':390,'height':844}); await pg.wait_for_timeout(400); await pg.evaluate('scrollBy(0,120)'); await pg.wait_for_timeout(300); g=await pg.evaluate(GEO,TARGETS[2])
    log('page scrolled under the tour: ring and bubble stay on the control',g['ring']==[4,4,4,4] and not g['covers'] and 15<=g['gap']<=17,g); await ctx.close()
    # 200% zoom phone
    ctx,pg,errs=await fresh(b,195,422,True)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650); await walk(pg,'195 px (200% zoom)',8); log('195 px: no errors',not errs,errs); await ctx.close()

    # ---- reduced motion
    ctx,pg,errs=await fresh(b,reduced_motion='reduce')
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    d=await pg.evaluate("(()=>{const s=getComputedStyle(document.querySelector('#tBub'));return [parseFloat(s.animationDuration),s.translate]})()")
    log('reduced motion: the bubble appears, no slide',d[0]<=.02 and d[1] in ('none','0px','0px 0px'),d)
    await walk(pg,'reduced motion'); await ctx.close()
    ctx,pg,errs=await fresh(b)
    await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    d=await pg.evaluate("(()=>{const s=getComputedStyle(document.querySelector('#tBub'));return [parseFloat(s.animationDuration),s.animationName]})()")
    log('with motion: a short rise (0.3 s)',d[0]==.3 and d[1] in ('tourUp','tourDown'),d); await ctx.close()

    # ---- the footer link, on a return visit with batches, the iPhone tip and the backup nudge about
    for tag,ua,want in (('iPhone',IOS,'#tip'),('Android',AND,'#bkNudge')):
        ctx,pg,errs=await fresh(b,pre=f"try{{if(!sessionStorage.getItem('t')){{sessionStorage.setItem('t','1');localStorage.setItem('bd-batches',{json.dumps(BATCH(3))})}}}}catch(e){{}}",user_agent=ua)
        log(f'{tag} return visit: {want} shows, no offer card, footer link there',await pg.evaluate(VIS,want) and not await pg.evaluate(VIS,'#tourOffer') and await pg.evaluate(VIS,'#tourGo'))
        await pg.evaluate("document.querySelector('#bkIn')&&0"); await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
        ev=await pg.evaluate(EV,'Tour'); g=await pg.evaluate(GEO,'#choose')
        log(f'{tag} footer link: tour starts on step 1 at Choose screenshots, event choice link',await pg.evaluate(VIS,'#tBub') and ev[-1].get('choice')=='link' and g['onScreen'] and g['targetSeen'] and not g['covers'],[ev,g])
        ov=await pg.evaluate("(s)=>{const a=document.querySelector(s).getBoundingClientRect(),b=document.querySelector('#tBub').getBoundingClientRect(),hit=!(b.right<=a.left||b.left>=a.right||b.bottom<=a.top||b.top>=a.bottom);return {hit,bubbleOnTop:document.elementFromPoint(b.left+b.width/2,b.top+20).closest('#tBub')!==null,z:[+getComputedStyle(document.querySelector('#tour')).zIndex,+getComputedStyle(document.querySelector('#toast')).zIndex]}}",want)
        log(f'{tag}: {want} is not on top of the bubble',ov['bubbleOnTop'] and ov['z'][0]>ov['z'][1] and not ov['hit'],ov)
        for _ in range(5): await pg.tap('#tNext'); await pg.wait_for_timeout(650)
        log(f'{tag} footer tour: finishes; batches untouched (3); no install tip on the sample',await pg.evaluate(SAVED)==3 and await pg.evaluate(LS,'bd-tour')=='done' and not await pg.evaluate(VIS,'[data-inst]') and not await pg.evaluate(VIS,'#adBox'))
        await pg.tap('#newRec'); await pg.wait_for_timeout(400); await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
        log(f'{tag}: the footer link runs it again any time',await pg.evaluate(VIS,'#tBub') and await pg.get_attribute('#tDots','aria-label')=='1 of 5')
        await pg.tap('#tSkip'); await pg.wait_for_timeout(300)
        log(f'{tag}: skipping a tour started from the footer shows no toast; focus back on the link','on' not in (await pg.get_attribute('#toast','class') or '') and await pg.evaluate(FOC)=='tourGo',await pg.evaluate(FOC))
        log(f'{tag}: no errors',not errs,errs); await ctx.close()
    # a toast that is up when the tour starts
    ctx,pg,errs=await fresh(b)
    await pg.tap('#pasteToggle'); await pg.fill('#paste','hello'); await pg.wait_for_timeout(550); await pg.tap('#usePaste'); await pg.wait_for_timeout(200)
    t0='on' in (await pg.get_attribute('#toast','class')); await pg.locator('#tourGo').scroll_into_view_if_needed(); await pg.tap('#tourGo'); await pg.wait_for_timeout(650)
    log('a toast on screen is cleared when the tour starts; paste box closes so the button is there',t0 and 'on' not in (await pg.get_attribute('#toast','class')) and await pg.evaluate(VIS,'#choose') and await pg.evaluate(VIS,'#tBub'))
    await ctx.close()

    # ---- the rest of the site is as it was
    ctx,pg,errs=await fresh(b)
    await pg.tap('#sample'); await pg.wait_for_timeout(600)
    log('Try a sample still tracks Plan from: sample and starts no tour',[e.get('from') for e in await pg.evaluate(EV,'Plan')]==['sample'] and not await pg.evaluate(VIS,'#tour') and await pg.evaluate(EV,'Tour')==[])
    await ctx.close()
    h=open('site/index.html').read()
    log('impact-site-verification tag kept','<meta name="impact-site-verification" value="44a0832b-93ba-4379-b2a0-530627c39acf">' in h)
    log('print hides the tour','.toast,.tour{display:none!important}' in h)
    await b.close()
  bad=[r for r in R if r[1]!='ok']; print(f'{len(R)-len(bad)} of {len(R)} ok')
asyncio.run(main())
