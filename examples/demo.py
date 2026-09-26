"""A complete example: two scenes, typing, a click, a camera move, Sorani (RTL) text, a QR code,
zoom and wipe transitions, motion blur only during transitions, and a synced soundtrack.
Run:  python demo.py sheet   |   python demo.py render demo.mp4"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import mv
import sfx
from mv import *

W, H, FPS = 1920, 1080, 30
FONT = 'Inter'                                # a family name or a font file; variable: wght 100-900
ARABIC = 'IBM Plex Sans Arabic'
INK, BG, ACCENT, SOFT = '#FAFAFA', '#0B0B12', '#7C3AED', '#A1A1AA'

# One source of truth for timing: the picture and the sound both read these.
T = dict(type_at=0.5, cps=16, click=2.6, scene1=4.0, ku_at=0.5, ku_cps=9, scene2=4.0)
HEAD = 'Every frame is code.'
KU = 'سڵاو، بەخێربێن.'
BUTTON = (760, 600, 1160, 700)               # x0, y0, x1, y1 in scene-1 layout coordinates

class Intro(Scene):
    def __init__(self):
        super().__init__(T['scene1'], exit=lambda u: self.cam.to_screen(u, 960, 650))
        self.cam = Camera(1.0, 960, 540, [(2.9, 3.9, 1.35, 960, 600)], screen=(W / 2, H / 2))
        self.ptr = Pointer([(0.8, 1500, 980), (2.3, 1010, 668)], clicks=(T['click'],), show=(0.8, 9))
    def draw(self, c, u):
        c.clear(color(BG)); glow(c, 960 + 240 * wave(u, 8), 460, 900, ACCENT, 0.35)
        c.save(); self.cam.apply(c, u)
        f = font(FONT, 110, wght=720)
        shown = typed(HEAD, u, T['type_at'], T['cps'])
        w = text(c, shown, 960 - width(HEAD, f) / 2, 420, f, INK)
        caret(c, 960 - width(HEAD, f) / 2 + w + 10, 420 + cap_height(f) / 2, cap_height(f) * 1.05, ACCENT, u,
              typing(HEAD, u, T['type_at'], T['cps']))
        e = out_back(seg(u, 1.9, 2.3))                          # the button pops in
        if e > 0:
            x0, y0, x1, y1 = BUTTON; press = self.ptr.pressed(u, T['click']); s = e * (1 - 0.06 * press)
            done = u >= T['click'] + 0.1
            c.save(); c.translate((x0 + x1) / 2, (y0 + y1) / 2); c.scale(s, s)
            shadow(c, -200, -50, 200, 50, 26, 0.5)
            rrect(c, -200, -50, 200, 50, 26, paint('#16A34A' if done else ACCENT))
            text(c, 'Rendered' if done else 'Render', 0, 0, font(FONT, 40, wght=650), INK, align='center')
            c.restore()
        self.ptr.draw(c, u)
        c.restore()

class Hello(Scene):
    def __init__(self):
        super().__init__(T['scene2'], entry=(W / 2, 420))
        self.P = Paragraphs({'Inter': FONT, 'Arabic': ARABIC})
        self.para = self.P.make('Mixed text wraps and orders itself: version 2.0 سڵاو 2026, then English again.',
                                900, 40, ['Inter', 'Arabic'], SOFT)
    def draw(self, c, u):
        c.clear(color('#101826')); glow(c, 1500, 800 + 120 * wave(u, 8), 900, '#2563EB', 0.35)
        s = typed(KU, u, T['ku_at'], T['ku_cps'])
        wv = text_shaped(c, s, 1500, 470, ARABIC, 120, INK)     # right-aligned RTL, re-shaped as it grows
        caret(c, 1500 - wv - 16, 470, 110, '#60A5FA', u, typing(KU, u, T['ku_at'], T['ku_cps']))
        with Layer(c, seg(u, 1.8, 2.4), dy=24 * (1 - out_cubic(seg(u, 1.8, 2.4)))):
            self.para.paint(c, 420, 620)
        e = out_back(seg(u, 2.4, 2.9))
        if e > 0:
            c.save(); c.translate(250, 740); c.scale(e, e)
            qr(c, 'https://example.com', -130, -130, 260, logo=lambda cc, x, y, s: cc.drawCircle(x, y, s / 2, paint(ACCENT)))
            c.restore()

tl = Timeline([Intro(), Hello()], (W, H), transition=zoom_through, before=0.7, after=0.9, loop=True,
              transitions={0: wipe})                            # the loop seam (Hello -> Intro) uses a wipe
video = Video(tl, tl.duration, (W, H), FPS, subframes=lambda t: 4 if tl.in_transition(t) else 1)

def soundtrack():
    m = sfx.Mixer(tl.duration, loop=True); b = Beats(120)
    for k in range(int(tl.duration / b(1))):                     # a quiet pulse on the beat
        m.add(sfx.kick(), b(k), 0.5, bus='drums'); m.duck([b(k)])
    m.add(sfx.pad([sfx.hz(n) for n in ('A3', 'C4', 'E4')], tl.duration), 0, 0.5, bus='music')
    for i in range(len(HEAD)):                                   # one key click per typed character
        m.add(sfx.click(0.8), T['type_at'] + i / T['cps'], 0.25, pan=0.1)
    m.add(sfx.click(1.0), T['click'], 0.5); m.add(sfx.blip(1320), T['click'] + 0.05, 0.35, reverb=0.4)
    m.add(sfx.whoosh(0.7), T['scene1'] - 0.7, 0.5)               # peaks exactly on the join
    for i in range(len(KU)): m.add(sfx.click(0.7), T['scene1'] + T['ku_at'] + i / T['ku_cps'], 0.22)
    m.add(sfx.blip(990), T['scene1'] + 2.4, 0.3, reverb=0.4)
    m.add(sfx.whoosh(0.6, 6000, 300), tl.duration - 0.6, 0.4)    # wipe back to the start
    return m.master('demo.wav', lufs=-14)

if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
