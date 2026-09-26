"""media.py: existing media in a code-drawn video: footage frames, image sequences, placeholder
images, website screenshots, and file facts.

    clip = media.Footage('interview.mp4')              # decoded by ffmpeg, frame-accurate
    clip.draw(c, t, (0, 0, W, H))                      # cover-fit the frame at time t
    shot = media.web_capture('https://example.com', 'site.png', 1440, 900)   # needs playwright
    img = media.placeholder(1600, 900, seed=3, label='Product photo')     # until real photos arrive

Footage works with parallel rendering: each render worker opens its own decoder at its first frame.
"""
import functools
import json
import os
import subprocess

import numpy as np
import skia

try:
    from . import mv
except ImportError:
    import mv


def probe_media(path):
    """{'width', 'height', 'fps', 'duration', 'frames', 'has_audio'} for a video or image file."""
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                          'stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration',
                          '-of', 'json', path], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout
    d = json.loads(out)
    v = next((s for s in d.get('streams', []) if s.get('codec_type') == 'video'), {})
    num, den = (v.get('r_frame_rate') or '0/1').split('/')
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(d.get('format', {}).get('duration') or 0.0)
    return dict(width=v.get('width'), height=v.get('height'), fps=fps, duration=dur,
                frames=int(v['nb_frames']) if str(v.get('nb_frames', '')).isdigit() else int(round(dur * fps)),
                has_audio=any(s.get('codec_type') == 'audio' for s in d.get('streams', [])))


class Footage:
    """Frames of a video file as skia Images, decoded by an ffmpeg pipe.
    Reading forward frame by frame is fast; jumping restarts the decoder at the new time.
    fit=(W, H) decodes at the smallest size that still covers a W x H frame (keeping the aspect
    ratio; faster for 4K sources); size forces an exact decode size. loop=True wraps past the end;
    start offsets into the clip; speed plays it faster or slower."""
    def __init__(self, path, fit=None, size=None, loop=False, start=0.0, speed=1.0):
        info = probe_media(path)
        self.path, self.info = path, info
        self.fps = info['fps'] or 30.0
        self.duration = info['duration']
        iw, ih = info['width'], info['height']
        if size:
            self.w, self.h = size
        elif fit:
            s = min(1.0, max(fit[0] / iw, fit[1] / ih))
            self.w, self.h = max(2, int(iw * s / 2) * 2), max(2, int(ih * s / 2) * 2)
        else:
            self.w, self.h = iw, ih
        self.loop, self.start, self.speed = loop, start, speed
        self._proc = None
        self._next = None
        self._last = (None, None)

    def _index(self, t):
        u = self.start + t * self.speed
        if self.loop and self.duration:
            u %= self.duration
        u = min(max(0.0, u), max(0.0, self.duration - 1.0 / self.fps))
        return int(round(u * self.fps))

    def _open(self, n):
        self.close()
        self._proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{n / self.fps:.6f}', '-i', self.path,
                                       '-vf', f'scale={self.w}:{self.h}:flags=bicubic', '-f', 'rawvideo',
                                       '-pix_fmt', 'rgba', '-'], stdout=subprocess.PIPE)
        self._next = n

    def frame(self, t):
        """The frame shown at video time t, as a skia.Image."""
        n = self._index(t)
        if self._last[0] == n:
            return self._last[1]
        if self._proc is None or n != self._next:
            if self._proc is not None and self._next is not None and 0 < n - self._next <= 12:
                while self._next < n:          # a small jump forward: read through
                    self._proc.stdout.read(self.w * self.h * 4)
                    self._next += 1
            else:
                self._open(n)
        raw = self._proc.stdout.read(self.w * self.h * 4)
        if len(raw) < self.w * self.h * 4:
            return self._last[1] if self._last[1] is not None else mv.image_from_array(np.zeros((self.h, self.w, 4), np.uint8))
        self._next = n + 1
        img = skia.Image.fromarray(np.frombuffer(raw, np.uint8).reshape(self.h, self.w, 4).copy(),
                                   colorType=skia.kRGBA_8888_ColorType)
        self._last = (n, img)
        return img

    def draw(self, c, t, rect, mode='cover', a=1.0, zoom=1.0):
        """Draw the frame at time t into rect, cover- or contain-fitted."""
        img = self.frame(t)
        if mode == 'cover':
            mv.cover(c, img, *rect, a=a, zoom=zoom)
        else:
            mv.contain(c, img, *rect, a=a)

    def close(self):
        if self._proc is not None:
            self._proc.kill()
            self._proc = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class Sequence:
    """An image sequence (frames/%05d.png or a list of paths) played at fps."""
    def __init__(self, paths_or_pattern, fps=30.0, loop=True):
        if isinstance(paths_or_pattern, str):
            folder = os.path.dirname(paths_or_pattern) or '.'
            prefix = os.path.basename(paths_or_pattern).split('%')[0]
            self.paths = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.startswith(prefix))
        else:
            self.paths = list(paths_or_pattern)
        self.fps, self.loop = fps, loop

    def frame(self, t):
        n = int(t * self.fps)
        n = n % len(self.paths) if self.loop else min(n, len(self.paths) - 1)
        return mv.image(self.paths[n])


