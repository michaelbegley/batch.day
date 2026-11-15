"""Checks for app.py with no network: every outside call is faked. Run: python3 test_app.py
No pytest needed. Exit code 1 if anything fails."""
import os, sys, io, json, base64, struct, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fastapi.testclient import TestClient

PASS = FAIL = 0
def ok(c, name, note=""):
    global PASS, FAIL
    if c: PASS += 1
    else:
        FAIL += 1; print("FAIL", name, str(note)[:300], flush=True)

O = {"Origin": "https://batch.recipes"}
PNG = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")).decode()
def wav(seconds=1.0, rate=16000):
    n = int(seconds * rate) * 2
    return b"RIFF" + struct.pack("<I", 36 + n) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", n) + b"\0" * n
def b64(b): return base64.b64encode(b).decode()
RECIPE = "Garlic rice\nServes 4\n2 cups rice\n3 cloves garlic\nsoy sauce (a splash)\n1. Cook the rice.\n2. Fry the garlic."

class Resp:
    def __init__(self, status=200, data=None): self.status_code = status; self._d = data
    def json(self):
        if self._d is None: raise ValueError("no json")
        return self._d

class Fake:
    """Stands in for httpx.AsyncClient. calls: every outside request made. plan: url substring -> list of responses (used in turn; the last repeats)."""
    calls = []; plan = {}
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    def _answer(self, method, url, **k):
        Fake.calls.append({"method": method, "url": url, **k})
        for key, seq in Fake.plan.items():
            if key in url:
                r = seq.pop(0) if len(seq) > 1 else seq[0]
                if isinstance(r, Exception): raise r
                return r
        raise AssertionError("unplanned outside call: " + url)
    async def post(self, url, **k): return self._answer("POST", url, **k)
    async def get(self, url, **k): return self._answer("GET", url, **k)

def chat(text): return Resp(200, {"choices": [{"message": {"content": text}}]})
def yt(desc="", dur="PT1M", privacy="public", title="Garlic rice", channel="Test Kitchen", live="none"):
    return Resp(200, {"items": [{"snippet": {"title": title, "description": desc, "channelTitle": channel, "liveBroadcastContent": live},
                                 "contentDetails": {"duration": dur}, "status": {"privacyStatus": privacy}}]})
def gem(text): return Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})

ENV_KEYS = ["HF_TOKEN", "GOOGLE_API_KEY", "VIDEO", "VIDEO_PER_VISITOR_PER_HOUR", "VIDEO_DAILY_CAP", "MAX_AUDIO_SECONDS", "MAX_FRAMES", "MAX_AUDIO_BYTES",
            "STT_MODELS", "STT_URL", "LINK_PER_VISITOR_PER_HOUR", "LINK_DAILY_CAP", "MAX_YOUTUBE_SECONDS", "GEMINI_MODEL", "GEMINI_URL", "PER_VISITOR_PER_HOUR", "DAILY_CAP", "ALLOWED_ORIGINS", "MODELS", "TEXT_MODELS"]
def load(**env):
    """a fresh copy of the app with these Space variables and nothing else"""
    for k in ENV_KEYS: os.environ.pop(k, None)
    os.environ.update({k: str(v) for k, v in env.items()})
    import app as A
    A = importlib.reload(A)
    A.httpx.AsyncClient = Fake
    Fake.calls = []; Fake.plan = {}
    return A, TestClient(A.app)
def stt_calls(): return [c for c in Fake.calls if "/models/" in c["url"] and "router.huggingface.co" in c["url"] and "chat/completions" not in c["url"]]
def chat_calls(): return [c for c in Fake.calls if "chat/completions" in c["url"]]

# ---------- health, and /read is as it was
A, c = load(HF_TOKEN="hf_test")
ok({k: v for k, v in c.get("/").json().items() if k not in ("hops", "first")} == {"ok": True, "ready": True, "video": True, "links": False}, "health: video on, links off without the Google key", c.get("/").json())
Fake.plan = {"chat/completions": [chat(RECIPE)]}
r = c.post("/read", json={"images": [PNG]}, headers=O)
ok(r.status_code == 200 and r.json() == {"text": RECIPE, "model": A.MODELS[0]}, "/read still answers {text, model}", r.text)
ok(c.post("/read", json={"images": [PNG]}).status_code == 403, "/read: no origin is refused")
ok(c.post("/read", json={"images": []}, headers=O).status_code == 400, "/read: no images is 400")
Fake.plan = {"chat/completions": [chat("NO_RECIPE")]}
ok(c.post("/read", json={"images": [PNG]}, headers=O).status_code == 422, "/read: NO_RECIPE is 422")

