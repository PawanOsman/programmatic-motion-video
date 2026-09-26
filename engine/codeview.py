"""codeview.py: code on screen: a syntax-highlighted editor that types, scrolls, highlights and
shows diffs, and a terminal that runs commands.

    codeview.editor(c, rect, CODE, th, lang='python', t=t, t0=1.0, cps=35, title='app.py',
                    highlight=[4], marks={6: 'add', 7: 'del'})
    codeview.terminal(c, rect, th, [dict(cmd='pip install mvkit', at=0.5),
                                    dict(spin='Installing', at=1.4, until=3.0, done='Installed 12 packages'),
                                    dict(ok='Ready', at=3.2)], t)

Highlighting uses Pygments when installed (every language it knows); otherwise a built-in lexer
covers Python, JavaScript/TypeScript, JSON, Bash, CSS, HTML and SQL.
"""
import functools
import re

try:
    from . import icons, mv
except ImportError:
    import icons
    import mv

KEYWORDS = {
    'python': 'False None True and as assert async await break class continue def del elif else except finally for from '
              'global if import in is lambda nonlocal not or pass raise return try while with yield match case self',
    'js': 'const let var function return if else for while do switch case break continue new class extends import from '
          'export default async await try catch finally throw typeof instanceof in of this super null undefined true '
          'false yield interface type enum implements public private protected readonly as',
    'bash': 'if then else elif fi for in do done while case esac function return export local echo cd sudo',
    'sql': 'select from where and or not insert into values update set delete create table join left right inner on '
           'group by order limit as distinct having null is in',
    'css': '', 'json': 'true false null', 'html': '',
}
ALIAS = {'ts': 'js', 'typescript': 'js', 'javascript': 'js', 'jsx': 'js', 'tsx': 'js', 'sh': 'bash', 'shell': 'bash',
         'zsh': 'bash', 'py': 'python'}
_TOKEN = re.compile(r'(?P<comment>#[^\n]*|//[^\n]*|/\*.*?\*/|<!--.*?-->|--[^\n]*)'
                    r'|(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)'
                    r'|(?P<number>\b\d[\d_]*(?:\.\d+)?(?:e[-+]?\d+)?\b|#[0-9a-fA-F]{3,8}\b)'
                    r'|(?P<ident>[A-Za-z_$@][\w$-]*)'
                    r'|(?P<space>\s+)'
                    r'|(?P<punct>.)', re.S)


def _builtin_tokens(code, lang):
    lang = ALIAS.get(lang, lang)
    kws = set(KEYWORDS.get(lang, KEYWORDS['js']).split())
    out = []
    toks = list(_TOKEN.finditer(code))
    for i, m in enumerate(toks):
        kind, text = m.lastgroup, m.group()
        if kind == 'comment' and lang in ('js', 'json', 'css') and text.startswith('#'):
            kind = 'number' if re.fullmatch(r'#[0-9a-fA-F]{3,8}', text) else 'plain'
        if kind == 'comment' and lang not in ('sql',) and text.startswith('--'):
            kind = 'punct'
        if kind == 'comment' and lang in ('python', 'bash') and text.startswith('//'):
            kind = 'punct'
        if kind == 'ident':
            nxt = next((t.group() for t in toks[i + 1:i + 3] if t.lastgroup != 'space'), '')
            if text.lower() in kws if lang == 'sql' else text in kws:
                kind = 'keyword'
            elif nxt == '(':
                kind = 'function'
            elif text[:1].isupper():
                kind = 'type'
            elif text.startswith('@'):
                kind = 'builtin'
            else:
                kind = 'plain'
        elif kind == 'space':
            kind = 'plain'
        out.append((text, kind))
    return out


