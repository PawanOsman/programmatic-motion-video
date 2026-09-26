# Engine API reference

Generated from the code by `python tools/gen_api.py`; every entry is the real signature.
Import the modules you need (`import mv, ui, fx`) after copying `engine/` next to your script,
or run templates from the repository, which put `engine/` on the path.

Modules: [mv](#mvpy), [sfx](#sfxpy), [ui](#uipy), [fx](#fxpy), [kinetic](#kineticpy), [charts](#chartspy), [captions](#captionspy), [codeview](#codeviewpy), [icons](#iconspy), [brand](#brandpy), [layout](#layoutpy), [media](#mediapy)

## mv.py

mv.py: the core of the motion-video engine. Skia draws every frame, ffmpeg encodes.

- **`clamp(x, lo=0.0, hi=1.0)`**
- **`lerp(a, b, t)`**
- **`seg(t, t0, t1)`**: Progress of one moment: 0 before t0, 1 after t1, linear between.
- **Easing curves** `f(x)`, x in 0..1: `linear_ease`, `smoothstep`, `in_quad`, `out_quad`, `inout_quad`, `in_cubic`, `out_cubic`, `inout_cubic`, `out_quint`, `inout_quint`, `in_expo`, `out_expo`, `inout_expo`, `in_back`, `out_back`, `inout_back`, `out_elastic`, `out_bounce`
- **`ease(name_or_fn)`**: An easing curve from its name ('out_cubic') or the function itself.
- **`spring(t, stiffness=180.0, damping=12.0)`**: Damped-spring step response, t in seconds: rises to 1 with a natural overshoot.
- **`tween(t, t0, dur, a, b, ease=out_cubic)`**: A value travelling from a to b during [t0, t0 + dur].
- **`keys(t, frames, ease=inout_cubic)`**: Keyframes [(time, value), ...] with easing between neighbours; values may be numbers or tuples. keys(t, [(0, 0), (1.2, 300), (2.0, 280)]) holds the first and last values outside the range.
- **`presence(t, start, end=None, fade_in=0.35, fade_out=0.25, ease_in=out_cubic, ease_out=in_cubic)`**: 0 -> 1 as something arrives at `start`, back to 0 as it leaves at `end`. Feed it to alpha, scale or offset so entrances and exits share one timing.
- **`stagger(t, t0, i, each=0.06, dur=0.5, ease=out_cubic)`**: Eased progress of item i in a staggered group that starts at t0.
- **`wave(t, period, phase=0.0)`**: Smooth -1..1 oscillation. In a loop, use periods that divide the loop length.
- **`wobble(t, seed=0, period=None, octaves=3)`**: Smooth pseudo-random motion in -1..1 (a sum of sines). With `period` it repeats exactly, so it is safe in loops.
- **class `Beats(bpm, per_bar=4)`**: Musical time: b = Beats(120); b(8) is the time of beat 8 in seconds; b.bar(2) is bar 2.
  - `.bar(n)`
  - `.of(t)`
  - `.pulse(t, decay=8.0)`: 1 on each beat, decaying to 0: drive a throb, a flash of glow or a scale bump.
- **`rgb(c)`**: '#7C3AED', '#fff', '7C3AED', (124, 58, 237) or skia colour int -> (r, g, b) in 0..255.
- **`hex_color(c)`**
- **`color(c, a=1.0)`**
- **`to_oklab(c)`**: sRGB colour -> OKLab (L, a, b): a perceptual space for blends and palettes.
- **`from_oklab(L, a, b)`**: OKLab -> (r, g, b) in 0..255, clipped to the sRGB gamut.
- **`mix(c1, c2, t, space='oklab')`**: Blend two colours. OKLab (default) keeps blends even and avoids muddy middles; 'srgb' is plain.
- **`paint(c='#FFFFFF', a=1.0, stroke=None, cap='round', blend=None, aa=True)`**: A fill paint, or a stroke paint when stroke=width. cap: 'round', 'butt' or 'square'.
- **`linear(x0, y0, x1, y1, colors, alphas=None, pos=None)`**: Paint with a linear gradient from (x0, y0) to (x1, y1).
- **`radial(cx, cy, r, colors, alphas=None, pos=None)`**: Paint with a radial gradient centred on (cx, cy).
- **`glow(c, x, y, r, col, a=0.4)`**: Soft radial light: the cheapest way to give a flat background depth.
- **`rect(x0, y0, x1, y1)`**
- **`rrect(c, x0, y0, x1, y1, r, p)`**: Rounded rectangle. r is one radius, or four (top-left, top-right, bottom-right, bottom-left).
- **`rrect_shape(x0, y0, x1, y1, r)`**
- **`poly(pts, close=True)`**
- **`ngon(cx, cy, r, n, rot=-90.0)`**: Regular polygon path with n sides.
- **`star(cx, cy, r_out, r_in, points=5, rot=-90.0)`**: Star path. points=4 with a small r_in gives a sparkle.
- **`shadow(c, x0, y0, x1, y1, r, a=0.35, spread=28, dy=18, steps=6)`**: Soft drop shadow from stacked translucent round-rects (no blur filter, cheap at 4K).
- **`blur_shadow(c, x0, y0, x1, y1, r, a=0.4, blur=24, dy=16, col='#000000')`**: Gaussian drop shadow for a rounded rectangle (Skia blurs round-rects fast).
- **`svg_path(d)`**: SVG path data ('M3 12h18...', with arcs and relative commands) -> skia.Path.
- **`path_length(path)`**
- **`trim(path, start=0.0, end=1.0, mode='sequential')`**: The part of a path between two fractions of its length: draw-on effects. mode='sequential' draws contours one after another; 'parallel' draws every contour at once.
- **`resample(path, n=200)`**: n points spaced evenly along the path's first contour, as an (n, 2) array (for morphing).
- **`morph(a, b, t, close=True, n=200)`**: Blend two outlines -> path. a and b are paths (resampled to n points here) or (n, 2) arrays from resample(). Roll one array (np.roll) so the start points match, or the morph twists.
- **`text_path(s, x, y, f)`**: Glyph outlines of one line of text with its baseline at (x, y), as one path. Run skia.Simplify(path) before stroking variable-font glyphs, which overlap contours.
- **class `Layer(c, alpha=1.0, dx=0.0, dy=0.0, bounds=None, scale=1.0, rotate=0.0, pivot=None, blur=0.0)`**: Draw a group with one opacity, offset, scale, rotation or blur:
- **class `Clip(c, shape, r=0.0, aa=True)`**: Restrict drawing to a shape:  with Clip(c, (x0, y0, x1, y1), r=24): ... shape: a rect tuple (with optional corner radius r), skia.Rect, skia.RRect or skia.Path.
- **`asset_dirs()`**: Where packaged assets (fonts, icons, samples) are searched: $MV_ASSETS, ./assets, and the assets folder next to this engine (a project copy or the skill repository).
- **`asset(rel)`**: Path of a packaged asset, e.g. asset('icons/lucide.json'); raises if missing.
- **`font_dirs()`**
- **`add_font_dir(path)`**: Search another folder for fonts (brand fonts, downloaded families).
- **`font_file(name)`**: A font file from a path or a family name: 'Inter', 'JetBrains Mono', 'IBM Plex Sans Arabic Bold'. Looks in $MV_FONTS, ./fonts, the packaged assets/fonts and the system font folders.
- **`font_axes(path)`**: Variable axes of a font: {'wght': (min, default, max), ...}.
- **`font_axes_safe(path)`**: font_axes(), or {} when the font is missing.
- **`typeface(path, axes=())`**: Typeface from a font file or family name. axes=(('wght', 700), ('wdth', 90)) for variable fonts.
- **`font(path, size, **axes)`**: font('Inter', 64, wght=650): a family name or file, a size in px and variable axes. Variable fonts default to wght 400 and, when they have one, an optical size matched to the size. Values are rounded so animated axes stay cacheable.
- **`cap_height(f)`**
- **`x_height(f)`**
- **`line_height(f, leading=1.25)`**
- **`width(s, f, tracking=0.0)`**: Advance width of one line; tracking is letter spacing in em (0.08 = 8 % of the size).
- **`text(c, s, x, y, f, col='#FFFFFF', a=1.0, align='left', anchor='middle', tracking=0.0, p=None)`**: One line of left-to-right text; returns its width. anchor='middle' centres the capitals on y, 'baseline' sits on y, 'top' hangs from y. tracking: letter spacing in em. p: a Paint to use instead of col/a (gradients, strokes). Arabic-script, Hebrew, Indic or mixed lines: use text_shaped() or para().
- **`wrap(s, f, max_w, tracking=0.0)`**: Greedy word wrap for space-separated scripts; keeps explicit newlines. CJK, Thai and mixed-direction text need para() instead.
- **`text_block(c, s, x, y, max_w, f, col='#FFFFFF', a=1.0, align='left', leading=1.3, tracking=0.0, draw=True)`**: Wrapped left-to-right text whose first line's cap top is at y; returns the block height. draw=False only measures.
- **`fit(path, s, max_w, size, tracking=0.0, **axes)`**: The largest font, up to size, whose line fits max_w.
- **`graphemes(s)`**: User-perceived characters, so typing never splits an emoji or a letter from its marks.
- **`typed(s, t, t0, cps=18.0)`**: The part of s typed by time t, at cps characters per second.
- **`typing(s, t, t0, cps=18.0)`**: True while s is still being typed.
- **`type_end(s, t0, cps=18.0)`**: When typing s finishes.
- **`streamed(s, t, t0, cps=40.0)`**: Word-by-word reveal like a streaming AI answer: whole words appear at about cps chars/s.
- **`caret(c, x, base, h, col, t, active=True, w=4)`**: Text cursor: solid while typing, blinking when idle.
- **`shaped(s, path, size, axes=(), features=())`**: Shape one single-direction run with HarfBuzz -> (TextBlob or None, width). Letters change form with their neighbours, so a typing reveal must re-shape the growing prefix (this does).
- **`text_shaped(c, s, x, base, path, size, col='#FFFFFF', a=1.0, align='right', axes=())`**: Draw a shaped run on a baseline; right-aligned by default, as RTL copy usually is. Returns its width.
- **class `Paragraphs(families)`**: Wrapped, mixed-direction text with font fallback (Skia's paragraph engine: shaping, bidi, line breaking). A family is a font name or path, or (path, {'wght': 700}) to pin an axis.
  - `.make(s, max_w, size, families, col='#FFFFFF', a=1.0, align='left', rtl=False, bold=False, tracking=0.0)`
- **`para(s, max_w, size, font='Inter', col='#FFFFFF', a=1.0, align='left', rtl=False, tracking=0.0, fallback=DEFAULT_FALLBACK, **axes)`**: A wrapped paragraph with shaping, bidi and font fallback, cached by its arguments. Returns a skia Paragraph: .paint(c, x, y) (y is the top), .Height, .LongestLine. para('Hello سڵاو', 600, 40, 'Inter', wght=600). Fallback fonts that are missing are skipped. Animate opacity with Layer rather than `a`, so the layout stays cached.
- **`image(path)`**: Load an image once (with mipmaps, so shrinking it stays smooth).
- **`image_from_array(arr)`**: numpy uint8 array (h, w, 3 or 4) -> skia.Image.
- **`cover(c, img, x0, y0, x1, y1, a=1.0, zoom=1.0, fx=0.5, fy=0.5)`**: Fill a rectangle like CSS object-fit: cover. Animate zoom slowly for a Ken Burns move; fx, fy (0..1) choose which part stays in view.
- **`contain(c, img, x0, y0, x1, y1, a=1.0, align=(0.5, 0.5))`**: Fit the whole image inside a rectangle (CSS object-fit: contain); returns the drawn rect.
- **`svg(path_or_markup)`**: An SVG document from a file path or from SVG markup.
- **`draw_svg(c, dom, x, y, w, h)`**: Draw an SVG (with a viewBox) scaled into the box.
- **`svg_shapes(src)`**: The drawable parts of an SVG (file path or markup), for animating a logo piece by piece. Returns (shapes, viewbox): shapes are dicts {path, fill, stroke, width, opacity, id} in the SVG's own units with group transforms applied, in paint order; viewbox is (x, y, w, h). Gradients and filters are not included: use svg()/draw_svg() for the finished look.
- **`pdf_vectors(pdf_path, page, clip, max_area=None, recolor=None, skip=())`**: Vector artwork from a PDF region (logos, illustrations, outlined text) as a sharp skia.Picture. clip = (x0, y0, x1, y1) in PDF points. max_area drops big shapes such as panel backgrounds. recolor = {(r, g, b): (r, g, b)} swaps colours; skip = {(r, g, b)} drops them. Returns (picture, (w, h)); draw with c.drawPicture(pic) after translate/scale.
- **`qr(c, data, x, y, size, fg='#0F1219', bg='#FFFFFF', ecl='h', quiet=3, logo=None, radius=0.04)`**: Crisp QR code. With ecl='h' a small centre logo(c, cx, cy, s) still scans; keep it under 20 % wide. Decode a rendered frame (qr_check or `python main.py qr t`) before delivering.
- **class `Camera(zoom, cx, cy, keys=(), screen=(960, 540), base=1.0, ease=inout_cubic)`**: Frames part of a scene drawn in its own layout coordinates. Camera(1.0, 960, 540, [(2.0, 3.2, 1.6, 1200, 400)]) means: from 2.0 s to 3.2 s glide to 1.6x zoom centred on (1200, 400), then hold. Zoom blends in log space so its speed feels even. screen is where the camera centre lands on screen; base scales everything (multi-aspect layouts).
  - `.at(t)`
  - `.apply(c, t)`
  - `.to_screen(t, x, y)`
- **class `Pointer(path, clicks=(), show=(0.0, 1000000000.0), size=1.8, fill='#FFFFFF', edge='#0A0A0E', ring='#A78BFA')`**: A cursor that glides through waypoints [(t, x, y), ...] and clicks at the given times. Buttons call pointer.pressed(t, click_time) to animate their press; show=(t_in, t_out) fades it.
  - `.pos(t)`
  - `.pressed(t, tc)`: 0 -> 1 -> 0 around a click at tc: scale a button by 1 - 0.06 * pressed.
  - `.clicked(t, tc)`
  - `.draw(c, t)`
- **class `Scene(duration, draw=None, entry=None, exit=None, name=None)`**: A section with its own clock u (0 -> duration). Subclass and define draw(c, u), or pass draw=. entry/exit give screen points for zoom transitions: (x, y) or f(u) -> (x, y). During a transition the outgoing scene keeps running past its duration: hold the final state.
  - `.entry_point(u)`
  - `.exit_point(u)`
- **class `Timeline(scenes, size, transition=None, before=0.6, after=0.6, loop=False, transitions=None, background=None, overlay=None)`**: Scenes back to back. A transition(c, A, B, p, ctx) runs across each join during [join - before, join + after]; A and B draw the outgoing/incoming scene; p goes 0 -> 1. transitions={k: fn or None} overrides the join into scene k (None = hard cut). loop=True lets the last scene flow into the first. background(c, t) and overlay(c, t) draw on global time under and over every scene: a continuous backdrop, a logo bug, a progress bar. Scenes drawn over a shared background must not clear().
  - `.locate(t)`: (scene index, local time) at global time t.
  - `.start(k)`: Global start time of scene k.
  - `.cuts()`: Hard-cut times; motion blur must never sample across them.
  - `.in_transition(t)`
  - `.describe()`
  - `.transition_at(t)`: The transition function running at time t, or None: lets motion blur target only some joins, e.g. subframes=lambda t: 4 if tl.transition_at(t) is zoom_through else 1.
- **`crossfade(c, A, B, p, ctx)`**
- **`fade_through(c, A, B, p, ctx, col='#000000')`**: Fade to a colour, then up into the next scene.
- **`push(c, A, B, p, ctx, dx=-1, dy=0, smear=True)`**: Slide the new scene in; dx/dy is the direction the old one leaves: (-1, 0) = to the left. smear adds a directional blur while the move is fast (a whip pan), which reads better than sub-frame motion blur for moves this fast, so skip subframes on push joins.
- **`slide_up(c, A, B, p, ctx)`**
- **`zoom_through(c, A, B, p, ctx, zin=2.6, zout=2.2)`**: Dive into the old scene's exit point and arrive out of the new scene's entry point.
- **`wipe(c, A, B, p, ctx, colors=('#7C3AED', '#C4B5FD'), slant=0.4, bands=(0.06, 0.09))`**: Two coloured slabs sweep across at an angle (take the colours and angle from the brand).
- **`iris(c, A, B, p, ctx)`**: The new scene opens as a growing circle from its entry point.
- **`blur_through(c, A, B, p, ctx, amount=18.0)`**: Defocus out of one scene and into the next (costly: blur is per pixel).
- **`env_size(default=(1920, 1080))`**: Frame size from $MV_SIZE ('1080x1920'), else the default. Environment variables reach the parallel render workers too, so one script can render several aspect ratios.
- **`env_fps(default=30)`**: Frame rate from $MV_FPS ('60', '25', '30000/1001' for US broadcast), else the default.
- **class `Video(draw, duration, size=(1920, 1080), fps=30, background='#000000', subframes=1, shutter=0.5, cuts=(), transparent=False, dither=True, scale=1.0, grain=0.0)`**: draw(c, t) plus a format. subframes > 1 (or f(t) -> int) adds motion blur with a 180-degree shutter by default; frames whose shutter would cross a hard cut are never blurred. transparent=True keeps alpha (use codec prores4444 or vp9-alpha). dither hides gradient banding in 8-bit output but raises the bitrate (about 3x in tests): turn it off for flat designs. grain (0.02-0.06) adds monochrome film grain while encoding, at no drawing cost (it also raises the bitrate). scale < 1 renders smaller previews of the same design (draw code keeps using full-size coordinates).
  - `.set_scale(scale)`
  - `.size()`
  - `.frame(n)`: Frame n as an RGBA uint8 array (a view that the next call overwrites; copy it to keep it).
  - `.still(t, path=None)`: The frame at time t as a PIL image (saved when path is given).
  - `.sheet(times, path, cols=4, tile_w=480)`: Contact sheet of stills with their timestamps: the main way to review work before rendering.
  - `.encode_range(a, b, out, codec='h264', crf=16, preset='medium', progress=None)`: Encode frames a..b-1 to one file.
  - `.render(out, workers=None, codec='h264', crf=16, preset='medium', audio=None, chunk_s=8.0, script=None, start=None, end=None)`: Render in chunks, several at once (one process per core), join without re-encoding, add audio. Finished chunks are kept in <out>.parts/, so re-running after an interruption resumes. start/end (seconds) render part of the timeline, for reviewing motion.
  - `.export_frames(folder, every=1, start=None, end=None)`: PNG sequence (with alpha when transparent=True) for editors and compositing.
- **`mux(video, audio, out, offset=0.0)`**: Add a soundtrack without re-encoding the picture (AAC for mp4, PCM for mov, Opus for webm). offset skips into the audio, for partial renders.
- **`probe(path)`**: Stream facts plus a full decode; any decode error means the file is not safe to deliver.
- **`seam_check(video)`**: For loops: the jump from the last frame to the first should be no bigger than a normal step.
- **`qr_check(video, t)`**: Decode every QR code visible at time t (pyzbar); returns the decoded strings.
- **`bench(video, samples=12)`**: Average and worst milliseconds per frame, and the render-time estimate on this machine.
- **`cli(video, audio=None)`**: python main.py info                     duration, size, scenes and their start times python main.py sheet [t1,t2,..] [out.png]   contact sheet (default: 12 evenly spaced frames) python main.py still t [out.png]        one frame python main.py bench                    ms per frame and a render estimate python main.py seam                     loop seam against a normal frame step python main.py qr t                     decode the QR codes visible at time t python main.py render out.mp4 [--workers N] [--codec h264] [--crf 16] [--preset medium] [--scale 0.5] [--start s] [--end s] [--no-audio] python main.py frames folder [--every N]    PNG sequence python main.py probe out.mp4            file facts and a full decode test audio: a WAV path or a function returning one (built before muxing). MV_SIZE=1080x1920 before the command renders another size when the script reads mv.env_size().

Constants: `HERE`, `EASE`, `FONT_EXTS`, `DEFAULT_FALLBACK`, `SAMPLING`, `TRANSITIONS`, `CODECS`

## sfx.py

sfx.py: music and sound effects synthesised with numpy, placed on the same timeline as the picture.

- **`secs(d)`**
- **`lp(x, fc, o=2)`**
- **`hp(x, fc, o=2)`**
- **`bp(x, lo, hi, o=2)`**
- **`env(n, attack=0.005, release=0.05, total=None)`**: Linear attack and release envelope over n samples.
- **`stereo(x, pan=0.0)`**: Mono -> stereo with an equal-power pan (-1 left .. 1 right).
- **`midi(note)`**: 'A4' -> 69, 'C#3', 'Eb5'.
- **`mtof(m)`**
- **`hz(note)`**: 'A4' -> 440.0, 'C#3', 'Eb5'.
- **`chord(key='A', mode='minor', degree=0, octave=3, size=3, inversion=0)`**: Frequencies of the triad (size=3) or seventh chord (size=4) on a scale degree of a key.
- **`saw(freq, n)`**: Band-limited sawtooth (polyBLEP): bright without aliasing whistles. freq may be an array.
- **`sine(f, dur, attack=0.005, release=0.05)`**
- **`kick(dur=0.45, f0=150, f1=45, punch=1.6)`**
- **`snare(dur=0.2)`**
- **`clap()`**
- **`hat(dur=0.05, decay=75)`**
- **`open_hat(dur=0.35)`**
- **`shaker(dur=0.09)`**
- **`tom(f=110, dur=0.35)`**
- **`bass(f, dur=0.2)`**
- **`sub(f, dur=1.0)`**: Pure sine sub-bass with soft edges: felt more than heard.
- **`pluck(f, dur=0.35)`**
- **`pad(freqs, dur, cutoff=1300, attack=0.3, release=0.2)`**: Warm detuned-saw chord, stereo.
- **`bell(f, dur=1.2)`**
- **`epiano(f, dur=0.8)`**: Soft electric-piano tone (two-operator FM) for corporate and calm beds.
- **`click(v=1.0)`**: UI click / keyboard tick.
- **`blip(f=880, dur=0.25, drop=0.6)`**: Soft pop for things appearing.
- **`whoosh(dur=0.4, f0=300, f1=6000, pan0=-0.6, pan1=0.6, curve=2.0)`**: Filtered-noise sweep for moves and transitions. It peaks at the END, so start it dur before the hit.
- **`swell(dur=1.5)`**: Reverse-cymbal-like noise swell that ends on its last sample: start it dur before a hit.
- **`riser(dur=2.0, f0=110, f1=880)`**
- **`impact(dur=1.6)`**
- **`chime(kind='success')`**: Short interface cues: 'success' (rising), 'notify' (two soft tones), 'error' (low double).
- **`sparkle(dur=0.9, notes=('E6', 'G#6', 'B6', 'E7'))`**: A quick glittering arpeggio for reveals and 'magic' moments.
- **class `Mixer(duration, loop=False)`**: Buses: 'music', 'fx', 'drums', 'voice'. add(sig, time_s, ...) places a sound. duck(times) sidechains the music under kicks or voice. loop=True wraps sounds and reverb tails that run past the end back to the start, so a looping video has no audible seam. master() mixes, limits and normalises loudness; write() only mixes.
  - `.add(sig, t, gain=1.0, pan=0.0, reverb=0.0, bus='fx')`: Place a sound at time t (seconds). reverb is the send level (0..1).
  - `.duck(times, depth=0.6, release=0.09)`: Dip the music bus at these times (kicks, voice onsets).
  - `.fade(bus, t0, t1, g0=1.0, g1=0.0)`: Gain ramp on a bus from g0 at t0 to g1 at t1, holding g0 before and g1 after. fade('music', end - 2, end) fades out; fade('music', 0, 1, 0, 1) fades in.
  - `.write(path, loop=None)`: Mix to a 32-bit float WAV (no loudness normalisation).
  - `.master(path, lufs=-14.0, tp=-1.5)`: Mix, then two-pass loudness normalisation to `lufs` (see loudnorm). Returns path.
- **`loudnorm(src, dst, lufs=-14.0, tp=-1.5, lra=11.0)`**: Two-pass EBU R128 loudness normalisation: -14 LUFS web/social, -16 podcasts, -23 EBU broadcast, -24 LKFS US broadcast (ATSC A/85). tp=-1.5 leaves room for the peaks AAC encoding adds.
- **`loudness(path)`**: Integrated loudness (LUFS) and true peak (dBTP) of a file, for checks before delivery.
- **`backing(m, start=0.0, end=None, bpm=110, key='A', mode='minor', progression=None, style='pulse', gain=0.8, seed=1, fade_in=0.0, fade_out=2.0, octave=3)`**: Write a music bed into mixer m between start and end (seconds; end defaults to the mix length).
- **`type_clicks(m, text_or_count, t0, cps=16.0, gain=0.25, pan=0.1)`**: One key click per typed character (spaces get a softer click).
- **`load(path, sr=SR)`**: Decode any audio or video file's sound to a stereo float array (2, n) at sr.
- **`analyze(sig_or_path, fps=30, bands=24, fmin=40.0, fmax=12000.0, attack=0.5, release=0.12, per_band=True)`**: Per-video-frame loudness and spectrum for audiograms and visualisers. Returns dict(level=(frames,), bands=(frames, bands)), both smoothed and scaled to 0..1. attack/release (0..1) set how fast values rise and fall between frames. per_band scales each band by its own range, so quiet high bands still move (set False for a true spectrum shape).

Constants: `SR`, `NOTES`, `SCALES`, `PROGRESSIONS`, `STYLES`

## ui.py

ui.py: interface mockups for product and app demos, drawn as crisp vectors.

- **class `Theme`**
  - `.s(v)`: A default size scaled by the theme.
  - `.syn(role)`
  - `.with_(**kw)`: A copy with some fields changed: DARK.with_(accent='#0EA5E9', radius=12).
- **`theme_from_brand(brand, dark=True, **kw)`**: A Theme from a brand.Brand (its colours and fonts), dark or light.
- **`label(c, s, x, y, th, size=26, wght=500, col=None, a=1.0, align='left', anchor='middle', tracking=0.0, family=None)`**: Theme-styled single line of text; size is scaled by th.scale. Returns the width.
- **`card(c, rect, th, fill=None, radius=None, border=True, shadow=True, a=1.0, border_col=None, elevation=1.0)`**: A rounded panel with a soft shadow and a hairline border.
- **`window(c, rect, th, title='', url=None, kind='browser', loading=None, a=1.0)`**: A desktop window. kind='browser' shows an address bar with url; kind='app' shows a centred title. loading (0..1) draws a progress line under the bar. Returns the content rect.
- **`phone(c, rect, th, clock='9:41', a=1.0, body='#0F0F13', screen=None)`**: A modern phone (rect should be about 9:19.5). Draws the frame, screen, island, status bar and home indicator; returns the content rect between status bar and home indicator.
- **`laptop(c, rect, th, a=1.0, screen=None)`**: A laptop: lid with a thin bezel above a base. Returns the screen rect (16:10 works well).
- **`button(c, rect, text, th, kind='primary', press=0.0, hover=0.0, icon=None, a=1.0, size=None, radius=None, icon_right=None, fill=None, text_col=None)`**: A button. press (0..1) squashes and darkens it: pass pointer.pressed(t, t_click). kind: primary, secondary, ghost, outline, danger, success. fill overrides the colour (the text then turns black or white, whichever reads better, unless text_col is given).
- **`text_field(c, rect, th, value='', placeholder='', focus=0.0, t=None, typing=False, icon=None, a=1.0, size=None, mono=False, radius=None, trailing=None)`**: An input box. focus (0..1) lights the border and ring; pass t to show a caret (solid while typing=True, blinking otherwise). Long values scroll so the end stays visible. trailing: an icon name drawn at the right end (a send or mic button).
- **`toggle(c, x, y, on, th, size=None, a=1.0)`**: A switch at (x, y) = left edge, vertical centre. on (0..1) slides the knob.
- **`checkbox(c, x, y, checked, th, size=None, text=None, a=1.0)`**: A checkbox at (x, y) = left edge, vertical centre; checked (0..1) fills it and draws the tick.
- **`slider(c, rect, value, th, a=1.0)`**: A horizontal slider in rect (its height is the knob size); value 0..1.
- **`tabs(c, rect, th, labels, active=0.0, size=None, a=1.0)`**: Tab labels spread across rect with an underline that glides to `active` (a float animates).
- **`menu(c, x, y, w, items, th, active=-1, p=1.0, size=None)`**: A dropdown menu whose top-left is (x, y). items: labels or (icon, label[, shortcut]). active highlights a row (float glides). p (0..1) unfolds it.
- **`badge(c, x, y, text, th, col=None, fill=None, align='left', size=None, icon=None, a=1.0, dot=False)`**: A pill label; (x, y) is the left edge (or centre/right with align) at its vertical centre. Returns (x0, y0, x1, y1).
- **`avatar(c, cx, cy, r, th, initials='', img=None, col=None, ring=None, status=None, a=1.0)`**: A round avatar: an image (skia.Image) or initials on a colour; ring and status colours optional.
- **`progress_bar(c, rect, frac, th, col=None, track=None, a=1.0)`**
- **`spinner(c, cx, cy, r, t, th, col=None, width=None, a=1.0)`**: A loading ring, a pure function of t.
- **`typing_dots(c, x, y, t, th, size=None, col=None, a=1.0)`**: Three bouncing dots ('someone is typing'); (x, y) is the centre.
- **`chat(c, rect, th, messages, t, size=None, gap=None, max_frac=0.78, pad=None, a=1.0, bot_icon='sparkles', user_fill=None, bot_fill=None, font=None)`**: A chat conversation that plays over time, scrolling to keep the newest message in view. messages: dicts with role  'user' or 'bot' text  the message (any script; mixed Arabic/English wraps and orders itself) at    time it appears (s) cps   stream it word by word at this many chars/s (bot answers); None shows it at once think seconds of typing dots before a streamed answer (default 0.9) rtl   True for right-to-left text Timing helpers: ui.chat_end(message) is when a message has fully appeared.
- **`chat_end(m)`**: When a chat message has fully appeared (for timing the next beat).
- **`list_item(c, rect, th, title, subtitle=None, icon=None, trailing=None, a=1.0, selected=0.0, icon_col=None)`**: A row: icon tile, title and subtitle, trailing text or badge; selected (0..1) tints it.
- **`table(c, rect, th, header, rows, reveal=None, highlight=None, widths=None, row_h=None, size=None, a=1.0)`**: A data table. reveal (float) = how many rows are visible (the next one slides in); highlight (float) tints a row and can glide between rows; widths are column fractions.
- **`media_card(c, rect, th, img, title, subtitle=None, a=1.0, zoom=1.0, img_frac=0.66)`**: A card with an image on top (cover-fitted, zoom for a slow push) and text below.
- **`skeleton(c, rect, t, th, radius=None)`**: A loading placeholder with a moving shimmer.
- **`sidebar(c, rect, th, items, active=0.0, title=None, a=1.0, size=None)`**: A navigation column. items: (icon, label) pairs; active (float) moves the highlight.
- **`toast(c, rect, th, title, body='', icon='circle-check', col=None, p=1.0, side='top')`**: A notification card. p (0..1) slides it in from `side` ('top', 'bottom', 'right') and fades it.
- **`tooltip(c, x, y, text, th, p=1.0, side='top', size=None)`**: A small dark label pointing at (x, y).
- **`modal_buttons(rect, th, buttons=(('Cancel', 'secondary'), ('Confirm', 'primary')))`**: Where modal() puts its buttons: a list of rects in the same order as buttons (for a Pointer).
- **`modal(c, size, rect, th, title, body='', buttons=(('Cancel', 'secondary'), ('Confirm', 'primary')), p=1.0, press=None, icon=None, content=None)`**: A dialog over a dimmed screen. size = (W, H) of the canvas, or an (x0, y0, x1, y1) area to dim; press = (button index, amount). content(c, inner_rect) draws custom content (a form, a preview) inside the dialog's animation.
- **`steps(c, x, y, labels, active, th, gap=None, size=None, a=1.0)`**: A horizontal stepper: numbered dots joined by a line that fills up to `active` (float).
- **`callout(c, target, box_xy, text, th, p=1.0, size=None, col=None)`**: An annotation: a dot on target (x, y), a line drawn to a label at box_xy (left-centre).
- **`focus_ring(c, rect, t, th, radius=None, col=None, a=1.0)`**: A pulsing ring that draws the eye to an element.

Constants: `DARK`, `LIGHT`

## fx.py

fx.py: backgrounds and effects: gradients, mesh blobs, shader backgrounds, grids, grain, vignette, particles, bokeh, stars, waves, rings, confetti, sparkles, shine, glass.

- **`lowres(c, W, H, draw, scale=0.125)`**: Draw soft content (gradients, glows, blurred shapes, shaders) at a fraction of the frame size and stretch it over the frame. For soft content this looks the same and costs far less; the stretch itself costs about as much as drawing one full-frame image. draw(sub_canvas) draws in full-frame coordinates.
- **`gradient(c, rect, colors, angle=90.0, alphas=None, pos=None)`**: Fill a rect with a linear gradient at an angle (degrees; 90 = top to bottom).
- **`vignette(c, W, H, strength=0.55, col='#000000', inner=0.5)`**: Darken the edges to pull the eye to the centre.
- **`mesh(c, W, H, t, colors, bg=None, seed=0, period=24.0, blobs=None, size=0.62, a=0.9, scale=0.1)`**: A soft, slowly moving field of colour blobs (a 'mesh gradient'). Loops every period seconds.
- **`shader(src, **uniforms)`**: A Paint running an SkSL shader. Uniforms are passed by name (floats or tuples of floats) and packed in declaration order. The effect is compiled once per source.
- **`flow(c, W, H, t, colors=('#0B0B1A', '#3B1C8C', '#0EA5E9'), period=30.0, zoom=1.6, scale=0.16)`**: Domain-warped noise in three colours (an SkSL shader), rendered small and stretched: a living, liquid backdrop. Loops every period. Costs roughly 2-3 full-frame draws.
- **`grain(c, W, H, t, amount=0.05, fps=30, size=256, seed=0)`**: Film grain over an area, changing every frame. For grain over the whole frame prefer Video(grain=0.04): it is added while encoding at almost no cost. Grain raises the bitrate.
- **`grid(c, W, H, t=0.0, step=64, col='#FFFFFF', a=0.07, kind='lines', drift=(0.0, 0.0), width=1.5, fade=0.85, center=None)`**: A background grid of lines or dots, drifting at `drift` px/s, fading out from `center`. Loop-safe when drift * loop length is a multiple of step.
- **`floor(c, W, H, t, horizon=0.55, speed=0.5, col='#A78BFA', a=0.5, lines=16, cols=24, width=2.0)`**: A perspective grid floor rushing toward the viewer (retro and tech intros). speed is grid rows per second; loop-safe when speed * loop length is a whole number.
- **`particles(c, W, H, t, n=60, seed=0, col='#FFFFFF', size=(1.5, 4.0), a=(0.15, 0.7), direction=-90.0, speed=(12.0, 40.0), period=None, twinkle=0.5, glow=False)`**: Drifting dust or embers. direction in degrees (-90 = up). With period, every particle returns to its start after `period` seconds (speeds are nudged to whole trips), so loops are seamless. col may be a list of colours.
- **`bokeh(c, W, H, t, n=14, colors=('#7C3AED', '#22D3EE', '#F472B6'), seed=3, period=20.0, size=(60, 220), a=(0.05, 0.16))`**: Large soft out-of-focus discs drifting on small orbits. Loops every period.
- **`starfield(c, W, H, t, n=350, speed=0.12, seed=2, col='#FFFFFF', period=None, center=None, streak=0.0)`**: Stars flying toward the camera. speed = depth units per second; with period it is rounded so the field repeats exactly. streak > 0 draws warp-speed trails.
- **`waves(c, W, H, t, lines=8, amp=60.0, col='#FFFFFF', a=0.25, period=8.0, y=None, spread=22.0, width=2.0, freq=1.3)`**: Flowing parallel sine lines (tech and audio backdrops). Loops every period.
- **`pulse_rings(c, cx, cy, t, period=2.4, rings=3, r0=20.0, r1=300.0, col='#A78BFA', width=3.0, a=0.6)`**: Rings expanding out of a point, like a radar or a live signal. Loops every period.
- **`confetti(c, t, t0, x, y, n=140, colors=('#F43F5E', '#F59E0B', '#22C55E', '#3B82F6', '#A855F7'), seed=5, spread=55.0, angle=-90.0, power=2400.0, gravity=1500.0, drag=1.6, dur=3.4, size=18.0)`**: A burst of confetti from (x, y) at time t0, in closed form (no simulation state).
- **`sparkle(c, x, y, size, p, col='#FFFFFF', rot=0.0)`**: A four-point star that grows and fades over its life p (0..1).
- **`shine(c, shape, t, t0, dur=0.9, angle=25.0, width=0.35, a=0.45, col='#FFFFFF')`**: A glossy light band that sweeps across a shape once, starting at t0. shape: a rect tuple, skia.RRect or skia.Path (text outlines from mv.text_path work well).
- **`glass(c, rect, radius=24.0, tint='#FFFFFF', a=0.07, border=0.2, highlight=0.1)`**: A frosted-glass-looking panel: translucent fill, bright rim and a top highlight.
- **`spotlight(c, W, H, x, y, r, a=0.6, col='#000000')`**: Darken everything except a soft circle at (x, y): focus attention on one element.
- **`logo(c, src, cx, cy, size, t=1000000000.0, t0=0.0, style='pop', dur=1.2, stroke_col=None, a=1.0, each=0.12)`**: Draw an SVG logo centred on (cx, cy), `size` px on its longer side, optionally animated. style: 'pop' springs the parts in one after another; 'draw' traces each part's outline, then fills it; 'static' draws the file with Skia's SVG renderer (gradients and all). Parts come from mv.svg_shapes, so flat-colour logos animate piece by piece.
- **`placeholder_mark(c, cx, cy, size, t=1000000000.0, t0=0.0, primary='#7C3AED', secondary='#22D3EE', letter=None, a=1.0)`**: A neutral stand-in logo (rounded tile with a play mark, or a letter) that pops in at t0. Use it until the client's real logo arrives.

Constants: `TAU`, `SMOOTH`, `FLOW_SKSL`

## kinetic.py

kinetic.py: kinetic typography: text that arrives, counts, decodes, rolls, rotates and breathes.

- **`reveal(c, s, x, y, f, t, t0, by='word', each=0.06, dur=0.55, style='rise', col='#FFFFFF', a=1.0, align='left', anchor='middle', dist=None, ease=None, t_out=None, out_dur=0.35, out_style=None, tracking=0.0, paint=None, emphasis=None, em_col=None)`**: Animate one line in, unit by unit (by='char' | 'word' | 'line'), and out again from t_out. style: fade, rise, drop, slide (in from the right), pop, blur (costly), mask (slides up from behind a line), flip, type (appears instantly), track (letter spacing closes up; use by='line'). Returns the line width. paint: a skia.Paint (gradient) used instead of col. emphasis: words (any case, punctuation ignored) drawn in em_col instead of col.
- **`reveal_rtl(c, s, x_right, base, font, size, t, t0, each=0.08, dur=0.5, style='rise', col='#FFFFFF', a=1.0, dist=None, axes=())`**: Right-to-left text (Arabic, Kurdish, Persian, Urdu, Hebrew) revealed word by word, each word shaped with HarfBuzz; the first word appears first, on the right. Returns the line width.
- **`lines(c, rows, x, y, f, t, t0, leading=1.15, line_each=0.14, **kw)`**: Several lines revealed one after another; y is the first line's cap-top (anchor='top'). Extra keywords go to reveal(). Returns the block height.
- **`fit_block(s, font, box_w, box_h, max_size=200, min_size=12, leading=1.1, tracking=0.0, **axes)`**: The largest font size (up to max_size) at which s, word-wrapped, fits box_w x box_h. Returns (font, lines). Use it for big statements that must fill a space in any language length.
- **`statement(c, s, rect, font, t, t0, max_size=180, leading=1.08, align='left', valign='middle', col='#FFFFFF', by='word', style='rise', each=0.07, line_each=0.12, tracking=-0.01, emphasis=None, em_col=None, **axes)`**: A big multi-line statement fitted into rect and revealed word by word; words in emphasis are drawn in em_col. Returns (font, lines).
- **`scramble(c, s, x, y, f, t, t0, dur=1.0, col='#FFFFFF', a=1.0, align='left', anchor='middle', charset='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*<>/', seed=0, tracking=0.0, fps=30, rate=2)`**: A decoding effect: random characters settle into s from left to right over dur seconds. Characters keep the final text's positions, so the line never jitters.
- **`counter(c, x, y, f, t, t0, dur, start, end, fmt='{:,.0f}', col='#FFFFFF', a=1.0, align='left', anchor='middle', ease=mv.out_expo, tabular=True, tracking=0.0)`**: A number counting from start to end over [t0, t0 + dur], formatted with fmt ('{:,.0f}', '${:,.2f}', '{:.0f}%'). tabular keeps digits in fixed cells. Returns the drawn string.
- **`odometer(c, x, y, f, value, col='#FFFFFF', a=1.0, align='left', anchor='middle', digits=None, sep=',', min_digits=1)`**: Rolling digits like a mechanical counter; value is a float (animate it with mv.tween). Lower digits roll continuously; higher ones turn over when the digit below passes 9.
- **`rotator(c, words, x, y, f, t, period=1.8, trans=0.45, col='#FFFFFF', a=1.0, align='left', anchor='middle', t0=0.0)`**: Cycle through words in place: each slides up and out as the next slides in. Loop-safe when the loop length is a multiple of len(words) * period.
- **`highlight(c, rect, t, t0, dur=0.45, col='#FACC15', a=0.35, radius=6.0, skew=0.0)`**: A marker-pen highlight sweeping left to right behind a word (draw it before the text).
- **`underline(c, x0, x1, y, t, t0, dur=0.4, col='#FFFFFF', width=6.0, a=1.0)`**: A line that draws itself under a word.
- **`strike(c, x0, x1, y, t, t0, dur=0.35, col='#EF4444', width=6.0, a=1.0)`**: A line drawn through a word (a price cut, a crossed-out claim).
- **`circle_mark(c, rect, t, t0, dur=0.7, col='#F43F5E', width=5.0, seed=1)`**: A hand-drawn loop around a word or number, drawn on over dur.
- **`weight_wave(c, s, x, y, font, size, t, lo=250, hi=900, period=2.0, spread=0.6, col='#FFFFFF', a=1.0, align='center', anchor='middle', tracking=0.0)`**: Letters breathe between two weights of a variable font in a travelling wave. Loop-safe when the loop length is a multiple of period.
- **`marquee(c, s, y, f, t, W, speed=120.0, col='#FFFFFF', a=1.0, sep='  •  ', x0=0.0, period=None, anchor='middle', tracking=0.0)`**: An endless ticker across the frame. With period, the speed is nudged so the ticker repeats exactly every period seconds (loop-safe).

Constants: `STYLES`

## charts.py

charts.py: animated data graphics: columns and bars, lines with areas, donuts, stat tiles (KPIs), sparklines, meters, heatmaps and legends. Every mark animates from a start time t0.

- **class `Style`**
  - `.s(v)`
  - `.color(i)`
- **`style(theme=None, dark=True, accent=None, **kw)`**: A chart Style, optionally from a ui.Theme (its surface, ink, font and scale).
- **`compact(v, prefix='', suffix='', decimals=1)`**: 1284 -> '1,284', 12900 -> '12.9K', 4200000 -> '4.2M' (with an optional $ or % around it).
- **`nice_ticks(lo, hi, n=5)`**: Round axis ticks covering lo..hi (0, 250, 500, ...).
- **`legend(c, x, y, names, colors, st=DEFAULT, size=None, gap=None, a=1.0)`**: A row of colour keys and names starting at (x, y) (vertical centre). Returns its width.
- **`bars(c, rect, values, labels=None, t=1000000000.0, t0=0.0, dur=0.9, each=0.08, st=DEFAULT, colors=None, highlight=None, fmt='{:,.0f}', axis_fmt=None, horizontal=False, max_value=None, show_values=True, grid=True, ticks=5, series=None, legend_names=None, a=1.0, thickness=None)`**: Columns (or horizontal bars) growing from one baseline, staggered by `each`. values: a list (one series) or a list of lists (grouped series; pass series names for the legend). highlight: index of the bar to emphasise (others turn grey). Values count up as bars grow and sit at the bar tips.
- **`line(c, rect, series, x_labels=None, t=1000000000.0, t0=0.0, dur=1.6, st=DEFAULT, colors=None, area=None, fmt='{:,.0f}', axis_fmt=None, y_range=None, ticks=5, smooth=True, end_labels=True, dots=False, highlight=None, a=1.0, label_every=None, width=None)`**: Lines that draw themselves on, left to right. series: a list (one line), a list of lists or a dict {name: values}. area: a 10 % wash under a single line (default on for one series). highlight: name or index of the line to emphasise (others grey).
- **`donut(c, cx, cy, r, values, labels=None, t=1000000000.0, t0=0.0, dur=1.2, st=DEFAULT, colors=None, thickness=0.3, center=None, center_sub=None, gap_deg=1.6, legend_at=None, fmt='{:.0%}', a=1.0)`**: Part-to-whole as a ring (at most 6 parts). Segments sweep in one after another. center and center_sub are text in the hole; legend_at=(x, y) lists the parts with their shares.
- **`sparkline(c, rect, values, t=1000000000.0, t0=0.0, dur=1.0, col=None, end_col=None, st=DEFAULT, width=None, a=1.0)`**: A small trend line; the latest point is marked in end_col.
- **`kpi(c, rect, label, value, t=1000000000.0, t0=0.0, dur=1.2, st=DEFAULT, fmt=None, delta=None, delta_fmt='{:+.0%}', good_up=True, period=None, spark=None, card=True, a=1.0)`**: A stat tile: label, a value that counts up, an optional delta (arrow + colour + text) and an optional sparkline. fmt: a format string or function; default is compact ('12.9K').
- **`meter(c, rect, frac, t=1000000000.0, t0=0.0, dur=1.0, st=DEFAULT, col=None, label=None, fmt='{:.0%}', a=1.0)`**: A horizontal meter: the fill's colour carries the meaning, the track is a quiet step of it.
- **`ring(c, cx, cy, r, frac, t=1000000000.0, t0=0.0, dur=1.2, st=DEFAULT, col=None, width=None, fmt='{:.0%}', sub=None, a=1.0)`**: A circular meter with its value in the middle.
- **`heatmap(c, rect, grid, t=1000000000.0, t0=0.0, dur=1.2, st=DEFAULT, ramp=None, gap=None, radius=None, a=1.0)`**: A grid of cells coloured by value on a one-hue ramp (small values closest to the surface colour), revealed in a diagonal sweep. grid: rows of numbers.

Constants: `PALETTE_DARK`, `PALETTE_LIGHT`, `SEQUENTIAL_BLUE`, `STATUS`, `DEFAULT`

## captions.py

captions.py: subtitles and word-timed captions from SRT, WebVTT or Whisper-style JSON, drawn in several styles (plain, karaoke, one word at a time, pop-on, highlight box), including RTL scripts.

- **class `Word`**
- **class `Cue`**
- **`load_srt(path)`**
- **`load_vtt(path)`**
- **`load_json(path, max_chars=42)`**: Whisper / faster-whisper / whisperx JSON ({'segments': [{start, end, text, words: [...]}]}), whisperx 'word_segments', or a plain list of words [{'start', 'end', 'word' or 'text'}] (words are grouped into cues of up to max_chars, breaking at pauses and sentence ends).
- **`load(path)`**: Captions from .srt, .vtt or .json.
- **`from_text(text, t0=0.0, wps=2.6, max_chars=42, gap=0.25)`**: Timed cues from a script with no audio: about wps words per second, cues of up to max_chars.
- **`words_of(cue)`**: Word timings for a cue; spread by word length when the file had none.
- **`chunk(cues, max_words=3, max_chars=18)`**: Re-split cues into short bursts of a few words (social-style captions).
- **`to_srt(cues, path)`**
- **`to_vtt(cues, path)`**
- **`active(cues, t)`**: The cue on screen at time t, or None.
- **`draw(c, cues, t, box, style='karaoke', font='Inter', size=54, col='#FFFFFF', hi='#FACC15', bg='box', wght=750, align='center', max_lines=2, rtl=False, upper=False, leading=1.25, bg_col='#000000', bg_a=0.55)`**: Draw the caption active at t inside box (x0, y0, x1, y1); lines sit on the box's bottom edge. style: 'plain' | 'karaoke' (spoken words turn `hi`) | 'box' (a pill behind the current word) | 'pop' (words pop on as spoken) | 'word' (one big word at a time). bg: 'box' (translucent panel), 'outline' (stroked letters), 'shadow' or 'none'. rtl=True for Arabic-script or Hebrew captions (font must support the script).

## codeview.py

codeview.py: code on screen: a syntax-highlighted editor that types, scrolls, highlights and shows diffs, and a terminal that runs commands.

- **`tokens(code, lang='python')`**: [(text, role)] covering the code exactly; roles match ui.Theme.syntax.
- **`editor(c, rect, code, th, lang='python', t=None, t0=0.0, cps=30.0, typed_from=None, title='main.py', line_numbers=True, highlight=(), marks=None, size=None, a=1.0, scroll=None, header=True, caret=True, insert=None)`**: A code editor card. With t, the code after char index typed_from (default 0) types in at cps from t0 and the view scrolls to follow. insert=(char_index, text, t_start, cps) instead types new text into the middle of existing code (an edit), pushing the lines below it down. highlight: line indices (0-based) to spotlight; marks: {line: 'add' | 'del'} for a diff. Returns the caret position (x, y) on screen.
- **`terminal(c, rect, th, lines, t, prompt='$', title='Terminal', size=None, cps=26.0, a=1.0, bg=None)`**: A terminal that plays a session. Each line is a dict with 'at' (seconds) and one of: cmd  a command typed after the prompt at cps out  output text (may contain newlines) ok / err  a result line with a green check / red cross spin with 'until' (and optional 'done' text): a spinner that turns into a check The view scrolls to keep the newest line in sight.

Constants: `KEYWORDS`, `ALIAS`

## icons.py

icons.py: 1,854 Lucide line icons as Skia paths, ready to draw, colour, animate or morph.

- **`names()`**: All icon names.
- **`exists(name)`**
- **`search(query, limit=40)`**: Icon names matching a word, by name first, then by Lucide's tags.
- **`parts(name)`**: The icon's elements as (skia.Path in a 24x24 box, filled?) pairs.
- **`path(name)`**: The whole icon as one path in a 24x24 box (for trimming, morphing or clipping).
- **`draw(c, name, x, y, size=24, col='#FFFFFF', a=1.0, stroke=2.0, align='center', progress=1.0, fill=None)`**: Draw an icon. (x, y) is its centre (align='center') or top-left corner ('topleft'). stroke is in icon units (Lucide uses 2 in a 24 box) and scales with size. progress < 1 draws it on stroke by stroke; fill colours its closed shapes too.
- **`sheet(icon_names, out, cols=10, size=72, bg='#111116', col='#F4F4F5')`**: Contact sheet of icons with their names, to choose icons by eye.

## brand.py

brand.py: brand kits: colours from CSS variables (hex, rgb, hsl, oklch, shadcn-style bare HSL), brand.json files, palettes, contrast checks, and colours picked from images and SVG logos.

- **class `Brand`**
  - `.color(role, default=None)`
  - `.logo_for(dark=True)`: The logo to use on a dark (or light) background.
  - `.save(path)`
- **`hsl_to_rgb(h, s, l)`**
- **`oklch_to_rgb(L, C, h)`**: OKLCH -> sRGB (0..255), reducing chroma until the colour fits the sRGB gamut.
- **`to_oklch(col)`**
- **`parse_color(value)`**: A CSS colour -> '#RRGGBB' (None for transparent/unknown). Handles #rgb, #rrggbb(aa), rgb()/rgba(), hsl()/hsla(), oklch(), oklab(), bare shadcn HSL ('222.2 84% 4.9%') and basic names.
- **`adjust(col, l=None, c=None, h=None, dl=0.0, dc=0.0, dh=0.0)`**: Change a colour in OKLCH: set or shift lightness (0..1), chroma (0..0.4) or hue (degrees).
- **`lighten(col, amount=0.1)`**
- **`darken(col, amount=0.1)`**
- **`tints(col, n=9, lo=0.97, hi=0.25)`**: n steps of one hue from very light to dark (like a 50..900 scale), keeping its chroma feel.
- **`luminance(col)`**
- **`contrast(a, b)`**: WCAG contrast ratio between two colours (1..21). Body text needs 4.5, large text 3.
- **`readable(bg, light='#FFFFFF', dark='#111111')`**: The text colour (light or dark) with the better contrast on bg.
- **`check_text(fg, bg, large=False)`**: (ratio, passes WCAG AA) for text colour fg on bg.
- **`css_vars(css, selector=':root')`**: Custom properties (--name: value) declared in the blocks matching selector, in order.
- **`from_css(css, dark=False, name='Brand')`**: A Brand from a stylesheet's custom properties (shadcn, Tailwind v4 @theme, or any --tokens). dark=True applies the .dark block over :root.
- **`load(path)`**: A Brand from brand.json (or a folder containing it). Relative paths resolve next to the file; a fonts/ folder beside it is added to the font search path.
- **`svg_colors(path)`**: Colours used in an SVG (fill, stroke, stop-color, style attributes), most used first.
- **`image_palette(path, k=5, seed=0, size=96)`**: Dominant colours of an image (k-means in OKLab on a thumbnail), most common first.

Constants: `NAMED`, `ROLE_KEYS`

## layout.py

layout.py: frame sizes, safe areas, grids and a unit that scales one design to any resolution.

- **`size(name_or_wh)`**: (W, H) from a preset name ('1080p', 'vertical', '2k-portrait'...) or 'WxH'.
- **`orientation(W, H)`**
- **`inset(rect, dx, dy=None)`**
- **`width(rect)`**
- **`height(rect)`**
- **`center(rect)`**
- **`anchor(rect, w, h, where='center', margin=0.0)`**: A w x h rect placed in rect at 'center', 'top', 'bottom', 'left', 'right', 'top-left', ...
- **`split_h(rect, fracs, gap=0.0)`**: Side-by-side rects; fracs are relative widths, e.g. (2, 1) for two-thirds and one-third.
- **`split_v(rect, fracs, gap=0.0)`**: Stacked rects; fracs are relative heights.
- **`grid(rect, cols, rows, gap=0.0)`**: cols x rows cells, row by row.
- **`fit_rect(w, h, box, mode='contain')`**: Scale a w x h item into box ('contain' shows all of it, 'cover' fills the box); centred.
- **class `Frame(W, H, base=1080)`**: Size-aware layout helpers for one frame size. u(px) scales a size designed at 1080 px on the short side, so one layout serves 1080p, 4K, vertical and square outputs.
  - `.u(px)`
  - `.rect()`
  - `.center()`
  - `.portrait()`
  - `.safe(kind='title')`: Safe areas: 'action' (3.5 % margins), 'title' (5 %, EBU R95), 'signage' (4 %), 'social' (vertical feeds: clear of the app's caption and buttons at the bottom and right).
  - `.pick(landscape, portrait, square=None)`: Choose a value by orientation.

Constants: `SIZES`

## media.py

media.py: existing media in a code-drawn video: footage frames, image sequences, placeholder images, website screenshots, and file facts.

- **`probe_media(path)`**: {'width', 'height', 'fps', 'duration', 'frames', 'has_audio'} for a video or image file.
- **class `Footage(path, fit=None, size=None, loop=False, start=0.0, speed=1.0)`**: Frames of a video file as skia Images, decoded by an ffmpeg pipe. Reading forward frame by frame is fast; jumping restarts the decoder at the new time. fit=(W, H) decodes at the smallest size that still covers a W x H frame (keeping the aspect ratio; faster for 4K sources); size forces an exact decode size. loop=True wraps past the end; start offsets into the clip; speed plays it faster or slower.
  - `.frame(t)`: The frame shown at video time t, as a skia.Image.
  - `.draw(c, t, rect, mode='cover', a=1.0, zoom=1.0)`: Draw the frame at time t into rect, cover- or contain-fitted.
  - `.close()`
- **class `Sequence(paths_or_pattern, fps=30.0, loop=True)`**: An image sequence (frames/%05d.png or a list of paths) played at fps.
  - `.frame(t)`
- **`placeholder(w, h, seed=0, label=None, colors=None, dark=True)`**: An abstract stand-in image (soft gradient, shapes, optional label) for photos not yet supplied; the label sits in a 'PLACEHOLDER' tag above the middle. Make it the frame's shape so cover-fitting doesn't crop the tag, and mark such frames as placeholders when you deliver.
- **`web_capture(url, out, width=1440, height=900, full_page=False, scale=2, wait_ms=1200, dark=None)`**: Screenshot a web page with headless Chromium (pip install playwright; playwright install chromium). Use it for UI demos that must match a real site; draw it with mv.image(out).
- **`audio_of(path, out_wav)`**: Extract a file's soundtrack to WAV (48 kHz stereo) for mixing or analysis.
