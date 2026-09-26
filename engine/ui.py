"""ui.py: interface mockups for product and app demos, drawn as crisp vectors.

Devices: window (browser or app), phone, laptop. Controls: button, text_field, toggle, checkbox,
slider, tabs, menu. Content: card, chat (with typing dots and streaming answers), list_item,
table, media_card, avatar, badge, toast, tooltip, modal, skeleton, sidebar, steps, callout,
focus_ring, spinner, progress_bar.

Every component is a plain function of what to show at this moment, so animate by passing values
that depend on t: press=pointer.pressed(t, t_click), p=mv.presence(t, t_in, t_out), active=...

    th = ui.DARK.with_(accent='#6E00FF')            # or ui.theme_from_brand(brand)
    area = ui.window(c, (160, 90, 1760, 990), th, url='app.example.com')
    ui.button(c, (x0, y0, x1, y1), 'Generate', th, icon='sparkles', press=ptr.pressed(t, 3.2))

Sizes are canvas pixels. Theme.scale multiplies the default text sizes and paddings (use 2 at 4K).
"""
import contextlib
import dataclasses
import math

import skia

try:
    from . import icons, mv
except ImportError:
    import icons
    import mv


# ---- theme -----------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Theme:
    name: str = 'dark'
    bg: str = '#0B0B10'
    surface: str = '#15151D'
    surface2: str = '#1E1E29'
    border: str = '#2B2B39'
    text: str = '#F4F4F6'
    muted: str = '#9B9BAD'
    accent: str = '#7C3AED'
    accent2: str = '#A78BFA'
    on_accent: str = '#FFFFFF'
    success: str = '#22C55E'
    warning: str = '#F59E0B'
    danger: str = '#EF4444'
    info: str = '#3B82F6'
    radius: float = 16.0
    font: str = 'Inter'
    display: str = 'Inter'
    mono: str = 'JetBrains Mono'
    shadow: float = 0.5
    scale: float = 1.0
    syntax: tuple = (('keyword', '#C678DD'), ('string', '#98C379'), ('number', '#D19A66'), ('comment', '#7F848E'),
                     ('function', '#61AFEF'), ('type', '#E5C07B'), ('builtin', '#56B6C2'), ('punct', '#ABB2BF'),
                     ('plain', '#E6E6EA'), ('added', '#22C55E'), ('removed', '#EF4444'))

    def s(self, v):
        """A default size scaled by the theme."""
        return v * self.scale

    def syn(self, role):
        d = dict(self.syntax)
        return d.get(role, d['plain'])

    def with_(self, **kw):
        """A copy with some fields changed: DARK.with_(accent='#0EA5E9', radius=12)."""
        return dataclasses.replace(self, **kw)


DARK = Theme()
LIGHT = Theme(name='light', bg='#F3F4F8', surface='#FFFFFF', surface2='#F2F3F7', border='#E1E3EA', text='#15161B',
              muted='#6A6E7C', accent='#6D28D9', accent2='#7C3AED', shadow=0.16,
              syntax=(('keyword', '#A626A4'), ('string', '#50A14F'), ('number', '#986801'), ('comment', '#A0A1A7'),
                      ('function', '#4078F2'), ('type', '#C18401'), ('builtin', '#0184BC'), ('punct', '#383A42'),
                      ('plain', '#24292F'), ('added', '#15803D'), ('removed', '#B91C1C')))


def theme_from_brand(brand, dark=True, **kw):
    """A Theme from a brand.Brand (its colours and fonts), dark or light."""
    base = DARK if dark else LIGHT
    col = brand.colors
    fields = dict(accent=col.get('primary', base.accent), accent2=col.get('secondary', col.get('accent', base.accent2)))
    for k in ('bg', 'surface', 'surface2', 'border', 'text', 'muted', 'success', 'warning', 'danger', 'info', 'on_accent'):
        if k in col:
            fields[k] = col[k]
    if brand.fonts.get('body'):
        fields['font'] = brand.fonts['body']
    if brand.fonts.get('display'):
        fields['display'] = brand.fonts['display']
    if brand.fonts.get('mono'):
        fields['mono'] = brand.fonts['mono']
    if brand.radius is not None:
        fields['radius'] = brand.radius
    fields.update(kw)
    return base.with_(**fields)


# ---- small helpers ---------------------------------------------------------------------------

def _fnt(th, px, wght=500, family=None):
    return mv.font(family or th.font, px, wght=wght)


def _alpha(c, a, bounds=None):
    return mv.Layer(c, a, bounds=bounds) if a < 0.999 else contextlib.nullcontext(c)


def _mid(r):
    return (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def label(c, s, x, y, th, size=26, wght=500, col=None, a=1.0, align='left', anchor='middle', tracking=0.0, family=None):
    """Theme-styled single line of text; size is scaled by th.scale. Returns the width."""
    return mv.text(c, s, x, y, _fnt(th, th.s(size), wght, family), col or th.text, a, align, anchor, tracking)


def card(c, rect, th, fill=None, radius=None, border=True, shadow=True, a=1.0, border_col=None, elevation=1.0):
    """A rounded panel with a soft shadow and a hairline border."""
    x0, y0, x1, y1 = rect
    r = th.s(th.radius) if radius is None else radius
    m = th.s(90) * elevation
    with _alpha(c, a, (x0 - m, y0 - m, x1 + m, y1 + m * 1.4)):
        if shadow:
            mv.blur_shadow(c, x0, y0, x1, y1, r, th.shadow * 0.8, th.s(40) * elevation, th.s(18) * elevation)
        mv.rrect(c, x0, y0, x1, y1, r, mv.paint(fill or th.surface))
        if border:
            mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, r, mv.paint(border_col or th.border, 1, stroke=th.s(1.5)))


surface = card


# ---- devices ---------------------------------------------------------------------------------

