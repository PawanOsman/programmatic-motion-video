#!/usr/bin/env python3
"""Check or fix the colour tags of a video file.

Videos encoded from RGB without saying which matrix they used play back with shifted colours:
ffmpeg's default conversion uses the BT.601 matrix, while players assume BT.709 for HD, so a brand
purple like #6E00FF plays back as about #7218FF. The engine avoids this; this tool repairs old files.

    python tools/fix_colors.py check video.mp4
    python tools/fix_colors.py retag video.mp4 fixed.mp4      tag it as BT.601: seconds, no quality loss
    python tools/fix_colors.py reencode video.mp4 fixed.mp4   convert to BT.709 and tag it: safest for
                                                              TVs and media players that ignore tags
Use retag when the file came from ffmpeg's default RGB -> YUV conversion without tags.
"""
import json
import subprocess
import sys


def info(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=codec_name,pix_fmt,width,height,color_space,color_primaries,color_transfer,color_range',
                          '-of', 'json', path], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout
    return json.loads(out)['streams'][0]


def check(path):
    s = info(path)
    tagged = s.get('color_space') not in (None, 'unknown', 'unspecified')
    print(json.dumps(s, indent=1))
    if tagged:
        print(f"tagged as {s['color_space']}: players will decode it correctly")
    else:
        hd = (s.get('height') or 0) >= 720
        print('untagged: players will assume ' + ('BT.709 (HD)' if hd else 'BT.601 (SD)') +
              '. If it was encoded from RGB by ffmpeg without a matrix, colours will shift; fix it with retag or reencode.')
    return tagged


def retag(src, dst):
    s = info(src)
    bsf = {'h264': 'h264_metadata', 'hevc': 'hevc_metadata'}.get(s['codec_name'])
    if not bsf:
        sys.exit(f"retag supports H.264 and HEVC; this is {s['codec_name']}. Use reencode.")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-map', '0', '-c', 'copy', '-bsf:v',
                    f'{bsf}=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=6:video_full_range_flag=0',
                    '-movflags', '+faststart', dst], check=True)
    print(f'wrote {dst} (tagged BT.601 matrix, BT.709 primaries, limited range)')


def reencode(src, dst, crf=16):
    vf = 'scale=in_color_matrix=bt601:in_range=tv:out_color_matrix=bt709:out_range=tv,format=yuv420p'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a?', '-vf', vf,
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-profile:v', 'high',
                    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
                    '-c:a', 'copy', '-movflags', '+faststart', dst], check=True)
    print(f'wrote {dst} (converted to BT.709 and tagged)')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('check', 'retag', 'reencode'):
        sys.exit(__doc__)
    cmd, src = sys.argv[1], sys.argv[2]
    if cmd == 'check':
        check(src)
    else:
        dst = sys.argv[3] if len(sys.argv) > 3 else src.rsplit('.', 1)[0] + '_fixed.mp4'
        (retag if cmd == 'retag' else reencode)(src, dst)
