"""mv.py: the core of the motion-video engine. Skia draws every frame, ffmpeg encodes.

A video is a pure function ``draw(canvas, t)``. Nothing carries over between frames, so any
frame can be drawn alone, in any order, on any core: previews are instant, rendering runs in
parallel, and loops close exactly.

Sections: time and easing, colour and paint, shapes, paths, groups and clips, fonts and text,
complex scripts and paragraphs, images/SVG/PDF/QR, camera and pointer, scenes and transitions,
rendering, checks, command line.

Needs: skia-python, numpy, ffmpeg on PATH. Optional: uharfbuzz (complex scripts), regex (safe
typing), segno (QR), pymupdf (PDF vectors), Pillow (stills and contact sheets), pyzbar (QR check).
"""
import fractions
import functools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))


# ---- time and easing -------------------------------------------------------------------------

def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, t0, t1):
    """Progress of one moment: 0 before t0, 1 after t1, linear between."""
    if t1 <= t0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / (t1 - t0))


def linear_ease(x): return x
def smoothstep(x): x = clamp(x); return x * x * (3 - 2 * x)
def in_quad(x): return x * x
def out_quad(x): return 1 - (1 - x) ** 2
def inout_quad(x): return 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2
def in_cubic(x): return x ** 3
def out_cubic(x): return 1 - (1 - x) ** 3
def inout_cubic(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def out_quint(x): return 1 - (1 - x) ** 5
def inout_quint(x): return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2
def in_expo(x): return 0.0 if x <= 0 else 2 ** (10 * x - 10)
def out_expo(x): return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def inout_expo(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2


def in_back(x, s=1.70158): return (s + 1) * x ** 3 - s * x ** 2
def out_back(x, s=1.70158): x -= 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


def inout_back(x, s=1.70158):
    s2 = s * 1.525
    if x < 0.5:
        return (2 * x) ** 2 * ((s2 + 1) * 2 * x - s2) / 2
    return ((2 * x - 2) ** 2 * ((s2 + 1) * (x * 2 - 2) + s2) + 2) / 2


def out_elastic(x):
    if x <= 0 or x >= 1:
        return clamp(x)
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi / 3)) + 1


def out_bounce(x):
    n, d = 7.5625, 2.75
    if x < 1 / d:
        return n * x * x
    if x < 2 / d:
        x -= 1.5 / d; return n * x * x + 0.75
    if x < 2.5 / d:
        x -= 2.25 / d; return n * x * x + 0.9375
    x -= 2.625 / d; return n * x * x + 0.984375


EASE = {  # look up curves by name, e.g. from a JSON or YAML spec
    'linear': linear_ease, 'smooth': smoothstep, 'in_quad': in_quad, 'out_quad': out_quad,
    'inout_quad': inout_quad, 'in_cubic': in_cubic, 'out_cubic': out_cubic, 'inout_cubic': inout_cubic,
    'out_quint': out_quint, 'inout_quint': inout_quint, 'in_expo': in_expo, 'out_expo': out_expo,
    'inout_expo': inout_expo, 'in_back': in_back, 'out_back': out_back, 'inout_back': inout_back,
    'out_elastic': out_elastic, 'out_bounce': out_bounce,
}


def ease(name_or_fn):
    """An easing curve from its name ('out_cubic') or the function itself."""
    return EASE[name_or_fn] if isinstance(name_or_fn, str) else name_or_fn


def spring(t, stiffness=180.0, damping=12.0):
    """Damped-spring step response, t in seconds: rises to 1 with a natural overshoot."""
    if t <= 0:
        return 0.0
    w0 = math.sqrt(stiffness)
    z = damping / (2 * w0)
    if z >= 1:
        return 1 - math.exp(-w0 * t) * (1 + w0 * t)
    wd = w0 * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))


def tween(t, t0, dur, a, b, ease=out_cubic):
    """A value travelling from a to b during [t0, t0 + dur]."""
    return lerp(a, b, ease(seg(t, t0, t0 + dur)))


def keys(t, frames, ease=inout_cubic):
    """Keyframes [(time, value), ...] with easing between neighbours; values may be numbers or tuples.
    keys(t, [(0, 0), (1.2, 300), (2.0, 280)]) holds the first and last values outside the range."""
    if t <= frames[0][0]:
        return frames[0][1]
    for (t0, a), (t1, b) in zip(frames, frames[1:]):
        if t <= t1:
            e = ease(seg(t, t0, t1))
            if isinstance(a, (tuple, list)):
                return tuple(lerp(x, y, e) for x, y in zip(a, b))
            return lerp(a, b, e)
    return frames[-1][1]


def presence(t, start, end=None, fade_in=0.35, fade_out=0.25, ease_in=out_cubic, ease_out=in_cubic):
    """0 -> 1 as something arrives at `start`, back to 0 as it leaves at `end`. Feed it to alpha,
    scale or offset so entrances and exits share one timing."""
    p = ease_in(seg(t, start, start + fade_in))
    if end is not None:
        p *= 1 - ease_out(seg(t, end - fade_out, end))
    return p


def stagger(t, t0, i, each=0.06, dur=0.5, ease=out_cubic):
    """Eased progress of item i in a staggered group that starts at t0."""
    return ease(seg(t, t0 + i * each, t0 + i * each + dur))


def wave(t, period, phase=0.0):
    """Smooth -1..1 oscillation. In a loop, use periods that divide the loop length."""
    return math.sin(2 * math.pi * (t / period + phase))


def wobble(t, seed=0, period=None, octaves=3):
    """Smooth pseudo-random motion in -1..1 (a sum of sines). With `period` it repeats exactly,
    so it is safe in loops."""
    rng = np.random.default_rng(seed)
    total, norm = 0.0, 0.0
    for k in range(octaves):
        amp = 0.5 ** k
        if period:
            f = (int(rng.integers(1, 3)) + 2 * k) / period
        else:
            f = 0.13 * (k + 1) * (1.0 + rng.random())
        total += amp * math.sin(2 * math.pi * f * t + rng.random() * 6.283)
        norm += amp
    return total / norm


class Beats:
    """Musical time: b = Beats(120); b(8) is the time of beat 8 in seconds; b.bar(2) is bar 2."""
    def __init__(self, bpm, per_bar=4):
        self.bpm, self.spb, self.per_bar = bpm, 60.0 / bpm, per_bar

    def __call__(self, n): return n * self.spb
    def bar(self, n): return n * self.per_bar * self.spb
    def of(self, t): return t / self.spb

    def pulse(self, t, decay=8.0):
        """1 on each beat, decaying to 0: drive a throb, a flash of glow or a scale bump."""
        return math.exp(-decay * ((t / self.spb) % 1.0) * self.spb)


# ---- colour and paint ------------------------------------------------------------------------

def rgb(c):
    """'#7C3AED', '#fff', '7C3AED', (124, 58, 237) or skia colour int -> (r, g, b) in 0..255."""
    if isinstance(c, str):
        h = c.strip().lstrip('#')
        if len(h) in (3, 4):
            h = ''.join(ch * 2 for ch in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if isinstance(c, int):
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255)
    return tuple(c[:3])


def hex_color(c):
    r, g, b = (int(round(clamp(v, 0, 255))) for v in rgb(c))
    return f'#{r:02X}{g:02X}{b:02X}'


def color(c, a=1.0):
    r, g, b = rgb(c)
    return skia.Color(int(round(r)), int(round(g)), int(round(b)), int(round(255 * clamp(a))))


def _to_linear(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _to_srgb(v):
    v = 12.92 * v if v <= 0.0031308 else 1.055 * max(v, 0.0) ** (1 / 2.4) - 0.055
    return clamp(v) * 255.0


def to_oklab(c):
    """sRGB colour -> OKLab (L, a, b): a perceptual space for blends and palettes."""
    r, g, b = (_to_linear(v) for v in rgb(c))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(L, a, b):
    """OKLab -> (r, g, b) in 0..255, clipped to the sRGB gamut."""
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            _to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            _to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def mix(c1, c2, t, space='oklab'):
    """Blend two colours. OKLab (default) keeps blends even and avoids muddy middles; 'srgb' is plain."""
    t = clamp(t)
    if space == 'srgb':
        a, b = rgb(c1), rgb(c2)
        return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
    a, b = to_oklab(c1), to_oklab(c2)
    return from_oklab(*(a[i] + (b[i] - a[i]) * t for i in range(3)))


def paint(c='#FFFFFF', a=1.0, stroke=None, cap='round', blend=None, aa=True):
    """A fill paint, or a stroke paint when stroke=width. cap: 'round', 'butt' or 'square'."""
    p = skia.Paint(AntiAlias=aa)
    p.setColor(color(c, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap == 'round':
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
        elif cap == 'square':
            p.setStrokeCap(skia.Paint.kSquare_Cap)
    if blend is not None:
        p.setBlendMode(blend)
    return p


def linear(x0, y0, x1, y1, colors, alphas=None, pos=None):
    """Paint with a linear gradient from (x0, y0) to (x1, y1)."""
    alphas = alphas or [1.0] * len(colors)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)],
                                               [color(c, a) for c, a in zip(colors, alphas)], pos))
    return p


def radial(cx, cy, r, colors, alphas=None, pos=None):
    """Paint with a radial gradient centred on (cx, cy)."""
    alphas = alphas or [1.0] * len(colors)
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(cx, cy), max(r, 1e-3),
                                               [color(c, a) for c, a in zip(colors, alphas)], pos))
    return p


def glow(c, x, y, r, col, a=0.4):
    """Soft radial light: the cheapest way to give a flat background depth."""
    c.drawCircle(x, y, r, radial(x, y, r, [col, col], [a, 0.0], [0.0, 1.0]))


# ---- shapes ----------------------------------------------------------------------------------

def rect(x0, y0, x1, y1):
    return skia.Rect.MakeLTRB(x0, y0, x1, y1)


def rrect(c, x0, y0, x1, y1, r, p):
    """Rounded rectangle. r is one radius, or four (top-left, top-right, bottom-right, bottom-left)."""
    c.drawRRect(rrect_shape(x0, y0, x1, y1, r), p)