def _pygments_tokens(code, lang):
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Token
    lexer = get_lexer_by_name(lang, stripnl=False, ensurenl=False)
    out = []
    for ttype, text in lexer.get_tokens(code):
        if ttype in Token.Comment:
            role = 'comment'
        elif ttype in Token.Literal.String:
            role = 'string'
        elif ttype in Token.Literal.Number:
            role = 'number'
        elif ttype in Token.Keyword:
            role = 'keyword'
        elif ttype in Token.Name.Function or ttype in Token.Name.Decorator:
            role = 'function'
        elif ttype in Token.Name.Class or ttype in Token.Name.Namespace:
            role = 'type'
        elif ttype in Token.Name.Builtin or ttype in Token.Name.Tag or ttype in Token.Name.Attribute:
            role = 'builtin'
        elif ttype in Token.Operator or ttype in Token.Punctuation:
            role = 'punct'
        else:
            role = 'plain'
        out.append((text, role))
    return out


@functools.lru_cache(maxsize=64)
def tokens(code, lang='python'):
    """[(text, role)] covering the code exactly; roles match ui.Theme.syntax."""
    try:
        return tuple(_pygments_tokens(code, lang))
    except Exception:
        return tuple(_builtin_tokens(code, lang))


@functools.lru_cache(maxsize=64)
def _lines(code, lang):
    """Per line: [(text, role)] and the char offset where the line starts."""
    lines, cur, starts, pos = [], [], [0], 0
    for text, role in tokens(code, lang):
        parts = text.split('\n')
        for k, part in enumerate(parts):
            if k:
                lines.append(cur); cur = []
                starts.append(pos)
            if part:
                cur.append((part.replace('\t', '    '), role))
            pos += len(part) + (1 if k < len(parts) - 1 else 0)
    lines.append(cur)
    return lines, starts[:len(lines)]


