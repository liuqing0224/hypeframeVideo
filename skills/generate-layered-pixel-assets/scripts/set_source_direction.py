#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--source-direction", choices=["left", "right"], required=True)
    parser.add_argument("--role", choices=["primary", "secondary", "tertiary"])
    args = parser.parse_args()
    production = Path(args.production).resolve()
    for name in ("story-plan.json", "production-manifest.json"):
        path = production / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        matches = [scene for scene in payload["scenes"] if scene["id"] == args.scene_id]
        if len(matches) != 1:
            raise ValueError(f"{name}: unknown scene {args.scene_id}")
        scene = matches[0]
        if args.role:
            source_directions = scene.setdefault(
                "sourceDirections",
                {
                    "primary": scene.get("sourceDirection", scene["direction"]),
                    "secondary": scene.get("sourceDirection", scene["direction"]),
                    "tertiary": scene.get("sourceDirection", scene["direction"]),
                },
            )
            source_directions[args.role] = args.source_direction
        else:
            scene["sourceDirection"] = args.source_direction
            scene["sourceDirections"] = {
                "primary": args.source_direction,
                "secondary": args.source_direction,
                "tertiary": args.source_direction,
            }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    role = args.role or "all"
    print(f"{args.scene_id}/{role}: sourceDirection={args.source_direction}")


if __name__ == "__main__":
    main()
