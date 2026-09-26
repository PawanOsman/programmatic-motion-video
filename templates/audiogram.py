"""Audiogram: a podcast or music clip for social feeds: cover art, show and episode titles, a live
spectrum that moves with the sound, word-timed captions and a progress bar.

Run:   python audiogram.py sheet   |   python audiogram.py render audiogram.mp4
Audio: set CONFIG['audio'] to the clip (WAV, MP3, M4A, or a video file); its analysis is cached next
       to it. Without audio, a music bed is generated so the template runs out of the box.
Captions: an SRT/VTT/Whisper JSON matching the audio (transcribe with faster-whisper).
Square by default; MV_SIZE=1080x1920 for Stories and Reels.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import numpy as np

import captions
import fx
import icons
import layout
import media
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    audio=None,                                    # e.g. 'episode12_clip.m4a'
    captions=mv.asset('sample/captions.srt'),
    cover=None,                                    # square artwork; None = placeholder
    show='The Motion Room', episode='Ep. 12 · Drawing video with code',
    accent='#F97316', bg='#120A06', ink='#FFF7ED',
    bands=36,
)
C = CONFIG
W, H = mv.env_size((1080, 1080))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
CUES = captions.chunk(captions.load(C['captions']), 4, 22)


def audio_file():
    """The clip, or a generated stand-in bed (cached) so the template renders without one."""
    if C['audio']:
        return C['audio']
    path = os.path.abspath('audiogram_standin.wav')
    if not os.path.exists(path):
        dur = CUES[-1].end + 1.0
        m = sfx.Mixer(dur)
        sfx.backing(m, bpm=96, key='E', mode='minor', style='lofi', gain=0.8, fade_in=0.3, fade_out=1.0)
        m.master(path, lufs=-16)
    return path


def analysis(path):
    """Per-frame loudness and spectrum, cached beside the audio so render workers reuse it."""
    cache = path + f'.{FPS}fps.{C["bands"]}b.npz'
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        d = np.load(cache)
        return dict(level=d['level'], bands=d['bands'])
    a = sfx.analyze(path, fps=FPS, bands=C['bands'])
    np.savez(cache, level=a['level'], bands=a['bands'])
    return a


AUDIO = audio_file()
A = analysis(AUDIO)
DURATION = min(media.probe_media(AUDIO)['duration'], len(A['level']) / FPS)
TH = ui.DARK.with_(accent=C['accent'])


def frame_of(t):
    return min(len(A['level']) - 1, max(0, int(t * FPS)))


def draw(c, t):
    c.clear(color(C['bg']))
    lvl = float(A['level'][frame_of(t)])
    fx.mesh(c, W, H, t, [C['bg'], C['accent'], '#7C2D12'], bg=C['bg'], period=20, a=0.35 + 0.15 * lvl)
    portrait = L.portrait
    safe = L.safe('social')                                     # Reels/Stories: keep clear of the app's UI
    s = L.u(420 if not portrait else 560)
    cx = W / 2
    cy = H * 0.30 if not portrait else safe[1] + s / 2 + L.u(30)
    # cover art with a ring that breathes with the loudness
    ring = s * (0.56 + 0.05 * lvl)
    c.drawCircle(cx, cy, ring, paint(C['accent'], 0.12 + 0.3 * lvl, stroke=L.u(4)))
    img = image(C['cover']) if C['cover'] else media.placeholder(800, 800, seed=2, colors=(C['bg'], C['accent'], '#FDBA74'))
    with Clip(c, mv.rrect_shape(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, L.u(36))):
        cover(c, img, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, zoom=1.02 + 0.03 * lvl)
    if not C['cover']:
        icons.draw(c, 'mic-vocal', cx, cy, s * 0.35, '#FFFFFF', 0.9, stroke=1.6)
    # titles
    ty = cy + s / 2 + L.u(70)
    mv.text(c, C['show'].upper(), cx, ty, mv.font('Inter', L.u(26), wght=700), C['accent'], align='center', tracking=0.12)
    fe = mv.fit('Inter', C['episode'], W * 0.86, L.u(46), wght=750)
    mv.text(c, C['episode'], cx, ty + L.u(56), fe, C['ink'], align='center')
    # spectrum: mirrored bars from the analysis
    bands = A['bands'][frame_of(t)]
    n = len(bands)
    bw = W * 0.8 / n
    by = ty + L.u(170) + (L.u(60) if portrait else 0)
    for i, v in enumerate(bands):
        k = min(i, n - 1 - i) / (n / 2)                       # quieter at the edges, like a lens
        h = L.u(8) + L.u(110) * float(v) * (0.45 + 0.55 * k)
        x = W * 0.1 + i * bw + bw * 0.2
        rrect(c, x, by - h / 2, x + bw * 0.6, by + h / 2, bw * 0.3, paint(C['ink'], 0.35 + 0.65 * float(v)))
    # captions
    box = (W * 0.08, by + L.u(60), W * 0.92, by + L.u(60) + L.u(110))
    captions.draw(c, CUES, t, box, style='karaoke', size=L.u(46 if not portrait else 52), hi=C['accent'], bg='none',
                  col=C['ink'], wght=700)
    # progress and time
    py = H - L.u(70) if not portrait else safe[3] - L.u(10)
    rrect(c, W * 0.08, py, W * 0.92, py + L.u(8), L.u(4), paint(C['ink'], 0.2))
    rrect(c, W * 0.08, py, W * 0.08 + W * 0.84 * t / DURATION, py + L.u(8), L.u(4), paint(C['accent']))
    fm = mv.font('JetBrains Mono', L.u(22), wght=500)
    mv.text(c, f'{int(t // 60)}:{int(t % 60):02d}', W * 0.08, py - L.u(26), fm, C['ink'], 0.7)
    mv.text(c, f'{int(DURATION // 60)}:{int(DURATION % 60):02d}', W * 0.92, py - L.u(26), fm, C['ink'], 0.7, 'right')


video = Video(draw, DURATION, (W, H), FPS, background=C['bg'])


def soundtrack():
    return sfx.loudnorm(AUDIO, 'audiogram_audio.wav', -16) if C['audio'] else AUDIO


if __name__ == '__main__':
    mv.cli(video, audio=soundtrack)
