#!/usr/bin/env python3
"""Validate the skill and build the zip.

    python tools/package_skill.py              validate, then write dist/programmatic-motion-video.zip
    python tools/package_skill.py --check      only validate (exit code 1 on problems)
    python tools/package_skill.py --out x.zip  choose where the zip goes

The zip holds the skill folder at its root (programmatic-motion-video/SKILL.md, not SKILL.md at
the top), which is what Claude's skill upload expects and what unzips into a skills directory.
Caches, renders, contact sheets and dist/ are left out.

Checks follow the Agent Skills format: allowed frontmatter keys, name rules and folder match,
description length (1024; Claude apps show 200) without angle brackets, compatibility length,
exactly one SKILL.md, every file SKILL.md mentions exists, and the repo files the README promises.
"""
import os
import re
import stat
import sys
import time
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NAME = os.path.basename(ROOT)
ALLOWED = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}
REPO_FILES = ['SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md',
              'requirements.txt', 'install.sh', 'install.ps1']
SKIP_DIRS = {'__pycache__', '.git', 'dist', '.pytest_cache', 'out', 'renders', '.venv', 'venv',
             'node_modules', '.idea', '.vscode', '.mypy_cache', '.ruff_cache'}
SKIP_EXT = ('.pyc', '.pyo', '.mp4', '.mov', '.webm', '.mkv', '.wav', '.mp3', '.m4a', '.gif', '.npz', '.log', '.zip')
IMAGE_DIRS = ('assets', 'docs')           # images elsewhere are stray sheets and stills
EXECUTABLE = ('install.sh',)


def frontmatter():
    text = open(os.path.join(ROOT, 'SKILL.md'), encoding='utf-8').read()
    m = re.match(r'---\r?\n(.*?)\r?\n---\r?\n', text, re.S)
    if not m:
        raise SystemExit('SKILL.md must start with YAML frontmatter between --- lines')
    try:
        import yaml
        fields = yaml.safe_load(m.group(1))
        if not isinstance(fields, dict):
            raise SystemExit('the frontmatter must be a YAML mapping')
    except ImportError:                     # a small fallback parser for flat keys
        fields = {}
        for line in m.group(1).split('\n'):
            if ':' in line and not line.startswith((' ', '\t')):
                k, v = line.split(':', 1)
                fields[k.strip()] = v.strip().strip('"\'') or {}
    return fields, text, text[m.end():]


def files():
    """Every file that goes into the zip, as paths relative to ROOT."""
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.endswith('.parts')
                         and (not d.startswith('.') or d == '.github'))
        rel_base = os.path.relpath(base, ROOT)
        top = rel_base.split(os.sep)[0]
        for fn in sorted(names):
            if fn.endswith(SKIP_EXT) or fn in ('.DS_Store', 'Thumbs.db'):
                continue
            if fn.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and top not in IMAGE_DIRS:
                continue
            if fn.startswith('.') and fn not in ('.gitignore', '.gitattributes'):
                continue
            out.append(os.path.normpath(os.path.join(rel_base, fn)))
    return out