def window(c, rect, th, title='', url=None, kind='browser', loading=None, a=1.0):
    """A desktop window. kind='browser' shows an address bar with url; kind='app' shows a centred
    title. loading (0..1) draws a progress line under the bar. Returns the content rect."""
    x0, y0, x1, y1 = rect
    s = th.s
    r, bar = s(14), s(58)
    m = s(120)
    with _alpha(c, a, (x0 - m, y0 - m, x1 + m, y1 + m * 1.3)):
        mv.blur_shadow(c, x0, y0, x1, y1, r, th.shadow, s(70), s(30))
        mv.rrect(c, x0, y0, x1, y1, r, mv.paint(th.surface))
        mv.rrect(c, x0, y0, x1, y0 + bar, (r, r, 0, 0), mv.paint(th.surface2))
        c.drawLine(x0, y0 + bar, x1, y0 + bar, mv.paint(th.border, 1, stroke=s(1.5)))
        for i, col in enumerate(('#FF5F57', '#FEBC2E', '#28C840')):
            c.drawCircle(x0 + s(28) + i * s(24), y0 + bar / 2, s(7), mv.paint(col))
        cy = y0 + bar / 2
        if kind == 'browser':
            ix = x0 + s(118)
            icons.draw(c, 'chevron-left', ix, cy, s(22), th.muted)
            icons.draw(c, 'chevron-right', ix + s(32), cy, s(22), th.muted, a=0.45)
            icons.draw(c, 'rotate-cw', ix + s(66), cy, s(18), th.muted)
            pw = min((x1 - x0) * 0.56, s(820))
            px0 = max((x0 + x1) / 2 - pw / 2, ix + s(96))
            mv.rrect(c, px0, y0 + s(12), px0 + pw, y0 + bar - s(12), s(10), mv.paint(th.bg if th.name == 'dark' else '#E9EBF1'))
            icons.draw(c, 'lock', px0 + s(22), cy, s(15), th.muted)
            if url:
                mv.text(c, url, px0 + s(40), cy, _fnt(th, s(19), 450), th.muted)
            if loading is not None and 0 < loading < 1:
                c.drawRect(skia.Rect.MakeLTRB(x0, y0 + bar - s(3), x0 + (x1 - x0) * mv.out_cubic(loading), y0 + bar),
                           mv.paint(th.accent))
        elif title:
            mv.text(c, title, (x0 + x1) / 2, cy, _fnt(th, s(20), 600), th.muted, align='center')
        mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, r, mv.paint(th.border, 1, stroke=s(1.5)))
    return x0, y0 + bar, x1, y1


def phone(c, rect, th, clock='9:41', a=1.0, body='#0F0F13', screen=None):
    """A modern phone (rect should be about 9:19.5). Draws the frame, screen, island, status bar
    and home indicator; returns the content rect between status bar and home indicator."""
    x0, y0, x1, y1 = rect
    w = x1 - x0
    R, bez = w * 0.165, w * 0.034
    m = w * 0.25
    fg = th.text
    with _alpha(c, a, (x0 - m, y0 - m, x1 + m, y1 + m)):
        mv.blur_shadow(c, x0, y0, x1, y1, R, th.shadow * 1.1, w * 0.18, w * 0.07)
        for side, ys in ((x0 - w * 0.012, (0.20, 0.27, 0.30, 0.37)), (x1, (0.25, 0.36))):
            for k in range(0, len(ys), 2):
                mv.rrect(c, side, y0 + (y1 - y0) * ys[k], side + w * 0.014, y0 + (y1 - y0) * ys[k + 1], w * 0.006, mv.paint('#2A2A31'))
        mv.rrect(c, x0, y0, x1, y1, R, mv.paint(body))
        mv.rrect(c, x0 + w * 0.004, y0 + w * 0.004, x1 - w * 0.004, y1 - w * 0.004, R, mv.paint('#4A4A55', 1, stroke=w * 0.007))
        sx0, sy0, sx1, sy1 = x0 + bez, y0 + bez, x1 - bez, y1 - bez
        mv.rrect(c, sx0, sy0, sx1, sy1, R - bez, mv.paint(screen or th.bg))
        iw, ih = w * 0.30, w * 0.088
        cx, iy = (x0 + x1) / 2, sy0 + w * 0.032
        mv.rrect(c, cx - iw / 2, iy, cx + iw / 2, iy + ih, ih / 2, mv.paint('#000000'))
        sb = iy + ih / 2
        mv.text(c, clock, sx0 + w * 0.15, sb, _fnt(th, w * 0.047, 600), fg, align='center')
        rx = sx1 - w * 0.12
        bw, bh = w * 0.066, w * 0.032
        mv.rrect(c, rx - bw / 2, sb - bh / 2, rx + bw / 2, sb + bh / 2, bh * 0.3, mv.paint(fg, 0.45, stroke=w * 0.004))
        mv.rrect(c, rx - bw / 2 + w * 0.006, sb - bh / 2 + w * 0.006, rx + bw * 0.25, sb + bh / 2 - w * 0.006, bh * 0.2, mv.paint(fg))
        c.drawRect(skia.Rect.MakeLTRB(rx + bw / 2 + w * 0.004, sb - bh * 0.2, rx + bw / 2 + w * 0.009, sb + bh * 0.2), mv.paint(fg, 0.45))
        icons.draw(c, 'wifi', rx - w * 0.085, sb, w * 0.05, fg, stroke=2.6)
        for k in range(4):
            bx = rx - w * 0.19 + k * w * 0.014
            hh = w * (0.012 + 0.0065 * k)
            mv.rrect(c, bx, sb + w * 0.016 - hh, bx + w * 0.009, sb + w * 0.016, w * 0.002, mv.paint(fg))
        hw = w * 0.36
        mv.rrect(c, cx - hw / 2, sy1 - w * 0.035, cx + hw / 2, sy1 - w * 0.022, w * 0.01, mv.paint(fg, 0.85))
    return sx0, iy + ih + w * 0.035, sx1, sy1 - w * 0.06


