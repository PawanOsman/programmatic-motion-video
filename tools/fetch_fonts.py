#!/usr/bin/env python3
"""Download Google Fonts families by name into a fonts folder (OFL, Apache or UFL licensed).

    python tools/fetch_fonts.py "Space Mono" "Noto Sans Arabic" "Vazirmatn"
    python tools/fetch_fonts.py "Noto Sans JP" --dest assets/fonts

Tries the google/fonts repository first (its METADATA.pb via raw.githubusercontent.com, then the
GitHub API; variable fonts plus the licence file), then the Google Fonts CSS API (static weights). The engine finds fonts in ./fonts and assets/fonts by name:
mv.font('Space Mono', 48). Needs network access to github.com or fonts.googleapis.com.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 programmatic-motion-video font fetcher'}


def get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


RAW = 'https://raw.githubusercontent.com/google/fonts/main'


def _save(url, dest, name):
    name = re.sub(r'\[.*?\]', '-VF', name)   # 'Inter[opsz,wght].ttf' -> 'Inter-VF.ttf': shell-friendly, found by name
    path = os.path.join(dest, name)
    with open(path, 'wb') as fh:
        fh.write(get(url))
    return path


def from_metadata(family, dest):
    """Read the family's METADATA.pb from raw.githubusercontent.com (no API rate limit) and fetch its files."""
    key = re.sub(r'[^a-z0-9]', '', family.lower())
    for lic in ('ofl', 'apache', 'ufl'):
        try:
            meta = get(f'{RAW}/{lic}/{key}/METADATA.pb').decode('utf-8', 'replace')
        except Exception:
            continue
        names = sorted(set(re.findall(r'filename:\s*"([^"]+)"', meta)))
        saved = [_save(f'{RAW}/{lic}/{key}/{urllib.parse.quote(n)}', dest, n) for n in names]
        for lic_file in ('OFL.txt', 'LICENSE.txt', 'UFL.txt'):
            try:
                saved.append(_save(f'{RAW}/{lic}/{key}/{lic_file}', dest, f'{key}-{lic_file}'))
                break
            except Exception:
                continue
        if saved:
            return saved
    return []


def from_github(family, dest):
    key = re.sub(r'[^a-z0-9]', '', family.lower())
    for lic in ('ofl', 'apache', 'ufl'):
        try:
            listing = json.loads(get(f'https://api.github.com/repos/google/fonts/contents/{lic}/{key}'))
        except Exception:
            continue
        files = [f for f in listing if f['name'].lower().endswith(('.ttf', '.otf')) or f['name'] in ('OFL.txt', 'LICENSE.txt', 'UFL.txt')]
        if not files:
            continue
        saved = []
        for f in files:
            name = re.sub(r'\[.*?\]', '-VF', f['name'])   # 'Inter[opsz,wght].ttf' -> 'Inter-VF.ttf': shell-friendly, found by name
            if name.endswith('.txt'):
                name = f'{key}-{name}'
            path = os.path.join(dest, name)
            with open(path, 'wb') as fh:
                fh.write(get(f['download_url']))
            saved.append(path)
        return saved
    return []


def from_css_api(family, dest, weights=(300, 400, 500, 600, 700, 800)):
    q = urllib.parse.quote_plus(family)
    css = get(f'https://fonts.googleapis.com/css2?family={q}:wght@{";".join(map(str, weights))}',
              headers={'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0)'}).decode()   # old agents get TTF files
    saved = []
    for block in re.findall(r'@font-face\s*{(.*?)}', css, re.S):
        w = re.search(r'font-weight:\s*(\d+)', block)
        u = re.search(r'url\((https://[^)]+\.ttf)\)', block)
        if u:
            path = os.path.join(dest, f"{family.replace(' ', '')}-{w.group(1) if w else '400'}.ttf")
            if not os.path.exists(path):
                with open(path, 'wb') as fh:
                    fh.write(get(u.group(1)))
                saved.append(path)
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('families', nargs='+')
    ap.add_argument('--dest', default='fonts')
    a = ap.parse_args()
    os.makedirs(a.dest, exist_ok=True)
    failed = []
    for fam in a.families:
        try:
            saved = from_metadata(fam, a.dest) or from_github(fam, a.dest) or from_css_api(fam, a.dest)
        except Exception as e:
            saved = []
            print(f'{fam}: {e}')
        if saved:
            print(f'{fam}: ' + ', '.join(os.path.basename(p) for p in saved))
        else:
            failed.append(fam)
    if failed:
        sys.exit('not found or no network: ' + ', '.join(failed) +
                 '\nCheck the exact family name at fonts.google.com, or copy the font files into ./fonts yourself.')


if __name__ == '__main__':
    main()
