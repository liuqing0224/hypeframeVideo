---
name: plan-task-card-video
description: Compile a structured child task card into a deterministic three-scene HyperFrames production plan with BRIEF.md, SCRIPT.md, STORYBOARD.md, frame.md, layer prompts, asset inventory, and mutable run state. Use when starting a task-card video or rebuilding planning artifacts before asset generation.
---

# Plan Task Card Video

Compile story intent before generating media. Treat `story-plan.json` as pre-audio truth and `production-manifest.json` as the post-TTS timing contract.

## Workflow

1. Validate exactly three story beats and three shot hints.
2. Map start, middle, and end to scene IDs `01-start`, `02-middle`, and `03-end`.
3. Preserve the child-authored beat as narration; do not add invented facts.
4. Write HyperFrames brief, script, storyboard, design truth, asset inventory, prompt queue inputs, and run state.
5. Leave scene duration unresolved until the audio stage measures real speech.

```bash
python3 skills/plan-task-card-video/scripts/compile_plan.py \
  --batch batches/ai-little-director-cards.json \
  --card-id glowing-solar-system \
  --output videos/glowing-solar-system
```

Read `references/production-contract.md` before changing a consumer.
