# Checks before delivery, and pitfalls

## Checks

1. **Contact sheet** (`python main.py sheet t1,t2,...`): the whole timeline, every transition
   midpoint, the first and last frames. `python main.py info` lists the scene start times.
2. **Crops**: full-resolution stills (`python main.py still t f.png`) of small text, RTL lines and UI detail.
3. **Proofreading**: every string against its source; foreign scripts compared with the client's
   rendering; prices, dates and counts current; placeholders replaced or flagged.
4. **QR codes**: `python main.py qr t` decodes every code to the exact expected URL.
5. **Timing**: typing finishes before the camera moves; text holds for its reading time; nothing
   important happens in the last half-second before a transition; toasts and captions stay long
   enough to read.
6. **Layout at every delivered size**: sheets at each `MV_SIZE`; text inside safe areas; nothing
   clipped or overlapping.
7. **Loops**: `python main.py seam` shows a seam about the size of a normal step, and the sound loops too.
8. **File**: `python main.py probe out.mp4` shows a clean decode, the right size, fps, frame count and
   duration, and `color_space=bt709`.
9. **Loudness**: within ±1 LU of the target, true peak at or below -1 dBTP after encoding:
   `sfx.loudness('out.mp4')`.
10. **Flashes**: no more than 3 per second.
11. **Playback**: play it on the target when possible: VLC full screen and looping, a phone for vertical.

If you cannot view images, add numeric layout checks: every text width fits its box
(`mv.width`, `mv.fit`), rectangles don't overlap, elements stay inside `L.safe(...)`.
`python tests/run_tests.py` checks the engine itself.

## Pitfalls

Each one of these has cost real time.

| Symptom | Cause and fix |
|---|---|
| Colours shift in players | RGB was converted with the BT.601 matrix and not tagged. The engine converts with BT.709 and tags; old files: `tools/fix_colors.py`. |
| Variable-font weight ignored | Skia keeps only pointers to the variation coordinates; keep them referenced until `makeClone`. The engine does. |
| Wrong colours or garbage frames | numpy surfaces must be `kRGBA_8888` explicitly; `kN32` is BGRA on some platforms. The engine does. |
| RTL punctuation on the wrong end | Isolate RTL paragraphs: `mv.para(..., rtl=True)`. |
| Arabic-script letters disconnected | The text was drawn unshaped; use `text_shaped`, `reveal_rtl`, `para`. |
| Typing splits an emoji or accent | Reveal grapheme clusters (`typed` does). |
| A font name "not found" | Put the file in `./fonts`, `mv.add_font_dir`, or `tools/fetch_fonts.py "Family"`. |
| A paragraph ignores a font registered later | Skia font collections cache lookups; `mv.para` makes a new collection when families change. |
| Inner seams on stroked variable-font glyphs | `skia.Simplify(path)` first. |
| Flicker or drift between frames | State leaked: unbalanced save/restore, globals mutated in draw, unseeded random, `time.time()`. Keep draw pure. |
| Render workers draw something different from the preview | They re-run the script: pass choices through `MV_*` environment variables, not interactive state. |
| Ghost copies on fast moves | Too few motion-blur samples; the push transitions smear instead: no subframes on those joins. |
| Ghost images across cuts | Motion blur sampled across a cut; the engine skips cuts it knows (`cuts=`). |
| The loop jumps | A period that doesn't divide the loop, unwrapped time, a background that restarts per scene (use `Timeline(background=...)`), or an audio tail (`Mixer(loop=True)`). |
| Rings in dark gradients | 8-bit banding; keep `dither=True` (about 3x bitrate in tests) or use 10-bit `hevc`. |
| Thin coloured text smears | 4:2:0 chroma; make it at least 2 px, or use `h264-444` for PC playback. |
| Text wobbles while moving | Hinting; the engine turns it off and enables subpixel positioning. |
| Numbers jitter while counting | Proportional digits; `kinetic.counter` uses fixed cells. |
| A button's label disappears | Text colour equals the fill; `ui.button(fill=...)` picks black or white automatically. |
| An icon name raises KeyError | Lucide renames icons between versions; `icons.search('word')` or `tools/find_icons.py`. |
| Stylised QR codes won't decode with OpenCV | Use pyzbar or zxing-cpp. |
| PDF text extraction returns nothing | The text is outlined; lift vectors (`pdf_vectors`) and verify visually. |
| Footage looks stretched | Decode keeping the aspect (`Footage(path, fit=(W, H))`) and cover-fit. |
| The render dies at a tool timeout | Run it detached; chunks resume. |
| Audio clips after upload | AAC adds peaks; normalise to -1.5 dBTP (`master` does). |
| Scaled-down photos shimmer | Mipmaps are missing; load images with `mv.image()`. |
| Zooms go blurry | Raster images limit how far the camera can push in; vectors don't. |
| Placeholder text shows through a title | Placeholder images carry labels; pass `label=None` behind titles. |
