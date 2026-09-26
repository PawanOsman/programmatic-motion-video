"""kinetic.py: kinetic typography: text that arrives, counts, decodes, rolls, rotates and breathes.

    f = mv.font('Inter', 120, wght=800)
    kinetic.reveal(c, 'Ship videos from code', 960, 540, f, t, 0.5, by='word', style='rise', align='center')
    kinetic.counter(c, 960, 700, f, t, 1.0, 1.4, 0, 12500, '{:,.0f}+', align='center')
    kinetic.rotator(c, ['faster', 'cheaper', 'on-brand'], 1200, 540, f, t, period=1.8)

All functions are pure in t. Positions follow mv.text: (x, y) with align 'left' | 'center' | 'right'
and anchor 'middle' (capitals centred on y) | 'baseline' | 'top'.
For Arabic-script and other right-to-left text use reveal_rtl() (whole words, shaped).
"""
import math

import numpy as np
import skia

try:
    from . import mv
except ImportError:
    import mv


def _base(f, y, anchor):
    ch = mv.cap_height(f)
    return y + ch / 2 if anchor == 'middle' else y + ch if anchor == 'top' else y


def _units(s, by):
    """[(unit text, prefix before it)] for chars (graphemes), words or the whole line."""
    if by == 'line':
        return [(s, '')]
    if by == 'word':
        words = s.split(' ')
        out = []
        for i, w in enumerate(words):
            if w:
                out.append((w, ' '.join(words[:i]) + (' ' if i else '')))
        return out
    g = mv.graphemes(s)
    return [(ch, ''.join(g[:i])) for i, ch in enumerate(g) if ch.strip()]


STYLES = ('fade', 'rise', 'drop', 'slide', 'pop', 'blur', 'mask', 'flip', 'type', 'track')


