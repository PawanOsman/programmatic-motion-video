"""Template checks: every template runs, draws a contact sheet at each size it supports, and renders
(at quarter size, so the whole set takes a few minutes). QR codes decode; the signage loop closes.

    python tests/run_tests.py --templates
    python tests/run_tests.py --only-templates -k promo
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES = os.path.join(ROOT, 'templates')

# other sizes each template is designed for (its default size is always checked)
OTHER_SIZES = {
    'promo': ['1080x1920', '1080x1080', '3840x2160'],
    'mobile_app': ['1080x1920'],
    'signage_loop': ['2560x1440'],
    'explainer': ['1080x1920'],
    'slideshow': ['1080x1920'],
    'captioned_clip': ['1920x1080'],
    'audiogram': ['1080x1920'],
}
QR_AT = {'promo': -0.5, 'signage_loop': 4.0, 'slideshow': -0.5, 'batch_videos': -0.5}   # negative: from the end
LOOPS = {'signage_loop'}


def _run(args, cwd, env=None, timeout=1800):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([sys.executable] + args, cwd=cwd, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    assert r.returncode == 0, f'{" ".join(args)} failed:\n{r.stdout[-3000:]}\n{r.stderr[-4000:]}'
    return r.stdout


def _probe_frames(text):
    m = re.search(r'codec_type=video[^\n]*?nb_frames=(\d+)', text) or re.search(r'nb_frames=(\d+)', text)
    return int(m.group(1)) if m else None


def check(name, keep=None):
    script = os.path.join(TEMPLATES, name + '.py')
    d = keep or tempfile.mkdtemp(prefix=f'mvtpl-{name}-')
    os.makedirs(d, exist_ok=True)
    try:
        info = json.loads(_run([script, 'info'], d))
        assert info['duration'] > 0 and info['frames'] > 0, info
        dur, fps = info['duration'], info['fps']
        times = ','.join(f'{dur * k / 7:.2f}' for k in range(1, 7)) + f',{max(0.0, dur - 0.05):.2f}'
        _run([script, 'sheet', times, os.path.join(d, 'sheet.png')], d)
        assert os.path.getsize(os.path.join(d, 'sheet.png')) > 20000
        for size in OTHER_SIZES.get(name, []):
            _run([script, 'sheet', times, os.path.join(d, f'sheet_{size}.png')], d, env={'MV_SIZE': size})
        if name == 'batch_videos':
            out = _run([script, 'check'], d)
            assert 'OK' in out, out
            _run([script, 'render-all', 'out', '--scale', '0.25'], d)
            files = sorted(os.listdir(os.path.join(d, 'out')))
            assert len([f for f in files if f.endswith('.mp4')]) >= 3, files
        else:
            out_file = 'out.mov' if name == 'lower_third' else 'out.mp4'
            out = _run([script, 'render', out_file, '--scale', '0.25', '--preset', 'veryfast'], d)
            assert 'decode: clean' in out, out
            frames = _probe_frames(out)
            assert frames is None or abs(frames - info['frames']) <= 1, (frames, info['frames'])
            if name == 'lower_third':
                assert 'yuva444p' in out, out
        if name in QR_AT:
            try:
                from pyzbar import pyzbar  # noqa: F401
            except Exception:
                pass
            else:
                t = QR_AT[name] if QR_AT[name] >= 0 else dur + QR_AT[name]
                found = _run([script, 'qr', f'{t:.2f}'], d)
                urls = ast.literal_eval(found.strip().splitlines()[-1])
                assert urls and all(u.startswith('http') for u in urls), (name, found)
        if name in LOOPS:
            seam = ast.literal_eval(_run([script, 'seam'], d).strip().splitlines()[-1])
            assert seam['seam'] <= max(2.0 * seam['normal_step'], 1.0), seam
    finally:
        if not keep:
            shutil.rmtree(d, ignore_errors=True)


def cases():
    names = sorted(f[:-3] for f in os.listdir(TEMPLATES) if f.endswith('.py') and not f.startswith('_'))
    keep_root = os.environ.get('MV_TEST_KEEP')       # a folder to keep the sheets and renders for review
    return [(f'template_{n}', (lambda n=n: check(n, os.path.join(keep_root, n) if keep_root else None)))
            for n in names]
