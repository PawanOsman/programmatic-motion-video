"""charts.py: animated data graphics: columns and bars, lines with areas, donuts, stat tiles (KPIs),
sparklines, meters, heatmaps and legends. Every mark animates from a start time t0.

    st = charts.style(ui.DARK)                     # colours, fonts and ink from a ui.Theme
    charts.bars(c, (200, 200, 1000, 800), [42, 58, 71, 96], ['Q1', 'Q2', 'Q3', 'Q4'], t, 1.0, st=st, fmt='{:.0f}k')
    charts.line(c, rect, {'2025': [...], '2026': [...]}, x_labels, t, 2.0, st=st)
    charts.kpi(c, rect, 'Monthly users', 128400, t, 0.5, st=st, delta=+0.18)

Design rules (adapted for video from a validated data-viz method):
- One series = one colour for every bar; to make a point, highlight one bar and grey the rest
  (highlight=index). Colours are assigned to series in a fixed order, never by rank.
- Two or more series always get a legend; values are labelled selectively (bar tips, line ends).
- Text uses ink colours, never the series colour; grids are thin, solid and quiet.
- No dual axes: two measures on different scales belong in two charts.
- Donuts are for part-to-whole with at most 6 parts; close values belong in bars.
The categorical palettes below pass colour-vision-deficiency checks on light and dark surfaces.
"""
import dataclasses
import math

import skia

try:
    from . import icons, mv
except ImportError:
    import icons
    import mv

# fixed categorical order (validated: adjacent CVD separation >= 8.4, normal-vision >= 19, >= 3:1 on dark)
PALETTE_DARK = ['#3987E5', '#D95926', '#199E70', '#C98500', '#D55181', '#008300', '#9085E9', '#E66767']
PALETTE_LIGHT = ['#2A78D6', '#EB6834', '#1BAF7A', '#EDA100', '#E87BA4', '#008300', '#4A3AA7', '#E34948']
SEQUENTIAL_BLUE = ['#CDE2FB', '#9EC5F4', '#6DA7EC', '#3987E5', '#256ABF', '#184F95', '#0D366B']
STATUS = dict(good='#0CA30C', warning='#FAB219', serious='#EC835A', critical='#D03B3B')


@dataclasses.dataclass(frozen=True)
class Style:
    surface: str = '#15151D'
    text: str = '#F4F4F6'
    text2: str = '#C3C2CF'
    muted: str = '#8A8A99'
    grid: str = '#2A2A35'
    axis: str = '#3A3A48'
    gray: str = '#4A4A58'          # de-emphasis for 'everything else'
    accent: str = '#3987E5'        # the one series or bar the story is about
    series: tuple = tuple(PALETTE_DARK)
    good: str = '#0CA30C'
    bad: str = '#E0524F'
    font: str = 'Inter'
    scale: float = 1.0

    def s(self, v):
        return v * self.scale

    def color(self, i):
        return self.series[i % len(self.series)]


def style(theme=None, dark=True, accent=None, **kw):
    """A chart Style, optionally from a ui.Theme (its surface, ink, font and scale)."""
    if theme is not None:
        dark = theme.name != 'light'
    base = Style() if dark else Style(surface='#FFFFFF', text='#0B0B0B', text2='#52514E', muted='#7A7973',
                                      grid='#E6E5DF', axis='#C3C2B7', gray='#C9C8C1', accent='#2A78D6',
                                      series=tuple(PALETTE_LIGHT), good='#006300', bad='#C62828')
    f = {}
    if theme is not None:
        f = dict(surface=theme.surface, text=theme.text, muted=theme.muted, font=theme.font, scale=theme.scale)
    if accent:
        f['accent'] = accent
    f.update(kw)
    return dataclasses.replace(base, **f)


DEFAULT = Style()


def _f(st, px, wght=500):
    return mv.font(st.font, px, wght=wght)


def compact(v, prefix='', suffix='', decimals=1):
    """1284 -> '1,284', 12900 -> '12.9K', 4200000 -> '4.2M' (with an optional $ or % around it)."""
    a = abs(v)
    if a >= 1e9:
        s = f'{v / 1e9:.{decimals}f}B'
    elif a >= 1e6:
        s = f'{v / 1e6:.{decimals}f}M'
    elif a >= 1e4:
        s = f'{v / 1e3:.{decimals}f}K'
    else:
        s = f'{v:,.0f}'
    return prefix + s.replace('.0K', 'K').replace('.0M', 'M').replace('.0B', 'B') + suffix