def reveal(c, s, x, y, f, t, t0, by='word', each=0.06, dur=0.55, style='rise', col='#FFFFFF', a=1.0,
           align='left', anchor='middle', dist=None, ease=None, t_out=None, out_dur=0.35, out_style=None,
           tracking=0.0, paint=None, emphasis=None, em_col=None):
    """Animate one line in, unit by unit (by='char' | 'word' | 'line'), and out again from t_out.
    style: fade, rise, drop, slide (in from the right), pop, blur (costly), mask (slides up from behind a line),
    flip, type (appears instantly), track (letter spacing closes up; use by='line').
    Returns the line width. paint: a skia.Paint (gradient) used instead of col.
    emphasis: words (any case, punctuation ignored) drawn in em_col instead of col."""
    if not s:
        return 0.0
    size = f.getSize()
    dist = size * 0.55 if dist is None else dist
    ease = ease or (mv.out_back if style == 'pop' else mv.out_expo if style in ('mask', 'slide') else mv.out_cubic)
    out_style = out_style or style
    units = _units(s, by)
    w = mv.width(s, f, tracking)
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    base = _base(f, y, anchor)
    ch = mv.cap_height(f)
    n = len(units)
    for i, (u, pre) in enumerate(units):
        p_in = seg_p = mv.seg(t, t0 + i * each, t0 + i * each + dur)
        if p_in <= 0:
            continue
        p = ease(p_in) if style != 'type' else 1.0
        q = 0.0
        if t_out is not None:
            q = mv.in_cubic(mv.seg(t, t_out + i * each * 0.5, t_out + i * each * 0.5 + out_dur))
            if q >= 1:
                continue
        st = out_style if q > 0 else style
        k = p if q <= 0 else 1 - q
        ux = x0 + (mv.width(pre, f, tracking) + (tracking * size if pre and tracking else 0.0) if pre else 0.0)
        uw = mv.width(u, f, tracking)
        cx, cy = ux + uw / 2, base - ch / 2
        alpha = a
        dx = dy = 0.0
        sc = 1.0
        blur = 0.0
        clip = None
        tr = tracking
        if st == 'fade':
            alpha *= k
        elif st == 'rise':
            dy, alpha = (1 - k) * dist, alpha * mv.clamp(k * 1.5)
        elif st == 'drop':
            dy, alpha = -(1 - k) * dist, alpha * mv.clamp(k * 1.5)
        elif st == 'slide':
            dx, alpha = (1 - k) * dist * 1.5, alpha * mv.clamp(k * 1.5)
        elif st == 'pop':
            sc, alpha = max(0.0, k), alpha * mv.clamp(seg_p * 4 if q <= 0 else k)
        elif st == 'blur':
            blur, alpha = (1 - k) * size * 0.18, alpha * k
        elif st == 'mask':
            dy = (1 - k) * size * 1.1
            clip = (ux - size, base - size * 1.05, ux + uw + size, base + size * 0.3)
        elif st == 'flip':
            sc, alpha = (1.0, max(0.0, k)), alpha * mv.clamp(k * 2)
        elif st == 'type':
            alpha *= 1.0 if q <= 0 else 1 - q
        elif st == 'track':
            tr = tracking + 0.6 * (1 - k)
            alpha *= mv.clamp(k * 1.5)
            if by == 'line':
                ww = mv.width(u, f, tr)
                ux = x - ww / 2 if align == 'center' else x - ww if align == 'right' else x
        if alpha <= 0.002:
            continue
        bounds = (ux - size, base - size * 1.6, ux + uw + size, base + size * 0.9)
        cm = mv.Clip(c, clip) if clip else None
        if cm:
            cm.__enter__()
        with mv.Layer(c, 1.0 if paint is None else alpha, dx=dx, dy=dy, scale=sc, pivot=(cx, cy), blur=blur,
                      bounds=bounds if blur else None):
            if paint is None:
                ucol = em_col if (emphasis and em_col and u.strip('.,!?;:"\'').lower() in emphasis) else col
                mv.text(c, u, ux, base, f, ucol, alpha, 'left', 'baseline', tr)
            else:
                mv.text(c, u, ux, base, f, anchor='baseline', tracking=tr, p=paint)
        if cm:
            cm.__exit__(None, None, None)
    return w


def reveal_rtl(c, s, x_right, base, font, size, t, t0, each=0.08, dur=0.5, style='rise', col='#FFFFFF', a=1.0,
               dist=None, axes=()):
    """Right-to-left text (Arabic, Kurdish, Persian, Urdu, Hebrew) revealed word by word, each word
    shaped with HarfBuzz; the first word appears first, on the right. Returns the line width."""
    words = [w for w in s.split(' ') if w]
    space = mv.shaped(' ', font, size, tuple(axes))[1] or size * 0.25
    widths = [mv.shaped(w, font, size, tuple(axes))[1] for w in words]
    dist = size * 0.5 if dist is None else dist
    x = x_right
    for i, (wd, ww) in enumerate(zip(words, widths)):
        k = mv.out_cubic(mv.seg(t, t0 + i * each, t0 + i * each + dur))
        if k > 0:
            dy = (1 - k) * dist if style == 'rise' else 0.0
            al = a * (mv.clamp(k * 1.5) if style in ('rise', 'fade') else 1.0)
            sc = k if style == 'pop' else 1.0
            with mv.Layer(c, 1.0, dy=dy, scale=sc, pivot=(x - ww / 2, base - size * 0.35)):
                mv.text_shaped(c, wd, x, base, font, size, col, al, 'right', axes)
        x -= ww + space
    return x_right - x - space


def lines(c, rows, x, y, f, t, t0, leading=1.15, line_each=0.14, **kw):
    """Several lines revealed one after another; y is the first line's cap-top (anchor='top').
    Extra keywords go to reveal(). Returns the block height."""
    lh = f.getSize() * leading
    for i, row in enumerate(rows):
        reveal(c, row, x, y + i * lh, f, t, t0 + i * line_each, anchor='top', **kw)
    return mv.cap_height(f) + lh * (len(rows) - 1)


