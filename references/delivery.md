# Output formats and delivery

## Where it plays decides the file

| Destination | Size | fps | Codec (`--codec`) | Audio |
|---|---|---|---|---|
| Web, YouTube, presentations | 1920x1080 or 3840x2160 | 30 or 60 | `h264` | AAC 256k, -14 LUFS |
| Instagram, TikTok, Shorts, Stories | 1080x1920 | 30 | `h264` | AAC, -14 LUFS |
| Instagram feed | 1080x1350 or 1080x1080 | 30 | `h264` | AAC |
| Signage, expo screen | the panel's native resolution (2560x1440, portrait 1440x2560, 3840x2160) | 30, or 60 for fast UI | `h264`; `h264-444` for crisp coloured text played from a PC | usually silent |
| Broadcast | 1920x1080 | 25 (Europe) or 29.97 (US: `MV_FPS=30000/1001`) | per spec, often `prores` | -23 LUFS (EBU R128) or -24 LKFS (ATSC A/85) |
| Editors, compositing | as the project | as the project | `prores4444` with alpha (.mov), or `frames` PNGs | WAV |
| Web with transparency | any | 30 | `vp9-alpha` (.webm) | Opus |
| Smaller files, modern players | any | any | `hevc` (10-bit, less banding) or `av1` | AAC or Opus |

Codecs: `h264`, `h264-444`, `hevc`, `av1`, `prores` (422 HQ), `prores4444` (alpha), `vp9`,
`vp9-alpha` (alpha). Transparent output needs `Video(transparent=True)` and an alpha codec
(`templates/lower_third.py`). Safari needs HEVC with alpha, which only Apple's encoder makes.

For broadcast, keep graphics inside the 90 % graphics-safe area (`L.safe('title')`, EBU R95).

## Sizes and frame rates

- Presets: `layout.size('vertical')`, `'1080p'`, `'4k'`, `'square'`, `'portrait'`, `'2k-portrait'`...
- One script, many sizes: templates read `mv.env_size()`, so
  `MV_SIZE=1080x1920 python main.py render vertical.mp4`. `MV_FPS=60` changes the rate.
- Previews: `render out.mp4 --scale 0.5` renders the same design at half size; `--start 12 --end 18`
  renders part of the timeline (the audio follows).

## Colour

The engine converts RGB to YUV with the BT.709 matrix and tags the file with it. Files encoded
without tags play back with shifted colours (ffmpeg's default BT.601 conversion read as BT.709:
#6E00FF shows as about #7218FF). Repair old files with `python tools/fix_colors.py check|retag|reencode`.

## Other deliverables

`python tools/export.py <command> in.mp4 [out]`:

| Command | Makes |
|---|---|
| `gif` | palette-optimised GIF (`--fps 15 --width 720`); gifski gives the best quality if installed |
| `webp` | animated WebP |
| `rotate` | pre-rotated video for players that can't rotate a portrait screen (`--dir cw|ccw`; ask which way the screen is turned) |
| `fallback` | H.264 High 8-bit at most 1080p/60 for USB media players and old TVs |
| `poster` | a still for thumbnails (`--t 2.5`) |
| `repeat` | a loop repeated N times for players that can't loop |
| `social` | platform-friendly H.264 + AAC |
| `webm` | VP9 + Opus |

PNG sequence: `python main.py frames out_frames/` (with alpha when transparent). Captions sidecar:
`captions.to_srt(cues, 'video.srt')` (the captioned_clip template writes one automatically).

## Looping playback

- VLC: `vlc --fullscreen --loop --no-video-title-show file.mp4`.
- USB media players often want H.264 High, 8-bit 4:2:0, at most 60 fps and sometimes at most 1080p:
  deliver the `fallback` export alongside the native file.
- Test on the target screen when possible; otherwise play full screen at native size.

## Handing over

Deliver the file with its specs (size, fps, codec, duration, loudness), how to play it, and a short
list of any illustrative content you invented for the client to confirm.
