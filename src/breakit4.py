# Checks for the small touches of 14 Nov (batch 1: tick + count, hold speeds up, close animations, changed amounts, top-bar title, press states).
# Phone viewport with touch. Nothing leaves the machine: the AI reader, analytics, ads and the CDN are blocked.
import asyncio, json
from playwright.async_api import async_playwright
U='http://localhost:8765/'
R=[]
def log(name,ok,note=''):
    R.append((name,'ok' if ok else 'FAIL',str(note))); open('breakit/r4.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',name,'|',str(note)[:300])
FOC="(()=>{const e=document.activeElement;return e.id||e.className||e.tagName})()"
CLS2="(s)=>[...document.querySelector(s).classList].join(' ')"
CLS="(id)=>[...document.getElementById(id).classList].join(' ')"
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective));
window.__amt=0;window.__draws=0;
document.addEventListener('animationstart',e=>{if(e.animationName==='amt'||(e.animationName==='fadeIn'&&e.target.classList.contains('chg')))window.__amt++},true);
addEventListener('DOMContentLoaded',()=>{new MutationObserver(m=>{window.__draws+=m.filter(x=>x.addedNodes.length).length}).observe(document.getElementById('sheet'),{childList:true})});"""
LONG="Slow cooker chicken tortilla soup for crowds\nServes 4\n"+"\n".join(f"{k+1} cups thing number {k}" for k in range(14))+"\n1. Cook it all for 30 minutes.\n2. Serve."
REC2="Lentil soup\nServes 4\n1 cup lentils\n2 carrots\n4 cups broth\n1. Simmer everything 30 minutes."
async def fresh(b,**kw):
    ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,permissions=['clipboard-read','clipboard-write'],**kw); errs=[]
    for pat in ('**/*.hf.space/**','**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**'): await ctx.route(pat,lambda r:r.abort())
    await ctx.add_init_script(INIT); pg=await ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    await pg.goto(U); await pg.wait_for_timeout(300)
    return ctx,pg,errs
async def sample(pg):
    await pg.tap('#sample'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(700)
async def hold(pg,sel,ms,marks=()):
    """press and hold a button with the pointer; returns the number at each mark (ms after pressing)"""
    box=await pg.locator(sel).bounding_box(); t=sel.split('data-t=')[1].split(']')[0]
    await pg.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2); await pg.mouse.down(); out=[]; at=0
    for m in marks:
        await pg.wait_for_timeout(m-at); at=m; out.append(int(await pg.input_value('#'+t)))
    await pg.wait_for_timeout(ms-at); await pg.mouse.up(); return out
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # 1 tick + count
        ctx,pg,errs=await fresh(b); await sample(pg)
        n=await pg.locator('.checks input').count(); c0=await pg.inner_text('#gcount'); live=await pg.get_attribute('#gcount','aria-live')
        await pg.tap('.checks label >> nth=0'); await pg.wait_for_timeout(600); c1=await pg.inner_text('#gcount')
        drawn=await pg.evaluate("(()=>{const i=document.querySelector('.checks input:checked');return [getComputedStyle(i,'::after').clipPath,getComputedStyle(i.nextElementSibling.querySelector('.tx')).backgroundSize,getComputedStyle(i.nextElementSibling).textDecorationLine]})()")
        log('1 first tick shows "1 of N", count is a polite live region',c0=='' and c1==f'1 of {n}' and live=='polite',f'n={n} before={c0!r} after={c1!r} live={live}')
        log('1 check and line are fully drawn after the tick',drawn[0]=='inset(0px)' and drawn[1].startswith('100%') and drawn[2]=='none',drawn)
        await pg.tap('.checks label >> nth=2'); await pg.wait_for_timeout(100); c2=await pg.inner_text('#gcount')
        await pg.tap('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(300); c3=await pg.inner_text('#gcount')
        log('1 count follows ticks and survives a redraw',c2==f'2 of {n}' and c3==f'2 of {n}',f'{c2!r} {c3!r}')
        for k in range(n):
            if not await pg.locator('.checks input').nth(k).is_checked(): await pg.locator('.checks label').nth(k).tap()
        await pg.wait_for_timeout(200); c4=await pg.inner_text('#gcount'); allc=await pg.evaluate(CLS,'gcount')
        await pg.tap('.checks label >> nth=1'); await pg.wait_for_timeout(100); c5=await pg.inner_text('#gcount')
        await pg.reload(); await pg.wait_for_timeout(600); c6=await pg.inner_text('#gcount')
        log('1 all ticked says "All set"; untick goes back; reload keeps it',c4=='All set' and 'all' in allc and c5==f'{n-1} of {n}' and c6==f'{n-1} of {n}' and not errs,f'{c4!r} {c5!r} reload={c6!r} errs={errs[:2]}'); await ctx.close()
        # 2 hold speeds up, one redraw on release
        ctx,pg,errs=await fresh(b); await sample(pg)
        d0=await pg.evaluate('window.__draws'); a0=await pg.evaluate('window.__amt'); meta0=await pg.inner_text('#sMeta'); amt0=await pg.inner_text('.checks b[data-a="s:boneless chicken thighs"]')
        box=await pg.locator('[data-t=want][data-d="1"]').bounding_box(); await pg.mouse.move(box['x']+22,box['y']+22); await pg.mouse.down()
        await pg.wait_for_timeout(500); v1=int(await pg.input_value('#want')); await pg.wait_for_timeout(900); v2=int(await pg.input_value('#want'))
        await pg.wait_for_timeout(200); v3=int(await pg.input_value('#want')); await pg.wait_for_timeout(900); v4=int(await pg.input_value('#want'))
        dmid=await pg.evaluate('window.__draws'); metamid=await pg.inner_text('#sMeta'); amid=await pg.evaluate('window.__amt')
        await pg.mouse.up(); await pg.wait_for_timeout(60); nchg=await pg.evaluate("document.querySelectorAll('#sheet .chg').length"); await pg.wait_for_timeout(400)
        v5=int(await pg.input_value('#want')); d1=await pg.evaluate('window.__draws'); a1=await pg.evaluate('window.__amt'); meta1=await pg.inner_text('#sMeta'); amt1=await pg.inner_text('.checks b[data-a="s:boneless chicken thighs"]')
        left=await pg.evaluate("document.querySelectorAll('#sheet .chg').length"); saved=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')||'[]')[0].w")
        slow,fast=v2-v1,v4-v3
        log('2 holding + is faster after 1.5 s (same 0.9 s window before and after)',slow>=5 and fast>=slow*1.4,f'0.5-1.4s: +{slow}  1.6-2.5s: +{fast}  ({v1},{v2},{v3},{v4})')
        log('2 while held only the number changes',dmid==d0 and metamid==meta0 and amid==a0 and v4>14,f'draws {d0}->{dmid} meta {metamid!r}')
        # v5 may be one or two counts past v4: a 60 ms repeat can fire between reading v4 and lifting the finger (timing, not a bug)
        log('2 one redraw on release, with the final number',d1==d0+1 and v4<=v5<=v4+2 and meta1!=meta0 and amt1!=amt0 and saved==v5,f'draws {d0}->{d1} want={v5} saved={saved} {meta0!r}->{meta1!r} {amt0!r}->{amt1!r}')
        log('4 changed amounts animate once on release, then the marker is cleared',a1>a0 and nchg>0 and left<=1,f'animations {a0}->{a1} marked at release={nchg} left after={left}')
        # a single tap also shows what changed, only on the visible tab
        a2=await pg.evaluate('window.__amt'); await pg.tap('[data-t=want][data-d="1"]'); await pg.wait_for_timeout(40)
        vis=await pg.evaluate("[...document.querySelectorAll('#sheet .chg')].every(e=>e.offsetParent)"); mcls=await pg.evaluate(CLS,'sMeta'); await pg.wait_for_timeout(300); a3=await pg.evaluate('window.__amt')
        await pg.tap('[data-tab=recipe]'); await pg.wait_for_timeout(300); a4=await pg.evaluate('window.__amt')
        log('4 a tap animates the changed amounts and the "× the recipe" line; switching tab does not replay it',a3>a2 and vis and 'chg' in mcls and a4==a3 and not errs,f'{a2}->{a3}->{a4} meta class={mcls!r} errs={errs[:2]}')
        # soft stop
        await pg.fill('#want','2'); await pg.locator('#want').blur(); await pg.wait_for_timeout(200)
        dis0=await pg.evaluate(CLS2,'[data-t=want][data-d="-1"]'); await pg.tap('[data-t=want][data-d="-1"]'); await pg.wait_for_timeout(350)
        dis1=await pg.evaluate(CLS2,'[data-t=want][data-d="-1"]'); op=await pg.evaluate("getComputedStyle(document.querySelector('[data-t=want][data-d=\"-1\"]')).opacity")
        await pg.tap('[data-t=want][data-d="-1"]'); await pg.wait_for_timeout(30); ncls=await pg.evaluate(CLS,'want'); val=await pg.input_value('#want')
        size=await pg.evaluate("(()=>{const r=document.querySelector('[data-t=want][data-d=\"-1\"]').getBoundingClientRect();return [r.width,r.height]})()")
        log('2 at 1 the minus dims to 40%, a further tap nudges the number and it stays 1',dis0=='' and dis1=='end' and abs(float(op)-.4)<.01 and 'nl' in ncls and val=='1' and size==[44,44],f'class {dis0!r}->{dis1!r} opacity={op} class={ncls!r} val={val} size={size}')
        await pg.fill('#want','990'); await pg.locator('#want').blur(); await pg.wait_for_timeout(200); d2=await pg.evaluate('window.__draws')
        await hold(pg,'[data-t=want][data-d="1"]',2200); await pg.wait_for_timeout(300); val=await pg.input_value('#want'); d3=await pg.evaluate('window.__draws')
        disp=await pg.evaluate(CLS2,'[data-t=want][data-d="1"]'); dism=await pg.evaluate(CLS2,'[data-t=want][data-d="-1"]'); ncls=await pg.evaluate(CLS,'want')
        log('2 a hold stops at 999, nudges, dims the plus, and redraws once',val=='999' and disp=='end' and dism=='' and 'nr' in ncls and d3==d2+1 and not errs,f'val={val} plus={disp} minus={dism} class={ncls!r} draws {d2}->{d3} errs={errs[:2]}'); await ctx.close()
        # 3 close animations, focus straight away
        ctx,pg,errs=await fresh(b); await sample(pg)
        await pg.tap('#dShare'); await pg.wait_for_timeout(450); opened=await pg.is_visible('#menu'); f0=await pg.evaluate(FOC)
        await pg.tap('#menuX'); f1=await pg.evaluate(FOC); c1=await pg.evaluate(CLS,'menu'); await pg.wait_for_timeout(400); c2=await pg.evaluate(CLS,'menu')
        log('3 Share sheet: Cancel moves focus back at once, sheet animates out, then hides',opened and f1=='dShare' and 'out' in c1 and 'hidden' not in c1 and 'hidden' in c2 and 'out' not in c2,f'focus in sheet={f0} after={f1} during={c1!r} end={c2!r}')
        await pg.tap('#dShare'); await pg.wait_for_timeout(450); await pg.touchscreen.tap(195,80); await pg.wait_for_timeout(400); c3=await pg.evaluate(CLS,'menu')
        await pg.tap('#dShare'); await pg.wait_for_timeout(450); await pg.keyboard.press('Escape'); f2=await pg.evaluate(FOC); await pg.wait_for_timeout(100)
        await pg.tap('#dShare'); await pg.wait_for_timeout(450); c4=await pg.evaluate(CLS,'menu'); vis=await pg.is_visible('#menuX'); await pg.tap('[data-link]'); await pg.wait_for_timeout(500); c5=await pg.evaluate(CLS,'menu'); toast=await pg.inner_text('#toast')
        log('3 Share sheet: backdrop tap and Escape close it; reopening while it fades works; Copy link still works','hidden' in c3 and f2=='dShare' and 'hidden' not in c4 and 'out' not in c4 and vis and 'hidden' in c5 and toast=='Link copied',f'backdrop={c3!r} esc focus={f2} reopened={c4!r} toast={toast!r}')
        await pg.evaluate('scrollTo(0,300)'); await pg.wait_for_timeout(200); y0=await pg.evaluate('scrollY')
        await pg.tap('#dCook'); await pg.wait_for_timeout(450); o=await pg.is_visible('#cook'); st=await pg.evaluate('!!(history.state&&history.state.cook)')
        await pg.tap('#cNext'); await pg.tap('#cClose'); f3=await pg.evaluate(FOC); c6=await pg.evaluate(CLS,'cook'); ov=await pg.evaluate('document.body.style.overflow')
        await pg.wait_for_timeout(450); c7=await pg.evaluate(CLS,'cook'); st2=await pg.evaluate('!!(history.state&&history.state.cook)'); y=await pg.evaluate('scrollY'); f4=await pg.evaluate(FOC)
        log('3 cook mode: Close moves focus back at once, fades out, then hides; page not moved',o and st and f3=='dCook' and 'out' in c6 and 'hidden' not in c6 and ov=='' and 'hidden' in c7 and 'out' not in c7 and not st2 and y==y0 and f4=='dCook',f'focus={f3}/{f4} during={c6!r} end={c7!r} cookState={st}->{st2} y={y0}->{y}')
        await pg.tap('#dCook'); await pg.wait_for_timeout(450); await pg.tap('#cClose'); await pg.wait_for_timeout(80); await pg.tap('#dCook'); await pg.wait_for_timeout(600)
        c8=await pg.evaluate(CLS,'cook'); stp=await pg.inner_text('#cStep'); op=await pg.evaluate("getComputedStyle(document.getElementById('cook')).opacity")
        await pg.go_back(); await pg.wait_for_timeout(500); c9=await pg.evaluate(CLS,'cook'); v=await pg.evaluate("!document.getElementById('v-sheet').classList.contains('hidden')"); f5=await pg.evaluate(FOC)
        log('3 cook mode: reopening while it fades works; Back closes it and stays on the recipe','hidden' not in c8 and 'out' not in c8 and op=='1' and stp.startswith('Step 1') and 'hidden' in c9 and v and f5=='dCook' and not errs,f'reopened={c8!r} opacity={op} {stp!r} afterBack={c9!r} sheet={v} focus={f5} errs={errs[:2]}'); await ctx.close()
        # 3 removed batch row folds
        ctx,pg,errs=await fresh(b)
        for txt in ("Bean chili\nServes 4\n2 cans beans\n1 onion\n1. Cook 20 minutes.",REC2):
            await pg.tap('#pasteToggle') if await pg.is_hidden('#paste') else None
            await pg.fill('#paste',txt); await pg.tap('#usePaste'); await pg.wait_for_selector('#v-sheet:not(.hidden)'); await pg.wait_for_timeout(300); await pg.tap('#newRec'); await pg.wait_for_timeout(300)
        r0=await pg.locator('#savedList .open').count(); await pg.locator('#savedList .rm').first.scroll_into_view_if_needed(); await pg.tap('#savedList .rm >> nth=0')
        st=await pg.evaluate("(()=>{const g=document.querySelector('#savedList li.gone');return [document.querySelectorAll('#savedList .open').length,!!g,g&&g.getAttribute('aria-hidden'),g?g.querySelectorAll('button,a,input').length:-1,JSON.parse(localStorage.getItem('bd-batches')).length,document.activeElement.className]})()")
        await pg.wait_for_timeout(900); g2=await pg.locator('#savedList li.gone').count(); lis=await pg.locator('#savedList li').count()
        await pg.tap('#toast button'); await pg.wait_for_timeout(300); r2=await pg.locator('#savedList .open').count()
        log('3 removed batch: list, storage and focus change at once; a hidden copy folds shut and is gone; Undo restores',r0==2 and st==[1,True,'true',0,1,'open'] and g2==0 and lis==1 and r2==2 and not errs,f'rows {r0}->{st[0]}->{r2} ghost={st[1:4]} stored={st[4]} focus={st[5]} ghostAfter={g2} errs={errs[:2]}'); await ctx.close()
        # 6 top-bar title
        ctx,pg,errs=await fresh(b); await sample(pg)
        BAR="(()=>{const b=document.querySelector('.bar'),t=document.getElementById('barTitle'),m=document.querySelector('.mark');return [b.classList.contains('t'),getComputedStyle(t).opacity,getComputedStyle(m).opacity,t.textContent,t.getAttribute('aria-hidden'),t.scrollWidth>t.clientWidth,getComputedStyle(t).pointerEvents]})()"
        top=await pg.evaluate(BAR); title=await pg.inner_text('#sTitle')
        await pg.evaluate('scrollTo(0,500)'); await pg.wait_for_timeout(500); down=await pg.evaluate(BAR)
        log('6 recipe name replaces the logo once the title scrolls under the bar; hidden from screen readers',top[0] is False and top[1]=='0' and top[2]=='1' and top[6]=='none' and down[0] is True and down[1]=='1' and down[2]=='0' and down[3]==title and down[4]=='true',f'top={top} scrolled={down}')
        await pg.tap('#barTitle'); await pg.wait_for_timeout(1200); y=await pg.evaluate('scrollY'); back=await pg.evaluate(BAR)
        log('6 tapping the name scrolls to the top and the logo comes back',y==0 and back[0] is False and back[2]=='1',f'y={y} {back}')
        await pg.evaluate('scrollTo(0,500)'); await pg.wait_for_timeout(300); await pg.keyboard.press('Tab'); await pg.keyboard.press('Shift+Tab'); await pg.wait_for_timeout(50)
        await pg.evaluate("document.querySelector('.mark').focus()"); await pg.go_back(); await pg.wait_for_timeout(500); home=await pg.evaluate(BAR)
        await pg.tap('#pasteToggle'); await pg.fill('#paste',LONG); await pg.tap('#usePaste'); await pg.wait_for_timeout(600)
        await pg.evaluate('scrollTo(0,500)'); await pg.wait_for_timeout(500); lng=await pg.evaluate(BAR); sw=await pg.evaluate("(()=>{const a=document.getElementById('barTitle').getBoundingClientRect(),s=document.getElementById('theme').getBoundingClientRect();return [a.right<=s.left,a.height,document.documentElement.scrollWidth<=innerWidth]})()")
        log('6 not shown on the home page; a long name is cut with an ellipsis on one line, clear of the switch',home[0] is False and lng[0] is True and lng[5] is True and sw==[True,52,True] and not errs,f'home={home[0]} long={lng} layout={sw} errs={errs[:2]}'); await ctx.close()
        # 7 press states, Copy
        ctx,pg,errs=await fresh(b); await sample(pg)
        hl=await pg.evaluate("[...document.querySelectorAll('.checks label,.seg button,.mrow,#dShare,.mark')].every(e=>getComputedStyle(e).webkitTapHighlightColor==='rgba(0, 0, 0, 0)')")
        async def pressed(sel):
            bx=await pg.locator(sel).first.bounding_box(); await pg.mouse.move(bx['x']+bx['width']-30,bx['y']+bx['height']/2); await pg.mouse.down()
            s=await pg.evaluate("(s)=>getComputedStyle(document.querySelector(s)).boxShadow",sel); await pg.mouse.move(0,0); await pg.mouse.up(); await pg.wait_for_timeout(250)
            s2=await pg.evaluate("(s)=>getComputedStyle(document.querySelector(s)).boxShadow",sel); return 'inset' in s and s2=='none'
        pr={'grocery row':await pressed('.checks label'),'tab':await pressed('[data-tab=store]')}
        await pg.tap('#dShare'); await pg.wait_for_timeout(450); pr['share row']=await pressed('[data-print]'); await pg.wait_for_timeout(400)  # releasing off the row lands on the backdrop, which closes the sheet
        if await pg.is_visible('#menuX'): await pg.tap('#menuX'); await pg.wait_for_timeout(400)
        # tabs: no fill on press (15 Nov, Michael): the sliding pill is the only feedback, so nothing pops up under the finger before the pill arrives
        log('7 no tap flash; rows and share rows fill while pressed and clear on release; tabs never fill (the pill slides)',hl and pr['grocery row'] and pr['share row'] and not pr['tab'],f'highlight off={hl} {pr}')
        await pg.tap('[data-copy]'); await pg.wait_for_timeout(350); t1=await pg.inner_text('[data-copy]'); svg=await pg.locator('[data-copy] svg.ck').count(); clip=await pg.evaluate('navigator.clipboard.readText()')
        await pg.wait_for_timeout(1700); t2=await pg.inner_text('[data-copy]'); svg2=await pg.locator('[data-copy] svg').count()
        log('7 Copy swaps to a check and "Copied", then back',t1.strip()=='Copied' and svg==1 and 'chicken' in clip and t2=='Copy' and svg2==0,f'{t1!r} check={svg} then {t2!r}')
        await pg.tap('#newRec'); await pg.wait_for_timeout(300); await pg.tap('#sample'); await pg.wait_for_timeout(500); await pg.tap('[data-t=want][data-d="1"]'); await pg.tap('#newRec'); await pg.wait_for_timeout(300)
        pr2=await pressed('#savedList .open'); small=await pg.evaluate("[...document.querySelectorAll('button,a,label')].filter(e=>e.offsetParent&&(e.getBoundingClientRect().height<44)&&e.id!=='theme').map(e=>e.outerHTML.slice(0,60))")
        log('7 saved batch row fills while pressed; no tap target under 44 px',pr2 and not small and not errs,f'{pr2} small={small} errs={errs[:2]}'); await ctx.close()
        # reduced motion: everything still works, end states, no errors
        ctx,pg,errs=await fresh(b,reduced_motion='reduce'); await sample(pg)
        n=await pg.locator('.checks input').count(); await pg.tap('.checks label >> nth=0'); await pg.wait_for_timeout(350); c1=await pg.inner_text('#gcount')
        tick=await pg.evaluate("(()=>{const i=document.querySelector('.checks input:checked');const a=getComputedStyle(i,'::after');return [a.opacity,a.clipPath,getComputedStyle(i.nextElementSibling.querySelector('.tx')).backgroundSize.split(' ')[0]]})()")
        d0=await pg.evaluate('window.__draws'); await hold(pg,'[data-t=want][data-d="1"]',1200); await pg.wait_for_timeout(300); d1=await pg.evaluate('window.__draws'); w=int(await pg.input_value('#want'))
        moved=await pg.evaluate("[...document.getAnimations()].filter(a=>a.animationName==='amt').length")
        await pg.tap('#dShare'); await pg.wait_for_timeout(300); mo=await pg.is_visible('#menu'); await pg.tap('#menuX'); f1=await pg.evaluate(FOC); await pg.wait_for_timeout(300); mc=await pg.evaluate(CLS,'menu')
        await pg.tap('#dCook'); await pg.wait_for_timeout(300); co=await pg.is_visible('#cook'); await pg.tap('#cClose'); f2=await pg.evaluate(FOC); await pg.wait_for_timeout(300); cc=await pg.evaluate(CLS,'cook')
        await pg.evaluate('scrollTo(0,500)'); await pg.wait_for_timeout(400); bt=await pg.evaluate("document.querySelector('.bar').classList.contains('t')"); await pg.tap('#barTitle'); await pg.wait_for_timeout(200); y=await pg.evaluate('scrollY')
        await pg.fill('#want','1'); await pg.locator('#want').blur(); await pg.tap('[data-t=want][data-d="-1"]'); await pg.wait_for_timeout(300); v=await pg.input_value('#want')
        await pg.tap('#newRec'); await pg.wait_for_timeout(300); r0=await pg.locator('#savedList li').count(); await pg.tap('#savedList .rm >> nth=0'); r1=await pg.locator('#savedList li').count()
        log('reduced motion: tick, count, hold, Share, cook mode, top-bar title, soft stop and remove all work with no movement',c1==f'1 of {n}' and tick[0]=='1' and tick[1] in ('none','inset(0px)') and tick[2]=='100%' and d1==d0+1 and w>14 and moved==0 and mo and f1=='dShare' and 'hidden' in mc and co and f2=='dCook' and 'hidden' in cc and bt and y==0 and v=='1' and r0==1 and r1==0 and not errs,
            f'count={c1!r} tick={tick} draws {d0}->{d1} want={w} slideAnims={moved} share={mo}/{f1}/{mc!r} cook={co}/{f2}/{cc!r} bar={bt} y={y} v={v} rows {r0}->{r1} errs={errs[:3]}'); await ctx.close()
        await b.close()
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)} checks, {len(bad)} failed')
asyncio.run(main())
