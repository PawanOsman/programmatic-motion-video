#!/usr/bin/env python3
"""Generate references/api.md from the engine's signatures and docstrings, so the reference never
drifts from the code. Run it after changing the engine:

    python tools/gen_api.py
"""
import ast
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(ROOT, 'engine')
ORDER = ['mv', 'sfx', 'ui', 'fx', 'kinetic', 'charts', 'captions', 'codeview', 'icons', 'brand', 'layout', 'media']


def sig(fn, drop_self=False):
    a = fn.args
    parts = []
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    for arg, d in zip(pos, defaults):
        if drop_self and arg.arg in ('self', 'cls') and not parts:
            continue
        parts.append(arg.arg + ('=' + ast.unparse(d) if d is not None else ''))
    if a.vararg:
        parts.append('*' + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append('*')
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg + ('=' + ast.unparse(d) if d is not None else ''))
    if a.kwarg:
        parts.append('**' + a.kwarg.arg)
    return '(' + ', '.join(parts) + ')'


def doc(node, full=False):
    d = ast.get_docstring(node) or ''
    if not full:
        d = d.split('\n\n')[0]
    return ' '.join(line.strip() for line in d.split('\n')).strip()


def module_md(name):
    path = os.path.join(ENGINE, name + '.py')
    tree = ast.parse(open(path, encoding='utf-8').read())
    out = [f'## {name}.py', '', doc(tree), '']
    consts = []
    curves = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not doc(n)
              and (n.name in ('smoothstep', 'linear_ease') or n.name.startswith(('in_', 'out_', 'inout_')))]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in curves:
            if node.name == curves[0]:
                out.append('- **Easing curves** `f(x)`, x in 0..1: ' + ', '.join(f'`{c}`' for c in curves))
            continue
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            out.append(f'- **`{node.name}{sig(node)}`**' + (f': {doc(node)}' if doc(node) else ''))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'), None)
            s = sig(init, True) if init else ''
            out.append(f'- **class `{node.name}{s}`**' + (f': {doc(node)}' if doc(node) else ''))
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and not m.name.startswith('_'):
                    out.append(f'  - `.{m.name}{sig(m, True)}`' + (f': {doc(m)}' if doc(m) else ''))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n.isupper() and not n.startswith('_'):
                consts.append(n)
    if consts:
        out.append('')
        out.append('Constants: ' + ', '.join(f'`{c}`' for c in consts))
    out.append('')
    return '\n'.join(out)


def main():
    names = [n for n in ORDER if os.path.exists(os.path.join(ENGINE, n + '.py'))]
    names += sorted(f[:-3] for f in os.listdir(ENGINE) if f.endswith('.py') and f[:-3] not in names)
    head = ['# Engine API reference', '',
            'Generated from the code by `python tools/gen_api.py`; every entry is the real signature.',
            'Import the modules you need (`import mv, ui, fx`) after copying `engine/` next to your script,',
            'or run templates from the repository, which put `engine/` on the path.', '',
            'Modules: ' + ', '.join(f'[{n}](#{n}py)' for n in names), '']
    body = [module_md(n) for n in names]
    dst = os.path.join(ROOT, 'references', 'api.md')
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(head + body))
    print(dst, sum(len(b.split('\n')) for b in body), 'lines')


if __name__ == '__main__':
    main()
