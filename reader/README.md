---
title: batch.recipes reader
emoji: 🍲
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Reads recipe screenshots for batch.recipes
---

Reads recipe screenshots, video frames and sound, and YouTube links into plain recipe text for [batch.recipes](https://batch.recipes), only when a cook asks.

- `/read`: screenshots. `/watch`: a few frames and up to 3 minutes of sound from a video the cook picked (the video file never comes here). `/link`: a YouTube link, through the YouTube Data API and Gemini; off until `GOOGLE_API_KEY` is set.
- Only accepts requests from batch.recipes and www.batch.recipes (set by the ALLOWED_ORIGINS variable).
- Rate limited per visitor and per day, with separate limits for screenshots, videos and links.
- Images and sound are sent to models through Hugging Face Inference Providers and are not stored here. Logs hold counts only.
- Secrets: `HF_TOKEN` (a fine-grained token with "Make calls to Inference Providers" only), and `GOOGLE_API_KEY` for YouTube links.
- Variables (all optional): `VIDEO` (set to `off` to stop video and link reads), `VIDEO_PER_VISITOR_PER_HOUR`, `VIDEO_DAILY_CAP`, `MAX_AUDIO_SECONDS`, `MAX_FRAMES`, `MAX_AUDIO_BYTES`, `STT_MODELS`, `STT_URL`, `TEXT_MODELS`, `GEMINI_MODEL`, `GEMINI_URL`, `LINK_PER_VISITOR_PER_HOUR`, `LINK_DAILY_CAP`, `MAX_YOUTUBE_SECONDS`. Defaults are at the top of `app.py`.
- `python3 test_app.py` runs the checks with every outside call faked.