# ---------- /watch: origin, missing token, kill switch
for h, n in [({}, "no origin"), ({"Origin": "https://evil.example"}, "another site"), ({"Origin": "https://batch.recipes.evil.example"}, "a lookalike origin"), ({"Origin": "http://batch.recipes"}, "http origin")]:
    r = c.post("/watch", json={"frames": [PNG]}, headers=h); ok(r.status_code == 403, "/watch: " + n + " is refused", r.status_code)
    r = c.post("/link", json={"url": "https://youtu.be/dQw4w9WgXcQ"}, headers=h); ok(r.status_code == 403, "/link: " + n + " is refused", r.status_code)
ok(not Fake.calls[2:], "refused requests made no outside call", Fake.calls[2:])
ok(c.options("/watch", headers={**O, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}).headers.get("access-control-allow-origin") == "https://batch.recipes", "CORS preflight allows batch.recipes")
ok("access-control-allow-origin" not in c.options("/watch", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}).headers, "CORS preflight does not allow another site")

A, c = load()
r = c.post("/watch", json={"frames": [PNG]}, headers=O); ok(r.status_code == 503 and r.json().get("why") == "off", "/watch: 503 without HF_TOKEN", r.text)
r = c.post("/read", json={"images": [PNG]}, headers=O); ok(r.status_code == 503, "/read: 503 without HF_TOKEN")
r = c.post("/link", json={"url": "https://youtu.be/dQw4w9WgXcQ"}, headers=O)
ok(r.status_code == 503 and r.json() == {"error": "YouTube links aren't on yet. Add the video or screenshots.", "why": "off"}, "/link: 503 with the page's words without GOOGLE_API_KEY", r.text)
ok(not Fake.calls, "nothing was called outside with no keys", Fake.calls)

A, c = load(HF_TOKEN="hf_test")
r = c.post("/link", json={"url": "https://youtu.be/dQw4w9WgXcQ"}, headers=O); ok(r.status_code == 503 and r.json()["why"] == "off", "/link: 503 with HF_TOKEN but no Google key", r.text)

for off in ["off", "OFF", "0", "false"]:
    A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test", VIDEO=off)
    r = c.post("/watch", json={"frames": [PNG]}, headers=O)
    ok(r.status_code == 429 and r.json() == {"error": "The video reader is busy today. Try again tomorrow, or add screenshots.", "why": "busy"}, f"kill switch VIDEO={off}: /watch says busy today", r.text)
    r = c.post("/link", json={"url": "https://youtu.be/dQw4w9WgXcQ"}, headers=O); ok(r.status_code == 429 and r.json()["why"] == "busy", f"kill switch VIDEO={off}: /link says busy today", r.text)
    ok(not Fake.calls, "kill switch: nothing called outside")
    ok(c.get("/").json()["video"] is False and c.get("/").json()["links"] is False, "kill switch shows in health")
    Fake.plan = {"chat/completions": [chat(RECIPE)]}
    ok(c.post("/read", json={"images": [PNG]}, headers=O).status_code == 200, "kill switch leaves /read on")

