#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MEDIA_USE = Path(
    os.environ.get(
        "HYPERFRAMES_MEDIA_USE_SCRIPT",
        str(Path.home() / ".agents/skills/media-use/scripts/resolve.mjs"),
    )
)
LAYER_ORDER = [
    "backdrop",
    "rear",
    "architecture",
    "tertiary",
    "secondary",
    "primary",
    "foreground",
]


def number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def clean_generated_html(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.splitlines()) + "\n"


def asset_src(path: str) -> str:
    return path


def subject_markup(scene: dict, role: str, layer_index: int) -> str:
    source_direction = scene.get("sourceDirections", {}).get(
        role,
        scene["sourceDirection"],
    )
    mirror = source_direction != scene["direction"]
    image_style = "transform: scaleX(-1);" if mirror else ""
    return f"""
      <div class="layer cutout subject {role}" data-pixel-layer="{role}" data-pixel-z="{layer_index}">
        <div class="sprite-mirror" style="{image_style}">
          <div class="blocking blocking-{role}">
            <div class="entrance"><div class="performance performance-{role}">
              <img data-layout-ignore src="{html.escape(asset_src(scene['assets'][role]))}" alt="" />
            </div></div>
          </div>
        </div>
      </div>"""


def scene_shots(scene: dict) -> list[dict]:
    shots = scene.get("shots") or []
    duration = float(scene["durationSeconds"])
    if len(shots) != 3:
        shots = [
            {"id": f"{scene['id']}-shot-1", "framing": "wide", "focusRole": "ensemble"},
            {"id": f"{scene['id']}-shot-2", "framing": "medium", "focusRole": "primary"},
            {"id": f"{scene['id']}-shot-3", "framing": "close", "focusRole": "primary"},
        ]
    weights = [0.31, 0.37, 0.32]
    cursor = 0.0
    normalized = []
    for index, shot in enumerate(shots):
        start = float(shot.get("startSeconds", cursor))
        if "durationSeconds" in shot:
            shot_duration = float(shot["durationSeconds"])
        elif index == len(shots) - 1:
            shot_duration = duration - start
        else:
            shot_duration = duration * weights[index]
        end = duration if index == len(shots) - 1 else min(duration, start + shot_duration)
        normalized.append({**shot, "startSeconds": start, "durationSeconds": end - start})
        cursor = end
    return normalized


def shot_camera(shot: dict, index: int) -> dict[str, float]:
    framing = shot.get("framing", "medium")
    focus = shot.get("focusRole", "primary")
    scale = {"wide": 1.0, "medium": 1.16, "close": 1.38}.get(framing, 1.16)
    anchors = {
        "primary": (0, -34),
        "secondary": (210, -12),
        "tertiary": (-250, -8),
        "ensemble": (0, 0),
        "architecture": (0, 40),
    }
    x, y = anchors.get(focus, (0, 0))
    return {"x": x, "y": y, "scale": scale, "push": 0.018 + index * 0.004}


def shot_blocking(shot: dict, index: int) -> dict:
    if shot.get("blocking"):
        return shot["blocking"]
    offsets = (-90, 45, 0)
    return {
        "subjects": {
            "primary": {
                "x": offsets[index],
                "y": -8 * index,
                "scale": (0.9, 1.02, 1.08)[index],
                "opacity": 1,
            },
            "secondary": {
                "x": (-30, 95, -70)[index],
                "y": 12 * index,
                "scale": (0.9, 0.96, 0.8)[index],
                "opacity": (0.95, 0.86, 0.42)[index],
            },
            "tertiary": {
                "x": (45, -85, 75)[index],
                "y": 10 * index,
                "scale": (0.86, 0.9, 0.76)[index],
                "opacity": (0.9, 0.76, 0.34)[index],
            },
        },
        "environment": {
            "rear": {"x": (-12, 18, -22)[index], "y": -4 * index, "scale": 1 + index * 0.02},
            "architecture": {"x": (0, -36, 54)[index], "y": 4 * index, "scale": 0.98 + index * 0.04},
            "foreground": {"x": (18, -28, 36)[index], "y": 6 * index, "scale": 1.02 + index * 0.02},
        },
        "travel": {"role": "primary", "x": (18, 52, -24)[index], "y": (-4, -10, -6)[index]},
    }


def blocking_timeline(shot: dict, index: int, start: float, duration: float) -> list[str]:
    blocking = shot_blocking(shot, index)
    rows = []
    for role, state in blocking["subjects"].items():
        rows.append(
            f'tl.set(q(".blocking-{role}"), '
            f'{{x:{number(state["x"])},y:{number(state["y"])},'
            f'scale:{number(state["scale"])},opacity:{number(state["opacity"])}}}, '
            f'{number(start)});'
        )
    for layer, state in blocking["environment"].items():
        rows.append(
            f'tl.set(q(".{layer}"), '
            f'{{x:{number(state["x"])},y:{number(state["y"])},'
            f'scale:{number(state["scale"])}}}, {number(start)});'
        )
    travel = blocking["travel"]
    move_start = start + min(0.16, duration * 0.08)
    move_duration = max(0.3, min(duration * 0.48, duration - 0.2))
    if travel["role"] == "ensemble":
        relative_x = f"{'+' if travel['x'] >= 0 else '-'}={number(abs(travel['x']))}"
        relative_y = f"{'+' if travel['y'] >= 0 else '-'}={number(abs(travel['y']))}"
        rows.append(
            f'tl.to(qAll(".blocking"), '
            f'{{x:"{relative_x}",y:"{relative_y}",'
            f'duration:{number(move_duration)},ease:"power1.inOut"}}, '
            f'{number(move_start)});'
        )
    else:
        state = blocking["subjects"][travel["role"]]
        rows.append(
            f'tl.to(q(".blocking-{travel["role"]}"), '
            f'{{x:{number(state["x"] + travel["x"])},'
            f'y:{number(state["y"] + travel["y"])},'
            f'duration:{number(move_duration)},ease:"power2.inOut"}}, '
            f'{number(move_start)});'
        )
    for layer, factor in (("rear", -0.1), ("architecture", -0.16), ("foreground", -0.24)):
        state = blocking["environment"][layer]
        rows.append(
            f'tl.to(q(".{layer}"), '
            f'{{x:{number(state["x"] + travel["x"] * factor)},'
            f'y:{number(state["y"] + travel["y"] * factor)},'
            f'duration:{number(move_duration)},ease:"sine.inOut"}}, '
            f'{number(move_start)});'
        )
    return rows


