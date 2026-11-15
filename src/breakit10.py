# Guide pages (the search pages): every page loads clean, its calculator shows what engine.js gives, the data blocks parse,
# links work, nothing scrolls sideways at 320 / 390 / 1440, light and dark. Nothing leaves the machine.
# Expected numbers come from test_guides.js, which works them out from engine.js and the written rules, not from guides.js.
import asyncio, json, re, subprocess, os, threading, http.server, functools, hashlib, base64
import xml.etree.ElementTree as ET
from playwright.async_api import async_playwright
PORT=8766; U=f'http://127.0.0.1:{PORT}/'; SITE='https://batch.recipes/'
AND='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36'
IOS='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
R=[]
os.makedirs('breakit',exist_ok=True)
def log(n,ok,note=''):
    R.append((n,'ok' if ok else 'FAIL',str(note))); open('breakit/r10.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',n,'|',str(note)[:300])
class H(http.server.SimpleHTTPRequestHandler):  # clean URLs, the way Vercel serves them: /guides is guides.html
    def translate_path(self,path):
        p=super().translate_path(path)
        return p+'.html' if not os.path.exists(p) and os.path.exists(p+'.html') else p
    def log_message(self,*a): pass
INIT="""document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective+' '+e.blockedURI));window.__ev=[];window.umami={track:(n,d)=>window.__ev.push([n,d])};"""
async def fresh(b,slug,w=390,h=844,scheme='light',mobile=True,ua=None,js=True,block=()):
    kw=dict(viewport={'width':w,'height':h},color_scheme=scheme,is_mobile=mobile,has_touch=mobile,java_script_enabled=js)
    if ua: kw['user_agent']=ua
    ctx=await b.new_context(**kw); errs=[]
    for pat in ('**/*.umami.is/**','**/pagead2.googlesyndication.com/**','**/cdn.jsdelivr.net/**','**/_vercel/**')+tuple(block): await ctx.route(pat,lambda r:r.abort())
    await ctx.add_init_script(INIT); pg=await ctx.new_page()
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    r=await pg.goto(U+slug); await pg.wait_for_timeout(200)
    return ctx,pg,errs,(r.status if r else 0)
norm=lambda s:re.sub(r'\s+',' ',s or '').strip()
READ="""(()=>{const t=e=>e?e.innerText.replace(/\\s+/g,' ').trim():'';const o=document.querySelector('.calc .out');
 return {big:t(document.querySelector('[data-o=big]')),sub:t(document.querySelector('[data-o=sub]')),
  rows:o?[...o.querySelectorAll('tr')].slice(1).map(r=>[...r.children].map(t)):[],
  list:o?[...o.querySelectorAll('.aisle,li')].map(e=>(e.matches('.aisle')?'#':'')+t(e)):[],
  vals:Object.fromEntries([...document.querySelectorAll('.step input,.step output')].map(e=>[e.id,e.value]))}})()"""
async def setv(pg,vals):
    for k,v in vals.items():
        if await pg.evaluate("id=>document.getElementById(id).tagName",k)=='INPUT':
            await pg.fill('#'+k,str(v)); await pg.dispatch_event('#'+k,'change')
        else:  # half-pound stepper: tap to it
            cur=await pg.evaluate("""id=>{const m={'½':.5,'¼':.25,'¾':.75};const s=document.getElementById(id).value;const f=m[s.slice(-1)];return f?(parseInt(s)||0)+f:+s}""",k)
            n=round((v-cur)/.5); sel=f'#{k} ~ button' if n>0 else f'.step:has(#{k}) button[data-d="-1"]'
            for _ in range(abs(n)): await pg.click(sel)
    await pg.wait_for_timeout(30)
