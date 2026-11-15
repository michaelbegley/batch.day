# Stress test for the reading flow. The AI reader and the on-device reader are mocked; the live reader is never called.
import asyncio, json
from playwright.async_api import async_playwright
U='http://localhost:8765/'
SHOTS=[f'/home/claude/test-shots/chicken{i}.jpg' for i in (1,2,3,4)]
TXT=open('/tmp/sample.txt').read() if __import__('os').path.exists('/tmp/sample.txt') else 'Chicken rice\nServes 4\n1 lb chicken thighs\n1 cup rice\n1. Cook the rice.\n2. Sear the chicken.'
R=[]
def log(group,name,ok,note=''):
    R.append((group,name,'ok' if ok else 'FAIL',note)); open('breakit/results.json','w').write(json.dumps(R,indent=1)); print('ok  ' if ok else 'FAIL',group,'|',name,'|',note)
VIEW="['v-add','v-sheet'].find(i=>!document.getElementById(i).classList.contains('hidden'))"
STATE="document.getElementById('reading').classList.contains('hidden')?'pick':document.getElementById('reading').dataset.state"
EV="window.__ev.filter(e=>e.name!=='Visit').map(e=>{const d=Object.assign({},e.data);delete d.src;const v=Object.values(d);return e.name+(v.length?':'+v.join('/'):'')})"  # Visit and src (added 14 Nov) are checked separately
TESS="window.Tesseract={createWorker:async(l,n,o)=>({recognize:async()=>{await new Promise(r=>setTimeout(r,window.__td||80));o.logger({status:'recognizing text',progress:1});return{data:{text:window.__tt}}},terminate:async()=>{window.__term=1}})};"
async def fresh(b,reader='ok',delay=0,tess=True,text=None,clock=False):
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await ctx.new_page(); errs=[]; calls=[]
    pg.on('pageerror',lambda e:errs.append('pageerror: '+str(e)[:160]))
    pg.on('console',lambda m: errs.append('console: '+m.text[:160]) if m.type=='error' and 'Failed to load resource' not in m.text and 'ERR_' not in m.text else None)
    pg.on('dialog',lambda d:(errs.append('DIALOG: '+d.message),asyncio.ensure_future(d.dismiss())))
    init="document.addEventListener('securitypolicyviolation',e=>console.error('CSP '+e.violatedDirective+' '+e.blockedURI));window.__ev=[];window.va=function(a,b){window.__ev.push(b)};"+f"window.__tt={json.dumps(TXT)};"
    if tess: init+=TESS
    if clock: init+="const _n=Date.now;let off=0;window.__skip=(ms)=>off+=ms;Date.now=()=>_n()+off;const _st=setTimeout;window.setTimeout=(f,ms,...a)=>_st(f,ms>=60000?window.__to||ms:ms,...a);"
    await pg.add_init_script(init)
    async def read(route):
        calls.append(len(json.loads(route.request.post_data)['images']))
        if delay: await asyncio.sleep(delay)
        H={'Access-Control-Allow-Origin':'*'}
        try:
            if reader=='ok': await route.fulfill(status=200,content_type='application/json',headers=H,body=json.dumps({'text':text if text is not None else TXT,'model':'mock'}))
            elif reader=='none': await route.fulfill(status=422,content_type='application/json',headers=H,body='{"error":"No recipe found"}')
            elif reader=='limit': await route.fulfill(status=429,content_type='application/json',headers=H,body='{"error":"Too many reads"}')
            elif reader=='bad': await route.fulfill(status=502,content_type='text/html',headers=H,body='<html>Bad gateway</html>')
            elif reader=='junk': await route.fulfill(status=200,content_type='application/json',headers=H,body='{"text":12}')
            else: await route.abort()
        except Exception: pass
    await pg.route('**/*.hf.space/**',read)
    await pg.route('**/cdn.jsdelivr.net/**',lambda r:r.abort())
    await pg.route('**/pagead2.googlesyndication.com/**',lambda r:r.abort())
    await pg.route('**/*.umami.is/**',lambda r:r.abort())
    await pg.goto(U); await pg.wait_for_timeout(400)
    return ctx,pg,errs,calls
