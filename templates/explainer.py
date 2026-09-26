"""Explainer / data story: title card, an emphasised bar chart with an annotation, a two-series line
chart, a part-to-whole donut, KPI tiles and a takeaway with its source. About 30 s, calm soundtrack.

Run:   python explainer.py sheet   |   python explainer.py render explainer.mp4
The numbers in CONFIG are placeholders: replace them with real data and cite the source on screen.
Chart rules built in: one colour per series in a fixed order, emphasis by greying the rest, legends
for two or more series, values labelled selectively, no dual axes.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import charts
import fx
import kinetic
import layout
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    kicker='REPORT · 2026',
    title='How our users grew this year',
    subtitle='Six months of product data in one minute',
    bars=dict(title='Monthly active users (thousands)', labels=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
              values=[42, 47, 51, 55, 63, 71], note='+69% since January'),
    lines=dict(title='Revenue by month ($k)', x=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
               series={'2025': [110, 118, 121, 130, 128, 140], '2026': [124, 139, 151, 170, 188, 214]}),
    donut=dict(title='Where requests come from', labels=['Chat', 'Voice', 'Images', 'Other'], values=[46, 27, 18, 9],
               center='3.1M', sub='requests'),
    kpis=[('Paying teams', 1840, None, 0.22), ('Avg. response', 420, '{:.0f} ms', -0.15), ('Uptime', 99.95, '{:.2f}%', 0.001)],
    takeaway='Growth came from voice and Kurdish-language features.',
    source='Source: example data for this template. Replace with your own.',
    accent='#2563EB',
)
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
TH = ui.LIGHT.with_(accent=C['accent'], bg='#F6F6F3', scale=L.unit)
ST = charts.style(TH, accent=C['accent'])
SAFE = L.safe('title')


def page(c, u, title=None, n=None):
    c.clear(color(TH.bg))
    if title:
        kinetic.reveal(c, title, SAFE[0], SAFE[1] + L.u(30), mv.font('Inter', L.u(54), wght=760), u, 0.1, by='word',
                       col=TH.text, anchor='top', each=0.05)
    if n is not None:
        mv.text(c, f'{n:02d}', SAFE[2], SAFE[1] + L.u(52), mv.font('JetBrains Mono', L.u(26), wght=600), TH.muted, align='right')


def plot_rect():
    return (SAFE[0], SAFE[1] + L.u(140), SAFE[2], SAFE[3] - L.u(20))


class TitleCard(Scene):
    def __init__(self):
        super().__init__(4.0)

    def draw(self, c, u):
        c.clear(color(TH.bg))
        fx.grid(c, W, H, u, step=L.u(64), col=TH.text, a=0.05, drift=(L.u(6), 0))
        x = SAFE[0] + L.u(20)
        ui.badge(c, x, H * 0.33, C['kicker'], TH, size=L.u(24), a=presence(u, 0.2, None, 0.4))
        f = mv.fit('Inter', C['title'], layout.width(SAFE) * 0.9, L.u(110), wght=820)
        kinetic.reveal(c, C['title'], x, H * 0.47, f, u, 0.4, by='word', style='rise', col=TH.text)
        kinetic.reveal(c, C['subtitle'], x, H * 0.47 + L.u(110), mv.font('Inter', L.u(40), wght=450), u, 1.0, by='word',
                       col=TH.muted, each=0.04)
        kinetic.underline(c, x, x + L.u(160), H * 0.47 + L.u(180), u, 1.3, 0.6, C['accent'], L.u(8))


class BarScene(Scene):
    def __init__(self):
        super().__init__(6.5)

    def draw(self, c, u):
        d = C['bars']
        page(c, u, d['title'], 1)
        r = plot_rect()
        n = len(d['values'])
        charts.bars(c, r, d['values'], d['labels'], u, 0.4, st=ST, highlight=n - 1, fmt='{:.0f}k')
        # annotation on the emphasised bar: where charts.bars puts the last column
        px0, px1 = r[0] + L.u(70), r[2]
        band = (px1 - px0) / n
        top_val = charts.nice_ticks(0, max(d['values']))[-1]
        py0, py1 = r[1] + L.u(20), r[3] - L.u(46)
        bx = px0 + band * (n - 0.5)
        by = py1 - d['values'][-1] / top_val * (py1 - py0)
        ui.callout(c, (bx - L.u(40), by + L.u(40)), (bx - L.u(360), by + L.u(10)), d['note'], TH,
                   p=seg(u, 2.2, 3.2), col=C['accent'], size=L.u(26))


class LineScene(Scene):
    def __init__(self):
        super().__init__(6.5)

    def draw(self, c, u):
        d = C['lines']
        page(c, u, d['title'], 2)
        charts.line(c, plot_rect(), d['series'], d['x'], u, 0.5, 2.4, st=ST, fmt='{:.0f}', highlight='2026')


class DonutScene(Scene):
    def __init__(self):
        super().__init__(5.5)

    def draw(self, c, u):
        d = C['donut']
        page(c, u, d['title'], 3)
        r = plot_rect()
        if L.portrait:                   # a big ring in the upper part, its legend centred below
            R = layout.width(r) * 0.33
            cx, cy = r[0] + layout.width(r) * 0.5, r[1] + layout.height(r) * 0.36
            leg = (cx - R * 0.75, cy + R * 1.45)
        else:                            # the ring on the left, its legend to the right
            R = min(layout.height(r), layout.width(r) * 0.45) * 0.42
            cx, cy = r[0] + layout.width(r) * 0.28, (r[1] + r[3]) / 2
            leg = (cx + R * 1.5, cy - R * 0.55)
        charts.donut(c, cx, cy, R, d['values'], d['labels'], u, 0.4, 1.4, st=ST, center=d['center'], center_sub=d['sub'],
                     legend_at=leg)


class KpiScene(Scene):
    def __init__(self):
        super().__init__(5.5)

    def draw(self, c, u):
        page(c, u, 'At a glance', 4)
        r = plot_rect()
        mid = (r[1] + r[3]) / 2
        cells = layout.split_h((r[0], mid - L.u(210), r[2], mid + L.u(190)), [1] * len(C['kpis']), L.u(34)) if not L.portrait \
            else layout.split_v(r, [1] * len(C['kpis']), L.u(30))
        spark = [[3, 4, 4, 5, 6, 6, 7, 9], [8, 7, 7, 6, 6, 5, 5, 4], [9, 9, 8, 9, 9, 9, 9, 9]]
        for i, ((label, val, fmt, delta), cell) in enumerate(zip(C['kpis'], cells)):
            charts.kpi(c, cell, label, val, u, 0.3 + i * 0.25, 1.4, st=ST, fmt=fmt, delta=delta,
                       delta_fmt='{:+.0%}' if abs(delta) >= 0.01 else '{:+.1%}', good_up=(i != 1), period='vs Jan',
                       spark=spark[i])


class Takeaway(Scene):
    def __init__(self):
        super().__init__(5.0)

    def draw(self, c, u):
        c.clear(color(C['accent']))
        kinetic.statement(c, C['takeaway'], layout.inset(SAFE, L.u(60)), 'Inter', u, 0.3, max_size=L.u(110), align='left',
                          col='#FFFFFF', wght=800)
        mv.text(c, C['source'], SAFE[0] + L.u(60), SAFE[3] - L.u(10), mv.font('Inter', L.u(24), wght=450), '#DBEAFE',
                a=presence(u, 1.5, None, 0.5))


tl = Timeline([TitleCard(), BarScene(), LineScene(), DonutScene(), KpiScene(), Takeaway()], (W, H),
              transition=push, before=0.4, after=0.45, transitions={1: crossfade, 5: iris})
video = Video(tl, tl.duration, (W, H), FPS, background=TH.bg)


def soundtrack():
    m = sfx.Mixer(tl.duration)
    sfx.backing(m, bpm=92, key='G', mode='major', style='corporate', gain=0.6, fade_in=1.0, fade_out=3.0)
    for k in range(1, len(tl.scenes)):
        m.add(sfx.whoosh(0.4, 300, 3500), tl.start(k) - 0.4, 0.3)
    m.add(sfx.blip(880), tl.start(1) + 2.2, 0.3, reverb=0.3)
    m.add(sfx.sparkle(), tl.start(5) + 0.3, 0.25, reverb=0.5)
    return m.master('explainer_audio.wav', lufs=-16)


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
