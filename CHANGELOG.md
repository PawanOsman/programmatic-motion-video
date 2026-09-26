# Changelog

## 1.0.0 (2026-09-26)

The skill became a repository: a tested engine that agents import instead of rewriting.

- **Engine** (`engine/`): `mv` (time, easing, colour, shapes, SVG paths, text and complex scripts,
  scenes, timeline, transitions, parallel resumable rendering, checks, command line), `sfx` (music
  beds in five styles, instruments, UI sounds, mixer with buses, ducking, loops, loudness), `ui`
  (themes, devices, controls, chat, tables, modals, toasts), `fx` (backgrounds, particles, logo
  reveals, shaders), `kinetic` (text reveals, counters, marks), `charts` (colour-blind-safe bars,
  lines, donuts, KPIs), `captions` (SRT, VTT, Whisper JSON, five styles), `codeview` (editor,
  terminal), `icons` (1,854 Lucide icons), `brand` (brand kits from CSS tokens), `layout` (sizes,
  safe areas, grids), `media` (footage, image sequences, placeholders, web capture).
- **Templates** (`templates/`): promo, ui_demo, mobile_app, social_ad, signage_loop, kinetic_type,
  explainer, logo_sting, lower_third, captioned_clip, slideshow, batch_videos, code_walkthrough,
  audiogram. All read `MV_SIZE`; seven adapt their layout to other aspect ratios from the same script.
- **Tools** (`tools/`): environment check, project scaffolding, Google Fonts download, icon search,
  exports (GIF, WebP, rotated, fallback, poster, repeat, social, WebM), colour-tag repair, API
  reference generation, packaging.
- **Assets**: five open-licensed font families including Arabic script (Kurdish, Arabic, Persian),
  the Lucide icons, a sample logo, brand kit, CSV and captions.
- **Docs and setup**: a lean `SKILL.md` with detailed `references/`, a README, install scripts for
  Claude, Codex, Gemini CLI, Cursor, GitHub Copilot, Windsurf and OpenCode (`install.sh`,
  `install.ps1`), engine and template tests, and a GitHub Actions workflow.