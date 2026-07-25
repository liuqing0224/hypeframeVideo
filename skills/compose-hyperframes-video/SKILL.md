---
name: compose-hyperframes-video
description: Assemble a timed task-card production into a deterministic modular HyperFrames project with three GSAP sub-compositions, root-owned audio and captions, style-mapped transitions, motion assertions, and local frozen assets. Use after processed layers and measured audio exist or when the composition must be rebuilt.
---

# Compose HyperFrames Video

Load `/hyperframes-core`, `/hyperframes-animation`, `/hyperframes-creative`, and `/media-use` before changing composition behavior.

## Workflow

1. Require `production-manifest.json`, processed layers, and `audio_meta.json`.
2. Copy a local GSAP runtime into `vendor/`.
3. Write three template-wrapped sub-compositions and matching `.motion.json` files.
4. Write a thin `index.html` with scene slots plus direct-root narration, music, SFX, captions, and transitions.
5. Adopt frozen media into the project `.media` ledger.
6. Run HyperFrames lint after the first full pass.

```bash
python3 skills/compose-hyperframes-video/scripts/compose.py --production videos/glowing-solar-system
```

Never use render-time network access, clocks, unseeded randomness, autoplay, or infinite repeats.