# ---------- /watch: the happy path
A, c = load(HF_TOKEN="hf_test")
ok(A.STT_MODELS == ["openai/whisper-large-v3-turbo", "openai/whisper-large-v3"], "STT_MODELS default: turbo first", A.STT_MODELS)
ok(A.STT_URL == "https://router.huggingface.co/hf-inference/models/{model}", "STT_URL default is the hf-inference route", A.STT_URL)
ok((A.VIDEO_PER_HOUR, A.VIDEO_PER_DAY, A.MAX_AUDIO_SECONDS, A.MAX_FRAMES, A.MAX_AUDIO_BYTES, A.LINK_PER_HOUR, A.LINK_PER_DAY, A.MAX_YOUTUBE_SECONDS) == (3, 100, 180, 8, 6000000, 5, 200, 1200), "limit defaults")
W = wav(2)
Fake.plan = {"hf-inference/models": [Resp(200, {"text": "Two cups of rice and three cloves of garlic and a splash of soy sauce."})], "chat/completions": [chat(RECIPE + "\nUSED: mix")]}
r = c.post("/watch", json={"frames": [PNG, PNG], "audio": "data:audio/wav;base64," + b64(W), "caption": "garlic rice #rice"}, headers=O)
j = r.json()
ok(r.status_code == 200 and j["text"] == RECIPE and j["model"] == A.MODELS[0] and j["used"] == "mix", "/watch answers {text, model, used} and strips the USED line", r.text)
s = stt_calls()
ok(len(s) == 1 and s[0]["url"] == "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3-turbo", "speech goes to the turbo model on the hf-inference route", [x["url"] for x in s])
ok(s[0]["content"] == W and s[0]["headers"] == {"Authorization": "Bearer hf_test", "Content-Type": "audio/wav"}, "speech call: raw WAV bytes, audio/wav, bearer token")
cc = chat_calls()[0]["json"]; parts = cc["messages"][0]["content"]
ok(len(chat_calls()) == 1 and [p["type"] for p in parts] == ["text", "image_url", "image_url"], "one vision call: prompt, then the frames")
ok("Two cups of rice" in parts[0]["text"] and "garlic rice #rice" in parts[0]["text"] and "Never invent a number" in parts[0]["text"] and "soy sauce (a splash)" in parts[0]["text"], "the vision prompt holds the transcript, the caption and the never-invent rule")
ok(cc["temperature"] == 0, "temperature 0")

# bare base64 sound, no caption; the model forgot the USED line
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [Resp(200, {"text": "two cups rice three cloves garlic"})], "chat/completions": [chat("```\n" + RECIPE + "\n```")]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 200 and r.json()["text"] == RECIPE and r.json()["used"] == "mix", "/watch: bare base64 sound works; code fence stripped; used falls back to mix", r.text)

# no sound: frames only, no speech call
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"chat/completions": [chat(RECIPE + "\nUSED: speech")]}
r = c.post("/watch", json={"frames": [PNG]}, headers=O)
ok(r.status_code == 200 and r.json()["used"] == "screen" and r.json()["speech"] == "none" and not stt_calls(), "/watch with no sound: no speech call, used is screen whatever the model says", r.text)
ok("(no speech)" in chat_calls()[0]["json"]["messages"][0]["content"][0]["text"], "no sound: the prompt says there is no speech")

# speech model fallback, then both fail
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"whisper-large-v3-turbo": [Resp(503, {"error": "loading"})], "models/openai/whisper-large-v3": [Resp(200, {"text": "two cups of rice please"})], "chat/completions": [chat(RECIPE + "\nUSED: speech")]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 200 and r.json()["used"] == "speech" and [x["url"].rsplit("/", 1)[1] for x in stt_calls()] == ["whisper-large-v3-turbo", "whisper-large-v3"], "speech: the second model is tried when the first fails", r.text)
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [Resp(500, None)], "chat/completions": [chat(RECIPE + "\nUSED: screen")]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 200 and r.json()["used"] == "screen" and r.json()["speech"] == "failed", "speech down: the frames are still read", r.text)
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [RuntimeError("boom")], "chat/completions": [chat("NO_RECIPE")]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 502, "speech down and nothing on screen: an error, not 'no recipe'", r.text)
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [Resp(200, {"text": "la la la la la"})], "chat/completions": [chat("NO_RECIPE\nUSED: mix")]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 422 and r.json() == {"error": "No recipe found in that video.", "why": "none"}, "music only: 422 No recipe found", r.text)
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [Resp(200, {"text": "two cups rice ok"})], "chat/completions": [Resp(500, None)]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 502 and len(chat_calls()) == len(A.MODELS), "every vision model failing is a 502 after trying each", r.text)
# custom route and models
A, c = load(HF_TOKEN="hf_test", STT_URL="https://router.huggingface.co/fal-ai/models/{model}", STT_MODELS="openai/whisper-large-v3")
Fake.plan = {"fal-ai/models": [Resp(200, {"text": "two cups of rice"})], "chat/completions": [chat(RECIPE)]}
r = c.post("/watch", json={"frames": [PNG], "audio": b64(W)}, headers=O)
ok(r.status_code == 200 and stt_calls()[0]["url"] == "https://router.huggingface.co/fal-ai/models/openai/whisper-large-v3", "STT_URL and STT_MODELS variables are used", [x["url"] for x in stt_calls()])

