"""brand.py: brand kits: colours from CSS variables (hex, rgb, hsl, oklch, shadcn-style bare HSL),
brand.json files, palettes, contrast checks, and colours picked from images and SVG logos.

    b = brand.from_css('globals.css', dark=True)       # shadcn / Tailwind tokens -> roles
    b = brand.load('brand/')                           # a folder with brand.json, logo.svg, fonts/
    th = ui.theme_from_brand(b)                        # every UI component in brand colours
    brand.contrast('#7C3AED', '#FFFFFF')               # 5.7 (WCAG ratio)

brand.json:
    {"name": "Acme", "url": "https://acme.com", "tagline": "...",
     "colors": {"primary": "#7C3AED", "secondary": "#A78BFA", "bg": "#0B0B10", "text": "#F5F5F7"},
     "fonts": {"display": "Space Grotesk", "body": "Inter", "mono": "JetBrains Mono", "arabic": "IBM Plex Sans Arabic"},
     "logo": "logo.svg", "logo_on_dark": "logo-white.svg", "radius": 16, "css": "globals.css"}
"""
import dataclasses
import json
import math
import os
import re

try:
    from . import mv
except ImportError:
    import mv

NAMED = {'white': '#FFFFFF', 'black': '#000000', 'red': '#FF0000', 'green': '#008000', 'blue': '#0000FF',
         'yellow': '#FFFF00', 'orange': '#FFA500', 'purple': '#800080', 'gray': '#808080', 'grey': '#808080',
         'transparent': None, 'currentcolor': None, 'inherit': None, 'none': None}


@dataclasses.dataclass
class Brand:
    name: str = 'Brand'
    colors: dict = dataclasses.field(default_factory=dict)
    fonts: dict = dataclasses.field(default_factory=dict)
    logo: str = None
    logo_on_dark: str = None
    radius: float = None
    url: str = None
    tagline: str = None
    extra: dict = dataclasses.field(default_factory=dict)

    def color(self, role, default=None):
        return self.colors.get(role, default)

    def logo_for(self, dark=True):
        """The logo to use on a dark (or light) background."""
        return (self.logo_on_dark or self.logo) if dark else self.logo

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({k: v for k, v in dataclasses.asdict(self).items() if v not in (None, {}, '')}, fh, indent=2)
        return path


# ---- colour parsing and spaces ----------------------------------------------------------------

def _num(s, scale=1.0):
    s = s.strip()
    if s.endswith('%'):
        return float(s[:-1]) / 100 * scale
    return float(s)


def _hue(s):
    s = s.strip().lower()
    for unit, k in (('deg', 1.0), ('grad', 0.9), ('rad', 180 / math.pi), ('turn', 360.0)):
        if s.endswith(unit):
            return float(s[:-len(unit)]) * k
    return float(s)


def hsl_to_rgb(h, s, l):
    h = (h % 360) / 360
    def f(n):
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))
    return (f(0) * 255, f(8) * 255, f(4) * 255)


def oklch_to_rgb(L, C, h):
    """OKLCH -> sRGB (0..255), reducing chroma until the colour fits the sRGB gamut."""
    for _ in range(40):
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        if all(-0.0005 <= v <= 1.0005 for v in lin) or C < 1e-4:
            break
        C *= 0.95
    return mv.from_oklab(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))


def to_oklch(col):
    L, a, b = mv.to_oklab(col)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def parse_color(value):
    """A CSS colour -> '#RRGGBB' (None for transparent/unknown). Handles #rgb, #rrggbb(aa), rgb()/rgba(),
    hsl()/hsla(), oklch(), oklab(), bare shadcn HSL ('222.2 84% 4.9%') and basic names."""
    v = value.strip().rstrip(';').strip()
    lv = v.lower()
    if lv in NAMED:
        return NAMED[lv]
    if re.fullmatch(r'#[0-9a-fA-F]{3,8}', v):
        h = v[1:]
        if len(h) in (3, 4):
            h = ''.join(ch * 2 for ch in h[:3])
        return '#' + h[:6].upper()
    m = re.fullmatch(r'(rgba?|hsla?|oklch|oklab)\((.*)\)', lv)
    if m:
        fn, args = m[1], re.split(r'[\s,/]+', m[2].strip())
        args = [x for x in args if x]
        if fn.startswith('rgb'):
            rgb = [_num(x, 255) for x in args[:3]]
        elif fn.startswith('hsl'):
            rgb = hsl_to_rgb(_hue(args[0]), _num(args[1], 1) if '%' in args[1] else float(args[1]) / 100,
                             _num(args[2], 1) if '%' in args[2] else float(args[2]) / 100)
        elif fn == 'oklch':
            L = _num(args[0], 1.0)
            C = _num(args[1], 0.4)
            rgb = oklch_to_rgb(L, C, _hue(args[2]) if args[2] != 'none' else 0.0)
        else:
            rgb = mv.from_oklab(_num(args[0], 1.0), _num(args[1], 0.4), _num(args[2], 0.4))
        return mv.hex_color(rgb)
    m = re.fullmatch(r'(-?[\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%', v)
    if m:   # shadcn v3 style bare HSL channels
        return mv.hex_color(hsl_to_rgb(float(m[1]), float(m[2]) / 100, float(m[3]) / 100))
    return None


