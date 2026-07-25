---
name: process-layered-assets
description: Convert generated pixel-video backdrops, chroma-key environment sheets, and character sheets into validated production layers using Pillow and NumPy minimum-cost seams, soft keying, despill, trimming, contact sheets, and alpha QA. Use after all raw sources for a task-card production exist or when processed layers must be rebuilt.
---

# Process Layered Assets

Process immutable files from `assets/source/` into rebuildable files under `assets/processed/`.

## Workflow

1. Require every prompt queue item to be generated and registered.
2. Split environment and character sheets with foreground-avoiding seams.
3. Soft-key green, despill edges, trim with padding, and preserve alpha.
4. Resize backdrops to 1920x1080.
5. Write contact sheets and `qa/layer-processing.json`.
6. Fail on empty columns, foreground collisions, opaque corners, cropped borders, or implausible coverage.

```bash
python3 skills/process-layered-assets/scripts/process_assets.py --production videos/glowing-solar-system
```