# ---------- /watch: bad inputs (none of them reach a model or count against the limits)
A, c = load(HF_TOKEN="hf_test")
big_img = "data:image/jpeg;base64," + b64(b"\xff" * 1_500_001)
bad = [
    ({"frames": []}, 400, "no frames"), ({}, 400, "no frames key"), ({"frames": "x"}, 400, "frames not a list"), ({"frames": [PNG] * 9}, 400, "nine frames"),
    ({"frames": ["data:text/html;base64,PGI+"]}, 400, "a frame that is not an image"), ({"frames": [123]}, 400, "a frame that is a number"),
    ({"frames": ["data:image/png;base64,@@@"]}, 400, "a frame with broken base64"), ({"frames": [big_img]}, 413, "a frame over 1.5 MB"),
    ({"frames": [PNG], "audio": 5}, 400, "sound that is a number"), ({"frames": [PNG], "audio": "data:audio/mpeg;base64," + b64(W)}, 400, "sound that is not WAV by type"),
    ({"frames": [PNG], "audio": b64(b"ID3" + b"\0" * 100)}, 400, "sound that is not WAV inside"), ({"frames": [PNG], "audio": "!!!notbase64"}, 400, "sound with broken base64"),
    ({"frames": [PNG], "audio": b64(wav(182))}, 413, "sound over 180 seconds"), ({"frames": [PNG], "caption": {"a": 1}}, 400, "a caption that is not text"),
]
for body, code, n in bad:
    r = c.post("/watch", json=body, headers=O); ok(r.status_code == code, f"/watch bad input: {n} is {code}", (r.status_code, r.text))
A2, c2 = load(HF_TOKEN="hf_test", MAX_AUDIO_BYTES=50000)
r = c2.post("/watch", json={"frames": [PNG], "audio": b64(wav(2))}, headers=O); ok(r.status_code == 413, "sound over MAX_AUDIO_BYTES is 413", r.text)
r = c2.post("/watch", content=b"{not json", headers={**O, "Content-Type": "application/json"}); ok(r.status_code == 400, "broken JSON is 400")
r = c2.post("/watch", content=b"[1,2]", headers={**O, "Content-Type": "application/json"}); ok(r.status_code == 400, "a JSON list is 400")
r = c2.post("/watch", content=b"x" * (A2.MAX_BODY_BYTES + 10), headers={**O, "Content-Type": "application/json"}); ok(r.status_code == 413, "a body over the cap is refused")
ok(not Fake.calls and A2.days["video"]["count"] == 0, "bad inputs called nothing outside and spent nothing", (Fake.calls[:1], A2.days["video"]))
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"hf-inference/models": [Resp(200, {"text": "two cups of rice"})], "chat/completions": [chat(RECIPE)]}
r = c.post("/watch", json={"frames": [PNG] * 8, "audio": b64(wav(180)), "caption": "x" * 9000}, headers=O)
ok(r.status_code == 200, "8 frames and exactly 180 s of sound are accepted", r.text[:200])
ok(len(chat_calls()[0]["json"]["messages"][0]["content"][0]["text"]) < len(A.VIDEO_PROMPT) + 3300, "a long caption is cut to 3,000 characters")