async def sheet(pg,t=6000):
    try: await pg.wait_for_selector('#v-sheet:not(.hidden)',timeout=t); return True
    except Exception: return False
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # AI ok
        ctx,pg,errs,calls=await fresh(b); await pg.set_input_files('#file',SHOTS); ok=await sheet(pg)
        ev=await pg.evaluate(EV); alerts=await pg.inner_text('#alerts')
        log('read','4 screenshots, AI answers',ok and calls==[4] and 'AI read:4/ok' in ev and 'Plan:batch/screenshots' in ev and not alerts.strip() and not errs,f'calls={calls} events={ev} errs={errs[:2]}'); 
        saved=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).length"); log('read','saved once',saved==1,f'{saved}')
        await pg.reload(); await pg.wait_for_timeout(600); log('read','reload reopens the recipe',await pg.evaluate(VIEW)=='v-sheet',''); await ctx.close()
        # each failure falls back to the device
        for reader,why in [('limit','limit'),('bad','error'),('junk','error'),('down','error')]:
            ctx,pg,errs,calls=await fresh(b,reader=reader); await pg.set_input_files('#file',SHOTS[:2]); ok=await sheet(pg)
            ev=await pg.evaluate(EV); al=(await pg.inner_text('#alerts')).replace('\n',' ')
            log('fallback',f'reader {reader} -> device',ok and f'Device read:{why}/yes' in ev and 'Read on this device' in al and 'Try AI again' in al and not errs,f'events={ev} alert={al!r} errs={errs[:2]}'); await ctx.close()
        # 422 (14 Nov): the AI saw no recipe, so this device reads it; no "Try AI again"
        ctx,pg,errs,calls=await fresh(b,reader='none'); await pg.set_input_files('#file',SHOTS[:1]); ok=await sheet(pg)
        ev=await pg.evaluate(EV); al=(await pg.inner_text('#alerts')).replace('\n',' ')
        log('fallback','422 -> device reads it',ok and 'AI read:1/none' in ev and 'Device read:none/yes' in ev and 'Read on this device' in al and 'Try AI again' not in al and not errs,f'events={ev} alert={al!r}'); await ctx.close()
        # 422 and the device finds nothing either: clear message
        ctx,pg,errs,calls=await fresh(b,reader='none'); await pg.evaluate("window.__tt=''"); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(2500)
        st=await pg.evaluate(STATE); log('fail','422 + device finds nothing: No recipe found',st=='fail' and await pg.inner_text('#rdTitle')=='No recipe found' and not errs,f'state={st} events={await pg.evaluate(EV)}')
        await pg.click('#rdPaste'); await pg.wait_for_timeout(200); log('fail','Paste text from the fail state',await pg.is_visible('#paste') and await pg.evaluate(STATE)=='pick',''); await ctx.close()
        # AI returns text with no recipe in it, device finds nothing either
        ctx,pg,errs,calls=await fresh(b,text='hello there\nnothing to cook'); await pg.evaluate("window.__tt=''"); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(5000)
        log('fail','AI text with no ingredients',await pg.evaluate(STATE)=='fail' and await pg.inner_text('#rdTitle')=='No recipe found' and not errs,await pg.inner_text('#rdTitle')); await ctx.close()
        # reader down and no on-device reader
        ctx,pg,errs,calls=await fresh(b,reader='down',tess=False); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(1800)
        log('fail','reader down + CDN blocked',await pg.evaluate(STATE)=='fail' and await pg.inner_text('#rdTitle')=="Couldn't read those" and not errs,f"{await pg.inner_text('#status')} events={await pg.evaluate(EV)} errs={errs[:2]}")
        await pg.click('#rdAgain') if False else None; await ctx.close()
        # offline: never calls the reader
        ctx,pg,errs,calls=await fresh(b); await ctx.set_offline(True); await pg.set_input_files('#file',SHOTS[:2]); ok=await sheet(pg)
        ev=await pg.evaluate(EV); al=(await pg.inner_text('#alerts')).replace('\n',' ')
        log('fallback','offline -> device, reader not called',ok and calls==[] and 'Device read:offline/yes' in ev and "You're offline" in al,f'calls={calls} events={ev} alert={al!r}'); await ctx.close()
        # cancel mid-read
        ctx,pg,errs,calls=await fresh(b,delay=3); await pg.set_input_files('#file',SHOTS); await pg.wait_for_timeout(900); await pg.click('#rdCancel'); await pg.wait_for_timeout(3600)
        log('cancel','Cancel during AI read',await pg.evaluate(VIEW)=='v-add' and await pg.evaluate(STATE)=='pick' and await pg.is_visible('#choose') and 'AI read:4/cancel' in await pg.evaluate(EV) and 'Plan' not in str(await pg.evaluate(EV)) and not errs,f'events={await pg.evaluate(EV)} errs={errs[:2]}')
        # then read again straight away
        await pg.set_input_files('#file',SHOTS[:1]); ok=await sheet(pg); log('cancel','read again after Cancel',ok and not errs,''); await ctx.close()
        # slow: "Read on this device instead" shows after 40 s and works
        ctx,pg,errs,calls=await fresh(b,delay=8,clock=True); await pg.set_input_files('#file',SHOTS[:2]); await pg.wait_for_timeout(800)
        hid=await pg.is_hidden('#rdDevice'); await pg.evaluate('__skip(41000)'); await pg.wait_for_timeout(500)
        vis=await pg.is_visible('#rdDevice'); stt=await pg.inner_text('#status'); await pg.click('#rdDevice'); ok=await sheet(pg)
        ev=await pg.evaluate(EV); log('slow','after 40 s offer the device reader',hid and vis and ok and 'Device read:choice/yes' in ev and not errs,f'status={stt!r} events={ev} errs={errs[:2]}')
        await pg.wait_for_timeout(8000); log('slow','late AI answer is ignored',await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')).length")==1 and not errs,''); await ctx.close()
        # timeout
        ctx,pg,errs,calls=await fresh(b,delay=6,clock=True); await pg.evaluate('window.__to=1500'); await pg.set_input_files('#file',SHOTS[:1]); ok=await sheet(pg)
        ev=await pg.evaluate(EV); log('fallback','timeout -> device',ok and 'Device read:timeout/yes' in ev and not errs,f'events={ev} errs={errs[:2]}'); await ctx.close()
        # 9 files: first 6 only, and non-images ignored
        ctx,pg,errs,calls=await fresh(b); await pg.set_input_files('#file',SHOTS+SHOTS+SHOTS[:1]); ok=await sheet(pg)
        al=await pg.inner_text('#alerts'); log('input','9 screenshots',ok and calls==[6] and 'first 6' in al and not errs,f'calls={calls} alert={al!r}'); await ctx.close()
        ctx,pg,errs,calls=await fresh(b); await pg.set_input_files('#file',[{'name':'a.txt','mimeType':'text/plain','buffer':b'hi'}]); await pg.wait_for_timeout(400)
        log('input','a text file',calls==[] and await pg.evaluate(STATE)=='pick' and not errs,repr(await pg.inner_text('#toast')))
        await pg.set_input_files('#file',[{'name':'a.png','mimeType':'image/png','buffer':b'not a png'}]); await pg.wait_for_timeout(1500)
        log('input','a broken image',await pg.evaluate(VIEW)=='v-add' and not errs,f"state={await pg.evaluate(STATE)} title={await pg.inner_text('#rdTitle')!r} errs={errs[:2]}"); await ctx.close()
        # two recipes
        ctx,pg,errs,calls=await fresh(b,text=TXT+'\n\n---\n\nGarlic butter noodles\nServes 2\n8 oz spaghetti\n3 tbsp butter\n1. Boil the pasta.'); await pg.set_input_files('#file',SHOTS[:2]); ok=await sheet(pg)
        n=await pg.locator('#which .chip').count(); await pg.click('#which .chip >> nth=1'); await pg.wait_for_timeout(400)
        log('input','two recipes: switch',ok and n==2 and await pg.inner_text('#sTitle')=='Garlic butter noodles' and await pg.input_value('#yield')=='2' and not errs,f"chips={n} title={await pg.inner_text('#sTitle')}"); await ctx.close()
        # Try AI again from a device read
        ctx,pg,errs,calls=await fresh(b,reader='limit'); await pg.set_input_files('#file',SHOTS[:2]); await sheet(pg)
        await pg.click('#aiGo'); await pg.wait_for_timeout(1500)
        log('retry','Try AI again, still limited',await pg.evaluate(VIEW)=='v-sheet' and 'limit' in await pg.inner_text('#toast') and 'Read with AI' in await pg.evaluate(EV) and not errs,f"toast={await pg.inner_text('#toast')!r}")
        await pg.unroute('**/*.hf.space/**')
        async def good(route): await route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'text':TXT}))
        await pg.route('**/*.hf.space/**',good); await pg.wait_for_timeout(2600); await pg.click('#aiGo'); await pg.wait_for_timeout(1500)
        ev=await pg.evaluate(EV); log('retry','Try AI again, works',await pg.evaluate(VIEW)=='v-sheet' and not (await pg.inner_text('#alerts')).strip() and ev.count('Plan:batch/screenshots')==1 and not errs,f'events={ev}')
        await pg.go_back(); await pg.wait_for_timeout(300); log('retry','Back after retry goes home',await pg.evaluate(VIEW)=='v-add',''); await ctx.close()
        # double pick while reading
        ctx,pg,errs,calls=await fresh(b,delay=1); await pg.set_input_files('#file',SHOTS[:1]); await pg.wait_for_timeout(300); await pg.evaluate("document.getElementById('file').value=''"); await pg.set_input_files('#file',SHOTS[:2]); ok=await sheet(pg); await pg.wait_for_timeout(1500)
        ev=await pg.evaluate(EV); log('repeat','second pick while the first is reading',ok and str(ev).count('Plan')==1 and not errs,f'calls={calls} events={ev}'); await ctx.close()
        # privacy copy
        ctx,pg,errs,calls=await fresh(b); body=await pg.inner_text('body'); pv=await (await ctx.new_page()).goto(U+'privacy.html'); t=await pv.text()
        log('copy','no "never leave your phone"; says screenshots are sent','never leave' not in body and 'Sent to an AI reader' in body and 'Hugging Face Inference Providers' in t and '—' not in body,''); await ctx.close()
        await b.close()
        bad=[r for r in R if r[2]=='FAIL']; print(len(R),'checks,',len(bad),'failed')
asyncio.run(main())