def nice_ticks(lo, hi, n=5):
    """Round axis ticks covering lo..hi (0, 250, 500, ...)."""
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / max(1, n)
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
    start = math.floor(lo / step) * step
    ticks = []
    v = start
    while v <= hi + step * 0.5:
        ticks.append(round(v, 10))
        v += step
        if v > hi and ticks[-1] >= hi:
            break
    return ticks


def _fmt(fmt, v):
    return fmt(v) if callable(fmt) else fmt.format(v)


def legend(c, x, y, names, colors, st=DEFAULT, size=None, gap=None, a=1.0):
    """A row of colour keys and names starting at (x, y) (vertical centre). Returns its width."""
    fs = size or st.s(26)
    gap = gap or fs * 1.4
    f = _f(st, fs, 500)
    cx = x
    for n, col in zip(names, colors):
        mv.rrect(c, cx, y - fs * 0.3, cx + fs * 0.6, y + fs * 0.3, fs * 0.12, mv.paint(col, a))
        cx += fs * 0.95
        cx += mv.text(c, n, cx, y, f, st.text2, a) + gap
    return cx - gap - x


def _y_axis(c, rect, lo, hi, ticks, st, fmt, fs, a):
    x0, y0, x1, y1 = rect
    f = _f(st, fs, 450)
    for v in ticks:
        if v < lo - 1e-9 or v > hi + 1e-9:
            continue
        y = y1 - (v - lo) / (hi - lo) * (y1 - y0)
        c.drawLine(x0, y, x1, y, mv.paint(st.axis if abs(v) < 1e-12 else st.grid, a, stroke=st.s(1.5), cap='butt'))
        mv.text(c, _fmt(fmt, v), x0 - st.s(14), y, f, st.muted, a, 'right')


def bars(c, rect, values, labels=None, t=1e9, t0=0.0, dur=0.9, each=0.08, st=DEFAULT, colors=None,
         highlight=None, fmt='{:,.0f}', axis_fmt=None, horizontal=False, max_value=None, show_values=True,
         grid=True, ticks=5, series=None, legend_names=None, a=1.0, thickness=None):
    """Columns (or horizontal bars) growing from one baseline, staggered by `each`.
    values: a list (one series) or a list of lists (grouped series; pass series names for the legend).
    highlight: index of the bar to emphasise (others turn grey). Values count up as bars grow and
    sit at the bar tips."""
    x0, y0, x1, y1 = rect
    grouped = bool(values) and isinstance(values[0], (list, tuple))
    groups = values if grouped else [[v] for v in values]
    k = len(groups[0])
    n = len(groups)
    vmax = max_value if max_value is not None else max(max(g) for g in groups)
    tk = nice_ticks(0, vmax, ticks)
    top = tk[-1] if max_value is None else vmax
    fs = st.s(26)
    names = series or legend_names
    leg_h = st.s(52) if (grouped and names) else 0.0
    if grouped and names:
        legend(c, x0, y0 + st.s(12), names, [st.color(j) for j in range(k)], st, a=a)
    lab_h = st.s(54) if labels and not horizontal else 0.0
    if horizontal:
        f = _f(st, fs, 500)
        lab_w = max((mv.width(l, f) for l in (labels or [''])), default=0) + st.s(22)
        plot = (x0 + lab_w, y0 + leg_h, x1 - st.s(90), y1)
    else:
        plot = (x0 + (st.s(84) if grid else 0), y0 + leg_h + st.s(24), x1, y1 - lab_h)
    px0, py0, px1, py1 = plot
    if grid and not horizontal:
        _y_axis(c, plot, 0, top, tk, st, axis_fmt or fmt, st.s(24), a)
    elif not horizontal:
        c.drawLine(px0, py1, px1, py1, mv.paint(st.axis, a, stroke=st.s(1.5), cap='butt'))
    span = (py1 - py0) if not horizontal else (px1 - px0)
    band = ((px1 - px0) if not horizontal else (py1 - py0)) / n
    gap = st.s(4)
    th = thickness or min(band * (0.62 if not grouped else 0.8) / k, st.s(84))
    fv = _f(st, st.s(30), 640)
    fl = _f(st, st.s(26), 500)
    rad = min(st.s(7), th / 2)
    for i, g in enumerate(groups):
        p = mv.out_cubic(mv.seg(t, t0 + i * each, t0 + i * each + dur))
        c_band = (px0 if not horizontal else py0) + band * (i + 0.5)
        total = th * k + gap * (k - 1)
        for j, v in enumerate(g):
            if colors:
                col = colors[i if not grouped else j]
            elif grouped:
                col = st.color(j)
            elif highlight is not None:
                col = st.accent if i == highlight else st.gray
            else:
                col = st.accent
            L = (v / top) * span * p
            off = c_band - total / 2 + j * (th + gap)
            if horizontal:
                rect_ = (px0, off, px0 + L, off + th)
                radii = (0, rad, rad, 0)
            else:
                rect_ = (off, py1 - L, off + th, py1)
                radii = (rad, rad, 0, 0)
            if L > 0.5:
                mv.rrect(c, *rect_, radii, mv.paint(col, a))
            if show_values and p > 0.05 and (not grouped or k <= 3):
                s = _fmt(fmt, v * p)
                va = a * mv.seg(p, 0.3, 0.8)
                if horizontal:
                    mv.text(c, s, px0 + L + st.s(12), off + th / 2, fv, st.text, va)
                else:
                    mv.text(c, s, off + th / 2, py1 - L - st.s(26), fv, st.text, va, 'center')
        if labels:
            la = a * mv.clamp(mv.seg(t, t0 + i * each - 0.2, t0 + i * each + 0.3))
            if horizontal:
                mv.text(c, labels[i], px0 - st.s(18), c_band, fl, st.text2, la, 'right')
            else:
                mv.text(c, labels[i], c_band, py1 + st.s(32), fl, st.text2, la, 'center')
    if horizontal:
        c.drawLine(px0, py0, px0, py1, mv.paint(st.axis, a, stroke=st.s(1.5), cap='butt'))


