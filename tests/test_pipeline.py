import concurrent.futures
import copy
import json
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
BATCH_PATH = REPO_ROOT / "batches/ai-little-director-cards.json"
SCHEMA_PATH = (
    REPO_ROOT
    / "skills/batch-task-card-videos/assets/task-card-batch.schema.json"
)


def test_task_card_schema_and_optional_shot_hints(scripts):
    batch = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(batch)
    without_hints = copy.deepcopy(batch)
    del without_hints["cards"][0]["shot_hints"]
    jsonschema.Draft202012Validator(schema).validate(without_hints)
    plan = scripts["plan"].build_plan(
        without_hints["defaults"],
        without_hints["cards"][0],
    )
    assert len(plan["scenes"]) == 3
    assert plan["scenes"][0]["shot"]["direction"] == "right"
    assert not any("duration" in card for card in batch["cards"])


def test_narration_duration_quantization(scripts):
    quantize = scripts["audio"].quantized_scene_duration
    assert quantize(0.1) == 4.0
    assert quantize(2.8) == 4.0
    assert quantize(3.01) == 4.5
    assert quantize(7.31) == 9.0


def test_green_sheet_minimum_cost_split(scripts, tmp_path):
    image = Image.new("RGB", (900, 420), "#00ff00")
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 55, 250, 380), fill="#f3c645")
    draw.ellipse((355, 70, 545, 370), fill="#396fb3")
    draw.polygon([(650, 380), (750, 45), (845, 380)], fill="#be3f42")
    path = tmp_path / "sheet.png"
    image.save(path)
    layers, seams = scripts["layers"].split_by_seams(image)
    assert len(layers) == 3
    assert all(item["pass"] for item in seams)
    for layer in layers:
        alpha = np.array(layer.getchannel("A"))
        assert np.any(alpha > 200)
        assert alpha[0, 0] == 0


def test_compose_static_duration_root_audio_layers_and_mirror(
    scripts,
    synthetic_production,
):
    manifest_path = synthetic_production / "production-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scenes"][0]["sourceDirections"]["primary"] = "left"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scripts["compose"].compose(synthetic_production, adopt=False)
    findings = scripts["verify"].structural_checks(synthetic_production)
    assert all(item["pass"] for item in findings), findings
    motion = scripts["verify"].motion_checks(synthetic_production)
    assert all(item["pass"] for item in motion), motion
    audio_sync = scripts["verify"].authored_audio_sync_findings(
        synthetic_production,
        manifest,
    )
    assert all(item["pass"] for item in audio_sync), audio_sync
    first_scene = (
        synthetic_production / "compositions/01-start.html"
    ).read_text(encoding="utf-8")
    assert 'class="sprite-mirror" style="transform: scaleX(-1);"' in first_scene
    assert 'data-duration="4"' in first_scene
    root = (synthetic_production / "index.html").read_text(encoding="utf-8")
    assert 'data-duration="12"' in root
    assert root.count("<audio ") == 5
    assert root.count('class="transition-fx ') == 2
    assert 'tl.fromTo("#transition-1-whip-pan-fx"' in root
    assert 'tl.set("#transition-1-whip-pan-fx", {opacity:0}' in root
    assert 'tl.fromTo("#transition-1-whip-pan",' not in root
    assert "bottom: 0;" in first_scene
    assert "height: 500px;" in first_scene


def test_status_retry_versions_sources_without_overwrite(
    scripts,
    tmp_path,
):
    production = tmp_path / "videos/guangzhou-tower-cloud-team"
    scripts["plan"].compile_card(
        BATCH_PATH,
        "guangzhou-tower-cloud-team",
        production,
    )
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    queue = scripts["queue"].queue_items(production, plan)
    queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
    queue_path.parent.mkdir(parents=True)
    queue_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in queue),
        encoding="utf-8",
    )
    status_path = production / "run-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["stages"]["audio"] = {"status": "complete", "evidence": ["audio_meta.json"]}
    status["stages"]["layer_processing"] = {
        "status": "complete",
        "evidence": ["qa/layer-processing.json"],
    }
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    original = production / queue[0]["targetPath"]
    original.parent.mkdir(parents=True)
    original.write_bytes(b"append-only")
    result = scripts["pipeline"].reset_retry(
        production,
        "visual_generation",
        queue[0]["assetId"],
    )
    assert result["status"] == "ready"
    assert original.read_bytes() == b"append-only"
    retried_status = json.loads(status_path.read_text(encoding="utf-8"))
    assert retried_status["stages"]["audio"]["status"] == "complete"
    assert retried_status["stages"]["layer_processing"]["status"] == "pending"
    retried = [
        json.loads(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
    ][0]
    assert retried["targetPath"].endswith("-v2.png")
    updated_plan = json.loads(
        (production / "story-plan.json").read_text(encoding="utf-8")
    )
    assert updated_plan["scenes"][0]["assets"]["backdropSource"].endswith("-v2.png")
    asset_manifest = json.loads(
        (production / "asset-manifest.json").read_text(encoding="utf-8")
    )
    assert asset_manifest["assets"][0]["sourcePath"].endswith("-v2.png")


def test_concurrent_production_writes_are_isolated(scripts, tmp_path):
    card_ids = ["guangzhou-tower-cloud-team", "glowing-solar-system"]

    def compile_one(card_id):
        target = tmp_path / "videos" / card_id
        scripts["plan"].compile_card(BATCH_PATH, card_id, target)
        return target

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        productions = list(executor.map(compile_one, card_ids))
    ids = []
    for production in productions:
        plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
        status = json.loads((production / "run-status.json").read_text(encoding="utf-8"))
        ids.append(plan["metadata"]["id"])
        assert status["stages"]["plan"]["status"] == "complete"
    assert ids == card_ids


def test_batch_contact_sheet(scripts, tmp_path):
    batch = {"cards": [{"id": "one"}, {"id": "two"}]}
    for card in batch["cards"]:
        path = (
            tmp_path
            / "videos"
            / card["id"]
            / "qa"
            / "scene-midpoints"
            / "contact-sheet.jpg"
        )
        path.parent.mkdir(parents=True)
        Image.new("RGB", (900, 220), "#224466").save(path)
    target = scripts["pipeline"].build_batch_contact_sheet(batch, tmp_path)
    assert target.is_file()
    with Image.open(target) as image:
        assert image.width == 900
        assert image.height == (220 + 34) * 2
