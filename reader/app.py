"""batch.recipes reader: turns recipe screenshots, video frames and sound, and YouTube links into plain recipe text.

/read   screenshots            -> vision model (Hugging Face Inference Providers)
/watch  frames + sound + caption from a video the cook picked. The video file itself never comes here.
        sound -> speech to text, then one vision call with the frames, the transcript and the caption
/link   a YouTube link -> YouTube Data API (description), then Gemini's YouTube input if the description has no recipe.
        Off (503) until GOOGLE_API_KEY is set. No other site is ever fetched, and never a URL a visitor gave us.

The browser never sees the Hugging Face token or the Google key; they live in this Space's secrets.
Nothing is stored. Logs hold counts only: never images, sound, transcripts, captions, links or recipe text.
"""
import os, re, json, time, base64, struct, ipaddress
from urllib.parse import urlparse, parse_qs
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

TOKEN = os.environ.get("HF_TOKEN", "")
MODELS = [m.strip() for m in os.environ.get(
    "MODELS", "Qwen/Qwen3-VL-30B-A3B-Instruct,Qwen/Qwen3-VL-235B-A22B-Instruct,Qwen/Qwen2.5-VL-32B-Instruct").split(",") if m.strip()]
ORIGINS = [o.strip() for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://batch.recipes,https://www.batch.recipes").split(",") if o.strip()]
PER_HOUR = int(os.environ.get("PER_VISITOR_PER_HOUR", "10"))
PER_DAY = int(os.environ.get("DAILY_CAP", "300"))
MAX_IMAGES = 6
MAX_IMAGE_BYTES = 1_500_000

PROMPT = (
    "These are screenshots of one recipe, possibly overlapping. Transcribe the recipe as plain text.\n"
    "A list of ingredients with amounts counts as a recipe, even with no title, no steps, or the steps cut off.\n"
    "Rules:\n"
    "- First line: the recipe title if one is shown; if not, skip it and start with the ingredients. Then the servings or yield line if shown.\n"
    "- Keep section headers (like 'Sauce' or 'For the rice') on their own line.\n"
    "- One ingredient per line, copying every amount and unit exactly. Write fractions as ½ ¼ ¾ ⅓ ⅔ ⅛.\n"
    "- Then the steps, numbered 1. 2. 3., if any are shown.\n"
    "- Merge overlapping screenshots and drop repeated lines.\n"
    "- If the screenshots hold more than one recipe, put a line of three dashes (---) between recipes.\n"
    "- Ignore ads, buttons, ratings, prep and cook times, hashtags, @mentions and captions that are not part of the recipe.\n"
    "- Do not add, guess or change anything. No commentary.\n"
    "- Only if there are no ingredients at all, reply with exactly NO_RECIPE."
)


def _int(name, default):
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _list(name, default):
    return [m.strip() for m in os.environ.get(name, default).split(",") if m.strip()]


# ---- video (/watch). Every number is a Space variable so it can be changed without a deploy.
VIDEO_ON = os.environ.get("VIDEO", "on").strip().lower() not in ("off", "0", "false", "no")   # kill switch for /watch and /link
VIDEO_PER_HOUR = _int("VIDEO_PER_VISITOR_PER_HOUR", 3)
VIDEO_PER_DAY = _int("VIDEO_DAILY_CAP", 100)
MAX_AUDIO_SECONDS = _int("MAX_AUDIO_SECONDS", 180)
MAX_FRAMES = _int("MAX_FRAMES", 8)
MAX_AUDIO_BYTES = _int("MAX_AUDIO_BYTES", 6_000_000)
MAX_CAPTION_CHARS = 3000
STT_MODELS = _list("STT_MODELS", "openai/whisper-large-v3-turbo,openai/whisper-large-v3")
# {model} is replaced by each name in STT_MODELS. The sound goes as raw WAV bytes (Content-Type: audio/wav) and the
# answer is JSON {"text": "..."}: the documented automatic-speech-recognition call. To use one provider instead of
# HF Inference, set e.g. STT_URL=https://router.huggingface.co/fal-ai/models/{model} (check the route live first).
STT_URL = os.environ.get("STT_URL", "").strip() or "https://router.huggingface.co/hf-inference/models/{model}"
TEXT_MODELS = _list("TEXT_MODELS", ",".join(MODELS))   # reads a YouTube description (text only)

# ---- YouTube links (/link). Off until GOOGLE_API_KEY exists.
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash-lite"
GEMINI_URL = os.environ.get("GEMINI_URL", "").strip() or "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LINK_PER_HOUR = _int("LINK_PER_VISITOR_PER_HOUR", 5)
LINK_PER_DAY = _int("LINK_DAILY_CAP", 200)
MAX_YOUTUBE_SECONDS = _int("MAX_YOUTUBE_SECONDS", 1200)
MAX_BODY_BYTES = 2_000_000 * MAX_FRAMES + (MAX_AUDIO_BYTES * 4) // 3 + 200_000   # frames and sound as base64, with room to spare

RULES = (
    "- First line: the dish name if it is said or shown; if not, skip it. Then 'Serves N' only if it is said or shown.\n"
    "- Keep section headers (like 'Sauce' or 'For the rice') on their own line.\n"
    "- One ingredient per line. Copy every amount and unit exactly as said or shown. Write fractions as ½ ¼ ¾ ⅓ ⅔ ⅛.\n"
    "- If an ingredient is used but no amount is said or shown, write the ingredient name and then the cook's own word in brackets, "
    "like 'soy sauce (a splash)' or 'olive oil (a drizzle)'. If there is no such word, write only the name. Never invent a number.\n"
    "- Then the steps, numbered 1. 2. 3., short, in plain words, in the order they happen. Do not copy the narration word for word.\n"
    "- Drop greetings, sponsor reads, 'link in bio', hashtags, @mentions and story.\n"
    "- Do not add, guess or change any amount. No commentary.\n"
    "- Only if there are no ingredients at all, reply with exactly NO_RECIPE."
)
VIDEO_PROMPT = (
    "You get still frames, a speech transcript and maybe a caption, all from one cooking video. Write the recipe as plain text.\n"
    "A list of ingredients counts as a recipe, even with no title and no steps.\n"
    "Rules:\n" + RULES + "\n"
    "- If the on-screen text and the speech disagree on an amount, use the on-screen text.\n"
    "- Speech to text makes mistakes, and may invent words over music or silence. Do not fix an amount by guessing. "
    "If a word is clearly a misheard food ('time' for 'thyme'), fix the food word only.\n"
    "- Ignore app buttons, usernames, like counts and comments in the frames.\n"
    "- After the recipe, add one last line that says where the recipe came from, exactly one of: "
    "USED: speech, USED: screen, USED: caption, USED: mix."
)
TEXT_PROMPT = (
    "This is the title and description of one cooking video. Write the recipe that is in it as plain text.\n"
    "A list of ingredients with amounts counts as a recipe, even with no steps.\n"
    "Rules:\n" + RULES + "\n"
    "- If the description holds no ingredient list (only a story, links or a teaser), reply with exactly NO_RECIPE."
)
LINK_PROMPT = (
    "Watch and listen to this cooking video. Write the recipe as plain text.\n"
    "Rules:\n" + RULES + "\n"
    "- If the on-screen text and the speech disagree on an amount, use the on-screen text."
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["POST", "GET"], allow_headers=["Content-Type"], max_age=86400)

# Counters live in memory and reset when the Space restarts. Each kind of read has its own.
LIMITS = {
    "read": {"hour": PER_HOUR, "day": PER_DAY},
    "video": {"hour": VIDEO_PER_HOUR, "day": VIDEO_PER_DAY},
    "link": {"hour": LINK_PER_HOUR, "day": LINK_PER_DAY},
}
hits = {k: defaultdict(deque) for k in LIMITS}             # kind -> visitor -> request times (last hour)
days = {k: {"date": "", "count": 0} for k in LIMITS}       # kind -> whole-site daily cap
day = days["read"]                                         # old name, kept for anything that reads it


def _public(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip.strip().strip("[]"))
    except ValueError:
        return False
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast or a.is_unspecified)