def _points(vals, plot, lo, hi, n):
    px0, py0, px1, py1 = plot
    return [(px0 + (px1 - px0) * i / max(1, n - 1), py1 - (v - lo) / (hi - lo) * (py1 - py0)) for i, v in enumerate(vals)]


def _smooth_path(pts):
    pth = skia.Path()
    pth.moveTo(*pts[0])
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        xm = (x0 + x1) / 2
        pth.cubicTo(xm, y0, xm, y1, x1, y1)
    return pth


def line(c, rect, series, x_labels=None, t=1e9, t0=0.0, dur=1.6, st=DEFAULT, colors=None, area=None,
         fmt='{:,.0f}', axis_fmt=None, y_range=None, ticks=5, smooth=True, end_labels=True, dots=False,
         highlight=None, a=1.0, label_every=None, width=None):
    """Lines that draw themselves on, left to right. series: a list (one line), a list of lists or a
    dict {name: values}. area: a 10 % wash under a single line (default on for one series).
    highlight: name or index of the line to emphasise (others grey)."""
    if isinstance(series, dict):
        names, data = list(series), list(series.values())
    elif series and isinstance(series[0], (list, tuple)):
        names, data = [f'Series {i + 1}' for i in range(len(series))], list(series)
    else:
        names, data = [''], [series]
    x0, y0, x1, y1 = rect
    lo_v = min(min(d) for d in data)
    hi_v = max(max(d) for d in data)
    if y_range:
        lo, hi = y_range
        tk = nice_ticks(lo, hi, ticks)
    else:
        tk = nice_ticks(min(0.0, lo_v) if lo_v >= 0 and lo_v < hi_v * 0.35 else lo_v, hi_v, ticks)
        lo, hi = tk[0], tk[-1]
    multi = len(data) > 1
    hi_i = names.index(highlight) if isinstance(highlight, str) else highlight
    cols = []
    for idx in range(len(data)):
        col = (colors[idx] if colors else st.color(idx)) if (multi or colors) else st.accent
        if hi_i is not None:
            col = st.accent if idx == hi_i else st.gray
        cols.append(col)
    leg_h = st.s(52) if multi else 0.0
    if multi:
        legend(c, x0, y0 + st.s(14), names, cols, st, a=a)
    lab_h = st.s(54) if x_labels else 0.0
    plot = (x0 + st.s(90), y0 + leg_h + st.s(24), x1 - (st.s(130) if end_labels else st.s(10)), y1 - lab_h)
    _y_axis(c, plot, lo, hi, tk, st, axis_fmt or fmt, st.s(24), a)
    n = max(len(d) for d in data)
    p = mv.inout_cubic(mv.seg(t, t0, t0 + dur))
    lw = width or st.s(5)
    if x_labels:
        f = _f(st, st.s(24), 450)
        every = label_every or max(1, math.ceil(len(x_labels) / 8))
        for i, lab in enumerate(x_labels):
            if i % every == 0 or i == len(x_labels) - 1:
                xx = plot[0] + (plot[2] - plot[0]) * i / max(1, n - 1)
                mv.text(c, lab, xx, plot[3] + st.s(32), f, st.muted, a * mv.seg(t, t0 - 0.3, t0 + 0.2), 'center')
    order = list(range(len(data)))
    if hi_i is not None:
        order.remove(hi_i)
        order.append(hi_i)   # the emphasised line draws last, on top
    for idx in order:
        vals = data[idx]
        col = cols[idx]
        pts = _points(vals, plot, lo, hi, n)
        pth = _smooth_path(pts) if smooth else mv.poly(pts, False)
        if p <= 0:
            continue
        part = mv.trim(pth, 0, p)
        # position of the pen tip
        pm = skia.PathMeasure(pth, False)
        tip, _ = pm.getPosTan(pm.getLength() * p)
        if (area if area is not None else not multi):
            fill = skia.Path(part)
            fill.lineTo(tip.x(), plot[3])
            fill.lineTo(pts[0][0], plot[3])
            fill.close()
            c.drawPath(fill, mv.linear(0, plot[1], 0, plot[3], [col, col], [0.22 * a, 0.02 * a]))
        c.drawPath(part, mv.paint(col, a, stroke=lw))
        if dots:
            for (px, py) in pts:
                if px <= tip.x() + 0.5:
                    c.drawCircle(px, py, lw * 1.6, mv.paint(st.surface, a))
                    c.drawCircle(px, py, lw * 1.1, mv.paint(col, a))
        c.drawCircle(tip.x(), tip.y(), lw * 2.1, mv.paint(st.surface, a))
        c.drawCircle(tip.x(), tip.y(), lw * 1.45, mv.paint(col, a))
        if end_labels:
            k = (len(vals) - 1) * p
            i0 = int(k)
            v = vals[min(i0, len(vals) - 1)] + (vals[min(i0 + 1, len(vals) - 1)] - vals[min(i0, len(vals) - 1)]) * (k - i0)
            mv.text(c, _fmt(fmt, v), tip.x() + st.s(20), tip.y(), _f(st, st.s(28), 650), st.text, a)


