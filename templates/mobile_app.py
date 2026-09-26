"""Mobile app demo: a phone plays a chat conversation (typed question, streamed answer, a message in
Kurdish, a notification) while headline and feature points appear beside it. About 16 s.

Run:   python mobile_app.py sheet   |   python mobile_app.py render mobile_app.mp4
Sizes: landscape puts the phone on the right; MV_SIZE=1080x1920 stacks the headline above it.
Swap in the real app's name, messages and screens before delivery.
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
    app='Acme Assistant', status='Online',
    headline='Your assistant, in your language.',
    points=[('messages-square', 'Answers in seconds'), ('languages', 'Speaks Kurdish, Arabic and English'),
            ('bell-ring', 'Reminds you on time')],
    question='Remind me to call the clinic tomorrow',
    answer='Done. I will remind you tomorrow at 9:00 to call the clinic.',
    kurdish='سوپاس، زۆر باشە!',
    notification=('Reminder', 'Call the clinic · 9:00'),
    cta='Get the app', url='acme.example/app',
    primary='#7C3AED', bg='#0B0B12',
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.DARK.with_(accent=C['primary'], accent2=mv.hex_color(mv.mix(C['primary'], '#FFFFFF', 0.35)), bg='#101018')

T = dict(phone_in=0.3, type_at=1.6, cps=18)
T['send'] = type_end(C['question'], T['type_at'], T['cps']) + 0.35
T['bot'] = T['send'] + 0.5
T['bot_done'] = T['bot'] + 0.8 + len(C['answer']) / 42
T['ku'] = T['bot_done'] + 0.9
T['notify'] = T['ku'] + 1.3
T['cta'] = T['notify'] + 2.0
T['end'] = T['cta'] + 3.0

if L.orientation == 'landscape':
    PH = L.u(930)
    PHONE = layout.anchor((W * 0.55, 0, W * 0.95, H), PH / 2.05, PH)
else:
    PH = min(H * 0.56, W * 0.95 * 2.05)
    PHONE = layout.anchor((0, H * 0.36, W, H * 0.98), PH / 2.05, PH, 'top')


class PhoneDemo(Scene):
    def __init__(self):
        super().__init__(T['end'])
        self.msgs = [dict(role='user', text=C['question'], at=T['send']),
                     dict(role='bot', text=C['answer'], at=T['bot'], cps=42, think=0.8),
                     dict(role='user', text=C['kurdish'], at=T['ku'], rtl=True)]

    def draw(self, c, u):
        c.clear(color(C['bg']))
        fx.mesh(c, W, H, u, [C['bg'], C['primary'], '#0E7490'], bg=C['bg'], period=20, size=0.5, a=0.45)
        fx.particles(c, W, H, u, n=40, period=20, col=['#FFFFFF', TH.accent2], a=(0.1, 0.4))
        self.copy(c, u)
        p = presence(u, T['phone_in'], None, 0.9, ease_in=out_expo)
        px0, py0, px1, py1 = PHONE
        with Layer(c, clamp(p * 1.4), dy=(1 - p) * L.u(260), rotate=(1 - p) * 6, pivot=((px0 + px1) / 2, py1)):
            scr = ui.phone(c, PHONE, TH, clock='9:41')
            self.app(c, u, scr)

    def app(self, c, u, scr):
        x0, y0, x1, y1 = scr
        w = x1 - x0
        s = w / 310          # app designed 310 units wide: larger than a real phone UI, so it reads on video
        head = y0 + 60 * s
        c.drawLine(x0, head, x1, head, paint(TH.border, 1, stroke=1.2 * s))
        ui.avatar(c, x0 + 36 * s, y0 + 30 * s, 17 * s, TH, col=TH.accent)
        icons.draw(c, 'sparkles', x0 + 36 * s, y0 + 30 * s, 17 * s, '#FFFFFF')
        mv.text(c, C['app'], x0 + 64 * s, y0 + 22 * s, mv.font('Inter', 15 * s, wght=650), TH.text)
        c.drawCircle(x0 + 68 * s, y0 + 41 * s, 3.5 * s, paint(TH.success))
        mv.text(c, C['status'], x0 + 76 * s, y0 + 41 * s, mv.font('Inter', 11.5 * s, wght=450), TH.muted)
        icons.draw(c, 'phone', x1 - 60 * s, y0 + 30 * s, 18 * s, TH.muted)
        icons.draw(c, 'ellipsis-vertical', x1 - 26 * s, y0 + 30 * s, 18 * s, TH.muted)
        ui.chat(c, (x0, head, x1, y1 - 64 * s), TH, self.msgs, u, size=15 * s, gap=9 * s, pad=12 * s, max_frac=0.84)
        val = typed(C['question'], u, T['type_at'], T['cps']) if u < T['send'] else ''
        ui.text_field(c, (x0 + 12 * s, y1 - 54 * s, x1 - 60 * s, y1 - 10 * s), TH, val, 'Message', focus=1.0 if val else 0.0,
                      t=u, typing=typing(C['question'], u, T['type_at'], T['cps']), size=14 * s, radius=22 * s)
        ui.button(c, (x1 - 52 * s, y1 - 54 * s, x1 - 10 * s, y1 - 10 * s), '', TH, icon='arrow-up', radius=22 * s,
                  press=seg(u, T['send'] - 0.12, T['send']) * (1 - seg(u, T['send'] + 0.05, T['send'] + 0.3)))
        n = presence(u, T['notify'], T['notify'] + 2.6, 0.45, 0.35)
        if n > 0:
            ui.toast(c, (x0 + 10 * s, y0 + 8 * s, x1 - 10 * s, y0 + 76 * s), TH, C['notification'][0], C['notification'][1],
                     icon='bell-ring', col=TH.warning, p=n)

    def copy(self, c, u):
        if L.orientation == 'landscape':
            box = (L.safe('title')[0] + L.u(20), H * 0.16, W * 0.52, H * 0.48)
            px, py, gap = box[0], H * 0.6, L.u(92)
            align = 'left'
        else:
            box = (L.u(70), H * 0.05, W - L.u(70), H * 0.19)
            px, py, gap = L.u(110), H * 0.24, L.u(62)
            align = 'center'
        kinetic.statement(c, C['headline'], box, 'Inter', u, 0.4, max_size=L.u(92), align=align, wght=820, valign='bottom')
        events = [T['send'], T['ku'], T['notify']]
        for i, ((ic, label), te) in enumerate(zip(C['points'], events)):
            a = presence(u, te - 0.2, None, 0.5)
            if a <= 0 or (L.orientation != 'landscape' and i > 0 and u < te):
                continue
            y = py + i * gap if L.orientation == 'landscape' else py
            if L.orientation != 'landscape':    # one point at a time under the headline
                nxt = events[i + 1] - 0.3 if i + 1 < len(events) else 1e9
                a *= 1 - seg(u, nxt - 0.3, nxt)
                if a <= 0:
                    continue
            with Layer(c, a, dx=(1 - a) * -L.u(30)):
                size = L.u(58)
                fl = mv.font('Inter', L.u(34), wght=560)
                if L.orientation == 'landscape':
                    x = px
                else:
                    x = W / 2 - (size + L.u(22) + mv.width(label, fl)) / 2
                rrect(c, x, y - size / 2, x + size, y + size / 2, L.u(16), paint(TH.accent, 0.22))
                icons.draw(c, ic, x + size / 2, y, size * 0.52, TH.accent2)
                mv.text(c, label, x + size + L.u(22), y, fl, TH.text)
        ca = presence(u, T['cta'], None, 0.5, ease_in=out_back)
        if ca > 0:
            if L.orientation == 'landscape':
                bx, by = px, py + 3 * gap
            else:
                bx, by = W / 2 - L.u(170), H * 0.24 + L.u(70)
            with Layer(c, clamp(ca * 1.5), scale=0.85 + 0.15 * ca, pivot=(bx, by)):
                ui.button(c, (bx, by - L.u(10), bx + L.u(340), by + L.u(76)), C['cta'], TH, icon='download', radius=L.u(43))
                if L.orientation == 'landscape':
                    mv.text(c, C['url'], bx + L.u(370), by + L.u(33), mv.font('Inter', L.u(28), wght=500), TH.muted)


scene = PhoneDemo()
tl = Timeline([scene], (W, H))
video = Video(tl, tl.duration, (W, H), FPS, background=C['bg'])


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=104, key='D', mode='minor', style='pulse', gain=0.6, fade_in=0.8, fade_out=2.5)
    m.add(sfx.whoosh(0.6, 200, 2500), T['phone_in'], 0.35)
    sfx.type_clicks(m, C['question'], T['type_at'], T['cps'], gain=0.16)
    m.add(sfx.blip(990), T['send'], 0.3, reverb=0.2)
    m.add(sfx.blip(760), T['bot'], 0.22, reverb=0.2)
    m.add(sfx.blip(990), T['ku'], 0.3, reverb=0.2)
    m.add(sfx.chime('notify'), T['notify'], 0.35, reverb=0.3)
    m.add(sfx.sparkle(), T['cta'], 0.3, reverb=0.4)
    return m.master('mobile_audio.wav', lufs=-14)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
