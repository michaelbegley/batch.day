# Video to recipe (15 Nov 2026): Add a video, YouTube links, link pastes, and amounts given as a word.
# Run from the build folder after build.py: python3 breakit13.py  (starts its own server; nothing live is called).
# The reader's /watch and /link are mocked (route **/*.hf.space/**). Umami, AdSense, jsDelivr and every other outside host are blocked.
# Test videos are made here with ffmpeg (test pattern, a tone, burned-in text). No one else's video is used.
import asyncio, json, os, sys, re, base64, struct, io, threading, http.server, subprocess, tempfile, shutil
from playwright.async_api import async_playwright
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.join(HERE,'site')
PORT=8765
SHOT='/home/claude/test-shots/chicken1.jpg'
BLOCK=['**/cloud.umami.is/**','**/gateway.umami.is/**','**/pagead2.googlesyndication.com/**','**/*.doubleclick.net/**','**/cdn.jsdelivr.net/**','**/*amazon.com/**','**/*instacart.com/**','**/batch.recipes/**','**/_vercel/**',
       '**/*youtube.com/**','**/youtu.be/**','**/*tiktok.com/**','**/*instagram.com/**','**/*facebook.com/**','**/fb.watch/**','**/*pinterest.com/**','**/pin.it/**','**/*googleapis.com/**','**/*seriouseats.com/**','**/*example.com/**']
VID='Garlic noodles\nServes 2\n8 oz noodles\n3 cloves garlic\nsoy sauce (a splash)\na drizzle of honey\n1. Boil the noodles.\n2. Fry the garlic and toss.'
MOST='Quick noodles\nServes 2\n2 cloves garlic\nsoy sauce (a splash)\nhoney (a drizzle)\nbutter (a knob)\n1. Toss it all.'
ONE='Rice bowl\nServes 2\n1 cup rice\n2 eggs\nsoy sauce (a splash)\n1. Cook the rice.'
FULL='Chicken rice\nServes 4\n1 lb chicken thighs\n1 cup rice\n1. Cook the rice.\n2. Sear the chicken.'
YT='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
R=[]; ERRS=[]
def log(n,ok,note=''):
    R.append([n,'ok' if ok else 'FAIL',str(note)[:600]]); print(('ok   ' if ok else 'FAIL ')+n+('' if ok else '  '+str(note)[:600]),flush=True)

def path_file(p):
    p=p.split('?')[0].split('#')[0]; f=os.path.join(ROOT,p.lstrip('/'))
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

# ---------- test videos (WebM: the test browser has no H.264)
TMP=tempfile.mkdtemp(prefix='bd13-'); FONT='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
def ff(out,*args):
    p=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args,os.path.join(TMP,out)],capture_output=True,text=True)
    if p.returncode: print('ffmpeg failed for',out,p.stderr[-400:],flush=True)
    return os.path.join(TMP,out)
VP=['-c:v','libvpx','-deadline','realtime','-cpu-used','8','-b:v','600k']; OP=['-c:a','libopus','-b:a','32k']
def make_videos():
    def card(col,txt,d,s='640x360'): return f"color=c={col}:s={s}:d={d}:r=10,drawtext=fontfile={FONT}:text='{txt}':fontcolor=black:fontsize=56:x=(w-text_w)/2:y=(h-text_h)/2"
    V={}
    # 12 s: a white card "2 cups rice", a test pattern, a blue card "Serves 4"; a 440 Hz tone all the way
    V['good']=ff('good.webm','-f','lavfi','-i',card('white','2 cups rice',4),'-f','lavfi','-i','testsrc=s=640x360:d=4:r=10','-f','lavfi','-i',card('blue','Serves 4',4),'-f','lavfi','-i','sine=frequency=440:duration=12',
                 '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]','-map','3:a',*VP,*OP)
    V['nosound']=ff('nosound.webm','-f','lavfi','-i',card('white','2 cups rice',3),'-f','lavfi','-i','testsrc=s=640x360:d=3:r=10','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]',*VP)
    V['silent']=ff('silent.webm','-f','lavfi','-i','testsrc=s=320x180:d=4:r=10','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-shortest','-t','4',*VP,*OP)
    # 40 s where every moment looks different: a red card, 38 s of turning colours, a green card
    V['busy']=ff('busy.webm','-f','lavfi','-i','color=c=red:s=320x180:d=1:r=10','-f','lavfi','-i','testsrc2=s=320x180:d=38:r=10,hue=h=t*40','-f','lavfi','-i','color=c=0x00ff00:s=320x180:d=1:r=10',
                 '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]',*VP)
    V['static']=ff('static.webm','-f','lavfi','-i',card('white','1 lb chicken',20),*VP)
    V['big1080']=ff('big1080.webm','-f','lavfi','-i','testsrc2=s=1920x1080:d=2:r=5',*VP)
    V['tall']=ff('tall.webm','-f','lavfi','-i','testsrc2=s=1080x1920:d=2:r=5',*VP)
    V['long200']=ff('long200.webm','-f','lavfi','-i','testsrc=s=160x90:d=200:r=2','-f','lavfi','-i','sine=frequency=300:duration=200',*VP[:-2],'-b:v','40k',*OP)
    V['over10']=ff('over10.webm','-f','lavfi','-i','testsrc=s=64x36:d=605:r=1',*VP[:-2],'-b:v','10k')
    V['soundonly']=ff('soundonly.webm','-f','lavfi','-i','sine=frequency=440:duration=3',*OP)
    V['pdf']=os.path.join(TMP,'recipe.mp4'); open(V['pdf'],'wb').write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF\n'*40)   # a PDF with a video name
    V['realpdf']=os.path.join(TMP,'recipe.pdf'); shutil.copy(V['pdf'],V['realpdf'])
    V['zero']=os.path.join(TMP,'empty.mp4'); open(V['zero'],'wb').close()
    V['huge']=os.path.join(TMP,'huge.webm')
    with open(V['huge'],'wb') as f: f.write(open(V['good'],'rb').read()[:4096]); f.truncate(2*1024**3)   # 2 GB on paper, no disk used
    return V

INIT="""try{localStorage.setItem("bd-video","1")}catch(e){}
window.__ev=[];window.va=function(a,b){if(a==='event')window.__ev.push({name:b.name,data:b.data||{}})};
document.addEventListener('securitypolicyviolation',function(e){console.error('CSP '+e.violatedDirective+' '+e.blockedURI)});"""
CLOCK="const _st=setTimeout;window.setTimeout=(f,ms,...a)=>_st(f,ms>=60000?(window.__to||ms):ms,...a);"
STATE="document.getElementById('reading').classList.contains('hidden')?'pick':document.getElementById('reading').dataset.state"
VIEW="['v-add','v-sheet'].find(i=>!document.getElementById(i).classList.contains('hidden'))"
FAILTXT="document.getElementById('rdTitle').innerText+' | '+document.getElementById('status').innerText"
BTNS="[...document.querySelectorAll('.failed button')].filter(b=>b.offsetParent).map(b=>b.innerText)"
CORS={'Access-Control-Allow-Origin':'*'}
class Mock:
    """what the mocked reader does next, and everything it was sent"""
    def __init__(s): s.watch='ok'; s.link='ok'; s.text=VID; s.used='mix'; s.delay=0; s.calls=[]; s.creator='Test Kitchen'; s.url=YT; s.other=[]
    def reply(s,mode,path):
        J=lambda st,b: (st,json.dumps(b))
        if mode=='ok':
            b={'text':s.text,'model':'mock','used':s.used}
            if path=='link': b.update(creator=s.creator,url=s.url)
            return J(200,b)
        if mode=='none': return J(422,{'error':'No recipe found in that video.','why':'none'})
        if mode=='limit': return J(429,{'error':"That's a lot of videos. Try again in a bit, or add screenshots.",'why':'limit'})
        if mode=='busy': return J(429,{'error':'The video reader is busy today. Try again tomorrow, or add screenshots.','why':'busy'})
        if mode=='off': return J(503,{'error':"YouTube links aren't on yet. Add the video or screenshots.",'why':'off'})
        if mode=='private': return J(404,{'error':'That video is private. Add screenshots or paste the recipe.','why':'private'})
        if mode=='toolong': return J(413,{'error':'That video is too long to read from a link.','why':'toolong'})
        if mode=='junk': return J(200,{'text':12})
        if mode=='html': return (502,'<html>Bad gateway</html>')
        return J(502,{'error':"The video reader couldn't read it right now. Add screenshots instead."})
