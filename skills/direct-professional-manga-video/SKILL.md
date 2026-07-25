---
name: direct-professional-manga-video
description: Direct child-authored task-card stories as distinct professional three-scene, nine-shot manga videos with a story engine, unique shot signatures and ending, concise dialogue, purposeful framing, role-aware blocking, continuity, pacing, and factual restraint. Use when authoring or reviewing manga task cards, upgrading three beats into a motion-comic sequence, or diagnosing repetitive narration, fixed staging, generic endings, and template-driven batch output.
---

# Direct Professional Manga Video

Turn three child-authored story beats into nine editorial shots without changing the story's facts. Keep the three scenes as narrative and asset groups; treat their internal shots as the performance and editing layer.

## Required Reading

Read `references/directing-contract.md` before authoring a `manga` block or approving a compiled plan.

## Workflow

1. Lock the original `beats`, protagonists, place, facts, visual style, and director intent.
2. Define one `director_profile` from the actual conflict: story engine,
   recurring visual motif, nine shot signatures, and a story-resolving ending.
3. Build three shots for each beat. Use establish/action/reaction only as
   narrative functions; do not reuse one visual treatment across stories.
4. Add two to four short performance lines per scene. Use narration for necessary causality and dialogue for decisions, discoveries, coordination, and emotional payoff.
5. Give every line a stable semantic role and speaker. When generated sheet
   columns differ, write `scene_role_maps` instead of changing speaker identity.
6. Track costume, signature colors, held props, screen direction, and emotional state across all nine shots.
7. Re-block every shot: place each role and environment layer for that framing, then define one motivated travel action.
8. Set relative pacing with `compact`, `standard`, `cinematic`, or `gentle`; never author a final video duration.
9. Compile with `plan-task-card-video`, then inspect `SCRIPT.md` and all nine shot entries in `STORYBOARD.md`.

## Non-Negotiable Gates

- Preserve exactly three story scenes and nine ordered shots.
- Assign every explicit script line to exactly one shot.
- For a legacy card without `manga.scene_scripts`, place the complete original beat on the middle shot exactly once. Keep the other two shots silent.
- Use at least two character roles across the full script; do not turn every line into narrator exposition.
- Keep dialogue performable, specific, and non-redundant with adjacent narration.
- Reject a nine-shot plan when character and environment positions remain identical across shots.
- Reject a multi-video batch when color and transition changes are its only
  differences. Camera behavior, panel geometry, climax, and ending must differ.
- Reject a generic ensemble ending when the task card promises a photograph,
  handoff, chain reaction, transformation, departure, or another visible payoff.
- Reject unexplained changes in identity, clothing, props, time, location, or factual claims.
- Leave final timings to measured speech plus pacing handles.

## Handoff

Treat `story-plan.json` as pre-audio directing truth. Keep its three `scenes` compatible with existing asset consumers and use each scene's three `shots` as the editorial contract for future audio and composition consumers.
