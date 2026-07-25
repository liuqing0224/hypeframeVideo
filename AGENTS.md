# Repository Guidelines

## Project Structure & Module Organization

This repository builds batches of professional manga-style layered-pixel
HyperFrames videos. Reusable workflows live in `skills/<workflow>/`; each skill
keeps Python entry points in `scripts/`, contracts in `references/`, and schemas
or templates in `assets/`. Batch inputs belong in `batches/`.

Each `videos/<card-id>/` directory is an isolated production containing planning
Markdown, manifests, three modular HTML sub-compositions, motion sidecars, and QA
evidence. Shared integration tests are in `tests/`; aggregate review artifacts
are in `qa/`, and approved deliverables are promoted to `out/final/`. Read a
production's nested `AGENTS.md` before editing generated compositions.

## Required Skills

Use the project skills as the workflow authority instead of reimplementing their
contracts:

- `direct-professional-manga-video`: turn a child-authored three-beat story into
  a restrained multi-character manga script and nine editorial shots.
- `plan-task-card-video`: compile task cards into `BRIEF.md`, `SCRIPT.md`,
  `STORYBOARD.md`, `frame.md`, and `story-plan.json`.
- `generate-layered-pixel-assets`: generate versioned backdrop, environment,
  and character sheets.
- `process-layered-assets`: key, despill, split, trim, and inspect transparent
  layers.
- `compose-hyperframes-video`: build deterministic modular HyperFrames
  compositions with camera rigs, performance motion, captions, and root audio.
- `verify-hyperframes-video`: run structural checks, strict browser checks,
  snapshots, approval, render verification, and promotion.
- `batch-task-card-videos`: coordinate concurrent productions and resumable
  stage state.

Official `hyperframes`, `hyperframes-core`, `hyperframes-animation`,
`hyperframes-keyframes`, `hyperframes-cli`, `hyperframes-creative`, and
`media-use` skills remain authoritative for runtime and media rules.

## Production Contract

- Keep exactly three narrative scenes and asset groups: start, middle, and end.
- Compile each scene into exactly three editorial shots. A complete video has
  nine shots with wide, medium, and close framing variation.
- Do not create nine independent asset scenes. Reuse each scene's independent
  backdrop, rear, architecture, subject, and foreground layers through camera
  framing and visibility changes.
- Keep visual order
  `backdrop -> rear -> architecture -> tertiary -> secondary -> primary -> foreground -> captions`.
- Every sub-composition owns one synchronously created paused GSAP timeline.
  Its registration key must match `data-composition-id`.
- All driven audio belongs directly under the root composition. Sub-compositions
  must not contain audio or video elements.
- Timings are narration-driven. Synthesize speech first, then derive scene and
  shot durations; task cards must not prescribe a fixed final duration.
- Store shot timings relative to their scene and caption/audio timings relative
  to the root timeline.
- Use deterministic, seek-safe motion only. No clocks, autoplay, infinite
  animation, unseeded randomness, or network media during render.
- Source media is append-only. Retries use `-v2`, `-v3`, and later versions;
  never overwrite an accepted source asset.

## Build, Test, and Development Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
npm test
npm run pipeline:validate
npm run pipeline:prepare
npm run pipeline:scan
npm run pipeline:summary
```

The first three commands install pinned Python and Node dependencies. `npm test`
runs the pytest suite. Pipeline commands validate the batch, scaffold
productions, inspect readiness, and report progress.

Use the batch CLI for production work:

```bash
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py advance \
  --batch batches/ai-little-director-cards.json --workspace . --workers 4
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py preview \
  --batch batches/ai-little-director-cards.json --workspace . --base-port 3201
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py render \
  --batch batches/ai-little-director-cards.json --workspace . --workers 2 \
  --manual-approved --promote
```

Formal rendering requires the current batch's explicit Studio approval. The
approval must bind each production's composition SHA-256; never reuse an approval
from an earlier batch or composition revision. Limit high-quality rendering to
two concurrent workers.

## Coding Style & Naming Conventions

Use four-space indentation and standard Python conventions: `snake_case` for
functions and modules, `PascalCase` for classes, and uppercase names for
constants. Prefer `pathlib.Path`, explicit UTF-8 file I/O, type hints on reusable
helpers, and deterministic output. Format JSON with two-space indentation and
preserve established schema keys and card IDs. No repository-wide formatter is
configured, so match nearby code and keep changes narrowly scoped.

## Testing Guidelines

Tests use pytest 9. Name files `test_*.py` and tests `test_<behavior>`, placing
shared fixtures in `tests/conftest.py`. Add focused coverage for schema,
speaker-aware audio, caption timing, stage transitions, asset seams, composition
structure, shot continuity, approval freshness, or render verification when
those behaviors change.

All tests must pass. Composition changes also require, for every affected
production:

```bash
.venv/bin/python skills/verify-hyperframes-video/scripts/verify.py check \
  --production videos/<card-id>
```

Review nine shot-midpoint snapshots, transition evidence, and the animation map
before Studio approval. After render, verify full decode, 1920x1080, 30fps,
H.264, AAC, declared duration, frame count, subtitles, crop safety, direction,
layer occlusion, green spill, and sound-picture synchronization.

## Commit & Pull Request Guidelines

Recent history uses short, imperative subjects such as
`Add task-card HyperFrames video pipeline`; keep each commit focused. Pull
requests should identify affected card IDs and pipeline stages, summarize
validation performed, and link related issues. Include compact contact sheets or
preview screenshots for visual changes.

Do not commit source images, processed layers, audio stems, final MP4 files, raw
snapshot frames, render caches, machine-local logs, credentials, absolute local
paths, or local virtual environments. Commit reproducible code, skills, task
cards, planning documents, manifests, generated HTML/motion sidecars, compact QA
reports, and approved contact sheets only.