def laptop(c, rect, th, a=1.0, screen=None):
    """A laptop: lid with a thin bezel above a base. Returns the screen rect (16:10 works well)."""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    lid_b = y0 + h * 0.935
    lx0, lx1 = x0 + w * 0.065, x1 - w * 0.065
    m = w * 0.12
    with _alpha(c, a, (x0 - m, y0 - m, x1 + m, y1 + m)):
        mv.blur_shadow(c, x0 + w * 0.05, y1 - h * 0.1, x1 - w * 0.05, y1, w * 0.02, th.shadow, w * 0.05, w * 0.02)
        mv.rrect(c, lx0, y0, lx1, lid_b, (w * 0.022, w * 0.022, w * 0.004, w * 0.004), mv.paint('#1B1B21'))
        mv.rrect(c, lx0, y0, lx1, lid_b, (w * 0.022, w * 0.022, w * 0.004, w * 0.004), mv.paint('#50505C', 1, stroke=w * 0.0025))
        bz = w * 0.014
        scr = (lx0 + bz, y0 + bz * 1.35, lx1 - bz, lid_b - bz * 0.6)
        mv.rrect(c, *scr, w * 0.006, mv.paint(screen or th.bg))
        c.drawCircle((x0 + x1) / 2, y0 + bz * 0.68, w * 0.0028, mv.paint('#33333C'))
        base = mv.poly([(x0, lid_b), (x1, lid_b), (x1 - w * 0.012, y1), (x0 + w * 0.012, y1)])
        pb = mv.linear(0, lid_b, 0, y1, ['#C9CAD2', '#8D8E98'])
        c.drawPath(base, pb)
        nw = w * 0.14
        mv.rrect(c, (x0 + x1) / 2 - nw / 2, lid_b, (x0 + x1) / 2 + nw / 2, lid_b + (y1 - lid_b) * 0.38, w * 0.004, mv.paint('#9C9DA6'))
    return scr


# ---- controls --------------------------------------------------------------------------------

_KINDS = {  # fill, text, border
    'primary': ('accent', 'on_accent', None), 'secondary': ('surface2', 'text', 'border'),
    'ghost': (None, 'accent2', None), 'outline': (None, 'text', 'border'),
    'danger': ('danger', '#FFFFFF', None), 'success': ('success', '#FFFFFF', None),
}


def _c(th, v):
    return getattr(th, v) if v and not v.startswith('#') else v


def button(c, rect, text, th, kind='primary', press=0.0, hover=0.0, icon=None, a=1.0, size=None, radius=None,
           icon_right=None, fill=None, text_col=None):
    """A button. press (0..1) squashes and darkens it: pass pointer.pressed(t, t_click).
    kind: primary, secondary, ghost, outline, danger, success. fill overrides the colour (the text
    then turns black or white, whichever reads better, unless text_col is given)."""
    x0, y0, x1, y1 = rect
    cx, cy = _mid(rect)
    h = y1 - y0
    fk, tk, bk = _KINDS[kind]
    fcol = fill or _c(th, fk)
    tcol, bcol = _c(th, tk), _c(th, bk)
    if fill and not text_col:
        tcol = '#111114' if mv.to_oklab(fill)[0] > 0.72 else '#FFFFFF'
    tcol = text_col or tcol
    if fcol:
        fcol = mv.mix(mv.mix(fcol, '#FFFFFF', 0.10 * hover), '#000000', 0.14 * press)
    r = radius if radius is not None else min(th.s(th.radius * 0.85), h / 2)
    fs = size or h * 0.36
    m = h
    with mv.Layer(c, a, scale=1 - 0.045 * press, pivot=(cx, cy), bounds=(x0 - m, y0 - m, x1 + m, y1 + m * 1.4)):
        if kind in ('primary', 'danger', 'success') and fcol:
            mv.blur_shadow(c, x0 + h * 0.15, y0, x1 - h * 0.15, y1, r, 0.45 * (1 - 0.6 * press), h * 0.5, h * 0.22, fcol)
        if fcol:
            mv.rrect(c, x0, y0, x1, y1, r, mv.paint(fcol))
        if bcol:
            mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, r, mv.paint(bcol, 1, stroke=th.s(1.5)))
        f = _fnt(th, fs, 620)
        tw = mv.width(text, f) if text else 0.0
        isz = fs * 1.15
        gap = fs * 0.45
        total = tw + (isz + gap if icon else 0) + (isz + gap if icon_right else 0)
        x = cx - total / 2
        if icon:
            icons.draw(c, icon, x + isz / 2, cy, isz, tcol, stroke=2.2)
            x += isz + gap
        if text:
            mv.text(c, text, x, cy, f, tcol)
            x += tw + gap
        if icon_right:
            icons.draw(c, icon_right, x + isz / 2, cy, isz, tcol, stroke=2.2)


def text_field(c, rect, th, value='', placeholder='', focus=0.0, t=None, typing=False, icon=None, a=1.0, size=None,
               mono=False, radius=None, trailing=None):
    """An input box. focus (0..1) lights the border and ring; pass t to show a caret (solid while
    typing=True, blinking otherwise). Long values scroll so the end stays visible.
    trailing: an icon name drawn at the right end (a send or mic button)."""
    x0, y0, x1, y1 = rect
    h = y1 - y0
    r = radius if radius is not None else min(th.s(th.radius * 0.8), h / 2)
    fs = size or h * 0.36
    with _alpha(c, a, (x0 - 20, y0 - 20, x1 + 20, y1 + 20)):
        if focus > 0:
            g = th.s(5) * focus
            mv.rrect(c, x0 - g, y0 - g, x1 + g, y1 + g, r + g, mv.paint(th.accent, 0.22 * focus))
        mv.rrect(c, x0, y0, x1, y1, r, mv.paint(th.surface2))
        mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, r, mv.paint(mv.mix(th.border, th.accent, focus), 1, stroke=th.s(1.6)))
        tx = x0 + (h * 0.95 if icon else h * 0.38)
        right = x1 - (h * 0.95 if trailing else h * 0.38)
        cy = (y0 + y1) / 2
        if icon:
            icons.draw(c, icon, x0 + h * 0.5, cy, fs * 1.15, th.muted)
        if trailing:
            icons.draw(c, trailing, x1 - h * 0.5, cy, fs * 1.15, th.accent2 if value else th.muted)
        f = _fnt(th, fs, 450, th.mono if mono else None)
        with mv.Clip(c, (tx - 2, y0, right, y1)):
            if value:
                w = mv.width(value, f)
                shift = max(0.0, w - (right - tx - fs * 0.4))
                mv.text(c, value, tx - shift, cy, f, th.text)
                end = tx - shift + w
            else:
                if placeholder:
                    mv.text(c, placeholder, tx, cy, f, th.muted)
                end = tx
            if t is not None and focus > 0.5:
                mv.caret(c, end + fs * 0.08, cy + mv.cap_height(f) / 2, mv.cap_height(f) * 1.25, th.accent2, t, typing, max(2, fs * 0.08))


