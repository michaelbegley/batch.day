# batch.day

Cook once, eat all week. Drop in a recipe screenshot or paste it, and get the whole batch day: what to buy, which pot, what to cook first, and what goes in the freezer.

- One page: `index.html` (engine inlined). Built from `template.html` + `engine.js` in the working folder.
- Screenshots are read in the browser with Tesseract.js (loaded from jsDelivr). Nothing is uploaded.
- Editing a `<script>` block means the Content-Security-Policy hashes in `<head>` must be recomputed, or that script stops running.
- Source: `src/` (run `python3 build.py` from a folder holding `template.html`, `engine.js` and a `site/` folder).
