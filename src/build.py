import os
READER=(open('reader.txt').read().strip() if os.path.exists('reader.txt') else '')  # e.g. https://user-space.hf.space
t=open('template.html').read().replace('/*READER*/',READER); e=open('engine.js').read()+'\n'+open('qr.js').read()  # the label QR encoder rides in the same inline script as the engine
open('site/index.html','w').write(t.replace('/*ENGINE*/',e))
open('site/favicon.svg','w').write('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="1.804 0.804 52.391 52.391"><style>g{stroke:#c2410c}@media(prefers-color-scheme:dark){g{stroke:#ff7a3d}}</style><g fill="none" stroke="#c2410c" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 16c-2-3 2-5 0-8"/><path d="M28 16c-2-3 2-5 0-8"/><path d="M36 16c-2-3 2-5 0-8"/><path d="M10 24h36"/><path d="M13 24v16a6 6 0 0 0 6 6h18a6 6 0 0 0 6-6V24"/><path d="M6 28h7M43 28h7"/></g></svg>''')  # from /home/claude/brand/mark.py: the one 3-steam pot
open('site/CNAME','w').write('batch.recipes\n')
open('site/.nojekyll','w').write('')
G='https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com https://*.gstatic.com https://*.googletagservices.com https://*.adtrafficquality.google https://*.googleadservices.com'
# CSP with script hashes (recompute on every build)
import re, hashlib, base64
h=open('site/index.html').read()
hashes=["'sha256-"+base64.b64encode(hashlib.sha256(m.encode()).digest()).decode()+"'" for m in re.findall(r'<script>(.*?)</script>', h, re.S)]
csp=("default-src 'self'; script-src 'self' "+' '.join(hashes)+" https://cdn.jsdelivr.net https://cloud.umami.is 'wasm-unsafe-eval' https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com https://*.gstatic.com https://*.googletagservices.com https://*.adtrafficquality.google https://*.googleadservices.com; worker-src blob: https://cdn.jsdelivr.net; "
     "connect-src 'self' https://cdn.jsdelivr.net https://gateway.umami.is "+G+(" "+READER if READER else "")+"; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: "+G+"; frame-src "+G+"; fenced-frame-src "+G+"; font-src 'self'; "
     "base-uri 'none'; object-src 'none'; form-action 'none'; upgrade-insecure-requests")
h=h.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="'+csp+'">\n<meta name="referrer" content="strict-origin-when-cross-origin">',1)
open('site/index.html','w').write(h)
print(len(hashes),'script hashes')
import json
json.dump({"name":"batch.recipes","short_name":"batch.recipes","description":"Cook once. Eat all week.","start_url":"./","scope":"./","display":"standalone","background_color":"#ffffff","theme_color":"#ffffff",
 "icons":[{"src":"icon-192.png?v=3","sizes":"192x192","type":"image/png"},{"src":"icon-512.png?v=3","sizes":"512x512","type":"image/png"},{"src":"icon-maskable-512.png?v=3","sizes":"512x512","type":"image/png","purpose":"maskable"}]},open('site/manifest.webmanifest','w'),indent=1)

# search pages ("guides"): node guides.js runs every page's calculator on engine.js and prints the pages as JSON
import subprocess, html as H
GD=json.loads(subprocess.run(['node','guides.js'],capture_output=True,text=True,check=True).stdout)
SITE='https://batch.recipes/'
open('site/engine.js','w').write(open('engine.js').read())  # the guides' calculators load the same engine as the home page
s=open('pages/_shell.html').read(); GCSS=open('pages/_guide.css').read()
def page(name,title,desc,body,head='',css='',csp=True):  # every page: the shell's inline script (theme, visit source, Vercel Web Analytics) is allowed by its hash
    h=s.replace('{{TITLE}}',H.escape(title,quote=False)).replace('{{DESC}}',H.escape(desc)).replace('{{HEAD}}',head).replace('{{CSS}}',css).replace('{{BODY}}',body)
    if csp:  # same model as the home page: every inline script is allowed by its hash
        hs=["'sha256-"+base64.b64encode(hashlib.sha256(m.encode()).digest()).decode()+"'" for m in re.findall(r'<script>(.*?)</script>', h, re.S)]
        # 'self' covers /_vercel/insights/script.js and its /_vercel/insights/view and /event calls
        c=("default-src 'self'; script-src 'self' "+' '.join(hs+['https://cloud.umami.is'])+"; connect-src 'self' https://gateway.umami.is; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
           "base-uri 'none'; object-src 'none'; form-action 'none'; upgrade-insecure-requests")
        h=h.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="'+c+'">\n<meta name="referrer" content="strict-origin-when-cross-origin">',1)
    open(f'site/{name}.html','w').write(h)