OV="(()=>{const W=document.documentElement.clientWidth;const bad=[...document.querySelectorAll('body *')].filter(e=>{if(!e.offsetParent)return false;const r=e.getBoundingClientRect();return r.width>0&&(r.right>W+1||r.left<-1)}).slice(0,4).map(e=>e.tagName+'.'+e.className);return [document.documentElement.scrollWidth,W,bad]})()"
SMALL="(()=>[...document.querySelectorAll('.step button,.step input,.step output,.btn,.gl a,footer a,.mark')].map(e=>{const r=e.getBoundingClientRect();return [e.tagName+(e.className?'.'+e.className:'')+' '+e.innerText.slice(0,20),Math.round(r.width),Math.round(r.height)]}).filter(x=>x[1]<44||x[2]<44))()"
LUM="""(()=>{const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number).slice(0,3).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
 const cr=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};const cs=e=>getComputedStyle(e);const body=cs(document.body).backgroundColor;
 const card=document.querySelector('.card');const cb=card?cs(card).backgroundColor:body;const q=(s)=>document.querySelector(s);const out={body};
 const pair=(n,s,bg)=>{const e=q(s);if(e)out[n]=Math.round(cr(cs(e).color,bg)*100)/100};
 pair('text','.lead',body);pair('sub','.sub',cb);pair('big','.big',cb);pair('link','.gl a',body);pair('muted','.gl a span',body);pair('foot','footer a',body);pair('th','.tbl th',cb);
 const b=q('.btn');if(b)out.btn=Math.round(cr(cs(b).color,cs(b).backgroundColor)*100)/100;
 const st=q('.step button');if(st)out.step=Math.round(cr(cs(st).color,cs(q('.step')).backgroundColor)*100)/100;return out})()"""

