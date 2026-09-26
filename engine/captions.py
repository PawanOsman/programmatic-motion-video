"""captions.py: subtitles and word-timed captions from SRT, WebVTT or Whisper-style JSON, drawn in
several styles (plain, karaoke, one word at a time, pop-on, highlight box), including RTL scripts.

    cues = captions.load('talk.srt')                    # or .vtt, or whisper/whisperx .json
    cues = captions.chunk(cues, max_words=3)            # short, punchy social captions
    captions.draw(c, cues, t, (120, 760, 1800, 1000), style='karaoke')
    captions.to_srt(cues, 'out.srt')                    # a sidecar file for players and platforms

Without timings, captions.from_text(script, t0) spreads words over time at a reading pace.
Word timings from speech: faster-whisper (word_timestamps=True) or whisperx, saved as JSON.
Good captions: at most 42 characters per line, 2 lines, about 15-20 characters per second.
"""
import dataclasses
import json
import re

try:
    from . import mv
except ImportError:
    import mv


@dataclasses.dataclass
class Word:
    start: float
    end: float
    text: str


@dataclasses.dataclass
class Cue:
    start: float
    end: float
    text: str
    words: list = dataclasses.field(default_factory=list)


def _ts(s):
    s = s.strip().replace(',', '.')
    parts = s.split(':')
    sec = float(parts[-1])
    if len(parts) >= 2:
        sec += int(parts[-2]) * 60
    if len(parts) >= 3:
        sec += int(parts[-3]) * 3600
    return sec


def _fmt_ts(t, sep=','):
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f'{h:02d}:{m:02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)):03d}'


_TIME = re.compile(r'((?:\d+:)?\d+:\d+[.,]\d+)\s*-->\s*((?:\d+:)?\d+:\d+[.,]\d+)')


def _parse_blocks(text):
    cues = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').strip()):
        lines = block.strip().split('\n')
        for i, line in enumerate(lines):
            m = _TIME.search(line)
            if m:
                body = ' '.join(l.strip() for l in lines[i + 1:] if l.strip())
                body = re.sub(r'<[^>]+>', '', body)
                if body:
                    cues.append(Cue(_ts(m[1]), _ts(m[2]), body))
                break
    return cues


def load_srt(path):
    with open(path, encoding='utf-8-sig') as fh:
        return _parse_blocks(fh.read())


def load_vtt(path):
    with open(path, encoding='utf-8-sig') as fh:
        return _parse_blocks(fh.read())


def load_json(path, max_chars=42):
    """Whisper / faster-whisper / whisperx JSON ({'segments': [{start, end, text, words: [...]}]}),
    whisperx 'word_segments', or a plain list of words [{'start', 'end', 'word' or 'text'}]
    (words are grouped into cues of up to max_chars, breaking at pauses and sentence ends)."""
    with open(path, encoding='utf-8') as fh:
        d = json.load(fh)
    segs = (d.get('segments') or d.get('word_segments') or []) if isinstance(d, dict) else d

    def word(w):
        return Word(float(w['start']), float(w['end']), str(w.get('word', w.get('text', ''))).strip())
    flat = segs and all('words' not in s for s in segs) and all(len(str(s.get('word', s.get('text', ''))).split()) <= 1 for s in segs)
    if flat:
        cues, cur = [], []
        for w in (word(x) for x in segs if 'start' in x and 'end' in x):
            if not w.text:
                continue
            if cur and (len(' '.join(x.text for x in cur + [w])) > max_chars or w.start - cur[-1].end > 0.6
                        or cur[-1].text[-1:] in '.!?؟'):
                cues.append(Cue(cur[0].start, cur[-1].end, ' '.join(x.text for x in cur), cur))
                cur = []
            cur.append(w)
        if cur:
            cues.append(Cue(cur[0].start, cur[-1].end, ' '.join(x.text for x in cur), cur))
        return cues
    cues = []
    for s in segs:
        words = [word(w) for w in s.get('words', []) if 'start' in w and 'end' in w]
        cues.append(Cue(float(s['start']), float(s['end']), str(s.get('text', '')).strip(), [w for w in words if w.text]))
    return cues


