# Recipes by video type

Start from the template in the first column when there is one (`python tools/new_project.py DIR
--template NAME`), then adapt. Every template has a CONFIG block at the top that the scenes and the
sound both read.

| Video | Template | Default size |
|---|---|---|
| Product promo | `promo` | 1920x1080; adapts to 1080x1920, 1080x1080, 4K |
| Desktop app walkthrough | `ui_demo` | 1920x1080 (stage fits any size) |
| Mobile app demo | `mobile_app` | 1920x1080 or 1080x1920 |
| Vertical social ad | `social_ad` | 1080x1920 |
| Trade-show / signage loop | `signage_loop` | 1440x2560 portrait, 2560x1440 landscape |
| Kinetic typography | `kinetic_type` | 1920x1080 |
| Explainer / data story | `explainer` | 1920x1080 |
| Logo sting | `logo_sting` | 1920x1080, optional alpha |
| Lower third (alpha) | `lower_third` | 1920x1080 ProRes 4444 / VP9 alpha |
| Captioned clip / talking head | `captioned_clip` | 1080x1920 |
| Photo slideshow (real estate, e-commerce) | `slideshow` | 1920x1080 |
| Personalised batch from CSV | `batch_videos` | 1920x1080 |
| Code walkthrough | `code_walkthrough` | 1920x1080 |
| Audiogram (podcast, music) | `audiogram` | 1080x1080 |

## Kinetic typography and title sequences
- `kinetic.reveal(..., by='char'|'word'|'line', style=...)`: rise, drop, slide, pop, blur, mask, flip, type, track.
- `kinetic.statement` fits a multi-line sentence into a box (any language length) and reveals it;
  `emphasis=[...]` colours key words.
- `kinetic.weight_wave` animates a variable font's weight; `scramble` decodes; `rotator` cycles
  words; `counter` / `odometer` count; `highlight`, `underline`, `strike`, `circle_mark` annotate;
  `marquee` runs a loop-safe ticker.
- Text as a mask: `mv.text_path(s, x, y, f)` gives outlines for `Clip`, `fx.shine` or strokes.
  Run `skia.Simplify(path)` before stroking variable-font glyphs, which overlap contours.

## Product and UI demos
- Draw the UI as vectors on a 1920x1080 stage: `ui.window`, `ui.sidebar`, `ui.button`,
  `ui.text_field`, `ui.chat`, `ui.table`, `ui.list_item`, `ui.modal`, `ui.toast`, `ui.menu`,
  `ui.tabs`, `ui.toggle`, `ui.checkbox`, `ui.slider`, `ui.skeleton`, `ui.tooltip`, `ui.callout`.
- Derive state from time: typed input (`typed`), streamed answers (`ui.chat` with `cps`), toggles
  (`on=seg(...)`), loading (`progress_bar`, `skeleton`, `spinner`).
- A `Pointer` clicks; buttons read `pointer.pressed(t, t_click)`. Put click times in one dict `T`.
- A `Camera` frames the active area at 1.2 to 1.5x before the action; notifications live in screen
  space (after `c.restore()`), so they stay in view.
- Captions name each step (`templates/ui_demo.py`); `ui.steps` shows progress.
- Use the product's real names, prices and copy; prefer real screenshots (`media.web_capture`)
  when exact fidelity matters.

## Mobile apps
- `ui.phone(c, rect, th)` returns the screen's content rect; design the app about 310 units wide
  and scale by the screen width, so it reads on video.
- Push notifications: `ui.toast` inside the screen's top edge.
- `ui.laptop` frames desktop screenshots in marketing shots.

## Explainers and data stories
- `charts.bars` (vertical, horizontal, grouped; `highlight=i` greys the rest), `charts.line`
  (draws on; `highlight='2026'`), `charts.donut` (at most 6 parts), `charts.kpi` (stat tile with
  delta and sparkline), `charts.meter`, `charts.ring`, `charts.heatmap`, `charts.legend`.
- Rules: one colour per series in a fixed order, emphasis by greying the rest, a legend for two or
  more series, selective labels, no dual axes. Cite the data source on screen.
- `ui.callout(c, target, label_xy, text, th, p)` annotates a point.
- matplotlib per frame (`fig.canvas.buffer_rgba()`) for scientific plots.

## Logo stings and intros
- `fx.logo(c, 'logo.svg', cx, cy, size, t, t0, style='draw' | 'pop' | 'static')`: outlines draw on
  then fill, or parts spring in one by one (flat-colour SVGs); `mv.svg_shapes` exposes the parts.