def rrect_shape(x0, y0, x1, y1, r):
    if isinstance(r, (tuple, list)):
        rr = skia.RRect()
        rr.setRectRadii(skia.Rect.MakeLTRB(x0, y0, x1, y1), [skia.Point(v, v) for v in r])
        return rr
    return skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x0, y0, x1, y1), r, r)


def poly(pts, close=True):
    path = skia.Path()
    path.addPoly([skia.Point(float(x), float(y)) for x, y in pts], close)
    return path


def ngon(cx, cy, r, n, rot=-90.0):
    """Regular polygon path with n sides."""
    return poly([(cx + r * math.cos(math.radians(rot + 360 * i / n)),
                  cy + r * math.sin(math.radians(rot + 360 * i / n))) for i in range(n)])


def star(cx, cy, r_out, r_in, points=5, rot=-90.0):
    """Star path. points=4 with a small r_in gives a sparkle."""
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + 180 * i / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return poly(pts)


def shadow(c, x0, y0, x1, y1, r, a=0.35, spread=28, dy=18, steps=6):
    """Soft drop shadow from stacked translucent round-rects (no blur filter, cheap at 4K)."""
    for k in range(steps, 0, -1):
        g = spread * k / steps
        rrect(c, x0 - g, y0 - g + dy, x1 + g, y1 + g + dy, r + g, paint('#000000', a * 0.3 * (1 - k / (steps + 1))))


def blur_shadow(c, x0, y0, x1, y1, r, a=0.4, blur=24, dy=16, col='#000000'):
    """Gaussian drop shadow for a rounded rectangle (Skia blurs round-rects fast)."""
    p = paint(col, a)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(0.1, blur / 2)))
    c.drawRRect(rrect_shape(x0, y0 + dy, x1, y1 + dy, r), p)


# ---- paths: SVG data, trimming, resampling, morphing ------------------------------------------

_SVG_TOKEN = re.compile(r'[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')


def svg_path(d):
    """SVG path data ('M3 12h18...', with arcs and relative commands) -> skia.Path."""
    toks = _SVG_TOKEN.findall(d)
    path = skia.Path()
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    last_c = last_q = None   # reflected control points for S/s and T/t

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v

    def flag():
        nonlocal i
        tok = toks[i]
        if len(tok) > 1:          # compact flags such as '01' or '1.5': the flag is one character
            toks[i] = tok[1:]
        else:
            i += 1
        return tok[0] == '1'

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]; i += 1
            if cmd in 'Zz':
                path.close(); x, y = sx, sy; last_c = last_q = None
                continue
        elif cmd is None:
            raise ValueError('SVG path data must start with a command')
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == 'M':
            x, y = ox + num(), oy + num(); path.moveTo(x, y); sx, sy = x, y
            cmd = 'l' if rel else 'L'; last_c = last_q = None
        elif C == 'L':
            x, y = ox + num(), oy + num(); path.lineTo(x, y); last_c = last_q = None
        elif C == 'H':
            x = ox + num(); path.lineTo(x, y); last_c = last_q = None
        elif C == 'V':
            y = (y if rel else 0.0) + num(); path.lineTo(x, y); last_c = last_q = None
        elif C == 'C':
            x1, y1, x2, y2 = ox + num(), oy + num(), ox + num(), oy + num()
            x, y = ox + num(), oy + num(); path.cubicTo(x1, y1, x2, y2, x, y); last_c = (x2, y2); last_q = None
        elif C == 'S':
            x1, y1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
            x2, y2 = ox + num(), oy + num()
            x, y = ox + num(), oy + num(); path.cubicTo(x1, y1, x2, y2, x, y); last_c = (x2, y2); last_q = None
        elif C == 'Q':
            x1, y1 = ox + num(), oy + num()
            x, y = ox + num(), oy + num(); path.quadTo(x1, y1, x, y); last_q = (x1, y1); last_c = None
        elif C == 'T':
            x1, y1 = (2 * x - last_q[0], 2 * y - last_q[1]) if last_q else (x, y)
            x, y = ox + num(), oy + num(); path.quadTo(x1, y1, x, y); last_q = (x1, y1); last_c = None
        elif C == 'A':
            rx, ry, rot = num(), num(), num()
            large, sweep = flag(), flag()
            x, y = ox + num(), oy + num()
            path.arcTo(rx, ry, rot, skia.Path.ArcSize.kLarge_ArcSize if large else skia.Path.ArcSize.kSmall_ArcSize,
                       skia.PathDirection.kCW if sweep else skia.PathDirection.kCCW, x, y)
            last_c = last_q = None
        else:
            raise ValueError(f'unsupported SVG path command {cmd}')
    return path


def _contours(path):
    pm = skia.PathMeasure(path, False)
    out = []
    while True:
        L = pm.getLength()
        if L > 0:
            seg_path = skia.Path()
            pm.getSegment(0, L, seg_path, True)
            out.append((seg_path, L))
        if not pm.nextContour():
            break
    return out


def path_length(path):
    return sum(L for _, L in _contours(path))


def trim(path, start=0.0, end=1.0, mode='sequential'):
    """The part of a path between two fractions of its length: draw-on effects.
    mode='sequential' draws contours one after another; 'parallel' draws every contour at once."""
    start, end = clamp(start), clamp(end)
    out = skia.Path()
    if end <= start:
        return out
    parts = _contours(path)
    total = sum(L for _, L in parts)
    pos = 0.0
    for p, L in parts:
        if mode == 'parallel':
            a, b = start * L, end * L
        else:
            a, b = start * total - pos, end * total - pos
            pos += L
        a, b = max(0.0, a), min(L, b)
        if b > a:
            pm = skia.PathMeasure(p, False)
            pm.getSegment(a, b, out, True)
    return out


def resample(path, n=200):
    """n points spaced evenly along the path's first contour, as an (n, 2) array (for morphing)."""
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    pts = []
    for k in range(n):
        p, _ = pm.getPosTan(L * k / n)
        pts.append((p.x(), p.y()))
    return np.array(pts, float)


def morph(a, b, t, close=True, n=200):
    """Blend two outlines -> path. a and b are paths (resampled to n points here) or (n, 2) arrays
    from resample(). Roll one array (np.roll) so the start points match, or the morph twists."""
    a = resample(a, n) if isinstance(a, skia.Path) else np.asarray(a, float)
    b = resample(b, n) if isinstance(b, skia.Path) else np.asarray(b, float)
    return poly(a + (b - a) * t, close)


def text_path(s, x, y, f):
    """Glyph outlines of one line of text with its baseline at (x, y), as one path. Run
    skia.Simplify(path) before stroking variable-font glyphs, which overlap contours."""
    glyphs = f.textToGlyphs(s)
    xs = np.cumsum([0.0] + list(f.getWidths(glyphs))[:-1])
    out = skia.Path()
    for g, gx in zip(glyphs, xs):
        gp = f.getPath(g)
        if gp is not None:
            out.addPath(gp, x + gx, y)
    return out


# ---- groups and clips ------------------------------------------------------------------------

class Layer:
    """Draw a group with one opacity, offset, scale, rotation or blur:

        with Layer(c, alpha=0.6, dy=20, scale=0.9, pivot=(960, 540), bounds=(x0, y0, x1, y1)):
            ...

    bounds (in coordinates before the transform) keeps the offscreen buffer small and fast.
    blur is a Gaussian sigma in pixels, or (sx, sy) for a directional smear; it is expensive, so
    give it bounds."""
    def __init__(self, c, alpha=1.0, dx=0.0, dy=0.0, bounds=None, scale=1.0, rotate=0.0, pivot=None, blur=0.0):
        self.c, self.a, self.dx, self.dy, self.b = c, clamp(alpha), dx, dy, bounds
        self.scale, self.rotate, self.pivot, self.blur = scale, rotate, pivot, blur
        self._paint = None

    def __enter__(self):
        c = self.c
        bx, by = self.blur if isinstance(self.blur, (tuple, list)) else (self.blur, self.blur)
        if self.a < 0.999 or bx > 0.05 or by > 0.05:
            self._paint = skia.Paint()
            self._paint.setAlphaf(self.a)
            b = self.b
            if bx > 0.05 or by > 0.05:
                self._filter = skia.ImageFilters.Blur(max(bx, 0.0), max(by, 0.0))   # keep a reference while drawing
                self._paint.setImageFilter(self._filter)
                if b:
                    b = (b[0] - bx * 3, b[1] - by * 3, b[2] + bx * 3, b[3] + by * 3)
            self._bounds = skia.Rect.MakeLTRB(*b) if b else None
            c.saveLayer(self._bounds, self._paint)
        else:
            c.save()
        c.translate(self.dx, self.dy)
        sx, sy = self.scale if isinstance(self.scale, (tuple, list)) else (self.scale, self.scale)
        if sx != 1 or sy != 1 or self.rotate:
            px, py = self.pivot or (0.0, 0.0)
            c.translate(px, py)
            if self.rotate:
                c.rotate(self.rotate)
            c.scale(sx, sy)
            c.translate(-px, -py)
        return c

    def __exit__(self, *exc):
        self.c.restore()


class Clip:
    """Restrict drawing to a shape:  with Clip(c, (x0, y0, x1, y1), r=24): ...
    shape: a rect tuple (with optional corner radius r), skia.Rect, skia.RRect or skia.Path."""
    def __init__(self, c, shape, r=0.0, aa=True):
        self.c, self.shape, self.r, self.aa = c, shape, r, aa

    def __enter__(self):
        c, s = self.c, self.shape
        c.save()
        if isinstance(s, skia.Path):
            c.clipPath(s, skia.ClipOp.kIntersect, self.aa)
        elif isinstance(s, skia.RRect):
            c.clipRRect(s, skia.ClipOp.kIntersect, self.aa)
        elif isinstance(s, skia.Rect):
            c.clipRect(s, skia.ClipOp.kIntersect, self.aa)
        elif self.r:
            c.clipRRect(rrect_shape(*s, self.r), skia.ClipOp.kIntersect, self.aa)
        else:
            c.clipRect(skia.Rect.MakeLTRB(*s), skia.ClipOp.kIntersect, self.aa)
        return c

    def __exit__(self, *exc):
        self.c.restore()


