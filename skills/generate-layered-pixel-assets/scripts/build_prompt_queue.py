#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def shared_style(plan: dict) -> str:
    style = plan["style"]
    return (
        "Handmade layered pixel collage, crisp 16-bit pixel clusters, torn-paper silhouettes, "
        "subtle halftone grain, strong readable shapes, no smooth vector gradients. "
        f"Visual direction: {', '.join(style['visual'])}. "
        f"Palette: {', '.join(style['paletteWords'])}. "
        "Keep recurring characters, clothing, proportions, and color identity consistent across scenes."
    )


def backdrop_prompt(plan: dict, scene: dict) -> str:
    shot = scene["shot"]
    return f"""Use case: illustration-story
Asset type: 1920x1080 HyperFrames backdrop layer for scene {scene['id']}
Primary request: Create the empty atmospheric base for "{scene['title']}" at {plan['metadata']['location']}.
Scene/backdrop: {shot['rear']}. Show only sky, ground, distant atmosphere, paper texture, and broad light.
Style/medium: {shared_style(plan)}
Composition/framing: Wide 16:9. Preserve open central and lower space for architecture and people composited later.
Lighting/mood: {', '.join(plan['style']['musicMood'])}.
Constraints: No people, human silhouettes, main architecture, foreground objects, readable text, frames, logos, or watermark.
Avoid: photorealism, vector-flat art, modern objects inconsistent with the story, blurry atmospheric-only imagery.
"""


def environment_prompt(plan: dict, scene: dict) -> str:
    shot = scene["shot"]
    return f"""Use case: illustration-story
Asset type: three-column isolated environment layer sheet for scene {scene['id']}
Primary request: Create exactly three complete environment cutout layers in equal vertical columns, in this exact order:
Column 1 REAR: {shot['rear']}.
Column 2 ARCHITECTURE: {shot['architecture']}.
Column 3 FOREGROUND: {shot['foreground']}.
Style/medium: {shared_style(plan)}
Composition/framing: Each layer is isolated inside its own equal-width column with generous padding. Keep all edges and props visible.
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background.
Constraints: Continuous pure-green safety gutters at least 6% of canvas width between columns. No people, shadows, floor plane, text, labels, watermark, panel borders, or green-colored subjects.
Avoid: overlapping columns, cropped objects, gradients or texture in the green background, perspective floor, reflections.
"""


def characters_prompt(plan: dict, scene: dict) -> str:
    shot = scene["shot"]
    direction = scene["direction"]
    return f"""Use case: illustration-story
Asset type: three-column isolated action-character sheet for scene {scene['id']}
Primary request: Create exactly three full subjects in equal vertical columns, in this exact order:
Column 1 PRIMARY: {shot['primary']}.
Column 2 SECONDARY: {shot['secondary']}.
Column 3 TERTIARY: {shot['tertiary']}.
Narrative facing: subjects generally face {direction}.
Style/medium: {shared_style(plan)}
Composition/framing: Full body or complete animal/robot, action-specific pose, common ground line, generous head and foot clearance.
Scene/backdrop: perfectly flat solid #00ff00 chroma-key background.
Constraints: Continuous pure-green gutters at least 6% of canvas width. Keep every head, hand, foot, wing, tail, prop, robe, and tool visible. No scenery, shadows, floor, text, watermark, or green clothing.
Avoid: extra people, duplicate limbs, fused subjects, cropped props, panel borders, gradients or texture in the green background.
"""


def queue_items(production: Path, plan: dict) -> list[dict]:
    items = []
    first = plan["scenes"][0]
    first_refs = {
        "backdrop": first["assets"]["backdropSource"],
        "environment-sheet": first["assets"]["environmentSource"],
        "character-sheet": first["assets"]["charactersSource"],
    }
    for scene in plan["scenes"]:
        specs = (
            ("backdrop", scene["assets"]["backdropSource"], backdrop_prompt(plan, scene)),
            ("environment-sheet", scene["assets"]["environmentSource"], environment_prompt(plan, scene)),
            ("character-sheet", scene["assets"]["charactersSource"], characters_prompt(plan, scene)),
        )
        for kind, target, prompt in specs:
            refs = []
            if scene["index"] > 1:
                if kind == "backdrop":
                    refs = [first_refs["backdrop"]]
                elif kind == "environment-sheet":
                    refs = [first_refs["backdrop"], first_refs["environment-sheet"]]
                else:
                    refs = [first_refs["character-sheet"]]
            items.append(
                {
                    "assetId": f"{scene['id']}-{kind.replace('-sheet', '')}",
                    "sceneId": scene["id"],
                    "kind": kind,
                    "targetPath": target,
                    "referencePaths": refs,
                    "prompt": prompt,
                    "status": "pending",
                    "version": 1,
                }
            )
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    args = parser.parse_args()
    production = Path(args.production).resolve()
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    items = queue_items(production, plan)
    queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items),
        encoding="utf-8",
    )
    print(queue_path)


if __name__ == "__main__":
    main()