def visitor(req: Request) -> str:
    """The visitor's address for the per-visitor limit.

    A Space sits behind Hugging Face's proxy, so the socket address is the proxy's. The proxy adds the address it saw to
    the END of X-Forwarded-For; anything a script puts in that header itself ends up to the LEFT of it. So read from the
    right and take the first public address: values on the left can be faked, the one the proxy appended cannot.
    (Before 15 Nov 2026 this took the first value, which any script could change on every call to dodge the limit.)
    If the header holds no public address, fall back to the socket address.
    """
    for part in reversed(req.headers.get("x-forwarded-for", "").split(",")):
        if _public(part):
            return part.strip()
    return req.client.host if req.client else "?"


def err(code: int, msg: str, why: str = ""):
    """why: a short word the page uses to pick its own message (limit, busy, off, private, toolong, none)."""
    return JSONResponse({"error": msg, "why": why} if why else {"error": msg}, status_code=code)


def gate(kind: str, req: Request, busy: str, lots: str):
    """Daily cap, then per-visitor cap. Returns (error or None, the visitor's queue, now)."""
    now = time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    d = days[kind]
    if d["date"] != today:
        d.update(date=today, count=0)
        for v in [v for v, q in hits[kind].items() if not q or now - q[-1] > 3600]:   # forget visitors from over an hour ago
            del hits[kind][v]
    if d["count"] >= LIMITS[kind]["day"]:
        return err(429, busy, "busy"), None, now
    q = hits[kind][visitor(req)]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= LIMITS[kind]["hour"]:
        return err(429, lots, "limit"), None, now
    return None, q, now