# ---- asset and font lookup -------------------------------------------------------------------

_EXTRA_FONT_DIRS = []
FONT_EXTS = ('.ttf', '.otf', '.ttc')


def asset_dirs():
    """Where packaged assets (fonts, icons, samples) are searched: $MV_ASSETS, ./assets, and the
    assets folder next to this engine (a project copy or the skill repository)."""
    dirs = [p for p in os.environ.get('MV_ASSETS', '').split(os.pathsep) if p]
    dirs += [os.path.join(os.getcwd(), 'assets'), os.path.join(HERE, 'assets'), os.path.join(HERE, '..', 'assets')]
    return [os.path.abspath(d) for d in dirs if os.path.isdir(d)]


def asset(rel):
    """Path of a packaged asset, e.g. asset('icons/lucide.json'); raises if missing."""
    if os.path.exists(rel):
        return rel
    for d in asset_dirs():
        p = os.path.join(d, rel)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f'asset {rel!r} not found in {asset_dirs()}')


def font_dirs():
    dirs = [p for p in os.environ.get('MV_FONTS', '').split(os.pathsep) if p]
    dirs += [os.path.join(os.getcwd(), 'fonts'), os.path.join(HERE, 'fonts')]
    dirs += [os.path.join(d, 'fonts') for d in asset_dirs()]
    dirs += _EXTRA_FONT_DIRS
    dirs += ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts'),
             os.path.expanduser('~/.local/share/fonts'), os.path.expanduser('~/Library/Fonts'),
             '/Library/Fonts', '/System/Library/Fonts', r'C:\Windows\Fonts']
    seen, out = set(), []
    for d in dirs:
        d = os.path.abspath(d)
        if d not in seen and os.path.isdir(d):
            seen.add(d); out.append(d)
    return out


def add_font_dir(path):
    """Search another folder for fonts (brand fonts, downloaded families)."""
    _EXTRA_FONT_DIRS.append(path)
    font_file.cache_clear(); _dir_fonts.cache_clear()


def _norm(s):
    return re.sub(r'\[.*?\]|[\s_\-.]', '', s.lower())


@functools.lru_cache(maxsize=None)
def _dir_fonts(d):
    out = []
    for root, _, files in os.walk(d):
        for fn in files:
            if fn.lower().endswith(FONT_EXTS):
                out.append((_norm(os.path.splitext(fn)[0]), os.path.join(root, fn)))
    return tuple(sorted(out))


@functools.lru_cache(maxsize=None)
def font_file(name):
    """A font file from a path or a family name: 'Inter', 'JetBrains Mono', 'IBM Plex Sans Arabic Bold'.
    Looks in $MV_FONTS, ./fonts, the packaged assets/fonts and the system font folders."""
    if os.path.isfile(name):
        return name
    key = _norm(os.path.splitext(os.path.basename(name))[0] if name.lower().endswith(FONT_EXTS) else name)
    for d in font_dirs():
        found = {stem: p for stem, p in _dir_fonts(d)}
        for cand in (key, key + 'regular', key + 'variable', key + 'vf', key + 'roman'):
            if cand in found:
                return found[cand]
    raise FileNotFoundError(f'font {name!r} not found. Put the file in ./fonts, call mv.add_font_dir(), '
                            f'or download it: python tools/fetch_fonts.py "{name}"')


def _tag(s):
    return int.from_bytes(s.ljust(4).encode('ascii'), 'big')


@functools.lru_cache(maxsize=None)
def font_axes(path):
    """Variable axes of a font: {'wght': (min, default, max), ...}."""
    tf = skia.Typeface.MakeFromFile(font_file(path))
    out = {}
    for a in (tf.getVariationDesignParameters() or []):
        tag = a.tag.to_bytes(4, 'big').decode('ascii', 'replace').strip()
        out[tag] = (a.min, getattr(a, 'def'), a.max)
    return out


def font_axes_safe(path):
    """font_axes(), or {} when the font is missing."""
    try:
        return font_axes(path)
    except FileNotFoundError:
        return {}


@functools.lru_cache(maxsize=None)
def typeface(path, axes=()):
    """Typeface from a font file or family name. axes=(('wght', 700), ('wdth', 90)) for variable fonts."""
    tf = skia.Typeface.MakeFromFile(font_file(path))
    if tf is None:
        raise FileNotFoundError(f'cannot load font {path}')
    if axes:
        V = skia.FontArguments.VariationPosition
        # Keep coords and pos in variables: skia only holds pointers to them until makeClone runs,
        # and a temporary would be freed first, silently dropping the axes.
        coords = V.Coordinates([V.Coordinate(_tag(k), float(v)) for k, v in axes])
        pos = V(coords)
        args = skia.FontArguments()
        args.setVariationDesignPosition(pos)
        tf = tf.makeClone(args)
    return tf


def _setup_font(f):
    f.setEdging(skia.Font.Edging.kAntiAlias)   # greyscale AA: no colour fringes after encoding
    f.setSubpixel(True)                         # smooth sub-pixel motion, no 1 px jumps
    f.setHinting(skia.FontHinting.kNone)        # hinting makes moving or scaling text wobble
    f.setLinearMetrics(True)
    return f


@functools.lru_cache(maxsize=4096)
def _font(path, size, axes):
    return _setup_font(skia.Font(typeface(path, axes), size))


def font(path, size, **axes):
    """font('Inter', 64, wght=650): a family name or file, a size in px and variable axes.
    Variable fonts default to wght 400 and, when they have one, an optical size matched to the size.
    Values are rounded so animated axes stay cacheable."""
    fa = font_axes(path)
    axes = {k: v for k, v in axes.items() if k in fa}   # static fonts simply ignore wght=...
    if 'wght' in fa and 'wght' not in axes:
        axes['wght'] = clamp(400, fa['wght'][0], fa['wght'][2])
    if 'opsz' in fa and 'opsz' not in axes:
        axes['opsz'] = clamp(size * 0.75, fa['opsz'][0], fa['opsz'][2])
    axes = {k: clamp(float(v), fa[k][0], fa[k][2]) for k, v in axes.items()}
    ax = tuple(sorted((k, round(float(v) * 2) / 2) for k, v in axes.items()))
    return _font(path, round(float(size) * 4) / 4, ax)


def cap_height(f):
    return f.getMetrics().fCapHeight


def x_height(f):
    return f.getMetrics().fXHeight


def line_height(f, leading=1.25):
    return f.getSize() * leading


# ---- text: Latin, Cyrillic, Greek -------------------------------------------------------------

def _tracked(s, f, tracking):
    glyphs = f.textToGlyphs(s)
    ws = list(f.getWidths(glyphs))
    step = tracking * f.getSize()
    xs = [0.0]
    for w in ws[:-1]:
        xs.append(xs[-1] + w + step)
    return xs, (xs[-1] + ws[-1] if ws else 0.0)


def width(s, f, tracking=0.0):
    """Advance width of one line; tracking is letter spacing in em (0.08 = 8 % of the size)."""
    if not s:
        return 0.0
    if tracking:
        return _tracked(s, f, tracking)[1]
    return f.measureText(s)


def text(c, s, x, y, f, col='#FFFFFF', a=1.0, align='left', anchor='middle', tracking=0.0, p=None):
    """One line of left-to-right text; returns its width.
    anchor='middle' centres the capitals on y, 'baseline' sits on y, 'top' hangs from y.
    tracking: letter spacing in em. p: a Paint to use instead of col/a (gradients, strokes).
    Arabic-script, Hebrew, Indic or mixed lines: use text_shaped() or para()."""
    if not s:
        return 0.0
    if tracking:
        xs, w = _tracked(s, f, tracking)
    else:
        w = f.measureText(s)
    if a <= 0 and p is None:
        return w
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    if anchor == 'middle':
        base = y + cap_height(f) / 2
    elif anchor == 'top':
        base = y + cap_height(f)
    else:
        base = y
    pt = p or paint(col, a)
    if tracking:
        c.drawTextBlob(skia.TextBlob.MakeFromPosTextH(s, xs, 0.0, f), x0, base, pt)
    else:
        c.drawString(s, x0, base, f, pt)
    return w


def wrap(s, f, max_w, tracking=0.0):
    """Greedy word wrap for space-separated scripts; keeps explicit newlines.
    CJK, Thai and mixed-direction text need para() instead."""
    lines = []
    for block in s.split('\n'):
        cur = ''
        for word in block.split(' '):
            t = (cur + ' ' + word).strip() if cur else word
            if width(t, f, tracking) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur); cur = word
        lines.append(cur)
    return lines


def text_block(c, s, x, y, max_w, f, col='#FFFFFF', a=1.0, align='left', leading=1.3, tracking=0.0, draw=True):
    """Wrapped left-to-right text whose first line's cap top is at y; returns the block height.
    draw=False only measures."""
    lines = wrap(s, f, max_w, tracking)
    lh = f.getSize() * leading
    if draw:
        for i, line in enumerate(lines):
            text(c, line, x, y + i * lh, f, col, a, align, 'top', tracking)
    return cap_height(f) + lh * (len(lines) - 1)


def fit(path, s, max_w, size, tracking=0.0, **axes):
    """The largest font, up to size, whose line fits max_w."""
    f = font(path, size, **axes)
    for _ in range(8):             # widths are not quite proportional to size (optical sizes, rounding)
        w = width(s, f, tracking)
        if w <= max_w:
            break
        size *= max_w / w * 0.995
        f = font(path, size, **axes)
    return f


@functools.lru_cache(maxsize=4096)
def graphemes(s):
    """User-perceived characters, so typing never splits an emoji or a letter from its marks."""
    try:
        import regex
        return tuple(regex.findall(r'\X', s))
    except ImportError:
        return tuple(s)


def typed(s, t, t0, cps=18.0):
    """The part of s typed by time t, at cps characters per second."""
    g = graphemes(s)
    return ''.join(g[:min(len(g), int(max(0.0, (t - t0) * cps)))])


