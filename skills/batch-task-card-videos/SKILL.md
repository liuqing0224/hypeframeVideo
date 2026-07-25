---
name: batch-task-card-videos
description: Orchestrate concurrent batches of child task-card stories into isolated layered-pixel HyperFrames productions, including planning, Imagegen prompt queues, transparent layer processing, narration-driven timing, composition, checks, preview approval, retries, and final delivery. Use when Codex must generate or resume one or more videos from the project task-card JSON format.
---

# Batch Task Card Videos

Keep each card in `videos/<card-id>/`. Workers may run different productions concurrently, but a production has one owner and one stage writer.

## Required Reading

- Read `references/batch-contract.md` before editing a batch.
- Read `references/stage-protocol.md` before executing or resuming.
- Load the child skill that owns the current stage.

## Workflow

1. Validate the task-card batch.
2. Prepare every production and write planning documents plus Imagegen queues.
3. Generate each queued source with the built-in Imagegen tool. Preserve versioned raw files.
4. Process layers and generate audio concurrently across ready productions.
5. Compose modular HyperFrames projects and run checks.
6. Start Studio previews and wait for final approval.
7. Render with at most two concurrent projects, verify, and promote passing outputs.

## Commands

```bash
python3 skills/batch-task-card-videos/scripts/pipeline.py validate --batch batches/ai-little-director-cards.json
python3 skills/batch-task-card-videos/scripts/pipeline.py prepare --batch batches/ai-little-director-cards.json --workspace .
python3 skills/batch-task-card-videos/scripts/pipeline.py scan --batch batches/ai-little-director-cards.json --workspace .
python3 skills/batch-task-card-videos/scripts/pipeline.py advance --batch batches/ai-little-director-cards.json --workspace . --workers 4
python3 skills/batch-task-card-videos/scripts/pipeline.py summary --batch batches/ai-little-director-cards.json --workspace .
```

Do not call `render` before the user approves the final Studio previews.
