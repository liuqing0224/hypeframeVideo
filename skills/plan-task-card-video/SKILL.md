---
name: plan-task-card-video
description: Compile a structured child task card into a deterministic three-scene, nine-shot professional manga production plan with multi-character performance script, BRIEF.md, SCRIPT.md, STORYBOARD.md, frame.md, asset inventory, and mutable run state. Use when starting a task-card video or rebuilding planning artifacts before asset generation.
---

# Plan Task Card Video

Compile story intent before generating media. Treat `story-plan.json` as pre-audio truth and `production-manifest.json` as the post-TTS timing contract.

## Workflow

1. Validate exactly three story beats and either three explicit shot hints or the deterministic visual fallback.
2. Read `../direct-professional-manga-video/references/directing-contract.md` when the card contains a `manga` block or the requested result is a professional manga video.
3. Map start, middle, and end to scene IDs `01-start`, `02-middle`, and `03-end`, with three internal shots per scene.
4. Use explicit `manga.scene_scripts` when present. Otherwise bind the complete child-authored beat to the middle shot exactly once; keep the establishing and reaction shots silent.
5. Preserve authored facts and character identities. Do not split, paraphrase, or invent fallback narration.
6. Write HyperFrames brief, performance script, nine-shot storyboard, design truth, asset inventory, prompt queue inputs, and run state.
7. Leave final duration unresolved until the audio stage measures real speech and applies pacing handles.

```bash
python3 skills/plan-task-card-video/scripts/compile_plan.py \
  --batch batches/ai-little-director-cards.json \
  --card-id glowing-solar-system \
  --output videos/glowing-solar-system
```

Read `references/production-contract.md` before changing a consumer.
