"""fx.py: backgrounds and effects: gradients, mesh blobs, shader backgrounds, grids, grain,
vignette, particles, bokeh, stars, waves, rings, confetti, sparkles, shine, glass.

Everything is a pure function of time t. Functions that take `period` repeat exactly every
`period` seconds, so they are safe in seamless loops when the loop length is a multiple of it.

    fx.mesh(c, W, H, t, ['#1E1B4B', '#7C3AED', '#0EA5E9'], period=20)   # soft moving colour field
    fx.grid(c, W, H, t, step=80, a=0.06, drift=(0, 12))
    fx.particles(c, W, H, t, n=70, period=20)
    fx.grain(c, W, H, t, 0.04)          # last: film grain over everything (raises bitrate)
"""
import functools
import math
import re

import numpy as np
import skia

try:
    from . import mv
except ImportError:
    import mv

TAU = 2 * math.pi


# ---- plumbing --------------------------------------------------------------------------------

@functools.lru_cache(maxsize=16)
def _surface(w, h):
    return skia.Surface.MakeRasterN32Premul(w, h)


SMOOTH = skia.SamplingOptions(skia.FilterMode.kLinear)


def lowres(c, W, H, draw, scale=0.125):
    """Draw soft content (gradients, glows, blurred shapes, shaders) at a fraction of the frame size
    and stretch it over the frame. For soft content this looks the same and costs far less; the
    stretch itself costs about as much as drawing one full-frame image.
    draw(sub_canvas) draws in full-frame coordinates."""
    w, h = max(2, int(W * scale)), max(2, int(H * scale))
    surf = _surface(w, h)
    with surf as sc:
        sc.clear(skia.ColorTRANSPARENT)
        sc.save()
        sc.scale(w / W, h / H)
        draw(sc)
        sc.restore()
    c.drawImageRect(surf.makeImageSnapshot(), skia.Rect.MakeWH(W, H), SMOOTH)