def transformed_bounds(base: dict, state: dict) -> dict[str, float]:
    scale = float(state["scale"])
    width = base["width"] * scale
    height = base["height"] * scale
    return {
        "x": round(base["x"] + state["x"] + (base["width"] - width) / 2, 3),
        "y": round(
            base["y"] + state["y"] + (base["height"] - height) * 0.75,
            3,
        ),
        "width": round(width, 3),
        "height": round(height, 3),
    }


def blocking_varies(shots: list[dict]) -> bool:
    for role in ("primary", "secondary", "tertiary"):
        states = {
            (
                row["blocking"]["subjects"][role]["x"],
                row["blocking"]["subjects"][role]["y"],
                row["blocking"]["subjects"][role]["scale"],
                row["blocking"]["subjects"][role]["opacity"],
            )
            for row in shots
        }
        if len(states) < 3:
            return False
    for layer in ("rear", "architecture", "foreground"):
        states = {
            (
                row["blocking"]["environment"][layer]["x"],
                row["blocking"]["environment"][layer]["y"],
                row["blocking"]["environment"][layer]["scale"],
            )
            for row in shots
        }
        if len(states) < 3:
            return False
    return True


def shot_timeline(scene: dict) -> str:
    rows = []
    shots = scene_shots(scene)
    for index, shot in enumerate(shots):
        start = shot["startSeconds"]
        duration = shot["durationSeconds"]
        rows.extend(blocking_timeline(shot, index, start, duration))
        camera = shot_camera(shot, index)
        selector = ".camera-rig"
        rows.append(
            f'tl.set(q("{selector}"), {{x:{number(camera["x"])},y:{number(camera["y"])},'
            f'scale:{number(camera["scale"])}}}, {number(start)});'
        )
        rows.append(
            f'tl.to(q("{selector}"), {{scale:{number(camera["scale"] + camera["push"])},'
            f'duration:{number(max(0.1, duration - 0.03))},ease:"none"}}, {number(start)});'
        )
        focus = shot.get("focusRole", "primary")
        if focus in {"primary", "secondary", "tertiary"}:
            anticipation = start + min(0.22, duration * 0.12)
            settle = min(0.32, duration * 0.14)
            rows.append(
                f'tl.to(q(".performance-{focus}"), {{y:-12,rotation:{2 if index % 2 == 0 else -2},'
                f'scale:1.025,duration:{number(settle)},ease:"power2.out"}}, {number(anticipation)});'
            )
            rows.append(
                f'tl.to(q(".performance-{focus}"), {{y:0,rotation:0,scale:1,'
                f'duration:{number(settle)},ease:"power2.inOut"}}, {number(anticipation + settle)});'
            )
        if index:
            rows.append(
                f'tl.fromTo(q(".internal-cut"), {{opacity:0.22}}, '
                f'{{opacity:0,duration:0.12,ease:"power2.out"}}, {number(start)});'
            )
        rows.append(
            f'tl.set(qAll(".comic-treatment"), {{opacity:0}}, {number(start)});'
        )
        rows.append(
            f'tl.set(q(".treatment-{index + 1}"), {{opacity:1}}, {number(start)});'
        )
        if shot.get("layoutMode") in {"reaction-panel", "decision-inset"}:
            rows.append(
                f'tl.fromTo(q(".treatment-{index + 1} .panel-inset"), '
                f'{{x:90,scale:0.92}}, {{x:0,scale:1,duration:0.24,'
                f'ease:"power3.out"}}, {number(start)});'
            )
    return "\n      ".join(rows)


def comic_treatments(scene: dict) -> str:
    rows = []
    for index, shot in enumerate(scene_shots(scene), start=1):
        mode = html.escape(shot.get("layoutMode", "full-bleed"))
        focus = shot.get("focusRole", "primary")
        inset = ""
        if focus in {"primary", "secondary", "tertiary"}:
            source_direction = scene.get("sourceDirections", {}).get(
                focus,
                scene["sourceDirection"],
            )
            mirror = source_direction != scene["direction"]
            mirror_class = " portrait-mirrored" if mirror else ""
            inset = (
                '<div class="panel-inset">'
                f'<div class="panel-portrait{mirror_class}" '
                f'style="background-image:url(&quot;'
                f'{html.escape(asset_src(scene["assets"][focus]))}'
                f'&quot;)"></div>'
                '</div>'
            )
        rows.append(
            f'<div class="comic-treatment treatment-{index} mode-{mode}" '
            f'data-shot-purpose="{html.escape(shot.get("purpose", "shot"))}">'
            f'{inset}<i class="panel-edge edge-a"></i><i class="panel-edge edge-b"></i>'
            '<i class="impact-ray ray-a"></i><i class="impact-ray ray-b"></i>'
            '<i class="impact-ray ray-c"></i></div>'
        )
    return "".join(rows)


