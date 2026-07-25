import asyncio
import concurrent.futures
import copy
import hashlib
import json
import math
from pathlib import Path

import jsonschema
import numpy as np
import yaml
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
    for scene in plan["scenes"]:
        assert len(scene["shots"]) == 3
        for role in ("primary", "secondary", "tertiary"):
            states = {
                tuple(shot["blocking"]["subjects"][role].values())
                for shot in scene["shots"]
            }
            assert len(states) == 3
        for layer in ("rear", "architecture", "foreground"):
            states = {
                tuple(shot["blocking"]["environment"][layer].values())
                for shot in scene["shots"]
            }
            assert len(states) == 3
    assert not any("duration" in card for card in batch["cards"])


def test_narration_duration_quantization(scripts):
    quantize = scripts["audio"].quantized_scene_duration
    assert quantize(0.1) == 4.0
    assert quantize(2.8) == 4.0
    assert quantize(3.01) == 4.5
    assert quantize(7.31) == 9.0


def test_multirole_audio_helpers_keep_legacy_and_build_short_cues(scripts):
    audio = scripts["audio"]
    legacy = audio.scene_lines({"id": "legacy", "narration": "旧旁白仍然可用。"})
    assert legacy == [
        {
            "id": "legacy-line-1",
            "speaker": "旁白",
            "role": "narrator",
            "kind": "narration",
            "text": "旧旁白仍然可用。",
        }
    ]

    config = {
        "voice": "fallback",
        "voiceCast": {
            "primary": "primary-voice",
            "secondary": {"voice": "secondary-voice", "rate": "-8%"},
        },
    }
    assert audio.line_voice_config(
        config,
        {"role": "primary"},
    )["voice"] == "primary-voice"
    secondary = audio.line_voice_config(config, {"role": "secondary"})
    assert secondary["voice"] == "secondary-voice"
    assert secondary["rate"] == "-8%"
    assert audio.line_voice_config(config, {"role": "tertiary"})["voice"] == "fallback"

    text = "这是一句需要拆成多个短字幕并保持语义顺序的测试台词。"
    chunks = audio.short_caption_chunks(text)
    assert "".join(chunks) == text
    assert all(len(chunk) <= audio.CAPTION_MAX_CHARS for chunk in chunks)
    line = {
        "id": "scene-line-1",
        "speaker": "主角",
        "role": "primary",
        "kind": "dialogue",
        "text": text,
    }
    cues = audio.caption_cues_for_line(
        "scene",
        line,
        0,
        "scene-shot-1",
        1.0,
        4.0,
    )
    assert cues[0]["startSeconds"] == 1.0
    assert cues[-1]["endSeconds"] == 5.0
    assert all(
        left["endSeconds"] == right["startSeconds"]
        for left, right in zip(cues, cues[1:])
    )

    shot_timings = audio.build_shot_timings(
        {"id": "scene"},
        [
            {"localStart": 0.45, "duration": 2.8},
            {"localStart": 3.67, "duration": 2.8},
            {"localStart": 6.89, "duration": 2.8},
        ],
        10.5,
    )
    assert len(shot_timings) == 3
    assert shot_timings[0]["startSeconds"] == 0
    assert sum(shot["durationSeconds"] for shot in shot_timings) == 10.5
    assert all(shot["durationSeconds"] >= audio.MIN_SHOT_SECONDS for shot in shot_timings)