def load(path):
    """Captions from .srt, .vtt or .json."""
    p = path.lower()
    if p.endswith('.srt'):
        return load_srt(path)
    if p.endswith('.vtt'):
        return load_vtt(path)
    if p.endswith('.json'):
        return load_json(path)
    raise ValueError('captions must be .srt, .vtt or .json')


def from_text(text, t0=0.0, wps=2.6, max_chars=42, gap=0.25):
    """Timed cues from a script with no audio: about wps words per second, cues of up to max_chars."""
    cues, t = [], t0
    for sentence in re.split(r'(?<=[.!?؟])\s+', text.strip()):
        words = sentence.split()
        line = []
        for w in words + [None]:
            if w is not None and len(' '.join(line + [w])) <= max_chars:
                line.append(w)
                continue
            if line:
                ws = []
                for x in line:
                    d = max(0.18, (0.25 + 0.045 * len(x)) * 2.6 / wps)
                    ws.append(Word(t, t + d, x))
                    t += d
                cues.append(Cue(ws[0].start, ws[-1].end, ' '.join(line), ws))
            line = [w] if w is not None else []
        t += gap
    return cues


def words_of(cue):
    """Word timings for a cue; spread by word length when the file had none."""
    if cue.words:
        return cue.words
    ws = cue.text.split()
    total = sum(len(w) + 1 for w in ws) or 1
    out, t = [], cue.start
    for w in ws:
        d = (cue.end - cue.start) * (len(w) + 1) / total
        out.append(Word(t, t + d, w))
        t += d
    return out


def chunk(cues, max_words=3, max_chars=18):
    """Re-split cues into short bursts of a few words (social-style captions)."""
    out = []
    for cue in cues:
        cur = []
        for w in words_of(cue):
            if cur and (len(cur) >= max_words or len(' '.join(x.text for x in cur + [w])) > max_chars):
                out.append(Cue(cur[0].start, cur[-1].end, ' '.join(x.text for x in cur), cur))
                cur = []
            cur.append(w)
        if cur:
            out.append(Cue(cur[0].start, cur[-1].end, ' '.join(x.text for x in cur), cur))
    for a, b in zip(out, out[1:]):   # hold each chunk until the next one starts (no flicker)
        if 0 < b.start - a.end < 0.6:
            a.end = b.start
    return out


def to_srt(cues, path):
    with open(path, 'w', encoding='utf-8') as fh:
        for i, c in enumerate(cues, 1):
            fh.write(f'{i}\n{_fmt_ts(c.start)} --> {_fmt_ts(c.end)}\n{c.text}\n\n')
    return path


def to_vtt(cues, path):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('WEBVTT\n\n')
        for c in cues:
            fh.write(f"{_fmt_ts(c.start, '.')} --> {_fmt_ts(c.end, '.')}\n{c.text}\n\n")
    return path


def active(cues, t):
    """The cue on screen at time t, or None."""
    for c in cues:
        if c.start <= t < c.end:
            return c
    return None


def _measure(word, f, font, size, rtl):
    return mv.shaped(word, font, size)[1] if rtl else mv.width(word, f)


def _draw_word(c, word, x, base, f, font, size, col, a, rtl, outline=None, ow=0.0):
    if rtl:   # outlines need glyph paths, so RTL captions rely on the box or shadow background instead
        mv.text_shaped(c, word, x, base, font, size, col, a, 'left')
    else:
        if outline and ow:
            mv.text(c, word, x, base, f, anchor='baseline', p=mv.paint(outline, a, stroke=ow))
        mv.text(c, word, x, base, f, col, a, 'left', 'baseline')


