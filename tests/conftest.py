import importlib.util
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def scripts():
    return {
        "plan": load_script(
            "compile_plan",
            "skills/plan-task-card-video/scripts/compile_plan.py",
        ),
        "audio": load_script(
            "generate_audio",
            "skills/batch-task-card-videos/scripts/generate_audio.py",
        ),
        "layers": load_script(
            "process_assets",
            "skills/process-layered-assets/scripts/process_assets.py",
        ),
        "queue": load_script(
            "build_prompt_queue",
            "skills/generate-layered-pixel-assets/scripts/build_prompt_queue.py",
        ),
        "compose": load_script(
            "compose",
            "skills/compose-hyperframes-video/scripts/compose.py",
        ),
        "verify": load_script(
            "verify",
            "skills/verify-hyperframes-video/scripts/verify.py",
        ),
        "pipeline": load_script(
            "pipeline",
            "skills/batch-task-card-videos/scripts/pipeline.py",
        ),
    }


def make_layer(path: Path, color: str, size=(420, 620)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((36, 28, size[0] - 36, size[1] - 28), fill=color)
    image.save(path)


def make_backdrop(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1920, 1080), color).save(path)


@pytest.fixture
def synthetic_production(tmp_path, scripts):
    production = tmp_path / "synthetic"
    batch_path = REPO_ROOT / "batches/ai-little-director-cards.json"
    plan = scripts["plan"].compile_card(
        batch_path,
        "guangzhou-tower-cloud-team",
        production,
    )
    timed = []
    cursor = 0.0
    for scene in plan["scenes"]:
        duration = 4.0
        make_backdrop(production / scene["assets"]["backdrop"], "#527fa3")
        for index, key in enumerate(
            ("rear", "architecture", "foreground", "primary", "secondary", "tertiary")
        ):
            make_layer(
                production / scene["assets"][key],
                ("#445566", "#aa5533", "#ded9c8", "#f0c940", "#4fa6d8", "#e84d4d")[index],
            )
        timed.append(
            {
                **scene,
                "startSeconds": cursor,
                "durationSeconds": duration,
                "startFrame": round(cursor * 30),
                "durationInFrames": 120,
                "narrationPath": f"assets/audio/segments/{scene['id']}.wav",
                "captionFrom": cursor + 0.45,
                "captionTo": cursor + duration - 0.35,
                "words": [],
            }
        )
        cursor += duration
    manifest = scripts["audio"].build_manifest(plan, timed)
    (production / "production-manifest.json").write_text(
        __import__("json").dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return production
