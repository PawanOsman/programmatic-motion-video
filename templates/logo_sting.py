"""Logo sting: the logo's outlines draw themselves, fill in on a hit, a light sweeps across, the name
and tagline arrive, then a short hold. 5 s with a riser, an impact and a sparkle.

Run:   python logo_sting.py sheet   |   python logo_sting.py render sting.mp4
Logo:  put the client's SVG path in CONFIG['logo'] (flat-colour SVGs animate part by part; for
       gradients or filters, use style='static' in fx.logo and animate the whole mark instead).
Alpha: set CONFIG['transparent'] = True and render with --codec prores4444 (sting.mov) to overlay it.
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
    logo=mv.asset('sample/logo.svg'),            # replace with the client's logo file
    name='Acme Studio',
    tagline='Videos from code',
    bg='#07070C', ink='#FFFFFF', accent='#7C3AED', glow='#A78BFA',
    hit=1.25,                                    # the moment the logo fills in (s)
    duration=5.0,
    transparent=False,
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)


def draw(c, t):
    if not C['transparent']:
        c.clear(color(C['bg']))
        glow(c, W / 2, H * 0.44, L.u(900), C['accent'], 0.18 + 0.25 * math.exp(-max(0.0, t - C['hit']) * 2.5) * (t > C['hit']))
        fx.particles(c, W, H, t, n=45, col=['#FFFFFF', C['glow']], a=(0.08, 0.35), speed=(8, 20))
    size = L.u(300)
    cx, cy = W / 2, H * 0.42
    push = 1 + 0.035 * seg(t, C['hit'], C['duration'])                     # a slow push-in during the hold
    kick = 1 + 0.06 * math.exp(-max(0.0, t - C['hit']) * 9) * (t >= C['hit'])  # a small bump on the hit
    out = 1 - seg(t, C['duration'] - 0.45, C['duration']) if not C['transparent'] else 1.0
    with Layer(c, out, scale=push * kick, pivot=(cx, cy)):
        fx.pulse_rings(c, cx, cy, max(0.0, t - C['hit']), period=10, rings=1, r0=size * 0.5, r1=size * 1.6, col=C['glow'],
                       a=0.6 * (t > C['hit']) * (1 - seg(t, C['hit'], C['hit'] + 1.2)))
        fx.logo(c, C['logo'], cx, cy, size, t, 0.15, style='draw', dur=C['hit'] - 0.15, stroke_col=C['glow'], each=0.1)
        fx.shine(c, (cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2), t, C['hit'] + 0.15, 0.8, a=0.5)
        for i, (dx, dy, s) in enumerate([(0.62, -0.5, 46), (-0.66, 0.35, 30), (0.5, 0.62, 24)]):
            fx.sparkle(c, cx + size * dx, cy + size * dy, L.u(s), seg(t, C['hit'] + 0.1 + i * 0.12, C['hit'] + 0.9 + i * 0.12))
        f = mv.fit('Inter', C['name'], W * 0.8, L.u(110), wght=820)
        kinetic.reveal(c, C['name'], cx, cy + size * 0.78, f, t, C['hit'] + 0.3, by='char', style='mask', each=0.03,
                       col=C['ink'], align='center', anchor='top', tracking=-0.02)
        kinetic.reveal(c, C['tagline'], cx, cy + size * 0.78 + f.getSize() * 1.25, mv.font('Inter', L.u(36), wght=450), t,
                       C['hit'] + 0.9, by='word', col='#B8B8C8', align='center', anchor='top', tracking=0.08)


video = Video(draw, C['duration'], (W, H), FPS, background=C['bg'], transparent=C['transparent'],
              subframes=lambda t: 3 if C['hit'] - 0.1 < t < C['hit'] + 0.35 else 1)


def soundtrack():
    m = sfx.Mixer(C['duration'])
    m.add(sfx.riser(C['hit'] - 0.1), 0.1, 0.35)
    m.add(sfx.swell(0.8), C['hit'] - 0.8, 0.3)
    m.add(sfx.impact(2.2), C['hit'], 0.8)
    m.add(sfx.sparkle(), C['hit'] + 0.1, 0.35, reverb=0.6)
    m.add(sfx.pad([sfx.hz(n) for n in ('A2', 'E3', 'A3', 'C#4')], C['duration'] - C['hit'], 900, 0.4, 1.2), C['hit'], 0.35,
          reverb=0.4, bus='music')
    m.add(sfx.bell(sfx.hz('E6'), 1.6), C['hit'] + 0.9, 0.12, reverb=0.6)
    return m.master('sting_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
