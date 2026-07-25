---
name: batch-task-card-videos
description: Orchestrate concurrent batches of child task-card stories into isolated, story-specific professional manga-style layered-pixel HyperFrames productions, including distinct director profiles, nine-shot signatures, authored endings, per-shot blocking, Imagegen assets, audio, composition, checks, approval, retries, and delivery. Use when Codex must generate or resume one or more videos from the project task-card JSON format without making the batch look template-driven.
---

# Batch Task Card Videos

Keep each card in `videos/<card-id>/`. Workers may run different productions concurrently, but a production has one owner and one stage writer.

## Required Reading

- Read `references/batch-contract.md` before editing a batch.
- Read `references/stage-protocol.md` before executing or resuming.
- Use `../direct-professional-manga-video/SKILL.md` to author or review each card's multi-character manga script.
- Load the child skill that owns the current stage.

## Workflow

1. Validate the task-card batch and its optional `manga` directing blocks.
   Require distinct `director_profile.id`, `shot_signatures`, and `ending_mode`
   values when multiple cards belong to one creative batch.
2. Direct each card from its own story engine as three story scenes and nine
   editorial shots. Vary camera language, panel grammar, recurring motif,
   climax construction, ending, and subject/environment blocking.
3. Generate each queued source with the built-in Imagegen tool. Preserve versioned raw files.
4. Process layers and generate audio concurrently across ready productions.
5. Compose modular HyperFrames projects and run checks.
6. Start Studio previews and wait for final approval.
7. Render with at most two concurrent projects, verify and promote passing
   outputs, then assemble one batch-level nine-shot render contact sheet.

Compare the batch contact sheet before approval. Reject a batch when videos
share the same nine signatures, ending composition, caption geometry, or
camera curve even if their palettes and assets differ.

## Commands

```bash
python3 skills/batch-task-card-videos/scripts/pipeline.py validate --batch batches/ai-little-director-cards.json
python3 skills/batch-task-card-videos/scripts/pipeline.py prepare --batch batches/ai-little-director-cards.json --workspace .
python3 skills/batch-task-card-videos/scripts/pipeline.py scan --batch batches/ai-little-director-cards.json --workspace .
python3 skills/batch-task-card-videos/scripts/pipeline.py advance --batch batches/ai-little-director-cards.json --workspace . --workers 4
python3 skills/batch-task-card-videos/scripts/pipeline.py summary --batch batches/ai-little-director-cards.json --workspace .
```

Do not call `render` before the user approves the final Studio previews.