def test_silent_multirole_audio_generation_outputs_shots_captions_and_cues(
    scripts,
    tmp_path,
):
    production = tmp_path / "videos" / "professional-audio"
    plan = scripts["plan"].compile_card(
        BATCH_PATH,
        "guangzhou-tower-cloud-team",
        production,
    )
    plan["audio"]["voiceCast"].update(
        {
            "narrator": "voice-narrator",
            "primary": "voice-primary",
            "secondary": "voice-secondary",
        }
    )
    for scene in plan["scenes"]:
        scene["script"] = [
            {
                "speaker": "旁白",
                "role": "narrator",
                "kind": "narration",
                "text": "风从远处吹来。",
            },
            {
                "speaker": "小雨",
                "role": "primary",
                "kind": "dialogue",
                "text": "看那边，我们找到线索了！",
            },
            {
                "speaker": "同学",
                "role": "secondary",
                "kind": "dialogue",
                "text": "一起出发。",
            },
        ]
    (production / "story-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    asyncio.run(scripts["audio"].generate(production, "silent"))

    manifest = json.loads(
        (production / "production-manifest.json").read_text(encoding="utf-8")
    )
    audio_meta = json.loads((production / "audio_meta.json").read_text(encoding="utf-8"))
    assert manifest["captions"]
    assert all(
        0 < len(cue["text"]) <= scripts["audio"].CAPTION_MAX_CHARS
        for cue in manifest["captions"]
    )
    assert all(
        left["endSeconds"] <= right["startSeconds"]
        for left, right in zip(manifest["captions"], manifest["captions"][1:])
    )
    for scene in manifest["scenes"]:
        assert len(scene["shots"]) == 3
        assert scene["shots"][0]["startSeconds"] == 0
        assert math.isclose(
            sum(shot["durationSeconds"] for shot in scene["shots"]),
            scene["durationSeconds"],
            abs_tol=1e-6,
        )
        assert scene["captions"]
        assert scene["words"]
        assert all(
            left["start"] <= right["start"]
            for left, right in zip(scene["words"], scene["words"][1:])
        )

    voices = {(item["role"], item["voice"]) for item in audio_meta["voices"]}
    assert ("narrator", "voice-narrator") in voices
    assert ("primary", "voice-primary") in voices
    assert ("secondary", "voice-secondary") in voices
    assert len(audio_meta["sfxEvents"]) == 9
    assert [clip["id"] for clip in manifest["audioClips"] if clip["id"] in {"sfx-1", "sfx-2", "sfx-3"}] == [
        "sfx-1",
        "sfx-2",
        "sfx-3",
    ]
    for key in (
        "narrationPath",
        "musicPath",
        "impactPath",
        "whooshPath",
        "chimePath",
        "ambiencePath",
    ):
        assert (production / manifest["audio"][key]).is_file()


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
    assert 'class="blocking blocking-primary"' in first_scene
    assert 'tl.set(q(".blocking-primary")' in first_scene
    assert 'tl.to(q(".blocking-primary")' in first_scene
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


def test_professional_shots_use_crisp_subjects_and_authored_layouts(
    scripts,
    tmp_path,
):
    production = tmp_path / "videos/crisp-manga"
    scripts["plan"].compile_card(
        BATCH_PATH,
        "guangzhou-tower-cloud-team",
        production,
    )
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    shots = [shot for scene in plan["scenes"] for shot in scene["shots"]]

    assert {shot["layoutMode"] for shot in shots} >= {
        "full-bleed",
        "speaker-stage",
        "reaction-panel",
        "action-diagonal",
        "decision-inset",
        "impact-frame",
        "closing-tableau",
    }
    assert all(
        state["opacity"] == 1.0
        for shot in shots
        for state in shot["blocking"]["subjects"].values()
    )


def test_composition_emits_comic_treatments_and_caption_grammar(
    scripts,
    synthetic_production,
):
    manifest_path = synthetic_production / "production-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for scene_index, scene in enumerate(manifest["scenes"]):
        modes = (
            ("full-bleed", "speaker-stage", "reaction-panel"),
            ("pressure-wide", "action-diagonal", "decision-inset"),
            ("impact-frame", "reaction-panel", "closing-tableau"),
        )[scene_index]
        for shot, mode in zip(scene["shots"], modes):
            shot["layoutMode"] = mode
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    scripts["compose"].compose(synthetic_production)

    first_scene = (
        synthetic_production / "compositions/01-start.html"
    ).read_text(encoding="utf-8")
    root = (synthetic_production / "index.html").read_text(encoding="utf-8")
    assert "mode-reaction-panel" in first_scene
    assert 'q(".treatment-3"), {opacity:1}' in first_scene
    assert 'class="panel-inset"' in first_scene
    assert '.treatment-3 .panel-inset' in first_scene
    assert "caption-dialogue" in root
    assert "caption-narration" in root


def test_ready_state_recovers_completed_visual_queue(scripts, tmp_path):
    production = tmp_path / "videos/recovered"
    scripts["plan"].compile_card(
        BATCH_PATH,
        "guangzhou-tower-cloud-team",
        production,
    )
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    queue = scripts["queue"].queue_items(production, plan)
    for item in queue:
        item["status"] = "generated"
    queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
    queue_path.parent.mkdir(parents=True)
    queue_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in queue),
        encoding="utf-8",
    )

    status = scripts["pipeline"].set_ready_states(production)

    assert status["stages"]["visual_generation"]["status"] == "complete"
    assert status["stages"]["visual_generation"]["evidence"] == [
        "tmp/imagegen/prompt-queue.jsonl",
        "asset-manifest.json",
    ]
    assert status["stages"]["layer_processing"]["status"] == "ready"