def editor(c, rect, code, th, lang='python', t=None, t0=0.0, cps=30.0, typed_from=None, title='main.py',
           line_numbers=True, highlight=(), marks=None, size=None, a=1.0, scroll=None, header=True, caret=True,
           insert=None):
    """A code editor card. With t, the code after char index typed_from (default 0) types in at cps
    from t0 and the view scrolls to follow. insert=(char_index, text, t_start, cps) instead types new
    text into the middle of existing code (an edit), pushing the lines below it down.
    highlight: line indices (0-based) to spotlight; marks: {line: 'add' | 'del'} for a diff.
    Returns the caret position (x, y) on screen."""
    x0, y0, x1, y1 = rect
    fs = size or th.s(24)
    f = mv.font(th.mono, fs, wght=450)
    cw = mv.width('M', f)
    lh = fs * 1.6
    bar = th.s(52) if header else 0.0
    code = code.expandtabs(4)
    typing = False
    if insert is not None and t is not None:
        idx, new, it0, icps = insert
        part = mv.typed(new.expandtabs(4), t, it0, icps)
        code = code[:idx] + part + code[idx:]
        shown = len(code)
        caret_at = idx + len(part)
        typing = mv.typing(new, t, it0, icps)
    else:
        shown = len(code)
        if t is not None:
            base = typed_from if typed_from is not None else 0
            shown = min(len(code), base + max(0, int((t - t0) * cps)))
            typing = shown < len(code) and t >= t0
        caret_at = shown
    lines, starts = _lines(code, lang)
    cl = max(0, next((i for i in range(len(starts) - 1, -1, -1) if starts[i] <= caret_at), 0))
    col = caret_at - starts[cl]
    gut = (len(str(len(lines))) + 2.2) * cw if line_numbers else fs * 0.8
    top = y0 + bar + fs * 0.7
    vis = max(1, int((y1 - top - fs * 0.4) / lh))
    if scroll is None:
        line_len = max(1, sum(len(s) for s, _ in lines[cl]) if cl < len(lines) else 1)
        prog = cl + min(1.0, col / line_len)
        scroll = max(0.0, min(len(lines) - vis, prog - (vis - 3)))
    with mv.Layer(c, a, bounds=(x0 - 100, y0 - 100, x1 + 100, y1 + 140)) if a < 0.999 else mv.Layer(c):
        mv.blur_shadow(c, x0, y0, x1, y1, th.s(14), th.shadow, th.s(60), th.s(26))
        mv.rrect(c, x0, y0, x1, y1, th.s(14), mv.paint(th.surface))
        if header:
            mv.rrect(c, x0, y0, x1, y0 + bar, (th.s(14), th.s(14), 0, 0), mv.paint(th.surface2))
            for i, cc in enumerate(('#FF5F57', '#FEBC2E', '#28C840')):
                c.drawCircle(x0 + th.s(26) + i * th.s(22), y0 + bar / 2, th.s(6.5), mv.paint(cc))
            tx = x0 + th.s(100)
            tw = mv.width(title, mv.font(th.font, th.s(19), wght=550)) + th.s(64)
            mv.rrect(c, tx, y0 + th.s(8), tx + tw, y0 + bar, (th.s(8), th.s(8), 0, 0), mv.paint(th.surface))
            icons.draw(c, 'file-code', tx + th.s(22), y0 + bar / 2 + th.s(4), th.s(18), th.accent2)
            mv.text(c, title, tx + th.s(40), y0 + bar / 2 + th.s(4), mv.font(th.font, th.s(19), wght=550), th.text)
        with mv.Clip(c, (x0, y0 + bar, x1, y1 - th.s(6))):
            first = int(scroll)
            for i in range(first, min(len(lines), first + vis + 2)):
                y = top + (i - scroll) * lh
                base = y + lh * 0.5 + mv.cap_height(f) / 2
                kind = (marks or {}).get(i)
                if i in highlight or kind:
                    colr = th.syn('added') if kind == 'add' else th.syn('removed') if kind == 'del' else th.accent
                    c.drawRect(mv.rect(x0, y, x1, y + lh), mv.paint(colr, 0.14))
                    c.drawRect(mv.rect(x0, y, x0 + th.s(4), y + lh), mv.paint(colr, 0.9))
                if line_numbers:
                    num = '+' if kind == 'add' else '-' if kind == 'del' else str(i + 1)
                    ncol = th.text if (i == cl and typing) else th.muted
                    mv.text(c, num, x0 + gut - cw * 1.2, base, f, ncol, 0.8 if num.isdigit() else 1.0, 'right', 'baseline')
                x = x0 + gut
                pos = starts[i]
                for text, role in lines[i]:
                    if pos >= shown:
                        break
                    part = text[:max(0, shown - pos)]
                    mv.text(c, part, x, base, f, th.syn(role), 1.0, 'left', 'baseline')
                    x += len(part) * cw
                    pos += len(text)
            cx = x0 + gut + col * cw
            cy = top + (cl - scroll) * lh
            if caret and t is not None:
                mv.caret(c, cx, cy + lh * 0.5 + mv.cap_height(f) / 2, mv.cap_height(f) * 1.2, th.accent2, t, typing, max(2, fs * 0.1))
        mv.rrect(c, x0 + 0.75, y0 + 0.75, x1 - 0.75, y1 - 0.75, th.s(14), mv.paint(th.border, 1, stroke=th.s(1.5)))
    return x0 + gut + col * cw, top + (cl - scroll) * lh + lh / 2