def toggle(c, x, y, on, th, size=None, a=1.0):
    """A switch at (x, y) = left edge, vertical centre. on (0..1) slides the knob."""
    h = size or th.s(36)
    w = h * 1.75
    on = mv.clamp(on)
    with _alpha(c, a, (x - 10, y - h, x + w + 10, y + h)):
        mv.rrect(c, x, y - h / 2, x + w, y + h / 2, h / 2, mv.paint(mv.mix(th.border, th.accent, on)))
        kx = x + h / 2 + (w - h) * mv.inout_cubic(on)
        mv.blur_shadow(c, kx - h * 0.4, y - h * 0.4, kx + h * 0.4, y + h * 0.4, h * 0.4, 0.3, h * 0.2, h * 0.06)
        c.drawCircle(kx, y, h * 0.4, mv.paint('#FFFFFF'))
    return w


def checkbox(c, x, y, checked, th, size=None, text=None, a=1.0):
    """A checkbox at (x, y) = left edge, vertical centre; checked (0..1) fills it and draws the tick."""
    s = size or th.s(30)
    with _alpha(c, a, (x - 10, y - s, x + s * 12, y + s)):
        mv.rrect(c, x, y - s / 2, x + s, y + s / 2, s * 0.25, mv.paint(th.surface2))
        mv.rrect(c, x, y - s / 2, x + s, y + s / 2, s * 0.25, mv.paint(th.accent, mv.clamp(checked * 2)))
        mv.rrect(c, x + 0.75, y - s / 2 + 0.75, x + s - 0.75, y + s / 2 - 0.75, s * 0.25,
                 mv.paint(mv.mix(th.border, th.accent, checked), 1, stroke=th.s(1.6)))
        if checked > 0:
            icons.draw(c, 'check', x + s / 2, y, s * 0.78, th.on_accent, stroke=3, progress=mv.seg(checked, 0.2, 1.0))
        if text:
            mv.text(c, text, x + s * 1.45, y, _fnt(th, s * 0.85, 480), th.text)


def slider(c, rect, value, th, a=1.0):
    """A horizontal slider in rect (its height is the knob size); value 0..1."""
    x0, y0, x1, y1 = rect
    h = y1 - y0
    cy = (y0 + y1) / 2
    tk = max(4.0, h * 0.2)
    with _alpha(c, a, (x0 - h, y0 - h, x1 + h, y1 + h)):
        mv.rrect(c, x0, cy - tk / 2, x1, cy + tk / 2, tk / 2, mv.paint(th.border))
        kx = x0 + (x1 - x0) * mv.clamp(value)
        mv.rrect(c, x0, cy - tk / 2, kx, cy + tk / 2, tk / 2, mv.paint(th.accent))
        mv.blur_shadow(c, kx - h * 0.4, cy - h * 0.4, kx + h * 0.4, cy + h * 0.4, h * 0.4, 0.3, h * 0.2, h * 0.08)
        c.drawCircle(kx, cy, h * 0.4, mv.paint('#FFFFFF'))


def tabs(c, rect, th, labels, active=0.0, size=None, a=1.0):
    """Tab labels spread across rect with an underline that glides to `active` (a float animates)."""
    x0, y0, x1, y1 = rect
    n = len(labels)
    w = (x1 - x0) / n
    cy = (y0 + y1) / 2
    f = _fnt(th, size or (y1 - y0) * 0.36, 560)
    with _alpha(c, a, (x0, y0, x1, y1 + 10)):
        c.drawLine(x0, y1, x1, y1, mv.paint(th.border, 1, stroke=th.s(1.5)))
        for i, s in enumerate(labels):
            near = 1 - mv.clamp(abs(active - i))
            mv.text(c, s, x0 + (i + 0.5) * w, cy, f, mv.mix(th.muted, th.text, near), align='center')
        i0 = int(math.floor(active))
        fr = active - i0
        tw0 = mv.width(labels[max(0, min(n - 1, i0))], f)
        tw1 = mv.width(labels[max(0, min(n - 1, i0 + 1))], f)
        tw = mv.lerp(tw0, tw1, fr) + th.s(16)
        mx = x0 + (active + 0.5) * w
        mv.rrect(c, mx - tw / 2, y1 - th.s(4), mx + tw / 2, y1, th.s(2), mv.paint(th.accent))


def menu(c, x, y, w, items, th, active=-1, p=1.0, size=None):
    """A dropdown menu whose top-left is (x, y). items: labels or (icon, label[, shortcut]).
    active highlights a row (float glides). p (0..1) unfolds it."""
    if p <= 0:
        return
    rh = size or th.s(54)
    pad = th.s(8)
    h = len(items) * rh + pad * 2
    with mv.Layer(c, mv.clamp(p * 1.4), scale=(1, 0.92 + 0.08 * mv.out_cubic(p)), pivot=(x, y),
                  bounds=(x - 60, y - 40, x + w + 60, y + h + 90)):
        card(c, (x, y, x + w, y + h), th, radius=th.s(12))
        if active >= 0:
            ay = y + pad + active * rh
            mv.rrect(c, x + pad, ay, x + w - pad, ay + rh, th.s(8), mv.paint(th.accent, 0.18))
        f = _fnt(th, rh * 0.4, 480)
        for i, it in enumerate(items):
            it = (None, it) if isinstance(it, str) else it
            cy = y + pad + (i + 0.5) * rh
            tx = x + pad + th.s(16)
            if it[0]:
                icons.draw(c, it[0], tx + rh * 0.2, cy, rh * 0.42, th.muted)
                tx += rh * 0.62
            mv.text(c, it[1], tx, cy, f, th.text)
            if len(it) > 2 and it[2]:
                mv.text(c, it[2], x + w - pad - th.s(16), cy, f, th.muted, align='right')


# ---- content ---------------------------------------------------------------------------------