def spend(kind: str, q, now):
    q.append(now)
    days[kind]["count"] += 1


async def body_json(req: Request, cap: int):
    """The request body as JSON, refused before it is read whole if it is bigger than cap."""
    try:
        if int(req.headers.get("content-length", "0") or 0) > cap:
            return None, err(413, "That's too much to send.")
    except ValueError:
        return None, err(400, "Couldn't read that request.")
    buf = bytearray()
    try:
        async for chunk in req.stream():
            buf += chunk
            if len(buf) > cap:
                return None, err(413, "That's too much to send.")
        data = json.loads(bytes(buf))
    except Exception:
        return None, err(400, "Couldn't read that request.")
    if not isinstance(data, dict):
        return None, err(400, "Couldn't read that request.")
    return data, None


IMG = ("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")


def clean(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1].strip()
    return text


def no_recipe(text: str) -> bool:
    return not text or text.strip(" .`*").upper() == "NO_RECIPE"


async def chat(client, models, parts):
    """One chat call through the Hugging Face router, trying each model in turn. Returns (text or None, model, last error)."""
    last = "unknown"
    for model in models:
        try:
            r = await client.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={"Authorization": f"Bearer {TOKEN}"},
                json={"model": model, "messages": [{"role": "user", "content": parts}], "temperature": 0, "max_tokens": 1800},
            )
            if r.status_code == 200:
                return clean(r.json()["choices"][0]["message"]["content"]), model, ""
            last = f"{model}: {r.status_code}"
        except Exception as e:  # try the next model
            last = f"{model}: {type(e).__name__}"
    return None, "", last


@app.get("/")
def health(req: Request):
    # proxy check without showing any address: how many public hops the proxy chain carries, and whether the
    # per-visitor key is the left-most one (if not, the proxy appends a public hop of its own and the limiter
    # would lump visitors together)
    pub = [p.strip() for p in req.headers.get("x-forwarded-for", "").split(",") if _public(p)]
    return {"ok": True, "ready": bool(TOKEN), "video": bool(TOKEN) and VIDEO_ON, "links": bool(GOOGLE_KEY) and VIDEO_ON,
            "hops": len(pub), "first": bool(pub) and visitor(req) == pub[0]}


