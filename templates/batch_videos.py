"""Personalised batch videos: one short video per row of a CSV (a welcome card with the person's name,
company, plan, seat count, brand colour and a personal QR link). Records are validated first.

Run:   python batch_videos.py check                     validate every row, render nothing
       python batch_videos.py sheet                     contact sheet of row 0 (MV_ROW=2 for another)
       python batch_videos.py render-all out/           one MP4 per row, each rendered in parallel
                                                        (--scale 0.5 for quick previews)
       MV_ROW=1 python batch_videos.py render one.mp4   a single row
Data: CONFIG['data'] points at a CSV with the columns in REQUIRED. JSON works too (a list of objects).
"""
import csv
import json
import os
import re
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
    data=mv.asset('sample/people.csv'),
    brand='Acme Studio', url='https://acme.example/welcome?c={slug}',
    duration=6.0, bg='#0A0A10',
)
REQUIRED = ['name', 'company', 'plan', 'color', 'seats']
C = CONFIG
W, H = mv.env_size((1920, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)


def load_rows(path):
    if path.endswith('.json'):
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def check(rows):
    """Problems per row: missing fields, bad colours, numbers that are not numbers, names too long."""
    problems = []
    f = mv.font('Inter', L.u(110), wght=820)
    for i, r in enumerate(rows):
        for k in REQUIRED:
            if not str(r.get(k, '')).strip():
                problems.append(f'row {i}: missing {k}')
        if r.get('color') and not re.fullmatch(r'#[0-9a-fA-F]{6}', r['color'].strip()):
            problems.append(f"row {i}: colour {r['color']!r} is not #RRGGBB")
        if r.get('seats') and not str(r['seats']).strip().isdigit():
            problems.append(f"row {i}: seats {r['seats']!r} is not a whole number")
        if r.get('name') and mv.width('Welcome, ' + r['name'], f) > W * 0.86:
            problems.append(f"row {i}: name {r['name']!r} is long; the title will shrink to fit")
    return problems


ROWS = load_rows(C['data'])
ROW_INDEX = int(os.environ.get('MV_ROW', 0))


def make(row):
    accent = row['color'].strip()
    th = ui.DARK.with_(accent=accent, accent2=mv.hex_color(mv.mix(accent, '#FFFFFF', 0.4)), scale=L.unit)
    seats = int(row['seats'])
    link = C['url'].format(slug=slug(row['company']))

    def draw(c, t):
        c.clear(color(C['bg']))
        fx.mesh(c, W, H, t, [C['bg'], accent, mv.hex_color(mv.mix(C['bg'], accent, 0.4))], bg=C['bg'], period=12, a=0.45)
        fx.particles(c, W, H, t, n=40, col=['#FFFFFF', th.accent2], a=(0.1, 0.35))
        safe = L.safe('title')
        x = safe[0] + L.u(40)
        ui.badge(c, x, H * 0.26, row['plan'].upper() + ' PLAN', th, col='#FFFFFF', fill=accent, size=L.u(24),
                 a=presence(t, 0.2, None, 0.4))
        title = f"Welcome, {row['name'].split()[0]}"
        f = mv.fit('Inter', title, W * 0.62, L.u(120), wght=820)
        kinetic.reveal(c, title, x, H * 0.4, f, t, 0.4, by='word', style='mask', col='#FFFFFF')
        kinetic.reveal(c, f"{row['company']} is set up on {C['brand']}.", x, H * 0.4 + L.u(110),
                       mv.font('Inter', L.u(40), wght=450), t, 1.0, by='word', col='#C9C9D6', each=0.04)
        a = presence(t, 1.6, None, 0.5)
        with Layer(c, a, dy=(1 - a) * L.u(30)):
            icons.draw(c, 'users', x + L.u(24), H * 0.66, L.u(48), th.accent2)
            fn = mv.font('Inter', L.u(64), wght=800)
            kinetic.counter(c, x + L.u(70), H * 0.66, fn, t, 1.6, 1.2, 0, seats, '{:.0f}', '#FFFFFF')
            digits_w = len(str(seats)) * max(mv.width(d, fn) for d in '0123456789')   # the counter uses fixed-width digits
            mv.text(c, 'seats ready', x + L.u(70) + digits_w + L.u(20), H * 0.66, mv.font('Inter', L.u(36), wght=450), '#C9C9D6')
        qs = L.u(300)
        qx, qy = safe[2] - qs - L.u(40), H / 2 - qs / 2
        qa = presence(t, 2.2, None, 0.5, ease_in=out_back)
        with Layer(c, clamp(qa * 1.5), scale=0.8 + 0.2 * qa, pivot=(qx + qs / 2, qy + qs / 2)):
            qr(c, link, qx, qy, qs)
            mv.text(c, 'Your team link', qx + qs / 2, qy + qs + L.u(46), mv.font('Inter', L.u(28), wght=600), '#FFFFFF',
                    align='center')

    return Video(draw, C['duration'], (W, H), FPS, background=C['bg'])


video = make(ROWS[ROW_INDEX])


def soundtrack():
    m = sfx.Mixer(C['duration'])
    sfx.backing(m, bpm=100, key='C', mode='major', style='pulse', gain=0.55, fade_out=1.5)
    m.add(sfx.chime('success'), 0.4, 0.35, reverb=0.4)
    m.add(sfx.blip(990), 2.2, 0.3, reverb=0.3)
    return m.master(f'batch_audio_{ROW_INDEX}.wav', lufs=-16)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'sheet'
    if cmd == 'check':
        print('\n'.join(check(ROWS)) or f'{len(ROWS)} rows OK')
    elif cmd == 'render-all':
        out_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 'out'
        scale = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.0
        os.makedirs(out_dir, exist_ok=True)
        issues = [p for p in check(ROWS) if 'long' not in p]
        if issues:
            sys.exit('fix the data first:\n' + '\n'.join(issues))
        for i, row in enumerate(ROWS):
            os.environ['MV_ROW'] = str(i)           # render workers re-run this script and read the same row
            ROW_INDEX = i
            v = make(row)
            v.set_scale(scale)
            v.render(os.path.join(out_dir, slug(row['name']) + '.mp4'), script=os.path.abspath(__file__), audio=soundtrack())
    else:
        mv.cli(video, audio=soundtrack)
