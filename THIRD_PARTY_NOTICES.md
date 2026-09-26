# Third-party notices

The code in this repository is MIT licensed (see `LICENSE`). These bundled files keep their own
licences. All of them allow use in commercial videos; keep this file and the licence texts when you
redistribute the repository or a project made with it.

## Fonts (`assets/fonts/`)

All under the SIL Open Font License 1.1. Full texts in `assets/fonts/licenses/`. The fonts may be
used, embedded and shipped with software freely; they may not be sold on their own, and modified
versions must not use the reserved names.

| Font | Files | Copyright | Licence text |
|---|---|---|---|
| Inter (variable: weight, optical size) | `Inter.ttf` | Copyright 2020 The Inter Project Authors (https://github.com/rsms/inter) | `licenses/inter-OFL.txt` |
| JetBrains Mono (variable: weight) | `JetBrainsMono.ttf` | Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono) | `licenses/jetbrainsmono-OFL.txt` |
| Space Grotesk (variable: weight) | `SpaceGrotesk.ttf` | Copyright 2020 The Space Grotesk Project Authors (https://github.com/floriankarsten/space-grotesk) | `licenses/spacegrotesk-OFL.txt` |
| Instrument Serif | `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf` | Copyright 2022 The Instrument Serif Project Authors (https://github.com/Instrument/instrument-serif) | `licenses/instrumentserif-OFL.txt` |
| IBM Plex Sans Arabic | `IBMPlexSansArabic-Regular.ttf`, `-Medium.ttf`, `-Bold.ttf` | Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" | `licenses/ibmplexsansarabic-OFL.txt` |

Fonts downloaded later with `tools/fetch_fonts.py` come from Google Fonts; most are OFL, some
Apache 2.0 or UFL. When it downloads from the google/fonts repository, the tool saves the family's
licence file next to the fonts.

## Icons (`assets/icons/lucide.json.gz`)

The Lucide icon set (lucide-static 1.48.0, 1,854 icons), stored as compressed SVG data with each
icon's tags. ISC License, Copyright (c) 2026 Lucide Icons and Contributors; the icons derived from
Feather are also MIT, Copyright (c) 2013-present Cole Bemis. Full text and the list of Feather
icons: `assets/icons/LICENSE-lucide.txt`.

## Samples (`assets/sample/`)

`logo.svg`, `brand.json`, `people.csv` and `captions.srt` were made for this repository and are
covered by its MIT licence. The names, companies and figures in them are fictional.

## Python packages and ffmpeg

Installed separately, not bundled: skia-python (BSD-3-Clause), numpy and scipy (BSD-3-Clause),
Pillow (MIT-CMU), uharfbuzz (Apache-2.0), regex (Apache-2.0), segno (BSD-3-Clause), and optionally
pyzbar (MIT), PyMuPDF (AGPL-3.0 or commercial), Pygments (BSD-2-Clause), Playwright (Apache-2.0),
PyYAML (MIT). ffmpeg is LGPL or GPL depending on the build; the videos you make with it are yours.