def typing(s, t, t0, cps=18.0):
    """True while s is still being typed."""
    return t0 <= t < t0 + len(graphemes(s)) / cps


def type_end(s, t0, cps=18.0):
    """When typing s finishes."""
    return t0 + len(graphemes(s)) / cps


def streamed(s, t, t0, cps=40.0):
    """Word-by-word reveal like a streaming AI answer: whole words appear at about cps chars/s."""
    n = int(max(0.0, (t - t0) * cps))
    if n >= len(s):
        return s
    cut = s.rfind(' ', 0, n + 1)
    return s[:cut] if cut > 0 else ''


def caret(c, x, base, h, col, t, active=True, w=4):
    """Text cursor: solid while typing, blinking when idle."""
    if active or (t * 1.6) % 1 < 0.55:
        c.drawRect(skia.Rect.MakeLTRB(x, base - h, x + w, base + h * 0.22), paint(col))


# ---- complex scripts: Arabic, Kurdish, Persian, Urdu, Hebrew, Devanagari, Thai, emoji ----------

@functools.lru_cache(maxsize=None)
def _hb(path, axes=()):
    import uharfbuzz as hb
    face = hb.Face(hb.Blob.from_file_path(font_file(path)))
    f = hb.Font(face)
    if axes:
        f.set_variations(dict(axes))
    return f, face.upem


@functools.lru_cache(maxsize=16384)
def shaped(s, path, size, axes=(), features=()):
    """Shape one single-direction run with HarfBuzz -> (TextBlob or None, width). Letters change
    form with their neighbours, so a typing reveal must re-shape the growing prefix (this does)."""
    if not s:
        return None, 0.0
    import uharfbuzz as hb
    hbf, upem = _hb(path, axes)
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbf, buf, dict(features))
    sc = size / upem
    x = 0.0
    glyphs, pos = [], []
    for info, p in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append(info.codepoint)
        pos.append(skia.Point(x + p.x_offset * sc, -p.y_offset * sc))
        x += p.x_advance * sc
    if not glyphs:
        return None, 0.0
    f = _setup_font(skia.Font(typeface(path, axes), size))
    b = skia.TextBlobBuilder()
    b.allocRunPos(f, glyphs, pos)
    return b.make(), x


def text_shaped(c, s, x, base, path, size, col='#FFFFFF', a=1.0, align='right', axes=()):
    """Draw a shaped run on a baseline; right-aligned by default, as RTL copy usually is.
    Returns its width."""
    blob, w = shaped(s, path, size, tuple(axes))
    if blob is not None and a > 0:
        x0 = x - w if align == 'right' else x - w / 2 if align == 'center' else x
        c.drawTextBlob(blob, x0, base, paint(col, a))
    return w


class Paragraphs:
    """Wrapped, mixed-direction text with font fallback (Skia's paragraph engine: shaping, bidi,
    line breaking). A family is a font name or path, or (path, {'wght': 700}) to pin an axis.

        P = Paragraphs({'Inter': 'Inter', 'Arabic': 'IBM Plex Sans Arabic'})
        p = P.make(txt, 900, 44, ['Inter', 'Arabic']); p.paint(c, x, y); p.Height; p.LongestLine

    Build once per distinct text and cache it; layout is the slow part. Line spacing comes from
    the font. For quick one-off paragraphs use para()."""
    ALIGN = {'left': 'kLeft', 'right': 'kRight', 'center': 'kCenter', 'justify': 'kJustify'}

    def __init__(self, families):
        self.provider = skia.textlayout.TypefaceFontProvider()
        for name, src in families.items():
            path, axes = (src, {}) if isinstance(src, str) else src
            self.provider.registerTypeface(typeface(path, tuple(sorted(axes.items()))), name)
        self.fc = skia.textlayout.FontCollection()
        self.fc.setDefaultFontManager(self.provider)

    def make(self, s, max_w, size, families, col='#FFFFFF', a=1.0, align='left', rtl=False, bold=False, tracking=0.0):
        if rtl:
            s = chr(0x2067) + s + chr(0x2069)   # isolate as RTL (RLI...PDI) or end punctuation lands on the wrong side
        ps = skia.textlayout.ParagraphStyle()
        ps.setTextAlign(getattr(skia.textlayout.TextAlign, self.ALIGN[align]))
        ts = skia.textlayout.TextStyle()
        ts.setFontFamilies(list(families))
        ts.setFontSize(size)
        if bold:
            ts.setFontStyle(skia.FontStyle.Bold())
        if tracking:
            ts.setLetterSpacing(tracking * size)
        ts.setForegroundColor(paint(col, a))
        b = skia.textlayout.ParagraphBuilder(ps, self.fc, skia.Unicode())
        b.pushStyle(ts)
        b.addText(s)
        p = b.Build()
        p.layout(max_w)
        return p


class _TextKit:
    """Registers fonts on demand for para(): a new FontCollection each time a family is added,
    because a collection caches its lookups."""
    def __init__(self):
        self.provider = skia.textlayout.TypefaceFontProvider()
        self.names = set()
        self.fc = None

    def family(self, name, axes):
        key = f'{name}|{axes}'
        if key not in self.names:
            self.provider.registerTypeface(typeface(name, axes), key)
            self.names.add(key)
            self.fc = None
        return key

    def collection(self):
        if self.fc is None:
            self.fc = skia.textlayout.FontCollection()
            self.fc.setDefaultFontManager(self.provider)
        return self.fc


_KIT = _TextKit()
DEFAULT_FALLBACK = ('IBM Plex Sans Arabic',)


@functools.lru_cache(maxsize=4096)
def _para(s, max_w, size, fams, col, a, align, rtl, tracking):
    names = [_KIT.family(n, ax) for n, ax in fams]
    if rtl:
        s = chr(0x2067) + s + chr(0x2069)
    ps = skia.textlayout.ParagraphStyle()
    ps.setTextAlign(getattr(skia.textlayout.TextAlign, Paragraphs.ALIGN[align]))
    ts = skia.textlayout.TextStyle()
    ts.setFontFamilies(names)
    ts.setFontSize(size)
    if tracking:
        ts.setLetterSpacing(tracking * size)
    ts.setForegroundColor(paint(col, a))
    b = skia.textlayout.ParagraphBuilder(ps, _KIT.collection(), skia.Unicode())
    b.pushStyle(ts)
    b.addText(s)
    p = b.Build()
    p.layout(max_w)
    return p


def para(s, max_w, size, font='Inter', col='#FFFFFF', a=1.0, align='left', rtl=False, tracking=0.0,
         fallback=DEFAULT_FALLBACK, **axes):
    """A wrapped paragraph with shaping, bidi and font fallback, cached by its arguments.
    Returns a skia Paragraph: .paint(c, x, y) (y is the top), .Height, .LongestLine.
    para('Hello سڵاو', 600, 40, 'Inter', wght=600). Fallback fonts that are missing are skipped.
    Animate opacity with Layer rather than `a`, so the layout stays cached."""
    def spec(name, extra):
        fa = font_axes(name)
        ax = {k: v for k, v in dict(extra).items() if k in fa} if name == font else {}
        if 'wght' in fa and 'wght' not in ax:
            ax['wght'] = clamp(axes.get('wght', 400), fa['wght'][0], fa['wght'][2])
        if 'opsz' in fa and 'opsz' not in ax:
            ax['opsz'] = clamp(size * 0.75, fa['opsz'][0], fa['opsz'][2])
        return name, tuple(sorted((k, round(float(v) * 2) / 2) for k, v in ax.items()))
    fams = [spec(font, axes)]
    wght = axes.get('wght', 400)
    for fb in fallback or ():
        names = [fb]
        if not font_axes_safe(fb).get('wght'):   # a static fallback: prefer its matching weight file
            names = ([fb + ' Bold'] if wght >= 600 else [fb + ' Medium'] if wght >= 500 else []) + [fb]
        for name in names:
            try:
                font_file(name)
            except FileNotFoundError:
                continue
            fams.append(spec(name, {}))
            break
    return _para(s, float(max_w), float(size), tuple(fams), hex_color(col), round(float(a), 3), align, rtl, tracking)


# ---- images, SVG, PDF vectors, QR ------------------------------------------------------------

SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


@functools.lru_cache(maxsize=256)
def image(path):
    """Load an image once (with mipmaps, so shrinking it stays smooth)."""
    img = skia.Image.open(path)
    if img is None:
        raise FileNotFoundError(path)
    return img.withDefaultMipmaps()


def image_from_array(arr):
    """numpy uint8 array (h, w, 3 or 4) -> skia.Image."""
    arr = np.ascontiguousarray(arr)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, np.uint8)], axis=2)
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


def cover(c, img, x0, y0, x1, y1, a=1.0, zoom=1.0, fx=0.5, fy=0.5):
    """Fill a rectangle like CSS object-fit: cover. Animate zoom slowly for a Ken Burns move;
    fx, fy (0..1) choose which part stays in view."""
    iw, ih = img.width(), img.height()
    s = max((x1 - x0) / iw, (y1 - y0) / ih) * zoom
    sw, sh = (x1 - x0) / s, (y1 - y0) / s
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    c.drawImageRect(img, skia.Rect.MakeXYWH((iw - sw) * fx, (ih - sh) * fy, sw, sh),
                    skia.Rect.MakeLTRB(x0, y0, x1, y1), SAMPLING, p)


def contain(c, img, x0, y0, x1, y1, a=1.0, align=(0.5, 0.5)):
    """Fit the whole image inside a rectangle (CSS object-fit: contain); returns the drawn rect."""
    iw, ih = img.width(), img.height()
    s = min((x1 - x0) / iw, (y1 - y0) / ih)
    w, h = iw * s, ih * s
    dx, dy = x0 + (x1 - x0 - w) * align[0], y0 + (y1 - y0 - h) * align[1]
    p = skia.Paint()
    p.setAlphaf(clamp(a))
    c.drawImageRect(img, skia.Rect.MakeXYWH(dx, dy, w, h), SAMPLING, p)
    return dx, dy, dx + w, dy + h


