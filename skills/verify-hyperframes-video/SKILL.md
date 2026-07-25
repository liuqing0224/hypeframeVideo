---
name: verify-hyperframes-video
description: Validate professional manga-style HyperFrames task-card videos with structural nine-shot checks, cue and speaker checks, strict browser checks, shot and transition snapshots, animation-map review, hash-bound Studio approval, high-quality render, FFprobe verification, evidence frames, and promotion. Use when a composed production is ready for QA, preview, rendering, or failure diagnosis.
---

# Verify HyperFrames Video

Read `/hyperframes-cli` before running commands. A successful check is not render approval.

## Workflow

1. Verify processed-layer and audio reports.
2. Run `lint` during iteration.
3. Run strict `check` with snapshots, transition samples, and frame checks.
4. Capture every scene midpoint and inspect the contact sheet.
5. Review the animation map and write manual review evidence.
6. Start Studio and wait for explicit final approval.
7. After approval, render at high quality and verify the encoded MP4 with FFprobe.

```bash
.venv/bin/python skills/verify-hyperframes-video/scripts/verify.py check --production videos/glowing-solar-system
.venv/bin/python skills/batch-task-card-videos/scripts/pipeline.py preview --batch batches/ai-little-director-cards.json --workspace .
.venv/bin/python skills/verify-hyperframes-video/scripts/verify.py render --production videos/glowing-solar-system --video videos/glowing-solar-system/renders/glowing-solar-system.mp4
```

Record preview approval through the batch pipeline only after the user explicitly approves the Studio views.