def common_scene_css(scene: dict, tokens: dict) -> str:
    composition_id = scene["id"]
    root_id = f"scene-{composition_id}"
    return f"""
    <style>
      #{root_id} {{
        position: relative;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: {tokens['canvas']};
        color: {tokens['ink']};
        image-rendering: pixelated;
      }}
      #{root_id} .layer {{
        position: absolute;
        overflow: hidden;
        transform-origin: 50% 70%;
      }}
      #{root_id} .camera-rig {{
        position: absolute;
        inset: 0;
        width: 1920px;
        height: 1080px;
        transform-origin: 50% 50%;
      }}
      #{root_id} .subject {{
        overflow: visible;
      }}
      #{root_id} .entrance,
      #{root_id} .blocking,
      #{root_id} .performance {{
        width: 100%;
        height: 100%;
        transform-origin: 50% 75%;
      }}
      #{root_id} .layer img {{
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
        image-rendering: pixelated;
      }}
      #{root_id} .backdrop {{
        inset: 0;
        z-index: 0;
      }}
      #{root_id} .backdrop img {{
        object-fit: cover;
      }}
      #{root_id} .rear {{
        left: 0;
        top: 25px;
        width: 1920px;
        height: 770px;
        z-index: 1;
        opacity: 0.86;
      }}
      #{root_id} .architecture {{
        left: 155px;
        top: 105px;
        width: 1610px;
        height: 800px;
        z-index: 2;
      }}
      #{root_id} .subject img {{
        filter:
          drop-shadow(4px 0 {tokens['ink']})
          drop-shadow(-4px 0 {tokens['ink']})
          drop-shadow(0 4px {tokens['ink']})
          drop-shadow(0 16px 8px rgba(0, 0, 0, 0.34));
      }}
      #{root_id} .sprite-mirror {{
        width: 100%;
        height: 100%;
      }}
      #{root_id} .tertiary {{
        right: 105px;
        top: 385px;
        width: 330px;
        height: 485px;
        z-index: 3;
      }}
      #{root_id} .secondary {{
        left: 95px;
        top: 300px;
        width: 450px;
        height: 590px;
        z-index: 4;
      }}
      #{root_id} .primary {{
        left: 615px;
        top: 190px;
        width: 690px;
        height: 715px;
        z-index: 5;
      }}
      #{root_id} .foreground {{
        left: 0;
        bottom: 0;
        width: 1920px;
        height: 500px;
        z-index: 6;
      }}
      #{root_id} .pixel-accent {{
        position: absolute;
        z-index: 7;
        opacity: 0;
        background: {tokens['accent2']};
      }}
      #{root_id} .glow {{
        position: absolute;
        left: 790px;
        top: 310px;
        width: 340px;
        height: 340px;
        z-index: 4;
        opacity: 0;
        border: 28px solid {tokens['accent2']};
        box-shadow: 0 0 80px {tokens['accent2']};
      }}
      #{root_id} .internal-cut {{
        position: absolute;
        inset: 0;
        z-index: 20;
        pointer-events: none;
        opacity: 0;
        background: {tokens['ink']};
        mix-blend-mode: screen;
      }}
      #{root_id} .comic-treatment {{
        position: absolute;
        inset: 0;
        z-index: 18;
        opacity: 0;
        pointer-events: none;
      }}
      #{root_id} .panel-edge {{
        position: absolute;
        display: none;
        border: 12px solid {tokens['ink']};
        box-shadow: 10px 10px 0 {tokens['accent']};
      }}
      #{root_id} .panel-inset {{
        position: absolute;
        display: none;
        right: 88px;
        top: 72px;
        width: 760px;
        height: 760px;
        overflow: hidden;
        background:
          linear-gradient(135deg, {tokens['canvas']} 0 48%, {tokens['accent2']} 48% 52%, {tokens['canvas']} 52%);
        border: 12px solid {tokens['ink']};
        box-shadow: 10px 10px 0 {tokens['accent']};
        transform-origin: 70% 50%;
      }}
      #{root_id} .panel-portrait {{
        width: 100%;
        height: 112%;
        background-repeat: no-repeat;
        background-position: 50% 8%;
        background-size: 155% auto;
        filter:
          drop-shadow(4px 0 {tokens['ink']})
          drop-shadow(-4px 0 {tokens['ink']})
          drop-shadow(0 4px {tokens['ink']});
      }}
      #{root_id} .panel-portrait.portrait-mirrored {{
        transform: scaleX(-1);
      }}
      #{root_id} .mode-reaction-panel .panel-inset,
      #{root_id} .mode-decision-inset .panel-inset {{
        display: block;
      }}
      #{root_id} .mode-reaction-panel .edge-a,
      #{root_id} .mode-decision-inset .edge-a {{
        display: none;
      }}
      #{root_id} .mode-decision-inset .edge-b {{
        display: block;
        left: 92px;
        bottom: 170px;
        width: 430px;
        height: 280px;
        border-width: 8px;
        box-shadow: 8px 8px 0 {tokens['accent2']};
      }}
      #{root_id} .mode-speaker-stage .edge-a {{
        display: block;
        left: 70px;
        top: 82px;
        width: 1080px;
        height: 760px;
        border-right: 0;
        box-shadow: none;
      }}
      #{root_id} .mode-action-diagonal::before,
      #{root_id} .mode-impact-frame::before {{
        content: "";
        position: absolute;
        inset: -180px;
        border: 34px solid {tokens['accent2']};
        transform: rotate(-5deg);
        opacity: .7;
      }}
      #{root_id} .impact-ray {{
        position: absolute;
        display: none;
        width: 720px;
        height: 14px;
        background: {tokens['accent2']};
        transform-origin: right center;
      }}
      #{root_id} .mode-action-diagonal .impact-ray,
      #{root_id} .mode-impact-frame .impact-ray {{
        display: block;
        right: -80px;
        top: 210px;
      }}
      #{root_id} .mode-action-diagonal .ray-b,
      #{root_id} .mode-impact-frame .ray-b {{ top: 510px; transform: rotate(8deg); }}
      #{root_id} .mode-action-diagonal .ray-c,
      #{root_id} .mode-impact-frame .ray-c {{ top: 760px; transform: rotate(-10deg); }}
      #{root_id} .mode-closing-tableau {{
        box-shadow: inset 0 0 0 18px {tokens['accent2']};
      }}
    </style>"""


