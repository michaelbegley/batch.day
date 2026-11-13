"""batch.recipes reader: turns recipe screenshots into plain text with a vision model.

The browser never sees the Hugging Face token; it lives in this Space's secrets.
"""
import os, time, base64
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

TOKEN = os.environ.get("HF_TOKEN", "")
MODELS = [m.strip() for m in os.environ.get(
    "MODELS", "Qwen/Qwen3-VL-235B-A22B-Instruct,Qwen/Qwen2.5-VL-32B-Instruct").split(",") if m.strip()]
ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://batch.recipes,https://www.batch.recipes,https://michaelbegley.github.io").split(",") if o.strip()]
PER_HOUR = int(os.environ.get("PER_VISITOR_PER_HOUR", "10"))
PER_DAY = int(os.environ.get("DAILY_CAP", "300"))
MAX_IMAGES = 6
MAX_IMAGE_BYTES = 1_500_000

PROMPT = (
    "These are screenshots of one recipe, possibly overlapping. Transcribe the recipe as plain text.\n"
    "Rules:\n"
    "- First line: the recipe title. Then the servings or yield line if shown.\n"
    "- Keep section headers (like 'Sauce' or 'For the rice') on their own line.\n"
    "- One ingredient per line, copying every amount and unit exactly. Write fractions as ½ ¼ ¾ ⅓ ⅔ ⅛.\n"
    "- Then the steps, numbered 1. 2. 3.\n"
    "- Merge overlapping screenshots and drop repeated lines.\n"
    "- If the screenshots hold more than one recipe, put a line of three dashes (---) between recipes.\n"
    "- Leave out hashtags, @mentions and captions that are not part of the recipe.\n"
    "- Do not add, guess or change anything. No commentary.\n"
    "- If there is no recipe, reply with exactly NO_RECIPE."
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["POST", "GET"], allow_headers=["Content-Type"], max_age=86400)

hits = defaultdict(deque)          # visitor -> request times (last hour)
day = {"date": "", "count": 0}     # whole-site daily cap (resets on restart too)


def visitor(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (req.client.host if req.client else "?")


def err(code: int, msg: str):
    return JSONResponse({"error": msg}, status_code=code)


@app.get("/")
def health():
    return {"ok": True, "ready": bool(TOKEN)}


@app.post("/read")
async def read(req: Request):
    if req.headers.get("origin", "") not in ORIGINS:
        return err(403, "Not allowed from this site.")
    if not TOKEN:
        return err(503, "The AI reader isn't set up yet.")

    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    if day["date"] != today:
        day.update(date=today, count=0)
    if day["count"] >= PER_DAY:
        return err(429, "The AI reader is busy today. Try again tomorrow, or paste the text.")
    q = hits[visitor(req)]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= PER_HOUR:
        return err(429, "That's a lot of reading. Try again in a bit.")

    try:
        body = await req.json()
        images = body.get("images", [])
    except Exception:
        return err(400, "Couldn't read that request.")
    if not isinstance(images, list) or not 1 <= len(images) <= MAX_IMAGES:
        return err(400, f"Send 1 to {MAX_IMAGES} screenshots.")
    parts = [{"type": "text", "text": PROMPT}]
    for im in images:
        if not isinstance(im, str) or not im.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
            return err(400, "Screenshots must be images.")
        try:
            size = len(base64.b64decode(im.split(",", 1)[1], validate=True))
        except Exception:
            return err(400, "That image looks broken.")
        if size > MAX_IMAGE_BYTES:
            return err(413, "That screenshot is too big.")
        parts.append({"type": "image_url", "image_url": {"url": im}})

    q.append(now)
    day["count"] += 1
    last = "unknown"
    async with httpx.AsyncClient(timeout=90) as client:
        for model in MODELS:
            try:
                r = await client.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                    json={"model": model, "messages": [{"role": "user", "content": parts}],
                          "temperature": 0, "max_tokens": 1800},
                )
                if r.status_code == 200:
                    text = (r.json()["choices"][0]["message"]["content"] or "").strip()
                    if text.startswith("```"):
                        text = text.strip("`").split("\n", 1)[-1]
                    if text == "NO_RECIPE" or not text:
                        return err(422, "No recipe found in those screenshots.")
                    return {"text": text, "model": model}
                last = f"{model}: {r.status_code}"
            except Exception as e:  # try the next model
                last = f"{model}: {type(e).__name__}"
    print("all models failed:", last, flush=True)
    return err(502, "The AI reader couldn't read it right now. Paste the text instead.")
