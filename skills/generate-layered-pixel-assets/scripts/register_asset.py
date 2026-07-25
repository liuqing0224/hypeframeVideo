#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def read_queue(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_queue(path: Path, items: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items),
        encoding="utf-8",
    )


def update_status(production: Path, queue: list[dict]) -> None:
    status_path = production / "run-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    complete = bool(queue) and all(item["status"] == "generated" for item in queue)
    evidence = [item["targetPath"] for item in queue if item["status"] == "generated"]
    status["stages"]["visual_generation"] = {
        "status": "complete" if complete else "pending",
        "evidence": evidence,
    }
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--asset-id", required=True)
    args = parser.parse_args()
    production = Path(args.production).resolve()
    queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
    queue = read_queue(queue_path)
    matches = [item for item in queue if item["assetId"] == args.asset_id]
    if len(matches) != 1:
        raise ValueError(f"unknown asset id: {args.asset_id}")
    item = matches[0]
    target = production / item["targetPath"]
    if not target.is_file():
        raise FileNotFoundError(target)
    with Image.open(target) as image:
        item["width"] = image.width
        item["height"] = image.height
        item["mode"] = image.mode
    item["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    item["status"] = "generated"
    write_queue(queue_path, queue)

    manifest_path = production / "asset-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset_matches = [asset for asset in manifest["assets"] if asset["id"] == args.asset_id]
    if len(asset_matches) != 1:
        raise ValueError(f"asset manifest does not contain {args.asset_id}")
    asset = asset_matches[0]
    asset.update(
        {
            "status": "generated",
            "width": item["width"],
            "height": item["height"],
            "mode": item["mode"],
            "sha256": item["sha256"],
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_status(production, queue)
    print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
