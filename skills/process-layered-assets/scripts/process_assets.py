#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SEAM_PASS_RATIO = 0.02
SEAM_CLEAN_RATIO = 0.002


def cover(image: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / image.width, height / image.height)
    resized = image.convert("RGB").resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.NEAREST,
    )
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def remove_green(image: Image.Image) -> Image.Image:
    rgba = np.array(image.convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.int16)
    green_score = rgb[:, :, 1] - np.maximum(rgb[:, :, 0], rgb[:, :, 2])
    alpha = np.full(green_score.shape, 255, dtype=np.uint8)
    hard = (rgb[:, :, 1] > 105) & (green_score > 24)
    soft = (rgb[:, :, 1] > 80) & (green_score > 5) & ~hard
    alpha[hard] = 0
    alpha[soft] = np.clip(255 - (green_score[soft] - 5) * 13, 0, 255)
    rgba[:, :, 3] = alpha
    rgba[:, :, 1] = np.where(
        alpha < 240,
        np.minimum(rgba[:, :, 1], np.maximum(rgba[:, :, 0], rgba[:, :, 2]) + 18),
        rgba[:, :, 1],
    )
    return Image.fromarray(rgba)


def trim(image: Image.Image, padding: int = 18) -> Image.Image:
    alpha = np.array(image.getchannel("A"))
    ys, xs = np.where(alpha > 18)
    if not len(xs):
        raise ValueError("chroma-key result is empty")
    box = (
        max(0, int(xs.min()) - padding),
        max(0, int(ys.min()) - padding),
        min(image.width, int(xs.max()) + padding + 1),
        min(image.height, int(ys.max()) + padding + 1),
    )
    return image.crop(box)


def minimum_cost_seam(alpha: np.ndarray, expected_x: int, radius: int) -> tuple[np.ndarray, float]:
    height, width = alpha.shape
    left = max(1, expected_x - radius)
    right = min(width - 1, expected_x + radius + 1)
    xs = np.arange(left, right)
    foreground = alpha[:, left:right].astype(np.float32) / 255.0
    distance = np.abs(xs - expected_x)[None, :] / max(1, radius)
    cost = foreground * 10000.0 + distance * 0.25
    dp = np.empty_like(cost)
    parent = np.zeros(cost.shape, dtype=np.int8)
    dp[0] = cost[0]
    offsets = np.arange(-3, 4)
    for y in range(1, height):
        previous = dp[y - 1]
        candidates = np.full((len(offsets), len(xs)), np.inf, dtype=np.float32)
        for index, offset in enumerate(offsets):
            if offset < 0:
                candidates[index, -offset:] = previous[:offset]
            elif offset > 0:
                candidates[index, :-offset] = previous[offset:]
            else:
                candidates[index] = previous
        choice = np.argmin(candidates, axis=0)
        dp[y] = cost[y] + candidates[choice, np.arange(len(xs))]
        parent[y] = offsets[choice]
    local = int(np.argmin(dp[-1]))
    seam = np.empty(height, dtype=np.int32)
    seam[-1] = left + local
    for y in range(height - 1, 0, -1):
        local += int(parent[y, local])
        seam[y - 1] = left + local
    collision = float(np.mean(alpha[np.arange(height), seam] > 18))
    return seam, collision


def split_by_seams(sheet: Image.Image, count: int = 3) -> tuple[list[Image.Image], list[dict]]:
    keyed = remove_green(sheet)
    rgba = np.array(keyed)
    alpha = rgba[:, :, 3]
    cell_width = sheet.width / count
    radius = max(28, round(cell_width * 0.28))
    seams = []
    reports = []
    for index in range(1, count):
        expected = round(index * cell_width)
        seam, collision = minimum_cost_seam(alpha, expected, radius)
        seams.append(seam)
        reports.append(
            {
                "boundary": index,
                "expectedX": expected,
                "minX": int(seam.min()),
                "maxX": int(seam.max()),
                "foregroundCollisionRatio": round(collision, 6),
                "quality": (
                    "clean"
                    if collision <= SEAM_CLEAN_RATIO
                    else "shared-prop-contact"
                    if collision <= SEAM_PASS_RATIO
                    else "collision"
                ),
                "pass": collision <= SEAM_PASS_RATIO,
            }
        )
    xs = np.arange(sheet.width)[None, :]
    outputs = []
    for index in range(count):
        region = np.ones(alpha.shape, dtype=bool)
        if index > 0:
            region &= xs > seams[index - 1][:, None]
        if index < count - 1:
            region &= xs <= seams[index][:, None]
        isolated = rgba.copy()
        isolated[:, :, 3] = np.where(region, isolated[:, :, 3], 0)
        outputs.append(trim(Image.fromarray(isolated)))
    return outputs, reports