async def new(b,w=390,h=844,mob=True,scheme='light',clock=False,reduced=False):
    ctx=await b.new_context(viewport={'width':w,'height':h},has_touch=mob,is_mobile=mob,color_scheme=scheme,reduced_motion='reduce' if reduced else 'no-preference')
    m=Mock(); ctx._m=m
    await ctx.add_init_script(INIT+(CLOCK if clock else ''))
    for pat in BLOCK: await ctx.route(pat,lambda r:r.abort())
    async def reader(route):
        rq=route.request; path=rq.url.rstrip('/').rsplit('/',1)[1]
        if rq.method=='OPTIONS': await route.fulfill(status=204,headers={**CORS,'Access-Control-Allow-Headers':'Content-Type','Access-Control-Allow-Methods':'POST'}); return
        try: body=json.loads(rq.post_data or '{}')
        except Exception: body={'_raw':rq.post_data}
        m.calls.append([path,body])
        mode=m.watch if path=='watch' else m.link if path=='link' else 'ok'
        if mode=='hang': await asyncio.sleep(30)
        if m.delay: await asyncio.sleep(m.delay)
        try:
            if mode=='abort': await route.abort(); return
            st,bd=m.reply(mode,path); await route.fulfill(status=st,headers={**CORS,'Content-Type':'application/json' if bd.startswith('{') else 'text/html'},body=bd)
        except Exception: pass
    await ctx.route('**/*.hf.space/**',reader)
    return ctx,m
async def tab(ctx,url=None):
    pg=await ctx.new_page(); pg._req=[]
    pg.on('pageerror',lambda e: ERRS.append('PAGEERROR '+str(e)[:200]))
    pg.on('console',lambda msg: ERRS.append('CONSOLE '+msg.text[:200]) if msg.type=='error' and 'Failed to load resource' not in msg.text and 'net::ERR' not in msg.text else None)
    pg.on('dialog',lambda d:(ERRS.append('DIALOG '+d.message[:100]),asyncio.ensure_future(d.dismiss())))
    pg.on('request',lambda r: pg._req.append(r.url))
    if url is not None: await pg.goto(url); await pg.wait_for_timeout(350)
    return pg