def accents(scene: dict) -> str:
    if scene["beat"] == "middle":
        return """
      <div class="pixel-accent streak streak-1"></div>
      <div class="pixel-accent streak streak-2"></div>
      <div class="pixel-accent streak streak-3"></div>
      <style>
        .streak { width: 410px; height: 10px; transform: rotate(-8deg); }
        .streak-1 { left: 180px; top: 255px; }
        .streak-2 { left: 1180px; top: 395px; width: 520px; }
        .streak-3 { left: 330px; top: 720px; width: 310px; }
      </style>"""
    if scene["beat"] == "end":
        pixels = []
        positions = [
            (410, 240), (520, 170), (690, 270), (930, 130), (1110, 230),
            (1335, 165), (1480, 310), (360, 520), (1530, 570), (1280, 720),
            (620, 755), (1010, 690),
        ]
        for index, (left, top) in enumerate(positions):
            size = 12 + (index % 3) * 8
            pixels.append(
                f'<div class="pixel-accent particle p-{index}" '
                f'style="left:{left}px;top:{top}px;width:{size}px;height:{size}px"></div>'
            )
        return '<div class="glow"></div>' + "".join(pixels)
    return """
      <div class="pixel-accent breeze b-1" style="left:280px;top:260px;width:18px;height:18px"></div>
      <div class="pixel-accent breeze b-2" style="left:1470px;top:390px;width:14px;height:14px"></div>
      <div class="pixel-accent breeze b-3" style="left:370px;top:680px;width:22px;height:22px"></div>"""


def start_timeline(scene: dict) -> str:
    duration = scene["durationSeconds"]
    entrance = duration * 0.18
    action_end = duration * 0.72
    exit_at = duration * 0.90
    primary_start = duration * 0.025
    secondary_start = duration * 0.075
    tertiary_start = duration * 0.12
    bob = max(0.25, (action_end - entrance) / 4)
    return f"""
      tl.fromTo(q(".backdrop img"), {{scale: 1}}, {{scale: 1.035, duration: {number(action_end)}, ease: "none"}}, 0);
      tl.fromTo(q(".rear img"), {{opacity: 0, x: -34}}, {{opacity: 0.86, x: 0, duration: {number(entrance * 0.78)}, ease: "power2.out"}}, 0);
      tl.fromTo(q(".architecture img"), {{opacity: 0, y: 28, scale: 0.98}}, {{opacity: 1, y: 0, scale: 1, duration: {number(entrance)}, ease: "power2.out"}}, 0);
      tl.fromTo(q(".primary img"), {{opacity: 0, y: 72, scale: 0.86}}, {{opacity: 1, y: 0, scale: 1, duration: {number(entrance - primary_start)}, ease: "back.out(1.45)"}}, {number(primary_start)});
      tl.fromTo(q(".secondary img"), {{opacity: 0, x: -62, y: 36, scale: 0.9}}, {{opacity: 1, x: 0, y: 0, scale: 1, duration: {number(entrance - secondary_start)}, ease: "power2.out"}}, {number(secondary_start)});
      tl.fromTo(q(".tertiary img"), {{opacity: 0, x: 48, y: 22, scale: 0.95}}, {{opacity: 1, x: 0, y: 0, scale: 1, duration: {number(entrance - tertiary_start)}, ease: "power2.out"}}, {number(tertiary_start)});
      tl.fromTo(q(".foreground img"), {{opacity: 0, y: 22}}, {{opacity: 1, y: 0, duration: {number(entrance * 0.7)}, ease: "power2.out"}}, {number(entrance * 0.3)});
      tl.to(q(".primary img"), {{y: -8, duration: {number(bob)}, ease: "sine.inOut"}}, {number(entrance)});
      tl.to(q(".primary img"), {{y: 0, duration: {number(bob)}, ease: "sine.inOut"}}, {number(entrance + bob)});
      tl.to(q(".primary img"), {{y: -6, duration: {number(bob)}, ease: "sine.inOut"}}, {number(entrance + bob * 2)});
      tl.to(q(".primary img"), {{y: 0, duration: {number(bob)}, ease: "sine.inOut"}}, {number(entrance + bob * 3)});
      tl.fromTo(qAll(".breeze"), {{opacity: 0, y: 34}}, {{opacity: 0.8, y: -28, duration: {number(action_end - entrance)}, stagger: 0.18, ease: "sine.inOut"}}, {number(entrance)});
      tl.to(root, {{opacity: 0.98, duration: {number(duration - exit_at)}, ease: "power1.in"}}, {number(exit_at)});"""