@app.post("/read")
async def read(req: Request):
    if req.headers.get("origin", "") not in ORIGINS:
        return err(403, "Not allowed from this site.")
    if not TOKEN:
        return err(503, "The AI reader isn't set up yet.")
    stop, q, now = gate("read", req, "The AI reader is busy today. Try again tomorrow, or paste the text.", "That's a lot of reading. Try again in a bit.")
    if stop:
        return stop

    try:
        body = await req.json()
        images = body.get("images", [])
    except Exception:
        return err(400, "Couldn't read that request.")
    if not isinstance(images, list) or not 1 <= len(images) <= MAX_IMAGES:
        return err(400, f"Send 1 to {MAX_IMAGES} screenshots.")
    parts = [{"type": "text", "text": PROMPT}]
    for im in images:
        if not isinstance(im, str) or not im.startswith(IMG):
            return err(400, "Screenshots must be images.")
        try:
            size = len(base64.b64decode(im.split(",", 1)[1], validate=True))
        except Exception:
            return err(400, "That image looks broken.")
        if size > MAX_IMAGE_BYTES:
            return err(413, "That screenshot is too big.")
        parts.append({"type": "image_url", "image_url": {"url": im}})

    spend("read", q, now)
    async with httpx.AsyncClient(timeout=90) as client:
        text, model, last = await chat(client, MODELS, parts)
    if text is None:
        print("all models failed:", last, flush=True)
        return err(502, "The AI reader couldn't read it right now. Paste the text instead.")
    if no_recipe(text):
        print("no recipe:", model, len(images), "images", flush=True)   # counts only, never the images or text
        return err(422, "No recipe found in those screenshots.")
    return {"text": text, "model": model}


# ---------------------------------------------------------------- /watch: frames and sound from the cook's own video

def wav_seconds(b: bytes):
    """Length of a PCM WAV in seconds, or None if it isn't one."""
    if len(b) < 44 or b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        return None
    i, rate, data = 12, 0, None
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if tag == b"fmt " and i + 20 <= len(b):
            rate = struct.unpack("<I", b[i + 16:i + 20])[0]   # bytes per second
        elif tag == b"data":
            data = min(size, len(b) - i - 8)
            break
        i += 8 + size + (size & 1)
    if not rate or data is None:
        return None
    return data / rate


async def transcribe(client, audio: bytes):
    """Speech to text. Returns (text, model) or (None, last error)."""
    last = "unknown"
    for model in STT_MODELS:
        try:
            r = await client.post(STT_URL.replace("{model}", model),
                                  headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "audio/wav"}, content=audio)
            if r.status_code == 200:
                j = r.json()
                t = j.get("text") if isinstance(j, dict) else None
                if isinstance(t, str):
                    return t.strip(), model
                last = f"{model}: no text"
            else:
                last = f"{model}: {r.status_code}"
        except Exception as e:
            last = f"{model}: {type(e).__name__}"
    return None, last


USED_RE = re.compile(r"\n?\s*\**USED:\**\s*(speech|screen|caption|mix)\b[^\n]*\s*$", re.I)
V_BUSY = "The video reader is busy today. Try again tomorrow, or add screenshots."
V_LOTS = "That's a lot of videos. Try again in a bit, or add screenshots."
V_DOWN = "The video reader couldn't read it right now. Add screenshots instead."
V_NONE = "No recipe found in that video."