def seo(url,title,desc,kind='article'):
    e=H.escape
    return ('\n<link rel="canonical" href="'+url+'">\n<meta property="og:type" content="'+kind+'">\n<meta property="og:site_name" content="batch.recipes">\n<meta property="og:title" content="'+e(title)+'">\n<meta property="og:description" content="'+e(desc)+'">'
            '\n<meta property="og:image" content="'+SITE+'og.png">\n<meta property="og:url" content="'+url+'">\n<meta name="twitter:card" content="summary_large_image">')
GLIST='<ul class="gl">'+''.join(f'<li><a href="{g["slug"]}">{H.escape(g["h1"],quote=False)}</a></li>' for g in GD['pages'])+'</ul>'
for n,t_,d in [('privacy','Privacy','How batch.recipes handles your recipes, screenshots and ads.'),('about','About','What batch.recipes is and who makes it.')]:
    page(n,t_,d,open(f'pages/{n}.body').read().replace('{{GUIDES}}',GLIST),seo(SITE+n,t_+' · batch.recipes',d,'website'),GCSS if n=='about' else '')
for g in GD['pages']:
    page(g['slug'],g['title'],g['desc'],g['body'],seo(g['url'],g['h1'],g['desc']),GCSS,True)
gd='Batch cooking questions, each with a calculator: rice, chicken, pot sizes, doubling, tripling and baking.'
ld={"@context":"https://schema.org","@type":"CollectionPage","url":SITE+"guides","name":"Guides","description":gd,"isPartOf":{"@type":"WebSite","name":"batch.recipes","url":SITE},
    "mainEntity":{"@type":"ItemList","itemListElement":[{"@type":"ListItem","position":i+1,"url":g['url'],"name":g['h1']} for i,g in enumerate(GD['pages'])]}}
page('guides','Guides',gd,'<article class="g">\n<h1>Guides</h1>\n<ul class="gl idx">'
     +''.join(f'<li><a href="{g["slug"]}">{H.escape(g["h1"],quote=False)}<span>{H.escape(g["sum"],quote=False)}</span></a></li>' for g in GD['pages'])
     +'</ul>\n<p class="cta"><a class="btn" href="./" data-umami-event="Guide plan" data-umami-event-guide="guides">Plan your own recipe</a></p>\n</article>\n<script type="application/ld+json">'+json.dumps(ld).replace('<','\\u003c')+'</script>',
     seo(SITE+'guides','Guides · batch.recipes',gd,'website'),GCSS,True)
# 404: a plain "Page not found" with ways on. Vercel serves /404.html, with status 404, for any address that isn't a file.
# It can show at any depth (/a/b/c), so every address in it starts at the root. Not in the sitemap, and marked noindex.
page('404','Page not found',"That page isn't here.",'<article class="g">\n<h1>Page not found</h1>\n<p class="lead">That address isn\'t on batch.recipes.</p>\n<p class="cta"><a class="btn" href="/">Go to the home page</a></p>\n<p class="nf"><a href="/guides">See the guides</a></p>\n</article>',
     '\n<meta name="robots" content="noindex">',GCSS+'.g .nf{margin:8px 0 0;text-align:center}.g .nf a{min-height:44px;display:inline-flex;align-items:center}')
h4=open('site/404.html').read()
for a,b in [('href="./"','href="/"'),('href="guides"','href="/guides"'),('href="about"','href="/about"'),('href="privacy"','href="/privacy"'),('href="favicon.svg','href="/favicon.svg'),('href="apple-touch-icon.png','href="/apple-touch-icon.png')]: h4=h4.replace(a,b)
assert 'href="./' not in h4 and not __import__('re').search(r'(href|src)="(?!/|https://)',h4), 'a relative address on the 404 page'
open('site/404.html','w').write(h4)
# sitemap and robots (robots allows everything)
urls=[SITE,SITE+'guides']+[g['url'] for g in GD['pages']]+[SITE+'about',SITE+'privacy']
# lastmod is each page's own last change: lastmod.json (kept beside this file, and in the repo) remembers a hash of every built page and the day it last changed.
# A page whose built file is the same as last time keeps its date; a changed or new page gets today's. BD_TODAY=YYYY-MM-DD overrides the day.
import datetime
try: LM=json.load(open('lastmod.json'))
except Exception: LM={}
TODAY=os.environ.get('BD_TODAY') or datetime.date.today().isoformat()
def lastmod(u):
    f='index' if u==SITE else u[len(SITE):]
    hsh=hashlib.sha256(open(f'site/{f}.html','rb').read()).hexdigest()
    if (LM.get(f) or {}).get('hash')!=hsh: LM[f]={'hash':hsh,'date':TODAY}
    return LM[f]['date']
open('site/sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{u}</loc><lastmod>{lastmod(u)}</lastmod></url>\n' for u in urls)+'</urlset>\n')
json.dump({k:LM[k] for k in sorted(LM)},open('lastmod.json','w'),indent=1)
open('site/robots.txt','w').write('User-agent: *\nAllow: /\n\nSitemap: '+SITE+'sitemap.xml\n')
print(len(GD['pages']),'guides')
