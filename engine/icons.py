"""icons.py: 1,854 Lucide line icons as Skia paths, ready to draw, colour, animate or morph.

    icons.draw(c, 'rocket', x, y, 48, '#FFFFFF')          # centred on (x, y), 48 px
    icons.draw(c, 'check', x, y, 64, col, progress=p)    # draw-on animation, p: 0 -> 1
    icons.search('money')                                 # names whose name or tags match

Icons come from assets/icons/lucide.json.gz (Lucide, ISC licence). Browse names at lucide.dev/icons,
or render a contact sheet: icons.sheet(icons.search('arrow'), 'arrows.png').
"""
import functools
import gzip
import json
import re

import skia

try:
    from . import mv
except ImportError:
    import mv


@functools.lru_cache(maxsize=None)
def _data():
    with gzip.open(mv.asset('icons/lucide.json.gz'), 'rt', encoding='utf-8') as fh:
        return json.load(fh)


def names():
    """All icon names."""
    return sorted(_data()['icons'])


def exists(name):
    return name in _data()['icons']


def search(query, limit=40):
    """Icon names matching a word, by name first, then by Lucide's tags."""
    q = query.lower().strip()
    d = _data()
    by_name = [n for n in d['icons'] if q in n]
    by_tag = [n for n, tags in d['tags'].items() if n not in by_name and any(q in t for t in tags)]
    return (sorted(by_name, key=len) + sorted(by_tag, key=len))[:limit]


def _num(v):
    return float(v) if v not in (None, '') else 0.0


def _element(tag, at):
    p = skia.Path()
    g = lambda k: _num(at.get(k))
    if tag == 'path':
        return mv.svg_path(at['d'])
    if tag == 'circle':
        p.addCircle(g('cx'), g('cy'), g('r'))
    elif tag == 'ellipse':
        p.addOval(skia.Rect.MakeLTRB(g('cx') - g('rx'), g('cy') - g('ry'), g('cx') + g('rx'), g('cy') + g('ry')))
    elif tag == 'rect':
        rx = _num(at.get('rx', at.get('ry')))
        ry = _num(at.get('ry', at.get('rx')))
        p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(g('x'), g('y'), g('width'), g('height')), rx, ry))
    elif tag == 'line':
        p.moveTo(g('x1'), g('y1'))
        p.lineTo(g('x2'), g('y2'))
    elif tag in ('polyline', 'polygon'):
        nums = [float(v) for v in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', at['points'])]
        return mv.poly(list(zip(nums[::2], nums[1::2])), tag == 'polygon')
    return p


@functools.lru_cache(maxsize=4096)
def parts(name):
    """The icon's elements as (skia.Path in a 24x24 box, filled?) pairs."""
    d = _data()['icons']
    if name not in d:
        close = search(name.split('-')[0], 6)
        raise KeyError(f'no icon {name!r}; similar: {close}')
    return tuple((_element(tag, at), at.get('fill') not in (None, 'none')) for tag, at in d[name])


@functools.lru_cache(maxsize=4096)
def path(name):
    """The whole icon as one path in a 24x24 box (for trimming, morphing or clipping)."""
    out = skia.Path()
    for p, _ in parts(name):
        out.addPath(p)
    return out


def draw(c, name, x, y, size=24, col='#FFFFFF', a=1.0, stroke=2.0, align='center', progress=1.0, fill=None):
    """Draw an icon. (x, y) is its centre (align='center') or top-left corner ('topleft').
    stroke is in icon units (Lucide uses 2 in a 24 box) and scales with size.
    progress < 1 draws it on stroke by stroke; fill colours its closed shapes too."""
    if a <= 0 or progress <= 0:
        return
    s = size / 24.0
    c.save()
    c.translate(x - size / 2 if align == 'center' else x, y - size / 2 if align == 'center' else y)
    c.scale(s, s)
    pen = mv.paint(col, a, stroke=stroke)
    for p, filled in parts(name):
        if progress < 1:
            p = mv.trim(p, 0, progress)
        if filled or fill:
            c.drawPath(p, mv.paint(fill or col, a))
        c.drawPath(p, pen)
    c.restore()


def sheet(icon_names, out, cols=10, size=72, bg='#111116', col='#F4F4F5'):
    """Contact sheet of icons with their names, to choose icons by eye."""
    import numpy as np
    from PIL import Image
    cell_w, cell_h = size * 2.4, size * 1.9
    rows = (len(icon_names) + cols - 1) // cols
    W, H = int(cols * cell_w), int(rows * cell_h)
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
    f = mv.font('Inter', size * 0.2)
    with surf as c:
        c.clear(mv.color(bg))
        for i, n in enumerate(icon_names):
            cx = (i % cols + 0.5) * cell_w
            cy = (i // cols) * cell_h + size * 0.8
            draw(c, n, cx, cy, size, col)
            mv.text(c, n, cx, cy + size * 0.85, f, '#A1A1AA', align='center')
    Image.fromarray(arr[:, :, :3].copy()).save(out)
    return out