def check():
    f, text, body = frontmatter()
    problems, notes = [], []
    extra = set(f) - ALLOWED
    if extra:
        problems.append(f'frontmatter keys not allowed: {", ".join(sorted(extra))} (allowed: {", ".join(sorted(ALLOWED))})')
    name = str(f.get('name', '')).strip()
    desc = str(f.get('description', '')).strip()
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', name) or len(name) > 64:
        problems.append(f'name {name!r}: lowercase letters, digits and single hyphens, at most 64 characters')
    if any(w in name for w in ('claude', 'anthropic')):
        problems.append('name must not contain "claude" or "anthropic"')
    if name != NAME:
        problems.append(f'name {name!r} must match the folder name {NAME!r}')
    if not desc:
        problems.append('description is empty')
    if '<' in desc or '>' in desc:
        problems.append('description must not contain angle brackets')
    if len(desc) > 1024:
        problems.append(f'description is {len(desc)} characters; the limit is 1024')
    elif len(desc) > 200:
        notes.append(f'description is {len(desc)} characters; Claude apps accept at most 200')
    comp = f.get('compatibility')
    if comp is not None and len(str(comp)) > 500:
        problems.append('compatibility is longer than 500 characters')
    if 'metadata' in f and not isinstance(f['metadata'], dict):
        problems.append('metadata must be a mapping')
    body_lines = body.count('\n')
    if body_lines > 500:
        notes.append(f'SKILL.md body is {body_lines} lines; under 500 is recommended')

    listed = files()
    skill_mds = [p for p in listed if os.path.basename(p) == 'SKILL.md']
    if skill_mds != ['SKILL.md']:
        problems.append(f'exactly one SKILL.md is allowed, at the root; found: {", ".join(skill_mds)}')
    for req in REPO_FILES:
        if not os.path.exists(os.path.join(ROOT, req)):
            problems.append(f'missing repo file: {req}')

    # every path SKILL.md mentions, in links or code spans, must exist
    mentioned = set()
    for m in re.finditer(r'(?<![\w/.-])(?:SKILL_DIR/)?((?:references|engine|templates|tools|assets|examples|tests|docs)/[\w./-]*)', text):
        mentioned.add(m.group(1).rstrip('.'))
    for ref in sorted(mentioned):
        if not os.path.exists(os.path.join(ROOT, ref)):
            problems.append(f'SKILL.md mentions a missing path: {ref}')
    for fn in sorted(os.listdir(os.path.join(ROOT, 'references'))):
        if fn.endswith('.md') and f'references/{fn}' not in text:
            notes.append(f'references/{fn} is not mentioned in SKILL.md, so agents may never read it')
    for tpl in sorted(os.listdir(os.path.join(ROOT, 'templates'))):
        if tpl.endswith('.py') and f'`{tpl[:-3]}`' not in text:
            notes.append(f'templates/{tpl} is not listed in SKILL.md')

    for n in notes:
        print('note:', n)
    for p in problems:
        print('problem:', p)
    if not problems:
        print(f'SKILL.md ok: name={name}, description {len(desc)} chars, body {body_lines} lines, '
              f'{len(listed)} files')
    return not problems


def build(out=None):
    out = out or os.path.join(ROOT, 'dist', f'{NAME}.zip')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    total = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        folders = {''}
        for p in files():                                                 # every folder and its parents
            d = os.path.dirname(p)
            while d:
                folders.add(d)
                d = os.path.dirname(d)
        for d in sorted(folders):                                         # folder entries first
            info = zipfile.ZipInfo(f'{NAME}/{d}/'.replace('//', '/').replace(os.sep, '/'),
                                   date_time=time.localtime(os.path.getmtime(os.path.join(ROOT, d)))[:6])
            info.external_attr = (0o40755 << 16) | 0x10
            z.writestr(info, b'')
        for rel in files():
            path = os.path.join(ROOT, rel)
            info = zipfile.ZipInfo.from_file(path, f'{NAME}/{rel}'.replace(os.sep, '/'))
            mode = 0o755 if (rel in EXECUTABLE or rel.replace(os.sep, '/').startswith('tools/')
                             or rel.replace(os.sep, '/') == 'tests/run_tests.py') else 0o644
            info.external_attr = ((stat.S_IFREG | mode) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, 'rb') as fh:
                data = fh.read()
            z.writestr(info, data, compresslevel=9)
            total += 1
    print(f'wrote {out}: {total} files, {os.path.getsize(out) / 1e6:.1f} MB')
    return out


if __name__ == '__main__':
    good = check()
    if '--check' in sys.argv:
        sys.exit(0 if good else 1)
    if not good:
        sys.exit('fix the problems above first')
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    build(out)