@app.post("/watch")
async def watch(req: Request):
    if req.headers.get("origin", "") not in ORIGINS:
        return err(403, "Not allowed from this site.")
    if not VIDEO_ON:
        return err(429, V_BUSY, "busy")
    if not TOKEN:
        return err(503, "The video reader isn't set up yet.", "off")
    stop, q, now = gate("video", req, V_BUSY, V_LOTS)
    if stop:
        return stop

    body, bad = await body_json(req, MAX_BODY_BYTES)
    if bad:
        return bad
    frames, audio, caption = body.get("frames", []), body.get("audio"), body.get("caption", "")
    if not isinstance(frames, list) or not 1 <= len(frames) <= MAX_FRAMES:
        return err(400, f"Send 1 to {MAX_FRAMES} frames.")
    for im in frames:
        if not isinstance(im, str) or not im.startswith(IMG):
            return err(400, "Frames must be images.")
        try:
            size = len(base64.b64decode(im.split(",", 1)[1], validate=True))
        except Exception:
            return err(400, "That frame looks broken.")
        if size > MAX_IMAGE_BYTES:
            return err(413, "That frame is too big.")
    sound = None
    if audio not in (None, ""):
        if not isinstance(audio, str):
            return err(400, "The sound must be WAV.")
        if audio.startswith("data:"):
            if not audio.startswith(("data:audio/wav;base64,", "data:audio/x-wav;base64,", "data:audio/wave;base64,")):
                return err(400, "The sound must be WAV.")
            audio = audio.split(",", 1)[1]
        if len(audio) > (MAX_AUDIO_BYTES * 4) // 3 + 8:
            return err(413, "That sound clip is too big.")
        try:
            sound = base64.b64decode(audio, validate=True)
        except Exception:
            return err(400, "That sound clip looks broken.")
        if len(sound) > MAX_AUDIO_BYTES:
            return err(413, "That sound clip is too big.")
        secs = wav_seconds(sound)
        if secs is None:
            return err(400, "The sound must be WAV.")
        if secs > MAX_AUDIO_SECONDS + 1:
            return err(413, "That sound clip is too long.")
    if caption is None:
        caption = ""
    if not isinstance(caption, str):
        return err(400, "The caption must be text.")
    caption = caption.strip()[:MAX_CAPTION_CHARS]

    spend("video", q, now)
    async with httpx.AsyncClient(timeout=90) as client:
        transcript, heard = "", "none"
        if sound:
            t, info = await transcribe(client, sound)
            if t is None:
                heard = "failed"
                print("speech failed:", info, flush=True)
            else:
                transcript, heard = t[:12000], ("yes" if len(t.split()) >= 3 else "empty")
        said = transcript if heard == "yes" else ""
        text_part = (VIDEO_PROMPT + "\n\nSpeech transcript:\n" + (said or "(no speech)")
                     + "\n\nCaption:\n" + (caption or "(no caption)"))
        parts = [{"type": "text", "text": text_part}] + [{"type": "image_url", "image_url": {"url": im}} for im in frames]
        text, model, last = await chat(client, MODELS, parts)
    if text is None:
        print("watch: all models failed:", last, flush=True)
        return err(502, V_DOWN)
    used = ""
    m = USED_RE.search(text)
    if m:
        used, text = m.group(1).lower(), text[:m.start()].rstrip()
    if no_recipe(text):
        print("watch: no recipe:", model, len(frames), "frames, speech", heard, flush=True)   # counts only
        if heard == "failed":   # we never heard it, so "no recipe" would be a guess
            return err(502, V_DOWN)
        return err(422, V_NONE, "none")
    if not said and not caption:
        used = "screen"
    elif not used or (used in ("speech", "mix") and not said) or (used == "caption" and not caption):
        used = "mix" if said else "screen"
    print("watch ok:", model, len(frames), "frames, speech", heard, "used", used, flush=True)       # counts only
    return {"text": text, "model": model, "used": used, "speech": heard}


# ---------------------------------------------------------------- /link: YouTube only, through Google's own APIs

YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
L_BUSY = "The video reader is busy today. Try again tomorrow, or add screenshots."
L_LOTS = "That's a lot of videos. Try again in a bit, or add screenshots."
L_OFF = "YouTube links aren't on yet. Add the video or screenshots."
L_PRIVATE = "That video is private. Add screenshots or paste the recipe."
L_LONG = "That video is too long to read from a link. Add screenshots or paste the recipe."


def youtube_id(url):
    """The 11-character video id from a youtube.com or youtu.be link, or None. Nothing else is accepted."""
    if not isinstance(url, str) or len(url) > 300:
        return None
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    try:
        u = urlparse(url)
        host = (u.hostname or "").lower()
    except ValueError:
        return None
    if u.scheme.lower() not in ("http", "https") or host not in YT_HOSTS or u.username or u.password or u.port not in (None, 80, 443):
        return None
    seg = [s for s in u.path.split("/") if s]
    vid = None
    if host.endswith("youtu.be"):
        vid = seg[0] if seg else None
    elif seg and seg[0] == "watch":
        vid = (parse_qs(u.query).get("v") or [None])[0]
    elif len(seg) >= 2 and seg[0] in ("shorts", "embed", "live", "v"):
        vid = seg[1]
    return vid if vid and YT_ID.match(vid) else None


def iso_seconds(d):
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$", d or "")
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


AMOUNT = re.compile(r"^\s*[-•*·]?\s*(?:\d|[½¼¾⅓⅔⅛]|(?:a|one|two|three|half)\s+(?:cup|tbsp|tsp|pound|lb|can|clove)s?\b)", re.I)
UNIT = re.compile(r"\b(cups?|tbsp|tsp|tablespoons?|teaspoons?|oz|ounces?|lbs?|pounds?|g|grams?|kg|ml|l|cloves?|cans?|pinch|sticks?)\b", re.I)