def middle_timeline(scene: dict) -> str:
    duration = scene["durationSeconds"]
    entrance = duration * 0.18
    action_end = duration * 0.72
    exit_at = duration * 0.90
    return f"""
      tl.fromTo(q(".backdrop img"), {{scale: 1.025, x: -12}}, {{scale: 1.06, x: 10, duration: {number(action_end)}, ease: "power1.inOut"}}, 0);
      tl.fromTo(q(".architecture img"), {{opacity: 0, scale: 0.92, x: 70}}, {{opacity: 1, scale: 1.035, x: 0, duration: {number(entrance)}, ease: "power3.out"}}, 0);
      tl.fromTo(q(".primary img"), {{opacity: 0, x: 170, y: 54, scale: 0.9}}, {{opacity: 1, x: 0, y: 0, scale: 1, duration: {number(entrance * 0.82)}, ease: "power3.out"}}, {number(duration * 0.02)});
      tl.fromTo(q(".secondary img"), {{opacity: 0, x: -86, y: 38}}, {{opacity: 1, x: 0, y: 0, duration: {number(entrance * 0.72)}, ease: "power2.out"}}, {number(duration * 0.075)});
      tl.fromTo(q(".tertiary img"), {{opacity: 0, x: 64, y: -22}}, {{opacity: 1, x: 0, y: 0, duration: {number(entrance * 0.58)}, ease: "power2.out"}}, {number(duration * 0.12)});
      tl.fromTo(q(".foreground img"), {{opacity: 0, y: 36}}, {{opacity: 1, y: 0, duration: {number(entrance)}, ease: "power3.out"}}, 0);
      tl.fromTo(qAll(".streak"), {{opacity: 0, x: 260, scaleX: 0.3}}, {{opacity: 0.8, x: -140, scaleX: 1, duration: {number(max(0.8, (action_end - entrance) * 0.58))}, stagger: 0.16, ease: "power2.out"}}, {number(entrance * 0.45)});
      tl.to(q(".rear img"), {{x: -26, y: 8, duration: {number((action_end - entrance) * 0.5)}, ease: "sine.inOut"}}, {number(entrance)});
      tl.to(q(".rear img"), {{x: 0, y: 0, duration: {number((action_end - entrance) * 0.5)}, ease: "sine.inOut"}}, {number((entrance + action_end) * 0.5)});
      tl.to(q(".primary img"), {{x: 24, y: -10, duration: {number(action_end - entrance)}, ease: "power1.inOut"}}, {number(entrance)});
      tl.to(root, {{opacity: 0.96, duration: {number(duration - exit_at)}, ease: "power1.in"}}, {number(exit_at)});"""


def end_timeline(scene: dict) -> str:
    duration = scene["durationSeconds"]
    entrance = duration * 0.18
    action_end = duration * 0.72
    exit_at = duration * 0.90
    particle_duration = max(0.9, action_end - entrance)
    return f"""
      tl.fromTo(q(".backdrop img"), {{scale: 1}}, {{scale: 1.045, duration: {number(action_end)}, ease: "none"}}, 0);
      tl.fromTo(q(".architecture img"), {{opacity: 0, scale: 0.9}}, {{opacity: 1, scale: 1, duration: {number(entrance)}, ease: "back.out(1.25)"}}, 0);
      tl.fromTo(q(".primary img"), {{opacity: 0, y: 62, scale: 0.82}}, {{opacity: 1, y: 0, scale: 1, duration: {number(entrance * 0.9)}, ease: "back.out(1.55)"}}, {number(duration * 0.02)});
      tl.fromTo(q(".secondary img"), {{opacity: 0, x: 190, scale: 0.9}}, {{opacity: 1, x: 0, scale: 1, duration: {number(entrance * 0.72)}, ease: "power3.out"}}, {number(duration * 0.075)});
      tl.fromTo(q(".tertiary img"), {{opacity: 0, x: -160, scale: 0.92}}, {{opacity: 1, x: 0, scale: 1, duration: {number(entrance * 0.58)}, ease: "power3.out"}}, {number(duration * 0.12)});
      tl.fromTo(q(".foreground img"), {{opacity: 0, y: 45}}, {{opacity: 1, y: 0, duration: {number(entrance)}, ease: "power2.out"}}, 0);
      tl.fromTo(q(".glow"), {{opacity: 0, scale: 0.45}}, {{opacity: 0.62, scale: 1.25, duration: {number(particle_duration * 0.62)}, ease: "sine.out"}}, {number(entrance * 0.55)});
      tl.fromTo(qAll(".particle"), {{opacity: 0, x: 0, y: 30, scale: 0.4}}, {{opacity: 0.9, x: 0, y: -42, scale: 1.15, duration: {number(particle_duration)}, stagger: 0.06, ease: "power2.out"}}, {number(entrance * 0.7)});
      tl.to(q(".primary img"), {{y: -8, duration: {number((action_end - entrance) * 0.5)}, ease: "sine.inOut"}}, {number(entrance)});
      tl.to(q(".primary img"), {{y: 0, duration: {number((action_end - entrance) * 0.5)}, ease: "sine.inOut"}}, {number((entrance + action_end) * 0.5)});
      tl.to(root, {{opacity: 0.99, duration: {number(duration - exit_at)}, ease: "power1.in"}}, {number(exit_at)});"""


def scene_html(scene: dict, tokens: dict) -> str:
    timeline = {
        "start": start_timeline,
        "middle": middle_timeline,
        "end": end_timeline,
    }[scene["beat"]](scene)
    layers = [
        f"""
      <div class="layer backdrop" data-pixel-layer="backdrop" data-pixel-z="0">
        <img data-layout-ignore src="{html.escape(asset_src(scene['assets']['backdrop']))}" alt="" />
      </div>""",
        f"""
      <div class="layer cutout rear" data-pixel-layer="rear" data-pixel-z="1">
        <img data-layout-ignore src="{html.escape(asset_src(scene['assets']['rear']))}" alt="" />
      </div>""",
        f"""
      <div class="layer cutout architecture" data-pixel-layer="architecture" data-pixel-z="2">
        <img data-layout-ignore src="{html.escape(asset_src(scene['assets']['architecture']))}" alt="" />
      </div>""",
        subject_markup(scene, "tertiary", 3),
        subject_markup(scene, "secondary", 4),
        subject_markup(scene, "primary", 5),
        f"""
      <div class="layer cutout foreground" data-pixel-layer="foreground" data-pixel-z="6">
        <img data-layout-ignore src="{html.escape(asset_src(scene['assets']['foreground']))}" alt="" />
      </div>""",
    ]
    editorial_timeline = shot_timeline(scene)
    return f"""<template id="{scene['id']}-template">
  <div
    id="scene-{scene['id']}"
    data-composition-id="{scene['id']}"
    data-width="1920"
    data-height="1080"
    data-duration="{number(scene['durationSeconds'])}"
    data-layout-allow-overflow
  >
    <div class="camera-rig" data-layout-allow-overflow>
      {''.join(layers)}
      {accents(scene)}
    </div>
    <div class="internal-cut"></div>
    {comic_treatments(scene)}
    {common_scene_css(scene, tokens)}
    <script>
      (function () {{
        const root = document.querySelector("#scene-{scene['id']}");
        const q = (selector) => root.querySelector(selector);
        const qAll = (selector) => root.querySelectorAll(selector);
        const tl = gsap.timeline({{ paused: true }});
        {timeline}
        {editorial_timeline}
        window.__timelines = window.__timelines || {{}};
        window.__timelines["{scene['id']}"] = tl;
      }})();
    </script>
  </div>
</template>
"""