def draw(c, cues, t, box, style='karaoke', font='Inter', size=54, col='#FFFFFF', hi='#FACC15', bg='box',
         wght=750, align='center', max_lines=2, rtl=False, upper=False, leading=1.25, bg_col='#000000', bg_a=0.55):
    """Draw the caption active at t inside box (x0, y0, x1, y1); lines sit on the box's bottom edge.
    style: 'plain' | 'karaoke' (spoken words turn `hi`) | 'box' (a pill behind the current word) |
           'pop' (words pop on as spoken) | 'word' (one big word at a time).
    bg: 'box' (translucent panel), 'outline' (stroked letters), 'shadow' or 'none'.
    rtl=True for Arabic-script or Hebrew captions (font must support the script)."""
    cue = active(cues, t)
    if cue is None:
        return
    x0, y0, x1, y1 = box
    words = words_of(cue)
    if style == 'word':
        cur = [w for w in words if w.start <= t] or words[:1]
        w = cur[-1]
        txt = w.text.upper() if upper else w.text
        big = size * 1.6
        f = mv.font(font, big, wght=wght)
        p = mv.out_back(mv.seg(t, w.start, w.start + 0.18))
        cx = (x0 + x1) / 2
        ww = _measure(txt, f, font, big, rtl)
        with mv.Layer(c, 1.0, scale=0.6 + 0.4 * p, pivot=(cx, y1 - big * 0.35)):
            if bg == 'box':
                mv.rrect(c, cx - ww / 2 - big * 0.3, y1 - big * 1.1, cx + ww / 2 + big * 0.3, y1 + big * 0.15, big * 0.2, mv.paint(bg_col, bg_a))
            _draw_word(c, txt, cx - ww / 2, y1 - big * 0.2, f, font, big, hi if hi else col, 1.0, rtl,
                       '#000000' if bg == 'outline' else None, big * 0.14)
        return
    f = mv.font(font, size, wght=wght)
    items = [(w, (w.text.upper() if upper else w.text)) for w in words]
    space = _measure(' ', f, font, size, rtl) or size * 0.28
    widths = [_measure(s, f, font, size, rtl) for _, s in items]
    lines, cur, cw = [], [], 0.0
    for (w, s), wd in zip(items, widths):
        need = wd if not cur else cw + space + wd
        if cur and need > (x1 - x0):
            lines.append(cur); cur, cw = [], 0.0
            need = wd
        cur.append((w, s, wd)); cw = need
    if cur:
        lines.append(cur)
    lines = lines[-max_lines:] if style == 'pop' else lines[:max_lines]
    lh = size * leading
    ch = mv.cap_height(f)
    n = len(lines)
    for li, line in enumerate(lines):
        lw = sum(wd for _, _, wd in line) + space * (len(line) - 1)
        base = y1 - (n - 1 - li) * lh
        if align == 'center':
            lx = (x0 + x1) / 2 - lw / 2
        elif (align == 'right') != rtl:
            lx = x1 - lw
        else:
            lx = x0
        if bg == 'box' and style != 'pop':
            mv.rrect(c, lx - size * 0.35, base - ch - size * 0.32, lx + lw + size * 0.35, base + size * 0.3, size * 0.22,
                     mv.paint(bg_col, bg_a))
        order = list(reversed(line)) if rtl else line
        x = lx
        for w, s, wd in order:
            spoken = t >= w.start
            current = w.start <= t < w.end
            a = 1.0
            wc = col
            if style == 'karaoke':
                wc = hi if spoken else col
                a = 1.0 if spoken else 0.85
            elif style == 'box':
                if current or (spoken and w is line[-1][0] and t < cue.end):
                    k = mv.out_cubic(mv.seg(t, w.start, w.start + 0.12))
                    mv.rrect(c, x - size * 0.16, base - ch - size * 0.2, x + wd + size * 0.16, base + size * 0.22,
                             size * 0.18, mv.paint(hi, k))
                    wc = '#111111' if sum(mv.rgb(hi)) > 380 else '#FFFFFF'
            elif style == 'pop':
                if not spoken:
                    x += wd + space
                    continue
                k = mv.out_back(mv.seg(t, w.start, w.start + 0.16))
                if bg == 'box':
                    mv.rrect(c, x - size * 0.2, base - ch - size * 0.3, x + wd + size * 0.2, base + size * 0.28, size * 0.2,
                             mv.paint(bg_col, bg_a * mv.clamp(k)))
                with mv.Layer(c, mv.clamp(k * 2), scale=max(0.01, k), pivot=(x + wd / 2, base - ch / 2)):
                    _draw_word(c, s, x, base, f, font, size, col, 1.0, rtl, '#000000' if bg == 'outline' else None, size * 0.14)
                x += wd + space
                continue
            if bg == 'shadow':
                _draw_word(c, s, x + size * 0.04, base + size * 0.05, f, font, size, '#000000', 0.55, rtl)
            _draw_word(c, s, x, base, f, font, size, wc, a, rtl, '#000000' if bg == 'outline' else None, size * 0.14)
            x += wd + space