def badge(c, x, y, text, th, col=None, fill=None, align='left', size=None, icon=None, a=1.0, dot=False):
    """A pill label; (x, y) is the left edge (or centre/right with align) at its vertical centre.
    Returns (x0, y0, x1, y1)."""
    fs = size or th.s(20)
    col = col or th.accent2
    f = _fnt(th, fs, 600)
    h = fs * 1.75
    pad = fs * 0.75
    lead = (fs * 1.15 if icon else 0) + (fs * 0.85 if dot else 0)
    w = mv.width(text, f) + pad * 2 + lead
    x0 = x - w / 2 if align == 'center' else x - w if align == 'right' else x
    with _alpha(c, a, (x0 - 4, y - h, x0 + w + 4, y + h)):
        mv.rrect(c, x0, y - h / 2, x0 + w, y + h / 2, h / 2, mv.paint(fill or col, 1.0 if fill else 0.16))
        tx = x0 + pad
        if dot:
            c.drawCircle(tx + fs * 0.25, y, fs * 0.25, mv.paint(col))
            tx += fs * 0.85
        if icon:
            icons.draw(c, icon, tx + fs * 0.45, y, fs * 0.95, col, stroke=2.4)
            tx += fs * 1.15
        mv.text(c, text, tx, y, f, col if not fill else th.on_accent)
    return x0, y - h / 2, x0 + w, y + h / 2


def avatar(c, cx, cy, r, th, initials='', img=None, col=None, ring=None, status=None, a=1.0):
    """A round avatar: an image (skia.Image) or initials on a colour; ring and status colours optional."""
    with _alpha(c, a, (cx - r * 1.4, cy - r * 1.4, cx + r * 1.4, cy + r * 1.4)):
        if ring:
            c.drawCircle(cx, cy, r * 1.12, mv.paint(ring, 1, stroke=r * 0.1))
        if img is not None:
            pth = skia.Path()
            pth.addCircle(cx, cy, r)
            with mv.Clip(c, pth):
                mv.cover(c, img, cx - r, cy - r, cx + r, cy + r)
        else:
            c.drawCircle(cx, cy, r, mv.paint(col or th.accent))
            if initials:
                mv.text(c, initials, cx, cy, _fnt(th, r * 0.8, 650), '#FFFFFF', align='center')
        if status:
            c.drawCircle(cx + r * 0.72, cy + r * 0.72, r * 0.26, mv.paint(th.surface))
            c.drawCircle(cx + r * 0.72, cy + r * 0.72, r * 0.18, mv.paint(status))


def progress_bar(c, rect, frac, th, col=None, track=None, a=1.0):
    x0, y0, x1, y1 = rect
    h = y1 - y0
    with _alpha(c, a, (x0 - 4, y0 - 4, x1 + 4, y1 + 4)):
        mv.rrect(c, x0, y0, x1, y1, h / 2, mv.paint(track or th.border))
        if frac > 0:
            mv.rrect(c, x0, y0, x0 + max(h, (x1 - x0) * mv.clamp(frac)), y1, h / 2, mv.paint(col or th.accent))


def spinner(c, cx, cy, r, t, th, col=None, width=None, a=1.0):
    """A loading ring, a pure function of t."""
    rect = skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r)
    w = width or r * 0.22
    c.drawCircle(cx, cy, r, mv.paint(col or th.accent, 0.18 * a, stroke=w))
    sweep = 90 + 120 * (0.5 + 0.5 * math.sin(t * 4.0))
    pth = skia.Path()
    pth.addArc(rect, (t * 400) % 360, sweep)
    c.drawPath(pth, mv.paint(col or th.accent, a, stroke=w))


def typing_dots(c, x, y, t, th, size=None, col=None, a=1.0):
    """Three bouncing dots ('someone is typing'); (x, y) is the centre."""
    s = size or th.s(10)
    for i in range(3):
        ph = max(0.0, math.sin(2 * math.pi * (t * 1.5 - i * 0.16)))
        c.drawCircle(x + (i - 1) * s * 2.3, y - s * 0.7 * ph, s * 0.72, mv.paint(col or th.muted, a * (0.45 + 0.55 * ph)))


def chat(c, rect, th, messages, t, size=None, gap=None, max_frac=0.78, pad=None, a=1.0, bot_icon='sparkles',
         user_fill=None, bot_fill=None, font=None):
    """A chat conversation that plays over time, scrolling to keep the newest message in view.
    messages: dicts with
      role  'user' or 'bot'
      text  the message (any script; mixed Arabic/English wraps and orders itself)
      at    time it appears (s)
      cps   stream it word by word at this many chars/s (bot answers); None shows it at once
      think seconds of typing dots before a streamed answer (default 0.9)
      rtl   True for right-to-left text
    Timing helpers: ui.chat_end(message) is when a message has fully appeared."""
    x0, y0, x1, y1 = rect
    fs = size or th.s(26)
    pad = th.s(22) if pad is None else pad
    gap = th.s(16) if gap is None else gap
    bx, by = fs * 0.78, fs * 0.58
    icon_w = fs * 1.9 if bot_icon else 0.0
    max_w = (x1 - x0 - 2 * pad - icon_w) * max_frac - 2 * bx
    fam = font or th.font
    items = []
    for m in messages:
        at = m['at']
        if t < at:
            continue
        user = m.get('role', 'user') == 'user'
        cps = m.get('cps')
        think = m.get('think', 0.9 if (cps and not user) else 0.0)
        p = mv.out_cubic(mv.seg(t, at, at + 0.32))
        if not user and t < at + think:
            items.append(dict(user=False, dots=True, w=fs * 3.4, h=fs * 2.1, p=p, t0=at))
            continue
        txt = mv.streamed(m['text'], t, at + think, cps) if cps else m['text']
        col = th.on_accent if user else th.text
        rtl = m.get('rtl', False)
        para = mv.para(txt or ' ', max_w, fs, fam, col, align='right' if rtl else 'left', rtl=rtl, wght=450)
        w = min(max_w, para.LongestLine) + 2 * bx
        items.append(dict(user=user, dots=False, para=para, w=w, h=para.Height + 2 * by, p=p if not cps or user else 1.0,
                          rtl=rtl, pw=min(max_w, para.LongestLine), t0=at))
    total = sum((it['h'] + gap) * it['p'] for it in items) - gap
    room = y1 - y0 - 2 * pad
    y = y0 + pad if total <= room else y1 - pad - total
    r = fs * 0.9
    with _alpha(c, a, rect), mv.Clip(c, rect):
        for it in items:
            w, h, p = it['w'], it['h'], it['p']
            if it['user']:
                bx1 = x1 - pad
                bx0 = bx1 - w
                radii = (r, r, r * 0.22, r)
                fill = user_fill or th.accent
                pivot = (bx1, y + h)
            else:
                bx0 = x0 + pad + icon_w
                bx1 = bx0 + w
                radii = (r, r, r, r * 0.22)
                fill = bot_fill or th.surface2
                pivot = (bx0, y + h)
            with mv.Layer(c, mv.clamp(p * 1.6), scale=0.9 + 0.1 * p, pivot=pivot, dy=(1 - p) * fs * 0.6,
                          bounds=(bx0 - icon_w - 20, y - 20, bx1 + 20, y + h + 40)):
                if not it['user'] and bot_icon:
                    ic = bx0 - icon_w + fs * 0.75
                    c.drawCircle(ic, y + h - fs * 0.75, fs * 0.75, mv.paint(th.accent, 0.2))
                    icons.draw(c, bot_icon, ic, y + h - fs * 0.75, fs * 0.9, th.accent2)
                mv.rrect(c, bx0, y, bx1, y + h, radii, mv.paint(fill))
                if it['dots']:
                    typing_dots(c, (bx0 + bx1) / 2, y + h / 2, t - it['t0'], th, fs * 0.2)
                else:
                    it['para'].paint(c, bx0 + bx - (max_w - it['pw'] if it['rtl'] else 0), y + by)
            y += (h + gap) * p