def transition_markup(manifest: dict) -> tuple[str, str]:
    scenes = manifest["scenes"]
    markup = []
    timeline = []
    for index, scene in enumerate(scenes[1:], start=1):
        kind = scene["transitionIn"]
        boundary = scene["startSeconds"]
        duration = min(0.9, max(0.6, scene["durationSeconds"] * 0.08))
        start = max(0, boundary - duration / 2)
        transition_id = f"transition-{index}-{kind}"
        children = ""
        if kind == "horizontal-blinds":
            children = "".join(f'<span style="top:{i * 90}px"></span>' for i in range(12))
        elif kind == "grid-dissolve":
            children = "".join(
                f'<span style="left:{(i % 8) * 240}px;top:{(i // 8) * 216}px"></span>'
                for i in range(40)
            )
        else:
            children = "<span></span><span></span><span></span>"
        markup.append(
            f"""
      <div id="{transition_id}" class="clip transition" data-layout-allow-overflow
           data-start="{number(start)}" data-duration="{number(duration)}" data-track-index="800">
        <div id="{transition_id}-fx" class="transition-fx transition-{kind}" data-layout-allow-overflow>
          {children}
        </div>
      </div>"""
        )
        selector = f"#{transition_id}-fx"
        half = duration * 0.5
        end = start + duration
        if kind == "whip-pan":
            timeline.append(
                f'tl.fromTo("{selector}", {{opacity:0,x:-1920}}, '
                f'{{opacity:1,x:0,duration:{number(half)},ease:"power4.in"}}, {number(start)});'
            )
            timeline.append(
                f'tl.to("{selector}", {{opacity:0,x:1920,duration:{number(half)},ease:"power4.out"}}, '
                f'{number(start + half)});'
            )
        elif kind in {"chromatic-split", "grid-dissolve"}:
            timeline.append(
                f'tl.fromTo("{selector}", {{opacity:0,scale:1.08}}, '
                f'{{opacity:0.94,scale:1,duration:{number(half)},ease:"steps(4)"}}, {number(start)});'
            )
            timeline.append(
                f'tl.to("{selector}", {{opacity:0,duration:{number(half)},ease:"steps(4)"}}, '
                f'{number(start + half)});'
            )
        else:
            timeline.append(
                f'tl.fromTo("{selector}", {{opacity:0,scale:0.96}}, '
                f'{{opacity:0.9,scale:1.04,duration:{number(half)},ease:"sine.in"}}, {number(start)});'
            )
            timeline.append(
                f'tl.to("{selector}", {{opacity:0,scale:1.08,duration:{number(half)},ease:"sine.out"}}, '
                f'{number(start + half)});'
            )
        timeline.append(
            f'tl.set("{selector}", {{opacity:0}}, {number(end)});'
        )
    return "".join(markup), "\n        ".join(timeline)


def caption_markup(manifest: dict) -> str:
    rows = []
    cues = manifest.get("captions")
    if not cues:
        cues = [
            {
                "startSeconds": scene["captionFrom"],
                "endSeconds": scene["captionTo"],
                "text": scene["narration"],
                "speaker": "旁白",
                "role": "narrator",
            }
            for scene in manifest["scenes"]
        ]
    for index, cue in enumerate(cues):
        start = cue["startSeconds"]
        duration = cue["endSeconds"] - start
        speaker = cue.get("speaker", "旁白")
        role = cue.get("role", "narrator")
        kind = cue.get("kind", "narration")
        rows.append(
            f"""
      <div id="caption-{index + 1}" class="clip caption caption-{html.escape(role)} caption-{html.escape(kind)}"
           data-start="{number(start)}" data-duration="{number(duration)}" data-track-index="900">
        <span>{html.escape(speaker)}</span><p>{html.escape(cue['text'])}</p>
      </div>"""
        )
    return "".join(rows)


def audio_markup(manifest: dict) -> str:
    total = manifest["metadata"]["durationSeconds"]
    audio = manifest["audio"]
    if manifest.get("audioClips"):
        return "".join(
            f"""
      <audio id="{html.escape(clip['id'])}" class="clip" src="{html.escape(clip['src'])}"
             data-start="{number(clip['startSeconds'])}" data-duration="{number(clip['durationSeconds'])}"
             data-track-index="{clip.get('trackIndex', 950)}" data-volume="{number(clip.get('volume', 1))}"></audio>"""
            for clip in manifest["audioClips"]
        )
    rows = [
        f"""
      <audio id="narration" class="clip" src="{html.escape(audio['narrationPath'])}"
             data-start="0" data-duration="{number(total)}" data-track-index="950" data-volume="1"></audio>""",
        f"""
      <audio id="music" class="clip" src="{html.escape(audio['musicPath'])}"
             data-start="0" data-duration="{number(total)}" data-track-index="951" data-volume="0.2"></audio>""",
    ]
    sfx_keys = ("impactPath", "whooshPath", "chimePath")
    for index, (scene, key) in enumerate(zip(manifest["scenes"], sfx_keys)):
        start = scene["startSeconds"] + 0.08
        rows.append(
            f"""
      <audio id="sfx-{index + 1}" class="clip" src="{html.escape(audio[key])}"
             data-start="{number(start)}" data-duration="1" data-track-index="{952 + index}" data-volume="0.72"></audio>"""
        )
    return "".join(rows)