@functools.lru_cache(maxsize=64)
def placeholder(w, h, seed=0, label=None, colors=None, dark=True):
    """An abstract stand-in image (soft gradient, shapes, optional label) for photos not yet
    supplied; the label sits in a 'PLACEHOLDER' tag above the middle. Make it the frame's shape so
    cover-fitting doesn't crop the tag, and mark such frames as placeholders when you deliver."""
    rng = np.random.default_rng(seed)
    pal = colors or [('#1E1B4B', '#7C3AED', '#22D3EE'), ('#0F172A', '#0EA5E9', '#F472B6'),
                     ('#1C1917', '#F59E0B', '#EF4444'), ('#052E16', '#22C55E', '#A3E635')][seed % 4]
    surf = skia.Surface.MakeRasterN32Premul(w, h)
    with surf as c:
        c.drawRect(skia.Rect.MakeWH(w, h), mv.linear(0, 0, w, h, [pal[0], mv.mix(pal[0], pal[1], 0.5)]))
        for _ in range(5):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            r = rng.uniform(0.3, 0.7) * max(w, h)
            col = pal[1 + int(rng.integers(0, len(pal) - 1))]
            c.drawCircle(x, y, r, mv.radial(x, y, r, [col, col], [0.55, 0.0]))
        for _ in range(3):
            x, y, s = rng.uniform(0.1, 0.9) * w, rng.uniform(0.1, 0.9) * h, rng.uniform(0.08, 0.2) * min(w, h)
            c.drawCircle(x, y, s, mv.paint('#FFFFFF', 0.08))
        if label:                       # a tag that reads as a placeholder, not as part of the design
            s = min(w, h)
            f = mv.fit('Inter', label, w * 0.8, s * 0.042, wght=650)
            fk = mv.font('Inter', s * 0.022, wght=700)
            pad, bh = s * 0.035, s * 0.15
            bw = mv.width(label, f) + 2 * pad
            x0, y0 = w / 2 - bw / 2, h * 0.3 - bh / 2     # above the middle, where titles usually sit
            mv.rrect(c, x0, y0, x0 + bw, y0 + bh, s * 0.03, mv.paint('#000000', 0.35))
            mv.text(c, 'PLACEHOLDER', w / 2, y0 + bh * 0.3, fk, '#FFFFFF', 0.7, 'center', tracking=0.14)
            mv.text(c, label, w / 2, y0 + bh * 0.65, f, '#FFFFFF', 0.95, 'center')
    return surf.makeImageSnapshot().withDefaultMipmaps()


def web_capture(url, out, width=1440, height=900, full_page=False, scale=2, wait_ms=1200, dark=None):
    """Screenshot a web page with headless Chromium (pip install playwright; playwright install chromium).
    Use it for UI demos that must match a real site; draw it with mv.image(out)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError('web_capture needs playwright: pip install playwright && playwright install chromium') from e
    with sync_playwright() as p:
        exe = '/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=scale,
                                color_scheme=('dark' if dark else 'light') if dark is not None else None)
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=out, full_page=full_page)
        browser.close()
    return out


def audio_of(path, out_wav):
    """Extract a file's soundtrack to WAV (48 kHz stereo) for mixing or analysis."""
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', path, '-vn', '-ac', '2', '-ar', '48000', out_wav], check=True)
    return out_wav
