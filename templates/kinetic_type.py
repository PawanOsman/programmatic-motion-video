"""Kinetic typography: words that punch in on the beat, masked lines, breathing weights, decoding text,
rotating words, marker highlights and a closing title. 16 s at 120 BPM, hard cuts on the bar.

Run:   python kinetic_type.py sheet   |   python kinetic_type.py render kinetic.mp4
Change WORDS and the lines in CONFIG; the beat grid keeps everything in time with the music.
Flash safety: colour changes land at most twice per second.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import fx
import kinetic
import layout
import mv
import sfx
from mv import *

CONFIG = dict(
    words=['EVERY', 'FRAME', 'IS', 'CODE.'],
    lines=['Change a line.', 'Render again.'],
    breathe='MOTION',
    marquee='TYPE IN MOTION',
    decode='BUILT FROM CODE',
    stats=[(60, '{:.0f} fps'), (4, '{:.0f}K')],
    rotate=('Make it', ['faster.', 'bolder.', 'yours.']),
    statement='Type sets the pace, the beat sets the cut.',
    mark='pace',
    title=('KINETIC', 'TYPE'),
    ink='#F5F5F0', paper='#0A0A0A', accent='#FF4D2E', accent2='#2E5BFF', bpm=120,
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
B = Beats(C['bpm'])
SAFE = L.safe('title')
BOX = layout.inset(SAFE, L.u(40))


def fitted(s, size, wght=900, font='Inter', tracking=-0.03):
    return mv.fit(font, s, layout.width(BOX), size, tracking, wght=wght)


class OneWord(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        k = min(len(C['words']) - 1, int(u / B(1)))
        c.clear(color(C['paper']))
        w = C['words'][k]
        f = fitted(w, L.u(330))
        p = spring(u - B(k), 260, 16)
        col = C['accent'] if k == len(C['words']) - 1 else C['ink']
        with Layer(c, 1.0, scale=0.55 + 0.45 * p, pivot=(W / 2, H / 2)):
            mv.text(c, w, W / 2, H / 2, f, col, align='center', tracking=-0.03)


class Lines(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color(C['paper']))
        wipe_p = out_expo(seg(u, 0, 0.45))
        c.drawRect(mv.rect(0, 0, W * wipe_p, H), paint(C['accent']))
        f = fitted(max(C['lines'], key=len), L.u(170), 850)
        lh = f.getSize() * 1.1
        top = H / 2 - lh * len(C['lines']) / 2 + mv.cap_height(f) * 0.1
        for i, line in enumerate(C['lines']):
            kinetic.reveal(c, line, W / 2, top + i * lh, f, u, 0.25 + i * B(1.5), by='char', style='mask', each=0.022,
                           col=C['paper'], align='center', anchor='top', tracking=-0.02)


class Breathe(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color(C['paper']))
        fm = mv.font('Inter', L.u(120), wght=900)
        outline = mv.paint(C['ink'], 0.16, stroke=2)
        for i, fy in enumerate((0.13, 0.29, 0.71, 0.87)):     # outline tickers above and below, clear of the word
            kinetic_marquee_outline(c, C['marquee'], H * fy, fm, u * (1 if i % 2 else -1) + 50, outline)
        kinetic.weight_wave(c, C['breathe'], W / 2, H / 2, 'Inter', fitted(C['breathe'], L.u(280)).getSize(), u,
                            lo=150, hi=900, period=B(2), spread=0.9, col=C['ink'])


def kinetic_marquee_outline(c, s, y, f, t, p, speed=160.0):
    unit = s + '   '
    uw = mv.width(unit, f)
    x = -((speed * t) % uw)
    while x < W:
        mv.text(c, unit, x, y, f, anchor='middle', p=p)
        x += uw


class Decode(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color(C['accent2']))
        fx.grid(c, W, H, u, step=L.u(60), col='#FFFFFF', a=0.12, fade=0.3)
        fm = mv.fit('JetBrains Mono', C['decode'], layout.width(BOX), L.u(120), wght=800)
        kinetic.scramble(c, C['decode'], W / 2, H * 0.4, fm, u, 0.05, 0.9, col='#FFFFFF', align='center')
        fs = mv.font('Inter', L.u(120), wght=850)
        for i, (v, fmt) in enumerate(C['stats']):
            x = W / 2 + (i - 0.5) * L.u(520)
            kinetic.counter(c, x, H * 0.68, fs, u, 0.6 + i * 0.25, 0.8, 0, v, fmt, '#FFFFFF', align='center')


class Rotate(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color(C['ink']))
        lead, words = C['rotate']
        f = mv.font('Inter', L.u(150), wght=850)
        lw = mv.width(lead + ' ', f)
        ww = max(mv.width(w, f) for w in words)
        x0 = W / 2 - (lw + ww) / 2
        mv.text(c, lead, x0, H / 2, f, C['paper'])
        kinetic.rotator(c, words, x0 + lw, H / 2, f, u, period=B(4) / len(words), trans=0.28, col=C['accent'])


class Statement(Scene):
    def __init__(self):
        super().__init__(B(4))

    def draw(self, c, u):
        c.clear(color(C['paper']))
        f, rows = kinetic.statement(c, C['statement'], BOX, 'Inter', u, 0.05, max_size=L.u(170), align='left',
                                    col=C['ink'], each=0.06, wght=850)
        # find the marked word to circle it
        lh = f.getSize() * 1.08
        h = mv.cap_height(f) + lh * (len(rows) - 1)
        top = (BOX[1] + BOX[3] - h) / 2
        for i, row in enumerate(rows):
            if C['mark'] in row:
                pre = row[:row.index(C['mark'])]
                x0 = BOX[0] + mv.width(pre, f, -0.01)
                x1 = x0 + mv.width(C['mark'], f, -0.01)
                y = top + i * lh
                kinetic.circle_mark(c, (x0 - L.u(10), y - L.u(10), x1 + L.u(10), y + mv.cap_height(f) + L.u(14)), u, 1.1,
                                    0.6, C['accent'], width=L.u(9))


class Title(Scene):
    def __init__(self):
        super().__init__(B(8))

    def draw(self, c, u):
        c.clear(color(C['paper']))
        glow(c, W / 2, H / 2, L.u(900), C['accent'], 0.18 * seg(u, 0.2, 1.5))
        a, b = C['title']
        f = fitted(a, L.u(240))
        kinetic.reveal(c, a, W / 2, H / 2 - L.u(20), f, u, 0.1, by='line', style='track', dur=1.2, col=C['ink'],
                       align='center', anchor='baseline', tracking=-0.02, t_out=B(8) - 0.8)
        fb = mv.font('Inter', f.getSize() * 0.55, wght=300)
        kinetic.reveal(c, b, W / 2, H / 2 + L.u(40), fb, u, 0.6, by='char', style='rise', col=C['accent'], align='center',
                       anchor='top', tracking=0.4, t_out=B(8) - 0.7)
        wline = mv.width(a, f, -0.02)
        kinetic.underline(c, W / 2 - wline / 2, W / 2 + wline / 2, H / 2 + L.u(210), u, 1.4, 0.8, C['accent'], L.u(10))


tl = Timeline([OneWord(), Lines(), Breathe(), Decode(), Rotate(), Statement(), Title()], (W, H), transition=None)
video = Video(tl, tl.duration, (W, H), FPS, background=C['paper'], dither=False)


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=C['bpm'], key='A', mode='minor', style='drive', gain=0.8, fade_out=2.0)
    for k in range(len(C['words'])):
        m.add(sfx.impact(0.6), B(k), 0.4)
    for k in range(1, len(tl.scenes)):
        m.add(sfx.whoosh(0.3), tl.start(k) - 0.3, 0.35)
    m.add(sfx.riser(B(8) - 0.2), tl.start(6) - B(8) + 0.2, 0.2)
    m.add(sfx.impact(1.6), tl.start(6), 0.55)
    return m.master('kinetic_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
