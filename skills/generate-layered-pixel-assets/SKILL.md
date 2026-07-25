---
name: generate-layered-pixel-assets
description: Build and execute built-in Imagegen prompt queues for layered pixel-collage videos, including character-free backdrops, three-column environment sheets, and three-column character sheets with versioned provenance. Use when a prepared task-card production needs missing visuals, prompt revisions, or source-direction inspection.
---

# Generate Layered Pixel Assets

Use the built-in Imagegen tool once per queue item. Never replace requested raster assets with SVG or HTML placeholders.

## Workflow

1. Read `references/prompt-contract.md`.
2. Generate `01-start` assets first.
3. For later scenes, pass the first approved backdrop and character sheet as visual references.
4. Copy the generated file into the queue item's exact target path.
5. Run `register_asset.py`; inspect the image before marking it approved.
6. Regenerate failures as `-v2`, `-v3`, and preserve earlier sources.

```bash
python3 skills/generate-layered-pixel-assets/scripts/build_prompt_queue.py --production videos/glowing-solar-system
python3 skills/generate-layered-pixel-assets/scripts/register_asset.py --production videos/glowing-solar-system --asset-id 01-start-backdrop
```

Do not combine distinct assets into one Imagegen request.