def has_ingredients(text: str) -> bool:
    """A description with at least three lines that start with an amount, two of them with a unit."""
    lines = [l for l in (text or "").splitlines() if AMOUNT.match(l) and not re.match(r"^\s*\d{1,2}:\d{2}", l)]   # not chapter times
    return len(lines) >= 3 and sum(1 for l in lines if UNIT.search(l)) >= 2


def gemini_text(j) -> str:
    try:
        return "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"] if isinstance(p, dict))
    except Exception:
        pass
    try:   # the newer "interactions" shape, if GEMINI_URL is pointed at it
        return "".join(o.get("text", "") for o in j["outputs"] if isinstance(o, dict) and o.get("type") == "text")
    except Exception:
        return ""


@app.post("/link")
async def link(req: Request):
    if req.headers.get("origin", "") not in ORIGINS:
        return err(403, "Not allowed from this site.")
    if not VIDEO_ON:
        return err(429, L_BUSY, "busy")
    if not GOOGLE_KEY:
        return err(503, L_OFF, "off")
    stop, q, now = gate("link", req, L_BUSY, L_LOTS)
    if stop:
        return stop
    body, bad = await body_json(req, 4000)
    if bad:
        return bad
    vid = youtube_id(body.get("url"))
    if not vid:
        return err(400, "That isn't a YouTube link.", "badlink")
    watch_url = "https://www.youtube.com/watch?v=" + vid   # built here from the id; the visitor's URL is never fetched

    spend("link", q, now)
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            r = await client.get("https://www.googleapis.com/youtube/v3/videos",
                                 params={"part": "snippet,contentDetails,status", "id": vid, "maxResults": 1},
                                 headers={"X-Goog-Api-Key": GOOGLE_KEY})
        except Exception as e:
            print("link: youtube failed:", type(e).__name__, flush=True)
            return err(502, V_DOWN)
        if r.status_code != 200:
            print("link: youtube status", r.status_code, flush=True)
            return err(502, V_DOWN)
        try:
            items = r.json().get("items") or []
        except Exception:
            items = []
        if not items:
            return err(404, L_PRIVATE, "private")   # private, deleted or never existed: the API shows none of them
        it = items[0]
        sn, cd, st = it.get("snippet") or {}, it.get("contentDetails") or {}, it.get("status") or {}
        creator = str(sn.get("channelTitle") or "")[:100]
        out = {"creator": creator, "url": watch_url}
        desc, title = str(sn.get("description") or ""), str(sn.get("title") or "")
        if has_ingredients(desc):
            text, model, last = await chat(client, TEXT_MODELS, [{"type": "text", "text": TEXT_PROMPT + "\n\nTitle: " + title[:200] + "\n\nDescription:\n" + desc[:6000]}])
            if text is not None and not no_recipe(text):
                print("link ok: description,", model, flush=True)   # counts only
                return {"text": text, "model": model, "used": "caption", **out}
        if st.get("privacyStatus") not in (None, "public"):
            return err(404, L_PRIVATE, "private")   # Gemini reads public videos only
        secs = iso_seconds(cd.get("duration"))
        if secs <= 0 or secs > MAX_YOUTUBE_SECONDS or sn.get("liveBroadcastContent") in ("live", "upcoming"):
            return err(413, L_LONG, "toolong")
        try:
            g = await client.post(GEMINI_URL.replace("{model}", GEMINI_MODEL), headers={"x-goog-api-key": GOOGLE_KEY},
                                  json={"contents": [{"parts": [{"file_data": {"file_uri": watch_url}}, {"text": LINK_PROMPT}]}],
                                        "generationConfig": {"temperature": 0, "maxOutputTokens": 1800}})
        except Exception as e:
            print("link: gemini failed:", type(e).__name__, flush=True)
            return err(502, V_DOWN)
        if g.status_code != 200:
            print("link: gemini status", g.status_code, flush=True)
            return err(429, L_BUSY, "busy") if g.status_code == 429 else err(502, V_DOWN)
        try:
            text = clean(gemini_text(g.json()))
        except Exception:
            text = ""
    if no_recipe(text):
        print("link: no recipe", flush=True)
        return err(422, V_NONE, "none")
    print("link ok: watched,", GEMINI_MODEL, flush=True)
    return {"text": text, "model": GEMINI_MODEL, "used": "mix", **out}
