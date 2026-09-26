"""Captioned clip: footage (or a placeholder) with a hook title, a progress bar and word-timed
captions burned in, sized for vertical feeds. Captions come from SRT, VTT or Whisper JSON.

Run:   python captioned_clip.py sheet   |   python captioned_clip.py render clip.mp4
Footage: set CONFIG['footage'] to a video file; its sound is used as the soundtrack.
Captions: set CONFIG['captions']; get word timings with faster-whisper (word_timestamps=True) and
save them as JSON. A sidecar SRT is also written next to the render for platforms that take one.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import captions
import fx
import layout
import media
import mv
import sfx
import ui
from mv import *

CONFIG = dict(
    footage=None,                                  # e.g. 'interview.mp4'; None draws a placeholder
    captions=mv.asset('sample/captions.srt'),
    title='How this video was made',
    speaker=('Lana Ahmed', 'Head of Product'),
    style='box',                                   # 'box' | 'karaoke' | 'pop' | 'word' | 'plain'
    words_per_caption=3,
    accent='#FACC15', font='Inter', rtl=False,     # rtl=True with an Arabic-script font for Kurdish/Arabic captions
)
C = CONFIG
W, H = mv.env_size((1080, 1920))
FPS = mv.env_fps(30)
L = layout.Frame(W, H)
CUES = captions.load(C['captions'])
if C['words_per_caption']:
    CUES = captions.chunk(CUES, C['words_per_caption'])
CLIP = media.Footage(C['footage'], fit=(W, H)) if C['footage'] else None
DURATION = CLIP.duration if CLIP else round(CUES[-1].end + 1.0, 3)
SAFE = L.safe('social') if L.portrait else L.safe('title')
TH = ui.DARK


def footage(c, t):
    if CLIP:
        CLIP.draw(c, t, (0, 0, W, H))
        return
    img = media.placeholder(1280, 1280, seed=2, label=None)          # stand-in until real footage arrives
    cover(c, img, 0, 0, W, H, zoom=1.05 + 0.08 * t / DURATION, fx=0.5 + 0.1 * wave(t, DURATION))
    c.drawRect(mv.rect(0, 0, W, H), paint('#000000', 0.25))
    mv.text(c, 'FOOTAGE PLACEHOLDER', W / 2, H * 0.45, mv.font('Inter', L.u(40), wght=700), '#FFFFFF', 0.35, 'center')


def draw(c, t):
    footage(c, t)
    # readability: darken the top and bottom behind the text
    c.drawRect(mv.rect(0, 0, W, H * 0.25), mv.linear(0, 0, 0, H * 0.25, ['#000000', '#000000'], [0.55, 0.0]))
    c.drawRect(mv.rect(0, H * 0.55, W, H), mv.linear(0, H * 0.55, 0, H, ['#000000', '#000000'], [0.0, 0.6]))
    # progress bar and title
    bar_y = SAFE[1] - L.u(40)
    rrect(c, SAFE[0], bar_y, SAFE[2], bar_y + L.u(8), L.u(4), paint('#FFFFFF', 0.25))
    rrect(c, SAFE[0], bar_y, SAFE[0] + (SAFE[2] - SAFE[0]) * t / DURATION, bar_y + L.u(8), L.u(4), paint(C['accent']))
    a = presence(t, 0.2, None, 0.5)
    f = mv.fit('Inter', C['title'], layout.width(SAFE), L.u(64), wght=800)
    with Layer(c, a, dy=(1 - a) * L.u(20)):
        mv.text(c, C['title'], (SAFE[0] + SAFE[2]) / 2, SAFE[1] + L.u(40), f, '#FFFFFF', align='center')
    # speaker tag for the first seconds
    if C['speaker']:
        p = presence(t, 0.6, 4.0, 0.5, 0.4)
        if p > 0:
            ui.badge(c, SAFE[0], SAFE[1] + L.u(130), C['speaker'][0] + '  ·  ' + C['speaker'][1], TH, col='#FFFFFF',
                     fill='#111118', size=L.u(26), icon='mic', a=p)
    # captions, inside the safe area above the platform's own UI
    box = (SAFE[0], SAFE[1], SAFE[2], SAFE[3] - L.u(40))
    size = L.u(64 if L.portrait else 52)
    captions.draw(c, CUES, t, box, style=C['style'], font=C['font'], size=size, hi=C['accent'], rtl=C['rtl'],
                  bg='box' if C['style'] in ('box', 'plain', 'karaoke', 'word') else 'outline', upper=False)


video = Video(draw, DURATION, (W, H), FPS)


def soundtrack():
    if C['footage']:
        track = media.audio_of(C['footage'], 'clip_audio_raw.wav')
        return sfx.loudnorm(track, 'clip_audio.wav', -14)
    m = sfx.Mixer(DURATION)
    sfx.backing(m, bpm=90, key='C', mode='major', style='lofi', gain=0.6, fade_in=0.5, fade_out=1.5)
    return m.master('clip_audio.wav', lufs=-16)


if __name__ == '__main__':
    if 'render' in sys.argv:
        out = next((a for a in sys.argv[2:] if not a.startswith('-')), 'clip.mp4')
        captions.to_srt(CUES, os.path.splitext(out)[0] + '.srt')
    mv.cli(video, audio=soundtrack)
