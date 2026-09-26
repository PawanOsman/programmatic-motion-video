# Text and languages

## Fonts

Fonts are found by family name or file path: `mv.font('Inter', 64, wght=700)`,
`mv.font('IBM Plex Sans Arabic Bold', 48)`, `mv.font('fonts/Brand-Regular.otf', 40)`.
The search covers `$MV_FONTS`, `./fonts`, `./assets/fonts`, the skill's `assets/fonts`, folders
added with `mv.add_font_dir(path)`, then the system font folders.

Bundled (SIL Open Font License, licences in `assets/fonts/licenses/`):

| Family | Use | Axes / files |
|---|---|---|
| Inter | UI and body text, Latin, Greek, Cyrillic | variable: `wght` 100-900, `opsz` 14-32 |
| Space Grotesk | display headlines with character | variable: `wght` 300-700 (default 300; the engine uses 400 unless told) |
| Instrument Serif | editorial titles, quotes | Regular, Italic |
| JetBrains Mono | code, terminals, numbers in columns | variable: `wght` 100-800 |
| IBM Plex Sans Arabic | Arabic script incl. Kurdish (Sorani), Persian, Urdu | Regular, Medium, Bold |

More families: `python tools/fetch_fonts.py "Space Mono" "Noto Sans JP" "Vazirmatn"` downloads
from Google Fonts into `./fonts`. Brand fonts: put the files in `./fonts` or a brand folder.

Variable fonts: the engine sets `wght` 400 and an optical size matched to the pixel size when you
don't, and ignores axes a font doesn't have. Animated axes are rounded so they stay cached.

## Latin, Cyrillic, Greek

- `mv.text(c, s, x, y, f, col, a, align, anchor, tracking)`: `align` left/center/right, `anchor`
  middle (capitals centred on y), baseline, or top. `tracking` is letter spacing in em (0.08 = 8 %).
- `mv.width`, `mv.wrap`, `mv.text_block` (wrapped block with leading), `mv.fit` (largest size that
  fits a width), `kinetic.fit_block` (largest size that fits a box, wrapped).
- Paint text with a gradient or stroke: `mv.text(..., p=mv.linear(...))`.

## Arabic, Kurdish (Sorani), Persian, Urdu, Hebrew, Indic, Thai, emoji

Letters change shape with their neighbours, so these scripts must be shaped (HarfBuzz). Never draw
them with plain `drawString`.

- One line: `mv.text_shaped(c, s, x_right, baseline, 'IBM Plex Sans Arabic', size, col)`
  (right-aligned by default); `mv.shaped(s, font, size)` returns `(blob, width)`.
- Word-by-word reveal: `kinetic.reveal_rtl(c, s, x_right, baseline, font, size, t, t0)`.
- Wrapped, mixed-direction paragraphs with font fallback: `mv.para(s, max_w, size, 'Inter',
  rtl=True)` (cached; `.paint(c, x, y)`, `.Height`, `.LongestLine`). It isolates RTL text so final
  punctuation lands on the correct (left) side, and falls back to IBM Plex Sans Arabic for Arabic
  script inside English text. `mv.Paragraphs` is the explicit version with your own family names.
- Chat bubbles (`ui.chat`) and captions (`captions.draw(rtl=True)`) handle RTL messages.
- Typing reveals: reveal whole grapheme clusters (`typed` does), re-shape the prefix every frame
  (the engine does), put the caret on the left for RTL.
- Check the font has the letters: Kurdish needs ڕ ڵ ۆ ێ ە (IBM Plex Sans Arabic, Noto Sans Arabic
  and Vazirmatn do).

## Digits and locale formats

- Eastern Arabic digits: `str.translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))`.
- Currencies, dates, grouping: Babel. `charts.compact(12900)` gives '12.9K'.
- Animated numbers: `kinetic.counter` keeps digits in fixed cells so they don't jitter.

## CJK and Thai

Line breaking needs a dictionary: use `mv.para`/`Paragraphs` (Skia's line breaker) or PyICU;
`mv.wrap` only breaks at spaces. Fonts: `python tools/fetch_fonts.py "Noto Sans JP"` (also SC, TC,
KR) and "Noto Sans Thai"; emoji: Noto Color Emoji.

## Typing and streaming

- `typed(s, t, t0, cps)`, `typing(...)`, `type_end(...)`, `caret(...)` for typed input.
- `streamed(s, t, t0, cps)` for AI answers that appear word by word.
- `sfx.type_clicks(m, s, t0, cps)` puts a key click on each character.

## Verification

Compare foreign-language text side by side with a trusted rendering, such as the client's brochure,
at full resolution. Do not rely on reading it yourself. Crop RTL lines from stills to check joins,
dots and the position of punctuation.