def chat_end(m):
    """When a chat message has fully appeared (for timing the next beat)."""
    cps = m.get('cps')
    if not cps:
        return m['at'] + 0.35
    think = m.get('think', 0.9 if m.get('role') != 'user' else 0.0)
    return m['at'] + think + len(m['text']) / cps


def list_item(c, rect, th, title, subtitle=None, icon=None, trailing=None, a=1.0, selected=0.0, icon_col=None):
    """A row: icon tile, title and subtitle, trailing text or badge; selected (0..1) tints it."""
    x0, y0, x1, y1 = rect
    h = y1 - y0
    cy = (y0 + y1) / 2
    with _alpha(c, a, (x0 - 10, y0 - 10, x1 + 10, y1 + 10)):
        if selected > 0:
            mv.rrect(c, x0, y0, x1, y1, th.s(12), mv.paint(th.accent, 0.16 * selected))
        tx = x0 + h * 0.3
        if icon:
            s = h * 0.62
            mv.rrect(c, tx, cy - s / 2, tx + s, cy + s / 2, s * 0.28, mv.paint(icon_col or th.accent, 0.16))
            icons.draw(c, icon, tx + s / 2, cy, s * 0.52, icon_col or th.accent2)
            tx += s + h * 0.25
        if subtitle:
            mv.text(c, title, tx, cy - h * 0.14, _fnt(th, h * 0.26, 600), th.text)
            mv.text(c, subtitle, tx, cy + h * 0.17, _fnt(th, h * 0.22, 450), th.muted)
        else:
            mv.text(c, title, tx, cy, _fnt(th, h * 0.28, 550), th.text)
        if trailing:
            mv.text(c, trailing, x1 - h * 0.3, cy, _fnt(th, h * 0.24, 550), th.muted, align='right')


def table(c, rect, th, header, rows, reveal=None, highlight=None, widths=None, row_h=None, size=None, a=1.0):
    """A data table. reveal (float) = how many rows are visible (the next one slides in);
    highlight (float) tints a row and can glide between rows; widths are column fractions."""
    x0, y0, x1, y1 = rect
    n = len(header)
    widths = widths or [1.0 / n] * n
    rh = row_h or th.s(58)
    fs = size or rh * 0.36
    fh = _fnt(th, fs * 0.8, 650)
    fb = _fnt(th, fs, 450)
    xs = [x0]
    for w in widths:
        xs.append(xs[-1] + w * (x1 - x0))
    pad = th.s(18)
    with _alpha(c, a, rect):
        for j, h in enumerate(header):
            mv.text(c, h.upper(), xs[j] + pad, y0 + rh / 2, fh, th.muted, tracking=0.06)
        c.drawLine(x0, y0 + rh, x1, y0 + rh, mv.paint(th.border, 1, stroke=th.s(1.5)))
        if highlight is not None and highlight >= 0:
            hy = y0 + rh * (1 + highlight)
            mv.rrect(c, x0, hy + 3, x1, hy + rh - 3, th.s(10), mv.paint(th.accent, 0.16))
        for i, row in enumerate(rows):
            vis = 1.0 if reveal is None else mv.out_cubic(mv.clamp(reveal - i))
            if vis <= 0:
                continue
            ry = y0 + rh * (1 + i)
            with mv.Layer(c, vis, dy=(1 - vis) * rh * 0.4, bounds=(x0, ry - rh, x1, ry + rh * 2)):
                for j, v in enumerate(row):
                    if isinstance(v, tuple):   # (text, colour) or ('badge', text, colour)
                        if v[0] == 'badge':
                            badge(c, xs[j] + pad, ry + rh / 2, v[1], th, col=v[2] if len(v) > 2 else None, size=fs * 0.75)
                            continue
                        mv.text(c, v[0], xs[j] + pad, ry + rh / 2, fb, v[1])
                    else:
                        mv.text(c, str(v), xs[j] + pad, ry + rh / 2, fb, th.text)
                c.drawLine(x0, ry + rh, x1, ry + rh, mv.paint(th.border, 0.6, stroke=th.s(1)))