async def until(pg,js,ms=20000,step=100):
    """polled: the page's CSP does not allow wait_for_function"""
    for _ in range(ms//step):
        try:
            if await pg.evaluate(js): return True
        except Exception: pass
        await pg.wait_for_timeout(step)
    return False
async def ev(pg): return await pg.evaluate("window.__ev.filter(e=>e.name!=='Visit')")
def of(e,n): return [x['data'] for x in e if x['name']==n]
async def pick_video(pg,path):
    if not await pg.is_visible('#vchoose'): await pg.click('#videoToggle'); await pg.wait_for_timeout(120)
    await pg.set_input_files('#vfile',path)
async def settled(pg,ms=30000): return await until(pg,f"({VIEW})==='v-sheet'||({STATE})==='fail'",ms)
async def paste_link(pg,text):
    if not await pg.is_visible('#paste'): await pg.click('#pasteToggle')
    await pg.fill('#paste',text); await pg.wait_for_timeout(550); await pg.click('#usePaste'); await pg.wait_for_timeout(350)
def wav_info(b64s):
    b=base64.b64decode(b64s); assert b[:4]==b'RIFF' and b[8:12]==b'WAVE' and b[12:16]==b'fmt ' and b[36:40]==b'data'
    fmt,ch,rate,brate,align,bits=struct.unpack('<HHIIHH',b[20:36]); n=struct.unpack('<I',b[40:44])[0]
    smp=struct.unpack('<%dh'%min(n//2,16000*3),b[44:44+min(n//2,16000*3)*2])
    return {'fmt':fmt,'ch':ch,'rate':rate,'bits':bits,'secs':n/brate,'bytes':len(b),'peak':max(abs(x) for x in smp) if smp else 0,'data_ok':n==len(b)-44}
def img_of(durl):
    assert durl.startswith('data:image/jpeg;base64,'); raw=base64.b64decode(durl.split(',',1)[1]); im=Image.open(io.BytesIO(raw)).convert('RGB'); return im,len(raw)
def mean(im):
    s=im.resize((8,8)); px=list(s.getdata()); return tuple(sum(p[i] for p in px)//len(px) for i in range(3))

async def main():
    global PORT
    try: srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H)
    except OSError: srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),H); PORT=srv.server_address[1]   # the usual port is taken: any free one
    threading.Thread(target=srv.serve_forever,daemon=True).start(); U=f'http://localhost:{PORT}/'
    if not shutil.which('ffmpeg'): log('ffmpeg is here to make the test videos',False); sys.exit(1)
    V=make_videos(); log('test videos made with ffmpeg',all(os.path.exists(p) for p in V.values()) and os.path.getsize(V['good'])>2000,{k:os.path.getsize(p) for k,p in V.items() if os.path.exists(p)})
    async with async_playwright() as p:
        b=await p.chromium.launch()

        # ================= 1. the home screen stays calm; Add a video is a quiet second way in
        for scheme in ('light','dark'):
            for w,h,mob in ((390,844,True),(1440,900,False)):
                tag=f'{scheme} {w}'; ctx,m=await new(b,w,h,mob,scheme); pg=await tab(ctx,U)
                st=await pg.evaluate("""()=>{const r=(s)=>{const e=document.querySelector(s),b=e.getBoundingClientRect();return {w:b.width,h:b.height,top:b.top,vis:!!e.offsetParent,color:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor,fw:getComputedStyle(e).fontWeight}};
                  return {vt:r('#videoToggle'),pt:r('#pasteToggle'),ch:r('#choose'),btns:[...document.querySelectorAll('#dropcard .btn')].filter(e=>e.offsetParent).length,vbox:!document.getElementById('videobox').classList.contains('hidden'),
                  over:document.documentElement.scrollWidth>innerWidth,txt:document.getElementById('videoToggle').innerText,fold:document.getElementById('videoToggle').getBoundingClientRect().bottom<innerHeight}}""")
                log(f'home {tag}: Add a video is a link beside Paste text, on the same line',st['vt']['vis'] and st['txt']=='Add a video' and abs(st['vt']['top']-st['pt']['top'])<1,st)
                log(f'home {tag}: Add a video is 44 px tall or more',st['vt']['h']>=44 and st['vt']['w']>=44,st['vt'])
                log(f'home {tag}: one main button on the first screen; the video box is closed',st['btns']==1 and not st['vbox'],st['btns'])
                log(f'home {tag}: Add a video looks like the Paste text link, not a second button',st['vt']['color']==st['pt']['color'] and st['vt']['bg']==st['pt']['bg'] and st['vt']['color']!=st['ch']['color'],(st['vt'],st['ch']))
                log(f'home {tag}: nothing wider than the screen',not st['over'])
                if mob: log(f'home {tag}: Add a video is on the first screen without scrolling',st['fold'],st['vt'])
                await pg.screenshot(path=os.path.join(HERE,'breakit',f'v13-home-{scheme}-{w}.png'))
                await pg.click('#videoToggle'); await pg.wait_for_timeout(250)
                st=await pg.evaluate("""()=>{const v=(s)=>{const e=document.querySelector(s);return !!e.offsetParent},b=document.getElementById('vchoose').getBoundingClientRect(),c=document.getElementById('choose');
                  const hint=[...document.querySelectorAll('#videobox .hint')];const cs=getComputedStyle(hint[1]),card=getComputedStyle(document.getElementById('dropcard'));
                  return {box:v('#videobox'),pick:v('#pick'),paste:v('#pastebox'),h:b.height,w:b.width,vt:document.getElementById('videoToggle').innerText,pt:document.getElementById('pasteToggle').innerText,hints:hint.map(e=>e.innerText),
                  focus:document.activeElement.id,over:document.documentElement.scrollWidth>innerWidth,ink:cs.color,cardbg:card.backgroundColor,btns:[...document.querySelectorAll('#dropcard .btn')].filter(e=>e.offsetParent).length,accept:document.getElementById('vfile').accept}}""")
                log(f'video box {tag}: opens in the card with one button, and the links change',st['box'] and not st['pick'] and not st['paste'] and st['btns']==1 and st['vt']=='Use screenshots' and st['pt']=='Paste text',st)
                log(f'video box {tag}: says how to get the video and what is sent',st['hints']==['Save or screen record the video, then pick it here.',"A few frames and the sound go to an AI reader. We don't keep them. The video stays on this device."],st['hints'])
                log(f'video box {tag}: button is 44 px or more, focus is on it, the picker takes video only',st['h']>=44 and st['focus']=='vchoose' and st['accept']=='video/*',st)
                log(f'video box {tag}: nothing wider than the screen',not st['over'])
                await pg.screenshot(path=os.path.join(HERE,'breakit',f'v13-videobox-{scheme}-{w}.png'))
                await pg.click('#pasteToggle'); await pg.wait_for_timeout(150)
                s2=await pg.evaluate("({box:!!document.getElementById('videobox').offsetParent,paste:!!document.getElementById('pastebox').offsetParent,vt:document.getElementById('videoToggle').innerText,pt:document.getElementById('pasteToggle').innerText})")
                log(f'video box {tag}: Paste text swaps it for the paste box',not s2['box'] and s2['paste'] and s2['vt']=='Add a video' and s2['pt']=='Use screenshots',s2)
                await pg.click('#videoToggle'); await pg.wait_for_timeout(150); await pg.click('#videoToggle'); await pg.wait_for_timeout(150)
                s3=await pg.evaluate("({box:!!document.getElementById('videobox').offsetParent,paste:!!document.getElementById('pastebox').offsetParent,pick:!!document.getElementById('pick').offsetParent})")
                log(f'video box {tag}: Use screenshots goes back to the first screen',s3=={'box':False,'paste':False,'pick':True},s3)
                await ctx.close()

        # keyboard: Tab reaches it, Enter opens it, Enter on the button opens the file picker
        ctx,m=await new(b,1280,900,False); pg=await tab(ctx,U)
        for _ in range(40):
            await pg.keyboard.press('Tab')
            if await pg.evaluate("document.activeElement.id")=='videoToggle': break
        ring=await pg.evaluate("(()=>{const c=getComputedStyle(document.activeElement);return c.outlineStyle+' '+c.outlineWidth+' '+c.boxShadow})()")
        log('keyboard: Tab reaches Add a video, with a focus ring',await pg.evaluate("document.activeElement.id")=='videoToggle' and ('none 0px none'!=ring),ring)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        log('keyboard: Enter opens the video box and moves focus to Choose a video',await pg.evaluate("document.activeElement.id")=='vchoose')
        try:
            async with pg.expect_file_chooser(timeout=3000) as fc: await pg.keyboard.press('Enter')
            ch=await fc.value; okc=not ch.is_multiple()
        except Exception as e: okc=False
        log('keyboard: Enter on Choose a video opens the picker, one file only',okc)
        await ctx.close()

        # ================= 2. a real video: frames and sound are pulled out on the device
        ctx,m=await new(b); pg=await tab(ctx,U); t_before=len(pg._req)
        await pick_video(pg,V['good'])
        seen=[]
        for _ in range(300):
            s=await pg.evaluate("document.getElementById('status').innerText"); 
            if s and (not seen or seen[-1]!=s): seen.append(s)
            if await pg.evaluate(VIEW)=='v-sheet': break
            await pg.wait_for_timeout(30)
        log('good video: lands on the recipe page',await pg.evaluate(VIEW)=='v-sheet',await pg.evaluate(FAILTXT))
        log('good video: progress says Getting the video ready, then Listening',seen[:2]==['Getting the video ready','Listening'],seen)
        w=[c for c in m.calls if c[0]=='watch']
        log('good video: one call to /watch, nothing to /read or /link',len(w)==1 and len(m.calls)==1,[c[0] for c in m.calls])
        body=w[0][1] if w else {}
        log('good video: the body is frames, audio and caption only; the caption is empty',sorted(body.keys())==['audio','caption','frames'] and body.get('caption')=='',sorted(body.keys()))
        fr=body.get('frames',[]); ims=[img_of(f) for f in fr] if fr else []
        log('good video: 2 to 8 frames',2<=len(fr)<=8,len(fr))
        log('good video: every frame is a JPEG, 1000 px or less on the long side, under 1.5 MB',bool(ims) and all(max(i.size)<=1000 and n<1_500_000 for i,n in ims),[(i.size,n) for i,n in ims])
        log('good video: frames keep the video shape (640 by 360)',bool(ims) and all(i.size==(640,360) for i,n in ims),[i.size for i,n in ims])
        m0=mean(ims[0][0]) if ims else (0,0,0); m1=mean(ims[-1][0]) if ims else (0,0,0)
        log('good video: the first frame is the opening card (white, with the text)',min(m0)>180,m0)
        log('good video: the last frame is the closing card (blue)',m1[2]>150 and m1[0]<90,m1)
        dark=sum(1 for px in ims[0][0].crop((120,130,520,230)).getdata() if sum(px)<200) if ims else 0
        log('good video: the burned-in text "2 cups rice" is in the first frame (dark letters on the card)',dark>1500,dark)
        sigs=[tuple(i.resize((12,12)).convert('L').getdata()) for i,n in ims]
        log('good video: no two frames next to each other are the same picture',all(sum(abs(a-b2) for a,b2 in zip(sigs[k],sigs[k+1]))/144>3 for k in range(len(sigs)-1)),len(sigs))
        try: wi=wav_info(body.get('audio',''))
        except Exception as e: wi={'err':str(e)}
        log('good video: sound is 16 kHz mono 16-bit WAV in base64',wi.get('fmt')==1 and wi.get('ch')==1 and wi.get('rate')==16000 and wi.get('bits')==16 and wi.get('data_ok'),wi)
        log('good video: the sound is the whole 12 seconds and not silent',11<wi.get('secs',0)<12.6 and wi.get('peak',0)>1000,wi)
        raw=json.dumps(body); vid=open(V['good'],'rb').read()
        log('good video: the video file itself is not in what was sent',base64.b64encode(vid[:300]).decode()[:200] not in raw and 'GkXfo' not in raw and 'webm' not in raw.lower() and 'good' not in raw,len(raw))
        log('good video: what was sent is small (under 1.5 MB for 12 s)',len(raw)<1_500_000,len(raw))
        outside=[u for u in pg._req[t_before:] if not u.startswith(U) and not u.startswith('data:') and not u.startswith('blob:')]
        log('good video: the only outside request is the reader',bool(outside) and all('.hf.space/watch' in u for u in outside),outside[:4])
        log('good video: the hidden player is gone from the page afterwards',await pg.evaluate("document.querySelectorAll('video').length")==0)
        al=await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText.replace(/\\s+/g,' ').trim())")
        log('recipe page: says Read from your video. Check the amounts.',any(a.startswith('Read from your video. Check the amounts.') for a in al),al)
        log('recipe page: says 2 ingredients had no amount in the video',any(a.startswith('2 ingredients had no amount in the video. Add them, or cook by eye.') for a in al),al)
        e=await ev(pg)
        log('events: Add video {how: file}',[{k:v for k,v in d.items() if k!='src'} for d in of(e,'Add video')]==[{'how':'file'}],of(e,'Add video'))
        pr=of(e,'Video prep')
        log('events: Video prep {secs 10, frames, sound yes, ok yes}',len(pr)==1 and pr[0].get('secs')==10 and pr[0].get('frames')==len(fr) and pr[0].get('sound')=='yes' and pr[0].get('ok')=='yes' and 'why' not in pr[0],pr)
        vr=of(e,'Video read')
        log('events: Video read {from file, result ok, used mix, ms in whole seconds}',len(vr)==1 and vr[0].get('from')=='file' and vr[0].get('result')=='ok' and vr[0].get('used')=='mix' and isinstance(vr[0].get('ms'),int) and vr[0]['ms']%1000==0,vr)
        log('events: Video amounts {n 4, missing 2}',[{k:v for k,v in d.items() if k!='src'} for d in of(e,'Video amounts')]==[{'n':4,'missing':2}],of(e,'Video amounts'))
        log('events: Plan {from: video}',[d.get('from') for d in of(e,'Plan')]==['video'],of(e,'Plan'))
        log('events: every event carries src',all('src' in x['data'] for x in e),[x for x in e if 'src' not in x['data']])
        order=[x['name'] for x in e if x['name'] in ('Add video','Video prep','Plan','Video read','Video amounts')]
        log('events: in the order Add video, Video prep, Plan, Video read, Video amounts',order==['Add video','Video prep','Plan','Video read','Video amounts'],order)
        blob=json.dumps(e).lower()
        log('events: no file name, recipe text or link in any event',not any(x in blob for x in ['good','webm','noodle','garlic','soy','honey','http','blob:']),blob[:300])
        # the amounts given as a word: name first, the cook's word beside it, no number made up
        rows=await pg.evaluate("[...document.querySelectorAll('#sheet tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())")
        soy=[r for r in rows if 'soy sauce' in r]; hon=[r for r in rows if 'honey' in r]
        log('recipe page: soy sauce and honey are both there (not dropped)',len(soy)>=1 and len(hon)>=1,rows[:12])
        log('recipe page: neither has a number of cups, spoons or ounces made up',all(not re.search(r'\d\s*(cup|tbsp|tsp|oz|lb|ml|g)\b',r) for r in soy+hon),soy+hon)
        log('recipe page: each says No amount given',all('No amount given' in r for r in soy[:1]+hon[:1]),soy+hon)
        shop=await pg.evaluate("[...document.querySelectorAll('[data-panel=shop]')].map(e=>e.innerText).join('\\n')")
        log('grocery list: honey and soy sauce are on it, name first',bool(re.search(r'(^|\n)\s*honey',shop,re.I)) and bool(re.search(r'(^|\n)\s*soy sauce',shop,re.I)) and 'a drizzle of honey' not in shop,shop[:400])
        await pg.screenshot(path=os.path.join(HERE,'breakit','v13-recipe-390.png'))
        # Edit the text picks out the first line with no amount
        await pg.locator('#alerts [data-edit=first]').first.click(); await pg.wait_for_timeout(500)
        sel=await pg.evaluate("(()=>{const t=document.getElementById('text');return {open:document.getElementById('edit').open,focus:document.activeElement.id,sel:t.value.slice(t.selectionStart,t.selectionEnd)}})()")
        log('recipe page: Edit the text opens the editor with the first no-amount line picked out',sel=={'open':True,'focus':'text','sel':'soy sauce (a splash)'},sel)
        # the batch is saved as the cook's own, and New recipe goes back to a clean first screen
        saved=await pg.evaluate("JSON.parse(localStorage.getItem('bd-batches')||localStorage.getItem('bd-saved')||'[]')")
        keys=await pg.evaluate("Object.keys(localStorage)")
        allb=[x for k in keys for x in (await pg.evaluate("(k)=>{try{const v=JSON.parse(localStorage.getItem(k));return Array.isArray(v)?v:[]}catch(e){return []}}",k)) if isinstance(x,dict) and 'text' in x]
        log('saved: the batch is kept with f: video',any(x.get('f')=='video' for x in allb),[(x.get('title'),x.get('f')) for x in allb])
        await pg.click('#newRec'); await pg.wait_for_timeout(350)
        s3=await pg.evaluate("({pick:!!document.getElementById('pick').offsetParent,box:!!document.getElementById('videobox').offsetParent,vt:document.getElementById('videoToggle').innerText,mine:!!document.getElementById('mine').offsetParent})")
        log('after a video read, New recipe shows the first screen and the batch under My batches',s3=={'pick':True,'box':False,'vt':'Add a video','mine':True},s3)
        await ctx.close()

        # ---- frame picking on other shapes of video
        async def body_for(path,**kw):
            ctx,m=await new(b,**kw); pg=await tab(ctx,U); m.text=FULL; await pick_video(pg,path); await settled(pg,60000)
            w=[c for c in m.calls if c[0]=='watch']; return ctx,m,pg,(w[0][1] if w else None)
        ctx,m,pg,body=await body_for(V['busy'])
        fr=body['frames'] if body else []; ims=[img_of(f)[0] for f in fr]
        log('busy 40 s video: exactly 8 frames are sent, never more',len(fr)==8,len(fr))
        c0=mean(ims[0]) if ims else (0,0,0); c1=mean(ims[-1]) if ims else (0,0,0)
        log('busy video: the first frame is the very first picture (red card)',c0[0]>170 and c0[1]<90 and c0[2]<90,c0)
        log('busy video: the last frame is the very last picture (green card)',c1[1]>170 and c1[0]<110 and c1[2]<110,c1)
        log('busy video: no sound track, so no sound is sent, and the recipe is still read',body is not None and body.get('audio')=='' and await pg.evaluate(VIEW)=='v-sheet',body.get('audio','')[:20] if body else None)
        e=await ev(pg); pr=of(e,'Video prep')
        log('busy video: Video prep says secs 40, frames 8, sound no',len(pr)==1 and pr[0].get('secs')==40 and pr[0].get('frames')==8 and pr[0].get('sound')=='no',pr)
        await ctx.close()
        ctx,m,pg,body=await body_for(V['static'])
        log('still 20 s video: the same picture is sent once, not 8 times',body is not None and len(body['frames'])==1,len(body['frames']) if body else None); await ctx.close()
        ctx,m,pg,body=await body_for(V['big1080'])
        sz=[img_of(f)[0].size for f in body['frames']] if body else []
        log('1920 by 1080 video: frames are made 1000 by 563',bool(sz) and all(s==(1000,563) or s==(1000,562) for s in sz),sz); await ctx.close()
        ctx,m,pg,body=await body_for(V['tall'])
        sz=[img_of(f)[0].size for f in body['frames']] if body else []
        log('upright 1080 by 1920 video: frames are 563 by 1000',bool(sz) and all(s==(563,1000) or s==(562,1000) for s in sz),sz); await ctx.close()
        ctx,m,pg,body=await body_for(V['long200'])
        try: wi=wav_info(body['audio'])
        except Exception as ex: wi={'err':str(ex)}
        log('200 s video: the sound is cut to the first 180 s',179<wi.get('secs',0)<=180.05,wi)
        log('200 s video: the sound is under the 6,000,000 byte limit',0<wi.get('bytes',0)<=6_000_000,wi.get('bytes'))
        log('200 s video: 8 frames or fewer, and it reads',body is not None and len(body['frames'])<=8 and await pg.evaluate(VIEW)=='v-sheet',len(body['frames']) if body else None)
        log('200 s video: Video prep says secs 200',[d.get('secs') for d in of(await ev(pg),'Video prep')]==[200],of(await ev(pg),'Video prep')); await ctx.close()

        # ---- no sound: frames only, and the page says so
        ctx,m=await new(b); pg=await tab(ctx,U); m.used='screen'; m.text=FULL
        await pick_video(pg,V['nosound']); await settled(pg)
        w=[c for c in m.calls if c[0]=='watch']
        log('no-sound video: frames are sent with no sound',len(w)==1 and w[0][1].get('audio')=='' and len(w[0][1]['frames'])>=2,w[0][1].get('audio','')[:30] if w else None)
        al=await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText.replace(/\\s+/g,' ').trim())")
        log('no-sound video: recipe page says Read from the screen. This video has no speech.',al[:1]==['Read from the screen. This video has no speech.'],al)
        log('no-sound video: no "had no amount" line when every amount was given',not any('no amount' in a for a in al),al)
        e=await ev(pg)
        log('no-sound video: events say sound no and used screen',[d.get('sound') for d in of(e,'Video prep')]==['no'] and [d.get('used') for d in of(e,'Video read')]==['screen'] and [d.get('missing') for d in of(e,'Video amounts')]==[0],(of(e,'Video prep'),of(e,'Video read')))
        await ctx.close()
        ctx,m,pg,body=await body_for(V['silent'])
        log('video with a silent sound track: no sound is sent',body is not None and body.get('audio')=='',(body or {}).get('audio','')[:30]); await ctx.close()

        # ---- the "no amount" lines
        for text,want,name in ((ONE,'1 ingredient had no amount in the video. Add it, or cook by eye.','one'),(MOST,"This video doesn't give amounts for most things. The plan can scale what it has.",'most')):
            ctx,m=await new(b); pg=await tab(ctx,U); m.text=text; await pick_video(pg,V['nosound']); await settled(pg)
            al=await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText.replace(/\\s+/g,' ').trim())")
            log(f'no-amount line ({name}): {want[:40]}',any(a.startswith(want) for a in al) and sum('amount' in a and 'Check' not in a for a in al)==1,al)
            rows=await pg.evaluate("[...document.querySelectorAll('#sheet tr')].length"); 
            await ctx.close()

        # ================= 3. every failure message, with the next step offered
        async def fail_case(name,path,title,line,btns,watch='ok',calls=0,why=None,result=None,offline=False,clock=False,text=None):
            ctx,m=await new(b,clock=clock); pg=await tab(ctx,U); m.watch=watch
            if text is not None: m.text=text
            if offline: await ctx.set_offline(True)
            if clock: await pg.evaluate("window.__to=400")
            await pick_video(pg,path); await settled(pg,40000)
            st=await pg.evaluate(STATE); t=await pg.evaluate(FAILTXT); bt=await pg.evaluate(BTNS)
            log(f'{name}: says "{title}. {line}"',st=='fail' and t==f'{title} | {line}',(st,t))
            log(f'{name}: offers {", ".join(btns)}',bt==btns,bt)
            log(f'{name}: {calls} call(s) to the reader',len(m.calls)==calls,[c[0] for c in m.calls])
            e=await ev(pg)
            if why: log(f'{name}: Video prep {{ok no, why {why}}}',[(d.get('ok'),d.get('why')) for d in of(e,'Video prep')]==[('no',why)],of(e,'Video prep'))
            if result: log(f'{name}: Video read {{result {result}}}',[(d.get('from'),d.get('result')) for d in of(e,'Video read')]==[('file',result)],of(e,'Video read'))
            log(f'{name}: no Plan event, and focus is on the heading',not of(e,'Plan') and await pg.evaluate("document.activeElement.id")=='rdTitle')
            sz=await pg.evaluate("[...document.querySelectorAll('.failed button')].filter(b=>b.offsetParent).map(b=>Math.round(b.getBoundingClientRect().height))")
            log(f'{name}: every button is 44 px or more',all(x>=44 for x in sz),sz)
            log(f'{name}: no hidden player left on the page',await pg.evaluate("document.querySelectorAll('video').length")==0)
            return ctx,m,pg
        VB=['Choose another video','Paste text','Choose screenshots']; SB=['Choose screenshots','Paste text','Choose another video']; RB=['Try again','Paste text','Choose screenshots','Choose another video']
        ctx,m,pg=await fail_case('a picture, not a video',SHOT,"That file isn't a video",'Choose a video, or add screenshots.',VB,why='badfile'); await ctx.close()
        ctx,m,pg=await fail_case('a real PDF',V['realpdf'],"That file isn't a video",'Choose a video, or add screenshots.',VB,why='badfile'); await ctx.close()
        ctx,m,pg=await fail_case('a sound-only file',V['soundonly'],"That file isn't a video",'Choose a video, or add screenshots.',VB,why='badfile'); await ctx.close()
        ctx,m,pg=await fail_case('a PDF renamed to .mp4',V['pdf'],"This phone couldn't open that video",'Try a screen recording.',VB,why='cantopen'); await ctx.close()
        ctx,m,pg=await fail_case('a 0-byte file',V['zero'],"This phone couldn't open that video",'Try a screen recording.',VB,why='cantopen'); await ctx.close()
        ctx,m,pg=await fail_case('a video over 10 minutes',V['over10'],'That video is over 10 minutes','Trim it to the cooking part and try again.',VB,why='toolong'); await ctx.close()
        import time; t0=time.time()
        ctx,m,pg=await fail_case('a 2 GB file',V['huge'],'That video is too big','Trim it to the cooking part and try again.',VB,why='toobig'); dt=time.time()-t0
        heap=await pg.evaluate("performance.memory?performance.memory.usedJSHeapSize:0")
        log('a 2 GB file: refused at once, before it is read into memory',dt<12 and heap<300e6,(round(dt,1),heap)); await ctx.close()
        ctx,m,pg=await fail_case('no recipe in the video',V['good'],'No recipe found in that video',"If it's in the caption, add a screenshot of the caption.",SB,watch='none',calls=1,result='none'); await ctx.close()
        ctx,m,pg=await fail_case('the reader sends text with no ingredients',V['nosound'],'No recipe found in that video',"If it's in the caption, add a screenshot of the caption.",SB,calls=1,result='none',text='Hello everyone and welcome back to my channel'); await ctx.close()
        ctx,m,pg=await fail_case('per-visitor limit',V['nosound'],"That's a lot of videos",'Try again in a bit, or add screenshots.',SB,watch='limit',calls=1,result='limit'); await ctx.close()
        ctx,m,pg=await fail_case('daily cap (and the kill switch)',V['nosound'],'The video reader is busy today','Try again tomorrow, or add screenshots.',SB,watch='busy',calls=1,result='limit'); await ctx.close()
        ctx,m,pg=await fail_case('reader error',V['nosound'],"The video reader couldn't read it right now",'Add screenshots instead.',RB,watch='error',calls=1,result='error'); await ctx.close()
        ctx,m,pg=await fail_case('reader sends a web page, not JSON',V['nosound'],"The video reader couldn't read it right now",'Add screenshots instead.',RB,watch='html',calls=1,result='error'); await ctx.close()
        ctx,m,pg=await fail_case('reader sends junk',V['nosound'],"The video reader couldn't read it right now",'Add screenshots instead.',RB,watch='junk',calls=1,result='error'); await ctx.close()
        ctx,m,pg=await fail_case('reader connection drops',V['nosound'],"The video reader couldn't read it right now",'Add screenshots instead.',RB,watch='abort',calls=1,result='error'); await ctx.close()
        ctx,m,pg=await fail_case('reader timeout',V['nosound'],"The video reader couldn't read it right now",'Add screenshots instead.',RB,watch='hang',calls=1,result='timeout',clock=True); await ctx.close()
        # offline, then back online: Try again sends the same video
        ctx,m,pg=await fail_case('offline',V['nosound'],"You're offline",'Videos need the AI reader.',RB,calls=0,result='offline',offline=True)
        await ctx.set_offline(False); m.text=FULL; await pg.wait_for_timeout(600); await pg.click('#rdAgain'); await settled(pg)
        log('offline: back online, Try again reads the same video',await pg.evaluate(VIEW)=='v-sheet' and len([c for c in m.calls if c[0]=='watch'])==1,(await pg.evaluate(FAILTXT),len(m.calls))); await ctx.close()
        # reader error, then Try again resends what was already prepared (no second Video prep)
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='error'; m.text=FULL; await pick_video(pg,V['good']); await settled(pg)
        m.watch='ok'; await pg.wait_for_timeout(600); await pg.click('#rdAgain'); await settled(pg); e=await ev(pg)
        same=len(m.calls)==2 and m.calls[0][1]==m.calls[1][1]
        log('reader error: Try again sends the same frames and sound again and lands on the recipe',await pg.evaluate(VIEW)=='v-sheet' and same and len(of(e,'Video prep'))==1 and [d['result'] for d in of(e,'Video read')]==['error','ok'],([d.get('result') for d in of(e,'Video read')],len(of(e,'Video prep')))); await ctx.close()
        # the fail screen's other buttons
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='limit'; await pick_video(pg,V['nosound']); await settled(pg); await pg.wait_for_timeout(600)
        try:
            async with pg.expect_file_chooser(timeout=3000) as fc: await pg.click('#rdAgain')
            ch=await fc.value; acc=await ch.element.get_attribute('accept'); okc=acc=='image/*'
        except Exception as ex: okc=False; acc=str(ex)[:80]
        log('limit: Choose screenshots opens the screenshot picker, and the first screen is back',okc and await pg.evaluate(STATE)=='pick' and await pg.is_visible('#choose'),acc); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); await pick_video(pg,V['zero']); await settled(pg); await pg.wait_for_timeout(600)
        try:
            async with pg.expect_file_chooser(timeout=3000) as fc: await pg.click('#rdAgain')
            ch=await fc.value; acc=await ch.element.get_attribute('accept'); okc=acc=='video/*'
        except Exception as ex: okc=False; acc=str(ex)[:80]
        log("can't open: Choose another video opens the video picker",okc,acc)
        await pick_video(pg,V['over10']); await settled(pg,40000); await pg.wait_for_timeout(600); await pg.click('#rdPaste'); await pg.wait_for_timeout(200)
        log('too long: Paste text opens the paste box',await pg.is_visible('#paste') and not await pg.is_visible('#videobox') and await pg.evaluate(STATE)=='pick'); await ctx.close()
        # after a video failure, a screenshot failure shows its own buttons again
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='limit'; await pick_video(pg,V['nosound']); await settled(pg); await pg.wait_for_timeout(600)
        await pg.set_input_files('#file',V['realpdf']); await pg.wait_for_timeout(600)
        await pg.set_input_files('#file',{'name':'broken.png','mimeType':'image/png','buffer':b'not a png'}); await until(pg,f"({STATE})==='fail'&&document.getElementById('rdTitle').innerText.startsWith('Those')",8000)
        log('a screenshot failure after a video failure shows the screenshot buttons, not the video ones',await pg.evaluate(BTNS)==['Choose other screenshots','Paste text'],await pg.evaluate(BTNS)); await ctx.close()

        # ================= 4. cancel, double submit, back
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='hang'; await pick_video(pg,V['good'])
        await until(pg,"document.getElementById('status').innerText==='Listening'",15000)
        log('while reading: Cancel is there, 44 px, and "Read on this device instead" is not',await pg.is_visible('#rdCancel') and not await pg.is_visible('#rdDevice') and (await pg.locator('#rdCancel').bounding_box())['height']>=44)
        th=await pg.evaluate("document.querySelectorAll('#thumbs .th img').length")
        log('while reading: the picked frames show as small pictures',2<=th<=8,th)
        await pg.screenshot(path=os.path.join(HERE,'breakit','v13-reading-390.png'))
        await pg.click('#rdCancel'); await pg.wait_for_timeout(500); e=await ev(pg)
        log('cancel while the reader works: back on the first screen, Video read {result cancel}, no failure shown',await pg.evaluate(STATE)=='pick' and await pg.evaluate(VIEW)=='v-add' and [(d.get('from'),d.get('result')) for d in of(e,'Video read')]==[('file','cancel')],of(e,'Video read'))
        m.watch='ok'; await pg.wait_for_timeout(1200)
        log('cancel: the late answer changes nothing',await pg.evaluate(VIEW)=='v-add' and not of(await ev(pg),'Plan')); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); await pick_video(pg,V['long200']); await pg.wait_for_timeout(250)
        st=await pg.evaluate("document.getElementById('status').innerText"); await pg.click('#rdCancel'); await pg.wait_for_timeout(2500)
        log('cancel while the video is being prepared: back on the first screen, nothing sent, player removed',st=='Getting the video ready' and await pg.evaluate(STATE)=='pick' and not m.calls and await pg.evaluate("document.querySelectorAll('video').length")==0,(st,len(m.calls)))
        await pick_video(pg,V['nosound']); m.text=FULL; await settled(pg)
        log('after a cancel, another video reads fine',await pg.evaluate(VIEW)=='v-sheet' and len(m.calls)==1); await ctx.close()
        # double submit: a second video while the first is still being read
        ctx,m=await new(b); pg=await tab(ctx,U); m.delay=1.5; m.text=FULL; await pick_video(pg,V['good'])
        await until(pg,"document.getElementById('status').innerText==='Listening'",15000)
        await pg.set_input_files('#vfile',V['nosound']); await settled(pg); await pg.wait_for_timeout(2200); e=await ev(pg)
        log('second video while the first is reading: one recipe, one Plan, the second video wins',await pg.evaluate(VIEW)=='v-sheet' and len(of(e,'Plan'))==1 and len(of(e,'Add video'))==2 and [d.get('result') for d in of(e,'Video read')]==['ok'] and m.calls[-1][1].get('audio')=='',(len(of(e,'Plan')),of(e,'Video read'),len(m.calls)))
        log('second video: no leftover player',await pg.evaluate("document.querySelectorAll('video').length")==0); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.text=FULL
        await pg.click('#videoToggle'); await pg.set_input_files('#vfile',V['good']); await pg.set_input_files('#vfile',V['nosound']); await settled(pg); await pg.wait_for_timeout(800); e=await ev(pg)
        log('two videos picked one right after the other: one recipe, one read sent',await pg.evaluate(VIEW)=='v-sheet' and len(of(e,'Plan'))==1 and len(m.calls)==1,(len(of(e,'Plan')),len(m.calls))); await ctx.close()
        # Back
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='hang'; await pick_video(pg,V['good']); await until(pg,"document.getElementById('status').innerText==='Listening'",15000)
        await pg.go_back(); await pg.wait_for_timeout(500)
        log('Back while reading a video: the first screen, still on the site',await pg.evaluate(STATE)=='pick' and await pg.evaluate(VIEW)=='v-add' and pg.url.startswith(U),pg.url)
        m.watch='ok'; m.text=FULL; await pick_video(pg,V['nosound']); await settled(pg)
        log('Back, then another video: reads',await pg.evaluate(VIEW)=='v-sheet')
        await pg.go_back(); await pg.wait_for_timeout(500)
        log('Back from the recipe: the first screen, not the reading screen',await pg.evaluate(STATE)=='pick' and await pg.evaluate(VIEW)=='v-add')
        await pg.go_forward(); await pg.wait_for_timeout(500)
        log('Forward: the recipe again',await pg.evaluate(VIEW)=='v-sheet'); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.watch='limit'; await pick_video(pg,V['nosound']); await settled(pg); await pg.go_back(); await pg.wait_for_timeout(500)
        log('Back from a failure: the first screen',await pg.evaluate(STATE)=='pick' and await pg.evaluate(VIEW)=='v-add'); await ctx.close()
        # a video dropped on the card
        ctx,m=await new(b,1280,900,False); pg=await tab(ctx,U); m.text=FULL
        data=base64.b64encode(open(V['nosound'],'rb').read()).decode()
        await pg.evaluate("""(d)=>{const u=Uint8Array.from(atob(d),c=>c.charCodeAt(0)),f=new File([u],'clip.webm',{type:'video/webm'}),dt=new DataTransfer();dt.items.add(f);
          document.getElementById('dropcard').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}))}""",data)
        await settled(pg)
        log('a video dropped on the card is read as a video',await pg.evaluate(VIEW)=='v-sheet' and [c[0] for c in m.calls]==['watch'],[c[0] for c in m.calls]); await ctx.close()
        # reduced motion, dark, desktop
        ctx,m=await new(b,1440,900,False,'dark',reduced=True); pg=await tab(ctx,U); await pick_video(pg,V['good']); await settled(pg)
        log('reduced motion, dark, 1440: the video reads',await pg.evaluate(VIEW)=='v-sheet')
        await pg.screenshot(path=os.path.join(HERE,'breakit','v13-recipe-dark-1440.png'))
        over=await pg.evaluate("document.documentElement.scrollWidth>innerWidth"); log('recipe from a video, dark 1440: nothing wider than the screen',not over); await ctx.close()
        for scheme,w,h,mob in (('dark',390,844,True),('light',1440,900,False)):
            ctx,m=await new(b,w,h,mob,scheme); pg=await tab(ctx,U); m.watch='error'; await pick_video(pg,V['nosound']); await settled(pg)
            st=await pg.evaluate("""()=>{const t=document.getElementById('rdTitle'),c=getComputedStyle(t),bg=getComputedStyle(document.body).backgroundColor;return {over:document.documentElement.scrollWidth>innerWidth,color:c.color,bg,vis:t.getBoundingClientRect().top>=0}}""")
            log(f'failure screen {scheme} {w}: fits, and the heading stands out from the page',not st['over'] and st['color']!=st['bg'] and st['vis'],st)
            await pg.screenshot(path=os.path.join(HERE,'breakit',f'v13-fail-{scheme}-{w}.png')); await ctx.close()

        # ================= 5. a paste that is only a link
        LINKS=[('https://www.tiktok.com/@cook/video/7300000000000000000','tiktok','TikTok'),('https://vm.tiktok.com/ZMabc123/','tiktok','TikTok'),('tiktok.com/@cook/video/73','tiktok','TikTok'),
               ('https://www.instagram.com/reel/Cabc123/?igsh=xyz','instagram','Instagram'),('instagr.am/p/abc','instagram','Instagram'),
               ('https://www.facebook.com/watch/?v=123','facebook','Facebook'),('https://fb.watch/abc123/','facebook','Facebook'),('https://m.facebook.com/reel/99','facebook','Facebook'),
               ('https://www.pinterest.com/pin/123456/','pinterest','Pinterest'),('https://pin.it/abc123','pinterest','Pinterest'),('https://www.pinterest.co.uk/pin/1/','pinterest','Pinterest')]
        ctx,m=await new(b); pg=await tab(ctx,U)
        for url,site,name in LINKS:
            n0=len(pg._req); await pg.evaluate("window.__ev.length=0"); await paste_link(pg,'  '+url+'\n')
            st=await pg.evaluate("({note:!!document.getElementById('linkNote').offsetParent,txt:document.getElementById('linkText').innerText,btns:[...document.querySelectorAll('#lnActs button')].filter(b=>b.offsetParent).map(b=>b.innerText),h:[...document.querySelectorAll('#lnActs button')].map(b=>Math.round(b.getBoundingClientRect().height)),view:"+VIEW+",state:"+STATE+"})")
            e=await ev(pg)
            log(f'{site} link {url[:38]}: says we can\'t read {name} links, offers Add a video and Choose screenshots',st['note'] and st['txt']==f"We can't read {name} links. Add the video or a screenshot instead." and st['btns']==['Add a video','Choose screenshots'] and all(x>=44 for x in st['h']) and st['view']=='v-add' and st['state']=='pick',st)
            log(f'{site} link: Link paste {{site {site}, result unsupported}} and nothing else',[(x['name'],x['data'].get('site'),x['data'].get('result')) for x in e]==[('Link paste',site,'unsupported')],e)
            log(f'{site} link: nothing is sent anywhere',len(pg._req)==n0 and not m.calls,pg._req[n0:])
            log(f'{site} link: the link is not in the event',not any(x in json.dumps(e) for x in ['http','.com','.am','.it','.watch','Cabc','ZMabc','cook','/']),e)
        await pg.screenshot(path=os.path.join(HERE,'breakit','v13-linknote-390.png'))
        await pg.click('#lnVideo'); await pg.wait_for_timeout(200)
        log('link note: Add a video opens the video box',await pg.is_visible('#vchoose') and not await pg.is_visible('#paste'))
        await paste_link(pg,'https://www.instagram.com/reel/Cabc123/'); await pg.wait_for_timeout(600)
        try:
            async with pg.expect_file_chooser(timeout=3000) as fc: await pg.click('#lnShots')
            okc=(await (await fc.value).element.get_attribute('accept'))=='image/*'
        except Exception: okc=False
        log('link note: Choose screenshots opens the screenshot picker and the first screen',okc and await pg.is_visible('#choose'))
        await paste_link(pg,'https://www.instagram.com/reel/Cabc123/'); await pg.type('#paste',' '); await pg.wait_for_timeout(100)
        log('link note: goes away when the cook types',not await pg.is_visible('#linkNote'))
        # a web page
        for url in ('https://www.seriouseats.com/best-chili-recipe','www.example.com/recipes/chili?x=1','http://example.com'):
            n0=len(pg._req); await pg.evaluate("window.__ev.length=0"); await paste_link(pg,url)
            st=await pg.evaluate("({note:!!document.getElementById('linkNote').offsetParent,txt:document.getElementById('linkText').innerText,btns:[...document.querySelectorAll('#lnActs button')].filter(b=>b.offsetParent).length,focus:document.activeElement.id,sel:(()=>{const t=document.getElementById('paste');return t.selectionEnd-t.selectionStart===t.value.length})()})"); e=await ev(pg)
            log(f'web page link {url[:34]}: says copy the recipe from the page and paste it here',st['note'] and st['txt']=='That looks like a web page. Copy the recipe from the page and paste it here.' and st['btns']==0 and st['focus']=='paste' and st['sel'],st)
            log('web page link: Link paste {site web, result unsupported}; nothing sent',[(x['name'],x['data'].get('site'),x['data'].get('result')) for x in e]==[('Link paste','web','unsupported')] and len(pg._req)==n0 and not m.calls,e)
        await ctx.close()
        # text that only has a link in it is still text
        for text,want,name in (('Beef chili from https://example.com/chili\nServes 6\n2 lb ground beef\n1 can beans\n1. Brown the beef.','v-sheet','a recipe with a link in it'),
                               ('check this https://youtu.be/dQw4w9WgXcQ','v-add','a link with words around it'),('rice.flour','v-add','a word with a dot'),('1/2 cup rice\n1 egg','v-sheet','amounts with a slash')):
            ctx,m=await new(b); pg=await tab(ctx,U); n0=len(pg._req); await paste_link(pg,text); await pg.wait_for_timeout(300); e=await ev(pg)
            log(f'{name}: treated as text, not as a link',await pg.evaluate(VIEW)==want and not of(e,'Link paste') and not m.calls and not await pg.evaluate("!!document.getElementById('linkNote').offsetParent"),(await pg.evaluate(VIEW),of(e,'Link paste')))
            if want=='v-add': log(f'{name}: the usual No ingredients found',(await pg.inner_text('#toast')).strip()=='No ingredients found',await pg.inner_text('#toast'))
            await ctx.close()

        # ================= 6. YouTube links
        for url in (YT,'https://youtu.be/dQw4w9WgXcQ?si=abc','youtube.com/shorts/dQw4w9WgXcQ','https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10s'):
            ctx,m=await new(b); pg=await tab(ctx,U); n0=len(pg._req); await paste_link(pg,url); await settled(pg); e=await ev(pg)
            sent=m.calls[0][1] if m.calls else {}
            log(f'YouTube link {url[:40]}: sent to /link as {{url}} and read',await pg.evaluate(VIEW)=='v-sheet' and [c[0] for c in m.calls]==['link'] and sorted(sent.keys())==['url'] and sent['url'].endswith(url.split('//')[-1]) and sent['url'].startswith('https://'),(await pg.evaluate(FAILTXT),sent))
            outside=[u for u in pg._req[n0:] if not u.startswith(U)]
            log('YouTube link: the page itself calls only the reader, never YouTube',outside!=[] and all('.hf.space/link' in u for u in outside),outside)
            log('YouTube link: Link paste {youtube, read}, Video read {youtube, ok}, Plan {from youtube}, Video amounts',[(d.get('site'),d.get('result')) for d in of(e,'Link paste')]==[('youtube','read')] and [(d.get('from'),d.get('result'),d.get('used')) for d in of(e,'Video read')]==[('youtube','ok','mix')] and [d.get('from') for d in of(e,'Plan')]==['youtube'] and len(of(e,'Video amounts'))==1,e)
            log('YouTube link: no link, video id or creator in any event',not any(x in json.dumps(e) for x in ['dQw4','youtu.be','youtube.com','http','Test Kitchen','Garlic']),json.dumps(e)[:300])
            await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.used='caption'; await paste_link(pg,YT); await settled(pg)
        fr=await pg.evaluate("""()=>{const p=document.getElementById('sFrom'),a=[...p.querySelectorAll('a')];return {vis:!!p.offsetParent,text:p.innerText.replace(/\\s+/g,' ').trim(),links:a.map(x=>[x.innerText,x.href,x.target,x.rel,Math.round(x.getBoundingClientRect().height)])}}""")
        log('YouTube recipe page: "From Test Kitchen on YouTube" links to the video',fr['vis'] and fr['text'].startswith('From Test Kitchen on YouTube') and fr['links'][0][:4]==['Test Kitchen',YT,'_blank','noopener'],fr)
        log('YouTube recipe page: a YouTube Terms link sits beside it',len(fr['links'])==2 and fr['links'][1][:4]==['YouTube Terms','https://www.youtube.com/t/terms','_blank','noopener'],fr['links'])
        log('YouTube recipe page: both links are 44 px tall',all(l[4]>=44 for l in fr['links']),[l[4] for l in fr['links']])
        al=await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText.replace(/\\s+/g,' ').trim())")
        log("YouTube recipe page: says Read from the video's description. Check the amounts.",al[:1]==["Read from the video's description. Check the amounts."] and any(a.startswith('2 ingredients had no amount in the video') for a in al),al)
        await pg.screenshot(path=os.path.join(HERE,'breakit','v13-youtube-390.png'))
        log('YouTube recipe page: nothing wider than the screen',not await pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        # kept with the saved batch, on this device
        await pg.reload(); await pg.wait_for_timeout(500)
        if await pg.evaluate(VIEW)!='v-sheet': await pg.locator('#savedList li button, #savedList li a').first.click(); await pg.wait_for_timeout(500)
        fr2=await pg.evaluate("(()=>{const p=document.getElementById('sFrom');return {vis:!!p.offsetParent,text:p.innerText.replace(/\\s+/g,' ').trim(),href:(p.querySelector('a')||{}).href}})()")
        log('YouTube batch reopened after a reload: still says who it is from',await pg.evaluate(VIEW)=='v-sheet' and fr2['vis'] and fr2['text'].startswith('From Test Kitchen on YouTube') and fr2['href']==YT,fr2)
        log('YouTube batch reopened: no reader call on reopen',len(m.calls)==0 or [c[0] for c in m.calls]==['link'],[c[0] for c in m.calls])
        await pg.click('#newRec'); await pg.wait_for_timeout(300); await paste_link(pg,FULL); await pg.wait_for_timeout(300)
        log('a pasted recipe after it shows no From line and no video note',await pg.evaluate(VIEW)=='v-sheet' and not await pg.evaluate("!!document.getElementById('sFrom').offsetParent") and not any('video' in a for a in await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText)")))
        await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.used='mix'; m.creator='<img src=x onerror=alert(1)> & "Co"'; await paste_link(pg,YT); await settled(pg)
        fr=await pg.evaluate("(()=>{const p=document.getElementById('sFrom');return {text:p.innerText,imgs:p.querySelectorAll('img').length}})()")
        al=await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText.replace(/\\s+/g,' ').trim())")
        log('a creator name with HTML in it is shown as text',fr['imgs']==0 and '<img src=x onerror=alert(1)> & "Co"' in fr['text'],fr)
        log('YouTube watched (not the description): says Read from the video. Check the amounts.',al[:1]==['Read from the video. Check the amounts.'],al); await ctx.close()
        for bad in ('javascript:alert(1)','https://evil.example/watch?v=dQw4w9WgXcQ','https://www.youtube.com/watch?v=dQw4w9WgXcQ&x="><script>alert(1)</script>',None):
            ctx,m=await new(b); pg=await tab(ctx,U); m.url=bad; await paste_link(pg,YT); await settled(pg)
            log(f'a reader answer with a bad link ({str(bad)[:28]}): the recipe shows, with no From line',await pg.evaluate(VIEW)=='v-sheet' and not await pg.evaluate("!!document.getElementById('sFrom').offsetParent")); await ctx.close()
        # YouTube failures
        async def link_case(name,mode,title,line,btns,result,calls=1,offline=False,clock=False):
            ctx,m=await new(b,clock=clock); pg=await tab(ctx,U); m.link=mode
            if clock: await pg.evaluate("window.__to=400")
            if not await pg.is_visible('#paste'): await pg.click('#pasteToggle')
            await pg.fill('#paste',YT); await pg.wait_for_timeout(550)
            if offline: await ctx.set_offline(True)
            await pg.click('#usePaste'); await settled(pg,40000)
            st=await pg.evaluate(STATE); t=await pg.evaluate(FAILTXT); bt=await pg.evaluate(BTNS); e=await ev(pg)
            log(f'YouTube, {name}: says "{title}. {line}"',st=='fail' and t==f'{title} | {line}',(st,t))
            log(f'YouTube, {name}: offers {", ".join(btns)}',bt==btns,bt)
            log(f'YouTube, {name}: Video read {{from youtube, result {result}}}, no Plan, {calls} call',[(d.get('from'),d.get('result')) for d in of(e,'Video read')]==[('youtube',result)] and not of(e,'Plan') and len(m.calls)==calls,(of(e,'Video read'),len(m.calls)))
            return ctx,m,pg
        LB=['Choose screenshots','Paste text','Add a video']; LR=['Try again','Paste text','Choose screenshots','Add a video']
        ctx,m,pg=await link_case('not switched on (503)','off',"YouTube links aren't on yet",'Add the video or screenshots.',LB,'off')
        await pg.wait_for_timeout(600); await pg.click('#rdVideo'); await pg.wait_for_timeout(250)
        log('YouTube not on: Add a video opens the video box',await pg.evaluate(STATE)=='pick' and await pg.is_visible('#vchoose')); await ctx.close()
        ctx,m,pg=await link_case('private or unlisted','private','That video is private','Add screenshots or paste the recipe.',LB,'private')
        await pg.wait_for_timeout(600); await pg.click('#rdPaste'); await pg.wait_for_timeout(250)
        log('YouTube private: Paste text opens the paste box',await pg.is_visible('#paste') and not await pg.is_visible('#linkNote')); await ctx.close()
        ctx,m,pg=await link_case('no recipe','none','No recipe found in that video','',LB,'none'); await ctx.close()
        ctx,m,pg=await link_case('too long','toolong','That video is too long to read from a link','Add screenshots or paste the recipe.',LB,'toolong'); await ctx.close()
        ctx,m,pg=await link_case('per-visitor limit','limit',"That's a lot of videos",'Try again in a bit, or add screenshots.',LB,'limit'); await ctx.close()
        ctx,m,pg=await link_case('daily cap','busy','The video reader is busy today','Try again tomorrow, or add screenshots.',LB,'limit'); await ctx.close()
        ctx,m,pg=await link_case('reader error','error',"The video reader couldn't read it right now",'Add screenshots instead.',LR,'error')
        m.link='ok'; await pg.wait_for_timeout(600); await pg.click('#rdAgain'); await settled(pg)
        log('YouTube reader error: Try again sends the link again and reads it',await pg.evaluate(VIEW)=='v-sheet' and len(m.calls)==2 and m.calls[0][1]==m.calls[1][1]); await ctx.close()
        ctx,m,pg=await link_case('timeout','hang',"The video reader couldn't read it right now",'Add screenshots instead.',LR,'timeout',clock=True); await ctx.close()
        ctx,m,pg=await link_case('offline','ok',"You're offline",'Videos need the AI reader.',LR,'offline',calls=0,offline=True); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.link='hang'; await paste_link(pg,YT); await pg.wait_for_timeout(400)
        st=await pg.evaluate("document.getElementById('status').innerText"); await pg.click('#rdCancel'); await pg.wait_for_timeout(500); e=await ev(pg)
        log('YouTube link: says Reading the video; Cancel goes back with Video read {youtube, cancel}',st=='Reading the video' and await pg.evaluate(STATE)=='pick' and [(d.get('from'),d.get('result')) for d in of(e,'Video read')]==[('youtube','cancel')],(st,of(e,'Video read'))); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); m.delay=1.2; m.text=FULL
        await paste_link(pg,YT); await pg.evaluate("document.getElementById('usePaste').click()"); await settled(pg); await pg.wait_for_timeout(1800); e=await ev(pg)
        log('YouTube link: Use this recipe tapped twice gives one recipe and one Plan',await pg.evaluate(VIEW)=='v-sheet' and len(of(e,'Plan'))==1,(len(of(e,'Plan')),len(m.calls))); await ctx.close()

        # ================= 7. screenshots and pasted text still work as before, and the page's CSP holds
        ctx,m=await new(b); pg=await tab(ctx,U); m.text=FULL
        await pg.set_input_files('#file',SHOT); await settled(pg); e=await ev(pg)
        log('screenshots still go to /read and land on the recipe',await pg.evaluate(VIEW)=='v-sheet' and [c[0] for c in m.calls]==['read'] and 'images' in m.calls[0][1] and [d.get('from') for d in of(e,'Plan')]==['screenshots'],[c[0] for c in m.calls])
        log('screenshots: no video note and no From line',not any('video' in a for a in await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText)")) and not await pg.evaluate("!!document.getElementById('sFrom').offsetParent")); await ctx.close()
        ctx,m=await new(b); pg=await tab(ctx,U); await paste_link(pg,'Honey toast\nServes 1\n2 slices bread\na drizzle of honey\na knob of butter\n1. Toast and spread.'); await pg.wait_for_timeout(300)
        rows=await pg.evaluate("[...document.querySelectorAll('#sheet tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())"); e=await ev(pg)
        log('pasted text with "a drizzle of honey" and "a knob of butter": both kept, name first',any(r.startswith('honey') or ' honey' in r for r in rows) and any('butter' in r for r in rows) and not any('a drizzle of honey' in r for r in rows),rows)
        log('pasted text: Plan {from paste}, and no video note',[d.get('from') for d in of(e,'Plan')]==['paste'] and not any('video' in a for a in await pg.evaluate("[...document.querySelectorAll('#alerts .alert')].map(a=>a.innerText)"))); await ctx.close()
        html=open(os.path.join(ROOT,'index.html')).read(); csp=re.search(r'Content-Security-Policy" content="([^"]+)"',html).group(1)
        log('CSP: media-src is blob: only',re.search(r"media-src ([^;]+)",csp) and re.search(r"media-src ([^;]+)",csp).group(1).strip()=='blob:',csp[-300:])
        log("CSP: still default-src 'self', no unsafe-inline or unsafe-eval for scripts, object-src none",csp.startswith("default-src 'self'") and "'unsafe-eval'" not in csp and "'unsafe-inline'" not in csp.split('script-src')[1].split(';')[0] and "object-src 'none'" in csp)
        log('CSP: connect-src has the reader and no video site',('hf.space' in csp.split('connect-src')[1].split(';')[0]) and not re.search(r'youtube|tiktok|instagram|googleapis',csp),csp.split('connect-src')[1].split(';')[0])
        pv=open(os.path.join(ROOT,'privacy.html')).read(); ab=open(os.path.join(ROOT,'about.html')).read()
        log('privacy page: has a Videos section that says the file is not uploaded, and names Google for YouTube links','<h2>Videos</h2>' in pv and 'The video file itself is not uploaded' in pv and 'YouTube' in pv and 'Gemini' in pv and 'youtube.com/t/terms' in pv and 'Last updated 15 November 2026' in pv)
        log('about page: says nothing about video while it is off (the video text waits in about.video.body.keep)','video' not in ab.lower() or 'stays on your device' in ab)
        tx=re.sub(r'<script.*?</script>|<style.*?</style>','',pv+ab+open(os.path.join(HERE,'template.html')).read(),flags=re.S)
        log('no em dash in the new words',not re.search(r"(video|YouTube|frames)[^<\n]{0,80}—|—[^<\n]{0,80}(video|YouTube|frames)",tx))

        await b.close()
    log('no console errors, page errors, dialogs or CSP violations in any run',not ERRS,ERRS[:6])
    os.makedirs(os.path.join(HERE,'breakit'),exist_ok=True); json.dump(R,open(os.path.join(HERE,'breakit','r13.json'),'w'),indent=1)
    shutil.rmtree(TMP,ignore_errors=True)
    bad=[r for r in R if r[1]!='ok']; print(f'\n{len(R)-len(bad)} of {len(R)} ok'); sys.exit(1 if bad else 0)
asyncio.run(main())
