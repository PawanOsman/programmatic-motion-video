---
name: programmatic-motion-video
description: Make animated videos in code - promos, UI and app demos, explainers, social ads, signage loops, captions, logo stings. Python and Skia draw each frame, ffmpeg encodes, sound is synced.
license: MIT for the code; bundled fonts SIL OFL 1.1, icons ISC. See LICENSE and THIRD_PARTY_NOTICES.md.
compatibility: Needs Python 3.9+, the packages in requirements.txt (skia-python, numpy, scipy, pillow, uharfbuzz...) and ffmpeg on PATH, in an environment that can run code and install packages.
metadata:
  version: "1.0.0"
---

# Motion video from code

Make broadcast-quality motion graphics without a video editor. Python draws every frame with Skia,
ffmpeg encodes the frames, and a soundtrack is synthesised on the same timeline. This skill ships a
tested engine, 14 starter templates, tools and references, so you assemble videos instead of writing
a renderer. `SKILL_DIR` below means the folder that contains this file.

The results are exact (every pixel computed), on-brand (real fonts, colours, vector logos),
repeatable (change a line, re-render) and cheap to vary (another language, size or product is new data).

## The model

A video is a pure function of time: `draw(c, t)` paints frame `n` at `t = n / fps` on a Skia canvas.
Draw code computes everything from `t` alone: no state between frames, no wall clock, no unseeded
randomness. So any frame renders alone (instant contact sheets), frames render in parallel, and
loops close exactly.

```python
x = tween(t, 1.2, 0.5, -200, 0)                 # slides in between 1.2 s and 1.7 s, eased
a = presence(t, 1.2, 4.0)                        # fades in at 1.2 s, out by 4.0 s
done = t >= T['click']                           # every UI state is a time comparison
shown = typed(TEXT, t, T['type_at'], cps=16)     # typing is a prefix of the text
```

Scenes have their own clocks; a `Timeline` joins them with transitions; a `Video` renders, encodes
and muxes the sound. Things that accumulate (physics) are simulated once up front into arrays.

## Start a video

1. **Check the machine** (installs are listed if anything is missing):
   `python SKILL_DIR/tools/check_env.py`. Setup: `bash SKILL_DIR/install.sh --deps-only` (Windows:
   `install.ps1 -DepsOnly`), or `pip install -r SKILL_DIR/requirements.txt` (add
   `--break-system-packages` on managed Pythons) plus ffmpeg:
   `apt-get install -y ffmpeg libzbar0 libgl1 libegl1`, `brew install ffmpeg zbar` or
   `winget install Gyan.FFmpeg`.
2. **Scaffold from the closest template**:
   `python SKILL_DIR/tools/new_project.py my-video --template promo` (list them with `--list`).
   This copies the engine modules, fonts, icons and samples next to `main.py`, so the project is
   self-contained. For a blank start use `--template minimal`. Never rewrite the engine: import it.
3. **Edit CONFIG** at the top of `main.py`: copy, colours, timings, logo, data. Scenes and sound read it.
4. **Iterate on stills**, not renders: `python main.py sheet` (12 moments) or
   `python main.py sheet 0.5,2.1,4.8 s.png`, `python main.py still 3.2 f.png`, `python main.py info`
   (scene start times). Look at every sheet; fix; repeat.
5. **Render**: `python main.py bench`, then `python main.py render out.mp4` (parallel, resumable,
   with sound). Other sizes: `MV_SIZE=1080x1920 python main.py render vertical.mp4`.
   Long renders: run detached and poll (`references/performance.md`).
6. **Verify and deliver** (checklist below).

Without code execution, still write the project and give the user these commands to run.

## Templates (`SKILL_DIR/templates/`)

| Template | Makes |
|---|---|
| `promo` | 30 s product promo: logo intro, hook, live product demo, features, numbers, CTA with QR; 16:9, 9:16, 1:1 |
| `ui_demo` | Desktop app walkthrough: pointer, modal, typing, loading, toasts, camera moves, step captions |
| `mobile_app` | Phone demo: chat with streamed answer, Kurdish message, notification, feature points |
| `social_ad` | 15 s vertical ad: hook, phone product shot, benefits, proof, CTA; social safe areas |
| `signage_loop` | Silent seamless expo loop (portrait 2K default): live mini demos, persistent QR, progress dots |
| `kinetic_type` | Kinetic typography on a 120 BPM grid: punches, masks, weight waves, decode, rotating words |
| `explainer` | Data story: emphasised bars with callout, lines, donut, KPI tiles, takeaway with source |
| `logo_sting` | 5 s logo reveal: outlines draw on, fill on the hit, shine, sparkles, name; optional alpha |
| `lower_third` | Name and title over footage, rendered with alpha (ProRes 4444 / VP9) |
| `captioned_clip` | Footage (or placeholder) with word-timed captions from SRT/VTT/Whisper JSON, progress bar |
| `slideshow` | Photos with Ken Burns, info cards, badges, price, contact card with QR |
| `batch_videos` | One personalised video per CSV row, validated, rendered in parallel |
| `code_walkthrough` | Typed, highlighted code; spotlight; an edit typed in as a diff; a terminal run |
| `audiogram` | Podcast/music clip: cover, live spectrum from the audio, captions, progress |

