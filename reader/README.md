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

Reads recipe screenshots into plain text for [batch.recipes](https://batch.recipes), only when a cook taps "Read with AI".

- Only accepts requests from batch.recipes and michaelbegley.github.io.
- Rate limited per visitor and per day.
- Images are sent to a vision model through Hugging Face Inference Providers and are not stored here.
- Needs one secret: `HF_TOKEN` (a fine-grained token with "Make calls to Inference Providers" only).
