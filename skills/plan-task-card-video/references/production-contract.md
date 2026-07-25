# Production Contracts

`story-plan.json` exists before audio and contains narrative, design, asset, and motion intent without final timing.

Every planned shot contains a `blocking` object for subject transforms,
environment parallax, and motivated in-shot travel. These values are
transform-relative to the scene's safe base boxes and remain timing-free until
audio resolves shot durations.

`production-manifest.json` is written after narration is measured. It contains:

- static width, height, fps, duration seconds, and frame count;
- ordered scenes with static start and duration seconds;
- processed visual-layer paths and source directions;
- narration, music, SFX, caption, and deliverable paths.

`run-status.json` is the only mutable stage-state file. Do not put completion state into either plan or manifest.
