"""Trade-show and signage loop: a slow, silent, seamless loop for a screen on a stand. A continuous
living background, a brand scene, three feature scenes with small live demos, a scan-to-try scene,
and a persistent QR code, URL and progress dots so passers-by can join at any moment. 60 s.

Run:   python signage_loop.py sheet   |   python signage_loop.py seam   |   python signage_loop.py render loop.mp4
Size:  portrait 1440x2560 by default (a 27" 2K screen turned vertical); MV_SIZE=2560x1440 for landscape,
       3840x2160 for 4K. Play with: vlc --fullscreen --loop --no-video-title-show loop.mp4
Every periodic motion repeats in a period that divides 60 s, so the loop has no seam.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import charts
import fx
import icons
import kinetic
import layout
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    name='Acme Studio', tagline='Videos from code, in minutes.', url='acme.example',
    logo=None,                                   # the client's SVG logo; None = placeholder mark
    features=[
        dict(icon='messages-square', title='Ask in plain words', body='Describe the video you need. The assistant plans every scene.', demo='chat'),
        dict(icon='chart-line', title='Numbers that move', body='Charts and counters animate straight from your data.', demo='chart'),
        dict(icon='languages', title='Every language', body='Kurdish, Arabic and English, shaped and aligned correctly.', demo='text'),
    ],
    cta='Scan to try it free',
    primary='#7C3AED', secondary='#22D3EE', bg='#06060C',
    scene_s=12.0,
    sound=False,                                 # expo floors are loud; turn on for a kiosk with speakers
)
C = CONFIG
W, H = mv.env_size((1440, 2560))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.DARK.with_(accent=C['primary'], accent2=mv.hex_color(mv.mix(C['primary'], '#FFFFFF', 0.35)), scale=L.unit * 1.25)
SAFE = L.safe('signage')
PORTRAIT = L.portrait
LOOP = C['scene_s'] * (2 + len(C['features']))
# the persistent QR code: bottom-right in portrait, top-right in landscape (scene content avoids it)
_qs = L.u(230) if PORTRAIT else L.u(170)
QR_BOX = (_qs, SAFE[2] - _qs - L.u(20), SAFE[3] - _qs - L.u(90)) if PORTRAIT else (_qs, SAFE[2] - _qs - L.u(20), SAFE[1] + L.u(10))


def backdrop(c, t):
    """Continuous across scenes, so transitions never cut the background."""
    c.clear(color(C['bg']))
    fx.flow(c, W, H, t, (C['bg'], mv.hex_color(mv.mix(C['bg'], C['primary'], 0.55)), mv.hex_color(mv.mix(C['bg'], C['secondary'], 0.45))),
            period=LOOP / 2, zoom=1.3)
    fx.particles(c, W, H, t, n=70, period=LOOP / 3, col=['#FFFFFF', TH.accent2], a=(0.08, 0.35), size=(1.5, 3.5))
    fx.vignette(c, W, H, 0.45)


def overlay(c, t):
    """Brand bar on top, QR + URL and progress dots at the bottom, on every scene."""
    k = int(t // C['scene_s'])
    n = len(tl.scenes)
    top = SAFE[1] + L.u(20)
    mark(c, SAFE[0] + L.u(40), top + L.u(40), L.u(80), 1e9)
    mv.text(c, C['name'], SAFE[0] + L.u(100), top + L.u(40), mv.font('Inter', L.u(40), wght=750), '#FFFFFF')
    dots_y = SAFE[3] - L.u(30)
    for i in range(n):
        near = 1 - clamp(abs(((t / C['scene_s']) - 0.5 - i + n / 2) % n - n / 2) * 1.2)
        w = L.u(18) + L.u(40) * near
        x = W / 2 + (i - (n - 1) / 2) * L.u(64) - w / 2
        rrect(c, x, dots_y - L.u(9), x + w, dots_y + L.u(9), L.u(9), paint('#FFFFFF', 0.25 + 0.65 * near))
    qa = 1 - presence(t % LOOP, (n - 1) * C['scene_s'] - 0.4, n * C['scene_s'] - 0.4, 0.6, 0.6)
    if qa > 0.01:                    # hidden while the CTA scene shows the big code
        qs, qx, qy = QR_BOX
        with Layer(c, qa):
            qr(c, 'https://' + C['url'], qx, qy, qs)
            if PORTRAIT:
                mv.text(c, C['url'], qx + qs, qy - L.u(34), mv.font('Inter', L.u(34), wght=600), '#E4E4E7', align='right')
            else:
                mv.text(c, C['url'], qx - L.u(24), qy + qs / 2, mv.font('Inter', L.u(34), wght=600), '#E4E4E7', align='right')


def mark(c, cx, cy, size, t, t0=0.0):
    if C['logo']:
        fx.logo(c, C['logo'], cx, cy, size, t, t0, style='pop')
    else:
        fx.placeholder_mark(c, cx, cy, size, t, t0, C['primary'], C['secondary'])


class Hero(Scene):
    def __init__(self):
        super().__init__(C['scene_s'])

    def draw(self, c, u):
        cx, cy = W / 2, H * (0.40 if PORTRAIT else 0.36)
        s = L.u(300 if PORTRAIT else 230)
        breathe = 1 + 0.025 * wave(u, C['scene_s'] / 2)
        fx.pulse_rings(c, cx, cy, u, period=C['scene_s'] / 3, rings=3, r0=s * 0.6, r1=s * 2.4, col=C['primary'], a=0.3)
        with Layer(c, 1.0, scale=breathe, pivot=(cx, cy)):
            mark(c, cx, cy, s, u + 10)
        fx.shine(c, mv.rrect_shape(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, s * 0.27), u, 1.0, 1.2, a=0.45)
        f = mv.font('Inter', L.u(150), wght=850)
        kinetic.reveal(c, C['name'], cx, cy + s * 0.9, f, u, 0.6, by='char', style='mask', each=0.04, align='center',
                       anchor='top', t_out=C['scene_s'] - 1.4)
        kinetic.reveal(c, C['tagline'], cx, cy + s * 0.9 + L.u(210), mv.font('Inter', L.u(58), wght=450), u, 1.4, by='word',
                       col='#C9C9D6', align='center', anchor='top', t_out=C['scene_s'] - 1.2)


class Feature(Scene):
    def __init__(self, k):
        super().__init__(C['scene_s'])
        self.k, self.f = k, C['features'][k]

    def draw(self, c, u):
        f = self.f
        end = C['scene_s'] - 1.0
        box = (SAFE[0] + L.u(40), H * 0.12, SAFE[2] - L.u(40), H * 0.40)
        if not PORTRAIT:
            box = (SAFE[0] + L.u(40), H * 0.24, W * 0.47, H * 0.85)
        a = presence(u, 0.3, end, 0.6, 0.6)
        s = L.u(130)
        with Layer(c, a, dy=(1 - a) * L.u(40)):
            rrect(c, box[0], box[1], box[0] + s, box[1] + s, L.u(36), paint(C['primary'], 0.85))
            icons.draw(c, f['icon'], box[0] + s / 2, box[1] + s / 2, s * 0.52, '#FFFFFF', stroke=2.2)
        title_f, title_rows = kinetic.fit_block(f['title'], 'Inter', box[2] - box[0], L.u(260), L.u(120), wght=850)
        kinetic.lines(c, title_rows, box[0], box[1] + s + L.u(70), title_f, u, 0.6, t_out=end - 0.3)
        ty = box[1] + s + L.u(70) + title_f.getSize() * 1.15 * len(title_rows) + L.u(40)
        ba = presence(u, 1.4, end, 0.6, 0.5)
        with Layer(c, ba, dy=(1 - ba) * L.u(30)):
            mv.text_block(c, f['body'], box[0], ty, box[2] - box[0], mv.font('Inter', L.u(52), wght=420), '#C9C9D6', leading=1.4)
        if PORTRAIT:
            demo = (SAFE[0] + L.u(40), H * 0.49, SAFE[2] - L.u(40), QR_BOX[2] - L.u(80))
        else:
            demo = (W * 0.52, QR_BOX[2] + QR_BOX[0] + L.u(50), SAFE[2] - L.u(20), SAFE[3] - L.u(90))
        da = presence(u, 1.0, end + 0.3, 0.8, 0.6)
        with Layer(c, da, dy=(1 - da) * L.u(60), bounds=(demo[0] - 200, demo[1] - 200, demo[2] + 200, demo[3] + 260)):
            getattr(self, 'demo_' + f['demo'])(c, u, demo)

    def demo_chat(self, c, u, r):
        area = ui.window(c, r, TH, kind='app', title='Assistant')
        msgs = [dict(role='user', text='A 30-second promo for our new app', at=1.8),
                dict(role='bot', text='Here is the plan: hook, live demo, three features and a call to action. Rendering now.', at=2.6, cps=30, think=1.0),
                dict(role='user', text='Make it vertical too', at=7.8)]
        ui.chat(c, area, TH, msgs, u, size=L.u(34))

    def demo_chart(self, c, u, r):
        ui.card(c, r, TH)
        st = charts.style(TH)
        pad = L.u(40)
        mv.text(c, 'Weekly renders', r[0] + pad, r[1] + pad + L.u(20), mv.font('Inter', L.u(40), wght=700), '#FFFFFF')
        charts.line(c, (r[0] + pad, r[1] + pad + L.u(80), r[2] - pad, r[3] - pad), [120, 180, 170, 260, 320, 410, 520, 640],
                    ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'], u, 1.8, 3.5, st=st, fmt='{:.0f}')

    def demo_text(self, c, u, r):
        ui.card(c, r, TH)
        cx = (r[0] + r[2]) / 2
        rows = [('Hello, welcome!', False), ('سڵاو، بەخێربێن!', True), ('مرحباً، أهلاً وسهلاً!', True)]
        h = (r[3] - r[1]) / (len(rows) + 1)
        for i, (s, rtl) in enumerate(rows):
            y = r[1] + h * (i + 1)
            a = presence(u, 1.8 + i * 1.2, None, 0.6)
            with Layer(c, a, dy=(1 - a) * L.u(30)):
                if rtl:
                    fsz = L.u(84)
                    wdt = shaped(s, 'IBM Plex Sans Arabic Bold', fsz)[1]
                    text_shaped(c, s, cx + wdt / 2, y + fsz * 0.3, 'IBM Plex Sans Arabic Bold', fsz, '#FFFFFF')
                else:
                    mv.text(c, s, cx, y, mv.font('Inter', L.u(76), wght=750), '#FFFFFF', align='center')


class CTA(Scene):
    def __init__(self):
        super().__init__(C['scene_s'])

    def draw(self, c, u):
        end = C['scene_s'] - 0.8
        cx = W / 2
        qs = min(W, H) * (0.46 if PORTRAIT else 0.42)
        qy = H * (0.36 if PORTRAIT else 0.3)
        a = presence(u, 0.4, end, 0.8, 0.6)
        head = mv.fit('Inter', C['cta'], layout.width(SAFE) - L.u(80), L.u(120), wght=850)
        with Layer(c, a, scale=0.94 + 0.06 * a, pivot=(cx, qy + qs / 2)):
            kinetic.reveal(c, C['cta'], cx, qy - L.u(110), head, u, 0.5, by='word', align='center', anchor='baseline',
                           t_out=end - 0.4)
            ui.focus_ring(c, (cx - qs / 2, qy, cx + qs / 2, qy + qs), u, TH, radius=qs * 0.05)
            qr(c, 'https://' + C['url'], cx - qs / 2, qy, qs, logo=lambda cc, x, y, s: mark(cc, x, y, s, 1e9))
            mv.text(c, C['url'], cx, qy + qs + L.u(90), mv.font('Inter', L.u(60), wght=650), '#FFFFFF', align='center')


SCENES = [Hero()] + [Feature(k) for k in range(len(C['features']))] + [CTA()]
tl = Timeline(SCENES, (W, H), transition=crossfade, before=0.6, after=0.6, loop=True, background=backdrop, overlay=overlay)
video = Video(tl, tl.duration, (W, H), FPS, background=C['bg'])


def soundtrack():
    """An ambient bed that loops with the picture (a whole number of bars: 60 s at 96 BPM = 24 bars)."""
    m = sfx.Mixer(tl.duration, loop=True)
    sfx.backing(m, bpm=96, key='D', mode='major', style='ambient', gain=0.7)
    return m.master('signage_audio.wav', lufs=-18)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack if C['sound'] else None)