@functools.lru_cache(maxsize=128)
def svg(path_or_markup):
    """An SVG document from a file path or from SVG markup."""
    if path_or_markup.lstrip().startswith('<'):
        data = path_or_markup.encode('utf-8')
    else:
        with open(path_or_markup, 'rb') as fh:
            data = fh.read()
    return skia.SVGDOM.MakeFromStream(skia.MemoryStream(data))


def draw_svg(c, dom, x, y, w, h):
    """Draw an SVG (with a viewBox) scaled into the box."""
    c.save()
    c.translate(x, y)
    dom.setContainerSize(skia.Size(w, h))
    dom.render(c)
    c.restore()


def _svg_matrix(tr):
    """An SVG transform attribute -> skia.Matrix (matrix, translate, scale, rotate, skewX, skewY)."""
    m = skia.Matrix()
    for fn, args in re.findall(r'(\w+)\s*\(([^)]*)\)', tr or ''):
        v = [float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', args)]
        k = skia.Matrix()
        if fn == 'matrix' and len(v) == 6:
            k.setAll(v[0], v[2], v[4], v[1], v[3], v[5], 0, 0, 1)
        elif fn == 'translate':
            k.setTranslate(v[0], v[1] if len(v) > 1 else 0.0)
        elif fn == 'scale':
            k.setScale(v[0], v[1] if len(v) > 1 else v[0])
        elif fn == 'rotate':
            k.setRotate(v[0], v[1], v[2]) if len(v) == 3 else k.setRotate(v[0])
        elif fn == 'skewX':
            k.setSkew(math.tan(math.radians(v[0])), 0)
        elif fn == 'skewY':
            k.setSkew(0, math.tan(math.radians(v[0])))
        m = skia.Matrix.Concat(m, k)
    return m


def _svg_color(v):
    v = (v or 'none').strip().lower()
    if v in ('none', 'transparent') or v.startswith('url'):
        return None
    if v.startswith('#'):
        return v
    m = re.match(r'rgba?\(([^)]*)\)', v)
    if m:
        return tuple(float(x) for x in re.split(r'[\s,/]+', m[1].strip())[:3])
    return {'white': '#FFFFFF', 'black': '#000000', 'currentcolor': '#000000'}.get(v, '#000000')


def svg_shapes(src):
    """The drawable parts of an SVG (file path or markup), for animating a logo piece by piece.
    Returns (shapes, viewbox): shapes are dicts {path, fill, stroke, width, opacity, id} in the
    SVG's own units with group transforms applied, in paint order; viewbox is (x, y, w, h).
    Gradients and filters are not included: use svg()/draw_svg() for the finished look."""
    import xml.etree.ElementTree as ET
    text = open(src, encoding='utf-8').read() if not src.lstrip().startswith('<') else src
    root = ET.fromstring(text)
    vb = root.get('viewBox')
    if vb:
        viewbox = tuple(float(x) for x in re.split(r'[\s,]+', vb.strip()))
    else:
        viewbox = (0.0, 0.0, float(re.sub(r'[^\d.]', '', root.get('width', '100')) or 100),
                   float(re.sub(r'[^\d.]', '', root.get('height', '100')) or 100))
    shapes = []

    def style_of(el, inherited):
        st = dict(inherited)
        for k in ('fill', 'stroke', 'stroke-width', 'opacity', 'fill-opacity', 'fill-rule'):
            if el.get(k) is not None:
                st[k] = el.get(k)
        for decl in (el.get('style') or '').split(';'):
            if ':' in decl:
                k, v = decl.split(':', 1)
                st[k.strip()] = v.strip()
        return st

    def num(el, k):
        v = el.get(k)
        return float(re.sub(r'[^\d.eE+-]', '', v)) if v else 0.0

    def walk(el, mat, inherited):
        tag = el.tag.split('}')[-1]
        if tag in ('defs', 'clipPath', 'mask', 'style', 'title', 'desc', 'linearGradient', 'radialGradient', 'filter'):
            return
        m = skia.Matrix.Concat(mat, _svg_matrix(el.get('transform')))
        st = style_of(el, inherited)
        p = None
        if tag == 'path' and el.get('d'):
            p = svg_path(el.get('d'))
        elif tag == 'rect':
            rx = num(el, 'rx') or num(el, 'ry')
            p = skia.Path()
            p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(num(el, 'x'), num(el, 'y'), num(el, 'width'), num(el, 'height')),
                                             rx, num(el, 'ry') or rx))
        elif tag == 'circle':
            p = skia.Path()
            p.addCircle(num(el, 'cx'), num(el, 'cy'), num(el, 'r'))
        elif tag == 'ellipse':
            p = skia.Path()
            cx, cy, rx, ry = num(el, 'cx'), num(el, 'cy'), num(el, 'rx'), num(el, 'ry')
            p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
        elif tag == 'line':
            p = skia.Path()
            p.moveTo(num(el, 'x1'), num(el, 'y1'))
            p.lineTo(num(el, 'x2'), num(el, 'y2'))
        elif tag in ('polygon', 'polyline'):
            v = [float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', el.get('points', ''))]
            p = poly(list(zip(v[::2], v[1::2])), tag == 'polygon')
        if p is not None:
            p.transform(m)
            if st.get('fill-rule') == 'evenodd':
                p.setFillType(skia.PathFillType.kEvenOdd)
            fill = _svg_color(st.get('fill', '#000000'))
            shapes.append(dict(path=p, fill=fill, stroke=_svg_color(st.get('stroke', 'none')),
                               width=float(re.sub(r'[^\d.]', '', st.get('stroke-width', '1')) or 1) * m.getScaleX(),
                               opacity=float(st.get('opacity', 1)) * float(st.get('fill-opacity', 1)), id=el.get('id')))
        for ch in el:
            walk(ch, m, st)

    walk(root, skia.Matrix(), {})
    return shapes, viewbox


def pdf_vectors(pdf_path, page, clip, max_area=None, recolor=None, skip=()):
    """Vector artwork from a PDF region (logos, illustrations, outlined text) as a sharp skia.Picture.
    clip = (x0, y0, x1, y1) in PDF points. max_area drops big shapes such as panel backgrounds.
    recolor = {(r, g, b): (r, g, b)} swaps colours; skip = {(r, g, b)} drops them.
    Returns (picture, (w, h)); draw with c.drawPicture(pic) after translate/scale."""
    import pymupdf
    drawings = pymupdf.open(pdf_path)[page].get_drawings()
    x0, y0, x1, y1 = clip
    rec = skia.PictureRecorder()
    cv = rec.beginRecording(skia.Rect.MakeLTRB(0, 0, x1 - x0, y1 - y0))
    cv.translate(-x0, -y0)
    for d in drawings:
        r = d['rect']
        if r.x0 < x0 - 1 or r.y0 < y0 - 1 or r.x1 > x1 + 1 or r.y1 > y1 + 1:
            continue
        path = skia.Path()
        last = None
        for it in d['items']:
            if it[0] in ('l', 'c'):
                a = it[1]
                if last is None or abs(a.x - last.x) > 1e-3 or abs(a.y - last.y) > 1e-3:
                    path.moveTo(a.x, a.y)
                if it[0] == 'l':
                    last = it[2]; path.lineTo(last.x, last.y)
                else:
                    last = it[4]; path.cubicTo(it[2].x, it[2].y, it[3].x, it[3].y, last.x, last.y)
            elif it[0] == 're':
                q = it[1]; path.addRect(skia.Rect.MakeLTRB(q.x0, q.y0, q.x1, q.y1)); last = None
            elif it[0] == 'qu':
                q = it[1]; path.addPoly([skia.Point(p.x, p.y) for p in (q.ul, q.ur, q.lr, q.ll)], True); last = None
        for kind in ('fill', 'color'):
            cc = d.get(kind)
            if cc is None or (kind == 'color' and not d.get('width')):
                continue
            if kind == 'fill' and max_area and r.width * r.height > max_area:
                continue
            c3 = tuple(int(round(v * 255)) for v in cc[:3])
            if c3 in skip:
                continue
            c3 = (recolor or {}).get(c3, c3)
            alpha = d.get('fill_opacity' if kind == 'fill' else 'stroke_opacity') or 1.0
            if kind == 'fill':
                q = skia.Path(path)
                q.setFillType(skia.PathFillType.kEvenOdd if d.get('even_odd') else skia.PathFillType.kWinding)
                cv.drawPath(q, paint(c3, alpha))
            else:
                cv.drawPath(path, paint(c3, alpha, stroke=d['width'], cap=None))
    return rec.finishRecordingAsPicture(), (x1 - x0, y1 - y0)


@functools.lru_cache(maxsize=64)
def _qr(data, ecl):
    import segno
    return tuple(tuple(bool(v) for v in row) for row in segno.make(data, error=ecl, micro=False).matrix)


def qr(c, data, x, y, size, fg='#0F1219', bg='#FFFFFF', ecl='h', quiet=3, logo=None, radius=0.04):
    """Crisp QR code. With ecl='h' a small centre logo(c, cx, cy, s) still scans; keep it under
    20 % wide. Decode a rendered frame (qr_check or `python main.py qr t`) before delivering."""
    m = _qr(data, ecl)
    ms = size / (len(m) + 2 * quiet)
    rrect(c, x, y, x + size, y + size, size * radius, paint(bg))
    path = skia.Path()
    for i, row in enumerate(m):
        for j, v in enumerate(row):
            if v:
                path.addRect(skia.Rect.MakeXYWH(x + (j + quiet) * ms, y + (i + quiet) * ms, ms + 0.3, ms + 0.3))
    c.drawPath(path, paint(fg))
    if logo:
        s = size * 0.2
        cx, cy = x + size / 2, y + size / 2
        rrect(c, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, s * 0.2, paint(bg))
        logo(c, cx, cy, s * 0.72)


# ---- camera and pointer ----------------------------------------------------------------------

class Camera:
    """Frames part of a scene drawn in its own layout coordinates.
    Camera(1.0, 960, 540, [(2.0, 3.2, 1.6, 1200, 400)]) means: from 2.0 s to 3.2 s glide to 1.6x
    zoom centred on (1200, 400), then hold. Zoom blends in log space so its speed feels even.
    screen is where the camera centre lands on screen; base scales everything (multi-aspect layouts)."""
    def __init__(self, zoom, cx, cy, keys=(), screen=(960, 540), base=1.0, ease=inout_cubic):
        self.z0, self.c0, self.keys, self.screen, self.base, self.ease = zoom, (cx, cy), sorted(keys), screen, base, ease

    def at(self, t):
        z, (x, y) = self.z0, self.c0
        for t0, t1, zz, xx, yy in self.keys:
            e = self.ease(seg(t, t0, t1))
            if e <= 0:
                break
            z = math.exp(lerp(math.log(z), math.log(zz), e))
            x = lerp(x, xx, e)
            y = lerp(y, yy, e)
        return z * self.base, x, y

    def apply(self, c, t):
        z, x, y = self.at(t)
        c.translate(*self.screen)
        c.scale(z, z)
        c.translate(-x, -y)

    def to_screen(self, t, x, y):
        z, cx, cy = self.at(t)
        return self.screen[0] + (x - cx) * z, self.screen[1] + (y - cy) * z


class Pointer:
    """A cursor that glides through waypoints [(t, x, y), ...] and clicks at the given times.
    Buttons call pointer.pressed(t, click_time) to animate their press; show=(t_in, t_out) fades it."""
    ARROW = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]

    def __init__(self, path, clicks=(), show=(0.0, 1e9), size=1.8, fill='#FFFFFF', edge='#0A0A0E', ring='#A78BFA'):
        self.path, self.clicks, self.show, self.size = sorted(path), tuple(clicks), show, size
        self.fill, self.edge, self.ring = fill, edge, ring

    def pos(self, t):
        p = self.path
        if t <= p[0][0]:
            return p[0][1], p[0][2]
        for (t0, x0, y0), (t1, x1, y1) in zip(p, p[1:]):
            if t <= t1:
                e = inout_cubic(seg(t, t0, t1))
                bow = 0.08 * math.sin(math.pi * e)   # a slight arc reads as a hand, not a robot
                return lerp(x0, x1, e) - (y1 - y0) * bow, lerp(y0, y1, e) + (x1 - x0) * bow
        return p[-1][1], p[-1][2]

    def pressed(self, t, tc):
        """0 -> 1 -> 0 around a click at tc: scale a button by 1 - 0.06 * pressed."""
        return seg(t, tc - 0.12, tc) * (1 - seg(t, tc + 0.05, tc + 0.3))

    def clicked(self, t, tc):
        return t >= tc

    def draw(self, c, t):
        a = min(seg(t, self.show[0], self.show[0] + 0.4), 1 - seg(t, self.show[1] - 0.4, self.show[1]))
        if a <= 0:
            return
        x, y = self.pos(t)
        press = max([self.pressed(t, tc) for tc in self.clicks] or [0.0])
        for tc in self.clicks:
            d = t - tc
            if 0 <= d < 0.9:
                c.drawCircle(x, y, 14 + 70 * out_expo(d / 0.9), paint(self.ring, 0.9 * (1 - d / 0.9) * a, stroke=4))
        s = self.size * (1 - 0.14 * press)
        with Layer(c, a, bounds=(x - 8, y - 8, x + 40 * s, y + 50 * s)):
            c.translate(x, y)
            c.scale(s, s)
            shape = poly(self.ARROW)
            c.drawPath(shape, paint(self.fill))
            c.drawPath(shape, paint(self.edge, 1, stroke=1.8))