def fit_block(s, font, box_w, box_h, max_size=200, min_size=12, leading=1.1, tracking=0.0, **axes):
    """The largest font size (up to max_size) at which s, word-wrapped, fits box_w x box_h.
    Returns (font, lines). Use it for big statements that must fill a space in any language length."""
    lo, hi = float(min_size), float(max_size)
    best = None
    for _ in range(14):
        mid = (lo + hi) / 2
        f = mv.font(font, mid, **axes)
        rows = mv.wrap(s, f, box_w, tracking)
        h = mv.cap_height(f) + f.getSize() * leading * (len(rows) - 1)
        wmax = max(mv.width(r, f, tracking) for r in rows)
        if h <= box_h and wmax <= box_w:
            best, lo = (f, rows), mid
        else:
            hi = mid
    if best is None:
        f = mv.font(font, min_size, **axes)
        best = (f, mv.wrap(s, f, box_w, tracking))
    return best


def statement(c, s, rect, font, t, t0, max_size=180, leading=1.08, align='left', valign='middle', col='#FFFFFF',
              by='word', style='rise', each=0.07, line_each=0.12, tracking=-0.01, emphasis=None, em_col=None, **axes):
    """A big multi-line statement fitted into rect and revealed word by word; words in emphasis are
    drawn in em_col. Returns (font, lines)."""
    x0, y0, x1, y1 = rect
    f, rows = fit_block(s, font, x1 - x0, y1 - y0, max_size, 12, leading, tracking, **axes)
    h = mv.cap_height(f) + f.getSize() * leading * (len(rows) - 1)
    top = y0 if valign == 'top' else y1 - h if valign == 'bottom' else (y0 + y1 - h) / 2
    x = x0 if align == 'left' else x1 if align == 'right' else (x0 + x1) / 2
    n_before = 0
    for i, row in enumerate(rows):
        start = t0 + i * line_each + n_before * each * 0.5
        reveal(c, row, x, top + i * f.getSize() * leading, f, t, start, by=by, style=style, each=each,
               col=col, align=align, anchor='top', tracking=tracking,
               emphasis={w.lower() for w in (emphasis or [])}, em_col=em_col)
        n_before += len(row.split(' '))
    return f, rows


def scramble(c, s, x, y, f, t, t0, dur=1.0, col='#FFFFFF', a=1.0, align='left', anchor='middle',
             charset='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*<>/', seed=0, tracking=0.0, fps=30, rate=2):
    """A decoding effect: random characters settle into s from left to right over dur seconds.
    Characters keep the final text's positions, so the line never jitters."""
    if t < t0:
        return 0.0
    g = mv.graphemes(s)
    w = mv.width(s, f, tracking)
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    base = _base(f, y, anchor)
    n = max(1, len(g))
    frame = int(t * fps) // rate
    for i, ch in enumerate(g):
        if not ch.strip():
            continue
        start = t0 + dur * 0.35 * i / n
        settle = t0 + dur * (0.35 + 0.65 * i / n)
        if t < start:
            continue
        ox = mv.width(''.join(g[:i]), f, tracking) + (tracking * f.getSize() if i and tracking else 0.0)
        cw = mv.width(ch, f)
        if t >= settle:
            mv.text(c, ch, x0 + ox, base, f, col, a, 'left', 'baseline')
        else:
            h = (hash((i, frame, seed)) & 0xFFFFFF) % len(charset)
            rc = charset[h]
            mv.text(c, rc, x0 + ox + cw / 2, base, f, col, a * 0.75, 'center', 'baseline')
    return w