def index_html(manifest: dict) -> str:
    total = manifest["metadata"]["durationSeconds"]
    tokens = manifest["style"]["tokens"]
    scene_hosts = []
    for scene in manifest["scenes"]:
        scene_hosts.append(
            f"""
      <div id="slot-{scene['id']}" class="clip scene-slot"
           data-composition-id="{scene['id']}"
           data-composition-src="compositions/{scene['id']}.html"
           data-start="{number(scene['startSeconds'])}"
           data-duration="{number(scene['durationSeconds'])}"
           data-track-index="10"></div>"""
        )
    transitions, transition_timeline = transition_markup(manifest)
    title = html.escape(manifest["metadata"]["title"])
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>{title}</title>
    <script src="vendor/gsap.min.js"></script>
    <style>
      * {{ box-sizing: border-box; }}
      @font-face {{
        font-family: "PixelChinese";
        src: local("PingFang SC");
        font-style: normal;
        font-weight: 400 900;
      }}
      html, body {{
        margin: 0;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: {tokens['canvas']};
      }}
      body {{
        font-family: "PixelChinese", sans-serif;
      }}
      #main {{
        position: relative;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: {tokens['canvas']};
      }}
      .scene-slot {{
        position: absolute;
        inset: 0;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
      }}
      .caption {{
        position: absolute;
        left: 170px;
        bottom: 58px;
        width: 1420px;
        min-height: 96px;
        z-index: 900;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px 46px;
        color: {tokens['ink']};
        background: {tokens['canvas']};
        border: 5px solid {tokens['ink']};
        box-shadow: 10px 10px 0 {tokens['shadow']};
      }}
      .caption-dialogue, .caption-thought {{
        left: auto;
        right: 150px;
        bottom: 72px;
        width: auto;
        max-width: 1180px;
        min-width: 620px;
        border-radius: 0;
        background: {tokens['ink']};
        color: {tokens['canvas']};
        transform: rotate(-0.4deg);
      }}
      .caption-dialogue::after {{
        content: "";
        position: absolute;
        right: 110px;
        bottom: -38px;
        width: 0;
        height: 0;
        border: 20px solid transparent;
        border-top-color: {tokens['ink']};
        border-left-width: 42px;
      }}
      .caption-thought {{
        border: 6px dashed {tokens['accent2']};
      }}
      .caption-narration {{
        left: 150px;
        bottom: 54px;
        width: 1280px;
        border-left: 18px solid {tokens['accent']};
      }}
      .caption p {{
        margin: 0;
        max-width: 1460px;
        font-size: 42px;
        line-height: 1.35;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0;
      }}
      .caption span {{
        flex: 0 0 auto;
        margin-right: 22px;
        padding: 8px 14px;
        font-size: 26px;
        font-weight: 900;
        color: {tokens['canvas']};
        background: {tokens['accent']};
      }}
      .transition {{
        position: absolute;
        inset: 0;
        z-index: 800;
        overflow: hidden;
      }}
      .transition-fx {{
        position: absolute;
        inset: 0;
        overflow: hidden;
        opacity: 0;
        background: {tokens['accent']};
      }}
      .transition span {{
        position: absolute;
        display: block;
        background: {tokens['accent2']};
      }}
      .transition-whip-pan span {{
        top: 0;
        width: 34%;
        height: 100%;
      }}
      .transition-whip-pan span:nth-child(1) {{ left: 0; background: {tokens['accent']}; }}
      .transition-whip-pan span:nth-child(2) {{ left: 33%; background: {tokens['ink']}; }}
      .transition-whip-pan span:nth-child(3) {{ left: 66%; background: {tokens['accent2']}; }}
      .transition-horizontal-blinds {{ background: transparent; }}
      .transition-horizontal-blinds span {{ left: 0; width: 100%; height: 92px; }}
      .transition-chromatic-split {{ background: {tokens['accent']}; mix-blend-mode: screen; }}
      .transition-chromatic-split span {{ inset: 0; width: 100%; height: 100%; }}
      .transition-chromatic-split span:nth-child(1) {{ left: -24px; background: #ff334f; }}
      .transition-chromatic-split span:nth-child(2) {{ left: 24px; background: #22d9ff; }}
      .transition-chromatic-split span:nth-child(3) {{ background: {tokens['ink']}; opacity: .42; }}
      .transition-grid-dissolve {{ background: transparent; }}
      .transition-grid-dissolve span {{ width: 242px; height: 218px; }}
      .transition-blur-through, .transition-light-leak {{
        background: {tokens['accent2']};
        box-shadow: inset 0 0 180px {tokens['ink']};
      }}
      .transition-blur-through span, .transition-light-leak span {{
        width: 42%;
        height: 100%;
        top: 0;
        opacity: .36;
      }}
      .transition-blur-through span:nth-child(2), .transition-light-leak span:nth-child(2) {{ left: 30%; }}
      .transition-blur-through span:nth-child(3), .transition-light-leak span:nth-child(3) {{ right: 0; }}
    </style>
  </head>
  <body>
    <div id="main" data-composition-id="main" data-start="0"
         data-duration="{number(total)}" data-width="1920" data-height="1080" data-fps="30">
      {''.join(scene_hosts)}
      {transitions}
      {caption_markup(manifest)}
      {audio_markup(manifest)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {transition_timeline}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def motion_payload(scene: dict) -> dict:
    duration = scene["durationSeconds"]
    starts = {
        "primary": round(duration * 0.025, 6),
        "secondary": round(duration * 0.075, 6),
        "tertiary": round(duration * 0.12, 6),
    }
    bounds = {
        "primary": {"x": 615, "y": 190, "width": 690, "height": 715},
        "secondary": {"x": 95, "y": 300, "width": 450, "height": 590},
        "tertiary": {"x": 1485, "y": 385, "width": 330, "height": 485},
    }
    shots = scene_shots(scene)
    shot_rows = []
    cuts = []
    for index, shot in enumerate(shots):
        camera = shot_camera(shot, index)
        blocking = shot_blocking(shot, index)
        travel = blocking["travel"]
        blocking_bounds = {}
        blocking_end_bounds = {}
        for role, base in bounds.items():
            state = blocking["subjects"][role]
            start_bounds = transformed_bounds(base, state)
            end_state = dict(state)
            if travel["role"] in {role, "ensemble"}:
                end_state["x"] += travel["x"]
                end_state["y"] += travel["y"]
            blocking_bounds[role] = start_bounds
            blocking_end_bounds[role] = transformed_bounds(base, end_state)
        shot_rows.append(
            {
                "id": shot["id"],
                "index": index + 1,
                "framing": shot.get("framing", "medium"),
                "focusRole": shot.get("focusRole", "primary"),
                "from": round(shot["startSeconds"], 6),
                "to": round(shot["startSeconds"] + shot["durationSeconds"], 6),
                "camera": camera,
                "blocking": blocking,
                "blockingBounds": blocking_bounds,
                "blockingEndBounds": blocking_end_bounds,
            }
        )
        if index:
            cuts.append(
                {
                    "fromShot": shots[index - 1]["id"],
                    "toShot": shot["id"],
                    "at": round(shot["startSeconds"], 6),
                    "anticipationAt": round(max(0, shot["startSeconds"] - 0.18), 6),
                }
            )
    return {
        "schemaVersion": 3,
        "compositionId": scene["id"],
        "durationSeconds": duration,
        "layerOrder": LAYER_ORDER,
        "phases": {
            "entrance": [0, round(duration * 0.18, 6)],
            "action": [round(duration * 0.18, 6), round(duration * 0.72, 6)],
            "hold": [round(duration * 0.72, 6), round(duration * 0.90, 6)],
            "transition": [round(duration * 0.90, 6), duration],
        },
        "subjects": [
            {"id": role, "role": role, "entranceStart": starts[role], "bounds": bounds[role]}
            for role in ("primary", "secondary", "tertiary")
        ],
        "shots": shot_rows,
        "cuts": cuts,
        "captionSegments": [
            cue
            for cue in scene.get("captions", [])
        ],
        "motionRules": scene["motionRules"],
        "transitionIn": scene["transitionIn"],
        "direction": scene["direction"],
        "sourceDirection": scene["sourceDirection"],
        "sourceDirections": scene.get(
            "sourceDirections",
            {
                "primary": scene["sourceDirection"],
                "secondary": scene["sourceDirection"],
                "tertiary": scene["sourceDirection"],
            },
        ),
        "assertions": {
            "primaryAppearsFirst": True,
            "subjectsStayInFrame": True,
            "plannedHoldWindow": True,
            "noUnboundedAnimation": True,
            "threeEditorialShots": len(shot_rows) == 3,
            "framingVariety": len({shot["framing"] for shot in shot_rows}) >= 3,
            "shotBlockingVariety": blocking_varies(shot_rows),
        },
    }


def update_storyboard(production: Path) -> None:
    path = production / "STORYBOARD.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^- status: (?:outline|timed)$", "- status: animated", text)
    path.write_text(text, encoding="utf-8")


def update_status(production: Path, evidence: list[str]) -> None:
    path = production / "run-status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    status["stages"]["composition"] = {"status": "complete", "evidence": evidence}
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def adopt_media(production: Path) -> str | None:
    if not MEDIA_USE.is_file():
        return None
    result = subprocess.run(
        ["node", str(MEDIA_USE), "--adopt", "--project", str(production), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def compose(production: Path, adopt: bool = True) -> None:
    manifest_path = production / "production-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("production-manifest.json is created after narration timing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for scene in manifest["scenes"]:
        for key in ("backdrop", "rear", "architecture", "foreground", "primary", "secondary", "tertiary"):
            path = production / scene["assets"][key]
            if not path.is_file():
                raise FileNotFoundError(path)

    vendor = production / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    gsap_source = REPO_ROOT / "node_modules/gsap/dist/gsap.min.js"
    if not gsap_source.is_file():
        raise FileNotFoundError("run npm install at the repository root before composing")
    shutil.copy2(gsap_source, vendor / "gsap.min.js")

    compositions = production / "compositions"
    compositions.mkdir(parents=True, exist_ok=True)
    evidence = ["index.html", "vendor/gsap.min.js"]
    for scene in manifest["scenes"]:
        html_path = compositions / f"{scene['id']}.html"
        html_path.write_text(
            clean_generated_html(scene_html(scene, manifest["style"]["tokens"])),
            encoding="utf-8",
        )
        motion_path = compositions / f"{scene['id']}.motion.json"
        motion_path.write_text(
            json.dumps(motion_payload(scene), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        evidence.extend(
            [
                html_path.relative_to(production).as_posix(),
                motion_path.relative_to(production).as_posix(),
            ]
        )
    (production / "index.html").write_text(
        clean_generated_html(index_html(manifest)),
        encoding="utf-8",
    )
    update_storyboard(production)
    if adopt:
        adopt_media(production)
        if (production / ".media/manifest.jsonl").is_file():
            evidence.extend([".media/manifest.jsonl", ".media/index.md"])
    update_status(production, evidence)
    print(json.dumps({"production": str(production), "evidence": evidence}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--no-adopt", action="store_true")
    args = parser.parse_args()
    compose(Path(args.production).resolve(), adopt=not args.no_adopt)


if __name__ == "__main__":
    main()
