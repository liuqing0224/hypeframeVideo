---
name: compose-hyperframes-video
description: Assemble a timed task-card production into a deterministic, story-specific professional manga-style HyperFrames project with three GSAP sub-compositions, nine signed editorial shots, authored ending motifs, role-aware blocking, distinct visual grammar, semantic audio, motion assertions, and frozen assets. Use after processed layers and measured audio exist or when a generic-looking composition must be rebuilt.
---

# Compose HyperFrames Video

Load `/hyperframes-core`, `/hyperframes-animation`, `/hyperframes-creative`, and `/media-use` before changing composition behavior.

## Workflow

1. Require `production-manifest.json`, processed layers, and `audio_meta.json`.
2. Copy a local GSAP runtime into `vendor/`.
3. Read `style.visualGrammar` and `manga.directorProfile`; compile every shot's
   signature, subject blocking, environment parallax, travel, camera, panel
   geometry, and micro-performance into three sub-compositions and motion maps.
4. Render the declared end-scene `endingMode` as a visible story payoff. Do not
   substitute the same particle burst or closing tableau for every story.
5. Write a thin `index.html` with scene slots plus direct-root narration, music, SFX, captions, and transitions. Let visual grammar change caption geometry.
6. Adopt frozen media into the project `.media` ledger.
7. Run HyperFrames lint after the first full pass.

```bash
python3 skills/compose-hyperframes-video/scripts/compose.py --production videos/glowing-solar-system
```

Never use render-time network access, clocks, unseeded randomness, autoplay, or infinite repeats.