def _tabular(c, s, x, y, f, col, a, align, anchor, tracking=0.0):
    """Draw s with every digit in a cell as wide as the widest digit, so changing numbers never jitter."""
    dw = max(mv.width(d, f) for d in '0123456789')
    widths = [dw if ch.isdigit() else mv.width(ch, f) for ch in s]
    step = tracking * f.getSize()
    w = sum(widths) + step * max(0, len(s) - 1)
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    base = _base(f, y, anchor)
    for ch, cw in zip(s, widths):
        mv.text(c, ch, x0 + cw / 2, base, f, col, a, 'center', 'baseline')
        x0 += cw + step
    return w


def counter(c, x, y, f, t, t0, dur, start, end, fmt='{:,.0f}', col='#FFFFFF', a=1.0, align='left',
            anchor='middle', ease=mv.out_expo, tabular=True, tracking=0.0):
    """A number counting from start to end over [t0, t0 + dur], formatted with fmt ('{:,.0f}',
    '${:,.2f}', '{:.0f}%'). tabular keeps digits in fixed cells. Returns the drawn string."""
    v = mv.lerp(start, end, ease(mv.seg(t, t0, t0 + dur)))
    s = fmt.format(v)
    if tabular:
        _tabular(c, s, x, y, f, col, a, align, anchor, tracking)
    else:
        mv.text(c, s, x, y, f, col, a, align, anchor, tracking)
    return s


def odometer(c, x, y, f, value, col='#FFFFFF', a=1.0, align='left', anchor='middle', digits=None, sep=',',
             min_digits=1):
    """Rolling digits like a mechanical counter; value is a float (animate it with mv.tween).
    Lower digits roll continuously; higher ones turn over when the digit below passes 9."""
    value = max(0.0, value)
    n = max(min_digits, len(str(int(value))) if digits is None else digits)
    dw = max(mv.width(d, f) for d in '0123456789')
    sw = mv.width(sep, f) if sep else 0.0
    groups = (n - 1) // 3 if sep else 0
    w = n * dw + groups * sw
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    base = _base(f, y, anchor)
    lh = f.getSize() * 1.15
    ch = mv.cap_height(f)
    cx = x0
    for k in range(n - 1, -1, -1):
        d = value / 10 ** k
        digit = int(d) % 10
        if k == 0:
            frac = d - math.floor(d)
        else:
            lower = (value / 10 ** (k - 1)) % 10
            frac = mv.clamp(lower - 9)
        frac = mv.smoothstep(frac)
        with mv.Clip(c, (cx - 2, base - ch * 1.22, cx + dw + 2, base + ch * 0.22)):
            mv.text(c, str(digit), cx + dw / 2, base - frac * lh, f, col, a, 'center', 'baseline')
            mv.text(c, str((digit + 1) % 10), cx + dw / 2, base - frac * lh + lh, f, col, a, 'center', 'baseline')
        cx += dw
        if sep and k % 3 == 0 and k > 0:
            mv.text(c, sep, cx, base, f, col, a, 'left', 'baseline')
            cx += sw
    return w