def adjust(col, l=None, c=None, h=None, dl=0.0, dc=0.0, dh=0.0):
    """Change a colour in OKLCH: set or shift lightness (0..1), chroma (0..0.4) or hue (degrees)."""
    L, C, H = to_oklch(col)
    L = (L if l is None else l) + dl
    C = max(0.0, (C if c is None else c) + dc)
    H = (H if h is None else h) + dh
    return mv.hex_color(oklch_to_rgb(mv.clamp(L), C, H))


def lighten(col, amount=0.1):
    return adjust(col, dl=amount)


def darken(col, amount=0.1):
    return adjust(col, dl=-amount)


def tints(col, n=9, lo=0.97, hi=0.25):
    """n steps of one hue from very light to dark (like a 50..900 scale), keeping its chroma feel."""
    L, C, H = to_oklch(col)
    out = []
    for i in range(n):
        l = lo + (hi - lo) * i / max(1, n - 1)
        edge = 1 - abs(l - 0.6) / 0.6
        out.append(mv.hex_color(oklch_to_rgb(l, C * (0.25 + 0.75 * max(0.0, edge)), H)))
    return out


def luminance(col):
    r, g, b = (mv._to_linear(v) for v in mv.rgb(col))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio between two colours (1..21). Body text needs 4.5, large text 3."""
    la, lb = luminance(a), luminance(b)
    return round((max(la, lb) + 0.05) / (min(la, lb) + 0.05), 2)


def readable(bg, light='#FFFFFF', dark='#111111'):
    """The text colour (light or dark) with the better contrast on bg."""
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def check_text(fg, bg, large=False):
    """(ratio, passes WCAG AA) for text colour fg on bg."""
    r = contrast(fg, bg)
    return r, r >= (3.0 if large else 4.5)


# ---- reading brand sources -------------------------------------------------------------------

def css_vars(css, selector=':root'):
    """Custom properties (--name: value) declared in the blocks matching selector, in order."""
    text = css if '{' in css else open(css, encoding='utf-8').read()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out = {}
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', text):
        sels = [s.strip() for s in m[1].split(';')[-1].split(',')]
        if selector in sels or (selector == ':root' and 'html' in sels):
            for d in re.finditer(r'--([\w-]+)\s*:\s*([^;]+);', m[2]):
                out[d[1]] = d[2].strip()
    return out


def _resolve(vars_, v, depth=0):
    m = re.fullmatch(r'var\(\s*--([\w-]+)\s*(?:,\s*(.+))?\)', v.strip())
    if m and depth < 8:
        if m[1] in vars_:
            return _resolve(vars_, vars_[m[1]], depth + 1)
        return _resolve(vars_, m[2], depth + 1) if m[2] else v
    return v


ROLE_KEYS = {  # brand role: candidate CSS variable names, best first
    'primary': ['brand-primary', 'app-primary', 'primary', 'brand', 'accent-color'],
    'secondary': ['brand-secondary', 'app-primary-light', 'primary-light', 'chart-2', 'secondary-brand'],
    'bg': ['background', 'bg', 'page'],
    'surface': ['card', 'surface', 'popover'],
    'surface2': ['muted', 'secondary', 'surface-2'],
    'border': ['border', 'input'],
    'text': ['foreground', 'text', 'card-foreground'],
    'muted': ['muted-foreground', 'text-muted', 'secondary-foreground'],
    'on_accent': ['primary-foreground'],
    'danger': ['destructive', 'app-error', 'error', 'danger'],
    'success': ['success', 'app-success'],
    'warning': ['warning', 'app-warning'],
    'info': ['info'],
}


def from_css(css, dark=False, name='Brand'):
    """A Brand from a stylesheet's custom properties (shadcn, Tailwind v4 @theme, or any --tokens).
    dark=True applies the .dark block over :root."""
    text = css if '{' in css else open(css, encoding='utf-8').read()
    vars_ = css_vars(text, ':root')
    for sel in ('@theme', '@theme inline'):
        for k, v in css_vars(text, sel).items():
            vars_.setdefault(k, v)
    if dark:
        vars_.update(css_vars(text, '.dark'))
    colors = {}
    for role, keys in ROLE_KEYS.items():
        for k in keys:
            if k in vars_:
                col = parse_color(_resolve(vars_, vars_[k]))
                if col:
                    colors[role] = col
                    break
    if 'primary' in colors and 'secondary' not in colors:
        colors['secondary'] = lighten(colors['primary'], 0.12)
    fonts = {}
    for role, keys in (('body', ['font-sans', 'font-body', 'font']), ('mono', ['font-mono']), ('display', ['font-display', 'font-heading'])):
        for k in keys:
            if k in vars_:
                fam = re.findall(r'"([^"]+)"|\'([^\']+)\'|([A-Za-z][\w ]+)', vars_[k])
                names = [a or b or c for a, b, c in fam if (a or b or c).strip() and not (a or b or c).startswith('var')]
                if names:
                    fonts[role] = names[0].strip()
                    break
    radius = None
    if 'radius' in vars_:
        m = re.match(r'([\d.]+)(rem|px)?', vars_['radius'])
        if m:
            radius = float(m[1]) * (16 if m[2] == 'rem' else 1) * 1.6   # web px -> video px at 1080p
    return Brand(name=name, colors=colors, fonts=fonts, radius=radius, extra={'css_vars': len(vars_)})


def load(path):
    """A Brand from brand.json (or a folder containing it). Relative paths resolve next to the file;
    a fonts/ folder beside it is added to the font search path."""
    if os.path.isdir(path):
        folder, file = path, os.path.join(path, 'brand.json')
    else:
        folder, file = os.path.dirname(os.path.abspath(path)), path
    with open(file, encoding='utf-8') as fh:
        d = json.load(fh)
    b = Brand(name=d.get('name', 'Brand'))
    if d.get('css'):
        css_path = os.path.join(folder, d['css'])
        b = from_css(css_path, dark=d.get('dark', False), name=b.name)
    b.colors.update({k: parse_color(v) or v for k, v in d.get('colors', {}).items()})
    b.fonts.update(d.get('fonts', {}))
    for key in ('logo', 'logo_on_dark'):
        if d.get(key):
            setattr(b, key, os.path.join(folder, d[key]))
    b.radius = d.get('radius', b.radius)
    b.url, b.tagline = d.get('url'), d.get('tagline')
    b.extra.update({k: v for k, v in d.items() if k not in ('name', 'colors', 'fonts', 'logo', 'logo_on_dark', 'radius', 'url', 'tagline', 'css')})
    if os.path.isdir(os.path.join(folder, 'fonts')):
        mv.add_font_dir(os.path.join(folder, 'fonts'))
    return b


def svg_colors(path):
    """Colours used in an SVG (fill, stroke, stop-color, style attributes), most used first."""
    text = open(path, encoding='utf-8').read()
    found = re.findall(r'(?:fill|stroke|stop-color)\s*[:=]\s*["\']?\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|oklch\([^)]*\))', text)
    counts = {}
    for f in found:
        col = parse_color(f)
        if col:
            counts[col] = counts.get(col, 0) + 1
    return sorted(counts, key=lambda k: -counts[k])


def image_palette(path, k=5, seed=0, size=96):
    """Dominant colours of an image (k-means in OKLab on a thumbnail), most common first."""
    import numpy as np
    img = mv.image(path)
    small = img.resize(size, max(1, int(size * img.height() / img.width())))
    arr = small.toarray()[:, :, :3].reshape(-1, 3).astype(float) if hasattr(small, 'toarray') else None
    if arr is None:
        raise RuntimeError('could not read image pixels')
    lab = np.array([mv.to_oklab(tuple(p)) for p in arr])
    rng = np.random.default_rng(seed)
    cent = lab[rng.choice(len(lab), k, replace=False)]
    for _ in range(12):
        d = ((lab[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
        lab_i = d.argmin(axis=1)
        for j in range(k):
            if (lab_i == j).any():
                cent[j] = lab[lab_i == j].mean(axis=0)
    counts = np.bincount(lab_i, minlength=k)
    order = np.argsort(-counts)
    return [mv.hex_color(mv.from_oklab(*cent[j])) for j in order]
