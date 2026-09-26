#!/usr/bin/env python3
"""Check that this machine can render: Python packages, ffmpeg and its encoders, fonts and icons.

    python tools/check_env.py            report, with the commands that fix anything missing
    python tools/check_env.py --quick    core requirements only

Exit code 0 when the core (skia-python, numpy, scipy, Pillow, ffmpeg with libx264) is ready.
"""
import importlib
import os
import platform
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'engine'))

CORE = [('skia', 'skia-python'), ('numpy', 'numpy'), ('scipy', 'scipy'), ('PIL', 'pillow')]
TEXT = [('uharfbuzz', 'uharfbuzz'), ('regex', 'regex'), ('segno', 'segno')]
EXTRA = [('pyzbar', 'pyzbar'), ('pymupdf', 'pymupdf'), ('pygments', 'pygments'), ('playwright', 'playwright')]
ENCODERS = [('libx264', 'H.264 (default)', True), ('libx265', 'HEVC 10-bit', False), ('libsvtav1', 'AV1', False),
            ('prores_ks', 'ProRes / ProRes 4444 with alpha', False), ('libvpx-vp9', 'VP9 / WebM with alpha', False),
            ('aac', 'AAC audio', True), ('libopus', 'Opus audio', False), ('libwebp_anim', 'animated WebP', False)]


TTY = sys.stdout.isatty()


def ok(flag):
    if not TTY:                      # plain text when an agent or a log reads the output
        return 'ok     ' if flag else 'MISSING'
    return '\033[32mok\033[0m     ' if flag else '\033[31mMISSING\033[0m'


SYSTEM_LIBS = []     # system libraries a Python package failed to load


def check_modules(group, title):
    print(f'\n{title}')
    missing = []
    for mod, pip in group:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, '__version__', '')
            print(f'  {ok(True)} {pip} {ver}')
        except ImportError as e:
            lib = re.search(r'(lib[\w.+-]+\.so[\w.]*)', str(e))
            if lib and not isinstance(e, ModuleNotFoundError):     # installed, but a system library is missing
                print(f'  {ok(False)} {pip}: needs the system library {lib.group(1)}')
                SYSTEM_LIBS.append(lib.group(1))
            else:
                print(f'  {ok(False)} {pip}')
                missing.append(pip)
        except Exception as e:
            print(f'  {ok(False)} {pip}: {e}')
            missing.append(pip)
    return missing


def main():
    quick = '--quick' in sys.argv
    print(f'Python {platform.python_version()} on {platform.system()} {platform.machine()}, {os.cpu_count()} cores')
    if sys.version_info < (3, 9):
        print('  Python 3.9 or newer is needed')
    miss_core = check_modules(CORE, 'Core')
    miss_text = check_modules(TEXT, 'Text shaping, safe typing, QR codes (requirements.txt)')
    miss_extra = [] if quick else check_modules(EXTRA, 'Optional: QR decoding, PDF artwork, highlighting, web capture (requirements-optional.txt)')
    ff = shutil.which('ffmpeg')
    print('\nffmpeg')
    print(f'  {ok(bool(ff))} ffmpeg {ff or ""}')
    have_x264 = False
    if ff:
        enc = subprocess.run([ff, '-hide_banner', '-encoders'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
        for name, what, core in ENCODERS:
            present = f' {name} ' in enc
            have_x264 |= name == 'libx264' and present
            if core or not quick:
                print(f'  {ok(present)} {name:<13} {what}')
        zbar = False
        try:
            from pyzbar import pyzbar  # noqa: F401  (needs the zbar system library)
            zbar = True
        except Exception:
            pass
        if not quick:
            print(f'  {ok(zbar)} zbar library   (QR checks)')
    print('\nAssets')
    try:
        import mv
        for fam in ('Inter', 'JetBrains Mono', 'IBM Plex Sans Arabic', 'Space Grotesk', 'Instrument Serif'):
            try:
                print(f'  {ok(True)} {fam:<22} {os.path.relpath(mv.font_file(fam), ROOT)}')
            except FileNotFoundError:
                print(f'  {ok(False)} {fam}')
        import icons
        print(f'  {ok(True)} icons: {len(icons.names())} Lucide icons')
    except Exception as e:
        print(f'  could not load the engine: {e}')
    need = miss_core + miss_text + miss_extra
    print()
    if need:
        print('Install the missing Python packages:')
        print(f'  pip install {" ".join(need)}' + ('   (add --break-system-packages on managed Pythons)' if sys.platform.startswith('linux') else ''))
    if SYSTEM_LIBS:
        print(f'Install the system libraries ({", ".join(SYSTEM_LIBS)}):')
        print('  Debian/Ubuntu: sudo apt-get install -y libgl1 libegl1')
        print('  Fedora:        sudo dnf install -y mesa-libGL mesa-libEGL')
        print('  Arch:          sudo pacman -S libglvnd')
    if not ff or not have_x264:
        print('Install ffmpeg:')
        print('  Debian/Ubuntu: sudo apt-get install -y ffmpeg libzbar0')
        print('  macOS:         brew install ffmpeg zbar')
        print('  Windows:       winget install Gyan.FFmpeg   (or choco install ffmpeg)')
    ready = not miss_core and not SYSTEM_LIBS and bool(ff) and have_x264
    print('Ready to render.' if ready else 'Not ready: fix the core items above.')
    sys.exit(0 if ready else 1)


if __name__ == '__main__':
    main()
