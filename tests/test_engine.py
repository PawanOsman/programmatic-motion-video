"""Engine tests: every module, plus a real parallel render with sound. About a minute.

    python tests/run_tests.py            (or: python -m pytest tests/test_engine.py)

Each test is a plain function; a failed assert names what broke.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(ROOT, 'engine')
sys.path.insert(0, ENGINE)

import numpy as np   # noqa: E402
import skia          # noqa: E402

import brand     # noqa: E402
import captions  # noqa: E402
import charts    # noqa: E402
import codeview  # noqa: E402
import fx        # noqa: E402
import icons     # noqa: E402
import kinetic   # noqa: E402
import layout    # noqa: E402
import media     # noqa: E402
import mv        # noqa: E402
import sfx       # noqa: E402
import ui        # noqa: E402


class Skip(Exception):
    """Raised when an optional dependency is missing."""


def skip(reason):
    try:
        import pytest
    except ImportError:
        raise Skip(reason)
    pytest.skip(reason)


def draw_to_array(fn, w=320, h=180, bg=skia.ColorBLACK):
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(bg)
    fn(c)
    return surf.makeImageSnapshot().toarray().copy()


def workdir():
    return tempfile.mkdtemp(prefix='mvtest-')


def run(args, cwd, env=None, timeout=600):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable] + args, cwd=cwd, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    assert r.returncode == 0, f'{" ".join(args)} failed:\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}'
    return r.stdout


# ---- time and easing ----------------------------------------------------------------------------

def test_easing_endpoints():
    for name, f in mv.EASE.items():
        assert abs(f(0.0)) < 1e-3, f'{name}(0) = {f(0.0)}'
        assert abs(f(1.0) - 1.0) < 1e-3, f'{name}(1) = {f(1.0)}'
        assert mv.ease(name) is f
    assert mv.out_back(0.6) > 1.0                          # back overshoots
    assert 0 < mv.out_cubic(0.5) < 1


def test_time_helpers():
    assert mv.tween(0.0, 1.0, 0.5, 10, 20) == 10
    assert mv.tween(2.0, 1.0, 0.5, 10, 20) == 20
    assert 10 < mv.tween(1.25, 1.0, 0.5, 10, 20) < 20
    assert mv.presence(0.5, 1.0, 3.0) == 0
    assert mv.presence(2.0, 1.0, 3.0) == 1
    assert mv.presence(3.5, 1.0, 3.0) == 0
    assert mv.keys(5.0, [(0, 0), (1, 10), (2, 4)]) == 4
    assert mv.keys(-1.0, [(0, 0), (1, 10)]) == 0
    assert mv.stagger(0.0, 0.0, 3) == 0 and mv.stagger(9.0, 0.0, 3) == 1
    assert abs(mv.spring(0.0)) < 1e-6 and abs(mv.spring(5.0) - 1) < 0.01
    for t in (0.3, 1.7, 2.9):
        assert abs(mv.wobble(t, seed=4, period=3.0) - mv.wobble(t + 3.0, seed=4, period=3.0)) < 1e-9
        assert abs(mv.wave(t, 1.5) - mv.wave(t + 1.5, 1.5)) < 1e-9
    b = mv.Beats(120)
    assert b(4) == 2.0 and b.bar(1) == 2.0
    assert mv.type_end('hello', 1.0, cps=10) == 1.5


def test_text_timing_and_graphemes():
    s = 'Hé👍🏽 ok'
    g = mv.graphemes(s)
    assert len(g) == 6, g                                  # the emoji with its skin tone is one cluster
    seen = set()
    for i in range(0, 60):
        part = mv.typed(s, i / 10, 0.0, cps=12)
        assert s.startswith(part)
        assert ''.join(mv.graphemes(part)) == part
        seen.add(part)
    assert '' in seen and s in seen
    words = mv.streamed('one two three four', 0.2, 0.0, cps=40)
    assert 'one two three four'.startswith(words)


# ---- colour and shapes ----------------------------------------------------------------------------

def test_colors():
    assert mv.rgb('#7C3AED') == (124, 58, 237)
    assert mv.rgb('#fff') == (255, 255, 255)
    assert mv.hex_color((124, 58, 237)) == '#7C3AED'
    for c in ('#7C3AED', '#22D3EE', '#101010', '#FFFFFF'):
        back = mv.from_oklab(*mv.to_oklab(c))
        assert max(abs(a - b) for a, b in zip(back, mv.rgb(c))) <= 1, (c, back)
    assert mv.hex_color(mv.mix('#FF0000', '#0000FF', 0.0)) == '#FF0000'
    assert mv.hex_color(mv.mix('#FF0000', '#0000FF', 1.0)) == '#0000FF'


def test_svg_path_parser():
    p = mv.svg_path('M3 12h18M12 3v18')
    b = p.computeTightBounds()
    assert (b.left(), b.top(), b.right(), b.bottom()) == (3, 3, 21, 21)
    arc = mv.svg_path('M2 12a10 10 0 1020 0')              # compact arc flags
    b = arc.computeTightBounds()
    assert abs(b.width() - 20) < 0.01 and abs(b.height() - 10) < 0.01, (b.width(), b.height())
    rel = mv.svg_path('m4 4 l4 0 0 4 -4 0z')
    assert rel.computeTightBounds().width() == 4


def test_path_tools():
    p = mv.svg_path('M0 0H100V100')
    assert abs(mv.path_length(p) - 200) < 0.5
    half = mv.trim(p, 0.0, 0.5)
    assert abs(mv.path_length(half) - 100) < 1.0
    pts = mv.resample(p, 50)
    assert pts.shape == (50, 2)
    m = mv.morph(mv.ngon(0, 0, 50, 3), mv.ngon(0, 0, 50, 6), 0.5)
    assert not m.isEmpty()
    m2 = mv.morph(mv.resample(mv.ngon(0, 0, 50, 3), 64), mv.resample(mv.ngon(0, 0, 50, 6), 64), 1.0)
    assert abs(m2.computeTightBounds().width() - mv.ngon(0, 0, 50, 6).computeTightBounds().width()) < 1


# ---- fonts and text -----------------------------------------------------------------------------

def test_fonts_by_name():
    for fam in ('Inter', 'JetBrains Mono', 'Space Grotesk', 'Instrument Serif', 'IBM Plex Sans Arabic'):
        assert os.path.exists(mv.font_file(fam)), fam
    assert 'wght' in mv.font_axes('Inter')
    bold, light = mv.font('Inter', 60, wght=800), mv.font('Inter', 60, wght=300)
    assert mv.width('Hello motion', bold) > mv.width('Hello motion', light)
    mv.font('Instrument Serif', 40, wght=700)              # axes a static font lacks are ignored
    assert mv.width('AB', light, tracking=0.1) > mv.width('AB', light)


def test_wrap_and_fit():
    f = mv.font('Inter', 40)
    text = 'Every frame is a pure function of time, so any moment renders on its own.'
    lines = mv.wrap(text, f, 400)
    assert len(lines) > 1 and all(mv.width(l, f) <= 400 + 1 for l in lines)
    ff = mv.fit('Inter', 'A very long headline that must fit', 500, 120)
    assert mv.width('A very long headline that must fit', ff) <= 501
    h = mv.text_block(None, text, 0, 0, 400, f, draw=False)
    assert h > 80


def test_shaping_and_rtl():
    kurdish = 'سڵاو، ئەمە ڤیدیۆیەکی کوردییە'
    blob, w = mv.shaped(kurdish, 'IBM Plex Sans Arabic', 40)
    assert blob is not None and w > 100
    tf = mv.typeface('IBM Plex Sans Arabic')
    glyphs = skia.Font(tf, 40).textToGlyphs('ڵڕێۆڤ')
    assert all(g != 0 for g in glyphs), 'a Kurdish letter has no glyph'
    p = mv.para('Mixed English and کوردی text wraps and orders itself', 300, 32, rtl=True)
    assert p.Height > 32 and p.LongestLine <= 301
    arr = draw_to_array(lambda c: p.paint(c, 10, 10), 320, 200)
    assert arr[..., :3].max() > 200                        # something white was drawn


# ---- canvas-level drawing -----------------------------------------------------------------------

def test_shapes_layers_and_clips():
    def scene(c):
        mv.glow(c, 160, 90, 120, '#7C3AED', 0.5)
        mv.rrect(c, 20, 20, 140, 80, (4, 12, 20, 28), mv.paint('#22D3EE'))
        mv.blur_shadow(c, 160, 30, 300, 90, 12)
        with mv.Layer(c, 0.5, dx=10, scale=(1.2, 0.8), rotate=10, pivot=(200, 120), blur=(3, 1)):
            c.drawPath(mv.star(200, 120, 30, 12), mv.paint('#F59E0B'))
        with mv.Clip(c, (20, 100, 120, 170), r=16):
            c.drawPaint(mv.linear(20, 0, 120, 0, ['#F43F5E', '#3B82F6']))
        mv.text(c, 'Hi', 250, 150, mv.font('Inter', 30, wght=700), '#FFFFFF', align='center', tracking=0.05)
        mv.qr(c, 'https://example.com', 260, 10, 50)
    a = draw_to_array(scene)
    b = draw_to_array(scene)
    assert np.array_equal(a, b), 'drawing is not deterministic'
    assert a[..., :3].std() > 10


def test_svg_and_logo():
    logo = mv.asset('sample/logo.svg')
    shapes, vb = mv.svg_shapes(logo)
    assert len(shapes) >= 2 and vb[2] > 0
    for style in ('pop', 'draw', 'static'):
        arr = draw_to_array(lambda c: fx.logo(c, logo, 160, 90, 120, t=0.6, t0=0.0, style=style))
        assert arr[..., :3].max() > 100, style


def test_qr_decodes():
    try:
        from pyzbar.pyzbar import decode
    except Exception:
        skip('pyzbar or the zbar library is not installed')
    from PIL import Image
    arr = draw_to_array(lambda c: mv.qr(c, 'https://example.com/qr-test', 60, 20, 200,
                                         logo=lambda cc, x, y, s: cc.drawCircle(x, y, s / 2, mv.paint('#7C3AED'))),
                        320, 240, skia.ColorWHITE)
    img = Image.fromarray(arr[..., :3]).convert('L')
    assert [d.data.decode() for d in decode(img)] == ['https://example.com/qr-test']


# ---- video, timeline, rendering -------------------------------------------------------------------

def _timeline():
    def scene(col, label):
        def draw(c, u):
            c.clear(mv.color(col))
            mv.text(c, label, 160 + 40 * math.sin(u), 90, mv.font('Inter', 40, wght=700), '#FFFFFF', align='center')
        return mv.Scene(1.0, draw, name=label)
    return mv.Timeline([scene('#1E1B4B', 'A'), scene('#064E3B', 'B'), scene('#7F1D1D', 'C')], (320, 180),
                       transition=mv.crossfade, before=0.2, after=0.2, transitions={2: None})


def test_timeline():
    tl = _timeline()
    assert tl.duration == 3.0
    assert tl.start(1) == 1.0 and tl.locate(1.25) == (1, 0.25)
    assert tl.cuts() == [2.0]
    assert tl.in_transition(1.1) and not tl.in_transition(1.5) and not tl.in_transition(2.05)
    assert tl.transition_at(0.9) is mv.crossfade and tl.transition_at(2.0) is None
    assert [d['name'] for d in tl.describe()] == ['A', 'B', 'C']


def test_video_frames():
    tl = _timeline()
    v = mv.Video(tl, tl.duration, (320, 180), 30, subframes=lambda t: 3 if tl.in_transition(t) else 1)
    assert v.frames == 90 and v.cuts == [2.0]
    f1 = v.frame(31).copy()
    f2 = v.frame(31).copy()
    assert f1.shape == (180, 320, 4) and f1.dtype == np.uint8
    assert np.array_equal(f1, f2)
    assert (f1[..., 3] == 255).all()
    for name, tr in mv.TRANSITIONS.items():
        if tr is None:
            continue
        t2 = mv.Timeline(tl.scenes[:2], (320, 180), transition=tr, before=0.3, after=0.3)
        mv.Video(t2, t2.duration, (320, 180), 30).frame(30)          # every transition draws
    v.set_scale(0.5)
    assert v.frame(10).shape == (90, 160, 4)


def test_env_size_and_fps():
    old = dict(os.environ)
    try:
        os.environ['MV_SIZE'] = '1080x1920'
        os.environ['MV_FPS'] = '30000/1001'
        assert mv.env_size() == (1080, 1920)
        assert abs(float(mv.env_fps()) - 29.97) < 0.01
    finally:
        os.environ.clear()
        os.environ.update(old)


RENDER_SCRIPT = '''
import sys
sys.path.insert(0, {engine!r})
import mv, sfx
from mv import *

W, H = mv.env_size((320, 180))
TRANSPARENT = {transparent!r}

def draw(c, t):
    if not TRANSPARENT:
        c.clear(color('#101018'))
    x = tween(t, 0.2, 0.8, 40, W - 40)
    rrect(c, x - 20, H / 2 - 20, x + 20, H / 2 + 20, 8, paint('#7C3AED'))
    text(c, '%.2f' % t, W / 2, 30, font('Inter', 22, wght=600), '#FFFFFF', align='center')

video = Video(draw, 3.0, (W, H), 30, transparent=TRANSPARENT, dither=not TRANSPARENT)

def soundtrack():
    m = sfx.Mixer(3.0)
    sfx.backing(m, bpm=120, style='pulse', fade_out=0.5)
    m.add(sfx.whoosh(0.4), 0.4, 0.5)
    m.add(sfx.chime('success'), 1.5, 0.4)
    return m.master('audio.wav', lufs=-16)

if __name__ == '__main__':
    mv.cli(video, audio=None if TRANSPARENT else soundtrack)
'''


def test_render_parallel_with_sound():
    d = workdir()
    try:
        with open(os.path.join(d, 'clip.py'), 'w', encoding='utf-8') as fh:
            fh.write(RENDER_SCRIPT.format(engine=ENGINE, transparent=False))
        out = run(['clip.py', 'render', 'out.mp4', '--workers', '2', '--preset', 'veryfast'], d)
        for fact in ('codec_name=h264', 'width=320', 'height=180', 'nb_frames=90', 'color_space=bt709',
                     'codec_name=aac', 'decode: clean'):
            assert fact in out, f'{fact} missing from:\n{out}'
        again = run(['clip.py', 'render', 'out.mp4', '--workers', '2', '--preset', 'veryfast'], d)
        assert '0 to render' in again, again                              # finished chunks are reused
        loud = sfx.loudness(os.path.join(d, 'out.mp4'))
        assert abs(loud['lufs'] + 16) < 1.5 and loud['true_peak'] <= -0.5, loud
        vertical = run(['clip.py', 'render', 'v.mp4', '--no-audio', '--start', '1', '--end', '2'], d,
                       env={'MV_SIZE': '180x320'})
        assert 'width=180' in vertical and 'height=320' in vertical and 'nb_frames=30' in vertical, vertical
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_render_alpha():
    d = workdir()
    try:
        with open(os.path.join(d, 'clip.py'), 'w', encoding='utf-8') as fh:
            fh.write(RENDER_SCRIPT.format(engine=ENGINE, transparent=True))
        out = run(['clip.py', 'render', 'out.mov', '--codec', 'prores4444', '--end', '1'], d)
        assert 'pix_fmt=yuva444p12le' in out and 'decode: clean' in out, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- sound ----------------------------------------------------------------------------------------

def test_music_theory():
    assert sfx.hz('A4') == 440.0 and sfx.midi('C4') == 60
    ch = sfx.chord('A', 'minor', 0, 3)
    assert len(ch) == 3 and abs(ch[0] - sfx.hz('A3')) < 1e-6
    assert set(sfx.STYLES) == {'ambient', 'pulse', 'drive', 'corporate', 'lofi'}


def test_backing_styles_hit_loudness():
    d = workdir()
    try:
        for style in sorted(sfx.STYLES):
            m = sfx.Mixer(6.0)
            info = sfx.backing(m, bpm=110, key='A', mode='minor', style=style)
            assert abs(info['beat'] - 60 / 110) < 1e-9 and len(info['bars']) >= 2
            path = m.master(os.path.join(d, f'{style}.wav'), lufs=-14)
            loud = sfx.loudness(path)
            assert abs(loud['lufs'] + 14) < 1.0 and loud['true_peak'] <= -1.0, (style, loud)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_mixer_loop_wraps_tails():
    d = workdir()
    try:
        m = sfx.Mixer(2.0, loop=True)
        m.add(sfx.impact(1.2), 1.6, 0.8)                    # rings past the end
        sig = sfx.load(m.write(os.path.join(d, 'loop.wav')))
        head = np.abs(sig[:, :int(0.2 * sfx.SR)]).max()
        assert head > 1e-3, 'the tail did not wrap to the start'
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_effects_and_analysis():
    for sig in (sfx.click(), sfx.blip(), sfx.whoosh(), sfx.swell(), sfx.riser(), sfx.impact(),
                sfx.chime('success'), sfx.chime('notify'), sfx.chime('error'), sfx.sparkle(),
                sfx.kick(), sfx.snare(), sfx.hat(), sfx.pad([220, 277, 330], 1.0), sfx.epiano(440), sfx.bell(880)):
        assert np.isfinite(sig).all() and np.abs(sig).max() > 0
    m = sfx.Mixer(2.0)
    sfx.backing(m, bpm=120, style='drive', fade_out=0.0)
    sfx.type_clicks(m, 'hello', 0.5)
    a = sfx.analyze(m._mix(), fps=30, bands=8)
    assert a['level'].shape == (60,) and a['bands'].shape == (60, 8)
    assert 0 <= a['level'].min() and a['level'].max() <= 1


# ---- interface, effects, type, charts -------------------------------------------------------------

def test_ui_components():
    img = media.placeholder(200, 120, seed=2)
    th_brand = ui.theme_from_brand(brand.load(mv.asset('sample/brand.json')))
    for th in (ui.DARK, ui.LIGHT, th_brand):
        def scene(c):
            ui.card(c, (10, 10, 300, 200), th)
            r = ui.window(c, (320, 10, 630, 200), th, title='App', url='example.com', loading=0.5)
            assert len(r) == 4
            ui.button(c, (20, 20, 150, 60), 'Save', th, press=0.3, icon='check')
            ui.button(c, (20, 70, 150, 110), 'Go', th, fill='#FFFFFF', icon_right='arrow-right')
            ui.text_field(c, (20, 120, 290, 160), th, value='hello', placeholder='Type', focus=1.0, t=1.0,
                          typing=True, icon='search', trailing='send')
            ui.toggle(c, 330, 60, 1.0, th)
            ui.checkbox(c, 400, 60, 0.5, th, text='Remember')
            ui.slider(c, (330, 90, 600, 110), 0.4, th)
            ui.tabs(c, (330, 120, 600, 150), th, ['One', 'Two', 'Three'], active=1.5)
            ui.badge(c, 340, 170, 'New', th, icon='sparkles')
            ui.avatar(c, 580, 170, 16, th, initials='AK', status='#22C55E')
            ui.progress_bar(c, (10, 210, 300, 222), 0.6, th)
            ui.spinner(c, 330, 220, 12, 0.7, th)
            ui.typing_dots(c, 380, 220, 0.7, th)
            ui.chat(c, (10, 230, 300, 460), th, [
                dict(role='user', text='Hi there', at=0.0),
                dict(role='bot', text='سڵاو! چۆنی؟', at=0.2, rtl=True),
                dict(role='bot', text='A streamed answer arrives word by word.', at=0.5, cps=40)], t=1.5)
            ui.list_item(c, (320, 230, 630, 290), th, 'Title', 'Subtitle', icon='folder', trailing='2m')
            ui.table(c, (320, 300, 630, 460), th, ['Name', 'Status'],
                     [['Alpha', ('badge', 'Live', '#22C55E')], ['Beta', 'Draft'], ['Gamma', 'Done']],
                     reveal=2.5, highlight=0.5)
            ui.menu(c, 10, 470, 200, ['Open', ('copy', 'Copy', 'Ctrl C')], th, active=1, p=1.0)
            ui.skeleton(c, (220, 470, 400, 520), 0.5, th)
            ui.sidebar(c, (420, 470, 630, 630), th, [('house', 'Home'), ('settings', 'Settings')], active=1, title='Acme')
            ui.toast(c, (10, 540, 300, 610), th, 'Saved', 'All changes saved', p=0.8, side='right')
            ui.tooltip(c, 200, 620, 'Tip', th, p=1.0)
            ui.steps(c, 20, 650, ['Plan', 'Build', 'Ship'], 1.5, th)
            ui.callout(c, (100, 100), (200, 60), 'Look here', th, p=1.0)
            ui.focus_ring(c, (20, 20, 150, 60), 0.5, th)
            ui.media_card(c, (330, 640, 630, 900), th, img, 'Title', 'Sub')
            ui.phone(c, (10, 700, 200, 1100), th)
            ui.laptop(c, (220, 910, 630, 1150), th)
            ui.modal(c, (640, 1200), (160, 300, 480, 520), th, 'Delete?', 'This cannot be undone.', p=1.0,
                     press=(1, 0.5), icon='trash')
            rects = ui.modal_buttons((160, 300, 480, 520), th)
            assert len(rects) == 2
        arr = draw_to_array(scene, 640, 1200)
        assert arr[..., :3].std() > 10


def test_fx_draw():
    W, H = 320, 180

    def scene(c):
        fx.mesh(c, W, H, 1.0, ['#7C3AED', '#22D3EE', '#F472B6'], bg='#0B0B10')
        fx.flow(c, W, H, 1.0)
        fx.gradient(c, (0, 0, W, H), ['#000000', '#7C3AED'], angle=45, alphas=[0.0, 0.3])
        fx.grid(c, W, H, 1.0, step=32)
        fx.floor(c, W, H, 1.0)
        fx.particles(c, W, H, 1.0, n=30)
        fx.bokeh(c, W, H, 1.0)
        fx.starfield(c, W, H, 1.0, n=80, streak=0.3)
        fx.waves(c, W, H, 1.0)
        fx.pulse_rings(c, 160, 90, 1.0)
        fx.confetti(c, 1.0, 0.5, 160, 150)
        fx.sparkle(c, 50, 50, 30, 0.5)
        fx.shine(c, (40, 40, 280, 140), 1.0, 0.7)
        fx.glass(c, (40, 40, 280, 140))
        fx.spotlight(c, W, H, 160, 90, 60)
        fx.grain(c, W, H, 1.0, amount=0.04)
        fx.vignette(c, W, H)
        fx.placeholder_mark(c, 160, 90, 60, t=1.0)
    arr = draw_to_array(scene, W, H)
    assert arr[..., :3].std() > 5


def test_fx_loops_close():
    W, H = 320, 180
    cases = [
        ('particles', 4.0, lambda c, t: fx.particles(c, W, H, t, n=40, period=4.0)),
        ('bokeh', 6.0, lambda c, t: fx.bokeh(c, W, H, t, period=6.0)),
        ('mesh', 6.0, lambda c, t: fx.mesh(c, W, H, t, ['#7C3AED', '#22D3EE'], period=6.0)),
        ('flow', 5.0, lambda c, t: fx.flow(c, W, H, t, period=5.0)),
        ('starfield', 5.0, lambda c, t: fx.starfield(c, W, H, t, n=80, period=5.0)),
        ('waves', 4.0, lambda c, t: fx.waves(c, W, H, t, period=4.0)),
        ('pulse_rings', 2.4, lambda c, t: fx.pulse_rings(c, 160, 90, t, period=2.4)),
        ('grid', 4.0, lambda c, t: fx.grid(c, W, H, t, step=32, drift=(8.0, 0.0))),
        ('floor', 4.0, lambda c, t: fx.floor(c, W, H, t, speed=0.5)),
        ('marquee', 6.0, lambda c, t: kinetic.marquee(c, 'LOOP SAFE TICKER', 90, mv.font('Inter', 30), t, W, period=6.0)),
        ('rotator', 3.6, lambda c, t: kinetic.rotator(c, ['one', 'two'], 20, 90, mv.font('Inter', 30), t, period=1.8)),
        ('weight_wave', 2.0, lambda c, t: kinetic.weight_wave(c, 'WAVE', 160, 90, 'Inter', 60, t, period=2.0)),
    ]
    for name, period, fn in cases:
        a = draw_to_array(lambda c: fn(c, 0.37), W, H)
        b = draw_to_array(lambda c: fn(c, 0.37 + period), W, H)
        diff = np.abs(a.astype(int) - b.astype(int)).max()
        assert diff <= 2, f'{name} does not repeat after {period} s (max diff {diff})'


def test_kinetic_type():
    f = mv.font('Inter', 48, wght=700)

    def scene(c):
        for i, style in enumerate(kinetic.STYLES):
            kinetic.reveal(c, 'Hello motion world', 10, 30 + 40 * i, f, 0.4, 0.0, style=style,
                           by='line' if style == 'track' else 'word', emphasis=['motion'], em_col='#FACC15')
        kinetic.reveal_rtl(c, 'سڵاو لە هەمووان', 630, 420, 'IBM Plex Sans Arabic', 40, 0.5, 0.0)
        kinetic.lines(c, ['First line', 'Second line'], 330, 30, f, 0.6, 0.0)
        kinetic.statement(c, 'Big words fill the space they are given', (330, 150, 630, 300), 'Inter', 1.0, 0.0,
                          emphasis=['space'], em_col='#22D3EE')
        kinetic.scramble(c, 'DECODED', 330, 330, f, 0.5, 0.0)
        kinetic.odometer(c, 330, 380, f, 1234.5)
        kinetic.highlight(c, (330, 400, 500, 440), 1.0, 0.5)
        kinetic.underline(c, 330, 500, 450, 1.0, 0.5)
        kinetic.strike(c, 330, 500, 420, 1.0, 0.5)
        kinetic.circle_mark(c, (330, 400, 500, 440), 1.0, 0.2)
    arr = draw_to_array(scene, 640, 480)
    assert arr[..., :3].std() > 10
    shown = []
    draw_to_array(lambda c: shown.append(kinetic.counter(c, 10, 50, f, 5.0, 0.0, 1.0, 0, 1234)))
    assert shown == ['1,234']
    font, rows = kinetic.fit_block('A statement that should wrap into a box', 'Inter', 400, 200, max_size=120)
    assert rows and all(mv.width(r, font) <= 401 for r in rows)


def test_charts():
    assert charts.compact(12900) == '12.9K' and charts.compact(1284) == '1,284' and charts.compact(4200000) == '4.2M'
    ticks = charts.nice_ticks(0, 97)
    assert ticks[0] <= 0 and ticks[-1] >= 97 and len(set(np.diff(ticks))) == 1
    for dark in (True, False):
        st = charts.style(ui.DARK if dark else ui.LIGHT, dark=dark)

        def scene(c):
            charts.bars(c, (20, 20, 300, 200), [3, 7, 5, 9], ['A', 'B', 'C', 'D'], t=0.6, st=st, highlight=3)
            charts.bars(c, (320, 20, 620, 200), [[3, 4], [5, 2], [6, 7]], ['Q1', 'Q2', 'Q3'], st=st,
                        series=['2025', '2026'], legend_names=['2025', '2026'])
            charts.bars(c, (20, 220, 300, 400), [3, 7, 5], ['A', 'B', 'C'], st=st, horizontal=True)
            charts.line(c, (320, 220, 620, 400), {'Users': [1, 3, 2, 5, 8], 'Paid': [0, 1, 1, 2, 4]},
                        ['M', 'T', 'W', 'T', 'F'], t=0.9, st=st, highlight='Paid')
            charts.donut(c, 100, 500, 70, [0.5, 0.3, 0.2], ['A', 'B', 'C'], st=st, center='42%', legend_at=(190, 450))
            charts.sparkline(c, (320, 430, 620, 470), [1, 4, 2, 6, 5, 9], st=st)
            charts.kpi(c, (320, 480, 620, 600), 'Revenue', 128400, st=st, delta=0.12, spark=[1, 3, 2, 5])
            charts.meter(c, (20, 610, 300, 640), 0.7, st=st, label='Storage')
            charts.ring(c, 400, 680, 50, 0.64, st=st, sub='done')
            charts.heatmap(c, (470, 630, 620, 740), [[1, 2, 3], [4, 5, 6]], st=st)
            charts.legend(c, 20, 700, ['One', 'Two'], [st.color(0), st.color(1)], st)
        arr = draw_to_array(scene, 640, 760, skia.ColorBLACK if dark else skia.ColorWHITE)
        assert arr[..., :3].std() > 10


def test_captions():
    cues = captions.load(mv.asset('sample/captions.srt'))
    assert len(cues) == 4 and cues[0].start == 0.4
    d = workdir()
    try:
        captions.to_srt(cues, os.path.join(d, 'a.srt'))
        again = captions.load(os.path.join(d, 'a.srt'))
        assert [(c.start, c.end, c.text) for c in again] == [(c.start, c.end, c.text) for c in cues]
        captions.to_vtt(cues, os.path.join(d, 'a.vtt'))
        assert len(captions.load(os.path.join(d, 'a.vtt'))) == 4
        with open(os.path.join(d, 'w.json'), 'w', encoding='utf-8') as fh:
            json.dump({'segments': [{'start': 0.0, 'end': 1.2, 'text': ' Hello there world',
                                     'words': [{'word': ' Hello', 'start': 0.0, 'end': 0.4},
                                               {'word': ' there', 'start': 0.4, 'end': 0.8},
                                               {'word': ' world', 'start': 0.8, 'end': 1.2}]}]}, fh)
        wc = captions.load(os.path.join(d, 'w.json'))
        assert wc[0].text.strip() == 'Hello there world' and len(captions.words_of(wc[0])) == 3
    finally:
        shutil.rmtree(d, ignore_errors=True)
    short = captions.chunk(cues, max_words=3)
    assert all(len(c.text.split()) <= 3 for c in short)
    auto = captions.from_text('One two three four five six seven eight nine ten.', t0=1.0)
    assert auto[0].start == 1.0
    assert captions.active(cues, 1.0) is cues[0] and captions.active(cues, 100) is None
    for style in ('karaoke', 'box', 'pop', 'word', 'plain'):
        for bg in ('box', 'outline', 'shadow', 'none'):
            arr = draw_to_array(lambda c: captions.draw(c, cues, 1.5, (20, 20, 620, 340), style=style, bg=bg, size=36),
                                640, 360)
            assert arr[..., :3].max() > 150, (style, bg)


def test_codeview():
    samples = {
        'python': 'def f(x):\n    return x * 2  # double\n',
        'js': 'const f = (x) => { return `v${x}`; } // js\n',
        'bash': 'for f in *.mp4; do echo "$f"; done\n',
    }
    for lang, code in samples.items():
        toks = codeview.tokens(code, lang)
        assert ''.join(t for t, _ in toks) == code, lang
    th = ui.DARK

    def scene(c):
        code = samples['python']
        codeview.editor(c, (10, 10, 630, 200), code, th, t=1.0, t0=0.0, highlight=[1], marks={1: 'add'},
                        insert=(code.index('\n    return'), '\n    x += 1', 0.5, 20))
        codeview.terminal(c, (10, 210, 630, 470), th, [
            dict(at=0.0, cmd='python main.py render out.mp4'),
            dict(at=0.8, spin='Rendering', until=1.5, done='Rendered'),
            dict(at=1.6, out='wrote out.mp4'), dict(at=1.7, ok='Done'), dict(at=1.8, err='Warning')], t=2.5)
    arr = draw_to_array(scene, 640, 480)
    assert arr[..., :3].std() > 10


def test_icons():
    names = icons.names()
    assert len(names) == 1854
    for n in ('circle-check', 'arrow-right', 'search', 'sparkles', 'house', 'mic-vocal'):
        assert icons.exists(n), n
    assert 'arrow-right' in icons.search('arrow')
    b = icons.path('house').computeTightBounds()
    assert 0 <= b.left() and b.right() <= 24 and 0 <= b.top() and b.bottom() <= 24
    arr = draw_to_array(lambda c: [icons.draw(c, 'rocket', 80, 90, 96, progress=0.5),
                                   icons.draw(c, 'heart', 240, 90, 96, fill='#F43F5E')])
    assert arr[..., :3].max() > 150


def test_brand():
    assert brand.parse_color('#abc') == '#AABBCC'
    assert brand.parse_color('rgb(255 0 0)') == '#FF0000'
    assert brand.parse_color('hsl(0 100% 50%)') == '#FF0000'
    assert brand.parse_color('222.2 84% 4.9%') == '#020817'          # shadcn bare HSL
    assert brand.parse_color('oklch(0.62 0.21 293)').startswith('#')
    assert brand.contrast('#000000', '#FFFFFF') == 21.0
    assert brand.readable('#111111') == '#FFFFFF'
    css = """
    :root { --background: oklch(1 0 0); --foreground: oklch(0.145 0 0); --primary: #7C3AED;
            --radius: 0.625rem; --font-sans: "Inter", sans-serif; }
    .dark { --background: oklch(0.145 0 0); --foreground: oklch(0.985 0 0); --primary: #A78BFA; }
    """
    light, dark = brand.from_css(css), brand.from_css(css, dark=True)
    assert light.color('primary') == '#7C3AED' and dark.color('primary') == '#A78BFA'
    assert light.color('bg') != dark.color('bg') and light.color('text') != dark.color('text')
    b = brand.load(mv.asset('sample/brand.json'))
    assert b.name and b.color('primary')
    assert len(brand.tints('#7C3AED', 9)) == 9


def test_layout():
    assert layout.size('vertical') == (1080, 1920) and layout.size('4k') == (3840, 2160)
    assert layout.size('1440x2560') == (1440, 2560)
    assert layout.Frame(3840, 2160).u(100) == 200 and layout.Frame(1080, 1920).u(100) == 100
    for W, H in ((1920, 1080), (1080, 1920), (1080, 1080)):
        fr = layout.Frame(W, H)
        for kind in ('action', 'title', 'signage', 'social'):
            x0, y0, x1, y1 = fr.safe(kind)
            assert 0 < x0 < x1 < W and 0 < y0 < y1 < H, (W, H, kind)
    cells = layout.grid((0, 0, 300, 200), 3, 2, gap=10)
    assert len(cells) == 6
    x0, y0, x1, y1 = layout.fit_rect(1600, 900, (0, 0, 800, 800))
    assert abs((x1 - x0) / (y1 - y0) - 16 / 9) < 1e-6


def test_media():
    img = media.placeholder(320, 180, seed=1, label='Photo')
    assert (img.width(), img.height()) == (320, 180)
    d = workdir()
    try:
        clip = os.path.join(d, 'src.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=30:duration=2',
                        '-pix_fmt', 'yuv420p', clip], check=True)
        info = media.probe_media(clip)
        assert info['width'] == 320 and abs(info['duration'] - 2) < 0.1
        foot = media.Footage(clip, fit=(160, 90))
        for t in (0.0, 0.5, 0.52, 1.5, 0.2):                  # forward reads, then a jump back
            fr = foot.frame(t)
            assert fr.width() >= 160 and fr.height() >= 90
            assert abs(fr.width() / fr.height() - 320 / 240) < 0.02    # aspect kept
        arr = draw_to_array(lambda c: foot.draw(c, 1.0, (0, 0, 320, 180)))
        assert arr[..., :3].std() > 10
        foot.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---- tools --------------------------------------------------------------------------------------------

def test_new_project_and_package_check():
    d = workdir()
    try:
        proj = os.path.join(d, 'hello')
        run([os.path.join(ROOT, 'tools', 'new_project.py'), proj, '--template', 'minimal'], d)
        for fn in ('main.py', 'mv.py', 'sfx.py', 'ui.py', 'README.md', os.path.join('assets', 'icons', 'lucide.json.gz')):
            assert os.path.exists(os.path.join(proj, fn)), fn
        with open(os.path.join(proj, 'main.py'), encoding='utf-8') as fh:
            assert 'repo layout' not in fh.read()
        info = json.loads(run(['main.py', 'info'], proj))
        assert info['duration'] == 4.0 and info['size'] == [1920, 1080]
        run(['main.py', 'still', '1.5', 'f.png'], proj)
        assert os.path.getsize(os.path.join(proj, 'f.png')) > 1000
    finally:
        shutil.rmtree(d, ignore_errors=True)
    run([os.path.join(ROOT, 'tools', 'package_skill.py'), '--check'], ROOT)
