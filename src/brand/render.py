# SVG -> PNG with headless Chromium (no cairo here). render({'out.png': (svg, w, h)})
import asyncio
from playwright.async_api import async_playwright


async def _run(jobs):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        for out, (svg, w, h) in jobs.items():
            await pg.set_viewport_size({'width': w, 'height': h})
            body = svg.replace('<svg ', f'<svg style="display:block;width:{w}px;height:{h}px" ', 1)
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{body}</body></html>')
            await pg.screenshot(path=out, omit_background=True, clip={'x': 0, 'y': 0, 'width': w, 'height': h})
        await b.close()


def render(jobs):
    asyncio.run(_run(jobs))
