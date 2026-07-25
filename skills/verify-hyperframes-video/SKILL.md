---
name: verify-hyperframes-video
description: Validate story-specific professional manga-style HyperFrames task-card videos with nine-shot and director-profile checks, batch differentiation gates, role-aware focus, authored ending evidence, blocking bounds, strict browser checks, snapshots, animation maps, hash-bound approval, render verification, and promotion. Use when compositions are ready for QA or when a batch still looks template-driven.
---

# Verify HyperFrames Video

Read `/hyperframes-cli` before running commands. A successful check is not render approval.

## Workflow

1. Verify processed-layer and audio reports plus three distinct subject and
   environment blocking states per scene.
2. Verify every shot has a story-specific signature, the end scene implements
   its ending mode, and semantic speakers resolve to the intended asset slots.
3. Run `lint` during iteration.
4. Run strict `check` with snapshots, transition samples, and frame checks.
5. Capture all nine shot midpoints. For batches, compare contact sheets and
   reject identical signature sequences, ending compositions, caption shapes,
   recurring motifs, or camera curves.
6. Review the animation map and write manual review evidence.
7. Start Studio and wait for explicit final approval.
8. After approval, render at high quality and verify the encoded MP4 with FFprobe.

```bash
.venv/bin/python skills/verify-hyperframes-video/scripts/verify.py check --production videos/glowing-solar-system
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py preview --batch batches/ai-little-director-cards.json --workspace .
.venv/bin/python skills/verify-hyperframes-video/scripts/verify.py render --production videos/glowing-solar-system --video videos/glowing-solar-system/renders/glowing-solar-system.mp4
```

Record preview approval through the batch pipeline only after the user explicitly approves the Studio views.