def donut(c, cx, cy, r, values, labels=None, t=1e9, t0=0.0, dur=1.2, st=DEFAULT, colors=None, thickness=0.3,
          center=None, center_sub=None, gap_deg=1.6, legend_at=None, fmt='{:.0%}', a=1.0):
    """Part-to-whole as a ring (at most 6 parts). Segments sweep in one after another. center and
    center_sub are text in the hole; legend_at=(x, y) lists the parts with their shares."""
    total = float(sum(values))
    w = r * thickness
    rect = skia.Rect.MakeLTRB(cx - r + w / 2, cy - r + w / 2, cx + r - w / 2, cy + r - w / 2)
    p = mv.inout_cubic(mv.seg(t, t0, t0 + dur))
    c.drawCircle(cx, cy, r - w / 2, mv.paint(st.grid, a * 0.6, stroke=w))
    ang = -90.0
    for i, v in enumerate(values):
        sweep = 360 * v / total
        drawn = mv.clamp((p * 360 - (ang + 90)) / max(sweep, 1e-6)) * sweep
        if drawn > gap_deg:
            pth = skia.Path()
            pth.addArc(rect, ang + gap_deg / 2, drawn - gap_deg)
            c.drawPath(pth, mv.paint((colors or st.series)[i % 8], a, stroke=w, cap='butt'))
        ang += sweep
    if center:
        mv.text(c, center, cx, cy - (r * 0.1 if center_sub else 0), _f(st, r * 0.34, 700), st.text,
                a * mv.seg(t, t0 + dur * 0.5, t0 + dur), 'center')
    if center_sub:
        mv.text(c, center_sub, cx, cy + r * 0.2, _f(st, r * 0.13, 500), st.muted, a * mv.seg(t, t0 + dur * 0.5, t0 + dur), 'center')
    if legend_at and labels:
        lx, ly = legend_at
        fs = st.s(30)
        for i, (lab, v) in enumerate(zip(labels, values)):
            la = a * mv.seg(t, t0 + dur * i / len(values), t0 + dur * i / len(values) + 0.4)
            yy = ly + i * fs * 1.9
            mv.rrect(c, lx, yy - fs * 0.32, lx + fs * 0.64, yy + fs * 0.32, fs * 0.14, mv.paint((colors or st.series)[i % 8], la))
            mv.text(c, lab, lx + fs, yy, _f(st, fs, 500), st.text2, la)
            mv.text(c, _fmt(fmt, v / total), lx + fs * 11, yy, _f(st, fs, 650), st.text, la, 'right')