# ---- scenes, timeline, transitions -----------------------------------------------------------

class Scene:
    """A section with its own clock u (0 -> duration). Subclass and define draw(c, u), or pass draw=.
    entry/exit give screen points for zoom transitions: (x, y) or f(u) -> (x, y).
    During a transition the outgoing scene keeps running past its duration: hold the final state."""
    def __init__(self, duration, draw=None, entry=None, exit=None, name=None):
        self.duration = duration
        self._entry, self._exit = entry, exit
        self.name = name or type(self).__name__
        if draw is not None:
            self.draw = draw

    def entry_point(self, u):
        return self._entry(u) if callable(self._entry) else self._entry

    def exit_point(self, u):
        return self._exit(u) if callable(self._exit) else self._exit


class Timeline:
    """Scenes back to back. A transition(c, A, B, p, ctx) runs across each join during
    [join - before, join + after]; A and B draw the outgoing/incoming scene; p goes 0 -> 1.
    transitions={k: fn or None} overrides the join into scene k (None = hard cut).
    loop=True lets the last scene flow into the first.
    background(c, t) and overlay(c, t) draw on global time under and over every scene: a continuous
    backdrop, a logo bug, a progress bar. Scenes drawn over a shared background must not clear()."""
    def __init__(self, scenes, size, transition=None, before=0.6, after=0.6, loop=False, transitions=None,
                 background=None, overlay=None):
        self.scenes, self.size, self.loop, self.default = scenes, size, loop, transition
        self.background, self.overlay = background, overlay
        self.before, self.after, self.per = before, after, dict(transitions or {})
        self.starts = []
        t = 0.0
        for s in scenes:
            self.starts.append(t)
            t += s.duration
        self.duration = t

    def _tr(self, k):
        return self.per.get(k, self.default)

    def locate(self, t):
        """(scene index, local time) at global time t."""
        for i in range(len(self.scenes) - 1, -1, -1):
            if t >= self.starts[i]:
                return i, t - self.starts[i]
        return 0, t

    def start(self, k):
        """Global start time of scene k."""
        return self.starts[k]

    def _join(self, t):
        n = len(self.scenes)
        for k in (range(n) if self.loop else range(1, n)):
            if self._tr(k) is None:
                continue
            b = self.starts[k]
            for bb in ((b, b + self.duration, b - self.duration) if self.loop else (b,)):
                if -self.before <= t - bb < self.after:
                    return (k - 1) % n, k, t - bb
        return None

    def cuts(self):
        """Hard-cut times; motion blur must never sample across them."""
        return [self.starts[k] for k in range(0 if self.loop else 1, len(self.scenes)) if self._tr(k) is None]

    def in_transition(self, t):
        return self._join(t % self.duration if self.loop else t) is not None

    def describe(self):
        return [dict(scene=i, name=s.name, start=round(self.starts[i], 3), end=round(self.starts[i] + s.duration, 3))
                for i, s in enumerate(self.scenes)]

    def __call__(self, c, t):
        if self.loop:
            t %= self.duration
        if self.background:
            self.background(c, t)
        self._scenes(c, t)
        if self.overlay:
            self.overlay(c, t)

    def _scenes(self, c, t):
        j = self._join(t)
        if j is None:
            i, u = self.locate(t)
            self.scenes[i].draw(c, u)
            return
        a, b, d = j
        A, B = self.scenes[a], self.scenes[b]
        ua, ub = d + A.duration, max(d, 0.0)
        mid = (self.size[0] / 2, self.size[1] / 2)
        ctx = dict(size=self.size, exit=A.exit_point(ua) or mid, entry=B.entry_point(ub) or mid, d=d,
                   span=self.before + self.after)
        self._tr(b)(c, lambda cc: A.draw(cc, ua), lambda cc: B.draw(cc, ub), seg(d, -self.before, self.after), ctx)

    def transition_at(self, t):
        """The transition function running at time t, or None: lets motion blur target only some joins,
        e.g. subframes=lambda t: 4 if tl.transition_at(t) is zoom_through else 1."""
        j = self._join(t % self.duration if self.loop else t)
        return self._tr(j[1]) if j else None


def crossfade(c, A, B, p, ctx):
    A(c)
    with Layer(c, smoothstep(p)):
        B(c)


def fade_through(c, A, B, p, ctx, col='#000000'):
    """Fade to a colour, then up into the next scene."""
    w, h = ctx['size']
    (A if p < 0.5 else B)(c)
    c.drawRect(skia.Rect.MakeWH(w, h), paint(col, 1 - abs(p * 2 - 1)))


def push(c, A, B, p, ctx, dx=-1, dy=0, smear=True):
    """Slide the new scene in; dx/dy is the direction the old one leaves: (-1, 0) = to the left.
    smear adds a directional blur while the move is fast (a whip pan), which reads better than
    sub-frame motion blur for moves this fast, so skip subframes on push joins."""
    w, h = ctx['size']
    e = inout_expo(p)
    speed = (inout_expo(min(1.0, p + 0.01)) - inout_expo(max(0.0, p - 0.01))) / 0.02   # 0 at rest, ~7 at the peak
    span = ctx.get('span', 1.2)
    sig = min(48.0, speed * 7.0 / max(span, 0.3)) if smear else 0.0
    blur = (sig * abs(dx), sig * abs(dy))
    for f, ox, oy in ((A, dx * w * e, dy * h * e), (B, dx * w * (e - 1), dy * h * (e - 1))):
        c.save()
        c.translate(ox, oy)
        c.clipRect(skia.Rect.MakeWH(w, h))
        if sig > 0.5:
            with Layer(c, 1.0, blur=blur, bounds=(0, 0, w, h)):
                f(c)
        else:
            f(c)
        c.restore()


def slide_up(c, A, B, p, ctx):
    push(c, A, B, p, ctx, 0, -1)


def zoom_through(c, A, B, p, ctx, zin=2.6, zout=2.2):
    """Dive into the old scene's exit point and arrive out of the new scene's entry point."""
    ex, ey = ctx['exit']
    nx, ny = ctx['entry']
    if p < 0.6:
        z = math.exp(math.log(zin) * in_cubic(seg(p, 0.0, 0.6)))
        c.save(); c.translate(ex, ey); c.scale(z, z); c.translate(-ex, -ey); A(c); c.restore()
    a = smoothstep(seg(p, 0.25, 0.55))
    if a > 0:
        z = math.exp(math.log(zout) * (1 - out_cubic(seg(p, 0.25, 1.0))))
        with Layer(c, a):
            c.translate(nx, ny); c.scale(z, z); c.translate(-nx, -ny); B(c)


