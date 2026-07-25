# Repository Guidelines

## Project Structure & Module Organization

This repository builds batches of layered-pixel HyperFrames videos. Reusable workflows live in `skills/<workflow>/`; each skill keeps its Python entry points in `scripts/`, contracts in `references/`, and schemas or templates in `assets/`. Batch inputs belong in `batches/`, while `videos/<card-id>/` contains one isolated production with planning Markdown, manifests, HTML compositions, and QA evidence. Shared integration tests are in `tests/`; aggregate review artifacts are in `qa/`, and approved deliverables are promoted to `out/final/`. Read a production's nested `AGENTS.md` before editing its compositions.

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

The first three commands install the pinned Python and Node dependencies. `npm test` runs the pytest suite. Pipeline commands validate the batch, scaffold productions, inspect stage readiness, and report progress. To preview or verify one video, run `npm run dev` or `npm run check` from `videos/<card-id>/`. Rendering requires an approved Studio preview.

## Coding Style & Naming Conventions

Use four-space indentation and standard Python conventions: `snake_case` for functions and modules, `PascalCase` for classes, and uppercase names for constants. Prefer `pathlib.Path`, explicit UTF-8 file I/O, type hints on reusable helpers, and deterministic output. Format JSON with two-space indentation and preserve established schema keys and card IDs. No repository-wide formatter is configured, so match nearby code and keep changes narrowly scoped.

## Testing Guidelines

Tests use pytest 9. Name files `test_*.py` and tests `test_<behavior>`, placing shared fixtures in `tests/conftest.py`. Add focused coverage for schema, stage-transition, asset, or composition behavior you change. There is no numeric coverage threshold; all tests must pass. Composition changes also require the video's `npm run check`, with warnings reviewed before render.

## Commit & Pull Request Guidelines

Recent history uses short, imperative subjects such as `Add task-card HyperFrames video pipeline`; keep each commit focused. Pull requests should identify affected card IDs and pipeline stages, summarize validation performed, and link related issues. Include contact sheets or preview screenshots for visual changes. Do not commit ignored generated media, renders, caches, credentials, or local virtual environments.
