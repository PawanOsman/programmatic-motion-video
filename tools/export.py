#!/usr/bin/env python3
"""Export a rendered video to other deliverables.

    python tools/export.py gif in.mp4 [out.gif] [--fps 15] [--width 720]     palette-optimised GIF
    python tools/export.py webp in.mp4 [out.webp] [--fps 20] [--width 720]   animated WebP
    python tools/export.py rotate in.mp4 [out.mp4] [--dir cw|ccw]            pre-rotated for sideways screens
    python tools/export.py fallback in.mp4 [out.mp4] [--height 1080]         H.264 High 8-bit for USB media players
    python tools/export.py poster in.mp4 [out.png] [--t 2.5]                 a still for thumbnails and posters
    python tools/export.py repeat in.mp4 [out.mp4] [--times 4]               a loop repeated (players that can't loop)
    python tools/export.py social in.mp4 [out.mp4]                           H.264 + AAC at platform-friendly bitrates
    python tools/export.py webm in.mp4 [out.webm]                            VP9 + Opus for the web

All outputs keep BT.709 colour tags.
"""
import os
import subprocess
import sys

TAGS = ['-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv']


def run(args):
    subprocess.run(['ffmpeg', '-y', '-v', 'error'] + args, check=True)


def opt(name, default):
    if name in sys.argv:
        return type(default)(sys.argv[sys.argv.index(name) + 1])
    return default


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, src = sys.argv[1], sys.argv[2]
    pos, rest = [], sys.argv[3:]
    while rest:                      # positional arguments, skipping '--name value' pairs
        a = rest.pop(0)
        if a.startswith('--'):
            rest = rest[1:]
        else:
            pos.append(a)
    base = os.path.splitext(src)[0]
    if cmd == 'gif':
        out = pos[0] if pos else base + '.gif'
        fps, w = opt('--fps', 15), opt('--width', 720)
        run(['-i', src, '-vf', f'fps={fps},scale={w}:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];'
             f'[b][p]paletteuse=dither=sierra2_4a', '-loop', '0', out])
    elif cmd == 'webp':
        out = pos[0] if pos else base + '.webp'
        fps, w = opt('--fps', 20), opt('--width', 720)
        run(['-i', src, '-vf', f'fps={fps},scale={w}:-1:flags=lanczos', '-c:v', 'libwebp_anim', '-q:v', '75', '-loop', '0', out])
    elif cmd == 'rotate':
        out = pos[0] if pos else base + '_rotated.mp4'
        tr = '1' if opt('--dir', 'cw') == 'cw' else '2'
        run(['-i', src, '-vf', f'transpose={tr}', '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p']
            + TAGS + ['-c:a', 'copy', '-movflags', '+faststart', out])
    elif cmd == 'fallback':
        out = pos[0] if pos else base + '_fallback.mp4'
        h = opt('--height', 1080)
        run(['-i', src, '-vf', f"scale=-2:'min({h},ih)':flags=lanczos,fps='min(60,source_fps)'", '-c:v', 'libx264', '-profile:v', 'high',
             '-level', '4.1', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow'] + TAGS +
            ['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    elif cmd == 'poster':
        out = pos[0] if pos else base + '_poster.png'
        run(['-ss', str(opt('--t', 1.0)), '-i', src, '-frames:v', '1', out])
    elif cmd == 'repeat':
        out = pos[0] if pos else base + f"_x{opt('--times', 4)}.mp4"
        run(['-stream_loop', str(opt('--times', 4) - 1), '-i', src, '-c', 'copy', '-movflags', '+faststart', out])
    elif cmd == 'social':
        out = pos[0] if pos else base + '_social.mp4'
        run(['-i', src, '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-crf', '19', '-maxrate', '20M',
             '-bufsize', '40M', '-preset', 'slow'] + TAGS + ['-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', out])
    elif cmd == 'webm':
        out = pos[0] if pos else base + '.webm'
        run(['-i', src, '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '30', '-row-mt', '1', '-pix_fmt', 'yuv420p'] + TAGS +
            ['-c:a', 'libopus', '-b:a', '160k', out])
    else:
        sys.exit(__doc__)
    print(out)


if __name__ == '__main__':
    main()
