"""Lower third with transparency, for editors: a name and title that slide in over footage, hold, and
leave. Renders with alpha so it drops onto any timeline.

Run:   python lower_third.py sheet
       python lower_third.py render lower_third.mov --codec prores4444     (alpha for Premiere, Resolve, FCP)
       python lower_third.py render lower_third.webm --codec vp9-alpha     (alpha for the web)
Check the alpha: ffprobe shows pix_fmt yuva444p12le (ProRes) or alpha_mode=1 (WebM).
The contact sheet shows the graphic over a checkerboard, so you can see what is transparent.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import icons
import kinetic
import layout
import mv
from mv import *

CONFIG = dict(
    name='Lana Ahmed',
    title='Head of Product, Acme Studio',
    icon='mic',                              # a Lucide icon in the tag, or None
    accent='#7C3AED', panel='#0E0E16', ink='#FFFFFF', sub='#C9C9D6',
    t_in=0.4, t_out=6.2, duration=7.0,
    side='left',                             # 'left' or 'right'
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
PREVIEW = 'sheet' in sys.argv or 'still' in sys.argv     # show a checkerboard behind the stills


def checker(c):
    s = L.u(40)
    c.drawRect(mv.rect(0, 0, W, H), paint('#9A9AA2'))
    p = skia.Path()
    for y in range(0, int(H / s) + 1):
        for x in range(0, int(W / s) + 1):
            if (x + y) % 2:
                p.addRect(mv.rect(x * s, y * s, (x + 1) * s, (y + 1) * s))
    c.drawPath(p, paint('#C4C4CC'))


def draw(c, t):
    if PREVIEW:
        checker(c)
    fn = mv.font('Inter', L.u(54), wght=760)
    ft = mv.font('Inter', L.u(30), wght=450)
    pad = L.u(34)
    tag = L.u(96) if C['icon'] else 0.0
    w = max(mv.width(C['name'], fn), mv.width(C['title'], ft)) + pad * 2 + tag
    h = L.u(150)
    safe = L.safe('title')
    x0 = safe[0] if C['side'] == 'left' else safe[2] - w
    y1 = safe[3] - L.u(20)
    y0 = y1 - h
    grow = out_expo(seg(t, C['t_in'], C['t_in'] + 0.6)) * (1 - in_expo(seg(t, C['t_out'] + 0.15, C['t_out'] + 0.7)))
    if grow <= 0:
        return
    bar_w = L.u(10)
    # accent bar first, then the panel wipes out of it
    c.drawRect(mv.rect(x0, y0, x0 + bar_w, y0 + h * mv.clamp(grow * 1.6)), paint(C['accent']))
    pw = (w - bar_w) * out_expo(seg(t, C['t_in'] + 0.2, C['t_in'] + 0.8)) * (1 - in_expo(seg(t, C['t_out'], C['t_out'] + 0.5)))
    if pw > 1:
        with Clip(c, (x0 + bar_w, y0, x0 + bar_w + pw, y1)):
            c.drawRect(mv.rect(x0 + bar_w, y0, x0 + w, y1), paint(C['panel'], 0.92))
            tx = x0 + bar_w + pad
            if C['icon']:
                s = L.u(64)
                rrect(c, tx, (y0 + y1) / 2 - s / 2, tx + s, (y0 + y1) / 2 + s / 2, L.u(16), paint(C['accent']))
                icons.draw(c, C['icon'], tx + s / 2, (y0 + y1) / 2, s * 0.55, '#FFFFFF')
                tx += tag
            kinetic.reveal(c, C['name'], tx, y0 + h * 0.36, fn, t, C['t_in'] + 0.45, by='word', style='mask',
                           col=C['ink'], t_out=C['t_out'] - 0.1)
            kinetic.reveal(c, C['title'], tx, y0 + h * 0.72, ft, t, C['t_in'] + 0.65, by='word', style='rise',
                           col=C['sub'], each=0.03, t_out=C['t_out'] - 0.15)


video = Video(draw, C['duration'], (W, H), FPS, transparent=not PREVIEW, dither=False)

if __name__ == '__main__':
    if 'render' in sys.argv and '--codec' not in sys.argv:
        sys.argv += ['--codec', 'prores4444']        # alpha needs an alpha codec
    mv.cli(video)