def sparkline(c, rect, values, t=1e9, t0=0.0, dur=1.0, col=None, end_col=None, st=DEFAULT, width=None, a=1.0):
    """A small trend line; the latest point is marked in end_col."""
    x0, y0, x1, y1 = rect
    lo, hi = min(values), max(values)
    hi = hi if hi > lo else lo + 1
    pts = [(x0 + (x1 - x0) * i / max(1, len(values) - 1), y1 - (v - lo) / (hi - lo) * (y1 - y0)) for i, v in enumerate(values)]
    pth = mv.poly(pts, False)
    p = mv.inout_cubic(mv.seg(t, t0, t0 + dur))
    if p <= 0:
        return
    c.drawPath(mv.trim(pth, 0, p), mv.paint(col or st.gray, a, stroke=width or st.s(3)))
    if p >= 1:
        c.drawCircle(*pts[-1], st.s(5.5), mv.paint(st.surface, a))
        c.drawCircle(*pts[-1], st.s(4), mv.paint(end_col or st.accent, a))


def kpi(c, rect, label, value, t=1e9, t0=0.0, dur=1.2, st=DEFAULT, fmt=None, delta=None, delta_fmt='{:+.0%}',
        good_up=True, period=None, spark=None, card=True, a=1.0):
    """A stat tile: label, a value that counts up, an optional delta (arrow + colour + text) and an
    optional sparkline. fmt: a format string or function; default is compact ('12.9K')."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    pad = min(w, h) * 0.12
    if card:
        mv.blur_shadow(c, x0, y0, x1, y1, st.s(18), 0.35 * a, st.s(30), st.s(12))
        mv.rrect(c, x0, y0, x1, y1, st.s(18), mv.paint(st.surface, a))
        mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, st.s(18), mv.paint(st.grid, a, stroke=st.s(1.5)))
    appear = mv.seg(t, t0 - 0.2, t0 + 0.3)
    mv.text(c, label, x0 + pad, y0 + pad + h * 0.06, _f(st, h * 0.12, 500), st.muted, a * appear)
    e = mv.out_expo(mv.seg(t, t0, t0 + dur))
    v = value * e
    s = _fmt(fmt, v) if fmt else compact(v)
    fv = _f(st, h * 0.3, 700)
    mv.text(c, s, x0 + pad, y0 + h * 0.5, fv, st.text, a * appear)
    if delta is not None:
        da = a * mv.seg(t, t0 + dur * 0.7, t0 + dur + 0.2)
        up = delta >= 0
        good = up == good_up
        col = st.good if good else st.bad
        fd = _f(st, h * 0.1, 650)
        dy = y1 - pad - h * 0.05
        icons.draw(c, 'trending-up' if up else 'trending-down', x0 + pad + h * 0.06, dy, h * 0.12, col, da, stroke=2.4)
        tw = mv.text(c, _fmt(delta_fmt, delta), x0 + pad + h * 0.16, dy, fd, col, da)
        if period:
            mv.text(c, period, x0 + pad + h * 0.2 + tw, dy, _f(st, h * 0.1, 450), st.muted, da)
    if spark:
        sparkline(c, (x0 + w * 0.6, y0 + h * 0.42, x1 - pad, y0 + h * 0.62), spark, t, t0 + 0.2, dur, st=st, a=a)


def meter(c, rect, frac, t=1e9, t0=0.0, dur=1.0, st=DEFAULT, col=None, label=None, fmt='{:.0%}', a=1.0):
    """A horizontal meter: the fill's colour carries the meaning, the track is a quiet step of it."""
    x0, y0, x1, y1 = rect
    h = y1 - y0
    col = col or st.accent
    p = mv.out_cubic(mv.seg(t, t0, t0 + dur))
    mv.rrect(c, x0, y0, x1, y1, h / 2, mv.paint(col, 0.2 * a))
    if p > 0:
        mv.rrect(c, x0, y0, x0 + max(h, (x1 - x0) * frac * p), y1, h / 2, mv.paint(col, a))
    if label:
        mv.text(c, label, x0, y0 - h * 1.1, _f(st, max(st.s(18), h * 0.9), 500), st.text2, a)
        mv.text(c, _fmt(fmt, frac * p), x1, y0 - h * 1.1, _f(st, max(st.s(18), h * 0.9), 650), st.text, a, 'right')


