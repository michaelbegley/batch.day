# The one batch.recipes mark: the pot from the home page (3 steam lines, side handles).
# Every icon, favicon and logo file is drawn from PATHS below, so they can't drift apart again.
PATHS = ('<path d="M20 16c-2-3 2-5 0-8"/><path d="M28 16c-2-3 2-5 0-8"/><path d="M36 16c-2-3 2-5 0-8"/>'
         '<path d="M10 24h36"/><path d="M13 24v16a6 6 0 0 0 6 6h18a6 6 0 0 0 6-6V24"/><path d="M6 28h7M43 28h7"/>')
CX, CY = 28, 27          # centre of the drawing (x 6..50, y 8..46) in its 56-unit box
SPAN = 44                # widest side of the drawing, before stroke
LINE = 2                 # page weight (home page, share image)
BOLD = 4.2               # icon and logo weight (sits with the SemiBold wordmark, holds at 16 px)
ORANGE, ORANGE_DARK, INK = '#c2410c', '#ff7a3d', '#1d1d1f'


def g(color, stroke):
    return (f'<g fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{PATHS}</g>')


def square(color=ORANGE, stroke=BOLD, fill=0.86, bg=None, radius=0, size=512, dark=False):
    """The mark centred in a square. fill = share of the square the drawing (with stroke) takes."""
    side = (SPAN + stroke) / fill
    x0, y0 = CX - side / 2, CY - side / 2
    bgs = (f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{side:.3f}" height="{side:.3f}" '
           f'rx="{radius * side:.3f}" fill="{bg}"/>') if bg else ''
    style = (f'<style>g{{stroke:{color}}}@media(prefers-color-scheme:dark){{g{{stroke:{ORANGE_DARK}}}}}</style>'
             if dark else '')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.3f} {y0:.3f} {side:.3f} {side:.3f}" '
            f'width="{size}" height="{size}">{style}{bgs}{g(color, stroke)}</svg>')


def placed(height, x, y_mid, color=ORANGE, stroke=BOLD):
    """The mark as a group for a lockup: drawing (with stroke) `height` tall, left edge at x, centred on y_mid."""
    k = height / (38 + stroke)                       # drawing is 38 tall (y 8..46)
    left = 6 - stroke / 2
    return (f'<g transform="translate({x - left * k:.3f},{y_mid - CY * k:.3f}) scale({k:.5f})">'
            f'{g(color, stroke)}</g>'), (SPAN + stroke) * k
