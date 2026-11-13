import os
READER=(open('reader.txt').read().strip() if os.path.exists('reader.txt') else '')  # e.g. https://user-space.hf.space
t=open('template.html').read().replace('/*READER*/',READER); e=open('engine.js').read()
open('site/index.html','w').write(t.replace('/*ENGINE*/',e))
open('site/favicon.svg','w').write('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><style>path{stroke:#d9480f}@media(prefers-color-scheme:dark){path{stroke:#ff7a3d}}</style><g fill="none" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 26h48"/><path d="M12 26v18a8 8 0 0 0 8 8h24a8 8 0 0 0 8-8V26"/><path d="M24 16c-2-3 2-5 0-8M40 16c-2-3 2-5 0-8"/></g></svg>''')
open('site/404.html','w').write('<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/"><title>batch.recipes</title>')
open('site/CNAME','w').write('batch.recipes\n')
open('site/.nojekyll','w').write('')
G='https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com https://*.gstatic.com https://*.googletagservices.com https://*.adtrafficquality.google https://*.googleadservices.com'
# CSP with script hashes (recompute on every build)
import re, hashlib, base64
h=open('site/index.html').read()
hashes=["'sha256-"+base64.b64encode(hashlib.sha256(m.encode()).digest()).decode()+"'" for m in re.findall(r'<script>(.*?)</script>', h, re.S)]
csp=("default-src 'self'; script-src 'self' "+' '.join(hashes)+" https://cdn.jsdelivr.net 'wasm-unsafe-eval' https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com https://*.gstatic.com https://*.googletagservices.com https://*.adtrafficquality.google https://*.googleadservices.com; worker-src blob: https://cdn.jsdelivr.net; "
     "connect-src 'self' https://cdn.jsdelivr.net "+G+(" "+READER if READER else "")+"; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: "+G+"; frame-src "+G+"; fenced-frame-src "+G+"; font-src 'self'; "
     "base-uri 'none'; object-src 'none'; form-action 'none'; upgrade-insecure-requests")
h=h.replace('<meta charset="utf-8">','<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="'+csp+'">\n<meta name="referrer" content="strict-origin-when-cross-origin">',1)
open('site/index.html','w').write(h)
print(len(hashes),'script hashes')
import json
json.dump({"name":"batch.recipes","short_name":"batch.recipes","description":"Cook once. Eat all week.","start_url":"./","scope":"./","display":"standalone","background_color":"#ffffff","theme_color":"#ffffff",
 "icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png"},{"src":"icon-512.png","sizes":"512x512","type":"image/png"},{"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},open('site/manifest.webmanifest','w'),indent=1)

s=open('pages/_shell.html').read()
for n,t_,d in [('privacy','Privacy','How batch.recipes handles your recipes, screenshots and ads.'),('about','About','What batch.recipes is and who makes it.')]:
    open(f'site/{n}.html','w').write(s.replace('{{TITLE}}',t_).replace('{{DESC}}',d).replace('{{BODY}}',open(f'pages/{n}.body').read()))
