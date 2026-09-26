#!/usr/bin/env python3
"""Start a new video project from a template, with the engine and assets copied in.

    python tools/new_project.py my-video --template promo
    python tools/new_project.py my-video --template minimal     # blank start (examples/ count too)
    python tools/new_project.py --list

The project is self-contained: main.py (the template), the engine modules next to it, and
assets/ (fonts, icons, samples). Later changes to the skill do not change existing projects.
"""
import argparse
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES = os.path.join(ROOT, 'templates')
EXAMPLES = os.path.join(ROOT, 'examples')
ENGINE = os.path.join(ROOT, 'engine')
ASSETS = os.path.join(ROOT, 'assets')


def templates():
    """name -> (path, first docstring line) for templates/*.py, then examples/*.py."""
    out = {}
    for folder in (TEMPLATES, EXAMPLES):
        for fn in sorted(os.listdir(folder)):
            if fn.endswith('.py') and not fn.startswith('_') and fn[:-3] not in out:
                path = os.path.join(folder, fn)
                with open(path, encoding='utf-8') as fh:
                    doc = re.search(r'"""(.*?)"""', fh.read(), re.S)
                note = ' '.join(doc.group(1).split()) if doc else ''
                note = re.split(r'(?<=[.])\s', note)[0]              # first sentence
                if len(note) > 100:
                    note = note[:97].rsplit(' ', 1)[0] + '...'
                if folder == EXAMPLES:
                    note = '(example) ' + note
                out[fn[:-3]] = (path, note)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder', nargs='?', help='new project folder')
    ap.add_argument('--template', '-t', default='promo', help='template name (see --list)')
    ap.add_argument('--list', action='store_true', help='list the templates')
    ap.add_argument('--no-fonts', action='store_true', help='skip copying the bundled fonts')
    ap.add_argument('--force', action='store_true', help='write into an existing folder')
    a = ap.parse_args()
    tpls = templates()
    if a.list or not a.folder:
        width = max(len(k) for k in tpls)
        for k, (_, note) in tpls.items():
            print(f'  {k:<{width}}  {note}')
        if not a.folder:
            print('\nusage: python tools/new_project.py FOLDER --template NAME')
        return
    if a.template not in tpls:
        sys.exit(f'unknown template {a.template!r}; choose from: {", ".join(tpls)}')
    dst = os.path.abspath(a.folder)
    if os.path.exists(dst) and os.listdir(dst) and not a.force:
        sys.exit(f'{dst} exists and is not empty (use --force to write into it)')
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(ENGINE):
        if fn.endswith('.py'):
            shutil.copy2(os.path.join(ENGINE, fn), os.path.join(dst, fn))
    for sub in ('icons', 'sample') + (() if a.no_fonts else ('fonts',)):
        src = os.path.join(ASSETS, sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, 'assets', sub), dirs_exist_ok=True)
    src_path = tpls[a.template][0]
    with open(src_path, encoding='utf-8') as fh:
        code = fh.read()
    code = '\n'.join(l for l in code.split('\n') if '# repo layout' not in l)   # the engine sits next to main.py now
    with open(os.path.join(dst, 'main.py'), 'w', encoding='utf-8') as fh:
        fh.write(code)
    with open(os.path.join(dst, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write(f"""# {os.path.basename(dst)}

Made from the `{a.template}` template of programmatic-motion-video.

```bash
python main.py info                     # duration, size and scene start times
python main.py sheet                    # contact sheet: sheet.png
python main.py still 2.5 frame.png      # one frame
python main.py render out.mp4           # full render in parallel, with sound
MV_SIZE=1080x1920 python main.py render vertical.mp4
```

Edit CONFIG at the top of main.py first. The engine modules (mv.py, sfx.py, ui.py, ...) are copies;
update them by copying newer ones from the skill.
""")
    print(f'created {dst}\n  main.py from {os.path.relpath(src_path, ROOT)}\n  engine: {", ".join(sorted(f for f in os.listdir(ENGINE) if f.endswith(".py")))}')
    print(f'next:\n  cd {a.folder}\n  python main.py sheet\n  python main.py render out.mp4')


if __name__ == '__main__':
    main()