`SKILL_DIR/examples/demo.py` is a compact two-scene reference (typing, click, camera, RTL, QR,
transitions, motion blur, synced sound).

## The engine (`SKILL_DIR/engine/`, import the modules you need)

| Module | What it gives you |
|---|---|
| `mv` | time and easing (`seg tween presence stagger keys spring wave wobble Beats EASE`), colour (`color paint linear radial mix to_oklab`), shapes and paths (`rrect ngon star svg_path trim resample morph text_path`), groups (`Layer` with alpha/offset/scale/rotate/blur, `Clip`), fonts by name (`font font_file add_font_dir`), text (`text width wrap text_block fit typed streamed caret`), complex scripts (`shaped text_shaped para Paragraphs`), assets (`image cover contain svg draw_svg svg_shapes pdf_vectors qr asset`), `Camera`, `Pointer`, `Scene`, `Timeline` (loop, shared background/overlay), transitions (`crossfade fade_through push slide_up zoom_through wipe iris blur_through`), `Video` (render, still, sheet, frames, scale, grain), checks (`probe seam_check qr_check bench`), `cli` |
| `sfx` | music beds (`backing`: ambient, pulse, drive, corporate, lofi), instruments, UI sounds (`click blip whoosh swell riser impact chime sparkle type_clicks`), `Mixer` (buses, duck, fade, loop, `master`), `loudnorm`, `loudness`, `load`, `analyze` |
| `ui` | `Theme` (`DARK`, `LIGHT`, `theme_from_brand`), devices (`window phone laptop`), controls (`button text_field toggle checkbox slider tabs menu`), content (`card chat list_item table media_card avatar badge toast tooltip modal skeleton sidebar steps callout focus_ring spinner progress_bar`) |
| `fx` | backgrounds (`mesh flow gradient grid floor vignette spotlight`), particles (`particles bokeh starfield waves pulse_rings confetti sparkle`), surfaces (`shine glass`), `shader` (SkSL), `lowres`, `logo`, `placeholder_mark`, `grain` |
| `kinetic` | `reveal` (10 styles), `reveal_rtl`, `lines`, `statement`, `fit_block`, `scramble`, `counter`, `odometer`, `rotator`, `highlight`, `underline`, `strike`, `circle_mark`, `weight_wave`, `marquee` |
| `charts` | `bars` (grouped, horizontal, emphasis), `line`, `donut`, `kpi`, `sparkline`, `meter`, `ring`, `heatmap`, `legend`, `style`, `compact`, `nice_ticks` (colour-blind-safe palettes) |
| `captions` | `load` (SRT, VTT, Whisper JSON), `from_text`, `chunk`, `draw` (karaoke, box, pop, word, plain; RTL), `to_srt`, `to_vtt` |
| `codeview` | `editor` (typing, `insert` edits, highlight, diff marks, scroll), `terminal`, `tokens` |
| `icons` | 1,854 Lucide icons: `draw(c, name, x, y, size, col, progress=)`, `search`, `path`, `sheet` |
| `brand` | `from_css` (shadcn/Tailwind tokens, oklch...), `load` (brand.json), `parse_color`, `tints`, `adjust`, `contrast`, `readable`, `svg_colors`, `image_palette` |
| `layout` | `size` presets, `Frame` (`u()` units, `safe()` areas, `pick()` by orientation), `grid`, `split_h`, `split_v`, `anchor`, `inset`, `fit_rect` |
| `media` | `Footage` (decode video frames), `Sequence`, `placeholder`, `web_capture`, `probe_media`, `audio_of` |

Every signature and docstring: `references/api.md` (read it before using a module you haven't used
in this session). The engine's own source is readable when you need the details.

## Workflow

