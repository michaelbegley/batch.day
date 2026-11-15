import os
READER=(open('reader.txt').read().strip() if os.path.exists('reader.txt') else '')  # e.g. https://user-space.hf.space
t=open('template.html').read().replace('/*READER*/',READER); e=open('engine.js').read()+'\n'+open('qr.js').read()  # the label QR encoder rides in the same inline script as the engine
open('site/index.html','w').write(t.replace('/*ENGINE*/',e))
open('site/favicon.svg','w').write('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="1.804 0.804 52.391 52.391"><style>g{stroke:#c2410c}@media(prefers-color-scheme:dark){g{stroke:#ff7a3d}}</style><g fill="none" stroke="#c2410c" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 16c-2-3 2-5 0-8"/><path d="M28 16c-2-3 2-5 0-8"/><path d="M36 16c-2-3 2-5 0-8"/><path d="M10 24h36"/><path d="M13 24v16a6 6 0 0 0 6 6h18a6 6 0 0 0 6-6V24"/><path d="M6 28h7M43 28h7"/></g></svg>''')  # from /home/claude/brand/mark.py: the one 3-steam pot
open('site/404.html','w').write('<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/"><title>batch.recipes</title>')
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

s=open('pages/_shell.html').read()
for n,t_,d in [('privacy','Privacy','How batch.recipes handles your recipes, screenshots and ads.'),('about','About','What batch.recipes is and who makes it.')]:
    open(f'site/{n}.html','w').write(s.replace('{{TITLE}}',t_).replace('{{DESC}}',d).replace('{{BODY}}',open(f'pages/{n}.body').read()))