def media_card(c, rect, th, img, title, subtitle=None, a=1.0, zoom=1.0, img_frac=0.66):
    """A card with an image on top (cover-fitted, zoom for a slow push) and text below."""
    x0, y0, x1, y1 = rect
    r = th.s(th.radius)
    ih = (y1 - y0) * img_frac
    with _alpha(c, a, (x0 - 80, y0 - 80, x1 + 80, y1 + 120)):
        card(c, rect, th)
        with mv.Clip(c, mv.rrect_shape(x0, y0, x1, y0 + ih, (r, r, 0, 0))):
            if img is not None:
                mv.cover(c, img, x0, y0, x1, y0 + ih, zoom=zoom)
            else:
                c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y0 + ih), mv.linear(x0, y0, x1, y0 + ih, [th.accent, th.accent2]))
        fs = th.s(26)
        mv.text(c, title, x0 + th.s(22), y0 + ih + (y1 - y0 - ih) * (0.36 if subtitle else 0.5), _fnt(th, fs, 620), th.text)
        if subtitle:
            mv.text(c, subtitle, x0 + th.s(22), y0 + ih + (y1 - y0 - ih) * 0.68, _fnt(th, fs * 0.8, 450), th.muted)


def skeleton(c, rect, t, th, radius=None):
    """A loading placeholder with a moving shimmer."""
    x0, y0, x1, y1 = rect
    r = radius if radius is not None else min(th.s(10), (y1 - y0) / 2)
    mv.rrect(c, x0, y0, x1, y1, r, mv.paint(th.surface2))
    w = x1 - x0
    sx = x0 - w + (2 * w + w) * ((t / 1.4) % 1.0)
    with mv.Clip(c, mv.rrect_shape(x0, y0, x1, y1, r)):
        c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1),
                   mv.linear(sx, y0, sx + w * 0.6, y0, [th.text, th.text, th.text], [0.0, 0.07, 0.0]))


def sidebar(c, rect, th, items, active=0.0, title=None, a=1.0, size=None):
    """A navigation column. items: (icon, label) pairs; active (float) moves the highlight."""
    x0, y0, x1, y1 = rect
    rh = size or th.s(56)
    pad = th.s(14)
    with _alpha(c, a, rect):
        c.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, y1), mv.paint(th.surface))
        c.drawLine(x1, y0, x1, y1, mv.paint(th.border, 1, stroke=th.s(1.5)))
        top = y0 + pad
        if title:
            mv.text(c, title, x0 + pad * 2, top + rh * 0.5, _fnt(th, rh * 0.36, 700), th.text)
            top += rh * 1.2
        ay = top + active * rh
        mv.rrect(c, x0 + pad, ay + 3, x1 - pad, ay + rh - 3, th.s(10), mv.paint(th.accent, 0.18))
        f = _fnt(th, rh * 0.32, 520)
        for i, (ic, lab) in enumerate(items):
            near = 1 - mv.clamp(abs(active - i))
            cy = top + (i + 0.5) * rh
            col = mv.mix(th.muted, th.text, near)
            icons.draw(c, ic, x0 + pad * 2 + rh * 0.2, cy, rh * 0.4, mv.mix(th.muted, th.accent2, near))
            mv.text(c, lab, x0 + pad * 2 + rh * 0.62, cy, f, col)


def toast(c, rect, th, title, body='', icon='circle-check', col=None, p=1.0, side='top'):
    """A notification card. p (0..1) slides it in from `side` ('top', 'bottom', 'right') and fades it."""
    if p <= 0:
        return
    x0, y0, x1, y1 = rect
    h = y1 - y0
    col = col or th.success
    e = mv.out_back(mv.clamp(p), 1.2) if p < 1 else 1.0
    dx = (1 - e) * (x1 - x0) * 0.6 if side == 'right' else 0.0
    dy = -(1 - e) * h * 1.2 if side == 'top' else (1 - e) * h * 1.2 if side == 'bottom' else 0.0
    with mv.Layer(c, mv.clamp(p * 1.5), dx=dx, dy=dy, bounds=(x0 - 90, y0 - 90, x1 + 90, y1 + 130)):
        card(c, rect, th, radius=th.s(16))
        s = h * 0.5
        cx = x0 + h * 0.5
        cy = (y0 + y1) / 2
        c.drawCircle(cx, cy, s / 2, mv.paint(col, 0.18))
        icons.draw(c, icon, cx, cy, s * 0.6, col, stroke=2.4)
        tx = x0 + h * 0.95
        if body:
            mv.text(c, title, tx, cy - h * 0.13, _fnt(th, h * 0.22, 650), th.text)
            mv.text(c, body, tx, cy + h * 0.15, _fnt(th, h * 0.19, 450), th.muted)
        else:
            mv.text(c, title, tx, cy, _fnt(th, h * 0.24, 600), th.text)


def tooltip(c, x, y, text, th, p=1.0, side='top', size=None):
    """A small dark label pointing at (x, y)."""
    if p <= 0:
        return
    fs = size or th.s(20)
    f = _fnt(th, fs, 550)
    w = mv.width(text, f) + fs * 1.4
    h = fs * 2.0
    ar = fs * 0.45
    by1 = y - ar if side == 'top' else y + ar + h
    by0 = by1 - h
    fill = '#111114' if th.name == 'light' else '#F4F4F6'
    tcol = '#FFFFFF' if th.name == 'light' else '#111114'
    with mv.Layer(c, mv.clamp(p * 1.5), scale=0.85 + 0.15 * mv.out_back(mv.clamp(p)), pivot=(x, y),
                  bounds=(x - w, by0 - 20, x + w, by1 + ar + 20)):
        mv.rrect(c, x - w / 2, by0, x + w / 2, by1, fs * 0.45, mv.paint(fill))
        tip = [(x - ar, by1), (x + ar, by1), (x, y)] if side == 'top' else [(x - ar, by0), (x + ar, by0), (x, y)]
        c.drawPath(mv.poly(tip), mv.paint(fill))
        mv.text(c, text, x, (by0 + by1) / 2, f, tcol, align='center')


def modal_buttons(rect, th, buttons=(('Cancel', 'secondary'), ('Confirm', 'primary'))):
    """Where modal() puts its buttons: a list of rects in the same order as buttons (for a Pointer)."""
    x0, y0, x1, y1 = rect
    pad = th.s(34)
    bh = th.s(60)
    bx = x1 - pad
    rects = []
    for lab, kind in reversed(buttons):
        bw = mv.width(lab, _fnt(th, bh * 0.36, 620)) + bh * 1.0
        rects.append((bx - bw, y1 - pad - bh, bx, y1 - pad))
        bx -= bw + th.s(14)
    return list(reversed(rects))


