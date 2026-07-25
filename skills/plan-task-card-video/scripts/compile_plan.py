#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


BEATS = (
    ("01-start", "start", ["multi-phase-camera", "waterfall-entry", "sine-wave-loop"]),
    ("02-middle", "middle", ["coordinate-target-zoom", "motion-blur-streak", "reactive-displacement"]),
    ("03-end", "end", ["center-outward-expansion", "ambient-glow-bloom", "particle-burst"]),
)

SHOT_BLUEPRINTS = {
    "start": (
        ("establish", "wide", "ensemble", "full-bleed", "交代空间、人物关系和故事目标"),
        ("discovery", "medium", "primary", "speaker-stage", "让主角发现异常并推动事件发生"),
        ("reaction", "close", "primary", "reaction-panel", "用反应特写建立情绪钩子"),
    ),
    "middle": (
        ("pressure", "wide", "ensemble", "pressure-wide", "展示困难规模和空间压力"),
        ("action", "medium", "primary", "action-diagonal", "用连续动作呈现解决过程"),
        ("decision", "close", "primary", "decision-inset", "锁定关键判断、道具或情绪转折"),
    ),
    "end": (
        ("climax", "medium", "primary", "impact-frame", "完成决定性动作并释放高潮"),
        ("payoff", "close", "primary", "reaction-panel", "让观众看清结果和人物反应"),
        ("resolution", "wide", "ensemble", "closing-tableau", "回到环境，给故事留下完整余韵"),
    ),
}

BLOCKING_BLUEPRINTS = {
    "start": (
        {
            "subjects": {
                "primary": (-150, 20, 0.84, 1.0),
                "secondary": (-30, 18, 0.86, 0.96),
                "tertiary": (65, 6, 0.82, 0.9),
            },
            "environment": {
                "rear": (-18, 0, 1.0),
                "architecture": (0, 12, 0.96),
                "foreground": (24, 8, 1.02),
            },
            "travel": {"role": "ensemble", "x": 18, "y": -4},
        },
        {
            "subjects": {
                "primary": (45, -12, 1.02, 1.0),
                "secondary": (105, 4, 0.94, 0.88),
                "tertiary": (-85, 14, 0.84, 0.72),
            },
            "environment": {
                "rear": (12, -8, 1.025),
                "architecture": (-42, 0, 1.04),
                "foreground": (-34, 0, 1.035),
            },
            "travel": {"role": "primary", "x": 54, "y": -10},
        },
        {
            "subjects": {
                "primary": (125, -28, 1.1, 1.0),
                "secondary": (-105, 28, 0.8, 0.38),
                "tertiary": (95, 28, 0.76, 0.3),
            },
            "environment": {
                "rear": (-24, -12, 1.04),
                "architecture": (-78, 8, 1.07),
                "foreground": (42, 12, 1.06),
            },
            "travel": {"role": "primary", "x": -28, "y": -8},
        },
    ),
    "middle": (
        {
            "subjects": {
                "primary": (-135, 22, 0.86, 1.0),
                "secondary": (-65, 18, 0.86, 0.9),
                "tertiary": (72, 8, 0.82, 0.84),
            },
            "environment": {
                "rear": (22, 0, 1.01),
                "architecture": (34, 8, 0.98),
                "foreground": (-28, 8, 1.03),
            },
            "travel": {"role": "ensemble", "x": -20, "y": 4},
        },
        {
            "subjects": {
                "primary": (80, -18, 1.02, 1.0),
                "secondary": (165, -4, 0.98, 1.0),
                "tertiary": (-155, 2, 0.92, 0.9),
            },
            "environment": {
                "rear": (-24, -10, 1.04),
                "architecture": (-55, -4, 1.055),
                "foreground": (38, 0, 1.045),
            },
            "travel": {"role": "primary", "x": 68, "y": -12},
        },
        {
            "subjects": {
                "primary": (-72, -30, 1.12, 1.0),
                "secondary": (92, 26, 0.78, 0.42),
                "tertiary": (82, 24, 0.74, 0.28),
            },
            "environment": {
                "rear": (18, -14, 1.045),
                "architecture": (72, 4, 1.075),
                "foreground": (-46, 14, 1.065),
            },
            "travel": {"role": "primary", "x": 24, "y": -10},
        },
    ),
    "end": (
        {
            "subjects": {
                "primary": (105, -24, 1.06, 1.0),
                "secondary": (90, 0, 0.96, 0.94),
                "tertiary": (-100, 4, 0.9, 0.86),
            },
            "environment": {
                "rear": (-20, -6, 1.025),
                "architecture": (-48, -4, 1.05),
                "foreground": (36, 2, 1.04),
            },
            "travel": {"role": "primary", "x": 48, "y": -14},
        },
        {
            "subjects": {
                "primary": (-95, -34, 1.14, 1.0),
                "secondary": (-105, 25, 0.8, 0.44),
                "tertiary": (92, 22, 0.76, 0.34),
            },
            "environment": {
                "rear": (28, -12, 1.045),
                "architecture": (68, 4, 1.07),
                "foreground": (-42, 12, 1.06),
            },
            "travel": {"role": "primary", "x": 34, "y": -8},
        },
        {
            "subjects": {
                "primary": (0, 14, 0.9, 1.0),
                "secondary": (18, 12, 0.9, 0.98),
                "tertiary": (-18, 10, 0.86, 0.94),
            },
            "environment": {
                "rear": (0, 0, 1.0),
                "architecture": (0, 6, 0.98),
                "foreground": (0, 8, 1.02),
            },
            "travel": {"role": "ensemble", "x": 0, "y": -6},
        },
    ),
}