def terminal(c, rect, th, lines, t, prompt='$', title='Terminal', size=None, cps=26.0, a=1.0, bg=None):
    """A terminal that plays a session. Each line is a dict with 'at' (seconds) and one of:
      cmd  a command typed after the prompt at cps
      out  output text (may contain newlines)
      ok / err  a result line with a green check / red cross
      spin with 'until' (and optional 'done' text): a spinner that turns into a check
    The view scrolls to keep the newest line in sight."""
    x0, y0, x1, y1 = rect
    fs = size or th.s(24)
    f = mv.font(th.mono, fs, wght=450)
    cw = mv.width('M', f)
    lh = fs * 1.55
    bar = th.s(48)
    rows = []
    for ln in lines:
        at = ln.get('at', 0.0)
        if t < at:
            continue
        if 'cmd' in ln:
            txt = mv.typed(ln['cmd'], t, at, ln.get('cps', cps))
            rows.append(('cmd', txt, mv.typing(ln['cmd'], t, at, ln.get('cps', cps))))
        elif 'out' in ln:
            for part in ln['out'].split('\n'):
                rows.append(('out', part, False))
        elif 'ok' in ln:
            rows.append(('ok', ln['ok'], False))
        elif 'err' in ln:
            rows.append(('err', ln['err'], False))
        elif 'spin' in ln:
            done = t >= ln.get('until', 1e9)
            rows.append(('ok' if done else 'spin', ln.get('done', ln['spin']) if done else ln['spin'], False))
    back = bg or ('#0A0A0F' if th.name == 'dark' else '#1B1B22')
    ink = '#E6E6EA'
    with mv.Layer(c, a, bounds=(x0 - 100, y0 - 100, x1 + 100, y1 + 140)) if a < 0.999 else mv.Layer(c):
        mv.blur_shadow(c, x0, y0, x1, y1, th.s(14), th.shadow, th.s(60), th.s(26))
        mv.rrect(c, x0, y0, x1, y1, th.s(14), mv.paint(back))
        mv.rrect(c, x0, y0, x1, y0 + bar, (th.s(14), th.s(14), 0, 0), mv.paint('#15151C'))
        for i, cc in enumerate(('#FF5F57', '#FEBC2E', '#28C840')):
            c.drawCircle(x0 + th.s(26) + i * th.s(22), y0 + bar / 2, th.s(6.5), mv.paint(cc))
        mv.text(c, title, (x0 + x1) / 2, y0 + bar / 2, mv.font(th.font, th.s(18), wght=550), '#9B9BAD', align='center')
        top = y0 + bar + fs * 0.6
        vis = int((y1 - top - fs * 0.4) / lh)
        start = max(0, len(rows) - vis)
        with mv.Clip(c, (x0, y0 + bar, x1, y1)):
            for k, (kind, txt, active) in enumerate(rows[start:]):
                base = top + k * lh + lh * 0.5 + mv.cap_height(f) / 2
                x = x0 + fs * 0.9
                if kind == 'cmd':
                    x += mv.text(c, prompt + ' ', x, base, f, th.accent2, 1, 'left', 'baseline')
                    w = mv.text(c, txt, x, base, f, ink, 1, 'left', 'baseline')
                    if k + start == len(rows) - 1:
                        mv.caret(c, x + w + 2, base, mv.cap_height(f) * 1.2, ink, t, active, max(2, fs * 0.1))
                elif kind == 'out':
                    mv.text(c, txt, x, base, f, '#A9A9B8', 1, 'left', 'baseline')
                elif kind in ('ok', 'err'):
                    icons.draw(c, 'check' if kind == 'ok' else 'x', x + fs * 0.4, base - mv.cap_height(f) / 2, fs * 0.9,
                               '#22C55E' if kind == 'ok' else '#EF4444', stroke=2.6)
                    mv.text(c, txt, x + fs * 1.3, base, f, '#22C55E' if kind == 'ok' else '#EF4444', 1, 'left', 'baseline')
                elif kind == 'spin':
                    r = fs * 0.36
                    cy = base - mv.cap_height(f) / 2
                    c.drawCircle(x + fs * 0.4, cy, r, mv.paint(th.accent2, 0.25, stroke=fs * 0.1))
                    arc = mv.skia.Path()
                    arc.addArc(mv.rect(x + fs * 0.4 - r, cy - r, x + fs * 0.4 + r, cy + r), (t * 420) % 360, 100)
                    c.drawPath(arc, mv.paint(th.accent2, 1, stroke=fs * 0.1))
                    mv.text(c, txt, x + fs * 1.3, base, f, ink, 1, 'left', 'baseline')
            if not rows or rows[-1][0] in ('ok', 'err'):
                base = top + (len(rows) - start) * lh + lh * 0.5 + mv.cap_height(f) / 2
                if len(rows) - start < vis:
                    px = x0 + fs * 0.9 + mv.text(c, prompt + ' ', x0 + fs * 0.9, base, f, th.accent2, 1, 'left', 'baseline')
                    mv.caret(c, px, base, mv.cap_height(f) * 1.2, ink, t, False, max(2, fs * 0.1))
