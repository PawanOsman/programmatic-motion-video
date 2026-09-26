# Growing it into a platform

For repeat work, keep the engine as a library and let an LLM write data instead of drawing code.
This repository is already the first step: templates configured by a CONFIG block, a brand kit
loader, batch rendering from records, and tools for projects, fonts, exports and checks.

- **Templates:** one scene class per video type (UI demo step, stat reveal, quote card, logo sting, product card). Each is configured by a small JSON or YAML spec: text, timings, assets, brand.
- **Brand kits:** colours, fonts, logos and lifted PDF vectors, stored once per client.
- **Review loop:**
  1. The LLM fills specs from a brief.
  2. pydantic validates them.
  3. The engine renders a contact sheet in seconds for review.
  4. The full video renders in parallel.
- **Formats:** one spec, many outputs (16:9, 9:16, 1:1, portrait signage), by swapping the frame layout and stage placement.
- **Scale:** a render service (FastAPI, a queue, workers, storage) spreads work across machines.
- **Specs as data:** turn a template's CONFIG into JSON or YAML, validate it with pydantic, and have
  the LLM fill it from the brief; `mv.EASE` and `mv.TRANSITIONS` look up curves and transitions by name.
- **Per-record renders:** `templates/batch_videos.py` shows the pattern: the record index travels in
  an environment variable (`MV_ROW`), so the parallel render workers rebuild the same video.
- **One engine copy per project** (`tools/new_project.py`) keeps old projects reproducible when the
  engine changes; `PYTHONPATH=/path/to/skill/engine` shares one copy across projects instead.