def gradient(c, rect, colors, angle=90.0, alphas=None, pos=None):
    """Fill a rect with a linear gradient at an angle (degrees; 90 = top to bottom)."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a = math.radians(angle)
    L = (abs(math.cos(a)) * (x1 - x0) + abs(math.sin(a)) * (y1 - y0)) / 2
    dx, dy = math.cos(a) * L, math.sin(a) * L
    c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), mv.linear(cx - dx, cy - dy, cx + dx, cy + dy, colors, alphas, pos))


def vignette(c, W, H, strength=0.55, col='#000000', inner=0.5):
    """Darken the edges to pull the eye to the centre."""
    R = math.hypot(W, H) / 2
    c.drawRect(skia.Rect.MakeWH(W, H), mv.radial(W / 2, H / 2, R, [col, col, col], [0.0, 0.0, strength], [0.0, inner, 1.0]))


# ---- colour fields ---------------------------------------------------------------------------

def mesh(c, W, H, t, colors, bg=None, seed=0, period=24.0, blobs=None, size=0.62, a=0.9, scale=0.1):
    """A soft, slowly moving field of colour blobs (a 'mesh gradient'). Loops every period seconds."""
    rng = np.random.default_rng(seed)
    n = blobs or max(3, len(colors) + 1)
    base = rng.uniform(0.1, 0.9, (n, 2))
    amp = rng.uniform(0.12, 0.28, (n, 2))
    k = rng.integers(1, 3, (n, 2))
    ph = rng.uniform(0, TAU, (n, 2))
    rad = rng.uniform(0.75, 1.25, n) * size * max(W, H)

    def draw(sc):
        sc.drawRect(skia.Rect.MakeWH(W, H), mv.paint(bg or colors[0]))
        for i in range(n):
            col = colors[(i + (1 if bg is None else 0)) % len(colors)]
            x = W * (base[i, 0] + amp[i, 0] * math.sin(TAU * k[i, 0] * t / period + ph[i, 0]))
            y = H * (base[i, 1] + amp[i, 1] * math.cos(TAU * k[i, 1] * t / period + ph[i, 1]))
            sc.drawCircle(x, y, rad[i], mv.radial(x, y, rad[i], [col, col], [a, 0.0], [0.0, 1.0]))
    lowres(c, W, H, draw, scale)


_SHADERS = {}


def shader(src, **uniforms):
    """A Paint running an SkSL shader. Uniforms are passed by name (floats or tuples of floats) and
    packed in declaration order. The effect is compiled once per source.

        src = 'uniform float2 res; uniform float t; half4 main(float2 p) { ... }'
        c.drawRect(skia.Rect.MakeWH(W, H), fx.shader(src, res=(W, H), t=t))"""
    if src not in _SHADERS:
        eff = skia.RuntimeEffect.MakeForShader(src)
        if eff is None:
            raise ValueError('SkSL did not compile; check the source')
        decl = re.findall(r'uniform\s+(?:half|float)(\d?)\s+(\w+)\s*;', src)
        _SHADERS[src] = (eff, [(name, int(n or 1)) for n, name in decl])
    eff, decl = _SHADERS[src]
    vals = []
    for name, n in decl:
        v = uniforms[name]
        v = list(v) if isinstance(v, (tuple, list, np.ndarray)) else [v]
        if len(v) != n:
            raise ValueError(f'uniform {name} needs {n} values')
        vals += [float(x) for x in v]
    p = skia.Paint(AntiAlias=True)
    p.setShader(eff.makeShader(skia.Data.MakeWithCopy(np.array(vals, np.float32).tobytes())))
    return p


FLOW_SKSL = """
uniform float2 res; uniform float phase; uniform float zoom;
uniform float3 c1; uniform float3 c2; uniform float3 c3;
float hash(float2 p) { return fract(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float noise(float2 p) {
    float2 i = floor(p); float2 f = fract(p); float2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + float2(1, 0)), u.x), mix(hash(i + float2(0, 1)), hash(i + float2(1, 1)), u.x), u.y);
}
float fbm(float2 p) { float v = 0.0; float a = 0.5; for (int i = 0; i < 3; i++) { v += a * noise(p); p *= 2.02; a *= 0.5; } return v * 1.15; }
half4 main(float2 fc) {
    float2 uv = fc / res.y * zoom;
    float2 o = float2(cos(phase), sin(phase)) * 0.9;
    float2 q = float2(fbm(uv + o), fbm(uv + float2(5.2, 1.3) - o));
    float n = fbm(uv + 2.4 * q + float2(sin(phase) * 0.5, cos(phase) * 0.5));
    float3 col = mix(c1, c2, smoothstep(0.25, 0.75, n));
    col = mix(col, c3, smoothstep(0.55, 0.95, q.x * n * 1.6));
    return half4(half3(col), 1.0);
}
"""


def flow(c, W, H, t, colors=('#0B0B1A', '#3B1C8C', '#0EA5E9'), period=30.0, zoom=1.6, scale=0.16):
    """Domain-warped noise in three colours (an SkSL shader), rendered small and stretched: a living,
    liquid backdrop. Loops every period. Costs roughly 2-3 full-frame draws."""
    cols = [tuple(v / 255 for v in mv.rgb(x)) for x in colors]

    def draw(sc):
        sc.drawRect(skia.Rect.MakeWH(W, H), shader(FLOW_SKSL, res=(W, H), phase=TAU * t / period, zoom=zoom,
                                                  c1=cols[0], c2=cols[1], c3=cols[2]))
    lowres(c, W, H, draw, scale)


# ---- texture ---------------------------------------------------------------------------------

@functools.lru_cache(maxsize=8)
def _noise_tile(size, seed):
    rng = np.random.default_rng(seed)
    v = np.clip(rng.normal(128, 42, (size, size)), 0, 255).astype(np.uint8)
    arr = np.stack([v, v, v, np.full_like(v, 255)], axis=2)
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


def grain(c, W, H, t, amount=0.05, fps=30, size=256, seed=0):
    """Film grain over an area, changing every frame. For grain over the whole frame prefer
    Video(grain=0.04): it is added while encoding at almost no cost. Grain raises the bitrate."""
    n = int(round(t * fps))
    img = _noise_tile(size, seed)
    m = skia.Matrix.Translate((n * 97) % size, (n * 57) % size)
    p = skia.Paint()
    p.setShader(img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(), m))
    p.setAlphaf(mv.clamp(amount * 4))
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawRect(skia.Rect.MakeWH(W, H), p)


def grid(c, W, H, t=0.0, step=64, col='#FFFFFF', a=0.07, kind='lines', drift=(0.0, 0.0), width=1.5, fade=0.85,
         center=None):
    """A background grid of lines or dots, drifting at `drift` px/s, fading out from `center`.
    Loop-safe when drift * loop length is a multiple of step."""
    ox = (drift[0] * t) % step
    oy = (drift[1] * t) % step
    cx, cy = center or (W / 2, H / 2)
    R = math.hypot(max(cx, W - cx), max(cy, H - cy))
    p = mv.radial(cx, cy, R, [col, col], [a, a * (1.0 - fade)], [0.0, 1.0])
    pth = skia.Path()
    if kind == 'dots':
        r = width * 1.2
        y = oy - step
        while y < H + step:
            x = ox - step
            while x < W + step:
                pth.addCircle(x, y, r)
                x += step
            y += step
    else:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(width)
        x = ox - step
        while x < W + step:
            pth.moveTo(x, 0); pth.lineTo(x, H); x += step
        y = oy - step
        while y < H + step:
            pth.moveTo(0, y); pth.lineTo(W, y); y += step
    c.drawPath(pth, p)


def floor(c, W, H, t, horizon=0.55, speed=0.5, col='#A78BFA', a=0.5, lines=16, cols=24, width=2.0):
    """A perspective grid floor rushing toward the viewer (retro and tech intros).
    speed is grid rows per second; loop-safe when speed * loop length is a whole number."""
    hy = H * horizon
    vx = W / 2
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, hy, W, H))
    phase = (t * speed) % 1.0
    for i in range(lines):
        z = (i + 1 - phase) / lines
        y = hy + (H - hy) * (z ** 2.2)
        c.drawLine(0, y, W, y, mv.paint(col, a * z, stroke=width * (0.4 + z)))
    for j in range(-cols, cols + 1):
        xb = vx + j * W / cols * 1.6
        c.drawLine(vx + j * 6, hy, xb, H, mv.paint(col, a * 0.7, stroke=width))
    c.drawRect(skia.Rect.MakeLTRB(0, hy, W, hy + (H - hy) * 0.35),
               mv.linear(0, hy, 0, hy + (H - hy) * 0.35, ['#000000', '#000000'], [0.9, 0.0]))
    c.restore()


# ---- particles -------------------------------------------------------------------------------

def particles(c, W, H, t, n=60, seed=0, col='#FFFFFF', size=(1.5, 4.0), a=(0.15, 0.7), direction=-90.0,
              speed=(12.0, 40.0), period=None, twinkle=0.5, glow=False):
    """Drifting dust or embers. direction in degrees (-90 = up). With period, every particle returns
    to its start after `period` seconds (speeds are nudged to whole trips), so loops are seamless.
    col may be a list of colours."""
    rng = np.random.default_rng(seed)
    x0 = rng.random(n) * W
    y0 = rng.random(n) * H
    sz = rng.uniform(size[0], size[1], n)
    al = rng.uniform(a[0], a[1], n)
    sp = rng.uniform(speed[0], speed[1], n)
    ph = rng.random(n)
    cols = col if isinstance(col, (list, tuple)) else [col]
    ci = rng.integers(0, len(cols), n)
    m = float(size[1]) * 6
    sx, sy = W + 2 * m, H + 2 * m
    d = math.radians(direction)
    vx, vy = math.cos(d) * sp, math.sin(d) * sp
    if period:
        vx = np.round(vx * period / sx) * sx / period
        vy = np.round(vy * period / sy) * sy / period
        tw = np.maximum(1, np.round(period / rng.uniform(2.0, 5.0, n))) / period
    else:
        tw = 1.0 / rng.uniform(2.0, 5.0, n)
    px = (x0 + vx * t + m) % sx - m
    py = (y0 + vy * t + m) % sy - m
    alpha = al * (1 - twinkle * 0.5 * (1 + np.sin(TAU * (tw * t + ph))))
    for i in range(n):
        if glow:
            c.drawCircle(px[i], py[i], sz[i] * 5, mv.radial(px[i], py[i], sz[i] * 5, [cols[ci[i]]] * 2, [alpha[i] * 0.35, 0.0]))
        c.drawCircle(px[i], py[i], sz[i], mv.paint(cols[ci[i]], alpha[i]))


def bokeh(c, W, H, t, n=14, colors=('#7C3AED', '#22D3EE', '#F472B6'), seed=3, period=20.0, size=(60, 220), a=(0.05, 0.16)):
    """Large soft out-of-focus discs drifting on small orbits. Loops every period."""
    rng = np.random.default_rng(seed)
    for i in range(n):
        x = rng.random() * W
        y = rng.random() * H
        r = rng.uniform(*size)
        al = rng.uniform(*a)
        col = colors[i % len(colors)]
        k = int(rng.integers(1, 3))
        phx, phy = rng.uniform(0, TAU, 2)
        ax, ay = rng.uniform(20, 70, 2)
        cx = x + ax * math.sin(TAU * k * t / period + phx)
        cy = y + ay * math.cos(TAU * k * t / period + phy)
        c.drawCircle(cx, cy, r, mv.radial(cx, cy, r, [col, col, col], [al, al * 0.8, 0.0], [0.0, 0.75, 1.0]))


def starfield(c, W, H, t, n=350, speed=0.12, seed=2, col='#FFFFFF', period=None, center=None, streak=0.0):
    """Stars flying toward the camera. speed = depth units per second; with period it is rounded so
    the field repeats exactly. streak > 0 draws warp-speed trails."""
    rng = np.random.default_rng(seed)
    if period:
        speed = max(1, round(speed * period)) / period
    cx, cy = center or (W / 2, H / 2)
    xs = rng.uniform(-1, 1, n)
    ys = rng.uniform(-1, 1, n)
    z0 = rng.random(n)
    sc = max(W, H) * 0.5
    z = (z0 - speed * t) % 1.0 + 0.02
    for i in range(n):
        x, y = cx + xs[i] / z[i] * sc * 0.35, cy + ys[i] / z[i] * sc * 0.35
        if not (-50 < x < W + 50 and -50 < y < H + 50):
            continue
        a = mv.clamp((1 - z[i]) * 1.4) * mv.clamp(z[i] * 20)
        r = max(0.6, (1 - z[i]) * 3.2)
        if streak > 0:
            z2 = z[i] + streak * 0.05
            x2, y2 = cx + xs[i] / z2 * sc * 0.35, cy + ys[i] / z2 * sc * 0.35
            c.drawLine(x2, y2, x, y, mv.paint(col, a * 0.8, stroke=r))
        else:
            c.drawCircle(x, y, r, mv.paint(col, a))


def waves(c, W, H, t, lines=8, amp=60.0, col='#FFFFFF', a=0.25, period=8.0, y=None, spread=22.0, width=2.0, freq=1.3):
    """Flowing parallel sine lines (tech and audio backdrops). Loops every period."""
    y = H * 0.6 if y is None else y
    for i in range(lines):
        pth = skia.Path()
        for k in range(0, 121):
            x = W * k / 120
            env = math.sin(math.pi * k / 120)
            yy = y + i * spread + amp * env * math.sin(TAU * (freq * k / 120 + t / period) + i * 0.35)
            if k == 0:
                pth.moveTo(x, yy)
            else:
                pth.lineTo(x, yy)
        c.drawPath(pth, mv.paint(col, a * (1 - i / (lines + 1)), stroke=width))


def pulse_rings(c, cx, cy, t, period=2.4, rings=3, r0=20.0, r1=300.0, col='#A78BFA', width=3.0, a=0.6):
    """Rings expanding out of a point, like a radar or a live signal. Loops every period."""
    for i in range(rings):
        k = ((t / period) + i / rings) % 1.0
        c.drawCircle(cx, cy, mv.lerp(r0, r1, mv.out_cubic(k)), mv.paint(col, a * (1 - k), stroke=width))


def confetti(c, t, t0, x, y, n=140, colors=('#F43F5E', '#F59E0B', '#22C55E', '#3B82F6', '#A855F7'), seed=5,
             spread=55.0, angle=-90.0, power=2400.0, gravity=1500.0, drag=1.6, dur=3.4, size=18.0):
    """A burst of confetti from (x, y) at time t0, in closed form (no simulation state)."""
    u = t - t0
    if u <= 0 or u > dur:
        return
    rng = np.random.default_rng(seed)
    ang = np.radians(angle + rng.uniform(-spread, spread, n))
    v = power * rng.uniform(0.45, 1.0, n)
    vx, vy = np.cos(ang) * v, np.sin(ang) * v
    k = drag
    e = 1 - math.exp(-k * u)
    px = x + vx / k * e
    py = y + (vy - gravity / k) / k * e + gravity * u / k
    rot = rng.uniform(0, 360, n) + rng.uniform(-500, 500, n) * u
    flip = np.cos(rng.uniform(4, 12, n) * u + rng.uniform(0, TAU, n))
    fade = 1 - mv.seg(u, dur - 0.6, dur)
    sz = size * rng.uniform(0.6, 1.2, n)
    for i in range(n):
        c.save()
        c.translate(px[i], py[i])
        c.rotate(rot[i])
        c.scale(1, flip[i])
        c.drawRect(skia.Rect.MakeLTRB(-sz[i] / 2, -sz[i] * 0.3, sz[i] / 2, sz[i] * 0.3), mv.paint(colors[i % len(colors)], fade))
        c.restore()


def sparkle(c, x, y, size, p, col='#FFFFFF', rot=0.0):
    """A four-point star that grows and fades over its life p (0..1)."""
    if p <= 0 or p >= 1:
        return
    s = size * math.sin(math.pi * p)
    c.save()
    c.translate(x, y)
    c.rotate(rot + 90 * p)
    c.drawPath(mv.star(0, 0, s, s * 0.18, 4), mv.paint(col, math.sin(math.pi * p)))
    c.restore()


# ---- surfaces --------------------------------------------------------------------------------

def shine(c, shape, t, t0, dur=0.9, angle=25.0, width=0.35, a=0.45, col='#FFFFFF'):
    """A glossy light band that sweeps across a shape once, starting at t0.
    shape: a rect tuple, skia.RRect or skia.Path (text outlines from mv.text_path work well)."""
    p = mv.inout_cubic(mv.seg(t, t0, t0 + dur))
    if p <= 0 or p >= 1:
        return
    if isinstance(shape, skia.Path):
        b = shape.getBounds()
    elif isinstance(shape, skia.RRect):
        b = shape.rect()
    else:
        b = skia.Rect.MakeLTRB(*shape)
    x0, y0, x1, y1 = b.left(), b.top(), b.right(), b.bottom()
    bw = (x1 - x0) * width
    cx = mv.lerp(x0 - bw - (y1 - y0), x1 + bw + (y1 - y0), p)
    with mv.Clip(c, shape if not isinstance(shape, tuple) else skia.Rect.MakeLTRB(*shape)):
        c.save()
        c.translate(cx, (y0 + y1) / 2)
        c.skew(-math.tan(math.radians(angle)), 0)
        c.drawRect(skia.Rect.MakeLTRB(-bw, -(y1 - y0), bw, y1 - y0),
                   mv.linear(-bw, 0, bw, 0, [col, col, col], [0.0, a, 0.0]))
        c.restore()


def glass(c, rect, radius=24.0, tint='#FFFFFF', a=0.07, border=0.2, highlight=0.10):
    """A frosted-glass-looking panel: translucent fill, bright rim and a top highlight."""
    x0, y0, x1, y1 = rect
    mv.rrect(c, x0, y0, x1, y1, radius, mv.paint(tint, a))
    mv.rrect(c, x0, y0, x1, y1, radius, mv.linear(0, y0, 0, y0 + (y1 - y0) * 0.5, [tint, tint], [highlight, 0.0]))
    rim = mv.linear(x0, y0, x1, y1, [tint, tint, tint], [border, border * 0.3, border * 0.8])
    rim.setStyle(skia.Paint.kStroke_Style)
    rim.setStrokeWidth(1.5)
    c.drawRRect(mv.rrect_shape(x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, radius), rim)


def spotlight(c, W, H, x, y, r, a=0.6, col='#000000'):
    """Darken everything except a soft circle at (x, y): focus attention on one element."""
    c.drawRect(skia.Rect.MakeWH(W, H), mv.radial(x, y, r * 1.6, [col, col, col], [0.0, 0.0, a], [0.0, 0.55, 1.0]))


# ---- logos -----------------------------------------------------------------------------------

@functools.lru_cache(maxsize=16)
def _logo_shapes(src):
    return mv.svg_shapes(src)


def logo(c, src, cx, cy, size, t=1e9, t0=0.0, style='pop', dur=1.2, stroke_col=None, a=1.0, each=0.12):
    """Draw an SVG logo centred on (cx, cy), `size` px on its longer side, optionally animated.
    style: 'pop' springs the parts in one after another; 'draw' traces each part's outline, then
    fills it; 'static' draws the file with Skia's SVG renderer (gradients and all).
    Parts come from mv.svg_shapes, so flat-colour logos animate piece by piece."""
    shapes, (vx, vy, vw, vh) = _logo_shapes(src)
    s = size / max(vw, vh)
    if style == 'static':
        dom = mv.svg(src)
        mv.draw_svg(c, dom, cx - vw * s / 2, cy - vh * s / 2, vw * s, vh * s)
        return
    c.save()
    c.translate(cx - (vx + vw / 2) * s, cy - (vy + vh / 2) * s)
    c.scale(s, s)
    n = len(shapes)
    for i, sh in enumerate(shapes):
        path = sh['path']
        b = path.getBounds()
        px, py = b.centerX(), b.centerY()
        k0 = t0 + i * each
        if style == 'pop':
            k = mv.spring(max(0.0, t - k0), 220, 14)
            if k <= 0:
                continue
            c.save()
            c.translate(px, py)
            c.scale(k, k)
            c.translate(-px, -py)
            if sh['fill']:
                c.drawPath(path, mv.paint(sh['fill'], a * sh['opacity'] * mv.clamp((t - k0) * 5)))
            if sh['stroke']:
                c.drawPath(path, mv.paint(sh['stroke'], a * mv.clamp((t - k0) * 5), stroke=sh['width']))
            c.restore()
        else:   # draw
            d_line = dur * 0.6
            p_line = mv.inout_cubic(mv.seg(t, k0, k0 + d_line))
            p_fill = mv.out_cubic(mv.seg(t, k0 + d_line * 0.7, k0 + dur))
            if p_line <= 0:
                continue
            col = stroke_col or sh['stroke'] or sh['fill'] or '#FFFFFF'
            if p_fill < 1:
                c.drawPath(mv.trim(path, 0, p_line, 'parallel'), mv.paint(col, a * (1 - p_fill * 0.8), stroke=max(2.0, 3.0 / s)))
            if p_fill > 0:
                if sh['fill']:
                    c.drawPath(path, mv.paint(sh['fill'], a * sh['opacity'] * p_fill))
                if sh['stroke']:
                    c.drawPath(path, mv.paint(sh['stroke'], a * p_fill, stroke=sh['width']))
    c.restore()


def placeholder_mark(c, cx, cy, size, t=1e9, t0=0.0, primary='#7C3AED', secondary='#22D3EE', letter=None, a=1.0):
    """A neutral stand-in logo (rounded tile with a play mark, or a letter) that pops in at t0.
    Use it until the client's real logo arrives."""
    k = mv.spring(max(0.0, t - t0), 200, 13)
    if k <= 0:
        return
    with mv.Layer(c, a * mv.clamp((t - t0) * 4), scale=k, pivot=(cx, cy), rotate=-10 * (1 - min(1.0, k))):
        r = size / 2
        mv.blur_shadow(c, cx - r, cy - r, cx + r, cy + r, size * 0.27, 0.45, size * 0.25, size * 0.1, primary)
        mv.rrect(c, cx - r, cy - r, cx + r, cy + r, size * 0.27, mv.linear(cx - r, cy - r, cx + r, cy + r, [mv.hex_color(mv.mix(primary, '#FFFFFF', 0.15)), primary]))
        if letter:
            mv.text(c, letter, cx, cy, mv.font('Inter', size * 0.55, wght=800), '#FFFFFF', align='center')
        else:
            tri = mv.poly([(cx - r * 0.22, cy - r * 0.36), (cx + r * 0.38, cy), (cx - r * 0.22, cy + r * 0.36)])
            c.drawPath(tri, mv.paint('#FFFFFF'))
            c.drawPath(tri, mv.paint('#FFFFFF', 1, stroke=size * 0.06))
            c.drawCircle(cx + r * 0.5, cy - r * 0.5, size * 0.07, mv.paint(secondary))
