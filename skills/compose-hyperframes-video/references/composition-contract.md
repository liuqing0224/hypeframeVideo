# Composition Contract

- Use a modular HyperFrames project: thin `index.html` plus three template-wrapped sub-compositions.
- Every root is 1920x1080 and has a static `data-duration`.
- Every composition registers exactly one paused, synchronous GSAP timeline.
- Slot ID, sub-composition ID, and timeline key must match.
- Audio elements are direct children of the main composition root.
- Use local assets only; no render-time network.
- Visual order is backdrop, rear, architecture, subjects, foreground, captions.
- Subject base boxes stay safe, but each shot applies a separate blocking wrapper
  for `x`, `y`, `scale`, and `opacity`; rear, architecture, and foreground
  receive independent shot-relative parallax.
- Keep entrance and micro-performance transforms inside the blocking wrapper so
  timelines do not overwrite one another.
- Motion is deterministic, seek-safe, transform/opacity based, and finite.
