"""layout.py: frame sizes, safe areas, grids and a unit that scales one design to any resolution.

    W, H = layout.size('vertical')              # 1080x1920; also '1080p', '4k', '2k-portrait', ...
    L = layout.Frame(W, H)                      # L.u(48): 48 design px at 1080p, scaled to this frame
    title_box = L.safe('title')                 # (x0, y0, x1, y1) inside the title-safe area
    cells = layout.grid(L.safe('action'), 3, 2, gap=L.u(24))

Rects are (x0, y0, x1, y1) tuples everywhere, as in mv and ui.
"""
SIZES = {
    '720p': (1280, 720), '1080p': (1920, 1080), 'hd': (1920, 1080), '1440p': (2560, 1440), '2k': (2560, 1440),
    '4k': (3840, 2160), 'uhd': (3840, 2160),
    'vertical': (1080, 1920), 'story': (1080, 1920), 'reel': (1080, 1920), 'tiktok': (1080, 1920), 'shorts': (1080, 1920),
    'square': (1080, 1080), 'portrait': (1080, 1350), 'feed': (1080, 1350),
    '2k-portrait': (1440, 2560), '4k-portrait': (2160, 3840), '1080p-portrait': (1080, 1920),
    'ultrawide': (2560, 1080), 'dci-2k': (2048, 1080), 'twitter': (1280, 720), 'linkedin': (1920, 1080),
}


def size(name_or_wh):
    """(W, H) from a preset name ('1080p', 'vertical', '2k-portrait'...) or 'WxH'."""
    if isinstance(name_or_wh, (tuple, list)):
        return tuple(name_or_wh)
    key = str(name_or_wh).lower()
    if key in SIZES:
        return SIZES[key]
    w, h = key.replace(':', 'x').split('x')
    return int(w), int(h)


def orientation(W, H):
    return 'square' if abs(W - H) < 0.05 * max(W, H) else 'portrait' if H > W else 'landscape'


def inset(rect, dx, dy=None):
    dy = dx if dy is None else dy
    x0, y0, x1, y1 = rect
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def width(rect):
    return rect[2] - rect[0]


def height(rect):
    return rect[3] - rect[1]


def center(rect):
    return (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2


def anchor(rect, w, h, where='center', margin=0.0):
    """A w x h rect placed in rect at 'center', 'top', 'bottom', 'left', 'right', 'top-left', ..."""
    x0, y0, x1, y1 = inset(rect, margin)
    cx = (x0 + x1 - w) / 2
    cy = (y0 + y1 - h) / 2
    x = x0 if 'left' in where else x1 - w if 'right' in where else cx
    y = y0 if 'top' in where else y1 - h if 'bottom' in where else cy
    return x, y, x + w, y + h


def split_h(rect, fracs, gap=0.0):
    """Side-by-side rects; fracs are relative widths, e.g. (2, 1) for two-thirds and one-third."""
    x0, y0, x1, y1 = rect
    total = sum(fracs)
    avail = x1 - x0 - gap * (len(fracs) - 1)
    out, x = [], x0
    for f in fracs:
        w = avail * f / total
        out.append((x, y0, x + w, y1))
        x += w + gap
    return out


def split_v(rect, fracs, gap=0.0):
    """Stacked rects; fracs are relative heights."""
    x0, y0, x1, y1 = rect
    total = sum(fracs)
    avail = y1 - y0 - gap * (len(fracs) - 1)
    out, y = [], y0
    for f in fracs:
        h = avail * f / total
        out.append((x0, y, x1, y + h))
        y += h + gap
    return out


def grid(rect, cols, rows, gap=0.0):
    """cols x rows cells, row by row."""
    return [cell for row in split_v(rect, [1] * rows, gap) for cell in split_h(row, [1] * cols, gap)]


def fit_rect(w, h, box, mode='contain'):
    """Scale a w x h item into box ('contain' shows all of it, 'cover' fills the box); centred."""
    x0, y0, x1, y1 = box
    s = (min if mode == 'contain' else max)((x1 - x0) / w, (y1 - y0) / h)
    return anchor(box, w * s, h * s)


class Frame:
    """Size-aware layout helpers for one frame size. u(px) scales a size designed at 1080 px on the
    short side, so one layout serves 1080p, 4K, vertical and square outputs."""
    def __init__(self, W, H, base=1080):
        self.W, self.H = W, H
        self.unit = min(W, H) / base
        self.orientation = orientation(W, H)

    def u(self, px):
        return px * self.unit

    @property
    def rect(self):
        return 0, 0, self.W, self.H

    @property
    def center(self):
        return self.W / 2, self.H / 2

    @property
    def portrait(self):
        return self.orientation == 'portrait'

    def safe(self, kind='title'):
        """Safe areas: 'action' (3.5 % margins), 'title' (5 %, EBU R95), 'signage' (4 %),
        'social' (vertical feeds: clear of the app's caption and buttons at the bottom and right)."""
        W, H = self.W, self.H
        if kind == 'social':
            return W * 0.06, H * 0.12, W * 0.86, H * 0.78
        m = {'action': 0.035, 'title': 0.05, 'signage': 0.04}.get(kind, 0.05)
        return W * m, H * m, W * (1 - m), H * (1 - m)

    def pick(self, landscape, portrait, square=None):
        """Choose a value by orientation."""
        if self.orientation == 'square' and square is not None:
            return square
        return portrait if self.orientation == 'portrait' else landscape
