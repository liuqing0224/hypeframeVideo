---
name: plan-task-card-video
description: Compile a structured child task card into a deterministic, story-specific three-scene, nine-shot professional manga plan with a director profile, unique shot signatures and ending, multi-character script, per-shot blocking, planning documents, asset inventory, and mutable run state. Use when starting a task-card video or rebuilding planning artifacts before asset generation.
---

# Plan Task Card Video

Compile story intent before generating media. Treat `story-plan.json` as pre-audio truth and `production-manifest.json` as the post-TTS timing contract.

## Workflow

1. Validate exactly three story beats and either three explicit shot hints or the deterministic visual fallback.
2. Read `../direct-professional-manga-video/references/directing-contract.md` when the card contains a `manga` block or the requested result is a professional manga video.
3. Map start, middle, and end to scene IDs `01-start`, `02-middle`, and
   `03-end`, with three internal shots per scene.
4. Compile `manga.director_profile`: preserve its story engine, assign all nine
   shot signatures, carry the ending mode into the end scene, and apply any
   per-scene semantic-to-asset `scene_role_maps`.
5. Use explicit `manga.scene_scripts` when present. Otherwise bind the complete child-authored beat to the middle shot exactly once; keep the establishing and reaction shots silent.
6. Preserve authored facts and character identities. Do not split, paraphrase, or invent fallback narration.
7. Write transform-relative blocking for all subjects and environment layers in every shot; mirror horizontal intent with narrative direction.
8. Write HyperFrames brief, performance script, nine-shot storyboard, design truth, asset inventory, prompt queue inputs, and run state.
9. Leave final duration unresolved until the audio stage measures real speech and applies pacing handles.

For a multi-card batch, assert that director IDs, signature sets, visual
grammars, and ending modes are not identical across cards.

```bash
python3 skills/plan-task-card-video/scripts/compile_plan.py \
  --batch batches/ai-little-director-cards.json \
  --card-id glowing-solar-system \
  --output videos/glowing-solar-system
```

Read `references/production-contract.md` before changing a consumer.
