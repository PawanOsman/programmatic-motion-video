"""Product promo: logo intro, hook line, live product demo, features, numbers, call to action.
30 s at 112 BPM with a synced soundtrack. Edit CONFIG; every scene and the sound read from it.

Run:   python promo.py sheet            contact sheet of 12 moments
       python promo.py render promo.mp4
Sizes: MV_SIZE=1080x1920 python promo.py render promo_vertical.mp4   (also 1080x1080, 3840x2160)
Replace every placeholder (name, copy, numbers, logo) with real, sourced material before delivery.
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
    name='Acme Studio',                                  # product or company
    tagline='Videos from code, in minutes.',
    url='acme.example',
    logo=None,                                           # path to the client's SVG logo; None = placeholder mark
    primary='#7C3AED', secondary='#22D3EE', bg='#07070D',
    hook='Turn a one-line brief into a finished video.',
    hook_emphasis=['finished', 'video.'],
    demo_caption='Describe it. Get a finished cut.',     # shown above the demo in vertical and square frames
    prompt='Make a 30-second launch video for our app',
    answer='Done. Six scenes, music synced to the cuts, exported in 16:9, 9:16 and 1:1.',
    features=[('wand-sparkles', 'Write the brief', 'Plain words in, a storyboard out.'),
              ('palette', 'Brand it once', 'Your colours, fonts and logo everywhere.'),
              ('rocket', 'Ship every format', 'Landscape, vertical and square in one go.')],
    stats=[(10, '{:.0f}x', 'faster first cut'), (120, '{:.0f}+', 'ready-made scenes'), (99.9, '{:.1f}%', 'render success')],
    cta='Start free',
    bpm=112,
)

W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
C = CONFIG
TH = ui.DARK.with_(accent=C['primary'], accent2=mv.hex_color(mv.mix(C['primary'], '#FFFFFF', 0.35)), bg=C['bg'])
BEAT = 60.0 / C['bpm']
DISPLAY = 'Inter'
STREAM_CPS = 55             # how fast the assistant's answer streams (characters per second)


def background(c, t, glow_at=(0.5, 0.45), strength=1.0):
    fx.mesh(c, W, H, t, [C['bg'], C['primary'], mv.hex_color(mv.mix(C['bg'], C['secondary'], 0.55))], bg=C['bg'],
            period=24, size=0.55, a=0.55 * strength)
    fx.grid(c, W, H, t, step=L.u(72), a=0.05, kind='dots', drift=(0, L.u(6)))
    fx.vignette(c, W, H, 0.5)


def mark(c, cx, cy, size, t, t0):
    if C['logo']:
        fx.logo(c, C['logo'], cx, cy, size, t, t0, style='pop')
    else:
        fx.placeholder_mark(c, cx, cy, size, t, t0, C['primary'], C['secondary'])


class Intro(Scene):
    def __init__(self):
        super().__init__(6 * BEAT, exit=(W / 2, H * 0.4))

    def draw(self, c, u):
        background(c, u)
        size = L.u(210)
        cx, cy = W / 2, H * 0.4
        fx.pulse_rings(c, cx, cy, u, period=2.4, rings=2, r0=size * 0.6, r1=size * 2.2, col=C['primary'], a=0.35 * seg(u, 0.4, 1.0))
        mark(c, cx, cy, size, u, 0.25)
        fx.shine(c, mv.rrect_shape(cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2, size * 0.27), u, 1.1, 0.8, a=0.55)
        fx.sparkle(c, cx + size * 0.62, cy - size * 0.55, L.u(40), seg(u, 1.2, 2.0))
        f = mv.font(DISPLAY, L.u(104), wght=850)
        kinetic.reveal(c, C['name'], W / 2, cy + size * 0.95, f, u, 0.8, by='char', style='mask', each=0.035,
                       align='center', anchor='top', tracking=-0.02)
        kinetic.reveal(c, C['tagline'], W / 2, cy + size * 0.95 + L.u(150), mv.font('Inter', L.u(38), wght=450), u, 1.5,
                       by='word', style='rise', each=0.06, col=TH.muted, align='center', anchor='top')


class Hook(Scene):
    def __init__(self):
        super().__init__(7 * BEAT)

    def draw(self, c, u):
        c.clear(color(C['bg']))
        glow(c, W * 0.3 + L.u(120) * wave(u, 8), H * 0.3, L.u(900), C['primary'], 0.28)
        glow(c, W * 0.8, H * 0.85, L.u(700), C['secondary'], 0.12)
        box = layout.inset(L.safe('title'), L.u(70), L.u(40))
        kinetic.statement(c, C['hook'], box, DISPLAY, u, 0.25, max_size=L.u(150), leading=1.05, align='center',
                          col='#FFFFFF', emphasis=C['hook_emphasis'], em_col=TH.accent2, wght=820)


class Demo(Scene):
    """The product demo is drawn on a 1920x1080 stage and placed into any frame size by the camera."""
    T = dict(ptr_in=0.3, focus=1.05, type_at=1.3, cps=22, send=None, answer=None)

    def __init__(self):
        super().__init__(16 * BEAT)
        T = self.T
        T['send'] = type_end(C['prompt'], T['type_at'], T['cps']) + 0.55
        T['answer'] = T['send'] + 0.25
        # landscape: the stage fills the frame; vertical/square: a larger, side-cropped stage under a caption
        base = min(W / 1920, H / 1080) * L.pick(0.96, 1.3, 1.12)
        # after sending, frame the whole chat panel (in portrait the narrow frame centres on it)
        chat_view = (L.pick(1.06, 1.14, 1.06), L.pick(990, 1120, 990), 560)
        self.cam = Camera(1.0, 960, 540, [(0.55, 1.45, 1.5, 1010, 760), (T['send'] - 0.1, T['send'] + 0.9) + chat_view],
                          screen=(W / 2, L.pick(H / 2, H * 0.56, H * 0.58)), base=base)
        self.ptr = Pointer([(T['ptr_in'], 1650, 1020), (T['focus'] - 0.15, 900, 868), (T['send'] - 0.45, 900, 868),
                            (T['send'] - 0.05, 1592, 868)], clicks=(T['focus'], T['send']), show=(T['ptr_in'], 99), ring=TH.accent2)
        self.msgs = [dict(role='user', text=C['prompt'], at=T['send'] + 0.1),
                     dict(role='bot', text=C['answer'], at=T['answer'] + 0.25, cps=STREAM_CPS, think=0.8)]

    def draw(self, c, u):
        T = self.T
        background(c, u, strength=0.7)
        c.save()
        if L.orientation != 'landscape':        # keep the stage below the caption
            c.clipRect(mv.rect(0, H * 0.27, W, H))
        self.cam.apply(c, u)
        area = ui.window(c, (160, 100, 1760, 980), TH, url=f"app.{C['url']}", loading=seg(u, 0.0, 0.8))
        x0, y0, x1, y1 = area
        ui.sidebar(c, (x0, y0, x0 + 300, y1), TH, [('clapperboard', 'Projects'), ('messages-square', 'Assistant'),
                                                  ('palette', 'Brand kit'), ('settings', 'Settings')], active=1, title=C['name'])
        ui.label(c, 'New video', x0 + 340, y0 + 56, TH, 30, 700)
        ui.badge(c, x0 + 540, y0 + 56, 'Draft', TH, dot=True)
        ui.chat(c, (x0 + 320, y0 + 90, x1 - 20, y1 - 130), TH, self.msgs, u, size=27)
        typed_now = typed(C['prompt'], u, T['type_at'], T['cps'])
        sent = u >= T['send']
        focus = seg(u, T['focus'] - 0.05, T['focus'] + 0.15) * (1 - seg(u, T['send'] + 0.2, T['send'] + 0.5))
        ui.text_field(c, (x0 + 340, y1 - 108, x1 - 150, y1 - 32), TH, '' if sent else typed_now, 'Describe your video...',
                      focus, u, typing(C['prompt'], u, T['type_at'], T['cps']), icon='sparkles', size=26)
        ui.button(c, (x1 - 134, y1 - 108, x1 - 36, y1 - 32), '', TH, icon='send', press=self.ptr.pressed(u, T['send']))
        done_at = T['answer'] + 0.25 + 0.8 + len(C['answer']) / STREAM_CPS
        ui.toast(c, (1240, 150, 1720, 250), TH, 'Video ready', '16:9 · 9:16 · 1:1', icon='circle-check',
                 p=presence(u, done_at + 0.2, None, 0.5))
        self.ptr.draw(c, u)
        c.restore()
        if L.orientation != 'landscape':
            kinetic.statement(c, C['demo_caption'], (L.u(70), H * 0.07, W - L.u(70), H * 0.24), DISPLAY, u, 0.2,
                              max_size=L.u(92), align='center', wght=820)


class Features(Scene):
    def __init__(self):
        super().__init__(10 * BEAT)

    def draw(self, c, u):
        c.clear(color(C['bg']))
        fx.grid(c, W, H, u, step=L.u(80), a=0.06, drift=(L.u(8), 0))
        glow(c, W / 2, H * 0.1, L.u(900), C['primary'], 0.22)
        safe = L.safe('title')
        head = mv.font(DISPLAY, L.u(64), wght=800)
        kinetic.reveal(c, 'Everything in one place', W / 2, safe[1] + L.u(40), head, u, 0.15, by='word', align='center', anchor='top')
        area = (safe[0], safe[1] + L.u(170), safe[2], safe[3] - L.u(10))
        n = len(C['features'])
        if L.orientation == 'landscape':
            cells = layout.split_h(area, [1] * n, L.u(36))
        else:
            stack = min(layout.height(area), n * L.u(320) + (n - 1) * L.u(30))
            cells = layout.split_v(layout.anchor(area, layout.width(area), stack, 'top'), [1] * n, L.u(30))
        for i, ((ic, title, body), cell) in enumerate(zip(C['features'], cells)):
            if L.orientation == 'landscape':
                cell = (cell[0], cell[1] + L.u(20), cell[2], min(cell[3], cell[1] + L.u(430)))
            p = presence(u, 0.45 + i * 0.22, None, 0.5, ease_in=out_back)
            focus = presence(u, 1.7 + i * 1.0, 1.7 + i * 1.0 + 1.1, 0.3, 0.3)
            if p <= 0:
                continue
            x0, y0, x1, y1 = cell
            with Layer(c, clamp(p * 1.5), dy=(1 - p) * L.u(60) - focus * L.u(14), bounds=(x0 - 120, y0 - 120, x1 + 120, y1 + 160)):
                ui.card(c, cell, TH, border_col=mix(TH.border, TH.accent, focus), elevation=1 + focus)
                s = L.u(84)
                compact = (y1 - y0) < L.u(330)          # short cards: icon on the left, text beside it
                ix, iy = x0 + L.u(40), (y0 + y1) / 2 - s / 2 if compact else y0 + L.u(40)
                rrect(c, ix, iy, ix + s, iy + s, L.u(22), paint(TH.accent, 0.18 + 0.2 * focus))
                icons.draw(c, ic, ix + s / 2, iy + s / 2, s * 0.5, TH.accent2, stroke=2.2)
                tx = ix + s + L.u(34) if compact else ix
                ty = (y0 + y1) / 2 - L.u(46) if compact else iy + s + L.u(44)
                mv.text(c, title, tx, ty, mv.fit('Inter', title, x1 - tx - L.u(30), L.u(38), wght=720), TH.text, anchor='top')
                mv.text_block(c, body, tx, ty + L.u(62), x1 - tx - L.u(40), mv.font('Inter', L.u(27), wght=450), TH.muted, leading=1.4)


class Stats(Scene):
    def __init__(self):
        super().__init__(8 * BEAT)

    def draw(self, c, u):
        c.clear(color(C['bg']))
        glow(c, W / 2, H / 2, L.u(1000), C['primary'], 0.2 + 0.08 * Beats(C['bpm']).pulse(u, 5))
        n = len(C['stats'])
        area = layout.inset(L.safe('title'), L.u(40))
        cells = layout.split_h(area, [1] * n, L.u(40)) if L.orientation != 'portrait' else layout.split_v(area, [1] * n, L.u(40))
        size = L.u(150 if L.orientation != 'portrait' else 170)
        for (val, fmt, _), cell in zip(C['stats'], cells):   # one size that fits the widest number
            size = min(size, mv.fit(DISPLAY, fmt.format(val), layout.width(cell) * 0.92, size, wght=850).getSize())
        fnum = mv.font(DISPLAY, size, wght=850)
        for i, ((val, fmt, label), cell) in enumerate(zip(C['stats'], cells)):
            cx, cy = layout.center(cell)
            a = presence(u, 0.2 + i * 0.25, None, 0.4)
            with Layer(c, a, dy=(1 - a) * L.u(40)):
                kinetic.counter(c, cx, cy - L.u(30), fnum, u, 0.2 + i * 0.25, 1.4, 0, val, fmt, '#FFFFFF', align='center')
                mv.text(c, label, cx, cy + L.u(90), mv.font('Inter', L.u(34), wght=500), TH.muted, align='center')
            if i:
                if L.orientation != 'portrait':
                    c.drawLine(cell[0] - L.u(20), cy - L.u(110), cell[0] - L.u(20), cy + L.u(110), paint(TH.border, a, stroke=2))


class CTA(Scene):
    def __init__(self):
        super().__init__(9 * BEAT, entry=(W / 2, H * 0.36))

    def draw(self, c, u):
        background(c, u + 7, glow_at=(0.5, 0.4))
        cx = W / 2
        top = H * (0.30 if L.orientation != 'portrait' else 0.28)
        mark(c, cx, top, L.u(150), u, 0.1)
        kinetic.reveal(c, C['name'], cx, top + L.u(120), mv.font(DISPLAY, L.u(76), wght=850), u, 0.35, by='word',
                       align='center', anchor='top')
        bw, bh = L.u(360), L.u(92)
        by = top + L.u(260)
        p = presence(u, 0.9, None, 0.5, ease_in=out_back)
        with Layer(c, clamp(p * 1.5), scale=0.8 + 0.2 * p, pivot=(cx, by + bh / 2)):
            ui.focus_ring(c, (cx - bw / 2, by, cx + bw / 2, by + bh), u, TH, radius=bh / 2, a=seg(u, 1.4, 1.8))
            ui.button(c, (cx - bw / 2, by, cx + bw / 2, by + bh), C['cta'], TH, icon_right='arrow-right', radius=bh / 2)
        qs = L.u(190)
        qa = presence(u, 1.3, None, 0.5)
        if L.orientation == 'portrait':
            qx, qy = cx - qs / 2, by + bh + L.u(90)
            ux, uy, ua = cx, qy + qs + L.u(56), 'center'
        else:
            qx, qy = W - L.safe('title')[0] - qs, H - L.safe('title')[1] - qs
            ux, uy, ua = cx, by + bh + L.u(80), 'center'
        with Layer(c, qa, dy=(1 - qa) * L.u(30)):
            qr(c, 'https://' + C['url'], qx, qy, qs, logo=lambda cc, x, y, s: cc.drawCircle(x, y, s / 2, paint(C['primary'])))
            mv.text(c, C['url'], ux, uy, mv.font('Inter', L.u(34), wght=600), TH.muted, align=ua)


SCENES = [Intro(), Hook(), Demo(), Features(), Stats(), CTA()]
WIPE = lambda c, A, B, p, ctx: wipe(c, A, B, p, ctx, colors=(C['primary'], C['secondary']))
tl = Timeline(SCENES, (W, H), transition=crossfade, before=0.45, after=0.55,
              transitions={1: zoom_through, 2: WIPE, 3: push, 4: slide_up, 5: zoom_through})
# motion blur on the zoom and wipe joins only; push and slide_up smear themselves
video = Video(tl, tl.duration, (W, H), FPS, background=C['bg'],
              subframes=lambda t: 3 if tl.transition_at(t) in (zoom_through, WIPE) else 1)


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=C['bpm'], key='E', mode='minor', style='drive', gain=0.75, fade_in=0.0, fade_out=2.5)
    m.add(sfx.impact(), 0.25, 0.6)
    m.add(sfx.sparkle(), 1.2, 0.35, reverb=0.5)
    for k in range(1, len(SCENES)):
        j = tl.start(k)
        m.add(sfx.whoosh(0.45), j - 0.45, 0.5)
    d0 = tl.start(2)
    T = SCENES[2].T
    m.add(sfx.click(), d0 + T['focus'], 0.45)
    sfx.type_clicks(m, C['prompt'], d0 + T['type_at'], T['cps'], gain=0.2)
    m.add(sfx.click(), d0 + T['send'], 0.5)
    m.add(sfx.blip(1100), d0 + T['send'] + 0.1, 0.3, reverb=0.3)
    done = d0 + T['answer'] + 0.25 + 0.8 + len(C['answer']) / STREAM_CPS + 0.2
    m.add(sfx.chime('success'), done, 0.35, reverb=0.4)
    f0 = tl.start(3)
    for i in range(len(C['features'])):
        m.add(sfx.blip(660 + 110 * i), f0 + 0.45 + i * 0.22, 0.25, reverb=0.3)
    m.add(sfx.riser(1.5), tl.start(4) - 1.5, 0.25)
    m.add(sfx.impact(1.2), tl.start(5) + 0.1, 0.45)
    m.add(sfx.sparkle(), tl.start(5) + 1.0, 0.3, reverb=0.5)
    return m.master('promo_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