async def main():
    srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(H,directory='site')); threading.Thread(target=srv.serve_forever,daemon=True).start()
    out=subprocess.run(['node','test_guides.js'],capture_output=True,text=True); T=json.loads(out.stdout)
    for n,ok,note in T['static']: log('engine: '+n,ok=='ok',note)
    CASES=T['cases']; slugs=list(CASES)
    log('ten guide pages built',len(slugs)==10 and all(os.path.exists(f'site/{s}.html') for s in slugs),len(slugs))
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for slug in slugs:
            html=open(f'site/{slug}.html').read()
            ctx,pg,errs,st=await fresh(b,slug,ua=IOS)
            h1=norm(await pg.inner_text('h1')); lead=norm(await pg.inner_text('.lead'))
            log(f'{slug}: loads at its clean URL, one h1 that is a question',st==200 and await pg.locator('h1').count()==1 and h1.endswith('?'),h1)
            # head
            head=await pg.evaluate("""()=>({t:document.title,d:document.querySelector('meta[name=description]').content,c:(document.querySelector('link[rel=canonical]')||{}).href,
              og:Object.fromEntries([...document.querySelectorAll('meta[property^="og:"]')].map(m=>[m.getAttribute('property'),m.content])),tw:(document.querySelector('meta[name="twitter:card"]')||{}).content})""")
            log(f'{slug}: title, description, canonical and og tags are for this question',head['t']==h1+' · batch.recipes' and 50<=len(head['d'])<=160 and head['c']==SITE+slug and head['og'].get('og:url')==SITE+slug and head['og'].get('og:image')==SITE+'og.png' and head['og'].get('og:title')==h1 and head['og'].get('og:description')==head['d'] and head['tw']=='summary_large_image',json.dumps(head)[:300])
            # data blocks
            try:
                blocks=[json.loads(x) for x in await pg.locator('script[type="application/ld+json"]').all_inner_texts()]; g={n['@type']:n for n in blocks[0]['@graph']}
                qa=await pg.evaluate("()=>[...document.querySelectorAll('.g h3')].map(h=>[h.innerText.trim(),h.nextElementSibling.innerText.replace(/\\s+/g,' ').trim()])")
                ld=[[q['name'],norm(q['acceptedAnswer']['text'])] for q in g['FAQPage']['mainEntity']]
                ok=len(blocks)==1 and g['WebPage']['url']==SITE+slug and g['WebPage']['name']==h1 and g['WebPage']['description']==head['d'] and ld[0]==[h1,lead] and ld[1:]==[[a,norm(c)] for a,c in qa] and 2<=len(qa)<=4
                log(f'{slug}: JSON-LD parses; WebPage and FAQPage say what the page says ({len(ld)} questions)',ok,json.dumps([ld,qa])[:300] if not ok else '')
            except Exception as e: log(f'{slug}: JSON-LD parses',False,repr(e)[:200])
            # CSP: one inline script, allowed by its hash
            inl=re.findall(r'<script>(.*?)</script>',html,re.S); csp=re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"',html)
            hs=["'sha256-"+base64.b64encode(hashlib.sha256(m.encode()).digest()).decode()+"'" for m in inl]
            inl=[i for i in inl if 'var C=' in i]+[i for i in inl if 'var C=' not in i]  # the calculator first, then the shell's script (theme, source, Vercel Web Analytics)
            log(f'{slug}: two small inline scripts (calculator, shell), hashed in the page\'s CSP; no unsafe-inline for scripts',len(inl)==2 and len(inl[0])<6000 and len(inl[1])<3000 and csp and all(h in csp.group(1) for h in hs) and "'unsafe-inline'" not in csp.group(1).split('script-src')[1].split(';')[0],[len(i) for i in inl])
            # what a crawler gets without scripts is what the calculator shows
            first=await pg.evaluate(READ)
            c2,p2,e2,_=await fresh(b,slug,js=False); raw=await p2.evaluate(READ) if False else None
            stat={'big':norm(await p2.inner_text('[data-o=big]')),'sub':norm(await p2.inner_text('[data-o=sub]')),'out':norm(await p2.inner_text('.calc .out')) if await p2.locator('.calc .out').count() else ''}
            live_out=norm(await pg.inner_text('.calc .out')) if await pg.locator('.calc .out').count() else ''
            log(f'{slug}: with scripts off the page already has the answer and the same numbers',stat['big']==first['big'] and stat['sub']==first['sub'] and stat['out']==live_out and len(norm(await p2.inner_text('.lead')))>40,stat); await c2.close()
            # the calculator against engine.js
            bad=[]
            for c in CASES[slug]:
                await setv(pg,c['set']); got=await pg.evaluate(READ)
                if got['big']!=c['big'] or any(s not in got['sub'] for s in c['sub']) or ('rows' in c and got['rows']!=c['rows']) or ('list' in c and got['list']!=c['list']):
                    bad.append({'set':c['set'],'want':[c['big'],c['sub'],c.get('rows'),c.get('list')],'got':[got['big'],got['sub'],got['rows'],got['list']]})
            sets=[list(c['set'].values())[0] for c in CASES[slug]]
            log(f'{slug}: calculator matches engine.js at {len(CASES[slug])} settings (first stepper at {sorted(set(sets))})',not bad,json.dumps(bad[:2],ensure_ascii=False)[:600])
            # the stepper itself
            cid=await pg.evaluate("()=>document.querySelector('.step input,.step output').id"); isin=await pg.evaluate("id=>document.getElementById(id).tagName=='INPUT'",cid)
            lim=json.loads(re.search(r'var C=(\[.*?\]);',inl[0]).group(1))[0]; stp=.5 if lim['h'] else 1
            if isin:
                await setv(pg,{cid:14 if lim['max']>=14 else 2}); v0=float(await pg.input_value('#'+cid)); b0=(await pg.evaluate(READ))
                await pg.tap(f'.step:has(#{cid}) button[data-d="1"]'); v1=float(await pg.input_value('#'+cid)); await pg.tap(f'.step:has(#{cid}) button[data-d="-1"]'); await pg.tap(f'.step:has(#{cid}) button[data-d="-1"]'); v2=float(await pg.input_value('#'+cid))
                log(f'{slug}: + and − step by one tap each',v1==v0+1 and v2==v0-1,[v0,v1,v2])
                res=[]
                for typed in ['0','-5','abc','0x10','','99999','7.5']:
                    await setv(pg,{cid:2}); await pg.fill('#'+cid,typed); await pg.dispatch_event('#'+cid,'change'); res.append(await pg.input_value('#'+cid))
                log(f'{slug}: typed 0 and negatives become {lim["min"]}, junk goes back to the last good number, too big becomes {lim["max"]}',res==[str(lim['min']),str(lim['min']),'2','2','2',str(lim['max']),'2'],res)
                await setv(pg,{cid:lim['min']}); bmin=(await pg.evaluate(READ))['big']; await pg.tap(f'.step:has(#{cid}) button[data-d="-1"]')
                e1=await pg.evaluate(f"()=>[document.querySelector('.step:has(#{cid}) button[data-d=\"-1\"]').classList.contains('end'),document.querySelector('.step:has(#{cid}) button[data-d=\"1\"]').classList.contains('end'),document.getElementById('{cid}').value]")
                await setv(pg,{cid:lim['max']}); await pg.tap(f'.step:has(#{cid}) button[data-d="1"]')
                e2_=await pg.evaluate(f"()=>[document.querySelector('.step:has(#{cid}) button[data-d=\"-1\"]').classList.contains('end'),document.querySelector('.step:has(#{cid}) button[data-d=\"1\"]').classList.contains('end'),document.getElementById('{cid}').value]")
                log(f'{slug}: stops at {lim["min"]} and {lim["max"]}; that button dims',e1==[True,False,str(lim['min'])] and e2_==[False,True,str(lim['max'])],[e1,e2_])
                # typing updates as you type, before leaving the box
                await setv(pg,{cid:2}); await pg.click('#'+cid); await pg.keyboard.press('Control+A'); await pg.keyboard.type('3'); live=(await pg.evaluate(READ))['big']; await setv(pg,{cid:3}); log(f'{slug}: answer updates while typing',live==(await pg.evaluate(READ))['big'],live)
                # hold
                await setv(pg,{cid:lim['min']}); bx=await pg.locator(f'.step:has(#{cid}) button[data-d="1"]').bounding_box()
                await pg.mouse.move(bx['x']+22,bx['y']+22); await pg.mouse.down(); await pg.wait_for_timeout(1000); await pg.mouse.up(); await pg.wait_for_timeout(250); hv=float(await pg.input_value('#'+cid))
                log(f'{slug}: holding + keeps counting, and stops on release',lim['min']+3<=hv<=lim['min']+8 or hv==lim['max'],hv)
            # keyboard on the buttons
            await setv(pg,{cid:lim['val']}); await pg.focus(f'.step:has(#{cid}) button[data-d="1"]'); await pg.keyboard.press('Enter'); kv=await pg.evaluate(f"()=>document.getElementById('{cid}').value")
            log(f'{slug}: Enter on + works from the keyboard',kv!=first['vals'][cid],kv)
            lab=await pg.evaluate("()=>[...document.querySelectorAll('.step')].map(s=>[!!document.querySelector('label[for=\"'+s.querySelector('input,output').id+'\"]'),...[...s.querySelectorAll('button')].map(b=>b.getAttribute('aria-label'))])")
            log(f'{slug}: every stepper has a label and named buttons; the result is a live region',all(l[0] and l[1] and l[2] for l in lab) and await pg.get_attribute('.res','aria-live')=='polite',lab)
            small=await pg.evaluate(SMALL); log(f'{slug}: no tap target under 44 px (steppers, button, guide links, footer)',not small,small)
            sz=await pg.evaluate("()=>[...document.querySelectorAll('.step')].map(s=>{const r=s.getBoundingClientRect();return [r.width,r.height]})")
            log(f'{slug}: steppers are 148 x 52, the home page\'s size',all(s==[148,52] for s in sz),sz)
            # words
            body=await pg.inner_text('main')
            log(f'{slug}: no em or en dash in the page\'s words','—' not in body and '–' not in body)
            keep=re.findall(r'(?i)\b(\d+\s*(?:days?|weeks?|months?|hours?)|keeps? for|use[- ]by|expires?|shelf life|eat within|safe to eat|healthy|calories|protein per)\b',body)
            log(f'{slug}: no keep times and no diet or health claims',not keep,keep)
            log(f'{slug}: How it works has 3 to 5 lines; a "Plan your own recipe" button goes home',3<=await pg.locator('.g h2:has-text("How it works") + ul li, .g h2:has-text("Steps") + ol li').count()<=5 and await pg.inner_text('.btn')=='Plan your own recipe' and await pg.get_attribute('.btn','href')=='./')
            # links
            hrefs=await pg.evaluate("()=>[...new Set([...document.querySelectorAll('a[href]')].map(a=>a.href))]"); dead=[]
            for h in hrefs:
                if h.startswith(U):
                    r=await ctx.request.get(h)
                    if r.status!=200: dead.append([h,r.status])
                else: dead.append([h,'off site'])
            log(f'{slug}: every link opens ({len(hrefs)}), all on this site',not dead,dead)
            log(f'{slug}: no console or CSP errors through all of that',not errs,errs[:3]); await ctx.close()
            # the button really lands on the home page
            ctx,pg,errs,_=await fresh(b,slug,ua=AND); await pg.tap('.btn'); await pg.wait_for_selector('#choose'); ev=await pg.evaluate('location.pathname')
            log(f'{slug}: "Plan your own recipe" opens the home page, Choose screenshots showing (Android)',ev=='/' and await pg.is_visible('#choose') and not errs,[ev,errs[:2]]); await ctx.close()
            # sizes and themes
            for w,h,mob in [(320,568,True),(390,844,True),(1440,900,False)]:
                for scheme in ['light','dark']:
                    ctx,pg,errs,_=await fresh(b,slug,w=w,h=h,scheme=scheme,mobile=mob)
                    ov=await pg.evaluate(OV); c=await pg.evaluate(LUM); want='rgb(255, 255, 255)' if scheme=='light' else 'rgb(0, 0, 0)'
                    low={k:v for k,v in c.items() if k!='body' and v<4.5}
                    # set the biggest numbers too, so the widest answer is what gets measured
                    big={k:v for k,v in [(x['id'],x['max']) for x in json.loads(re.search(r'var C=(\[.*?\]);',html).group(1))] if True}
                    await setv(pg,{k:v for k,v in big.items() if await pg.evaluate("id=>document.getElementById(id).tagName=='INPUT'",k)}); ov2=await pg.evaluate(OV)
                    ok=ov[0]<=ov[1] and not ov[2] and ov2[0]<=ov2[1] and not ov2[2] and c['body']==want and not low and not errs
                    log(f'{slug} {w} {scheme}: no sideways scroll (also at the biggest numbers), right colours, contrast 4.5:1 or better',ok,[ov,ov2,c,errs[:2]] if not ok else min(v for k,v in c.items() if k!='body')); await ctx.close()
            # evenness at 390 and 1440
            for w,mob in [(390,True),(1440,False)]:
                ctx,pg,errs,_=await fresh(b,slug,w=w,h=900,mobile=mob)
                m=await pg.evaluate("""()=>{const W=document.documentElement.clientWidth,r=s=>document.querySelector(s).getBoundingClientRect(),c=r('.card'),a=r('.g'),s0=r('.set'),st=r('.step'),lab=r('.set label'),btn=r('.btn'),big=r('.big');
                  return {colL:Math.round(a.left),colR:Math.round(W-a.right),cardL:Math.round(c.left-a.left),cardR:Math.round(a.right-c.right),padL:Math.round(lab.left-c.left),padR:Math.round(c.right-st.right),padT:Math.round(s0.top-c.top),bigL:Math.round(big.left-c.left),btnL:Math.round(btn.left-a.left),btnR:Math.round(a.right-btn.right),btnH:btn.height,
                   padB:Math.round(c.bottom-[...document.querySelectorAll('.card > *')].pop().getBoundingClientRect().bottom)}}""")
                ok=abs(m['colL']-m['colR'])<=1 and m['cardL']==0 and m['cardR']==0 and m['padL']==m['padR']==m['padT']==m['bigL']==m['padB']==(33 if w>720 else 21) and m['btnL']==0 and m['btnR']==0 and m['btnH']==56
                log(f'{slug} {w}: even: column centred, card padding 20 (32 on desktop) + hairline on all four sides, button full width and 56 high',ok,m); await ctx.close()
            # reduced motion and a blocked engine
            ctx,pg,errs,_=await fresh(b,slug,block=('**/engine.js',)); st=norm(await pg.inner_text('[data-o=big]'))
            log(f'{slug}: if engine.js doesn\'t load, the built-in answer stays and nothing errors',st==first['big'] and not errs,[st,errs[:2]]); await ctx.close()

        # ---- the index, About, home, sitemap, robots ----
        ctx,pg,errs,st=await fresh(b,'guides'); rows=await pg.evaluate("()=>[...document.querySelectorAll('.gl.idx a')].map(a=>[a.getAttribute('href'),a.firstChild.textContent.trim(),a.querySelector('span').innerText.trim()])")
        log('guides: index lists all ten, each with its question and a one-line answer',st==200 and [r[0] for r in rows]==slugs and all(r[1].endswith('?') and len(r[2])>10 for r in rows) and not errs,rows[:2])
        ld=json.loads(await pg.locator('script[type="application/ld+json"]').inner_text()); log('guides: JSON-LD list parses and has the ten URLs',[i['url'] for i in ld['mainEntity']['itemListElement']]==[SITE+s for s in slugs])
        log('guides: canonical, no tap target under 44 px, no dash',await pg.get_attribute('link[rel=canonical]','href')==SITE+'guides' and not await pg.evaluate(SMALL) and '—' not in await pg.inner_text('main'),await pg.evaluate(SMALL))
        await pg.tap('.gl.idx a >> nth=0'); await pg.wait_for_selector('.calc'); log('guides: a row opens its page',(await pg.evaluate('location.pathname'))=='/'+slugs[0] and not errs,errs[:2]); await ctx.close()
        for w,h,mob in [(320,568,True),(390,844,True),(1440,900,False)]:
            for scheme in ['light','dark']:
                for pgn in ['guides','about','privacy']:
                    ctx,pg,errs,_=await fresh(b,pgn,w=w,h=h,scheme=scheme,mobile=mob); ov=await pg.evaluate(OV); c=await pg.evaluate(LUM); small=await pg.evaluate(SMALL)
                    ok=ov[0]<=ov[1] and not ov[2] and c['body']==('rgb(255, 255, 255)' if scheme=='light' else 'rgb(0, 0, 0)') and not {k:v for k,v in c.items() if k!='body' and v<4.5} and not small and not errs
                    log(f'{pgn} {w} {scheme}: no sideways scroll, right colours, contrast, 44 px targets',ok,[ov,c,small,errs[:2]] if not ok else ''); await ctx.close()
        ctx,pg,errs,st=await fresh(b,'about'); al=await pg.evaluate("()=>[...document.querySelectorAll('main a, article a')].filter(a=>a.innerText.trim()=='All guides').map(a=>a.getAttribute('href'))")
        foot=await pg.evaluate("()=>[...document.querySelectorAll('footer a')].map(a=>[a.innerText,a.getAttribute('href')])")
        log('about: links to all guides; footer has Guides',al==['guides'] and ['Guides','guides'] in foot and not errs,[al[:2],foot])
        log('about: its WebApplication data block still parses',json.loads(await pg.locator('script[type="application/ld+json"]').inner_text())['@type']=='WebApplication')
        await pg.tap('footer a[href=guides]'); await pg.wait_for_selector('.gl.idx'); log('about: footer Guides opens /guides',(await pg.evaluate('location.pathname'))=='/guides'); await ctx.close()
        ctx,pg,errs,st=await fresh(b,''); hf=await pg.evaluate("()=>[...document.querySelectorAll('footer.foot a')].map(a=>[a.innerText,a.getAttribute('href'),Math.round(a.getBoundingClientRect().height),Math.round(a.getBoundingClientRect().width)])")
        log('home: footer has Guides, 44 px, next to About and Privacy',[x[:2] for x in hf]==[['Guides','guides'],['About','about'],['Privacy','privacy']] and all(x[2]>=44 and x[3]>=44 for x in hf) and not errs,[hf,errs[:2]])
        await pg.tap('footer.foot a[href=guides]'); await pg.wait_for_selector('.gl.idx'); log('home: footer Guides opens /guides',(await pg.evaluate('location.pathname'))=='/guides'); await ctx.close()
        ctx,pg,errs,_=await fresh(b,'',w=320,h=568); ov=await pg.evaluate(OV); log('home 320: footer with the new link doesn\'t scroll sideways',ov[0]<=ov[1] and not ov[2],ov); await ctx.close()
        # files
        sm=ET.parse('site/sitemap.xml').getroot(); ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'; locs=[u.find(ns+'loc').text for u in sm.findall(ns+'url')]
        want=[SITE,SITE+'guides',SITE+'about',SITE+'privacy']+[SITE+s for s in slugs]
        log('sitemap.xml parses and lists home, guides, about, privacy and the ten pages, once each',sorted(locs)==sorted(want) and all(re.fullmatch(r'\d{4}-\d\d-\d\d',u.find(ns+'lastmod').text) for u in sm.findall(ns+'url')),len(locs))
        dead=[]; ctx=await b.new_context()
        for l in locs:
            r=await ctx.request.get(l.replace(SITE,U))
            if r.status!=200: dead.append(l)
        log('sitemap: every URL is served',not dead,dead); await ctx.close()
        rb=open('site/robots.txt').read(); log('robots.txt allows everything and points to the sitemap','User-agent: *' in rb and 'Allow: /' in rb and 'Disallow' not in rb and 'Sitemap: '+SITE+'sitemap.xml' in rb,rb)
        html=open('site/index.html').read()
        log('build: impact-site-verification tag and AFF are still there','<meta name="impact-site-verification" value="44a0832b-93ba-4379-b2a0-530627c39acf">' in html and "const AFF={instacart:'',amazonTag:'batchrecipes-20'}" in html)
        log('build: home page still has 6 script tags and 4 hashes',html.count('<script')==6 and len(re.findall(r"'sha256-",html))==4,html.count('<script'))
        allp=''.join(open(f'site/{s}.html').read() for s in slugs+['guides'])
        log('build: guide pages load nothing from another host but the analytics script the other pages use',set(re.findall(r'(?:src|href)="(https?://[^"/]+)',re.sub(r'<link rel="canonical"[^>]*>','',allp)))=={'https://cloud.umami.is'},set(re.findall(r'(?:src|href)="(https?://[^"/]+)',allp)))
        await b.close()
    bad=[r for r in R if r[1]=='FAIL']; print(f'\n{len(R)-len(bad)} of {len(R)} ok')
asyncio.run(main())