DEFAULT_VOICE_CAST = {
    "narrator": "zh-CN-XiaoxiaoNeural",
    "primary": "zh-CN-XiaoyiNeural",
    "secondary": "zh-CN-YunxiNeural",
    "tertiary": "zh-CN-YunyangNeural",
    "ensemble": "zh-CN-XiaoxiaoNeural",
}

PALETTES = {
    "science": {
        "canvas": "#071b2e",
        "ink": "#f5f7ff",
        "accent": "#28d7d0",
        "accent2": "#ffc857",
        "shadow": "#020b16",
    },
    "fantasy": {
        "canvas": "#0c2a27",
        "ink": "#f7f0df",
        "accent": "#f3c969",
        "accent2": "#ee8cb8",
        "shadow": "#041513",
    },
    "history": {
        "canvas": "#e8d6ae",
        "ink": "#211b18",
        "accent": "#a9362b",
        "accent2": "#2c6c80",
        "shadow": "#3c2a20",
    },
    "field-trip": {
        "canvas": "#e9f5f5",
        "ink": "#17324d",
        "accent": "#e34a3a",
        "accent2": "#f7b32b",
        "shadow": "#0b2435",
    },
}


def load_card(batch_path: Path, card_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    matches = [item for item in batch["cards"] if item["id"] == card_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one card with id {card_id!r}")
    card = matches[0]
    if "shot_hints" in card and len(card["shot_hints"]) != 3:
        raise ValueError("task cards require exactly three shot hints")
    return batch["defaults"], card


def style_key(card: dict[str, Any]) -> str:
    text = " ".join([card["story_type"], *card["visual_style"]]).lower()
    if "科学" in text or "科技" in text:
        return "science"
    if "奇幻" in text or "童话" in text:
        return "fantasy"
    if "历史" in text or "中国风" in text:
        return "history"
    return "field-trip"


def transitions(key: str) -> list[str]:
    if key == "science":
        return ["cut", "chromatic-split", "grid-dissolve"]
    if key == "fantasy":
        return ["cut", "blur-through", "light-leak"]
    if key == "history":
        return ["cut", "whip-pan", "horizontal-blinds"]
    return ["cut", "whip-pan", "horizontal-blinds"]


def fallback_shot_hints(card: dict[str, Any]) -> list[dict[str, str]]:
    protagonist = card["protagonists"][0]
    companions = "、".join(card["protagonists"][1:]) or "一名同行伙伴"
    location = card["location"]
    beat_details = (
        ("故事开始", f"{protagonist}准备开始任务", "right"),
        ("挑战发生", f"{protagonist}专注解决眼前的困难", "right"),
        ("任务完成", f"{protagonist}带着成果露出笑容", "left"),
    )
    hints = []
    for title, primary, direction in beat_details:
        hints.append(
            {
                "title": title,
                "primary": primary,
                "secondary": f"{companions}在旁协作",
                "tertiary": "一名远处的见证者或小型伙伴",
                "rear": f"{location}的远景轮廓与天空",
                "architecture": f"{location}最有辨识度的主体结构",
                "foreground": "贴近镜头的环境边缘、纸片与像素装饰",
                "direction": direction,
            }
        )
    return hints


def scene_script(card: dict[str, Any], beat_key: str) -> list[dict[str, str]]:
    configured = (
        card.get("manga", {})
        .get("scene_scripts", {})
        .get(beat_key)
    )
    if configured:
        return [
            {
                "speaker": line["speaker"],
                "role": line["role"],
                "kind": line["kind"],
                "text": line["text"],
            }
            for line in configured
        ]
    return [
        {
            "speaker": "旁白",
            "role": "narrator",
            "kind": "narration",
            "text": card["beats"][beat_key],
        }
    ]


def distribute_line_indexes(line_count: int, shot_count: int = 3) -> list[list[int]]:
    assignments: list[list[int]] = [[] for _ in range(shot_count)]
    if line_count == 1:
        assignments[shot_count // 2].append(0)
        return assignments
    if line_count > 1:
        for line_index in range(line_count):
            shot_index = round(line_index * (shot_count - 1) / (line_count - 1))
            assignments[shot_index].append(line_index)
    return assignments


def focus_blocking(
    blocking: dict[str, Any],
    focus_role: str,
) -> dict[str, Any]:
    if focus_role not in {"primary", "secondary", "tertiary"}:
        return blocking
    focus_targets = {
        "primary": {"x": blocking["subjects"]["primary"]["x"], "scale": 1.1},
        "secondary": {"x": 145, "scale": 1.04},
        "tertiary": {"x": -130, "scale": 1.0},
    }
    for role, state in blocking["subjects"].items():
        if role == focus_role:
            state.update(
                {
                    "x": focus_targets[role]["x"],
                    "y": min(state["y"], -24),
                    "scale": max(state["scale"], focus_targets[role]["scale"]),
                    "opacity": 1.0,
                }
            )
        else:
            # Keep cutouts visually solid. Hierarchy comes from scale, crop,
            # screen side, and occlusion rather than ghost-like transparency.
            state["scale"] = min(state["scale"], 0.78)
            state["opacity"] = 1.0
    travel_x = {"primary": 42, "secondary": 48, "tertiary": -48}[focus_role]
    blocking["travel"] = {"role": focus_role, "x": travel_x, "y": -8}
    return blocking


def build_shots(
    scene_id: str,
    beat_key: str,
    script: list[dict[str, str]],
    direction: str,
) -> list[dict[str, Any]]:
    shots = []
    line_assignments = distribute_line_indexes(len(script))
    direction_sign = -1 if direction == "left" else 1
    for index, (purpose, framing, focus_role, layout_mode, intent) in enumerate(
        SHOT_BLUEPRINTS[beat_key]
    ):
        blocking = BLOCKING_BLUEPRINTS[beat_key][index]
        assigned_roles = [
            script[line_index]["role"]
            for line_index in line_assignments[index]
            if script[line_index]["role"] in {"primary", "secondary", "tertiary"}
        ]
        if assigned_roles and purpose not in {"establish", "pressure", "resolution"}:
            focus_role = assigned_roles[0]
        compiled_blocking = {
            "subjects": {
                role: {
                    "x": values[0] * direction_sign,
                    "y": values[1],
                    "scale": values[2],
                    "opacity": 1.0,
                }
                for role, values in blocking["subjects"].items()
            },
            "environment": {
                layer: {
                    "x": values[0] * direction_sign,
                    "y": values[1],
                    "scale": values[2],
                }
                for layer, values in blocking["environment"].items()
            },
            "travel": {
                **blocking["travel"],
                "x": blocking["travel"]["x"] * direction_sign,
            },
        }
        compiled_blocking = focus_blocking(compiled_blocking, focus_role)
        shots.append(
            {
                "id": f"{scene_id}-shot-{index + 1}",
                "index": index + 1,
                "purpose": purpose,
                "framing": framing,
                "focusRole": focus_role,
                "layoutMode": layout_mode,
                "lineIndexes": line_assignments[index],
                "intent": intent,
                "blocking": compiled_blocking,
            }
        )
    return shots


def build_plan(defaults: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    key = style_key(card)
    scene_transitions = transitions(key)
    shot_hints = card.get("shot_hints") or fallback_shot_hints(card)
    scenes = []
    for index, (scene_id, beat_key, rules) in enumerate(BEATS):
        hint = shot_hints[index]
        script = scene_script(card, beat_key)
        source_root = f"assets/source/{scene_id}"
        processed_root = f"assets/processed/{scene_id}"
        scenes.append(
            {
                "id": scene_id,
                "index": index + 1,
                "beat": beat_key,
                "title": hint["title"],
                "narration": card["beats"][beat_key],
                "script": script,
                "shots": build_shots(
                    scene_id,
                    beat_key,
                    script,
                    hint["direction"],
                ),
                "transitionIn": scene_transitions[index],
                "motionRules": rules,
                "direction": hint["direction"],
                "sourceDirection": hint["direction"],
                "sourceDirections": {
                    "primary": hint["direction"],
                    "secondary": hint["direction"],
                    "tertiary": hint["direction"],
                },
                "shot": hint,
                "assets": {
                    "backdropSource": f"{source_root}-backdrop-v1.png",
                    "environmentSource": f"{source_root}-environment-v1.png",
                    "charactersSource": f"{source_root}-characters-v1.png",
                    "backdrop": f"{processed_root}/backdrop.png",
                    "rear": f"{processed_root}/rear.png",
                    "architecture": f"{processed_root}/architecture.png",
                    "foreground": f"{processed_root}/foreground.png",
                    "primary": f"{processed_root}/primary.png",
                    "secondary": f"{processed_root}/secondary.png",
                    "tertiary": f"{processed_root}/tertiary.png",
                },
            }
        )
    manga = card.get("manga", {})
    voice_cast = {**DEFAULT_VOICE_CAST, **manga.get("voice_cast", {})}
    return {
        "schemaVersion": 2,
        "metadata": {
            "id": card["id"],
            "title": card["title"],
            "storyType": card["story_type"],
            "location": card["location"],
            "author": card["author"],
            "directorIntent": card["director_intent"],
            "width": defaults["width"],
            "height": defaults["height"],
            "fps": defaults["fps"],
            "format": "professional-manga-v1",
        },
        "style": {
            "key": key,
            "visual": card["visual_style"],
            "paletteWords": card["palette"],
            "musicMood": card["music_mood"],
            "tokens": PALETTES[key],
            "fontDisplay": "Songti SC",
            "fontBody": "PingFang SC",
        },
        "audio": {
            **defaults["audio"],
            "voiceCast": voice_cast,
        },
        "manga": {
            "pacing": manga.get("pacing", "cinematic"),
            "dialogueRatio": manga.get("dialogue_ratio", 0.6),
            "audienceGrade": manga.get(
                "audience_grade",
                "primary-and-middle-school",
            ),
            "mustShow": manga.get("must_show", []),
            "avoid": manga.get("avoid", []),
            "factualNotes": manga.get("factual_notes", []),
            "shotCount": 9,
            "shotsPerScene": 3,
        },
        "scenes": scenes,
    }


def write_brief(output: Path, plan: dict[str, Any]) -> None:
    meta = plan["metadata"]
    text = f"""---
workflow: general-video
flow: automation
storyboard: no
message: "{meta['directorIntent']}"
destination: classroom-demo
aspect: 1920x1080
language: zh-CN
audience: primary-and-middle-school-students
length: narration-driven
---

## Intent

把任务卡《{meta['title']}》制作成三场九镜头的专业漫剧。故事依次呈现开始、挑战和结果，
每场包含建立、动作和反应镜头，保持儿童视角、真实因果关系和清晰的主角层级。

## Customizations

- HyperFrames modular composition with three scenes and nine internal shots.
- Background, rear environment, architecture, characters, and foreground stay independent.
- Use wide, medium, and close framings with motivated cuts and character micro-performance.
- Re-block characters, architecture, rear, and foreground for every editorial shot.
- Keep narration concise; let short character dialogue carry key decisions and reactions.
- Real narration duration determines the static composition duration.
- One cue-based Chinese caption track, local music, ambience, and shot sound marks.

## Assets

- Built-in Imagegen backdrops, environment sheets, and character sheets.
- Locally processed transparent PNG layers.
- Edge TTS narration with an F5-TTS-compatible replacement interface.

## Notes

- Simulated author metadata is not rendered on screen.
- Render only after the final Studio preview is approved.
"""
    (output / "BRIEF.md").write_text(text, encoding="utf-8")


def write_script(output: Path, plan: dict[str, Any]) -> None:
    rows = ["# Manga Performance Script", ""]
    for scene in plan["scenes"]:
        rows.extend([f"## {scene['id']} - {scene['title']}", ""])
        for line in scene["script"]:
            rows.append(
                f"- [{line['kind']}/{line['role']}] "
                f"{line['speaker']}：{line['text']}"
            )
        rows.append("")
    (output / "SCRIPT.md").write_text("\n".join(rows), encoding="utf-8")


def storyboard_text(plan: dict[str, Any], timed_scenes: list[dict[str, Any]] | None = None) -> str:
    meta = plan["metadata"]
    timings = {scene["id"]: scene for scene in (timed_scenes or [])}
    rows = [
        "---",
        "format: 1920x1080",
        f'message: "{meta["directorIntent"]}"',
        "arc: Start -> Challenge -> Resolution",
        "audience: primary-and-middle-school-students",
        "---",
        "",
    ]
    for scene in plan["scenes"]:
        timed = timings.get(scene["id"])
        duration = f"{timed['durationSeconds']:.3f}s" if timed else "pending"
        rows.extend(
            [
                f"## Frame {scene['index']} - {scene['title']}",
                "",
                f"- status: {'animated' if timed else 'outline'}",
                f"- src: compositions/{scene['id']}.html",
                f"- duration: {duration}",
                f"- transition_in: {scene['transitionIn']}",
                f"- scene: {scene['shot']['architecture']}；{scene['shot']['primary']}",
                f"- performance_lines: {len(scene['script'])}",
                f"- motion: {', '.join(scene['motionRules'])}",
                "- sfx: scene-impact",
                "",
                f"{scene['title']}承担故事的 {scene['beat']} 节点。",
                "",
            ]
        )
        for shot in scene["shots"]:
            shot_lines = [
                scene["script"][line_index]
                for line_index in shot["lineIndexes"]
            ]
            rendered_lines = (
                [f"{line['speaker']}：{line['text']}" for line in shot_lines]
                or ["silent"]
            )
            rows.extend(
                [
                    f"### Shot {scene['index']}.{shot['index']} - {shot['purpose']}",
                    "",
                    f"- framing: {shot['framing']}",
                    f"- focus: {shot['focusRole']}",
                    f"- intent: {shot['intent']}",
                    (
                        "- blocking: "
                        + "; ".join(
                            f"{role} x={state['x']} y={state['y']} "
                            f"scale={state['scale']} opacity={state['opacity']}"
                            for role, state in shot["blocking"]["subjects"].items()
                        )
                    ),
                    *(f"- line: {line}" for line in rendered_lines),
                    "",
                ]
            )
    return "\n".join(rows)


def write_frame(output: Path, plan: dict[str, Any]) -> None:
    style = plan["style"]
    tokens = style["tokens"]
    text = f"""---
canvas: "{tokens['canvas']}"
ink: "{tokens['ink']}"
accent: "{tokens['accent']}"
accent2: "{tokens['accent2']}"
shadow: "{tokens['shadow']}"
font_display: "{style['fontDisplay']}"
font_body: "{style['fontBody']}"
corner_radius: 0
---

# Professional Layered Pixel Manga

Use crisp pixel clusters, torn-paper silhouettes, restrained halftone texture, visible foreground framing,
and a clear primary/secondary/tertiary hierarchy. Every scene must provide wide, medium, and close framings,
one dominant focal point, motivated camera movement, anticipation, action, settle, and secondary motion.
Keep backgrounds 15–25% quieter than the active subject. Avoid rounded interface cards, heavy explanatory
caption boxes, full-screen moving grain, photorealism, readable text inside generated images, and flat
one-image camera moves.
"""
    (output / "frame.md").write_text(text, encoding="utf-8")


def write_asset_manifest(output: Path, plan: dict[str, Any]) -> None:
    assets = []
    for scene in plan["scenes"]:
        for kind, key in (
            ("backdrop", "backdropSource"),
            ("environment-sheet", "environmentSource"),
            ("character-sheet", "charactersSource"),
        ):
            assets.append(
                {
                    "id": f"{scene['id']}-{kind.replace('-sheet', '')}",
                    "sceneId": scene["id"],
                    "kind": kind,
                    "sourcePath": scene["assets"][key],
                    "status": "pending",
                }
            )
    (output / "asset-manifest.json").write_text(
        json.dumps({"schemaVersion": 1, "assets": assets}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_status(output: Path) -> None:
    stage_names = [
        "plan",
        "visual_generation",
        "audio",
        "layer_processing",
        "composition",
        "check",
        "preview",
        "render",
        "qa",
    ]
    stages = {name: {"status": "pending", "evidence": []} for name in stage_names}
    stages["plan"] = {
        "status": "complete",
        "evidence": ["story-plan.json", "BRIEF.md", "SCRIPT.md", "STORYBOARD.md", "frame.md"],
    }
    payload = {"schemaVersion": 1, "stages": stages}
    (output / "run-status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def compile_card(batch_path: Path, card_id: str, output: Path) -> dict[str, Any]:
    defaults, card = load_card(batch_path, card_id)
    output.mkdir(parents=True, exist_ok=True)
    plan = build_plan(defaults, card)
    (output / "story-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_brief(output, plan)
    write_script(output, plan)
    (output / "STORYBOARD.md").write_text(storyboard_text(plan), encoding="utf-8")
    write_frame(output, plan)
    write_asset_manifest(output, plan)
    write_status(output)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    parser.add_argument("--card-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    compile_card(Path(args.batch).resolve(), args.card_id, output)
    print(output / "story-plan.json")


if __name__ == "__main__":
    main()
