"""Vertical social ad (Reels, TikTok, Shorts): a hook in the first second, the product on a phone,
three benefits, social proof, and a call to action. 15 s at 128 BPM, cut on the beat.

Run:   python social_ad.py sheet   |   python social_ad.py render ad.mp4
Keeps text inside the social safe area (clear of the app's buttons and captions).
Replace the placeholder rating and numbers with real, citable ones, or remove that scene.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import fx
import icons
import kinetic
import layout
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    name='Acme Studio', url='acme.example',
    hook=['STOP', 'EDITING', 'BY HAND.'],
    promise='Type an idea. Get a video.',
    benefits=[('zap', 'Ready in minutes'), ('palette', 'On-brand every time'), ('smartphone', 'Every format at once')],
    proof=('4.9', 'rating from 2,000+ creators'),          # placeholder: use real, sourced numbers
    cta='Try it free',
    colors=['#7C3AED', '#F43F5E', '#0EA5E9'], bg='#09090F', bpm=128,
)
C = CONFIG
W, H = mv.env_size((1080, 1920))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
SAFE = L.safe('social') if L.portrait else L.safe('title')
B = Beats(C['bpm'])
TH = ui.DARK.with_(accent=C['colors'][0], accent2='#C4B5FD')
DISPLAY = 'Inter'


class Hook(Scene):
    def __init__(self):
        super().__init__(B(5))

    def draw(self, c, u):
        k = min(len(C['hook']) - 1, int(u / B(1.5)))
        c.clear(color(C['colors'][k % len(C['colors'])]))
        fx.grid(c, W, H, u, step=L.u(90), a=0.12, drift=(0, L.u(40)))
        box = layout.inset(SAFE, L.u(20))
        rows = C['hook']
        size = min(mv.fit(DISPLAY, r, layout.width(box), L.u(230), wght=900).getSize() for r in rows)
        f = mv.font(DISPLAY, size, wght=900)
        lh = size * 1.0
        shown = sum(inout_cubic(seg(u, B(1.5) * i, B(1.5) * i + 0.25)) for i in range(len(rows)))
        top = (box[1] + box[3]) / 2 - lh * max(1.0, shown) / 2     # the block re-centres as words arrive
        for i, r in enumerate(rows):
            t0 = B(1.5) * i
            if u < t0:
                continue
            p = out_back(seg(u, t0, t0 + 0.28), 2.2)
            with Layer(c, 1.0, scale=0.4 + 0.6 * p, pivot=(W / 2, top + lh * (i + 0.5))):
                mv.text(c, r, W / 2, top + lh * (i + 0.5), f, '#FFFFFF', align='center', tracking=-0.02)


class Product(Scene):
    def __init__(self):
        super().__init__(B(8))

    def draw(self, c, u):
        c.clear(color(C['bg']))
        fx.mesh(c, W, H, u, [C['bg'], C['colors'][0], C['colors'][2]], bg=C['bg'], period=16, a=0.5)
        f = mv.font(DISPLAY, L.u(78), wght=850)
        kinetic.statement(c, C['promise'], (SAFE[0], SAFE[1], SAFE[2], SAFE[1] + L.u(260)), DISPLAY, u, 0.1,
                          max_size=L.u(96), align='center', wght=850)
        ph = layout.width(SAFE) * 0.78 * 2.05       # a big phone that runs off the bottom edge, as in real ads
        pr = layout.anchor((SAFE[0], SAFE[1] + L.u(300), SAFE[2], SAFE[1] + L.u(300) + ph), ph / 2.05, ph, 'top')
        p = presence(u, 0.15, None, 0.7, ease_in=out_expo)
        with Layer(c, clamp(p * 1.5), dy=(1 - p) * L.u(400)):
            scr = ui.phone(c, pr, TH)
            x0, y0, x1, y1 = scr
            s = (x1 - x0) / 300
            ui.label(c, 'New video', x0 + 18 * s, y0 + 26 * s, TH.with_(scale=s), 20, 700)
            ui.text_field(c, (x0 + 14 * s, y0 + 52 * s, x1 - 14 * s, y0 + 96 * s), TH, typed('A 15s ad for our coffee app', u, 0.9, 30),
                          focus=1.0 if u < 2.2 else 0.0, t=u, typing=u < 2.0, size=14 * s, radius=12 * s)
            prog = seg(u, 2.3, 3.4)
            if 2.2 < u:
                ui.progress_bar(c, (x0 + 14 * s, y0 + 112 * s, x1 - 14 * s, y0 + 120 * s), prog, TH)
            thumbs = layout.grid((x0 + 14 * s, y0 + 136 * s, x1 - 14 * s, y0 + 136 * s + 3 * 150 * s), 2, 3, 10 * s)
            for i, r in enumerate(thumbs):
                a = presence(u, 2.5 + i * 0.12, None, 0.3, ease_in=out_back)
                if a <= 0:
                    continue
                with Layer(c, clamp(a * 2), scale=0.7 + 0.3 * a, pivot=layout.center(r)):
                    rrect(c, *r, 10 * s, fx_linear(r, C['colors'][i % 3], C['colors'][(i + 1) % 3]))
                    icons.draw(c, 'play', *layout.center(r), 22 * s, '#FFFFFF', 0.9)


def fx_linear(r, a, b):
    return mv.linear(r[0], r[1], r[2], r[3], [a, b])


class Benefits(Scene):
    def __init__(self):
        super().__init__(B(9))

    def draw(self, c, u):
        c.clear(color(C['bg']))
        glow(c, W / 2, H * 0.3, L.u(900), C['colors'][0], 0.35)
        rows = layout.split_v(layout.inset(SAFE, 0, L.u(60)), [1] * len(C['benefits']), L.u(40))
        for i, ((ic, label), r) in enumerate(zip(C['benefits'], rows)):
            t0 = B(1 + i * 2.5)
            p = presence(u, t0, None, 0.35, ease_in=out_back)
            if p <= 0:
                continue
            cx, cy = layout.center(r)
            with Layer(c, clamp(p * 2), scale=0.7 + 0.3 * p, pivot=(cx, cy)):
                s = L.u(170)
                rrect(c, cx - s / 2, cy - s * 0.95, cx + s / 2, cy + s * 0.05, L.u(44), paint(C['colors'][i % 3]))
                icons.draw(c, ic, cx, cy - s * 0.45, s * 0.52, '#FFFFFF', stroke=2.4)
                f = mv.fit(DISPLAY, label, layout.width(r), L.u(70), wght=850)
                mv.text(c, label, cx, cy + L.u(95), f, '#FFFFFF', align='center')


class Proof(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color('#FFFFFF'))
        cx, cy = W / 2, H * 0.45
        f = mv.font(DISPLAY, L.u(250), wght=900)
        kinetic.counter(c, cx, cy - L.u(40), f, u, 0.1, 0.9, 0, float(C['proof'][0]), '{:.1f}', '#0B0B12', align='center')
        for i in range(5):
            p = out_back(seg(u, 0.3 + i * 0.08, 0.6 + i * 0.08))
            x = cx + (i - 2) * L.u(110)
            with Layer(c, clamp(p * 2), scale=max(0.01, p), pivot=(x, cy + L.u(140))):
                icons.draw(c, 'star', x, cy + L.u(140), L.u(90), '#F59E0B', fill='#F59E0B')
        mv.text(c, C['proof'][1], cx, cy + L.u(290), mv.font('Inter', L.u(46), wght=600), '#3F3F46', align='center')


class CTA(Scene):
    def __init__(self):
        super().__init__(B(6))

    def draw(self, c, u):
        fx.mesh(c, W, H, u, [C['bg'], C['colors'][0], C['colors'][1]], bg=C['bg'], period=12, a=0.6)
        cx = W / 2
        fx.placeholder_mark(c, cx, H * 0.3, L.u(200), u, 0.05, C['colors'][0], C['colors'][2])
        kinetic.reveal(c, C['name'], cx, H * 0.3 + L.u(170), mv.font(DISPLAY, L.u(90), wght=900), u, 0.25, by='char',
                       style='mask', each=0.03, align='center', anchor='top')
        bw, bh = L.u(560), L.u(130)
        by = H * 0.52
        p = presence(u, 0.5, None, 0.45, ease_in=out_back)
        with Layer(c, clamp(p * 2), scale=0.8 + 0.2 * p, pivot=(cx, by + bh / 2)):
            ui.focus_ring(c, (cx - bw / 2, by, cx + bw / 2, by + bh), u, TH, radius=bh / 2)
            ui.button(c, (cx - bw / 2, by, cx + bw / 2, by + bh), C['cta'], TH, fill='#FFFFFF', radius=bh / 2,
                      size=L.u(52), icon_right='arrow-right')
        mv.text(c, C['url'], cx, by + bh + L.u(90), mv.font('Inter', L.u(44), wght=600), '#E4E4E7', align='center',
                a=presence(u, 0.9, None, 0.4))


tl = Timeline([Hook(), Product(), Benefits(), Proof(), CTA()], (W, H), transition=None,
              transitions={1: zoom_through, 2: push, 3: slide_up, 4: zoom_through}, before=0.35, after=0.4)
# motion blur only on the zoom joins; push and slide_up smear themselves
video = Video(tl, tl.duration, (W, H), FPS, background=C['bg'],
              subframes=lambda t: 4 if tl.transition_at(t) is zoom_through else 1)


def soundtrack():
    m = sfx.Mixer(tl.duration)
    info = sfx.backing(m, bpm=C['bpm'], key='F', mode='minor', style='drive', gain=0.8, fade_out=1.5)
    for i in range(len(C['hook'])):
        m.add(sfx.impact(0.8), B(1.5) * i, 0.45)
    for k in range(1, 5):
        m.add(sfx.whoosh(0.35), tl.start(k) - 0.35, 0.45)
    m.add(sfx.chime('success'), tl.start(1) + 3.4, 0.3, reverb=0.3)
    for i in range(len(C['benefits'])):
        m.add(sfx.blip(700 + 150 * i), tl.start(2) + B(1 + i * 2.5), 0.35, reverb=0.3)
    m.add(sfx.sparkle(), tl.start(3) + 0.3, 0.3, reverb=0.4)
    m.add(sfx.impact(1.4), tl.start(4) + 0.05, 0.5)
    return m.master('social_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