def rotator(c, words, x, y, f, t, period=1.8, trans=0.45, col='#FFFFFF', a=1.0, align='left', anchor='middle', t0=0.0):
    """Cycle through words in place: each slides up and out as the next slides in.
    Loop-safe when the loop length is a multiple of len(words) * period."""
    u = max(0.0, t - t0)
    i = int(u // period) % len(words)
    ph = u % period
    base = _base(f, y, anchor)
    lh = f.getSize() * 1.2
    ch = mv.cap_height(f)
    k = mv.inout_cubic(mv.seg(ph, period - trans, period))
    wmax = max(mv.width(w, f) for w in words)
    left = x - wmax / 2 if align == 'center' else x - wmax if align == 'right' else x
    with mv.Clip(c, (left - f.getSize(), base - ch - lh * 0.35, left + wmax + f.getSize(), base + lh * 0.3)):
        mv.text(c, words[i], x, base - k * lh, f, col, a * (1 - k * 0.6), align, 'baseline')
        if k > 0:
            mv.text(c, words[(i + 1) % len(words)], x, base + (1 - k) * lh, f, col, a, align, 'baseline')
    return wmax


def highlight(c, rect, t, t0, dur=0.45, col='#FACC15', a=0.35, radius=6.0, skew=0.0):
    """A marker-pen highlight sweeping left to right behind a word (draw it before the text)."""
    p = mv.out_cubic(mv.seg(t, t0, t0 + dur))
    if p <= 0:
        return
    x0, y0, x1, y1 = rect
    c.save()
    if skew:
        c.skew(skew, 0)
    mv.rrect(c, x0, y0, x0 + (x1 - x0) * p, y1, radius, mv.paint(col, a))
    c.restore()


def underline(c, x0, x1, y, t, t0, dur=0.4, col='#FFFFFF', width=6.0, a=1.0):
    """A line that draws itself under a word."""
    p = mv.out_cubic(mv.seg(t, t0, t0 + dur))
    if p > 0:
        c.drawLine(x0, y, x0 + (x1 - x0) * p, y, mv.paint(col, a, stroke=width))


def strike(c, x0, x1, y, t, t0, dur=0.35, col='#EF4444', width=6.0, a=1.0):
    """A line drawn through a word (a price cut, a crossed-out claim)."""
    underline(c, x0, x1, y, t, t0, dur, col, width, a)


def circle_mark(c, rect, t, t0, dur=0.7, col='#F43F5E', width=5.0, seed=1):
    """A hand-drawn loop around a word or number, drawn on over dur."""
    p = mv.out_cubic(mv.seg(t, t0, t0 + dur))
    if p <= 0:
        return
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 * 1.12, (y1 - y0) / 2 * 1.3
    rng = np.random.default_rng(seed)
    wob = rng.uniform(-0.05, 0.05, 4)
    pth = skia.Path()
    steps = 90
    for k in range(steps + 1):
        a = -2.2 + 2 * math.pi * 1.08 * k / steps
        r = 1 + wob[0] * math.sin(a * 2) + wob[1] * math.cos(a * 3)
        px, py = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a) + wob[2] * ry * k / steps
        if k == 0:
            pth.moveTo(px, py)
        else:
            pth.lineTo(px, py)
    c.drawPath(mv.trim(pth, 0, p), mv.paint(col, 1, stroke=width))


def weight_wave(c, s, x, y, font, size, t, lo=250, hi=900, period=2.0, spread=0.6, col='#FFFFFF', a=1.0,
                align='center', anchor='middle', tracking=0.0):
    """Letters breathe between two weights of a variable font in a travelling wave.
    Loop-safe when the loop length is a multiple of period."""
    g = [ch for ch in mv.graphemes(s)]
    n = max(1, len(g))
    fonts = []
    for i in range(n):
        wv = lo + (hi - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * (t / period - spread * i / n)))
        fonts.append(mv.font(font, size, wght=round(wv / 10) * 10))
    step = tracking * size
    widths = [mv.width(ch, fn) for ch, fn in zip(g, fonts)]
    w = sum(widths) + step * (n - 1)
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    base = _base(fonts[0], y, anchor)
    for ch, fn, cw in zip(g, fonts, widths):
        mv.text(c, ch, x0, base, fn, col, a, 'left', 'baseline')
        x0 += cw + step
    return w


def marquee(c, s, y, f, t, W, speed=120.0, col='#FFFFFF', a=1.0, sep='  •  ', x0=0.0, period=None,
            anchor='middle', tracking=0.0):
    """An endless ticker across the frame. With period, the speed is nudged so the ticker repeats
    exactly every period seconds (loop-safe)."""
    unit = s + sep
    uw = mv.width(unit, f, tracking)
    if period:
        speed = max(1, round(speed * period / uw)) * uw / period
    off = (speed * t) % uw
    x = x0 - off
    while x < W:
        mv.text(c, unit, x, y, f, col, a, 'left', anchor, tracking)
        x += uw
