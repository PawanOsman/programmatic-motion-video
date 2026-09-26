# Speed and long renders

## Measure first

`python main.py bench` prints milliseconds per frame (average and worst) and a render estimate:
total time ≈ frames × ms ÷ cores. Under about 100 ms per 1080p frame per core is comfortable; the
templates run 15 to 70 ms on one core of a small cloud machine.

What things cost at 1920x1080 on one CPU core (measured; your machine will differ, the ratios hold):

| Operation | Cost |
|---|---|
| Solid fill, text, icons, UI components | well under 1 ms each |
| A full-frame image draw (1:1) | ~13 ms |
| A full-frame radial or linear gradient | 11-18 ms |
| `fx.lowres` stretch (any soft layer) | ~30 ms |
| `fx.mesh` background | ~33 ms |
| `fx.flow` SkSL background | ~45 ms |
| Blurred round-rect shadow (`blur_shadow`, 1000x600) | ~3.5 ms |
| A layer blur (`Layer(blur=8)`) over 1300x500 | ~60 ms |
| Full-frame directional smear (push and slide transitions) | 100-200 ms, only during the move |
| `fx.grain` full frame | ~50 ms (prefer `Video(grain=...)`, which is free) |

## Cache everything that repeats

- Fonts, typefaces, shaped runs, paragraphs (`mv.para`), SVGs, images and icon paths are cached by
  the engine. Build your own expensive objects once, outside `draw`.
- Record groups of static vectors as a `skia.Picture` (`PictureRecorder`) and draw the picture.
- Pre-render static full-frame backgrounds once to an image, then draw the image each frame.
- Soft layers (gradients, glows, shaders) at a fraction of the size: `fx.lowres(c, W, H, draw, 0.125)`.

## Keep costs bounded

- Give fading and blurred groups bounds: `Layer(c, a, bounds=(x0, y0, x1, y1))`.
- Motion blur multiplies render time: only on fast moments (`subframes=lambda t: 4 if ... else 1`).
- Avoid per-pixel Python loops; use numpy, numba or SkSL shaders (`fx.shader`).
- Load images with `mv.image()` (mipmaps): shrinking without them shimmers and costs more.
- Footage: decode at the size you need (`media.Footage(path, fit=(W, H))`).

## Parallel rendering and resume

- `render` splits the frames into chunks, renders them in separate processes (one per core by
  default, `--workers N`), then joins them without re-encoding and adds the sound.
- Finished chunks are kept in `out.mp4.parts/`; running the same command again resumes. Changing the
  settings (size, codec, range) clears the old chunks automatically.
- Render workers re-run your script, so everything a frame needs must come from the script itself or
  from environment variables (`MV_SIZE`, `MV_FPS`, `MV_ROW`...), never from state set at the prompt.
- More machines: split frame ranges (`--start/--end`) across them (ray, dask or plain SSH) and join
  the parts with ffmpeg's concat demuxer (`-c copy`).

## Tool-call time limits

Agents often run commands with a time limit. Start long renders detached and poll the log:

```bash
setsid nohup python main.py render out.mp4 > render.log 2>&1 < /dev/null &
tail -n 3 render.log          # repeat until it prints "wrote out.mp4"
```

Re-running the same render command resumes from the finished chunks.

## Faster previews

- Contact sheets (`python main.py sheet`) cost a dozen frames; use them for every change.
- `render preview.mp4 --scale 0.5 --preset veryfast` renders the same design at half size quickly.
- `--start/--end` renders just the part you are working on, with its sound.

## GPU when available

- Skia on OpenGL: `skia.GrDirectContext.MakeGL()` with an EGL or GLFW context.
- moderngl or pygfx for shader-heavy parts; hardware encoders (`h264_nvenc`, `h264_videotoolbox`,
  `h264_qsv`, `h264_vaapi`) by editing `mv.CODECS`.
