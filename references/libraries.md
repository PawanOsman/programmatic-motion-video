# Library catalogue

Every entry is a PyPI package unless noted. Pick by the need in front of you; most videos only need
the first group. The engine already covers several needs natively: UI mockups (`ui`), charts
(`charts`), captions (`captions`), icons (`icons`, Lucide), brand colours from CSS (`brand`),
kinetic type (`kinetic`), backgrounds and effects (`fx`), code views (`codeview`), footage decoding
(`media`) and music and effects (`sfx`). Reach for these libraries when a job goes further.

**Core (this engine):** skia-python (vectors, text, images, SVG, shaders, paragraphs), numpy, scipy, Pillow, ffmpeg (system tool), uharfbuzz, regex, segno, pyzbar, pymupdf, Pygments (optional, highlighting), playwright (optional, web capture).

**2D drawing alternatives and pixel work**
- **pycairo / cairocffi:** Cairo 2D vector drawing; pair with Pango (PyGObject) for text layout.
- **Pillow:** image input/output and simple drawing; shapes complex scripts when built with Raqm.
- **aggdraw:** anti-aliased drawing on Pillow images.
- **skia-pathops:** boolean path operations (union, difference, intersection).
- **PySide6:** Qt's QPainter offscreen, when a Qt interface must be reproduced exactly.
- **opencv-python-headless, scikit-image, numba:** fast per-pixel effects, warps, blurs and remaps.

**GPU and shaders**
- **Skia's RuntimeEffect (SkSL, built in):** custom shaders, even on the CPU.
- **moderngl + glcontext:** headless OpenGL for shader-heavy effects and particles.
- **wgpu, pygfx:** WebGPU rendering, offscreen.
- **vispy:** OpenGL scientific visualisation.
- **taichi:** GPU simulation (fluids, particles).
- **cupy-cuda12x, torch:** GPU array maths for 4K effects.

**3D**
- **trimesh:** load, inspect and convert meshes (glTF, OBJ, STL).
- **pygfx:** offscreen 3D scenes with PBR materials.
- **bpy:** Blender as a Python module, for photoreal product shots (Cycles, EEVEE).
- **open3d, pyvista:** meshes, point clouds and scientific 3D, with offscreen screenshots.
- **mitsuba:** physically based rendering.
- **pyrender:** a simple glTF offscreen renderer (older; needs EGL or OSMesa).
- **scipy.spatial.transform (Rotation, Slerp), numpy-quaternion:** rotations and smooth orientation blends.

**SVG and vector**
- **skia.SVGDOM (built in):** draws SVGs.
- **CairoSVG, resvg-py:** SVG to PNG or PDF; resvg is the most spec-complete.
- **svgpathtools:** parse paths and find points at a given length, for draw-on effects and morph preparation.
- **svgelements:** full SVG parsing, including transforms and groups.
- **picosvg:** flatten and simplify SVGs.
- **pymupdf:** vectors, images, fonts and text from PDF and AI files.

**Text, fonts and languages**
- **uharfbuzz:** shaping for every script.
- **skia.textlayout (built in):** paragraphs with shaping, bidi, line breaking and font fallback.
- **python-bidi:** the Unicode bidi algorithm, to split mixed-direction lines.
- **PyICU:** line, word and grapheme breaking (CJK, Thai, Khmer) and locale data.
- **regex:** grapheme clusters (`\X`).
- **fonttools:** inspect, subset and instance fonts; variable axes.
- **freetype-py:** FreeType glyph access.
- **Babel:** locale-aware numbers, dates and currencies.
- **pyphen:** hyphenation.
- **arabic-reshaper:** only for legacy renderers without shaping.
- **Pygments, tree-sitter-language-pack:** syntax highlighting and exact parse trees for code.
- **ziamath:** LaTeX or MathML to SVG without installing LaTeX (matplotlib mathtext also works).
- **emoji:** find and iterate emoji; render them with Noto Color Emoji.