- Add `fx.shine` on the mark, `fx.sparkle`, `fx.pulse_rings`, an impact on the hit, 2 to 5 s total.
- Until the real logo arrives: `fx.placeholder_mark` (and say so on delivery).

## Showreels and montage
- Build the beat grid first (`Beats`), then cut to it; vary scale and direction; match cuts.
- `fx.starfield(streak=...)`, `fx.floor`, `fx.flow` give energetic backdrops.

## Social ads (vertical)
- 1080x1920, a hook in the first 1 to 2 s, captions burned in, first frame strong (it is the thumbnail).
- Keep text in `L.safe('social')`: clear of the top ~12 % and bottom ~22 % where the app's UI sits.

## Trade-show and signage loops
- The panel's native resolution and orientation; silent; 1 to 5 min; seamless (`Timeline(loop=True)`).
- Slow, readable from 2 to 3 m; a persistent QR code and progress dots (`overlay=`) so passers-by
  can join mid-loop. Play with VLC `--loop` or a media player's loop mode.

## Slideshows, real estate, e-commerce
- `cover(c, img, ..., zoom=1.02 + 0.08 * p, fx=...)` for Ken Burns moves; alternate directions.
- Info cards, `ui.badge(icon=...)` for features, a price pill; cut products out with rembg.
- Batch many videos from a spreadsheet (next section).

## Personalised and batch videos
- `templates/batch_videos.py`: validate rows first (`check`), then `render-all out/`.
- Render workers re-run the script, so the record index travels in the `MV_ROW` environment
  variable; the same trick works for any per-record variable.

## Footage with graphics (lower thirds, callouts, captions)
- `media.Footage(path, fit=(W, H))` decodes frames with ffmpeg; `clip.draw(c, t, rect)` cover-fits.
- Lower thirds as separate alpha files (`templates/lower_third.py`) drop onto an editor's timeline.
- Track graphics to people with OpenCV or MediaPipe, precomputed per frame.

## Captions, lyrics and karaoke
- `captions.load('x.srt' | 'x.vtt' | 'x.json')`, `captions.chunk(cues, 3)`, `captions.draw(..., style=
  'karaoke' | 'box' | 'pop' | 'word' | 'plain', rtl=...)`, `captions.to_srt` for a sidecar.
- Word timestamps: faster-whisper (`word_timestamps=True`) or whisperx saved as JSON.
- At most 42 characters per line, 2 lines, about 15 to 20 characters/s. Only use lyrics the client
  has the rights to.

## Code walkthroughs
- `codeview.editor(..., t, t0, cps)` types code with highlighting; `insert=(index, text, t0, cps)`
  types an edit into existing code; `highlight=[line]` and `marks={line: 'add'|'del'}` explain and diff.
- `codeview.terminal` plays commands, output, spinners and results.

## Maths and science
- Formulas: ziamath (LaTeX to SVG, then `mv.svg`), or matplotlib mathtext.
- Draw strokes on with `mv.trim(path, 0, p)`; morph shapes with `mv.resample` + `mv.morph`.

## Maps and routes
- Project longitude/latitude with pyproj; coastlines from Natural Earth, streets from OpenStreetMap
  (osmnx) as paths; draw the route on with `trim` while the camera follows. Credit OpenStreetMap.

## 3D products
- Render the 3D pass with bpy (Blender), pygfx or moderngl to images, then composite text and UI in
  Skia. Simple wireframes and isometric plates need only numpy projection.

## Music visualisers and audiograms
- `sfx.analyze(audio, fps, bands)` gives per-frame loudness and spectrum (`templates/audiogram.py`);
  cache it beside the audio so render workers reuse it. Beats: librosa or beat-this.

## Generative loops and backgrounds
- `fx.mesh`, `fx.flow` (SkSL), `fx.particles`, `fx.bokeh`, `fx.starfield`, `fx.waves`, `fx.grid`,
  `fx.floor`, `fx.pulse_rings`, `fx.confetti` (closed form, no state).
- Seed randomness (`np.random.default_rng(seed)`); write your own SkSL with `fx.shader(src, **uniforms)`
  and render soft shaders small with `fx.lowres`.

## Multi-aspect versions
- Keep scenes in layout units (`L.u`), re-lay only the frame around them, and render each size with
  `MV_SIZE=WxH python main.py render out_WxH.mp4`.
