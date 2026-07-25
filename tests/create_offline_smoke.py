#!/usr/bin/env python3
import asyncio
import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = REPO_ROOT / "batches/ai-little-director-cards.json"
OUTPUT_ROOT = REPO_ROOT / "qa/offline-smoke"


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


plan_module = load_script(
    "smoke_compile_plan",
    "skills/plan-task-card-video/scripts/compile_plan.py",
)
audio_module = load_script(
    "smoke_generate_audio",
    "skills/batch-task-card-videos/scripts/generate_audio.py",
)
compose_module = load_script(
    "smoke_compose",
    "skills/compose-hyperframes-video/scripts/compose.py",
)
verify_module = load_script(
    "smoke_verify",
    "skills/verify-hyperframes-video/scripts/verify.py",
)


def scaffold(production: Path) -> None:
    production.mkdir(parents=True, exist_ok=True)
    package = {
        "name": f"offline-smoke-{production.name}",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "npx --yes hyperframes@0.7.71 preview",
            "check": "npx --yes hyperframes@0.7.71 check",
            "render": "npx --yes hyperframes@0.7.71 render",
        },
    }
    (production / "package.json").write_text(
        json.dumps(package, indent=2) + "\n",
        encoding="utf-8",
    )
    (production / "meta.json").write_text(
        json.dumps({"id": production.name, "name": production.name}, indent=2) + "\n",
        encoding="utf-8",
    )
    (production / "hyperframes.json").write_text(
        json.dumps(
            {
                "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                "paths": {
                    "blocks": "compositions",
                    "components": "compositions/components",
                    "assets": "assets",
                },
                "media": {"autoProxy": True},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def backdrop(path: Path, palette: list[str], scene_index: int) -> None:
    image = Image.new("RGB", (1920, 1080), palette[0])
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 610, 1919, 1079), fill=palette[1])
    draw.rectangle((0, 860, 1919, 1079), fill=palette[2])
    for index in range(18):
        size = 18 + (index % 4) * 8
        x = (index * 127 + scene_index * 73) % 1880
        y = 60 + (index * 83) % 470
        draw.rectangle((x, y, x + size, y + size), fill=palette[3])
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def transparent_layer(
    path: Path,
    color: str,
    layer_index: int,
    scene_index: int,
) -> None:
    width, height = (720, 720) if layer_index < 3 else (420, 680)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = 28 + layer_index * 5
    if layer_index % 3 == 0:
        draw.polygon(
            [
                (width // 2, inset),
                (width - inset, height - inset),
                (inset, height - inset),
            ],
            fill=color,
        )
    elif layer_index % 3 == 1:
        draw.rectangle(
            (inset, height // 4, width - inset, height - inset),
            fill=color,
        )
        draw.rectangle(
            (width // 3, inset, width * 2 // 3, height // 2),
            fill=color,
        )
    else:
        draw.ellipse((inset, inset, width - inset, height - inset), fill=color)
    pixel = 10 + scene_index * 4
    draw.rectangle((inset, inset, inset + pixel, inset + pixel), fill="#ffffff")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def make_assets(production: Path, plan: dict, palette: list[str]) -> None:
    keys = ("rear", "architecture", "foreground", "primary", "secondary", "tertiary")
    colors = [palette[1], palette[2], palette[3], "#f1c84a", "#51a7d8", "#e85656"]
    for scene_index, scene in enumerate(plan["scenes"]):
        backdrop(production / scene["assets"]["backdrop"], palette, scene_index)
        for layer_index, (key, color) in enumerate(zip(keys, colors)):
            transparent_layer(
                production / scene["assets"][key],
                color,
                layer_index,
                scene_index,
            )


def complete_fixture_stages(production: Path) -> None:
    status_path = production / "run-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    for stage in ("visual_generation", "layer_processing"):
        status["stages"][stage] = {
            "status": "complete",
            "evidence": ["programmatic offline smoke fixture"],
        }
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def build(card_id: str, palette: list[str]) -> dict:
    production = OUTPUT_ROOT / card_id
    scaffold(production)
    plan = plan_module.compile_card(BATCH_PATH, card_id, production)
    make_assets(production, plan, palette)
    complete_fixture_stages(production)
    await audio_module.generate(production, "silent")
    compose_module.compose(production, adopt=True)
    report = verify_module.check(production, run_hyperframes=True)
    return {
        "id": card_id,
        "production": production.relative_to(REPO_ROOT).as_posix(),
        "pass": report["pass"],
        "verification": f"qa/offline-smoke/{card_id}/qa/verification.json",
        "snapshots": f"qa/offline-smoke/{card_id}/qa/scene-midpoints",
    }


async def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    specifications = [
        (
            "guangzhou-tower-cloud-team",
            ["#5ca6c4", "#9ed9e6", "#29526e", "#e94d3d"],
        ),
        (
            "glowing-solar-system",
            ["#071b2e", "#123e62", "#07101f", "#ffc857"],
        ),
    ]
    reports = []
    for card_id, palette in specifications:
        reports.append(await build(card_id, palette))
    summary = {
        "schemaVersion": 1,
        "kind": "offline-hyperframes-smoke",
        "pass": all(item["pass"] for item in reports),
        "productions": reports,
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