**Images and photos**
- **pillow-heif, rawpy, pyvips:** HEIC and AVIF files, camera RAW files, and very large images, fast.
- **rembg:** background removal for product and people cut-outs.
- **mediapipe:** face, pose, hand and person segmentation, for tracking graphics to people.
- **coloraide:** colour spaces, OKLab and OKLCH blends, contrast ratios, CSS colour parsing.
- **colour-science:** colour management and conversions.
- **colorthief:** a palette from an image.
- **spandrel (+ torch):** upscaling and restoration models such as Real-ESRGAN, for low-resolution assets.

**Existing video and media**
- **av (PyAV):** frame-accurate decoding and encoding from Python.
- **imageio, imageio-ffmpeg:** simple video input/output; ships an ffmpeg binary when none is installed.
- **scenedetect:** find the cuts in footage.
- **moviepy:** quick cuts, concatenation and overlays.
- **ffmpeg-python, python-ffmpeg:** build ffmpeg filter graphs from Python.
- **vidgear:** high-performance video input/output and streaming.
- **pymediainfo:** inspect delivered files.
- **opentimelineio:** hand edit timelines to Premiere, Resolve or Avid.
- **playwright:** headless Chromium, when the source must be a real web page. Pause its CSS and Web Animations, set their `currentTime` per frame and take a screenshot of each frame; use `page.clock` for script-driven animation.
- **lottie, rlottie-python:** write Lottie animations for apps and the web; render Lottie files to frames.

**Data, charts and maps**
- **pandas, polars:** data wrangling.
- **matplotlib:** per-frame scientific plots into a buffer.
- **plotly + kaleido, vl-convert-python (Vega-Lite):** static chart images.
- **geopandas, shapely, pyproj:** geometry, simplification and projections.
- **osmnx:** OpenStreetMap streets and buildings (credit OpenStreetMap).
- **cartopy:** projections and coastlines; Natural Earth data is public domain.
- **contextily:** basemap tiles; respect the provider's terms and attribution.

**Motion, physics and generative**
- **pymunk:** 2D rigid-body physics (drops, bounces, stacking).
- **pybullet, mujoco:** 3D physics.
- **opensimplex, pyfastnoiselite:** smooth noise for organic motion.
- **scipy.interpolate:** splines for smooth paths.
- **pytweening:** ready-made easing functions.

**Sound and music**
- **pedalboard:** studio effects (reverb, compressor, EQ, limiter) and plugin hosting.
- **soundfile:** read and write WAV, FLAC and OGG.
- **pydub:** simple audio edits.
- **librosa, essentia, beat-this:** tempo, beats, onsets and spectra.
- **pyloudnorm:** BS.1770 loudness measurement in Python.
- **mido, pretty_midi:** MIDI composition and timing.
- **pyfluidsynth:** render MIDI with SoundFont instruments.
- **pyo:** a DSP synthesis toolkit.
- **noisereduce:** clean up voice recordings.
- **sox:** SoX effects and conversions.

**Voice, speech and captions**
- **piper-tts, kokoro, coqui-tts, chatterbox-tts:** local text-to-speech. coqui-tts and chatterbox-tts can clone voices; do so only with consent.
- **faster-whisper, whisperx, stable-ts:** transcription with word timestamps.
- **montreal-forced-aligner:** align a known script to audio (install via conda).
- **pysubs2, srt, webvtt-py:** subtitle files (SRT, ASS, VTT).

**QR, barcodes and documents**
- **segno, qrcode:** make QR codes.
- **pyzbar, zxing-cpp:** read and verify QR codes.
- **python-barcode:** 1D barcodes.
- **pypdf, pdfplumber, pikepdf, pdf2image (+ poppler-utils):** PDF text, tables, internals and rasterising.
- **python-pptx, python-docx:** text and images from decks and documents.
- **tinycss2:** parse CSS for brand tokens.

**Workflow and platform**
- **pydantic:** validate scene specs before rendering.
- **PyYAML, Jinja2:** editable specs and templated variants.
- **watchdog:** re-render the contact sheet on save.
- **tqdm:** progress bars.
- **ray, dask:** spread frame ranges across machines.
- **fastapi + celery or rq (Redis), boto3:** a render service with a queue and storage.
