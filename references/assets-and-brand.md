# Client assets, brand and honesty

## Brand kits

- **From the website's CSS** (shadcn, Tailwind v4 `@theme`, any `--tokens`):
  `b = brand.from_css('globals.css', dark=True)` maps tokens to roles (`primary`, `secondary`, `bg`,
  `surface`, `surface2`, `border`, `text`, `muted`, `on_accent`, `danger`, `success`, `warning`) and
  reads `--font-sans`, `--font-mono`, `--radius`. Colours in hex, `rgb()`, `hsl()`, bare shadcn HSL
  (`222 47% 11%`), `oklch()` and `oklab()` are converted (`brand.parse_color`).
- **From a brand folder**: `brand.load('brand/')` reads `brand.json` (schema in `engine/brand.py`),
  resolves logo paths, and adds `brand/fonts/` to the font search path. `assets/sample/brand.json`
  is an example.
- **Apply it**: `th = ui.theme_from_brand(b)` for every UI component, `charts.style(th)` for charts,
  `wipe(..., colors=(b.color('primary'), b.color('secondary')))` for transitions.
- **Palettes**: `brand.tints(col, 9)` (a 50-900 scale in OKLCH), `brand.adjust(col, dl=..., dc=...)`,
  `brand.lighten/darken`, `mv.mix(a, b, t)` (OKLab), `brand.contrast(a, b)`, `brand.readable(bg)`.
- **From artwork**: `brand.svg_colors('logo.svg')`, `brand.image_palette('photo.jpg', k=5)`.

## Logos and vector art

- **SVG**: `fx.logo(c, path, cx, cy, size, t, t0, style='pop' | 'draw' | 'static')`. Flat-colour
  SVGs animate part by part; `mv.svg_shapes(path)` returns the parts (paths with fills and strokes,
  group transforms applied) for your own animation. Gradients and filters: `style='static'`
  (Skia's SVG renderer) and animate the whole mark.
- **PDF and AI files** (brochures often have outlined text and no text layer, so pdftotext returns
  nothing): `mv.pdf_vectors(pdf, page, clip, max_area, recolor, skip)` lifts logos, illustrations and
  exact foreign-language lines as sharp vectors. `recolor` adapts artwork for dark backgrounds; `skip`
  drops a colour so a static element can be replaced by an animated one. Find the clip region by
  rasterising the page (`pdftoppm -r 110`) and measuring.
- **Embedded images**: extract with `pdfimages -png` or PyMuPDF; apply their soft masks.
- **No logo yet**: `fx.placeholder_mark` draws a neutral stand-in. List it as a placeholder on delivery.

## Images, screenshots and footage

- `mv.image(path)` loads once with mipmaps (smooth when shrunk); `mv.cover` (fill, Ken Burns with
  `zoom`, focus with `fx`, `fy`) and `mv.contain` (fit whole).
- `media.web_capture(url, 'site.png', 1440, 900)` screenshots a real page with headless Chromium
  (needs playwright); draw it in a `ui.window` for demos that must match the live product.
- `media.Footage(path, fit=(W, H))` decodes video frames with ffmpeg for drawing under graphics;
  `media.Sequence` plays PNG sequences; `media.audio_of` extracts a clip's sound.
- `media.placeholder(w, h, seed, label)` stands in for photos not supplied yet (label them).
- Low-resolution assets limit how far the camera can push in; vectors don't. Upscale photos with
  spandrel (Real-ESRGAN) when you must.

## QR codes

1. Decode the client's printed ones with pyzbar or zxing-cpp (OpenCV fails on stylised dots), so the
   video points to the same places.
2. Draw crisp ones with `mv.qr(c, url, x, y, size, logo=...)`; use error correction `'h'` (the default)
   when a centre logo covers part of it (keep the logo under 20 % wide).
3. Verify: `python main.py qr 12.5` must print the exact URL.

## Honesty

- Use real product names, prices and claims from current sources. Numbers, ratings and testimonials
  in the templates are placeholders: replace them with sourced ones or remove them.
- Mark example data as illustrative on screen when it stays. List every invented bit (sample chats,
  names, code, numbers) for the client to confirm before delivery.
- Don't reproduce other brands' logos, characters or trade dress; Lucide has no brand icons on purpose.
- Fonts, music, photos and footage need licences that allow the use; the bundled fonts (OFL) and
  icons (ISC) allow commercial use with their notices.
- Voice clones only with the speaker's consent.