def wipe(c, A, B, p, ctx, colors=('#7C3AED', '#C4B5FD'), slant=0.4, bands=(0.06, 0.09)):
    """Two coloured slabs sweep across at an angle (take the colours and angle from the brand)."""
    w, h = ctx['size']
    e = inout_cubic(p)
    b1, b2 = bands[0] * w, bands[1] * w
    edge = lerp(-(b1 + b2) - slant * h, w + 10, e)

    def region(xa, xb):
        return poly([(xa, h), (xb, h), (xb + slant * h, 0), (xa + slant * h, 0)])
    A(c)
    c.save(); c.clipPath(region(-4 * w, edge), skia.ClipOp.kIntersect, True); B(c); c.restore()
    c.drawPath(region(edge - 1, edge + b1), paint(colors[0]))
    c.drawPath(region(edge + b1 - 1, edge + b1 + b2), paint(colors[1]))


def iris(c, A, B, p, ctx):
    """The new scene opens as a growing circle from its entry point."""
    w, h = ctx['size']
    cx, cy = ctx['entry']
    r = math.hypot(max(cx, w - cx), max(cy, h - cy)) * inout_cubic(p)
    A(c)
    if r > 0:
        c.save()
        pth = skia.Path()
        pth.addCircle(cx, cy, r)
        c.clipPath(pth, skia.ClipOp.kIntersect, True)
        B(c)
        c.restore()


def blur_through(c, A, B, p, ctx, amount=18.0):
    """Defocus out of one scene and into the next (costly: blur is per pixel)."""
    w, h = ctx['size']
    if p < 0.5:
        with Layer(c, 1.0, blur=amount * smoothstep(p * 2), bounds=(0, 0, w, h)):
            A(c)
    else:
        with Layer(c, 1.0, blur=amount * (1 - smoothstep(p * 2 - 1)), bounds=(0, 0, w, h)):
            B(c)


TRANSITIONS = {'crossfade': crossfade, 'fade_through': fade_through, 'push': push, 'slide_up': slide_up,
               'zoom_through': zoom_through, 'wipe': wipe, 'iris': iris, 'blur_through': blur_through, 'cut': None}


# ---- rendering and encoding ------------------------------------------------------------------

CODECS = {  # name: (pixel format, encoder arguments, file extension)
    'h264':       ('yuv420p',      ['-c:v', 'libx264', '-preset', '{preset}', '-crf', '{crf}', '-profile:v', 'high'], '.mp4'),
    'h264-444':   ('yuv444p',      ['-c:v', 'libx264', '-preset', '{preset}', '-crf', '{crf}', '-profile:v', 'high444'], '.mp4'),
    'hevc':       ('yuv420p10le',  ['-c:v', 'libx265', '-preset', '{preset}', '-crf', '{crf}', '-tag:v', 'hvc1',
                                    '-x265-params', 'log-level=error'], '.mp4'),
    'av1':        ('yuv420p10le',  ['-c:v', 'libsvtav1', '-preset', '6', '-crf', '{crf}'], '.mp4'),
    'prores':     ('yuv422p10le',  ['-c:v', 'prores_ks', '-profile:v', '3', '-vendor', 'apl0'], '.mov'),
    'prores4444': ('yuva444p10le', ['-c:v', 'prores_ks', '-profile:v', '4444', '-vendor', 'apl0'], '.mov'),
    'vp9':        ('yuv420p',      ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '{crf}', '-row-mt', '1'], '.webm'),
    'vp9-alpha':  ('yuva420p',     ['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '{crf}', '-row-mt', '1'], '.webm'),
}


def env_size(default=(1920, 1080)):
    """Frame size from $MV_SIZE ('1080x1920'), else the default. Environment variables reach the
    parallel render workers too, so one script can render several aspect ratios."""
    s = os.environ.get('MV_SIZE')
    if not s:
        return tuple(default)
    w, h = re.split(r'[x:,]', s.lower())
    return int(w), int(h)


def env_fps(default=30):
    """Frame rate from $MV_FPS ('60', '25', '30000/1001' for US broadcast), else the default."""
    v = os.environ.get('MV_FPS')
    if not v:
        return default
    if '/' in v:
        a, b = v.split('/')
        return float(a) / float(b)
    return float(v) if '.' in v else int(v)


class Video:
    """draw(c, t) plus a format.
    subframes > 1 (or f(t) -> int) adds motion blur with a 180-degree shutter by default; frames
    whose shutter would cross a hard cut are never blurred. transparent=True keeps alpha (use codec
    prores4444 or vp9-alpha). dither hides gradient banding in 8-bit output but raises the bitrate
    (about 3x in tests): turn it off for flat designs. grain (0.02-0.06) adds monochrome film grain
    while encoding, at no drawing cost (it also raises the bitrate). scale < 1 renders smaller
    previews of the same design (draw code keeps using full-size coordinates)."""
    def __init__(self, draw, duration, size=(1920, 1080), fps=30, background='#000000', subframes=1,
                 shutter=0.5, cuts=(), transparent=False, dither=True, scale=1.0, grain=0.0):
        self.draw, self.duration, self.fps = draw, duration, fps
        self.W, self.H = size
        self.background, self.subframes, self.shutter, self.transparent = background, subframes, shutter, transparent
        self.use_dither, self.grain = dither, grain
        self.cuts = list(cuts) or (draw.cuts() if hasattr(draw, 'cuts') else [])
        self.frames = int(round(duration * fps))
        self.set_scale(scale)

    def set_scale(self, scale):
        self.scale = float(scale)
        self.w = max(2, int(round(self.W * self.scale / 2)) * 2)   # even sizes for 4:2:0 video
        self.h = max(2, int(round(self.H * self.scale / 2)) * 2)
        self._arr = np.zeros((self.h, self.w, 4), np.uint8)
        self._surf = skia.Surface(self._arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
        self._acc = None
        self.dither = None
        rng = np.random.default_rng(1)
        if self.grain > 0:
            # monochrome film grain: 4 noise fields that cycle; it also dithers
            g = rng.normal(0, self.grain * 255 * 0.5, (4, self.h, self.w, 1)).clip(-127, 127).astype(np.int8)
            self.dither = np.ascontiguousarray(np.repeat(g, 3, axis=3))
        elif self.use_dither:
            # +-1 level of noise before 8-bit encoding hides the stair-step banding in dark gradients
            self.dither = rng.integers(-1, 2, (2, self.h, self.w, 3), dtype=np.int8)

    @property
    def size(self):
        return self.W, self.H

    def _paint(self, t):
        with self._surf as c:
            c.restoreToCount(1)
            c.resetMatrix()   # drop anything a previous frame left behind
            c.clear(skia.ColorTRANSPARENT if self.transparent else color(self.background))
            c.save()
            if self.scale != 1.0:
                c.scale(self.w / self.W, self.h / self.H)
            self.draw(c, t)
            c.restoreToCount(1)
        return self._arr

    def frame(self, n):
        """Frame n as an RGBA uint8 array (a view that the next call overwrites; copy it to keep it)."""
        t = n / self.fps
        k = self.subframes(t) if callable(self.subframes) else self.subframes
        open_ = self.shutter / self.fps
        if k <= 1 or any(t < cut <= t + open_ for cut in self.cuts):
            return self._paint(t)
        if self._acc is None:
            self._acc = np.zeros((self.h, self.w, 4), np.uint32)
        self._acc[:] = 0
        for i in range(k):
            self._acc += self._paint(t + open_ * (i + 0.5) / k)
        self._arr[:] = self._acc // k
        return self._arr

    def still(self, t, path=None):
        """The frame at time t as a PIL image (saved when path is given)."""
        from PIL import Image
        n = t * self.fps
        f = self.frame(n)
        if self.grain > 0 and not self.transparent:   # previews show the grain; plain dither is invisible
            f = f.copy()
            f[:, :, :3] = np.clip(f[:, :, :3].astype(np.int16) + self.dither[int(n) % len(self.dither)], 0, 255)
        im = Image.fromarray(f[:, :, :4 if self.transparent else 3].copy())
        if path:
            im.save(path)
        return im

    def sheet(self, times, path, cols=4, tile_w=480):
        """Contact sheet of stills with their timestamps: the main way to review work before rendering."""
        from PIL import Image, ImageDraw
        th = int(tile_w * self.h / self.w)
        rows = (len(times) + cols - 1) // cols
        out = Image.new('RGB', (cols * (tile_w + 8) + 8, rows * (th + 30) + 8), (40, 40, 44))
        for k, t in enumerate(times):
            im = self.still(t).convert('RGB').resize((tile_w, th), Image.LANCZOS)
            x, y = 8 + (k % cols) * (tile_w + 8), 8 + (k // cols) * (th + 30)
            out.paste(im, (x, y))
            ImageDraw.Draw(out).text((x + 2, y + th + 6), f'{t:.2f}s', fill=(230, 230, 230))
        out.save(path)
        return path

    def _ffmpeg_args(self, out, codec, crf, preset):
        pix, enc, _ = CODECS[codec]
        enc = [a.format(crf=crf, preset=preset) for a in enc]
        # RGB -> YUV with the BT.709 matrix, and say so in the file. Without this, players decode
        # HD video as BT.709 while ffmpeg encoded BT.601, and brand colours visibly shift.
        vf = f'scale=out_color_matrix=bt709:out_range=tv,format={pix}'
        tags = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']
        rate = str(fractions.Fraction(self.fps).limit_denominator(1001))   # 29.97002997 -> 30000/1001
        return (['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{self.w}x{self.h}',
                 '-r', rate, '-i', '-', '-vf', vf] + enc + tags + ['-g', str(int(round(self.fps * 2))), out])

    def encode_range(self, a, b, out, codec='h264', crf=16, preset='medium', progress=None):
        """Encode frames a..b-1 to one file."""
        ff = subprocess.Popen(self._ffmpeg_args(out, codec, crf, preset), stdin=subprocess.PIPE)
        t0 = time.time()
        dither = self.dither is not None and not self.transparent and (self.grain > 0 or '10' not in CODECS[codec][0])
        for n in range(a, b):
            f = self.frame(n)
            if dither:
                f[:, :, :3] = np.clip(f[:, :, :3].astype(np.int16) + self.dither[n % len(self.dither)], 0, 255)
            ff.stdin.write(f.tobytes())
            if progress and (n - a) % 15 == 0:
                with open(progress, 'w', encoding='utf-8') as fh:
                    fh.write(f'{n - a} {b - a} {time.time() - t0:.1f}')
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError(f'ffmpeg failed for {out}')

    def render(self, out, workers=None, codec='h264', crf=16, preset='medium', audio=None, chunk_s=8.0,
               script=None, start=None, end=None):
        """Render in chunks, several at once (one process per core), join without re-encoding, add audio.
        Finished chunks are kept in <out>.parts/, so re-running after an interruption resumes.
        start/end (seconds) render part of the timeline, for reviewing motion."""
        workers = workers or os.cpu_count() or 1
        ext = CODECS[codec][2]
        if not out.endswith(ext):
            print(f'note: codec {codec} normally writes {ext} files', flush=True)
        f0 = int(round((start or 0.0) * self.fps))
        f1 = min(self.frames, int(round(end * self.fps))) if end is not None else self.frames
        if f1 <= f0:
            raise ValueError('nothing to render: end must be after start')
        parts = out + '.parts'
        step = max(1, min(int(chunk_s * self.fps), math.ceil((f1 - f0) / workers)))
        sig = dict(f0=f0, f1=f1, step=step, codec=codec, crf=crf, preset=preset, scale=self.scale,
                   size=[self.w, self.h], fps=self.fps)
        sig_path = os.path.join(parts, 'job.json')
        if os.path.isdir(parts):
            try:
                with open(sig_path, encoding='utf-8') as fh:
                    same = json.load(fh) == sig
            except (OSError, ValueError):
                same = False
            if not same:
                shutil.rmtree(parts)   # settings changed: old chunks would not match
        os.makedirs(parts, exist_ok=True)
        with open(sig_path, 'w', encoding='utf-8') as fh:
            json.dump(sig, fh)
        jobs = [(a, min(f1, a + step), os.path.join(parts, f'{i:04d}{ext}')) for i, a in enumerate(range(f0, f1, step))]
        todo = [j for j in jobs if not os.path.exists(j[2] + '.done')]
        running, t0 = [], time.time()
        print(f'{len(jobs)} chunks, {len(todo)} to render, {workers} at a time', flush=True)
        while todo or running:
            while todo and len(running) < workers:
                a, b, p = todo.pop(0)
                arg = json.dumps(dict(a=a, b=b, out=p, codec=codec, crf=crf, preset=preset, scale=self.scale))
                running.append((subprocess.Popen([sys.executable, script or sys.argv[0], '_chunk', arg]), p))
            time.sleep(0.5)
            for pr, p in list(running):
                if pr.poll() is not None:
                    running.remove((pr, p))
                    if pr.returncode != 0:
                        for other, _ in running:
                            other.kill()
                        raise RuntimeError(f'chunk {p} failed (see the error above)')
                    open(p + '.done', 'w').close()
                    done = sum(os.path.exists(j[2] + '.done') for j in jobs)
                    print(f'  {done}/{len(jobs)} chunks  {time.time() - t0:.0f}s', flush=True)
        lst = os.path.join(parts, 'list.txt')
        with open(lst, 'w', encoding='utf-8') as fh:
            fh.writelines(f"file '{os.path.abspath(j[2])}'\n" for j in jobs)
        joined = out if not audio else out + '.video' + ext
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy']
                       + (['-movflags', '+faststart'] if ext in ('.mp4', '.mov') else []) + [joined], check=True)
        if audio:
            mux(joined, audio, out, offset=f0 / self.fps)
            os.remove(joined)
        print(f'wrote {out} in {time.time() - t0:.0f}s', flush=True)
        return out

    def export_frames(self, folder, every=1, start=None, end=None):
        """PNG sequence (with alpha when transparent=True) for editors and compositing."""
        os.makedirs(folder, exist_ok=True)
        f0 = int(round((start or 0.0) * self.fps))
        f1 = min(self.frames, int(round(end * self.fps))) if end is not None else self.frames
        for n in range(f0, f1, every):
            self.still(n / self.fps, os.path.join(folder, f'{n:05d}.png'))
        return folder


def mux(video, audio, out, offset=0.0):
    """Add a soundtrack without re-encoding the picture (AAC for mp4, PCM for mov, Opus for webm).
    offset skips into the audio, for partial renders."""
    ext = os.path.splitext(out)[1]
    acodec = {'.mov': ['-c:a', 'pcm_s24le'], '.webm': ['-c:a', 'libopus', '-b:a', '192k']}.get(ext, ['-c:a', 'aac', '-b:a', '256k'])
    seek = ['-ss', f'{offset:.4f}'] if offset else []
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video] + seek + ['-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy']
                   + acodec + ['-ar', '48000', '-shortest'] + (['-movflags', '+faststart'] if ext in ('.mp4', '.mov') else [])
                   + [out], check=True)