def ring(c, cx, cy, r, frac, t=1e9, t0=0.0, dur=1.2, st=DEFAULT, col=None, width=None, fmt='{:.0%}', sub=None, a=1.0):
    """A circular meter with its value in the middle."""
    w = width or r * 0.16
    col = col or st.accent
    p = mv.out_cubic(mv.seg(t, t0, t0 + dur))
    c.drawCircle(cx, cy, r, mv.paint(col, 0.18 * a, stroke=w))
    if p > 0:
        pth = skia.Path()
        pth.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), -90, 360 * frac * p)
        c.drawPath(pth, mv.paint(col, a, stroke=w))
    mv.text(c, _fmt(fmt, frac * p), cx, cy - (r * 0.12 if sub else 0), _f(st, r * 0.42, 700), st.text, a, 'center')
    if sub:
        mv.text(c, sub, cx, cy + r * 0.3, _f(st, r * 0.16, 500), st.muted, a, 'center')


def heatmap(c, rect, grid, t=1e9, t0=0.0, dur=1.2, st=DEFAULT, ramp=None, gap=None, radius=None, a=1.0):
    """A grid of cells coloured by value on a one-hue ramp (small values closest to the surface
    colour), revealed in a diagonal sweep. grid: rows of numbers."""
    x0, y0, x1, y1 = rect
    rows, cols = len(grid), len(grid[0])
    ramp = list(ramp or SEQUENTIAL_BLUE)
    if ramp is not None and sum(mv.rgb(st.surface)) < 3 * 128 and mv.to_oklab(ramp[0])[0] > mv.to_oklab(ramp[-1])[0]:
        ramp = ramp[::-1]   # on a dark surface, small values recede into the dark and large ones glow
    lo = min(min(r) for r in grid)
    hi = max(max(r) for r in grid)
    g = gap if gap is not None else st.s(4)
    cw = (x1 - x0 - g * (cols - 1)) / cols
    ch = (y1 - y0 - g * (rows - 1)) / rows
    rad = radius if radius is not None else min(cw, ch) * 0.18
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            k = (i + j) / max(1, rows + cols - 2)
            p = mv.out_cubic(mv.seg(t, t0 + dur * 0.7 * k, t0 + dur * 0.7 * k + dur * 0.3))
            if p <= 0:
                continue
            q = (v - lo) / (hi - lo) if hi > lo else 0.5
            pos = q * (len(ramp) - 1)
            m = int(min(len(ramp) - 2, math.floor(pos)))
            col = mv.mix(ramp[m], ramp[m + 1], pos - m)
            cx0 = x0 + j * (cw + g)
            cy0 = y0 + i * (ch + g)
            s = 0.6 + 0.4 * p
            mx, my = cx0 + cw / 2, cy0 + ch / 2
            mv.rrect(c, mx - cw * s / 2, my - ch * s / 2, mx + cw * s / 2, my + ch * s / 2, rad, mv.paint(col, a * p))