1. **Pin down where it plays**: screen size and orientation, viewing distance, sound on or off,
   loop or once, duration, audience, call to action. Defaults: general 1920x1080, 30 fps, 30-60 s,
   sound on; signage at the panel's native resolution, silent, seamless loop; social 1080x1920
   with captions burned in and a hook in the first second.
2. **Collect real material first**: website, brochures, brand CSS or tokens, logos (SVG or PDF),
   fonts, screenshots, prices, QR targets. Facts come from sources, not memory. Decode printed QR
   codes so the video points to the same places.
3. **Plan on paper**: a timing table (scene, duration, the one idea, what moves, transition out,
   sound cue). Pick a tempo and cut on beats. Budget reading time: `0.3 s × words + 1 s`.
4. **Build one scene at a time** from the template, with a sheet after every change. Check crops of
   small text at full resolution.
5. **Benchmark, render, verify, deliver**, with the specs, how to play it, and a list of anything
   illustrative you invented for the client to confirm.

## Rules that matter most

- **Easing**: arrivals `out_cubic`/`out_expo`, exits `in_cubic` (shorter), moves `inout_cubic`,
  pops `out_back`/`spring`, only continuous motion linear. Entrances 0.3-0.6 s, stagger 0.04-0.08 s,
  camera moves 0.8-1.4 s then hold.
- **One focal point at a time**; move the camera before an action, not during it.
- **Legibility**: body text ≥ 2.5 % of frame height (3 %+ for signage), contrast ≥ 4.5:1, lines ≥ 2 px.
- **Sound on every event**, timed from the same dict as the picture; -14 LUFS for web and social.
- **Loops**: `Timeline(loop=True)`, periods that divide the loop, shared `background=`,
  `Mixer(loop=True)` with a whole number of bars; check `python main.py seam`.
- **Scripts**: Arabic-script, Hebrew and Indic text must be shaped (`text_shaped`, `para`,
  `reveal_rtl`); never plain `drawString`.
- **Charts**: fixed colour order, emphasis by greying the rest, legends for 2+ series, no dual axes.
- **Safety**: no more than 3 flashes per second.
- **Honesty**: real names, prices and claims; placeholders (numbers, ratings, logos, photos,
  contacts) replaced or flagged; licences for fonts, music, footage.

## Checks before delivery

Sheet of the whole timeline and every transition midpoint; full-resolution crops of small and RTL
text; proofreading against sources; `python main.py qr t` for every QR code; `python main.py seam`
for loops; `python main.py probe out.mp4` (clean decode, size, fps, frames, `color_space=bt709`);
loudness `sfx.loudness('out.mp4')` within ±1 LU and true peak ≤ -1 dBTP; layout checked at every
delivered size. Full list and a table of known pitfalls: `references/checks-and-pitfalls.md`.

## Tools (`SKILL_DIR/tools/`)

| Tool | Does |
|---|---|
| `check_env.py` | Checks Python packages, ffmpeg encoders, fonts, icons; prints install commands |
| `new_project.py` | Scaffolds a self-contained project from a template |
| `fetch_fonts.py` | Downloads Google Fonts families by name into `./fonts` |
| `find_icons.py` | Searches the icon set, renders contact sheets |
| `export.py` | GIF, WebP, rotated, USB-player fallback, poster, repeated loop, social, WebM |
| `fix_colors.py` | Checks or repairs colour tags of existing videos (retag or re-encode) |
| `gen_api.py` | Regenerates `references/api.md` after engine changes |
| `package_skill.py` | Validates this skill and builds an upload zip |

Tests: `python SKILL_DIR/tests/run_tests.py` (engine checks; `--templates` also renders every template).

## References (read when the task needs them)

| File | When |
|---|---|
| `references/api.md` | Exact signatures of every engine function |
| `references/recipes.md` | Techniques per video type, and which template to start from |
| `references/motion-craft.md` | Easing, durations, transitions, motion blur, loops, safety, craft touches |
| `references/text-and-languages.md` | Fonts, RTL and complex scripts, typing, digits, CJK |
| `references/assets-and-brand.md` | Brand kits from CSS, logos, PDF artwork, images, footage, QR codes, honesty |
| `references/sound.md` | Music beds, sound design, loudness, loops, voice-over |
| `references/delivery.md` | Formats per destination, codecs, sizes, colour, exports, looping playback |
| `references/performance.md` | Costs, caching, parallel and detached renders, previews |
| `references/checks-and-pitfalls.md` | The full delivery checklist and known pitfalls |
| `references/libraries.md` | Python libraries for every other need (3D, maps, physics, speech, ...) |
| `references/platform.md` | Turning this into a repeatable video platform |