def test_prompt_queue_restores_only_matching_generated_assets(scripts, tmp_path):
    production = tmp_path / "videos/restored-assets"
    production.mkdir(parents=True)
    target = production / "assets/source/asset-v1.png"
    target.parent.mkdir(parents=True)
    Image.new("RGB", (32, 24), "#224466").save(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    item = {
        "assetId": "asset",
        "sceneId": "01-start",
        "kind": "backdrop",
        "targetPath": "assets/source/asset-v1.png",
        "referencePaths": [],
        "prompt": "same prompt",
        "status": "pending",
        "version": 1,
    }
    old = {**item, "status": "generated", "sha256": digest}
    queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
    queue_path.parent.mkdir(parents=True)
    queue_path.write_text(json.dumps(old) + "\n", encoding="utf-8")
    (production / "asset-manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "assets": [
                    {
                        "id": "asset",
                        "sceneId": "01-start",
                        "kind": "backdrop",
                        "sourcePath": item["targetPath"],
                        "status": "pending",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    restored = scripts["queue"].restore_generated_assets(production, [item.copy()])
    assert restored[0]["status"] == "generated"
    assert restored[0]["sha256"] == digest
    manifest = json.loads(
        (production / "asset-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["assets"][0]["status"] == "generated"

    changed = {**item, "prompt": "changed prompt"}
    not_restored = scripts["queue"].restore_generated_assets(production, [changed])
    assert not_restored[0]["status"] == "pending"


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


def test_batch_render_contact_sheet(scripts, tmp_path):
    batch = {"batch_id": "render-batch", "cards": [{"id": "one"}, {"id": "two"}]}
    for card in batch["cards"]:
        path = (
            tmp_path
            / "videos"
            / card["id"]
            / "qa"
            / "render-shot-contact-sheet.png"
        )
        path.parent.mkdir(parents=True)
        Image.new("RGB", (900, 600), "#334455").save(path)
    target = scripts["pipeline"].build_batch_render_contact_sheet(batch, tmp_path)
    assert target == tmp_path / "qa/render-batch-render-contact-sheet.jpg"
    with Image.open(target) as image:
        assert image.width == 900
        assert image.height == (600 + 40) * 2


def test_skill_metadata_invokes_matching_project_skill():
    skill_dirs = sorted(path for path in (REPO_ROOT / "skills").iterdir() if path.is_dir())
    assert skill_dirs
    for skill_dir in skill_dirs:
        metadata = yaml.safe_load(
            (skill_dir / "agents/openai.yaml").read_text(encoding="utf-8")
        )
        prompt = metadata["interface"]["default_prompt"]
        assert f"${skill_dir.name}" in prompt
