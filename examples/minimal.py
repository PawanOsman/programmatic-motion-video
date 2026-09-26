"""The smallest complete video: a title slides in, holds, and fades out over a soft glow. 4 s.
Every frame is a function of time t, so any moment can be drawn on its own.

Run:  python minimal.py still 1.5      one frame
      python minimal.py render hello.mp4
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))  # repo layout

import mv
from mv import *

W, H = 1920, 1080


def draw(c, t):
    c.clear(color('#0B0B12'))
    glow(c, W / 2, H / 2, 800, '#7C3AED', 0.35)
    x = tween(t, 0.3, 0.8, -500, W / 2, out_expo)          # slide in between 0.3 s and 1.1 s
    a = presence(t, 0.3, 3.6)                             # fade in, and out again by 3.6 s
    text(c, 'Hello, motion.', x, H / 2, font('Inter', 120, wght=800), '#FFFFFF', a, align='center')


video = Video(draw, 4.0, (W, H), 30)

if __name__ == '__main__':
    mv.cli(video)