# ---------- /watch: limits
A, c = load(HF_TOKEN="hf_test")
Fake.plan = {"chat/completions": [chat(RECIPE)]}
codes = [c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.8.8"}).status_code for _ in range(4)]
r = c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.8.8"})
ok(codes == [200, 200, 200, 429] and r.json() == {"error": "That's a lot of videos. Try again in a bit, or add screenshots.", "why": "limit"}, "/watch: the 4th video in an hour from one visitor is 429", (codes, r.text))
ok(c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "9.9.9.9"}).status_code == 200, "another visitor is not limited")
ok(c.post("/read", json={"images": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.8.8"}).status_code == 200, "the video limit does not use up screenshot reads")
# the limit can't be dodged by putting a made-up address first
codes = [c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": f"1.2.3.{k}, 8.8.8.8"}).status_code for k in range(3)]
ok(codes == [429, 429, 429], "a faked first X-Forwarded-For value does not dodge the limit", codes)
codes = [c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": f"1.2.3.{k}, 8.8.8.8, 10.0.0.7"}).status_code for k in range(2)]
ok(codes == [429, 429], "an internal proxy hop after the visitor's address is skipped", codes)
A, c = load(HF_TOKEN="hf_test", VIDEO_DAILY_CAP=2, VIDEO_PER_VISITOR_PER_HOUR=1)
Fake.plan = {"chat/completions": [chat(RECIPE)]}
codes = [c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": f"8.8.4.{k}"}) for k in range(3)]
ok([x.status_code for x in codes] == [200, 200, 429] and codes[2].json()["why"] == "busy" and "busy today" in codes[2].json()["error"], "/watch: the daily cap answers busy today", [x.text[:80] for x in codes])
ok(c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.4.0"}).json()["why"] == "busy", "the daily cap is checked before the visitor's own")
A.days["video"]["date"] = "2000-01-01"
ok(c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.4.9"}).status_code == 200, "a new day resets the daily cap")

# visitor(): which address counts
class Rq:
    def __init__(self, xff, host="10.1.2.3"): self.headers = {"x-forwarded-for": xff} if xff is not None else {}; self.client = type("C", (), {"host": host})()
for xff, want, n in [("8.8.8.8", "8.8.8.8", "one address"), ("1.1.1.1, 8.8.8.8", "8.8.8.8", "the last public one, not a faked first"), ("8.8.8.8, 10.0.0.1, 172.20.0.3", "8.8.8.8", "internal hops skipped"),
                     ("2001:4860:4860::8888", "2001:4860:4860::8888", "IPv6"), ("garbage, 8.8.8.8", "8.8.8.8", "junk ignored"), ("", "10.1.2.3", "no header: the socket"), (None, "10.1.2.3", "header missing"),
                     ("10.0.0.1, 192.168.1.1", "10.1.2.3", "only internal addresses: the socket"), ("evil<script>, 127.0.0.1", "10.1.2.3", "junk and loopback: the socket")]:
    ok(A.visitor(Rq(xff)) == want, "visitor: " + n, A.visitor(Rq(xff)))

# ---------- /link
YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
for u, want in [(YT, "dQw4w9WgXcQ"), ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"), ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"), ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
                ("youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"), ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"), ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
                ("https://www.tiktok.com/@a/video/123", None), ("https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ", None), ("https://evil.example/?u=youtube.com/watch?v=dQw4w9WgXcQ", None),
                ("https://user:pw@youtube.com/watch?v=dQw4w9WgXcQ", None), ("https://youtube.com:8080/watch?v=dQw4w9WgXcQ", None), ("https://www.youtube.com/watch?v=short", None),
                ("https://www.youtube.com/watch?v=dQw4w9WgXcQ/../x", None), ("https://www.youtube.com/@channel", None), ("https://www.youtube.com/playlist?list=PL123", None),
                ("ftp://youtube.com/watch?v=dQw4w9WgXcQ", None), ("javascript:alert(1)", None), ("http://169.254.169.254/latest", None), ("http://localhost/watch?v=dQw4w9WgXcQ", None),
                ("", None), (None, None), (5, None), (["https://youtu.be/dQw4w9WgXcQ"], None), ("https://youtu.be/" + "a" * 400, None)]:
    ok(A.youtube_id(u) == want, f"youtube_id({str(u)[:60]!r}) is {want}", A.youtube_id(u))
for d, want in [("PT1M", 60), ("PT1H2M3S", 3723), ("PT45S", 45), ("P1DT1S", 86401), ("P0D", 0), ("", 0), (None, 0), ("junk", 0)]:
    ok(A.iso_seconds(d) == want, f"iso_seconds({d!r})", A.iso_seconds(d))
DESC = "My favourite!\n\nIngredients\n2 cups rice\n3 cloves garlic\n1 tbsp soy sauce\n\n0:00 intro\n1:30 cook"
ok(A.has_ingredients(DESC), "a description with an ingredient list is seen")
ok(not A.has_ingredients("Follow me!\n0:00 intro\n1:30 rice\n2:45 serve\n3:10 outro\nhttps://example.com"), "chapter times are not ingredients")
ok(not A.has_ingredients("Best rice ever. Subscribe for more."), "a teaser is not a recipe")

A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test")
ok(c.get("/").json()["links"] is True, "health: links on with the key")
Fake.plan = {"googleapis.com/youtube/v3/videos": [yt(DESC)], "chat/completions": [chat(RECIPE)]}
r = c.post("/link", json={"url": "https://youtu.be/dQw4w9WgXcQ?si=tracking"}, headers=O); j = r.json()
ok(r.status_code == 200 and j == {"text": RECIPE, "model": A.TEXT_MODELS[0], "used": "caption", "creator": "Test Kitchen", "url": YT}, "/link: a recipe in the description is read as text, with the creator and a clean link", r.text)
y = Fake.calls[0]
ok(y["method"] == "GET" and y["url"] == "https://www.googleapis.com/youtube/v3/videos" and y["params"]["id"] == "dQw4w9WgXcQ" and "snippet" in y["params"]["part"] and "contentDetails" in y["params"]["part"], "YouTube Data API videos.list is called with the id", y)
ok(y["headers"] == {"X-Goog-Api-Key": "g_test"} and "key" not in y["params"], "the Google key goes in a header, not the URL")
ok(len(Fake.calls) == 2 and "generativelanguage" not in json.dumps([x["url"] for x in Fake.calls]), "Gemini is not called when the description has the recipe")
ok(all("tracking" not in json.dumps(x.get("json", {})) + x["url"] + json.dumps(x.get("params", {})) for x in Fake.calls), "the visitor's own URL is never passed on")
t = chat_calls()[0]["json"]["messages"][0]["content"]
ok(len(t) == 1 and t[0]["type"] == "text" and "2 cups rice" in t[0]["text"] and "Never invent a number" in t[0]["text"], "description read: text only, same rules")

A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test")
Fake.plan = {"googleapis.com/youtube/v3/videos": [yt("Subscribe!", "PT9M")], "generativelanguage": [gem(RECIPE)]}
r = c.post("/link", json={"url": YT}, headers=O); j = r.json()
ok(r.status_code == 200 and j["text"] == RECIPE and j["used"] == "mix" and j["model"] == "gemini-2.5-flash-lite" and j["creator"] == "Test Kitchen", "/link: no recipe in the description, so Gemini watches it", r.text)
g = Fake.calls[1]
ok(g["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent" and g["headers"] == {"x-goog-api-key": "g_test"}, "Gemini call: default model and URL, key in a header", g["url"])
ok(g["json"]["contents"][0]["parts"][0] == {"file_data": {"file_uri": YT}} and "Never invent a number" in g["json"]["contents"][0]["parts"][1]["text"], "Gemini gets the YouTube URL as file_data and the same rules")
A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test", GEMINI_MODEL="gemini-x-lite")
Fake.plan = {"googleapis.com/youtube/v3/videos": [yt(DESC)], "chat/completions": [chat("NO_RECIPE")], "generativelanguage": [gem(RECIPE)]}
r = c.post("/link", json={"url": YT}, headers=O)
ok(r.status_code == 200 and r.json()["model"] == "gemini-x-lite" and "models/gemini-x-lite:generateContent" in Fake.calls[-1]["url"], "the description had no real recipe: falls through to Gemini; GEMINI_MODEL is used", r.text)

def link_case(plan, **env):
    A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test", **env); Fake.plan = plan
    return A, c.post("/link", json={"url": YT}, headers=O)
A, r = link_case({"googleapis.com/youtube/v3/videos": [Resp(200, {"items": []})]})
ok(r.status_code == 404 and r.json() == {"error": "That video is private. Add screenshots or paste the recipe.", "why": "private"}, "/link: a video the API can't see is 'private'", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi", privacy="unlisted")]})
ok(r.status_code == 404 and r.json()["why"] == "private" and len(Fake.calls) == 1, "/link: an unlisted video is not sent to Gemini", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi", "PT20M1S")]})
ok(r.status_code == 413 and r.json()["why"] == "toolong" and len(Fake.calls) == 1, "/link: over MAX_YOUTUBE_SECONDS is refused before Gemini", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi", "PT20M")], "generativelanguage": [gem(RECIPE)]})
ok(r.status_code == 200, "/link: exactly 20 minutes is read")
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi", "PT5M")], "generativelanguage": [gem(RECIPE)]}, MAX_YOUTUBE_SECONDS=120)
ok(r.status_code == 413, "/link: MAX_YOUTUBE_SECONDS variable is used")
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi", "P0D", live="live")]})
ok(r.status_code == 413 and len(Fake.calls) == 1, "/link: a live stream is refused", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi")], "generativelanguage": [gem("NO_RECIPE")]})
ok(r.status_code == 422 and r.json() == {"error": "No recipe found in that video.", "why": "none"}, "/link: no recipe is 422", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [Resp(403, {"error": "quota"})]})
ok(r.status_code == 502, "/link: YouTube API error is 502", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [RuntimeError("net")]})
ok(r.status_code == 502, "/link: YouTube API down is 502")
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi")], "generativelanguage": [Resp(500, None)]})
ok(r.status_code == 502, "/link: Gemini error is 502")
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi")], "generativelanguage": [Resp(429, None)]})
ok(r.status_code == 429 and r.json()["why"] == "busy", "/link: Gemini over its quota says busy today", r.text)
A, r = link_case({"googleapis.com/youtube/v3/videos": [yt("hi")], "generativelanguage": [Resp(200, {"promptFeedback": {}})]})
ok(r.status_code == 422, "/link: an empty Gemini answer is 'no recipe', not a crash", r.text)

A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test")
for u, n in [("https://www.tiktok.com/@a/video/1", "TikTok"), ("https://www.instagram.com/reel/abc/", "Instagram"), ("https://example.com/recipe", "a web page"), ("http://169.254.169.254/", "an internal address"), ("", "empty"), (None, "null"), (7, "a number")]:
    r = c.post("/link", json={"url": u}, headers=O); ok(r.status_code == 400 and r.json()["why"] == "badlink", f"/link refuses {n}", r.text)
ok(c.post("/link", json={}, headers=O).status_code == 400, "/link: no url is 400")
ok(c.post("/link", content=b"x" * 5000, headers={**O, "Content-Type": "application/json"}).status_code == 413, "/link: a big body is refused")
ok(not Fake.calls and A.days["link"]["count"] == 0, "refused links called nothing outside and spent nothing", Fake.calls[:1])
Fake.plan = {"googleapis.com/youtube/v3/videos": [yt(DESC)], "chat/completions": [chat(RECIPE)]}
codes = [c.post("/link", json={"url": YT}, headers={**O, "X-Forwarded-For": "8.8.8.8"}).status_code for _ in range(6)]
ok(codes == [200] * 5 + [429], "/link: the 6th link in an hour from one visitor is 429", codes)
ok(c.post("/watch", json={"frames": [PNG]}, headers={**O, "X-Forwarded-For": "8.8.8.8"}).status_code == 200, "link reads don't use up video reads")
A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test", LINK_DAILY_CAP=1)
Fake.plan = {"googleapis.com/youtube/v3/videos": [yt(DESC)], "chat/completions": [chat(RECIPE)]}
codes = [c.post("/link", json={"url": YT}, headers={**O, "X-Forwarded-For": f"8.8.4.{k}"}) for k in range(2)]
ok(codes[0].status_code == 200 and codes[1].status_code == 429 and codes[1].json()["why"] == "busy", "/link: daily cap says busy today", codes[1].text)

# ---------- logs hold counts only
A, c = load(HF_TOKEN="hf_test", GOOGLE_API_KEY="g_test")
buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
try:
    Fake.plan = {"hf-inference/models": [Resp(200, {"text": "SECRETWORD two cups of rice"})], "chat/completions": [chat(RECIPE + "\nUSED: mix"), chat("NO_RECIPE"), chat(RECIPE)], "googleapis.com/youtube/v3/videos": [yt(DESC, channel="SECRETCHANNEL")]}
    c.post("/watch", json={"frames": [PNG], "audio": b64(W), "caption": "SECRETCAPTION"}, headers={**O, "X-Forwarded-For": "8.8.8.8"})
    c.post("/watch", json={"frames": [PNG], "audio": b64(W), "caption": "SECRETCAPTION"}, headers={**O, "X-Forwarded-For": "8.8.8.8"})
    c.post("/link", json={"url": YT}, headers={**O, "X-Forwarded-For": "8.8.8.8"})
finally:
    sys.stdout = old
out = buf.getvalue()
ok(out.strip() and not any(w in out for w in ["SECRET", "Garlic", "rice", "dQw4w9WgXcQ", "8.8.8.8", "hf_test", "g_test", "youtube.com"]), "logs hold counts only: no text, link, address or key", out)

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
