"""Code walkthrough: an editor types a function with syntax highlighting, a line is spotlighted and
explained, a change lands as a diff, and a terminal runs it. About 20 s.

Run:   python code_walkthrough.py sheet   |   python code_walkthrough.py render code.mp4
Put real code in CONFIG (highlighting uses Pygments when installed, so any language works).
Keep lines short (under ~60 characters) so they stay legible on video.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import codeview
import fx
import kinetic
import layout
import mv
import sfx
import ui
from mv import *

CODE = '''import mv

def draw(c, t):
    x = mv.tween(t, 0.5, 0.8, -300, 960)
    mv.text(c, "Hello", x, 540, FONT, "#FFF")

video = mv.Video(draw, 4.0)
mv.cli(video)
'''
EDIT_AT = CODE.index('\n    mv.text(')                     # end of the tween line: press Enter, then type
EDIT = '\n    mv.glow(c, x, 540, 300, "#7C3AED")'
CONFIG = dict(
    file='hello.py', lang='python',
    steps=[
        (0.6, 'Every frame is a function of time'),
        (6.2, 'tween() moves x from -300 to 960'),
        (9.4, 'One new line adds a glow that follows it'),
        (13.6, 'Render it: frames run in parallel'),
    ],
    spotlight_line=3,                    # 0-based line explained in step 2
    added_line=4,                        # 0-based line added in step 3
    command='python hello.py render hello.mp4',
    accent='#7C3AED',
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.DARK.with_(accent=C['accent'], accent2=mv.hex_color(mv.mix(C['accent'], '#FFFFFF', 0.4)))
T = dict(type_at=1.0, cps=34, spot=6.2, change=9.4, run=13.6, end=20.0)
T['typed'] = T['type_at'] + len(CODE) / T['cps']


class Walk(Scene):
    def __init__(self):
        super().__init__(T['end'])
        base = min(W / 1920, H / 1080)
        self.cam = Camera(1.0, 960, 540, [(T['spot'] - 0.4, T['spot'] + 0.6, 1.25, 820, 470),
                                          (T['run'] - 0.5, T['run'] + 0.5, 1.0, 960, 540)], screen=(W / 2, H / 2), base=base)

    def draw(self, c, u):
        c.clear(color('#08080D'))
        fx.grid(c, W, H, u, step=L.u(56), a=0.05, kind='dots')
        glow(c, W * 0.3, H * 0.2, L.u(900), C['accent'], 0.16)
        c.save()
        self.cam.apply(c, u)
        changed = u >= T['change']
        marks = {C['added_line']: 'add'} if u >= T['change'] + 0.2 else {}
        hl = [C['spotlight_line']] if T['spot'] <= u < T['change'] else []
        editor_rect = (120, 90, 1210 if u >= T['run'] - 0.3 else 1800, 990)
        codeview.editor(c, editor_rect, CODE, TH, C['lang'], t=u, t0=T['type_at'], cps=T['cps'], title=C['file'],
                        highlight=hl, marks=marks, size=30,
                        insert=(EDIT_AT, EDIT, T['change'] + 0.3, 22) if changed else None)
        if T['run'] - 0.3 <= u:
            p = presence(u, T['run'] - 0.3, None, 0.5)
            with Layer(c, p, dx=(1 - p) * 120):
                codeview.terminal(c, (1250, 90, 1800, 990), TH, [
                    dict(cmd=C['command'], at=T['run'] + 0.3, cps=30),
                    dict(out='1 chunk, 1 to render', at=T['run'] + 1.9),
                    dict(spin='Rendering 120 frames', at=T['run'] + 2.1, until=T['run'] + 3.8, done='Rendered 120 frames'),
                    dict(ok='wrote hello.mp4 in 3s', at=T['run'] + 4.0)], u, size=24)
        c.restore()
        self.caption(c, u)

    def caption(self, c, u):
        k = max([i for i, (ts, _) in enumerate(C['steps']) if u >= ts] or [-1])
        if k < 0:
            return
        ts, text_ = C['steps'][k]
        a = presence(u, ts, None, 0.4) * (1 - seg(u, T['end'] - 0.6, T['end']))
        f = mv.font('Inter', L.u(34), wght=650)
        w = mv.width(text_, f) + L.u(110)
        cx, cy = W / 2, H - L.u(70)
        with Layer(c, a, dy=(1 - a) * L.u(20)):
            rrect(c, cx - w / 2, cy - L.u(38), cx + w / 2, cy + L.u(38), L.u(38), paint('#14141C', 0.95))
            rrect(c, cx - w / 2, cy - L.u(38), cx + w / 2, cy + L.u(38), L.u(38), paint(TH.border, 1, stroke=1.5))
            c.drawCircle(cx - w / 2 + L.u(42), cy, L.u(16), paint(C['accent']))
            mv.text(c, str(k + 1), cx - w / 2 + L.u(42), cy, mv.font('Inter', L.u(20), wght=800), '#FFFFFF', align='center')
            mv.text(c, text_, cx - w / 2 + L.u(76), cy, f, '#F4F4F6')


tl = Timeline([Walk()], (W, H))
video = Video(tl, tl.duration, (W, H), FPS, background='#08080D')


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=90, key='A', mode='minor', style='lofi', gain=0.55, fade_in=1.0, fade_out=2.0)
    sfx.type_clicks(m, CODE, T['type_at'], T['cps'], gain=0.1)
    sfx.type_clicks(m, EDIT.strip(), T['change'] + 0.3 + 4 / 22, 22, gain=0.12)
    sfx.type_clicks(m, C['command'], T['run'] + 0.3, 30, gain=0.12)
    m.add(sfx.chime('success'), T['run'] + 4.0, 0.3, reverb=0.3)
    for ts, _ in C['steps']:
        m.add(sfx.blip(880), ts, 0.2, reverb=0.3)
    return m.master('code_audio.wav', lufs=-16)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