def inspect(path: Path, label: str) -> dict:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha = np.array(rgba.getchannel("A"))
        corners = [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])]
        coverage = float(np.mean(alpha > 20))
        border = np.concatenate((alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]))
        border_ratio = float(np.mean(border > 20))
        return {
            "label": label,
            "path": path.as_posix(),
            "width": rgba.width,
            "height": rgba.height,
            "corners": corners,
            "coverage": round(coverage, 6),
            "borderOpaqueRatio": round(border_ratio, 6),
            "pass": max(corners) == 0 and 0.01 <= coverage <= 0.95 and border_ratio < 0.28,
        }


def checker(size: tuple[int, int], cell: int = 16) -> Image.Image:
    image = Image.new("RGB", size, "#dedede")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill="#ffffff")
    return image


def contact_sheet(production: Path, groups: list[tuple[str, list[Path]]]) -> Path:
    tile_w, tile_h = 300, 310
    columns = 6
    rows = len(groups)
    sheet = Image.new("RGB", (tile_w * columns, tile_h * rows), "#242424")
    font = ImageFont.load_default()
    for row, (scene_id, paths) in enumerate(groups):
        for column, path in enumerate(paths):
            tile = checker((tile_w, tile_h))
            with Image.open(path) as image:
                rgba = image.convert("RGBA")
                rgba.thumbnail((270, 250), Image.Resampling.NEAREST)
                tile.paste(rgba, ((tile_w - rgba.width) // 2, 14), rgba)
            ImageDraw.Draw(tile).text(
                (10, 280),
                f"{scene_id}/{path.stem}",
                fill="#111111",
                font=font,
            )
            sheet.paste(tile, (column * tile_w, row * tile_h))
    target = production / "qa/contact-sheets/layers.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    return target


def update_status(production: Path, passed: bool, evidence: list[str]) -> None:
    path = production / "run-status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    status["stages"]["layer_processing"] = {
        "status": "complete" if passed else "failed",
        "evidence": evidence,
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    args = parser.parse_args()
    production = Path(args.production).resolve()
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    queue = [
        json.loads(line)
        for line in (production / "tmp/imagegen/prompt-queue.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not queue or any(item["status"] != "generated" for item in queue):
        raise ValueError("all Imagegen queue items must be generated and registered first")

    width = plan["metadata"]["width"]
    height = plan["metadata"]["height"]
    reports = []
    seam_reports = []
    contact_groups = []
    for scene in plan["scenes"]:
        assets = scene["assets"]
        backdrop_source = production / assets["backdropSource"]
        environment_source = production / assets["environmentSource"]
        characters_source = production / assets["charactersSource"]
        for source in (backdrop_source, environment_source, characters_source):
            if not source.is_file():
                raise FileNotFoundError(source)

        backdrop_target = production / assets["backdrop"]
        backdrop_target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(backdrop_source) as image:
            cover(image, width, height).save(backdrop_target)

        with Image.open(environment_source) as image:
            environment_layers, env_seams = split_by_seams(image.convert("RGBA"))
        with Image.open(characters_source) as image:
            character_layers, char_seams = split_by_seams(image.convert("RGBA"))
        seam_reports.extend(
            [
                {"sceneId": scene["id"], "kind": "environment", "seams": env_seams, "pass": all(item["pass"] for item in env_seams)},
                {"sceneId": scene["id"], "kind": "characters", "seams": char_seams, "pass": all(item["pass"] for item in char_seams)},
            ]
        )

        output_keys = ["rear", "architecture", "foreground", "primary", "secondary", "tertiary"]
        output_images = [*environment_layers, *character_layers]
        paths = []
        for key, image in zip(output_keys, output_images):
            target = production / assets[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target)
            report = inspect(target, key)
            report["sceneId"] = scene["id"]
            reports.append(report)
            paths.append(target)
        contact_groups.append((scene["id"], paths))

    contact = contact_sheet(production, contact_groups)
    passed = all(item["pass"] for item in reports) and all(item["pass"] for item in seam_reports)
    report_path = production / "qa/layer-processing.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "complete" if passed else "failed",
        "pass": passed,
        "seams": seam_reports,
        "layers": reports,
        "contactSheet": contact.relative_to(production).as_posix(),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = [
        report_path.relative_to(production).as_posix(),
        contact.relative_to(production).as_posix(),
    ]
    update_status(production, passed, evidence)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
