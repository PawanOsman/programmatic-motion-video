# Motion craft

The rules that make code-drawn motion look designed rather than generated. Every number here has a
function in the engine: `seg`, `tween`, `presence`, `stagger`, `spring`, `keys`, `Beats`.

## Easing

| Motion | Curve | Why |
|---|---|---|
| Something arrives | `out_cubic`, `out_quint`, `out_expo` | Fast start, soft landing: it feels placed. |
| Something leaves | `in_cubic`, `in_expo` | Gathers speed as it goes; exits run shorter than entrances. |
| Travel from A to B, camera moves | `inout_cubic`, `inout_expo` | Calm start and stop. |
| A pop, badge or button appearing | `out_back`, `spring(t)` | A little overshoot reads as physical. |
| Continuous motion (rotation, marquee, progress, counters) | `linear_ease` | A constant rate is the point. |

Never start or stop a visible object linearly; it looks mechanical. `mv.EASE['out_cubic']` looks
curves up by name, for specs written as data.

```python
x = tween(t, 1.2, 0.5, -200, 0)                 # slides in between 1.2 s and 1.7 s (out_cubic)
a = presence(t, 1.2, 4.0)                       # 0 -> 1 at 1.2 s, back to 0 by 4.0 s
p = stagger(t, 2.0, i, each=0.06)               # item i of a group that starts at 2.0 s
y = keys(t, [(0, 0), (1.2, 300), (2.0, 280)])   # keyframes, eased between neighbours
```

## Durations

| Motion | Duration |
|---|---|
| Micro feedback (press, toggle) | 0.12 to 0.25 s |
| Entrances | 0.3 to 0.6 s |
| Exits | 0.2 to 0.4 s |
| Stagger between siblings | 0.04 to 0.08 s |
| Camera moves | 0.8 to 1.4 s, then hold at least 1 s |
| Typing | 12 to 20 characters/s (8 to 10 for emphasis or RTL) |
| Streaming AI answers | 40 to 60 characters/s, word by word (`streamed`) |
| Waits and spinners | 0.8 to 1.5 s |

**Reading time:** hold text at least `0.3 s × words + 1 s`. If it cannot be read in the time, cut
words, not time.

## Hierarchy and composition

- Show one focal point at a time; motion is how you point. Everything else stays still or drifts.
- Move the camera before an action, not during it. `Camera` keys are `(t0, t1, zoom, cx, cy)`.
- Keep a layout grid: `layout.Frame(W, H)` gives `u()` units, safe areas and orientation;
  `layout.grid`, `split_h`, `split_v`, `anchor` place things.
- Design once, deliver many sizes: sizes in `L.u(px)`, positions from `W`, `H` and safe areas,
  `L.pick(landscape, portrait, square)` for the few things that must change. Product UIs live on a
  1920x1080 stage placed by `Camera(screen=..., base=...)` (see `templates/promo.py`).

## Legibility

- **Size:** body text at least 2.5 % of frame height on TVs and signage, 3 % or more from a distance.
  Real app UIs are too small on video: design phone screens about 310 units wide (`templates/mobile_app.py`).
- **Contrast:** at least 4.5:1 for body text (WCAG AA) and 3:1 for large text: `brand.contrast(a, b)`,
  `brand.readable(bg)`.
- **Thin lines:** at least 2 px, because video stores colour at half resolution.
- **Behind captions and titles over footage:** a gradient or a box, never bare text.

## Rhythm

Land cuts and hits on beats (`Beats(bpm)`, `b.bar(n)`, `b.pulse(t)`), alternate fast and still
moments, and give the ending the longest hold. `sfx.backing()` returns the bar and beat times it
used, so picture and music share one grid.

## Transitions

Pick the one the content motivates. All are `f(c, A, B, p, ctx)`; `Timeline(transition=...,
transitions={k: fn or None})` sets the default and per-join choices (`None` = hard cut).

| Transition | Use for |
|---|---|
| hard cut (`None`) | The default and the cleanest, on the beat. |
| `crossfade` | Time passing, mood; calm signage. |
| `fade_through` | A pause or a chapter break (to black or a brand colour). |
| `push`, `slide_up` | Sequential steps; built-in directional smear at speed. |
| `zoom_through` | From the thing you clicked into what it opens (set the scene's `exit`/`entry` points). |
| `wipe` | A brand shape or angle sweeping across (pass the brand colours). |
| `iris` | A reveal from a point. |
| `blur_through` | A dreamy defocus; costly, use sparingly. |
| Match cut (your own) | An element survives the cut: a cursor grows into the next background, a dot swallows the frame. |

Avoid gimmicks unrelated to the content: cube spins, page curls, random glitches.

## Motion blur

- `Video(subframes=4)` averages sub-samples over a 180-degree shutter. It multiplies render time,
  so apply it only where motion is fast: `subframes=lambda t: 4 if tl.transition_at(t) is zoom_through else 1`.
- Very fast full-frame moves (push, slide_up) need 12+ samples or they show separate copies; the
  engine's push transitions smear themselves with a directional blur instead, so skip subframes there.
- The engine never blurs across hard cuts.

## Loops

- `Timeline(loop=True)` wraps time and runs the last transition into the first scene.
- Every periodic motion needs a period that divides the loop length. The `period=` arguments of
  `fx.mesh`, `fx.flow`, `fx.particles`, `fx.bokeh`, `fx.starfield`, `fx.waves`, `kinetic.rotator`,
  `kinetic.marquee`, `wobble` round speeds so they repeat exactly.
- Shared layers: `Timeline(background=fn, overlay=fn)` draw on global time under and over every
  scene, so a backdrop never cuts at a transition (scenes then must not `clear()`).
- Sound: `sfx.Mixer(duration, loop=True)` wraps sounds and reverb tails; make music a whole number of
  bars (`bar = 240 / bpm` seconds).
- Check: `python main.py seam` prints the jump from the last frame to the first; it should be about
  the size of a normal frame step.

## Safety

Public screens and social feeds reach people with photosensitive epilepsy. Allow no more than three
flashes in any second, no large saturated red flashes and no fast high-contrast stripes (WCAG 2.3.1,
ITU-R BT.1702). Colour changes on beats at 120 BPM (two per second) are within the limit.

## Craft touches that separate professional work

- **Overlap:** the next element starts before the last one settles.
- **Anticipation:** a small wind-up before a big move.
- **Follow-through:** secondary parts lag behind and settle (`spring`).
- **Parallax:** background layers move less than the foreground.
- **Ambient drift:** a slow drift (`wave`, `wobble`, `fx.particles`), so a held frame never looks frozen.
- **Sound on every event:** see `sound.md`.