def modal(c, size, rect, th, title, body='', buttons=(('Cancel', 'secondary'), ('Confirm', 'primary')), p=1.0,
          press=None, icon=None, content=None):
    """A dialog over a dimmed screen. size = (W, H) of the canvas, or an (x0, y0, x1, y1) area to dim;
    press = (button index, amount). content(c, inner_rect) draws custom content (a form, a preview)
    inside the dialog's animation."""
    if p <= 0:
        return
    dim = size if len(size) == 4 else (0, 0, size[0], size[1])
    c.drawRect(skia.Rect.MakeLTRB(*dim), mv.paint('#000000', 0.45 * mv.clamp(p)))
    x0, y0, x1, y1 = rect
    cx, cy = _mid(rect)
    e = mv.out_back(mv.clamp(p), 1.1)
    with mv.Layer(c, mv.clamp(p * 1.5), scale=0.94 + 0.06 * e, pivot=(cx, cy), bounds=(x0 - 120, y0 - 120, x1 + 120, y1 + 160)):
        card(c, rect, th, radius=th.s(20), elevation=1.5)
        pad = th.s(34)
        ty = y0 + pad
        if icon:
            c.drawCircle(x0 + pad + th.s(26), ty + th.s(26), th.s(26), mv.paint(th.accent, 0.18))
            icons.draw(c, icon, x0 + pad + th.s(26), ty + th.s(26), th.s(28), th.accent2)
            ty += th.s(74)
        mv.text(c, title, x0 + pad, ty, _fnt(th, th.s(32), 700), th.text, anchor='top')
        if body:
            mv.text_block(c, body, x0 + pad, ty + th.s(56), x1 - x0 - 2 * pad, _fnt(th, th.s(23), 450), th.muted, leading=1.45)
        if content:
            content(c, (x0 + pad, ty + th.s(56), x1 - pad, y1 - pad - th.s(80)))
        for k, ((lab, kind), r) in enumerate(zip(buttons, modal_buttons(rect, th, buttons))):
            pr = press[1] if press and press[0] == k else 0.0
            button(c, r, lab, th, kind, press=pr)


def steps(c, x, y, labels, active, th, gap=None, size=None, a=1.0):
    """A horizontal stepper: numbered dots joined by a line that fills up to `active` (float)."""
    s = size or th.s(34)
    gap = gap or th.s(220)
    f = _fnt(th, s * 0.46, 650)
    fl = _fnt(th, s * 0.52, 520)
    with _alpha(c, a, (x - s, y - s * 2, x + gap * len(labels) + s, y + s * 3)):
        for i in range(len(labels) - 1):
            x0, x1 = x + i * gap + s * 0.6, x + (i + 1) * gap - s * 0.6
            c.drawLine(x0, y, x1, y, mv.paint(th.border, 1, stroke=th.s(3)))
            fr = mv.clamp(active - i)
            if fr > 0:
                c.drawLine(x0, y, x0 + (x1 - x0) * fr, y, mv.paint(th.accent, 1, stroke=th.s(3)))
        for i, lab in enumerate(labels):
            cx = x + i * gap
            on = mv.clamp(active - i + 1)
            done = mv.clamp(active - i)
            c.drawCircle(cx, y, s / 2, mv.paint(mv.mix(th.surface2, th.accent, on)))
            c.drawCircle(cx, y, s / 2, mv.paint(mv.mix(th.border, th.accent, on), 1, stroke=th.s(2)))
            if done >= 1:
                icons.draw(c, 'check', cx, y, s * 0.55, th.on_accent, stroke=3)
            else:
                mv.text(c, str(i + 1), cx, y, f, mv.mix(th.muted, th.on_accent, on), align='center')
            mv.text(c, lab, cx, y + s * 1.2, fl, mv.mix(th.muted, th.text, on), align='center')


def callout(c, target, box_xy, text, th, p=1.0, size=None, col=None):
    """An annotation: a dot on target (x, y), a line drawn to a label at box_xy (left-centre)."""
    if p <= 0:
        return
    tx, ty = target
    bx, by = box_xy
    col = col or th.accent2
    fs = size or th.s(24)
    line_p = mv.seg(p, 0.0, 0.6)
    c.drawCircle(tx, ty, fs * 0.28 * mv.out_back(mv.seg(p, 0, 0.3)), mv.paint(col))
    c.drawCircle(tx, ty, fs * 0.6 * mv.seg(p, 0, 0.5), mv.paint(col, 0.35 * (1 - mv.seg(p, 0.3, 0.9)), stroke=2))
    pth = skia.Path()
    pth.moveTo(tx, ty)
    pth.lineTo(bx, by)
    c.drawPath(mv.trim(pth, 0, line_p), mv.paint(col, 1, stroke=th.s(2.5)))
    lp = mv.seg(p, 0.5, 1.0)
    if lp > 0:
        f = _fnt(th, fs, 600)
        w = mv.width(text, f) + fs * 1.2
        left = bx if bx >= tx else bx - w
        with mv.Layer(c, lp, dx=(1 - mv.out_cubic(lp)) * fs * (0.6 if bx >= tx else -0.6), bounds=(left - 40, by - fs * 2, left + w + 40, by + fs * 2)):
            mv.rrect(c, left, by - fs * 0.95, left + w, by + fs * 0.95, fs * 0.5, mv.paint(th.surface2))
            mv.rrect(c, left, by - fs * 0.95, left + w, by + fs * 0.95, fs * 0.5, mv.paint(col, 1, stroke=th.s(1.5)))
            mv.text(c, text, left + fs * 0.6, by, f, th.text)


def focus_ring(c, rect, t, th, radius=None, col=None, a=1.0):
    """A pulsing ring that draws the eye to an element."""
    x0, y0, x1, y1 = rect
    r = th.s(th.radius) if radius is None else radius
    k = (t * 1.2) % 1.0
    g = th.s(6) + th.s(18) * mv.out_cubic(k)
    mv.rrect(c, x0 - g, y0 - g, x1 + g, y1 + g, r + g, mv.paint(col or th.accent2, a * 0.8 * (1 - k), stroke=th.s(3)))
    mv.rrect(c, x0 - th.s(5), y0 - th.s(5), x1 + th.s(5), y1 + th.s(5), r + th.s(5), mv.paint(col or th.accent2, a, stroke=th.s(2.5)))