# ---- checks ----------------------------------------------------------------------------------

def probe(path):
    """Stream facts plus a full decode; any decode error means the file is not safe to deliver."""
    info = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                           'stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,pix_fmt,color_space:format=duration,size',
                           '-of', 'compact', path], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    err = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    return info + ('decode: clean' if not err.strip() else 'decode ERRORS:\n' + err[:2000])


def seam_check(video):
    """For loops: the jump from the last frame to the first should be no bigger than a normal step."""
    n = video.frames
    last = video.frame(n - 1).astype(np.int16).copy()
    prev = video.frame(n - 2).astype(np.int16).copy()
    first = video.frame(0).astype(np.int16)
    return dict(seam=round(float(np.abs(first - last).mean()), 3), normal_step=round(float(np.abs(last - prev).mean()), 3))


def qr_check(video, t):
    """Decode every QR code visible at time t (pyzbar); returns the decoded strings."""
    from pyzbar.pyzbar import decode
    return [d.data.decode() for d in decode(video.still(t).convert('L'))]


def bench(video, samples=12):
    """Average and worst milliseconds per frame, and the render-time estimate on this machine."""
    ts = []
    for i in range(samples):
        n = int((i + 0.5) * video.frames / samples)
        t0 = time.perf_counter()
        video.frame(n)
        ts.append(time.perf_counter() - t0)
    avg, worst = sum(ts) / len(ts), max(ts)
    cores = os.cpu_count() or 1
    return dict(ms_avg=round(avg * 1000, 1), ms_worst=round(worst * 1000, 1),
                est_minutes=round(video.frames * avg / cores / 60 * 1.15, 1), cores=cores)


# ---- command line ----------------------------------------------------------------------------

def cli(video, audio=None):
    """python main.py info                     duration, size, scenes and their start times
       python main.py sheet [t1,t2,..] [out.png]   contact sheet (default: 12 evenly spaced frames)
       python main.py still t [out.png]        one frame
       python main.py bench                    ms per frame and a render estimate
       python main.py seam                     loop seam against a normal frame step
       python main.py qr t                     decode the QR codes visible at time t
       python main.py render out.mp4 [--workers N] [--codec h264] [--crf 16] [--preset medium]
                                            [--scale 0.5] [--start s] [--end s] [--no-audio]
       python main.py frames folder [--every N]    PNG sequence
       python main.py probe out.mp4            file facts and a full decode test
    audio: a WAV path or a function returning one (built before muxing).
    MV_SIZE=1080x1920 before the command renders another size when the script reads mv.env_size()."""
    args = sys.argv[1:] or ['sheet']
    cmd = args[0]
    opts, pos = {}, []
    i = 1
    while i < len(args):
        if args[i].startswith('--'):
            if args[i] in ('--no-audio',):
                opts[args[i]] = True; i += 1
            else:
                opts[args[i]] = args[i + 1] if i + 1 < len(args) else ''; i += 2
        else:
            pos.append(args[i]); i += 1
    if cmd == '_chunk':
        j = json.loads(args[1])
        if j.get('scale', 1.0) != video.scale:
            video.set_scale(j['scale'])
        video.encode_range(j['a'], j['b'], j['out'], j['codec'], j['crf'], j['preset'])
        return
    if '--scale' in opts:
        video.set_scale(float(opts['--scale']))
    if cmd == 'info':
        d = dict(duration=video.duration, frames=video.frames, fps=video.fps, size=[video.W, video.H],
                 transparent=video.transparent)
        if hasattr(video.draw, 'describe'):
            d['scenes'] = video.draw.describe()
        print(json.dumps(d, indent=1))
    elif cmd == 'sheet':
        ts = ([float(x) for x in pos[0].split(',')] if pos else
              [video.duration * (k + 0.5) / 12 for k in range(12)])
        print(video.sheet(ts, pos[1] if len(pos) > 1 else 'sheet.png'))
    elif cmd == 'still':
        out = pos[1] if len(pos) > 1 else 'still.png'
        video.still(float(pos[0]), out)
        print(out)
    elif cmd == 'bench':
        print(bench(video))
    elif cmd == 'seam':
        print(seam_check(video))
    elif cmd == 'qr':
        print(qr_check(video, float(pos[0])))
    elif cmd == 'probe':
        print(probe(pos[0]))
    elif cmd == 'frames':
        print(video.export_frames(pos[0] if pos else 'frames', int(opts.get('--every', 1)),
                                  float(opts['--start']) if '--start' in opts else None,
                                  float(opts['--end']) if '--end' in opts else None))
    elif cmd == 'render':
        out = pos[0] if pos else 'out' + CODECS[opts.get('--codec', 'h264')][2]
        a = None if opts.get('--no-audio') else (audio() if callable(audio) else audio)
        video.render(out, workers=int(opts.get('--workers', 0)) or None, codec=opts.get('--codec', 'h264'),
                     crf=int(opts.get('--crf', 16)), preset=opts.get('--preset', 'medium'), audio=a,
                     start=float(opts['--start']) if '--start' in opts else None,
                     end=float(opts['--end']) if '--end' in opts else None)
        print(probe(out))
    else:
        print(cli.__doc__)
