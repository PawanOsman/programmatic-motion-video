"""Photo slideshow (real estate, e-commerce, events): slow Ken Burns moves, an info card per photo
with title, details, badges and price, then a contact card with a QR code. About 23 s.

Run:   python slideshow.py sheet   |   python slideshow.py render slideshow.mp4
Photos: list image paths in CONFIG['slides'] (JPG/PNG/WebP); missing ones show a labelled placeholder.
Cut-outs: remove backgrounds with rembg first when products should float on colour.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import fx
import icons
import kinetic
import layout
import media
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    title='Riverside Residences', kicker='NOW SELLING',
    slides=[
        dict(image=None, title='Light-filled living room', detail='South-facing, floor-to-ceiling glass', price='$420,000',
             badges=[('bed-double', '3 bed'), ('bath', '2 bath'), ('ruler', '140 m²')]),
        dict(image=None, title='Chef\'s kitchen', detail='Quartz counters, integrated appliances', price=None,
             badges=[('flame', 'Gas hob'), ('refrigerator', 'Built-in')]),
        dict(image=None, title='Private terrace', detail='18 m² with river views', price=None,
             badges=[('sun', 'Sunset side'), ('trees', 'Park next door')]),
        dict(image=None, title='Rooftop pool', detail='Shared with 24 homes', price=None,
             badges=[('waves-ladder', 'Heated'), ('dumbbell', 'Gym')]),
    ],
    contact=('Sara Jalal', 'Sales Manager', '+964 750 000 0000'),       # placeholder contact
    url='riverside.example',
    accent='#0EA5E9', ink='#FFFFFF', panel='#0B1220',
    slide_s=4.2,
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.DARK.with_(accent=C['accent'], accent2=C['accent'], scale=L.unit)


def photo(i, label=True):
    s = C['slides'][i]
    if s.get('image') and os.path.exists(s['image']):
        return image(s['image'])
    pw, ph = (1600, round(1600 * H / W)) if W >= H else (round(1600 * W / H), 1600)    # the frame's shape
    return media.placeholder(pw, ph, seed=i + 3, label=f"Photo {i + 1}: {s['title']}" if label else None)


class Intro(Scene):
    def __init__(self):
        super().__init__(3.2)

    def draw(self, c, u):
        cover(c, photo(0, label=False), 0, 0, W, H, zoom=1.12 - 0.04 * seg(u, 0, 3.2))
        c.drawRect(mv.rect(0, 0, W, H), paint('#000000', 0.45))
        cx, cy = W / 2, H / 2
        ui.badge(c, cx, cy - L.u(120), C['kicker'], TH, col='#FFFFFF', fill=C['accent'], align='center', size=L.u(26),
                 a=presence(u, 0.2, None, 0.4))
        f = mv.fit('Inter', C['title'], W * 0.85, L.u(120), wght=800)
        kinetic.reveal(c, C['title'], cx, cy + L.u(20), f, u, 0.45, by='word', style='mask', align='center', col=C['ink'])
        kinetic.underline(c, cx - L.u(90), cx + L.u(90), cy + L.u(120), u, 1.1, 0.6, C['accent'], L.u(6))


class Slide(Scene):
    def __init__(self, i):
        super().__init__(C['slide_s'])
        self.i, self.s = i, C['slides'][i]

    def draw(self, c, u):
        s = self.s
        # alternate the direction of the slow move from slide to slide
        d = 1 if self.i % 2 == 0 else -1
        cover(c, photo(self.i), 0, 0, W, H, zoom=1.02 + 0.08 * seg(u, 0, C['slide_s'] + 1), fx=0.5 + 0.08 * d * seg(u, 0, C['slide_s']))
        c.drawRect(mv.rect(0, H * 0.45, W, H), mv.linear(0, H * 0.45, 0, H, ['#000000', '#000000'], [0.0, 0.7]))
        safe = L.safe('title')
        fh = mv.font('Inter', L.u(58), wght=780)
        fd = mv.font('Inter', L.u(30), wght=450)
        bh = L.u(56)
        card_w = max(mv.width(s['title'], fh), mv.width(s['detail'], fd)) + L.u(90)
        n_badges = len(s['badges'])
        card_h = L.u(180) + (bh + L.u(24) if n_badges else 0)
        x0, y1 = safe[0], safe[3]
        y0 = y1 - card_h
        p = presence(u, 0.35, C['slide_s'] - 0.2, 0.6, 0.35)
        with Layer(c, p, dx=(1 - p) * -L.u(60), bounds=(x0 - 100, y0 - 100, x0 + card_w + 100, y1 + 100)):
            rrect(c, x0, y0, x0 + card_w, y1, L.u(20), paint(C['panel'], 0.82))
            c.drawRect(mv.rect(x0, y0 + L.u(24), x0 + L.u(6), y0 + L.u(94)), paint(C['accent']))
            mv.text(c, s['title'], x0 + L.u(44), y0 + L.u(40), fh, C['ink'], anchor='top')
            mv.text(c, s['detail'], x0 + L.u(44), y0 + L.u(122), fd, '#CBD5E1', anchor='top')
            bx = x0 + L.u(44)
            for k, (ic, lab) in enumerate(s['badges']):
                a = presence(u, 0.8 + k * 0.15, None, 0.35, ease_in=out_back)
                r = ui.badge(c, bx, y1 - L.u(40) - bh / 2, lab, TH, col='#FFFFFF', size=L.u(24), icon=ic, a=a)
                bx = r[2] + L.u(14)
        if s.get('price'):
            pp = presence(u, 1.0, C['slide_s'] - 0.2, 0.5, 0.3, ease_in=out_back)
            f = mv.font('Inter', L.u(64), wght=820)
            pw = mv.width(s['price'], f) + L.u(70)
            px1, py1 = (safe[2], y0 - L.u(28)) if L.portrait else (safe[2], safe[3])   # above the card in portrait
            with Layer(c, clamp(pp * 1.5), scale=0.85 + 0.15 * pp, pivot=(px1 - pw / 2, py1 - L.u(60))):
                rrect(c, px1 - pw, py1 - L.u(120), px1, py1, L.u(60), paint(C['accent']))
                mv.text(c, s['price'], px1 - pw / 2, py1 - L.u(60), f, '#FFFFFF', align='center')
        # progress ticks: which photo of how many
        n = len(C['slides'])
        for k in range(n):
            on = 1.0 if k == self.i else 0.35
            x = safe[2] - (n - k) * L.u(46)
            rrect(c, x, safe[1], x + L.u(34), safe[1] + L.u(6), L.u(3), paint('#FFFFFF', on))


class Contact(Scene):
    def __init__(self):
        super().__init__(4.5)

    def draw(self, c, u):
        c.clear(color(C['panel']))
        fx.mesh(c, W, H, u, [C['panel'], C['accent'], '#1E3A8A'], bg=C['panel'], period=12, a=0.4)
        name, role, phone_ = C['contact']
        cx = W * (0.36 if not L.portrait else 0.5)
        cy = H * 0.5
        a = presence(u, 0.2, None, 0.5)
        with Layer(c, a, dy=(1 - a) * L.u(30)):
            ui.avatar(c, cx - L.u(250), cy - L.u(60), L.u(70), TH, ''.join(w[0] for w in name.split()[:2]), col=C['accent'])
            mv.text(c, name, cx - L.u(150), cy - L.u(90), mv.font('Inter', L.u(54), wght=780), '#FFFFFF')
            mv.text(c, role, cx - L.u(150), cy - L.u(30), mv.font('Inter', L.u(32), wght=450), '#CBD5E1')
            icons.draw(c, 'phone', cx - L.u(250), cy + L.u(90), L.u(40), C['accent'])
            mv.text(c, phone_, cx - L.u(200), cy + L.u(90), mv.font('Inter', L.u(44), wght=650), '#FFFFFF')
        qs = L.u(300)
        qx = W * 0.62 if not L.portrait else W / 2 - qs / 2
        qy = cy - qs / 2 if not L.portrait else cy + L.u(260)
        qa = presence(u, 0.6, None, 0.5, ease_in=out_back)
        with Layer(c, clamp(qa * 1.5), scale=0.8 + 0.2 * qa, pivot=(qx + qs / 2, qy + qs / 2)):
            qr(c, 'https://' + C['url'], qx, qy, qs)
            mv.text(c, C['url'], qx + qs / 2, qy + qs + L.u(50), mv.font('Inter', L.u(32), wght=600), '#FFFFFF', align='center')


SCENES = [Intro()] + [Slide(i) for i in range(len(C['slides']))] + [Contact()]
tl = Timeline(SCENES, (W, H), transition=crossfade, before=0.5, after=0.6, transitions={len(SCENES) - 1: zoom_through})
video = Video(tl, tl.duration, (W, H), FPS, background='#000000')


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=96, key='F', mode='major', style='corporate', gain=0.65, fade_in=1.0, fade_out=3.0)
    for k in range(1, len(SCENES)):
        m.add(sfx.whoosh(0.5, 300, 2500), tl.start(k) - 0.5, 0.2)
    for i, s in enumerate(C['slides']):
        if s.get('price'):
            m.add(sfx.blip(990), tl.start(1 + i) + 1.0, 0.3, reverb=0.3)
    return m.master('slideshow_audio.wav', lufs=-16)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
